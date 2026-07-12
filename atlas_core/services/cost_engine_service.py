"""Deterministic acquisition cost engine for Atlas Core."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP
import hashlib
import io
import json
import math
from typing import Any, cast

from atlas_core.domain.commercial_knowledge import KnowledgeFreshnessStatus
from atlas_core.domain.cost_engine import (
    CommercialCoverage,
    CostCandidate,
    CostConfidence,
    CostEvaluationRequest,
    CostEvaluationResult,
    CostFreshness,
    CostLine,
    CostProvenance,
    CostResult,
    CostSelectionDiagnostic,
    CostSelectionRequest,
    CostSelectionResult,
    CostSelectionResultStatus,
    CostSelection,
    CostStatus,
    CostSummary,
    ProjectCostSummary,
    VendorClassification,
)
from atlas_core.domain.deterministic_estimate import (
    CostStatus as EstimateCostStatus,
    Estimate,
    EstimateLine,
    EstimatePackage,
    ProductResolutionStatus,
)
from atlas_core.domain.product_resolution import ProductResolution
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService


class DeterministicCostEngine:
    POLICY_VERSION = "atlas-cost-policy:v2"

    def __init__(self, *, as_of: date | None = None) -> None:
        self.as_of = as_of or datetime.now(UTC).date()

    def run(
        self,
        *,
        estimate: Estimate,
        product_resolutions: list[ProductResolution | dict[str, Any]],
        commercial_state: dict[str, Any],
        project_id: str,
        preferred_vendor_policy: dict[str, Any] | None = None,
        project_quotes: list[dict[str, Any]] | None = None,
        allowances: dict[str, float] | None = None,
        vendor_type_overrides: dict[str, str] | None = None,
        quick_add_products: list[dict[str, Any]] | None = None,
        manual_overrides: dict[str, dict[str, Any]] | None = None,
        eligibility_state: dict[str, Any] | None = None,
    ) -> CostResult:
        resolutions = [
            item if isinstance(item, ProductResolution) else ProductResolution(**item)
            for item in product_resolutions
        ]
        by_source = {item.source_object_id: item for item in resolutions}
        policy = dict(preferred_vendor_policy or {})
        quote_rows = [dict(item) for item in list(project_quotes or [])]
        allowance_map = dict(allowances or {})
        vendor_type_map: dict[str, VendorClassification] = {}
        for key, value in dict(vendor_type_overrides or {}).items():
            vendor_key = self._safe(key)
            if not vendor_key:
                continue
            try:
                vendor_type_map[vendor_key] = VendorClassification(
                    self._safe(value, VendorClassification.OTHER.value)
                )
            except ValueError:
                vendor_type_map[vendor_key] = VendorClassification.OTHER
        quick_add = [dict(item) for item in list(quick_add_products or [])]
        overrides = dict(manual_overrides or {})
        eligibility = dict(eligibility_state or {})

        commercial_service = CommercialKnowledgeService(
            state=commercial_state, as_of=self.as_of
        )
        commercial = commercial_service.to_dict()
        freshness_rows = {
            self._safe(item.get("product"), ""): dict(item)
            for item in commercial_service.freshness_rows()
            if self._safe(item.get("product"), "")
        }

        lines: list[CostLine] = []
        for line in estimate.all_lines():
            resolution = by_source.get(line.source_object)
            cost_line = self._cost_line(
                line=line,
                resolution=resolution,
                commercial=commercial,
                freshness_rows=freshness_rows,
                policy=policy,
                project_quotes=quote_rows,
                allowances=allowance_map,
                vendor_type_overrides=vendor_type_map,
                quick_add_products=quick_add,
                project_id=project_id,
                manual_overrides=overrides,
                eligibility_state=eligibility,
            )
            lines.append(cost_line)

        summary = self._summary(lines)
        coverage = self._coverage(lines)
        run_id = self._run_id(
            estimate=estimate,
            resolutions=resolutions,
            commercial=commercial,
            policy=policy,
            quotes=quote_rows,
            allowances=allowance_map,
            quick_add=quick_add,
        )
        return CostResult(
            cost_run_id=run_id,
            run_timestamp=self._now_iso(),
            cost_policy_version=self.POLICY_VERSION,
            lines=lines,
            summary=summary,
            commercial_coverage=coverage,
        )

    def evaluate_costs(
        self, request: CostEvaluationRequest | dict[str, Any]
    ) -> CostEvaluationResult:
        payload = (
            request
            if isinstance(request, CostEvaluationRequest)
            else CostEvaluationRequest(**request)
        )
        normalized_resolutions = cast(
            list[ProductResolution | dict[str, Any]],
            [dict(item) for item in list(payload.product_resolutions or [])],
        )
        result = self.run(
            estimate=(
                payload.estimate
                if isinstance(payload.estimate, Estimate)
                else Estimate(**payload.estimate)
            ),
            product_resolutions=normalized_resolutions,
            commercial_state=payload.commercial_state,
            project_id=payload.project_id,
            preferred_vendor_policy=payload.preferred_vendor_policy,
            project_quotes=payload.project_quotes,
            allowances=payload.allowances,
            vendor_type_overrides=payload.vendor_type_overrides,
            quick_add_products=payload.quick_add_products,
            manual_overrides=payload.manual_overrides,
            eligibility_state=payload.eligibility_state,
        )
        return CostEvaluationResult(result=result)

    def replay_cost_snapshot(self, snapshot: CostResult | dict[str, Any]) -> CostResult:
        return snapshot if isinstance(snapshot, CostResult) else CostResult(**snapshot)

    def compare_cost_snapshots(
        self,
        *,
        baseline: CostResult | dict[str, Any],
        candidate: CostResult | dict[str, Any],
    ) -> list[dict[str, Any]]:
        left = baseline if isinstance(baseline, CostResult) else CostResult(**baseline)
        right = (
            candidate if isinstance(candidate, CostResult) else CostResult(**candidate)
        )
        left_by_line = {item.estimate_line_id: item for item in left.lines}
        right_by_line = {item.estimate_line_id: item for item in right.lines}
        keys = sorted(set(left_by_line) | set(right_by_line))
        deltas: list[dict[str, Any]] = []
        for line_id in keys:
            old = left_by_line.get(line_id)
            new = right_by_line.get(line_id)
            if old is None or new is None:
                deltas.append(
                    {
                        "estimate_line_id": line_id,
                        "change": "line_added_or_removed",
                        "old_status": old.status.value if old else None,
                        "new_status": new.status.value if new else None,
                    }
                )
                continue
            if (
                old.unit_cost != new.unit_cost
                or old.status is not new.status
                or old.price_record_id != new.price_record_id
                or old.vendor_offering_id != new.vendor_offering_id
            ):
                deltas.append(
                    {
                        "estimate_line_id": line_id,
                        "change": "cost_selection_changed",
                        "old_unit_cost": old.unit_cost,
                        "new_unit_cost": new.unit_cost,
                        "old_status": old.status.value,
                        "new_status": new.status.value,
                        "old_price_record_id": old.price_record_id,
                        "new_price_record_id": new.price_record_id,
                        "old_vendor_offering_id": old.vendor_offering_id,
                        "new_vendor_offering_id": new.vendor_offering_id,
                    }
                )
        return deltas

    def select_cost(
        self,
        request: CostSelectionRequest | dict[str, Any],
        *,
        commercial_state: dict[str, Any],
    ) -> CostSelectionResult:
        req = (
            request
            if isinstance(request, CostSelectionRequest)
            else CostSelectionRequest(**request)
        )
        estimate = Estimate(
            estimate_id="estimate:cost-selection-inspector",
            project_id="cost-selection-inspector",
            project_name="Cost Selection Inspector",
            packages=[
                EstimatePackage(
                    package_id="pkg:selection",
                    name="Cost Selection",
                    lines=[
                        EstimateLine(
                            line_id="cost-selection-line:1",
                            source_object="cost-selection-source:1",
                            object_type="product",
                            manufacturer=(
                                req.product_id.split("::", 1)[0]
                                if "::" in req.product_id
                                else "Unknown"
                            ),
                            model=(
                                req.product_id.split("::", 1)[1]
                                if "::" in req.product_id
                                else req.product_id
                            ),
                            description="Core Cost Selection",
                            quantity=req.requested_quantity,
                            pricing_status=EstimateCostStatus.NO_PRICING,
                            labor_status=EstimateCostStatus.NO_PRICING,
                            confidence=0.9,
                        )
                    ],
                )
            ],
        )
        resolution = ProductResolution(
            resolution_id="resolution:cost-selection:1",
            source_object_id="cost-selection-source:1",
            resolution_status=ProductResolutionStatus.EXACT_PRODUCT,
            canonical_product={
                "product_id": req.product_id,
                "manufacturer": (
                    req.product_id.split("::", 1)[0]
                    if "::" in req.product_id
                    else "Unknown"
                ),
                "model": (
                    req.product_id.split("::", 1)[1]
                    if "::" in req.product_id
                    else req.product_id
                ),
            },
            manufacturer=(
                req.product_id.split("::", 1)[0]
                if "::" in req.product_id
                else "Unknown"
            ),
            model=(
                req.product_id.split("::", 1)[1]
                if "::" in req.product_id
                else req.product_id
            ),
            resolution_confidence=1.0,
            resolution_reason="cost_selection_request",
            candidate_matches=[],
            source_evidence=[],
            canonical_product_id=req.product_id,
            manufacturer_id=(
                req.product_id.split("::", 1)[0]
                if "::" in req.product_id
                else "unknown"
            ),
        )
        policy: dict[str, Any] = {}
        if req.preferred_vendor:
            policy["organization"] = req.preferred_vendor
        if req.preferred_purchasing_channel:
            policy["preferred_purchasing_channel"] = req.preferred_purchasing_channel

        as_of_date = self._date_from_text(req.as_of_date)
        engine = (
            self if as_of_date is None else DeterministicCostEngine(as_of=as_of_date)
        )
        result = engine.run(
            estimate=estimate,
            product_resolutions=[resolution],
            commercial_state=commercial_state,
            project_id="cost-selection-inspector",
            preferred_vendor_policy=policy,
        )
        line = result.lines[0] if result.lines else None
        if line is None:
            return CostSelectionResult(
                request=req,
                status=CostSelectionResultStatus.NO_ELIGIBLE_COST,
                selected_candidate=None,
                diagnostics=[
                    CostSelectionDiagnostic(
                        code="no_cost_line",
                        severity="error",
                        message="Cost selection did not produce a cost line.",
                    )
                ],
            )

        selection = line.selection or CostSelection(
            selected_candidate_id=None,
            method="none",
            reason="No selection payload.",
            candidates=[],
            decision_trace=[],
        )
        selected_candidate = next(
            (
                item
                for item in selection.candidates
                if item.candidate_id == selection.selected_candidate_id
            ),
            None,
        )
        filtered_candidates, diagnostics = engine._apply_request_restrictions(
            candidates=selection.candidates,
            request=req,
        )
        if (
            selected_candidate is not None
            and selected_candidate not in filtered_candidates
        ):
            selected_candidate = None

        if selected_candidate is None:
            status = CostSelectionResultStatus.NO_ELIGIBLE_COST
            if any(item.code == "future_cost_only" for item in diagnostics):
                status = CostSelectionResultStatus.FUTURE_COST_ONLY
            elif any(item.code == "expired_cost_only" for item in diagnostics):
                status = CostSelectionResultStatus.EXPIRED_COST_ONLY
            elif any(item.code == "unsupported_currency" for item in diagnostics):
                status = CostSelectionResultStatus.UNSUPPORTED_CURRENCY
            return CostSelectionResult(
                request=req,
                status=status,
                selected_candidate=None,
                rejected_candidates=list(filtered_candidates),
                normalized_requested_quantity=req.requested_quantity,
                purchasable_quantity=0.0,
                package_count=0,
                extended_acquisition_cost=0.0,
                deterministic_confidence=0.0,
                confidence_breakdown={},
                diagnostics=diagnostics,
                tie_break_sequence=list(selection.decision_trace),
                selection_timestamp=engine._now_iso(),
            )
        raw_unit = selected_candidate.acquisition_cost
        eff_unit = selected_candidate.normalized_unit_cost or raw_unit
        purch_qty = selected_candidate.purchasing_quantity or req.requested_quantity
        extended_cost = self._decimal_mul(eff_unit, purch_qty)
        package_count = 0
        if selected_candidate.pack_quantity and selected_candidate.pack_quantity > 0:
            package_count = int(math.ceil(purch_qty / selected_candidate.pack_quantity))

        confidence_breakdown: dict[str, Any] = {}
        if line.confidence is not None:
            confidence_breakdown = {
                "rationale": list(line.confidence.rationale),
                "score": line.confidence.score,
            }

        source_file_hash = ""
        version_id = self._safe(selected_candidate.price_sheet_version_id, "")
        if version_id:
            version = dict(
                (commercial_state.get("price_sheet_versions") or {}).get(version_id)
                or {}
            )
            source_file_hash = self._safe(version.get("file_hash"), "")

        provenance = CostProvenance(
            product_id=req.product_id,
            vendor=selected_candidate.vendor,
            vendor_offering_id=selected_candidate.vendor_offering_id,
            price_sheet_id=selected_candidate.price_sheet_id,
            price_sheet_version_id=selected_candidate.price_sheet_version_id,
            price_record_id=selected_candidate.price_record_id,
            source_filename=selected_candidate.source_file,
            source_file_hash=source_file_hash,
            import_timestamp=selected_candidate.import_date,
            effective_date=selected_candidate.effective_date,
            expiration_date=selected_candidate.expiration_date,
            source_reference=(
                str(selected_candidate.source_row)
                if selected_candidate.source_row is not None
                else ""
            ),
            selection_rule=line.selection_rule_id,
            selection_timestamp=line.selection_timestamp,
        )
        rejected = [
            item
            for item in filtered_candidates
            if item.candidate_id != selected_candidate.candidate_id
        ]
        status = (
            CostSelectionResultStatus.SELECTED_WITH_WARNINGS
            if diagnostics or line.warnings
            else CostSelectionResultStatus.SELECTED
        )
        return CostSelectionResult(
            request=req,
            status=status,
            selected_candidate=selected_candidate,
            rejected_candidates=rejected,
            normalized_requested_quantity=req.requested_quantity,
            purchasable_quantity=float(purch_qty),
            package_count=package_count,
            selected_source_unit_cost=raw_unit,
            effective_per_unit_cost=eff_unit,
            extended_acquisition_cost=extended_cost,
            selection_rule=line.selection_rule_id,
            tie_break_sequence=list(selection.decision_trace),
            deterministic_confidence=(
                line.confidence.score if line.confidence else 0.0
            ),
            confidence_breakdown=confidence_breakdown,
            diagnostics=diagnostics
            + [
                CostSelectionDiagnostic(
                    code="cost_warning",
                    severity="warning",
                    message=item,
                )
                for item in list(line.warnings)
            ],
            provenance=provenance,
            selection_timestamp=line.selection_timestamp,
        )

    def list_eligible_candidates(
        self,
        request: CostSelectionRequest | dict[str, Any],
        *,
        commercial_state: dict[str, Any],
    ) -> list[CostCandidate]:
        result = self.select_cost(request, commercial_state=commercial_state)
        candidates: list[CostCandidate] = []
        if result.selected_candidate is not None:
            candidates.append(result.selected_candidate)
        candidates.extend(list(result.rejected_candidates))
        return candidates

    def evaluate_candidate(
        self, candidate: CostCandidate | dict[str, Any]
    ) -> dict[str, Any]:
        item = (
            candidate
            if isinstance(candidate, CostCandidate)
            else CostCandidate(**candidate)
        )
        return {
            "candidate_id": item.candidate_id,
            "eligible": item.selected or not bool(item.rejected_reason),
            "reason": item.reason,
            "rejected_reason": item.rejected_reason,
            "rank": item.rank,
            "source_class": item.source_class,
        }

    def explain_candidate_rejection(
        self, candidate: CostCandidate | dict[str, Any]
    ) -> CostSelectionDiagnostic:
        item = (
            candidate
            if isinstance(candidate, CostCandidate)
            else CostCandidate(**candidate)
        )
        return CostSelectionDiagnostic(
            code="candidate_rejected" if item.rejected_reason else "candidate_selected",
            severity="warning" if item.rejected_reason else "informational",
            message=item.rejected_reason or "Candidate was selected.",
        )

    def compare_candidates(
        self,
        left: CostCandidate | dict[str, Any],
        right: CostCandidate | dict[str, Any],
    ) -> dict[str, Any]:
        lhs = left if isinstance(left, CostCandidate) else CostCandidate(**left)
        rhs = right if isinstance(right, CostCandidate) else CostCandidate(**right)
        return {
            "left_candidate_id": lhs.candidate_id,
            "right_candidate_id": rhs.candidate_id,
            "left_rank": lhs.rank,
            "right_rank": rhs.rank,
            "left_cost": lhs.normalized_unit_cost or lhs.acquisition_cost,
            "right_cost": rhs.normalized_unit_cost or rhs.acquisition_cost,
            "winner": lhs.candidate_id if lhs.rank <= rhs.rank else rhs.candidate_id,
        }

    def preview_quantity_normalization(
        self,
        *,
        requested_quantity: float,
        unit_cost: float,
        pack_quantity: int | None,
        minimum_order_quantity: int | None,
        purchase_multiple: int | None,
    ) -> dict[str, Any]:
        eff_unit, purch_qty = self._normalized_cost_quantity(
            raw_unit_cost=unit_cost,
            quantity=requested_quantity,
            pack_quantity=pack_quantity,
            minimum_order_quantity=minimum_order_quantity,
            purchase_multiple=purchase_multiple,
        )
        package_count = 0
        if pack_quantity and pack_quantity > 0:
            package_count = int(math.ceil(purch_qty / float(pack_quantity)))
        return {
            "requested_quantity": requested_quantity,
            "purchasable_quantity": purch_qty,
            "package_count": package_count,
            "effective_unit_cost": eff_unit,
            "extended_acquisition_cost": self._decimal_mul(eff_unit, purch_qty),
        }

    def get_selection_provenance(
        self, result: CostSelectionResult | dict[str, Any]
    ) -> dict[str, Any]:
        payload = (
            result
            if isinstance(result, CostSelectionResult)
            else CostSelectionResult(**result)
        )
        return payload.provenance.to_dict() if payload.provenance else {}

    def get_confidence_breakdown(
        self, result: CostSelectionResult | dict[str, Any]
    ) -> dict[str, Any]:
        payload = (
            result
            if isinstance(result, CostSelectionResult)
            else CostSelectionResult(**result)
        )
        return dict(payload.confidence_breakdown)

    def export_cost_summary_json(self, result: CostResult | dict[str, Any]) -> str:
        payload = result if isinstance(result, CostResult) else CostResult(**result)
        return json.dumps(
            {
                "cost_run_id": payload.cost_run_id,
                "run_timestamp": payload.run_timestamp,
                "cost_policy_version": payload.cost_policy_version,
                "summary": payload.summary.to_dict() if payload.summary else {},
            },
            indent=2,
            sort_keys=True,
        )

    def export_cost_lines_csv(self, result: CostResult | dict[str, Any]) -> str:
        payload = result if isinstance(result, CostResult) else CostResult(**result)
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "cost_line_id",
                "estimate_line_id",
                "equipment_object_id",
                "resolved_product_id",
                "vendor",
                "vendor_type",
                "unit_cost",
                "extended_cost",
                "status",
                "freshness",
                "price_sheet_version_id",
                "price_record_id",
                "source_file",
                "source_row",
            ],
        )
        writer.writeheader()
        for line in payload.lines:
            writer.writerow(
                {
                    "cost_line_id": line.cost_line_id,
                    "estimate_line_id": line.estimate_line_id,
                    "equipment_object_id": line.equipment_object_id,
                    "resolved_product_id": line.resolved_product_id,
                    "vendor": line.vendor,
                    "vendor_type": (
                        line.vendor_type.value if line.vendor_type is not None else ""
                    ),
                    "unit_cost": line.unit_cost,
                    "extended_cost": line.extended_cost,
                    "status": line.status.value,
                    "freshness": line.freshness.value,
                    "price_sheet_version_id": line.price_sheet_version_id,
                    "price_record_id": line.price_record_id,
                    "source_file": line.source_file,
                    "source_row": line.source_row,
                }
            )
        return buffer.getvalue()

    def export_commercial_coverage_json(
        self, result: CostResult | dict[str, Any]
    ) -> str:
        payload = result if isinstance(result, CostResult) else CostResult(**result)
        return json.dumps(
            (
                payload.commercial_coverage.to_dict()
                if payload.commercial_coverage
                else {}
            ),
            indent=2,
            sort_keys=True,
        )

    def export_cost_exceptions_csv(self, result: CostResult | dict[str, Any]) -> str:
        payload = result if isinstance(result, CostResult) else CostResult(**result)
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "cost_line_id",
                "status",
                "warning",
                "selection_reason",
            ],
        )
        writer.writeheader()
        for line in payload.lines:
            exceptional = line.status in {
                CostStatus.MISSING,
                CostStatus.ALLOWANCE,
                CostStatus.STALE,
                CostStatus.EXPIRED,
                CostStatus.UNAVAILABLE,
            }
            if not exceptional and not line.warnings:
                continue
            if line.warnings:
                for warning in line.warnings:
                    writer.writerow(
                        {
                            "cost_line_id": line.cost_line_id,
                            "status": line.status.value,
                            "warning": warning,
                            "selection_reason": (
                                line.selection.reason if line.selection else ""
                            ),
                        }
                    )
            else:
                writer.writerow(
                    {
                        "cost_line_id": line.cost_line_id,
                        "status": line.status.value,
                        "warning": "cost_exception",
                        "selection_reason": (
                            line.selection.reason if line.selection else ""
                        ),
                    }
                )
        return buffer.getvalue()

    def quick_add_product(
        self,
        *,
        project_id: str,
        manufacturer: str,
        model: str,
        description: str,
        vendor: str,
        vendor_type: str,
        cost: float,
        source: str,
        project_only: bool,
        project_state: dict[str, Any] | None = None,
        commercial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        product_key = (
            f"{self._safe(manufacturer, 'Unknown')}::{self._safe(model, 'Unknown')}"
        )
        payload: dict[str, Any] = {
            "project_id": self._safe(project_id, ""),
            "product": product_key,
            "manufacturer": self._safe(manufacturer, "Unknown"),
            "model": self._safe(model, "Unknown"),
            "description": self._safe(description, ""),
            "vendor": self._safe(vendor, "Unknown Vendor"),
            "vendor_type": self._safe(vendor_type, VendorClassification.OTHER.value),
            "cost": round(float(cost), 4),
            "source": self._safe(source, "quick_add"),
            "created_at": self._now_iso(),
        }

        if project_only:
            state = dict(project_state or {})
            quick = dict(state.get("quick_add_products") or {})
            project_rows = list(quick.get(project_id) or [])
            project_rows.append(payload)
            quick[project_id] = project_rows
            state["quick_add_products"] = quick
            return {
                "mode": "project_only",
                "quick_product": payload,
                "project_state": state,
            }

        service = CommercialKnowledgeService(state=commercial_state or {})
        promoted_vendor = str(payload["vendor"])
        promoted_manufacturer = str(payload["manufacturer"])
        promoted_model = str(payload["model"])
        result = service.import_price_sheet(
            vendor=promoted_vendor,
            manufacturer=promoted_manufacturer,
            sheet_name=f"Quick Add {promoted_manufacturer}",
            description="Quick Add Product Promotion",
            source_filename="quick_add_product",
            file_bytes=json.dumps(payload, sort_keys=True).encode("utf-8"),
            imported_by="atlas-estimator",
            rows=[
                {
                    "vendor": promoted_vendor,
                    "vendor_type": str(payload["vendor_type"]),
                    "manufacturer": promoted_manufacturer,
                    "model": promoted_model,
                    "description": str(payload["description"]),
                    "vendor_sku": promoted_model,
                    "unit_cost": float(payload["cost"]),
                    "currency": "USD",
                    "availability_status": "in_stock",
                    "effective_date": self.as_of.isoformat(),
                }
            ],
        )
        return {
            "mode": "promoted",
            "quick_product": payload,
            "promotion": result,
            "commercial_state": service.to_dict(),
        }

    def _cost_line(
        self,
        *,
        line: Any,
        resolution: ProductResolution | None,
        commercial: dict[str, Any],
        freshness_rows: dict[str, dict[str, Any]],
        policy: dict[str, Any],
        project_quotes: list[dict[str, Any]],
        allowances: dict[str, float],
        vendor_type_overrides: dict[str, VendorClassification],
        quick_add_products: list[dict[str, Any]],
        project_id: str,
        manual_overrides: dict[str, dict[str, Any]],
        eligibility_state: dict[str, Any],
    ) -> CostLine:
        source_id = self._safe(line.source_object, "")
        quantity = float(line.quantity)
        quantity_uom = self._safe(getattr(line, "unit_of_measure", "ea"), "ea")
        now_iso = self._now_iso()

        resolved_product_id = None
        resolution_status = ProductResolutionStatus.UNKNOWN_PRODUCT
        resolution_confidence = float(getattr(line, "confidence", 0.0) or 0.0)
        if resolution is not None:
            resolved_product_id = resolution.canonical_product_id
            resolution_status = resolution.resolution_status
            resolution_confidence = float(resolution.resolution_confidence)

        if resolution_status is ProductResolutionStatus.UNKNOWN_PRODUCT:
            return self._missing_line(
                line=line,
                source_id=source_id,
                resolved_product_id=resolved_product_id,
                reason="Unknown product is not eligible for deterministic cost.",
            )

        if resolution_status is ProductResolutionStatus.GENERIC_ALLOWANCE:
            allowance = allowances.get(source_id)
            if allowance is None:
                return self._missing_line(
                    line=line,
                    source_id=source_id,
                    resolved_product_id=resolved_product_id,
                    reason="No allowance configured for generic allowance product.",
                )
            return self._allowance_line(
                line=line,
                source_id=source_id,
                resolved_product_id=resolved_product_id,
                allowance=allowance,
            )

        override_key = self._safe(line.line_id, source_id)
        override = dict(
            manual_overrides.get(override_key) or manual_overrides.get(source_id) or {}
        )
        if self._override_active(override):
            override_cost = self._float_or_none(override.get("unit_cost"))
            if override_cost is not None:
                vendor_name = self._safe(override.get("vendor"), "Manual Override")
                override_candidate = CostCandidate(
                    candidate_id=f"override:{source_id}",
                    vendor=vendor_name,
                    vendor_type=self._classify_vendor(
                        vendor=vendor_name,
                        manufacturer=self._safe(line.manufacturer, ""),
                        override=vendor_type_overrides.get(vendor_name),
                        record={"vendor_type": override.get("vendor_type")},
                    ),
                    acquisition_cost=override_cost,
                    currency=self._safe(override.get("currency"), "USD"),
                    effective_date=self._safe(override.get("effective_date"), ""),
                    expiration_date=self._safe(override.get("expires_at"), ""),
                    import_date=self._safe(override.get("created_at"), now_iso),
                    days_since_import=0,
                    source_file="manual_override",
                    source_row=None,
                    price_sheet_id="",
                    price_sheet_version_id="",
                    vendor_offering_id=self._safe(
                        override.get("vendor_offering_id"), ""
                    ),
                    price_record_id=self._safe(override.get("price_record_id"), ""),
                    freshness=CostFreshness.UNKNOWN,
                    rank=0,
                    reason=self._safe(
                        override.get("reason"),
                        "Manual override selected as highest precedence source.",
                    ),
                    availability="override",
                    confidence=1.0,
                    source_class="manual_override",
                    candidate_fingerprint=self._candidate_fingerprint(
                        source_class="manual_override",
                        vendor=vendor_name,
                        price_record_id=self._safe(override.get("price_record_id"), ""),
                        effective_date=self._safe(override.get("effective_date"), ""),
                        expiration_date=self._safe(override.get("expires_at"), ""),
                    ),
                    selected=True,
                )
                selection = CostSelection(
                    selected_candidate_id=override_candidate.candidate_id,
                    method="manual_override",
                    reason=override_candidate.reason,
                    candidates=[override_candidate],
                    decision_trace=[
                        "Manual override evaluated before all deterministic commercial sources.",
                        f"Override owner={self._safe(override.get('owner_user_id'), 'unknown')}.",
                    ],
                )
                confidence_score, confidence_messages = self._confidence(
                    status=CostStatus.VERIFIED,
                    selected=override_candidate,
                    resolution_confidence=resolution_confidence,
                    candidate_count=1,
                    conflict_count=0,
                )
                return CostLine(
                    cost_line_id=f"cost-line:{line.line_id}",
                    estimate_line_id=line.line_id,
                    equipment_object_id=source_id,
                    resolved_product_id=resolved_product_id,
                    vendor_offering_id=override_candidate.vendor_offering_id or None,
                    price_record_id=override_candidate.price_record_id or None,
                    price_sheet_version_id=(
                        override_candidate.price_sheet_version_id or None
                    ),
                    vendor=override_candidate.vendor,
                    vendor_type=override_candidate.vendor_type,
                    quantity=quantity,
                    unit_cost=override_cost,
                    extended_cost=self._decimal_mul(override_cost, quantity),
                    currency=override_candidate.currency,
                    status=CostStatus.VERIFIED,
                    freshness=override_candidate.freshness,
                    import_date=override_candidate.import_date,
                    effective_date=override_candidate.effective_date,
                    expiration_date=override_candidate.expiration_date,
                    days_since_import=override_candidate.days_since_import,
                    source_file=override_candidate.source_file,
                    source_row=override_candidate.source_row,
                    price_sheet_id=override_candidate.price_sheet_id or None,
                    source_filename=override_candidate.source_file,
                    selection_rule_id="cost_source_hierarchy:manual_override",
                    selection_timestamp=now_iso,
                    as_of_date=self.as_of.isoformat(),
                    policy_version=self.POLICY_VERSION,
                    candidate_fingerprint=override_candidate.candidate_fingerprint,
                    vendor_id=vendor_name,
                    vendor_name=vendor_name,
                    purchasing_quantity=quantity,
                    quantity_uom=quantity_uom,
                    warnings=[],
                    confidence=CostConfidence(
                        score=confidence_score,
                        rationale=confidence_messages,
                    ),
                    selection=selection,
                    supporting_evidence=[
                        "SourceClass=manual_override",
                        f"Reason={override_candidate.reason}",
                    ],
                )

        product_key = self._product_key(
            canonical_product_id=resolved_product_id,
            manufacturer=self._safe(line.manufacturer, "Unknown"),
            model=self._safe(line.model, "Unknown"),
        )

        candidates = self._build_candidates(
            line=line,
            product_key=product_key,
            source_id=source_id,
            commercial=commercial,
            freshness_rows=freshness_rows,
            policy=policy,
            project_quotes=project_quotes,
            allowances=allowances,
            vendor_type_overrides=vendor_type_overrides,
            quick_add_products=quick_add_products,
            project_id=project_id,
            quantity=quantity,
            quantity_uom=quantity_uom,
            eligibility_state=eligibility_state,
        )
        candidates.sort(
            key=lambda item: (
                item.rank,
                float(item.normalized_unit_cost or item.acquisition_cost or 0.0),
                item.days_since_import if item.days_since_import is not None else 10**9,
                item.vendor.lower(),
                item.candidate_id,
            )
        )
        selected = candidates[0] if candidates else None

        if selected is None:
            has_future = self._has_future_records(
                product_key=product_key, commercial=commercial
            )
            return self._missing_line(
                line=line,
                source_id=source_id,
                resolved_product_id=resolved_product_id,
                reason=(
                    "future_pricing_only: no current pricing is effective for the as-of date."
                    if has_future
                    else "no_pricing_found: no deterministic cost candidate found."
                ),
                candidates=candidates,
            )

        for idx, candidate in enumerate(candidates):
            candidate.selected = idx == 0
            if idx > 0:
                candidate.rejected_reason = (
                    "Lower precedence candidate after deterministic ranking tie-break."
                )

        status = self._status_for_candidate(selected)
        unit_cost = selected.normalized_unit_cost or selected.acquisition_cost
        purchasing_quantity = selected.purchasing_quantity or quantity
        extended = round((unit_cost or 0.0) * purchasing_quantity, 2)

        confidence_score, confidence_messages = self._confidence(
            status=status,
            selected=selected,
            resolution_confidence=resolution_confidence,
            candidate_count=len(candidates),
            conflict_count=sum(1 for item in candidates if item.rank == selected.rank),
        )

        selection = CostSelection(
            selected_candidate_id=selected.candidate_id,
            method="deterministic",
            reason=selected.reason,
            candidates=candidates,
            decision_trace=[
                "Evaluated source hierarchy, vendor/channel precedence, date validity, and deterministic tie-breaks.",
                f"Selected rank {selected.rank} candidate {selected.candidate_id}.",
            ],
        )

        warnings: list[str] = []
        if status in {CostStatus.STALE, CostStatus.EXPIRED, CostStatus.MISSING}:
            warnings.append(f"Selected cost status requires review: {status.value}.")
        if status is CostStatus.UNAVAILABLE:
            warnings.append("Selected candidate is unavailable.")

        return CostLine(
            cost_line_id=f"cost-line:{line.line_id}",
            estimate_line_id=line.line_id,
            equipment_object_id=source_id,
            resolved_product_id=resolved_product_id,
            vendor_offering_id=selected.vendor_offering_id or None,
            price_record_id=selected.price_record_id or None,
            price_sheet_version_id=selected.price_sheet_version_id or None,
            vendor=selected.vendor,
            vendor_type=selected.vendor_type,
            quantity=quantity,
            unit_cost=unit_cost,
            extended_cost=extended,
            currency=selected.currency,
            status=status,
            freshness=selected.freshness,
            import_date=selected.import_date,
            effective_date=selected.effective_date,
            expiration_date=selected.expiration_date,
            days_since_import=selected.days_since_import,
            source_file=selected.source_file,
            source_row=selected.source_row,
            price_sheet_id=selected.price_sheet_id or None,
            source_filename=selected.source_file,
            selection_rule_id=f"cost_source_hierarchy:{selected.source_class}",
            selection_timestamp=now_iso,
            as_of_date=self.as_of.isoformat(),
            policy_version=self.POLICY_VERSION,
            candidate_fingerprint=selected.candidate_fingerprint,
            vendor_id=selected.vendor,
            vendor_name=selected.vendor,
            purchasing_quantity=purchasing_quantity,
            quantity_uom=quantity_uom,
            warnings=warnings,
            confidence=CostConfidence(
                score=confidence_score, rationale=confidence_messages
            ),
            selection=selection,
            supporting_evidence=[
                f"Vendor={selected.vendor}",
                f"VendorType={selected.vendor_type.value}",
                f"PriceSheet={selected.price_sheet_id or 'n/a'}",
                f"PriceSheetVersion={selected.price_sheet_version_id or 'n/a'}",
                f"PriceRecord={selected.price_record_id or 'n/a'}",
            ],
        )

    def _build_candidates(
        self,
        *,
        line: Any,
        product_key: str,
        source_id: str,
        commercial: dict[str, Any],
        freshness_rows: dict[str, dict[str, Any]],
        policy: dict[str, Any],
        project_quotes: list[dict[str, Any]],
        allowances: dict[str, float],
        vendor_type_overrides: dict[str, VendorClassification],
        quick_add_products: list[dict[str, Any]],
        project_id: str,
        quantity: float,
        quantity_uom: str,
        eligibility_state: dict[str, Any],
    ) -> list[CostCandidate]:
        candidates: list[CostCandidate] = []
        preferred_channel = self._safe(policy.get("preferred_purchasing_channel"), "")

        for index, quote in enumerate(project_quotes, start=1):
            if self._safe(quote.get("project_id"), "") != self._safe(project_id, ""):
                continue
            if self._safe(quote.get("product"), "") != product_key:
                continue
            if not bool(quote.get("active", True)):
                continue
            candidates.append(
                CostCandidate(
                    candidate_id=f"quote:{source_id}:{index}",
                    vendor=self._safe(quote.get("vendor"), "Quoted Vendor"),
                    vendor_type=self._classify_vendor(
                        vendor=self._safe(quote.get("vendor"), ""),
                        manufacturer=self._safe(line.manufacturer, ""),
                        override=vendor_type_overrides.get(
                            self._safe(quote.get("vendor"), "")
                        ),
                        record=None,
                    ),
                    acquisition_cost=self._float_or_none(quote.get("unit_cost")),
                    currency=self._safe(quote.get("currency"), "USD"),
                    effective_date=self._safe(quote.get("effective_date"), ""),
                    expiration_date=self._safe(quote.get("expiration_date"), ""),
                    import_date=self._safe(quote.get("import_date"), ""),
                    days_since_import=None,
                    source_file=self._safe(quote.get("source_file"), "project_quote"),
                    source_row=None,
                    price_sheet_id=self._safe(quote.get("price_sheet_id"), ""),
                    price_sheet_version_id=self._safe(
                        quote.get("price_sheet_version_id"), ""
                    ),
                    vendor_offering_id=self._safe(quote.get("vendor_offering_id"), ""),
                    price_record_id=self._safe(quote.get("price_record_id"), ""),
                    freshness=CostFreshness.FRESH,
                    rank=1,
                    reason="Project-specific quoted cost.",
                    availability=self._safe(quote.get("availability"), "quoted"),
                    confidence=0.99,
                    source_class="project_quote",
                    candidate_fingerprint=self._candidate_fingerprint(
                        source_class="project_quote",
                        vendor=self._safe(quote.get("vendor"), "Quoted Vendor"),
                        price_record_id=self._safe(quote.get("price_record_id"), ""),
                        effective_date=self._safe(quote.get("effective_date"), ""),
                        expiration_date=self._safe(quote.get("expiration_date"), ""),
                    ),
                    unit_of_measure=self._safe(
                        quote.get("unit_of_measure"), quantity_uom
                    ),
                    pack_quantity=self._int_or_none(quote.get("pack_quantity")),
                    minimum_order_quantity=self._int_or_none(
                        quote.get("minimum_order_quantity")
                    ),
                    purchase_multiple=self._int_or_none(quote.get("purchase_multiple")),
                )
            )

        preferred_vendor = self._preferred_vendor(
            source_id=source_id,
            product_key=product_key,
            manufacturer=self._safe(line.manufacturer, ""),
            policy=policy,
        )

        for row in quick_add_products:
            if self._safe(row.get("project_id"), "") != self._safe(project_id, ""):
                continue
            if self._safe(row.get("product"), "") != product_key:
                continue
            vendor = self._safe(row.get("vendor"), "Unknown Vendor")
            override = vendor_type_overrides.get(vendor)
            classification = self._classify_vendor(
                vendor=vendor,
                manufacturer=self._safe(line.manufacturer, ""),
                override=override,
                record={"vendor_type": row.get("vendor_type")},
            )
            rank = (
                2
                if preferred_vendor and vendor.lower() == preferred_vendor.lower()
                else 5
            )
            if (
                preferred_channel
                and self._safe(row.get("vendor_type"), "") == preferred_channel
            ):
                rank = min(rank, 3)
            candidates.append(
                CostCandidate(
                    candidate_id=f"quick_add:{source_id}:{len(candidates)+1}",
                    vendor=vendor,
                    vendor_type=classification,
                    acquisition_cost=self._float_or_none(row.get("cost")),
                    currency="USD",
                    effective_date=self._safe(row.get("created_at"), ""),
                    expiration_date="",
                    import_date=self._safe(row.get("created_at"), ""),
                    days_since_import=0,
                    source_file=self._safe(row.get("source"), "quick_add"),
                    source_row=None,
                    price_sheet_id="",
                    price_sheet_version_id="",
                    vendor_offering_id="",
                    price_record_id="",
                    freshness=CostFreshness.FRESH,
                    rank=rank,
                    reason="Quick Add project cost candidate.",
                    availability="in_stock",
                    confidence=0.88,
                    source_class="quick_add",
                    candidate_fingerprint=self._candidate_fingerprint(
                        source_class="quick_add",
                        vendor=vendor,
                        price_record_id="",
                        effective_date=self._safe(row.get("created_at"), ""),
                        expiration_date="",
                    ),
                    unit_of_measure=self._safe(
                        row.get("unit_of_measure"), quantity_uom
                    ),
                    pack_quantity=self._int_or_none(row.get("pack_quantity")),
                    minimum_order_quantity=self._int_or_none(
                        row.get("minimum_order_quantity")
                    ),
                    purchase_multiple=self._int_or_none(row.get("purchase_multiple")),
                )
            )

        for record_id, record in commercial.get("price_records", {}).items():
            if self._safe(record.get("product"), "") != product_key:
                continue
            if not bool(record.get("active", True)):
                continue
            version_id = self._safe(record.get("version_id"), "")
            version = dict(
                commercial.get("price_sheet_versions", {}).get(version_id) or {}
            )
            version_status = self._safe(version.get("status"), "finalized").lower()
            if version_status and version_status != "finalized":
                continue
            sheet_id = self._safe(version.get("price_sheet_id"), "")
            sheet = dict(commercial.get("price_sheets", {}).get(sheet_id) or {})
            vendor = self._safe(
                record.get("vendor"), self._safe(sheet.get("vendor"), "Unknown Vendor")
            )
            override = vendor_type_overrides.get(vendor)
            classification = self._classify_vendor(
                vendor=vendor,
                manufacturer=self._safe(line.manufacturer, ""),
                override=override,
                record=record,
            )
            freshness = self._freshness(
                record=record,
                product_key=product_key,
                freshness_rows=freshness_rows,
            )
            if (
                self._window_for_dates(
                    effective_date=self._safe(record.get("effective_date"), ""),
                    expiration_date=self._safe(record.get("expiration_date"), ""),
                )
                == "future"
            ):
                continue
            offering_id = self._offering_for_record(
                commercial=commercial, record=record
            )
            if not self._is_eligible(
                product_key=product_key,
                vendor=vendor,
                vendor_offering_id=offering_id,
                eligibility_state=eligibility_state,
            ):
                continue
            rank = self._rank(
                preferred_vendor=preferred_vendor,
                vendor=vendor,
                vendor_type=classification,
                freshness=freshness,
                availability=self._safe(record.get("availability"), "unknown"),
                preferred_channel=preferred_channel,
                vendor_channel=self._safe(record.get("vendor_type"), ""),
            )
            reason = self._reason(
                preferred_vendor=preferred_vendor,
                vendor=vendor,
                vendor_type=classification,
                freshness=freshness,
                preferred_channel=preferred_channel,
                vendor_channel=self._safe(record.get("vendor_type"), ""),
            )
            source_file = self._safe(version.get("source_filename"), "")
            source_row = record.get("source_row")
            days_since = self._days_since_import(
                self._safe(version.get("import_date"), "")
            )
            pack_quantity = self._int_or_none(record.get("pack_quantity"))
            minimum_order_quantity = self._int_or_none(
                record.get("minimum_order_quantity")
            )
            purchase_multiple = self._int_or_none(record.get("purchase_multiple"))
            normalized_unit_cost, purchasing_quantity = self._normalized_cost_quantity(
                raw_unit_cost=self._float_or_none(record.get("cost")),
                quantity=quantity,
                pack_quantity=pack_quantity,
                minimum_order_quantity=minimum_order_quantity,
                purchase_multiple=purchase_multiple,
            )

            candidates.append(
                CostCandidate(
                    candidate_id=f"record:{record_id}",
                    vendor=vendor,
                    vendor_type=classification,
                    acquisition_cost=self._float_or_none(record.get("cost")),
                    currency=self._safe(record.get("currency"), "USD"),
                    effective_date=self._safe(record.get("effective_date"), ""),
                    expiration_date=self._safe(record.get("expiration_date"), ""),
                    import_date=self._safe(version.get("import_date"), ""),
                    days_since_import=days_since,
                    source_file=source_file,
                    source_row=(
                        int(source_row) if isinstance(source_row, int) else None
                    ),
                    price_sheet_id=sheet_id,
                    price_sheet_version_id=version_id,
                    vendor_offering_id=offering_id,
                    price_record_id=record_id,
                    freshness=freshness,
                    rank=rank,
                    reason=reason,
                    availability=self._safe(record.get("availability"), "unknown"),
                    confidence=float(record.get("confidence", 0.8) or 0.8),
                    source_class=self._source_class_for_rank(rank),
                    candidate_fingerprint=self._candidate_fingerprint(
                        source_class=self._source_class_for_rank(rank),
                        vendor=vendor,
                        price_record_id=record_id,
                        effective_date=self._safe(record.get("effective_date"), ""),
                        expiration_date=self._safe(record.get("expiration_date"), ""),
                    ),
                    unit_of_measure=self._safe(
                        record.get("unit_of_measure"), quantity_uom
                    ),
                    pack_quantity=pack_quantity,
                    minimum_order_quantity=minimum_order_quantity,
                    purchase_multiple=purchase_multiple,
                    normalized_unit_cost=normalized_unit_cost,
                    purchasing_quantity=purchasing_quantity,
                )
            )

        allowance = allowances.get(source_id)
        if allowance is not None:
            candidates.append(
                CostCandidate(
                    candidate_id=f"allowance:{source_id}",
                    vendor="Allowance",
                    vendor_type=VendorClassification.OTHER,
                    acquisition_cost=float(allowance),
                    currency="USD",
                    effective_date="",
                    expiration_date="",
                    import_date="",
                    days_since_import=None,
                    source_file="allowance_map",
                    source_row=None,
                    price_sheet_id="",
                    price_sheet_version_id="",
                    vendor_offering_id="",
                    price_record_id="",
                    freshness=CostFreshness.UNKNOWN,
                    rank=12,
                    reason="Allowance fallback",
                    availability="allowance",
                    confidence=0.55,
                    source_class="allowance",
                    candidate_fingerprint=self._candidate_fingerprint(
                        source_class="allowance",
                        vendor="Allowance",
                        price_record_id="",
                        effective_date="",
                        expiration_date="",
                    ),
                    unit_of_measure=quantity_uom,
                    normalized_unit_cost=float(allowance),
                    purchasing_quantity=quantity,
                )
            )

        return candidates

    def _allowance_line(
        self,
        *,
        line: Any,
        source_id: str,
        resolved_product_id: str | None,
        allowance: float,
    ) -> CostLine:
        unit_cost = round(float(allowance), 4)
        quantity = float(line.quantity)
        return CostLine(
            cost_line_id=f"cost-line:{line.line_id}",
            estimate_line_id=line.line_id,
            equipment_object_id=source_id,
            resolved_product_id=resolved_product_id,
            vendor_offering_id=None,
            price_record_id=None,
            price_sheet_version_id=None,
            vendor="Allowance",
            vendor_type=VendorClassification.OTHER,
            quantity=quantity,
            unit_cost=unit_cost,
            extended_cost=self._decimal_mul(unit_cost, quantity),
            currency="USD",
            status=CostStatus.ALLOWANCE,
            freshness=CostFreshness.UNKNOWN,
            import_date="",
            effective_date="",
            expiration_date="",
            days_since_import=None,
            source_file="allowance_map",
            source_row=None,
            warnings=[
                "Allowance used because deterministic current cost is unavailable."
            ],
            confidence=CostConfidence(
                score=0.55,
                rationale=[
                    "Allowance placeholder used.",
                    "Replace with current vendor or quote cost when available.",
                ],
            ),
            selection=CostSelection(
                selected_candidate_id=None,
                method="allowance",
                reason="Allowance fallback",
                candidates=[],
                decision_trace=["No current deterministic cost candidate."],
            ),
            supporting_evidence=["Allowance entry from project configuration."],
        )

    def _missing_line(
        self,
        *,
        line: Any,
        source_id: str,
        resolved_product_id: str | None,
        reason: str,
        candidates: list[CostCandidate] | None = None,
    ) -> CostLine:
        return CostLine(
            cost_line_id=f"cost-line:{line.line_id}",
            estimate_line_id=line.line_id,
            equipment_object_id=source_id,
            resolved_product_id=resolved_product_id,
            vendor_offering_id=None,
            price_record_id=None,
            price_sheet_version_id=None,
            vendor=None,
            vendor_type=None,
            quantity=float(line.quantity),
            unit_cost=None,
            extended_cost=0.0,
            currency="USD",
            status=CostStatus.MISSING,
            freshness=CostFreshness.MISSING,
            import_date="",
            effective_date="",
            expiration_date="",
            days_since_import=None,
            source_file="",
            source_row=None,
            warnings=[reason],
            confidence=CostConfidence(score=0.2, rationale=[reason]),
            selection=CostSelection(
                selected_candidate_id=None,
                method="none",
                reason=reason,
                candidates=candidates or [],
                decision_trace=["No deterministic cost candidate selected."],
            ),
            supporting_evidence=[],
        )

    def _status_for_candidate(self, candidate: CostCandidate) -> CostStatus:
        if candidate.source_class == "manual_override":
            return CostStatus.VERIFIED
        if candidate.candidate_id.startswith("quote:"):
            return CostStatus.QUOTED
        if candidate.candidate_id.startswith("allowance:"):
            return CostStatus.ALLOWANCE
        if candidate.availability.lower() in {"unavailable", "out_of_stock"}:
            return CostStatus.UNAVAILABLE
        if candidate.freshness is CostFreshness.EXPIRED:
            return CostStatus.EXPIRED
        if candidate.freshness is CostFreshness.STALE:
            return CostStatus.STALE
        if candidate.rank == 2:
            return CostStatus.VERIFIED
        if candidate.rank in {3, 4, 5, 6, 7, 8, 9, 10}:
            return CostStatus.CURRENT
        if candidate.rank == 11:
            return CostStatus.HISTORICAL
        if candidate.rank == 12:
            return CostStatus.ALLOWANCE
        return CostStatus.MISSING

    def _rank(
        self,
        *,
        preferred_vendor: str,
        vendor: str,
        vendor_type: VendorClassification,
        freshness: CostFreshness,
        availability: str,
        preferred_channel: str,
        vendor_channel: str,
    ) -> int:
        if availability.lower() in {"unavailable", "out_of_stock"}:
            return 13
        if freshness is CostFreshness.EXPIRED:
            return 13
        if (
            preferred_vendor
            and vendor.lower() == preferred_vendor.lower()
            and freshness
            in {
                CostFreshness.FRESH,
                CostFreshness.REVIEW_RECOMMENDED,
            }
        ):
            return 2
        if preferred_channel and preferred_channel == self._safe(vendor_channel, ""):
            return 3
        if vendor_type is VendorClassification.MANUFACTURER_DIRECT and freshness in {
            CostFreshness.FRESH,
            CostFreshness.REVIEW_RECOMMENDED,
        }:
            return 4
        if (
            vendor_type is VendorClassification.AUTHORIZED_DISTRIBUTOR
            and freshness
            in {
                CostFreshness.FRESH,
                CostFreshness.REVIEW_RECOMMENDED,
            }
        ):
            return 5
        if vendor_type is VendorClassification.REGIONAL_DISTRIBUTOR and freshness in {
            CostFreshness.FRESH,
            CostFreshness.REVIEW_RECOMMENDED,
        }:
            return 6
        if vendor_type is VendorClassification.BUYING_GROUP and freshness in {
            CostFreshness.FRESH,
            CostFreshness.REVIEW_RECOMMENDED,
        }:
            return 8
        if vendor_type is VendorClassification.MARKETPLACE and freshness in {
            CostFreshness.FRESH,
            CostFreshness.REVIEW_RECOMMENDED,
        }:
            return 9
        if freshness in {CostFreshness.FRESH, CostFreshness.REVIEW_RECOMMENDED}:
            return 10
        return 11

    def _reason(
        self,
        *,
        preferred_vendor: str,
        vendor: str,
        vendor_type: VendorClassification,
        freshness: CostFreshness,
        preferred_channel: str,
        vendor_channel: str,
    ) -> str:
        if (
            preferred_vendor
            and vendor.lower() == preferred_vendor.lower()
            and freshness
            in {
                CostFreshness.FRESH,
                CostFreshness.REVIEW_RECOMMENDED,
            }
        ):
            return "Preferred vendor current cost."
        if preferred_channel and preferred_channel == self._safe(vendor_channel, ""):
            return "Preferred purchasing channel current cost."
        if vendor_type is VendorClassification.MANUFACTURER_DIRECT and freshness in {
            CostFreshness.FRESH,
            CostFreshness.REVIEW_RECOMMENDED,
        }:
            return "Manufacturer direct current cost."
        if (
            vendor_type is VendorClassification.AUTHORIZED_DISTRIBUTOR
            and freshness
            in {
                CostFreshness.FRESH,
                CostFreshness.REVIEW_RECOMMENDED,
            }
        ):
            return "Authorized distributor current cost."
        if freshness in {CostFreshness.FRESH, CostFreshness.REVIEW_RECOMMENDED}:
            return "Other current vendor cost."
        return "Historical current-equivalent cost fallback."

    def _source_class_for_rank(self, rank: int) -> str:
        mapping = {
            2: "preferred_vendor",
            3: "preferred_channel",
            4: "manufacturer_direct",
            5: "authorized_distributor",
            6: "regional_distributor",
            7: "dealer_reseller",
            8: "buying_group",
            9: "marketplace",
            10: "other_vendor",
            11: "historical",
            12: "allowance",
        }
        return mapping.get(rank, "commercial_record")

    @staticmethod
    def _candidate_fingerprint(
        *,
        source_class: str,
        vendor: str,
        price_record_id: str,
        effective_date: str,
        expiration_date: str,
    ) -> str:
        digest = hashlib.sha1(
            f"{source_class}|{vendor}|{price_record_id}|{effective_date}|{expiration_date}".encode(
                "utf-8"
            )
        ).hexdigest()[:20]
        return f"candidate:{digest}"

    def _window_for_dates(self, *, effective_date: str, expiration_date: str) -> str:
        start = self._date_from_text(effective_date)
        end = self._date_from_text(expiration_date)
        if start is not None and start > self.as_of:
            return "future"
        if end is not None and end < self.as_of:
            return "historical"
        return "current"

    def _has_future_records(
        self, *, product_key: str, commercial: dict[str, Any]
    ) -> bool:
        for record in commercial.get("price_records", {}).values():
            if self._safe(record.get("product"), "") != product_key:
                continue
            window = self._window_for_dates(
                effective_date=self._safe(record.get("effective_date"), ""),
                expiration_date=self._safe(record.get("expiration_date"), ""),
            )
            if window == "future":
                return True
        return False

    def _is_eligible(
        self,
        *,
        product_key: str,
        vendor: str,
        vendor_offering_id: str,
        eligibility_state: dict[str, Any],
    ) -> bool:
        inactive_products = {
            self._safe(item, "")
            for item in list(eligibility_state.get("inactive_products") or [])
        }
        inactive_vendors = {
            self._safe(item, "")
            for item in list(eligibility_state.get("inactive_vendors") or [])
        }
        inactive_offerings = {
            self._safe(item, "")
            for item in list(eligibility_state.get("inactive_vendor_offerings") or [])
        }
        if product_key in inactive_products:
            return False
        if vendor in inactive_vendors:
            return False
        if vendor_offering_id and vendor_offering_id in inactive_offerings:
            return False
        return True

    def _normalized_cost_quantity(
        self,
        *,
        raw_unit_cost: float | None,
        quantity: float,
        pack_quantity: int | None,
        minimum_order_quantity: int | None,
        purchase_multiple: int | None,
    ) -> tuple[float | None, float]:
        if raw_unit_cost is None:
            return None, float(quantity)
        pack = max(1, int(pack_quantity or 1))
        moq = max(1, int(minimum_order_quantity or 1))
        multiple = max(1, int(purchase_multiple or 1))
        unit = Decimal(str(raw_unit_cost))
        normalized_unit_cost = (unit / Decimal(pack)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        requested = Decimal(str(quantity))
        min_required = max(requested, Decimal(moq))
        multiple_dec = Decimal(multiple)
        purchase_units = int(
            (min_required / multiple_dec).to_integral_value(rounding=ROUND_CEILING)
        )
        purchase_qty = (Decimal(purchase_units) * multiple_dec).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        return float(normalized_unit_cost), float(purchase_qty)

    def _override_active(self, override: dict[str, Any]) -> bool:
        if not override:
            return False
        if not bool(override.get("active", True)):
            return False
        expires_at = self._safe(override.get("expires_at"), "")
        expires = self._date_from_text(expires_at)
        if expires is not None and expires < self.as_of:
            return False
        return self._float_or_none(override.get("unit_cost")) is not None

    def _freshness(
        self,
        *,
        record: dict[str, Any],
        product_key: str,
        freshness_rows: dict[str, dict[str, Any]],
    ) -> CostFreshness:
        expiration = self._date_from_text(self._safe(record.get("expiration_date"), ""))
        if expiration is not None and expiration < self.as_of:
            return CostFreshness.EXPIRED

        mapped = self._safe(
            (freshness_rows.get(product_key) or {}).get("current_status"), ""
        )
        if mapped == KnowledgeFreshnessStatus.FRESH.value:
            return CostFreshness.FRESH
        if mapped == KnowledgeFreshnessStatus.REVIEW_RECOMMENDED.value:
            return CostFreshness.REVIEW_RECOMMENDED
        if mapped == KnowledgeFreshnessStatus.STALE.value:
            return CostFreshness.STALE
        if mapped == KnowledgeFreshnessStatus.MISSING.value:
            return CostFreshness.MISSING
        return CostFreshness.UNKNOWN

    def _classify_vendor(
        self,
        *,
        vendor: str,
        manufacturer: str,
        override: VendorClassification | None,
        record: dict[str, Any] | None,
    ) -> VendorClassification:
        if override is not None:
            return override
        if record is not None:
            raw = self._safe(record.get("vendor_type"), "")
            if raw:
                try:
                    return VendorClassification(raw)
                except ValueError:
                    pass
        vendor_norm = vendor.lower()
        if vendor_norm == manufacturer.lower() or "manufacturer" in vendor_norm:
            return VendorClassification.MANUFACTURER_DIRECT
        if any(
            token in vendor_norm for token in ["authorized", "dist", "distribution"]
        ):
            return VendorClassification.AUTHORIZED_DISTRIBUTOR
        if "regional" in vendor_norm:
            return VendorClassification.REGIONAL_DISTRIBUTOR
        if "buying group" in vendor_norm:
            return VendorClassification.BUYING_GROUP
        if any(token in vendor_norm for token in ["market", "amazon", "ebay"]):
            return VendorClassification.MARKETPLACE
        if "integrator" in vendor_norm:
            return VendorClassification.INTEGRATOR
        return VendorClassification.OTHER

    def _confidence(
        self,
        *,
        status: CostStatus,
        selected: CostCandidate,
        resolution_confidence: float,
        candidate_count: int,
        conflict_count: int,
    ) -> tuple[float, list[str]]:
        freshness_map = {
            CostFreshness.FRESH: 1.0,
            CostFreshness.REVIEW_RECOMMENDED: 0.85,
            CostFreshness.STALE: 0.55,
            CostFreshness.EXPIRED: 0.35,
            CostFreshness.MISSING: 0.2,
            CostFreshness.UNKNOWN: 0.7,
        }
        freshness_score = freshness_map.get(selected.freshness, 0.6)

        completeness_fields = [
            selected.vendor,
            selected.currency,
            selected.effective_date,
            selected.source_file,
            selected.price_sheet_version_id,
        ]
        completeness_score = round(
            sum(1 for item in completeness_fields if self._safe(item, ""))
            / len(completeness_fields),
            4,
        )

        provenance_fields = [
            selected.price_sheet_id,
            selected.price_sheet_version_id,
            selected.price_record_id,
            selected.vendor_offering_id,
            selected.import_date,
            selected.candidate_fingerprint,
        ]
        provenance_score = round(
            sum(1 for item in provenance_fields if self._safe(item, ""))
            / len(provenance_fields),
            4,
        )

        conflict_penalty = 0.0
        if candidate_count > 1:
            conflict_penalty += 0.1
        if conflict_count > 1:
            conflict_penalty += 0.15
        if status in {CostStatus.HISTORICAL, CostStatus.STALE, CostStatus.EXPIRED}:
            conflict_penalty += 0.1
        if status in {CostStatus.UNAVAILABLE, CostStatus.MISSING}:
            conflict_penalty += 0.2
        conflict_score = round(max(0.0, 1.0 - conflict_penalty), 4)

        score = (
            0.35 * freshness_score
            + 0.25 * completeness_score
            + 0.20 * provenance_score
            + 0.20 * conflict_score
        )
        score = 0.85 * score + 0.15 * max(0.0, min(1.0, resolution_confidence))
        final = round(max(0.0, min(1.0, score)), 4)
        rationale = [
            f"freshness_score={round(freshness_score, 4)}",
            f"completeness_score={round(completeness_score, 4)}",
            f"provenance_score={round(provenance_score, 4)}",
            f"conflict_score={round(conflict_score, 4)}",
            f"resolution_confidence={round(resolution_confidence, 4)}",
            f"confidence_final={final}",
        ]
        return final, rationale

    def _summary(self, lines: list[CostLine]) -> CostSummary:
        equipment_cost = round(sum(item.extended_cost for item in lines), 2)
        allowance_cost = round(
            sum(
                item.extended_cost
                for item in lines
                if item.status is CostStatus.ALLOWANCE
            ),
            2,
        )
        known_cost = round(
            sum(
                item.extended_cost
                for item in lines
                if item.status not in {CostStatus.MISSING, CostStatus.ALLOWANCE}
            ),
            2,
        )
        unknown_cost = round(
            sum(
                item.extended_cost
                for item in lines
                if item.status is CostStatus.MISSING
            ),
            2,
        )
        total = max(equipment_cost, 0.0)
        known_pct = round((known_cost / total) * 100, 4) if total else 0.0
        unknown_pct = round((unknown_cost / total) * 100, 4) if total else 0.0
        without_cost = sum(1 for item in lines if item.status is CostStatus.MISSING)

        freshness_counts = {
            CostFreshness.FRESH.value: 0,
            CostFreshness.REVIEW_RECOMMENDED.value: 0,
            CostFreshness.STALE.value: 0,
            CostFreshness.EXPIRED.value: 0,
            CostFreshness.MISSING.value: 0,
            CostFreshness.UNKNOWN.value: 0,
        }
        for item in lines:
            freshness_counts[item.freshness.value] += 1

        dominant = (
            max(freshness_counts, key=lambda item: freshness_counts[item])
            if lines
            else "unknown"
        )
        confidence = (
            round(
                sum(
                    (item.confidence.score if item.confidence else 0.0)
                    for item in lines
                )
                / len(lines),
                4,
            )
            if lines
            else 0.0
        )

        return CostSummary(
            project_summary=ProjectCostSummary(
                equipment_cost=equipment_cost,
                accessory_cost=0.0,
                software_cost=0.0,
                freight_placeholder=0.0,
                travel_placeholder=0.0,
                labor_placeholder=0.0,
                project_services_placeholder=0.0,
                subcontractor_placeholder=0.0,
                allowance_cost=allowance_cost,
                known_cost=known_cost,
                unknown_cost=unknown_cost,
                known_cost_percent=known_pct,
                unknown_cost_percent=unknown_pct,
                products_without_cost=without_cost,
                pricing_freshness=dominant,
                commercial_confidence=confidence,
            )
        )

    def _coverage(self, lines: list[CostLine]) -> CommercialCoverage:
        resolved = len(lines)
        current = sum(
            1
            for item in lines
            if item.status
            in {CostStatus.CURRENT, CostStatus.VERIFIED, CostStatus.QUOTED}
        )
        historical = sum(1 for item in lines if item.status is CostStatus.HISTORICAL)
        allowances = sum(1 for item in lines if item.status is CostStatus.ALLOWANCE)
        missing = sum(1 for item in lines if item.status is CostStatus.MISSING)
        stale = sum(
            1 for item in lines if item.status in {CostStatus.STALE, CostStatus.EXPIRED}
        )
        coverage = (
            round(((resolved - missing) / resolved) * 100, 4) if resolved else 0.0
        )
        confidence = (
            round(
                sum(
                    (item.confidence.score if item.confidence else 0.0)
                    for item in lines
                )
                / resolved,
                4,
            )
            if resolved
            else 0.0
        )
        return CommercialCoverage(
            resolved_products=resolved,
            products_with_current_cost=current,
            products_using_historical_cost=historical,
            products_using_allowances=allowances,
            products_missing_cost=missing,
            products_with_stale_cost=stale,
            coverage_percent=coverage,
            material_cost_confidence=confidence,
        )

    def _run_id(
        self,
        *,
        estimate: Estimate,
        resolutions: list[ProductResolution],
        commercial: dict[str, Any],
        policy: dict[str, Any],
        quotes: list[dict[str, Any]],
        allowances: dict[str, float],
        quick_add: list[dict[str, Any]],
    ) -> str:
        payload = {
            "estimate": [item.to_dict() for item in estimate.all_lines()],
            "resolutions": [item.to_dict() for item in resolutions],
            "commercial": commercial,
            "policy": policy,
            "quotes": quotes,
            "allowances": allowances,
            "quick_add": quick_add,
            "as_of": self.as_of.isoformat(),
            "policy_version": self.POLICY_VERSION,
        }
        digest = hashlib.sha1(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        return f"cost-run:{digest}"

    def _apply_request_restrictions(
        self,
        *,
        candidates: list[CostCandidate],
        request: CostSelectionRequest,
    ) -> tuple[list[CostCandidate], list[CostSelectionDiagnostic]]:
        diagnostics: list[CostSelectionDiagnostic] = []
        filtered = list(candidates)

        if request.currency:
            by_currency = [
                item
                for item in filtered
                if item.currency.upper() == request.currency.upper()
            ]
            if by_currency:
                filtered = by_currency
            else:
                diagnostics.append(
                    CostSelectionDiagnostic(
                        code="unsupported_currency",
                        severity="error",
                        message=f"No candidate priced in requested currency {request.currency}.",
                    )
                )
                filtered = []

        if request.price_sheet_id:
            by_sheet = [
                item
                for item in filtered
                if item.price_sheet_id == request.price_sheet_id
            ]
            if by_sheet:
                filtered = by_sheet

        if request.preferred_vendor_offering_id:
            by_offering = [
                item
                for item in filtered
                if item.vendor_offering_id == request.preferred_vendor_offering_id
            ]
            if by_offering:
                filtered = by_offering

        if request.manual_price_record_id:
            by_manual = [
                item
                for item in filtered
                if item.price_record_id == request.manual_price_record_id
            ]
            if by_manual:
                filtered = by_manual
            else:
                diagnostics.append(
                    CostSelectionDiagnostic(
                        code="manual_selection_invalid",
                        severity="error",
                        message="Manual price record was requested but did not match an eligible candidate.",
                    )
                )

        if request.permitted_purchasing_channels:
            channel_set = {
                self._safe(item, "")
                for item in list(request.permitted_purchasing_channels)
                if self._safe(item, "")
            }
            by_channel = [
                item
                for item in filtered
                if self._safe(item.vendor_type.value, "") in channel_set
            ]
            if by_channel:
                filtered = by_channel

        if not filtered and candidates:
            windows = {
                self._window_for_dates(
                    effective_date=item.effective_date,
                    expiration_date=item.expiration_date,
                )
                for item in candidates
            }
            if windows == {"future"}:
                diagnostics.append(
                    CostSelectionDiagnostic(
                        code="future_cost_only",
                        severity="warning",
                        message="Only future-effective costs are available for the as-of date.",
                    )
                )
            elif windows == {"historical"}:
                diagnostics.append(
                    CostSelectionDiagnostic(
                        code="expired_cost_only",
                        severity="warning",
                        message="Only historical/expired costs are available for the as-of date.",
                    )
                )

        return filtered, diagnostics

    @staticmethod
    def _decimal_mul(value: float | None, qty: float) -> float:
        if value is None:
            return 0.0
        try:
            unit = Decimal(str(value))
            quantity = Decimal(str(qty))
            total = (unit * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return float(total)
        except InvalidOperation, ValueError:
            return 0.0

    @staticmethod
    def _offering_for_record(commercial: dict[str, Any], record: dict[str, Any]) -> str:
        product = str(record.get("product") or "")
        vendor = str(record.get("vendor") or "")
        sku = str(record.get("vendor_sku") or "")
        for offering_id, offering in commercial.get("vendor_offerings", {}).items():
            if (
                str(offering.get("product") or "") == product
                and str(offering.get("vendor") or "") == vendor
                and str(offering.get("vendor_sku") or "") == sku
            ):
                return str(offering_id)
        return ""

    def _preferred_vendor(
        self,
        *,
        source_id: str,
        product_key: str,
        manufacturer: str,
        policy: dict[str, Any],
    ) -> str:
        by_project = dict(policy.get("project", {}))
        if source_id in by_project:
            return self._safe(by_project.get(source_id), "")

        by_product = dict(policy.get("product", {}))
        if product_key in by_product:
            return self._safe(by_product.get(product_key), "")

        by_manufacturer = dict(policy.get("manufacturer", {}))
        if manufacturer in by_manufacturer:
            return self._safe(by_manufacturer.get(manufacturer), "")

        return self._safe(policy.get("organization"), "")

    @staticmethod
    def _product_key(
        *, canonical_product_id: str | None, manufacturer: str, model: str
    ) -> str:
        if canonical_product_id:
            return canonical_product_id
        return f"{manufacturer}::{model}"

    def _days_since_import(self, import_date: str) -> int | None:
        value = self._date_from_text(import_date)
        if value is None:
            return None
        delta = (self.as_of - value).days
        return max(delta, 0)

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return round(float(value), 4)
        text = str(value).strip().replace("$", "").replace(",", "")
        if not text:
            return None
        try:
            return round(float(text), 4)
        except ValueError:
            return None

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value.is_integer():
                return int(value)
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    @staticmethod
    def _safe(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _date_from_text(value: str) -> date | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            for pattern in ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"]:
                try:
                    return datetime.strptime(value, pattern).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()

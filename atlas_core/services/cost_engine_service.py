"""Deterministic acquisition cost engine for Atlas Core."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
import hashlib
import io
import json
from typing import Any

from atlas_core.domain.commercial_knowledge import KnowledgeFreshnessStatus
from atlas_core.domain.cost_engine import (
    CommercialCoverage,
    CostCandidate,
    CostConfidence,
    CostFreshness,
    CostLine,
    CostResult,
    CostSelection,
    CostStatus,
    CostSummary,
    ProjectCostSummary,
    VendorClassification,
)
from atlas_core.domain.deterministic_estimate import Estimate, ProductResolutionStatus
from atlas_core.domain.product_resolution import ProductResolution
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService


class DeterministicCostEngine:
    POLICY_VERSION = "atlas-cost-policy:v1"

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
    ) -> CostLine:
        source_id = self._safe(line.source_object, "")
        quantity = float(line.quantity)

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
        )
        candidates.sort(
            key=lambda item: (
                item.rank,
                float(item.acquisition_cost or 0.0),
                item.vendor.lower(),
                item.candidate_id,
            )
        )
        selected = candidates[0] if candidates else None

        if selected is None:
            return self._missing_line(
                line=line,
                source_id=source_id,
                resolved_product_id=resolved_product_id,
                reason="No deterministic cost candidate found.",
                candidates=candidates,
            )

        status = self._status_for_candidate(selected)
        unit_cost = selected.acquisition_cost
        extended = round((unit_cost or 0.0) * quantity, 2)

        confidence_score, confidence_messages = self._confidence(
            status=status,
            selected=selected,
            resolution_confidence=resolution_confidence,
        )

        selection = CostSelection(
            selected_candidate_id=selected.candidate_id,
            method="deterministic",
            reason=selected.reason,
            candidates=candidates,
            decision_trace=[
                "Evaluated quote, preferred vendor, vendor type hierarchy, current/historical availability.",
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
            warnings=warnings,
            confidence=CostConfidence(
                score=confidence_score, rationale=confidence_messages
            ),
            selection=selection,
            supporting_evidence=[
                f"Vendor={selected.vendor}",
                f"VendorType={selected.vendor_type.value}",
                f"PriceSheetVersion={selected.price_sheet_version_id or 'n/a'}",
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
    ) -> list[CostCandidate]:
        candidates: list[CostCandidate] = []

        for index, quote in enumerate(project_quotes, start=1):
            if self._safe(quote.get("project_id"), "") != self._safe(project_id, ""):
                continue
            if self._safe(quote.get("product"), "") != product_key:
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
                )
            )

        for record_id, record in commercial.get("price_records", {}).items():
            if self._safe(record.get("product"), "") != product_key:
                continue
            version_id = self._safe(record.get("version_id"), "")
            version = dict(
                commercial.get("price_sheet_versions", {}).get(version_id) or {}
            )
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
            rank = self._rank(
                preferred_vendor=preferred_vendor,
                vendor=vendor,
                vendor_type=classification,
                freshness=freshness,
                availability=self._safe(record.get("availability"), "unknown"),
            )
            reason = self._reason(
                preferred_vendor=preferred_vendor,
                vendor=vendor,
                vendor_type=classification,
                freshness=freshness,
            )
            offering_id = self._offering_for_record(
                commercial=commercial, record=record
            )
            source_file = self._safe(version.get("source_filename"), "")
            source_row = record.get("source_row")
            days_since = self._days_since_import(
                self._safe(version.get("import_date"), "")
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
                    rank=7,
                    reason="Allowance fallback",
                    availability="allowance",
                    confidence=0.55,
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
            extended_cost=round(unit_cost * quantity, 2),
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
        if candidate.rank in {3, 4, 5}:
            return CostStatus.CURRENT
        if candidate.rank == 6:
            return CostStatus.HISTORICAL
        if candidate.rank == 7:
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
    ) -> int:
        if availability.lower() in {"unavailable", "out_of_stock"}:
            return 8
        if freshness is CostFreshness.EXPIRED:
            return 8
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
        if vendor_type is VendorClassification.MANUFACTURER_DIRECT and freshness in {
            CostFreshness.FRESH,
            CostFreshness.REVIEW_RECOMMENDED,
        }:
            return 3
        if (
            vendor_type is VendorClassification.AUTHORIZED_DISTRIBUTOR
            and freshness
            in {
                CostFreshness.FRESH,
                CostFreshness.REVIEW_RECOMMENDED,
            }
        ):
            return 4
        if freshness in {CostFreshness.FRESH, CostFreshness.REVIEW_RECOMMENDED}:
            return 5
        return 6

    def _reason(
        self,
        *,
        preferred_vendor: str,
        vendor: str,
        vendor_type: VendorClassification,
        freshness: CostFreshness,
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
    ) -> tuple[float, list[str]]:
        score = 0.6 + (resolution_confidence - 0.5) * 0.3
        rationale = [
            f"Resolution confidence contribution: {round(resolution_confidence, 4)}.",
            f"Vendor classification: {selected.vendor_type.value}.",
        ]

        if status is CostStatus.QUOTED:
            score += 0.28
        elif status is CostStatus.VERIFIED:
            score += 0.2
        elif status is CostStatus.CURRENT:
            score += 0.14
        elif status is CostStatus.HISTORICAL:
            score -= 0.1
        elif status is CostStatus.STALE:
            score -= 0.22
        elif status is CostStatus.EXPIRED:
            score -= 0.32
        elif status is CostStatus.UNAVAILABLE:
            score -= 0.4
        elif status is CostStatus.ALLOWANCE:
            score -= 0.18
        elif status is CostStatus.MISSING:
            score -= 0.5

        if selected.currency.upper() != "USD":
            score -= 0.05
            rationale.append("Currency mismatch with USD reduced confidence.")

        final = round(max(0.0, min(1.0, score)), 4)
        rationale.append(f"Final commercial confidence: {final}.")
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

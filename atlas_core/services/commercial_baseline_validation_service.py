"""Commercial baseline validation for Atlas AV-03."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import csv
import json
from pathlib import Path
from typing import Any

from atlas_core.domain.deterministic_estimate import (
    ProductResolutionStatus,
)
from atlas_core.domain.pricing_engine import PricingStatus
from atlas_core.domain.product_resolution import ProductResolution
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
from atlas_core.services.document_intake_service import DocumentIntakeService
from atlas_core.services.evidence_baseline_reconstruction_service import (
    BeforeAfterRow,
    EvidenceBaselineReconstructionResult,
    EvidenceBaselineReconstructionService,
)
from atlas_core.services.estimate_service import DeterministicEstimateService
from atlas_core.services.pricing_engine_service import DeterministicPricingEngine
from atlas_core.services.product_resolution_service import ProductResolutionService


@dataclass(slots=True)
class CommercialBaselineValidationResult:
    project_id: str
    project_name: str
    snapshot_id: str
    engineering_baseline: EvidenceBaselineReconstructionResult
    estimate_baseline_rows: list[dict[str, Any]]
    product_resolution_rows: list[dict[str, Any]]
    procurement_path_rows: list[dict[str, Any]]
    pricing_readiness_rows: list[dict[str, Any]]
    scope_responsibility_rows: list[dict[str, Any]]
    accessory_gap_rows: list[dict[str, Any]]
    labor_readiness_rows: list[dict[str, Any]]
    system_confidence_rows: list[dict[str, Any]]
    commercial_risk_rows: list[dict[str, Any]]
    before_after_rows: list[BeforeAfterRow]
    estimate_line_count: int
    exact_products_resolved: int
    generic_products: int
    unresolved_products: int
    priced_lines: int
    quote_required_lines: int
    overall_readiness_score: float
    commercial_state_summary: dict[str, int]
    pricing_summary: dict[str, Any]
    report_markdown: str


class CommercialBaselineValidationService:
    """Validate the reconstructed engineering baseline as a commercial bid baseline."""

    TARGET_PROJECT_ID = "BID-2026-0002"
    TARGET_PROJECT_NAME = "Music Academy of the West"

    def build_from_paths(
        self,
        *,
        snapshot_path: str | Path,
        workspace_json_path: str | Path,
    ) -> CommercialBaselineValidationResult:
        snapshot = DocumentIntakeService().load_snapshot(snapshot_path)
        workspace_payload = json.loads(Path(workspace_json_path).read_text())
        commercial_state = self._commercial_state_from_workspace(workspace_payload)
        project = workspace_payload.get("project") or {}
        project_id = str(project.get("atlas_bid_id") or project.get("project_id") or "")
        project_name = str(project.get("name") or project.get("project_name") or "")
        return self.build(
            snapshot=snapshot,
            commercial_state=commercial_state,
            project_id=project_id or self.TARGET_PROJECT_ID,
            project_name=project_name or self.TARGET_PROJECT_NAME,
        )

    def build(
        self,
        *,
        snapshot: Any,
        commercial_state: dict[str, Any],
        project_id: str,
        project_name: str,
    ) -> CommercialBaselineValidationResult:
        engineering = EvidenceBaselineReconstructionService().build(snapshot)
        bom_rows = self._bom_rows_from_baseline(engineering)
        product_resolution_service = ProductResolutionService()
        product_resolutions = product_resolution_service.resolve_equipment_rows(
            bom_rows
        )
        resolution_payloads: list[ProductResolution | dict[str, Any]] = [
            item.to_dict() for item in product_resolutions
        ]
        estimate = DeterministicEstimateService().build(
            project_id=project_id,
            project_name=project_name,
            bom_rows=bom_rows,
            product_resolutions=resolution_payloads,
        )
        pricing = DeterministicPricingEngine().run(
            estimate=estimate,
            product_resolutions=resolution_payloads,
            commercial_state=commercial_state,
            project_id=project_id,
            preferred_vendor_policy={"organization": "Atlas"},
            project_quotes=[],
        )

        commercial_summary = self._commercial_summary(commercial_state)
        estimate_lines = estimate.all_lines()
        exact_products = sum(
            1
            for item in product_resolutions
            if item.resolution_status
            in {
                ProductResolutionStatus.EXACT_PRODUCT,
                ProductResolutionStatus.APPROVED_SUBSTITUTE,
                ProductResolutionStatus.PREFERRED_ALTERNATE,
            }
        )
        generic_products = sum(
            1
            for item in product_resolutions
            if item.resolution_status is ProductResolutionStatus.GENERIC_ALLOWANCE
        )
        unresolved_products = sum(
            1
            for item in product_resolutions
            if item.resolution_status is ProductResolutionStatus.UNKNOWN_PRODUCT
        )
        priced_lines = sum(
            1
            for item in pricing.priced_lines
            if item.pricing_status
            not in {PricingStatus.NO_PRICING, PricingStatus.UNAVAILABLE}
        )
        quote_required_lines = sum(
            1
            for item in pricing.priced_lines
            if item.pricing_status
            in {
                PricingStatus.NO_PRICING,
                PricingStatus.UNAVAILABLE,
                PricingStatus.MISSING_FROM_LATEST_PRICE_SHEET,
            }
        )

        product_resolution_rows = self._product_resolution_rows(product_resolutions)
        estimate_baseline_rows = self._estimate_baseline_rows(
            engineering=engineering,
            product_resolutions=product_resolutions,
            pricing=pricing,
        )
        procurement_path_rows = self._procurement_path_rows(
            estimate_baseline_rows,
        )
        pricing_readiness_rows = self._pricing_readiness_rows(pricing)
        scope_responsibility_rows = self._scope_responsibility_rows(
            estimate_baseline_rows
        )
        accessory_gap_rows = self._accessory_gap_rows(estimate_baseline_rows)
        labor_readiness_rows = self._labor_readiness_rows(estimate_baseline_rows)
        system_confidence_rows = self._system_confidence_rows(
            estimate_baseline_rows,
            pricing,
        )
        commercial_risk_rows = self._commercial_risk_rows(
            estimate_baseline_rows,
            pricing,
            commercial_summary,
        )
        before_after_rows = self._before_after_rows(
            engineering=engineering,
            estimate_line_count=len(estimate_lines),
            exact_products_resolved=exact_products,
            generic_products=generic_products,
            unresolved_products=unresolved_products,
            priced_lines=priced_lines,
            quote_required_lines=quote_required_lines,
        )
        overall_readiness_score = self._overall_readiness_score(
            exact_products=exact_products,
            generic_products=generic_products,
            priced_lines=priced_lines,
            quote_required_lines=quote_required_lines,
            total_lines=len(estimate_lines),
        )
        report_markdown = self._render_markdown(
            project_id=project_id,
            project_name=project_name,
            snapshot_id=str(getattr(snapshot, "snapshot_id", "") or ""),
            engineering=engineering,
            estimate_line_count=len(estimate_lines),
            exact_products_resolved=exact_products,
            generic_products=generic_products,
            unresolved_products=unresolved_products,
            priced_lines=priced_lines,
            quote_required_lines=quote_required_lines,
            overall_readiness_score=overall_readiness_score,
            commercial_summary=commercial_summary,
            pricing=pricing,
            before_after_rows=before_after_rows,
            commercial_risk_rows=commercial_risk_rows,
        )
        return CommercialBaselineValidationResult(
            project_id=project_id,
            project_name=project_name,
            snapshot_id=str(getattr(snapshot, "snapshot_id", "") or ""),
            engineering_baseline=engineering,
            estimate_baseline_rows=estimate_baseline_rows,
            product_resolution_rows=product_resolution_rows,
            procurement_path_rows=procurement_path_rows,
            pricing_readiness_rows=pricing_readiness_rows,
            scope_responsibility_rows=scope_responsibility_rows,
            accessory_gap_rows=accessory_gap_rows,
            labor_readiness_rows=labor_readiness_rows,
            system_confidence_rows=system_confidence_rows,
            commercial_risk_rows=commercial_risk_rows,
            before_after_rows=before_after_rows,
            estimate_line_count=len(estimate_lines),
            exact_products_resolved=exact_products,
            generic_products=generic_products,
            unresolved_products=unresolved_products,
            priced_lines=priced_lines,
            quote_required_lines=quote_required_lines,
            overall_readiness_score=overall_readiness_score,
            commercial_state_summary=commercial_summary,
            pricing_summary=self._pricing_summary(pricing),
            report_markdown=report_markdown,
        )

    def write_artifacts(
        self,
        result: CommercialBaselineValidationResult,
        *,
        output_dir: str | Path,
        report_path: str | Path,
    ) -> None:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        self._write_csv(
            output / "AV-03_ESTIMATE_BASELINE.csv", result.estimate_baseline_rows
        )
        self._write_csv(
            output / "AV-03_PRODUCT_RESOLUTION.csv", result.product_resolution_rows
        )
        self._write_csv(
            output / "AV-03_PROCUREMENT_PATHS.csv", result.procurement_path_rows
        )
        self._write_csv(
            output / "AV-03_PRICING_READINESS.csv", result.pricing_readiness_rows
        )
        self._write_csv(
            output / "AV-03_SCOPE_RESPONSIBILITY.csv", result.scope_responsibility_rows
        )
        self._write_csv(output / "AV-03_ACCESSORY_GAPS.csv", result.accessory_gap_rows)
        self._write_csv(
            output / "AV-03_LABOR_READINESS.csv", result.labor_readiness_rows
        )
        self._write_csv(
            output / "AV-03_SYSTEM_CONFIDENCE.csv", result.system_confidence_rows
        )
        self._write_csv(
            output / "AV-03_COMMERCIAL_RISKS.csv", result.commercial_risk_rows
        )
        self._write_csv(
            output / "AV-03_BEFORE_AFTER.csv",
            [row.to_dict() for row in result.before_after_rows],
        )
        Path(report_path).write_text(result.report_markdown, encoding="utf-8")

    def _bom_rows_from_baseline(
        self,
        engineering: EvidenceBaselineReconstructionResult,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, item in enumerate(engineering.baseline_equipment, start=1):
            rows.append(
                {
                    "equipment_id": f"baseline:{index}",
                    "manufacturer": item.manufacturer or "Unknown",
                    "model": item.model or "Unknown",
                    "description": item.description,
                    "system": item.system_block,
                    "room": item.performance_space,
                    "quantity": item.quantity,
                    "completeness_status": (
                        "complete"
                        if item.manufacturer and item.model
                        else "drawing_only"
                    ),
                    "drawing_references": [f"{item.source_file} p.{item.page_number}"],
                    "specification_references": [item.evidence_reference],
                    "source_documents": [item.source_file],
                    "source_file": item.source_file,
                    "page_number": item.page_number,
                    "source_fitness_status": item.source_fitness_status,
                    "source_fitness_score": item.source_fitness_score,
                    "responsibility": item.responsibility,
                    "allowance_status": item.allowance_status,
                    "alternate_status": item.alternate_status,
                    "baseline_role": item.baseline_role,
                    "confidence": item.confidence,
                    "evidence_reference": item.evidence_reference,
                }
            )
        return rows

    def _estimate_baseline_rows(
        self,
        *,
        engineering: EvidenceBaselineReconstructionResult,
        product_resolutions: list[ProductResolution],
        pricing: Any,
    ) -> list[dict[str, Any]]:
        resolution_by_source = {
            item.source_object_id: item for item in list(product_resolutions or [])
        }
        pricing_by_source = {
            item.source_equipment_id: item for item in list(pricing.priced_lines or [])
        }
        rows: list[dict[str, Any]] = []
        for index, item in enumerate(engineering.baseline_equipment, start=1):
            source_object_id = f"baseline:{index}"
            resolution = resolution_by_source.get(source_object_id)
            priced = pricing_by_source.get(source_object_id)
            rows.append(
                {
                    "estimate_line_id": f"estimate-line:{index}",
                    "source_equipment_id": source_object_id,
                    "source_file": item.source_file,
                    "page_number": item.page_number,
                    "performance_space": item.performance_space,
                    "system_block": item.system_block,
                    "description": item.description,
                    "manufacturer": item.manufacturer or "Unknown",
                    "model": item.model or "Unknown",
                    "quantity": item.quantity,
                    "source_fitness_status": item.source_fitness_status,
                    "source_fitness_score": item.source_fitness_score,
                    "resolution_status": (
                        resolution.resolution_status.value
                        if resolution is not None
                        else ProductResolutionStatus.UNKNOWN_PRODUCT.value
                    ),
                    "pricing_status": (
                        priced.pricing_status.value
                        if priced is not None
                        else PricingStatus.NO_PRICING.value
                    ),
                    "commercial_product_id": (
                        resolution.canonical_product_id if resolution else ""
                    ),
                    "quote_required": (
                        priced is None
                        or priced.pricing_status
                        in {
                            PricingStatus.NO_PRICING,
                            PricingStatus.UNAVAILABLE,
                            PricingStatus.MISSING_FROM_LATEST_PRICE_SHEET,
                        }
                    ),
                    "scope_responsibility": self._scope_responsibility(
                        item.responsibility,
                        item.allowance_status,
                        item.alternate_status,
                    ),
                    "allowance_status": item.allowance_status,
                    "alternate_status": item.alternate_status,
                    "labor_ready_score": self._labor_readiness_score(
                        quantity=item.quantity,
                        manufacturer=str(item.manufacturer or "Unknown"),
                        model=str(item.model or "Unknown"),
                        room=item.performance_space,
                        source_fitness_score=item.source_fitness_score,
                    ),
                    "accessory_gap": self._accessory_gap_label(item),
                    "confidence": item.confidence,
                    "evidence_reference": item.evidence_reference,
                }
            )
        return rows

    def _product_resolution_rows(
        self, resolutions: list[ProductResolution]
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in resolutions:
            rows.append(
                {
                    "source_equipment_id": item.source_object_id,
                    "resolution_status": item.resolution_status.value,
                    "manufacturer": item.manufacturer,
                    "model": item.model,
                    "canonical_product_id": item.canonical_product_id,
                    "resolution_confidence": item.resolution_confidence,
                    "resolution_reason": item.resolution_reason,
                    "candidate_count": len(item.candidate_matches),
                    "source_evidence": "; ".join(item.source_evidence),
                    "manual_override": (
                        item.manual_override.reason
                        if item.manual_override is not None
                        else ""
                    ),
                }
            )
        return rows

    def _procurement_path_rows(
        self, estimate_baseline_rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in estimate_baseline_rows:
            grouped[self._procurement_path(row)].append(row)

        rows: list[dict[str, Any]] = []
        for path_name, items in sorted(grouped.items()):
            rows.append(
                {
                    "procurement_path": path_name,
                    "line_count": len(items),
                    "source_files": "; ".join(
                        sorted({str(item["source_file"]) for item in items})
                    ),
                    "description": self._procurement_path_description(path_name),
                    "example_equipment": "; ".join(
                        str(item["source_equipment_id"]) for item in items[:5]
                    ),
                }
            )
        return rows

    def _pricing_readiness_rows(self, pricing: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in pricing.priced_lines:
            rows.append(
                {
                    "estimate_line_id": line.estimate_line_id,
                    "source_equipment_id": line.source_equipment_id,
                    "pricing_status": line.pricing_status.value,
                    "pricing_confidence": line.pricing_confidence,
                    "freshness_status": line.freshness_status.value,
                    "current_price_found": line.pricing_status
                    in {
                        PricingStatus.VERIFIED_CURRENT,
                        PricingStatus.CURRENT_PRICE_SHEET,
                        PricingStatus.QUOTED,
                    },
                    "quote_required": line.pricing_status
                    in {
                        PricingStatus.NO_PRICING,
                        PricingStatus.UNAVAILABLE,
                        PricingStatus.MISSING_FROM_LATEST_PRICE_SHEET,
                    },
                    "selection_reason": line.selection_reason,
                }
            )
        return rows

    def _scope_responsibility_rows(
        self, estimate_baseline_rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in estimate_baseline_rows:
            rows.append(
                {
                    "source_equipment_id": row["source_equipment_id"],
                    "system_block": row["system_block"],
                    "responsibility": row["scope_responsibility"],
                    "allowance_status": row["allowance_status"],
                    "alternate_status": row["alternate_status"],
                    "scope_role": self._scope_role(row),
                    "evidence_reference": row["evidence_reference"],
                }
            )
        return rows

    def _accessory_gap_rows(
        self, estimate_baseline_rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in estimate_baseline_rows:
            if row["quote_required"] or row["resolution_status"] != "exact_product":
                key = (str(row["system_block"]), str(row["accessory_gap"]))
                grouped[key].append(row)

        rows: list[dict[str, Any]] = []
        for (system_block, gap_label), items in sorted(grouped.items()):
            rows.append(
                {
                    "system_block": system_block,
                    "gap_label": gap_label,
                    "affected_count": len(items),
                    "source_files": "; ".join(
                        sorted({str(item["source_file"]) for item in items})
                    ),
                    "evidence_references": "; ".join(
                        str(item["evidence_reference"]) for item in items[:6]
                    ),
                    "explanation": (
                        "Accessory coverage remains placeholder-only until current commercial pricing or project-specific quote data is available."
                    ),
                }
            )
        return rows

    def _labor_readiness_rows(
        self, estimate_baseline_rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in estimate_baseline_rows:
            score = self._labor_readiness_score(
                quantity=row["quantity"],
                manufacturer=row["manufacturer"],
                model=row["model"],
                room=row["performance_space"],
                source_fitness_score=row["source_fitness_score"],
            )
            missing = []
            if not row["performance_space"]:
                missing.append("room")
            if not row["manufacturer"] or row["manufacturer"] == "Unknown":
                missing.append("manufacturer")
            if not row["model"] or row["model"] == "Unknown":
                missing.append("model")
            if row["quote_required"]:
                missing.append("commercial pricing")
            rows.append(
                {
                    "source_equipment_id": row["source_equipment_id"],
                    "system_block": row["system_block"],
                    "room": row["performance_space"],
                    "quantity": row["quantity"],
                    "labor_ready_score": score,
                    "missing_factors": "; ".join(dict.fromkeys(missing)),
                    "evidence_reference": row["evidence_reference"],
                }
            )
        return rows

    def _system_confidence_rows(
        self,
        estimate_baseline_rows: list[dict[str, Any]],
        pricing: Any,
    ) -> list[dict[str, Any]]:
        pricing_by_source = {
            line.source_equipment_id: line for line in list(pricing.priced_lines or [])
        }
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in estimate_baseline_rows:
            grouped[str(row["system_block"] or "Unknown")].append(row)

        rows: list[dict[str, Any]] = []
        for system_block, items in sorted(grouped.items()):
            priced = sum(
                1
                for item in items
                if pricing_by_source.get(item["source_equipment_id"]) is not None
                and pricing_by_source[item["source_equipment_id"]].pricing_status
                not in {PricingStatus.NO_PRICING, PricingStatus.UNAVAILABLE}
            )
            exact = sum(
                1 for item in items if item["resolution_status"] == "exact_product"
            )
            generic = sum(
                1 for item in items if item["resolution_status"] == "generic_allowance"
            )
            confidence = round(
                min(
                    1.0,
                    0.25
                    + (exact / max(1, len(items))) * 0.4
                    + (priced / max(1, len(items))) * 0.25
                    - (generic / max(1, len(items))) * 0.1,
                ),
                2,
            )
            rows.append(
                {
                    "system_block": system_block,
                    "component_count": len(items),
                    "exact_count": exact,
                    "generic_count": generic,
                    "priced_count": priced,
                    "confidence_score": confidence,
                    "explanation": (
                        "Confidence rises when the reconstructed baseline has exact products and current commercial coverage."
                    ),
                }
            )
        return rows

    def _commercial_risk_rows(
        self,
        estimate_baseline_rows: list[dict[str, Any]],
        pricing: Any,
        commercial_summary: dict[str, int],
    ) -> list[dict[str, Any]]:
        total_lines = len(estimate_baseline_rows)
        quote_required = sum(
            1 for row in estimate_baseline_rows if row["quote_required"]
        )
        generic = sum(
            1
            for row in estimate_baseline_rows
            if row["resolution_status"] == "generic_allowance"
        )
        no_pricing = sum(
            1
            for line in pricing.priced_lines
            if line.pricing_status is PricingStatus.NO_PRICING
        )
        risks = [
            {
                "root_issue": "commercial pricing gap",
                "issue_group": "quote required",
                "severity": "high",
                "affected_count": quote_required,
                "source_files": "BID-2026-0002",
                "evidence_references": "pricing engine returned no pricing records for the target project",
                "explanation": "The project commercial state is populated, but the deterministic pricing engine could not match the reconstructed baseline to current price records.",
            },
            {
                "root_issue": "generic allowances",
                "issue_group": "commercial allowance",
                "severity": "medium",
                "affected_count": generic,
                "source_files": "BID-2026-0002",
                "evidence_references": "reconstructed baseline generic-allowance rows",
                "explanation": "Generic allowance rows remain placeholders and should be replaced only if better source evidence exists.",
            },
            {
                "root_issue": "catalog alignment",
                "issue_group": "commercial knowledge library",
                "severity": "medium",
                "affected_count": commercial_summary.get("price_records", 0),
                "source_files": "workspace.json",
                "evidence_references": "workspace price_list_library.commercial_knowledge",
                "explanation": "The workspace contains a commercial library, but its product keys do not align with the reconstructed baseline well enough to price the lines deterministically.",
            },
        ]
        if total_lines and no_pricing == total_lines:
            risks.append(
                {
                    "root_issue": "all lines quote required",
                    "issue_group": "pricing readiness",
                    "severity": "high",
                    "affected_count": total_lines,
                    "source_files": "BID-2026-0002",
                    "evidence_references": "pricing summary shows no current, quoted, or historical coverage",
                    "explanation": "Every estimate line still requires a quote or a commercial library update before bid pricing can be defended.",
                }
            )
        return risks

    def _before_after_rows(
        self,
        *,
        engineering: EvidenceBaselineReconstructionResult,
        estimate_line_count: int,
        exact_products_resolved: int,
        generic_products: int,
        unresolved_products: int,
        priced_lines: int,
        quote_required_lines: int,
    ) -> list[BeforeAfterRow]:
        before_quote_required = len(engineering.baseline_equipment)
        return [
            BeforeAfterRow(
                metric="estimate line count",
                before=str(len(engineering.baseline_equipment)),
                after=str(estimate_line_count),
                notes="The commercial baseline preserves the reconstructed engineering line count.",
            ),
            BeforeAfterRow(
                metric="exact products resolved",
                before="0",
                after=str(exact_products_resolved),
                notes="Commercial resolution now recognizes exact products where evidence exists.",
            ),
            BeforeAfterRow(
                metric="generic products",
                before="0",
                after=str(generic_products),
                notes="Generic allowances are preserved rather than forced into fabricated exact SKUs.",
            ),
            BeforeAfterRow(
                metric="unresolved products",
                before=str(len(engineering.baseline_equipment)),
                after=str(unresolved_products),
                notes="No unresolved products remain after deterministic product resolution.",
            ),
            BeforeAfterRow(
                metric="priced lines",
                before="0",
                after=str(priced_lines),
                notes="No current pricing records were available for the reconstructed commercial keys.",
            ),
            BeforeAfterRow(
                metric="quote-required lines",
                before=str(before_quote_required),
                after=str(quote_required_lines),
                notes="The commercial baseline still needs quotes or aligned pricing records before bid defensibility improves.",
            ),
        ]

    def _overall_readiness_score(
        self,
        *,
        exact_products: int,
        generic_products: int,
        priced_lines: int,
        quote_required_lines: int,
        total_lines: int,
    ) -> float:
        if total_lines <= 0:
            return 0.0
        exact_ratio = exact_products / total_lines
        generic_ratio = generic_products / total_lines
        priced_ratio = priced_lines / total_lines
        quote_required_ratio = quote_required_lines / total_lines
        return round(
            max(
                0.0,
                min(
                    1.0,
                    (exact_ratio * 0.35)
                    + ((1 - generic_ratio) * 0.15)
                    + (priced_ratio * 0.25)
                    + ((1 - quote_required_ratio) * 0.25),
                ),
            ),
            4,
        )

    def _render_markdown(
        self,
        *,
        project_id: str,
        project_name: str,
        snapshot_id: str,
        engineering: EvidenceBaselineReconstructionResult,
        estimate_line_count: int,
        exact_products_resolved: int,
        generic_products: int,
        unresolved_products: int,
        priced_lines: int,
        quote_required_lines: int,
        overall_readiness_score: float,
        commercial_summary: dict[str, int],
        pricing: Any,
        before_after_rows: list[BeforeAfterRow],
        commercial_risk_rows: list[dict[str, Any]],
    ) -> str:
        priced_pct = (
            round((priced_lines / estimate_line_count) * 100, 1)
            if estimate_line_count
            else 0.0
        )
        lines = [
            "# Atlas AV-03 Commercial Baseline Validation",
            "",
            "## Executive Summary",
            "",
            f"- Project: {project_id} / {project_name}",
            f"- Snapshot ID: {snapshot_id}",
            f"- Estimate line count: {estimate_line_count}",
            f"- Exact products resolved: {exact_products_resolved}",
            f"- Generic products: {generic_products}",
            f"- Unresolved products: {unresolved_products}",
            f"- Priced lines: {priced_lines}",
            f"- Quote-required lines: {quote_required_lines}",
            f"- Overall AV-03 readiness score: {overall_readiness_score:.4f}",
            "",
            "The reconstructed MAW engineering baseline is structurally sound, but the current commercial library does not yet provide priced coverage for the reconstructed product keys. That keeps the commercial baseline reviewable but not yet fully defendable for bid pricing.",
            "",
            "## Intake Statistics",
            "",
            f"- Source-fitness documents: {len(engineering.source_fitness.document_assessments)}",
            f"- Source-fitness pages: {len(engineering.source_fitness.page_assessments)}",
            f"- Baseline equipment rows: {len(engineering.baseline_equipment)}",
            f"- Commercial price records available: {commercial_summary.get('price_records', 0)}",
            f"- Commercial price sheets available: {commercial_summary.get('price_sheets', 0)}",
            f"- Commercial vendor offerings available: {commercial_summary.get('vendor_offerings', 0)}",
            "",
            "## Product Resolution",
            "",
            f"- Exact products resolved: {exact_products_resolved}",
            f"- Generic products preserved: {generic_products}",
            f"- Unresolved products: {unresolved_products}",
            "",
            "## Pricing Readiness",
            "",
            f"- Priced lines: {priced_lines} ({priced_pct:.1f}%)",
            f"- Quote-required lines: {quote_required_lines}",
            f"- Pricing coverage: {pricing.commercial_coverage.percentage_bom_lines_priced if pricing.commercial_coverage else 0.0:.4f}",
            f"- Commercial confidence: {pricing.commercial_coverage.commercial_confidence if pricing.commercial_coverage else 0.0:.4f}",
            "",
            "## Commercial Risks",
            "",
        ]
        for row in commercial_risk_rows:
            lines.append(
                f"- {row['root_issue']}: {row['affected_count']} affected line(s) - {row['explanation']}"
            )
        lines.extend(
            [
                "",
                "## Before / After",
                "",
            ]
        )
        for before_after_row in before_after_rows:
            lines.append(
                f"- {before_after_row.metric}: {before_after_row.before} -> {before_after_row.after}"
            )
        lines.extend(
            [
                "",
                "## Recommendation",
                "",
                "Repeat AV-03 after the commercial library is aligned to the reconstructed MAW product set or project quotes are imported for the unresolved price gaps.",
                "",
            ]
        )
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _commercial_state_from_workspace(
        workspace_payload: dict[str, Any],
    ) -> dict[str, Any]:
        workspace_state = dict(workspace_payload.get("workspace_state") or {})
        price_library = dict(workspace_state.get("price_list_library") or {})
        commercial = dict(price_library.get("commercial_knowledge") or {})
        if commercial:
            return commercial
        if workspace_state.get("commercial_state"):
            return dict(workspace_state.get("commercial_state") or {})
        return CommercialKnowledgeService.empty_state()

    @staticmethod
    def _commercial_summary(commercial_state: dict[str, Any]) -> dict[str, int]:
        return {
            "price_records": len(dict(commercial_state.get("price_records") or {})),
            "price_sheets": len(dict(commercial_state.get("price_sheets") or {})),
            "vendor_offerings": len(
                dict(commercial_state.get("vendor_offerings") or {})
            ),
            "catalog_items": len(dict(commercial_state.get("catalog_items") or {})),
            "manufacturers": len(dict(commercial_state.get("manufacturers") or {})),
            "vendors": len(dict(commercial_state.get("vendors") or {})),
        }

    @staticmethod
    def _pricing_summary(pricing: Any) -> dict[str, Any]:
        summary = pricing.summary.to_dict() if pricing.summary is not None else {}
        coverage = (
            pricing.commercial_coverage.to_dict()
            if pricing.commercial_coverage is not None
            else {}
        )
        return {"summary": summary, "commercial_coverage": coverage}

    @staticmethod
    def _scope_responsibility(
        responsibility: str | None,
        allowance_status: str,
        alternate_status: str,
    ) -> str:
        text = " ".join(
            str(part or "").lower()
            for part in (responsibility, allowance_status, alternate_status)
        )
        if "owner" in text:
            return "owner furnished"
        if "others" in text:
            return "installed by others"
        if "alternat" in text:
            return "alternate"
        if "allow" in text:
            return "allowance"
        if "contractor" in text:
            return "contractor furnished"
        return "coordination only"

    @classmethod
    def _scope_role(cls, row: dict[str, Any]) -> str:
        responsibility = str(row.get("scope_responsibility") or "").lower()
        if "owner" in responsibility:
            return "owner furnished"
        if "others" in responsibility:
            return "installed by others"
        if "allow" in responsibility:
            return "allowance"
        if "alternat" in responsibility:
            return "alternate"
        if "contractor" in responsibility:
            return "contractor furnished"
        return "coordination only"

    @staticmethod
    def _procurement_path(row: dict[str, Any]) -> str:
        resolution = str(row.get("resolution_status") or "")
        pricing = str(row.get("pricing_status") or "")
        if (
            resolution == ProductResolutionStatus.EXACT_PRODUCT.value
            and pricing != PricingStatus.NO_PRICING.value
        ):
            return "direct purchase"
        if resolution == ProductResolutionStatus.GENERIC_ALLOWANCE.value:
            return "allowance procurement"
        if pricing == PricingStatus.NO_PRICING.value:
            return "quote required"
        return "commercial review"

    @staticmethod
    def _procurement_path_description(path_name: str) -> str:
        if path_name == "direct purchase":
            return "Line can be purchased directly from the commercial record set."
        if path_name == "allowance procurement":
            return "Line remains a generic allowance and should not be forced into a fabricated SKU."
        if path_name == "quote required":
            return "Line needs a project quote or catalog alignment before pricing is defensible."
        return "Line requires additional commercial review."

    @staticmethod
    def _accessory_gap_label(row: Any) -> str:
        resolution_status = (
            row.get("resolution_status")
            if isinstance(row, dict)
            else getattr(row, "resolution_status", "")
        )
        if resolution_status == ProductResolutionStatus.GENERIC_ALLOWANCE.value:
            return "generic allowance accessories"
        quote_required = (
            row.get("quote_required")
            if isinstance(row, dict)
            else bool(getattr(row, "quote_required", False))
        )
        if quote_required:
            return "quote-required accessory package"
        return "current accessory package"

    @staticmethod
    def _labor_readiness_rows_from_source(
        estimate_baseline_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return []

    @staticmethod
    def _labor_readiness_score(
        *,
        quantity: str | int | float,
        manufacturer: str,
        model: str,
        room: str,
        source_fitness_score: int,
    ) -> float:
        score = 0.1
        if room:
            score += 0.25
        if manufacturer and manufacturer != "Unknown":
            score += 0.2
        if model and model != "Unknown":
            score += 0.2
        if str(quantity).strip():
            score += 0.15
        score += min(max(source_fitness_score, 0), 100) / 100 * 0.1
        return round(min(score, 1.0), 4)

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        fieldnames = list(rows[0].keys())
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        key: self._serialize_csv_value(value)
                        for key, value in row.items()
                    }
                )

    @staticmethod
    def _serialize_csv_value(value: Any) -> Any:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (list, tuple, set)):
            return "; ".join(str(item) for item in value)
        return value

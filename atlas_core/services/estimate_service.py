"""Deterministic estimate foundation service for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from atlas_core.domain.deterministic_estimate import (
    AccessoryCost,
    Allowance,
    Contingency,
    CostStatus,
    Estimate,
    EstimateConfidenceModel,
    EstimateLine,
    EstimatePackage,
    EstimateSourceReference,
    FreightCost,
    LaborCategory,
    LaborCost,
    Markup,
    MaterialCost,
    ProductResolutionStatus,
)


class VendorRegistryGateway(Protocol):
    def lookup_vendor(self, vendor_id: str) -> dict[str, Any] | None: ...


class ManufacturerRegistryGateway(Protocol):
    def lookup_manufacturer(self, manufacturer: str) -> dict[str, Any] | None: ...


class PriceListGateway(Protocol):
    def lookup_price(self, manufacturer: str, model: str) -> dict[str, Any] | None: ...


class QuoteImportGateway(Protocol):
    def lookup_quote(self, manufacturer: str, model: str) -> dict[str, Any] | None: ...


class LaborRuleGateway(Protocol):
    def resolve_labor_rule(self, line: EstimateLine) -> dict[str, Any] | None: ...


class RegionalMultiplierGateway(Protocol):
    def get_multiplier(self, region: str) -> float | None: ...


class SalesTaxGateway(Protocol):
    def get_sales_tax_rate(self, jurisdiction: str) -> float | None: ...


class CurrencyGateway(Protocol):
    def convert(
        self,
        amount: float,
        source_currency: str,
        target_currency: str,
    ) -> float | None: ...


class ProposalGeneratorGateway(Protocol):
    def generate(self, estimate: Estimate) -> dict[str, Any]: ...


class RFQGeneratorGateway(Protocol):
    def generate(self, estimate: Estimate) -> dict[str, Any]: ...


class AccessoryGenerationGateway(Protocol):
    def placeholder_categories_for_line(self, line: EstimateLine) -> list[str]: ...


@dataclass(frozen=True)
class EstimateExtensionPoints:
    vendor_registry: VendorRegistryGateway | None = None
    manufacturer_registry: ManufacturerRegistryGateway | None = None
    price_list: PriceListGateway | None = None
    quote_import: QuoteImportGateway | None = None
    labor_rules: LaborRuleGateway | None = None
    regional_multipliers: RegionalMultiplierGateway | None = None
    sales_tax: SalesTaxGateway | None = None
    currency: CurrencyGateway | None = None
    proposal_generator: ProposalGeneratorGateway | None = None
    rfq_generator: RFQGeneratorGateway | None = None
    accessory_generation: AccessoryGenerationGateway | None = None


class DeterministicEstimateService:
    """Build deterministic estimates from reviewed engineering objects."""

    ACCESSORY_PLACEHOLDER_CATEGORIES = [
        "Mounts",
        "Cables",
        "Connectors",
        "Rack Hardware",
        "Faceplates",
        "Adapters",
        "Power Supplies",
        "Network Modules",
    ]

    def __init__(
        self,
        extension_points: EstimateExtensionPoints | None = None,
    ) -> None:
        self.extension_points = extension_points or EstimateExtensionPoints()

    def build(
        self,
        *,
        project_id: str,
        project_name: str,
        bom_rows: list[dict[str, Any]],
        labor_estimate: Any | None = None,
    ) -> Estimate:
        lines = [
            self._line_from_bom_row(index, row, labor_estimate=labor_estimate)
            for index, row in enumerate(list(bom_rows or []), start=1)
        ]

        estimate = Estimate(
            estimate_id=f"estimate:{project_id}",
            project_id=project_id,
            project_name=project_name,
            packages=[
                EstimatePackage(
                    package_id="estimate-package:equipment",
                    name="Equipment Cost",
                    lines=lines,
                )
            ],
            freight_cost=FreightCost(amount=0.0, status=CostStatus.NO_PRICING),
            allowances=self._allowances_from_lines(lines),
            markup=Markup(percent=0.0),
            contingency=Contingency(percent=0.0),
        )
        estimate.confidence_model = self._build_confidence_model(estimate)
        return estimate

    def build_dashboard(self, estimate: Estimate) -> dict[str, Any]:
        lines = estimate.all_lines()
        line_count = len(lines)
        resolved_count = sum(
            1
            for line in lines
            if line.product_resolution_status
            in {
                ProductResolutionStatus.EXACT_PRODUCT,
                ProductResolutionStatus.APPROVED_SUBSTITUTE,
                ProductResolutionStatus.PREFERRED_ALTERNATE,
            }
        )
        unresolved_count = line_count - resolved_count

        material_cost = round(sum(line.material_cost.amount for line in lines), 2)
        labor_cost = round(sum(line.labor_cost.amount for line in lines), 2)
        accessory_cost = round(sum(line.accessory_cost.amount for line in lines), 2)
        allowance_cost = round(
            sum(line.allowance_cost for line in lines)
            + sum(item.amount for item in estimate.allowances),
            2,
        )

        known_cost_lines = sum(
            1 for line in lines if line.pricing_status is not CostStatus.NO_PRICING
        )
        known_cost_percent = (
            round((known_cost_lines / line_count) * 100, 1) if line_count else 0.0
        )
        unknown_cost_percent = (
            round(100.0 - known_cost_percent, 1) if line_count else 0.0
        )

        confidence_model = estimate.confidence_model or self._build_confidence_model(
            estimate
        )

        return {
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "accessory_cost": accessory_cost,
            "allowance_cost": allowance_cost,
            "freight": estimate.freight_cost.amount,
            "contingency": estimate.contingency_amount(),
            "known_cost_percent": known_cost_percent,
            "unknown_cost_percent": unknown_cost_percent,
            "resolved_products": resolved_count,
            "unresolved_products": unresolved_count,
            "pricing_confidence": round(confidence_model.known_pricing_ratio * 100, 1),
            "overall_estimate_confidence": round(confidence_model.score * 100, 1),
            "line_count": line_count,
        }

    def labor_architecture_rows(self, estimate: Estimate) -> list[dict[str, Any]]:
        lines = estimate.all_lines()
        labor_hours = [line.labor_cost.hours for line in lines if line.labor_cost.hours]
        blended_status = (
            "Estimated"
            if any(line.labor_status is not CostStatus.NO_PRICING for line in lines)
            else "No Pricing"
        )
        total_hours = round(sum(labor_hours), 2) if labor_hours else None

        return [
            {
                "Labor Category": category.value.replace("_", " ").title(),
                "Planned Hours": total_hours,
                "Status": blended_status,
            }
            for category in LaborCategory
        ]

    def _line_from_bom_row(
        self,
        index: int,
        row: dict[str, Any],
        *,
        labor_estimate: Any | None,
    ) -> EstimateLine:
        manufacturer = _safe_text(row.get("manufacturer"), "Unknown")
        model = _safe_text(row.get("model"), "Unknown")
        quantity = _coerce_quantity(row.get("quantity"))
        known_cost = _coerce_float(row.get("known_cost"))
        pricing_source = _safe_text(row.get("pricing_source"), "")
        warnings = [_safe_text(item, "") for item in list(row.get("warnings") or [])]
        completeness_status = _safe_text(row.get("completeness_status"), "")

        resolution_status = self._resolution_status_for_row(
            manufacturer=manufacturer,
            model=model,
            completeness_status=completeness_status,
            warnings=warnings,
        )
        pricing_status = self._pricing_status_for_row(
            known_cost=known_cost,
            pricing_source=pricing_source,
            warnings=warnings,
        )
        if resolution_status is ProductResolutionStatus.UNKNOWN_PRODUCT:
            pricing_status = CostStatus.NO_PRICING
            known_cost = None
        labor_status = (
            CostStatus.ESTIMATED
            if labor_estimate is not None
            else CostStatus.NO_PRICING
        )

        material_amount = round((known_cost or 0.0) * quantity, 2)
        labor_hours = (
            _coerce_float(getattr(labor_estimate, "total_labor_hours_expected", None))
            if labor_estimate is not None
            else None
        )
        labor_amount = 0.0

        source_refs = self._source_refs_for_row(row)

        line = EstimateLine(
            line_id=f"estimate-line:{index}",
            source_object=_safe_text(
                row.get("bom_item_id"),
                _safe_text(row.get("equipment_id"), f"source:{index}"),
            ),
            object_type="equipment",
            manufacturer=manufacturer,
            model=model,
            description=_safe_text(row.get("description"), "n/a"),
            quantity=quantity,
            pricing_status=pricing_status,
            labor_status=labor_status,
            confidence=self._line_confidence(
                pricing_status=pricing_status,
                resolution_status=resolution_status,
                quantity=quantity,
                manufacturer=manufacturer,
                model=model,
            ),
            source_references=source_refs,
            product_resolution_status=resolution_status,
            material_cost=MaterialCost(amount=material_amount, status=pricing_status),
            labor_cost=LaborCost(
                amount=labor_amount, hours=labor_hours, status=labor_status
            ),
            accessory_cost=AccessoryCost(
                amount=0.0,
                status=CostStatus.NO_PRICING,
                placeholder_categories=self.ACCESSORY_PLACEHOLDER_CATEGORIES,
            ),
            allowance_cost=0.0,
            freight_cost=0.0,
            navigation_refs=self._navigation_refs_for_row(row),
        )
        return line

    def _navigation_refs_for_row(self, row: dict[str, Any]) -> list[dict[str, str]]:
        line_id = _safe_text(
            row.get("bom_item_id"),
            _safe_text(row.get("equipment_id"), "source"),
        )
        drawing_refs = [
            _safe_text(item, "") for item in list(row.get("drawing_references") or [])
        ]
        specification_refs = [
            _safe_text(item, "")
            for item in list(row.get("specification_references") or [])
        ]
        source_documents = [
            _safe_text(item, "") for item in list(row.get("source_documents") or [])
        ]

        refs: list[dict[str, str]] = [
            {
                "target": "Equipment",
                "kind": "equipment",
                "value": line_id,
            },
            {
                "target": "Relationships",
                "kind": "relationships",
                "value": line_id,
            },
        ]
        if drawing_refs:
            refs.append(
                {
                    "target": "Drawing",
                    "kind": "drawing",
                    "value": drawing_refs[0],
                }
            )
        if specification_refs:
            refs.append(
                {
                    "target": "Specification",
                    "kind": "specification",
                    "value": specification_refs[0],
                }
            )
        if source_documents:
            refs.append(
                {
                    "target": "Evidence",
                    "kind": "evidence",
                    "value": source_documents[0],
                }
            )
        return refs

    def _source_refs_for_row(
        self, row: dict[str, Any]
    ) -> list[EstimateSourceReference]:
        refs: list[EstimateSourceReference] = []
        for item in list(row.get("source_documents") or []):
            document = _safe_text(item, "")
            if not document:
                continue
            refs.append(
                EstimateSourceReference(
                    source_type="document",
                    source_id=document,
                    source_label=document,
                )
            )
        for item in list(row.get("drawing_references") or []):
            drawing = _safe_text(item, "")
            if not drawing:
                continue
            refs.append(
                EstimateSourceReference(
                    source_type="drawing",
                    source_id=drawing,
                    source_label=drawing,
                )
            )
        for item in list(row.get("specification_references") or []):
            section = _safe_text(item, "")
            if not section:
                continue
            refs.append(
                EstimateSourceReference(
                    source_type="specification",
                    source_id=section,
                    source_label=section,
                )
            )
        return refs

    def _allowances_from_lines(self, lines: list[EstimateLine]) -> list[Allowance]:
        generic_lines = [
            line
            for line in lines
            if line.product_resolution_status
            is ProductResolutionStatus.GENERIC_ALLOWANCE
        ]
        if not generic_lines:
            return []

        refs = []
        for line in generic_lines:
            refs.extend(line.source_references)
        return [
            Allowance(
                allowance_id="allowance:generic-products",
                description="Generic product allowance pending deterministic resolution",
                amount=0.0,
                status=CostStatus.ESTIMATED,
                source_references=refs,
            )
        ]

    def _resolution_status_for_row(
        self,
        *,
        manufacturer: str,
        model: str,
        completeness_status: str,
        warnings: list[str],
    ) -> ProductResolutionStatus:
        warning_text = " ".join(item.lower() for item in warnings)
        if manufacturer.lower() == "unknown" or model.lower() == "unknown":
            return ProductResolutionStatus.UNKNOWN_PRODUCT
        if completeness_status in {
            "unresolved",
            "missing_manufacturer",
            "missing_model",
        }:
            return ProductResolutionStatus.UNKNOWN_PRODUCT
        if "substitute" in warning_text:
            return ProductResolutionStatus.APPROVED_SUBSTITUTE
        if "alternate" in warning_text:
            return ProductResolutionStatus.PREFERRED_ALTERNATE
        if completeness_status in {"drawing_only", "specification_only"}:
            return ProductResolutionStatus.GENERIC_ALLOWANCE
        return ProductResolutionStatus.EXACT_PRODUCT

    def _pricing_status_for_row(
        self,
        *,
        known_cost: float | None,
        pricing_source: str,
        warnings: list[str],
    ) -> CostStatus:
        warning_text = " ".join(item.lower() for item in warnings)
        source_text = pricing_source.lower()
        if "unavailable" in warning_text:
            return CostStatus.UNAVAILABLE
        if "expired" in warning_text:
            return CostStatus.EXPIRED
        if known_cost is None:
            return CostStatus.NO_PRICING
        if "verified" in source_text:
            return CostStatus.VERIFIED
        if "quote" in source_text:
            return CostStatus.QUOTED
        return CostStatus.ESTIMATED

    def _line_confidence(
        self,
        *,
        pricing_status: CostStatus,
        resolution_status: ProductResolutionStatus,
        quantity: float,
        manufacturer: str,
        model: str,
    ) -> float:
        confidence = 1.0

        status_penalties = {
            CostStatus.NO_PRICING: 0.35,
            CostStatus.ESTIMATED: 0.2,
            CostStatus.QUOTED: 0.1,
            CostStatus.VERIFIED: 0.0,
            CostStatus.EXPIRED: 0.4,
            CostStatus.UNAVAILABLE: 0.45,
        }
        confidence -= status_penalties[pricing_status]

        resolution_penalties = {
            ProductResolutionStatus.EXACT_PRODUCT: 0.0,
            ProductResolutionStatus.APPROVED_SUBSTITUTE: 0.08,
            ProductResolutionStatus.PREFERRED_ALTERNATE: 0.14,
            ProductResolutionStatus.GENERIC_ALLOWANCE: 0.25,
            ProductResolutionStatus.UNKNOWN_PRODUCT: 0.35,
        }
        confidence -= resolution_penalties[resolution_status]

        if quantity <= 0:
            confidence -= 0.2
        if manufacturer.lower() == "unknown":
            confidence -= 0.15
        if model.lower() == "unknown":
            confidence -= 0.15

        return round(max(0.0, min(confidence, 1.0)), 4)

    def _build_confidence_model(self, estimate: Estimate) -> EstimateConfidenceModel:
        lines = estimate.all_lines()
        total_lines = len(lines)
        if total_lines == 0:
            return EstimateConfidenceModel(
                score=0.0,
                known_pricing_ratio=0.0,
                resolved_product_ratio=0.0,
                unpriced_labor_ratio=1.0,
                unknown_quantity_ratio=0.0,
                generic_allowance_ratio=0.0,
                messages=[
                    "Estimate contains no lines; add reviewed engineering objects to begin costing."
                ],
            )

        known_pricing_ratio = (
            sum(1 for line in lines if line.pricing_status is not CostStatus.NO_PRICING)
            / total_lines
        )
        resolved_product_ratio = (
            sum(
                1
                for line in lines
                if line.product_resolution_status
                in {
                    ProductResolutionStatus.EXACT_PRODUCT,
                    ProductResolutionStatus.APPROVED_SUBSTITUTE,
                    ProductResolutionStatus.PREFERRED_ALTERNATE,
                }
            )
            / total_lines
        )
        unpriced_labor_ratio = (
            sum(1 for line in lines if line.labor_status is CostStatus.NO_PRICING)
            / total_lines
        )
        unknown_quantity_ratio = (
            sum(1 for line in lines if line.quantity <= 0) / total_lines
        )
        generic_allowance_ratio = (
            sum(
                1
                for line in lines
                if line.product_resolution_status
                is ProductResolutionStatus.GENERIC_ALLOWANCE
            )
            / total_lines
        )

        score = (
            (known_pricing_ratio * 0.45)
            + (resolved_product_ratio * 0.3)
            + ((1 - unpriced_labor_ratio) * 0.1)
            + ((1 - unknown_quantity_ratio) * 0.1)
            + ((1 - generic_allowance_ratio) * 0.05)
        )
        score = round(max(0.0, min(score, 1.0)), 4)

        messages: list[str] = []
        if known_pricing_ratio < 0.75:
            messages.append(
                "Pricing coverage is below preferred threshold; unresolved lines remain no-pricing."
            )
        if resolved_product_ratio < 0.8:
            messages.append(
                "Product resolution is incomplete; unknown or generic allowance lines require review."
            )
        if unpriced_labor_ratio > 0:
            messages.append(
                "Labor architecture exists but labor cost remains unpriced for one or more lines."
            )
        if unknown_quantity_ratio > 0:
            messages.append(
                "At least one line has unknown quantity, lowering deterministic confidence."
            )
        if generic_allowance_ratio > 0:
            messages.append(
                "Generic allowance lines are placeholders pending exact or approved product resolution."
            )
        if not messages:
            messages.append(
                "Estimate confidence is high for current deterministic coverage."
            )

        return EstimateConfidenceModel(
            score=score,
            known_pricing_ratio=round(known_pricing_ratio, 4),
            resolved_product_ratio=round(resolved_product_ratio, 4),
            unpriced_labor_ratio=round(unpriced_labor_ratio, 4),
            unknown_quantity_ratio=round(unknown_quantity_ratio, 4),
            generic_allowance_ratio=round(generic_allowance_ratio, 4),
            messages=messages,
        )


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or default
    return str(value)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _coerce_quantity(value: Any) -> float:
    quantity = _coerce_float(value)
    if quantity is None:
        return 0.0
    return round(max(quantity, 0.0), 2)

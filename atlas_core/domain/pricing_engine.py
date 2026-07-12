"""Deterministic pricing engine domain entities for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class PricingStatus(str, Enum):
    VERIFIED_CURRENT = "verified_current"
    QUOTED = "quoted"
    CURRENT_PRICE_SHEET = "current_price_sheet"
    HISTORICAL_PRICE = "historical_price"
    ESTIMATED_ALLOWANCE = "estimated_allowance"
    STALE_PRICE = "stale_price"
    EXPIRED_PRICE = "expired_price"
    MISSING_FROM_LATEST_PRICE_SHEET = "missing_from_latest_price_sheet"
    UNAVAILABLE = "unavailable"
    NO_PRICING = "no_pricing"
    MANUAL_OVERRIDE = "manual_override"


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    REVIEW_RECOMMENDED = "review_recommended"
    STALE = "stale"
    EXPIRED = "expired"
    MISSING_FROM_LATEST = "missing_from_latest"
    UNKNOWN = "unknown"


@dataclass
class PricingRule:
    rule_id: str
    name: str
    priority: int
    matched: bool
    detail: str

    def __post_init__(self) -> None:
        self.rule_id = _required("rule_id", self.rule_id)
        self.name = _required("name", self.name)
        self.priority = _non_negative_int("priority", self.priority)
        self.detail = _required("detail", self.detail)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "priority": self.priority,
            "matched": self.matched,
            "detail": self.detail,
        }


@dataclass
class PricingWarning:
    code: str
    message: str
    severity: str = "warning"

    def __post_init__(self) -> None:
        self.code = _required("code", self.code)
        self.message = _required("message", self.message)
        self.severity = _required("severity", self.severity)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass
class PriceSelectionCandidate:
    candidate_id: str
    vendor: str
    unit_cost: float | None
    list_price: float | None
    currency: str
    effective_date: str
    expiration_date: str
    import_date: str
    freshness_status: FreshnessStatus
    lead_time: str
    availability: str
    source_price_sheet_id: str
    source_price_sheet_version_id: str
    source_price_record_id: str
    source_vendor_offering_id: str
    confidence: float
    rank: int
    selection_reason: str

    def __post_init__(self) -> None:
        self.candidate_id = _required("candidate_id", self.candidate_id)
        self.vendor = _required("vendor", self.vendor)
        self.currency = _required("currency", self.currency)
        self.effective_date = _safe(self.effective_date)
        self.expiration_date = _safe(self.expiration_date)
        self.import_date = _safe(self.import_date)
        if not isinstance(self.freshness_status, FreshnessStatus):
            self.freshness_status = FreshnessStatus(self.freshness_status)
        self.lead_time = _safe(self.lead_time)
        self.availability = _safe(self.availability)
        self.source_price_sheet_id = _safe(self.source_price_sheet_id)
        self.source_price_sheet_version_id = _safe(self.source_price_sheet_version_id)
        self.source_price_record_id = _safe(self.source_price_record_id)
        self.source_vendor_offering_id = _safe(self.source_vendor_offering_id)
        self.confidence = _rate("confidence", self.confidence)
        self.rank = _non_negative_int("rank", self.rank)
        self.selection_reason = _required("selection_reason", self.selection_reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "vendor": self.vendor,
            "unit_cost": self.unit_cost,
            "list_price": self.list_price,
            "currency": self.currency,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "import_date": self.import_date,
            "freshness_status": self.freshness_status.value,
            "lead_time": self.lead_time,
            "availability": self.availability,
            "source_price_sheet_id": self.source_price_sheet_id,
            "source_price_sheet_version_id": self.source_price_sheet_version_id,
            "source_price_record_id": self.source_price_record_id,
            "source_vendor_offering_id": self.source_vendor_offering_id,
            "confidence": self.confidence,
            "rank": self.rank,
            "selection_reason": self.selection_reason,
        }


@dataclass
class PriceSelection:
    selected_candidate_id: str | None
    selection_method: str
    selection_reason: str
    candidates: list[PriceSelectionCandidate] = field(default_factory=list)
    applied_rules: list[PricingRule] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.selected_candidate_id = _safe(self.selected_candidate_id) or None
        self.selection_method = _required("selection_method", self.selection_method)
        self.selection_reason = _required("selection_reason", self.selection_reason)
        self.candidates = [
            (
                item
                if isinstance(item, PriceSelectionCandidate)
                else PriceSelectionCandidate(**item)
            )
            for item in list(self.candidates)
        ]
        self.applied_rules = [
            item if isinstance(item, PricingRule) else PricingRule(**item)
            for item in list(self.applied_rules)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_candidate_id": self.selected_candidate_id,
            "selection_method": self.selection_method,
            "selection_reason": self.selection_reason,
            "candidates": [item.to_dict() for item in self.candidates],
            "applied_rules": [item.to_dict() for item in self.applied_rules],
        }


@dataclass
class PriceManualOverride:
    original_automatic_selection: dict[str, Any] | None
    manual_unit_cost: float
    selected_vendor: str | None
    override_reason: str
    reviewer_placeholder: str
    timestamp: str
    source_reference: str

    def __post_init__(self) -> None:
        self.original_automatic_selection = (
            dict(self.original_automatic_selection or {}) or None
        )
        self.manual_unit_cost = _non_negative_float(
            "manual_unit_cost", self.manual_unit_cost
        )
        self.selected_vendor = _safe(self.selected_vendor) or None
        self.override_reason = _required("override_reason", self.override_reason)
        self.reviewer_placeholder = _required(
            "reviewer_placeholder", self.reviewer_placeholder
        )
        self.timestamp = _required("timestamp", self.timestamp)
        self.source_reference = _required("source_reference", self.source_reference)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_automatic_selection": dict(
                self.original_automatic_selection or {}
            ),
            "manual_unit_cost": self.manual_unit_cost,
            "selected_vendor": self.selected_vendor,
            "override_reason": self.override_reason,
            "reviewer_placeholder": self.reviewer_placeholder,
            "timestamp": self.timestamp,
            "source_reference": self.source_reference,
        }


@dataclass
class PricedEstimateLine:
    estimate_line_id: str
    source_equipment_id: str
    canonical_product_id: str | None
    manufacturer_id: str | None
    quantity: float
    selected_price_record_id: str | None
    selected_vendor_offering_id: str | None
    selected_price_sheet_id: str | None
    selected_price_sheet_version_id: str | None
    unit_cost: float | None
    extended_cost: float
    currency: str
    pricing_status: PricingStatus
    pricing_confidence: float
    selection_method: str
    selection_reason: str
    effective_date: str
    expiration_date: str
    import_date: str
    days_since_import: int | None
    freshness_status: FreshnessStatus
    warnings: list[PricingWarning] = field(default_factory=list)
    source_refs: list[dict[str, Any]] = field(default_factory=list)
    manual_override: PriceManualOverride | None = None
    selection: PriceSelection | None = None
    confidence_rationale: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.estimate_line_id = _required("estimate_line_id", self.estimate_line_id)
        self.source_equipment_id = _required(
            "source_equipment_id", self.source_equipment_id
        )
        self.canonical_product_id = _safe(self.canonical_product_id) or None
        self.manufacturer_id = _safe(self.manufacturer_id) or None
        self.quantity = _non_negative_float("quantity", self.quantity)
        self.selected_price_record_id = _safe(self.selected_price_record_id) or None
        self.selected_vendor_offering_id = (
            _safe(self.selected_vendor_offering_id) or None
        )
        self.selected_price_sheet_id = _safe(self.selected_price_sheet_id) or None
        self.selected_price_sheet_version_id = (
            _safe(self.selected_price_sheet_version_id) or None
        )
        self.unit_cost = (
            None
            if self.unit_cost is None
            else _non_negative_float("unit_cost", self.unit_cost)
        )
        self.extended_cost = _non_negative_float("extended_cost", self.extended_cost)
        self.currency = _required("currency", self.currency)
        if not isinstance(self.pricing_status, PricingStatus):
            self.pricing_status = PricingStatus(self.pricing_status)
        self.pricing_confidence = _rate("pricing_confidence", self.pricing_confidence)
        self.selection_method = _required("selection_method", self.selection_method)
        self.selection_reason = _required("selection_reason", self.selection_reason)
        self.effective_date = _safe(self.effective_date)
        self.expiration_date = _safe(self.expiration_date)
        self.import_date = _safe(self.import_date)
        if self.days_since_import is not None:
            self.days_since_import = _non_negative_int(
                "days_since_import", self.days_since_import
            )
        if not isinstance(self.freshness_status, FreshnessStatus):
            self.freshness_status = FreshnessStatus(self.freshness_status)
        self.warnings = [
            item if isinstance(item, PricingWarning) else PricingWarning(**item)
            for item in list(self.warnings)
        ]
        self.source_refs = [dict(item) for item in list(self.source_refs)]
        if self.manual_override is not None and not isinstance(
            self.manual_override, PriceManualOverride
        ):
            self.manual_override = PriceManualOverride(**self.manual_override)
        if self.selection is not None and not isinstance(
            self.selection, PriceSelection
        ):
            self.selection = PriceSelection(**self.selection)
        self.confidence_rationale = [
            _required("confidence_rationale", item)
            for item in list(self.confidence_rationale)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimate_line_id": self.estimate_line_id,
            "source_equipment_id": self.source_equipment_id,
            "canonical_product_id": self.canonical_product_id,
            "manufacturer_id": self.manufacturer_id,
            "quantity": self.quantity,
            "selected_price_record_id": self.selected_price_record_id,
            "selected_vendor_offering_id": self.selected_vendor_offering_id,
            "selected_price_sheet_id": self.selected_price_sheet_id,
            "selected_price_sheet_version_id": self.selected_price_sheet_version_id,
            "unit_cost": self.unit_cost,
            "extended_cost": self.extended_cost,
            "currency": self.currency,
            "pricing_status": self.pricing_status.value,
            "pricing_confidence": self.pricing_confidence,
            "selection_method": self.selection_method,
            "selection_reason": self.selection_reason,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "import_date": self.import_date,
            "days_since_import": self.days_since_import,
            "freshness_status": self.freshness_status.value,
            "warnings": [item.to_dict() for item in self.warnings],
            "source_refs": list(self.source_refs),
            "manual_override": (
                self.manual_override.to_dict()
                if self.manual_override is not None
                else None
            ),
            "selection": (
                self.selection.to_dict() if self.selection is not None else None
            ),
            "confidence_rationale": list(self.confidence_rationale),
        }


@dataclass
class CommercialCoverageSummary:
    total_resolved_products: int
    products_with_current_pricing: int
    products_with_quoted_pricing: int
    products_using_historical_pricing: int
    products_using_stale_pricing: int
    products_using_allowances: int
    products_with_no_pricing: int
    percentage_bom_lines_priced: float
    percentage_material_value_current: float
    percentage_material_value_quoted: float
    percentage_material_value_stale_or_estimated: float
    commercial_confidence: float

    def __post_init__(self) -> None:
        for name in [
            "total_resolved_products",
            "products_with_current_pricing",
            "products_with_quoted_pricing",
            "products_using_historical_pricing",
            "products_using_stale_pricing",
            "products_using_allowances",
            "products_with_no_pricing",
        ]:
            setattr(self, name, _non_negative_int(name, getattr(self, name)))

        self.percentage_bom_lines_priced = _rate_percent(
            "percentage_bom_lines_priced", self.percentage_bom_lines_priced
        )
        self.percentage_material_value_current = _rate_percent(
            "percentage_material_value_current", self.percentage_material_value_current
        )
        self.percentage_material_value_quoted = _rate_percent(
            "percentage_material_value_quoted", self.percentage_material_value_quoted
        )
        self.percentage_material_value_stale_or_estimated = _rate_percent(
            "percentage_material_value_stale_or_estimated",
            self.percentage_material_value_stale_or_estimated,
        )
        self.commercial_confidence = _rate(
            "commercial_confidence", self.commercial_confidence
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_resolved_products": self.total_resolved_products,
            "products_with_current_pricing": self.products_with_current_pricing,
            "products_with_quoted_pricing": self.products_with_quoted_pricing,
            "products_using_historical_pricing": self.products_using_historical_pricing,
            "products_using_stale_pricing": self.products_using_stale_pricing,
            "products_using_allowances": self.products_using_allowances,
            "products_with_no_pricing": self.products_with_no_pricing,
            "percentage_bom_lines_priced": self.percentage_bom_lines_priced,
            "percentage_material_value_current": self.percentage_material_value_current,
            "percentage_material_value_quoted": self.percentage_material_value_quoted,
            "percentage_material_value_stale_or_estimated": self.percentage_material_value_stale_or_estimated,
            "commercial_confidence": self.commercial_confidence,
        }


@dataclass
class PricingSummary:
    material_subtotal: float
    known_cost: float
    allowance_cost: float
    unpriced_exposure: float
    current_pricing_coverage: float
    commercial_confidence: float

    def __post_init__(self) -> None:
        self.material_subtotal = _non_negative_float(
            "material_subtotal", self.material_subtotal
        )
        self.known_cost = _non_negative_float("known_cost", self.known_cost)
        self.allowance_cost = _non_negative_float("allowance_cost", self.allowance_cost)
        self.unpriced_exposure = _non_negative_float(
            "unpriced_exposure", self.unpriced_exposure
        )
        self.current_pricing_coverage = _rate_percent(
            "current_pricing_coverage", self.current_pricing_coverage
        )
        self.commercial_confidence = _rate(
            "commercial_confidence", self.commercial_confidence
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_subtotal": self.material_subtotal,
            "known_cost": self.known_cost,
            "allowance_cost": self.allowance_cost,
            "unpriced_exposure": self.unpriced_exposure,
            "current_pricing_coverage": self.current_pricing_coverage,
            "commercial_confidence": self.commercial_confidence,
        }


@dataclass
class PricingResult:
    pricing_run_id: str
    run_timestamp: str
    pricing_policy_version: str
    priced_lines: list[PricedEstimateLine] = field(default_factory=list)
    summary: PricingSummary | None = None
    commercial_coverage: CommercialCoverageSummary | None = None
    warnings: list[PricingWarning] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.pricing_run_id = _required("pricing_run_id", self.pricing_run_id)
        self.run_timestamp = _required("run_timestamp", self.run_timestamp)
        self.pricing_policy_version = _required(
            "pricing_policy_version", self.pricing_policy_version
        )
        self.priced_lines = [
            item if isinstance(item, PricedEstimateLine) else PricedEstimateLine(**item)
            for item in list(self.priced_lines)
        ]
        if self.summary is not None and not isinstance(self.summary, PricingSummary):
            self.summary = PricingSummary(**self.summary)
        if self.commercial_coverage is not None and not isinstance(
            self.commercial_coverage, CommercialCoverageSummary
        ):
            self.commercial_coverage = CommercialCoverageSummary(
                **self.commercial_coverage
            )
        self.warnings = [
            item if isinstance(item, PricingWarning) else PricingWarning(**item)
            for item in list(self.warnings)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pricing_run_id": self.pricing_run_id,
            "run_timestamp": self.run_timestamp,
            "pricing_policy_version": self.pricing_policy_version,
            "priced_lines": [item.to_dict() for item in self.priced_lines],
            "summary": self.summary.to_dict() if self.summary is not None else None,
            "commercial_coverage": (
                self.commercial_coverage.to_dict()
                if self.commercial_coverage is not None
                else None
            ),
            "warnings": [item.to_dict() for item in self.warnings],
        }


def _safe(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _required(field_name: str, value: Any) -> str:
    text = _safe(value)
    if not text:
        raise ValueError(f"{field_name} cannot be blank")
    return text


def _non_negative_int(field_name: str, value: Any) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _non_negative_float(field_name: str, value: Any) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 4)
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return normalized


def _rate(field_name: str, value: Any) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 4)
    if not 0 <= normalized <= 1:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return normalized


def _rate_percent(field_name: str, value: Any) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 4)
    if not 0 <= normalized <= 100:
        raise ValueError(f"{field_name} must be between 0 and 100")
    return normalized

"""Deterministic cost engine domain entities for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VendorClassification(str, Enum):
    MANUFACTURER_DIRECT = "manufacturer_direct"
    AUTHORIZED_DISTRIBUTOR = "authorized_distributor"
    REGIONAL_DISTRIBUTOR = "regional_distributor"
    BUYING_GROUP = "buying_group"
    MARKETPLACE = "marketplace"
    INTEGRATOR = "integrator"
    OTHER = "other"


class CostStatus(str, Enum):
    VERIFIED = "verified"
    QUOTED = "quoted"
    CURRENT = "current"
    HISTORICAL = "historical"
    ALLOWANCE = "allowance"
    STALE = "stale"
    EXPIRED = "expired"
    UNAVAILABLE = "unavailable"
    MISSING = "missing"


class CostFreshness(str, Enum):
    FRESH = "fresh"
    REVIEW_RECOMMENDED = "review_recommended"
    STALE = "stale"
    EXPIRED = "expired"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass
class CostCandidate:
    candidate_id: str
    vendor: str
    vendor_type: VendorClassification
    acquisition_cost: float | None
    currency: str
    effective_date: str
    expiration_date: str
    import_date: str
    days_since_import: int | None
    source_file: str
    source_row: int | None
    price_sheet_id: str
    price_sheet_version_id: str
    vendor_offering_id: str
    price_record_id: str
    freshness: CostFreshness
    rank: int
    reason: str
    availability: str
    confidence: float

    def __post_init__(self) -> None:
        self.candidate_id = _required("candidate_id", self.candidate_id)
        self.vendor = _required("vendor", self.vendor)
        if not isinstance(self.vendor_type, VendorClassification):
            self.vendor_type = VendorClassification(self.vendor_type)
        self.acquisition_cost = (
            None
            if self.acquisition_cost is None
            else _non_negative_float("acquisition_cost", self.acquisition_cost)
        )
        self.currency = _required("currency", self.currency)
        self.effective_date = _safe(self.effective_date)
        self.expiration_date = _safe(self.expiration_date)
        self.import_date = _safe(self.import_date)
        if self.days_since_import is not None:
            self.days_since_import = _non_negative_int(
                "days_since_import", self.days_since_import
            )
        self.source_file = _safe(self.source_file)
        if self.source_row is not None:
            self.source_row = _non_negative_int("source_row", self.source_row)
        self.price_sheet_id = _safe(self.price_sheet_id)
        self.price_sheet_version_id = _safe(self.price_sheet_version_id)
        self.vendor_offering_id = _safe(self.vendor_offering_id)
        self.price_record_id = _safe(self.price_record_id)
        if not isinstance(self.freshness, CostFreshness):
            self.freshness = CostFreshness(self.freshness)
        self.rank = _non_negative_int("rank", self.rank)
        self.reason = _required("reason", self.reason)
        self.availability = _safe(self.availability)
        self.confidence = _rate("confidence", self.confidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "vendor": self.vendor,
            "vendor_type": self.vendor_type.value,
            "acquisition_cost": self.acquisition_cost,
            "currency": self.currency,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "import_date": self.import_date,
            "days_since_import": self.days_since_import,
            "source_file": self.source_file,
            "source_row": self.source_row,
            "price_sheet_id": self.price_sheet_id,
            "price_sheet_version_id": self.price_sheet_version_id,
            "vendor_offering_id": self.vendor_offering_id,
            "price_record_id": self.price_record_id,
            "freshness": self.freshness.value,
            "rank": self.rank,
            "reason": self.reason,
            "availability": self.availability,
            "confidence": self.confidence,
        }


@dataclass
class CostSelection:
    selected_candidate_id: str | None
    method: str
    reason: str
    candidates: list[CostCandidate] = field(default_factory=list)
    decision_trace: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.selected_candidate_id = _safe(self.selected_candidate_id) or None
        self.method = _required("method", self.method)
        self.reason = _required("reason", self.reason)
        self.candidates = [
            item if isinstance(item, CostCandidate) else CostCandidate(**item)
            for item in list(self.candidates)
        ]
        self.decision_trace = [
            _required("decision_trace", item) for item in self.decision_trace
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_candidate_id": self.selected_candidate_id,
            "method": self.method,
            "reason": self.reason,
            "candidates": [item.to_dict() for item in self.candidates],
            "decision_trace": list(self.decision_trace),
        }


@dataclass
class CostConfidence:
    score: float
    rationale: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.score = _rate("score", self.score)
        self.rationale = [_required("rationale", item) for item in self.rationale]

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "rationale": list(self.rationale)}


@dataclass
class CostLine:
    cost_line_id: str
    estimate_line_id: str
    equipment_object_id: str
    resolved_product_id: str | None
    vendor_offering_id: str | None
    price_record_id: str | None
    price_sheet_version_id: str | None
    vendor: str | None
    vendor_type: VendorClassification | None
    quantity: float
    unit_cost: float | None
    extended_cost: float
    currency: str
    status: CostStatus
    freshness: CostFreshness
    import_date: str
    effective_date: str
    expiration_date: str
    days_since_import: int | None
    source_file: str
    source_row: int | None
    warnings: list[str] = field(default_factory=list)
    confidence: CostConfidence | None = None
    selection: CostSelection | None = None
    supporting_evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cost_line_id = _required("cost_line_id", self.cost_line_id)
        self.estimate_line_id = _required("estimate_line_id", self.estimate_line_id)
        self.equipment_object_id = _required(
            "equipment_object_id", self.equipment_object_id
        )
        self.resolved_product_id = _safe(self.resolved_product_id) or None
        self.vendor_offering_id = _safe(self.vendor_offering_id) or None
        self.price_record_id = _safe(self.price_record_id) or None
        self.price_sheet_version_id = _safe(self.price_sheet_version_id) or None
        self.vendor = _safe(self.vendor) or None
        if self.vendor_type is not None and not isinstance(
            self.vendor_type, VendorClassification
        ):
            self.vendor_type = VendorClassification(self.vendor_type)
        self.quantity = _non_negative_float("quantity", self.quantity)
        self.unit_cost = (
            None
            if self.unit_cost is None
            else _non_negative_float("unit_cost", self.unit_cost)
        )
        self.extended_cost = _non_negative_float("extended_cost", self.extended_cost)
        self.currency = _required("currency", self.currency)
        if not isinstance(self.status, CostStatus):
            self.status = CostStatus(self.status)
        if not isinstance(self.freshness, CostFreshness):
            self.freshness = CostFreshness(self.freshness)
        self.import_date = _safe(self.import_date)
        self.effective_date = _safe(self.effective_date)
        self.expiration_date = _safe(self.expiration_date)
        if self.days_since_import is not None:
            self.days_since_import = _non_negative_int(
                "days_since_import", self.days_since_import
            )
        self.source_file = _safe(self.source_file)
        if self.source_row is not None:
            self.source_row = _non_negative_int("source_row", self.source_row)
        self.warnings = [_required("warning", item) for item in self.warnings]
        if self.confidence is not None and not isinstance(
            self.confidence, CostConfidence
        ):
            self.confidence = CostConfidence(**self.confidence)
        if self.selection is not None and not isinstance(self.selection, CostSelection):
            self.selection = CostSelection(**self.selection)
        self.supporting_evidence = [
            _required("supporting_evidence", item) for item in self.supporting_evidence
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cost_line_id": self.cost_line_id,
            "estimate_line_id": self.estimate_line_id,
            "equipment_object_id": self.equipment_object_id,
            "resolved_product_id": self.resolved_product_id,
            "vendor_offering_id": self.vendor_offering_id,
            "price_record_id": self.price_record_id,
            "price_sheet_version_id": self.price_sheet_version_id,
            "vendor": self.vendor,
            "vendor_type": (
                self.vendor_type.value if self.vendor_type is not None else None
            ),
            "quantity": self.quantity,
            "unit_cost": self.unit_cost,
            "extended_cost": self.extended_cost,
            "currency": self.currency,
            "status": self.status.value,
            "freshness": self.freshness.value,
            "import_date": self.import_date,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "days_since_import": self.days_since_import,
            "source_file": self.source_file,
            "source_row": self.source_row,
            "warnings": list(self.warnings),
            "confidence": (
                self.confidence.to_dict() if self.confidence is not None else None
            ),
            "selection": (
                self.selection.to_dict() if self.selection is not None else None
            ),
            "supporting_evidence": list(self.supporting_evidence),
        }


@dataclass
class CommercialCoverage:
    resolved_products: int
    products_with_current_cost: int
    products_using_historical_cost: int
    products_using_allowances: int
    products_missing_cost: int
    products_with_stale_cost: int
    coverage_percent: float
    material_cost_confidence: float

    def __post_init__(self) -> None:
        self.resolved_products = _non_negative_int(
            "resolved_products", self.resolved_products
        )
        self.products_with_current_cost = _non_negative_int(
            "products_with_current_cost", self.products_with_current_cost
        )
        self.products_using_historical_cost = _non_negative_int(
            "products_using_historical_cost", self.products_using_historical_cost
        )
        self.products_using_allowances = _non_negative_int(
            "products_using_allowances", self.products_using_allowances
        )
        self.products_missing_cost = _non_negative_int(
            "products_missing_cost", self.products_missing_cost
        )
        self.products_with_stale_cost = _non_negative_int(
            "products_with_stale_cost", self.products_with_stale_cost
        )
        self.coverage_percent = _rate_percent("coverage_percent", self.coverage_percent)
        self.material_cost_confidence = _rate(
            "material_cost_confidence", self.material_cost_confidence
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolved_products": self.resolved_products,
            "products_with_current_cost": self.products_with_current_cost,
            "products_using_historical_cost": self.products_using_historical_cost,
            "products_using_allowances": self.products_using_allowances,
            "products_missing_cost": self.products_missing_cost,
            "products_with_stale_cost": self.products_with_stale_cost,
            "coverage_percent": self.coverage_percent,
            "material_cost_confidence": self.material_cost_confidence,
        }


@dataclass
class ProjectCostSummary:
    equipment_cost: float
    accessory_cost: float
    software_cost: float
    freight_placeholder: float
    travel_placeholder: float
    labor_placeholder: float
    project_services_placeholder: float
    subcontractor_placeholder: float
    allowance_cost: float
    known_cost: float
    unknown_cost: float
    known_cost_percent: float
    unknown_cost_percent: float
    products_without_cost: int
    pricing_freshness: str
    commercial_confidence: float

    def __post_init__(self) -> None:
        for field_name in [
            "equipment_cost",
            "accessory_cost",
            "software_cost",
            "freight_placeholder",
            "travel_placeholder",
            "labor_placeholder",
            "project_services_placeholder",
            "subcontractor_placeholder",
            "allowance_cost",
            "known_cost",
            "unknown_cost",
        ]:
            setattr(
                self,
                field_name,
                _non_negative_float(field_name, getattr(self, field_name)),
            )
        self.known_cost_percent = _rate_percent(
            "known_cost_percent", self.known_cost_percent
        )
        self.unknown_cost_percent = _rate_percent(
            "unknown_cost_percent", self.unknown_cost_percent
        )
        self.products_without_cost = _non_negative_int(
            "products_without_cost", self.products_without_cost
        )
        self.pricing_freshness = _required("pricing_freshness", self.pricing_freshness)
        self.commercial_confidence = _rate(
            "commercial_confidence", self.commercial_confidence
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "equipment_cost": self.equipment_cost,
            "accessory_cost": self.accessory_cost,
            "software_cost": self.software_cost,
            "freight_placeholder": self.freight_placeholder,
            "travel_placeholder": self.travel_placeholder,
            "labor_placeholder": self.labor_placeholder,
            "project_services_placeholder": self.project_services_placeholder,
            "subcontractor_placeholder": self.subcontractor_placeholder,
            "allowance_cost": self.allowance_cost,
            "known_cost": self.known_cost,
            "unknown_cost": self.unknown_cost,
            "known_cost_percent": self.known_cost_percent,
            "unknown_cost_percent": self.unknown_cost_percent,
            "products_without_cost": self.products_without_cost,
            "pricing_freshness": self.pricing_freshness,
            "commercial_confidence": self.commercial_confidence,
        }


@dataclass
class CostSummary:
    project_summary: ProjectCostSummary

    def __post_init__(self) -> None:
        if not isinstance(self.project_summary, ProjectCostSummary):
            self.project_summary = ProjectCostSummary(**self.project_summary)

    def to_dict(self) -> dict[str, Any]:
        return {"project_summary": self.project_summary.to_dict()}


@dataclass
class CostResult:
    cost_run_id: str
    run_timestamp: str
    cost_policy_version: str
    lines: list[CostLine] = field(default_factory=list)
    summary: CostSummary | None = None
    commercial_coverage: CommercialCoverage | None = None

    def __post_init__(self) -> None:
        self.cost_run_id = _required("cost_run_id", self.cost_run_id)
        self.run_timestamp = _required("run_timestamp", self.run_timestamp)
        self.cost_policy_version = _required(
            "cost_policy_version", self.cost_policy_version
        )
        self.lines = [
            item if isinstance(item, CostLine) else CostLine(**item)
            for item in self.lines
        ]
        if self.summary is not None and not isinstance(self.summary, CostSummary):
            self.summary = CostSummary(**self.summary)
        if self.commercial_coverage is not None and not isinstance(
            self.commercial_coverage, CommercialCoverage
        ):
            self.commercial_coverage = CommercialCoverage(**self.commercial_coverage)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cost_run_id": self.cost_run_id,
            "run_timestamp": self.run_timestamp,
            "cost_policy_version": self.cost_policy_version,
            "lines": [item.to_dict() for item in self.lines],
            "summary": self.summary.to_dict() if self.summary is not None else None,
            "commercial_coverage": (
                self.commercial_coverage.to_dict()
                if self.commercial_coverage is not None
                else None
            ),
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


def _non_negative_float(field_name: str, value: Any) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 4)
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return normalized


def _non_negative_int(field_name: str, value: Any) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


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

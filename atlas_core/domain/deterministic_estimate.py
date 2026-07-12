"""Deterministic estimating domain models for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProductResolutionStatus(str, Enum):
    EXACT_PRODUCT = "exact_product"
    APPROVED_SUBSTITUTE = "approved_substitute"
    PREFERRED_ALTERNATE = "preferred_alternate"
    GENERIC_ALLOWANCE = "generic_allowance"
    UNKNOWN_PRODUCT = "unknown_product"


class CostStatus(str, Enum):
    NO_PRICING = "no_pricing"
    ESTIMATED = "estimated"
    QUOTED = "quoted"
    VERIFIED = "verified"
    EXPIRED = "expired"
    UNAVAILABLE = "unavailable"


class LaborCategory(str, Enum):
    RECEIVING = "receiving"
    STAGING = "staging"
    RACK_BUILD = "rack_build"
    INSTALLATION = "installation"
    TERMINATION = "termination"
    PROGRAMMING = "programming"
    COMMISSIONING = "commissioning"
    TESTING = "testing"
    TRAINING = "training"
    PUNCH = "punch"


@dataclass
class EstimateSourceReference:
    source_type: str
    source_id: str
    source_label: str | None = None
    excerpt: str | None = None

    def __post_init__(self) -> None:
        self.source_type = _normalize_required_text("source_type", self.source_type)
        self.source_id = _normalize_required_text("source_id", self.source_id)
        self.source_label = _normalize_optional_text(self.source_label)
        self.excerpt = _normalize_optional_text(self.excerpt)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_label": self.source_label,
            "excerpt": self.excerpt,
        }


@dataclass
class MaterialCost:
    amount: float = 0.0
    status: CostStatus = CostStatus.NO_PRICING

    def __post_init__(self) -> None:
        self.amount = _normalize_non_negative_float("amount", self.amount)
        if not isinstance(self.status, CostStatus):
            self.status = CostStatus(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "status": self.status.value,
        }


@dataclass
class LaborCost:
    amount: float = 0.0
    hours: float | None = None
    category_hours: dict[str, float | None] = field(default_factory=dict)
    status: CostStatus = CostStatus.NO_PRICING

    def __post_init__(self) -> None:
        self.amount = _normalize_non_negative_float("amount", self.amount)
        if self.hours is not None:
            self.hours = _normalize_non_negative_float("hours", self.hours)
        self.category_hours = {
            _normalize_required_text("category", str(key)): (
                None if value is None else _normalize_non_negative_float("hours", value)
            )
            for key, value in self.category_hours.items()
        }
        if not isinstance(self.status, CostStatus):
            self.status = CostStatus(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "hours": self.hours,
            "category_hours": dict(self.category_hours),
            "status": self.status.value,
        }


@dataclass
class AccessoryCost:
    amount: float = 0.0
    status: CostStatus = CostStatus.NO_PRICING
    placeholder_categories: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.amount = _normalize_non_negative_float("amount", self.amount)
        self.placeholder_categories = [
            _normalize_required_text("placeholder_category", category)
            for category in self.placeholder_categories
        ]
        if not isinstance(self.status, CostStatus):
            self.status = CostStatus(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "status": self.status.value,
            "placeholder_categories": list(self.placeholder_categories),
        }


@dataclass
class FreightCost:
    amount: float = 0.0
    status: CostStatus = CostStatus.NO_PRICING

    def __post_init__(self) -> None:
        self.amount = _normalize_non_negative_float("amount", self.amount)
        if not isinstance(self.status, CostStatus):
            self.status = CostStatus(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "status": self.status.value,
        }


@dataclass
class Allowance:
    allowance_id: str
    description: str
    amount: float = 0.0
    status: CostStatus = CostStatus.ESTIMATED
    source_references: list[EstimateSourceReference] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.allowance_id = _normalize_required_text("allowance_id", self.allowance_id)
        self.description = _normalize_required_text("description", self.description)
        self.amount = _normalize_non_negative_float("amount", self.amount)
        if not isinstance(self.status, CostStatus):
            self.status = CostStatus(self.status)
        self.source_references = [
            (
                source
                if isinstance(source, EstimateSourceReference)
                else EstimateSourceReference(**source)
            )
            for source in self.source_references
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowance_id": self.allowance_id,
            "description": self.description,
            "amount": self.amount,
            "status": self.status.value,
            "source_references": [
                source.to_dict() for source in self.source_references
            ],
        }


@dataclass
class Subtotal:
    amount: float

    def __post_init__(self) -> None:
        self.amount = _normalize_non_negative_float("amount", self.amount)

    def to_dict(self) -> dict[str, Any]:
        return {"amount": self.amount}


@dataclass
class Markup:
    percent: float = 0.0

    def __post_init__(self) -> None:
        self.percent = _normalize_rate("percent", self.percent)

    def amount_for(self, base_amount: float) -> float:
        return round(
            _normalize_non_negative_float("base_amount", base_amount) * self.percent, 2
        )

    def to_dict(self) -> dict[str, Any]:
        return {"percent": self.percent}


@dataclass
class Contingency:
    percent: float = 0.0

    def __post_init__(self) -> None:
        self.percent = _normalize_rate("percent", self.percent)

    def amount_for(self, base_amount: float) -> float:
        return round(
            _normalize_non_negative_float("base_amount", base_amount) * self.percent, 2
        )

    def to_dict(self) -> dict[str, Any]:
        return {"percent": self.percent}


@dataclass
class GrandTotal:
    amount: float

    def __post_init__(self) -> None:
        self.amount = _normalize_non_negative_float("amount", self.amount)

    def to_dict(self) -> dict[str, Any]:
        return {"amount": self.amount}


@dataclass
class EstimateLine:
    line_id: str
    source_object: str
    object_type: str
    manufacturer: str
    model: str
    description: str
    quantity: float
    pricing_status: CostStatus
    labor_status: CostStatus
    confidence: float
    source_references: list[EstimateSourceReference] = field(default_factory=list)
    product_resolution_status: ProductResolutionStatus = (
        ProductResolutionStatus.UNKNOWN_PRODUCT
    )
    material_cost: MaterialCost = field(default_factory=MaterialCost)
    labor_cost: LaborCost = field(default_factory=LaborCost)
    accessory_cost: AccessoryCost = field(default_factory=AccessoryCost)
    allowance_cost: float = 0.0
    freight_cost: float = 0.0
    navigation_refs: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.line_id = _normalize_required_text("line_id", self.line_id)
        self.source_object = _normalize_required_text(
            "source_object", self.source_object
        )
        self.object_type = _normalize_required_text("object_type", self.object_type)
        self.manufacturer = _normalize_optional_text(self.manufacturer) or "Unknown"
        self.model = _normalize_optional_text(self.model) or "Unknown"
        self.description = _normalize_optional_text(self.description) or "n/a"
        self.quantity = _normalize_non_negative_float("quantity", self.quantity)
        self.confidence = _normalize_rate("confidence", self.confidence)
        self.allowance_cost = _normalize_non_negative_float(
            "allowance_cost", self.allowance_cost
        )
        self.freight_cost = _normalize_non_negative_float(
            "freight_cost", self.freight_cost
        )

        if not isinstance(self.pricing_status, CostStatus):
            self.pricing_status = CostStatus(self.pricing_status)
        if not isinstance(self.labor_status, CostStatus):
            self.labor_status = CostStatus(self.labor_status)
        if not isinstance(self.product_resolution_status, ProductResolutionStatus):
            self.product_resolution_status = ProductResolutionStatus(
                self.product_resolution_status
            )

        self.source_references = [
            (
                source
                if isinstance(source, EstimateSourceReference)
                else EstimateSourceReference(**source)
            )
            for source in self.source_references
        ]
        self.material_cost = (
            self.material_cost
            if isinstance(self.material_cost, MaterialCost)
            else MaterialCost(**self.material_cost)
        )
        self.labor_cost = (
            self.labor_cost
            if isinstance(self.labor_cost, LaborCost)
            else LaborCost(**self.labor_cost)
        )
        self.accessory_cost = (
            self.accessory_cost
            if isinstance(self.accessory_cost, AccessoryCost)
            else AccessoryCost(**self.accessory_cost)
        )

    def line_total(self) -> float:
        return round(
            self.material_cost.amount
            + self.labor_cost.amount
            + self.accessory_cost.amount
            + self.allowance_cost
            + self.freight_cost,
            2,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_id": self.line_id,
            "source_object": self.source_object,
            "object_type": self.object_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "description": self.description,
            "quantity": self.quantity,
            "pricing_status": self.pricing_status.value,
            "labor_status": self.labor_status.value,
            "confidence": self.confidence,
            "product_resolution_status": self.product_resolution_status.value,
            "source_references": [
                source.to_dict() for source in self.source_references
            ],
            "material_cost": self.material_cost.to_dict(),
            "labor_cost": self.labor_cost.to_dict(),
            "accessory_cost": self.accessory_cost.to_dict(),
            "allowance_cost": self.allowance_cost,
            "freight_cost": self.freight_cost,
            "line_total": self.line_total(),
            "navigation_refs": list(self.navigation_refs),
        }


@dataclass
class EstimatePackage:
    package_id: str
    name: str
    lines: list[EstimateLine] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.package_id = _normalize_required_text("package_id", self.package_id)
        self.name = _normalize_required_text("name", self.name)
        self.lines = [
            line if isinstance(line, EstimateLine) else EstimateLine(**line)
            for line in self.lines
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "name": self.name,
            "lines": [line.to_dict() for line in self.lines],
        }


@dataclass
class EstimateConfidenceModel:
    score: float
    known_pricing_ratio: float
    resolved_product_ratio: float
    unpriced_labor_ratio: float
    unknown_quantity_ratio: float
    generic_allowance_ratio: float
    messages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.score = _normalize_rate("score", self.score)
        self.known_pricing_ratio = _normalize_rate(
            "known_pricing_ratio", self.known_pricing_ratio
        )
        self.resolved_product_ratio = _normalize_rate(
            "resolved_product_ratio", self.resolved_product_ratio
        )
        self.unpriced_labor_ratio = _normalize_rate(
            "unpriced_labor_ratio", self.unpriced_labor_ratio
        )
        self.unknown_quantity_ratio = _normalize_rate(
            "unknown_quantity_ratio", self.unknown_quantity_ratio
        )
        self.generic_allowance_ratio = _normalize_rate(
            "generic_allowance_ratio", self.generic_allowance_ratio
        )
        self.messages = [
            _normalize_required_text("message", message) for message in self.messages
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "known_pricing_ratio": self.known_pricing_ratio,
            "resolved_product_ratio": self.resolved_product_ratio,
            "unpriced_labor_ratio": self.unpriced_labor_ratio,
            "unknown_quantity_ratio": self.unknown_quantity_ratio,
            "generic_allowance_ratio": self.generic_allowance_ratio,
            "messages": list(self.messages),
        }


@dataclass
class Estimate:
    estimate_id: str
    project_id: str
    project_name: str
    packages: list[EstimatePackage] = field(default_factory=list)
    freight_cost: FreightCost = field(default_factory=FreightCost)
    allowances: list[Allowance] = field(default_factory=list)
    markup: Markup = field(default_factory=Markup)
    contingency: Contingency = field(default_factory=Contingency)
    confidence_model: EstimateConfidenceModel | None = None

    def __post_init__(self) -> None:
        self.estimate_id = _normalize_required_text("estimate_id", self.estimate_id)
        self.project_id = _normalize_required_text("project_id", self.project_id)
        self.project_name = _normalize_required_text("project_name", self.project_name)
        self.packages = [
            (
                package
                if isinstance(package, EstimatePackage)
                else EstimatePackage(**package)
            )
            for package in self.packages
        ]
        self.freight_cost = (
            self.freight_cost
            if isinstance(self.freight_cost, FreightCost)
            else FreightCost(**self.freight_cost)
        )
        self.allowances = [
            allowance if isinstance(allowance, Allowance) else Allowance(**allowance)
            for allowance in self.allowances
        ]
        self.markup = (
            self.markup if isinstance(self.markup, Markup) else Markup(**self.markup)
        )
        self.contingency = (
            self.contingency
            if isinstance(self.contingency, Contingency)
            else Contingency(**self.contingency)
        )
        if self.confidence_model is not None and not isinstance(
            self.confidence_model, EstimateConfidenceModel
        ):
            self.confidence_model = EstimateConfidenceModel(**self.confidence_model)

    def all_lines(self) -> list[EstimateLine]:
        return [line for package in self.packages for line in package.lines]

    def subtotal(self) -> Subtotal:
        line_total = sum(line.line_total() for line in self.all_lines())
        allowance_total = sum(item.amount for item in self.allowances)
        amount = round(line_total + self.freight_cost.amount + allowance_total, 2)
        return Subtotal(amount=amount)

    def markup_amount(self) -> float:
        return self.markup.amount_for(self.subtotal().amount)

    def contingency_amount(self) -> float:
        return self.contingency.amount_for(
            self.subtotal().amount + self.markup_amount()
        )

    def grand_total(self) -> GrandTotal:
        amount = round(
            self.subtotal().amount + self.markup_amount() + self.contingency_amount(),
            2,
        )
        return GrandTotal(amount=amount)

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimate_id": self.estimate_id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "packages": [package.to_dict() for package in self.packages],
            "freight_cost": self.freight_cost.to_dict(),
            "allowances": [allowance.to_dict() for allowance in self.allowances],
            "subtotal": self.subtotal().to_dict(),
            "markup": self.markup.to_dict(),
            "markup_amount": self.markup_amount(),
            "contingency": self.contingency.to_dict(),
            "contingency_amount": self.contingency_amount(),
            "grand_total": self.grand_total().to_dict(),
            "confidence_model": (
                self.confidence_model.to_dict()
                if self.confidence_model is not None
                else None
            ),
        }


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value.strip()


def _normalize_non_negative_float(field_name: str, value: float) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 2)
    if normalized < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return normalized


def _normalize_rate(field_name: str, value: float) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 4)
    if not 0 <= normalized <= 1:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return normalized

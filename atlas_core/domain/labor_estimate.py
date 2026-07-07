"""Labor estimate domain models for Atlas Core bid intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LaborEstimateSourceRef:
    source_type: str
    source_id: str
    field: str | None = None
    source_label: str | None = None
    excerpt: str | None = None

    def __post_init__(self) -> None:
        self.source_type = self._normalize_required_text(
            "source_type", self.source_type
        )
        self.source_id = self._normalize_required_text("source_id", self.source_id)
        self.field = self._normalize_optional_text(self.field)
        self.source_label = self._normalize_optional_text(self.source_label)
        self.excerpt = self._normalize_optional_text(self.excerpt)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "field": self.field,
            "source_label": self.source_label,
            "excerpt": self.excerpt,
        }

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


@dataclass
class LaborEstimateCategory:
    category_id: str
    category_name: str
    system_area: str
    quantity_basis: str
    hours_low: float
    hours_expected: float
    hours_high: float
    confidence: float
    calculation_method: str
    source_refs: list[LaborEstimateSourceRef] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.category_id = self._normalize_required_text(
            "category_id", self.category_id
        )
        self.category_name = self._normalize_required_text(
            "category_name", self.category_name
        )
        self.system_area = self._normalize_required_text(
            "system_area", self.system_area
        )
        self.quantity_basis = self._normalize_required_text(
            "quantity_basis", self.quantity_basis
        )
        self.calculation_method = self._normalize_required_text(
            "calculation_method", self.calculation_method
        )

        self.hours_low = self._normalize_non_negative_float("hours_low", self.hours_low)
        self.hours_expected = self._normalize_non_negative_float(
            "hours_expected", self.hours_expected
        )
        self.hours_high = self._normalize_non_negative_float(
            "hours_high", self.hours_high
        )

        if not (self.hours_low <= self.hours_expected <= self.hours_high):
            raise ValueError("hours must satisfy low <= expected <= high")

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.source_refs = [
            (
                source_ref
                if isinstance(source_ref, LaborEstimateSourceRef)
                else LaborEstimateSourceRef(**source_ref)
            )
            for source_ref in self.source_refs
        ]
        self.assumptions = [
            self._normalize_required_text("assumption", assumption)
            for assumption in self.assumptions
        ]
        self.risk_factors = [
            self._normalize_required_text("risk_factor", risk_factor)
            for risk_factor in self.risk_factors
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "category_id": self.category_id,
            "category_name": self.category_name,
            "system_area": self.system_area,
            "quantity_basis": self.quantity_basis,
            "hours_low": self.hours_low,
            "hours_expected": self.hours_expected,
            "hours_high": self.hours_high,
            "confidence": self.confidence,
            "calculation_method": self.calculation_method,
            "source_refs": [source_ref.to_dict() for source_ref in self.source_refs],
            "assumptions": list(self.assumptions),
            "risk_factors": list(self.risk_factors),
        }

    @staticmethod
    def _normalize_non_negative_float(field_name: str, value: float) -> float:
        if not isinstance(value, (int, float)):
            raise ValueError(f"{field_name} must be numeric")

        numeric_value = round(float(value), 2)
        if numeric_value < 0:
            raise ValueError(f"{field_name} cannot be negative")

        return numeric_value

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


@dataclass
class LaborEstimate:
    project_id: str
    total_labor_hours_low: float
    total_labor_hours_expected: float
    total_labor_hours_high: float
    labor_categories: list[LaborEstimateCategory] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    confidence: float = 0.75
    source_refs: list[LaborEstimateSourceRef] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_by_engine_version: str = "labor-estimation-engine/1.0.0"

    def __post_init__(self) -> None:
        self.project_id = self._normalize_required_text("project_id", self.project_id)
        self.created_by_engine_version = self._normalize_required_text(
            "created_by_engine_version", self.created_by_engine_version
        )

        self.total_labor_hours_low = self._normalize_non_negative_float(
            "total_labor_hours_low", self.total_labor_hours_low
        )
        self.total_labor_hours_expected = self._normalize_non_negative_float(
            "total_labor_hours_expected", self.total_labor_hours_expected
        )
        self.total_labor_hours_high = self._normalize_non_negative_float(
            "total_labor_hours_high", self.total_labor_hours_high
        )

        if not (
            self.total_labor_hours_low
            <= self.total_labor_hours_expected
            <= self.total_labor_hours_high
        ):
            raise ValueError("total labor hours must satisfy low <= expected <= high")

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.labor_categories = [
            (
                category
                if isinstance(category, LaborEstimateCategory)
                else LaborEstimateCategory(**category)
            )
            for category in self.labor_categories
        ]
        self.source_refs = [
            (
                source_ref
                if isinstance(source_ref, LaborEstimateSourceRef)
                else LaborEstimateSourceRef(**source_ref)
            )
            for source_ref in self.source_refs
        ]
        self.assumptions = [
            self._normalize_required_text("assumption", assumption)
            for assumption in self.assumptions
        ]
        self.exclusions = [
            self._normalize_required_text("exclusion", exclusion)
            for exclusion in self.exclusions
        ]
        self.warnings = [
            self._normalize_required_text("warning", warning)
            for warning in self.warnings
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "total_labor_hours_low": self.total_labor_hours_low,
            "total_labor_hours_expected": self.total_labor_hours_expected,
            "total_labor_hours_high": self.total_labor_hours_high,
            "labor_categories": [
                category.to_dict() for category in self.labor_categories
            ],
            "assumptions": list(self.assumptions),
            "exclusions": list(self.exclusions),
            "confidence": self.confidence,
            "source_refs": [source_ref.to_dict() for source_ref in self.source_refs],
            "warnings": list(self.warnings),
            "created_by_engine_version": self.created_by_engine_version,
        }

    @staticmethod
    def _normalize_non_negative_float(field_name: str, value: float) -> float:
        if not isinstance(value, (int, float)):
            raise ValueError(f"{field_name} must be numeric")

        numeric_value = round(float(value), 2)
        if numeric_value < 0:
            raise ValueError(f"{field_name} cannot be negative")

        return numeric_value

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

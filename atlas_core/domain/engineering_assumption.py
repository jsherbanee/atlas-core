"""Engineering assumption domain model for Atlas Core."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AssumptionSeverity(str, Enum):
    INFORMATIONAL = "informational"
    REVIEW = "review"
    RISK = "risk"


@dataclass
class EngineeringAssumption:
    assumption_id: str
    category: str
    description: str
    severity: AssumptionSeverity = AssumptionSeverity.REVIEW
    source: str = "atlas"
    related_sheet: str | None = None
    related_specification: str | None = None
    related_equipment: str | None = None
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.assumption_id = self._normalize_required_text(
            "assumption_id", self.assumption_id
        )
        self.category = self._normalize_required_text("category", self.category)
        self.description = self._normalize_required_text(
            "description", self.description
        )

        if not isinstance(self.severity, AssumptionSeverity):
            self.severity = AssumptionSeverity(self.severity)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.source = self._normalize_required_text("source", self.source)
        self.related_sheet = self._normalize_optional_text(self.related_sheet)
        self.related_specification = self._normalize_optional_text(
            self.related_specification
        )
        self.related_equipment = self._normalize_optional_text(self.related_equipment)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "category": self.category,
            "description": self.description,
            "severity": self.severity.value,
            "source": self.source,
            "related_sheet": self.related_sheet,
            "related_specification": self.related_specification,
            "related_equipment": self.related_equipment,
            "confidence": self.confidence,
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

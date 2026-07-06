"""RFI candidate domain model for Atlas Core."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RFIPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RFICandidate:
    rfi_id: str
    title: str
    question: str
    priority: RFIPriority = RFIPriority.MEDIUM
    category: str = "general"
    related_sheet: str | None = None
    related_specification: str | None = None
    related_equipment: str | None = None
    source: str = "atlas"
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.rfi_id = self._normalize_required_text("rfi_id", self.rfi_id)
        self.title = self._normalize_required_text("title", self.title)
        self.question = self._normalize_required_text("question", self.question)
        self.category = self._normalize_required_text("category", self.category)

        if not isinstance(self.priority, RFIPriority):
            self.priority = RFIPriority(self.priority)

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
            "rfi_id": self.rfi_id,
            "title": self.title,
            "question": self.question,
            "priority": self.priority.value,
            "category": self.category,
            "related_sheet": self.related_sheet,
            "related_specification": self.related_specification,
            "related_equipment": self.related_equipment,
            "source": self.source,
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

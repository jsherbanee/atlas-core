"""Keynote domain model for Atlas Core."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Keynote:
    keynote_id: str
    number: str
    description: str
    source_sheet_number: str | None = None
    equipment_category: str | None = None
    system_category: str | None = None
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.keynote_id = self._normalize_required_text("keynote_id", self.keynote_id)
        self.number = self._normalize_required_text("number", self.number)
        self.description = self._normalize_required_text(
            "description", self.description
        )

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.source_sheet_number = self._normalize_optional_text(
            self.source_sheet_number
        )
        self.equipment_category = self._normalize_optional_text(self.equipment_category)
        self.system_category = self._normalize_optional_text(self.system_category)
        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def to_dict(self) -> dict[str, Any]:
        return {
            "keynote_id": self.keynote_id,
            "number": self.number,
            "description": self.description,
            "source_sheet_number": self.source_sheet_number,
            "equipment_category": self.equipment_category,
            "system_category": self.system_category,
            "notes": list(self.notes),
            "confidence": self.confidence,
        }

    @classmethod
    def _normalize_note(cls, note: str) -> str:
        return cls._normalize_required_text("note", note)

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

"""Detail callout domain model for Atlas Core."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DetailCallout:
    callout_id: str
    detail_number: str
    source_sheet_number: str
    target_sheet_number: str | None = None
    description: str | None = None
    system_category: str | None = None
    equipment_category: str | None = None
    room_name: str | None = None
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.callout_id = self._normalize_required_text("callout_id", self.callout_id)
        self.detail_number = self._normalize_required_text(
            "detail_number", self.detail_number
        )
        self.source_sheet_number = self._normalize_required_text(
            "source_sheet_number", self.source_sheet_number
        )

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.target_sheet_number = self._normalize_optional_text(
            self.target_sheet_number
        )
        self.description = self._normalize_optional_text(self.description)
        self.system_category = self._normalize_optional_text(self.system_category)
        self.equipment_category = self._normalize_optional_text(self.equipment_category)
        self.room_name = self._normalize_optional_text(self.room_name)
        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def to_dict(self) -> dict[str, Any]:
        return {
            "callout_id": self.callout_id,
            "detail_number": self.detail_number,
            "source_sheet_number": self.source_sheet_number,
            "target_sheet_number": self.target_sheet_number,
            "description": self.description,
            "system_category": self.system_category,
            "equipment_category": self.equipment_category,
            "room_name": self.room_name,
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

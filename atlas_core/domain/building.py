"""Building domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BuildingType(str, Enum):
    """Building type for an Atlas project building."""

    PERFORMANCE = "performance"
    EDUCATION = "education"
    OFFICE = "office"
    HEALTHCARE = "healthcare"
    HOSPITALITY = "hospitality"
    MUSEUM = "museum"
    MIXED_USE = "mixed_use"
    SUPPORT = "support"
    UNKNOWN = "unknown"


@dataclass
class Building:
    building_id: str
    name: str
    project_id: str
    building_type: BuildingType = BuildingType.UNKNOWN
    address: str | None = None
    room_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.building_id = self._normalize_required_text(
            "building_id", self.building_id
        )
        self.name = self._normalize_required_text("name", self.name)
        self.project_id = self._normalize_required_text("project_id", self.project_id)

        if not isinstance(self.building_type, BuildingType):
            self.building_type = BuildingType(self.building_type)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.room_ids = [
            self._normalize_required_text("room_id", room_id)
            for room_id in self.room_ids
        ]
        self.notes = [
            self._normalize_required_text("note", note)
            for note in self.notes
        ]

    def add_room(self, room_id: str) -> None:
        self.room_ids.append(self._normalize_required_text("room_id", room_id))

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_required_text("note", note))

    def to_dict(self) -> dict[str, Any]:
        return {
            "building_id": self.building_id,
            "name": self.name,
            "project_id": self.project_id,
            "building_type": self.building_type.value,
            "address": self.address,
            "room_ids": list(self.room_ids),
            "notes": list(self.notes),
            "confidence": self.confidence,
        }

    @staticmethod
    def _validate_required_text(field_name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

    @classmethod
    def _normalize_required_text(cls, field_name: str, value: str) -> str:
        cls._validate_required_text(field_name, value)
        return value.strip()

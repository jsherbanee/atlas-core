"""Room domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RoomType(str, Enum):
    """Room type for an Atlas building room."""

    PERFORMANCE = "performance"
    CLASSROOM = "classroom"
    CONFERENCE = "conference"
    LOBBY = "lobby"
    CONTROL_ROOM = "control_room"
    BOOTH = "booth"
    EQUIPMENT_ROOM = "equipment_room"
    REHEARSAL = "rehearsal"
    STUDIO = "studio"
    OFFICE = "office"
    SUPPORT = "support"
    CIRCULATION = "circulation"
    OUTDOOR = "outdoor"
    UNKNOWN = "unknown"


@dataclass
class Room:
    room_id: str
    name: str
    building_id: str
    room_number: str | None = None
    room_type: RoomType = RoomType.UNKNOWN
    space_ids: list[str] = field(default_factory=list)
    system_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.room_id = self._normalize_required_text("room_id", self.room_id)
        self.name = self._normalize_required_text("name", self.name)
        self.building_id = self._normalize_required_text(
            "building_id", self.building_id
        )

        if not isinstance(self.room_type, RoomType):
            self.room_type = RoomType(self.room_type)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.space_ids = [
            self._normalize_required_text("space_id", space_id)
            for space_id in self.space_ids
        ]
        self.system_ids = [
            self._normalize_required_text("system_id", system_id)
            for system_id in self.system_ids
        ]
        self.notes = [
            self._normalize_required_text("note", note)
            for note in self.notes
        ]

    def add_space(self, space_id: str) -> None:
        self.space_ids.append(self._normalize_required_text("space_id", space_id))

    def add_system(self, system_id: str) -> None:
        self.system_ids.append(self._normalize_required_text("system_id", system_id))

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_required_text("note", note))

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "name": self.name,
            "building_id": self.building_id,
            "room_number": self.room_number,
            "room_type": self.room_type.value,
            "space_ids": list(self.space_ids),
            "system_ids": list(self.system_ids),
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

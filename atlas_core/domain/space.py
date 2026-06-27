"""Space domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpaceType(str, Enum):
    """Space type for an Atlas room space."""

    STAGE = "stage"
    AUDIENCE = "audience"
    FRONT_OF_HOUSE = "front_of_house"
    BACK_OF_HOUSE = "back_of_house"
    CONTROL_POSITION = "control_position"
    RACK_LOCATION = "rack_location"
    CEILING = "ceiling"
    WALL = "wall"
    FLOOR = "floor"
    CATWALK = "catwalk"
    BOOTH = "booth"
    LECTERN = "lectern"
    DISPLAY_WALL = "display_wall"
    EQUIPMENT_LOCATION = "equipment_location"
    OUTDOOR = "outdoor"
    UNKNOWN = "unknown"


@dataclass
class Space:
    space_id: str
    name: str
    room_id: str
    space_type: SpaceType = SpaceType.UNKNOWN
    scene_ids: list[str] = field(default_factory=list)
    equipment_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.space_id = self._normalize_required_text("space_id", self.space_id)
        self.name = self._normalize_required_text("name", self.name)
        self.room_id = self._normalize_required_text("room_id", self.room_id)

        if not isinstance(self.space_type, SpaceType):
            self.space_type = SpaceType(self.space_type)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.scene_ids = [
            self._normalize_required_text("scene_id", scene_id)
            for scene_id in self.scene_ids
        ]
        self.equipment_ids = [
            self._normalize_required_text("equipment_id", equipment_id)
            for equipment_id in self.equipment_ids
        ]
        self.notes = [
            self._normalize_required_text("note", note)
            for note in self.notes
        ]

    def add_scene(self, scene_id: str) -> None:
        self.scene_ids.append(self._normalize_required_text("scene_id", scene_id))

    def add_equipment(self, equipment_id: str) -> None:
        self.equipment_ids.append(
            self._normalize_required_text("equipment_id", equipment_id)
        )

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_required_text("note", note))

    def to_dict(self) -> dict[str, Any]:
        return {
            "space_id": self.space_id,
            "name": self.name,
            "room_id": self.room_id,
            "space_type": self.space_type.value,
            "scene_ids": list(self.scene_ids),
            "equipment_ids": list(self.equipment_ids),
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

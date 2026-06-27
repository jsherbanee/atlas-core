"""Scene domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SceneType(str, Enum):
    """Scene type for an Atlas space."""

    LECTURE = "lecture"
    PRESENTATION = "presentation"
    PERFORMANCE = "performance"
    REHEARSAL = "rehearsal"
    FILM_SCREENING = "film_screening"
    HOUSE_MUSIC = "house_music"
    PRODUCTION = "production"
    RECORDING = "recording"
    BROADCAST = "broadcast"
    MEETING = "meeting"
    TRAINING = "training"
    MAINTENANCE = "maintenance"
    DEFAULT = "default"
    UNKNOWN = "unknown"


@dataclass
class Scene:
    scene_id: str
    name: str
    space_id: str
    scene_type: SceneType = SceneType.UNKNOWN
    system_ids: list[str] = field(default_factory=list)
    equipment_ids: list[str] = field(default_factory=list)
    control_notes: list[str] = field(default_factory=list)
    commissioning_notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.scene_id = self._normalize_required_text("scene_id", self.scene_id)
        self.name = self._normalize_required_text("name", self.name)
        self.space_id = self._normalize_required_text("space_id", self.space_id)

        if not isinstance(self.scene_type, SceneType):
            self.scene_type = SceneType(self.scene_type)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.system_ids = [
            self._normalize_required_text("system_id", system_id)
            for system_id in self.system_ids
        ]
        self.equipment_ids = [
            self._normalize_required_text("equipment_id", equipment_id)
            for equipment_id in self.equipment_ids
        ]
        self.control_notes = [
            self._normalize_required_text("control_note", note)
            for note in self.control_notes
        ]
        self.commissioning_notes = [
            self._normalize_required_text("commissioning_note", note)
            for note in self.commissioning_notes
        ]

    def add_system(self, system_id: str) -> None:
        self.system_ids.append(self._normalize_required_text("system_id", system_id))

    def add_equipment(self, equipment_id: str) -> None:
        self.equipment_ids.append(
            self._normalize_required_text("equipment_id", equipment_id)
        )

    def add_control_note(self, note: str) -> None:
        self.control_notes.append(self._normalize_required_text("control_note", note))

    def add_commissioning_note(self, note: str) -> None:
        self.commissioning_notes.append(
            self._normalize_required_text("commissioning_note", note)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "space_id": self.space_id,
            "scene_type": self.scene_type.value,
            "system_ids": list(self.system_ids),
            "equipment_ids": list(self.equipment_ids),
            "control_notes": list(self.control_notes),
            "commissioning_notes": list(self.commissioning_notes),
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

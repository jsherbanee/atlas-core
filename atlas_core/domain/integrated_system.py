"""Integrated system domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SystemCategory(str, Enum):
    """System category for an integrated Atlas scope item."""

    AUDIO = "audio"
    VIDEO = "video"
    CONTROL = "control"
    LIGHTING = "lighting"
    INTERCOM = "intercom"
    ASSISTED_LISTENING = "assisted_listening"
    PROJECTION = "projection"
    DISPLAY = "display"
    DRAPERY = "drapery"
    INFRASTRUCTURE = "infrastructure"
    NETWORKING = "networking"
    UNKNOWN = "unknown"


class SystemComplexity(str, Enum):
    """Complexity level for an integrated Atlas system."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class IntegratedSystem:
    system_id: str
    name: str
    category: SystemCategory
    room_id: str | None = None
    building_id: str | None = None
    description: str | None = None
    complexity: SystemComplexity = SystemComplexity.MEDIUM
    manufacturers: list[str] = field(default_factory=list)
    equipment_ids: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    review_required: bool = False
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.system_id = self._normalize_required_text("system_id", self.system_id)
        self.name = self._normalize_required_text("name", self.name)

        if not isinstance(self.category, SystemCategory):
            self.category = SystemCategory(self.category)

        if not isinstance(self.complexity, SystemComplexity):
            self.complexity = SystemComplexity(self.complexity)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.manufacturers = [
            self._normalize_required_text("manufacturer", manufacturer)
            for manufacturer in self.manufacturers
        ]
        self.equipment_ids = [
            self._normalize_required_text("equipment_id", equipment_id)
            for equipment_id in self.equipment_ids
        ]
        self.assumptions = [
            self._normalize_required_text("assumption", assumption)
            for assumption in self.assumptions
        ]

    def add_manufacturer(self, manufacturer: str) -> None:
        self.manufacturers.append(
            self._normalize_required_text("manufacturer", manufacturer)
        )

    def add_equipment(self, equipment_id: str) -> None:
        self.equipment_ids.append(
            self._normalize_required_text("equipment_id", equipment_id)
        )

    def add_assumption(self, assumption: str) -> None:
        self.assumptions.append(
            self._normalize_required_text("assumption", assumption)
        )

    def mark_for_review(self, reason: str | None = None) -> None:
        self.review_required = True

        if reason is not None:
            self.add_assumption(reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_id": self.system_id,
            "name": self.name,
            "category": self.category.value,
            "room_id": self.room_id,
            "building_id": self.building_id,
            "description": self.description,
            "complexity": self.complexity.value,
            "manufacturers": list(self.manufacturers),
            "equipment_ids": list(self.equipment_ids),
            "assumptions": list(self.assumptions),
            "review_required": self.review_required,
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

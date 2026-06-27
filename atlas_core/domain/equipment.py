"""Equipment domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EquipmentStatus(str, Enum):
    """Lifecycle status for an Atlas equipment item."""

    DETECTED = "detected"
    PLACEHOLDER = "placeholder"
    PRICED = "priced"
    APPROVED = "approved"
    ORDERED = "ordered"
    RECEIVED = "received"
    INSTALLED = "installed"
    COMMISSIONED = "commissioned"
    EXCLUDED = "excluded"


class EquipmentCategory(str, Enum):
    """Equipment category for an Atlas equipment item."""

    SPEAKER = "speaker"
    AMPLIFIER = "amplifier"
    DSP = "dsp"
    CONTROL_PROCESSOR = "control_processor"
    DISPLAY = "display"
    PROJECTOR = "projector"
    PROJECTION_SCREEN = "projection_screen"
    MICROPHONE = "microphone"
    CAMERA = "camera"
    LIGHTING_FIXTURE = "lighting_fixture"
    LIGHTING_CONSOLE = "lighting_console"
    INTERCOM = "intercom"
    ASSISTED_LISTENING = "assisted_listening"
    NETWORK = "network"
    RACK = "rack"
    CABLE = "cable"
    MOUNT = "mount"
    DRAPERY = "drapery"
    INFRASTRUCTURE = "infrastructure"
    ACCESSORY = "accessory"
    UNKNOWN = "unknown"


@dataclass
class Equipment:
    equipment_id: str
    description: str
    category: EquipmentCategory
    quantity: float = 1
    manufacturer: str | None = None
    model: str | None = None
    system_id: str | None = None
    room_id: str | None = None
    building_id: str | None = None
    status: EquipmentStatus = EquipmentStatus.DETECTED
    budget_cost: float | None = None
    sell_price: float | None = None
    labor_template: str | None = None
    drawing_reference: str | None = None
    specification_reference: str | None = None
    confidence: float = 0.75
    assumptions: list[str] = field(default_factory=list)
    review_required: bool = False

    def __post_init__(self) -> None:
        self.equipment_id = self._normalize_required_text(
            "equipment_id", self.equipment_id
        )
        self.description = self._normalize_required_text(
            "description", self.description
        )

        if not isinstance(self.category, EquipmentCategory):
            self.category = EquipmentCategory(self.category)

        if not isinstance(self.status, EquipmentStatus):
            self.status = EquipmentStatus(self.status)

        if not isinstance(self.quantity, (int, float)) or self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self._validate_non_negative_price("budget_cost", self.budget_cost)
        self._validate_non_negative_price("sell_price", self.sell_price)

        self.assumptions = [
            self._normalize_required_text("assumption", assumption)
            for assumption in self.assumptions
        ]

    def set_pricing(self, budget_cost: float, sell_price: float | None = None) -> None:
        self._validate_non_negative_price("budget_cost", budget_cost)
        self._validate_non_negative_price("sell_price", sell_price)

        self.budget_cost = budget_cost
        self.sell_price = sell_price if sell_price is not None else budget_cost
        self.status = EquipmentStatus.PRICED

    def add_assumption(self, assumption: str) -> None:
        self.assumptions.append(
            self._normalize_required_text("assumption", assumption)
        )

    def mark_placeholder(self, reason: str | None = None) -> None:
        self.status = EquipmentStatus.PLACEHOLDER

        if reason is not None:
            self.add_assumption(reason)

    def mark_for_review(self, reason: str | None = None) -> None:
        self.review_required = True

        if reason is not None:
            self.add_assumption(reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "equipment_id": self.equipment_id,
            "description": self.description,
            "category": self.category.value,
            "quantity": self.quantity,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "system_id": self.system_id,
            "room_id": self.room_id,
            "building_id": self.building_id,
            "status": self.status.value,
            "budget_cost": self.budget_cost,
            "sell_price": self.sell_price,
            "labor_template": self.labor_template,
            "drawing_reference": self.drawing_reference,
            "specification_reference": self.specification_reference,
            "confidence": self.confidence,
            "assumptions": list(self.assumptions),
            "review_required": self.review_required,
        }

    @staticmethod
    def _validate_required_text(field_name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

    @classmethod
    def _normalize_required_text(cls, field_name: str, value: str) -> str:
        cls._validate_required_text(field_name, value)
        return value.strip()

    @staticmethod
    def _validate_non_negative_price(
        field_name: str, value: float | None
    ) -> None:
        if value is None:
            return

        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{field_name} cannot be negative")

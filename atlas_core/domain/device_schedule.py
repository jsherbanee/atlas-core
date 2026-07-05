"""Device schedule domain models for Atlas Core."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeviceScheduleItem:
    item_id: str
    tag: str
    description: str
    quantity: float = 1
    manufacturer: str | None = None
    model: str | None = None
    room_name: str | None = None
    system_name: str | None = None
    drawing_reference: str | None = None
    specification_reference: str | None = None
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.item_id = self._normalize_required_text("item_id", self.item_id)
        self.tag = self._normalize_required_text("tag", self.tag)
        self.description = self._normalize_required_text(
            "description", self.description
        )

        if not isinstance(self.quantity, (int, float)) or self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.manufacturer = self._normalize_optional_text(self.manufacturer)
        self.model = self._normalize_optional_text(self.model)
        self.room_name = self._normalize_optional_text(self.room_name)
        self.system_name = self._normalize_optional_text(self.system_name)
        self.drawing_reference = self._normalize_optional_text(self.drawing_reference)
        self.specification_reference = self._normalize_optional_text(
            self.specification_reference
        )

        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "tag": self.tag,
            "description": self.description,
            "quantity": self.quantity,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "room_name": self.room_name,
            "system_name": self.system_name,
            "drawing_reference": self.drawing_reference,
            "specification_reference": self.specification_reference,
            "notes": list(self.notes),
            "confidence": self.confidence,
        }

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @classmethod
    def _normalize_note(cls, note: str) -> str:
        return cls._normalize_required_text("note", note)

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


@dataclass
class DeviceSchedule:
    schedule_id: str
    source_sheet_number: str | None = None
    title: str = "Device Schedule"
    items: list[DeviceScheduleItem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.schedule_id = self._normalize_required_text(
            "schedule_id", self.schedule_id
        )
        self.title = self._normalize_required_text("title", self.title)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.source_sheet_number = self._normalize_optional_text(
            self.source_sheet_number
        )
        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_item(self, item: DeviceScheduleItem) -> None:
        self.items.append(item)

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def item_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "source_sheet_number": self.source_sheet_number,
            "title": self.title,
            "items": [item.to_dict() for item in self.items],
            "notes": list(self.notes),
            "confidence": self.confidence,
        }

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @classmethod
    def _normalize_note(cls, note: str) -> str:
        return cls._normalize_required_text("note", note)

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

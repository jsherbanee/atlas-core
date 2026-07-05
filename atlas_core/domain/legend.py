"""Legend domain models for Atlas Core."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LegendItem:
    legend_item_id: str
    symbol: str
    description: str
    equipment_category: str | None = None
    system_category: str | None = None
    source_sheet_number: str | None = None
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.legend_item_id = self._normalize_required_text(
            "legend_item_id", self.legend_item_id
        )
        self.symbol = self._normalize_required_text("symbol", self.symbol)
        self.description = self._normalize_required_text(
            "description", self.description
        )

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.equipment_category = self._normalize_optional_text(self.equipment_category)
        self.system_category = self._normalize_optional_text(self.system_category)
        self.source_sheet_number = self._normalize_optional_text(
            self.source_sheet_number
        )
        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def to_dict(self) -> dict[str, Any]:
        return {
            "legend_item_id": self.legend_item_id,
            "symbol": self.symbol,
            "description": self.description,
            "equipment_category": self.equipment_category,
            "system_category": self.system_category,
            "source_sheet_number": self.source_sheet_number,
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


@dataclass
class Legend:
    legend_id: str
    title: str = "Legend"
    source_sheet_number: str | None = None
    items: list[LegendItem] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.legend_id = self._normalize_required_text("legend_id", self.legend_id)
        self.title = self._normalize_required_text("title", self.title)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.source_sheet_number = self._normalize_optional_text(
            self.source_sheet_number
        )

    def add_item(self, item: LegendItem) -> None:
        self.items.append(item)

    def item_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "legend_id": self.legend_id,
            "title": self.title,
            "source_sheet_number": self.source_sheet_number,
            "items": [item.to_dict() for item in self.items],
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

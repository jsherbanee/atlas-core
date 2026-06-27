"""Bid package review domain model for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from atlas_core.domain import (
    DrawingSheet,
    Equipment,
    IntegratedSystem,
    SpecificationSection,
)
from atlas_core.rules import Resolution

if TYPE_CHECKING:
    from atlas_core.services import ManufacturerReviewIssue, ReviewReportItem
    from atlas_core.services.cross_reference_service import CrossReference


@dataclass
class BidPackageReview:
    review_id: str
    project_id: str
    name: str
    drawing_sheets: list[DrawingSheet] = field(default_factory=list)
    specification_sections: list[SpecificationSection] = field(default_factory=list)
    systems: list[IntegratedSystem] = field(default_factory=list)
    equipment: list[Equipment] = field(default_factory=list)
    resolutions: list[Resolution] = field(default_factory=list)
    manufacturer_review_issues: list[ManufacturerReviewIssue] = field(
        default_factory=list
    )
    review_report: list[ReviewReportItem] = field(default_factory=list)
    cross_references: list[CrossReference] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.review_id = self._normalize_required_text("review_id", self.review_id)
        self.project_id = self._normalize_required_text("project_id", self.project_id)
        self.name = self._normalize_required_text("name", self.name)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def drawing_count(self) -> int:
        return len(self.drawing_sheets)

    def specification_count(self) -> int:
        return len(self.specification_sections)

    def equipment_count(self) -> int:
        return len(self.equipment)

    def cross_reference_count(self) -> int:
        return len(self.cross_references)

    def issue_count(self) -> int:
        return (
            len(self.resolutions)
            + len(self.manufacturer_review_issues)
            + len(self.review_report)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "project_id": self.project_id,
            "name": self.name,
            "drawing_sheets": self._serialize_items(self.drawing_sheets),
            "specification_sections": self._serialize_items(
                self.specification_sections
            ),
            "systems": self._serialize_items(self.systems),
            "equipment": self._serialize_items(self.equipment),
            "resolutions": self._serialize_items(self.resolutions),
            "manufacturer_review_issues": self._serialize_items(
                self.manufacturer_review_issues
            ),
            "review_report": self._serialize_items(self.review_report),
            "cross_references": self._serialize_items(self.cross_references),
            "notes": list(self.notes),
            "confidence": self.confidence,
        }

    @classmethod
    def _serialize_items(cls, items: list[Any]) -> list[Any]:
        return [cls._serialize_item(item) for item in items]

    @classmethod
    def _serialize_item(cls, item: Any) -> Any:
        if hasattr(item, "to_dict"):
            return item.to_dict()

        if hasattr(item, "__dict__"):
            return {
                key: cls._serialize_value(value)
                for key, value in item.__dict__.items()
            }

        return item

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value

        return value

    @classmethod
    def _normalize_note(cls, note: str) -> str:
        return cls._normalize_required_text("note", note)

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

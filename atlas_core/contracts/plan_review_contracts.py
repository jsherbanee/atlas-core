"""Plan review request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlas_core.services import PlanReviewWorkflowResult


@dataclass
class PlanReviewRequest:
    review_id: str
    project_id: str
    name: str
    raw_pages: list[dict] = field(default_factory=list)
    document_sections: list[dict] = field(default_factory=list)
    document_section_summary: dict | None = None
    raw_sheets: list[dict] = field(default_factory=list)
    raw_sections: list[dict] = field(default_factory=list)
    raw_device_schedules: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.review_id = self._normalize_required_text("review_id", self.review_id)
        self.project_id = self._normalize_required_text("project_id", self.project_id)
        self.name = self._normalize_required_text("name", self.name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "project_id": self.project_id,
            "name": self.name,
            "raw_pages": list(self.raw_pages),
            "document_sections": list(self.document_sections),
            "document_section_summary": self.document_section_summary,
            "raw_sheets": list(self.raw_sheets),
            "raw_sections": list(self.raw_sections),
            "raw_device_schedules": list(self.raw_device_schedules),
        }

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


@dataclass
class PlanReviewResponse:
    result: PlanReviewWorkflowResult

    def to_dict(self) -> dict[str, Any]:
        return {"result": self.result.to_dict()}

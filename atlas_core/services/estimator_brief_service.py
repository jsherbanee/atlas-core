"""Estimator brief helpers for Atlas Core services."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview


@dataclass
class EstimatorBrief:
    review_id: str
    project_id: str
    name: str
    drawing_count: int
    specification_count: int
    system_count: int
    equipment_count: int
    issue_count: int
    placeholder_count: int
    review_required_count: int
    cross_reference_count: int
    scope_gap_count: int
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EstimatorBriefService:
    def build_brief(self, review: BidPackageReview) -> EstimatorBrief:
        return EstimatorBrief(
            review_id=review.review_id,
            project_id=review.project_id,
            name=review.name,
            drawing_count=review.drawing_count(),
            specification_count=review.specification_count(),
            system_count=len(review.systems),
            equipment_count=review.equipment_count(),
            issue_count=review.issue_count(),
            placeholder_count=self._placeholder_count(review),
            review_required_count=self._review_required_count(review),
            cross_reference_count=review.cross_reference_count(),
            scope_gap_count=review.scope_gap_count(),
            confidence=review.confidence,
        )

    @classmethod
    def _placeholder_count(cls, review: BidPackageReview) -> int:
        return sum(
            1
            for equipment in review.equipment
            if cls._value(getattr(equipment, "status", None)) == "placeholder"
        )

    @classmethod
    def _review_required_count(cls, review: BidPackageReview) -> int:
        equipment_count = sum(
            1
            for equipment in review.equipment
            if getattr(equipment, "review_required", False) is True
        )
        return equipment_count + len(review.review_report)

    @staticmethod
    def _value(value: Any) -> Any:
        return getattr(value, "value", value)

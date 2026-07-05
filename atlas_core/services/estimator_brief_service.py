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
    room_count: int
    issue_count: int
    placeholder_count: int
    review_required_count: int
    cross_reference_count: int
    reconciliation_issue_count: int
    scope_gap_count: int
    estimator_risk_count: int
    keynote_count: int
    legend_count: int
    legend_item_count: int
    confidence: float
    bid_completeness_score: float | None = None
    bid_completeness_status: str | None = None
    readiness_status: str | None = None
    readiness_message: str | None = None
    recommendation_count: int = 0

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
            room_count=review.room_count(),
            issue_count=review.issue_count(),
            placeholder_count=self._placeholder_count(review),
            review_required_count=self._review_required_count(review),
            cross_reference_count=review.cross_reference_count(),
            reconciliation_issue_count=review.reconciliation_issue_count(),
            scope_gap_count=review.scope_gap_count(),
            estimator_risk_count=review.estimator_risk_count(),
            keynote_count=review.keynote_count(),
            legend_count=review.legend_count(),
            legend_item_count=review.legend_item_count(),
            recommendation_count=review.recommendation_count(),
            confidence=review.confidence,
            bid_completeness_score=self._bid_completeness_score(review),
            bid_completeness_status=self._bid_completeness_status(review),
            readiness_status=self._readiness_status(review),
            readiness_message=self._readiness_message(review),
        )

    @classmethod
    def _bid_completeness_score(cls, review: BidPackageReview) -> float | None:
        bid_completeness = getattr(review, "bid_completeness", None)
        if bid_completeness is None:
            return None

        return float(bid_completeness.score)

    @classmethod
    def _bid_completeness_status(cls, review: BidPackageReview) -> str | None:
        bid_completeness = getattr(review, "bid_completeness", None)
        if bid_completeness is None:
            return None

        return str(getattr(bid_completeness.status, "value", bid_completeness.status))

    @classmethod
    def _readiness_status(cls, review: BidPackageReview) -> str | None:
        readiness = getattr(review, "readiness", None)
        if readiness is None:
            return None

        return str(getattr(readiness.status, "value", readiness.status))

    @classmethod
    def _readiness_message(cls, review: BidPackageReview) -> str | None:
        readiness = getattr(review, "readiness", None)
        if readiness is None:
            return None

        return str(readiness.message)

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

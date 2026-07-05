"""Final estimator review helpers for Atlas Core services."""

from dataclasses import asdict, dataclass, field
from typing import Any

from atlas_core.domain import BidPackageReview


@dataclass
class FinalEstimatorReview:
    review_id: str
    project_id: str
    name: str
    readiness_status: str | None = None
    readiness_message: str | None = None
    completeness_status: str | None = None
    completeness_score: float | None = None
    confidence: float = 0.75
    total_issues: int = 0
    total_recommendations: int = 0
    executive_summary: str = ""
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FinalEstimatorReviewService:
    def build(self, review: BidPackageReview) -> FinalEstimatorReview:
        readiness = getattr(review, "readiness", None)
        bid_completeness = getattr(review, "bid_completeness", None)

        readiness_status = self._value(getattr(readiness, "status", None))
        readiness_message = getattr(readiness, "message", None)
        completeness_status = self._value(getattr(bid_completeness, "status", None))
        completeness_score = self._float_or_none(
            getattr(bid_completeness, "score", None)
        )

        return FinalEstimatorReview(
            review_id=review.review_id,
            project_id=review.project_id,
            name=review.name,
            readiness_status=readiness_status,
            readiness_message=readiness_message,
            completeness_status=completeness_status,
            completeness_score=completeness_score,
            confidence=review.confidence,
            total_issues=review.issue_count(),
            total_recommendations=review.recommendation_count(),
            executive_summary=self._executive_summary(readiness_status),
            next_actions=self._next_actions(review),
        )

    @classmethod
    def _executive_summary(cls, readiness_status: str | None) -> str:
        if readiness_status == "ready":
            return "Bid package appears ready for pricing."
        if readiness_status == "needs_review":
            return "Bid package requires estimator review before pricing."
        if readiness_status == "not_ready":
            return "Bid package is not ready for pricing."

        return "Bid package review summary is available."

    @classmethod
    def _next_actions(cls, review: BidPackageReview) -> list[str]:
        actions: list[str] = []
        emitted: set[str] = set()

        readiness = getattr(review, "readiness", None)
        for blocker in getattr(readiness, "blockers", []):
            cls._add_action(actions, emitted, blocker)
        for warning in getattr(readiness, "warnings", []):
            cls._add_action(actions, emitted, warning)

        for recommendation in review.recommendations:
            cls._add_action(actions, emitted, recommendation.message)

        for scope_gap in review.scope_gaps:
            if cls._value(getattr(scope_gap, "severity", None)) != "high":
                continue
            cls._add_action(actions, emitted, scope_gap.suggested_action)

        if not actions:
            return ["Proceed with pricing review."]

        return actions

    @staticmethod
    def _add_action(actions: list[str], emitted: set[str], action: str | None) -> None:
        if not isinstance(action, str):
            return

        normalized = action.strip()
        if not normalized or normalized in emitted:
            return

        emitted.add(normalized)
        actions.append(normalized)

    @staticmethod
    def _value(value: Any) -> Any:
        return getattr(value, "value", value)

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None

        return float(value)

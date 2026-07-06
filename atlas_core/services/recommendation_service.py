"""Recommendation helpers for Atlas Core plan review."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from atlas_core.domain import BidPackageReview
from atlas_core.utils.refactoring import enum_value


class RecommendationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Recommendation:
    recommendation_id: str
    message: str
    priority: RecommendationPriority | str = RecommendationPriority.MEDIUM
    category: str = "general"
    target_id: str | None = None

    def __post_init__(self) -> None:
        self.recommendation_id = self._normalize_required_text(
            "recommendation_id",
            self.recommendation_id,
        )
        self.message = self._normalize_required_text("message", self.message)

        if not isinstance(self.priority, RecommendationPriority):
            self.priority = RecommendationPriority(self.priority)

        self.category = self.category.strip()
        self.target_id = self._normalize_optional_text(self.target_id)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["priority"] = enum_value(self.priority)
        return data

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            return None

        normalized = value.strip()
        return normalized or None


class RecommendationService:
    def build_recommendations(
        self,
        review: BidPackageReview,
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        emitted: set[str] = set()

        for gap in review.scope_gaps:
            if self._value(gap.severity) != "high":
                continue

            self._add_recommendation(
                recommendations,
                emitted,
                Recommendation(
                    recommendation_id=f"scope-gap-{gap.gap_id}-{gap.target_id}",
                    message=gap.suggested_action or gap.message,
                    priority=RecommendationPriority.HIGH,
                    category="scope_gap",
                    target_id=gap.target_id,
                ),
            )

        if review.estimator_risks:
            self._add_recommendation(
                recommendations,
                emitted,
                Recommendation(
                    recommendation_id="review-estimator-risks",
                    message=(
                        "Review estimator risks before pricing or submitting bid."
                    ),
                    priority=RecommendationPriority.MEDIUM,
                    category="risk",
                ),
            )

        if review.manufacturer_review_issues:
            self._add_recommendation(
                recommendations,
                emitted,
                Recommendation(
                    recommendation_id="confirm-manufacturers",
                    message=(
                        "Confirm unknown or review-required manufacturers before "
                        "pricing."
                    ),
                    priority=RecommendationPriority.MEDIUM,
                    category="manufacturer",
                ),
            )

        detail_callouts = list(getattr(review, "detail_callouts", []))

        if any(
            self._value(getattr(callout, "equipment_category", None)) == "mount"
            for callout in detail_callouts
        ):
            self._add_recommendation(
                recommendations,
                emitted,
                Recommendation(
                    recommendation_id="review-mounting-details",
                    message=(
                        "Review mounting details and include allowance for "
                        "backing, structure, anchors, power coordination, and "
                        "field conditions."
                    ),
                    priority=RecommendationPriority.MEDIUM,
                    category="mounting",
                ),
            )

        if any(
            self._value(getattr(callout, "equipment_category", None)) == "rack"
            for callout in detail_callouts
        ):
            self._add_recommendation(
                recommendations,
                emitted,
                Recommendation(
                    recommendation_id="review-rack-details",
                    message=(
                        "Review rack details for rack size, ventilation, power, "
                        "cable pathway, and service access."
                    ),
                    priority=RecommendationPriority.MEDIUM,
                    category="rack",
                ),
            )

        if any(
            self._value(getattr(callout, "system_category", None)) == "infrastructure"
            for callout in detail_callouts
        ):
            self._add_recommendation(
                recommendations,
                emitted,
                Recommendation(
                    recommendation_id="review-infrastructure-details",
                    message=(
                        "Review infrastructure details for conduit, backing, "
                        "power, structural support, and scope responsibility."
                    ),
                    priority=RecommendationPriority.MEDIUM,
                    category="infrastructure",
                ),
            )

        if review.confidence < 0.75:
            self._add_recommendation(
                recommendations,
                emitted,
                Recommendation(
                    recommendation_id="review-low-confidence",
                    message=(
                        "Review confidence is below target threshold; estimator "
                        "review is required."
                    ),
                    priority=RecommendationPriority.HIGH,
                    category="confidence",
                ),
            )

        if not review.drawing_sheets:
            self._add_recommendation(
                recommendations,
                emitted,
                Recommendation(
                    recommendation_id="missing-drawing-index",
                    message=(
                        "No drawing index is available. Upload or extract drawing "
                        "sheets before pricing."
                    ),
                    priority=RecommendationPriority.HIGH,
                    category="drawings",
                ),
            )

        if not review.specification_sections:
            self._add_recommendation(
                recommendations,
                emitted,
                Recommendation(
                    recommendation_id="missing-specification-index",
                    message=(
                        "No specification index is available. Upload or extract "
                        "specifications before pricing."
                    ),
                    priority=RecommendationPriority.HIGH,
                    category="specifications",
                ),
            )

        engineering_assumptions = list(
            getattr(review, "engineering_assumptions", []) or []
        )
        high_risk_assumptions = [
            assumption
            for assumption in engineering_assumptions
            if self._value(getattr(assumption, "severity", None)) == "risk"
        ]
        if (
            high_risk_assumptions
            and not review.scope_gaps
            and not review.estimator_risks
        ):
            self._add_recommendation(
                recommendations,
                emitted,
                Recommendation(
                    recommendation_id="review-engineering-assumptions",
                    message=(
                        "Review high-risk engineering assumptions before pricing "
                        "or submitting bid."
                    ),
                    priority=RecommendationPriority.HIGH,
                    category="engineering_assumptions",
                ),
            )

        return recommendations

    @staticmethod
    def _add_recommendation(
        recommendations: list[Recommendation],
        emitted: set[str],
        recommendation: Recommendation,
    ) -> None:
        if recommendation.recommendation_id in emitted:
            return

        emitted.add(recommendation.recommendation_id)
        recommendations.append(recommendation)

    @staticmethod
    def _value(value: Any) -> Any:
        return enum_value(value)

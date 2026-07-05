"""Plan review readiness assessment for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from atlas_core.domain import BidPackageReview


class ReadinessStatus(str, Enum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    NOT_READY = "not_ready"


@dataclass
class PlanReviewReadiness:
    status: ReadinessStatus
    message: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.status, ReadinessStatus):
            self.status = ReadinessStatus(self.status)

        self.message = self._normalize_required_text("message", self.message)
        self.blockers = [
            self._normalize_required_text("blocker", blocker)
            for blocker in self.blockers
        ]
        self.warnings = [
            self._normalize_required_text("warning", warning)
            for warning in self.warnings
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


class PlanReviewReadinessService:
    READY_MESSAGE = "Plan review is ready for pricing."
    NEEDS_REVIEW_MESSAGE = "Plan review needs estimator review before pricing."
    NOT_READY_MESSAGE = "Plan review is not ready for pricing."

    def assess(self, readiness_review: BidPackageReview) -> PlanReviewReadiness:
        blockers = self._blockers(readiness_review)
        warnings = self._warnings(readiness_review)

        if blockers:
            return PlanReviewReadiness(
                status=ReadinessStatus.NOT_READY,
                message=self.NOT_READY_MESSAGE,
                blockers=blockers,
                warnings=warnings,
            )

        if warnings:
            return PlanReviewReadiness(
                status=ReadinessStatus.NEEDS_REVIEW,
                message=self.NEEDS_REVIEW_MESSAGE,
                warnings=warnings,
            )

        return PlanReviewReadiness(
            status=ReadinessStatus.READY,
            message=self.READY_MESSAGE,
        )

    @staticmethod
    def _blockers(review: BidPackageReview) -> list[str]:
        blockers: list[str] = []

        if not review.drawing_sheets:
            blockers.append("No drawing sheets are available.")

        if not review.specification_sections:
            blockers.append("No specification sections are available.")

        if not review.systems:
            blockers.append("No systems were detected.")

        if not review.equipment:
            blockers.append("No equipment was detected.")

        return blockers

    @classmethod
    def _warnings(cls, review: BidPackageReview) -> list[str]:
        warnings: list[str] = []

        if review.scope_gaps:
            warnings.append("Scope gaps require estimator review.")

        if any(
            cls._value(risk.risk_level) == "high" for risk in review.estimator_risks
        ):
            warnings.append("High estimator risks require estimator review.")

        if any(
            cls._value(recommendation.priority) == "high"
            for recommendation in review.recommendations
        ):
            warnings.append("High-priority recommendations require estimator review.")

        if review.confidence < 0.75:
            warnings.append("Review confidence is below 0.75.")

        return warnings

    @staticmethod
    def _value(value: Any) -> Any:
        return getattr(value, "value", value)

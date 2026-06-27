"""Estimator risk assessment helpers for Atlas Core services."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from atlas_core.domain import BidPackageReview


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class EstimatorRisk:
    risk_id: str
    message: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    category: str = "general"
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.risk_id = self._normalize_required_text("risk_id", self.risk_id)
        self.message = self._normalize_required_text("message", self.message)
        self.category = self.category.strip()

        if not isinstance(self.risk_level, RiskLevel):
            self.risk_level = RiskLevel(self.risk_level)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["risk_level"] = self.risk_level.value
        return data

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


class EstimatorRiskService:
    def assess(self, review: BidPackageReview) -> list[EstimatorRisk]:
        risks: list[EstimatorRisk] = []
        emitted: set[str] = set()

        if review.scope_gap_count() > 0:
            self._add_risk(
                risks,
                emitted,
                EstimatorRisk(
                    risk_id="scope_gaps_detected",
                    message=(
                        "Scope gaps were detected and require estimator review."
                    ),
                    risk_level=RiskLevel.HIGH,
                    category="scope",
                ),
            )

        if review.manufacturer_review_issues:
            self._add_risk(
                risks,
                emitted,
                EstimatorRisk(
                    risk_id="manufacturer_review_required",
                    message="One or more manufacturers require review.",
                    risk_level=RiskLevel.MEDIUM,
                    category="manufacturer",
                ),
            )

        if any(self._value(item.category) == "drapery" for item in review.equipment):
            self._add_risk(
                risks,
                emitted,
                EstimatorRisk(
                    risk_id="drapery_scope_review",
                    message=(
                        "Drapery scope requires review of track, hardware, "
                        "structure, fire rating, and site conditions."
                    ),
                    risk_level=RiskLevel.HIGH,
                    category="drapery",
                ),
            )

        if review.confidence < 0.7:
            self._add_risk(
                risks,
                emitted,
                EstimatorRisk(
                    risk_id="low_review_confidence",
                    message="Overall review confidence is below threshold.",
                    risk_level=RiskLevel.MEDIUM,
                    category="confidence",
                ),
            )

        if review.review_report:
            self._add_risk(
                risks,
                emitted,
                EstimatorRisk(
                    risk_id="review_report_action_items",
                    message="Review report contains estimator action items.",
                    risk_level=RiskLevel.MEDIUM,
                    category="review",
                ),
            )

        return risks

    @staticmethod
    def _add_risk(
        risks: list[EstimatorRisk],
        emitted: set[str],
        risk: EstimatorRisk,
    ) -> None:
        if risk.risk_id in emitted:
            return

        emitted.add(risk.risk_id)
        risks.append(risk)

    @staticmethod
    def _value(value: Any) -> Any:
        return getattr(value, "value", value)

"""Confidence scoring helpers for Atlas Core plan review."""

from atlas_core.domain import BidPackageReview


class ConfidenceScoringService:
    def score_review(self, review: BidPackageReview) -> float:
        score = 1.0

        score -= self._capped_count_penalty(review.scope_gap_count(), 0.05, 0.25)
        score -= self._capped_count_penalty(
            review.estimator_risk_count(),
            0.03,
            0.18,
        )
        score -= self._capped_count_penalty(
            len(review.manufacturer_review_issues),
            0.02,
            0.10,
        )
        score -= self._capped_count_penalty(len(review.resolutions), 0.01, 0.10)

        if not review.drawing_sheets:
            score -= 0.05

        if not review.specification_sections:
            score -= 0.05

        if not review.systems:
            score -= 0.05

        if not review.equipment:
            score -= 0.05

        return round(min(max(score, 0.25), 1.0), 2)

    @staticmethod
    def _capped_count_penalty(count: int, penalty: float, cap: float) -> float:
        return min(count * penalty, cap)

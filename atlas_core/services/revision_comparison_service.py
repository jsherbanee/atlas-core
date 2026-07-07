"""Revision comparison service wrapper for Atlas Core."""

from atlas_core.domain.bid_package_review import BidPackageReview
from atlas_core.domain.revision_comparison import RevisionComparison
from atlas_core.services.revision_comparison_engine import RevisionComparisonEngine


class RevisionComparisonService:
    def __init__(self, engine: RevisionComparisonEngine | None = None) -> None:
        self.engine = engine or RevisionComparisonEngine()

    def build(
        self,
        baseline_review: BidPackageReview,
        comparison_review: BidPackageReview,
        baseline_revision_id: str | None = None,
        comparison_revision_id: str | None = None,
    ) -> RevisionComparison:
        return self.engine.build(
            baseline_review=baseline_review,
            comparison_review=comparison_review,
            baseline_revision_id=baseline_revision_id,
            comparison_revision_id=comparison_revision_id,
        )

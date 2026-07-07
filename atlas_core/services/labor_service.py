"""Labor estimation service wrapper for Atlas Core."""

from atlas_core.domain.bid_package_review import BidPackageReview
from atlas_core.domain.labor_estimate import LaborEstimate
from atlas_core.services.labor_estimation_engine import LaborEstimationEngine


class LaborService:
    def __init__(self, engine: LaborEstimationEngine | None = None) -> None:
        self.engine = engine or LaborEstimationEngine()

    def build(self, review: BidPackageReview) -> LaborEstimate:
        existing_estimate = getattr(review, "labor_estimate", None)
        if isinstance(existing_estimate, LaborEstimate):
            return existing_estimate

        return self.engine.build(review)

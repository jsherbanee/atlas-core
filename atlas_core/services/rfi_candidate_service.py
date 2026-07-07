"""RFI candidate generation service for Atlas Core."""

from atlas_core.domain import BidPackageReview, RFICandidate
from atlas_core.services.rfi_candidate_engine import RFICandidateEngine


class RFICandidateService:
    def __init__(self, engine: RFICandidateEngine | None = None) -> None:
        self.engine = engine or RFICandidateEngine()

    def build(self, review: BidPackageReview) -> list[RFICandidate]:
        return self.engine.build(review)

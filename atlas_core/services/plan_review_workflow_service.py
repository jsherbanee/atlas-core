"""Plan review workflow orchestration for Atlas Core services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from atlas_core.registry import ManufacturerRegistry
from atlas_core.services import (
    BidPackageReviewService,
    EstimatorBrief,
    EstimatorBriefService,
)

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview


@dataclass
class PlanReviewWorkflowResult:
    review: BidPackageReview
    brief: EstimatorBrief

    def to_dict(self) -> dict[str, Any]:
        return {
            "review": self.review.to_dict(),
            "brief": self.brief.to_dict(),
        }


class PlanReviewWorkflowService:
    def __init__(
        self,
        bid_package_review_service: BidPackageReviewService | None = None,
        estimator_brief_service: EstimatorBriefService | None = None,
        manufacturer_registry: ManufacturerRegistry | None = None,
    ) -> None:
        self.bid_package_review_service = bid_package_review_service
        if self.bid_package_review_service is None:
            self.bid_package_review_service = BidPackageReviewService(
                manufacturer_registry=manufacturer_registry
            )

        self.estimator_brief_service = (
            estimator_brief_service or EstimatorBriefService()
        )

    def run_review(
        self,
        review_id: str,
        project_id: str,
        name: str,
        raw_sheets: list[dict] | None = None,
        raw_sections: list[dict] | None = None,
        buildings: list | None = None,
        rooms: list | None = None,
        spaces: list | None = None,
        scenes: list | None = None,
        systems: list | None = None,
        equipment: list | None = None,
    ) -> PlanReviewWorkflowResult:
        review = self.bid_package_review_service.build_review(
            review_id=review_id,
            project_id=project_id,
            name=name,
            raw_sheets=raw_sheets,
            raw_sections=raw_sections,
            buildings=buildings,
            rooms=rooms,
            spaces=spaces,
            scenes=scenes,
            systems=systems,
            equipment=equipment,
        )
        brief = self.estimator_brief_service.build_brief(review)
        return PlanReviewWorkflowResult(review=review, brief=brief)

"""Plan review workflow orchestration for Atlas Core services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from atlas_core.registry import ManufacturerRegistry
from atlas_core.services import (
    BidPackageReviewService,
    EstimatorBrief,
    EstimatorBriefService,
    EquipmentMatrixRow,
)

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview
    from atlas_core.services import FinalEstimatorReview, FinalEstimatorReviewService


@dataclass
class PlanReviewWorkflowResult:
    review: BidPackageReview
    brief: EstimatorBrief
    final_review: FinalEstimatorReview | None = None
    rows: list[EquipmentMatrixRow] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "review": self.review.to_dict(),
            "brief": self.brief.to_dict(),
            "final_review": (
                self.final_review.to_dict() if self.final_review is not None else None
            ),
            "drawing_metadata": [
                md.to_dict() for md in getattr(self.review, "drawing_metadata", [])
            ],
        }


class PlanReviewWorkflowService:
    def __init__(
        self,
        bid_package_review_service: BidPackageReviewService | None = None,
        estimator_brief_service: EstimatorBriefService | None = None,
        final_estimator_review_service: FinalEstimatorReviewService | None = None,
        manufacturer_registry: ManufacturerRegistry | None = None,
    ) -> None:
        from atlas_core.services import FinalEstimatorReviewService

        self.bid_package_review_service: BidPackageReviewService = (
            bid_package_review_service
            or BidPackageReviewService(manufacturer_registry=manufacturer_registry)
        )

        self.estimator_brief_service = (
            estimator_brief_service or EstimatorBriefService()
        )
        self.final_estimator_review_service = (
            final_estimator_review_service or FinalEstimatorReviewService()
        )

    def run_review(
        self,
        review_id: str,
        project_id: str,
        name: str,
        raw_sheets: list[dict] | None = None,
        raw_sections: list[dict] | None = None,
        raw_device_schedules: list[dict] | None = None,
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
            raw_device_schedules=raw_device_schedules,
            buildings=buildings,
            rooms=rooms,
            spaces=spaces,
            scenes=scenes,
            systems=systems,
            equipment=equipment,
        )
        brief = self.estimator_brief_service.build_brief(review)
        final_review = self.final_estimator_review_service.build(review)
        return PlanReviewWorkflowResult(
            review=review,
            brief=brief,
            final_review=final_review,
        )

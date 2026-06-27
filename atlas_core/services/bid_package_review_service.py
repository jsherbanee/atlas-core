"""Bid package review orchestration for Atlas Core services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from atlas_core.registry import ManufacturerRegistry
from atlas_core.services import (
    DrawingIndexerService,
    EstimateWorkflowService,
    SpecificationIndexerService,
)

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview


class BidPackageReviewService:
    def __init__(
        self,
        drawing_indexer: DrawingIndexerService | None = None,
        specification_indexer: SpecificationIndexerService | None = None,
        estimate_workflow_service: EstimateWorkflowService | None = None,
        manufacturer_registry: ManufacturerRegistry | None = None,
    ) -> None:
        self.drawing_indexer = drawing_indexer or DrawingIndexerService()
        self.specification_indexer = (
            specification_indexer or SpecificationIndexerService()
        )
        self.estimate_workflow_service = estimate_workflow_service

        if self.estimate_workflow_service is None:
            self.estimate_workflow_service = EstimateWorkflowService(
                manufacturer_registry=manufacturer_registry
            )

    def build_review(
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
    ) -> BidPackageReview:
        from atlas_core.domain import BidPackageReview

        sheet_items = list(raw_sheets or [])
        section_items = list(raw_sections or [])
        building_items = list(buildings or [])
        room_items = list(rooms or [])
        space_items = list(spaces or [])
        scene_items = list(scenes or [])
        system_items = list(systems or [])
        equipment_items = list(equipment or [])

        drawing_sheets = self.drawing_indexer.index_sheets(sheet_items)
        specification_sections = self.specification_indexer.index_sections(
            section_items
        )
        workflow_result = (
            self.estimate_workflow_service.build_equipment_matrix_with_resolutions(
                buildings=building_items,
                rooms=room_items,
                spaces=space_items,
                scenes=scene_items,
                systems=system_items,
                equipment=equipment_items,
            )
        )

        return BidPackageReview(
            review_id=review_id,
            project_id=project_id,
            name=name,
            drawing_sheets=drawing_sheets,
            specification_sections=specification_sections,
            systems=system_items,
            equipment=equipment_items,
            resolutions=workflow_result.resolutions,
            manufacturer_review_issues=workflow_result.manufacturer_review_issues,
            review_report=workflow_result.review_report,
            confidence=0.75,
        )

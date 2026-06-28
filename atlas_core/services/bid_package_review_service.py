"""Bid package review orchestration for Atlas Core services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from atlas_core.registry import ManufacturerRegistry
from atlas_core.services import (
    CrossReferenceService,
    DrawingIndexerService,
    EquipmentDetectionService,
    EstimateWorkflowService,
    EstimatorRiskService,
    ScopeGapService,
    SpecificationIndexerService,
    SystemDetectionService,
)

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview


class BidPackageReviewService:
    def __init__(
        self,
        drawing_indexer: DrawingIndexerService | None = None,
        specification_indexer: SpecificationIndexerService | None = None,
        estimate_workflow_service: EstimateWorkflowService | None = None,
        cross_reference_service: CrossReferenceService | None = None,
        scope_gap_service: ScopeGapService | None = None,
        estimator_risk_service: EstimatorRiskService | None = None,
        system_detection_service: SystemDetectionService | None = None,
        equipment_detection_service: EquipmentDetectionService | None = None,
        manufacturer_registry: ManufacturerRegistry | None = None,
    ) -> None:
        self.drawing_indexer = drawing_indexer or DrawingIndexerService()
        self.specification_indexer = (
            specification_indexer or SpecificationIndexerService()
        )
        self.estimate_workflow_service = estimate_workflow_service
        self.cross_reference_service = (
            cross_reference_service or CrossReferenceService()
        )
        self.scope_gap_service = scope_gap_service or ScopeGapService()
        self.estimator_risk_service = (
            estimator_risk_service or EstimatorRiskService()
        )
        self.system_detection_service = (
            system_detection_service or SystemDetectionService()
        )
        self.equipment_detection_service = (
            equipment_detection_service or EquipmentDetectionService()
        )

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
        if not system_items:
            system_items = self.system_detection_service.detect_systems(
                drawings=drawing_sheets,
                specifications=specification_sections,
            )

        if not equipment_items:
            equipment_items = self.equipment_detection_service.detect_equipment(
                drawings=drawing_sheets,
                specifications=specification_sections,
                system_id=self._first_system_id(system_items),
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
        cross_references = self.cross_reference_service.build_references(
            drawings=drawing_sheets,
            specifications=specification_sections,
            systems=system_items,
            equipment=equipment_items,
        )
        scope_gaps = self.scope_gap_service.detect_gaps(
            equipment=equipment_items,
            cross_references=cross_references,
        )

        review = BidPackageReview(
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
            cross_references=cross_references,
            scope_gaps=scope_gaps,
            confidence=0.75,
        )
        review.estimator_risks = self.estimator_risk_service.assess(review)
        return review

    @staticmethod
    def _first_system_id(systems: list) -> str | None:
        if not systems:
            return None

        return getattr(systems[0], "system_id", None)

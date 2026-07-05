"""Bid package review orchestration for Atlas Core services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atlas_core.domain import BidPackageReview
from atlas_core.registry import ManufacturerRegistry
from atlas_core.services import (
    ConfidenceScoringService,
    CrossReferenceService,
    DrawingIndexerService,
    EquipmentDetectionService,
    EstimateWorkflowService,
    EstimatorRiskService,
    RecommendationService,
    ScopeGapService,
    SpecificationIndexerService,
    SystemDetectionService,
)

from atlas_core.services.drawing_metadata_service import DrawingMetadataService

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
        confidence_scoring_service: ConfidenceScoringService | None = None,
        recommendation_service: RecommendationService | None = None,
        manufacturer_registry: ManufacturerRegistry | None = None,
        drawing_metadata_service: DrawingMetadataService | None = None,
    ) -> None:
        self.drawing_indexer = drawing_indexer or DrawingIndexerService()
        self.specification_indexer = (
            specification_indexer or SpecificationIndexerService()
        )
        self.cross_reference_service = (
            cross_reference_service or CrossReferenceService()
        )
        self.scope_gap_service = scope_gap_service or ScopeGapService()
        self.estimator_risk_service = estimator_risk_service or EstimatorRiskService()
        self.system_detection_service = (
            system_detection_service or SystemDetectionService()
        )
        self.equipment_detection_service = (
            equipment_detection_service or EquipmentDetectionService()
        )
        self.confidence_scoring_service = (
            confidence_scoring_service or ConfidenceScoringService()
        )
        self.recommendation_service = recommendation_service or RecommendationService()
        self.drawing_metadata_service = (
            drawing_metadata_service or DrawingMetadataService()
        )

        self.estimate_workflow_service: EstimateWorkflowService = (
            estimate_workflow_service
            or EstimateWorkflowService(manufacturer_registry=manufacturer_registry)
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
        inputs = self._prepare_inputs(
            raw_sheets=raw_sheets,
            raw_sections=raw_sections,
            buildings=buildings,
            rooms=rooms,
            spaces=spaces,
            scenes=scenes,
            systems=systems,
            equipment=equipment,
        )

        drawing_sheets = self.drawing_indexer.index_sheets(inputs["sheet_items"])
        drawing_metadata = [
            self.drawing_metadata_service.extract(sheet) for sheet in drawing_sheets
        ]
        specification_sections = self.specification_indexer.index_sections(
            inputs["section_items"]
        )

        system_items = self._detect_systems(
            system_items=inputs["system_items"],
            drawing_sheets=drawing_sheets,
            specification_sections=specification_sections,
        )
        equipment_items = self._detect_equipment(
            equipment_items=inputs["equipment_items"],
            drawing_sheets=drawing_sheets,
            specification_sections=specification_sections,
            system_items=system_items,
        )

        workflow_result = (
            self.estimate_workflow_service.build_equipment_matrix_with_resolutions(
                buildings=inputs["building_items"],
                rooms=inputs["room_items"],
                spaces=inputs["space_items"],
                scenes=inputs["scene_items"],
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

        review = self._assemble_review(
            review_id=review_id,
            project_id=project_id,
            name=name,
            drawing_sheets=drawing_sheets,
            specification_sections=specification_sections,
            system_items=system_items,
            equipment_items=equipment_items,
            workflow_result=workflow_result,
            cross_references=cross_references,
            scope_gaps=scope_gaps,
            drawing_metadata=drawing_metadata,
        )
        review.estimator_risks = self.estimator_risk_service.assess(review)
        review.confidence = self.confidence_scoring_service.score_review(review)
        review.recommendations = self.recommendation_service.build_recommendations(
            review
        )
        return review

    def _prepare_inputs(
        self,
        raw_sheets: list[dict] | None = None,
        raw_sections: list[dict] | None = None,
        buildings: list | None = None,
        rooms: list | None = None,
        spaces: list | None = None,
        scenes: list | None = None,
        systems: list | None = None,
        equipment: list | None = None,
    ) -> dict[str, list]:
        return {
            "sheet_items": list(raw_sheets or []),
            "section_items": list(raw_sections or []),
            "building_items": list(buildings or []),
            "room_items": list(rooms or []),
            "space_items": list(spaces or []),
            "scene_items": list(scenes or []),
            "system_items": list(systems or []),
            "equipment_items": list(equipment or []),
        }

    def _detect_systems(
        self,
        system_items: list,
        drawing_sheets: list,
        specification_sections: list,
    ) -> list:
        if system_items:
            return system_items

        return self.system_detection_service.detect_systems(
            drawings=drawing_sheets,
            specifications=specification_sections,
        )

    def _detect_equipment(
        self,
        equipment_items: list,
        drawing_sheets: list,
        specification_sections: list,
        system_items: list,
    ) -> list:
        if equipment_items:
            return equipment_items

        return self.equipment_detection_service.detect_equipment(
            drawings=drawing_sheets,
            specifications=specification_sections,
            system_id=self._first_system_id(system_items),
        )

    def _assemble_review(
        self,
        review_id: str,
        project_id: str,
        name: str,
        drawing_sheets: list,
        drawing_metadata: list | None,
        specification_sections: list,
        system_items: list,
        equipment_items: list,
        workflow_result: Any,
        cross_references: list,
        scope_gaps: list,
    ) -> Any:
        return BidPackageReview(
            review_id=review_id,
            project_id=project_id,
            name=name,
            drawing_sheets=drawing_sheets,
            drawing_metadata=drawing_metadata or [],
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

    @staticmethod
    def _first_system_id(systems: list) -> str | None:
        if not systems:
            return None

        return getattr(systems[0], "system_id", None)

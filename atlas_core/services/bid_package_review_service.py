"""Bid package review orchestration for Atlas Core services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atlas_core.domain import BidPackageReview, DeviceSchedule
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
from atlas_core.services.device_schedule_equipment_service import (
    DeviceScheduleEquipmentService,
)
from atlas_core.services.device_schedule_extraction_service import (
    DeviceScheduleExtractionService,
)

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview
    from atlas_core.services import (
        BidCompletenessService,
        KeynoteExtractionService,
        LegendExtractionService,
        ScopeReconciliationService,
    )


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
        bid_completeness_service: BidCompletenessService | None = None,
        scope_reconciliation_service: ScopeReconciliationService | None = None,
        manufacturer_registry: ManufacturerRegistry | None = None,
        drawing_metadata_service: DrawingMetadataService | None = None,
        device_schedule_extraction_service: (
            DeviceScheduleExtractionService | None
        ) = None,
        device_schedule_equipment_service: DeviceScheduleEquipmentService | None = None,
        keynote_extraction_service: KeynoteExtractionService | None = None,
        legend_extraction_service: LegendExtractionService | None = None,
    ) -> None:
        from atlas_core.services import (
            BidCompletenessService,
            KeynoteExtractionService,
            LegendExtractionService,
            ScopeReconciliationService,
        )

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
        self.bid_completeness_service = (
            bid_completeness_service or BidCompletenessService()
        )
        self.scope_reconciliation_service = (
            scope_reconciliation_service or ScopeReconciliationService()
        )
        self.drawing_metadata_service = (
            drawing_metadata_service or DrawingMetadataService()
        )
        self.device_schedule_extraction_service = (
            device_schedule_extraction_service or DeviceScheduleExtractionService()
        )
        self.device_schedule_equipment_service = (
            device_schedule_equipment_service or DeviceScheduleEquipmentService()
        )
        self.keynote_extraction_service = (
            keynote_extraction_service or KeynoteExtractionService()
        )
        self.legend_extraction_service = (
            legend_extraction_service or LegendExtractionService()
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
        raw_device_schedules: list[dict] | None = None,
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
            raw_device_schedules=raw_device_schedules,
        )

        drawing_sheets = self.drawing_indexer.index_sheets(inputs["sheet_items"])
        self._enrich_indexed_drawing_sheets(
            drawing_sheets=drawing_sheets,
            raw_sheets=inputs["sheet_items"],
        )
        drawing_metadata = [
            self.drawing_metadata_service.extract(sheet) for sheet in drawing_sheets
        ]
        keynotes = [
            keynote
            for sheet in drawing_sheets
            for keynote in self.keynote_extraction_service.extract_from_sheet(sheet)
        ]
        legends = [
            legend
            for sheet in drawing_sheets
            for legend in [self.legend_extraction_service.extract_from_sheet(sheet)]
            if legend is not None
        ]
        specification_sections = self.specification_indexer.index_sections(
            inputs["section_items"]
        )
        device_schedules = self._extract_device_schedules(
            inputs["device_schedule_items"]
        )
        schedule_derived_equipment = self._equipment_from_device_schedules(
            device_schedules
        )

        system_items = self._detect_systems(
            system_items=inputs["system_items"],
            drawing_sheets=drawing_sheets,
            specification_sections=specification_sections,
        )
        base_equipment_items = self._detect_equipment(
            equipment_items=inputs["equipment_items"],
            drawing_sheets=drawing_sheets,
            specification_sections=specification_sections,
            system_items=system_items,
        )
        equipment_items = [*base_equipment_items, *schedule_derived_equipment]
        reconciliation_issues = self.scope_reconciliation_service.reconcile(
            equipment=equipment_items,
            device_schedules=device_schedules,
            keynotes=keynotes,
            legends=legends,
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
            reconciliation_issues=reconciliation_issues,
            scope_gaps=scope_gaps,
            drawing_metadata=drawing_metadata,
            device_schedules=device_schedules,
            keynotes=keynotes,
            legends=legends,
        )
        review.bid_completeness = self.bid_completeness_service.assess(review)
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
        raw_device_schedules: list[dict] | None = None,
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
            "device_schedule_items": list(raw_device_schedules or []),
        }

    def _extract_device_schedules(
        self,
        raw_device_schedules: list[dict],
    ) -> list[DeviceSchedule]:
        schedules: list[DeviceSchedule] = []
        for idx, raw_schedule in enumerate(raw_device_schedules, start=1):
            if not isinstance(raw_schedule, dict):
                continue

            schedule_id = raw_schedule.get("schedule_id") or f"device-schedule-{idx}"
            source_sheet_number = raw_schedule.get("source_sheet_number")
            title = raw_schedule.get("title") or "Device Schedule"
            rows = raw_schedule.get("rows")
            if not isinstance(rows, list):
                rows = []

            schedules.append(
                self.device_schedule_extraction_service.extract_from_rows(
                    schedule_id=schedule_id,
                    rows=rows,
                    source_sheet_number=source_sheet_number,
                    title=title,
                )
            )

        return schedules

    def _equipment_from_device_schedules(
        self,
        schedules: list[DeviceSchedule],
    ) -> list:
        equipment_items: list = []
        for schedule in schedules:
            schedule_equipment = (
                self.device_schedule_equipment_service.equipment_from_schedule(schedule)
            )
            fallback_system_id = f"schedule-{schedule.schedule_id}"
            for equipment in schedule_equipment:
                if not getattr(equipment, "system_id", None):
                    equipment.system_id = fallback_system_id

            equipment_items.extend(schedule_equipment)

        return equipment_items

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

    @staticmethod
    def _enrich_indexed_drawing_sheets(
        drawing_sheets: list,
        raw_sheets: list[dict],
    ) -> None:
        raw_by_key: dict[tuple[str, str], dict] = {}
        for raw_sheet in raw_sheets:
            if not isinstance(raw_sheet, dict):
                continue

            sheet_number = raw_sheet.get("sheet_number")
            title = raw_sheet.get("title")
            if not isinstance(sheet_number, str) or not isinstance(title, str):
                continue

            key = (sheet_number.strip().casefold(), title.strip().casefold())
            raw_by_key[key] = raw_sheet

        for drawing_sheet in drawing_sheets:
            key = (
                drawing_sheet.sheet_number.strip().casefold(),
                drawing_sheet.title.strip().casefold(),
            )
            matched_raw_sheet = raw_by_key.get(key)
            if matched_raw_sheet is None:
                continue

            notes = matched_raw_sheet.get("notes")
            if isinstance(notes, list):
                drawing_sheet.notes = []
                for note in notes:
                    if isinstance(note, str) and note.strip():
                        drawing_sheet.add_note(note)

            confidence = matched_raw_sheet.get("confidence")
            if isinstance(confidence, (int, float)) and 0 <= confidence <= 1:
                drawing_sheet.confidence = confidence

    def _assemble_review(
        self,
        review_id: str,
        project_id: str,
        name: str,
        drawing_sheets: list,
        drawing_metadata: list | None,
        device_schedules: list | None,
        keynotes: list | None,
        legends: list | None,
        specification_sections: list,
        system_items: list,
        equipment_items: list,
        workflow_result: Any,
        cross_references: list,
        reconciliation_issues: list,
        scope_gaps: list,
    ) -> Any:
        return BidPackageReview(
            review_id=review_id,
            project_id=project_id,
            name=name,
            drawing_sheets=drawing_sheets,
            drawing_metadata=drawing_metadata or [],
            device_schedules=device_schedules or [],
            keynotes=keynotes or [],
            legends=legends or [],
            specification_sections=specification_sections,
            systems=system_items,
            equipment=equipment_items,
            resolutions=workflow_result.resolutions,
            manufacturer_review_issues=workflow_result.manufacturer_review_issues,
            review_report=workflow_result.review_report,
            cross_references=cross_references,
            reconciliation_issues=reconciliation_issues,
            scope_gaps=scope_gaps,
            confidence=0.75,
        )

    @staticmethod
    def _first_system_id(systems: list) -> str | None:
        if not systems:
            return None

        return getattr(systems[0], "system_id", None)

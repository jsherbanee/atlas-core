"""Bid package review orchestration for Atlas Core services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atlas_core.domain import BidPackageReview, DeviceSchedule
from atlas_core.registry import ManufacturerRegistry
from atlas_core.services import (
    ConfidenceScoringService,
    CrossReferenceService,
    DetailCalloutExtractionService,
    DrawingIndexerService,
    EquipmentDetectionService,
    EstimateWorkflowService,
    EstimatorRiskService,
    RecommendationService,
    RoomDetectionService,
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
    from atlas_core.rules import EngineeringRuleEngine, EngineeringRuleRegistry
    from atlas_core.domain import BidPackageReview
    from atlas_core.services import (
        BidCompletenessService,
        KeynoteExtractionService,
        LegendExtractionService,
        LaborService,
        PlanReviewReadinessService,
        RFICandidateService,
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
        plan_review_readiness_service: PlanReviewReadinessService | None = None,
        scope_reconciliation_service: ScopeReconciliationService | None = None,
        manufacturer_registry: ManufacturerRegistry | None = None,
        drawing_metadata_service: DrawingMetadataService | None = None,
        device_schedule_extraction_service: (
            DeviceScheduleExtractionService | None
        ) = None,
        device_schedule_equipment_service: DeviceScheduleEquipmentService | None = None,
        keynote_extraction_service: KeynoteExtractionService | None = None,
        legend_extraction_service: LegendExtractionService | None = None,
        room_detection_service: RoomDetectionService | None = None,
        detail_callout_extraction_service: DetailCalloutExtractionService | None = None,
        engineering_rule_engine: EngineeringRuleEngine | None = None,
        engineering_rule_registry: EngineeringRuleRegistry | None = None,
        rfi_candidate_service: RFICandidateService | None = None,
        labor_service: LaborService | None = None,
    ) -> None:
        from atlas_core.services import (
            BidCompletenessService,
            KeynoteExtractionService,
            LegendExtractionService,
            LaborService,
            PlanReviewReadinessService,
            RFICandidateService,
            ScopeReconciliationService,
        )
        from atlas_core.rules import (
            EngineeringRuleEngine,
            EngineeringRuleRegistry,
            register_default_engineering_rules,
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
        self.plan_review_readiness_service = (
            plan_review_readiness_service or PlanReviewReadinessService()
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
        self.room_detection_service = room_detection_service or RoomDetectionService()
        self.detail_callout_extraction_service = (
            detail_callout_extraction_service or DetailCalloutExtractionService()
        )
        self.rfi_candidate_service = rfi_candidate_service or RFICandidateService()
        self.labor_service = labor_service or LaborService()

        self.estimate_workflow_service: EstimateWorkflowService = (
            estimate_workflow_service
            or EstimateWorkflowService(manufacturer_registry=manufacturer_registry)
        )

        if engineering_rule_engine is not None:
            self.engineering_rule_engine = engineering_rule_engine
        else:
            registry = engineering_rule_registry or EngineeringRuleRegistry()
            if engineering_rule_registry is None:
                register_default_engineering_rules(registry)
            self.engineering_rule_engine = EngineeringRuleEngine(registry)

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
        detail_callouts = [
            callout
            for sheet in drawing_sheets
            for callout in self.detail_callout_extraction_service.extract_from_sheet(
                sheet
            )
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
        room_items = self._prepare_rooms(
            room_items=inputs["room_items"],
            building_items=inputs["building_items"],
            drawing_metadata=drawing_metadata,
            drawing_sheets=drawing_sheets,
            specification_sections=specification_sections,
            device_schedules=device_schedules,
            keynotes=keynotes,
            legends=legends,
            equipment_items=equipment_items,
        )
        reconciliation_issues = self.scope_reconciliation_service.reconcile(
            equipment=equipment_items,
            device_schedules=device_schedules,
            keynotes=keynotes,
            legends=legends,
        )

        workflow_result = (
            self.estimate_workflow_service.build_equipment_matrix_with_resolutions(
                buildings=inputs["building_items"],
                rooms=room_items,
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
            room_items=room_items,
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
            detail_callouts=detail_callouts,
        )
        review.bid_completeness = self.bid_completeness_service.assess(review)
        review.estimator_risks = self.estimator_risk_service.assess(review)
        review.confidence = self.confidence_scoring_service.score_review(review)
        review.engineering_assumptions = self.engineering_rule_engine.evaluate(review)
        review.rfi_candidates = self.rfi_candidate_service.build(review)
        review.labor_estimate = self.labor_service.build(review)
        review.recommendations = self.recommendation_service.build_recommendations(
            review
        )
        review.readiness = self.plan_review_readiness_service.assess(review)
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

    def _prepare_rooms(
        self,
        room_items: list,
        building_items: list,
        drawing_metadata: list,
        drawing_sheets: list,
        specification_sections: list,
        device_schedules: list,
        keynotes: list,
        legends: list,
        equipment_items: list,
    ) -> list:
        normalized_rooms = list(room_items or [])
        if normalized_rooms:
            return normalized_rooms

        building_id = self._first_building_id(building_items)
        if building_id is None:
            return []

        return self.room_detection_service.detect_rooms(
            building_id=building_id,
            drawing_metadata=drawing_metadata,
            drawings=drawing_sheets,
            specifications=specification_sections,
            device_schedules=device_schedules,
            keynotes=keynotes,
            legends=legends,
            equipment=equipment_items,
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
        detail_callouts: list | None,
        specification_sections: list,
        room_items: list,
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
            detail_callouts=detail_callouts or [],
            rooms=room_items,
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

    @staticmethod
    def _first_building_id(buildings: list) -> str | None:
        if not buildings:
            return None

        first_building = buildings[0]
        building_id = getattr(first_building, "building_id", None)
        if isinstance(building_id, str) and building_id.strip():
            return building_id.strip()

        if isinstance(first_building, dict):
            building_id = first_building.get("building_id")
            if isinstance(building_id, str) and building_id.strip():
                return building_id.strip()

        return None

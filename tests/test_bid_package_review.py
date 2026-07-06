import pytest

from atlas_core.domain import (
    AssumptionSeverity,
    BidPackageReview,
    DetailCallout,
    DeviceSchedule,
    DrawingDiscipline,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    Keynote,
    Legend,
    LegendItem,
    Room,
    RoomType,
    SpecificationDiscipline,
    SpecificationSection,
    SystemCategory,
    EngineeringAssumption,
)
from atlas_core.rules import Resolution, ResolutionAction
from atlas_core.services import (
    BidCompleteness,
    CompletenessStatus,
    CrossReference,
    CrossReferenceType,
    EstimatorRisk,
    ManufacturerReviewIssue,
    ReconciliationIssue,
    ReconciliationSeverity,
    Recommendation,
    RecommendationPriority,
    PlanReviewReadiness,
    ReviewReportItem,
    ReadinessStatus,
    RiskLevel,
    ScopeGap,
)
from atlas_core.services import DrawingMetadata


def make_drawing_sheet() -> DrawingSheet:
    return DrawingSheet(
        sheet_id="av101",
        sheet_number="AV1.01",
        title="AV Plan",
        discipline=DrawingDiscipline.AUDIOVISUAL,
    )


def make_specification_section() -> SpecificationSection:
    return SpecificationSection(
        section_id="27-41-16",
        section_number="27 41 16",
        title="Integrated Audio-Video Systems",
        discipline=SpecificationDiscipline.AUDIOVISUAL,
    )


def make_system() -> IntegratedSystem:
    return IntegratedSystem(
        system_id="sys-001",
        name="Performance Audio",
        category=SystemCategory.AUDIO,
    )


def make_equipment() -> Equipment:
    return Equipment(
        equipment_id="eq-001",
        description="Display",
        category=EquipmentCategory.DISPLAY,
    )


def make_resolution() -> Resolution:
    return Resolution(
        rule_id="RULE-001",
        action=ResolutionAction.MARK_FOR_REVIEW,
        target_id="eq-001",
        message="Review required.",
    )


def make_cross_reference() -> CrossReference:
    return CrossReference(
        reference_type=CrossReferenceType.EQUIPMENT_TO_DRAWING,
        source_id="eq-001",
        target_id="av101",
        message="Equipment references drawing.",
    )


def make_scope_gap() -> ScopeGap:
    return ScopeGap(
        gap_id="display_missing_mount",
        target_id="eq-001",
        message="Display is missing a mount.",
    )


def make_estimator_risk() -> EstimatorRisk:
    return EstimatorRisk(
        risk_id="scope_gaps_detected",
        message="Scope gaps were detected and require estimator review.",
        risk_level=RiskLevel.HIGH,
        category="scope",
    )


def make_recommendation() -> Recommendation:
    return Recommendation(
        recommendation_id="review-low-confidence",
        message="Review confidence before pricing.",
        priority=RecommendationPriority.HIGH,
        category="confidence",
    )


def make_engineering_assumption() -> EngineeringAssumption:
    return EngineeringAssumption(
        assumption_id="projection_mount_missing_eq-001",
        category="mounting",
        description="Projector mounting solution should be verified.",
        severity=AssumptionSeverity.REVIEW,
        related_equipment="eq-001",
    )


def make_bid_completeness() -> BidCompleteness:
    return BidCompleteness(
        status=CompletenessStatus.PARTIAL,
        score=0.7,
        drawing_completeness=1.0,
        specification_completeness=1.0,
        system_completeness=0.0,
        equipment_completeness=1.0,
        schedule_completeness=0.5,
        missing_items=["Missing system detection."],
    )


def make_reconciliation_issue() -> ReconciliationIssue:
    return ReconciliationIssue(
        issue_id="device_schedule_item_missing_equipment:sched-001-item-1",
        message="Device schedule item is not represented in equipment matrix.",
        severity=ReconciliationSeverity.HIGH,
        target_id="sched-001-item-1",
    )


def make_device_schedule() -> DeviceSchedule:
    return DeviceSchedule(schedule_id="sched-001", title="Device Schedule")


def make_keynote() -> Keynote:
    return Keynote(
        keynote_id="av101-kn-1",
        number="1",
        description="Ceiling Speaker",
        source_sheet_number="AV1.01",
    )


def make_legend() -> Legend:
    return Legend(
        legend_id="av1.01-legend",
        source_sheet_number="AV1.01",
        items=[
            LegendItem(
                legend_item_id="av1.01-legend-spk",
                symbol="SPK",
                description="Ceiling Speaker",
            )
        ],
    )


def make_room() -> Room:
    return Room(
        room_id="building-001-main-lobby",
        name="Main Lobby",
        building_id="building-001",
        room_type=RoomType.LOBBY,
    )


def make_detail_callout() -> DetailCallout:
    return DetailCallout(
        callout_id="av1.01-detail-5-av-701",
        detail_number="5",
        source_sheet_number="AV1.01",
        target_sheet_number="AV-701",
        description="Detail 5/AV-701",
    )


def test_creating_valid_review():
    review = BidPackageReview(
        review_id=" review-001 ",
        project_id=" project-001 ",
        name=" Bid Package Review ",
        drawing_sheets=[make_drawing_sheet()],
        specification_sections=[make_specification_section()],
        systems=[make_system()],
        equipment=[make_equipment()],
        resolutions=[make_resolution()],
        manufacturer_review_issues=[
            ManufacturerReviewIssue(
                equipment_id="eq-001",
                manufacturer="Unknown",
                message="Manufacturer requires review.",
            )
        ],
        review_report=[
            ReviewReportItem(
                source="resolver",
                target_id="eq-001",
                message="Review required.",
            )
        ],
        notes=[" Confirm scope. "],
        confidence=0.9,
    )

    assert review.review_id == "review-001"
    assert review.project_id == "project-001"
    assert review.name == "Bid Package Review"
    assert review.confidence == 0.9
    assert review.notes == ["Confirm scope."]


def test_rejecting_blank_name():
    with pytest.raises(ValueError, match="name cannot be blank"):
        BidPackageReview(
            review_id="review-001",
            project_id="project-001",
            name=" ",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        BidPackageReview(
            review_id="review-001",
            project_id="project-001",
            name="Bid Package Review",
            confidence=1.2,
        )


def test_adding_notes():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
    )

    review.add_note(" Confirm bid forms. ")
    review.add_note("Review alternates.")

    assert review.notes == ["Confirm bid forms.", "Review alternates."]


def test_drawing_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        drawing_sheets=[make_drawing_sheet()],
    )

    assert review.drawing_count() == 1


def test_specification_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        specification_sections=[make_specification_section()],
    )

    assert review.specification_count() == 1


def test_equipment_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        equipment=[make_equipment()],
    )

    assert review.equipment_count() == 1


def test_issue_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        resolutions=[make_resolution()],
        manufacturer_review_issues=[
            ManufacturerReviewIssue(
                equipment_id="eq-001",
                manufacturer="Unknown",
                message="Manufacturer requires review.",
            )
        ],
        review_report=[
            ReviewReportItem(
                source="resolver",
                target_id="eq-001",
                message="Review required.",
            )
        ],
        reconciliation_issues=[make_reconciliation_issue()],
        scope_gaps=[make_scope_gap()],
        estimator_risks=[make_estimator_risk()],
    )

    assert review.issue_count() == 6


def test_reconciliation_issue_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        reconciliation_issues=[make_reconciliation_issue()],
    )

    assert review.reconciliation_issue_count() == 1


def test_cross_reference_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        cross_references=[make_cross_reference()],
    )

    assert review.cross_reference_count() == 1


def test_scope_gap_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        scope_gaps=[make_scope_gap()],
    )

    assert review.scope_gap_count() == 1


def test_estimator_risk_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        estimator_risks=[make_estimator_risk()],
    )

    assert review.estimator_risk_count() == 1


def test_recommendation_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        recommendations=[make_recommendation()],
    )

    assert review.recommendation_count() == 1


def test_to_dict_output():
    drawing_sheet = make_drawing_sheet()
    specification_section = make_specification_section()
    system = make_system()
    equipment = make_equipment()
    resolution = make_resolution()
    room = make_room()
    detail_callout = make_detail_callout()
    manufacturer_issue = ManufacturerReviewIssue(
        equipment_id="eq-001",
        manufacturer="Unknown",
        message="Manufacturer requires review.",
    )
    review_report_item = ReviewReportItem(
        source="resolver",
        target_id="eq-001",
        message="Review required.",
    )
    cross_reference = make_cross_reference()
    scope_gap = make_scope_gap()
    estimator_risk = make_estimator_risk()
    recommendation = make_recommendation()
    engineering_assumption = make_engineering_assumption()
    reconciliation_issue = make_reconciliation_issue()
    bid_completeness = make_bid_completeness()
    device_schedule = make_device_schedule()
    keynote = make_keynote()
    legend = make_legend()
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        drawing_sheets=[drawing_sheet],
        specification_sections=[specification_section],
        systems=[system],
        equipment=[equipment],
        rooms=[room],
        detail_callouts=[detail_callout],
        resolutions=[resolution],
        manufacturer_review_issues=[manufacturer_issue],
        review_report=[review_report_item],
        cross_references=[cross_reference],
        reconciliation_issues=[reconciliation_issue],
        scope_gaps=[scope_gap],
        estimator_risks=[estimator_risk],
        recommendations=[recommendation],
        engineering_assumptions=[engineering_assumption],
        bid_completeness=bid_completeness,
        drawing_metadata=[DrawingMetadata(sheet_number="AV1.01", title="AV Plan")],
        device_schedules=[device_schedule],
        keynotes=[keynote],
        legends=[legend],
        notes=["Confirm scope."],
        confidence=0.85,
    )

    assert review.to_dict() == {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Bid Package Review",
        "drawing_sheets": [drawing_sheet.to_dict()],
        "specification_sections": [specification_section.to_dict()],
        "systems": [system.to_dict()],
        "equipment": [equipment.to_dict()],
        "rooms": [room.to_dict()],
        "detail_callouts": [detail_callout.to_dict()],
        "resolutions": [
            {
                "rule_id": "RULE-001",
                "action": "mark_for_review",
                "target_id": "eq-001",
                "message": "Review required.",
                "confidence": 0.75,
                "suggested_category": None,
                "suggested_description": None,
                "suggested_manufacturer": None,
                "suggested_model": None,
                "source_system_id": None,
                "source_room_id": None,
                "source_building_id": None,
            }
        ],
        "manufacturer_review_issues": [manufacturer_issue.to_dict()],
        "review_report": [review_report_item.to_dict()],
        "cross_references": [cross_reference.to_dict()],
        "reconciliation_issues": [reconciliation_issue.to_dict()],
        "scope_gaps": [scope_gap.to_dict()],
        "estimator_risks": [estimator_risk.to_dict()],
        "recommendations": [recommendation.to_dict()],
        "engineering_assumptions": [engineering_assumption.to_dict()],
        "bid_completeness": bid_completeness.to_dict(),
        "readiness": None,
        "drawing_metadata": [
            DrawingMetadata(sheet_number="AV1.01", title="AV Plan").to_dict()
        ],
        "device_schedules": [device_schedule.to_dict()],
        "keynotes": [keynote.to_dict()],
        "legends": [legend.to_dict()],
        "notes": ["Confirm scope."],
        "confidence": 0.85,
    }


def test_to_dict_output_includes_none_bid_completeness_when_missing():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
    )

    assert review.to_dict()["bid_completeness"] is None


def test_to_dict_output_includes_readiness_when_present():
    readiness = PlanReviewReadiness(
        status=ReadinessStatus.NEEDS_REVIEW,
        message="Plan review needs estimator review before pricing.",
        blockers=[],
        warnings=["Scope gaps require estimator review."],
    )
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        readiness=readiness,
    )

    assert review.to_dict()["readiness"] == readiness.to_dict()


def test_drawing_metadata_count():
    metadata = DrawingMetadata(sheet_number="AV1.01", title="AV Plan")
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        drawing_metadata=[metadata],
    )

    assert review.drawing_metadata_count() == 1


def test_device_schedule_count():
    schedule = DeviceSchedule(schedule_id="sched-001")
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        device_schedules=[schedule],
    )

    assert review.device_schedule_count() == 1


def test_keynote_count():
    keynote = make_keynote()
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        keynotes=[keynote],
    )

    assert review.keynote_count() == 1


def test_legend_count():
    legend = make_legend()
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        legends=[legend],
    )

    assert review.legend_count() == 1


def test_legend_item_count():
    legend_a = make_legend()
    legend_b = Legend(
        legend_id="av1.02-legend",
        items=[
            LegendItem(
                legend_item_id="av1.02-legend-cam",
                symbol="CAM",
                description="PTZ Camera",
            ),
            LegendItem(
                legend_item_id="av1.02-legend-dsp",
                symbol="DSP",
                description="Display",
            ),
        ],
    )
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        legends=[legend_a, legend_b],
    )

    assert review.legend_item_count() == 3


def test_room_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        rooms=[make_room()],
    )

    assert review.room_count() == 1


def test_detail_callout_count():
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        detail_callouts=[make_detail_callout()],
    )

    assert review.detail_callout_count() == 1

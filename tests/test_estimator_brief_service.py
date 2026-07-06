from atlas_core.domain import (
    AssumptionSeverity,
    BidPackageReview,
    DetailCallout,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    Keynote,
    Legend,
    LegendItem,
    Room,
    RoomType,
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
    EstimatorBrief,
    EstimatorBriefService,
    EstimatorRisk,
    ManufacturerReviewIssue,
    ReconciliationIssue,
    Recommendation,
    RecommendationPriority,
    PlanReviewReadiness,
    ReadinessStatus,
    ReviewReportItem,
    RiskLevel,
    ScopeGap,
)


def make_review() -> BidPackageReview:
    placeholder = Equipment(
        equipment_id="eq-placeholder",
        description="Placeholder mount",
        category=EquipmentCategory.MOUNT,
        status="placeholder",
        review_required=True,
    )
    display = Equipment(
        equipment_id="eq-display",
        description="Display",
        category=EquipmentCategory.DISPLAY,
    )
    room = Room(
        room_id="building-001-main-lobby",
        name="Main Lobby",
        building_id="building-001",
        room_type=RoomType.LOBBY,
    )
    detail_callout = DetailCallout(
        callout_id="av1.01-detail-5-av-701",
        detail_number="5",
        source_sheet_number="AV1.01",
        target_sheet_number="AV-701",
        description="Detail 5/AV-701",
    )

    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        drawing_sheets=[
            DrawingSheet(
                sheet_id="av101",
                sheet_number="AV1.01",
                title="AV Plan",
            )
        ],
        specification_sections=[
            SpecificationSection(
                section_id="27-41-16",
                section_number="27 41 16",
                title="Integrated Audio-Video Systems",
            )
        ],
        systems=[
            IntegratedSystem(
                system_id="sys-001",
                name="Display System",
                category=SystemCategory.DISPLAY,
            )
        ],
        equipment=[placeholder, display],
        rooms=[room],
        detail_callouts=[detail_callout],
        resolutions=[
            Resolution(
                rule_id="RULE-001",
                action=ResolutionAction.MARK_FOR_REVIEW,
                target_id="eq-placeholder",
                message="Review required.",
            )
        ],
        manufacturer_review_issues=[
            ManufacturerReviewIssue(
                equipment_id="eq-display",
                manufacturer="Unknown",
                message="Manufacturer requires review.",
            )
        ],
        review_report=[
            ReviewReportItem(
                source="resolver",
                target_id="eq-placeholder",
                message="Review required.",
            )
        ],
        cross_references=[
            CrossReference(
                reference_type=CrossReferenceType.EQUIPMENT_TO_DRAWING,
                source_id="eq-display",
                target_id="av101",
                message="Equipment references drawing.",
            )
        ],
        reconciliation_issues=[
            ReconciliationIssue(
                issue_id="keynote_missing_equipment_category:projector",
                message=(
                    "Keynote references equipment category not found in "
                    "equipment matrix."
                ),
                target_id="av101-keynote-k1",
            )
        ],
        scope_gaps=[
            ScopeGap(
                gap_id="display_missing_mount",
                target_id="eq-display",
                message="Display is missing a mount.",
            )
        ],
        estimator_risks=[
            EstimatorRisk(
                risk_id="scope_gaps_detected",
                message="Scope gaps were detected and require estimator review.",
                risk_level=RiskLevel.HIGH,
                category="scope",
            )
        ],
        recommendations=[
            Recommendation(
                recommendation_id="review-low-confidence",
                message=(
                    "Review confidence is below target threshold; estimator "
                    "review is required."
                ),
                priority=RecommendationPriority.HIGH,
                category="confidence",
            )
        ],
        engineering_assumptions=[
            EngineeringAssumption(
                assumption_id="assumption-001",
                category="mounting",
                description="Mounting should be verified.",
                severity=AssumptionSeverity.REVIEW,
            )
        ],
        keynotes=[
            Keynote(
                keynote_id="av101-keynote-k1",
                number="K1",
                description="Ceiling Speaker",
                source_sheet_number="AV1.01",
            )
        ],
        legends=[
            Legend(
                legend_id="av1.01-legend",
                source_sheet_number="AV1.01",
                items=[
                    LegendItem(
                        legend_item_id="av1.01-legend-spk",
                        symbol="SPK",
                        description="Ceiling Speaker",
                    ),
                    LegendItem(
                        legend_item_id="av1.01-legend-cam",
                        symbol="CAM",
                        description="PTZ Camera",
                    ),
                ],
            )
        ],
        bid_completeness=BidCompleteness(
            status=CompletenessStatus.PARTIAL,
            score=0.7,
            drawing_completeness=1.0,
            specification_completeness=1.0,
            system_completeness=0.0,
            equipment_completeness=1.0,
            schedule_completeness=0.5,
            missing_items=["Missing system detection."],
        ),
        readiness=PlanReviewReadiness(
            status=ReadinessStatus.NEEDS_REVIEW,
            message="Plan review needs estimator review before pricing.",
            warnings=["Scope gaps require estimator review."],
        ),
        confidence=0.82,
    )


def test_builds_brief_from_review():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.review_id == "review-001"
    assert brief.project_id == "project-001"
    assert brief.name == "Bid Package Review"
    assert brief.confidence == 0.82


def test_counts_drawings():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.drawing_count == 1


def test_counts_specifications():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.specification_count == 1


def test_counts_systems():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.system_count == 1


def test_counts_equipment():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.equipment_count == 2


def test_counts_rooms():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.room_count == 1


def test_counts_detail_callouts():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.detail_callout_count == 1


def test_counts_issues():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.issue_count == 6


def test_counts_placeholder_equipment():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.placeholder_count == 1


def test_counts_review_required_equipment_and_report_items():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.review_required_count == 2


def test_counts_cross_references():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.cross_reference_count == 1


def test_counts_reconciliation_issues():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.reconciliation_issue_count == 1


def test_counts_scope_gaps():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.scope_gap_count == 1


def test_counts_estimator_risks():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.estimator_risk_count == 1


def test_counts_keynotes():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.keynote_count == 1


def test_counts_legends():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.legend_count == 1


def test_counts_legend_items():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.legend_item_count == 2


def test_counts_recommendations():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.recommendation_count == 1


def test_counts_engineering_assumptions():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.engineering_assumption_count == 1


def test_includes_bid_completeness_fields_when_present():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.bid_completeness_score == 0.7
    assert brief.bid_completeness_status == "partial"


def test_includes_readiness_fields_when_present():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.readiness_status == "needs_review"
    assert (
        brief.readiness_message == "Plan review needs estimator review before pricing."
    )


def test_to_dict_output():
    brief = EstimatorBrief(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        drawing_count=1,
        specification_count=1,
        system_count=1,
        equipment_count=2,
        room_count=1,
        detail_callout_count=1,
        issue_count=5,
        placeholder_count=1,
        review_required_count=2,
        cross_reference_count=1,
        reconciliation_issue_count=1,
        scope_gap_count=1,
        estimator_risk_count=1,
        keynote_count=1,
        legend_count=1,
        legend_item_count=2,
        recommendation_count=1,
        confidence=0.82,
        bid_completeness_score=0.7,
        bid_completeness_status="partial",
        readiness_status="needs_review",
        readiness_message="Plan review needs estimator review before pricing.",
    )

    assert brief.to_dict() == {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Bid Package Review",
        "drawing_count": 1,
        "specification_count": 1,
        "system_count": 1,
        "equipment_count": 2,
        "room_count": 1,
        "detail_callout_count": 1,
        "issue_count": 5,
        "placeholder_count": 1,
        "review_required_count": 2,
        "cross_reference_count": 1,
        "reconciliation_issue_count": 1,
        "scope_gap_count": 1,
        "estimator_risk_count": 1,
        "engineering_assumption_count": 0,
        "keynote_count": 1,
        "legend_count": 1,
        "legend_item_count": 2,
        "recommendation_count": 1,
        "confidence": 0.82,
        "bid_completeness_score": 0.7,
        "bid_completeness_status": "partial",
        "readiness_status": "needs_review",
        "readiness_message": "Plan review needs estimator review before pricing.",
    }


def test_bid_completeness_fields_are_none_when_missing():
    review = make_review()
    review.bid_completeness = None

    brief = EstimatorBriefService().build_brief(review)

    assert brief.bid_completeness_score is None
    assert brief.bid_completeness_status is None


def test_readiness_fields_are_none_when_missing():
    review = make_review()
    review.readiness = None

    brief = EstimatorBriefService().build_brief(review)

    assert brief.readiness_status is None
    assert brief.readiness_message is None

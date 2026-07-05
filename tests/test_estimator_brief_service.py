from atlas_core.domain import (
    BidPackageReview,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    Keynote,
    Legend,
    LegendItem,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.rules import Resolution, ResolutionAction
from atlas_core.services import (
    CrossReference,
    CrossReferenceType,
    EstimatorBrief,
    EstimatorBriefService,
    EstimatorRisk,
    ManufacturerReviewIssue,
    ReconciliationIssue,
    Recommendation,
    RecommendationPriority,
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


def test_to_dict_output():
    brief = EstimatorBrief(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        drawing_count=1,
        specification_count=1,
        system_count=1,
        equipment_count=2,
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
    )

    assert brief.to_dict() == {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Bid Package Review",
        "drawing_count": 1,
        "specification_count": 1,
        "system_count": 1,
        "equipment_count": 2,
        "issue_count": 5,
        "placeholder_count": 1,
        "review_required_count": 2,
        "cross_reference_count": 1,
        "reconciliation_issue_count": 1,
        "scope_gap_count": 1,
        "estimator_risk_count": 1,
        "keynote_count": 1,
        "legend_count": 1,
        "legend_item_count": 2,
        "recommendation_count": 1,
        "confidence": 0.82,
    }

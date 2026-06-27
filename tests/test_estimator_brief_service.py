from atlas_core.domain import (
    BidPackageReview,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.rules import Resolution, ResolutionAction
from atlas_core.services import (
    CrossReference,
    EstimatorBrief,
    EstimatorBriefService,
    ManufacturerReviewIssue,
    ReviewReportItem,
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
                reference_type="equipment_to_drawing",
                source_id="eq-display",
                target_id="av101",
                message="Equipment references drawing.",
            )
        ],
        scope_gaps=[
            ScopeGap(
                gap_id="display_missing_mount",
                target_id="eq-display",
                message="Display is missing a mount.",
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

    assert brief.issue_count == 4


def test_counts_placeholder_equipment():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.placeholder_count == 1


def test_counts_review_required_equipment_and_report_items():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.review_required_count == 2


def test_counts_cross_references():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.cross_reference_count == 1


def test_counts_scope_gaps():
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.scope_gap_count == 1


def test_to_dict_output():
    brief = EstimatorBrief(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        drawing_count=1,
        specification_count=1,
        system_count=1,
        equipment_count=2,
        issue_count=4,
        placeholder_count=1,
        review_required_count=2,
        cross_reference_count=1,
        scope_gap_count=1,
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
        "issue_count": 4,
        "placeholder_count": 1,
        "review_required_count": 2,
        "cross_reference_count": 1,
        "scope_gap_count": 1,
        "confidence": 0.82,
    }

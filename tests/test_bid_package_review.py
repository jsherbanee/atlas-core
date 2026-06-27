import pytest

from atlas_core.domain import (
    BidPackageReview,
    DrawingDiscipline,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    SpecificationDiscipline,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.rules import Resolution, ResolutionAction
from atlas_core.services import (
    CrossReference,
    ManufacturerReviewIssue,
    ReviewReportItem,
    ScopeGap,
)


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
        reference_type="equipment_to_drawing",
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
        scope_gaps=[make_scope_gap()],
    )

    assert review.issue_count() == 4


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


def test_to_dict_output():
    drawing_sheet = make_drawing_sheet()
    specification_section = make_specification_section()
    system = make_system()
    equipment = make_equipment()
    resolution = make_resolution()
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
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        drawing_sheets=[drawing_sheet],
        specification_sections=[specification_section],
        systems=[system],
        equipment=[equipment],
        resolutions=[resolution],
        manufacturer_review_issues=[manufacturer_issue],
        review_report=[review_report_item],
        cross_references=[cross_reference],
        scope_gaps=[scope_gap],
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
        "scope_gaps": [scope_gap.to_dict()],
        "notes": ["Confirm scope."],
        "confidence": 0.85,
    }

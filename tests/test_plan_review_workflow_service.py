from atlas_core.domain import Equipment, EquipmentCategory
from atlas_core.services import (
    PlanReviewWorkflowResult,
    PlanReviewWorkflowService,
)


def run_review(**kwargs) -> PlanReviewWorkflowResult:
    return PlanReviewWorkflowService().run_review(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        **kwargs,
    )


def test_run_review_returns_review_and_brief():
    result = run_review()

    assert result.review.review_id == "review-001"
    assert result.brief.review_id == "review-001"


def test_works_with_empty_inputs():
    result = run_review()

    assert result.review.drawing_sheets == []
    assert result.review.specification_sections == []
    assert result.review.equipment == []
    assert result.review.resolutions == []
    assert result.brief.equipment_count == 0


def test_includes_drawing_count_in_brief():
    result = run_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ]
    )

    assert result.brief.drawing_count == 1


def test_includes_specification_count_in_brief():
    result = run_review(
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ]
    )

    assert result.brief.specification_count == 1


def test_includes_resolver_issues_in_review_when_equipment_needs_placeholders():
    speaker = Equipment(
        equipment_id="eq-speaker",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
        system_id="sys-001",
    )

    result = run_review(equipment=[speaker])

    assert len(result.review.resolutions) == 1
    assert result.review.resolutions[0].rule_id == "RULE-001"
    assert len(result.review.review_report) == 1
    assert result.review.scope_gap_count() == 1
    assert result.review.estimator_risk_count() == 2
    assert result.brief.issue_count == 5
    assert result.brief.estimator_risk_count == 2


def test_to_dict_output():
    result = run_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ]
    )

    assert result.to_dict() == {
        "review": result.review.to_dict(),
        "brief": result.brief.to_dict(),
    }

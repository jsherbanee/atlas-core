from atlas_core.contracts import PlanReviewRequest, PlanReviewResponse
from atlas_core.domain import BidPackageReview
from atlas_core.services import EstimatorBrief, PlanReviewWorkflowResult


def make_workflow_result() -> PlanReviewWorkflowResult:
    return PlanReviewWorkflowResult(
        review=BidPackageReview(
            review_id="review-001",
            project_id="project-001",
            name="Plan Review",
        ),
        brief=EstimatorBrief(
            review_id="review-001",
            project_id="project-001",
            name="Plan Review",
            drawing_count=0,
            specification_count=0,
            system_count=0,
            equipment_count=0,
            detail_callout_count=0,
            issue_count=0,
            placeholder_count=0,
            review_required_count=0,
            cross_reference_count=0,
            reconciliation_issue_count=0,
            scope_gap_count=0,
            estimator_risk_count=0,
            keynote_count=0,
            legend_count=0,
            legend_item_count=0,
            room_count=0,
            confidence=0.0,
        ),
    )


def test_creating_valid_request():
    request = PlanReviewRequest(
        review_id=" review-001 ",
        project_id=" project-001 ",
        name=" Plan Review ",
    )

    assert request.review_id == "review-001"
    assert request.project_id == "project-001"
    assert request.name == "Plan Review"
    assert request.raw_pages == []
    assert request.document_sections == []
    assert request.document_section_summary is None
    assert request.raw_sheets == []
    assert request.raw_sections == []
    assert request.raw_device_schedules == []


def test_rejecting_blank_review_id():
    try:
        PlanReviewRequest(
            review_id="   ",
            project_id="project-001",
            name="Plan Review",
        )
    except ValueError as exc:
        assert str(exc) == "review_id cannot be blank"
    else:
        assert False, "Expected ValueError"


def test_rejecting_blank_project_id():
    try:
        PlanReviewRequest(
            review_id="review-001",
            project_id="   ",
            name="Plan Review",
        )
    except ValueError as exc:
        assert str(exc) == "project_id cannot be blank"
    else:
        assert False, "Expected ValueError"


def test_rejecting_blank_name():
    try:
        PlanReviewRequest(
            review_id="review-001",
            project_id="project-001",
            name="   ",
        )
    except ValueError as exc:
        assert str(exc) == "name cannot be blank"
    else:
        assert False, "Expected ValueError"


def test_to_dict_output():
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        raw_pages=[{"page": 1}],
        document_sections=[{"document_type": "cover_sheet"}],
        document_section_summary={"total_sections": 1, "cover_pages": 1},
        raw_sheets=[{"sheet": "AV-101"}],
        raw_sections=[{"section": "27 41 16"}],
        raw_device_schedules=[{"schedule": "S1"}],
    )

    assert request.to_dict() == {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Plan Review",
        "raw_pages": [{"page": 1}],
        "document_sections": [{"document_type": "cover_sheet"}],
        "document_section_summary": {"total_sections": 1, "cover_pages": 1},
        "raw_sheets": [{"sheet": "AV-101"}],
        "raw_sections": [{"section": "27 41 16"}],
        "raw_device_schedules": [{"schedule": "S1"}],
    }


def test_response_to_dict_output():
    result = make_workflow_result()
    response = PlanReviewResponse(result=result)

    assert response.to_dict() == {"result": result.to_dict()}

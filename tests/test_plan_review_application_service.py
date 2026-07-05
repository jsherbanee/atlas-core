from atlas_core.contracts import PlanReviewRequest, PlanReviewResponse
from atlas_core.services.plan_review_application_service import (
    PlanReviewApplicationService,
)


def test_runs_plan_review_from_request():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        raw_sheets=[{"sheet_number": "AV1.01", "title": "AV Plan"}],
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ],
        raw_device_schedules=[
            {
                "schedule_id": "sched-1",
                "source_sheet_number": "AV1.01",
                "rows": [{"tag": "SPK-1", "description": "Main loudspeaker"}],
            }
        ],
    )

    response = service.run(request)

    assert response.result.review.review_id == "review-001"
    assert response.result.review.project_id == "project-001"
    assert response.result.review.name == "Plan Review"


def test_returns_plan_review_response():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    response = service.run(request)

    assert isinstance(response, PlanReviewResponse)


def test_response_includes_review():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    response = service.run(request)

    assert response.result.review.review_id == "review-001"


def test_response_includes_brief():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    response = service.run(request)

    assert response.result.brief.review_id == "review-001"


def test_response_includes_final_review():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    response = service.run(request)

    assert response.result.final_review is not None
    assert response.result.final_review.review_id == "review-001"


def test_works_with_empty_raw_inputs():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    response = service.run(request)

    assert response.result.review.drawing_sheets == []
    assert response.result.review.specification_sections == []
    assert response.result.review.device_schedules == []


def test_accepts_raw_pages_without_crashing():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        raw_pages=[
            {"page_number": 1, "text": "TABLE OF CONTENTS"},
            {"page_number": 2, "text": "Division 27 - Specification"},
        ],
    )

    response = service.run(request)

    assert response.result.review.review_id == "review-001"

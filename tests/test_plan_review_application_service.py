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


def test_raw_pages_create_drawing_sheets_in_response_review():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        raw_pages=[
            {
                "page_number": 1,
                "source_file": "drawings.pdf",
                "text": "AV-101 Audio Floor Plan",
            }
        ],
    )

    response = service.run(request)

    assert any(
        sheet.sheet_number == "AV-101"
        for sheet in response.result.review.drawing_sheets
    )


def test_raw_pages_create_specification_sections_in_response_review():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        raw_pages=[
            {
                "page_number": 2,
                "source_file": "specs.pdf",
                "text": "27 41 16 Integrated Audio-Video Systems",
            }
        ],
    )

    response = service.run(request)

    assert any(
        section.section_number == "27 41 16"
        for section in response.result.review.specification_sections
    )


def test_explicit_raw_sheets_are_preserved():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        raw_pages=[
            {
                "page_number": 1,
                "text": "AV-101 Audio Plan",
            }
        ],
        raw_sheets=[{"sheet_number": "E-601", "title": "Electrical Plan"}],
    )

    response = service.run(request)

    assert any(
        sheet.sheet_number == "E-601" for sheet in response.result.review.drawing_sheets
    )


def test_explicit_raw_sections_are_preserved():
    service = PlanReviewApplicationService()
    request = PlanReviewRequest(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        raw_pages=[
            {
                "page_number": 2,
                "text": "27 41 16 Integrated Audio-Video Systems",
            }
        ],
        raw_sections=[
            {
                "section_number": "26 05 00",
                "title": "Common Work Results for Electrical",
            }
        ],
    )

    response = service.run(request)

    assert any(
        section.section_number == "26 05 00"
        for section in response.result.review.specification_sections
    )

from pathlib import Path

import pytest

from atlas_core.services.pdf_plan_review_intake_service import (
    PdfPlanReviewIntakeService,
)


@pytest.fixture
def fixture_pdf_path() -> Path:
    return Path(__file__).parent / "fixtures" / "simple.pdf"


def test_builds_request_from_pdf(fixture_pdf_path: Path) -> None:
    request = PdfPlanReviewIntakeService().build_request_from_pdf(
        pdf_path=fixture_pdf_path,
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    assert request.review_id == "review-001"
    assert request.project_id == "project-001"
    assert request.name == "Plan Review"


def test_includes_raw_pages(fixture_pdf_path: Path) -> None:
    request = PdfPlanReviewIntakeService().build_request_from_pdf(
        pdf_path=fixture_pdf_path,
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    assert len(request.raw_pages) == 2
    assert request.raw_pages[0]["page_number"] == 1
    assert request.raw_pages[0]["source_file"] == "simple.pdf"


def test_preserves_review_id(fixture_pdf_path: Path) -> None:
    request = PdfPlanReviewIntakeService().build_request_from_pdf(
        pdf_path=fixture_pdf_path,
        review_id="review-custom",
        project_id="project-001",
        name="Plan Review",
    )

    assert request.review_id == "review-custom"


def test_preserves_project_id(fixture_pdf_path: Path) -> None:
    request = PdfPlanReviewIntakeService().build_request_from_pdf(
        pdf_path=fixture_pdf_path,
        review_id="review-001",
        project_id="project-custom",
        name="Plan Review",
    )

    assert request.project_id == "project-custom"


def test_preserves_name(fixture_pdf_path: Path) -> None:
    request = PdfPlanReviewIntakeService().build_request_from_pdf(
        pdf_path=fixture_pdf_path,
        review_id="review-001",
        project_id="project-001",
        name="Custom Name",
    )

    assert request.name == "Custom Name"


def test_raises_file_not_found_error_for_missing_pdf(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        PdfPlanReviewIntakeService().build_request_from_pdf(
            pdf_path=tmp_path / "missing.pdf",
            review_id="review-001",
            project_id="project-001",
            name="Plan Review",
        )

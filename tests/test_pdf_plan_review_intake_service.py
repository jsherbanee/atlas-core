from pathlib import Path

import pytest

from atlas_core.services import ExtractedPdfPage, PdfTextExtractionService
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


def test_includes_document_sections_when_built_from_pdf(
    fixture_pdf_path: Path,
) -> None:
    request = PdfPlanReviewIntakeService().build_request_from_pdf(
        pdf_path=fixture_pdf_path,
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    assert len(request.document_sections) >= 1


def test_extracted_document_sections_are_dictionaries(
    fixture_pdf_path: Path,
) -> None:
    request = PdfPlanReviewIntakeService().build_request_from_pdf(
        pdf_path=fixture_pdf_path,
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    assert all(isinstance(section, dict) for section in request.document_sections)


def test_request_includes_document_section_summary(fixture_pdf_path: Path) -> None:
    request = PdfPlanReviewIntakeService().build_request_from_pdf(
        pdf_path=fixture_pdf_path,
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    assert isinstance(request.document_section_summary, dict)


def test_summary_includes_total_pages(fixture_pdf_path: Path) -> None:
    request = PdfPlanReviewIntakeService().build_request_from_pdf(
        pdf_path=fixture_pdf_path,
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    assert request.document_section_summary is not None
    assert request.document_section_summary["total_pages"] == 2


def test_summary_includes_drawing_spec_unknown_counts() -> None:
    class StubPdfTextExtractionService(PdfTextExtractionService):
        def extract_pages(self, pdf_path: str | Path) -> list[ExtractedPdfPage]:
            return [
                ExtractedPdfPage(
                    page_number=1,
                    text="A101 Floor Plan",
                    source_file="stub.pdf",
                ),
                ExtractedPdfPage(
                    page_number=2,
                    text="Division 27 Specification",
                    source_file="stub.pdf",
                ),
                ExtractedPdfPage(
                    page_number=3,
                    text="General project notes",
                    source_file="stub.pdf",
                ),
            ]

    request = PdfPlanReviewIntakeService(
        pdf_text_extraction_service=StubPdfTextExtractionService()
    ).build_request_from_pdf(
        pdf_path="unused.pdf",
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    assert request.document_section_summary is not None
    assert request.document_section_summary["drawing_pages"] == 1
    assert request.document_section_summary["specification_pages"] == 1
    assert request.document_section_summary["unknown_pages"] == 1


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

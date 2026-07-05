"""PDF intake service for creating plan review requests."""

from __future__ import annotations

from pathlib import Path

from atlas_core.contracts import PlanReviewRequest
from atlas_core.services import (
    DocumentClassifierService,
    DocumentSectionSummaryService,
    PdfTextExtractionService,
)


class PdfPlanReviewIntakeService:
    def __init__(
        self,
        pdf_text_extraction_service: PdfTextExtractionService | None = None,
        document_classifier_service: DocumentClassifierService | None = None,
        document_section_summary_service: DocumentSectionSummaryService | None = None,
    ) -> None:
        self.pdf_text_extraction_service = (
            pdf_text_extraction_service or PdfTextExtractionService()
        )
        self.document_classifier_service = (
            document_classifier_service or DocumentClassifierService()
        )
        self.document_section_summary_service = (
            document_section_summary_service or DocumentSectionSummaryService()
        )

    def build_request_from_pdf(
        self,
        pdf_path: str | Path,
        review_id: str,
        project_id: str,
        name: str,
    ) -> PlanReviewRequest:
        pages = self.pdf_text_extraction_service.extract_pages(pdf_path)
        raw_pages = [page.to_dict() for page in pages]
        document_sections = [
            section.to_dict()
            for section in self.document_classifier_service.classify(raw_pages)
        ]
        document_section_summary = self.document_section_summary_service.summarize(
            document_sections
        )

        return PlanReviewRequest(
            review_id=review_id,
            project_id=project_id,
            name=name,
            raw_pages=raw_pages,
            document_sections=document_sections,
            document_section_summary=document_section_summary.to_dict(),
        )

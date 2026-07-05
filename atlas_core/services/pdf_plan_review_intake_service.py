"""PDF intake service for creating plan review requests."""

from __future__ import annotations

from pathlib import Path

from atlas_core.contracts import PlanReviewRequest
from atlas_core.services import PdfTextExtractionService


class PdfPlanReviewIntakeService:
    def __init__(
        self,
        pdf_text_extraction_service: PdfTextExtractionService | None = None,
    ) -> None:
        self.pdf_text_extraction_service = (
            pdf_text_extraction_service or PdfTextExtractionService()
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

        return PlanReviewRequest(
            review_id=review_id,
            project_id=project_id,
            name=name,
            raw_pages=raw_pages,
        )

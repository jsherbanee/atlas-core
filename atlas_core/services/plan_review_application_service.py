"""Application service for plan review requests."""

from __future__ import annotations

from typing import Any

from atlas_core.contracts import PlanReviewRequest, PlanReviewResponse
from atlas_core.services import (
    DocumentClassifierService,
    PageCandidateExtractionService,
    PlanReviewWorkflowService,
)


class PlanReviewApplicationService:
    def __init__(
        self,
        workflow_service: PlanReviewWorkflowService | None = None,
        document_classifier_service: DocumentClassifierService | None = None,
        page_candidate_extraction_service: PageCandidateExtractionService | None = None,
    ) -> None:
        self.workflow_service = workflow_service or PlanReviewWorkflowService()
        self.document_classifier_service = (
            document_classifier_service or DocumentClassifierService()
        )
        self.page_candidate_extraction_service = (
            page_candidate_extraction_service or PageCandidateExtractionService()
        )

    def run(self, request: PlanReviewRequest) -> PlanReviewResponse:
        # Resolve request-level document metadata now so it can be passed through
        # this application layer, while workflow inputs remain unchanged.
        _document_sections = list(request.document_sections)
        _document_section_summary = request.document_section_summary

        if request.raw_pages and not _document_sections:
            _document_sections = [
                section.to_dict()
                for section in self.document_classifier_service.classify(
                    request.raw_pages
                )
            ]

        enriched_raw_pages = self._enrich_raw_pages_with_document_type(
            request.raw_pages,
            _document_sections,
        )

        extracted_raw_sheets = (
            self.page_candidate_extraction_service.extract_sheet_candidates(
                enriched_raw_pages
            )
        )
        extracted_raw_sections = (
            self.page_candidate_extraction_service.extract_specification_candidates(
                enriched_raw_pages
            )
        )

        combined_raw_sheets = self._merge_unique_dicts(
            request.raw_sheets,
            extracted_raw_sheets,
        )
        combined_raw_sections = self._merge_unique_dicts(
            request.raw_sections,
            extracted_raw_sections,
        )

        request.raw_pages = enriched_raw_pages
        request.document_sections = _document_sections
        request.document_section_summary = _document_section_summary
        request.raw_sheets = combined_raw_sheets
        request.raw_sections = combined_raw_sections

        result = self.workflow_service.run_review(
            review_id=request.review_id,
            project_id=request.project_id,
            name=request.name,
            raw_sheets=combined_raw_sheets,
            raw_sections=combined_raw_sections,
            raw_device_schedules=request.raw_device_schedules,
        )

        return PlanReviewResponse(result=result)

    @classmethod
    def _enrich_raw_pages_with_document_type(
        cls,
        raw_pages: list[dict],
        document_sections: list[dict],
    ) -> list[dict]:
        enriched_pages: list[dict] = []

        for raw_page in raw_pages:
            enriched_page = dict(raw_page)
            if "document_type" not in enriched_page or not cls._text(
                enriched_page.get("document_type")
            ):
                page_number = cls._page_number(enriched_page.get("page_number"))
                section_document_type = cls._document_type_for_page(
                    document_sections,
                    page_number,
                )
                if section_document_type is not None:
                    enriched_page["document_type"] = section_document_type

            enriched_pages.append(enriched_page)

        return enriched_pages

    @staticmethod
    def _document_type_for_page(
        document_sections: list[dict],
        page_number: int | None,
    ) -> str | None:
        if page_number is None:
            return None

        for section in document_sections:
            start_page = section.get("start_page")
            end_page = section.get("end_page")
            if (
                isinstance(start_page, int)
                and isinstance(end_page, int)
                and start_page <= page_number <= end_page
            ):
                document_type = section.get("document_type")
                if isinstance(document_type, str) and document_type.strip():
                    return document_type.strip()

        return None

    @classmethod
    def _merge_unique_dicts(
        cls,
        explicit_items: list[dict],
        extracted_items: list[dict],
    ) -> list[dict]:
        merged: list[dict] = []
        seen: set[tuple] = set()

        for item in [*explicit_items, *extracted_items]:
            if not isinstance(item, dict):
                continue

            normalized_item = dict(item)
            marker = cls._dict_marker(normalized_item)
            if marker in seen:
                continue

            seen.add(marker)
            merged.append(normalized_item)

        return merged

    @staticmethod
    def _dict_marker(value: dict) -> tuple:
        return tuple(sorted((str(key), repr(item)) for key, item in value.items()))

    @staticmethod
    def _page_number(value: Any) -> int | None:
        if isinstance(value, int) and value > 0:
            return value

        return None

    @staticmethod
    def _text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        normalized = value.strip()
        return normalized or None

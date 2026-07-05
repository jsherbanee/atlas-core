"""Document section summarization for Atlas Core services."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from atlas_core.services.document_classifier_service import (
    DocumentSection,
    DocumentType,
)


@dataclass
class DocumentSectionSummary:
    total_sections: int
    total_pages: int
    drawing_pages: int
    specification_pages: int
    schedule_pages: int
    cover_pages: int
    unknown_pages: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DocumentSectionSummaryService:
    def summarize(
        self,
        sections: list[DocumentSection] | list[dict],
    ) -> DocumentSectionSummary:
        summary = DocumentSectionSummary(
            total_sections=len(sections),
            total_pages=0,
            drawing_pages=0,
            specification_pages=0,
            schedule_pages=0,
            cover_pages=0,
            unknown_pages=0,
        )

        for section in sections:
            page_count = self._page_count(section)
            summary.total_pages += page_count

            document_type = self._document_type(section)
            if document_type == DocumentType.DRAWING_SET.value:
                summary.drawing_pages += page_count
            elif document_type == DocumentType.SPECIFICATION_BOOK.value:
                summary.specification_pages += page_count
            elif document_type == DocumentType.SCHEDULE.value:
                summary.schedule_pages += page_count
            elif document_type == DocumentType.COVER_SHEET.value:
                summary.cover_pages += page_count
            else:
                summary.unknown_pages += page_count

        return summary

    @staticmethod
    def _document_type(section: DocumentSection | dict) -> str:
        value: Any
        if isinstance(section, DocumentSection):
            value = section.document_type
        else:
            value = section.get("document_type")

        if isinstance(value, DocumentType):
            return value.value

        if not isinstance(value, str):
            return DocumentType.UNKNOWN.value

        normalized = value.strip()
        if not normalized:
            return DocumentType.UNKNOWN.value

        try:
            return DocumentType(normalized).value
        except ValueError:
            return DocumentType.UNKNOWN.value

    @staticmethod
    def _page_count(section: DocumentSection | dict) -> int:
        start_page: Any
        end_page: Any

        if isinstance(section, DocumentSection):
            start_page = section.start_page
            end_page = section.end_page
        else:
            start_page = section.get("start_page")
            end_page = section.get("end_page")

        if not isinstance(start_page, int) or not isinstance(end_page, int):
            return 0

        if end_page < start_page:
            return 0

        return end_page - start_page + 1

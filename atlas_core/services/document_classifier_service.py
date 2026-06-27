"""Bid package document classification helpers for Atlas Core."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class DocumentType(str, Enum):
    DRAWING_SET = "drawing_set"
    SPECIFICATION_BOOK = "specification_book"
    SUBMITTAL = "submittal"
    SCHEDULE = "schedule"
    COVER_SHEET = "cover_sheet"
    UNKNOWN = "unknown"


@dataclass
class DocumentSection:
    document_type: DocumentType
    start_page: int
    end_page: int
    title: str
    confidence: float = 0.75

    def __post_init__(self) -> None:
        if not isinstance(self.document_type, DocumentType):
            self.document_type = DocumentType(self.document_type)

        if self.start_page < 0:
            raise ValueError("start_page cannot be negative")

        if self.end_page < 0:
            raise ValueError("end_page cannot be negative")

        if self.end_page < self.start_page:
            raise ValueError("end_page cannot be less than start_page")

        self.title = self._normalize_title(self.title)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type.value,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "title": self.title,
            "confidence": self.confidence,
        }

    @staticmethod
    def _normalize_title(title: str) -> str:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title cannot be blank")

        return title.strip()


class DocumentClassifierService:
    _SHEET_NUMBER_PATTERN = re.compile(
        r"\b(?:SEC|AV|TL|LX|FA|A|E|T)-?\d{3}\b",
        re.IGNORECASE,
    )

    def classify(self, raw_pages: list[dict]) -> list[DocumentSection]:
        sections: list[DocumentSection] = []

        for index, raw_page in enumerate(raw_pages, start=1):
            page_number = self._page_number(raw_page.get("page_number"), index)
            document_type, confidence = self._classify_text(
                self._text(raw_page.get("text"))
            )

            if sections and sections[-1].document_type is document_type:
                sections[-1].end_page = page_number
                sections[-1].confidence = min(sections[-1].confidence, confidence)
                continue

            sections.append(
                DocumentSection(
                    document_type=document_type,
                    start_page=page_number,
                    end_page=page_number,
                    title=self._title(document_type),
                    confidence=confidence,
                )
            )

        return sections

    def _classify_text(self, text: str) -> tuple[DocumentType, float]:
        normalized = text.casefold()

        if "table of contents" in normalized:
            return DocumentType.COVER_SHEET, 0.9

        if "division 27" in normalized or "specification" in normalized:
            return DocumentType.SPECIFICATION_BOOK, 0.9

        if "equipment schedule" in normalized or "device schedule" in normalized:
            return DocumentType.SCHEDULE, 0.9

        if self._SHEET_NUMBER_PATTERN.search(text):
            return DocumentType.DRAWING_SET, 0.85

        return DocumentType.UNKNOWN, 0.5

    @staticmethod
    def _page_number(value: Any, default: int) -> int:
        if isinstance(value, int) and value > 0:
            return value

        return default

    @staticmethod
    def _text(value: Any) -> str:
        if not isinstance(value, str):
            return ""

        return value

    @staticmethod
    def _title(document_type: DocumentType) -> str:
        return document_type.value.replace("_", " ").title()

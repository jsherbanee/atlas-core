"""Extract rough drawing and specification candidates from raw PDF pages."""

from __future__ import annotations

import re
from typing import Any

from atlas_core.services.document_classifier_service import DocumentType


class PageCandidateExtractionService:
    _SHEET_PATTERN = re.compile(
        r"\b(AV|SEC|TL|LX|FA|A|E|T)[-\s]?(\d{3})\b",
        re.IGNORECASE,
    )
    _SPEC_PATTERN = re.compile(
        r"\b((?:11|26|27|28)[\s-]?\d{2}[\s-]?\d{2})\b",
        re.IGNORECASE,
    )

    def extract_sheet_candidates(self, raw_pages: list[dict]) -> list[dict]:
        candidates: list[dict] = []
        seen: set[tuple[str, int | None]] = set()

        for raw_page in raw_pages:
            document_type = self._document_type(raw_page.get("document_type"))
            if document_type == DocumentType.SPECIFICATION_BOOK.value:
                continue

            page_number = self._page_number(raw_page.get("page_number"))
            source_file = self._text(raw_page.get("source_file"))
            text = self._text(raw_page.get("text")) or ""

            for match in self._SHEET_PATTERN.finditer(text):
                sheet_number = f"{match.group(1).upper()}-{match.group(2)}"
                dedupe_key = (sheet_number, page_number)
                if dedupe_key in seen:
                    continue

                seen.add(dedupe_key)
                candidates.append(
                    {
                        "sheet_number": sheet_number,
                        "title": self._sheet_title(text, match.group(0)),
                        "source_file": source_file,
                        "page_number": page_number,
                    }
                )

        return candidates

    def extract_specification_candidates(self, raw_pages: list[dict]) -> list[dict]:
        candidates: list[dict] = []
        seen: set[tuple[str, int | None]] = set()

        for raw_page in raw_pages:
            document_type = self._document_type(raw_page.get("document_type"))
            if document_type == DocumentType.DRAWING_SET.value:
                continue

            page_number = self._page_number(raw_page.get("page_number"))
            source_file = self._text(raw_page.get("source_file"))
            text = self._text(raw_page.get("text")) or ""

            for match in self._SPEC_PATTERN.finditer(text):
                section_number = self._normalize_section_number(match.group(1))
                dedupe_key = (section_number, page_number)
                if dedupe_key in seen:
                    continue

                seen.add(dedupe_key)
                candidates.append(
                    {
                        "section_number": section_number,
                        "title": self._spec_title(text, match.group(0)),
                        "source_file": source_file,
                        "page_start": page_number,
                        "page_end": page_number,
                    }
                )

        return candidates

    @classmethod
    def _sheet_title(cls, text: str, matched: str) -> str:
        title = cls._extract_title(text, matched)
        return title or "Untitled Sheet"

    @classmethod
    def _spec_title(cls, text: str, matched: str) -> str:
        title = cls._extract_title(text, matched)
        return title or "Untitled Specification Section"

    @staticmethod
    def _extract_title(text: str, matched: str) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        for index, line in enumerate(lines):
            if matched not in line:
                continue

            trailing = line.replace(matched, "", 1).strip(" :-\t")
            if trailing and any(char.isalpha() for char in trailing):
                return trailing

            if index + 1 < len(lines):
                next_line = lines[index + 1].strip(" :-\t")
                if next_line and any(char.isalpha() for char in next_line):
                    return next_line

        return None

    @staticmethod
    def _normalize_section_number(value: str) -> str:
        digits = re.sub(r"[^0-9]", "", value)
        return f"{digits[0:2]} {digits[2:4]} {digits[4:6]}"

    @staticmethod
    def _document_type(value: Any) -> str | None:
        if isinstance(value, DocumentType):
            return value.value

        if not isinstance(value, str):
            return None

        normalized = value.strip()
        if not normalized:
            return None

        try:
            return DocumentType(normalized).value
        except ValueError:
            return normalized

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

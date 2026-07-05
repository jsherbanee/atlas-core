"""Structured drawing metadata extraction for Atlas Core."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from atlas_core.domain import DrawingSheet


@dataclass(slots=True)
class DrawingMetadata:
    sheet_number: str
    title: str
    revision: str | None = None
    issue_date: str | None = None
    discipline: str = "unknown"
    referenced_sheet_numbers: list[str] = field(default_factory=list)
    referenced_specification_sections: list[str] = field(default_factory=list)
    room_names: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.sheet_number = DrawingMetadata._normalize_required_text(
            "sheet_number", self.sheet_number
        )
        self.title = DrawingMetadata._normalize_required_text("title", self.title)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.referenced_sheet_numbers = DrawingMetadata._normalize_list(
            self.referenced_sheet_numbers
        )
        self.referenced_specification_sections = DrawingMetadata._normalize_list(
            self.referenced_specification_sections
        )
        self.room_names = DrawingMetadata._normalize_list(self.room_names)

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

    @staticmethod
    def _normalize_list(values: list[str]) -> list[str]:
        return [item.strip() for item in values if item and item.strip()]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet_number": self.sheet_number,
            "title": self.title,
            "revision": self.revision,
            "issue_date": self.issue_date,
            "discipline": self.discipline,
            "referenced_sheet_numbers": list(self.referenced_sheet_numbers),
            "referenced_specification_sections": list(
                self.referenced_specification_sections
            ),
            "room_names": list(self.room_names),
            "confidence": self.confidence,
        }


class DrawingMetadataService:
    def extract(self, sheet: DrawingSheet) -> DrawingMetadata:
        return DrawingMetadata(
            sheet_number=sheet.sheet_number,
            title=sheet.title,
            revision=sheet.revision,
            issue_date=sheet.issue_date,
            discipline=sheet.discipline.value,
            referenced_sheet_numbers=self._extract_sheet_references(sheet),
            referenced_specification_sections=self._extract_spec_sections(sheet),
            room_names=self._extract_room_names(sheet),
            confidence=sheet.confidence,
        )

    def _extract_sheet_references(self, sheet: DrawingSheet) -> list[str]:
        text = " ".join([sheet.title, *sheet.notes])
        candidates = re.findall(
            r"\b(?:AV|A|E|T|TL|LX|FA|SEC)(?:-|\s)?\d{3,4}\b",
            text,
            flags=re.IGNORECASE,
        )
        refs = [self._normalize_sheet_reference(candidate) for candidate in candidates]
        return self._unique(refs)

    def _extract_spec_sections(self, sheet: DrawingSheet) -> list[str]:
        text = " ".join([sheet.title, *sheet.notes])
        pattern = re.compile(r"\b\d{2}\s+\d{2}\s+\d{2,4}\b")
        sections = pattern.findall(text)
        return self._unique([section.strip() for section in sections])

    def _extract_room_names(self, sheet: DrawingSheet) -> list[str]:
        title_text = sheet.title.strip()
        note_text = " ".join(sheet.notes)
        patterns = [
            r"\b(?:Recital Hall|Control Booth|Main Lobby|Equipment Room|Conference Room|Control Room)\b",
            r"\bClassroom\s+\d+\b",
        ]

        names: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, title_text, flags=re.IGNORECASE):
                if self._is_title_room_match(title_text, match):
                    names.append(self._normalize_room_name(match.group(0)))

            for match in re.finditer(pattern, note_text, flags=re.IGNORECASE):
                if match.group(0):
                    names.append(self._normalize_room_name(match.group(0)))

        return self._unique(names)

    @staticmethod
    def _is_title_room_match(text: str, match: re.Match[str]) -> bool:
        suffix = text[match.end() :]
        if not suffix:
            return True

        trimmed_suffix = suffix.strip()
        if not trimmed_suffix:
            return True

        return bool(re.match(r"^[,;:\-./]+", trimmed_suffix))

    @staticmethod
    def _normalize_sheet_reference(value: str) -> str:
        token = re.sub(r"[^A-Za-z0-9]", "", value.upper())
        prefix = ""
        number = token
        for idx, char in enumerate(token):
            if char.isdigit():
                prefix = token[:idx]
                number = token[idx:]
                break

        if not prefix or not number:
            return value.upper()

        return f"{prefix}-{number}"

    @staticmethod
    def _normalize_room_name(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        words = [word for word in cleaned.split(" ") if word]
        if not words:
            return ""

        if words[-1].lower() in {
            "room",
            "hall",
            "lobby",
            "booth",
            "classroom",
            "studio",
            "stage",
            "theater",
            "theatre",
        }:
            return " ".join(words).title()

        return " ".join(words).title()

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(
            dict.fromkeys(value.strip() for value in values if value and value.strip())
        )

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
        pattern = re.compile(r"\b([A-Za-z]{1,3}\d{1,4}(?:\.\d+)?)\b")
        matches = pattern.findall(sheet.title + " " + " ".join(sheet.notes))
        refs = [match.strip().replace(".", "") for match in matches if match]
        return self._unique(refs)

    def _extract_spec_sections(self, sheet: DrawingSheet) -> list[str]:
        pattern = re.compile(r"\b(2[0-9]{1,2}\s?[0-9]{2}\s?[0-9]{2,4})\b")
        matches = pattern.findall(sheet.title + " " + " ".join(sheet.notes))
        sections = [match.replace(" ", "") for match in matches]
        return self._unique(sections)

    def _extract_room_names(self, sheet: DrawingSheet) -> list[str]:
        text = " ".join([sheet.title, *sheet.notes]).lower()
        room_patterns = [
            r"\b(?:room|rm)\s+(?P<room>[a-z0-9\-]+)",
            r"\b(?:conference|lobby|office|classroom|restroom|storage|lab|suite)\s+(?P<room>[a-z0-9\-]+)",
        ]
        names: list[str] = []
        for pattern in room_patterns:
            for match in re.finditer(pattern, text):
                room_name = match.groupdict().get("room")
                if room_name:
                    names.append(room_name.strip())

        return self._unique(
            [name.title() for name in names if name and name.lower() != "room"]
        )

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(
            dict.fromkeys(value.strip() for value in values if value and value.strip())
        )

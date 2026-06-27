"""Specification domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpecificationDiscipline(str, Enum):
    AUDIOVISUAL = "audiovisual"
    THEATRICAL = "theatrical"
    ELECTRICAL = "electrical"
    COMMUNICATIONS = "communications"
    LIGHTING = "lighting"
    DRAPERY = "drapery"
    RIGGING = "rigging"
    ACOUSTICS = "acoustics"
    SECURITY = "security"
    UNKNOWN = "unknown"


@dataclass
class SpecificationSection:
    section_id: str
    section_number: str
    title: str
    discipline: SpecificationDiscipline = SpecificationDiscipline.UNKNOWN
    source_file: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    manufacturers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.section_id = self._normalize_required_text(
            "section_id",
            self.section_id,
        )
        self.section_number = self._normalize_required_text(
            "section_number",
            self.section_number,
        )
        self.title = self._normalize_required_text("title", self.title)

        if not isinstance(self.discipline, SpecificationDiscipline):
            self.discipline = SpecificationDiscipline(self.discipline)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        if self.page_start is not None and self.page_start < 0:
            raise ValueError("page_start cannot be negative")

        if self.page_end is not None and self.page_end < 0:
            raise ValueError("page_end cannot be negative")

        if (
            self.page_start is not None
            and self.page_end is not None
            and self.page_end < self.page_start
        ):
            raise ValueError("page_end cannot be less than page_start")

        self.source_file = self._normalize_optional_text(self.source_file)
        self.manufacturers = [
            self._normalize_manufacturer(manufacturer)
            for manufacturer in self.manufacturers
        ]
        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_manufacturer(self, manufacturer: str) -> None:
        self.manufacturers.append(self._normalize_manufacturer(manufacturer))

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "section_number": self.section_number,
            "title": self.title,
            "discipline": self.discipline.value,
            "source_file": self.source_file,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "manufacturers": list(self.manufacturers),
            "notes": list(self.notes),
            "confidence": self.confidence,
        }

    @classmethod
    def _normalize_manufacturer(cls, manufacturer: str) -> str:
        return cls._normalize_required_text("manufacturer", manufacturer)

    @classmethod
    def _normalize_note(cls, note: str) -> str:
        return cls._normalize_required_text("note", note)

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

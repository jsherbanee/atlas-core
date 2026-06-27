"""Drawing domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DrawingDiscipline(str, Enum):
    ARCHITECTURAL = "architectural"
    ELECTRICAL = "electrical"
    AUDIOVISUAL = "audiovisual"
    THEATRICAL = "theatrical"
    LIGHTING = "lighting"
    STRUCTURAL = "structural"
    MECHANICAL = "mechanical"
    PLUMBING = "plumbing"
    TELECOM = "telecom"
    FIRE_ALARM = "fire_alarm"
    SECURITY = "security"
    UNKNOWN = "unknown"


@dataclass
class DrawingSheet:
    sheet_id: str
    sheet_number: str
    title: str
    discipline: DrawingDiscipline = DrawingDiscipline.UNKNOWN
    revision: str | None = None
    issue_date: str | None = None
    source_file: str | None = None
    page_number: int | None = None
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.sheet_id = self._normalize_required_text("sheet_id", self.sheet_id)
        self.sheet_number = self._normalize_required_text(
            "sheet_number",
            self.sheet_number,
        )
        self.title = self._normalize_required_text("title", self.title)

        if not isinstance(self.discipline, DrawingDiscipline):
            self.discipline = DrawingDiscipline(self.discipline)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        if self.page_number is not None and self.page_number < 0:
            raise ValueError("page_number cannot be negative")

        self.revision = self._normalize_optional_text(self.revision)
        self.issue_date = self._normalize_optional_text(self.issue_date)
        self.source_file = self._normalize_optional_text(self.source_file)
        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet_id": self.sheet_id,
            "sheet_number": self.sheet_number,
            "title": self.title,
            "discipline": self.discipline.value,
            "revision": self.revision,
            "issue_date": self.issue_date,
            "source_file": self.source_file,
            "page_number": self.page_number,
            "notes": list(self.notes),
            "confidence": self.confidence,
        }

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

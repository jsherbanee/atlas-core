"""Deterministic drawing intelligence models for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from statistics import fmean
from typing import Any


class DrawingDiscipline(str, Enum):
    ARCHITECTURAL = "architectural"
    AV = "av"
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"
    STRUCTURAL = "structural"
    TECHNOLOGY = "technology"
    LOW_VOLTAGE = "low_voltage"
    FIRE_ALARM = "fire_alarm"
    TELECOM = "telecom"
    CIVIL = "civil"
    LANDSCAPE = "landscape"
    UNKNOWN = "unknown"


class DrawingSheetCategory(str, Enum):
    COVER_SHEET = "cover_sheet"
    GENERAL_NOTES = "general_notes"
    LEGEND = "legend"
    SYMBOLS = "symbols"
    SITE_PLAN = "site_plan"
    FLOOR_PLAN = "floor_plan"
    REFLECTED_CEILING_PLAN = "reflected_ceiling_plan"
    EQUIPMENT_PLAN = "equipment_plan"
    RACK_ELEVATION = "rack_elevation"
    SINGLE_LINE_DIAGRAM = "single_line_diagram"
    BLOCK_DIAGRAM = "block_diagram"
    SIGNAL_FLOW = "signal_flow"
    TYPICAL_DETAIL = "typical_detail"
    MOUNTING_DETAIL = "mounting_detail"
    SECTION = "section"
    ELEVATION = "elevation"
    SCHEDULE = "schedule"
    INDEX = "index"
    OTHER = "other"


class DrawingReferenceType(str, Enum):
    SHEET = "sheet"
    DETAIL = "detail"
    SECTION = "section"
    CALLOUT = "callout"
    VIEW = "view"
    SCHEDULE = "schedule"
    INDEX = "index"


@dataclass(frozen=True)
class DrawingReference:
    source_sheet: str
    target_id: str
    reference_type: DrawingReferenceType
    confidence: float = 0.75
    source_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_sheet": self.source_sheet,
            "target_id": self.target_id,
            "reference_type": self.reference_type.value,
            "confidence": self.confidence,
            "source_text": self.source_text,
        }


@dataclass(frozen=True)
class DrawingRelationship:
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float = 0.75
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class DrawingMetadata:
    sheet_number: str
    title: str
    revision: str | None
    issue_date: str | None
    scale: str | None
    discipline: DrawingDiscipline
    sheet_category: DrawingSheetCategory
    sheet_sequence: int | None
    references: list[DrawingReference] = field(default_factory=list)
    general_notes: list[str] = field(default_factory=list)
    detail_references: list[str] = field(default_factory=list)
    view_references: list[str] = field(default_factory=list)
    keynotes: list[str] = field(default_factory=list)
    confidence: float = 0.75
    source_trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet_number": self.sheet_number,
            "title": self.title,
            "revision": self.revision,
            "issue_date": self.issue_date,
            "scale": self.scale,
            "discipline": self.discipline.value,
            "sheet_category": self.sheet_category.value,
            "sheet_sequence": self.sheet_sequence,
            "references": [item.to_dict() for item in self.references],
            "general_notes": list(self.general_notes),
            "detail_references": list(self.detail_references),
            "view_references": list(self.view_references),
            "keynotes": list(self.keynotes),
            "confidence": self.confidence,
            "source_trace": dict(self.source_trace),
        }


@dataclass(frozen=True)
class DrawingIndex:
    by_sheet_number: dict[str, DrawingMetadata]
    by_discipline: dict[str, list[str]]
    by_sheet_category: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "by_sheet_number": {
                key: value.to_dict() for key, value in self.by_sheet_number.items()
            },
            "by_discipline": {
                key: list(value) for key, value in self.by_discipline.items()
            },
            "by_sheet_category": {
                key: list(value) for key, value in self.by_sheet_category.items()
            },
        }


@dataclass(frozen=True)
class DrawingHierarchy:
    project_id: str
    disciplines: dict[str, dict[str, list[str]]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "disciplines": {
                discipline: {
                    drawing_set: list(sheets)
                    for drawing_set, sheets in drawing_sets.items()
                }
                for discipline, drawing_sets in self.disciplines.items()
            },
        }


@dataclass(frozen=True)
class DrawingIntelligenceResult:
    metadata: list[DrawingMetadata]
    drawing_index: DrawingIndex
    relationships: list[DrawingRelationship]
    hierarchy: DrawingHierarchy
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": [item.to_dict() for item in self.metadata],
            "drawing_index": self.drawing_index.to_dict(),
            "relationships": [item.to_dict() for item in self.relationships],
            "hierarchy": self.hierarchy.to_dict(),
            "confidence": self.confidence,
        }


def aggregate_confidence(values: list[float], default: float = 0.75) -> float:
    usable = [value for value in values if isinstance(value, (int, float))]
    if not usable:
        return default
    return max(0.0, min(1.0, float(fmean(usable))))

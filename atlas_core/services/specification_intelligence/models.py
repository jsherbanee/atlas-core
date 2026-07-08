"""Deterministic specification intelligence models for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from statistics import fmean
from typing import Any


class SpecificationDiscipline(str, Enum):
    DIVISION_01_GENERAL_REQUIREMENTS = "division_01_general_requirements"
    DIVISION_26_ELECTRICAL = "division_26_electrical"
    DIVISION_27_COMMUNICATIONS = "division_27_communications"
    DIVISION_28_ELECTRONIC_SAFETY_SECURITY = "division_28_electronic_safety_security"
    AV_SYSTEMS = "av_systems"
    AUDIO_SYSTEMS = "audio_systems"
    VIDEO_SYSTEMS = "video_systems"
    CONTROL_SYSTEMS = "control_systems"
    NETWORK_SYSTEMS = "network_systems"
    TELECOM = "telecom"
    SECURITY = "security"
    THEATRICAL_SYSTEMS = "theatrical_systems"
    LIGHTING_SYSTEMS = "lighting_systems"
    RIGGING = "rigging"
    ACOUSTICS = "acoustics"
    OTHER = "other"


class SpecificationReferenceType(str, Enum):
    SECTION = "section"
    DRAWING = "drawing"
    EQUIPMENT = "equipment"
    MANUFACTURER = "manufacturer"
    PRODUCT = "product"
    SYSTEM = "system"
    STANDARD = "standard"
    SCHEDULE = "schedule"
    ADDENDUM = "addendum"


@dataclass(frozen=True)
class SpecificationArticle:
    identifier: str
    heading: str
    source_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "heading": self.heading,
            "source_text": self.source_text,
        }


@dataclass(frozen=True)
class SpecificationPart:
    part_number: str
    title: str
    articles: list[SpecificationArticle] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "part_number": self.part_number,
            "title": self.title,
            "articles": [item.to_dict() for item in self.articles],
        }


@dataclass(frozen=True)
class SpecificationReference:
    source_section: str
    target_id: str
    reference_type: SpecificationReferenceType
    confidence: float = 0.75
    source_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_section": self.source_section,
            "target_id": self.target_id,
            "reference_type": self.reference_type.value,
            "confidence": self.confidence,
            "source_text": self.source_text,
        }


@dataclass(frozen=True)
class SpecificationRelationship:
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
class SpecificationMetadata:
    section_number: str
    title: str
    division: str
    discipline: SpecificationDiscipline
    revision: str | None
    issue_date: str | None
    addendum_references: list[str] = field(default_factory=list)
    referenced_standards: list[str] = field(default_factory=list)
    referenced_manufacturers: list[str] = field(default_factory=list)
    referenced_products: list[str] = field(default_factory=list)
    referenced_systems: list[str] = field(default_factory=list)
    referenced_drawings: list[str] = field(default_factory=list)
    related_schedules: list[str] = field(default_factory=list)
    confidence: float = 0.75
    source_trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_number": self.section_number,
            "title": self.title,
            "division": self.division,
            "discipline": self.discipline.value,
            "revision": self.revision,
            "issue_date": self.issue_date,
            "addendum_references": list(self.addendum_references),
            "referenced_standards": list(self.referenced_standards),
            "referenced_manufacturers": list(self.referenced_manufacturers),
            "referenced_products": list(self.referenced_products),
            "referenced_systems": list(self.referenced_systems),
            "referenced_drawings": list(self.referenced_drawings),
            "related_schedules": list(self.related_schedules),
            "confidence": self.confidence,
            "source_trace": dict(self.source_trace),
        }


@dataclass(frozen=True)
class SpecificationSection:
    section_number: str
    title: str
    division: str
    discipline: SpecificationDiscipline
    status: str
    revision: str | None
    issue_date: str | None
    metadata: SpecificationMetadata
    parts: list[SpecificationPart] = field(default_factory=list)
    articles: list[SpecificationArticle] = field(default_factory=list)
    references: list[SpecificationReference] = field(default_factory=list)
    requirement_candidates: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.75

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_number": self.section_number,
            "title": self.title,
            "division": self.division,
            "discipline": self.discipline.value,
            "status": self.status,
            "revision": self.revision,
            "issue_date": self.issue_date,
            "metadata": self.metadata.to_dict(),
            "parts": [item.to_dict() for item in self.parts],
            "articles": [item.to_dict() for item in self.articles],
            "references": [item.to_dict() for item in self.references],
            "requirement_candidates": [
                dict(item) for item in self.requirement_candidates
            ],
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class SpecificationIndex:
    by_section: dict[str, SpecificationSection]
    by_division: dict[str, list[str]]
    by_discipline: dict[str, list[str]]
    by_status: dict[str, list[str]]
    by_revision: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "by_section": {
                key: value.to_dict() for key, value in self.by_section.items()
            },
            "by_division": {
                key: list(value) for key, value in self.by_division.items()
            },
            "by_discipline": {
                key: list(value) for key, value in self.by_discipline.items()
            },
            "by_status": {key: list(value) for key, value in self.by_status.items()},
            "by_revision": {
                key: list(value) for key, value in self.by_revision.items()
            },
        }


@dataclass(frozen=True)
class SpecificationIntelligenceResult:
    metadata: list[SpecificationMetadata]
    sections: list[SpecificationSection]
    specification_index: SpecificationIndex
    relationships: list[SpecificationRelationship]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": [item.to_dict() for item in self.metadata],
            "sections": [item.to_dict() for item in self.sections],
            "specification_index": self.specification_index.to_dict(),
            "relationships": [item.to_dict() for item in self.relationships],
            "confidence": self.confidence,
        }


def aggregate_confidence(values: list[float], default: float = 0.75) -> float:
    usable = [value for value in values if isinstance(value, (int, float))]
    if not usable:
        return default
    return max(0.0, min(1.0, float(fmean(usable))))

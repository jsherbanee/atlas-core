"""Explainable source-fitness assessments for intake and baseline reconstruction."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceFitnessAssessment:
    record_type: str
    source_file: str
    fitness_status: str
    baseline_role: str
    fitness_score: int
    authority_level: str
    source_group: str | None = None
    page_number: int | None = None
    evidence_id: str | None = None
    evidence_type: str | None = None
    detected_sheet_number: str | None = None
    detected_discipline: str | None = None
    source_excerpt: str | None = None
    governing_for: list[str] = field(default_factory=list)
    coordination_for: list[str] = field(default_factory=list)
    non_governing_for: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)
    review_flags: list[str] = field(default_factory=list)
    source_deficiencies: list[str] = field(default_factory=list)
    atlas_failures: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.record_type = self._normalize_required_text(
            "record_type", self.record_type
        )
        self.source_file = self._normalize_required_text(
            "source_file", self.source_file
        )
        self.fitness_status = self._normalize_required_text(
            "fitness_status", self.fitness_status
        )
        self.baseline_role = self._normalize_required_text(
            "baseline_role", self.baseline_role
        )
        self.authority_level = self._normalize_required_text(
            "authority_level", self.authority_level
        )
        self.source_group = self._normalize_optional_text(self.source_group)
        self.page_number = self._normalize_optional_int(self.page_number)
        self.evidence_id = self._normalize_optional_text(self.evidence_id)
        self.evidence_type = self._normalize_optional_text(self.evidence_type)
        self.detected_sheet_number = self._normalize_optional_text(
            self.detected_sheet_number
        )
        self.detected_discipline = self._normalize_optional_text(
            self.detected_discipline
        )
        self.source_excerpt = self._normalize_optional_text(self.source_excerpt)
        self.fitness_score = self._normalize_score("fitness_score", self.fitness_score)
        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")
        self.governing_for = self._normalize_list(self.governing_for)
        self.coordination_for = self._normalize_list(self.coordination_for)
        self.non_governing_for = self._normalize_list(self.non_governing_for)
        self.reasons = self._normalize_list(self.reasons)
        self.evidence_references = self._normalize_list(self.evidence_references)
        self.review_flags = self._normalize_list(self.review_flags)
        self.source_deficiencies = self._normalize_list(self.source_deficiencies)
        self.atlas_failures = self._normalize_list(self.atlas_failures)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceFitnessAssessment":
        return cls(**dict(payload))

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")
        return value.strip()

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_optional_int(value: int | None) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return value if value >= 0 else None

    @staticmethod
    def _normalize_list(values: list[str]) -> list[str]:
        return [
            item.strip() for item in values if isinstance(item, str) and item.strip()
        ]

    @staticmethod
    def _normalize_score(field_name: str, value: int) -> int:
        if not isinstance(value, int):
            raise ValueError(f"{field_name} must be an int")
        if not 0 <= value <= 100:
            raise ValueError(f"{field_name} must be between 0 and 100")
        return value


@dataclass
class SourceFitnessResult:
    document_assessments: list[SourceFitnessAssessment] = field(default_factory=list)
    page_assessments: list[SourceFitnessAssessment] = field(default_factory=list)
    evidence_assessments: list[SourceFitnessAssessment] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    created_by_engine_version: str = "source-fitness-service/1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_assessments": [
                item.to_dict() for item in self.document_assessments
            ],
            "page_assessments": [item.to_dict() for item in self.page_assessments],
            "evidence_assessments": [
                item.to_dict() for item in self.evidence_assessments
            ],
            "summary": dict(self.summary),
            "created_by_engine_version": self.created_by_engine_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceFitnessResult":
        return cls(
            document_assessments=[
                (
                    item
                    if isinstance(item, SourceFitnessAssessment)
                    else SourceFitnessAssessment.from_dict(dict(item))
                )
                for item in list(payload.get("document_assessments") or [])
            ],
            page_assessments=[
                (
                    item
                    if isinstance(item, SourceFitnessAssessment)
                    else SourceFitnessAssessment.from_dict(dict(item))
                )
                for item in list(payload.get("page_assessments") or [])
            ],
            evidence_assessments=[
                (
                    item
                    if isinstance(item, SourceFitnessAssessment)
                    else SourceFitnessAssessment.from_dict(dict(item))
                )
                for item in list(payload.get("evidence_assessments") or [])
            ],
            summary=dict(payload.get("summary") or {}),
            created_by_engine_version=str(
                payload.get("created_by_engine_version")
                or "source-fitness-service/1.0.0"
            ),
        )

"""Document relevance domain model for Atlas Core intake."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RelevanceWorkflowScores:
    intake: int
    estimating: int
    engineering: int
    procurement: int
    construction: int
    commissioning: int
    service: int

    def __post_init__(self) -> None:
        for field_name in (
            "intake",
            "estimating",
            "engineering",
            "procurement",
            "construction",
            "commissioning",
            "service",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int):
                raise ValueError(f"{field_name} must be an int")
            if not 0 <= value <= 100:
                raise ValueError(f"{field_name} must be between 0 and 100")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PageRelevanceAssessment:
    source_file: str
    page_number: int | None
    detected_sheet_number: str | None
    detected_discipline: str | None
    project_membership_score: int
    project_membership_status: str
    primary_discipline: str | None
    secondary_disciplines: list[str] = field(default_factory=list)
    overall_relevance_score: int = 0
    workflow_scores: RelevanceWorkflowScores = field(
        default_factory=lambda: RelevanceWorkflowScores(
            intake=0,
            estimating=0,
            engineering=0,
            procurement=0,
            construction=0,
            commissioning=0,
            service=0,
        )
    )
    authority_level: str = "contextual"
    governing_for: list[str] = field(default_factory=list)
    coordination_for: list[str] = field(default_factory=list)
    non_governing_for: list[str] = field(default_factory=list)
    relevance_reasons: list[str] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)
    review_flags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.source_file = self._normalize_required_text(
            "source_file", self.source_file
        )
        if self.page_number is not None and self.page_number < 0:
            raise ValueError("page_number cannot be negative")
        self.detected_sheet_number = self._normalize_optional_text(
            self.detected_sheet_number
        )
        self.detected_discipline = self._normalize_optional_text(
            self.detected_discipline
        )
        self.project_membership_score = self._normalize_score(
            "project_membership_score",
            self.project_membership_score,
        )
        self.project_membership_status = self._normalize_required_text(
            "project_membership_status",
            self.project_membership_status,
        )
        self.primary_discipline = self._normalize_optional_text(self.primary_discipline)
        self.secondary_disciplines = self._normalize_list(self.secondary_disciplines)
        self.overall_relevance_score = self._normalize_score(
            "overall_relevance_score",
            self.overall_relevance_score,
        )
        if not isinstance(self.workflow_scores, RelevanceWorkflowScores):
            self.workflow_scores = RelevanceWorkflowScores(**dict(self.workflow_scores))
        self.authority_level = self._normalize_required_text(
            "authority_level",
            self.authority_level,
        )
        self.governing_for = self._normalize_list(self.governing_for)
        self.coordination_for = self._normalize_list(self.coordination_for)
        self.non_governing_for = self._normalize_list(self.non_governing_for)
        self.relevance_reasons = self._normalize_list(self.relevance_reasons)
        self.evidence_references = self._normalize_list(self.evidence_references)
        self.review_flags = self._normalize_list(self.review_flags)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["workflow_scores"] = self.workflow_scores.to_dict()
        return payload

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
class DocumentRelevanceAssessment:
    source_file: str
    document_group: str
    page_count: int
    project_membership_score: int
    project_membership_status: str
    primary_discipline: str | None
    secondary_disciplines: list[str] = field(default_factory=list)
    overall_relevance_score: int = 0
    workflow_scores: RelevanceWorkflowScores = field(
        default_factory=lambda: RelevanceWorkflowScores(
            intake=0,
            estimating=0,
            engineering=0,
            procurement=0,
            construction=0,
            commissioning=0,
            service=0,
        )
    )
    authority_level: str = "contextual"
    governing_for: list[str] = field(default_factory=list)
    coordination_for: list[str] = field(default_factory=list)
    non_governing_for: list[str] = field(default_factory=list)
    relevance_reasons: list[str] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)
    review_flags: list[str] = field(default_factory=list)
    page_assessments: list[PageRelevanceAssessment] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.source_file = self._normalize_required_text(
            "source_file", self.source_file
        )
        self.document_group = self._normalize_required_text(
            "document_group",
            self.document_group,
        )
        if self.page_count < 0:
            raise ValueError("page_count cannot be negative")
        self.project_membership_score = self._normalize_score(
            "project_membership_score",
            self.project_membership_score,
        )
        self.project_membership_status = self._normalize_required_text(
            "project_membership_status",
            self.project_membership_status,
        )
        self.primary_discipline = self._normalize_optional_text(self.primary_discipline)
        self.secondary_disciplines = self._normalize_list(self.secondary_disciplines)
        self.overall_relevance_score = self._normalize_score(
            "overall_relevance_score",
            self.overall_relevance_score,
        )
        if not isinstance(self.workflow_scores, RelevanceWorkflowScores):
            self.workflow_scores = RelevanceWorkflowScores(**dict(self.workflow_scores))
        self.authority_level = self._normalize_required_text(
            "authority_level",
            self.authority_level,
        )
        self.governing_for = self._normalize_list(self.governing_for)
        self.coordination_for = self._normalize_list(self.coordination_for)
        self.non_governing_for = self._normalize_list(self.non_governing_for)
        self.relevance_reasons = self._normalize_list(self.relevance_reasons)
        self.evidence_references = self._normalize_list(self.evidence_references)
        self.review_flags = self._normalize_list(self.review_flags)
        self.page_assessments = [
            (
                item
                if isinstance(item, PageRelevanceAssessment)
                else PageRelevanceAssessment(**dict(item))
            )
            for item in self.page_assessments
        ]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["workflow_scores"] = self.workflow_scores.to_dict()
        payload["page_assessments"] = [item.to_dict() for item in self.page_assessments]
        return payload

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

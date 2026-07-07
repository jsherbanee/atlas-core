"""RFI candidate domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RFICandidateCategory(str, Enum):
    MISSING_INFORMATION = "missing_information"
    SCOPE_AMBIGUITY = "scope_ambiguity"
    QUANTITY_CONFLICT = "quantity_conflict"
    PRODUCT_CONFLICT = "product_conflict"
    RESPONSIBILITY_GAP = "responsibility_gap"
    ADD_ALTERNATE_CLARIFICATION = "add_alternate_clarification"
    DRAWING_SPEC_MISMATCH = "drawing_spec_mismatch"


class RFICandidateSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RFICandidateStatus(str, Enum):
    CANDIDATE = "candidate"
    DISMISSED = "dismissed"
    PROMOTED = "promoted"


@dataclass
class RFICandidateSourceRef:
    source_type: str
    source_id: str
    field: str | None = None
    source_label: str | None = None
    excerpt: str | None = None

    def __post_init__(self) -> None:
        self.source_type = self._normalize_required_text(
            "source_type", self.source_type
        )
        self.source_id = self._normalize_required_text("source_id", self.source_id)
        self.field = self._normalize_optional_text(self.field)
        self.source_label = self._normalize_optional_text(self.source_label)
        self.excerpt = self._normalize_optional_text(self.excerpt)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "field": self.field,
            "source_label": self.source_label,
            "excerpt": self.excerpt,
        }

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


@dataclass
class RFICandidate:
    candidate_id: str
    project_id: str
    title: str
    description: str
    category: RFICandidateCategory | str
    severity: RFICandidateSeverity | str
    confidence: float
    source_refs: list[RFICandidateSourceRef] = field(default_factory=list)
    related_items: list[str] = field(default_factory=list)
    detected_condition: str = ""
    recommended_action: str = ""
    status: RFICandidateStatus | str = RFICandidateStatus.CANDIDATE
    created_by_engine_version: str = "rfi-candidate-engine/1.0.0"

    def __post_init__(self) -> None:
        self.candidate_id = self._normalize_required_text(
            "candidate_id", self.candidate_id
        )
        self.project_id = self._normalize_required_text("project_id", self.project_id)
        self.title = self._normalize_required_text("title", self.title)
        self.description = self._normalize_required_text(
            "description", self.description
        )
        self.detected_condition = self._normalize_required_text(
            "detected_condition", self.detected_condition
        )
        self.recommended_action = self._normalize_required_text(
            "recommended_action", self.recommended_action
        )
        self.created_by_engine_version = self._normalize_required_text(
            "created_by_engine_version", self.created_by_engine_version
        )

        if not isinstance(self.category, RFICandidateCategory):
            self.category = RFICandidateCategory(self.category)

        if not isinstance(self.severity, RFICandidateSeverity):
            self.severity = RFICandidateSeverity(self.severity)

        if not isinstance(self.status, RFICandidateStatus):
            self.status = RFICandidateStatus(self.status)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.source_refs = [
            (
                ref
                if isinstance(ref, RFICandidateSourceRef)
                else RFICandidateSourceRef(**ref)
            )
            for ref in self.source_refs
        ]
        self.related_items = [
            self._normalize_required_text("related_item", related_item)
            for related_item in self.related_items
        ]

    def to_dict(self) -> dict[str, Any]:
        category = (
            self.category.value
            if isinstance(self.category, RFICandidateCategory)
            else str(self.category)
        )
        severity = (
            self.severity.value
            if isinstance(self.severity, RFICandidateSeverity)
            else str(self.severity)
        )
        status = (
            self.status.value
            if isinstance(self.status, RFICandidateStatus)
            else str(self.status)
        )

        return {
            "candidate_id": self.candidate_id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "category": category,
            "severity": severity,
            "confidence": self.confidence,
            "source_refs": [source_ref.to_dict() for source_ref in self.source_refs],
            "related_items": list(self.related_items),
            "detected_condition": self.detected_condition,
            "recommended_action": self.recommended_action,
            "status": status,
            "created_by_engine_version": self.created_by_engine_version,
        }

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

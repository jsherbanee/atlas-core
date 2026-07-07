"""Revision comparison domain models for Atlas Core bid intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RevisionChangeType(str, Enum):
    ITEM_ADDED = "item_added"
    ITEM_REMOVED = "item_removed"
    ITEM_MODIFIED = "item_modified"
    QUANTITY_CHANGED = "quantity_changed"
    SCOPE_RESPONSIBILITY_CHANGED = "scope_responsibility_changed"
    SPECIFICATION_CHANGED = "specification_changed"
    DRAWING_REFERENCE_CHANGED = "drawing_reference_changed"
    ADD_ALTERNATE_CHANGED = "add_alternate_changed"
    ASSUMPTION_CHANGED = "assumption_changed"
    RFI_CANDIDATE_CHANGED = "rfi_candidate_changed"
    LABOR_ESTIMATE_CHANGED = "labor_estimate_changed"


class RevisionChangeSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RevisionComparisonSourceRef:
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
class RevisionChangeRecord:
    change_id: str
    change_type: RevisionChangeType
    title: str
    description: str
    severity: RevisionChangeSeverity
    confidence: float
    source_refs: list[RevisionComparisonSourceRef] = field(default_factory=list)
    affected_items: list[str] = field(default_factory=list)
    previous_value: Any = None
    current_value: Any = None
    detected_condition: str = ""
    estimating_impact: str = ""
    labor_impact: bool = False
    recommended_action: str = ""

    def __post_init__(self) -> None:
        self.change_id = self._normalize_required_text("change_id", self.change_id)
        self.title = self._normalize_required_text("title", self.title)
        self.description = self._normalize_required_text(
            "description", self.description
        )
        self.detected_condition = self._normalize_required_text(
            "detected_condition", self.detected_condition
        )
        self.estimating_impact = self._normalize_required_text(
            "estimating_impact", self.estimating_impact
        )
        self.recommended_action = self._normalize_required_text(
            "recommended_action", self.recommended_action
        )

        if not isinstance(self.change_type, RevisionChangeType):
            self.change_type = RevisionChangeType(self.change_type)

        if not isinstance(self.severity, RevisionChangeSeverity):
            self.severity = RevisionChangeSeverity(self.severity)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.source_refs = [
            (
                source_ref
                if isinstance(source_ref, RevisionComparisonSourceRef)
                else RevisionComparisonSourceRef(**source_ref)
            )
            for source_ref in self.source_refs
        ]
        self.affected_items = [
            self._normalize_required_text("affected_item", item)
            for item in self.affected_items
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "source_refs": [source_ref.to_dict() for source_ref in self.source_refs],
            "affected_items": list(self.affected_items),
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "detected_condition": self.detected_condition,
            "estimating_impact": self.estimating_impact,
            "labor_impact": self.labor_impact,
            "recommended_action": self.recommended_action,
        }

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


@dataclass
class RevisionComparison:
    project_id: str
    baseline_revision_id: str
    comparison_revision_id: str
    summary: dict[str, Any]
    changes: list[RevisionChangeRecord] = field(default_factory=list)
    added_items: list[str] = field(default_factory=list)
    removed_items: list[str] = field(default_factory=list)
    modified_items: list[str] = field(default_factory=list)
    quantity_changes: list[str] = field(default_factory=list)
    scope_changes: list[str] = field(default_factory=list)
    labor_impact_flags: list[str] = field(default_factory=list)
    assumption_impacts: list[str] = field(default_factory=list)
    rfi_impacts: list[str] = field(default_factory=list)
    confidence: float = 0.75
    source_refs: list[RevisionComparisonSourceRef] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_by_engine_version: str = "revision-comparison-engine/1.0.0"

    def __post_init__(self) -> None:
        self.project_id = self._normalize_required_text("project_id", self.project_id)
        self.baseline_revision_id = self._normalize_required_text(
            "baseline_revision_id", self.baseline_revision_id
        )
        self.comparison_revision_id = self._normalize_required_text(
            "comparison_revision_id", self.comparison_revision_id
        )
        self.created_by_engine_version = self._normalize_required_text(
            "created_by_engine_version", self.created_by_engine_version
        )

        if not isinstance(self.summary, dict):
            raise ValueError("summary must be a dict")

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.changes = [
            (
                change
                if isinstance(change, RevisionChangeRecord)
                else RevisionChangeRecord(**change)
            )
            for change in self.changes
        ]
        self.source_refs = [
            (
                source_ref
                if isinstance(source_ref, RevisionComparisonSourceRef)
                else RevisionComparisonSourceRef(**source_ref)
            )
            for source_ref in self.source_refs
        ]
        self.added_items = [
            self._normalize_required_text("added_item", item)
            for item in self.added_items
        ]
        self.removed_items = [
            self._normalize_required_text("removed_item", item)
            for item in self.removed_items
        ]
        self.modified_items = [
            self._normalize_required_text("modified_item", item)
            for item in self.modified_items
        ]
        self.quantity_changes = [
            self._normalize_required_text("quantity_change", change_id)
            for change_id in self.quantity_changes
        ]
        self.scope_changes = [
            self._normalize_required_text("scope_change", change_id)
            for change_id in self.scope_changes
        ]
        self.labor_impact_flags = [
            self._normalize_required_text("labor_impact_flag", change_id)
            for change_id in self.labor_impact_flags
        ]
        self.assumption_impacts = [
            self._normalize_required_text("assumption_impact", impact)
            for impact in self.assumption_impacts
        ]
        self.rfi_impacts = [
            self._normalize_required_text("rfi_impact", impact)
            for impact in self.rfi_impacts
        ]
        self.warnings = [
            self._normalize_required_text("warning", warning)
            for warning in self.warnings
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "baseline_revision_id": self.baseline_revision_id,
            "comparison_revision_id": self.comparison_revision_id,
            "summary": dict(self.summary),
            "changes": [change.to_dict() for change in self.changes],
            "added_items": list(self.added_items),
            "removed_items": list(self.removed_items),
            "modified_items": list(self.modified_items),
            "quantity_changes": list(self.quantity_changes),
            "scope_changes": list(self.scope_changes),
            "labor_impact_flags": list(self.labor_impact_flags),
            "assumption_impacts": list(self.assumption_impacts),
            "rfi_impacts": list(self.rfi_impacts),
            "confidence": self.confidence,
            "source_refs": [source_ref.to_dict() for source_ref in self.source_refs],
            "warnings": list(self.warnings),
            "created_by_engine_version": self.created_by_engine_version,
        }

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

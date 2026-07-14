"""Deterministic AV lifecycle engine contracts for Atlas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Iterable

from atlas_core.domain.project import ProjectStatus

AV_LIFECYCLE_SCHEMA_VERSION = "1.0"
AV_LIFECYCLE_DEFINITION_KEY = "atlas.av.lifecycle"


class LifecycleStageStatus(str, Enum):
    NOT_STARTED = "not_started"
    AVAILABLE = "available"
    ACTIVE = "active"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    ARCHIVED = "archived"


_STAGE_DEFINITIONS: list[tuple[str, str, str, bool]] = [
    ("lead", "Lead", "sales", True),
    ("opportunity", "Opportunity", "sales", True),
    ("discovery", "Discovery", "sales", True),
    ("bid_intake", "Bid Intake", "operations", True),
    ("bid_intelligence", "Bid Intelligence", "engineering", True),
    ("estimating", "Estimating", "estimating", True),
    ("proposal", "Proposal", "sales", True),
    ("award", "Award", "sales", True),
    ("project_initialization", "Project Initialization", "project management", True),
    ("engineering", "Engineering", "engineering", True),
    ("submittals", "Submittals", "engineering", True),
    ("procurement", "Procurement", "procurement", True),
    ("logistics_and_receiving", "Logistics and Receiving", "logistics", True),
    ("project_management", "Project Management", "project management", True),
    ("field_installation", "Field Installation", "field", True),
    (
        "programming_and_configuration",
        "Programming and Configuration",
        "engineering",
        True,
    ),
    (
        "testing_and_commissioning",
        "Testing and Commissioning",
        "commissioning",
        True,
    ),
    ("training", "Training", "project management", True),
    ("punch_and_completion", "Punch and Completion", "project management", True),
    ("closeout", "Closeout", "project management", True),
    ("warranty", "Warranty", "service", True),
    ("service_and_support", "Service and Support", "service", True),
    ("asset_lifecycle", "Asset Lifecycle", "service", True),
    (
        "upgrade_or_replacement",
        "Upgrade or Replacement",
        "service",
        True,
    ),
    ("archived", "Archived", "archive", False),
]

_STATUS_ORDER = [status.value for status in LifecycleStageStatus]

_LEGACY_STATUS_TO_STAGE_KEY = {
    ProjectStatus.OPPORTUNITY.value: "opportunity",
    ProjectStatus.INTAKE.value: "bid_intake",
    ProjectStatus.ESTIMATING.value: "estimating",
    ProjectStatus.SUBMITTED.value: "proposal",
    ProjectStatus.AWARDED.value: "award",
    ProjectStatus.ENGINEERING.value: "engineering",
    ProjectStatus.PROCUREMENT.value: "procurement",
    ProjectStatus.ACTIVE.value: "project_management",
    ProjectStatus.CLOSEOUT.value: "closeout",
    ProjectStatus.ARCHIVED.value: "archived",
}

_STAGE_TO_LEGACY_STATUS = {
    "lead": ProjectStatus.OPPORTUNITY.value,
    "opportunity": ProjectStatus.OPPORTUNITY.value,
    "discovery": ProjectStatus.OPPORTUNITY.value,
    "bid_intake": ProjectStatus.INTAKE.value,
    "bid_intelligence": ProjectStatus.INTAKE.value,
    "estimating": ProjectStatus.ESTIMATING.value,
    "proposal": ProjectStatus.SUBMITTED.value,
    "award": ProjectStatus.AWARDED.value,
    "project_initialization": ProjectStatus.AWARDED.value,
    "engineering": ProjectStatus.ENGINEERING.value,
    "submittals": ProjectStatus.ENGINEERING.value,
    "procurement": ProjectStatus.PROCUREMENT.value,
    "logistics_and_receiving": ProjectStatus.PROCUREMENT.value,
    "project_management": ProjectStatus.ACTIVE.value,
    "field_installation": ProjectStatus.ACTIVE.value,
    "programming_and_configuration": ProjectStatus.ACTIVE.value,
    "testing_and_commissioning": ProjectStatus.ACTIVE.value,
    "training": ProjectStatus.ACTIVE.value,
    "punch_and_completion": ProjectStatus.CLOSEOUT.value,
    "closeout": ProjectStatus.CLOSEOUT.value,
    "warranty": ProjectStatus.ACTIVE.value,
    "service_and_support": ProjectStatus.ACTIVE.value,
    "asset_lifecycle": ProjectStatus.ACTIVE.value,
    "upgrade_or_replacement": ProjectStatus.ACTIVE.value,
    "archived": ProjectStatus.ARCHIVED.value,
}


def _required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    return normalized or None


def _optional_list(values: Iterable[Any] | None) -> list[str]:
    return [
        item for item in (_optional_text(value) for value in list(values or [])) if item
    ]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_key(value: Any) -> str:
    normalized = _optional_text(value)
    if normalized is None:
        return ""
    return normalized.replace(" ", "_").replace("-", "_").lower()


def _normalize_stage_key(value: Any) -> str:
    key = _normalize_key(value)
    if not key:
        return ""
    if key in {item[0] for item in _STAGE_DEFINITIONS}:
        return key
    for stage_key, label, _owner_role, _default_applicable in _STAGE_DEFINITIONS:
        if key == _normalize_key(label):
            return stage_key
    if key in _LEGACY_STATUS_TO_STAGE_KEY:
        return _LEGACY_STATUS_TO_STAGE_KEY[key]
    return key


def _legacy_status_for_stage(stage_key: str) -> str:
    normalized = _normalize_stage_key(stage_key)
    return _STAGE_TO_LEGACY_STATUS.get(normalized, ProjectStatus.INTAKE.value)


def _stage_label(stage_key: str) -> str:
    normalized = _normalize_stage_key(stage_key)
    for candidate_key, label, _owner_role, _default_applicable in _STAGE_DEFINITIONS:
        if candidate_key == normalized:
            return label
    return normalized.replace("_", " ").title()


def _stage_owner_role(stage_key: str) -> str | None:
    normalized = _normalize_stage_key(stage_key)
    for candidate_key, _label, owner_role, _default_applicable in _STAGE_DEFINITIONS:
        if candidate_key == normalized:
            return owner_role
    return None


def _stage_default_applicability(stage_key: str) -> bool:
    normalized = _normalize_stage_key(stage_key)
    for candidate_key, _label, _owner_role, default_applicable in _STAGE_DEFINITIONS:
        if candidate_key == normalized:
            return default_applicable
    return True


def _stage_order(stage_key: str) -> int:
    normalized = _normalize_stage_key(stage_key)
    for index, (candidate_key, _label, _owner_role, _default_applicable) in enumerate(
        _STAGE_DEFINITIONS
    ):
        if candidate_key == normalized:
            return index
    return len(_STAGE_DEFINITIONS)


def _ordered_unique_keys(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        key = _normalize_stage_key(value)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    ordered.sort(key=_stage_order)
    return ordered


def _ordered_unique_texts(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = _optional_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _current_timestamp_or(value: Any) -> str:
    normalized = _optional_text(value)
    return normalized or _utc_now()


@dataclass(frozen=True)
class LifecycleStageDefinition:
    key: str
    label: str
    order: int
    owner_role: str | None = None
    default_applicable: bool = True
    optional: bool = False
    terminal: bool = False
    summary_action: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _required_text("key", self.key))
        object.__setattr__(self, "label", _required_text("label", self.label))
        object.__setattr__(self, "owner_role", _optional_text(self.owner_role))
        object.__setattr__(self, "summary_action", _optional_text(self.summary_action))

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "order": int(self.order),
            "owner_role": self.owner_role,
            "default_applicable": bool(self.default_applicable),
            "optional": bool(self.optional),
            "terminal": bool(self.terminal),
            "summary_action": self.summary_action,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LifecycleStageDefinition":
        return cls(
            key=str(payload.get("key") or ""),
            label=str(payload.get("label") or ""),
            order=int(payload.get("order") or 0),
            owner_role=payload.get("owner_role"),
            default_applicable=bool(payload.get("default_applicable", True)),
            optional=bool(payload.get("optional", False)),
            terminal=bool(payload.get("terminal", False)),
            summary_action=payload.get("summary_action"),
        )


@dataclass(frozen=True)
class LifecycleTransitionRequirement:
    category: str
    label: str
    required: bool = True
    satisfied: bool = False
    value: Any = None
    evidence_references: list[str] = field(default_factory=list)
    affected_objects: list[str] = field(default_factory=list)
    source_references: list[str] = field(default_factory=list)
    threshold: float | None = None
    details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": _required_text("category", self.category),
            "label": _required_text("label", self.label),
            "required": bool(self.required),
            "satisfied": bool(self.satisfied),
            "value": self.value,
            "evidence_references": _optional_list(self.evidence_references),
            "affected_objects": _optional_list(self.affected_objects),
            "source_references": _optional_list(self.source_references),
            "threshold": self.threshold,
            "details": _optional_text(self.details),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LifecycleTransitionRequirement":
        return cls(
            category=str(payload.get("category") or ""),
            label=str(payload.get("label") or ""),
            required=bool(payload.get("required", True)),
            satisfied=bool(payload.get("satisfied", False)),
            value=payload.get("value"),
            evidence_references=[
                str(item) for item in list(payload.get("evidence_references") or [])
            ],
            affected_objects=[
                str(item) for item in list(payload.get("affected_objects") or [])
            ],
            source_references=[
                str(item) for item in list(payload.get("source_references") or [])
            ],
            threshold=payload.get("threshold"),
            details=payload.get("details"),
        )


@dataclass(frozen=True)
class LifecycleTransitionDiagnostic:
    code: str
    severity: str
    message: str
    requirement_category: str | None = None
    evidence_references: list[str] = field(default_factory=list)
    source_references: list[str] = field(default_factory=list)
    affected_objects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": _required_text("code", self.code),
            "severity": _required_text("severity", self.severity),
            "message": _required_text("message", self.message),
            "requirement_category": _optional_text(self.requirement_category),
            "evidence_references": _optional_list(self.evidence_references),
            "source_references": _optional_list(self.source_references),
            "affected_objects": _optional_list(self.affected_objects),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LifecycleTransitionDiagnostic":
        return cls(
            code=str(payload.get("code") or ""),
            severity=str(payload.get("severity") or "info"),
            message=str(payload.get("message") or ""),
            requirement_category=payload.get("requirement_category"),
            evidence_references=[
                str(item) for item in list(payload.get("evidence_references") or [])
            ],
            source_references=[
                str(item) for item in list(payload.get("source_references") or [])
            ],
            affected_objects=[
                str(item) for item in list(payload.get("affected_objects") or [])
            ],
        )


@dataclass(frozen=True)
class LifecycleTransition:
    transition_key: str
    action: str
    from_stage_key: str
    to_stage_key: str
    label: str
    required_reason: bool = True
    allowed_source_statuses: list[str] = field(default_factory=list)
    requirement_categories: list[str] = field(default_factory=list)
    optional_only: bool = False
    terminal: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transition_key",
            _required_text("transition_key", self.transition_key),
        )
        object.__setattr__(self, "action", _required_text("action", self.action))
        object.__setattr__(
            self, "from_stage_key", _normalize_stage_key(self.from_stage_key)
        )
        object.__setattr__(
            self, "to_stage_key", _normalize_stage_key(self.to_stage_key)
        )
        object.__setattr__(self, "label", _required_text("label", self.label))
        object.__setattr__(
            self,
            "allowed_source_statuses",
            _ordered_unique_texts(self.allowed_source_statuses),
        )
        object.__setattr__(
            self,
            "requirement_categories",
            _ordered_unique_texts(self.requirement_categories),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_key": self.transition_key,
            "action": self.action,
            "from_stage_key": self.from_stage_key,
            "to_stage_key": self.to_stage_key,
            "label": self.label,
            "required_reason": bool(self.required_reason),
            "allowed_source_statuses": list(self.allowed_source_statuses),
            "requirement_categories": list(self.requirement_categories),
            "optional_only": bool(self.optional_only),
            "terminal": bool(self.terminal),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LifecycleTransition":
        return cls(
            transition_key=str(payload.get("transition_key") or ""),
            action=str(payload.get("action") or ""),
            from_stage_key=str(payload.get("from_stage_key") or ""),
            to_stage_key=str(payload.get("to_stage_key") or ""),
            label=str(payload.get("label") or ""),
            required_reason=bool(payload.get("required_reason", True)),
            allowed_source_statuses=[
                str(item) for item in list(payload.get("allowed_source_statuses") or [])
            ],
            requirement_categories=[
                str(item) for item in list(payload.get("requirement_categories") or [])
            ],
            optional_only=bool(payload.get("optional_only", False)),
            terminal=bool(payload.get("terminal", False)),
        )


@dataclass(frozen=True)
class LifecycleHistoryEvent:
    event_id: str
    project_id: str
    tenant_id: str
    source_stage: str
    destination_stage: str
    source_status: str
    destination_status: str
    actor: str
    timestamp: str
    reason: str
    diagnostics_snapshot: list[LifecycleTransitionDiagnostic] = field(
        default_factory=list
    )
    related_objects: list[dict[str, Any]] = field(default_factory=list)
    source_references: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _required_text("event_id", self.event_id))
        object.__setattr__(
            self, "project_id", _required_text("project_id", self.project_id)
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self, "source_stage", _normalize_stage_key(self.source_stage)
        )
        object.__setattr__(
            self, "destination_stage", _normalize_stage_key(self.destination_stage)
        )
        object.__setattr__(
            self, "source_status", _required_text("source_status", self.source_status)
        )
        object.__setattr__(
            self,
            "destination_status",
            _required_text("destination_status", self.destination_status),
        )
        object.__setattr__(self, "actor", _required_text("actor", self.actor))
        object.__setattr__(
            self, "timestamp", _required_text("timestamp", self.timestamp)
        )
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        object.__setattr__(
            self,
            "diagnostics_snapshot",
            [
                (
                    item
                    if isinstance(item, LifecycleTransitionDiagnostic)
                    else LifecycleTransitionDiagnostic.from_dict(dict(item))
                )
                for item in list(self.diagnostics_snapshot)
            ],
        )
        object.__setattr__(
            self, "related_objects", [dict(item) for item in list(self.related_objects)]
        )
        object.__setattr__(
            self, "source_references", _optional_list(self.source_references)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "source_stage": self.source_stage,
            "destination_stage": self.destination_stage,
            "source_status": self.source_status,
            "destination_status": self.destination_status,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "diagnostics_snapshot": [
                item.to_dict() for item in self.diagnostics_snapshot
            ],
            "related_objects": [dict(item) for item in self.related_objects],
            "source_references": list(self.source_references),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LifecycleHistoryEvent":
        return cls(
            event_id=str(payload.get("event_id") or ""),
            project_id=str(payload.get("project_id") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            source_stage=str(payload.get("source_stage") or ""),
            destination_stage=str(payload.get("destination_stage") or ""),
            source_status=str(payload.get("source_status") or ""),
            destination_status=str(payload.get("destination_status") or ""),
            actor=str(payload.get("actor") or ""),
            timestamp=str(payload.get("timestamp") or _utc_now()),
            reason=str(payload.get("reason") or ""),
            diagnostics_snapshot=[
                LifecycleTransitionDiagnostic.from_dict(dict(item))
                for item in list(payload.get("diagnostics_snapshot") or [])
                if isinstance(item, dict)
            ],
            related_objects=[
                dict(item)
                for item in list(payload.get("related_objects") or [])
                if isinstance(item, dict)
            ],
            source_references=[
                str(item) for item in list(payload.get("source_references") or [])
            ],
        )


@dataclass(frozen=True)
class LifecycleReadiness:
    ready: bool
    needs_review: bool
    blocked: bool
    diagnostics: list[LifecycleTransitionDiagnostic] = field(default_factory=list)
    missing_requirements: list[LifecycleTransitionRequirement] = field(
        default_factory=list
    )
    recommended_next_action: str | None = None
    affected_objects: list[str] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": bool(self.ready),
            "needs_review": bool(self.needs_review),
            "blocked": bool(self.blocked),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "missing_requirements": [
                item.to_dict() for item in self.missing_requirements
            ],
            "recommended_next_action": _optional_text(self.recommended_next_action),
            "affected_objects": _optional_list(self.affected_objects),
            "evidence_references": _optional_list(self.evidence_references),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LifecycleReadiness":
        return cls(
            ready=bool(payload.get("ready", False)),
            needs_review=bool(payload.get("needs_review", False)),
            blocked=bool(payload.get("blocked", False)),
            diagnostics=[
                LifecycleTransitionDiagnostic.from_dict(dict(item))
                for item in list(payload.get("diagnostics") or [])
                if isinstance(item, dict)
            ],
            missing_requirements=[
                LifecycleTransitionRequirement.from_dict(dict(item))
                for item in list(payload.get("missing_requirements") or [])
                if isinstance(item, dict)
            ],
            recommended_next_action=payload.get("recommended_next_action"),
            affected_objects=[
                str(item) for item in list(payload.get("affected_objects") or [])
            ],
            evidence_references=[
                str(item) for item in list(payload.get("evidence_references") or [])
            ],
        )


@dataclass(frozen=True)
class LifecycleStageState:
    stage_key: str
    label: str
    status: LifecycleStageStatus
    applicable: bool = True
    owner_role: str | None = None
    entered_at: str | None = None
    completed_at: str | None = None
    transition_reason: str | None = None
    transition_actor: str | None = None
    readiness: LifecycleReadiness | None = None
    diagnostics: list[LifecycleTransitionDiagnostic] = field(default_factory=list)
    requirements: list[LifecycleTransitionRequirement] = field(default_factory=list)
    next_action: str | None = None
    evidence_references: list[str] = field(default_factory=list)
    related_objects: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage_key", _normalize_stage_key(self.stage_key))
        object.__setattr__(self, "label", _required_text("label", self.label))
        if not isinstance(self.status, LifecycleStageStatus):
            object.__setattr__(self, "status", LifecycleStageStatus(str(self.status)))
        object.__setattr__(self, "owner_role", _optional_text(self.owner_role))
        object.__setattr__(self, "entered_at", _optional_text(self.entered_at))
        object.__setattr__(self, "completed_at", _optional_text(self.completed_at))
        object.__setattr__(
            self, "transition_reason", _optional_text(self.transition_reason)
        )
        object.__setattr__(
            self, "transition_actor", _optional_text(self.transition_actor)
        )
        object.__setattr__(
            self,
            "readiness",
            (
                self.readiness
                if self.readiness is None
                else (
                    self.readiness
                    if isinstance(self.readiness, LifecycleReadiness)
                    else LifecycleReadiness.from_dict(dict(self.readiness))
                )
            ),
        )
        object.__setattr__(
            self,
            "diagnostics",
            [
                (
                    item
                    if isinstance(item, LifecycleTransitionDiagnostic)
                    else LifecycleTransitionDiagnostic.from_dict(dict(item))
                )
                for item in list(self.diagnostics)
            ],
        )
        object.__setattr__(
            self,
            "requirements",
            [
                (
                    item
                    if isinstance(item, LifecycleTransitionRequirement)
                    else LifecycleTransitionRequirement.from_dict(dict(item))
                )
                for item in list(self.requirements)
            ],
        )
        object.__setattr__(self, "next_action", _optional_text(self.next_action))
        object.__setattr__(
            self, "evidence_references", _optional_list(self.evidence_references)
        )
        object.__setattr__(
            self, "related_objects", _optional_list(self.related_objects)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_key": self.stage_key,
            "label": self.label,
            "status": self.status.value,
            "applicable": bool(self.applicable),
            "owner_role": self.owner_role,
            "entered_at": self.entered_at,
            "completed_at": self.completed_at,
            "transition_reason": self.transition_reason,
            "transition_actor": self.transition_actor,
            "readiness": (
                self.readiness.to_dict() if self.readiness is not None else None
            ),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "requirements": [item.to_dict() for item in self.requirements],
            "next_action": self.next_action,
            "evidence_references": list(self.evidence_references),
            "related_objects": list(self.related_objects),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LifecycleStageState":
        readiness_payload = payload.get("readiness")
        return cls(
            stage_key=str(payload.get("stage_key") or ""),
            label=str(payload.get("label") or ""),
            status=LifecycleStageStatus(
                str(payload.get("status") or LifecycleStageStatus.NOT_STARTED.value)
            ),
            applicable=bool(payload.get("applicable", True)),
            owner_role=payload.get("owner_role"),
            entered_at=payload.get("entered_at"),
            completed_at=payload.get("completed_at"),
            transition_reason=payload.get("transition_reason"),
            transition_actor=payload.get("transition_actor"),
            readiness=(
                LifecycleReadiness.from_dict(dict(readiness_payload))
                if isinstance(readiness_payload, dict)
                else None
            ),
            diagnostics=[
                LifecycleTransitionDiagnostic.from_dict(dict(item))
                for item in list(payload.get("diagnostics") or [])
                if isinstance(item, dict)
            ],
            requirements=[
                LifecycleTransitionRequirement.from_dict(dict(item))
                for item in list(payload.get("requirements") or [])
                if isinstance(item, dict)
            ],
            next_action=payload.get("next_action"),
            evidence_references=[
                str(item) for item in list(payload.get("evidence_references") or [])
            ],
            related_objects=[
                str(item) for item in list(payload.get("related_objects") or [])
            ],
        )


@dataclass(frozen=True)
class LifecycleDefinition:
    definition_key: str
    schema_version: str = AV_LIFECYCLE_SCHEMA_VERSION
    stages: list[LifecycleStageDefinition] = field(default_factory=list)
    transitions: list[LifecycleTransition] = field(default_factory=list)
    default_applicable_stage_keys: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "definition_key",
            _required_text("definition_key", self.definition_key),
        )
        object.__setattr__(
            self,
            "schema_version",
            _required_text("schema_version", self.schema_version),
        )
        stages = [
            (
                stage
                if isinstance(stage, LifecycleStageDefinition)
                else LifecycleStageDefinition.from_dict(dict(stage))
            )
            for stage in list(self.stages)
        ]
        stages.sort(key=lambda item: item.order)
        object.__setattr__(self, "stages", stages)
        object.__setattr__(
            self,
            "transitions",
            [
                (
                    transition
                    if isinstance(transition, LifecycleTransition)
                    else LifecycleTransition.from_dict(dict(transition))
                )
                for transition in list(self.transitions)
            ],
        )
        object.__setattr__(
            self,
            "default_applicable_stage_keys",
            _ordered_unique_keys(
                self.default_applicable_stage_keys
                or [
                    stage.key
                    for stage in stages
                    if stage.default_applicable and not stage.terminal
                ]
            ),
        )

    def stage(self, stage_key: str) -> LifecycleStageDefinition:
        normalized = _normalize_stage_key(stage_key)
        for stage in self.stages:
            if stage.key == normalized:
                return stage
        raise KeyError(stage_key)

    def transition(self, transition_key: str) -> LifecycleTransition:
        normalized = _normalize_key(transition_key)
        for transition in self.transitions:
            if _normalize_key(transition.transition_key) == normalized:
                return transition
        raise KeyError(transition_key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition_key": self.definition_key,
            "schema_version": self.schema_version,
            "stages": [stage.to_dict() for stage in self.stages],
            "transitions": [transition.to_dict() for transition in self.transitions],
            "default_applicable_stage_keys": list(self.default_applicable_stage_keys),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LifecycleDefinition":
        return cls(
            definition_key=str(
                payload.get("definition_key") or AV_LIFECYCLE_DEFINITION_KEY
            ),
            schema_version=str(
                payload.get("schema_version") or AV_LIFECYCLE_SCHEMA_VERSION
            ),
            stages=[
                LifecycleStageDefinition.from_dict(dict(item))
                for item in list(payload.get("stages") or [])
                if isinstance(item, dict)
            ],
            transitions=[
                LifecycleTransition.from_dict(dict(item))
                for item in list(payload.get("transitions") or [])
                if isinstance(item, dict)
            ],
            default_applicable_stage_keys=[
                str(item)
                for item in list(payload.get("default_applicable_stage_keys") or [])
            ],
        )


@dataclass(frozen=True)
class LifecyclePlan:
    project_id: str
    tenant_id: str
    current_stage_key: str
    current_stage_status: LifecycleStageStatus
    applicable_stage_keys: list[str]
    completed_stage_keys: list[str] = field(default_factory=list)
    skipped_stage_keys: list[str] = field(default_factory=list)
    blocked_stage_keys: list[str] = field(default_factory=list)
    current_owner_role: str | None = None
    entered_at: str | None = None
    completed_at: str | None = None
    transition_reason: str | None = None
    transition_actor: str | None = None
    readiness: LifecycleReadiness | None = None
    stage_states: list[LifecycleStageState] = field(default_factory=list)
    history_events: list[LifecycleHistoryEvent] = field(default_factory=list)
    resume_stage_key: str | None = None
    legacy_project_status: str | None = None
    source_references: list[str] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)
    schema_version: str = AV_LIFECYCLE_SCHEMA_VERSION
    definition_key: str = AV_LIFECYCLE_DEFINITION_KEY

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "project_id", _required_text("project_id", self.project_id)
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self, "current_stage_key", _normalize_stage_key(self.current_stage_key)
        )
        if not isinstance(self.current_stage_status, LifecycleStageStatus):
            object.__setattr__(
                self,
                "current_stage_status",
                LifecycleStageStatus(str(self.current_stage_status)),
            )
        object.__setattr__(
            self,
            "applicable_stage_keys",
            _ordered_unique_keys(self.applicable_stage_keys),
        )
        object.__setattr__(
            self,
            "completed_stage_keys",
            _ordered_unique_keys(self.completed_stage_keys),
        )
        object.__setattr__(
            self, "skipped_stage_keys", _ordered_unique_keys(self.skipped_stage_keys)
        )
        object.__setattr__(
            self, "blocked_stage_keys", _ordered_unique_keys(self.blocked_stage_keys)
        )
        object.__setattr__(
            self, "current_owner_role", _optional_text(self.current_owner_role)
        )
        object.__setattr__(self, "entered_at", _optional_text(self.entered_at))
        object.__setattr__(self, "completed_at", _optional_text(self.completed_at))
        object.__setattr__(
            self, "transition_reason", _optional_text(self.transition_reason)
        )
        object.__setattr__(
            self, "transition_actor", _optional_text(self.transition_actor)
        )
        object.__setattr__(
            self,
            "readiness",
            (
                self.readiness
                if self.readiness is None
                else (
                    self.readiness
                    if isinstance(self.readiness, LifecycleReadiness)
                    else LifecycleReadiness.from_dict(dict(self.readiness))
                )
            ),
        )
        object.__setattr__(
            self,
            "stage_states",
            [
                (
                    stage
                    if isinstance(stage, LifecycleStageState)
                    else LifecycleStageState.from_dict(dict(stage))
                )
                for stage in list(self.stage_states)
            ],
        )
        object.__setattr__(
            self,
            "history_events",
            [
                (
                    event
                    if isinstance(event, LifecycleHistoryEvent)
                    else LifecycleHistoryEvent.from_dict(dict(event))
                )
                for event in list(self.history_events)
            ],
        )
        object.__setattr__(
            self, "resume_stage_key", _optional_text(self.resume_stage_key)
        )
        object.__setattr__(
            self, "legacy_project_status", _optional_text(self.legacy_project_status)
        )
        object.__setattr__(
            self, "source_references", _optional_list(self.source_references)
        )
        object.__setattr__(
            self, "evidence_references", _optional_list(self.evidence_references)
        )
        object.__setattr__(
            self,
            "schema_version",
            _required_text("schema_version", self.schema_version),
        )
        object.__setattr__(
            self,
            "definition_key",
            _required_text("definition_key", self.definition_key),
        )

    @property
    def current_stage(self) -> LifecycleStageState:
        for stage in self.stage_states:
            if stage.stage_key == self.current_stage_key:
                return stage
        return LifecycleStageState(
            stage_key=self.current_stage_key,
            label=_stage_label(self.current_stage_key),
            status=self.current_stage_status,
            applicable=True,
            owner_role=self.current_owner_role,
            entered_at=self.entered_at,
            completed_at=self.completed_at,
            transition_reason=self.transition_reason,
            transition_actor=self.transition_actor,
            readiness=self.readiness,
            evidence_references=list(self.evidence_references),
        )

    def stage(self, stage_key: str) -> LifecycleStageState | None:
        normalized = _normalize_stage_key(stage_key)
        for stage in self.stage_states:
            if stage.stage_key == normalized:
                return stage
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "current_stage_key": self.current_stage_key,
            "current_stage_status": self.current_stage_status.value,
            "applicable_stage_keys": list(self.applicable_stage_keys),
            "completed_stage_keys": list(self.completed_stage_keys),
            "skipped_stage_keys": list(self.skipped_stage_keys),
            "blocked_stage_keys": list(self.blocked_stage_keys),
            "current_owner_role": self.current_owner_role,
            "entered_at": self.entered_at,
            "completed_at": self.completed_at,
            "transition_reason": self.transition_reason,
            "transition_actor": self.transition_actor,
            "readiness": (
                self.readiness.to_dict() if self.readiness is not None else None
            ),
            "stage_states": [stage.to_dict() for stage in self.stage_states],
            "history_events": [event.to_dict() for event in self.history_events],
            "resume_stage_key": self.resume_stage_key,
            "legacy_project_status": self.legacy_project_status,
            "source_references": list(self.source_references),
            "evidence_references": list(self.evidence_references),
            "schema_version": self.schema_version,
            "definition_key": self.definition_key,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LifecyclePlan":
        readiness_payload = payload.get("readiness")
        return cls(
            project_id=str(payload.get("project_id") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            current_stage_key=str(payload.get("current_stage_key") or ""),
            current_stage_status=LifecycleStageStatus(
                str(
                    payload.get("current_stage_status")
                    or LifecycleStageStatus.NOT_STARTED.value
                )
            ),
            applicable_stage_keys=[
                str(item) for item in list(payload.get("applicable_stage_keys") or [])
            ],
            completed_stage_keys=[
                str(item) for item in list(payload.get("completed_stage_keys") or [])
            ],
            skipped_stage_keys=[
                str(item) for item in list(payload.get("skipped_stage_keys") or [])
            ],
            blocked_stage_keys=[
                str(item) for item in list(payload.get("blocked_stage_keys") or [])
            ],
            current_owner_role=payload.get("current_owner_role"),
            entered_at=payload.get("entered_at"),
            completed_at=payload.get("completed_at"),
            transition_reason=payload.get("transition_reason"),
            transition_actor=payload.get("transition_actor"),
            readiness=(
                LifecycleReadiness.from_dict(dict(readiness_payload))
                if isinstance(readiness_payload, dict)
                else None
            ),
            stage_states=[
                LifecycleStageState.from_dict(dict(item))
                for item in list(payload.get("stage_states") or [])
                if isinstance(item, dict)
            ],
            history_events=[
                LifecycleHistoryEvent.from_dict(dict(item))
                for item in list(payload.get("history_events") or [])
                if isinstance(item, dict)
            ],
            resume_stage_key=payload.get("resume_stage_key"),
            legacy_project_status=payload.get("legacy_project_status"),
            source_references=[
                str(item) for item in list(payload.get("source_references") or [])
            ],
            evidence_references=[
                str(item) for item in list(payload.get("evidence_references") or [])
            ],
            schema_version=str(
                payload.get("schema_version") or AV_LIFECYCLE_SCHEMA_VERSION
            ),
            definition_key=str(
                payload.get("definition_key") or AV_LIFECYCLE_DEFINITION_KEY
            ),
        )


def default_lifecycle_definition() -> LifecycleDefinition:
    transitions: list[LifecycleTransition] = []
    for index, (stage_key, _label, _owner_role, _default_applicable) in enumerate(
        _STAGE_DEFINITIONS[:-1]
    ):
        next_stage_key = _STAGE_DEFINITIONS[index + 1][0]
        if next_stage_key == "archived":
            continue
        transitions.append(
            LifecycleTransition(
                transition_key=f"advance_to_{next_stage_key}",
                action="advance",
                from_stage_key=stage_key,
                to_stage_key=next_stage_key,
                label=f"Advance to {_stage_label(next_stage_key)}",
                required_reason=True,
                allowed_source_statuses=[
                    LifecycleStageStatus.ACTIVE.value,
                    LifecycleStageStatus.NEEDS_REVIEW.value,
                ],
            )
        )
        transitions.append(
            LifecycleTransition(
                transition_key=f"return_to_{stage_key}",
                action="return",
                from_stage_key=next_stage_key,
                to_stage_key=stage_key,
                label=f"Return to {_stage_label(stage_key)}",
                required_reason=True,
                allowed_source_statuses=[
                    LifecycleStageStatus.ACTIVE.value,
                    LifecycleStageStatus.NEEDS_REVIEW.value,
                    LifecycleStageStatus.COMPLETE.value,
                ],
            )
        )

    transitions.extend(
        [
            LifecycleTransition(
                transition_key="skip_optional_stage",
                action="skip",
                from_stage_key="bid_intake",
                to_stage_key="bid_intelligence",
                label="Skip optional stage",
                required_reason=True,
                allowed_source_statuses=[
                    LifecycleStageStatus.ACTIVE.value,
                    LifecycleStageStatus.NEEDS_REVIEW.value,
                ],
                optional_only=True,
            ),
            LifecycleTransition(
                transition_key="archive_project",
                action="archive",
                from_stage_key="project_management",
                to_stage_key="archived",
                label="Archive project",
                required_reason=True,
                allowed_source_statuses=_STATUS_ORDER,
                terminal=True,
            ),
            LifecycleTransition(
                transition_key="restore_project",
                action="restore",
                from_stage_key="archived",
                to_stage_key="project_management",
                label="Restore project",
                required_reason=True,
                allowed_source_statuses=[LifecycleStageStatus.ARCHIVED.value],
            ),
            LifecycleTransition(
                transition_key="reopen_stage",
                action="reopen",
                from_stage_key="project_management",
                to_stage_key="project_management",
                label="Reopen current stage",
                required_reason=True,
                allowed_source_statuses=[
                    LifecycleStageStatus.COMPLETE.value,
                    LifecycleStageStatus.SKIPPED.value,
                ],
            ),
        ]
    )

    stages = [
        LifecycleStageDefinition(
            key=key,
            label=label,
            order=index,
            owner_role=owner_role,
            default_applicable=default_applicable,
            optional=key
            in {
                "lead",
                "discovery",
                "award",
                "training",
                "warranty",
                "service_and_support",
                "asset_lifecycle",
                "upgrade_or_replacement",
            },
            terminal=(key == "archived"),
            summary_action=(
                f"Advance to {label}" if key != "archived" else "Archive project"
            ),
        )
        for index, (key, label, owner_role, default_applicable) in enumerate(
            _STAGE_DEFINITIONS
        )
    ]
    return LifecycleDefinition(
        definition_key=AV_LIFECYCLE_DEFINITION_KEY,
        stages=stages,
        transitions=transitions,
    )


def legacy_stage_key_from_status(status: str | ProjectStatus | None) -> str:
    if status is None:
        return "bid_intake"
    value = getattr(status, "value", status)
    normalized = _normalize_key(value)
    return _LEGACY_STATUS_TO_STAGE_KEY.get(normalized, "bid_intake")


def legacy_status_for_stage(stage_key: str) -> str:
    return _legacy_status_for_stage(stage_key)


def normalize_stage_key(value: Any) -> str:
    return _normalize_stage_key(value)


def build_default_stage_states(
    definition: LifecycleDefinition,
    current_stage_key: str,
    *,
    applicable_stage_keys: list[str] | None = None,
    current_status: LifecycleStageStatus | str = LifecycleStageStatus.ACTIVE,
    owner_role: str | None = None,
    entered_at: str | None = None,
    completed_at: str | None = None,
    transition_reason: str | None = None,
    transition_actor: str | None = None,
    readiness: LifecycleReadiness | None = None,
    blocked_stage_keys: list[str] | None = None,
    skipped_stage_keys: list[str] | None = None,
    completed_stage_keys: list[str] | None = None,
) -> list[LifecycleStageState]:
    current_stage_key = _normalize_stage_key(current_stage_key)
    applicable = _ordered_unique_keys(
        applicable_stage_keys or definition.default_applicable_stage_keys
    )
    blocked = set(_ordered_unique_keys(blocked_stage_keys or []))
    skipped = set(_ordered_unique_keys(skipped_stage_keys or []))
    completed = set(_ordered_unique_keys(completed_stage_keys or []))
    current_index = next(
        (
            index
            for index, stage in enumerate(definition.stages)
            if stage.key == current_stage_key
        ),
        0,
    )
    states: list[LifecycleStageState] = []
    encountered_current = False
    for index, stage in enumerate(definition.stages):
        if stage.key not in applicable and stage.key != "archived":
            status = LifecycleStageStatus.SKIPPED
        elif stage.key == "archived":
            status = (
                LifecycleStageStatus.ARCHIVED
                if current_stage_key == "archived"
                else LifecycleStageStatus.NOT_STARTED
            )
        elif stage.key in skipped:
            status = LifecycleStageStatus.SKIPPED
        elif stage.key in completed:
            status = LifecycleStageStatus.COMPLETE
        elif stage.key in blocked:
            status = LifecycleStageStatus.BLOCKED
        elif stage.key == current_stage_key:
            status = (
                current_status
                if isinstance(current_status, LifecycleStageStatus)
                else LifecycleStageStatus(str(current_status))
            )
            encountered_current = True
        elif index < current_index:
            status = LifecycleStageStatus.COMPLETE
        elif encountered_current:
            status = LifecycleStageStatus.NOT_STARTED
        elif index == current_index + 1:
            status = LifecycleStageStatus.AVAILABLE
        else:
            status = LifecycleStageStatus.NOT_STARTED

        state = LifecycleStageState(
            stage_key=stage.key,
            label=stage.label,
            status=status,
            applicable=stage.key in applicable or stage.key == "archived",
            owner_role=stage.owner_role or owner_role,
            entered_at=(entered_at if stage.key == current_stage_key else None),
            completed_at=(completed_at if stage.key in completed else None),
            transition_reason=(
                transition_reason if stage.key == current_stage_key else None
            ),
            transition_actor=(
                transition_actor if stage.key == current_stage_key else None
            ),
            readiness=readiness if stage.key == current_stage_key else None,
            diagnostics=list(
                readiness.diagnostics
                if readiness and stage.key == current_stage_key
                else []
            ),
            requirements=list(
                readiness.missing_requirements
                if readiness and stage.key == current_stage_key
                else []
            ),
            next_action=stage.summary_action,
            evidence_references=[],
            related_objects=[],
        )
        states.append(state)
    return states


def build_default_lifecycle_plan(
    *,
    project_id: str,
    tenant_id: str,
    current_stage_key: str | None = None,
    current_stage_status: LifecycleStageStatus | str = LifecycleStageStatus.ACTIVE,
    applicable_stage_keys: list[str] | None = None,
    current_owner_role: str | None = None,
    entered_at: str | None = None,
    completed_at: str | None = None,
    transition_reason: str | None = None,
    transition_actor: str | None = None,
    readiness: LifecycleReadiness | None = None,
    history_events: list[LifecycleHistoryEvent] | None = None,
    resume_stage_key: str | None = None,
    legacy_project_status: str | ProjectStatus | None = None,
    evidence_references: list[str] | None = None,
    source_references: list[str] | None = None,
    blocked_stage_keys: list[str] | None = None,
    skipped_stage_keys: list[str] | None = None,
    completed_stage_keys: list[str] | None = None,
) -> LifecyclePlan:
    definition = default_lifecycle_definition()
    stage_key = _normalize_stage_key(
        current_stage_key or legacy_stage_key_from_status(legacy_project_status)
    )
    if stage_key == "":
        stage_key = "bid_intake"
    if applicable_stage_keys is None:
        applicable_stage_keys = list(definition.default_applicable_stage_keys)
    states = build_default_stage_states(
        definition,
        stage_key,
        applicable_stage_keys=applicable_stage_keys,
        current_status=current_stage_status,
        owner_role=current_owner_role,
        entered_at=entered_at,
        completed_at=completed_at,
        transition_reason=transition_reason,
        transition_actor=transition_actor,
        readiness=readiness,
        blocked_stage_keys=blocked_stage_keys,
        skipped_stage_keys=skipped_stage_keys,
        completed_stage_keys=completed_stage_keys,
    )
    current_stage = next(
        (item for item in states if item.stage_key == stage_key), states[0]
    )
    derived_readiness = readiness or LifecycleReadiness(
        ready=current_stage.status
        in {
            LifecycleStageStatus.AVAILABLE,
            LifecycleStageStatus.ACTIVE,
            LifecycleStageStatus.COMPLETE,
        },
        needs_review=current_stage.status is LifecycleStageStatus.NEEDS_REVIEW,
        blocked=current_stage.status is LifecycleStageStatus.BLOCKED,
        diagnostics=list(current_stage.diagnostics),
        missing_requirements=list(current_stage.requirements),
        recommended_next_action=current_stage.next_action,
        affected_objects=[],
        evidence_references=list(evidence_references or []),
    )
    return LifecyclePlan(
        project_id=project_id,
        tenant_id=tenant_id,
        current_stage_key=stage_key,
        current_stage_status=current_stage.status,
        applicable_stage_keys=list(applicable_stage_keys),
        completed_stage_keys=[
            item.stage_key
            for item in states
            if item.status is LifecycleStageStatus.COMPLETE
        ],
        skipped_stage_keys=[
            item.stage_key
            for item in states
            if item.status is LifecycleStageStatus.SKIPPED
        ],
        blocked_stage_keys=[
            item.stage_key
            for item in states
            if item.status is LifecycleStageStatus.BLOCKED
        ],
        current_owner_role=current_owner_role or current_stage.owner_role,
        entered_at=entered_at
        or (current_stage.entered_at if current_stage.entered_at else _utc_now()),
        completed_at=completed_at,
        transition_reason=transition_reason,
        transition_actor=transition_actor,
        readiness=derived_readiness,
        stage_states=states,
        history_events=list(history_events or []),
        resume_stage_key=_normalize_stage_key(resume_stage_key) or None,
        legacy_project_status=(
            _optional_text(
                getattr(legacy_project_status, "value", legacy_project_status)
            )
            or _legacy_status_for_stage(stage_key)
        ),
        source_references=_optional_list(source_references),
        evidence_references=_optional_list(evidence_references),
        schema_version=AV_LIFECYCLE_SCHEMA_VERSION,
        definition_key=AV_LIFECYCLE_DEFINITION_KEY,
    )


class AVLifecycleEngine:
    """Deterministic AV lifecycle engine."""

    def __init__(self, definition: LifecycleDefinition | None = None) -> None:
        self.definition = definition or default_lifecycle_definition()

    @classmethod
    def default(cls) -> "AVLifecycleEngine":
        return cls(default_lifecycle_definition())

    def stage_definition(self, stage_key: str) -> LifecycleStageDefinition:
        return self.definition.stage(stage_key)

    def stage_label(self, stage_key: str) -> str:
        return self.stage_definition(stage_key).label

    def stage_order(self, stage_key: str) -> int:
        return self.stage_definition(stage_key).order

    def normalize_stage_key(self, value: Any) -> str:
        return _normalize_stage_key(value)

    def build_plan(
        self,
        *,
        project_id: str,
        tenant_id: str,
        current_stage_key: str | None = None,
        current_stage_status: LifecycleStageStatus | str = LifecycleStageStatus.ACTIVE,
        applicable_stage_keys: list[str] | None = None,
        current_owner_role: str | None = None,
        entered_at: str | None = None,
        completed_at: str | None = None,
        transition_reason: str | None = None,
        transition_actor: str | None = None,
        readiness: LifecycleReadiness | None = None,
        history_events: list[LifecycleHistoryEvent] | None = None,
        resume_stage_key: str | None = None,
        legacy_project_status: str | ProjectStatus | None = None,
        evidence_references: list[str] | None = None,
        source_references: list[str] | None = None,
        blocked_stage_keys: list[str] | None = None,
        skipped_stage_keys: list[str] | None = None,
        completed_stage_keys: list[str] | None = None,
    ) -> LifecyclePlan:
        return build_default_lifecycle_plan(
            project_id=project_id,
            tenant_id=tenant_id,
            current_stage_key=current_stage_key,
            current_stage_status=current_stage_status,
            applicable_stage_keys=applicable_stage_keys,
            current_owner_role=current_owner_role,
            entered_at=entered_at,
            completed_at=completed_at,
            transition_reason=transition_reason,
            transition_actor=transition_actor,
            readiness=readiness,
            history_events=history_events,
            resume_stage_key=resume_stage_key,
            legacy_project_status=legacy_project_status,
            evidence_references=evidence_references,
            source_references=source_references,
            blocked_stage_keys=blocked_stage_keys,
            skipped_stage_keys=skipped_stage_keys,
            completed_stage_keys=completed_stage_keys,
        )

    def build_plan_from_project(
        self,
        project: Any,
        *,
        tenant_id: str,
        applicable_stage_keys: list[str] | None = None,
        current_stage_key: str | None = None,
        current_stage_status: LifecycleStageStatus | str = LifecycleStageStatus.ACTIVE,
        resume_stage_key: str | None = None,
        history_events: list[LifecycleHistoryEvent] | None = None,
        evidence_references: list[str] | None = None,
        source_references: list[str] | None = None,
    ) -> LifecyclePlan:
        project_id = _required_text(
            "project_id", str(getattr(project, "project_id", None) or "")
        )
        legacy_status = getattr(project, "status", ProjectStatus.INTAKE)
        if current_stage_key is None:
            current_stage_key = legacy_stage_key_from_status(legacy_status)
        if applicable_stage_keys is None:
            applicable_stage_keys = list(self.definition.default_applicable_stage_keys)
        return self.build_plan(
            project_id=project_id,
            tenant_id=tenant_id,
            current_stage_key=current_stage_key,
            current_stage_status=current_stage_status,
            applicable_stage_keys=applicable_stage_keys,
            current_owner_role=None,
            legacy_project_status=legacy_status,
            history_events=history_events,
            resume_stage_key=resume_stage_key,
            evidence_references=evidence_references,
            source_references=source_references,
        )

    def available_transitions(self, plan: LifecyclePlan) -> list[LifecycleTransition]:
        self._ensure_plan_compatibility(plan)
        transitions: list[LifecycleTransition] = []
        current_index = self.stage_order(plan.current_stage_key)
        applicable = plan.applicable_stage_keys or list(
            self.definition.default_applicable_stage_keys
        )

        if plan.current_stage_key == "archived":
            try:
                transitions.append(self.definition.transition("restore_project"))
            except KeyError:
                pass
            return transitions

        if current_index + 1 < len(self.definition.stages):
            next_stage = self.definition.stages[current_index + 1]
            if next_stage.key in applicable or next_stage.terminal:
                transitions.append(
                    LifecycleTransition(
                        transition_key=f"advance_to_{next_stage.key}",
                        action="advance",
                        from_stage_key=plan.current_stage_key,
                        to_stage_key=next_stage.key,
                        label=f"Advance to {next_stage.label}",
                        required_reason=True,
                        allowed_source_statuses=[
                            LifecycleStageStatus.ACTIVE.value,
                            LifecycleStageStatus.NEEDS_REVIEW.value,
                        ],
                    )
                )

        previous_stage = self._previous_applicable_stage(plan)
        if previous_stage is not None:
            transitions.append(
                LifecycleTransition(
                    transition_key=f"return_to_{previous_stage.key}",
                    action="return",
                    from_stage_key=plan.current_stage_key,
                    to_stage_key=previous_stage.key,
                    label=f"Return to {previous_stage.label}",
                    required_reason=True,
                    allowed_source_statuses=[
                        LifecycleStageStatus.ACTIVE.value,
                        LifecycleStageStatus.NEEDS_REVIEW.value,
                        LifecycleStageStatus.COMPLETE.value,
                    ],
                )
            )

        current_stage = self.stage_definition(plan.current_stage_key)
        if current_stage.optional and plan.current_stage_status in {
            LifecycleStageStatus.ACTIVE,
            LifecycleStageStatus.NEEDS_REVIEW,
        }:
            try:
                transitions.append(self.definition.transition("skip_optional_stage"))
            except KeyError:
                pass

        if plan.current_stage_status is not LifecycleStageStatus.ARCHIVED:
            try:
                transitions.append(self.definition.transition("archive_project"))
            except KeyError:
                pass

        return transitions

    def evaluate_readiness(
        self,
        plan: LifecyclePlan,
        *,
        requirements: list[LifecycleTransitionRequirement] | None = None,
        diagnostics: list[LifecycleTransitionDiagnostic] | None = None,
        recommended_next_action: str | None = None,
        affected_objects: list[str] | None = None,
        evidence_references: list[str] | None = None,
    ) -> LifecycleReadiness:
        self._ensure_plan_compatibility(plan)
        requirements = list(requirements or [])
        diagnostics = list(diagnostics or [])
        missing_requirements = [
            requirement
            for requirement in requirements
            if requirement.required and not requirement.satisfied
        ]
        blocked = any(
            item.severity.lower() in {"error", "blocked"} for item in diagnostics
        ) or bool(missing_requirements)
        needs_review = any(
            item.severity.lower() == "warning" for item in diagnostics
        ) or plan.current_stage_status in {
            LifecycleStageStatus.NEEDS_REVIEW,
        }
        ready = not blocked and not needs_review
        next_action = recommended_next_action or self._recommended_next_action(plan)
        return LifecycleReadiness(
            ready=ready,
            needs_review=needs_review,
            blocked=blocked,
            diagnostics=diagnostics,
            missing_requirements=missing_requirements,
            recommended_next_action=next_action,
            affected_objects=_optional_list(affected_objects),
            evidence_references=_optional_list(evidence_references),
        )

    def transition(
        self,
        plan: LifecyclePlan,
        transition_key: str,
        *,
        actor: str,
        reason: str,
        tenant_id: str,
        requirements: list[LifecycleTransitionRequirement] | None = None,
        diagnostics: list[LifecycleTransitionDiagnostic] | None = None,
        related_objects: list[dict[str, Any]] | None = None,
        source_references: list[str] | None = None,
        event_timestamp: str | None = None,
    ) -> tuple[LifecyclePlan, LifecycleHistoryEvent]:
        self._ensure_plan_compatibility(plan)
        normalized_key = _normalize_key(transition_key)
        if tenant_id != plan.tenant_id:
            raise ValueError("lifecycle tenant mismatch")
        if not actor or not str(actor).strip():
            raise ValueError("actor cannot be blank")
        if not reason or not str(reason).strip():
            raise ValueError("reason cannot be blank")

        requirement_rows = list(requirements or [])
        diagnostic_rows = list(diagnostics or [])
        active_requirement_categories = {
            item.category
            for item in requirement_rows
            if item.required and not item.satisfied
        }
        if normalized_key in {"archive_project", "archive"}:
            return self._archive_plan(
                plan,
                actor=str(actor).strip(),
                reason=str(reason).strip(),
                diagnostics=diagnostic_rows,
                related_objects=related_objects,
                source_references=source_references,
                event_timestamp=event_timestamp,
            )
        if normalized_key in {"restore_project", "restore"}:
            return self._restore_plan(
                plan,
                actor=str(actor).strip(),
                reason=str(reason).strip(),
                diagnostics=diagnostic_rows,
                related_objects=related_objects,
                source_references=source_references,
                event_timestamp=event_timestamp,
            )

        if plan.current_stage_status is LifecycleStageStatus.ARCHIVED:
            raise ValueError("archived projects must be restored before transitioning")

        transition = self._resolve_transition(plan, normalized_key)
        if transition is None:
            raise ValueError(f"transition not allowed: {transition_key}")
        if (
            transition.from_stage_key != plan.current_stage_key
            and transition.action != "skip"
        ):
            raise ValueError("transition does not match the current stage")
        if (
            transition.allowed_source_statuses
            and plan.current_stage_status.value
            not in transition.allowed_source_statuses
        ):
            raise ValueError("current stage status is not eligible for this transition")
        if transition.required_reason and not reason.strip():
            raise ValueError("reason cannot be blank")
        if (
            transition.optional_only
            and not self.stage_definition(plan.current_stage_key).optional
        ):
            raise ValueError("current stage is not optional")

        if active_requirement_categories:
            raise ValueError(
                "lifecycle transition blocked by unsatisfied requirements: "
                + ", ".join(sorted(active_requirement_categories))
            )

        if transition.action == "advance":
            return self._advance_plan(
                plan,
                transition=transition,
                actor=str(actor).strip(),
                reason=str(reason).strip(),
                diagnostics=diagnostic_rows,
                related_objects=related_objects,
                source_references=source_references,
                event_timestamp=event_timestamp,
            )
        if transition.action in {"return", "reopen"}:
            return self._return_plan(
                plan,
                transition=transition,
                actor=str(actor).strip(),
                reason=str(reason).strip(),
                diagnostics=diagnostic_rows,
                related_objects=related_objects,
                source_references=source_references,
                event_timestamp=event_timestamp,
            )
        if transition.action == "skip":
            return self._skip_plan(
                plan,
                transition=transition,
                actor=str(actor).strip(),
                reason=str(reason).strip(),
                diagnostics=diagnostic_rows,
                related_objects=related_objects,
                source_references=source_references,
                event_timestamp=event_timestamp,
            )

        raise ValueError(f"unsupported transition action: {transition.action}")

    def set_stage(
        self,
        plan: LifecyclePlan,
        target_stage_key: str,
        *,
        actor: str,
        reason: str,
        tenant_id: str,
        diagnostics: list[LifecycleTransitionDiagnostic] | None = None,
        related_objects: list[dict[str, Any]] | None = None,
        source_references: list[str] | None = None,
        event_timestamp: str | None = None,
    ) -> tuple[LifecyclePlan, LifecycleHistoryEvent]:
        target_stage_key = _normalize_stage_key(target_stage_key)
        current_index = self.stage_order(plan.current_stage_key)
        target_index = self.stage_order(target_stage_key)
        if target_stage_key == plan.current_stage_key:
            return self.transition(
                plan,
                "reopen_stage",
                actor=actor,
                reason=reason,
                tenant_id=tenant_id,
                diagnostics=diagnostics,
                related_objects=related_objects,
                source_references=source_references,
                event_timestamp=event_timestamp,
            )
        if target_index > current_index:
            return self.transition(
                plan,
                f"advance_to_{target_stage_key}",
                actor=actor,
                reason=reason,
                tenant_id=tenant_id,
                diagnostics=diagnostics,
                related_objects=related_objects,
                source_references=source_references,
                event_timestamp=event_timestamp,
            )
        return self.transition(
            plan,
            f"return_to_{target_stage_key}",
            actor=actor,
            reason=reason,
            tenant_id=tenant_id,
            diagnostics=diagnostics,
            related_objects=related_objects,
            source_references=source_references,
            event_timestamp=event_timestamp,
        )

    def _resolve_transition(
        self, plan: LifecyclePlan, transition_key: str
    ) -> LifecycleTransition | None:
        try:
            transition = self.definition.transition(transition_key)
        except KeyError:
            transition = None
        if transition is not None:
            return transition

        normalized = _normalize_key(transition_key)
        for candidate in self.definition.transitions:
            if _normalize_key(candidate.transition_key) == normalized:
                return candidate
        return None

    def _previous_applicable_stage(
        self, plan: LifecyclePlan
    ) -> LifecycleStageDefinition | None:
        current_index = self.stage_order(plan.current_stage_key)
        for index in range(current_index - 1, -1, -1):
            stage = self.definition.stages[index]
            if stage.key in plan.applicable_stage_keys or stage.terminal:
                return stage
        return None

    def _advance_plan(
        self,
        plan: LifecyclePlan,
        *,
        transition: LifecycleTransition,
        actor: str,
        reason: str,
        diagnostics: list[LifecycleTransitionDiagnostic],
        related_objects: list[dict[str, Any]] | None,
        source_references: list[str] | None,
        event_timestamp: str | None,
    ) -> tuple[LifecyclePlan, LifecycleHistoryEvent]:
        next_stage = self._next_applicable_stage(plan)
        if next_stage is None:
            raise ValueError("no next applicable stage is available")
        stage_states = []
        current_completed_at = event_timestamp or _utc_now()
        for stage in plan.stage_states:
            if stage.stage_key == plan.current_stage_key:
                stage_states.append(
                    LifecycleStageState(
                        stage_key=stage.stage_key,
                        label=stage.label,
                        status=LifecycleStageStatus.COMPLETE,
                        applicable=stage.applicable,
                        owner_role=stage.owner_role,
                        entered_at=stage.entered_at,
                        completed_at=current_completed_at,
                        transition_reason=reason,
                        transition_actor=actor,
                        readiness=stage.readiness,
                        diagnostics=stage.diagnostics,
                        requirements=stage.requirements,
                        next_action=stage.next_action,
                        evidence_references=stage.evidence_references,
                        related_objects=stage.related_objects,
                    )
                )
            elif stage.stage_key == next_stage.key:
                next_stage_definition = self.stage_definition(stage.stage_key)
                stage_states.append(
                    LifecycleStageState(
                        stage_key=stage.stage_key,
                        label=stage.label,
                        status=LifecycleStageStatus.ACTIVE,
                        applicable=stage.applicable,
                        owner_role=stage.owner_role,
                        entered_at=event_timestamp or _utc_now(),
                        transition_reason=reason,
                        transition_actor=actor,
                        next_action=next_stage_definition.summary_action,
                        evidence_references=stage.evidence_references,
                        related_objects=stage.related_objects,
                    )
                )
            else:
                stage_states.append(stage)
        new_plan = LifecyclePlan(
            project_id=plan.project_id,
            tenant_id=plan.tenant_id,
            current_stage_key=next_stage.key,
            current_stage_status=LifecycleStageStatus.ACTIVE,
            applicable_stage_keys=list(plan.applicable_stage_keys),
            completed_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.COMPLETE
            ],
            skipped_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.SKIPPED
            ],
            blocked_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.BLOCKED
            ],
            current_owner_role=next_stage.owner_role,
            entered_at=event_timestamp or _utc_now(),
            completed_at=None,
            transition_reason=reason,
            transition_actor=actor,
            readiness=self.evaluate_readiness(
                plan,
                requirements=[],
                diagnostics=diagnostics,
                recommended_next_action=next_stage.summary_action,
            ),
            stage_states=stage_states,
            history_events=list(plan.history_events),
            resume_stage_key=plan.current_stage_key,
            legacy_project_status=_legacy_status_for_stage(next_stage.key),
            source_references=_optional_list(source_references),
            evidence_references=list(plan.evidence_references),
            schema_version=plan.schema_version,
            definition_key=plan.definition_key,
        )
        event = self._build_history_event(
            plan,
            new_plan,
            actor=actor,
            reason=reason,
            diagnostics=diagnostics,
            related_objects=related_objects,
            source_references=source_references,
            event_timestamp=event_timestamp,
        )
        return self._append_history(new_plan, event), event

    def _return_plan(
        self,
        plan: LifecyclePlan,
        *,
        transition: LifecycleTransition,
        actor: str,
        reason: str,
        diagnostics: list[LifecycleTransitionDiagnostic],
        related_objects: list[dict[str, Any]] | None,
        source_references: list[str] | None,
        event_timestamp: str | None,
    ) -> tuple[LifecyclePlan, LifecycleHistoryEvent]:
        previous_stage = self._previous_applicable_stage(plan)
        if previous_stage is None:
            raise ValueError("no prior stage is available")
        stage_states = []
        for stage in plan.stage_states:
            if stage.stage_key == plan.current_stage_key:
                stage_states.append(
                    LifecycleStageState(
                        stage_key=stage.stage_key,
                        label=stage.label,
                        status=LifecycleStageStatus.NEEDS_REVIEW,
                        applicable=stage.applicable,
                        owner_role=stage.owner_role,
                        entered_at=stage.entered_at,
                        completed_at=stage.completed_at,
                        transition_reason=reason,
                        transition_actor=actor,
                        readiness=stage.readiness,
                        diagnostics=stage.diagnostics,
                        requirements=stage.requirements,
                        next_action=stage.next_action,
                        evidence_references=stage.evidence_references,
                        related_objects=stage.related_objects,
                    )
                )
            elif stage.stage_key == previous_stage.key:
                previous_stage_definition = self.stage_definition(stage.stage_key)
                stage_states.append(
                    LifecycleStageState(
                        stage_key=stage.stage_key,
                        label=stage.label,
                        status=LifecycleStageStatus.ACTIVE,
                        applicable=stage.applicable,
                        owner_role=stage.owner_role,
                        entered_at=event_timestamp or _utc_now(),
                        transition_reason=reason,
                        transition_actor=actor,
                        next_action=previous_stage_definition.summary_action,
                        evidence_references=stage.evidence_references,
                        related_objects=stage.related_objects,
                    )
                )
            else:
                stage_states.append(stage)
        new_plan = LifecyclePlan(
            project_id=plan.project_id,
            tenant_id=plan.tenant_id,
            current_stage_key=previous_stage.key,
            current_stage_status=LifecycleStageStatus.ACTIVE,
            applicable_stage_keys=list(plan.applicable_stage_keys),
            completed_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.COMPLETE
            ],
            skipped_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.SKIPPED
            ],
            blocked_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.BLOCKED
            ],
            current_owner_role=previous_stage.owner_role,
            entered_at=event_timestamp or _utc_now(),
            completed_at=None,
            transition_reason=reason,
            transition_actor=actor,
            readiness=self.evaluate_readiness(
                plan,
                requirements=[],
                diagnostics=diagnostics,
                recommended_next_action=previous_stage.summary_action,
            ),
            stage_states=stage_states,
            history_events=list(plan.history_events),
            resume_stage_key=plan.current_stage_key,
            legacy_project_status=_legacy_status_for_stage(previous_stage.key),
            source_references=_optional_list(source_references),
            evidence_references=list(plan.evidence_references),
            schema_version=plan.schema_version,
            definition_key=plan.definition_key,
        )
        event = self._build_history_event(
            plan,
            new_plan,
            actor=actor,
            reason=reason,
            diagnostics=diagnostics,
            related_objects=related_objects,
            source_references=source_references,
            event_timestamp=event_timestamp,
        )
        return self._append_history(new_plan, event), event

    def _skip_plan(
        self,
        plan: LifecyclePlan,
        *,
        transition: LifecycleTransition,
        actor: str,
        reason: str,
        diagnostics: list[LifecycleTransitionDiagnostic],
        related_objects: list[dict[str, Any]] | None,
        source_references: list[str] | None,
        event_timestamp: str | None,
    ) -> tuple[LifecyclePlan, LifecycleHistoryEvent]:
        next_stage = self._next_applicable_stage(plan)
        if next_stage is None:
            raise ValueError("no next applicable stage is available")
        stage_states = []
        for stage in plan.stage_states:
            if stage.stage_key == plan.current_stage_key:
                stage_states.append(
                    LifecycleStageState(
                        stage_key=stage.stage_key,
                        label=stage.label,
                        status=LifecycleStageStatus.SKIPPED,
                        applicable=stage.applicable,
                        owner_role=stage.owner_role,
                        entered_at=stage.entered_at,
                        completed_at=stage.completed_at,
                        transition_reason=reason,
                        transition_actor=actor,
                        readiness=stage.readiness,
                        diagnostics=stage.diagnostics,
                        requirements=stage.requirements,
                        next_action=stage.next_action,
                        evidence_references=stage.evidence_references,
                        related_objects=stage.related_objects,
                    )
                )
            elif stage.stage_key == next_stage.key:
                next_stage_definition = self.stage_definition(stage.stage_key)
                stage_states.append(
                    LifecycleStageState(
                        stage_key=stage.stage_key,
                        label=stage.label,
                        status=LifecycleStageStatus.ACTIVE,
                        applicable=stage.applicable,
                        owner_role=stage.owner_role,
                        entered_at=event_timestamp or _utc_now(),
                        transition_reason=reason,
                        transition_actor=actor,
                        next_action=next_stage_definition.summary_action,
                        evidence_references=stage.evidence_references,
                        related_objects=stage.related_objects,
                    )
                )
            else:
                stage_states.append(stage)
        new_plan = LifecyclePlan(
            project_id=plan.project_id,
            tenant_id=plan.tenant_id,
            current_stage_key=next_stage.key,
            current_stage_status=LifecycleStageStatus.ACTIVE,
            applicable_stage_keys=list(plan.applicable_stage_keys),
            completed_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.COMPLETE
            ],
            skipped_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.SKIPPED
            ],
            blocked_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.BLOCKED
            ],
            current_owner_role=next_stage.owner_role,
            entered_at=event_timestamp or _utc_now(),
            completed_at=None,
            transition_reason=reason,
            transition_actor=actor,
            readiness=self.evaluate_readiness(
                plan,
                requirements=[],
                diagnostics=diagnostics,
                recommended_next_action=next_stage.summary_action,
            ),
            stage_states=stage_states,
            history_events=list(plan.history_events),
            resume_stage_key=plan.current_stage_key,
            legacy_project_status=_legacy_status_for_stage(next_stage.key),
            source_references=_optional_list(source_references),
            evidence_references=list(plan.evidence_references),
            schema_version=plan.schema_version,
            definition_key=plan.definition_key,
        )
        event = self._build_history_event(
            plan,
            new_plan,
            actor=actor,
            reason=reason,
            diagnostics=diagnostics,
            related_objects=related_objects,
            source_references=source_references,
            event_timestamp=event_timestamp,
        )
        return self._append_history(new_plan, event), event

    def _archive_plan(
        self,
        plan: LifecyclePlan,
        *,
        actor: str,
        reason: str,
        diagnostics: list[LifecycleTransitionDiagnostic],
        related_objects: list[dict[str, Any]] | None,
        source_references: list[str] | None,
        event_timestamp: str | None,
    ) -> tuple[LifecyclePlan, LifecycleHistoryEvent]:
        stage_states = []
        for stage in plan.stage_states:
            if stage.stage_key == plan.current_stage_key:
                stage_states.append(
                    LifecycleStageState(
                        stage_key=stage.stage_key,
                        label=stage.label,
                        status=LifecycleStageStatus.ARCHIVED,
                        applicable=stage.applicable,
                        owner_role=stage.owner_role,
                        entered_at=stage.entered_at,
                        completed_at=event_timestamp or _utc_now(),
                        transition_reason=reason,
                        transition_actor=actor,
                        readiness=stage.readiness,
                        diagnostics=stage.diagnostics,
                        requirements=stage.requirements,
                        next_action=stage.next_action,
                        evidence_references=stage.evidence_references,
                        related_objects=stage.related_objects,
                    )
                )
            else:
                stage_states.append(stage)
        new_plan = LifecyclePlan(
            project_id=plan.project_id,
            tenant_id=plan.tenant_id,
            current_stage_key="archived",
            current_stage_status=LifecycleStageStatus.ARCHIVED,
            applicable_stage_keys=list(plan.applicable_stage_keys),
            completed_stage_keys=plan.completed_stage_keys,
            skipped_stage_keys=plan.skipped_stage_keys,
            blocked_stage_keys=plan.blocked_stage_keys,
            current_owner_role="archive",
            entered_at=plan.entered_at,
            completed_at=event_timestamp or _utc_now(),
            transition_reason=reason,
            transition_actor=actor,
            readiness=self.evaluate_readiness(
                plan, diagnostics=diagnostics, recommended_next_action="Restore project"
            ),
            stage_states=stage_states,
            history_events=list(plan.history_events),
            resume_stage_key=plan.current_stage_key,
            legacy_project_status=ProjectStatus.ARCHIVED.value,
            source_references=_optional_list(source_references),
            evidence_references=list(plan.evidence_references),
            schema_version=plan.schema_version,
            definition_key=plan.definition_key,
        )
        event = self._build_history_event(
            plan,
            new_plan,
            actor=actor,
            reason=reason,
            diagnostics=diagnostics,
            related_objects=related_objects,
            source_references=source_references,
            event_timestamp=event_timestamp,
        )
        return self._append_history(new_plan, event), event

    def _restore_plan(
        self,
        plan: LifecyclePlan,
        *,
        actor: str,
        reason: str,
        diagnostics: list[LifecycleTransitionDiagnostic],
        related_objects: list[dict[str, Any]] | None,
        source_references: list[str] | None,
        event_timestamp: str | None,
    ) -> tuple[LifecyclePlan, LifecycleHistoryEvent]:
        previous_stage = self._previous_applicable_stage(plan)
        resume_stage_key = _normalize_stage_key(
            plan.resume_stage_key
            or (
                previous_stage.key
                if previous_stage is not None
                else "project_management"
            )
        )
        resume_stage = self.stage_definition(resume_stage_key)
        stage_states = []
        for stage in plan.stage_states:
            if stage.stage_key == "archived":
                stage_states.append(
                    LifecycleStageState(
                        stage_key=stage.stage_key,
                        label=stage.label,
                        status=LifecycleStageStatus.NOT_STARTED,
                        applicable=False,
                        owner_role=stage.owner_role,
                        entered_at=None,
                        completed_at=None,
                        transition_reason=reason,
                        transition_actor=actor,
                    )
                )
            elif stage.stage_key == resume_stage.key:
                resume_stage_definition = self.stage_definition(stage.stage_key)
                stage_states.append(
                    LifecycleStageState(
                        stage_key=stage.stage_key,
                        label=stage.label,
                        status=LifecycleStageStatus.ACTIVE,
                        applicable=stage.applicable,
                        owner_role=stage.owner_role,
                        entered_at=event_timestamp or _utc_now(),
                        transition_reason=reason,
                        transition_actor=actor,
                        next_action=resume_stage_definition.summary_action,
                        evidence_references=stage.evidence_references,
                        related_objects=stage.related_objects,
                    )
                )
            else:
                stage_states.append(stage)
        new_plan = LifecyclePlan(
            project_id=plan.project_id,
            tenant_id=plan.tenant_id,
            current_stage_key=resume_stage.key,
            current_stage_status=LifecycleStageStatus.ACTIVE,
            applicable_stage_keys=list(plan.applicable_stage_keys),
            completed_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.COMPLETE
            ],
            skipped_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.SKIPPED
            ],
            blocked_stage_keys=[
                item.stage_key
                for item in stage_states
                if item.status is LifecycleStageStatus.BLOCKED
            ],
            current_owner_role=resume_stage.owner_role,
            entered_at=event_timestamp or _utc_now(),
            completed_at=None,
            transition_reason=reason,
            transition_actor=actor,
            readiness=self.evaluate_readiness(
                plan,
                diagnostics=diagnostics,
                recommended_next_action=resume_stage.summary_action,
            ),
            stage_states=stage_states,
            history_events=list(plan.history_events),
            resume_stage_key=resume_stage.key,
            legacy_project_status=_legacy_status_for_stage(resume_stage.key),
            source_references=_optional_list(source_references),
            evidence_references=list(plan.evidence_references),
            schema_version=plan.schema_version,
            definition_key=plan.definition_key,
        )
        event = self._build_history_event(
            plan,
            new_plan,
            actor=actor,
            reason=reason,
            diagnostics=diagnostics,
            related_objects=related_objects,
            source_references=source_references,
            event_timestamp=event_timestamp,
        )
        return self._append_history(new_plan, event), event

    def _append_history(
        self, plan: LifecyclePlan, event: LifecycleHistoryEvent
    ) -> LifecyclePlan:
        history = list(plan.history_events)
        history.append(event)
        return LifecyclePlan(
            project_id=plan.project_id,
            tenant_id=plan.tenant_id,
            current_stage_key=plan.current_stage_key,
            current_stage_status=plan.current_stage_status,
            applicable_stage_keys=list(plan.applicable_stage_keys),
            completed_stage_keys=list(plan.completed_stage_keys),
            skipped_stage_keys=list(plan.skipped_stage_keys),
            blocked_stage_keys=list(plan.blocked_stage_keys),
            current_owner_role=plan.current_owner_role,
            entered_at=plan.entered_at,
            completed_at=plan.completed_at,
            transition_reason=plan.transition_reason,
            transition_actor=plan.transition_actor,
            readiness=plan.readiness,
            stage_states=list(plan.stage_states),
            history_events=history,
            resume_stage_key=plan.resume_stage_key,
            legacy_project_status=plan.legacy_project_status,
            source_references=list(plan.source_references),
            evidence_references=list(plan.evidence_references),
            schema_version=plan.schema_version,
            definition_key=plan.definition_key,
        )

    def _build_history_event(
        self,
        source_plan: LifecyclePlan,
        destination_plan: LifecyclePlan,
        *,
        actor: str,
        reason: str,
        diagnostics: list[LifecycleTransitionDiagnostic],
        related_objects: list[dict[str, Any]] | None,
        source_references: list[str] | None,
        event_timestamp: str | None,
    ) -> LifecycleHistoryEvent:
        return LifecycleHistoryEvent(
            event_id=f"{source_plan.project_id}:{event_timestamp or _utc_now()}:{destination_plan.current_stage_key}",
            project_id=source_plan.project_id,
            tenant_id=source_plan.tenant_id,
            source_stage=source_plan.current_stage_key,
            destination_stage=destination_plan.current_stage_key,
            source_status=source_plan.current_stage_status.value,
            destination_status=destination_plan.current_stage_status.value,
            actor=actor,
            timestamp=event_timestamp or _utc_now(),
            reason=reason,
            diagnostics_snapshot=list(diagnostics),
            related_objects=list(related_objects or []),
            source_references=_optional_list(source_references),
        )

    def _ensure_plan_compatibility(self, plan: LifecyclePlan) -> None:
        if _normalize_key(plan.definition_key) != _normalize_key(
            self.definition.definition_key
        ):
            raise ValueError("lifecycle definition mismatch")
        if plan.project_id.strip() == "":
            raise ValueError("project_id cannot be blank")
        if plan.tenant_id.strip() == "":
            raise ValueError("tenant_id cannot be blank")

    def _next_applicable_stage(
        self, plan: LifecyclePlan
    ) -> LifecycleStageDefinition | None:
        current_index = self.stage_order(plan.current_stage_key)
        for index in range(current_index + 1, len(self.definition.stages)):
            stage = self.definition.stages[index]
            if stage.key in plan.applicable_stage_keys or stage.terminal:
                return stage
        return None

    def _recommended_next_action(self, plan: LifecyclePlan) -> str | None:
        if plan.current_stage_key == "archived":
            return "Restore project"
        transition = self._next_applicable_stage(plan)
        if transition is not None:
            return f"Advance to {transition.label}"
        return self.stage_definition(plan.current_stage_key).summary_action


def project_lifecycle_from_legacy(
    project_id: str,
    tenant_id: str,
    *,
    legacy_status: str | ProjectStatus | None = None,
    lifecycle_stage: str | None = None,
    applicable_stage_keys: list[str] | None = None,
    history_events: list[LifecycleHistoryEvent] | None = None,
    resume_stage_key: str | None = None,
) -> LifecyclePlan:
    engine = AVLifecycleEngine.default()
    stage_key = _normalize_stage_key(lifecycle_stage) or legacy_stage_key_from_status(
        legacy_status
    )
    if not stage_key:
        stage_key = "bid_intake"
    legacy = getattr(legacy_status, "value", legacy_status)
    return engine.build_plan(
        project_id=project_id,
        tenant_id=tenant_id,
        current_stage_key=stage_key,
        current_stage_status=(
            LifecycleStageStatus.ACTIVE
            if stage_key != "archived"
            else LifecycleStageStatus.ARCHIVED
        ),
        applicable_stage_keys=applicable_stage_keys,
        legacy_project_status=legacy,
        history_events=history_events,
        resume_stage_key=resume_stage_key,
    )

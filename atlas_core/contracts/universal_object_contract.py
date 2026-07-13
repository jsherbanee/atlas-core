"""Universal object interoperability contracts for Atlas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

UNIVERSAL_OBJECT_SCHEMA_VERSION = "1.0"


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


@dataclass(frozen=True)
class UniversalObjectIdentity:
    object_id: str
    object_type: str
    tenant_id: str
    owning_workspace: str
    canonical_display_name: str
    secondary_identifier: str | None = None
    owning_project_id: str | None = None
    status: str | None = None
    lifecycle_state: str | None = None
    schema_version: str = UNIVERSAL_OBJECT_SCHEMA_VERSION
    source_authority: str = "atlas"
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "object_id", _required_text("object_id", self.object_id)
        )
        object.__setattr__(
            self, "object_type", _required_text("object_type", self.object_type)
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "owning_workspace",
            _required_text("owning_workspace", self.owning_workspace),
        )
        object.__setattr__(
            self,
            "canonical_display_name",
            _required_text("canonical_display_name", self.canonical_display_name),
        )
        object.__setattr__(
            self,
            "secondary_identifier",
            _optional_text(self.secondary_identifier),
        )
        object.__setattr__(
            self,
            "owning_project_id",
            _optional_text(self.owning_project_id),
        )
        object.__setattr__(self, "status", _optional_text(self.status))
        object.__setattr__(
            self,
            "lifecycle_state",
            _optional_text(self.lifecycle_state),
        )
        object.__setattr__(
            self,
            "schema_version",
            _required_text("schema_version", self.schema_version),
        )
        object.__setattr__(
            self,
            "source_authority",
            _required_text("source_authority", self.source_authority),
        )
        object.__setattr__(self, "created_at", _optional_text(self.created_at))
        object.__setattr__(self, "updated_at", _optional_text(self.updated_at))

    @property
    def universal_object_id(self) -> str:
        project_scope = self.owning_project_id or "application"
        return f"{self.tenant_id}:{self.object_type}:{project_scope}:{self.object_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "universal_object_id": self.universal_object_id,
            "object_id": self.object_id,
            "object_type": self.object_type,
            "tenant_id": self.tenant_id,
            "owning_workspace": self.owning_workspace,
            "owning_project_id": self.owning_project_id,
            "canonical_display_name": self.canonical_display_name,
            "secondary_identifier": self.secondary_identifier,
            "status": self.status,
            "lifecycle_state": self.lifecycle_state,
            "schema_version": self.schema_version,
            "source_authority": self.source_authority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UniversalObjectIdentity":
        return cls(
            object_id=str(payload.get("object_id") or ""),
            object_type=str(payload.get("object_type") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            owning_workspace=str(payload.get("owning_workspace") or ""),
            canonical_display_name=str(payload.get("canonical_display_name") or ""),
            secondary_identifier=payload.get("secondary_identifier"),
            owning_project_id=payload.get("owning_project_id"),
            status=payload.get("status"),
            lifecycle_state=payload.get("lifecycle_state"),
            schema_version=str(
                payload.get("schema_version") or UNIVERSAL_OBJECT_SCHEMA_VERSION
            ),
            source_authority=str(payload.get("source_authority") or "atlas"),
            created_at=payload.get("created_at"),
            updated_at=payload.get("updated_at"),
        )


@dataclass(frozen=True)
class UniversalObjectMetadata:
    description: str | None = None
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    external_identifiers: dict[str, str] = field(default_factory=dict)
    source_references: list[str] = field(default_factory=list)
    confidence: str | None = None
    warnings: list[str] = field(default_factory=list)
    archived: bool = False
    revision: str | None = None
    custom_metadata: dict[str, Any] = field(default_factory=dict)
    stewardship: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": _optional_text(self.description),
            "aliases": [value for value in [*_clean_list(self.aliases)] if value],
            "tags": [value for value in [*_clean_list(self.tags)] if value],
            "external_identifiers": {
                _required_text("external_identifier_key", key): _required_text(
                    "external_identifier_value", value
                )
                for key, value in dict(self.external_identifiers).items()
                if _optional_text(key) and _optional_text(value)
            },
            "source_references": [
                value for value in [*_clean_list(self.source_references)] if value
            ],
            "confidence": _optional_text(self.confidence),
            "warnings": [value for value in [*_clean_list(self.warnings)] if value],
            "archived": bool(self.archived),
            "revision": _optional_text(self.revision),
            "custom_metadata": dict(self.custom_metadata),
            "stewardship": _optional_text(self.stewardship),
            "provenance": dict(self.provenance),
        }


def _clean_list(values: list[Any]) -> list[str]:
    return [_optional_text(value) or "" for value in list(values or [])]


@dataclass(frozen=True)
class UniversalObjectRelationship:
    relationship_id: str
    source_identity: UniversalObjectIdentity
    target_identity: UniversalObjectIdentity
    relationship_type: str
    direction: str
    tenant_id: str
    status: str | None = None
    confidence: float | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    source_evidence: list[str] = field(default_factory=list)
    effective_start: str | None = None
    effective_end: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        if self.source_identity.tenant_id != self.target_identity.tenant_id:
            raise ValueError("cross-tenant relationships are not allowed")
        if self.source_identity.tenant_id != _required_text(
            "tenant_id", self.tenant_id
        ):
            raise ValueError("relationship tenant_id must match source and target")

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": _required_text("relationship_id", self.relationship_id),
            "source_identity": self.source_identity.to_dict(),
            "target_identity": self.target_identity.to_dict(),
            "relationship_type": _required_text(
                "relationship_type", self.relationship_type
            ),
            "direction": _required_text("direction", self.direction),
            "tenant_id": self.tenant_id,
            "status": _optional_text(self.status),
            "confidence": self.confidence,
            "provenance": dict(self.provenance),
            "source_evidence": [
                value for value in [*_clean_list(self.source_evidence)] if value
            ],
            "effective_start": _optional_text(self.effective_start),
            "effective_end": _optional_text(self.effective_end),
            "created_at": _optional_text(self.created_at),
            "updated_at": _optional_text(self.updated_at),
        }


@dataclass(frozen=True)
class UniversalObjectActivity:
    activity_id: str
    object_identity: UniversalObjectIdentity
    activity_type: str
    actor: str
    timestamp: str
    tenant_id: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    related_objects: list[dict[str, Any]] = field(default_factory=list)
    before_state_ref: str | None = None
    after_state_ref: str | None = None
    project_scope: str | None = None

    def __post_init__(self) -> None:
        if self.object_identity.tenant_id != _required_text(
            "tenant_id", self.tenant_id
        ):
            raise ValueError("activity tenant_id must match object tenant_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "activity_id": _required_text("activity_id", self.activity_id),
            "object_identity": self.object_identity.to_dict(),
            "activity_type": _required_text("activity_type", self.activity_type),
            "actor": _required_text("actor", self.actor),
            "timestamp": _required_text("timestamp", self.timestamp),
            "tenant_id": self.tenant_id,
            "summary": _required_text("summary", self.summary),
            "details": dict(self.details),
            "source": _optional_text(self.source),
            "related_objects": [
                dict(item) for item in list(self.related_objects or [])
            ],
            "before_state_ref": _optional_text(self.before_state_ref),
            "after_state_ref": _optional_text(self.after_state_ref),
            "project_scope": _optional_text(self.project_scope),
        }


@dataclass(frozen=True)
class UniversalObjectAction:
    action_key: str
    label: str
    action_type: str
    target_route: str | None = None
    enabled: bool = True
    visible: bool = True
    required_selection: str | None = None
    required_lifecycle_state: str | None = None
    permission_hook: str | None = None
    destructive: bool = False
    confirmation_required: bool = False
    disabled_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_key": _required_text("action_key", self.action_key),
            "label": _required_text("label", self.label),
            "action_type": _required_text("action_type", self.action_type),
            "target_route": _optional_text(self.target_route),
            "enabled": bool(self.enabled),
            "visible": bool(self.visible),
            "required_selection": _optional_text(self.required_selection),
            "required_lifecycle_state": _optional_text(self.required_lifecycle_state),
            "permission_hook": _optional_text(self.permission_hook),
            "destructive": bool(self.destructive),
            "confirmation_required": bool(self.confirmation_required),
            "disabled_reason": _optional_text(self.disabled_reason),
        }


@dataclass(frozen=True)
class UniversalObjectLifecycleTransition:
    state: str
    reason: str | None = None
    actor: str | None = None
    timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": _required_text("state", self.state),
            "reason": _optional_text(self.reason),
            "actor": _optional_text(self.actor),
            "timestamp": _optional_text(self.timestamp),
        }


@dataclass(frozen=True)
class UniversalObjectLifecycle:
    current_state: str
    allowed_transitions: list[UniversalObjectLifecycleTransition] = field(
        default_factory=list
    )
    terminal_states: list[str] = field(default_factory=list)
    archived: bool = False
    extension: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_state": _required_text("current_state", self.current_state),
            "allowed_transitions": [
                item.to_dict() for item in self.allowed_transitions
            ],
            "terminal_states": [
                value for value in [*_clean_list(self.terminal_states)] if value
            ],
            "archived": bool(self.archived),
            "extension": dict(self.extension),
        }


@dataclass(frozen=True)
class UniversalObjectPresentation:
    primary_label: str
    secondary_label: str | None = None
    icon_key: str | None = None
    status_label: str | None = None
    status_severity: str | None = None
    identity_fields: list[str] = field(default_factory=list)
    summary_fields: list[str] = field(default_factory=list)
    supported_views: list[str] = field(default_factory=list)
    supported_actions: list[str] = field(default_factory=list)
    relationship_groups: list[str] = field(default_factory=list)
    activity_available: bool = False
    document_available: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_label": _required_text("primary_label", self.primary_label),
            "secondary_label": _optional_text(self.secondary_label),
            "icon_key": _optional_text(self.icon_key),
            "status_label": _optional_text(self.status_label),
            "status_severity": _optional_text(self.status_severity),
            "identity_fields": [
                value for value in [*_clean_list(self.identity_fields)] if value
            ],
            "summary_fields": [
                value for value in [*_clean_list(self.summary_fields)] if value
            ],
            "supported_views": [
                value for value in [*_clean_list(self.supported_views)] if value
            ],
            "supported_actions": [
                value for value in [*_clean_list(self.supported_actions)] if value
            ],
            "relationship_groups": [
                value for value in [*_clean_list(self.relationship_groups)] if value
            ],
            "activity_available": bool(self.activity_available),
            "document_available": bool(self.document_available),
        }


@dataclass(frozen=True)
class UniversalObjectIntelligenceHooks:
    deterministic_insights: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: str | None = None
    source_citations: list[str] = field(default_factory=list)
    unresolved_issues: list[str] = field(default_factory=list)
    standards_references: list[str] = field(default_factory=list)
    manufacturer_references: list[str] = field(default_factory=list)
    ai_context_eligible: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "deterministic_insights": [
                value for value in [*_clean_list(self.deterministic_insights)] if value
            ],
            "recommendations": [
                value for value in [*_clean_list(self.recommendations)] if value
            ],
            "confidence": _optional_text(self.confidence),
            "source_citations": [
                value for value in [*_clean_list(self.source_citations)] if value
            ],
            "unresolved_issues": [
                value for value in [*_clean_list(self.unresolved_issues)] if value
            ],
            "standards_references": [
                value for value in [*_clean_list(self.standards_references)] if value
            ],
            "manufacturer_references": [
                value for value in [*_clean_list(self.manufacturer_references)] if value
            ],
            "ai_context_eligible": bool(self.ai_context_eligible),
        }


@dataclass(frozen=True)
class UniversalObject:
    identity: UniversalObjectIdentity
    metadata: UniversalObjectMetadata = field(default_factory=UniversalObjectMetadata)
    relationships: list[UniversalObjectRelationship] = field(default_factory=list)
    activity: list[UniversalObjectActivity] = field(default_factory=list)
    actions: list[UniversalObjectAction] = field(default_factory=list)
    lifecycle: UniversalObjectLifecycle | None = None
    presentation: UniversalObjectPresentation | None = None
    intelligence_hooks: UniversalObjectIntelligenceHooks = field(
        default_factory=UniversalObjectIntelligenceHooks
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "metadata": self.metadata.to_dict(),
            "relationships": [item.to_dict() for item in self.relationships],
            "activity": [item.to_dict() for item in self.activity],
            "actions": [item.to_dict() for item in self.actions],
            "lifecycle": (
                self.lifecycle.to_dict() if self.lifecycle is not None else None
            ),
            "presentation": (
                self.presentation.to_dict() if self.presentation is not None else None
            ),
            "intelligence_hooks": self.intelligence_hooks.to_dict(),
        }

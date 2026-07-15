"""Immutable audit contracts for tenant-scoped activity tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


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


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class AuditRetentionClass(str, Enum):
    OPERATIONAL = "operational"
    COMPLIANCE = "compliance"
    SECURITY = "security"


@dataclass(frozen=True)
class AuditActor:
    actor_id: str
    actor_type: str = "user"
    display_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor_id", _required_text("actor_id", self.actor_id))
        object.__setattr__(
            self, "actor_type", _required_text("actor_type", self.actor_type)
        )
        object.__setattr__(self, "display_name", _optional_text(self.display_name))

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "display_name": self.display_name,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "AuditActor":
        return AuditActor(
            actor_id=str(payload.get("actor_id") or ""),
            actor_type=str(payload.get("actor_type") or "user"),
            display_name=payload.get("display_name"),
        )


@dataclass(frozen=True)
class AuditTarget:
    target_type: str
    target_id: str
    tenant_id: str
    organization_id: str
    project_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "target_type", _required_text("target_type", self.target_type)
        )
        object.__setattr__(
            self, "target_id", _required_text("target_id", self.target_id)
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )
        object.__setattr__(self, "project_id", _optional_text(self.project_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_type": self.target_type,
            "target_id": self.target_id,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "AuditTarget":
        return AuditTarget(
            target_type=str(payload.get("target_type") or ""),
            target_id=str(payload.get("target_id") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            organization_id=str(payload.get("organization_id") or ""),
            project_id=payload.get("project_id"),
        )


@dataclass(frozen=True)
class AuditPermissionReference:
    permission_key: str
    allowed: bool
    decision_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "permission_key",
            _required_text("permission_key", self.permission_key),
        )
        object.__setattr__(self, "decision_code", _optional_text(self.decision_code))

    def to_dict(self) -> dict[str, Any]:
        return {
            "permission_key": self.permission_key,
            "allowed": bool(self.allowed),
            "decision_code": self.decision_code,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "AuditPermissionReference":
        return AuditPermissionReference(
            permission_key=str(payload.get("permission_key") or ""),
            allowed=bool(payload.get("allowed", False)),
            decision_code=payload.get("decision_code"),
        )


@dataclass(frozen=True)
class ImmutableAuditEvent:
    event_id: str
    action: str
    actor: AuditActor
    target: AuditTarget
    occurred_at: str
    retention_class: AuditRetentionClass
    source: str = "atlas"
    correlation_id: str | None = None
    before: dict[str, Any] = field(default_factory=dict)
    after: dict[str, Any] = field(default_factory=dict)
    change_summary: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    permission_reference: AuditPermissionReference | None = None
    previous_event_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _required_text("event_id", self.event_id))
        object.__setattr__(self, "action", _required_text("action", self.action))
        object.__setattr__(self, "source", _required_text("source", self.source))
        object.__setattr__(
            self, "occurred_at", _required_text("occurred_at", self.occurred_at)
        )
        object.__setattr__(self, "correlation_id", _optional_text(self.correlation_id))
        object.__setattr__(
            self, "previous_event_id", _optional_text(self.previous_event_id)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "event_id": self.event_id,
            "action": self.action,
            "actor": self.actor.to_dict(),
            "target": self.target.to_dict(),
            "occurred_at": self.occurred_at,
            "retention_class": self.retention_class.value,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "before": dict(self.before),
            "after": dict(self.after),
            "change_summary": dict(self.change_summary),
            "context": dict(self.context),
            "permission_reference": (
                self.permission_reference.to_dict()
                if self.permission_reference is not None
                else None
            ),
            "previous_event_id": self.previous_event_id,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "ImmutableAuditEvent":
        permission_payload = payload.get("permission_reference")
        return ImmutableAuditEvent(
            event_id=str(payload.get("event_id") or ""),
            action=str(payload.get("action") or ""),
            actor=AuditActor.from_dict(dict(payload.get("actor") or {})),
            target=AuditTarget.from_dict(dict(payload.get("target") or {})),
            occurred_at=str(payload.get("occurred_at") or ""),
            retention_class=AuditRetentionClass(
                str(
                    payload.get("retention_class")
                    or AuditRetentionClass.OPERATIONAL.value
                )
            ),
            source=str(payload.get("source") or "atlas"),
            correlation_id=payload.get("correlation_id"),
            before=dict(payload.get("before") or {}),
            after=dict(payload.get("after") or {}),
            change_summary=dict(payload.get("change_summary") or {}),
            context=dict(payload.get("context") or {}),
            permission_reference=(
                AuditPermissionReference.from_dict(dict(permission_payload))
                if isinstance(permission_payload, dict)
                else None
            ),
            previous_event_id=payload.get("previous_event_id"),
        )


@dataclass(frozen=True)
class AuditExportRecord:
    export_id: str
    generated_at: str
    project_id: str
    tenant_id: str
    organization_id: str
    event_count: int
    events: list[dict[str, Any]]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "export_id", _required_text("export_id", self.export_id)
        )
        object.__setattr__(
            self, "generated_at", _required_text("generated_at", self.generated_at)
        )
        object.__setattr__(
            self, "project_id", _required_text("project_id", self.project_id)
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "export_id": self.export_id,
            "generated_at": self.generated_at,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "event_count": int(self.event_count),
            "events": [dict(item) for item in self.events],
        }

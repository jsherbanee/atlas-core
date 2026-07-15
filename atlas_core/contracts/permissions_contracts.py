"""Deterministic tenant-scoped permissions and access contracts."""

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


def _sorted_unique(values: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    return sorted(
        {_required_text("value", item) for item in values if str(item).strip()}
    )


class PermissionEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class AccessSurface(str, Enum):
    VISIBLE_ENABLED = "visible_enabled"
    VISIBLE_DISABLED = "visible_disabled"
    HIDDEN = "hidden"


@dataclass(frozen=True)
class Permission:
    permission_key: str
    category: str
    label: str
    description: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "permission_key",
            _required_text("permission_key", self.permission_key),
        )
        object.__setattr__(self, "category", _required_text("category", self.category))
        object.__setattr__(self, "label", _required_text("label", self.label))
        object.__setattr__(
            self,
            "description",
            _required_text("description", self.description),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "permission_key": self.permission_key,
            "category": self.category,
            "label": self.label,
            "description": self.description,
        }


@dataclass(frozen=True)
class Role:
    role_key: str
    display_name: str
    system_role: bool
    allowed_permissions: list[str] = field(default_factory=list)
    denied_permissions: list[str] = field(default_factory=list)
    description: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "role_key", _required_text("role_key", self.role_key))
        object.__setattr__(
            self,
            "display_name",
            _required_text("display_name", self.display_name),
        )
        object.__setattr__(
            self, "allowed_permissions", _sorted_unique(self.allowed_permissions)
        )
        object.__setattr__(
            self, "denied_permissions", _sorted_unique(self.denied_permissions)
        )
        object.__setattr__(self, "description", _optional_text(self.description))

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_key": self.role_key,
            "display_name": self.display_name,
            "system_role": bool(self.system_role),
            "allowed_permissions": list(self.allowed_permissions),
            "denied_permissions": list(self.denied_permissions),
            "description": self.description,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "Role":
        return Role(
            role_key=str(payload.get("role_key") or ""),
            display_name=str(payload.get("display_name") or ""),
            system_role=bool(payload.get("system_role", False)),
            allowed_permissions=[
                str(item) for item in list(payload.get("allowed_permissions") or [])
            ],
            denied_permissions=[
                str(item) for item in list(payload.get("denied_permissions") or [])
            ],
            description=payload.get("description"),
        )


@dataclass(frozen=True)
class RoleAssignment:
    assignment_id: str
    tenant_id: str
    organization_id: str
    principal_id: str
    role_key: str
    assigned_by: str
    assigned_at: str
    project_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assignment_id",
            _required_text("assignment_id", self.assignment_id),
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )
        object.__setattr__(
            self,
            "principal_id",
            _required_text("principal_id", self.principal_id),
        )
        object.__setattr__(self, "role_key", _required_text("role_key", self.role_key))
        object.__setattr__(
            self,
            "assigned_by",
            _required_text("assigned_by", self.assigned_by),
        )
        object.__setattr__(
            self,
            "assigned_at",
            _required_text("assigned_at", self.assigned_at),
        )
        object.__setattr__(self, "project_id", _optional_text(self.project_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "principal_id": self.principal_id,
            "role_key": self.role_key,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at,
            "project_id": self.project_id,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "RoleAssignment":
        return RoleAssignment(
            assignment_id=str(payload.get("assignment_id") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            organization_id=str(payload.get("organization_id") or ""),
            principal_id=str(payload.get("principal_id") or ""),
            role_key=str(payload.get("role_key") or ""),
            assigned_by=str(payload.get("assigned_by") or ""),
            assigned_at=str(payload.get("assigned_at") or ""),
            project_id=payload.get("project_id"),
        )


@dataclass(frozen=True)
class ProjectAccessOverride:
    override_id: str
    tenant_id: str
    organization_id: str
    project_id: str
    permission_key: str
    effect: PermissionEffect
    reason: str
    principal_id: str | None = None
    role_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "override_id", _required_text("override_id", self.override_id)
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )
        object.__setattr__(
            self, "project_id", _required_text("project_id", self.project_id)
        )
        object.__setattr__(
            self,
            "permission_key",
            _required_text("permission_key", self.permission_key),
        )
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        object.__setattr__(self, "principal_id", _optional_text(self.principal_id))
        object.__setattr__(self, "role_key", _optional_text(self.role_key))
        if self.principal_id is None and self.role_key is None:
            raise ValueError("project override requires principal_id or role_key")

    def to_dict(self) -> dict[str, Any]:
        return {
            "override_id": self.override_id,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "permission_key": self.permission_key,
            "effect": self.effect.value,
            "reason": self.reason,
            "principal_id": self.principal_id,
            "role_key": self.role_key,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "ProjectAccessOverride":
        effect_value = str(payload.get("effect") or PermissionEffect.DENY.value)
        return ProjectAccessOverride(
            override_id=str(payload.get("override_id") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            organization_id=str(payload.get("organization_id") or ""),
            project_id=str(payload.get("project_id") or ""),
            permission_key=str(payload.get("permission_key") or ""),
            effect=PermissionEffect(effect_value),
            reason=str(payload.get("reason") or ""),
            principal_id=payload.get("principal_id"),
            role_key=payload.get("role_key"),
        )


@dataclass(frozen=True)
class AccessRequest:
    tenant_id: str
    organization_id: str
    principal_id: str
    permission_key: str
    project_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )
        object.__setattr__(
            self,
            "principal_id",
            _required_text("principal_id", self.principal_id),
        )
        object.__setattr__(
            self,
            "permission_key",
            _required_text("permission_key", self.permission_key),
        )
        object.__setattr__(self, "project_id", _optional_text(self.project_id))


@dataclass(frozen=True)
class AccessDiagnostic:
    code: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _required_text("code", self.code))
        object.__setattr__(self, "message", _required_text("message", self.message))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AccessDecision:
    effect: PermissionEffect
    allowed: bool
    reason: str
    permission_key: str
    surface: AccessSurface
    diagnostics: list[AccessDiagnostic] = field(default_factory=list)
    resolved_roles: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        object.__setattr__(
            self,
            "permission_key",
            _required_text("permission_key", self.permission_key),
        )
        object.__setattr__(self, "resolved_roles", _sorted_unique(self.resolved_roles))

    def to_dict(self) -> dict[str, Any]:
        return {
            "effect": self.effect.value,
            "allowed": bool(self.allowed),
            "reason": self.reason,
            "permission_key": self.permission_key,
            "surface": self.surface.value,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "resolved_roles": list(self.resolved_roles),
        }


@dataclass(frozen=True)
class PermissionChangeEvent:
    event_id: str
    tenant_id: str
    organization_id: str
    actor: str
    event_type: str
    timestamp: str
    details: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _required_text("event_id", self.event_id))
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )
        object.__setattr__(self, "actor", _required_text("actor", self.actor))
        object.__setattr__(
            self,
            "event_type",
            _required_text("event_type", self.event_type),
        )
        object.__setattr__(
            self,
            "timestamp",
            _required_text("timestamp", self.timestamp),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "actor": self.actor,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class TenantPolicy:
    tenant_id: str
    organization_id: str
    custom_roles: list[Role] = field(default_factory=list)
    role_assignments: list[RoleAssignment] = field(default_factory=list)
    project_overrides: list[ProjectAccessOverride] = field(default_factory=list)

    def __post_init__(self) -> None:
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
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "custom_roles": [
                role.to_dict()
                for role in sorted(
                    self.custom_roles,
                    key=lambda item: (item.display_name.lower(), item.role_key.lower()),
                )
            ],
            "role_assignments": [
                assignment.to_dict()
                for assignment in sorted(
                    self.role_assignments,
                    key=lambda item: (
                        item.principal_id,
                        item.project_id or "",
                        item.role_key,
                        item.assignment_id,
                    ),
                )
            ],
            "project_overrides": [
                override.to_dict()
                for override in sorted(
                    self.project_overrides,
                    key=lambda item: (
                        item.project_id,
                        item.permission_key,
                        item.principal_id or "",
                        item.role_key or "",
                        item.override_id,
                    ),
                )
            ],
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "TenantPolicy":
        return TenantPolicy(
            tenant_id=str(payload.get("tenant_id") or ""),
            organization_id=str(payload.get("organization_id") or ""),
            custom_roles=[
                Role.from_dict(dict(item))
                for item in list(payload.get("custom_roles") or [])
                if isinstance(item, dict)
            ],
            role_assignments=[
                RoleAssignment.from_dict(dict(item))
                for item in list(payload.get("role_assignments") or [])
                if isinstance(item, dict)
            ],
            project_overrides=[
                ProjectAccessOverride.from_dict(dict(item))
                for item in list(payload.get("project_overrides") or [])
                if isinstance(item, dict)
            ],
        )


def now_iso() -> str:
    return datetime.now(UTC).isoformat()

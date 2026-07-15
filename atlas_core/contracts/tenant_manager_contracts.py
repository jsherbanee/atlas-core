"""Tenant manager contracts for sandbox provisioning and isolation controls."""

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


class TenantStatus(str, Enum):
    DRAFT = "draft"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    FAILED = "failed"


@dataclass(frozen=True)
class TenantEnvironment:
    environment_id: str
    tenant_id: str
    environment_type: str = "alpha_sandbox"
    storage_root: str = ""
    repository_paths: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "environment_id",
            _required_text("environment_id", self.environment_id),
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "environment_type",
            _required_text("environment_type", self.environment_type),
        )
        object.__setattr__(
            self, "storage_root", _required_text("storage_root", self.storage_root)
        )
        object.__setattr__(
            self, "created_at", _required_text("created_at", self.created_at)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "tenant_id": self.tenant_id,
            "environment_type": self.environment_type,
            "storage_root": self.storage_root,
            "repository_paths": dict(self.repository_paths),
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "TenantEnvironment":
        return TenantEnvironment(
            environment_id=str(payload.get("environment_id") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            environment_type=str(payload.get("environment_type") or "alpha_sandbox"),
            storage_root=str(payload.get("storage_root") or ""),
            repository_paths=dict(payload.get("repository_paths") or {}),
            created_at=str(payload.get("created_at") or now_iso()),
        )


@dataclass(frozen=True)
class TenantMembership:
    tenant_id: str
    user_id: str
    role_key: str
    status: str = "active"
    is_owner: bool = False
    notes: str | None = None
    joined_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(self, "user_id", _required_text("user_id", self.user_id))
        object.__setattr__(self, "role_key", _required_text("role_key", self.role_key))
        object.__setattr__(
            self, "status", _required_text("status", self.status).lower()
        )
        object.__setattr__(self, "notes", _optional_text(self.notes))
        object.__setattr__(
            self, "joined_at", _required_text("joined_at", self.joined_at)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "role_key": self.role_key,
            "status": self.status,
            "is_owner": bool(self.is_owner),
            "notes": self.notes,
            "joined_at": self.joined_at,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "TenantMembership":
        return TenantMembership(
            tenant_id=str(payload.get("tenant_id") or ""),
            user_id=str(payload.get("user_id") or ""),
            role_key=str(payload.get("role_key") or "tenant_administrator"),
            status=str(payload.get("status") or "active"),
            is_owner=bool(payload.get("is_owner", False)),
            notes=payload.get("notes"),
            joined_at=str(payload.get("joined_at") or now_iso()),
        )


@dataclass(frozen=True)
class TenantConfiguration:
    sandbox_label: str
    expiration_date: str | None
    enable_seed_data: bool
    seed_data_profile: str
    test_user_notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "sandbox_label", _required_text("sandbox_label", self.sandbox_label)
        )
        object.__setattr__(
            self, "expiration_date", _optional_text(self.expiration_date)
        )
        object.__setattr__(
            self,
            "seed_data_profile",
            _required_text("seed_data_profile", self.seed_data_profile).lower(),
        )
        object.__setattr__(
            self, "test_user_notes", _optional_text(self.test_user_notes)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sandbox_label": self.sandbox_label,
            "expiration_date": self.expiration_date,
            "enable_seed_data": bool(self.enable_seed_data),
            "seed_data_profile": self.seed_data_profile,
            "test_user_notes": self.test_user_notes,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "TenantConfiguration":
        return TenantConfiguration(
            sandbox_label=str(payload.get("sandbox_label") or ""),
            expiration_date=payload.get("expiration_date"),
            enable_seed_data=bool(payload.get("enable_seed_data", False)),
            seed_data_profile=str(payload.get("seed_data_profile") or "none"),
            test_user_notes=payload.get("test_user_notes"),
        )


@dataclass(frozen=True)
class TenantDataBoundary:
    active_tenant_required: bool = True
    prohibit_cross_tenant_references: bool = True
    prohibit_cross_tenant_attachments: bool = True
    prohibit_cross_tenant_relationships: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_tenant_required": bool(self.active_tenant_required),
            "prohibit_cross_tenant_references": bool(
                self.prohibit_cross_tenant_references
            ),
            "prohibit_cross_tenant_attachments": bool(
                self.prohibit_cross_tenant_attachments
            ),
            "prohibit_cross_tenant_relationships": bool(
                self.prohibit_cross_tenant_relationships
            ),
        }


@dataclass(frozen=True)
class SandboxProvisioningRequest:
    sandbox_label: str
    owner_user_id: str
    expiration_date: str | None = None
    enable_seed_data: bool = False
    seed_data_profile: str = "none"
    test_user_notes: str | None = None
    tenant_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "sandbox_label", _required_text("sandbox_label", self.sandbox_label)
        )
        object.__setattr__(
            self, "owner_user_id", _required_text("owner_user_id", self.owner_user_id)
        )
        object.__setattr__(
            self, "expiration_date", _optional_text(self.expiration_date)
        )
        object.__setattr__(
            self,
            "seed_data_profile",
            _required_text("seed_data_profile", self.seed_data_profile).lower(),
        )
        object.__setattr__(
            self, "test_user_notes", _optional_text(self.test_user_notes)
        )
        object.__setattr__(self, "tenant_id", _optional_text(self.tenant_id))


@dataclass(frozen=True)
class SandboxProvisioningResult:
    tenant_id: str
    status: TenantStatus
    environment: TenantEnvironment
    seeded: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "environment": self.environment.to_dict(),
            "seeded": bool(self.seeded),
            "message": self.message,
        }


@dataclass(frozen=True)
class TenantAuditEvent:
    event_id: str
    tenant_id: str
    actor_id: str
    action: str
    details: dict[str, Any] = field(default_factory=dict)
    occurred_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _required_text("event_id", self.event_id))
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(self, "actor_id", _required_text("actor_id", self.actor_id))
        object.__setattr__(self, "action", _required_text("action", self.action))
        object.__setattr__(
            self, "occurred_at", _required_text("occurred_at", self.occurred_at)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "action": self.action,
            "details": dict(self.details),
            "occurred_at": self.occurred_at,
        }


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    tenant_name: str
    status: TenantStatus
    owner_user_id: str
    environment: TenantEnvironment
    configuration: TenantConfiguration
    memberships: list[TenantMembership] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    last_activity_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self, "tenant_name", _required_text("tenant_name", self.tenant_name)
        )
        object.__setattr__(
            self, "owner_user_id", _required_text("owner_user_id", self.owner_user_id)
        )
        object.__setattr__(
            self, "created_at", _required_text("created_at", self.created_at)
        )
        object.__setattr__(
            self, "updated_at", _required_text("updated_at", self.updated_at)
        )
        object.__setattr__(
            self, "last_activity_at", _optional_text(self.last_activity_at)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "status": self.status.value,
            "owner_user_id": self.owner_user_id,
            "environment": self.environment.to_dict(),
            "configuration": self.configuration.to_dict(),
            "memberships": [item.to_dict() for item in self.memberships],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_activity_at": self.last_activity_at,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "Tenant":
        memberships = [
            TenantMembership.from_dict(item)
            for item in list(payload.get("memberships") or [])
            if isinstance(item, dict)
        ]
        return Tenant(
            tenant_id=str(payload.get("tenant_id") or ""),
            tenant_name=str(payload.get("tenant_name") or ""),
            status=TenantStatus(str(payload.get("status") or TenantStatus.DRAFT.value)),
            owner_user_id=str(payload.get("owner_user_id") or ""),
            environment=TenantEnvironment.from_dict(
                dict(payload.get("environment") or {})
            ),
            configuration=TenantConfiguration.from_dict(
                dict(payload.get("configuration") or {})
            ),
            memberships=memberships,
            created_at=str(payload.get("created_at") or now_iso()),
            updated_at=str(payload.get("updated_at") or now_iso()),
            last_activity_at=payload.get("last_activity_at"),
        )

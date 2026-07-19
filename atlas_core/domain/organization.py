"""Shared organization and project stakeholder domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid


class OrganizationRole(str, Enum):
    OWNER_CLIENT = "owner_client"
    GENERAL_CONTRACTOR = "general_contractor"
    ELECTRICAL_CONTRACTOR = "electrical_contractor"
    ARCHITECT = "architect"
    CONSULTANT = "consultant"
    ENGINEER = "engineer"
    CUSTOMER = "customer"
    VENDOR = "vendor"
    MANUFACTURER = "manufacturer"
    OTHER = "other"


def parse_organization_role(value: Any) -> OrganizationRole:
    if isinstance(value, OrganizationRole):
        return value
    text = str(value or "").strip()
    if not text:
        raise ValueError("organization role cannot be blank")
    by_value = {item.value: item for item in OrganizationRole}
    if text in by_value:
        return by_value[text]
    by_name = {item.name: item for item in OrganizationRole}
    upper_text = text.upper()
    if upper_text in by_name:
        return by_name[upper_text]
    raise ValueError(f"unknown organization role: {text}")


@dataclass
class Organization:
    organization_id: str
    canonical_name: str
    display_name: str
    normalized_name: str
    supported_roles: list[OrganizationRole] = field(default_factory=list)
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    active: bool = True
    aliases: list[str] = field(default_factory=list)
    notes: str | None = None
    tenant_id: str = "local"
    organization_scope_id: str = "atlas"
    role_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    merge_history: list[dict[str, Any]] = field(default_factory=list)
    redirected_from: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(
        cls,
        *,
        name: str,
        role: OrganizationRole,
        website: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
        notes: str | None = None,
        aliases: list[str] | None = None,
        tenant_id: str = "local",
        organization_scope_id: str = "atlas",
        role_profiles: dict[str, dict[str, Any]] | None = None,
    ) -> "Organization":
        normalized = _normalize_name(name)
        display_name = name.strip()
        return cls(
            organization_id=f"org-{uuid.uuid4().hex[:12]}",
            canonical_name=display_name,
            display_name=display_name,
            normalized_name=normalized,
            supported_roles=[role],
            website=_optional_text(website),
            phone=_optional_text(phone),
            email=_optional_text(email),
            address=_optional_text(address),
            notes=_optional_text(notes),
            aliases=[item for item in list(aliases or []) if _optional_text(item)],
            tenant_id=tenant_id.strip() or "local",
            organization_scope_id=organization_scope_id.strip() or "atlas",
            role_profiles=dict(role_profiles or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "canonical_name": self.canonical_name,
            "display_name": self.display_name,
            "normalized_name": self.normalized_name,
            "supported_roles": [item.value for item in self.supported_roles],
            "website": self.website,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "active": self.active,
            "aliases": list(self.aliases),
            "notes": self.notes,
            "tenant_id": self.tenant_id,
            "organization_scope_id": self.organization_scope_id,
            "role_profiles": dict(self.role_profiles),
            "merge_history": [dict(item) for item in self.merge_history],
            "redirected_from": [dict(item) for item in self.redirected_from],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Organization":
        normalized_name = _optional_text(payload.get("normalized_name"))
        canonical_name = _optional_text(payload.get("canonical_name"))
        display_name = _optional_text(payload.get("display_name"))
        resolved_display = display_name or canonical_name or "Unknown"
        resolved_canonical = canonical_name or resolved_display
        return cls(
            organization_id=str(payload.get("organization_id") or ""),
            canonical_name=resolved_canonical,
            display_name=resolved_display,
            normalized_name=normalized_name or _normalize_name(resolved_canonical),
            supported_roles=[
                parse_organization_role(item)
                for item in list(payload.get("supported_roles") or [])
                if _role_can_parse(item)
            ],
            website=_optional_text(payload.get("website")),
            phone=_optional_text(payload.get("phone")),
            email=_optional_text(payload.get("email")),
            address=_optional_text(payload.get("address")),
            active=bool(payload.get("active", True)),
            aliases=[
                str(item)
                for item in list(payload.get("aliases") or [])
                if str(item).strip()
            ],
            notes=_optional_text(payload.get("notes")),
            tenant_id=str(payload.get("tenant_id") or "local"),
            organization_scope_id=str(payload.get("organization_scope_id") or "atlas"),
            role_profiles={
                str(key): dict(value)
                for key, value in dict(payload.get("role_profiles") or {}).items()
                if isinstance(value, dict)
            },
            merge_history=[
                dict(item)
                for item in list(payload.get("merge_history") or [])
                if isinstance(item, dict)
            ],
            redirected_from=[
                dict(item)
                for item in list(payload.get("redirected_from") or [])
                if isinstance(item, dict)
            ],
            created_at=str(payload.get("created_at") or datetime.now(UTC).isoformat()),
            updated_at=str(payload.get("updated_at") or datetime.now(UTC).isoformat()),
        )


@dataclass
class ProjectStakeholder:
    stakeholder_id: str
    project_id: str
    organization_id: str
    role: OrganizationRole
    is_primary: bool = False
    contact_display: str | None = None
    project_notes: str | None = None
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        organization_id: str,
        role: OrganizationRole,
        is_primary: bool = False,
        contact_display: str | None = None,
        project_notes: str | None = None,
    ) -> "ProjectStakeholder":
        return cls(
            stakeholder_id=f"ps-{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            organization_id=organization_id,
            role=role,
            is_primary=is_primary,
            contact_display=_optional_text(contact_display),
            project_notes=_optional_text(project_notes),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stakeholder_id": self.stakeholder_id,
            "project_id": self.project_id,
            "organization_id": self.organization_id,
            "role": self.role.value,
            "is_primary": self.is_primary,
            "contact_display": self.contact_display,
            "project_notes": self.project_notes,
            "active": self.active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectStakeholder":
        role_text = str(payload.get("role") or OrganizationRole.OTHER.value)
        role = (
            parse_organization_role(role_text)
            if _role_can_parse(role_text)
            else OrganizationRole.OTHER
        )
        return cls(
            stakeholder_id=str(payload.get("stakeholder_id") or ""),
            project_id=str(payload.get("project_id") or ""),
            organization_id=str(payload.get("organization_id") or ""),
            role=role,
            is_primary=bool(payload.get("is_primary", False)),
            contact_display=_optional_text(payload.get("contact_display")),
            project_notes=_optional_text(payload.get("project_notes")),
            active=bool(payload.get("active", True)),
            created_at=str(payload.get("created_at") or datetime.now(UTC).isoformat()),
            updated_at=str(payload.get("updated_at") or datetime.now(UTC).isoformat()),
        )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _role_can_parse(value: Any) -> bool:
    try:
        parse_organization_role(value)
    except ValueError:
        return False
    return True


def _normalize_name(value: str) -> str:
    normalized = " ".join(value.strip().lower().split())
    for ch in [",", ".", "'", '"', "(", ")", "[", "]", "{", "}", "-"]:
        normalized = normalized.replace(ch, " ")
    return " ".join(normalized.split())

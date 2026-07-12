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
    OTHER = "other"


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
                OrganizationRole(str(item))
                for item in list(payload.get("supported_roles") or [])
                if str(item) in {role.value for role in OrganizationRole}
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
            OrganizationRole(role_text)
            if role_text in {item.value for item in OrganizationRole}
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


def _normalize_name(value: str) -> str:
    normalized = " ".join(value.strip().lower().split())
    for ch in [",", ".", "'", '"', "(", ")", "[", "]", "{", "}", "-"]:
        normalized = normalized.replace(ch, " ")
    return " ".join(normalized.split())

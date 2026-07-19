"""Shared organization directory and project stakeholder relationship service."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from atlas_core.domain import (
    Organization,
    OrganizationRole,
    ProjectStakeholder,
    parse_organization_role,
)

BUSINESS_ORGANIZATION_ROLES = {
    OrganizationRole.CUSTOMER,
    OrganizationRole.VENDOR,
    OrganizationRole.MANUFACTURER,
}


class OrganizationDirectoryService:
    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self._org_path = self.workspace_root / ".atlas_organizations.json"
        self._stakeholder_path = (
            self.workspace_root / ".atlas_project_stakeholders.json"
        )

    def list_organizations(self, include_inactive: bool = True) -> list[Organization]:
        rows = [
            Organization.from_dict(item)
            for item in self._read_json_list(self._org_path)
        ]
        if include_inactive:
            return rows
        return [item for item in rows if item.active]

    def search_organizations(
        self,
        query: str,
        *,
        role: OrganizationRole | None = None,
        include_inactive: bool = False,
        limit: int = 20,
    ) -> list[Organization]:
        normalized_query = normalize_name(query)
        organizations = self.list_organizations(include_inactive=include_inactive)
        if role is not None:
            organizations = [
                item
                for item in organizations
                if role in item.supported_roles or not item.supported_roles
            ]
        if not normalized_query:
            return organizations[:limit]

        def _match_score(item: Organization) -> tuple[int, str]:
            names = [
                item.normalized_name,
                *[normalize_name(alias) for alias in item.aliases],
            ]
            if normalized_query in names:
                return (0, item.display_name)
            if any(name.startswith(normalized_query) for name in names):
                return (1, item.display_name)
            if any(normalized_query in name for name in names):
                return (2, item.display_name)
            return (9, item.display_name)

        scored = sorted(organizations, key=_match_score)
        return [item for item in scored if _match_score(item)[0] < 9][:limit]

    def find_likely_duplicates(self, name: str) -> list[Organization]:
        normalized = normalize_name(name)
        if not normalized:
            return []

        duplicates: list[Organization] = []
        for item in self.list_organizations(include_inactive=True):
            names = {
                item.normalized_name,
                *[normalize_name(alias) for alias in item.aliases],
            }
            if normalized in names:
                duplicates.append(item)
                continue
            if _close_name(normalized, item.normalized_name):
                duplicates.append(item)
        return duplicates

    def create_organization(
        self,
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
    ) -> Organization:
        organizations = self.list_organizations(include_inactive=True)
        org = Organization.create(
            name=name,
            role=role,
            website=website,
            phone=phone,
            email=email,
            address=address,
            notes=notes,
            aliases=aliases,
            tenant_id=tenant_id,
            organization_scope_id=organization_scope_id,
            role_profiles=role_profiles,
        )
        organizations.append(org)
        self._write_json_list(
            self._org_path, [item.to_dict() for item in organizations]
        )
        return org

    def get_organization(self, organization_id: str) -> Organization | None:
        normalized = str(organization_id or "").strip()
        for item in self.list_organizations(include_inactive=True):
            if item.organization_id == normalized:
                return item
        return None

    def save_organization(self, organization: Organization) -> Organization:
        organizations = self.list_organizations(include_inactive=True)
        now_text = datetime.now(UTC).isoformat()
        organization.updated_at = now_text
        replaced = False
        for index, item in enumerate(organizations):
            if item.organization_id == organization.organization_id:
                organizations[index] = organization
                replaced = True
                break
        if not replaced:
            organizations.append(organization)
        self._write_json_list(
            self._org_path, [item.to_dict() for item in organizations]
        )
        return organization

    def add_role_profile(
        self,
        *,
        organization_id: str,
        role: OrganizationRole,
        profile: dict[str, Any],
    ) -> Organization:
        if role not in BUSINESS_ORGANIZATION_ROLES:
            raise ValueError("only business organization roles can be profiled")
        organization = self.get_organization(organization_id)
        if organization is None:
            raise ValueError("Organization not found")
        if role not in organization.supported_roles:
            organization.supported_roles.append(role)
        current = dict(organization.role_profiles.get(role.value) or {})
        merged = _merge_profile(current, dict(profile))
        organization.role_profiles[role.value] = merged
        return self.save_organization(organization)

    def duplicate_suggestions(
        self,
        *,
        tenant_id: str,
        organization_scope_id: str,
        candidate: dict[str, Any],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        self._assert_scope(
            tenant_id=tenant_id, organization_scope_id=organization_scope_id
        )
        candidate_signals = _organization_match_signals(candidate)
        suggestions: list[dict[str, Any]] = []
        for item in self.list_organizations(include_inactive=False):
            if (
                item.tenant_id != tenant_id
                or item.organization_scope_id != organization_scope_id
            ):
                continue
            reasons = _matching_signal_reasons(
                candidate_signals, _organization_match_signals(item.to_dict())
            )
            if not reasons:
                continue
            suggestions.append(
                {
                    "organization_id": item.organization_id,
                    "display_name": item.display_name,
                    "roles": [role.value for role in item.supported_roles],
                    "reasons": reasons,
                    "confidence_inputs": reasons,
                    "score": len(reasons),
                }
            )
        suggestions.sort(
            key=lambda row: (
                -int(row.get("score", 0)),
                str(row.get("display_name", "")).lower(),
            )
        )
        return suggestions[:limit]

    def preview_merge(
        self,
        *,
        primary_organization_id: str,
        source_organizations: list[dict[str, Any]],
        tenant_id: str,
        organization_scope_id: str,
        conflict_resolutions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._assert_scope(
            tenant_id=tenant_id, organization_scope_id=organization_scope_id
        )
        primary = self.get_organization(primary_organization_id)
        if primary is None:
            raise ValueError("Primary organization not found")
        self._assert_same_scope(
            primary, tenant_id=tenant_id, organization_scope_id=organization_scope_id
        )
        resolutions = dict(conflict_resolutions or {})
        conflicts: list[dict[str, Any]] = []
        role_profiles = dict(primary.role_profiles)
        roles_after = {role.value for role in primary.supported_roles}
        aliases_after = set(primary.aliases)
        source_refs: list[dict[str, Any]] = []
        for source in source_organizations:
            source_role = _coerce_business_role(source.get("role"))
            if source_role:
                roles_after.add(source_role.value)
                role_profiles[source_role.value] = _merge_profile(
                    dict(role_profiles.get(source_role.value) or {}),
                    dict(source.get("profile") or {}),
                )
            source_refs.append(
                {
                    "source_entity_id": str(source.get("source_entity_id") or ""),
                    "role": source_role.value if source_role else "",
                    "display_name": str(source.get("display_name") or ""),
                }
            )
            for alias in list(source.get("aliases") or []):
                if str(alias).strip():
                    aliases_after.add(str(alias).strip())
            for field in [
                "canonical_name",
                "display_name",
                "website",
                "phone",
                "email",
                "address",
                "notes",
            ]:
                primary_value = getattr(primary, field, None)
                source_value = source.get(field)
                if _conflicts(primary_value, source_value):
                    conflicts.append(
                        {
                            "field": field,
                            "primary_value": primary_value,
                            "source_value": source_value,
                            "resolution": resolutions.get(field, "primary"),
                            "allowed_resolutions": ["primary", "source", "both"],
                        }
                    )
        correlation_id = _merge_correlation_id(primary.organization_id, source_refs)
        return {
            "correlation_id": correlation_id,
            "primary_organization_id": primary.organization_id,
            "primary_display_name": primary.display_name,
            "source_records": source_refs,
            "conflicts": conflicts,
            "roles_after": sorted(roles_after),
            "aliases_after": sorted(aliases_after),
            "role_profiles_after": role_profiles,
            "relationship_reassignment_preview": {
                "knowledge_relationships": 0,
                "legacy_records": len(source_refs),
            },
        }

    def confirm_merge(
        self,
        *,
        primary_organization_id: str,
        source_organizations: list[dict[str, Any]],
        tenant_id: str,
        organization_scope_id: str,
        actor: str,
        reason: str,
        conflict_resolutions: dict[str, Any] | None = None,
        permission_granted: bool,
        relationship_reassignment_counts: dict[str, int] | None = None,
    ) -> Organization:
        self._assert_scope(
            tenant_id=tenant_id, organization_scope_id=organization_scope_id
        )
        if not permission_granted:
            raise PermissionError(
                "knowledge.edit permission is required to merge organizations"
            )
        if not str(actor or "").strip():
            raise ValueError("actor is required")
        if not str(reason or "").strip():
            raise ValueError("merge reason is required")
        preview = self.preview_merge(
            primary_organization_id=primary_organization_id,
            source_organizations=source_organizations,
            tenant_id=tenant_id,
            organization_scope_id=organization_scope_id,
            conflict_resolutions=conflict_resolutions,
        )
        organization = self.get_organization(primary_organization_id)
        if organization is None:
            raise ValueError("Primary organization not found")
        organization.supported_roles = [
            parse_organization_role(role)
            for role in list(preview.get("roles_after") or [])
            if _role_can_parse(role)
        ]
        organization.role_profiles = dict(preview.get("role_profiles_after") or {})
        organization.aliases = sorted(
            {
                *organization.aliases,
                *list(preview.get("aliases_after") or []),
                *[
                    str(item.get("display_name"))
                    for item in list(preview.get("source_records") or [])
                    if str(item.get("display_name") or "").strip()
                ],
            }
        )
        resolutions = dict(conflict_resolutions or {})
        for conflict in list(preview.get("conflicts") or []):
            field = str(conflict.get("field") or "")
            resolution = str(
                resolutions.get(field) or conflict.get("resolution") or "primary"
            )
            if resolution == "source" and hasattr(organization, field):
                setattr(organization, field, conflict.get("source_value"))
            elif resolution == "both" and field in {
                "canonical_name",
                "display_name",
                "website",
                "phone",
                "email",
                "address",
            }:
                source_value = str(conflict.get("source_value") or "").strip()
                if source_value:
                    organization.aliases = sorted({*organization.aliases, source_value})
        merge_event = {
            "event_type": "organization_merge_confirmed",
            "correlation_id": preview.get("correlation_id"),
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": str(actor).strip(),
            "reason": str(reason).strip(),
            "primary_organization_id": organization.organization_id,
            "source_records": list(preview.get("source_records") or []),
            "conflict_resolutions": resolutions,
            "relationship_reassignment_counts": dict(
                relationship_reassignment_counts or {}
            ),
        }
        organization.merge_history.append(merge_event)
        organization.redirected_from.extend(list(preview.get("source_records") or []))
        return self.save_organization(organization)

    def _assert_scope(self, *, tenant_id: str, organization_scope_id: str) -> None:
        if not str(tenant_id or "").strip():
            raise PermissionError("active tenant scope is required")
        if not str(organization_scope_id or "").strip():
            raise PermissionError("active organization scope is required")

    @staticmethod
    def _assert_same_scope(
        organization: Organization,
        *,
        tenant_id: str,
        organization_scope_id: str,
    ) -> None:
        if (
            organization.tenant_id != tenant_id
            or organization.organization_scope_id != organization_scope_id
        ):
            raise PermissionError("organization scope mismatch")

    def list_project_stakeholders(self, project_id: str) -> list[ProjectStakeholder]:
        rows = [
            ProjectStakeholder.from_dict(item)
            for item in self._read_json_list(self._stakeholder_path)
        ]
        return [item for item in rows if item.project_id == project_id and item.active]

    def replace_project_stakeholders(
        self,
        project_id: str,
        stakeholders: list[ProjectStakeholder],
    ) -> list[ProjectStakeholder]:
        existing = [
            ProjectStakeholder.from_dict(item)
            for item in self._read_json_list(self._stakeholder_path)
        ]
        kept = [item for item in existing if item.project_id != project_id]
        now = datetime.now(UTC).isoformat()
        for item in stakeholders:
            item.updated_at = now
            kept.append(item)
        self._write_json_list(self._stakeholder_path, [item.to_dict() for item in kept])
        return self.list_project_stakeholders(project_id)

    def link_organization_to_project(
        self,
        *,
        project_id: str,
        organization_id: str,
        role: OrganizationRole,
        is_primary: bool = False,
        contact_display: str | None = None,
        project_notes: str | None = None,
    ) -> ProjectStakeholder:
        current = self.list_project_stakeholders(project_id)
        for item in current:
            if item.organization_id == organization_id and item.role == role:
                item.is_primary = is_primary
                item.contact_display = contact_display or item.contact_display
                item.project_notes = project_notes or item.project_notes
                self.replace_project_stakeholders(project_id, current)
                return item

        created = ProjectStakeholder.create(
            project_id=project_id,
            organization_id=organization_id,
            role=role,
            is_primary=is_primary,
            contact_display=contact_display,
            project_notes=project_notes,
        )
        current.append(created)
        self.replace_project_stakeholders(project_id, current)
        return created

    @staticmethod
    def _read_json_list(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            with path.open(encoding="utf-8") as file:
                payload = json.load(file)
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    @staticmethod
    def _write_json_list(path: Path, payload: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, sort_keys=True)


def normalize_name(value: str) -> str:
    normalized = " ".join(str(value).strip().lower().split())
    for ch in [",", ".", "'", '"', "(", ")", "[", "]", "{", "}", "-"]:
        normalized = normalized.replace(ch, " ")
    return " ".join(normalized.split())


def _coerce_business_role(value: Any) -> OrganizationRole | None:
    try:
        role = parse_organization_role(value)
    except ValueError:
        return None
    if role in BUSINESS_ORGANIZATION_ROLES:
        return role
    return None


def _role_can_parse(value: Any) -> bool:
    try:
        parse_organization_role(value)
    except ValueError:
        return False
    return True


def _merge_profile(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    identifiers = {
        str(item).strip()
        for item in list(left.get("identifiers") or [])
        if str(item).strip()
    }
    identifiers.update(
        {
            str(item).strip()
            for item in list(right.get("identifiers") or [])
            if str(item).strip()
        }
    )
    for key, value in right.items():
        if key == "identifiers":
            continue
        if key not in merged or _empty_profile_value(merged.get(key)):
            merged[key] = value
        elif merged.get(key) != value:
            existing_values = merged.get(f"{key}_alternates")
            alternates = (
                list(existing_values) if isinstance(existing_values, list) else []
            )
            if value not in alternates:
                alternates.append(value)
            merged[f"{key}_alternates"] = alternates
    if identifiers:
        merged["identifiers"] = sorted(identifiers)
    return merged


def _organization_match_signals(payload: dict[str, Any]) -> dict[str, set[str]]:
    aliases = {
        normalize_name(str(item))
        for item in list(payload.get("aliases") or [])
        if str(item).strip()
    }
    names = {
        normalize_name(str(payload.get("canonical_name") or "")),
        normalize_name(str(payload.get("display_name") or "")),
        normalize_name(str(payload.get("organization") or "")),
        *aliases,
    }
    return {
        "name": {item for item in names if item},
        "website_domain": {_domain(payload.get("website"))},
        "email_domain": {
            _email_domain(payload.get("email") or payload.get("primary_email"))
        },
        "phone": {_phone_digits(payload.get("phone") or payload.get("primary_phone"))},
        "tax_identifier_ref": {
            str(
                payload.get("tax_identifier_ref")
                or payload.get("tax_identifier_reference")
                or ""
            ).strip()
        },
        "address": {normalize_name(str(payload.get("address") or ""))},
    }


def _matching_signal_reasons(
    left: dict[str, set[str]], right: dict[str, set[str]]
) -> list[str]:
    labels = {
        "name": "normalized name",
        "website_domain": "website domain",
        "email_domain": "email domain",
        "phone": "phone number",
        "tax_identifier_ref": "tax identifier reference",
        "address": "address",
    }
    reasons: list[str] = []
    for key, label in labels.items():
        left_values = {item for item in left.get(key, set()) if item}
        right_values = {item for item in right.get(key, set()) if item}
        if left_values.intersection(right_values):
            reasons.append(label)
    return reasons


def _domain(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = parsed.netloc or parsed.path
    return host.removeprefix("www.").split("/")[0]


def _email_domain(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "@" not in text:
        return ""
    return text.rsplit("@", 1)[-1]


def _phone_digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _empty_profile_value(value: Any) -> bool:
    return value is None or value == "" or value == []


def _conflicts(primary_value: Any, source_value: Any) -> bool:
    primary_text = str(primary_value or "").strip()
    source_text = str(source_value or "").strip()
    if not primary_text or not source_text:
        return False
    return primary_text != source_text


def _merge_correlation_id(
    primary_organization_id: str, source_refs: list[dict[str, Any]]
) -> str:
    token = json.dumps(
        {
            "primary": primary_organization_id,
            "sources": source_refs,
        },
        sort_keys=True,
    )
    return f"org-merge:{hashlib.sha1(token.encode('utf-8')).hexdigest()[:16]}"


def _close_name(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens.intersection(right_tokens))
    minimum = min(len(left_tokens), len(right_tokens))
    return overlap >= minimum and abs(len(left) - len(right)) <= 4

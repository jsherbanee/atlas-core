"""Shared organization directory and project stakeholder relationship service."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from atlas_core.domain import Organization, OrganizationRole, ProjectStakeholder


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
        )
        organizations.append(org)
        self._write_json_list(
            self._org_path, [item.to_dict() for item in organizations]
        )
        return org

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

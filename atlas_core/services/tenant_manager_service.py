"""Tenant sandbox manager for deterministic alpha multi-tenant isolation."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from atlas_core.contracts.permissions_contracts import AccessRequest
from atlas_core.contracts.tenant_manager_contracts import (
    SandboxProvisioningRequest,
    SandboxProvisioningResult,
    Tenant,
    TenantAuditEvent,
    TenantConfiguration,
    TenantEnvironment,
    TenantMembership,
    TenantStatus,
    now_iso,
)
from atlas_core.services.permissions_service import PermissionsService


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    return normalized or default


def _slug(value: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", _safe_text(value).lower())
    return lowered.strip("-") or "sandbox"


class TenantManagerService:
    """Deterministic tenant sandbox lifecycle and data-boundary controls."""

    def __init__(
        self,
        *,
        workspace_root: str | Path = "AtlasProjects",
        state: dict[str, Any] | None = None,
        permissions_service: PermissionsService | None = None,
    ) -> None:
        incoming = dict(state or {})
        self.workspace_root = Path(workspace_root)
        self.permissions_service = permissions_service or PermissionsService(
            state=dict(incoming.get("permissions_state") or {})
        )
        self.state: dict[str, Any] = {
            "tenants": dict(incoming.get("tenants") or {}),
            "tenant_data": dict(incoming.get("tenant_data") or {}),
            "audit_events": [
                dict(item)
                for item in list(incoming.get("audit_events") or [])
                if isinstance(item, dict)
            ],
            "active_tenant_id": _safe_text(incoming.get("active_tenant_id"), ""),
            "active_organization_id": _safe_text(
                incoming.get("active_organization_id"), ""
            ),
            "permissions_state": dict(incoming.get("permissions_state") or {}),
        }
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.ensure_default_local_tenant()

    @staticmethod
    def empty_state() -> dict[str, Any]:
        return {
            "tenants": {},
            "tenant_data": {},
            "audit_events": [],
            "active_tenant_id": "",
            "active_organization_id": "",
            "permissions_state": PermissionsService.empty_state(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenants": {
                key: Tenant.from_dict(dict(payload)).to_dict()
                for key, payload in sorted(
                    dict(self.state.get("tenants") or {}).items()
                )
            },
            "tenant_data": {
                key: deepcopy(dict(payload))
                for key, payload in sorted(
                    dict(self.state.get("tenant_data") or {}).items()
                )
            },
            "audit_events": [
                dict(item)
                for item in list(self.state.get("audit_events") or [])
                if isinstance(item, dict)
            ],
            "active_tenant_id": _safe_text(self.state.get("active_tenant_id"), ""),
            "active_organization_id": _safe_text(
                self.state.get("active_organization_id"), ""
            ),
            "permissions_state": self.permissions_service.to_dict(),
        }

    def ensure_default_local_tenant(self) -> Tenant:
        existing = self._tenant_or_none("local")
        if existing is not None:
            return existing
        environment = self._build_environment("local", "atlas")
        tenant = Tenant(
            tenant_id="local",
            tenant_name="Local Atlas Sandbox",
            status=TenantStatus.ACTIVE,
            owner_user_id="local-user",
            environment=environment,
            configuration=TenantConfiguration(
                sandbox_label="Local Atlas Sandbox",
                expiration_date=None,
                enable_seed_data=True,
                seed_data_profile="compatibility",
                test_user_notes="Backward-compatible local default tenant.",
            ),
            memberships=[
                TenantMembership(
                    tenant_id="local",
                    user_id="local-user",
                    role_key="tenant_administrator",
                    is_owner=True,
                    status="active",
                    notes="compatibility",
                )
            ],
            last_activity_at=now_iso(),
        )
        self._save_tenant(tenant)
        self._ensure_tenant_data_container("local")
        self.state["active_tenant_id"] = "local"
        self.state["active_organization_id"] = "atlas"
        return tenant

    def list_tenants(
        self,
        *,
        actor_id: str,
        include_archived: bool = True,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> list[dict[str, Any]]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        rows: list[Tenant] = []
        for payload in dict(self.state.get("tenants") or {}).values():
            tenant = Tenant.from_dict(dict(payload))
            if not include_archived and tenant.status == TenantStatus.ARCHIVED:
                continue
            rows.append(tenant)
        rows.sort(key=lambda item: (item.tenant_name.lower(), item.tenant_id))
        return [item.to_dict() for item in rows]

    def create_sandbox(
        self,
        *,
        request: SandboxProvisioningRequest,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        tenant_id = _safe_text(request.tenant_id, "") or self._allocate_tenant_id(
            request.sandbox_label
        )
        if self._tenant_or_none(tenant_id) is not None:
            raise ValueError("tenant_id already exists")

        org_id = f"org-{tenant_id}"
        environment = self._build_environment(tenant_id, org_id)
        tenant = Tenant(
            tenant_id=tenant_id,
            tenant_name=request.sandbox_label,
            status=TenantStatus.PROVISIONING,
            owner_user_id=request.owner_user_id,
            environment=environment,
            configuration=TenantConfiguration(
                sandbox_label=request.sandbox_label,
                expiration_date=request.expiration_date,
                enable_seed_data=bool(request.enable_seed_data),
                seed_data_profile=request.seed_data_profile,
                test_user_notes=request.test_user_notes,
            ),
            memberships=[
                TenantMembership(
                    tenant_id=tenant_id,
                    user_id=request.owner_user_id,
                    role_key="tenant_administrator",
                    is_owner=True,
                    status="active",
                    notes=request.test_user_notes,
                )
            ],
            last_activity_at=now_iso(),
        )
        self._save_tenant(tenant)
        data_state = self._ensure_tenant_data_container(tenant_id)
        seeded = False
        if request.enable_seed_data:
            self.load_seed_data(
                tenant_id=tenant_id,
                profile=request.seed_data_profile,
                actor_id=actor_id,
                requester_tenant_id=requester_tenant_id,
                requester_organization_id=requester_organization_id,
            )
            seeded = True
            data_state = self._tenant_data(tenant_id)
        tenant = self._set_status_internal(
            tenant_id=tenant_id,
            status=TenantStatus.ACTIVE,
            actor_id=actor_id,
            details={"seeded": seeded},
        )
        self.state["active_tenant_id"] = tenant_id
        self.state["active_organization_id"] = org_id

        result = SandboxProvisioningResult(
            tenant_id=tenant_id,
            status=tenant.status,
            environment=tenant.environment,
            seeded=seeded,
            message="Sandbox provisioned.",
        )
        return {
            "result": result.to_dict(),
            "tenant": tenant.to_dict(),
            "storage_usage_summary": self.storage_usage_summary(tenant_id=tenant_id),
            "health": self.tenant_health(tenant_id=tenant_id),
            "data_summary": self._data_summary(data_state),
        }

    def open_sandbox(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        tenant = self._tenant_required(tenant_id)
        if tenant.status not in {TenantStatus.ACTIVE, TenantStatus.SUSPENDED}:
            raise ValueError("sandbox cannot be opened in current status")
        self.state["active_tenant_id"] = tenant.tenant_id
        self.state["active_organization_id"] = self._organization_id_for_tenant(
            tenant.tenant_id
        )
        self._record_audit(
            tenant_id=tenant.tenant_id,
            actor_id=actor_id,
            action="tenant.opened",
            details={},
        )
        return {
            "tenant_id": tenant.tenant_id,
            "organization_id": self._organization_id_for_tenant(tenant.tenant_id),
            "status": tenant.status.value,
        }

    def suspend_sandbox(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        tenant = self._set_status_internal(
            tenant_id=tenant_id,
            status=TenantStatus.SUSPENDED,
            actor_id=actor_id,
            details={},
        )
        return tenant.to_dict()

    def restore_sandbox(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        tenant = self._set_status_internal(
            tenant_id=tenant_id,
            status=TenantStatus.ACTIVE,
            actor_id=actor_id,
            details={},
        )
        return tenant.to_dict()

    def archive_sandbox(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        tenant = self._set_status_internal(
            tenant_id=tenant_id,
            status=TenantStatus.ARCHIVED,
            actor_id=actor_id,
            details={},
        )
        return tenant.to_dict()

    def load_seed_data(
        self,
        *,
        tenant_id: str,
        profile: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        tenant = self._tenant_required(tenant_id)
        data = self._tenant_data(tenant.tenant_id)
        normalized = _safe_text(profile, "none").lower()
        seed_payload = {
            "profile": normalized,
            "applied_at": now_iso(),
            "seeded_by": actor_id,
        }
        data["catalog"] = {
            "seed_profile": normalized,
            "items": [
                {
                    "catalog_item_id": f"{tenant.tenant_id}:{normalized}:item-{index}",
                    "name": f"{tenant.tenant_name} Seed Item {index}",
                    "tenant_id": tenant.tenant_id,
                }
                for index in range(1, 4)
            ],
        }
        data["transactions"] = {
            "documents": [
                {
                    "document_id": f"{tenant.tenant_id}:{normalized}:txn-1",
                    "tenant_id": tenant.tenant_id,
                    "status": "draft",
                }
            ],
            "seed_metadata": seed_payload,
        }
        data["projects"] = [
            {
                "project_id": f"{tenant.tenant_id}:{normalized}:project-1",
                "tenant_id": tenant.tenant_id,
                "name": f"{tenant.tenant_name} Seed Project",
            }
        ]
        self._touch_activity(tenant.tenant_id)
        self._record_audit(
            tenant_id=tenant.tenant_id,
            actor_id=actor_id,
            action="tenant.seed_loaded",
            details={"profile": normalized},
        )
        return {"tenant_id": tenant.tenant_id, "profile": normalized, "seeded": True}

    def reset_sandbox_data(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        confirmation: str,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        if _safe_text(confirmation, "") != f"RESET {tenant_id}":
            raise ValueError("reset confirmation phrase is invalid")
        data = self._tenant_data(tenant_id)
        preserved_preferences = deepcopy(dict(data.get("user_preferences") or {}))
        data.clear()
        data.update(self._empty_tenant_data(tenant_id))
        data["user_preferences"] = preserved_preferences
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.data_reset",
            details={},
        )
        return {"tenant_id": tenant_id, "reset": True}

    def export_tenant_data(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        tenant = self._tenant_required(tenant_id)
        payload = {
            "tenant": tenant.to_dict(),
            "data": deepcopy(self._tenant_data(tenant.tenant_id)),
            "exported_at": now_iso(),
            "exported_by": actor_id,
        }
        self._tenant_data(tenant.tenant_id)["export_history"] = {
            "last_export_at": payload["exported_at"],
            "last_export_by": actor_id,
        }
        self._record_audit(
            tenant_id=tenant.tenant_id,
            actor_id=actor_id,
            action="tenant.exported",
            details={"bytes": len(json.dumps(payload, sort_keys=True))},
        )
        return payload

    def delete_sandbox_guarded(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        confirmation: str,
        require_export: bool = True,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        expected = f"DELETE {tenant_id}"
        if _safe_text(confirmation, "") != expected:
            raise ValueError("delete confirmation phrase is invalid")
        if tenant_id == "local":
            raise ValueError("local compatibility tenant cannot be deleted")

        data = self._tenant_data(tenant_id)
        export_meta = dict(data.get("export_history") or {})
        if require_export and not _safe_text(export_meta.get("last_export_at"), ""):
            raise ValueError("tenant export is required before deletion")

        self.state.setdefault("tenants", {})
        self.state.setdefault("tenant_data", {})
        del self.state["tenants"][tenant_id]
        del self.state["tenant_data"][tenant_id]
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.deleted",
            details={"required_export": bool(require_export)},
        )
        return {"tenant_id": tenant_id, "deleted": True}

    def assert_active_tenant_context(self, tenant_id: str | None) -> str:
        active = _safe_text(tenant_id, "") or _safe_text(
            self.state.get("active_tenant_id"), ""
        )
        if not active:
            raise PermissionError("active tenant context is required")
        self._tenant_required(active)
        return active

    def assert_same_tenant_reference(
        self,
        *,
        source_tenant_id: str,
        target_tenant_id: str,
        reference_type: str,
    ) -> None:
        if _safe_text(source_tenant_id, "") != _safe_text(target_tenant_id, ""):
            raise ValueError(f"cross-tenant {reference_type} is not allowed")

    def assert_attachment_scope(
        self,
        *,
        tenant_id: str,
        attachment_tenant_id: str,
    ) -> None:
        self.assert_same_tenant_reference(
            source_tenant_id=tenant_id,
            target_tenant_id=attachment_tenant_id,
            reference_type="attachment reference",
        )

    def set_search_index(
        self,
        *,
        tenant_id: str,
        index_key: str,
        records: list[dict[str, Any]],
    ) -> None:
        data = self._tenant_data(tenant_id)
        data.setdefault("search_indexes", {})
        data["search_indexes"][_safe_text(index_key, "default")] = [
            deepcopy(dict(item)) for item in records if isinstance(item, dict)
        ]
        self._touch_activity(tenant_id)

    def get_search_index(
        self, *, tenant_id: str, index_key: str
    ) -> list[dict[str, Any]]:
        data = self._tenant_data(tenant_id)
        index = dict(data.get("search_indexes") or {})
        rows = list(index.get(_safe_text(index_key, "default")) or [])
        return [deepcopy(dict(item)) for item in rows if isinstance(item, dict)]

    def append_job_record(self, *, tenant_id: str, job_payload: dict[str, Any]) -> None:
        data = self._tenant_data(tenant_id)
        data.setdefault("jobs", [])
        data["jobs"].append(deepcopy(dict(job_payload)))
        self._touch_activity(tenant_id)

    def list_job_records(self, *, tenant_id: str) -> list[dict[str, Any]]:
        rows = list(self._tenant_data(tenant_id).get("jobs") or [])
        return [deepcopy(dict(item)) for item in rows if isinstance(item, dict)]

    def set_user_preference(
        self,
        *,
        tenant_id: str,
        user_id: str,
        preference_key: str,
        preference_value: Any,
    ) -> None:
        data = self._tenant_data(tenant_id)
        preferences = data.setdefault("user_preferences", {})
        user_preferences = dict(preferences.get(_safe_text(user_id, "")) or {})
        user_preferences[_safe_text(preference_key, "")] = deepcopy(preference_value)
        preferences[_safe_text(user_id, "")] = user_preferences
        self._touch_activity(tenant_id)

    def user_preferences(self, *, tenant_id: str, user_id: str) -> dict[str, Any]:
        data = self._tenant_data(tenant_id)
        return deepcopy(dict((data.get("user_preferences") or {}).get(user_id) or {}))

    def set_working_set(
        self,
        *,
        tenant_id: str,
        user_id: str,
        object_ids: list[str],
    ) -> None:
        data = self._tenant_data(tenant_id)
        working_set = data.setdefault("working_set", {})
        working_set[_safe_text(user_id, "")] = [
            _safe_text(item, "") for item in object_ids if _safe_text(item, "")
        ]
        self._touch_activity(tenant_id)

    def working_set(self, *, tenant_id: str, user_id: str) -> list[str]:
        data = self._tenant_data(tenant_id)
        rows = list((data.get("working_set") or {}).get(user_id) or [])
        return [_safe_text(item, "") for item in rows if _safe_text(item, "")]

    def tenant_health(self, *, tenant_id: str) -> dict[str, Any]:
        tenant = self._tenant_required(tenant_id)
        data = self._tenant_data(tenant_id)
        expired = False
        if tenant.configuration.expiration_date:
            try:
                expired = datetime.fromisoformat(
                    tenant.configuration.expiration_date
                ) < datetime.now(UTC)
            except ValueError:
                expired = False
        return {
            "tenant_id": tenant.tenant_id,
            "status": tenant.status.value,
            "expired": expired,
            "has_seed_data": bool(dict(data.get("catalog") or {}).get("items")),
            "job_count": len(list(data.get("jobs") or [])),
            "attachment_count": len(list(data.get("attachments") or [])),
            "audit_event_count": len(
                self.recent_tenant_audit_events(tenant_id=tenant_id, limit=500)
            ),
        }

    def storage_usage_summary(self, *, tenant_id: str) -> dict[str, Any]:
        data = self._tenant_data(tenant_id)
        return {
            "projects": len(list(data.get("projects") or [])),
            "knowledge_records": len(list(data.get("knowledge") or [])),
            "catalog_items": len(
                list(dict(data.get("catalog") or {}).get("items") or [])
            ),
            "transactions": len(
                list(dict(data.get("transactions") or {}).get("documents") or [])
            ),
            "attachments": len(list(data.get("attachments") or [])),
            "jobs": len(list(data.get("jobs") or [])),
            "search_indexes": len(dict(data.get("search_indexes") or {})),
        }

    def recent_tenant_audit_events(
        self, *, tenant_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        rows = [
            TenantAuditEvent(**dict(item)).to_dict()
            for item in list(self.state.get("audit_events") or [])
            if isinstance(item, dict)
            and _safe_text(item.get("tenant_id"), "") == tenant_id
        ]
        rows.sort(
            key=lambda item: (
                str(item.get("occurred_at") or ""),
                str(item.get("event_id") or ""),
            )
        )
        return rows[-max(1, int(limit)) :]

    def _assert_platform_admin(
        self,
        *,
        actor_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> None:
        decision = self.permissions_service.evaluate(
            AccessRequest(
                tenant_id=_safe_text(tenant_id, "local"),
                organization_id=_safe_text(organization_id, "atlas"),
                principal_id=_safe_text(actor_id, "local-user"),
                permission_key="platform.tenants.manage",
                project_id=None,
            )
        )
        if not decision.allowed:
            raise PermissionError(
                decision.reason or "platform tenant management is not allowed"
            )

    def _allocate_tenant_id(self, sandbox_label: str) -> str:
        token = _slug(sandbox_label)
        digest = hashlib.sha1(f"{token}:{now_iso()}".encode("utf-8")).hexdigest()[:8]
        return f"tnt-{token[:24]}-{digest}"

    def _build_environment(
        self, tenant_id: str, organization_id: str
    ) -> TenantEnvironment:
        root = self.workspace_root / ".atlas_tenants" / tenant_id / organization_id
        root.mkdir(parents=True, exist_ok=True)
        paths: dict[str, str] = {}
        for key in (
            "projects",
            "knowledge",
            "catalog",
            "transactions",
            "settings",
            "templates",
            "attachments",
            "audit",
            "jobs",
            "search_indexes",
            "working_set",
            "user_preferences",
        ):
            candidate = root / key
            candidate.mkdir(parents=True, exist_ok=True)
            paths[key] = str(candidate)
        return TenantEnvironment(
            environment_id=f"env-{tenant_id}",
            tenant_id=tenant_id,
            environment_type="alpha_sandbox",
            storage_root=str(root),
            repository_paths=paths,
        )

    def _organization_id_for_tenant(self, tenant_id: str) -> str:
        return "atlas" if tenant_id == "local" else f"org-{tenant_id}"

    def _tenant_or_none(self, tenant_id: str) -> Tenant | None:
        payload = dict(self.state.get("tenants") or {}).get(_safe_text(tenant_id, ""))
        if not isinstance(payload, dict) or not payload:
            return None
        return Tenant.from_dict(dict(payload))

    def _tenant_required(self, tenant_id: str) -> Tenant:
        tenant = self._tenant_or_none(tenant_id)
        if tenant is None:
            raise ValueError("tenant does not exist")
        return tenant

    def _save_tenant(self, tenant: Tenant) -> None:
        self.state.setdefault("tenants", {})
        self.state["tenants"][tenant.tenant_id] = tenant.to_dict()

    def _empty_tenant_data(self, tenant_id: str) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "projects": [],
            "knowledge": [],
            "catalog": {},
            "transactions": {},
            "settings": {},
            "templates": {},
            "attachments": [],
            "audit": [],
            "jobs": [],
            "search_indexes": {},
            "working_set": {},
            "user_preferences": {},
            "export_history": {},
        }

    def _ensure_tenant_data_container(self, tenant_id: str) -> dict[str, Any]:
        self.state.setdefault("tenant_data", {})
        payload = self.state["tenant_data"].get(tenant_id)
        if isinstance(payload, dict):
            return payload
        seeded = self._empty_tenant_data(tenant_id)
        self.state["tenant_data"][tenant_id] = seeded
        return seeded

    def _tenant_data(self, tenant_id: str) -> dict[str, Any]:
        self._tenant_required(tenant_id)
        return self._ensure_tenant_data_container(tenant_id)

    def _data_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "projects": len(list(data.get("projects") or [])),
            "catalog_items": len(
                list(dict(data.get("catalog") or {}).get("items") or [])
            ),
            "transactions": len(
                list(dict(data.get("transactions") or {}).get("documents") or [])
            ),
        }

    def _touch_activity(self, tenant_id: str) -> None:
        tenant = self._tenant_required(tenant_id)
        updated = Tenant(
            tenant_id=tenant.tenant_id,
            tenant_name=tenant.tenant_name,
            status=tenant.status,
            owner_user_id=tenant.owner_user_id,
            environment=tenant.environment,
            configuration=tenant.configuration,
            memberships=list(tenant.memberships),
            created_at=tenant.created_at,
            updated_at=now_iso(),
            last_activity_at=now_iso(),
        )
        self._save_tenant(updated)

    def _set_status_internal(
        self,
        *,
        tenant_id: str,
        status: TenantStatus,
        actor_id: str,
        details: dict[str, Any],
    ) -> Tenant:
        tenant = self._tenant_required(tenant_id)
        updated = Tenant(
            tenant_id=tenant.tenant_id,
            tenant_name=tenant.tenant_name,
            status=status,
            owner_user_id=tenant.owner_user_id,
            environment=tenant.environment,
            configuration=tenant.configuration,
            memberships=list(tenant.memberships),
            created_at=tenant.created_at,
            updated_at=now_iso(),
            last_activity_at=now_iso(),
        )
        self._save_tenant(updated)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=f"tenant.status.{status.value}",
            details=details,
        )
        return updated

    def _record_audit(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        action: str,
        details: dict[str, Any],
    ) -> None:
        event = TenantAuditEvent(
            event_id=f"tenant-audit:{hashlib.sha1(f'{tenant_id}:{action}:{now_iso()}'.encode('utf-8')).hexdigest()[:16]}",
            tenant_id=tenant_id,
            actor_id=_safe_text(actor_id, "system"),
            action=action,
            details=deepcopy(dict(details)),
            occurred_at=now_iso(),
        )
        self.state.setdefault("audit_events", [])
        self.state["audit_events"].append(event.to_dict())
        self.state["audit_events"] = list(self.state["audit_events"])[-5000:]

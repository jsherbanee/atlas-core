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
from atlas_core.contracts.error_logging_contracts import (
    ApplicationError,
    ErrorContext,
    ErrorOccurrence,
    ErrorResolutionStatus,
    ErrorSeverity,
)
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


def _redact_diagnostic_value(key: str, value: Any) -> Any:
    key_lower = _safe_text(key, "").lower()
    if any(
        token in key_lower
        for token in (
            "secret",
            "token",
            "password",
            "credential",
            "storage_root",
            "repository_paths",
        )
    ):
        return "[redacted]"
    if isinstance(value, dict):
        return {
            str(child_key): _redact_diagnostic_value(str(child_key), child_value)
            for child_key, child_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_diagnostic_value(key, item) for item in value]
    if isinstance(value, str):
        text = _safe_text(value, "")
        if "secret://" in text:
            return "[redacted-secret-reference]"
        if (
            text.startswith("/")
            or text.startswith("~")
            or text.startswith(".atlas_tenants")
            or "/Users/" in text
            or "\\" in text
        ):
            return "[redacted-path]"
        return text[:240]
    return value


def _sanitize_free_text(value: Any, *, max_length: int = 1024) -> str:
    sanitized = _safe_text(value, "")
    if not sanitized:
        return ""
    lowered = sanitized.lower()
    if "secret://" in lowered:
        return "[redacted-secret-reference]"
    if any(
        token in lowered
        for token in (
            "password",
            "passwd",
            "token",
            "secret",
            "credential",
            "authorization",
            "api_key",
            "private_key",
        )
    ):
        return "[redacted-sensitive]"
    if (
        "/Users/" in sanitized
        or sanitized.startswith("/")
        or sanitized.startswith("~")
        or "\\" in sanitized
    ):
        return "[redacted-path]"
    redacted_email = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "[redacted-email]",
        sanitized,
    )
    return redacted_email[:max_length]


def _sanitize_stack_trace(value: Any) -> str:
    lines = [
        _sanitize_free_text(item, max_length=320)
        for item in _safe_text(value, "").splitlines()
        if _safe_text(item, "")
    ]
    if not lines:
        return "[stack-trace-unavailable]"
    return "\n".join(lines[-40:])


def _normalize_choice(value: str, *, allowed: set[str], label: str) -> str:
    token = _safe_text(value, "").replace("_", " ").lower()
    for item in sorted(allowed):
        if token == item.lower():
            return item
    raise ValueError(f"{label} is invalid")


_ALPHA_TESTER_STATES = {
    "invited",
    "onboarding",
    "active",
    "paused",
    "completed",
    "deactivated",
}

_ALPHA_SCENARIO_STATUS = {"pending", "in_progress", "completed"}

_ALPHA_DEFECT_SEVERITY_CHOICES = {
    "Critical",
    "High",
    "Medium",
    "Low",
    "Enhancement",
}

_ALPHA_DEFECT_STATUS_CHOICES = {
    "New",
    "Needs Reproduction",
    "Confirmed",
    "In Progress",
    "Ready for Retest",
    "Verified",
    "Deferred",
    "Closed",
}

_ALPHA_REPRODUCTION_STATUS_CHOICES = {
    "Not Attempted",
    "Needs Reproduction",
    "Reproduced",
    "Not Reproduced",
}

_ALPHA_RETEST_STATUS_CHOICES = {
    "Not Started",
    "Ready for Retest",
    "Retest In Progress",
    "Passed",
    "Failed",
}

_ALPHA_RESOLUTION_PRIORITY_CHOICES = {"P0", "P1", "P2", "P3", "Backlog"}

_ALPHA_RELEASE_STATUS_CHOICES = {
    "Draft",
    "Approved",
    "Deployed to Sandbox",
    "Under Test",
    "Accepted",
    "Superseded",
    "Withdrawn",
}

_ALPHA_SCENARIO_TEMPLATES: list[dict[str, str]] = [
    {
        "scenario_key": "organization_settings",
        "title": "Organization Settings",
        "instructions": "Review organization profile settings and validate metadata persistence.",
        "expected_outcome": "Settings updates save deterministically with tenant scope.",
    },
    {
        "scenario_key": "customer_project_creation",
        "title": "Customer and Project Creation",
        "instructions": "Create a customer and a project, then verify project visibility in tenant scope.",
        "expected_outcome": "Customer and project are created and visible only in assigned tenant.",
    },
    {
        "scenario_key": "catalog_browsing",
        "title": "Catalog Browsing",
        "instructions": "Browse commercial catalog content and inspect representative item detail views.",
        "expected_outcome": "Catalog rows render consistently with tenant-scoped records.",
    },
    {
        "scenario_key": "estimate_creation_pdf",
        "title": "Estimate Creation and PDF",
        "instructions": "Create an estimate and run deterministic PDF export.",
        "expected_outcome": "Estimate draft and PDF export complete without cross-tenant leakage.",
    },
    {
        "scenario_key": "sales_order_creation",
        "title": "Sales Order Creation",
        "instructions": "Create a sales order from valid source data and verify lifecycle state.",
        "expected_outcome": "Sales order is created with expected numbering and status behavior.",
    },
    {
        "scenario_key": "change_order_tracking",
        "title": "Change Order Tracking",
        "instructions": "Exercise additive/deductive change-order tracking on existing project transactions.",
        "expected_outcome": "Change-order metadata and rollups remain deterministic.",
    },
    {
        "scenario_key": "customer_invoice",
        "title": "Customer Invoice",
        "instructions": "Create a customer invoice and verify draft-state metadata and export path.",
        "expected_outcome": "Invoice draft workflow completes with deterministic metadata.",
    },
    {
        "scenario_key": "return_order_credit_memo",
        "title": "Return Order and Credit Memo",
        "instructions": "Create a return order and linked credit memo for representative tenant data.",
        "expected_outcome": "Return and credit workflows complete with valid linked references.",
    },
    {
        "scenario_key": "search_object_workspace",
        "title": "Search and Object Workspace",
        "instructions": "Validate search and object-workspace navigation continuity in assigned tenant.",
        "expected_outcome": "Search results and object views remain tenant-scoped and stable.",
    },
    {
        "scenario_key": "attachments",
        "title": "Attachments",
        "instructions": "Upload and review attachment metadata while respecting extension constraints.",
        "expected_outcome": "Attachment handling remains deterministic and tenant-scoped.",
    },
    {
        "scenario_key": "permissions",
        "title": "Permissions",
        "instructions": "Validate allowed and denied operations under assigned tenant user context.",
        "expected_outcome": "Permission boundaries enforce tenant-scoped least privilege behavior.",
    },
    {
        "scenario_key": "error_reporting",
        "title": "Error Reporting",
        "instructions": "Submit feedback linked to Error ID and verify sanitized error visibility.",
        "expected_outcome": "Feedback and error linkage is retained with redacted diagnostics.",
    },
]


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
            "alpha_tester_cohorts": dict(incoming.get("alpha_tester_cohorts") or {}),
            "alpha_release_records": [
                dict(item)
                for item in list(incoming.get("alpha_release_records") or [])
                if isinstance(item, dict)
            ],
            "alpha_stabilization_history": [
                dict(item)
                for item in list(incoming.get("alpha_stabilization_history") or [])
                if isinstance(item, dict)
            ],
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
            "alpha_tester_cohorts": {},
            "alpha_release_records": [],
            "alpha_stabilization_history": [],
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
            "alpha_tester_cohorts": {
                key: deepcopy(dict(payload))
                for key, payload in sorted(
                    dict(self.state.get("alpha_tester_cohorts") or {}).items()
                )
            },
            "alpha_release_records": [
                deepcopy(dict(item))
                for item in list(self.state.get("alpha_release_records") or [])
                if isinstance(item, dict)
            ],
            "alpha_stabilization_history": [
                deepcopy(dict(item))
                for item in list(self.state.get("alpha_stabilization_history") or [])
                if isinstance(item, dict)
            ],
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
        self._assert_operational_access(active)
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
        self._assert_operational_access(tenant_id)
        data = self._tenant_data(tenant_id)
        data.setdefault("search_indexes", {})
        data["search_indexes"][_safe_text(index_key, "default")] = [
            deepcopy(dict(item)) for item in records if isinstance(item, dict)
        ]
        self._touch_activity(tenant_id)

    def get_search_index(
        self, *, tenant_id: str, index_key: str
    ) -> list[dict[str, Any]]:
        self._assert_operational_access(tenant_id)
        data = self._tenant_data(tenant_id)
        index = dict(data.get("search_indexes") or {})
        rows = list(index.get(_safe_text(index_key, "default")) or [])
        return [deepcopy(dict(item)) for item in rows if isinstance(item, dict)]

    def append_job_record(self, *, tenant_id: str, job_payload: dict[str, Any]) -> None:
        self._assert_operational_access(tenant_id)
        data = self._tenant_data(tenant_id)
        data.setdefault("jobs", [])
        data["jobs"].append(deepcopy(dict(job_payload)))
        self._touch_activity(tenant_id)

    def list_job_records(self, *, tenant_id: str) -> list[dict[str, Any]]:
        self._assert_operational_access(tenant_id)
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
        self._assert_operational_access(tenant_id)
        data = self._tenant_data(tenant_id)
        preferences = data.setdefault("user_preferences", {})
        user_preferences = dict(preferences.get(_safe_text(user_id, "")) or {})
        user_preferences[_safe_text(preference_key, "")] = deepcopy(preference_value)
        preferences[_safe_text(user_id, "")] = user_preferences
        self._touch_activity(tenant_id)

    def user_preferences(self, *, tenant_id: str, user_id: str) -> dict[str, Any]:
        self._assert_operational_access(tenant_id)
        data = self._tenant_data(tenant_id)
        return deepcopy(dict((data.get("user_preferences") or {}).get(user_id) or {}))

    def set_working_set(
        self,
        *,
        tenant_id: str,
        user_id: str,
        object_ids: list[str],
    ) -> None:
        self._assert_operational_access(tenant_id)
        data = self._tenant_data(tenant_id)
        working_set = data.setdefault("working_set", {})
        working_set[_safe_text(user_id, "")] = [
            _safe_text(item, "") for item in object_ids if _safe_text(item, "")
        ]
        self._touch_activity(tenant_id)

    def working_set(self, *, tenant_id: str, user_id: str) -> list[str]:
        self._assert_operational_access(tenant_id)
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

    def log_application_error(
        self,
        *,
        actor_id: str,
        tenant_id: str,
        environment_label: str,
        application_version: str,
        severity: str,
        exception_type: str,
        message: str,
        stack_trace: str,
        workspace: str,
        route: str,
        related_object_id: str | None = None,
        related_object_type: str | None = None,
        correlation_id: str | None = None,
        background_job_id: str | None = None,
        request_or_session_ref: str | None = None,
        integration_hook: str | None = None,
    ) -> dict[str, Any]:
        tenant = self._tenant_required(tenant_id)
        data = self._tenant_data(tenant.tenant_id)
        errors = data.setdefault("application_errors", [])

        normalized_severity = _safe_text(severity, ErrorSeverity.MEDIUM.value).lower()
        if normalized_severity not in {item.value for item in ErrorSeverity}:
            normalized_severity = ErrorSeverity.MEDIUM.value

        normalized_exception_type = _safe_text(exception_type, "Exception")
        normalized_workspace = _safe_text(workspace, "Unknown")
        normalized_route = _safe_text(route, "Unknown")
        sanitized_message = _sanitize_free_text(message) or "[message-unavailable]"
        sanitized_stack_trace = _sanitize_stack_trace(stack_trace)
        normalized_related_object_type = _safe_text(related_object_type, "")
        normalized_related_object_id = _safe_text(related_object_id, "")
        normalized_correlation_id = _safe_text(correlation_id, "")
        normalized_job_id = _safe_text(background_job_id, "")

        fingerprint_source = "|".join(
            [
                tenant.tenant_id,
                normalized_exception_type.lower(),
                sanitized_message.lower(),
                normalized_workspace.lower(),
                normalized_route.lower(),
                normalized_related_object_type.lower(),
                normalized_related_object_id.lower(),
                normalized_job_id.lower(),
                normalized_correlation_id.lower(),
            ]
        )
        fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[
            :20
        ]

        existing: dict[str, Any] | None = None
        for item in errors:
            candidate = dict(item)
            if _safe_text(candidate.get("fingerprint"), "") == fingerprint:
                existing = item
                break

        timestamp = now_iso()
        error_id = (
            _safe_text(existing.get("error_id"), "")
            if isinstance(existing, dict)
            else f"ERR-{hashlib.sha1(f'{tenant.tenant_id}:{fingerprint}'.encode('utf-8')).hexdigest()[:12].upper()}"
        )
        status = (
            _safe_text(existing.get("status"), ErrorResolutionStatus.NEW.value)
            if isinstance(existing, dict)
            else ErrorResolutionStatus.NEW.value
        )
        if status == ErrorResolutionStatus.RESOLVED.value:
            status = ErrorResolutionStatus.REOPENED.value

        occurrence = ErrorOccurrence(
            occurrence_id=f"error-occurrence:{hashlib.sha1(f'{error_id}:{timestamp}'.encode('utf-8')).hexdigest()[:16]}",
            error_id=error_id,
            timestamp=timestamp,
            exception_type=normalized_exception_type,
            sanitized_message=sanitized_message,
            sanitized_stack_trace=sanitized_stack_trace,
            actor_id=_safe_text(actor_id, "system") or None,
        ).to_dict()

        if not isinstance(existing, dict):
            created = ApplicationError(
                error_id=error_id,
                fingerprint=fingerprint,
                tenant_id=tenant.tenant_id,
                actor_id=_safe_text(actor_id, "system") or None,
                environment_label=_safe_text(environment_label, "Controlled Alpha"),
                application_version=_safe_text(application_version, "0.0.0-alpha"),
                severity=ErrorSeverity(normalized_severity),
                status=ErrorResolutionStatus(status),
                summary=sanitized_message,
                context=ErrorContext(
                    workspace=normalized_workspace,
                    route=normalized_route,
                    related_object_id=normalized_related_object_id or None,
                    related_object_type=normalized_related_object_type or None,
                    correlation_id=normalized_correlation_id or None,
                    background_job_id=normalized_job_id or None,
                    request_or_session_ref=request_or_session_ref,
                    integration_hook=integration_hook,
                ),
                first_seen_at=timestamp,
                last_seen_at=timestamp,
                occurrence_count=1,
            ).to_dict()
            created["occurrences"] = [occurrence]
            errors.append(created)
            self._record_audit(
                tenant_id=tenant.tenant_id,
                actor_id=actor_id,
                action="tenant.application_error.logged",
                details={
                    "error_id": error_id,
                    "severity": normalized_severity,
                    "status": status,
                },
            )
            return deepcopy(created)

        occurrences = list(existing.get("occurrences") or [])
        occurrences.append(occurrence)
        existing["occurrences"] = occurrences[-200:]
        existing["last_seen_at"] = timestamp
        existing["occurrence_count"] = int(existing.get("occurrence_count") or 1) + 1
        existing["status"] = status
        existing["severity"] = normalized_severity
        existing["summary"] = sanitized_message
        existing["environment_label"] = _safe_text(
            environment_label, "Controlled Alpha"
        )
        existing["application_version"] = _safe_text(application_version, "0.0.0-alpha")
        context = dict(existing.get("context") or {})
        context.update(
            {
                "workspace": normalized_workspace,
                "route": normalized_route,
                "related_object_id": normalized_related_object_id or None,
                "related_object_type": normalized_related_object_type or None,
                "correlation_id": normalized_correlation_id or None,
                "background_job_id": normalized_job_id or None,
                "request_or_session_ref": _safe_text(request_or_session_ref, "")
                or context.get("request_or_session_ref"),
                "integration_hook": _safe_text(integration_hook, "")
                or context.get("integration_hook"),
            }
        )
        existing["context"] = context
        if status == ErrorResolutionStatus.REOPENED.value:
            self._record_audit(
                tenant_id=tenant.tenant_id,
                actor_id=actor_id,
                action="tenant.application_error.reopened",
                details={"error_id": error_id},
            )
        return deepcopy(existing)

    def list_application_errors(
        self,
        *,
        requester_tenant_id: str,
        requester_organization_id: str,
        actor_id: str,
        tenant_id: str | None = None,
        severities: list[str] | None = None,
        statuses: list[str] | None = None,
        limit: int = 250,
    ) -> list[dict[str, Any]]:
        is_platform_admin = self._is_platform_admin_scope_actor(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        requester_tenant = _safe_text(requester_tenant_id, "")
        if not is_platform_admin:
            self._assert_operational_access(requester_tenant)

        requested_tenant = _safe_text(tenant_id, "")
        if requested_tenant and not is_platform_admin:
            self._assert_tenant_scope_request(
                tenant_id=requested_tenant,
                requester_tenant_id=requester_tenant_id,
                requester_organization_id=requester_organization_id,
            )

        tenant_ids = (
            [requested_tenant]
            if requested_tenant
            else sorted(dict(self.state.get("tenants") or {}).keys())
        )
        if not is_platform_admin and not requested_tenant:
            tenant_ids = [requester_tenant]

        selected_severities = {
            _safe_text(item, "").lower() for item in list(severities or []) if item
        }
        selected_statuses = {
            _safe_text(item, "").lower() for item in list(statuses or []) if item
        }

        rows: list[dict[str, Any]] = []
        for current_tenant in tenant_ids:
            if not _safe_text(current_tenant, ""):
                continue
            tenant_rows = list(
                self._tenant_data(current_tenant).get("application_errors") or []
            )
            for item in tenant_rows:
                payload = dict(item)
                severity = _safe_text(payload.get("severity"), "").lower()
                status = _safe_text(payload.get("status"), "").lower()
                if selected_severities and severity not in selected_severities:
                    continue
                if selected_statuses and status not in selected_statuses:
                    continue
                context = dict(payload.get("context") or {})
                rows.append(
                    {
                        "error_id": _safe_text(payload.get("error_id"), ""),
                        "severity": severity,
                        "summary": _safe_text(payload.get("summary"), ""),
                        "tenant_id": _safe_text(
                            payload.get("tenant_id"), current_tenant
                        ),
                        "workspace": _safe_text(context.get("workspace"), "Unknown"),
                        "route": _safe_text(context.get("route"), "Unknown"),
                        "related_object": (
                            f"{_safe_text(context.get('related_object_type'), '')}:{_safe_text(context.get('related_object_id'), '')}".strip(
                                ":"
                            )
                        ),
                        "first_seen_at": _safe_text(payload.get("first_seen_at"), ""),
                        "last_seen_at": _safe_text(payload.get("last_seen_at"), ""),
                        "occurrence_count": int(payload.get("occurrence_count") or 0),
                        "status": status,
                    }
                )

        rows.sort(
            key=lambda item: (
                _safe_text(item.get("last_seen_at"), ""),
                _safe_text(item.get("error_id"), ""),
            )
        )
        return rows[-max(1, int(limit)) :]

    def get_application_error_details(
        self,
        *,
        requester_tenant_id: str,
        requester_organization_id: str,
        actor_id: str,
        tenant_id: str,
        error_id: str,
    ) -> dict[str, Any]:
        self._assert_error_log_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        rows = list(self._tenant_data(tenant_id).get("application_errors") or [])
        for item in rows:
            payload = dict(item)
            if _safe_text(payload.get("error_id"), "") == _safe_text(error_id, ""):
                return deepcopy(payload)
        raise ValueError("application error does not exist")

    def update_application_error_status(
        self,
        *,
        requester_tenant_id: str,
        requester_organization_id: str,
        actor_id: str,
        tenant_id: str,
        error_id: str,
        status: str,
        resolution_notes: str | None = None,
    ) -> dict[str, Any]:
        self._assert_error_log_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        normalized_status = _safe_text(status, "").lower()
        if normalized_status not in {item.value for item in ErrorResolutionStatus}:
            raise ValueError("error status is invalid")

        rows = list(self._tenant_data(tenant_id).get("application_errors") or [])
        target: dict[str, Any] | None = None
        for item in rows:
            if _safe_text(dict(item).get("error_id"), "") == _safe_text(error_id, ""):
                target = item
                break
        if not isinstance(target, dict):
            raise ValueError("application error does not exist")

        target["status"] = normalized_status
        target["last_seen_at"] = now_iso()
        if resolution_notes is not None:
            target["resolution_notes"] = _sanitize_free_text(resolution_notes) or None
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.application_error.status_updated",
            details={"error_id": _safe_text(error_id, ""), "status": normalized_status},
        )
        return deepcopy(target)

    def export_application_error_diagnostics(
        self,
        *,
        requester_tenant_id: str,
        requester_organization_id: str,
        actor_id: str,
        tenant_id: str,
        statuses: list[str] | None = None,
        severities: list[str] | None = None,
    ) -> dict[str, Any]:
        self._assert_error_log_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        summary_rows = self.list_application_errors(
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            actor_id=actor_id,
            tenant_id=tenant_id,
            statuses=statuses,
            severities=severities,
            limit=1000,
        )
        details: list[dict[str, Any]] = []
        for item in summary_rows:
            details.append(
                self.get_application_error_details(
                    requester_tenant_id=requester_tenant_id,
                    requester_organization_id=requester_organization_id,
                    actor_id=actor_id,
                    tenant_id=tenant_id,
                    error_id=_safe_text(item.get("error_id"), ""),
                )
            )
        return {
            "tenant_id": tenant_id,
            "exported_at": now_iso(),
            "exported_by": _safe_text(actor_id, "system"),
            "errors": details,
        }

    def list_alpha_scenario_templates(self) -> list[dict[str, str]]:
        return [deepcopy(item) for item in _ALPHA_SCENARIO_TEMPLATES]

    def assign_alpha_tester(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        tester_id: str,
        display_name: str,
        email: str,
        sandbox_expiration: str | None = None,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        self._assert_operational_access(tenant_id)
        normalized_tester_id = _safe_text(tester_id, "")
        if not normalized_tester_id:
            raise ValueError("tester_id is required")
        data = self._tenant_data(tenant_id)
        testers = data.setdefault("alpha_testers", {})
        existing = dict(testers.get(normalized_tester_id) or {})
        base_state = _safe_text(existing.get("state"), "invited").lower()
        if base_state not in _ALPHA_TESTER_STATES:
            base_state = "invited"
        tenant = self._tenant_required(tenant_id)
        default_expiration = _safe_text(tenant.configuration.expiration_date, "")
        record = {
            "tester_id": normalized_tester_id,
            "tenant_id": tenant_id,
            "organization_id": self._organization_id_for_tenant(tenant_id),
            "display_name": _safe_text(display_name, normalized_tester_id),
            "email": _sanitize_free_text(email, max_length=180),
            "state": base_state,
            "sandbox_expiration": _safe_text(
                sandbox_expiration,
                default_expiration,
            )
            or None,
            "assigned_at": _safe_text(existing.get("assigned_at"), now_iso()),
            "assigned_by": _safe_text(existing.get("assigned_by"), actor_id),
            "terms_acknowledged": bool(existing.get("terms_acknowledged", False)),
            "terms_acknowledged_at": _safe_text(
                existing.get("terms_acknowledged_at"), ""
            )
            or None,
            "known_limitations_acknowledged": bool(
                existing.get("known_limitations_acknowledged", False)
            ),
            "known_limitations_acknowledged_at": _safe_text(
                existing.get("known_limitations_acknowledged_at"), ""
            )
            or None,
            "last_activity_at": _safe_text(existing.get("last_activity_at"), now_iso()),
            "last_activity_summary": _safe_text(
                existing.get("last_activity_summary"), "tester_assigned"
            ),
            "deactivated_at": _safe_text(existing.get("deactivated_at"), "") or None,
            "deactivated_by": _safe_text(existing.get("deactivated_by"), "") or None,
        }
        testers[normalized_tester_id] = record
        data.setdefault("alpha_tester_scenarios", {})
        data["alpha_tester_scenarios"].setdefault(normalized_tester_id, [])
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_tester.assigned",
            details={"tester_id": normalized_tester_id},
        )
        return self.get_alpha_tester(
            tenant_id=tenant_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            actor_id=actor_id,
            tester_id=normalized_tester_id,
        )

    def get_alpha_tester(
        self,
        *,
        tenant_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        actor_id: str,
        tester_id: str,
    ) -> dict[str, Any]:
        self._assert_tester_admin_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        data = self._tenant_data(tenant_id)
        testers = dict(data.get("alpha_testers") or {})
        normalized_tester_id = _safe_text(tester_id, "")
        payload = dict(testers.get(normalized_tester_id) or {})
        if not payload:
            raise ValueError("alpha tester does not exist")
        payload.update(
            self._alpha_tester_summary(
                tenant_id=tenant_id, tester_id=normalized_tester_id
            )
        )
        return payload

    def list_alpha_testers(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        tenant_id: str | None = None,
        states: list[str] | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        is_platform_admin = self._is_platform_admin_scope_actor(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        requested_tenant = _safe_text(tenant_id, "")
        if not is_platform_admin:
            self._assert_tenant_scope_request(
                tenant_id=requested_tenant or requester_tenant_id,
                requester_tenant_id=requester_tenant_id,
                requester_organization_id=requester_organization_id,
            )
            self._assert_operational_access(requested_tenant or requester_tenant_id)
        tenant_ids = (
            [requested_tenant]
            if requested_tenant
            else sorted(dict(self.state.get("tenants") or {}).keys())
        )
        if not is_platform_admin and not requested_tenant:
            tenant_ids = [_safe_text(requester_tenant_id, "")]
        requested_states = {
            _safe_text(item, "").lower() for item in list(states or []) if item
        }
        rows: list[dict[str, Any]] = []
        for current_tenant_id in tenant_ids:
            if not current_tenant_id:
                continue
            testers = dict(
                self._tenant_data(current_tenant_id).get("alpha_testers") or {}
            )
            for tester_id, payload in testers.items():
                tester = dict(payload)
                state = _safe_text(tester.get("state"), "invited").lower()
                if requested_states and state not in requested_states:
                    continue
                tester.update(
                    self._alpha_tester_summary(
                        tenant_id=current_tenant_id,
                        tester_id=_safe_text(tester_id, ""),
                    )
                )
                rows.append(tester)
        rows.sort(
            key=lambda item: (
                _safe_text(item.get("last_activity_at"), ""),
                _safe_text(item.get("tester_id"), ""),
            )
        )
        return rows[-max(1, int(limit)) :]

    def acknowledge_alpha_onboarding(
        self,
        *,
        tenant_id: str,
        tester_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        terms_acknowledged: bool,
        known_limitations_acknowledged: bool,
    ) -> dict[str, Any]:
        self._assert_tester_admin_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        tester = self._alpha_tester_record_mutable(
            tenant_id=tenant_id, tester_id=tester_id
        )
        tester["terms_acknowledged"] = bool(terms_acknowledged)
        tester["known_limitations_acknowledged"] = bool(known_limitations_acknowledged)
        if terms_acknowledged:
            tester["terms_acknowledged_at"] = now_iso()
        if known_limitations_acknowledged:
            tester["known_limitations_acknowledged_at"] = now_iso()
        if tester["state"] == "invited":
            tester["state"] = "onboarding"
        tester["last_activity_at"] = now_iso()
        tester["last_activity_summary"] = "acknowledgements_recorded"
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_tester.acknowledged",
            details={
                "tester_id": _safe_text(tester_id, ""),
                "terms": bool(terms_acknowledged),
                "limitations": bool(known_limitations_acknowledged),
            },
        )
        return deepcopy(tester)

    def assign_alpha_scenarios(
        self,
        *,
        tenant_id: str,
        tester_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        scenario_keys: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        self._assert_tester_admin_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        _ = self._alpha_tester_record_mutable(tenant_id=tenant_id, tester_id=tester_id)
        allowed = {
            _safe_text(item.get("scenario_key"), ""): dict(item)
            for item in _ALPHA_SCENARIO_TEMPLATES
        }
        requested = [
            _safe_text(item, "") for item in list(scenario_keys or list(allowed.keys()))
        ]
        cleaned = [item for item in requested if item in allowed]
        if not cleaned:
            raise ValueError("at least one valid scenario is required")
        data = self._tenant_data(tenant_id)
        scenario_map = data.setdefault("alpha_tester_scenarios", {})
        existing_rows = list(scenario_map.get(_safe_text(tester_id, "")) or [])
        existing_by_key = {
            _safe_text(dict(item).get("scenario_key"), ""): dict(item)
            for item in existing_rows
            if isinstance(item, dict)
        }
        assigned_rows: list[dict[str, Any]] = []
        for key in cleaned:
            template = dict(allowed[key])
            row = dict(existing_by_key.get(key) or {})
            if not row:
                row = {
                    "scenario_id": f"scenario:{hashlib.sha1(f'{tenant_id}:{tester_id}:{key}'.encode('utf-8')).hexdigest()[:16]}",
                    "scenario_key": key,
                    "title": template["title"],
                    "instructions": template["instructions"],
                    "expected_outcome": template["expected_outcome"],
                    "status": "pending",
                    "tester_notes": None,
                    "related_feedback": [],
                    "related_error_id": None,
                    "started_at": None,
                    "completed_at": None,
                }
            assigned_rows.append(row)
        scenario_map[_safe_text(tester_id, "")] = assigned_rows
        tester = self._alpha_tester_record_mutable(
            tenant_id=tenant_id, tester_id=tester_id
        )
        if _safe_text(tester.get("state"), "") in {"invited", "onboarding"}:
            tester["state"] = "onboarding"
        tester["last_activity_at"] = now_iso()
        tester["last_activity_summary"] = "scenarios_assigned"
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_tester.scenarios_assigned",
            details={
                "tester_id": _safe_text(tester_id, ""),
                "scenario_count": len(assigned_rows),
            },
        )
        return [deepcopy(item) for item in assigned_rows]

    def update_alpha_scenario_status(
        self,
        *,
        tenant_id: str,
        tester_id: str,
        scenario_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        status: str,
        tester_notes: str | None = None,
        related_feedback: list[str] | None = None,
        related_error_id: str | None = None,
    ) -> dict[str, Any]:
        self._assert_tester_admin_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        normalized_status = _safe_text(status, "pending").lower()
        if normalized_status not in _ALPHA_SCENARIO_STATUS:
            raise ValueError("scenario status is invalid")
        scenario = self._alpha_tester_scenario_mutable(
            tenant_id=tenant_id,
            tester_id=tester_id,
            scenario_id=scenario_id,
        )
        scenario["status"] = normalized_status
        if normalized_status == "in_progress" and not _safe_text(
            scenario.get("started_at"), ""
        ):
            scenario["started_at"] = now_iso()
        if normalized_status == "completed":
            if not _safe_text(scenario.get("started_at"), ""):
                scenario["started_at"] = now_iso()
            scenario["completed_at"] = now_iso()
        if tester_notes is not None:
            scenario["tester_notes"] = _sanitize_free_text(tester_notes) or None
        if related_feedback is not None:
            scenario["related_feedback"] = [
                _safe_text(item, "")
                for item in list(related_feedback)
                if _safe_text(item, "")
            ]
        if related_error_id is not None:
            scenario["related_error_id"] = _safe_text(related_error_id, "") or None
        tester = self._alpha_tester_record_mutable(
            tenant_id=tenant_id, tester_id=tester_id
        )
        if tester.get("state") in {"invited", "onboarding"} and normalized_status in {
            "in_progress",
            "completed",
        }:
            tester["state"] = "active"
        tester["last_activity_at"] = now_iso()
        tester["last_activity_summary"] = f"scenario_{normalized_status}"
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_tester.scenario_updated",
            details={
                "tester_id": _safe_text(tester_id, ""),
                "scenario_id": _safe_text(scenario_id, ""),
                "status": normalized_status,
            },
        )
        return deepcopy(scenario)

    def list_alpha_tester_scenarios(
        self,
        *,
        tenant_id: str,
        tester_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> list[dict[str, Any]]:
        self._assert_tester_admin_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        _ = self._alpha_tester_record_mutable(tenant_id=tenant_id, tester_id=tester_id)
        rows = list(
            dict(self._tenant_data(tenant_id).get("alpha_tester_scenarios") or {}).get(
                _safe_text(tester_id, "")
            )
            or []
        )
        return [deepcopy(dict(item)) for item in rows if isinstance(item, dict)]

    def update_alpha_tester_status(
        self,
        *,
        tenant_id: str,
        tester_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        status: str,
    ) -> dict[str, Any]:
        self._assert_tester_admin_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        normalized_status = _safe_text(status, "").lower()
        if normalized_status not in _ALPHA_TESTER_STATES:
            raise ValueError("tester status is invalid")
        tester = self._alpha_tester_record_mutable(
            tenant_id=tenant_id, tester_id=tester_id
        )
        tester["state"] = normalized_status
        tester["last_activity_at"] = now_iso()
        tester["last_activity_summary"] = f"status_{normalized_status}"
        if normalized_status == "deactivated":
            tester["deactivated_at"] = now_iso()
            tester["deactivated_by"] = _safe_text(actor_id, "system")
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_tester.status_updated",
            details={
                "tester_id": _safe_text(tester_id, ""),
                "status": normalized_status,
            },
        )
        return deepcopy(tester)

    def deactivate_alpha_tester(
        self,
        *,
        tenant_id: str,
        tester_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> dict[str, Any]:
        return self.update_alpha_tester_status(
            tenant_id=tenant_id,
            tester_id=tester_id,
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            status="deactivated",
        )

    def assert_alpha_tester_access(
        self,
        *,
        tenant_id: str,
        tester_id: str,
    ) -> dict[str, Any]:
        self._assert_operational_access(tenant_id)
        tester = self._alpha_tester_record_mutable(
            tenant_id=tenant_id, tester_id=tester_id
        )
        state = _safe_text(tester.get("state"), "invited").lower()
        if state == "deactivated":
            raise PermissionError("tester access is deactivated")
        if state == "paused":
            raise PermissionError("tester access is paused")
        return deepcopy(tester)

    def request_sandbox_reset(
        self,
        *,
        tenant_id: str,
        tester_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        reason: str,
    ) -> dict[str, Any]:
        self._assert_tester_admin_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        _ = self._alpha_tester_record_mutable(tenant_id=tenant_id, tester_id=tester_id)
        data = self._tenant_data(tenant_id)
        data.setdefault("alpha_reset_requests", [])
        payload = {
            "request_id": f"reset-request:{hashlib.sha1(f'{tenant_id}:{tester_id}:{now_iso()}'.encode('utf-8')).hexdigest()[:16]}",
            "tenant_id": tenant_id,
            "tester_id": _safe_text(tester_id, ""),
            "requested_by": _safe_text(actor_id, "system"),
            "requested_at": now_iso(),
            "reason": _sanitize_free_text(reason) or "requested",
            "status": "requested",
        }
        data["alpha_reset_requests"].append(payload)
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_tester.reset_requested",
            details={
                "tester_id": _safe_text(tester_id, ""),
                "request_id": payload["request_id"],
            },
        )
        return deepcopy(payload)

    def request_tenant_export(
        self,
        *,
        tenant_id: str,
        tester_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        reason: str,
    ) -> dict[str, Any]:
        self._assert_tester_admin_access(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
            tenant_id=tenant_id,
        )
        _ = self._alpha_tester_record_mutable(tenant_id=tenant_id, tester_id=tester_id)
        data = self._tenant_data(tenant_id)
        data.setdefault("alpha_export_requests", [])
        payload = {
            "request_id": f"export-request:{hashlib.sha1(f'{tenant_id}:{tester_id}:{now_iso()}'.encode('utf-8')).hexdigest()[:16]}",
            "tenant_id": tenant_id,
            "tester_id": _safe_text(tester_id, ""),
            "requested_by": _safe_text(actor_id, "system"),
            "requested_at": now_iso(),
            "reason": _sanitize_free_text(reason) or "requested",
            "status": "requested",
        }
        data["alpha_export_requests"].append(payload)
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_tester.export_requested",
            details={
                "tester_id": _safe_text(tester_id, ""),
                "request_id": payload["request_id"],
            },
        )
        return deepcopy(payload)

    def alpha_operations_dashboard(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        rows: list[dict[str, Any]] = []
        now = datetime.now(UTC)
        expiring_sandboxes = 0
        all_defects: list[dict[str, Any]] = []
        all_feedback: list[dict[str, Any]] = []
        unresolved_errors_total = 0
        completed_scenarios_total = 0
        scenario_total_count = 0
        for tenant_payload in dict(self.state.get("tenants") or {}).values():
            tenant = Tenant.from_dict(dict(tenant_payload))
            if tenant.tenant_id == "local":
                continue
            if not include_archived and tenant.status == TenantStatus.ARCHIVED:
                continue
            data = self._tenant_data(tenant.tenant_id)
            testers = list(dict(data.get("alpha_testers") or {}).values())
            scenarios_by_tester = dict(data.get("alpha_tester_scenarios") or {})
            all_scenarios = [
                dict(row)
                for rows_for_tester in scenarios_by_tester.values()
                for row in list(rows_for_tester or [])
                if isinstance(row, dict)
            ]
            scenario_completed = len(
                [
                    row
                    for row in all_scenarios
                    if _safe_text(row.get("status"), "") == "completed"
                ]
            )
            scenario_total = len(all_scenarios)
            completed_scenarios_total += scenario_completed
            scenario_total_count += len(all_scenarios)
            feedback_rows = list(data.get("alpha_feedback") or [])
            all_feedback.extend(
                [dict(item) for item in feedback_rows if isinstance(item, dict)]
            )
            open_defects = len(
                [
                    item
                    for item in feedback_rows
                    if _safe_text(dict(item).get("status"), "")
                    not in {"resolved", "closed"}
                ]
            )
            unresolved_errors = len(
                [
                    item
                    for item in list(data.get("application_errors") or [])
                    if _safe_text(dict(item).get("status"), "")
                    in {
                        ErrorResolutionStatus.NEW.value,
                        ErrorResolutionStatus.ACKNOWLEDGED.value,
                        ErrorResolutionStatus.INVESTIGATING.value,
                        ErrorResolutionStatus.REOPENED.value,
                    }
                ]
            )
            unresolved_errors_total += int(unresolved_errors)
            defects = [
                dict(item)
                for item in list(data.get("alpha_defects") or [])
                if isinstance(item, dict)
            ]
            all_defects.extend(defects)
            sandbox_expiration = _safe_text(tenant.configuration.expiration_date, "")
            if sandbox_expiration:
                try:
                    expires = datetime.fromisoformat(sandbox_expiration)
                    if expires >= now and (expires - now).days <= 14:
                        expiring_sandboxes += 1
                except ValueError:
                    pass
            rows.append(
                {
                    "tenant_id": tenant.tenant_id,
                    "sandbox_status": tenant.status.value,
                    "active_testers": len(
                        [
                            item
                            for item in testers
                            if _safe_text(dict(item).get("state"), "")
                            in {"active", "onboarding"}
                        ]
                    ),
                    "scenario_completion": (
                        f"{scenario_completed}/{scenario_total}"
                        if scenario_total
                        else "0/0"
                    ),
                    "feedback_count": len(feedback_rows),
                    "open_defects": open_defects,
                    "confirmed_defects": len(
                        [
                            item
                            for item in defects
                            if _safe_text(item.get("defect_status"), "")
                            in {
                                "Confirmed",
                                "In Progress",
                                "Ready for Retest",
                            }
                        ]
                    ),
                    "unresolved_errors": unresolved_errors,
                    "last_activity": _safe_text(tenant.last_activity_at, ""),
                    "sandbox_expiration": sandbox_expiration,
                    "reset_requests": len(list(data.get("alpha_reset_requests") or [])),
                    "export_requests": len(
                        list(data.get("alpha_export_requests") or [])
                    ),
                }
            )
        rows.sort(
            key=lambda item: (
                _safe_text(item.get("last_activity"), ""),
                _safe_text(item.get("tenant_id"), ""),
            )
        )
        release_history = self.alpha_stabilization_release_history(
            actor_id=actor_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
        )
        current_release = release_history[-1] if release_history else {}
        current_release_id = _safe_text(current_release.get("release_id"), "")
        active_cohorts = [
            item
            for item in list(current_release.get("assigned_tester_cohorts") or [])
            if isinstance(item, dict)
        ]
        new_feedback = len(
            [
                item
                for item in all_feedback
                if _safe_text(item.get("status"), "") in {"open", "in_review"}
            ]
        )
        confirmed_defects = len(
            [
                item
                for item in all_defects
                if _safe_text(item.get("defect_status"), "")
                in {"Confirmed", "In Progress", "Ready for Retest"}
            ]
        )
        alpha_blockers = len(
            [
                item
                for item in all_defects
                if bool(item.get("alpha_blocking", False))
                and _safe_text(item.get("defect_status"), "")
                not in {"Verified", "Closed", "Deferred"}
            ]
        )
        ready_for_retest = len(
            [
                item
                for item in all_defects
                if _safe_text(item.get("defect_status"), "") == "Ready for Retest"
            ]
        )
        active_sandboxes = len(
            [
                item
                for item in rows
                if _safe_text(item.get("sandbox_status"), "") == "active"
            ]
        )
        degraded_sandboxes = len(
            [
                item
                for item in rows
                if _safe_text(item.get("sandbox_status"), "")
                in {"suspended", "archived"}
            ]
        )
        return {
            "generated_at": now_iso(),
            "active_testers": sum(
                int(item.get("active_testers") or 0) for item in rows
            ),
            "expiring_sandboxes": int(expiring_sandboxes),
            "current_alpha_version": _safe_text(
                current_release.get("version_identifier"),
                "n/a",
            ),
            "active_tester_cohorts": len(active_cohorts),
            "scenario_completion": (
                (
                    f"{completed_scenarios_total}/{scenario_total_count}"
                    if scenario_total_count
                    else "0/0"
                )
            ),
            "new_feedback": int(new_feedback),
            "confirmed_defects": int(confirmed_defects),
            "alpha_blockers": int(alpha_blockers),
            "ready_for_retest": int(ready_for_retest),
            "unresolved_errors": int(unresolved_errors_total),
            "release_status": _safe_text(
                current_release.get("release_status"), "Draft"
            ),
            "current_release_id": current_release_id or None,
            "sandbox_health": {
                "active": int(active_sandboxes),
                "degraded": int(degraded_sandboxes),
                "total": len(rows),
            },
            "rows": rows,
        }

    def submit_alpha_feedback(
        self,
        *,
        tenant_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        user_id: str,
        workspace: str,
        object_or_transaction: str,
        severity: str,
        reproduction_steps: str,
        expected_result: str,
        actual_result: str,
        attachment_references: list[str] | None = None,
        environment_diagnostics: dict[str, Any] | None = None,
        related_error_id: str | None = None,
        status: str = "open",
        resolution_notes: str | None = None,
    ) -> dict[str, Any]:
        self._assert_tenant_scope_request(
            tenant_id=tenant_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
        )
        self._assert_operational_access(tenant_id)
        normalized_status = _safe_text(status, "open").lower()
        if normalized_status not in {"open", "in_review", "resolved", "closed"}:
            raise ValueError("feedback status is invalid")
        feedback_id = f"feedback:{hashlib.sha1(f'{tenant_id}:{user_id}:{now_iso()}'.encode('utf-8')).hexdigest()[:16]}"
        record = {
            "feedback_id": feedback_id,
            "tenant_id": tenant_id,
            "user_id": _safe_text(user_id, "unknown"),
            "workspace": _safe_text(workspace, "Unknown"),
            "object_or_transaction": _safe_text(object_or_transaction, ""),
            "severity": _safe_text(severity, "medium").lower(),
            "reproduction_steps": _safe_text(reproduction_steps, ""),
            "expected_result": _safe_text(expected_result, ""),
            "actual_result": _safe_text(actual_result, ""),
            "attachment_references": [
                _safe_text(item, "")
                for item in list(attachment_references or [])
                if _safe_text(item, "")
            ],
            "environment_diagnostics": _redact_diagnostic_value(
                "environment_diagnostics", dict(environment_diagnostics or {})
            ),
            "related_error_id": _safe_text(related_error_id, "") or None,
            "status": normalized_status,
            "resolution_notes": _safe_text(resolution_notes, "") or None,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        if record["related_error_id"]:
            _ = self.get_application_error_details(
                requester_tenant_id=requester_tenant_id,
                requester_organization_id=requester_organization_id,
                actor_id=user_id,
                tenant_id=tenant_id,
                error_id=record["related_error_id"],
            )
        data = self._tenant_data(tenant_id)
        data.setdefault("alpha_feedback", [])
        data["alpha_feedback"].append(record)
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=user_id,
            action="tenant.alpha_feedback.submitted",
            details={
                "feedback_id": feedback_id,
                "severity": record["severity"],
                "status": normalized_status,
            },
        )
        return deepcopy(record)

    def list_alpha_feedback(
        self,
        *,
        tenant_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        actor_id: str | None = None,
        statuses: list[str] | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        is_platform_admin = self._is_platform_admin_scope_actor(
            actor_id=_safe_text(actor_id, ""),
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        if not is_platform_admin:
            self._assert_tenant_scope_request(
                tenant_id=tenant_id,
                requester_tenant_id=requester_tenant_id,
                requester_organization_id=requester_organization_id,
            )
            self._assert_operational_access(tenant_id)
        rows = list(self._tenant_data(tenant_id).get("alpha_feedback") or [])
        normalized = {
            _safe_text(item, "").lower() for item in list(statuses or []) if item
        }
        actor_scope = _safe_text(actor_id, "")
        filtered = [
            deepcopy(dict(item))
            for item in rows
            if isinstance(item, dict)
            and (
                not normalized
                or _safe_text(item.get("status"), "").lower() in normalized
            )
            and (
                is_platform_admin
                or not actor_scope
                or _safe_text(item.get("user_id"), "") == actor_scope
            )
        ]
        filtered.sort(
            key=lambda item: (
                _safe_text(item.get("updated_at"), ""),
                _safe_text(item.get("feedback_id"), ""),
            )
        )
        return filtered[-max(1, int(limit)) :]

    def update_alpha_feedback_status(
        self,
        *,
        tenant_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        actor_id: str,
        feedback_id: str,
        status: str,
        resolution_notes: str | None = None,
    ) -> dict[str, Any]:
        self._assert_tenant_scope_request(
            tenant_id=tenant_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
        )
        normalized_status = _safe_text(status, "").lower()
        if normalized_status not in {"open", "in_review", "resolved", "closed"}:
            raise ValueError("feedback status is invalid")
        rows = list(self._tenant_data(tenant_id).get("alpha_feedback") or [])
        target = None
        for item in rows:
            if _safe_text(dict(item).get("feedback_id"), "") == _safe_text(
                feedback_id, ""
            ):
                target = item
                break
        if not isinstance(target, dict):
            raise ValueError("feedback record does not exist")
        target["status"] = normalized_status
        if resolution_notes is not None:
            target["resolution_notes"] = _safe_text(resolution_notes, "") or None
        target["updated_at"] = now_iso()
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_feedback.updated",
            details={
                "feedback_id": _safe_text(feedback_id, ""),
                "status": normalized_status,
            },
        )
        return deepcopy(dict(target))

    def alpha_health_check(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        application_version: str,
        environment_label: str,
        test_suite_baseline_reference: str,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        tenant = self._tenant_required(tenant_id)
        data = self._tenant_data(tenant_id)
        jobs = [
            dict(item)
            for item in list(data.get("jobs") or [])
            if isinstance(item, dict)
        ]
        failed_jobs = [
            item
            for item in jobs
            if _safe_text(item.get("status"), "").lower()
            in {"failed", "error", "cancelled"}
        ]
        search_indexes = dict(data.get("search_indexes") or {})
        search_record_count = sum(
            len(list(records or []))
            for records in search_indexes.values()
            if isinstance(records, list)
        )
        feedback_rows = [
            dict(item)
            for item in list(data.get("alpha_feedback") or [])
            if isinstance(item, dict)
        ]
        high_feedback = [
            item
            for item in feedback_rows
            if _safe_text(item.get("severity"), "").lower() in {"high", "critical"}
            and _safe_text(item.get("status"), "").lower() not in {"resolved", "closed"}
        ]
        export_meta = dict(data.get("export_history") or {})
        application_errors = [
            dict(item)
            for item in list(data.get("application_errors") or [])
            if isinstance(item, dict)
        ]
        unresolved_statuses = {
            ErrorResolutionStatus.NEW.value,
            ErrorResolutionStatus.ACKNOWLEDGED.value,
            ErrorResolutionStatus.INVESTIGATING.value,
            ErrorResolutionStatus.REOPENED.value,
        }
        unresolved_error_count = len(
            [
                item
                for item in application_errors
                if _safe_text(item.get("status"), "").lower() in unresolved_statuses
            ]
        )
        recent_application_errors = sorted(
            application_errors,
            key=lambda item: (
                _safe_text(item.get("last_seen_at"), ""),
                _safe_text(item.get("error_id"), ""),
            ),
        )[-8:]
        error_severity_counts = {
            severity.value: len(
                [
                    item
                    for item in application_errors
                    if _safe_text(item.get("severity"), "").lower() == severity.value
                ]
            )
            for severity in ErrorSeverity
        }
        recent_errors = (
            [
                {
                    "source": "job",
                    "status": _safe_text(item.get("status"), "unknown"),
                    "message": _safe_text(item.get("error"), ""),
                    "updated_at": _safe_text(item.get("updated_at"), ""),
                }
                for item in failed_jobs[-5:]
            ]
            + [
                {
                    "source": "feedback",
                    "feedback_id": _safe_text(item.get("feedback_id"), ""),
                    "severity": _safe_text(item.get("severity"), ""),
                    "workspace": _safe_text(item.get("workspace"), ""),
                    "status": _safe_text(item.get("status"), ""),
                    "updated_at": _safe_text(item.get("updated_at"), ""),
                }
                for item in high_feedback[-5:]
            ]
            + [
                {
                    "source": "application_error",
                    "error_id": _safe_text(item.get("error_id"), ""),
                    "severity": _safe_text(item.get("severity"), ""),
                    "status": _safe_text(item.get("status"), ""),
                    "workspace": _safe_text(
                        dict(item.get("context") or {}).get("workspace"), ""
                    ),
                    "message": _safe_text(item.get("summary"), ""),
                    "updated_at": _safe_text(item.get("last_seen_at"), ""),
                }
                for item in recent_application_errors
            ]
        )
        health_payload = {
            "application_version": _safe_text(application_version, "n/a"),
            "environment_label": _safe_text(environment_label, "Controlled Alpha"),
            "tenant_id": tenant.tenant_id,
            "tenant_status": tenant.status.value,
            "repository_health": {
                "status": (
                    "healthy" if tenant.status == TenantStatus.ACTIVE else "degraded"
                ),
                "projects": len(list(data.get("projects") or [])),
                "knowledge_records": len(list(data.get("knowledge") or [])),
                "transactions": len(
                    list(dict(data.get("transactions") or {}).get("documents") or [])
                ),
            },
            "seed_data_status": {
                "enabled": bool(dict(data.get("catalog") or {}).get("items")),
                "profile": _safe_text(
                    dict(data.get("catalog") or {}).get("seed_profile"), "none"
                ),
                "catalog_item_count": len(
                    list(dict(data.get("catalog") or {}).get("items") or [])
                ),
                "last_seeded_by": _safe_text(
                    dict(
                        dict(data.get("transactions") or {}).get("seed_metadata") or {}
                    ).get("seeded_by"),
                    "",
                ),
                "last_seeded_at": _safe_text(
                    dict(
                        dict(data.get("transactions") or {}).get("seed_metadata") or {}
                    ).get("applied_at"),
                    "",
                ),
            },
            "background_job_health": {
                "total_jobs": len(jobs),
                "failed_jobs": len(failed_jobs),
                "running_jobs": len(
                    [
                        item
                        for item in jobs
                        if _safe_text(item.get("status"), "").lower()
                        in {"queued", "running", "retry_scheduled"}
                    ]
                ),
            },
            "attachment_storage_health": {
                "attachment_count": len(list(data.get("attachments") or [])),
                "status": "healthy",
            },
            "search_index_status": {
                "index_count": len(search_indexes),
                "record_count": int(search_record_count),
            },
            "recent_errors_by_severity": error_severity_counts,
            "unresolved_error_count": int(unresolved_error_count),
            "recent_errors": _redact_diagnostic_value("recent_errors", recent_errors),
            "last_backup_or_export": {
                "last_export_at": _safe_text(export_meta.get("last_export_at"), ""),
                "last_export_by": _safe_text(export_meta.get("last_export_by"), ""),
            },
            "test_suite_baseline_reference": _safe_text(
                test_suite_baseline_reference, "1408 passing"
            ),
        }
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_health_check.viewed",
            details={
                "tenant_status": tenant.status.value,
                "failed_jobs": len(failed_jobs),
                "unresolved_error_count": int(unresolved_error_count),
            },
        )
        return health_payload

    def create_alpha_tester_cohort(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        cohort_name: str,
        member_assignments: list[dict[str, str]],
        notes: str | None = None,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        normalized_name = _safe_text(cohort_name, "")
        if not normalized_name:
            raise ValueError("cohort_name is required")
        members: list[dict[str, str]] = []
        for assignment in list(member_assignments or []):
            tenant_id = _safe_text(dict(assignment).get("tenant_id"), "")
            tester_id = _safe_text(dict(assignment).get("tester_id"), "")
            if not tenant_id or not tester_id:
                continue
            _ = self._alpha_tester_record_mutable(
                tenant_id=tenant_id, tester_id=tester_id
            )
            members.append(
                {
                    "tenant_id": tenant_id,
                    "tester_id": tester_id,
                }
            )
        if not members:
            raise ValueError("cohort must include at least one tester assignment")
        cohort_id = f"cohort:{hashlib.sha1(f'{normalized_name}:{now_iso()}'.encode('utf-8')).hexdigest()[:16]}"
        payload = {
            "cohort_id": cohort_id,
            "cohort_name": normalized_name,
            "member_assignments": members,
            "notes": _safe_text(notes, "") or None,
            "created_at": now_iso(),
            "created_by": _safe_text(actor_id, "system"),
            "updated_at": now_iso(),
            "status": "active",
        }
        self.state.setdefault("alpha_tester_cohorts", {})
        self.state["alpha_tester_cohorts"][cohort_id] = payload
        self.state.setdefault("alpha_stabilization_history", [])
        self.state["alpha_stabilization_history"].append(
            {
                "event_type": "cohort_created",
                "occurred_at": now_iso(),
                "actor_id": _safe_text(actor_id, "system"),
                "cohort_id": cohort_id,
            }
        )
        self._record_audit(
            tenant_id="local",
            actor_id=actor_id,
            action="alpha.cohort.created",
            details={"cohort_id": cohort_id, "member_count": len(members)},
        )
        return deepcopy(payload)

    def list_alpha_tester_cohorts(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> list[dict[str, Any]]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        rows = [
            deepcopy(dict(item))
            for item in dict(self.state.get("alpha_tester_cohorts") or {}).values()
            if isinstance(item, dict)
        ]
        rows.sort(
            key=lambda item: (
                _safe_text(item.get("created_at"), ""),
                _safe_text(item.get("cohort_id"), ""),
            )
        )
        return rows

    def create_alpha_release_record(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        version_identifier: str,
        release_date: str,
        commit_hash: str,
        included_fixes: list[str],
        known_limitations: list[str],
        supported_test_scenarios: list[str],
        assigned_tester_cohort_ids: list[str],
        rollback_reference: str,
        release_status: str = "Draft",
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        normalized_version = _safe_text(version_identifier, "")
        if not normalized_version:
            raise ValueError("version_identifier is required")
        normalized_status = _normalize_choice(
            release_status,
            allowed=_ALPHA_RELEASE_STATUS_CHOICES,
            label="release status",
        )
        cohorts = dict(self.state.get("alpha_tester_cohorts") or {})
        assigned_cohorts = []
        for cohort_id in list(assigned_tester_cohort_ids or []):
            normalized = _safe_text(cohort_id, "")
            payload = cohorts.get(normalized)
            if isinstance(payload, dict):
                assigned_cohorts.append(deepcopy(dict(payload)))
        release_id = f"release:{hashlib.sha1(f'{normalized_version}:{now_iso()}'.encode('utf-8')).hexdigest()[:16]}"
        payload = {
            "release_id": release_id,
            "version_identifier": normalized_version,
            "release_date": _safe_text(release_date, now_iso()),
            "commit_hash": _safe_text(commit_hash, "") or "unknown",
            "included_fixes": [
                _sanitize_free_text(item, max_length=280)
                for item in list(included_fixes or [])
                if _safe_text(item, "")
            ],
            "known_limitations": [
                _sanitize_free_text(item, max_length=280)
                for item in list(known_limitations or [])
                if _safe_text(item, "")
            ],
            "supported_test_scenarios": [
                _safe_text(item, "")
                for item in list(supported_test_scenarios or [])
                if _safe_text(item, "")
            ],
            "assigned_tester_cohorts": assigned_cohorts,
            "rollback_reference": _safe_text(rollback_reference, "") or None,
            "release_status": normalized_status,
            "created_at": now_iso(),
            "created_by": _safe_text(actor_id, "system"),
            "updated_at": now_iso(),
            "status_history": [
                {
                    "status": normalized_status,
                    "occurred_at": now_iso(),
                    "actor_id": _safe_text(actor_id, "system"),
                    "notes": "release_created",
                }
            ],
        }
        self.state.setdefault("alpha_release_records", [])
        self.state["alpha_release_records"].append(payload)
        self.state.setdefault("alpha_stabilization_history", [])
        self.state["alpha_stabilization_history"].append(
            {
                "event_type": "release_created",
                "occurred_at": now_iso(),
                "actor_id": _safe_text(actor_id, "system"),
                "release_id": release_id,
                "release_status": normalized_status,
            }
        )
        self._record_audit(
            tenant_id="local",
            actor_id=actor_id,
            action="alpha.release.created",
            details={"release_id": release_id, "release_status": normalized_status},
        )
        return deepcopy(payload)

    def list_alpha_release_records(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> list[dict[str, Any]]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        rows = [
            deepcopy(dict(item))
            for item in list(self.state.get("alpha_release_records") or [])
            if isinstance(item, dict)
        ]
        rows.sort(
            key=lambda item: (
                _safe_text(item.get("release_date"), ""),
                _safe_text(item.get("version_identifier"), ""),
                _safe_text(item.get("release_id"), ""),
            )
        )
        return rows

    def update_alpha_release_status(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        release_id: str,
        release_status: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        normalized_release_id = _safe_text(release_id, "")
        normalized_status = _normalize_choice(
            release_status,
            allowed=_ALPHA_RELEASE_STATUS_CHOICES,
            label="release status",
        )
        target: dict[str, Any] | None = None
        for item in list(self.state.get("alpha_release_records") or []):
            if _safe_text(dict(item).get("release_id"), "") == normalized_release_id:
                if isinstance(item, dict):
                    target = item
                break
        if target is None:
            raise ValueError("alpha release record does not exist")
        target["release_status"] = normalized_status
        target["updated_at"] = now_iso()
        history = list(target.get("status_history") or [])
        history.append(
            {
                "status": normalized_status,
                "occurred_at": now_iso(),
                "actor_id": _safe_text(actor_id, "system"),
                "notes": _sanitize_free_text(notes or "status_updated", max_length=240),
            }
        )
        target["status_history"] = history
        self.state.setdefault("alpha_stabilization_history", [])
        self.state["alpha_stabilization_history"].append(
            {
                "event_type": "release_status_updated",
                "occurred_at": now_iso(),
                "actor_id": _safe_text(actor_id, "system"),
                "release_id": normalized_release_id,
                "release_status": normalized_status,
            }
        )
        self._record_audit(
            tenant_id="local",
            actor_id=actor_id,
            action="alpha.release.status_updated",
            details={
                "release_id": normalized_release_id,
                "release_status": normalized_status,
            },
        )
        return deepcopy(target)

    def assign_alpha_release_cohorts(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        release_id: str,
        cohort_ids: list[str],
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        normalized_release_id = _safe_text(release_id, "")
        target: dict[str, Any] | None = None
        for item in list(self.state.get("alpha_release_records") or []):
            if _safe_text(dict(item).get("release_id"), "") == normalized_release_id:
                if isinstance(item, dict):
                    target = item
                break
        if target is None:
            raise ValueError("alpha release record does not exist")
        cohorts = dict(self.state.get("alpha_tester_cohorts") or {})
        assigned = []
        for cohort_id in list(cohort_ids or []):
            payload = cohorts.get(_safe_text(cohort_id, ""))
            if isinstance(payload, dict):
                assigned.append(deepcopy(dict(payload)))
        if not assigned:
            raise ValueError("at least one valid tester cohort is required")
        target["assigned_tester_cohorts"] = assigned
        target["updated_at"] = now_iso()
        self._record_audit(
            tenant_id="local",
            actor_id=actor_id,
            action="alpha.release.cohorts_assigned",
            details={
                "release_id": normalized_release_id,
                "cohort_count": len(assigned),
            },
        )
        return deepcopy(target)

    def create_alpha_defect_from_feedback(
        self,
        *,
        tenant_id: str,
        feedback_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        application_version: str,
        tester_id: str | None = None,
        severity: str = "Medium",
        alpha_blocking: bool = False,
        defect_status: str = "Confirmed",
        assigned_sprint_or_release: str | None = None,
        resolution_priority: str = "P2",
        regression_test_required: bool = True,
        release_note_linkage: str | None = None,
        reproduction_status: str = "Reproduced",
        resolution_notes: str | None = None,
        verification_evidence: str | None = None,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        self._assert_operational_access(tenant_id)
        feedback_rows = list(self._tenant_data(tenant_id).get("alpha_feedback") or [])
        feedback = None
        normalized_feedback_id = _safe_text(feedback_id, "")
        for item in feedback_rows:
            if _safe_text(dict(item).get("feedback_id"), "") == normalized_feedback_id:
                if isinstance(item, dict):
                    feedback = item
                break
        if not isinstance(feedback, dict):
            raise ValueError("feedback record does not exist")
        normalized_severity = _normalize_choice(
            severity,
            allowed=_ALPHA_DEFECT_SEVERITY_CHOICES,
            label="defect severity",
        )
        normalized_status = _normalize_choice(
            defect_status,
            allowed=_ALPHA_DEFECT_STATUS_CHOICES,
            label="defect status",
        )
        normalized_priority = _normalize_choice(
            resolution_priority,
            allowed=_ALPHA_RESOLUTION_PRIORITY_CHOICES,
            label="resolution priority",
        )
        normalized_reproduction = _normalize_choice(
            reproduction_status,
            allowed=_ALPHA_REPRODUCTION_STATUS_CHOICES,
            label="reproduction status",
        )
        effective_tester = _safe_text(tester_id, "") or _safe_text(
            feedback.get("user_id"),
            "unknown",
        )
        effective_blocking = bool(alpha_blocking)
        if normalized_severity == "Enhancement":
            effective_blocking = False
            normalized_status = "Deferred"
        defect_id = f"defect:{hashlib.sha1(f'{tenant_id}:{normalized_feedback_id}:{now_iso()}'.encode('utf-8')).hexdigest()[:16]}"
        record = {
            "defect_id": defect_id,
            "tenant_id": tenant_id,
            "feedback_id": normalized_feedback_id,
            "feedback_user_id": _safe_text(feedback.get("user_id"), "unknown"),
            "tester_id": effective_tester,
            "application_version": _safe_text(application_version, "unknown"),
            "workspace": _safe_text(feedback.get("workspace"), "Unknown"),
            "related_object": _safe_text(feedback.get("object_or_transaction"), ""),
            "related_error_id": _safe_text(feedback.get("related_error_id"), "")
            or None,
            "reproduction_steps": _safe_text(feedback.get("reproduction_steps"), ""),
            "expected_result": _safe_text(feedback.get("expected_result"), ""),
            "actual_result": _safe_text(feedback.get("actual_result"), ""),
            "defect_severity": normalized_severity,
            "alpha_blocking": effective_blocking,
            "defect_status": normalized_status,
            "reproduction_status": normalized_reproduction,
            "resolution_priority": normalized_priority,
            "assigned_sprint_or_release": _safe_text(assigned_sprint_or_release, "")
            or None,
            "regression_test_required": bool(regression_test_required),
            "regression_test_references": [],
            "release_note_linkage": _safe_text(release_note_linkage, "") or None,
            "retest_status": "Not Started",
            "resolution_notes": _safe_text(resolution_notes, "") or None,
            "verification_evidence": _safe_text(verification_evidence, "") or None,
            "created_at": now_iso(),
            "created_by": _safe_text(actor_id, "system"),
            "updated_at": now_iso(),
            "closed_at": None,
            "status_history": [
                {
                    "status": normalized_status,
                    "occurred_at": now_iso(),
                    "actor_id": _safe_text(actor_id, "system"),
                    "notes": "converted_from_feedback",
                }
            ],
        }
        data = self._tenant_data(tenant_id)
        data.setdefault("alpha_defects", [])
        data["alpha_defects"].append(record)
        feedback["status"] = "in_review"
        feedback["updated_at"] = now_iso()
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_defect.created",
            details={
                "defect_id": defect_id,
                "feedback_id": normalized_feedback_id,
                "severity": normalized_severity,
                "status": normalized_status,
            },
        )
        return deepcopy(record)

    def update_alpha_defect(
        self,
        *,
        tenant_id: str,
        defect_id: str,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        defect_status: str | None = None,
        defect_severity: str | None = None,
        alpha_blocking: bool | None = None,
        assigned_sprint_or_release: str | None = None,
        resolution_priority: str | None = None,
        release_note_linkage: str | None = None,
        regression_test_references: list[str] | None = None,
        reproduction_status: str | None = None,
        retest_status: str | None = None,
        resolution_notes: str | None = None,
        verification_evidence: str | None = None,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        self._assert_operational_access(tenant_id)
        rows = list(self._tenant_data(tenant_id).get("alpha_defects") or [])
        normalized_defect_id = _safe_text(defect_id, "")
        defect = None
        for item in rows:
            if _safe_text(dict(item).get("defect_id"), "") == normalized_defect_id:
                if isinstance(item, dict):
                    defect = item
                break
        if not isinstance(defect, dict):
            raise ValueError("alpha defect does not exist")
        changes: dict[str, Any] = {}
        if defect_status is not None:
            normalized = _normalize_choice(
                defect_status,
                allowed=_ALPHA_DEFECT_STATUS_CHOICES,
                label="defect status",
            )
            if _safe_text(defect.get("defect_status"), "") != normalized:
                defect["defect_status"] = normalized
                changes["defect_status"] = normalized
                status_history = list(defect.get("status_history") or [])
                status_history.append(
                    {
                        "status": normalized,
                        "occurred_at": now_iso(),
                        "actor_id": _safe_text(actor_id, "system"),
                        "notes": "status_updated",
                    }
                )
                defect["status_history"] = status_history
                if normalized in {"Verified", "Closed", "Deferred"}:
                    defect["closed_at"] = now_iso()
                if normalized == "Ready for Retest":
                    defect["retest_status"] = "Ready for Retest"
                if normalized == "Verified" and not _safe_text(
                    defect.get("retest_status"), ""
                ):
                    defect["retest_status"] = "Passed"
        if defect_severity is not None:
            normalized = _normalize_choice(
                defect_severity,
                allowed=_ALPHA_DEFECT_SEVERITY_CHOICES,
                label="defect severity",
            )
            if _safe_text(defect.get("defect_severity"), "") != normalized:
                defect["defect_severity"] = normalized
                changes["defect_severity"] = normalized
                if normalized == "Enhancement":
                    defect["alpha_blocking"] = False
        if alpha_blocking is not None:
            if _safe_text(defect.get("defect_severity"), "") == "Enhancement":
                defect["alpha_blocking"] = False
            else:
                defect["alpha_blocking"] = bool(alpha_blocking)
            changes["alpha_blocking"] = bool(defect.get("alpha_blocking", False))
        if assigned_sprint_or_release is not None:
            defect["assigned_sprint_or_release"] = (
                _safe_text(assigned_sprint_or_release, "") or None
            )
            changes["assigned_sprint_or_release"] = defect["assigned_sprint_or_release"]
        if resolution_priority is not None:
            normalized = _normalize_choice(
                resolution_priority,
                allowed=_ALPHA_RESOLUTION_PRIORITY_CHOICES,
                label="resolution priority",
            )
            defect["resolution_priority"] = normalized
            changes["resolution_priority"] = normalized
        if release_note_linkage is not None:
            defect["release_note_linkage"] = (
                _safe_text(release_note_linkage, "") or None
            )
            changes["release_note_linkage"] = defect["release_note_linkage"]
        if regression_test_references is not None:
            defect["regression_test_references"] = [
                _safe_text(item, "")
                for item in list(regression_test_references)
                if _safe_text(item, "")
            ]
            changes["regression_test_references"] = len(
                list(defect.get("regression_test_references") or [])
            )
        if reproduction_status is not None:
            normalized = _normalize_choice(
                reproduction_status,
                allowed=_ALPHA_REPRODUCTION_STATUS_CHOICES,
                label="reproduction status",
            )
            defect["reproduction_status"] = normalized
            changes["reproduction_status"] = normalized
        if retest_status is not None:
            normalized = _normalize_choice(
                retest_status,
                allowed=_ALPHA_RETEST_STATUS_CHOICES,
                label="retest status",
            )
            defect["retest_status"] = normalized
            changes["retest_status"] = normalized
        if resolution_notes is not None:
            defect["resolution_notes"] = _safe_text(resolution_notes, "") or None
            changes["resolution_notes"] = bool(defect["resolution_notes"])
        if verification_evidence is not None:
            defect["verification_evidence"] = (
                _safe_text(verification_evidence, "") or None
            )
            changes["verification_evidence"] = bool(defect["verification_evidence"])
        defect["updated_at"] = now_iso()
        self._touch_activity(tenant_id)
        self._record_audit(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.alpha_defect.updated",
            details={"defect_id": normalized_defect_id, "changes": changes},
        )
        return deepcopy(defect)

    def list_alpha_defects(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        tenant_id: str | None = None,
        defect_statuses: list[str] | None = None,
        severities: list[str] | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        is_platform_admin = self._is_platform_admin_scope_actor(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        requested_tenant = _safe_text(tenant_id, "")
        if not is_platform_admin:
            self._assert_tenant_scope_request(
                tenant_id=requested_tenant or requester_tenant_id,
                requester_tenant_id=requester_tenant_id,
                requester_organization_id=requester_organization_id,
            )
            self._assert_operational_access(requested_tenant or requester_tenant_id)
        tenant_ids = (
            [requested_tenant]
            if requested_tenant
            else sorted(dict(self.state.get("tenants") or {}).keys())
        )
        if not is_platform_admin:
            tenant_ids = [_safe_text(requester_tenant_id, "")]
        allowed_status = {
            _normalize_choice(
                item, allowed=_ALPHA_DEFECT_STATUS_CHOICES, label="defect status"
            )
            for item in list(defect_statuses or [])
            if _safe_text(item, "")
        }
        allowed_severity = {
            _normalize_choice(
                item, allowed=_ALPHA_DEFECT_SEVERITY_CHOICES, label="defect severity"
            )
            for item in list(severities or [])
            if _safe_text(item, "")
        }
        rows: list[dict[str, Any]] = []
        for current_tenant in tenant_ids:
            if not current_tenant or current_tenant == "local":
                continue
            defects = list(self._tenant_data(current_tenant).get("alpha_defects") or [])
            for item in defects:
                if not isinstance(item, dict):
                    continue
                payload = dict(item)
                if (
                    allowed_status
                    and _safe_text(payload.get("defect_status"), "")
                    not in allowed_status
                ):
                    continue
                if (
                    allowed_severity
                    and _safe_text(payload.get("defect_severity"), "")
                    not in allowed_severity
                ):
                    continue
                if not is_platform_admin and _safe_text(
                    payload.get("feedback_user_id"), ""
                ) != _safe_text(actor_id, ""):
                    continue
                rows.append(payload)
        rows.sort(
            key=lambda item: (
                _safe_text(item.get("updated_at"), ""),
                _safe_text(item.get("defect_id"), ""),
            )
        )
        return [deepcopy(item) for item in rows[-max(1, int(limit)) :]]

    def alpha_feedback_triage_queue(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> dict[str, Any]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        feedback_queue: list[dict[str, Any]] = []
        defect_queue: list[dict[str, Any]] = []
        for tenant_payload in dict(self.state.get("tenants") or {}).values():
            tenant = Tenant.from_dict(dict(tenant_payload))
            if tenant.tenant_id == "local":
                continue
            data = self._tenant_data(tenant.tenant_id)
            feedback_queue.extend(
                [
                    {"tenant_id": tenant.tenant_id, **dict(item)}
                    for item in list(data.get("alpha_feedback") or [])
                    if isinstance(item, dict)
                    and _safe_text(item.get("status"), "") in {"open", "in_review"}
                ]
            )
            defect_queue.extend(
                [
                    {"tenant_id": tenant.tenant_id, **dict(item)}
                    for item in list(data.get("alpha_defects") or [])
                    if isinstance(item, dict)
                    and _safe_text(item.get("defect_status"), "")
                    not in {"Verified", "Closed", "Deferred"}
                ]
            )
        feedback_queue.sort(
            key=lambda item: (
                _safe_text(item.get("updated_at"), ""),
                _safe_text(item.get("feedback_id"), ""),
            )
        )
        defect_queue.sort(
            key=lambda item: (
                _safe_text(item.get("updated_at"), ""),
                _safe_text(item.get("defect_id"), ""),
            )
        )
        return {
            "generated_at": now_iso(),
            "feedback_queue": [deepcopy(item) for item in feedback_queue],
            "defect_queue": [deepcopy(item) for item in defect_queue],
        }

    def alpha_stabilization_release_history(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> list[dict[str, Any]]:
        self._assert_platform_admin(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        )
        rows = [
            deepcopy(dict(item))
            for item in list(self.state.get("alpha_release_records") or [])
            if isinstance(item, dict)
        ]
        rows.sort(
            key=lambda item: (
                _safe_text(item.get("release_date"), ""),
                _safe_text(item.get("version_identifier"), ""),
                _safe_text(item.get("release_id"), ""),
            )
        )
        return rows

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
        normalized_tenant = _safe_text(tenant_id, "")
        normalized_organization = _safe_text(organization_id, "")
        if normalized_tenant != "local" or normalized_organization != "atlas":
            raise PermissionError(
                "platform tenant management is only available in the platform administration scope"
            )
        decision = self.permissions_service.evaluate(
            AccessRequest(
                tenant_id=normalized_tenant,
                organization_id=normalized_organization,
                principal_id=_safe_text(actor_id, "local-user"),
                permission_key="platform.tenants.manage",
                project_id=None,
            )
        )
        if not decision.allowed:
            raise PermissionError(
                decision.reason or "platform tenant management is not allowed"
            )

    def _is_platform_admin_scope_actor(
        self,
        *,
        actor_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> bool:
        try:
            self._assert_platform_admin(
                actor_id=actor_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
            return True
        except PermissionError:
            return False

    def _assert_error_log_access(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        tenant_id: str,
    ) -> None:
        if self._is_platform_admin_scope_actor(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        ):
            return
        self._assert_tenant_scope_request(
            tenant_id=tenant_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
        )
        self._assert_operational_access(tenant_id)

    def _assert_tester_admin_access(
        self,
        *,
        actor_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
        tenant_id: str,
    ) -> None:
        if self._is_platform_admin_scope_actor(
            actor_id=actor_id,
            tenant_id=requester_tenant_id,
            organization_id=requester_organization_id,
        ):
            self._assert_operational_access(tenant_id)
            return
        self._assert_tenant_scope_request(
            tenant_id=tenant_id,
            requester_tenant_id=requester_tenant_id,
            requester_organization_id=requester_organization_id,
        )
        self._assert_operational_access(tenant_id)

    def _alpha_tester_record_mutable(
        self,
        *,
        tenant_id: str,
        tester_id: str,
    ) -> dict[str, Any]:
        data = self._tenant_data(tenant_id)
        testers = data.setdefault("alpha_testers", {})
        normalized_tester_id = _safe_text(tester_id, "")
        payload = testers.get(normalized_tester_id)
        if not isinstance(payload, dict):
            raise ValueError("alpha tester does not exist")
        return payload

    def _alpha_tester_scenario_mutable(
        self,
        *,
        tenant_id: str,
        tester_id: str,
        scenario_id: str,
    ) -> dict[str, Any]:
        data = self._tenant_data(tenant_id)
        scenario_map = data.setdefault("alpha_tester_scenarios", {})
        rows = list(scenario_map.get(_safe_text(tester_id, "")) or [])
        for item in rows:
            if _safe_text(dict(item).get("scenario_id"), "") == _safe_text(
                scenario_id, ""
            ):
                if isinstance(item, dict):
                    return item
        raise ValueError("alpha scenario does not exist")

    def _alpha_tester_summary(
        self, *, tenant_id: str, tester_id: str
    ) -> dict[str, Any]:
        data = self._tenant_data(tenant_id)
        feedback_rows = [
            dict(item)
            for item in list(data.get("alpha_feedback") or [])
            if isinstance(item, dict)
            and _safe_text(item.get("user_id"), "") == _safe_text(tester_id, "")
        ]
        open_feedback = len(
            [
                item
                for item in feedback_rows
                if _safe_text(item.get("status"), "") not in {"resolved", "closed"}
            ]
        )
        linked_error_ids = {
            _safe_text(item.get("related_error_id"), "")
            for item in feedback_rows
            if _safe_text(item.get("related_error_id"), "")
        }
        unresolved_errors = len(
            [
                item
                for item in list(data.get("application_errors") or [])
                if isinstance(item, dict)
                and _safe_text(item.get("error_id"), "") in linked_error_ids
                and _safe_text(item.get("status"), "")
                in {
                    ErrorResolutionStatus.NEW.value,
                    ErrorResolutionStatus.ACKNOWLEDGED.value,
                    ErrorResolutionStatus.INVESTIGATING.value,
                    ErrorResolutionStatus.REOPENED.value,
                }
            ]
        )
        scenario_rows = list(
            dict(data.get("alpha_tester_scenarios") or {}).get(
                _safe_text(tester_id, "")
            )
            or []
        )
        completed = len(
            [
                item
                for item in scenario_rows
                if _safe_text(dict(item).get("status"), "") == "completed"
            ]
        )
        return {
            "feedback_summary": {
                "total_feedback": len(feedback_rows),
                "open_feedback": int(open_feedback),
            },
            "open_defect_summary": {
                "open_defects": int(open_feedback),
                "unresolved_errors": int(unresolved_errors),
            },
            "scenario_summary": {
                "total": len(scenario_rows),
                "completed": int(completed),
            },
        }

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
            "alpha_testers": {},
            "alpha_tester_scenarios": {},
            "alpha_reset_requests": [],
            "alpha_export_requests": [],
            "alpha_feedback": [],
            "alpha_defects": [],
            "application_errors": [],
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

    def _assert_tenant_scope_request(
        self,
        *,
        tenant_id: str,
        requester_tenant_id: str,
        requester_organization_id: str,
    ) -> None:
        normalized_tenant = _safe_text(tenant_id, "")
        if normalized_tenant != _safe_text(requester_tenant_id, ""):
            raise PermissionError("cross-tenant diagnostics are not allowed")
        expected_organization = self._organization_id_for_tenant(normalized_tenant)
        if expected_organization != _safe_text(requester_organization_id, ""):
            raise PermissionError("request organization scope is invalid")

    def _assert_operational_access(self, tenant_id: str) -> None:
        tenant = self._tenant_required(tenant_id)
        if tenant.status != TenantStatus.ACTIVE:
            raise PermissionError("tenant operational access requires active status")

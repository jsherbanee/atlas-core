"""Deterministic tenant-scoped roles and permissions evaluation service."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any
from uuid import uuid4

from atlas_core.contracts.audit_contracts import (
    AuditActor,
    AuditRetentionClass,
    AuditTarget,
    ImmutableAuditEvent,
    now_iso as audit_now_iso,
)
from atlas_core.contracts.permissions_contracts import (
    AccessDecision,
    AccessDiagnostic,
    AccessRequest,
    AccessSurface,
    Permission,
    PermissionChangeEvent,
    PermissionEffect,
    ProjectAccessOverride,
    Role,
    RoleAssignment,
    TenantPolicy,
    now_iso,
)


def _scope_key(tenant_id: str, organization_id: str) -> str:
    return f"{tenant_id.strip()}::{organization_id.strip()}"


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    return normalized or default


PERMISSION_CATALOG: tuple[Permission, ...] = (
    Permission("projects.view", "Projects", "View projects", "View project records."),
    Permission("projects.edit", "Projects", "Edit projects", "Modify project records."),
    Permission(
        "projects.archive",
        "Projects",
        "Archive projects",
        "Archive or restore project records.",
    ),
    Permission(
        "knowledge.view", "Knowledge", "View knowledge", "View knowledge records."
    ),
    Permission(
        "knowledge.edit", "Knowledge", "Edit knowledge", "Modify knowledge records."
    ),
    Permission(
        "transactions.view",
        "Transactions",
        "View transactions",
        "View transaction records.",
    ),
    Permission(
        "transactions.edit",
        "Transactions",
        "Edit transactions",
        "Modify transaction drafts and lines.",
    ),
    Permission(
        "settings.view", "Settings", "View settings", "View tenant configuration."
    ),
    Permission(
        "settings.manage", "Settings", "Manage settings", "Manage tenant configuration."
    ),
    Permission("reports.view", "Reports", "View reports", "View reporting surfaces."),
    Permission(
        "reports.export", "Reports", "Export reports", "Export reports and summaries."
    ),
    Permission(
        "integrations.view",
        "Integrations",
        "View integrations",
        "View integration settings and statuses.",
    ),
    Permission(
        "integrations.manage",
        "Integrations",
        "Manage integrations",
        "Manage integration credentials and configuration.",
    ),
    Permission(
        "users_roles.view",
        "Users and roles",
        "View users and roles",
        "View role assignments and effective access.",
    ),
    Permission(
        "users_roles.manage",
        "Users and roles",
        "Manage users and roles",
        "Assign and revoke roles.",
    ),
    Permission(
        "commercial_documents.view",
        "Commercial documents",
        "View commercial documents",
        "View commercial document records.",
    ),
    Permission(
        "commercial_documents.edit",
        "Commercial documents",
        "Edit commercial documents",
        "Edit commercial document drafts.",
    ),
    Permission(
        "lifecycle_transitions.execute",
        "Lifecycle transitions",
        "Execute lifecycle transitions",
        "Perform lifecycle state transitions.",
    ),
    Permission(
        "export.execute", "Export", "Execute exports", "Export files and datasets."
    ),
    Permission(
        "jobs.view",
        "Background jobs",
        "View background jobs",
        "View background job status and diagnostics.",
    ),
    Permission(
        "jobs.manage",
        "Background jobs",
        "Manage background jobs",
        "Retry and cancel background jobs where safe.",
    ),
    Permission(
        "archive_restore.execute",
        "Archive and restore",
        "Archive and restore",
        "Archive and restore records where allowed.",
    ),
    Permission(
        "platform.tenants.manage",
        "Platform administration",
        "Manage tenant sandboxes",
        "Create, suspend, restore, export, archive, and delete tenant sandboxes.",
    ),
)


SYSTEM_ROLES: tuple[Role, ...] = (
    Role(
        role_key="tenant_administrator",
        display_name="Tenant Administrator",
        system_role=True,
        description="Full tenant administration role.",
        allowed_permissions=[item.permission_key for item in PERMISSION_CATALOG],
    ),
    Role(
        role_key="executive",
        display_name="Executive",
        system_role=True,
        description="Executive read and reporting role.",
        allowed_permissions=[
            "projects.view",
            "knowledge.view",
            "transactions.view",
            "reports.view",
            "reports.export",
            "commercial_documents.view",
            "export.execute",
            "jobs.view",
        ],
    ),
    Role(
        role_key="estimator",
        display_name="Estimator",
        system_role=True,
        description="Estimator workflow role.",
        allowed_permissions=[
            "projects.view",
            "projects.edit",
            "knowledge.view",
            "transactions.view",
            "transactions.edit",
            "commercial_documents.view",
            "commercial_documents.edit",
            "reports.view",
            "export.execute",
            "lifecycle_transitions.execute",
            "jobs.view",
            "jobs.manage",
        ],
    ),
    Role(
        role_key="project_manager",
        display_name="Project Manager",
        system_role=True,
        description="Project delivery role.",
        allowed_permissions=[
            "projects.view",
            "projects.edit",
            "projects.archive",
            "knowledge.view",
            "transactions.view",
            "transactions.edit",
            "commercial_documents.view",
            "lifecycle_transitions.execute",
            "reports.view",
            "archive_restore.execute",
            "jobs.view",
            "jobs.manage",
        ],
    ),
    Role(
        role_key="engineering",
        display_name="Engineering",
        system_role=True,
        description="Engineering execution role.",
        allowed_permissions=[
            "projects.view",
            "projects.edit",
            "knowledge.view",
            "knowledge.edit",
            "transactions.view",
            "commercial_documents.view",
            "lifecycle_transitions.execute",
            "reports.view",
            "export.execute",
        ],
    ),
    Role(
        role_key="purchasing",
        display_name="Purchasing",
        system_role=True,
        description="Purchasing execution role.",
        allowed_permissions=[
            "projects.view",
            "knowledge.view",
            "knowledge.edit",
            "transactions.view",
            "transactions.edit",
            "commercial_documents.view",
            "commercial_documents.edit",
            "reports.view",
            "export.execute",
            "integrations.view",
        ],
    ),
    Role(
        role_key="finance",
        display_name="Finance",
        system_role=True,
        description="Finance and controls role.",
        allowed_permissions=[
            "projects.view",
            "transactions.view",
            "commercial_documents.view",
            "reports.view",
            "reports.export",
            "settings.view",
            "integrations.view",
            "export.execute",
            "jobs.view",
        ],
    ),
    Role(
        role_key="field_operations",
        display_name="Field Operations",
        system_role=True,
        description="Field delivery role.",
        allowed_permissions=[
            "projects.view",
            "projects.edit",
            "knowledge.view",
            "reports.view",
            "lifecycle_transitions.execute",
        ],
    ),
    Role(
        role_key="service",
        display_name="Service",
        system_role=True,
        description="Service lifecycle role.",
        allowed_permissions=[
            "projects.view",
            "projects.edit",
            "knowledge.view",
            "transactions.view",
            "reports.view",
            "lifecycle_transitions.execute",
        ],
    ),
    Role(
        role_key="read_only",
        display_name="Read Only",
        system_role=True,
        description="Read-only role.",
        allowed_permissions=[
            "projects.view",
            "knowledge.view",
            "transactions.view",
            "settings.view",
            "reports.view",
            "commercial_documents.view",
            "jobs.view",
        ],
    ),
)


_ROLE_BY_KEY = {role.role_key: role for role in SYSTEM_ROLES}
_PERMISSION_KEYS = {permission.permission_key for permission in PERMISSION_CATALOG}


@dataclass(frozen=True)
class ActionAccessResult:
    visible: bool
    enabled: bool
    reason: str | None
    permission_key: str
    decision: AccessDecision


class PermissionsService:
    def __init__(self, *, state: dict[str, Any] | None = None) -> None:
        incoming = dict(state or {})
        self.state: dict[str, Any] = {
            "tenant_policies": dict(incoming.get("tenant_policies") or {}),
            "permission_events": [
                dict(item)
                for item in list(incoming.get("permission_events") or [])
                if isinstance(item, dict)
            ],
            "immutable_audit_events": [
                dict(item)
                for item in list(incoming.get("immutable_audit_events") or [])
                if isinstance(item, dict)
            ],
        }

    @staticmethod
    def empty_state() -> dict[str, Any]:
        return {
            "tenant_policies": {},
            "permission_events": [],
            "immutable_audit_events": [],
        }

    def to_dict(self) -> dict[str, Any]:
        policies: dict[str, Any] = {}
        for key in sorted(dict(self.state.get("tenant_policies") or {}).keys()):
            payload = dict(self.state["tenant_policies"][key] or {})
            policy = TenantPolicy.from_dict(payload)
            policies[key] = policy.to_dict()
        events = [
            dict(item)
            for item in list(self.state.get("permission_events") or [])
            if isinstance(item, dict)
        ]
        events.sort(
            key=lambda item: (
                _safe_text(item.get("timestamp"), ""),
                _safe_text(item.get("event_id"), ""),
            )
        )
        return {
            "tenant_policies": policies,
            "permission_events": events,
            "immutable_audit_events": [
                dict(item)
                for item in list(self.state.get("immutable_audit_events") or [])
                if isinstance(item, dict)
            ],
        }

    def list_permissions(self) -> list[Permission]:
        return sorted(
            PERMISSION_CATALOG, key=lambda item: (item.category, item.permission_key)
        )

    def list_system_roles(self) -> list[Role]:
        return list(SYSTEM_ROLES)

    def list_all_roles(self, *, tenant_id: str, organization_id: str) -> list[Role]:
        policy = self.tenant_policy(
            tenant_id=tenant_id, organization_id=organization_id
        )
        merged = {role.role_key: role for role in SYSTEM_ROLES}
        for role in policy.custom_roles:
            merged[role.role_key] = role
        return sorted(merged.values(), key=lambda item: item.display_name.lower())

    def tenant_policy(self, *, tenant_id: str, organization_id: str) -> TenantPolicy:
        key = _scope_key(tenant_id, organization_id)
        payload = dict(self.state.get("tenant_policies", {}).get(key) or {})
        if not payload:
            return TenantPolicy(tenant_id=tenant_id, organization_id=organization_id)
        policy = TenantPolicy.from_dict(payload)
        if policy.tenant_id != tenant_id or policy.organization_id != organization_id:
            raise ValueError("tenant policy scope mismatch")
        return policy

    def _write_policy(self, policy: TenantPolicy) -> None:
        key = _scope_key(policy.tenant_id, policy.organization_id)
        self.state.setdefault("tenant_policies", {})
        self.state["tenant_policies"][key] = policy.to_dict()

    def _emit_event(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
        event_type: str,
        details: dict[str, Any],
    ) -> PermissionChangeEvent:
        event = PermissionChangeEvent(
            event_id=f"pce-{uuid4().hex[:12]}",
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            event_type=event_type,
            timestamp=now_iso(),
            details=deepcopy(details),
        )
        self.state.setdefault("permission_events", [])
        self.state["permission_events"].append(event.to_dict())
        self._append_immutable_audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            event_type=event_type,
            details=details,
        )
        return event

    def _append_immutable_audit(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
        event_type: str,
        details: dict[str, Any],
    ) -> None:
        occurred_at = audit_now_iso()
        material = {
            "tenant_id": tenant_id,
            "organization_id": organization_id,
            "event_type": event_type,
            "timestamp": occurred_at,
            "details": details,
        }
        digest = hashlib.sha1(
            json.dumps(material, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]
        event = ImmutableAuditEvent(
            event_id=f"audit-permissions:{digest}",
            action=f"permissions.{event_type}",
            actor=AuditActor(actor_id=_safe_text(actor, "system"), actor_type="user"),
            target=AuditTarget(
                target_type="permissions_policy",
                target_id=f"{tenant_id}::{organization_id}",
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=None,
            ),
            occurred_at=occurred_at,
            retention_class=AuditRetentionClass.SECURITY,
            source="permissions_service",
            before={},
            after={},
            change_summary={
                "changed_fields": sorted(dict(details).keys()),
                "added_fields": sorted(dict(details).keys()),
                "removed_fields": [],
            },
            context=deepcopy(dict(details)),
        )
        rows = [
            dict(item)
            for item in list(self.state.get("immutable_audit_events") or [])
            if isinstance(item, dict)
        ]
        rows.append(event.to_dict())
        self.state["immutable_audit_events"] = rows[-2000:]

    def immutable_audit_events(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        rows = [
            dict(item)
            for item in list(self.state.get("immutable_audit_events") or [])
            if isinstance(item, dict)
            and _safe_text(dict(item.get("target") or {}).get("tenant_id"), "")
            == tenant_id
            and _safe_text(dict(item.get("target") or {}).get("organization_id"), "")
            == organization_id
        ]
        rows.sort(
            key=lambda item: (
                _safe_text(item.get("occurred_at"), ""),
                _safe_text(item.get("event_id"), ""),
            )
        )
        return rows[-max(1, int(limit)) :]

    def permission_events(
        self, *, tenant_id: str, organization_id: str
    ) -> list[dict[str, Any]]:
        rows = [
            dict(item)
            for item in list(self.state.get("permission_events") or [])
            if _safe_text(item.get("tenant_id"), "") == tenant_id
            and _safe_text(item.get("organization_id"), "") == organization_id
        ]
        rows.sort(
            key=lambda item: (
                _safe_text(item.get("timestamp"), ""),
                _safe_text(item.get("event_id"), ""),
            )
        )
        return rows

    def create_custom_role(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        role_key: str,
        display_name: str,
        allowed_permissions: list[str],
        denied_permissions: list[str],
        description: str | None,
        actor: str,
    ) -> Role:
        key = _safe_text(role_key).lower().replace(" ", "_")
        if key in _ROLE_BY_KEY:
            raise ValueError("system roles are immutable")
        self._validate_permissions(allowed_permissions)
        self._validate_permissions(denied_permissions)
        policy = self.tenant_policy(
            tenant_id=tenant_id, organization_id=organization_id
        )
        existing = {item.role_key for item in policy.custom_roles}
        if key in existing:
            raise ValueError("custom role already exists")
        role = Role(
            role_key=key,
            display_name=display_name,
            system_role=False,
            allowed_permissions=list(allowed_permissions),
            denied_permissions=list(denied_permissions),
            description=description,
        )
        updated = TenantPolicy(
            tenant_id=policy.tenant_id,
            organization_id=policy.organization_id,
            custom_roles=[*policy.custom_roles, role],
            role_assignments=list(policy.role_assignments),
            project_overrides=list(policy.project_overrides),
        )
        self._write_policy(updated)
        self._emit_event(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            event_type="custom_role_created",
            details=role.to_dict(),
        )
        return role

    def assign_role(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        principal_id: str,
        role_key: str,
        actor: str,
        project_id: str | None = None,
    ) -> RoleAssignment:
        role = self._resolve_role(
            role_key=role_key,
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        policy = self.tenant_policy(
            tenant_id=tenant_id, organization_id=organization_id
        )
        assignment = RoleAssignment(
            assignment_id=f"ra-{uuid4().hex[:12]}",
            tenant_id=tenant_id,
            organization_id=organization_id,
            principal_id=principal_id,
            role_key=role.role_key,
            assigned_by=_safe_text(actor, "system"),
            assigned_at=now_iso(),
            project_id=project_id,
        )
        duplicate = next(
            (
                item
                for item in policy.role_assignments
                if (
                    item.tenant_id == assignment.tenant_id
                    and item.organization_id == assignment.organization_id
                    and item.principal_id == assignment.principal_id
                    and item.role_key == assignment.role_key
                    and (item.project_id or "") == (assignment.project_id or "")
                )
            ),
            None,
        )
        if duplicate is not None:
            return duplicate

        updated = TenantPolicy(
            tenant_id=policy.tenant_id,
            organization_id=policy.organization_id,
            custom_roles=list(policy.custom_roles),
            role_assignments=[*policy.role_assignments, assignment],
            project_overrides=list(policy.project_overrides),
        )
        self._write_policy(updated)
        self._emit_event(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            event_type="role_assigned",
            details=assignment.to_dict(),
        )
        return assignment

    def revoke_role(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        assignment_id: str,
        actor: str,
    ) -> bool:
        policy = self.tenant_policy(
            tenant_id=tenant_id, organization_id=organization_id
        )
        keep = [
            item
            for item in policy.role_assignments
            if item.assignment_id != _safe_text(assignment_id, "")
        ]
        if len(keep) == len(policy.role_assignments):
            return False
        updated = TenantPolicy(
            tenant_id=policy.tenant_id,
            organization_id=policy.organization_id,
            custom_roles=list(policy.custom_roles),
            role_assignments=keep,
            project_overrides=list(policy.project_overrides),
        )
        self._write_policy(updated)
        self._emit_event(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            event_type="role_revoked",
            details={"assignment_id": assignment_id},
        )
        return True

    def list_role_assignments(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        principal_id: str | None = None,
    ) -> list[RoleAssignment]:
        policy = self.tenant_policy(
            tenant_id=tenant_id, organization_id=organization_id
        )
        rows = [
            item
            for item in policy.role_assignments
            if principal_id is None or item.principal_id == _safe_text(principal_id, "")
        ]
        rows.sort(
            key=lambda item: (
                item.principal_id,
                item.project_id or "",
                item.role_key,
                item.assignment_id,
            )
        )
        return rows

    def set_project_override(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        permission_key: str,
        effect: PermissionEffect,
        reason: str,
        actor: str,
        principal_id: str | None = None,
        role_key: str | None = None,
    ) -> ProjectAccessOverride:
        self._validate_permissions([permission_key])
        if role_key:
            _ = self._resolve_role(
                role_key=role_key,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
        override = ProjectAccessOverride(
            override_id=f"ovr-{uuid4().hex[:12]}",
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            permission_key=permission_key,
            effect=effect,
            reason=reason,
            principal_id=principal_id,
            role_key=role_key,
        )
        policy = self.tenant_policy(
            tenant_id=tenant_id, organization_id=organization_id
        )
        retained = [
            item
            for item in policy.project_overrides
            if not (
                item.project_id == override.project_id
                and item.permission_key == override.permission_key
                and (item.principal_id or "") == (override.principal_id or "")
                and (item.role_key or "") == (override.role_key or "")
            )
        ]
        updated = TenantPolicy(
            tenant_id=policy.tenant_id,
            organization_id=policy.organization_id,
            custom_roles=list(policy.custom_roles),
            role_assignments=list(policy.role_assignments),
            project_overrides=[*retained, override],
        )
        self._write_policy(updated)
        self._emit_event(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            event_type="project_override_set",
            details=override.to_dict(),
        )
        return override

    def evaluate(self, request: AccessRequest) -> AccessDecision:
        if request.permission_key not in _PERMISSION_KEYS:
            return AccessDecision(
                effect=PermissionEffect.DENY,
                allowed=False,
                reason="Permission key is unknown.",
                permission_key=request.permission_key,
                surface=AccessSurface.VISIBLE_DISABLED,
                diagnostics=[
                    AccessDiagnostic(
                        code="unknown_permission",
                        message="Requested permission key is not recognized.",
                        metadata={"permission_key": request.permission_key},
                    )
                ],
                resolved_roles=[],
            )

        policy = self.tenant_policy(
            tenant_id=request.tenant_id,
            organization_id=request.organization_id,
        )

        assignments = [
            item
            for item in policy.role_assignments
            if (
                item.tenant_id == request.tenant_id
                and item.organization_id == request.organization_id
                and item.principal_id == request.principal_id
                and (item.project_id is None or item.project_id == request.project_id)
            )
        ]

        if not assignments and self._is_local_compatibility_context(request):
            assignments = [
                RoleAssignment(
                    assignment_id="compat-local-admin",
                    tenant_id=request.tenant_id,
                    organization_id=request.organization_id,
                    principal_id=request.principal_id,
                    role_key="tenant_administrator",
                    assigned_by="compatibility",
                    assigned_at=now_iso(),
                    project_id=None,
                )
            ]

        if not assignments:
            return AccessDecision(
                effect=PermissionEffect.DENY,
                allowed=False,
                reason="No role assignment grants this permission.",
                permission_key=request.permission_key,
                surface=AccessSurface.VISIBLE_DISABLED,
                diagnostics=[
                    AccessDiagnostic(
                        code="deny_by_default",
                        message="Access denied by default because no matching assignment exists.",
                        metadata={"principal_id": request.principal_id},
                    )
                ],
                resolved_roles=[],
            )

        roles = [
            self._resolve_role(
                role_key=item.role_key,
                tenant_id=request.tenant_id,
                organization_id=request.organization_id,
            )
            for item in assignments
        ]

        allowed_by_role = {
            role.role_key
            for role in roles
            if request.permission_key in set(role.allowed_permissions)
        }
        denied_by_role = {
            role.role_key
            for role in roles
            if request.permission_key in set(role.denied_permissions)
        }

        override_decisions = self._matching_overrides(
            policy=policy, request=request, roles=roles
        )
        denied_by_override = [
            item for item in override_decisions if item.effect is PermissionEffect.DENY
        ]
        allowed_by_override = [
            item for item in override_decisions if item.effect is PermissionEffect.ALLOW
        ]

        if denied_by_role or denied_by_override:
            return AccessDecision(
                effect=PermissionEffect.DENY,
                allowed=False,
                reason=(
                    denied_by_override[0].reason
                    if denied_by_override
                    else "Denied by explicit role rule."
                ),
                permission_key=request.permission_key,
                surface=AccessSurface.VISIBLE_DISABLED,
                diagnostics=[
                    AccessDiagnostic(
                        code="explicit_deny",
                        message="Explicit deny takes precedence over allow.",
                        metadata={
                            "roles": sorted(denied_by_role),
                            "project_override_count": len(denied_by_override),
                        },
                    )
                ],
                resolved_roles=[role.role_key for role in roles],
            )

        if allowed_by_override or allowed_by_role:
            return AccessDecision(
                effect=PermissionEffect.ALLOW,
                allowed=True,
                reason=(
                    allowed_by_override[0].reason
                    if allowed_by_override
                    else "Allowed by role assignment."
                ),
                permission_key=request.permission_key,
                surface=AccessSurface.VISIBLE_ENABLED,
                diagnostics=[
                    AccessDiagnostic(
                        code="explicit_allow",
                        message="Permission granted by role or project override.",
                        metadata={
                            "roles": sorted(allowed_by_role),
                            "project_override_count": len(allowed_by_override),
                        },
                    )
                ],
                resolved_roles=[role.role_key for role in roles],
            )

        return AccessDecision(
            effect=PermissionEffect.DENY,
            allowed=False,
            reason="No allow rule matched this permission.",
            permission_key=request.permission_key,
            surface=AccessSurface.VISIBLE_DISABLED,
            diagnostics=[
                AccessDiagnostic(
                    code="no_allow_match",
                    message="Assignments exist but none grant this permission.",
                    metadata={"principal_id": request.principal_id},
                )
            ],
            resolved_roles=[role.role_key for role in roles],
        )

    def effective_permissions(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        principal_id: str,
        project_id: str | None = None,
    ) -> dict[str, list[str]]:
        allowed: list[str] = []
        denied: list[str] = []
        for permission in sorted(_PERMISSION_KEYS):
            decision = self.evaluate(
                AccessRequest(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    principal_id=principal_id,
                    permission_key=permission,
                    project_id=project_id,
                )
            )
            if decision.allowed:
                allowed.append(permission)
            else:
                denied.append(permission)
        return {"allowed": allowed, "denied": denied}

    def action_access(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        principal_id: str,
        permission_hook: str | None,
        action_key: str,
        workspace_scope: str,
        project_id: str | None = None,
    ) -> ActionAccessResult:
        permission_key = self.resolve_permission_key(
            permission_hook=permission_hook,
            action_key=action_key,
            workspace_scope=workspace_scope,
        )
        decision = self.evaluate(
            AccessRequest(
                tenant_id=tenant_id,
                organization_id=organization_id,
                principal_id=principal_id,
                permission_key=permission_key,
                project_id=project_id,
            )
        )
        if decision.allowed:
            return ActionAccessResult(
                visible=True,
                enabled=True,
                reason=None,
                permission_key=permission_key,
                decision=decision,
            )

        if permission_key.endswith(".view"):
            surface = AccessSurface.HIDDEN
            visible = False
            enabled = False
        else:
            surface = AccessSurface.VISIBLE_DISABLED
            visible = True
            enabled = False

        denied = AccessDecision(
            effect=decision.effect,
            allowed=False,
            reason=decision.reason,
            permission_key=decision.permission_key,
            surface=surface,
            diagnostics=list(decision.diagnostics),
            resolved_roles=list(decision.resolved_roles),
        )
        return ActionAccessResult(
            visible=visible,
            enabled=enabled,
            reason=decision.reason,
            permission_key=permission_key,
            decision=denied,
        )

    def resolve_permission_key(
        self,
        *,
        permission_hook: str | None,
        action_key: str,
        workspace_scope: str,
    ) -> str:
        hook = _safe_text(permission_hook, "")
        scope = _safe_text(workspace_scope, "projects").lower()
        if not hook:
            return {
                "open": f"{scope}.view",
                "view_activity": f"{scope}.view",
                "view_documents": f"{scope}.view",
                "edit": f"{scope}.edit",
                "archive": "archive_restore.execute",
                "restore": "archive_restore.execute",
                "export": "export.execute",
            }.get(action_key, f"{scope}.view")

        if hook.startswith("object."):
            suffix = hook.split(".", 1)[1]
            if suffix == "view":
                return f"{scope}.view"
            if suffix == "edit":
                return f"{scope}.edit"
            if suffix == "archive_restore":
                return "archive_restore.execute"
            if suffix == "export":
                return "export.execute"
        if hook in _PERMISSION_KEYS:
            return hook
        return f"{scope}.view"

    def _matching_overrides(
        self,
        *,
        policy: TenantPolicy,
        request: AccessRequest,
        roles: list[Role],
    ) -> list[ProjectAccessOverride]:
        if not request.project_id:
            return []
        role_keys = {item.role_key for item in roles}
        matched = [
            item
            for item in policy.project_overrides
            if (
                item.tenant_id == request.tenant_id
                and item.organization_id == request.organization_id
                and item.project_id == request.project_id
                and item.permission_key == request.permission_key
                and (
                    item.principal_id == request.principal_id
                    or (item.role_key is not None and item.role_key in role_keys)
                )
            )
        ]
        matched.sort(
            key=lambda item: (
                item.principal_id is None,
                item.role_key or "",
                item.override_id,
            )
        )
        return matched

    def _resolve_role(
        self,
        *,
        role_key: str,
        tenant_id: str,
        organization_id: str,
    ) -> Role:
        normalized = _safe_text(role_key, "").lower()
        if normalized in _ROLE_BY_KEY:
            return _ROLE_BY_KEY[normalized]
        policy = self.tenant_policy(
            tenant_id=tenant_id, organization_id=organization_id
        )
        for role in policy.custom_roles:
            if role.role_key == normalized:
                return role
        raise ValueError(f"unknown role: {normalized}")

    def _validate_permissions(self, permission_keys: list[str]) -> None:
        invalid = sorted(
            {
                _safe_text(item, "")
                for item in permission_keys
                if _safe_text(item, "") not in _PERMISSION_KEYS
            }
        )
        if invalid:
            raise ValueError(f"unknown permissions: {', '.join(invalid)}")

    def _is_local_compatibility_context(self, request: AccessRequest) -> bool:
        return (
            request.tenant_id == "local"
            and request.organization_id == "atlas"
            and request.principal_id in {"local-user", "", "atlas-local-user"}
        )

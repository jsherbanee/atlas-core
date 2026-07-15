from __future__ import annotations

from atlas_core.contracts.permissions_contracts import AccessRequest, PermissionEffect
from atlas_core.services.permissions_service import PermissionsService


def test_permissions_deny_by_default_without_assignment() -> None:
    service = PermissionsService()

    decision = service.evaluate(
        AccessRequest(
            tenant_id="tenant-a",
            organization_id="org-a",
            principal_id="user-1",
            permission_key="projects.view",
        )
    )

    assert decision.allowed is False
    assert decision.effect is PermissionEffect.DENY
    assert any(item.code == "deny_by_default" for item in decision.diagnostics)


def test_system_role_permissions_tenant_administrator_allows_sensitive_actions() -> (
    None
):
    service = PermissionsService()
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="admin-1",
        role_key="tenant_administrator",
        actor="test",
    )

    decision = service.evaluate(
        AccessRequest(
            tenant_id="tenant-a",
            organization_id="org-a",
            principal_id="admin-1",
            permission_key="users_roles.manage",
        )
    )

    assert decision.allowed is True
    assert decision.effect is PermissionEffect.ALLOW


def test_tenant_mismatch_rejects_cross_tenant_access() -> None:
    service = PermissionsService()
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="user-1",
        role_key="executive",
        actor="test",
    )

    decision = service.evaluate(
        AccessRequest(
            tenant_id="tenant-b",
            organization_id="org-b",
            principal_id="user-1",
            permission_key="projects.view",
        )
    )

    assert decision.allowed is False
    assert decision.effect is PermissionEffect.DENY


def test_multiple_role_resolution_allows_if_any_role_allows_without_deny() -> None:
    service = PermissionsService()
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="user-1",
        role_key="read_only",
        actor="test",
    )
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="user-1",
        role_key="engineering",
        actor="test",
    )

    decision = service.evaluate(
        AccessRequest(
            tenant_id="tenant-a",
            organization_id="org-a",
            principal_id="user-1",
            permission_key="knowledge.edit",
        )
    )

    assert decision.allowed is True
    assert "engineering" in decision.resolved_roles


def test_explicit_deny_project_override_beats_role_allow() -> None:
    service = PermissionsService()
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="pm-1",
        role_key="project_manager",
        actor="test",
    )
    service.set_project_override(
        tenant_id="tenant-a",
        organization_id="org-a",
        project_id="prj-1",
        permission_key="projects.edit",
        effect=PermissionEffect.DENY,
        reason="Project is in external legal hold.",
        actor="test",
        principal_id="pm-1",
    )

    decision = service.evaluate(
        AccessRequest(
            tenant_id="tenant-a",
            organization_id="org-a",
            principal_id="pm-1",
            permission_key="projects.edit",
            project_id="prj-1",
        )
    )

    assert decision.allowed is False
    assert decision.effect is PermissionEffect.DENY
    assert "legal hold" in decision.reason.lower()


def test_project_scoped_assignment_only_applies_to_matching_project() -> None:
    service = PermissionsService()
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="field-1",
        role_key="field_operations",
        actor="test",
        project_id="prj-1",
    )

    decision_matching = service.evaluate(
        AccessRequest(
            tenant_id="tenant-a",
            organization_id="org-a",
            principal_id="field-1",
            permission_key="projects.edit",
            project_id="prj-1",
        )
    )
    decision_non_matching = service.evaluate(
        AccessRequest(
            tenant_id="tenant-a",
            organization_id="org-a",
            principal_id="field-1",
            permission_key="projects.edit",
            project_id="prj-2",
        )
    )

    assert decision_matching.allowed is True
    assert decision_non_matching.allowed is False


def test_local_development_backward_compatibility_allows_local_user_without_assignment() -> (
    None
):
    service = PermissionsService()

    decision = service.evaluate(
        AccessRequest(
            tenant_id="local",
            organization_id="atlas",
            principal_id="local-user",
            permission_key="settings.manage",
        )
    )

    assert decision.allowed is True
    assert decision.effect is PermissionEffect.ALLOW


def test_universal_action_gating_supports_hidden_and_disabled_states() -> None:
    service = PermissionsService()
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="viewer-1",
        role_key="read_only",
        actor="test",
    )

    hidden = service.action_access(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="viewer-1",
        permission_hook="object.view",
        action_key="open",
        workspace_scope="integrations",
        project_id=None,
    )
    disabled = service.action_access(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="viewer-1",
        permission_hook="object.edit",
        action_key="edit",
        workspace_scope="projects",
        project_id=None,
    )

    assert hidden.visible is False
    assert hidden.enabled is False
    assert disabled.visible is True
    assert disabled.enabled is False
    assert isinstance(disabled.reason, str) and disabled.reason


def test_settings_access_for_read_only_allows_view_denies_manage() -> None:
    service = PermissionsService()
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="reader-1",
        role_key="read_only",
        actor="test",
    )

    can_view = service.evaluate(
        AccessRequest(
            tenant_id="tenant-a",
            organization_id="org-a",
            principal_id="reader-1",
            permission_key="settings.view",
        )
    )
    can_manage = service.evaluate(
        AccessRequest(
            tenant_id="tenant-a",
            organization_id="org-a",
            principal_id="reader-1",
            permission_key="users_roles.manage",
        )
    )

    assert can_view.allowed is True
    assert can_manage.allowed is False


def test_serialization_is_deterministic_and_sorted() -> None:
    service = PermissionsService()
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="user-b",
        role_key="executive",
        actor="test",
    )
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="user-a",
        role_key="read_only",
        actor="test",
    )
    service.set_project_override(
        tenant_id="tenant-a",
        organization_id="org-a",
        project_id="prj-2",
        permission_key="projects.view",
        effect=PermissionEffect.ALLOW,
        reason="Pilot visibility.",
        actor="test",
        principal_id="user-a",
    )

    payload = service.to_dict()
    policy = payload["tenant_policies"]["tenant-a::org-a"]
    principal_order = [item["principal_id"] for item in policy["role_assignments"]]

    assert principal_order == sorted(principal_order)
    assert payload["permission_events"]
    event_types = {item["event_type"] for item in payload["permission_events"]}
    assert "role_assigned" in event_types
    assert "project_override_set" in event_types

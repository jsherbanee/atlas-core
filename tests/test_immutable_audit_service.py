from __future__ import annotations

from pathlib import Path

from atlas_core.domain.commercial_document import CommercialDocumentType
from atlas_core.services.permissions_service import PermissionsService
from atlas_core.services.project_workspace_service import ProjectWorkspaceService
from atlas_core.services.settings_service import SettingsService


def _create_workspace(service: ProjectWorkspaceService, project_id: str) -> None:
    record = service.create_manual_record(
        project_id=project_id,
        name="Audit Workspace",
        client="Atlas",
    )
    record.metadata["tenant_id"] = "tenant-a"
    record.metadata["organization_id"] = "org-a"
    service.save_record(record)


def test_immutable_audit_persists_in_history_and_redacts_sensitive_payload(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    _create_workspace(service, "project-audit-1")

    service.manager.record_audit_event(
        project_id="project-audit-1",
        action="settings.updated",
        actor_id="user-1",
        tenant_id="tenant-a",
        organization_id="org-a",
        target_type="settings",
        target_id="tenant-a::org-a",
        before={"timezone": "UTC"},
        after={"timezone": "America/Los_Angeles"},
        context={"api_key": "secret-value", "note": "safe"},
    )

    events = service.list_audit_history("project-audit-1")

    assert events
    latest = events[-1]
    assert latest["action"] == "settings.updated"
    assert latest["context"]["api_key"] == "[REDACTED]"
    assert latest["change_summary"]["changed_fields"] == ["timezone"]


def test_immutable_audit_event_chain_and_tenant_filtering(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    _create_workspace(service, "project-audit-2")

    first = service.manager.record_audit_event(
        project_id="project-audit-2",
        action="project.created",
        actor_id="user-1",
        tenant_id="tenant-a",
        organization_id="org-a",
        target_type="project",
        target_id="project-audit-2",
        after={"project_name": "A"},
    )
    second = service.manager.record_audit_event(
        project_id="project-audit-2",
        action="project.identity.updated",
        actor_id="user-2",
        tenant_id="tenant-a",
        organization_id="org-a",
        target_type="project",
        target_id="project-audit-2",
        before={"project_name": "A"},
        after={"project_name": "B"},
    )

    events = service.manager.list_audit_events(
        project_id="project-audit-2",
        tenant_id="tenant-a",
        organization_id="org-a",
    )
    wrong_tenant = service.manager.list_audit_events(
        project_id="project-audit-2",
        tenant_id="tenant-b",
        organization_id="org-a",
    )

    assert len(events) >= 2
    assert second["previous_event_id"] == first["event_id"]
    assert wrong_tenant == []


def test_immutable_audit_export_is_deterministic_for_same_events(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    _create_workspace(service, "project-audit-3")

    service.manager.record_audit_event(
        project_id="project-audit-3",
        action="project.archived",
        actor_id="user-1",
        tenant_id="tenant-a",
        organization_id="org-a",
        target_type="project",
        target_id="project-audit-3",
        after={"archived": True},
    )

    export_one = service.export_audit_history("project-audit-3")
    export_two = service.export_audit_history("project-audit-3")

    assert export_one["export_id"] == export_two["export_id"]
    assert export_one["events"] == export_two["events"]


def test_legacy_history_events_are_adapted_to_audit_shape(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    _create_workspace(service, "project-audit-4")

    service.log_event(
        "project-audit-4",
        "project_renamed",
        {"new_name": "Renamed", "tenant_id": "tenant-a", "organization_id": "org-a"},
    )

    events = service.list_audit_history("project-audit-4")

    assert any(item["action"] == "legacy.project_renamed" for item in events)


def test_permissions_service_emits_immutable_audit_events() -> None:
    service = PermissionsService()
    service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-a",
        principal_id="user-1",
        role_key="read_only",
        actor="tester",
    )

    events = service.immutable_audit_events(
        tenant_id="tenant-a",
        organization_id="org-a",
    )
    other_scope = service.immutable_audit_events(
        tenant_id="tenant-b",
        organization_id="org-a",
    )

    assert events
    assert events[-1]["action"] == "permissions.role_assigned"
    assert other_scope == []


def test_settings_service_emits_immutable_audit_events() -> None:
    service = SettingsService()
    service.update_numbering_policy(
        tenant_id="tenant-a",
        organization_id="org-a",
        document_type=CommercialDocumentType.ESTIMATE,
        actor="tester",
        syntax_template="{PREFIX}-{SEQUENCE}",
        prefix="EST",
        suffix="",
        starting_sequence=1,
        sequence_padding=5,
        separator="-",
        reset_policy="never",
        include_year_token=False,
        include_month_token=False,
        include_project_code_token=False,
    )

    events = service.immutable_audit_events(
        tenant_id="tenant-a",
        organization_id="org-a",
    )

    assert events
    assert events[-1]["action"] == "organization.numbering_policy.updated"

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from atlas_core.contracts.tenant_manager_contracts import SandboxProvisioningRequest
from atlas_core.services.permissions_service import PermissionsService
from atlas_core.services.tenant_manager_service import TenantManagerService


def _service(tmp_path: Path) -> TenantManagerService:
    permissions = PermissionsService()
    permissions.assign_role(
        tenant_id="local",
        organization_id="atlas",
        principal_id="platform-admin",
        role_key="tenant_administrator",
        actor="tests",
    )
    return TenantManagerService(
        workspace_root=tmp_path / "AtlasProjects",
        permissions_service=permissions,
    )


def test_local_default_tenant_is_backward_compatible(tmp_path: Path) -> None:
    service = _service(tmp_path)

    local = service.list_tenants(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    assert any(item["tenant_id"] == "local" for item in local)


def test_tenant_creation_stable_id_and_repository_isolation(tmp_path: Path) -> None:
    service = _service(tmp_path)

    created = service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-alpha",
            sandbox_label="Tenant Alpha",
            owner_user_id="owner-a",
            seed_data_profile="alpha",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    tenant = created["tenant"]
    assert tenant["tenant_id"] == "tenant-alpha"
    assert tenant["status"] == "active"
    repository_paths = tenant["environment"]["repository_paths"]
    assert "projects" in repository_paths
    assert Path(repository_paths["projects"]).exists()

    suspended = service.suspend_sandbox(
        tenant_id="tenant-alpha",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    restored = service.restore_sandbox(
        tenant_id="tenant-alpha",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    assert suspended["tenant_id"] == "tenant-alpha"
    assert restored["tenant_id"] == "tenant-alpha"


def test_cross_tenant_reference_attachment_and_relationship_rejection(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="cross-tenant object relationship"):
        service.assert_same_tenant_reference(
            source_tenant_id="tenant-a",
            target_tenant_id="tenant-b",
            reference_type="object relationship",
        )

    with pytest.raises(ValueError, match="cross-tenant attachment reference"):
        service.assert_attachment_scope(
            tenant_id="tenant-a",
            attachment_tenant_id="tenant-b",
        )


def test_platform_admin_permission_enforced(tmp_path: Path) -> None:
    permissions = PermissionsService()
    service = TenantManagerService(
        workspace_root=tmp_path / "AtlasProjects",
        permissions_service=permissions,
    )

    with pytest.raises(PermissionError):
        service.create_sandbox(
            request=SandboxProvisioningRequest(
                sandbox_label="Denied",
                owner_user_id="user-1",
                seed_data_profile="none",
            ),
            actor_id="user-1",
            requester_tenant_id="local",
            requester_organization_id="atlas",
        )


def test_tenant_scope_admin_cannot_use_platform_management(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.permissions_service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-tenant-a",
        principal_id="owner-a",
        role_key="tenant_administrator",
        actor="tests",
    )

    with pytest.raises(PermissionError, match="platform administration scope"):
        service.list_tenants(
            actor_id="owner-a",
            requester_tenant_id="tenant-a",
            requester_organization_id="org-tenant-a",
        )


def test_search_job_settings_and_preferences_are_tenant_isolated(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-b",
            sandbox_label="Tenant B",
            owner_user_id="owner-b",
            seed_data_profile="profile-b",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    service.set_search_index(
        tenant_id="tenant-a",
        index_key="objects",
        records=[{"id": "A-1"}],
    )
    service.set_search_index(
        tenant_id="tenant-b",
        index_key="objects",
        records=[{"id": "B-1"}],
    )
    service.append_job_record(tenant_id="tenant-a", job_payload={"job_id": "job-a"})
    service.append_job_record(tenant_id="tenant-b", job_payload={"job_id": "job-b"})
    service.set_user_preference(
        tenant_id="tenant-a",
        user_id="owner-a",
        preference_key="density",
        preference_value="compact",
    )
    service.set_user_preference(
        tenant_id="tenant-b",
        user_id="owner-b",
        preference_key="density",
        preference_value="comfortable",
    )
    service.set_working_set(
        tenant_id="tenant-a",
        user_id="owner-a",
        object_ids=["obj-a"],
    )
    service.set_working_set(
        tenant_id="tenant-b",
        user_id="owner-b",
        object_ids=["obj-b"],
    )

    assert service.get_search_index(tenant_id="tenant-a", index_key="objects") == [
        {"id": "A-1"}
    ]
    assert service.get_search_index(tenant_id="tenant-b", index_key="objects") == [
        {"id": "B-1"}
    ]
    assert service.list_job_records(tenant_id="tenant-a") == [{"job_id": "job-a"}]
    assert service.list_job_records(tenant_id="tenant-b") == [{"job_id": "job-b"}]
    assert service.user_preferences(tenant_id="tenant-a", user_id="owner-a") == {
        "density": "compact"
    }
    assert service.user_preferences(tenant_id="tenant-b", user_id="owner-b") == {
        "density": "comfortable"
    }
    assert service.working_set(tenant_id="tenant-a", user_id="owner-a") == ["obj-a"]
    assert service.working_set(tenant_id="tenant-b", user_id="owner-b") == ["obj-b"]


def test_seed_reset_export_archive_and_delete_workflow_is_guarded(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-b",
            sandbox_label="Tenant B",
            owner_user_id="owner-b",
            seed_data_profile="profile-b",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    before_a = service.storage_usage_summary(tenant_id="tenant-a")
    before_b = service.storage_usage_summary(tenant_id="tenant-b")
    assert before_a["catalog_items"] > 0
    assert before_b["catalog_items"] > 0

    service.reset_sandbox_data(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        confirmation="RESET tenant-a",
    )

    after_a = service.storage_usage_summary(tenant_id="tenant-a")
    after_b = service.storage_usage_summary(tenant_id="tenant-b")
    assert after_a["catalog_items"] == 0
    assert after_b["catalog_items"] == before_b["catalog_items"]

    exported_b = service.export_tenant_data(
        tenant_id="tenant-b",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    export_json = str(exported_b)
    assert "tenant-b" in export_json
    assert "tenant-a" not in export_json

    archived = service.archive_sandbox(
        tenant_id="tenant-b",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    assert archived["status"] == "archived"

    with pytest.raises(ValueError, match="delete confirmation"):
        service.delete_sandbox_guarded(
            tenant_id="tenant-b",
            actor_id="platform-admin",
            requester_tenant_id="local",
            requester_organization_id="atlas",
            confirmation="DELETE wrong",
        )

    deleted = service.delete_sandbox_guarded(
        tenant_id="tenant-b",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        confirmation="DELETE tenant-b",
    )
    assert deleted["deleted"] is True


def test_recent_audit_events_capture_lifecycle_actions(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=False,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.suspend_sandbox(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.restore_sandbox(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    events = service.recent_tenant_audit_events(tenant_id="tenant-a")
    actions = {item["action"] for item in events}
    assert "tenant.status.suspended" in actions
    assert "tenant.status.active" in actions


def test_suspended_tenant_cannot_access_operational_data(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=False,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    service.suspend_sandbox(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    with pytest.raises(PermissionError, match="active status"):
        service.set_search_index(
            tenant_id="tenant-a",
            index_key="objects",
            records=[{"id": "blocked"}],
        )
    with pytest.raises(PermissionError, match="active status"):
        service.assert_active_tenant_context("tenant-a")


def test_alpha_feedback_is_tenant_scoped_and_structured(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    created = service.submit_alpha_feedback(
        tenant_id="tenant-a",
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        user_id="owner-a",
        workspace="Transactions",
        object_or_transaction="estimate:EST-001",
        severity="high",
        reproduction_steps="1. Open draft\n2. Click issue",
        expected_result="Issue action warns only when invalid.",
        actual_result="Issue action failed with generic error.",
        attachment_references=["att-1"],
        environment_diagnostics={"token": "secret://token", "page": "Transactions"},
    )
    assert created["tenant_id"] == "tenant-a"
    assert created["workspace"] == "Transactions"
    assert created["status"] == "open"
    assert created["environment_diagnostics"]["token"] == "[redacted]"

    listed = service.list_alpha_feedback(
        tenant_id="tenant-a",
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
    )
    assert len(listed) == 1
    assert listed[0]["feedback_id"] == created["feedback_id"]

    with pytest.raises(PermissionError, match="cross-tenant diagnostics"):
        service.list_alpha_feedback(
            tenant_id="tenant-a",
            requester_tenant_id="tenant-b",
            requester_organization_id="org-tenant-b",
        )


def test_alpha_health_check_requires_platform_admin_and_redacts(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.append_job_record(
        tenant_id="tenant-a",
        job_payload={
            "job_id": "job-1",
            "status": "failed",
            "error": "/Users/tester/private/path failure",
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
    )

    with pytest.raises(PermissionError):
        service.alpha_health_check(
            tenant_id="tenant-a",
            actor_id="owner-a",
            requester_tenant_id="tenant-a",
            requester_organization_id="org-tenant-a",
            application_version="1.5.0-alpha-a02",
            environment_label="Controlled Alpha",
            test_suite_baseline_reference="1408 passing",
        )

    payload = service.alpha_health_check(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        application_version="1.5.0-alpha-a02",
        environment_label="Controlled Alpha",
        test_suite_baseline_reference="1408 passing",
    )
    assert payload["application_version"] == "1.5.0-alpha-a02"
    assert payload["tenant_id"] == "tenant-a"
    assert payload["tenant_status"] == "active"
    assert payload["test_suite_baseline_reference"] == "1408 passing"
    assert payload["background_job_health"]["failed_jobs"] == 1
    assert payload["recent_errors"][0]["message"] == "[redacted-path]"


def test_two_sandbox_alpha_operations_are_isolated(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="alpha-basic",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-b",
            sandbox_label="Tenant B",
            owner_user_id="owner-b",
            seed_data_profile="alpha-commercial",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    feedback_a = service.submit_alpha_feedback(
        tenant_id="tenant-a",
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        user_id="owner-a",
        workspace="Settings",
        object_or_transaction="tenant_manager",
        severity="medium",
        reproduction_steps="open",
        expected_result="ok",
        actual_result="ok",
    )
    feedback_b = service.submit_alpha_feedback(
        tenant_id="tenant-b",
        requester_tenant_id="tenant-b",
        requester_organization_id="org-tenant-b",
        user_id="owner-b",
        workspace="Transactions",
        object_or_transaction="invoice:INV-1",
        severity="high",
        reproduction_steps="issue",
        expected_result="ok",
        actual_result="warning",
    )
    assert feedback_a["tenant_id"] == "tenant-a"
    assert feedback_b["tenant_id"] == "tenant-b"

    export_b = service.export_tenant_data(
        tenant_id="tenant-b",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    assert "tenant-b" in str(export_b)
    assert "tenant-a" not in str(export_b)

    before_b = service.storage_usage_summary(tenant_id="tenant-b")
    service.reset_sandbox_data(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        confirmation="RESET tenant-a",
    )
    after_b = service.storage_usage_summary(tenant_id="tenant-b")
    assert after_b["catalog_items"] == before_b["catalog_items"]

    tenant_a_feedback = service.list_alpha_feedback(
        tenant_id="tenant-a",
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
    )
    tenant_b_feedback = service.list_alpha_feedback(
        tenant_id="tenant-b",
        requester_tenant_id="tenant-b",
        requester_organization_id="org-tenant-b",
    )
    assert len(tenant_a_feedback) == 0
    assert len(tenant_b_feedback) == 1

    health_a = service.alpha_health_check(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        application_version="1.5.0-alpha-a02",
        environment_label="Controlled Alpha",
        test_suite_baseline_reference="1408 passing",
    )
    assert health_a["tenant_id"] == "tenant-a"
    assert health_a["last_backup_or_export"]["last_export_at"] == ""


def test_application_error_fingerprinting_redaction_and_occurrences(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=False,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    first = service.log_application_error(
        actor_id="owner-a",
        tenant_id="tenant-a",
        environment_label="Controlled Alpha",
        application_version="1.5.0-alpha-a02",
        severity="high",
        exception_type="ValueError",
        message="/Users/private/secrets.txt",
        stack_trace="Traceback\nline /Users/private/secrets.txt\nsecret://token",
        workspace="Transactions",
        route="Transactions",
        background_job_id="job-123",
    )
    second = service.log_application_error(
        actor_id="owner-a",
        tenant_id="tenant-a",
        environment_label="Controlled Alpha",
        application_version="1.5.0-alpha-a02",
        severity="high",
        exception_type="ValueError",
        message="/Users/private/secrets.txt",
        stack_trace="Traceback\nline /Users/private/secrets.txt\nsecret://token",
        workspace="Transactions",
        route="Transactions",
        background_job_id="job-123",
    )

    assert first["error_id"] == second["error_id"]
    assert second["occurrence_count"] == 2
    assert second["summary"] == "[redacted-sensitive]"
    assert "secret://" not in second["occurrences"][0]["sanitized_stack_trace"]
    assert second["context"]["background_job_id"] == "job-123"


def test_application_error_tenant_scope_and_suspended_rejection(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=False,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-b",
            sandbox_label="Tenant B",
            owner_user_id="owner-b",
            seed_data_profile="profile-b",
            enable_seed_data=False,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    service.log_application_error(
        actor_id="platform-admin",
        tenant_id="tenant-a",
        environment_label="Controlled Alpha",
        application_version="1.5.0-alpha-a02",
        severity="medium",
        exception_type="RuntimeError",
        message="a-error",
        stack_trace="trace",
        workspace="Settings",
        route="Platform Management",
    )
    service.log_application_error(
        actor_id="platform-admin",
        tenant_id="tenant-b",
        environment_label="Controlled Alpha",
        application_version="1.5.0-alpha-a02",
        severity="medium",
        exception_type="RuntimeError",
        message="b-error",
        stack_trace="trace",
        workspace="Settings",
        route="Platform Management",
    )

    tenant_a_rows = service.list_application_errors(
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        actor_id="owner-a",
        tenant_id="tenant-a",
    )
    assert len(tenant_a_rows) == 1
    assert tenant_a_rows[0]["tenant_id"] == "tenant-a"

    platform_rows = service.list_application_errors(
        requester_tenant_id="local",
        requester_organization_id="atlas",
        actor_id="platform-admin",
        tenant_id=None,
    )
    assert len(platform_rows) >= 2

    with pytest.raises(PermissionError, match="cross-tenant diagnostics"):
        service.get_application_error_details(
            requester_tenant_id="tenant-a",
            requester_organization_id="org-tenant-a",
            actor_id="owner-a",
            tenant_id="tenant-b",
            error_id=tenant_a_rows[0]["error_id"],
        )

    service.suspend_sandbox(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    with pytest.raises(PermissionError, match="active status"):
        service.list_application_errors(
            requester_tenant_id="tenant-a",
            requester_organization_id="org-tenant-a",
            actor_id="owner-a",
            tenant_id="tenant-a",
        )


def test_application_error_status_workflow_and_feedback_linking(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=False,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    created = service.log_application_error(
        actor_id="owner-a",
        tenant_id="tenant-a",
        environment_label="Controlled Alpha",
        application_version="1.5.0-alpha-a02",
        severity="critical",
        exception_type="LookupError",
        message="integration hook failed",
        stack_trace="stack",
        workspace="Transactions",
        route="Transactions",
        correlation_id="corr-1",
        integration_hook="qbo.sync",
    )

    updated = service.update_application_error_status(
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        actor_id="owner-a",
        tenant_id="tenant-a",
        error_id=created["error_id"],
        status="resolved",
        resolution_notes="fixed by retry",
    )
    assert updated["status"] == "resolved"
    assert updated["resolution_notes"] == "fixed by retry"

    reopened = service.log_application_error(
        actor_id="owner-a",
        tenant_id="tenant-a",
        environment_label="Controlled Alpha",
        application_version="1.5.0-alpha-a02",
        severity="critical",
        exception_type="LookupError",
        message="integration hook failed",
        stack_trace="stack",
        workspace="Transactions",
        route="Transactions",
        correlation_id="corr-1",
        integration_hook="qbo.sync",
    )
    assert reopened["status"] == "reopened"

    feedback = service.submit_alpha_feedback(
        tenant_id="tenant-a",
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        user_id="owner-a",
        workspace="Transactions",
        object_or_transaction="invoice:INV-1",
        severity="high",
        reproduction_steps="step",
        expected_result="ok",
        actual_result="fail",
        related_error_id=created["error_id"],
    )
    assert feedback["related_error_id"] == created["error_id"]

    with pytest.raises(ValueError, match="application error does not exist"):
        service.submit_alpha_feedback(
            tenant_id="tenant-a",
            requester_tenant_id="tenant-a",
            requester_organization_id="org-tenant-a",
            user_id="owner-a",
            workspace="Transactions",
            object_or_transaction="invoice:INV-1",
            severity="high",
            reproduction_steps="step",
            expected_result="ok",
            actual_result="fail",
            related_error_id="ERR-DOES-NOT-EXIST",
        )

    health = service.alpha_health_check(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        application_version="1.5.0-alpha-a02",
        environment_label="Controlled Alpha",
        test_suite_baseline_reference="1412 passing",
    )
    assert health["recent_errors_by_severity"]["critical"] >= 1
    assert health["unresolved_error_count"] >= 1

    diagnostics = service.export_application_error_diagnostics(
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        actor_id="owner-a",
        tenant_id="tenant-a",
    )
    assert diagnostics["tenant_id"] == "tenant-a"
    assert diagnostics["errors"][0]["error_id"].startswith("ERR-")


def test_alpha_tester_onboarding_scenario_completion_and_deactivation(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=True,
            expiration_date=(datetime.now(UTC) + timedelta(days=7)).isoformat(),
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    tester = service.assign_alpha_tester(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        tester_id="tester-1",
        display_name="Tester One",
        email="tester-1@example.com",
    )
    assert tester["state"] == "invited"
    assert tester["sandbox_expiration"]

    acknowledged = service.acknowledge_alpha_onboarding(
        tenant_id="tenant-a",
        tester_id="tester-1",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        terms_acknowledged=True,
        known_limitations_acknowledged=True,
    )
    assert acknowledged["state"] == "onboarding"
    assert acknowledged["terms_acknowledged"] is True
    assert acknowledged["known_limitations_acknowledged"] is True

    assigned = service.assign_alpha_scenarios(
        tenant_id="tenant-a",
        tester_id="tester-1",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        scenario_keys=["organization_settings", "estimate_creation_pdf"],
    )
    assert len(assigned) == 2

    scenario_id = assigned[0]["scenario_id"]
    updated_scenario = service.update_alpha_scenario_status(
        tenant_id="tenant-a",
        tester_id="tester-1",
        scenario_id=scenario_id,
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        status="completed",
        tester_notes="Completed baseline walkthrough",
        related_feedback=["feedback:abc123"],
        related_error_id="ERR-12345",
    )
    assert updated_scenario["status"] == "completed"
    assert updated_scenario["related_error_id"] == "ERR-12345"
    assert updated_scenario["related_feedback"] == ["feedback:abc123"]

    listed = service.list_alpha_tester_scenarios(
        tenant_id="tenant-a",
        tester_id="tester-1",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    assert any(
        row["scenario_id"] == scenario_id and row["status"] == "completed"
        for row in listed
    )

    tester_after_progress = service.get_alpha_tester(
        tenant_id="tenant-a",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        actor_id="platform-admin",
        tester_id="tester-1",
    )
    assert tester_after_progress["state"] == "active"

    access = service.assert_alpha_tester_access(
        tenant_id="tenant-a", tester_id="tester-1"
    )
    assert access["tester_id"] == "tester-1"

    deactivated = service.deactivate_alpha_tester(
        tenant_id="tenant-a",
        tester_id="tester-1",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    assert deactivated["state"] == "deactivated"

    with pytest.raises(PermissionError, match="deactivated"):
        service.assert_alpha_tester_access(tenant_id="tenant-a", tester_id="tester-1")

    actions = {
        event["action"]
        for event in service.recent_tenant_audit_events(tenant_id="tenant-a")
    }
    assert "tenant.alpha_tester.assigned" in actions
    assert "tenant.alpha_tester.acknowledged" in actions
    assert "tenant.alpha_tester.scenarios_assigned" in actions
    assert "tenant.alpha_tester.scenario_updated" in actions
    assert "tenant.alpha_tester.status_updated" in actions


def test_alpha_tester_cross_tenant_rejection_and_platform_scope_requirements(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=False,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-b",
            sandbox_label="Tenant B",
            owner_user_id="owner-b",
            seed_data_profile="profile-b",
            enable_seed_data=False,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.permissions_service.assign_role(
        tenant_id="tenant-a",
        organization_id="org-tenant-a",
        principal_id="owner-a",
        role_key="tenant_administrator",
        actor="tests",
    )

    with pytest.raises(PermissionError):
        service.assign_alpha_tester(
            tenant_id="tenant-a",
            actor_id="owner-a",
            requester_tenant_id="tenant-a",
            requester_organization_id="org-tenant-a",
            tester_id="tester-unauthorized",
            display_name="Unauthorized",
            email="unauthorized@example.com",
        )

    service.assign_alpha_tester(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        tester_id="tester-a",
        display_name="Tester A",
        email="tester-a@example.com",
    )

    with pytest.raises(PermissionError, match="cross-tenant"):
        service.get_alpha_tester(
            tenant_id="tenant-a",
            requester_tenant_id="tenant-b",
            requester_organization_id="org-tenant-b",
            actor_id="owner-b",
            tester_id="tester-a",
        )


def test_alpha_operations_dashboard_and_requests_are_tracked(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=True,
            expiration_date=(datetime.now(UTC) + timedelta(days=10)).isoformat(),
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-b",
            sandbox_label="Tenant B",
            owner_user_id="owner-b",
            seed_data_profile="profile-b",
            enable_seed_data=True,
            expiration_date=(datetime.now(UTC) + timedelta(days=45)).isoformat(),
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    service.assign_alpha_tester(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        tester_id="tester-a1",
        display_name="Tester A1",
        email="tester-a1@example.com",
    )
    service.assign_alpha_scenarios(
        tenant_id="tenant-a",
        tester_id="tester-a1",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        scenario_keys=["organization_settings"],
    )
    scenarios = service.list_alpha_tester_scenarios(
        tenant_id="tenant-a",
        tester_id="tester-a1",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.update_alpha_scenario_status(
        tenant_id="tenant-a",
        tester_id="tester-a1",
        scenario_id=scenarios[0]["scenario_id"],
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        status="completed",
    )
    service.request_sandbox_reset(
        tenant_id="tenant-a",
        tester_id="tester-a1",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        reason="reset for second pass",
    )
    service.request_tenant_export(
        tenant_id="tenant-a",
        tester_id="tester-a1",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        reason="export validation package",
    )

    dashboard = service.alpha_operations_dashboard(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    assert dashboard["active_testers"] >= 1
    assert dashboard["expiring_sandboxes"] >= 1
    row_a = next(item for item in dashboard["rows"] if item["tenant_id"] == "tenant-a")
    assert row_a["scenario_completion"] == "1/1"
    assert row_a["reset_requests"] == 1
    assert row_a["export_requests"] == 1

    with pytest.raises(PermissionError):
        service.alpha_operations_dashboard(
            actor_id="owner-a",
            requester_tenant_id="tenant-a",
            requester_organization_id="org-tenant-a",
        )


def test_alpha_release_management_and_deterministic_ordering(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-b",
            sandbox_label="Tenant B",
            owner_user_id="owner-b",
            seed_data_profile="profile-b",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.assign_alpha_tester(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        tester_id="tester-a",
        display_name="Tester A",
        email="tester-a@example.com",
    )
    service.assign_alpha_tester(
        tenant_id="tenant-b",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        tester_id="tester-b",
        display_name="Tester B",
        email="tester-b@example.com",
    )

    cohort = service.create_alpha_tester_cohort(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        cohort_name="Wave 1",
        member_assignments=[
            {"tenant_id": "tenant-a", "tester_id": "tester-a"},
            {"tenant_id": "tenant-b", "tester_id": "tester-b"},
        ],
        notes="initial rollout",
    )

    release_a = service.create_alpha_release_record(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        version_identifier="1.5.0-alpha-a03",
        release_date="2026-07-10T00:00:00+00:00",
        commit_hash="0b72d0f",
        included_fixes=["A-03 rollout baseline"],
        known_limitations=["local deterministic runtime only"],
        supported_test_scenarios=["organization_settings"],
        assigned_tester_cohort_ids=[cohort["cohort_id"]],
        rollback_reference="git checkout 0b72d0f^",
        release_status="Approved",
    )
    release_b = service.create_alpha_release_record(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        version_identifier="1.5.0-alpha-a04",
        release_date="2026-07-14T00:00:00+00:00",
        commit_hash="head-a04",
        included_fixes=["A-04 stabilization"],
        known_limitations=["no hosted infrastructure"],
        supported_test_scenarios=["error_reporting"],
        assigned_tester_cohort_ids=[cohort["cohort_id"]],
        rollback_reference="git checkout 0b72d0f",
        release_status="Draft",
    )
    assert release_a["release_status"] == "Approved"
    assert release_b["release_status"] == "Draft"

    releases = service.list_alpha_release_records(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    assert [row["version_identifier"] for row in releases][-2:] == [
        "1.5.0-alpha-a03",
        "1.5.0-alpha-a04",
    ]

    updated = service.update_alpha_release_status(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        release_id=release_b["release_id"],
        release_status="Under Test",
        notes="assigned to sandboxes",
    )
    assert updated["release_status"] == "Under Test"

    reassigned = service.assign_alpha_release_cohorts(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        release_id=release_b["release_id"],
        cohort_ids=[cohort["cohort_id"]],
    )
    assert len(reassigned["assigned_tester_cohorts"]) == 1

    history = service.alpha_stabilization_release_history(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    assert history[-1]["release_id"] == release_b["release_id"]

    local_actions = {
        item["action"] for item in service.recent_tenant_audit_events(tenant_id="local")
    }
    assert "alpha.release.created" in local_actions
    assert "alpha.release.status_updated" in local_actions
    assert "alpha.release.cohorts_assigned" in local_actions


def test_alpha_feedback_to_defect_triage_and_retest_lifecycle(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.assign_alpha_tester(
        tenant_id="tenant-a",
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        tester_id="tester-a",
        display_name="Tester A",
        email="tester-a@example.com",
    )

    error_row = service.log_application_error(
        actor_id="owner-a",
        tenant_id="tenant-a",
        environment_label="Controlled Alpha",
        application_version="1.5.0-alpha-a04",
        severity="high",
        exception_type="RuntimeError",
        message="stabilization issue",
        stack_trace="trace",
        workspace="Transactions",
        route="Transactions",
    )
    feedback = service.submit_alpha_feedback(
        tenant_id="tenant-a",
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        user_id="tester-a",
        workspace="Transactions",
        object_or_transaction="estimate:EST-900",
        severity="high",
        reproduction_steps="1. Open estimate\n2. Save",
        expected_result="Estimate saves successfully",
        actual_result="Save throws runtime error",
        related_error_id=error_row["error_id"],
    )

    triage = service.alpha_feedback_triage_queue(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    assert any(
        item["feedback_id"] == feedback["feedback_id"]
        for item in triage["feedback_queue"]
    )

    defect = service.create_alpha_defect_from_feedback(
        tenant_id="tenant-a",
        feedback_id=feedback["feedback_id"],
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        application_version="1.5.0-alpha-a04",
        severity="High",
        alpha_blocking=True,
        defect_status="Confirmed",
        assigned_sprint_or_release="A-04",
        resolution_priority="P1",
        regression_test_required=True,
        release_note_linkage="RELEASE_NOTES:A-04",
    )
    assert defect["defect_status"] == "Confirmed"
    assert defect["alpha_blocking"] is True
    assert defect["related_error_id"] == error_row["error_id"]

    ready_for_retest = service.update_alpha_defect(
        tenant_id="tenant-a",
        defect_id=defect["defect_id"],
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        defect_status="Ready for Retest",
        retest_status="Ready for Retest",
        regression_test_references=[
            "tests/test_tenant_manager_service.py::test_alpha_feedback_to_defect_triage_and_retest_lifecycle"
        ],
        resolution_notes="patched in A-04",
    )
    assert ready_for_retest["defect_status"] == "Ready for Retest"
    assert ready_for_retest["retest_status"] == "Ready for Retest"

    verified = service.update_alpha_defect(
        tenant_id="tenant-a",
        defect_id=defect["defect_id"],
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        defect_status="Verified",
        retest_status="Passed",
        verification_evidence="pytest tests/test_tenant_manager_service.py -q",
    )
    assert verified["defect_status"] == "Verified"
    assert verified["retest_status"] == "Passed"
    assert verified["verification_evidence"]

    dashboard = service.alpha_operations_dashboard(
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    assert dashboard["unresolved_errors"] >= 1
    assert "/" in dashboard["scenario_completion"]

    tenant_actions = {
        item["action"]
        for item in service.recent_tenant_audit_events(tenant_id="tenant-a")
    }
    assert "tenant.alpha_defect.created" in tenant_actions
    assert "tenant.alpha_defect.updated" in tenant_actions


def test_alpha_enhancement_defect_rule_and_tenant_visibility(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-a",
            sandbox_label="Tenant A",
            owner_user_id="owner-a",
            seed_data_profile="profile-a",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )
    service.create_sandbox(
        request=SandboxProvisioningRequest(
            tenant_id="tenant-b",
            sandbox_label="Tenant B",
            owner_user_id="owner-b",
            seed_data_profile="profile-b",
            enable_seed_data=True,
        ),
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
    )

    feedback_owner_a = service.submit_alpha_feedback(
        tenant_id="tenant-a",
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        user_id="owner-a",
        workspace="Settings",
        object_or_transaction="tenant_manager",
        severity="medium",
        reproduction_steps="step",
        expected_result="ok",
        actual_result="warn",
    )
    service.submit_alpha_feedback(
        tenant_id="tenant-a",
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        user_id="owner-b",
        workspace="Settings",
        object_or_transaction="tenant_manager",
        severity="medium",
        reproduction_steps="step",
        expected_result="ok",
        actual_result="warn",
    )
    enhancement = service.create_alpha_defect_from_feedback(
        tenant_id="tenant-a",
        feedback_id=feedback_owner_a["feedback_id"],
        actor_id="platform-admin",
        requester_tenant_id="local",
        requester_organization_id="atlas",
        application_version="1.5.0-alpha-a04",
        severity="Enhancement",
        alpha_blocking=True,
        defect_status="Confirmed",
        assigned_sprint_or_release="backlog",
        resolution_priority="Backlog",
        regression_test_required=False,
    )
    assert enhancement["defect_severity"] == "Enhancement"
    assert enhancement["alpha_blocking"] is False
    assert enhancement["defect_status"] == "Deferred"

    owner_a_feedback = service.list_alpha_feedback(
        tenant_id="tenant-a",
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        actor_id="owner-a",
    )
    assert all(item["user_id"] == "owner-a" for item in owner_a_feedback)

    owner_a_defects = service.list_alpha_defects(
        actor_id="owner-a",
        requester_tenant_id="tenant-a",
        requester_organization_id="org-tenant-a",
        tenant_id="tenant-a",
    )
    assert len(owner_a_defects) == 1
    assert owner_a_defects[0]["feedback_user_id"] == "owner-a"

    with pytest.raises(PermissionError, match="cross-tenant diagnostics"):
        service.list_alpha_feedback(
            tenant_id="tenant-a",
            requester_tenant_id="tenant-b",
            requester_organization_id="org-tenant-b",
            actor_id="owner-b",
        )

    with pytest.raises(PermissionError, match="cross-tenant diagnostics"):
        service.list_alpha_defects(
            actor_id="owner-b",
            requester_tenant_id="tenant-b",
            requester_organization_id="org-tenant-b",
            tenant_id="tenant-a",
        )

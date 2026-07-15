from __future__ import annotations

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

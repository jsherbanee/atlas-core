from pathlib import Path
from atlas_core.services.project_workspace_service import ProjectWorkspaceService
from atlas_core.contracts.background_job_contracts import (
    JobRequest,
    JobDefinition,
    JobRetryPolicy,
    JobCategory,
)
from atlas_core.services.permissions_service import PermissionsService
from atlas_core.contracts.permissions_contracts import AccessRequest


def _create_service_and_record(tmp_path: Path, project_id: str):
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id=project_id, name=project_id, client="Client"
    )
    # default tenant/org for workspace persistence
    record.metadata["tenant_id"] = "tenant-a"
    record.metadata["organization_id"] = "org-a"
    service.save_record(record)
    return service, record


def test_project_job_listing_and_isolation_and_restart_durability(
    tmp_path: Path,
) -> None:
    service, record_a = _create_service_and_record(tmp_path, "proc-a")
    service_b, record_b = _create_service_and_record(tmp_path, "proc-b")

    # enqueue a document processing job for project A
    service.enqueue_document_processing(
        workspace_id=record_a.workspace_id,
        uploaded_files=[("a.pdf", b"pdf-bytes")],
        actor_id="user-1",
    )

    visible = service.list_background_jobs(record_a.workspace_id)
    assert len(visible) >= 1

    hidden = service.list_background_jobs(record_b.workspace_id)
    assert hidden == []

    # restart durability: new service instance reading same path
    restarted = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    visible_after_restart = restarted.list_background_jobs(record_a.workspace_id)
    assert any(str(item.get("job_id") or "") for item in visible_after_restart)


def test_retry_and_cancel_actions_change_state(tmp_path: Path) -> None:
    service, record = _create_service_and_record(tmp_path, "proc-actions")
    # failing handler registered for SEARCH_INDEXING to force retry logic

    def _failing_handler(_context: object) -> dict[str, object]:
        raise RuntimeError("simulated failure")

    service.manager.background_job_service.register_handler(
        category=JobCategory.SEARCH_INDEXING,
        handler=_failing_handler,
    )

    request = JobRequest(
        tenant_id="tenant-a",
        organization_id="org-a",
        actor_id="user-1",
        category=JobCategory.SEARCH_INDEXING,
        definition=JobDefinition(
            category=JobCategory.SEARCH_INDEXING,
            handler_key="tests.search_indexing",
            cancellable=False,
        ),
        input_payload={"workspace_id": record.workspace_id},
        related_object_type="project",
        related_object_id=record.workspace_id,
        idempotency_key="retry-job-1",
        retry_policy=JobRetryPolicy(max_attempts=2, retry_delay_seconds=0),
    )

    created = service.manager.background_job_service.submit_job(
        project_id=record.workspace_id, request=request
    )

    # run will fail and schedule retry
    failed = service.manager.background_job_service.run_job(
        project_id=record.workspace_id,
        job_id=str(created.get("job_id")),
        tenant_id="tenant-a",
        organization_id="org-a",
    )

    assert str(failed.get("status")) in {"retry_scheduled", "failed"}

    # retry via wrapper should eventually produce a failed final state
    retried = service.retry_background_job(
        record.workspace_id, job_id=str(created.get("job_id"))
    )
    assert str(retried.get("status")) in {"failed", "succeeded", "retry_scheduled"}

    # cancel a queued cancellable job
    request2 = JobRequest(
        tenant_id="tenant-a",
        organization_id="org-a",
        actor_id="user-1",
        category=JobCategory.COMMERCIAL_IMPORT,
        definition=JobDefinition(
            category=JobCategory.COMMERCIAL_IMPORT,
            handler_key="tests.commercial_import",
            cancellable=True,
        ),
        input_payload={"workspace_id": record.workspace_id},
        related_object_type="project",
        related_object_id=record.workspace_id,
        idempotency_key="cancel-job-1",
        retry_policy=JobRetryPolicy(max_attempts=1),
    )

    created2 = service.manager.background_job_service.submit_job(
        project_id=record.workspace_id, request=request2
    )
    cancelled = service.cancel_background_job(
        record.workspace_id,
        job_id=str(created2.get("job_id")),
        actor_id="user-1",
        reason="Cancelled in test",
    )

    assert str(cancelled.get("status")) == "cancelled"
    assert dict(cancelled.get("cancellation") or {}).get("requested") is True


def test_permissions_enforcement_for_manage_controls() -> None:
    perms = PermissionsService()
    # default: no role assigned -> deny
    decision = perms.evaluate(
        AccessRequest(
            tenant_id="local",
            organization_id="atlas",
            principal_id="anon",
            permission_key="jobs.manage",
        )
    )
    assert not decision.allowed

    # assign a role that grants jobs.manage
    perms.assign_role(
        tenant_id="local",
        organization_id="atlas",
        principal_id="op-1",
        role_key="estimator",
        actor="system",
    )
    allowed = perms.evaluate(
        AccessRequest(
            tenant_id="local",
            organization_id="atlas",
            principal_id="op-1",
            permission_key="jobs.manage",
        )
    )
    assert allowed.allowed

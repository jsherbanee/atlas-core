from pathlib import Path
import json
import re

from atlas_core.contracts.background_job_contracts import (
    JobCategory,
    JobDefinition,
    JobRequest,
    JobRetryPolicy,
)
from atlas_core.domain import Project, ProjectLifecycleEvent, ProjectStatus
from atlas_core.domain import OrganizationRole
from atlas_core.services.project_workspace_service import (
    ProjectWorkspaceRecord,
    ProjectWorkspaceService,
)
from pypdf import PdfWriter
import pytest


def _blank_pdf_bytes() -> bytes:
    from io import BytesIO

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_project_round_trip_preserves_lifecycle_events() -> None:
    project = Project(
        project_id="project-001",
        name="Workspace Project",
        client="Atlas Client",
        lifecycle_events=[
            ProjectLifecycleEvent(
                from_status=ProjectStatus.OPPORTUNITY,
                to_status=ProjectStatus.INTAKE,
                note="Imported into workspace",
            )
        ],
    )

    restored = Project.from_dict(project.to_dict())

    assert restored.project_id == project.project_id
    assert restored.name == project.name
    assert restored.lifecycle_events[0].to_status == ProjectStatus.INTAKE


def test_workspace_service_saves_and_loads_records(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = ProjectWorkspaceRecord(
        workspace_id="project-001",
        project=Project(
            project_id="project-001",
            name="Workspace Project",
            client="Atlas Client",
        ),
        source_mode="manual",
        source_label="Manual Project",
        metadata={"project_name": "Workspace Project"},
        import_summary={"drawing_count": 2},
    )

    saved_path = service.save_record(record)
    loaded = service.load_record(saved_path)

    assert saved_path.exists()
    assert (tmp_path / "AtlasProjects" / "project-001" / "project.json").exists()
    assert (tmp_path / "AtlasProjects" / "project-001" / "metadata.json").exists()
    assert loaded.workspace_id == "project-001"
    assert loaded.project.name == "Workspace Project"
    assert loaded.import_summary["drawing_count"] == 2


def test_workspace_service_lists_recent_projects_by_last_opened(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    first = ProjectWorkspaceRecord(
        workspace_id="project-a",
        project=Project(project_id="project-a", name="A", client="Client A"),
        last_opened_at="2024-01-01T00:00:00+00:00",
    )
    second = ProjectWorkspaceRecord(
        workspace_id="project-b",
        project=Project(project_id="project-b", name="B", client="Client B"),
        last_opened_at="2024-01-02T00:00:00+00:00",
    )

    service.save_record(first)
    service.save_record(second)

    recent = service.list_recent_workspaces()

    assert [record.workspace_id for record in recent[:2]] == ["project-b", "project-a"]


def test_workspace_service_recent_projects_break_ties_by_workspace_id(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    first = ProjectWorkspaceRecord(
        workspace_id="project-a",
        project=Project(project_id="project-a", name="A", client="Client A"),
        last_opened_at="2024-01-02T00:00:00+00:00",
    )
    second = ProjectWorkspaceRecord(
        workspace_id="project-b",
        project=Project(project_id="project-b", name="B", client="Client B"),
        last_opened_at="2024-01-02T00:00:00+00:00",
    )

    service.save_record(first)
    service.save_record(second)

    recent = service.list_recent_workspaces()

    assert [record.workspace_id for record in recent[:2]] == ["project-b", "project-a"]


def test_workspace_service_recent_projects_excludes_archived_by_default(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    active = ProjectWorkspaceRecord(
        workspace_id="project-active",
        project=Project(project_id="project-active", name="Active", client="Client"),
        last_opened_at="2024-01-02T00:00:00+00:00",
    )
    archived = ProjectWorkspaceRecord(
        workspace_id="project-archived",
        project=Project(
            project_id="project-archived", name="Archived", client="Client"
        ),
        last_opened_at="2024-01-03T00:00:00+00:00",
        archived=True,
    )

    service.save_record(active)
    service.save_record(archived)

    recent = service.list_recent_workspaces()

    assert [record.workspace_id for record in recent] == ["project-active"]


def test_workspace_service_project_manager_actions(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="project-001",
        name="Project 001",
        client="Client",
    )
    service.save_record(record)

    renamed = service.rename_project("project-001", "Project 001 Renamed")
    assert renamed.project.name == "Project 001 Renamed"

    pinned = service.pin_project("project-001", pinned=True)
    assert pinned.pinned is True

    reference = service.set_reference_project("project-001", reference=True)
    assert reference.is_reference is True

    archived = service.archive_project("project-001", archived=True)
    assert archived.archived is True

    duplicated = service.duplicate_project(
        "project-001",
        new_workspace_id="project-001-copy",
        new_name="Project 001 Copy",
    )
    assert duplicated.project.project_id == "project-001-copy"


def test_workspace_service_manifest_health_and_bundle(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="project-bundle",
        name="Project Bundle",
        client="Client",
    )
    service.save_record(record)

    manifest = service.read_manifest("project-bundle")
    assert manifest["project_id"] == "project-bundle"

    health = service.project_health("project-bundle")
    assert health["status"] in {"healthy", "warning"}

    bundle_path = service.export_project_bundle(
        "project-bundle",
        str(tmp_path / "project-bundle"),
    )
    assert Path(bundle_path).exists()
    assert Path(bundle_path).suffix == ".atlaspkg"

    service.delete_project("project-bundle")
    imported = service.import_project_bundle(bundle_path)
    assert imported.workspace_id == "project-bundle"
    assert Path(service.project_location("project-bundle")).exists()


def test_workspace_service_runtime_wiring_exposes_preview_authority(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    assert callable(getattr(service, "preview_next_bid_id", None))
    assert callable(getattr(service.manager, "preview_next_bid_id", None))
    assert callable(
        getattr(service.manager.project_repository, "peek_next_bid_id", None)
    )


def test_workspace_service_runtime_wiring_exposes_upload_inspection_api(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    assert callable(getattr(service, "inspect_uploaded_documents", None))


def test_workspace_service_loads_legacy_project_without_identifier_fields(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="legacy-project",
        name="Legacy Project",
        client="Legacy Client",
    )
    service.save_record(record)

    project_json = tmp_path / "AtlasProjects" / "legacy-project" / "project.json"
    payload = json.loads(project_json.read_text(encoding="utf-8"))
    payload.pop("client_project_number", None)
    payload.pop("internal_project_number", None)
    payload.pop("atlas_bid_id", None)
    project_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    loaded = service.load_record("legacy-project")

    assert loaded.project.project_id == "legacy-project"
    assert loaded.project.client_project_number is None
    assert loaded.project.internal_project_number is None


def test_workspace_service_upload_inspection_is_read_only(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    workspace_root = tmp_path / "AtlasProjects"
    before = list(workspace_root.glob("**/*"))

    inspected = service.inspect_uploaded_documents(
        [
            ("bid.pdf", b"pdf-content"),
            ("bad.exe", b"bad"),
        ]
    )

    after = list(workspace_root.glob("**/*"))
    assert any(item.get("accepted", False) for item in inspected.diagnostics)
    assert any(not item.get("accepted", False) for item in inspected.diagnostics)
    assert before == after


def test_workspace_service_stakeholder_directory_create_and_link(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="BID-2099-0001",
        name="Stakeholder Project",
        client="Client",
    )
    service.save_record(record)

    created_org = service.create_stakeholder_organization(
        name="Acme Owner",
        role=OrganizationRole.OWNER_CLIENT,
    )
    linked = service.link_project_stakeholder(
        workspace_id=record.workspace_id,
        organization_id=str(created_org.get("organization_id")),
        role=OrganizationRole.OWNER_CLIENT,
        is_primary=True,
    )

    stakeholders = service.list_project_stakeholders(record.workspace_id)
    assert linked["organization_id"] == created_org["organization_id"]
    assert len(stakeholders) == 1
    assert stakeholders[0]["organization_display_name"] == "Acme Owner"


def test_workspace_service_preview_bid_id_returns_expected_format(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    preview = service.preview_next_bid_id()

    assert re.fullmatch(r"BID-\d{4}-\d{4}", preview) is not None


def test_workspace_service_preview_bid_id_does_not_consume_ids(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    preview = service.preview_next_bid_id()

    created = service.create_manual_record(
        name="Preview Non-Consuming",
        client="Client",
    )

    assert created.project.project_id == preview


def test_workspace_service_multiple_preview_calls_return_identical_value(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    first_preview = service.preview_next_bid_id()
    second_preview = service.preview_next_bid_id()

    assert first_preview == second_preview


def test_workspace_service_preview_then_create_allocates_previewed_id(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    preview = service.preview_next_bid_id()

    created = service.create_manual_record(
        name="Preview Then Create",
        client="Client",
    )

    assert created.project.project_id == preview


def test_workspace_service_create_then_preview_advances_to_next_id(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    first_preview = service.preview_next_bid_id()

    record = service.create_manual_record(
        name="Create Then Preview",
        client="Client",
    )

    next_preview = service.preview_next_bid_id()

    assert record.project.project_id == first_preview
    assert next_preview != first_preview


def test_workspace_service_preview_does_not_reuse_deleted_or_archived_ids(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    first = service.create_manual_record(
        name="First",
        client="Client",
    )
    service.save_record(first)
    first_id = first.workspace_id

    second_preview = service.preview_next_bid_id()
    second = service.create_manual_record(
        name="Second",
        client="Client",
    )
    service.save_record(second)
    second_id = second.workspace_id

    service.archive_project(second_id, archived=True)
    service.delete_project(first_id)

    next_preview = service.preview_next_bid_id()

    assert second_id == second_preview
    assert next_preview not in {first_id, second_id}


def test_workspace_service_create_project_without_documents(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        name="No Docs Yet",
        client="Client",
    )
    service.save_record(record)

    loaded = service.load_record(record.workspace_id)
    assert loaded.workspace_id == record.workspace_id
    assert loaded.project.name == "No Docs Yet"
    assert loaded.import_summary == {}


def test_workspace_service_create_project_with_single_pdf_upload(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        name="Single PDF",
        client="Client",
    )
    service.save_record(record)

    uploaded = service.import_uploaded_documents(
        record.workspace_id,
        [("bid-package.pdf", _blank_pdf_bytes())],
    )

    assert uploaded.workspace_id == record.workspace_id
    assert int(uploaded.import_summary.get("uploaded_file_count", 0) or 0) >= 1


def test_workspace_service_mixed_valid_invalid_uploads_partial_success(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        name="Mixed Upload",
        client="Client",
    )
    service.save_record(record)

    uploaded = service.import_uploaded_documents(
        record.workspace_id,
        [
            ("bid-package.pdf", _blank_pdf_bytes()),
            ("not-supported.exe", b"bad"),
        ],
    )

    assert uploaded.workspace_id == record.workspace_id
    assert int(uploaded.import_summary.get("uploaded_file_count", 0) or 0) >= 1
    assert int(uploaded.import_summary.get("rejected_file_count", 0) or 0) >= 1
    rejected = list(uploaded.import_summary.get("rejected_file_diagnostics") or [])
    assert any(
        str(item.get("name", "")).endswith("not-supported.exe") for item in rejected
    )


def test_workspace_service_project_id_stable_after_import_failure(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        name="Stable ID",
        client="Client",
    )
    service.save_record(record)
    created_id = record.workspace_id

    original_import = service.manager.document_repository.import_uploads

    def _raise_failure(
        project_id: str, uploaded_files: list[tuple[str, bytes]]
    ) -> dict:
        _ = (project_id, uploaded_files)
        raise RuntimeError("simulated import failure")

    service.manager.document_repository.import_uploads = _raise_failure  # type: ignore[assignment]
    try:
        try:
            service.import_uploaded_documents(
                created_id,
                [("bid-package.pdf", b"fake-pdf")],
            )
        except RuntimeError:
            pass
    finally:
        service.manager.document_repository.import_uploads = original_import  # type: ignore[assignment]

    loaded = service.load_record(created_id)
    assert loaded.workspace_id == created_id


def test_workspace_service_upload_flow_preserves_identity_and_owner_across_batches(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    organization = service.create_stakeholder_organization(
        name="Northstar Owner Group",
        role=OrganizationRole.OWNER_CLIENT,
    )
    record = service.create_manual_record(
        name="X03 Validation Main",
        client="Northstar Owner Group",
    )
    service.save_record(record)
    service.link_project_stakeholder(
        workspace_id=record.workspace_id,
        organization_id=str(organization.get("organization_id")),
        role=OrganizationRole.OWNER_CLIENT,
        is_primary=True,
    )

    project_path_before = service.project_location(record.workspace_id)
    atlas_bid_id_before = record.project.atlas_bid_id

    service.import_uploaded_documents(
        record.workspace_id,
        [("batch-one.pdf", _blank_pdf_bytes())],
    )
    service.import_uploaded_documents(
        record.workspace_id,
        [("batch-two.csv", b"col1,col2\n1,2\n")],
    )

    reloaded = service.load_record(record.workspace_id)
    stakeholders = service.list_project_stakeholders(record.workspace_id)
    metadata_path = Path(project_path_before) / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert reloaded.project.name == "X03 Validation Main"
    assert reloaded.project.atlas_bid_id == atlas_bid_id_before
    assert reloaded.project.client == "Northstar Owner Group"
    assert service.project_location(record.workspace_id) == project_path_before
    assert (Path(project_path_before) / "documents" / "drawings").exists()
    assert (Path(project_path_before) / "documents" / "schedules").exists()
    assert metadata.get("project_name") == "X03 Validation Main"
    assert metadata.get("atlas_bid_id") == atlas_bid_id_before
    assert metadata.get("owner") == "Northstar Owner Group"
    assert metadata.get("owner_client") == "Northstar Owner Group"
    assert "current_route" not in metadata
    assert stakeholders
    assert stakeholders[0]["organization_display_name"] == "Northstar Owner Group"


def test_workspace_service_reuses_one_organization_across_projects_and_roles(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    organization = service.create_stakeholder_organization(
        name="Shared Engineering Group",
        role=OrganizationRole.OWNER_CLIENT,
    )
    org_id = str(organization.get("organization_id"))

    first = service.create_manual_record(name="Project One", client="Client One")
    second = service.create_manual_record(name="Project Two", client="Client Two")
    service.save_record(first)
    service.save_record(second)

    service.link_project_stakeholder(
        workspace_id=first.workspace_id,
        organization_id=org_id,
        role=OrganizationRole.OWNER_CLIENT,
        is_primary=True,
    )
    service.link_project_stakeholder(
        workspace_id=first.workspace_id,
        organization_id=org_id,
        role=OrganizationRole.CONSULTANT,
        is_primary=False,
    )
    service.link_project_stakeholder(
        workspace_id=second.workspace_id,
        organization_id=org_id,
        role=OrganizationRole.OWNER_CLIENT,
        is_primary=True,
    )

    first_stakeholders = service.list_project_stakeholders(first.workspace_id)
    second_stakeholders = service.list_project_stakeholders(second.workspace_id)
    organizations = service.organization_directory.list_organizations(
        include_inactive=True
    )

    assert len([item for item in organizations if item.organization_id == org_id]) == 1
    assert len(first_stakeholders) == 2
    assert len(second_stakeholders) == 1
    assert {item["role"] for item in first_stakeholders} == {
        OrganizationRole.OWNER_CLIENT.value,
        OrganizationRole.CONSULTANT.value,
    }


def test_workspace_service_rejects_atlas_bid_id_mutation_after_create(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(name="Immutable Bid", client="Client")
    service.save_record(record)

    loaded = service.load_record(record.workspace_id)
    loaded.project.atlas_bid_id = "BID-2099-9999"
    loaded.metadata["atlas_bid_id"] = "BID-2099-9999"

    with pytest.raises(ValueError, match="Atlas Bid ID is immutable"):
        service.save_record(loaded)


def test_workspace_service_runs_document_import_as_background_job(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="job-import-1",
        name="Import Job",
        client="Client",
    )
    record.metadata["tenant_id"] = "tenant-a"
    record.metadata["organization_id"] = "org-a"
    service.save_record(record)

    result = service.run_document_import_job(
        workspace_id=record.workspace_id,
        uploaded_files=[("bid-package.pdf", _blank_pdf_bytes())],
        actor_id="user-1",
    )
    jobs = service.list_background_jobs(record.workspace_id)

    assert result["status"] == "succeeded"
    assert jobs
    assert jobs[-1]["status"] == "succeeded"
    assert jobs[-1]["request"]["category"] == JobCategory.DOCUMENT_IMPORT.value
    assert service.load_record(record.workspace_id).workspace_id == record.workspace_id


def test_workspace_service_enqueues_document_import_without_running(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="job-enqueue-1",
        name="Queued Import",
        client="Client",
    )
    service.save_record(record)

    submitted = service.enqueue_document_processing(
        workspace_id=record.workspace_id,
        uploaded_files=[("bid-package.pdf", _blank_pdf_bytes())],
        actor_id="user-1",
    )
    loaded = service.load_record(record.workspace_id)

    assert submitted["status"] == "queued"
    assert loaded.import_summary == {}
    assert service.list_background_jobs(record.workspace_id)[0]["status"] == "queued"


def test_workspace_service_enqueues_observed_maw_plan_check_size_without_running(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="job-large-upload-1",
        name="Large Upload",
        client="Client",
    )
    service.save_record(record)
    filename = "09_Theater Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf"

    submitted = service.enqueue_document_processing(
        workspace_id=record.workspace_id,
        uploaded_files=[(filename, b"x" * 54_830_000)],
        actor_id="user-1",
    )

    assert submitted["status"] == "queued"
    assert service.load_record(record.workspace_id).import_summary == {}
    queued_uploads = service.list_background_jobs(record.workspace_id)[0]["request"][
        "input_payload"
    ]["uploaded_files"]
    assert len(queued_uploads) == 1
    assert queued_uploads[0]["name"] == filename
    assert queued_uploads[0]["size_bytes"] == 54_830_000


def test_workspace_service_prevents_duplicate_active_document_jobs(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="job-duplicate-1",
        name="Duplicate Import",
        client="Client",
    )
    service.save_record(record)
    uploaded = [("bid-package.pdf", _blank_pdf_bytes())]

    first = service.enqueue_document_processing(
        workspace_id=record.workspace_id,
        uploaded_files=uploaded,
        actor_id="user-1",
    )
    second = service.enqueue_document_processing(
        workspace_id=record.workspace_id,
        uploaded_files=uploaded,
        actor_id="user-1",
    )

    assert second["job_id"] == first["job_id"]
    assert len(service.list_background_jobs(record.workspace_id)) == 1


def test_workspace_service_claims_and_processes_next_document_job(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="job-process-1",
        name="Process Import",
        client="Client",
    )
    service.save_record(record)
    submitted = service.enqueue_document_processing(
        workspace_id=record.workspace_id,
        uploaded_files=[("bid-package.pdf", _blank_pdf_bytes())],
        actor_id="user-1",
    )

    claimed = service.claim_next_processing_job()
    assert claimed is not None
    assert claimed["job_id"] == submitted["job_id"]
    assert claimed["status"] == "running"

    processed = service.process_document_job(
        workspace_id=record.workspace_id,
        job_id=str(submitted["job_id"]),
    )

    assert processed["status"] == "succeeded"
    assert service.load_record(record.workspace_id).import_summary


def test_workspace_service_process_next_document_job_is_failure_isolated(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    first = service.create_manual_record(
        project_id="job-fail-1",
        name="Failure Import",
        client="Client",
    )
    second = service.create_manual_record(
        project_id="job-ok-1",
        name="Successful Import",
        client="Client",
    )
    service.save_record(first)
    service.save_record(second)
    service.enqueue_document_processing(
        workspace_id=first.workspace_id,
        uploaded_files=[("empty.pdf", b"")],
        actor_id="user-1",
    )
    service.enqueue_document_processing(
        workspace_id=second.workspace_id,
        uploaded_files=[("bid-package.pdf", _blank_pdf_bytes())],
        actor_id="user-1",
    )

    first_result = service.process_next_document_job()
    second_result = service.process_next_document_job()

    assert first_result is not None
    assert second_result is not None
    statuses = {str(first_result["status"]), str(second_result["status"])}
    assert "retry_scheduled" in statuses
    assert "succeeded" in statuses


def test_workspace_service_runs_export_as_background_job(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="job-export-1",
        name="Export Job",
        client="Client",
    )
    record.metadata["tenant_id"] = "tenant-a"
    record.metadata["organization_id"] = "org-a"
    service.save_record(record)

    out_path = str(tmp_path / "outputs" / f"{record.workspace_id}.atlaspkg")
    result = service.run_export_generation_job(
        workspace_id=record.workspace_id,
        out_path=out_path,
        actor_id="user-1",
    )

    payload = dict(result.get("result") or {}).get("payload") or {}
    assert result["status"] == "succeeded"
    assert str(payload.get("bundle_path") or "").endswith(".atlaspkg")
    assert Path(str(payload.get("bundle_path"))).exists()


def test_workspace_service_cancels_queued_background_job(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="job-cancel-1",
        name="Cancel Job",
        client="Client",
    )
    record.metadata["tenant_id"] = "tenant-a"
    record.metadata["organization_id"] = "org-a"
    service.save_record(record)

    request = JobRequest(
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
    created = service.manager.background_job_service.submit_job(
        project_id=record.workspace_id,
        request=request,
    )

    cancelled = service.cancel_background_job(
        record.workspace_id,
        job_id=str(created.get("job_id")),
        actor_id="user-1",
        reason="Cancelled in test",
    )

    assert cancelled["status"] == "cancelled"
    assert dict(cancelled.get("cancellation") or {}).get("requested") is True


def test_workspace_service_retries_failed_job_via_wrapper(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="job-retry-1",
        name="Retry Job",
        client="Client",
    )
    record.metadata["tenant_id"] = "tenant-a"
    record.metadata["organization_id"] = "org-a"
    service.save_record(record)

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
        retry_policy=JobRetryPolicy(max_attempts=2),
    )
    created = service.manager.background_job_service.submit_job(
        project_id=record.workspace_id,
        request=request,
    )
    failed = service.manager.background_job_service.run_job(
        project_id=record.workspace_id,
        job_id=str(created.get("job_id")),
        tenant_id="tenant-a",
        organization_id="org-a",
    )
    retried = service.retry_background_job(
        record.workspace_id,
        job_id=str(created.get("job_id")),
    )

    assert failed["status"] == "retry_scheduled"
    assert retried["status"] == "failed"
    assert retried["retry_available"] is False


def test_workspace_service_job_scope_enforced_on_listing(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="job-scope-1",
        name="Scope Job",
        client="Client",
    )
    record.metadata["tenant_id"] = "tenant-a"
    record.metadata["organization_id"] = "org-a"
    service.save_record(record)

    service.run_export_generation_job(
        workspace_id=record.workspace_id,
        out_path=str(tmp_path / "outputs" / "scope-test.atlaspkg"),
        actor_id="user-1",
    )

    visible = service.list_background_jobs(record.workspace_id)
    hidden = service.list_background_jobs(
        record.workspace_id,
        tenant_id="tenant-b",
        organization_id="org-a",
    )

    assert visible
    assert hidden == []

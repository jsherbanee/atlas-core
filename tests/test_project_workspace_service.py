from pathlib import Path
import json
import re

from atlas_core.domain import Project, ProjectLifecycleEvent, ProjectStatus
from atlas_core.domain import OrganizationRole
from atlas_core.services.project_workspace_service import (
    ProjectWorkspaceRecord,
    ProjectWorkspaceService,
)
from pypdf import PdfWriter


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

from pathlib import Path

from atlas_core.domain import Project, ProjectLifecycleEvent, ProjectStatus
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


def test_workspace_service_preview_bid_id_is_non_consuming(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    first_preview = service.preview_next_bid_id()
    second_preview = service.preview_next_bid_id()

    record = service.create_manual_record(
        name="Preview Project",
        client="Client",
    )

    assert first_preview == second_preview
    assert record.project.project_id == first_preview
    assert service.preview_next_bid_id() != first_preview


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

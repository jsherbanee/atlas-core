from pathlib import Path

from atlas_core.domain import Project
from atlas_core.repository import LocalProjectRepository


def _seed_project(
    repo: LocalProjectRepository, project_id: str = "project-001"
) -> Path:
    return repo.create(
        project_id,
        {
            "project_id": project_id,
            "name": "Atlas Project",
            "client": "Atlas Client",
            "status": "intake",
        },
        {
            "project_name": "Atlas Project",
            "owner": "Atlas Client",
            "project_number": project_id,
            "status": "intake",
            "lifecycle_stage": "intake",
            "atlas_version": "test",
            "pinned": False,
            "reference": False,
            "archived": False,
        },
        {
            "workspace_id": project_id,
            "project": {
                "project_id": project_id,
                "name": "Atlas Project",
                "client": "Atlas Client",
                "status": "intake",
            },
            "source_mode": "manual",
            "source_label": "Manual Project",
            "workspace_state": {},
        },
    )


def test_local_project_repository_creates_required_layout(tmp_path: Path) -> None:
    repo = LocalProjectRepository(tmp_path / "AtlasProjects")
    project_dir = _seed_project(repo)

    assert (project_dir / "project.json").exists()
    assert (project_dir / "metadata.json").exists()
    assert (project_dir / "workspace.json").exists()
    assert (project_dir / "documents" / "drawings").exists()
    assert (project_dir / "documents" / "specifications").exists()
    assert (project_dir / "review" / "knowledge_graph.json").exists()
    assert (project_dir / "history").exists()


def test_local_project_repository_management_actions(tmp_path: Path) -> None:
    repo = LocalProjectRepository(tmp_path / "AtlasProjects")
    _seed_project(repo, "project-001")

    repo.rename("project-001", "Renamed Project")
    repo.set_pinned("project-001", True)
    repo.set_reference("project-001", True)
    repo.archive("project-001", archived=True)

    project_payload, metadata_payload, workspace_payload, _ = repo.load("project-001")
    assert project_payload["name"] == "Renamed Project"
    assert metadata_payload["pinned"] is True
    assert metadata_payload["reference"] is True
    assert metadata_payload["archived"] is True
    assert workspace_payload["workspace_id"] == "project-001"

    repo.duplicate("project-001", "project-002", new_name="Duplicate")
    duplicated_project_payload, _, _, _ = repo.load("project-002")
    assert duplicated_project_payload["project_id"] == "project-002"
    assert duplicated_project_payload["name"] == "Duplicate"

    repo.delete("project-001")
    projects = repo.list_projects(include_archived=True)
    loaded_ids = {item[0] for item in projects}
    assert "project-001" not in loaded_ids
    assert "project-002" in loaded_ids


def test_project_domain_roundtrip_still_works() -> None:
    project = Project(project_id="id-1", name="Name", client="Client")
    restored = Project.from_dict(project.to_dict())
    assert restored.project_id == "id-1"

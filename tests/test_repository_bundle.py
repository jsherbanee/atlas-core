from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from atlas_core.repository.contracts import (
    ProjectRepository,
    RepositoryBundle,
    WorkspaceRepository,
)
from atlas_core.repository.local import (
    LocalAttachmentRepository,
    LocalDocumentRepository,
    LocalHistoryRepository,
    LocalJobRepository,
    LocalKnowledgeRepository,
    LocalProjectRepository,
    LocalReviewRepository,
    LocalWorkspaceRepository,
    build_local_repository_bundle,
)
from atlas_core.repository.project_manager import AtlasProjectManager


def _project_payload(project_id: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "name": "Atlas Project",
        "client": "Atlas Client",
        "status": "intake",
    }


def _metadata_payload(project_id: str) -> dict[str, Any]:
    return {
        "project_name": "Atlas Project",
        "owner": "Atlas Client",
        "project_number": project_id,
        "status": "intake",
        "lifecycle_stage": "intake",
        "atlas_version": "test",
        "pinned": False,
        "reference": False,
        "archived": False,
    }


def _workspace_payload(project_id: str) -> dict[str, Any]:
    return {
        "workspace_id": project_id,
        "project": _project_payload(project_id),
        "source_mode": "manual",
        "source_label": "Manual Project",
        "workspace_state": {},
    }


def test_local_repository_bundle_uses_shared_project_repository(tmp_path: Path) -> None:
    bundle = build_local_repository_bundle(tmp_path / "AtlasProjects")

    assert isinstance(bundle.project_repository, LocalProjectRepository)
    assert isinstance(bundle.workspace_repository, LocalWorkspaceRepository)
    assert isinstance(bundle.document_repository, LocalDocumentRepository)
    assert isinstance(bundle.review_repository, LocalReviewRepository)
    assert isinstance(bundle.knowledge_repository, LocalKnowledgeRepository)
    assert isinstance(bundle.history_repository, LocalHistoryRepository)
    assert isinstance(bundle.job_repository, LocalJobRepository)
    assert isinstance(bundle.attachment_repository, LocalAttachmentRepository)

    assert bundle.workspace_repository.project_repository is bundle.project_repository
    assert bundle.document_repository.project_repository is bundle.project_repository
    assert bundle.review_repository.project_repository is bundle.project_repository
    assert bundle.knowledge_repository.project_repository is bundle.project_repository
    assert bundle.history_repository.project_repository is bundle.project_repository
    assert bundle.job_repository.project_repository is bundle.project_repository
    assert bundle.attachment_repository.project_repository is bundle.project_repository
    assert bundle.attachment_repository.root == bundle.project_repository.root


def test_project_manager_default_construction_uses_local_adapters(
    tmp_path: Path,
) -> None:
    manager = AtlasProjectManager(tmp_path / "AtlasProjects")

    assert isinstance(manager.project_repository, LocalProjectRepository)
    assert isinstance(manager.workspace_repository, LocalWorkspaceRepository)
    assert isinstance(manager.document_repository, LocalDocumentRepository)
    assert isinstance(manager.review_repository, LocalReviewRepository)
    assert isinstance(manager.knowledge_repository, LocalKnowledgeRepository)
    assert isinstance(manager.history_repository, LocalHistoryRepository)
    assert isinstance(manager.job_repository, LocalJobRepository)
    assert isinstance(manager.attachment_repository, LocalAttachmentRepository)

    assert manager.repositories.project_repository is manager.project_repository
    assert manager.audit_service.history_repository is manager.history_repository
    assert manager.background_job_service.repository is manager.job_repository
    assert manager.attachment_service.repository is manager.attachment_repository


def test_project_manager_honors_explicit_repository_bundle() -> None:
    project_repository = cast(ProjectRepository, SimpleNamespace(name="project"))
    workspace_repository = cast(WorkspaceRepository, SimpleNamespace(name="workspace"))
    document_repository = SimpleNamespace(name="document")
    review_repository = SimpleNamespace(name="review")
    knowledge_repository = SimpleNamespace(name="knowledge")
    history_repository = SimpleNamespace(name="history")
    job_repository = SimpleNamespace(name="job")
    attachment_repository = SimpleNamespace(name="attachment")

    bundle = RepositoryBundle(
        project_repository=project_repository,
        workspace_repository=cast(WorkspaceRepository, workspace_repository),
        document_repository=cast(Any, document_repository),
        review_repository=cast(Any, review_repository),
        knowledge_repository=cast(Any, knowledge_repository),
        history_repository=cast(Any, history_repository),
        job_repository=cast(Any, job_repository),
        attachment_repository=cast(Any, attachment_repository),
    )

    manager = AtlasProjectManager(repositories=bundle)

    assert manager.repositories is bundle
    assert manager.project_repository is project_repository
    assert manager.workspace_repository is workspace_repository
    assert manager.document_repository is document_repository
    assert manager.review_repository is review_repository
    assert manager.knowledge_repository is knowledge_repository
    assert manager.history_repository is history_repository
    assert manager.job_repository is job_repository
    assert manager.attachment_repository is attachment_repository

    assert manager.audit_service.history_repository is history_repository
    assert manager.background_job_service.repository is job_repository
    assert manager.attachment_service.repository is attachment_repository


def test_project_manager_root_constructor_remains_compatible(tmp_path: Path) -> None:
    manager = AtlasProjectManager(root=tmp_path / "AtlasProjects")
    project_id = "project-001"

    manager.project_repository.create(
        project_id,
        _project_payload(project_id),
        _metadata_payload(project_id),
        _workspace_payload(project_id),
    )

    projects = manager.list_projects()

    assert [item["project_id"] for item in projects] == [project_id]
    assert manager.project_repository.project_location(project_id).endswith(project_id)

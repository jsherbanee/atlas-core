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
    build_local_tenant_repository_bundle,
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
    assert bundle.attachment_repository.root == bundle.tenant_root
    assert bundle.tenant_id is None
    assert bundle.tenant_root == tmp_path / "AtlasProjects"


def test_local_tenant_repository_bundle_uses_isolated_roots(tmp_path: Path) -> None:
    tenant_a = build_local_tenant_repository_bundle("tenant-a", tmp_path / "Atlas")
    tenant_b = build_local_tenant_repository_bundle("tenant-b", tmp_path / "Atlas")

    assert tenant_a.tenant_id == "tenant-a"
    assert tenant_b.tenant_id == "tenant-b"
    assert tenant_a.tenant_root == tmp_path / "Atlas" / "tenants" / "tenant-a"
    assert tenant_b.tenant_root == tmp_path / "Atlas" / "tenants" / "tenant-b"
    assert tenant_a.tenant_root != tenant_b.tenant_root


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
    assert manager.tenant_id is None
    assert manager.tenant_root == tmp_path / "AtlasProjects"


def test_project_manager_can_use_tenant_scoped_bundle(tmp_path: Path) -> None:
    bundle = build_local_tenant_repository_bundle("tenant-a", tmp_path / "Atlas")

    manager = AtlasProjectManager(repositories=bundle)

    assert manager.repositories is bundle
    assert manager.tenant_id == "tenant-a"
    assert manager.tenant_root == tmp_path / "Atlas" / "tenants" / "tenant-a"
    assert manager.tenant_root == bundle.tenant_root


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


def test_two_tenant_bundles_do_not_share_storage(tmp_path: Path) -> None:
    bundle_a = build_local_tenant_repository_bundle("tenant-a", tmp_path / "Atlas")
    bundle_b = build_local_tenant_repository_bundle("tenant-b", tmp_path / "Atlas")

    manager_a = AtlasProjectManager(repositories=bundle_a)
    manager_b = AtlasProjectManager(repositories=bundle_b)

    project_id = "project-001"
    project_payload = _project_payload(project_id)
    metadata_payload = _metadata_payload(project_id)
    workspace_a = _workspace_payload(project_id)
    workspace_b = _workspace_payload(project_id)

    manager_a.project_repository.create(
        project_id,
        project_payload,
        metadata_payload,
        workspace_a,
    )
    manager_b.project_repository.create(
        project_id,
        project_payload,
        metadata_payload,
        workspace_b,
    )

    manager_a.workspace_repository.save_state(project_id, {"tenant": "a"})
    manager_b.workspace_repository.save_state(project_id, {"tenant": "b"})

    manager_a.review_repository.save_artifact(
        project_id, "bid_package_review", {"tenant": "a"}
    )
    manager_b.review_repository.save_artifact(
        project_id, "bid_package_review", {"tenant": "b"}
    )
    manager_a.review_repository.save_transaction_document(
        project_id, {"document_id": "doc-1", "document_type": "estimate"}
    )
    manager_b.review_repository.save_transaction_document(
        project_id, {"document_id": "doc-1", "document_type": "estimate"}
    )
    manager_a.knowledge_repository.save_knowledge_graph(project_id, {"tenant": "a"})
    manager_b.knowledge_repository.save_knowledge_graph(project_id, {"tenant": "b"})
    manager_a.history_repository.append_event(project_id, "audit", {"tenant": "a"})
    manager_b.history_repository.append_event(project_id, "audit", {"tenant": "b"})
    manager_a.job_repository.save_job(project_id, {"job_id": "job-1", "tenant": "a"})
    manager_b.job_repository.save_job(project_id, {"job_id": "job-1", "tenant": "b"})

    attachment_a = {
        "attachment_id": "att-1",
        "tenant_id": "tenant-a",
        "organization_id": "org-1",
        "status": "active",
        "versions": [
            {
                "version_id": "v1",
                "version_number": 1,
                "metadata": {"file_hash": "hash-a", "size_bytes": 10},
                "storage_reference": "blobs/a.txt",
            }
        ],
    }
    attachment_b = {
        "attachment_id": "att-1",
        "tenant_id": "tenant-b",
        "organization_id": "org-1",
        "status": "active",
        "versions": [
            {
                "version_id": "v1",
                "version_number": 1,
                "metadata": {"file_hash": "hash-b", "size_bytes": 10},
                "storage_reference": "blobs/b.txt",
            }
        ],
    }
    manager_a.attachment_repository.save_attachment("tenant-a", "org-1", attachment_a)
    manager_b.attachment_repository.save_attachment("tenant-b", "org-1", attachment_b)
    blob_a = manager_a.attachment_repository.write_blob(
        "tenant-a",
        "org-1",
        attachment_id="att-1",
        version_id="v1",
        filename="a.txt",
        data=b"tenant-a",
    )
    blob_b = manager_b.attachment_repository.write_blob(
        "tenant-b",
        "org-1",
        attachment_id="att-1",
        version_id="v1",
        filename="b.txt",
        data=b"tenant-b",
    )

    assert manager_a.list_projects()[0]["project_id"] == project_id
    assert manager_b.list_projects()[0]["project_id"] == project_id
    assert manager_a.read_manifest(project_id)["project_id"] == project_id
    assert manager_b.read_manifest(project_id)["project_id"] == project_id
    assert manager_a.workspace_repository.load_state(project_id) == {"tenant": "a"}
    assert manager_b.workspace_repository.load_state(project_id) == {"tenant": "b"}
    assert manager_a.review_repository.load_artifact(
        project_id, "bid_package_review"
    ) == {"tenant": "a"}
    assert manager_b.review_repository.load_artifact(
        project_id, "bid_package_review"
    ) == {"tenant": "b"}
    assert (
        manager_a.review_repository.load_transaction_documents(project_id)[0][
            "document_id"
        ]
        == "doc-1"
    )
    assert (
        manager_b.review_repository.load_transaction_documents(project_id)[0][
            "document_id"
        ]
        == "doc-1"
    )
    assert manager_a.knowledge_repository.load_knowledge_graph(project_id) == {
        "tenant": "a"
    }
    assert manager_b.knowledge_repository.load_knowledge_graph(project_id) == {
        "tenant": "b"
    }
    assert (
        manager_a.history_repository.list_events(project_id)[0]["payload"]["tenant"]
        == "a"
    )
    assert (
        manager_b.history_repository.list_events(project_id)[0]["payload"]["tenant"]
        == "b"
    )
    assert manager_a.job_repository.list_jobs(project_id)[0]["tenant"] == "a"
    assert manager_b.job_repository.list_jobs(project_id)[0]["tenant"] == "b"
    attachment_a_loaded = manager_a.attachment_repository.load_attachment(
        "tenant-a", "org-1", "att-1"
    )
    attachment_b_loaded = manager_b.attachment_repository.load_attachment(
        "tenant-b", "org-1", "att-1"
    )
    assert attachment_a_loaded is not None
    assert attachment_b_loaded is not None
    assert attachment_a_loaded["tenant_id"] == "tenant-a"
    assert attachment_b_loaded["tenant_id"] == "tenant-b"
    assert (
        manager_a.attachment_repository.read_blob(
            "tenant-a", "org-1", storage_reference=blob_a
        )
        == b"tenant-a"
    )
    assert (
        manager_b.attachment_repository.read_blob(
            "tenant-b", "org-1", storage_reference=blob_b
        )
        == b"tenant-b"
    )


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

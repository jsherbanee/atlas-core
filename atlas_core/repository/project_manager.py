"""Atlas Project Manager orchestrating repository adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from atlas_core.repository.contracts import ProjectRepository, RepositoryBundle
from atlas_core.repository.local import (
    LocalAttachmentRepository,
    LocalDocumentRepository,
    LocalHistoryRepository,
    LocalJobRepository,
    LocalKnowledgeRepository,
    LocalReviewRepository,
    LocalWorkspaceRepository,
    build_local_repository_bundle,
    build_local_tenant_repository_bundle,
)
from atlas_core.services.background_job_service import BackgroundJobService
from atlas_core.services.attachment_service import AttachmentService
from atlas_core.services.immutable_audit_service import ImmutableAuditService


class AtlasProjectManager:
    """Single orchestration surface used by workspace services and UI."""

    def __init__(
        self,
        root: str | Path = "AtlasProjects",
        tenant_id: str | None = None,
        project_repository: ProjectRepository | None = None,
        repositories: RepositoryBundle | None = None,
    ) -> None:
        if repositories is None:
            if project_repository is None:
                if tenant_id is None:
                    repositories = build_local_repository_bundle(root)
                else:
                    repositories = build_local_tenant_repository_bundle(
                        tenant_id,
                        root,
                    )
            else:
                repositories = RepositoryBundle(
                    project_repository=project_repository,
                    workspace_repository=LocalWorkspaceRepository(project_repository),
                    document_repository=LocalDocumentRepository(project_repository),
                    review_repository=LocalReviewRepository(project_repository),
                    knowledge_repository=LocalKnowledgeRepository(project_repository),
                    history_repository=LocalHistoryRepository(project_repository),
                    job_repository=LocalJobRepository(project_repository),
                    attachment_repository=LocalAttachmentRepository(project_repository),
                    tenant_id=tenant_id,
                    tenant_root=getattr(project_repository, "root", None),
                )

        self.repositories = repositories
        self.tenant_id = repositories.tenant_id
        self.tenant_root = repositories.tenant_root
        self.project_repository = repositories.project_repository
        self.workspace_repository = repositories.workspace_repository
        self.document_repository = repositories.document_repository
        self.review_repository = repositories.review_repository
        self.knowledge_repository = repositories.knowledge_repository
        self.history_repository = repositories.history_repository
        self.job_repository = repositories.job_repository
        self.attachment_repository = repositories.attachment_repository
        self.commercial_repository = repositories.commercial_repository
        self.audit_service = ImmutableAuditService(self.history_repository)
        self.background_job_service = BackgroundJobService(
            repository=self.job_repository,
            audit_callback=self.record_audit_event,
        )
        self.attachment_service = AttachmentService(
            repository=self.attachment_repository,
            audit_callback=self.record_audit_event,
        )

    def log(self, project_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.history_repository.append_event(project_id, event_type, payload)

    def record_audit_event(
        self,
        *,
        project_id: str,
        action: str,
        actor_id: str,
        actor_type: str = "user",
        actor_display_name: str | None = None,
        tenant_id: str,
        organization_id: str,
        target_type: str,
        target_id: str,
        source: str = "atlas",
        correlation_id: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        permission_reference: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = self.audit_service.append_event(
            project_id=project_id,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_display_name=actor_display_name,
            tenant_id=tenant_id,
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            source=source,
            correlation_id=correlation_id,
            before=before,
            after=after,
            context=context,
            permission_reference=permission_reference,
        )
        return event.to_dict()

    def list_audit_events(
        self,
        *,
        project_id: str,
        tenant_id: str,
        organization_id: str,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        return self.audit_service.list_events(
            project_id=project_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            limit=limit,
        )

    def export_audit_events(
        self,
        *,
        project_id: str,
        tenant_id: str,
        organization_id: str,
        limit: int = 5000,
    ) -> dict[str, Any]:
        return self.audit_service.export_events(
            project_id=project_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            limit=limit,
        )

    def list_projects(self, include_archived: bool = False) -> list[dict[str, Any]]:
        rows = self.project_repository.list_projects(include_archived=include_archived)
        return [
            {
                "project_id": project_id,
                "project": project_payload,
                "metadata": metadata_payload,
                "workspace": workspace_payload,
                "storage_location": storage_location,
            }
            for (
                project_id,
                project_payload,
                metadata_payload,
                workspace_payload,
                storage_location,
            ) in rows
        ]

    def read_manifest(self, project_id: str) -> dict[str, Any]:
        return self.project_repository.read_manifest(project_id)

    def refresh_manifest(self, project_id: str) -> dict[str, Any]:
        return self.project_repository.refresh_manifest(project_id)

    def export_project_bundle(self, project_id: str, out_path: str) -> str:
        return self.project_repository.export_bundle(project_id, out_path)

    def import_project_bundle(self, bundle_path: str) -> str:
        return self.project_repository.import_bundle(bundle_path)

    def health_check(self, project_id: str) -> dict[str, Any]:
        return self.project_repository.health_check(project_id)

    def allocate_bid_id(self, year: int | None = None) -> str:
        return self.project_repository.allocate_bid_id(year=year)

    def preview_next_bid_id(self, year: int | None = None) -> str:
        return self.project_repository.peek_next_bid_id(year=year)

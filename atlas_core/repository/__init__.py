"""Atlas Project Repository interfaces and local adapters."""

from atlas_core.repository.contracts import (
    AttachmentRepository,
    CommercialRepository,
    DocumentRepository,
    HistoryRepository,
    JobRepository,
    KnowledgeRepository,
    RepositoryBundle,
    ProjectRepository,
    ReviewRepository,
    WorkspaceRepository,
)
from atlas_core.repository.local import (
    LocalAttachmentRepository,
    LocalCommercialRepository,
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
from atlas_core.repository.models import ProjectManifest, RepositoryHealthReport
from atlas_core.repository.project_manager import AtlasProjectManager

__all__ = [
    "DocumentRepository",
    "AttachmentRepository",
    "HistoryRepository",
    "JobRepository",
    "KnowledgeRepository",
    "CommercialRepository",
    "RepositoryBundle",
    "ProjectRepository",
    "ReviewRepository",
    "WorkspaceRepository",
    "LocalDocumentRepository",
    "LocalAttachmentRepository",
    "LocalHistoryRepository",
    "LocalJobRepository",
    "LocalKnowledgeRepository",
    "LocalCommercialRepository",
    "LocalProjectRepository",
    "LocalReviewRepository",
    "LocalWorkspaceRepository",
    "build_local_repository_bundle",
    "build_local_tenant_repository_bundle",
    "ProjectManifest",
    "RepositoryHealthReport",
    "AtlasProjectManager",
]

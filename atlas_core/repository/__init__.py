"""Atlas Project Repository interfaces and local adapters."""

from atlas_core.repository.contracts import (
    AttachmentRepository,
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
    LocalDocumentRepository,
    LocalHistoryRepository,
    LocalJobRepository,
    LocalKnowledgeRepository,
    LocalProjectRepository,
    LocalReviewRepository,
    LocalWorkspaceRepository,
    build_local_repository_bundle,
)
from atlas_core.repository.models import ProjectManifest, RepositoryHealthReport
from atlas_core.repository.project_manager import AtlasProjectManager

__all__ = [
    "DocumentRepository",
    "AttachmentRepository",
    "HistoryRepository",
    "JobRepository",
    "KnowledgeRepository",
    "RepositoryBundle",
    "ProjectRepository",
    "ReviewRepository",
    "WorkspaceRepository",
    "LocalDocumentRepository",
    "LocalAttachmentRepository",
    "LocalHistoryRepository",
    "LocalJobRepository",
    "LocalKnowledgeRepository",
    "LocalProjectRepository",
    "LocalReviewRepository",
    "LocalWorkspaceRepository",
    "build_local_repository_bundle",
    "ProjectManifest",
    "RepositoryHealthReport",
    "AtlasProjectManager",
]

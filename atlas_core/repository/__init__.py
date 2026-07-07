"""Atlas Project Repository interfaces and local adapters."""

from atlas_core.repository.contracts import (
    DocumentRepository,
    HistoryRepository,
    KnowledgeRepository,
    ProjectRepository,
    ReviewRepository,
    WorkspaceRepository,
)
from atlas_core.repository.local import (
    LocalDocumentRepository,
    LocalHistoryRepository,
    LocalKnowledgeRepository,
    LocalProjectRepository,
    LocalReviewRepository,
    LocalWorkspaceRepository,
)
from atlas_core.repository.models import ProjectManifest, RepositoryHealthReport
from atlas_core.repository.project_manager import AtlasProjectManager

__all__ = [
    "DocumentRepository",
    "HistoryRepository",
    "KnowledgeRepository",
    "ProjectRepository",
    "ReviewRepository",
    "WorkspaceRepository",
    "LocalDocumentRepository",
    "LocalHistoryRepository",
    "LocalKnowledgeRepository",
    "LocalProjectRepository",
    "LocalReviewRepository",
    "LocalWorkspaceRepository",
    "ProjectManifest",
    "RepositoryHealthReport",
    "AtlasProjectManager",
]

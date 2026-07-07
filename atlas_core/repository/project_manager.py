"""Atlas Project Manager orchestrating repository adapters."""

from __future__ import annotations

from typing import Any

from atlas_core.repository.local import (
    LocalDocumentRepository,
    LocalHistoryRepository,
    LocalKnowledgeRepository,
    LocalProjectRepository,
    LocalReviewRepository,
    LocalWorkspaceRepository,
)


class AtlasProjectManager:
    """Single orchestration surface used by workspace services and UI."""

    def __init__(self, root: str = "AtlasProjects") -> None:
        self.project_repository = LocalProjectRepository(root)
        self.workspace_repository = LocalWorkspaceRepository(self.project_repository)
        self.document_repository = LocalDocumentRepository(self.project_repository)
        self.review_repository = LocalReviewRepository(self.project_repository)
        self.knowledge_repository = LocalKnowledgeRepository(self.project_repository)
        self.history_repository = LocalHistoryRepository(self.project_repository)

    def log(self, project_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.history_repository.append_event(project_id, event_type, payload)

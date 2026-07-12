"""Repository contracts for Atlas Project persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

JsonDict = dict[str, Any]


class ProjectRepository(ABC):
    """Persistence contract for project-level records and lifecycle actions."""

    @abstractmethod
    def create(
        self,
        project_id: str,
        project_payload: JsonDict,
        metadata_payload: JsonDict,
        workspace_payload: JsonDict,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def save(
        self,
        project_id: str,
        project_payload: JsonDict,
        metadata_payload: JsonDict,
        workspace_payload: JsonDict,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def load(self, project_ref: str) -> tuple[JsonDict, JsonDict, JsonDict, str]:
        raise NotImplementedError

    @abstractmethod
    def list_projects(
        self,
        include_archived: bool = False,
    ) -> list[tuple[str, JsonDict, JsonDict, JsonDict, str]]:
        raise NotImplementedError

    @abstractmethod
    def rename(self, project_id: str, new_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def archive(self, project_id: str, archived: bool = True) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, project_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def duplicate(
        self,
        project_id: str,
        new_project_id: str,
        new_name: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def set_pinned(self, project_id: str, pinned: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_reference(self, project_id: str, reference: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def project_location(self, project_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def read_manifest(self, project_id: str) -> JsonDict:
        raise NotImplementedError

    @abstractmethod
    def refresh_manifest(self, project_id: str) -> JsonDict:
        raise NotImplementedError

    @abstractmethod
    def export_bundle(self, project_id: str, out_path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def import_bundle(self, bundle_path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def health_check(self, project_id: str) -> JsonDict:
        raise NotImplementedError

    @abstractmethod
    def allocate_bid_id(self, year: int | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def peek_next_bid_id(self, year: int | None = None) -> str:
        raise NotImplementedError


class WorkspaceRepository(ABC):
    """Persistence contract for workspace-view and UI state."""

    @abstractmethod
    def load_state(self, project_id: str) -> JsonDict:
        raise NotImplementedError

    @abstractmethod
    def save_state(self, project_id: str, state: JsonDict) -> None:
        raise NotImplementedError


class DocumentRepository(ABC):
    """Persistence contract for project documents and import intake."""

    @abstractmethod
    def import_uploads(
        self,
        project_id: str,
        uploaded_files: list[tuple[str, bytes]],
    ) -> JsonDict:
        raise NotImplementedError


class ReviewRepository(ABC):
    """Persistence contract for review result artifacts."""

    @abstractmethod
    def save_artifact(
        self, project_id: str, artifact_name: str, payload: JsonDict
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_artifact(self, project_id: str, artifact_name: str) -> JsonDict | None:
        raise NotImplementedError


class KnowledgeRepository(ABC):
    """Persistence contract for graph/knowledge artifacts."""

    @abstractmethod
    def save_knowledge_graph(self, project_id: str, payload: JsonDict) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_knowledge_graph(self, project_id: str) -> JsonDict | None:
        raise NotImplementedError

    @abstractmethod
    def save_engineering_intelligence(self, project_id: str, payload: JsonDict) -> None:
        raise NotImplementedError


class HistoryRepository(ABC):
    """Persistence contract for simple project timeline events."""

    @abstractmethod
    def append_event(self, project_id: str, event_type: str, payload: JsonDict) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, project_id: str, limit: int = 100) -> list[JsonDict]:
        raise NotImplementedError

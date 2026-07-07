"""Local filesystem-backed Atlas project repositories."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
import shutil

from atlas_core.repository.contracts import (
    DocumentRepository,
    HistoryRepository,
    JsonDict,
    KnowledgeRepository,
    ProjectRepository,
    ReviewRepository,
    WorkspaceRepository,
)
from atlas_core.services.document_intake_service import (
    DocumentIntakeService,
    UploadedIntakeFile,
)

_PROJECT_FILE = "project.json"
_METADATA_FILE = "metadata.json"
_WORKSPACE_FILE = "workspace.json"
_HISTORY_FILE = "history/events.jsonl"
_REVIEW_FILE_BY_ARTIFACT = {
    "bid_package_review": "bid_package_review.json",
    "readiness": "readiness.json",
    "estimator_brief": "estimator_brief.json",
    "engineering_intelligence": "engineering_intelligence.json",
    "labor_estimate": "labor_estimate.json",
    "revision_comparison": "revision_comparison.json",
    "rfi_candidates": "rfi_candidates.json",
    "knowledge_graph": "knowledge_graph.json",
}


class LocalProjectRepository(ProjectRepository):
    """Project repository persisted under AtlasProjects/<project_id>/..."""

    def __init__(self, root: str | Path = "AtlasProjects") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        project_id: str,
        project_payload: JsonDict,
        metadata_payload: JsonDict,
        workspace_payload: JsonDict,
    ) -> Path:
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            raise FileExistsError(f"Project already exists: {project_id}")

        self._ensure_project_layout(project_dir)
        self._write_project(project_dir, project_payload)
        self._write_metadata(project_dir, metadata_payload)
        self._write_workspace(project_dir, workspace_payload)
        return project_dir

    def save(
        self,
        project_id: str,
        project_payload: JsonDict,
        metadata_payload: JsonDict,
        workspace_payload: JsonDict,
    ) -> Path:
        project_dir = self._project_dir(project_id)
        self._ensure_project_layout(project_dir)
        self._write_project(project_dir, project_payload)
        self._write_metadata(project_dir, metadata_payload)
        self._write_workspace(project_dir, workspace_payload)
        return project_dir

    def load(
        self, project_ref: str | Path
    ) -> tuple[JsonDict, JsonDict, JsonDict, Path]:
        project_dir = self._resolve_project_dir(project_ref)
        project_payload = self._read_json(project_dir / _PROJECT_FILE)
        metadata_payload = self._read_json(project_dir / _METADATA_FILE)
        workspace_payload = self._read_json(project_dir / _WORKSPACE_FILE)
        return project_payload, metadata_payload, workspace_payload, project_dir

    def list_projects(
        self,
        include_archived: bool = False,
    ) -> list[tuple[str, JsonDict, JsonDict, JsonDict, Path]]:
        rows: list[tuple[str, JsonDict, JsonDict, JsonDict, Path]] = []
        for child in sorted(self.root.iterdir()):
            if not child.is_dir():
                continue
            if (
                not (child / _PROJECT_FILE).exists()
                or not (child / _WORKSPACE_FILE).exists()
            ):
                continue
            try:
                project_payload = self._read_json(child / _PROJECT_FILE)
                metadata_payload = self._read_json(child / _METADATA_FILE)
                workspace_payload = self._read_json(child / _WORKSPACE_FILE)
            except Exception:
                continue

            if not include_archived and bool(metadata_payload.get("archived", False)):
                continue

            project_id = str(project_payload.get("project_id") or child.name)
            rows.append(
                (
                    project_id,
                    project_payload,
                    metadata_payload,
                    workspace_payload,
                    child,
                )
            )

        return rows

    def rename(self, project_id: str, new_name: str) -> None:
        project_payload, metadata_payload, workspace_payload, project_dir = self.load(
            project_id
        )
        project_payload["name"] = new_name
        metadata_payload["project_name"] = new_name
        metadata_payload["last_modified"] = _utc_now()
        workspace_payload["updated_at"] = _utc_now()
        self._write_project(project_dir, project_payload)
        self._write_metadata(project_dir, metadata_payload)
        self._write_workspace(project_dir, workspace_payload)

    def archive(self, project_id: str, archived: bool = True) -> None:
        _, metadata_payload, workspace_payload, project_dir = self.load(project_id)
        metadata_payload["archived"] = archived
        metadata_payload["status"] = (
            "archived" if archived else str(metadata_payload.get("status") or "intake")
        )
        metadata_payload["last_modified"] = _utc_now()
        workspace_payload["updated_at"] = _utc_now()
        self._write_metadata(project_dir, metadata_payload)
        self._write_workspace(project_dir, workspace_payload)

    def delete(self, project_id: str) -> None:
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)

    def duplicate(
        self,
        project_id: str,
        new_project_id: str,
        new_name: str | None = None,
    ) -> Path:
        _, _, _, source_dir = self.load(project_id)
        target_dir = self._project_dir(new_project_id)
        if target_dir.exists():
            raise FileExistsError(f"Target project exists: {new_project_id}")

        shutil.copytree(source_dir, target_dir)
        project_payload = self._read_json(target_dir / _PROJECT_FILE)
        metadata_payload = self._read_json(target_dir / _METADATA_FILE)
        workspace_payload = self._read_json(target_dir / _WORKSPACE_FILE)

        project_payload["project_id"] = new_project_id
        project_payload["name"] = (
            new_name or f"{project_payload.get('name', project_id)} Copy"
        )

        metadata_payload["project_number"] = new_project_id
        metadata_payload["project_name"] = (
            new_name or f"{metadata_payload.get('project_name', project_id)} Copy"
        )
        metadata_payload["created_at"] = _utc_now()
        metadata_payload["last_opened"] = None
        metadata_payload["last_modified"] = _utc_now()
        metadata_payload["pinned"] = False
        metadata_payload["reference"] = False
        metadata_payload["archived"] = False

        workspace_payload["workspace_id"] = new_project_id
        workspace_payload["created_at"] = _utc_now()
        workspace_payload["updated_at"] = _utc_now()
        workspace_payload["last_opened_at"] = None

        self._write_project(target_dir, project_payload)
        self._write_metadata(target_dir, metadata_payload)
        self._write_workspace(target_dir, workspace_payload)
        return target_dir

    def set_pinned(self, project_id: str, pinned: bool) -> None:
        _, metadata_payload, _, project_dir = self.load(project_id)
        metadata_payload["pinned"] = pinned
        metadata_payload["last_modified"] = _utc_now()
        self._write_metadata(project_dir, metadata_payload)

    def set_reference(self, project_id: str, reference: bool) -> None:
        _, metadata_payload, _, project_dir = self.load(project_id)
        metadata_payload["reference"] = reference
        metadata_payload["last_modified"] = _utc_now()
        self._write_metadata(project_dir, metadata_payload)

    def project_path(self, project_id: str) -> Path:
        return self._project_dir(project_id)

    def _resolve_project_dir(self, project_ref: str | Path) -> Path:
        ref = Path(project_ref)
        if (
            ref.exists()
            and ref.is_file()
            and ref.name
            in {
                _PROJECT_FILE,
                _METADATA_FILE,
                _WORKSPACE_FILE,
            }
        ):
            return ref.parent

        if ref.exists() and ref.is_dir() and (ref / _PROJECT_FILE).exists():
            return ref

        return self._project_dir(str(project_ref))

    def _project_dir(self, project_id: str) -> Path:
        return self.root / _slugify(project_id)

    def _ensure_project_layout(self, project_dir: Path) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "intake").mkdir(parents=True, exist_ok=True)
        docs_root = project_dir / "documents"
        for folder in [
            "drawings",
            "specifications",
            "schedules",
            "addenda",
            "images",
            "other",
        ]:
            (docs_root / folder).mkdir(parents=True, exist_ok=True)

        review_root = project_dir / "review"
        review_root.mkdir(parents=True, exist_ok=True)
        for file_name in _REVIEW_FILE_BY_ARTIFACT.values():
            path = review_root / file_name
            if not path.exists():
                path.write_text("{}\n", encoding="utf-8")

        (project_dir / "exports").mkdir(parents=True, exist_ok=True)
        (project_dir / "history").mkdir(parents=True, exist_ok=True)
        (project_dir / "cache").mkdir(parents=True, exist_ok=True)

    def _read_json(self, path: Path) -> JsonDict:
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
            if isinstance(payload, dict):
                return payload
            return {}

    def _write_project(self, project_dir: Path, payload: JsonDict) -> None:
        self._write_json(project_dir / _PROJECT_FILE, payload)

    def _write_metadata(self, project_dir: Path, payload: JsonDict) -> None:
        self._write_json(project_dir / _METADATA_FILE, payload)

    def _write_workspace(self, project_dir: Path, payload: JsonDict) -> None:
        self._write_json(project_dir / _WORKSPACE_FILE, payload)

    @staticmethod
    def _write_json(path: Path, payload: JsonDict) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, sort_keys=True)


class LocalWorkspaceRepository(WorkspaceRepository):
    """Workspace UI state persisted inside workspace.json."""

    def __init__(self, project_repository: LocalProjectRepository) -> None:
        self.project_repository = project_repository

    def load_state(self, project_id: str) -> JsonDict:
        _, _, workspace_payload, _ = self.project_repository.load(project_id)
        state = workspace_payload.get("workspace_state")
        if isinstance(state, dict):
            return dict(state)
        return {}

    def save_state(self, project_id: str, state: JsonDict) -> None:
        project_payload, metadata_payload, workspace_payload, project_dir = (
            self.project_repository.load(project_id)
        )
        workspace_payload["workspace_state"] = dict(state)
        workspace_payload["updated_at"] = _utc_now()
        self.project_repository._write_project(project_dir, project_payload)
        self.project_repository._write_metadata(project_dir, metadata_payload)
        self.project_repository._write_workspace(project_dir, workspace_payload)


class LocalDocumentRepository(DocumentRepository):
    """Document import persisted in project intake and documents folders."""

    def __init__(self, project_repository: LocalProjectRepository) -> None:
        self.project_repository = project_repository

    def import_uploads(
        self,
        project_id: str,
        uploaded_files: list[tuple[str, bytes]],
    ) -> JsonDict:
        if not uploaded_files:
            raise ValueError("No uploaded files to import")

        _, _, _, project_dir = self.project_repository.load(project_id)
        uploads = [
            UploadedIntakeFile(name=name, data=data) for name, data in uploaded_files
        ]

        intake_root = project_dir / "intake"
        intake_result = DocumentIntakeService().build_session_package_from_uploads(
            uploaded_files=uploads,
            uploads_root=intake_root,
            session_id="latest",
        )

        documents_root = project_dir / "documents"
        source_root = intake_result.package_path
        for folder in ["drawings", "specifications", "schedules", "addenda", "images"]:
            self._copy_group(source_root / folder, documents_root / folder)

        self._copy_group(source_root / "unsupported", documents_root / "other")

        metadata_source = source_root / "metadata.json"
        if metadata_source.exists():
            shutil.copy2(metadata_source, project_dir / "metadata.json")

        return {
            "intake_snapshot_path": str(intake_result.snapshot_path),
            "package_location": str(documents_root),
            "warnings": list(intake_result.warnings),
            "import_summary": dict(intake_result.import_summary),
        }

    @staticmethod
    def _copy_group(source: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        if not source.exists() or not source.is_dir():
            return

        for file_path in source.rglob("*"):
            if not file_path.is_file():
                continue
            destination = target / file_path.name
            if destination.exists():
                destination = (
                    target / f"{file_path.stem}-{_utc_stamp()}{file_path.suffix}"
                )
            shutil.copy2(file_path, destination)


class LocalReviewRepository(ReviewRepository):
    """Review artifact persistence under project review/ folder."""

    def __init__(self, project_repository: LocalProjectRepository) -> None:
        self.project_repository = project_repository

    def save_artifact(
        self, project_id: str, artifact_name: str, payload: JsonDict
    ) -> None:
        _, _, _, project_dir = self.project_repository.load(project_id)
        file_name = _REVIEW_FILE_BY_ARTIFACT.get(artifact_name)
        if file_name is None:
            file_name = f"{_slugify(artifact_name)}.json"

        path = project_dir / "review" / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, sort_keys=True)

    def load_artifact(self, project_id: str, artifact_name: str) -> JsonDict | None:
        _, _, _, project_dir = self.project_repository.load(project_id)
        file_name = _REVIEW_FILE_BY_ARTIFACT.get(artifact_name)
        if file_name is None:
            file_name = f"{_slugify(artifact_name)}.json"

        path = project_dir / "review" / file_name
        if not path.exists():
            return None

        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
            if isinstance(payload, dict):
                return payload
            return None


class LocalKnowledgeRepository(KnowledgeRepository):
    """Knowledge persistence under project review/ folder."""

    def __init__(self, project_repository: LocalProjectRepository) -> None:
        self.project_repository = project_repository

    def save_knowledge_graph(self, project_id: str, payload: JsonDict) -> None:
        LocalReviewRepository(self.project_repository).save_artifact(
            project_id, "knowledge_graph", payload
        )

    def load_knowledge_graph(self, project_id: str) -> JsonDict | None:
        return LocalReviewRepository(self.project_repository).load_artifact(
            project_id,
            "knowledge_graph",
        )

    def save_engineering_intelligence(self, project_id: str, payload: JsonDict) -> None:
        LocalReviewRepository(self.project_repository).save_artifact(
            project_id,
            "engineering_intelligence",
            payload,
        )


class LocalHistoryRepository(HistoryRepository):
    """Simple timeline event persistence using JSONL history file."""

    def __init__(self, project_repository: LocalProjectRepository) -> None:
        self.project_repository = project_repository

    def append_event(self, project_id: str, event_type: str, payload: JsonDict) -> None:
        _, _, _, project_dir = self.project_repository.load(project_id)
        history_file = project_dir / _HISTORY_FILE
        history_file.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": _utc_now(),
            "event_type": event_type,
            "payload": dict(payload),
        }
        with history_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, sort_keys=True) + "\n")

    def list_events(self, project_id: str, limit: int = 100) -> list[JsonDict]:
        _, _, _, project_dir = self.project_repository.load(project_id)
        history_file = project_dir / _HISTORY_FILE
        if not history_file.exists():
            return []

        rows: list[JsonDict] = []
        with history_file.open(encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    rows.append(parsed)

        rows.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
        return rows[:limit]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "project"

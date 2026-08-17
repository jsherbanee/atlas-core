"""Local filesystem-backed Atlas project repositories."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any
import zipfile

from atlas_core import __version__
from atlas_core.repository.contracts import (
    AttachmentRepository,
    DocumentRepository,
    HistoryRepository,
    JobRepository,
    JsonDict,
    KnowledgeRepository,
    ProjectRepository,
    ReviewRepository,
    WorkspaceRepository,
)
from atlas_core.repository.models import ProjectManifest, RepositoryHealthReport
from atlas_core.services.document_intake_service import (
    DocumentIntakeService,
    cleanup_duplicate_document_variants,
    UploadedIntakeFile,
)

_PROJECT_FILE = "project.json"
_METADATA_FILE = "metadata.json"
_WORKSPACE_FILE = "workspace.json"
_MANIFEST_FILE = "project_manifest.json"
_HISTORY_FILE = "history/events.jsonl"
_JOBS_FILE = "jobs/jobs.jsonl"
_ATTACHMENTS_ROOT = ".atlas_attachments"
_ATTACHMENTS_FILE = "attachments.jsonl"
_ATTACHMENT_LINKS_FILE = "links.jsonl"
_ATTACHMENT_ACTIVITY_FILE = "activity.jsonl"
_BID_SEQUENCE_FILE = ".atlas_bid_id_sequence.json"
_SCHEMA_VERSION = "1.0"
_STORAGE_VERSION = "1.0"
_REQUIRED_TOP_LEVEL_DIRS = [
    "intake",
    "documents",
    "review",
    "exports",
    "history",
    "jobs",
    "cache",
]
_REQUIRED_TOP_LEVEL_FILES = [
    _PROJECT_FILE,
    _METADATA_FILE,
    _WORKSPACE_FILE,
    _MANIFEST_FILE,
]
_DOCUMENT_FOLDERS = [
    "drawings",
    "specifications",
    "schedules",
    "addenda",
    "images",
    "other",
]
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
    ) -> str:
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            raise FileExistsError(f"Project already exists: {project_id}")

        self._ensure_project_layout(project_dir)
        self._write_project(project_dir, project_payload)
        self._write_metadata(project_dir, metadata_payload)
        self._write_workspace(project_dir, workspace_payload)
        self._observe_bid_id(project_id)
        self._write_manifest(project_dir)
        return str(project_dir)

    def save(
        self,
        project_id: str,
        project_payload: JsonDict,
        metadata_payload: JsonDict,
        workspace_payload: JsonDict,
    ) -> str:
        project_dir = self._project_dir(project_id)
        self._ensure_project_layout(project_dir)
        self._write_project(project_dir, project_payload)
        self._write_metadata(project_dir, metadata_payload)
        self._write_workspace(project_dir, workspace_payload)
        self._observe_bid_id(project_id)
        self._write_manifest(project_dir)
        return str(project_dir)

    def load(self, project_ref: str) -> tuple[JsonDict, JsonDict, JsonDict, str]:
        project_dir = self._resolve_project_dir(project_ref)
        project_payload = self._read_json(project_dir / _PROJECT_FILE)
        metadata_payload = self._read_json(project_dir / _METADATA_FILE)
        workspace_payload = self._read_json(project_dir / _WORKSPACE_FILE)
        return project_payload, metadata_payload, workspace_payload, str(project_dir)

    def list_projects(
        self,
        include_archived: bool = False,
    ) -> list[tuple[str, JsonDict, JsonDict, JsonDict, str]]:
        rows: list[tuple[str, JsonDict, JsonDict, JsonDict, str]] = []
        for child in sorted(self.root.iterdir()):
            if not child.is_dir():
                continue
            # Require the authoritative project payloads to be present
            # A filesystem folder should not be considered a project unless
            # it contains the required repository files. This prevents
            # stray directories (for example a top-level `documents` folder)
            # from being enumerated as Atlas projects merely because they
            # exist beneath the projects root.
            if (
                not (child / _PROJECT_FILE).exists()
                or not (child / _WORKSPACE_FILE).exists()
                or not (child / _METADATA_FILE).exists()
                or not (child / _MANIFEST_FILE).exists()
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
                    str(child),
                )
            )

        return rows

    def rename(self, project_id: str, new_name: str) -> None:
        project_payload, metadata_payload, workspace_payload, location = self.load(
            project_id
        )
        project_dir = Path(location)
        project_payload["name"] = new_name
        metadata_payload["project_name"] = new_name
        metadata_payload["last_modified"] = _utc_now()
        workspace_payload["updated_at"] = _utc_now()
        self._write_project(project_dir, project_payload)
        self._write_metadata(project_dir, metadata_payload)
        self._write_workspace(project_dir, workspace_payload)
        self._write_manifest(project_dir)

    def archive(self, project_id: str, archived: bool = True) -> None:
        _, metadata_payload, workspace_payload, location = self.load(project_id)
        project_dir = Path(location)
        metadata_payload["archived"] = archived
        metadata_payload["status"] = (
            "archived" if archived else str(metadata_payload.get("status") or "intake")
        )
        metadata_payload["last_modified"] = _utc_now()
        workspace_payload["updated_at"] = _utc_now()
        self._write_metadata(project_dir, metadata_payload)
        self._write_workspace(project_dir, workspace_payload)
        self._write_manifest(project_dir)

    def delete(self, project_id: str) -> None:
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)

    def duplicate(
        self,
        project_id: str,
        new_project_id: str,
        new_name: str | None = None,
    ) -> str:
        _, _, _, source_location = self.load(project_id)
        source_dir = Path(source_location)
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
        self._write_manifest(target_dir)
        return str(target_dir)

    def set_pinned(self, project_id: str, pinned: bool) -> None:
        _, metadata_payload, _, location = self.load(project_id)
        project_dir = Path(location)
        metadata_payload["pinned"] = pinned
        metadata_payload["last_modified"] = _utc_now()
        self._write_metadata(project_dir, metadata_payload)
        self._write_manifest(project_dir)

    def set_reference(self, project_id: str, reference: bool) -> None:
        _, metadata_payload, _, location = self.load(project_id)
        project_dir = Path(location)
        metadata_payload["reference"] = reference
        metadata_payload["last_modified"] = _utc_now()
        self._write_metadata(project_dir, metadata_payload)
        self._write_manifest(project_dir)

    def project_location(self, project_id: str) -> str:
        return str(self._project_dir(project_id))

    def read_manifest(self, project_id: str) -> JsonDict:
        _, _, _, location = self.load(project_id)
        project_dir = Path(location)
        manifest_path = project_dir / _MANIFEST_FILE
        if not manifest_path.exists():
            return self.refresh_manifest(project_id)
        return self._read_json(manifest_path)

    def refresh_manifest(self, project_id: str) -> JsonDict:
        _, _, _, location = self.load(project_id)
        project_dir = Path(location)
        self._write_manifest(project_dir)
        return self._read_json(project_dir / _MANIFEST_FILE)

    def export_bundle(self, project_id: str, out_path: str) -> str:
        _, _, _, location = self.load(project_id)
        project_dir = Path(location)
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix != ".atlaspkg":
            out = out.with_suffix(".atlaspkg")

        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(project_dir.rglob("*")):
                if not path.is_file():
                    continue
                arcname = Path(project_dir.name) / path.relative_to(project_dir)
                archive.write(path, arcname=str(arcname))

        return str(out)

    def import_bundle(self, bundle_path: str) -> str:
        source = Path(bundle_path)
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Bundle not found: {source}")

        with tempfile.TemporaryDirectory(prefix="atlas-bundle-import-") as tmp_dir:
            tmp_root = Path(tmp_dir)
            with zipfile.ZipFile(source, "r") as archive:
                archive.extractall(tmp_root)

            candidates = [
                path.parent for path in tmp_root.rglob(_PROJECT_FILE) if path.is_file()
            ]
            if not candidates:
                raise ValueError("No project.json found in bundle")
            if len(candidates) > 1:
                raise ValueError("Bundle contains multiple projects; expected one")

            project_dir = candidates[0]
            project_payload = self._read_json(project_dir / _PROJECT_FILE)
            project_id = str(project_payload.get("project_id") or project_dir.name)
            target_dir = self._project_dir(project_id)
            if target_dir.exists():
                raise FileExistsError(f"Project already exists: {project_id}")

            shutil.move(str(project_dir), str(target_dir))

        self._ensure_project_layout(target_dir)
        self._observe_bid_id(project_id)
        self._write_manifest(target_dir)
        return project_id

    def allocate_bid_id(self, year: int | None = None) -> str:
        target_year = year or datetime.now(UTC).year
        state = self._read_bid_sequence_state()
        years = dict(state.get("years") or {})
        current = int(years.get(str(target_year), 0) or 0)

        while True:
            current += 1
            candidate = f"BID-{target_year:04d}-{current:04d}"
            if not self._project_dir(candidate).exists():
                years[str(target_year)] = current
                self._write_bid_sequence_state({"years": years})
                return candidate

    def peek_next_bid_id(self, year: int | None = None) -> str:
        target_year = year or datetime.now(UTC).year
        state = self._read_bid_sequence_state()
        years = dict(state.get("years") or {})
        current = int(years.get(str(target_year), 0) or 0)

        while True:
            current += 1
            candidate = f"BID-{target_year:04d}-{current:04d}"
            if not self._project_dir(candidate).exists():
                return candidate

    def health_check(self, project_id: str) -> JsonDict:
        _, _, _, location = self.load(project_id)
        project_dir = Path(location)

        errors: list[str] = []
        warnings: list[str] = []
        missing_files: list[str] = []
        orphaned_files: list[str] = []
        repair_recommendations: list[str] = []

        for name in _REQUIRED_TOP_LEVEL_FILES:
            if not (project_dir / name).exists():
                missing_files.append(name)
                errors.append(f"Missing required file: {name}")

        for name in _REQUIRED_TOP_LEVEL_DIRS:
            if not (project_dir / name).exists():
                missing_files.append(name)
                errors.append(f"Missing required folder: {name}")

        _ = self._safe_read_json(project_dir / _PROJECT_FILE, errors)
        metadata_payload = self._safe_read_json(project_dir / _METADATA_FILE, errors)
        _ = self._safe_read_json(project_dir / _WORKSPACE_FILE, errors)
        manifest_payload = self._safe_read_json(project_dir / _MANIFEST_FILE, errors)

        schema_version = str(manifest_payload.get("schema_version") or "")
        if schema_version and not schema_version.startswith("1."):
            errors.append(f"Incompatible schema_version: {schema_version}")

        referenced_documents = list(metadata_payload.get("referenced_documents") or [])
        documents_root = project_dir / "documents"
        for item in referenced_documents:
            candidate = documents_root / str(item)
            if not candidate.exists():
                warnings.append(f"Referenced document missing: {item}")

        history_path = project_dir / _HISTORY_FILE
        if history_path.exists():
            with history_path.open(encoding="utf-8") as file:
                for index, line in enumerate(file, start=1):
                    value = line.strip()
                    if not value:
                        continue
                    try:
                        parsed = json.loads(value)
                    except json.JSONDecodeError:
                        errors.append(f"History line {index} is not valid JSON")
                        continue
                    if not isinstance(parsed, dict):
                        errors.append(f"History line {index} must be a JSON object")
        else:
            warnings.append("History file is missing; project has no recorded events")

        for review_file in (project_dir / "review").glob("*.json"):
            _ = self._safe_read_json(review_file, errors)

        allowed_top = {
            *_REQUIRED_TOP_LEVEL_FILES,
            *_REQUIRED_TOP_LEVEL_DIRS,
        }
        for child in sorted(project_dir.iterdir()):
            if child.name in allowed_top:
                continue
            orphaned_files.append(str(child.relative_to(project_dir)))

        if missing_files:
            repair_recommendations.append(
                "Run project manifest refresh and recreate missing repository layout."
            )
        if errors:
            repair_recommendations.append(
                "Fix invalid JSON files and re-run atlas project-health."
            )
        if not errors and warnings:
            repair_recommendations.append(
                "Project is usable; address warnings to improve portability."
            )

        status = "healthy"
        if errors:
            status = "error"
        elif warnings:
            status = "warning"

        report = RepositoryHealthReport(
            status=status,
            errors=errors,
            warnings=warnings,
            missing_files=missing_files,
            orphaned_files=orphaned_files,
            repair_recommendations=repair_recommendations,
            validated_at=_utc_now(),
        )
        return report.to_dict()

    def _resolve_project_dir(self, project_ref: str) -> Path:
        ref = Path(project_ref)
        if (
            ref.exists()
            and ref.is_file()
            and ref.name
            in {_PROJECT_FILE, _METADATA_FILE, _WORKSPACE_FILE, _MANIFEST_FILE}
        ):
            return ref.parent

        if ref.exists() and ref.is_dir() and (ref / _PROJECT_FILE).exists():
            return ref

        return self._project_dir(project_ref)

    def _read_bid_sequence_state(self) -> JsonDict:
        path = self.root / _BID_SEQUENCE_FILE
        if not path.exists():
            return {"years": {}}
        payload = self._read_json(path)
        years = payload.get("years")
        if not isinstance(years, dict):
            return {"years": {}}
        normalized: dict[str, int] = {}
        for raw_year, raw_value in years.items():
            year_text = str(raw_year).strip()
            if not year_text.isdigit():
                continue
            try:
                normalized[year_text] = int(raw_value)
            except Exception:
                continue
        return {"years": normalized}

    def _write_bid_sequence_state(self, payload: JsonDict) -> None:
        path = self.root / _BID_SEQUENCE_FILE
        self._write_json(path, payload)

    def _observe_bid_id(self, project_id: str) -> None:
        matched = re.match(r"^BID-(\d{4})-(\d+)$", project_id.strip(), flags=re.I)
        if matched is None:
            return

        year = matched.group(1)
        sequence = int(matched.group(2))
        state = self._read_bid_sequence_state()
        years = dict(state.get("years") or {})
        current = int(years.get(year, 0) or 0)
        if sequence > current:
            years[year] = sequence
            self._write_bid_sequence_state({"years": years})

    def _project_dir(self, project_id: str) -> Path:
        return self.root / _slugify(project_id)

    def _ensure_project_layout(self, project_dir: Path) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "intake").mkdir(parents=True, exist_ok=True)
        docs_root = project_dir / "documents"
        for folder in _DOCUMENT_FOLDERS:
            (docs_root / folder).mkdir(parents=True, exist_ok=True)

        review_root = project_dir / "review"
        review_root.mkdir(parents=True, exist_ok=True)
        for file_name in _REVIEW_FILE_BY_ARTIFACT.values():
            path = review_root / file_name
            if not path.exists():
                path.write_text("{}\n", encoding="utf-8")

        (project_dir / "exports").mkdir(parents=True, exist_ok=True)
        (project_dir / "history").mkdir(parents=True, exist_ok=True)
        (project_dir / "jobs").mkdir(parents=True, exist_ok=True)
        (project_dir / "cache").mkdir(parents=True, exist_ok=True)

    def _read_json(self, path: Path) -> JsonDict:
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
            if isinstance(payload, dict):
                return payload
            return {}

    @staticmethod
    def _safe_read_json(path: Path, errors: list[str]) -> JsonDict:
        if not path.exists():
            return {}
        try:
            with path.open(encoding="utf-8") as file:
                payload = json.load(file)
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON at {path.name}: {exc}")
            return {}

        if not isinstance(payload, dict):
            errors.append(f"Expected object JSON at {path.name}")
            return {}

        return payload

    def _write_project(self, project_dir: Path, payload: JsonDict) -> None:
        self._write_json(project_dir / _PROJECT_FILE, payload)

    def _write_metadata(self, project_dir: Path, payload: JsonDict) -> None:
        self._write_json(project_dir / _METADATA_FILE, payload)

    def _write_workspace(self, project_dir: Path, payload: JsonDict) -> None:
        self._write_json(project_dir / _WORKSPACE_FILE, payload)

    def _write_manifest(self, project_dir: Path) -> None:
        project_payload = self._read_json(project_dir / _PROJECT_FILE)
        metadata_payload = self._read_json(project_dir / _METADATA_FILE)
        workspace_payload = self._read_json(project_dir / _WORKSPACE_FILE)

        document_counts = {
            folder: self._count_files(project_dir / "documents" / folder)
            for folder in _DOCUMENT_FOLDERS
        }

        review_counts: dict[str, int] = {}
        for artifact_name, file_name in _REVIEW_FILE_BY_ARTIFACT.items():
            review_counts[artifact_name] = self._artifact_presence_count(
                project_dir / "review" / file_name
            )

        intelligence_counts = {
            "engineering_intelligence": review_counts.get(
                "engineering_intelligence",
                0,
            ),
            "knowledge_graph": review_counts.get("knowledge_graph", 0),
        }

        manifest = ProjectManifest(
            project_id=str(project_payload.get("project_id") or project_dir.name),
            project_name=str(
                project_payload.get("name")
                or metadata_payload.get("project_name")
                or project_dir.name
            ),
            owner=str(
                project_payload.get("client")
                or metadata_payload.get("owner")
                or "Unknown"
            ),
            status=str(
                metadata_payload.get("status")
                or project_payload.get("status")
                or "intake"
            ),
            lifecycle_stage=str(
                metadata_payload.get("lifecycle_stage")
                or metadata_payload.get("status")
                or project_payload.get("status")
                or "intake"
            ),
            created_at=str(
                metadata_payload.get("created_at")
                or workspace_payload.get("created_at")
                or _utc_now()
            ),
            updated_at=str(
                workspace_payload.get("updated_at")
                or metadata_payload.get("last_modified")
                or _utc_now()
            ),
            last_opened_at=(
                str(
                    metadata_payload.get("last_opened")
                    or workspace_payload.get("last_opened_at")
                    or ""
                )
                or None
            ),
            atlas_version=str(metadata_payload.get("atlas_version") or __version__),
            schema_version=_SCHEMA_VERSION,
            storage_version=_STORAGE_VERSION,
            document_counts=document_counts,
            review_artifact_counts=review_counts,
            intelligence_artifact_counts=intelligence_counts,
            history_event_count=self._history_count(project_dir / _HISTORY_FILE),
            checksum_summary=self._checksum_summary(project_dir),
        )

        self._write_json(project_dir / _MANIFEST_FILE, manifest.to_dict())

    @staticmethod
    def _count_files(folder: Path) -> int:
        if not folder.exists() or not folder.is_dir():
            return 0
        return sum(1 for path in folder.rglob("*") if path.is_file())

    @staticmethod
    def _artifact_presence_count(path: Path) -> int:
        if not path.exists() or not path.is_file():
            return 0
        try:
            with path.open(encoding="utf-8") as file:
                payload = json.load(file)
        except json.JSONDecodeError:
            return 0
        if isinstance(payload, dict):
            return 1 if len(payload) > 0 else 0
        if isinstance(payload, list):
            return 1 if len(payload) > 0 else 0
        return 0

    @staticmethod
    def _history_count(path: Path) -> int:
        if not path.exists() or not path.is_file():
            return 0
        count = 0
        with path.open(encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    count += 1
        return count

    @staticmethod
    def _checksum_summary(project_dir: Path) -> dict[str, str]:
        checksums: dict[str, str] = {}
        for name in [_PROJECT_FILE, _METADATA_FILE, _WORKSPACE_FILE]:
            path = project_dir / name
            if path.exists() and path.is_file():
                checksums[name] = _sha1_file(path)

        checksums["review"] = _sha1_tree(project_dir / "review")
        checksums["documents"] = _sha1_tree(project_dir / "documents")
        checksums["history"] = _sha1_tree(project_dir / "history")
        checksums["jobs"] = _sha1_tree(project_dir / "jobs")
        return checksums

    @staticmethod
    def _write_json(path: Path, payload: JsonDict) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, sort_keys=True)


class LocalWorkspaceRepository(WorkspaceRepository):
    """Workspace UI state persisted inside workspace.json."""

    def __init__(self, project_repository: ProjectRepository) -> None:
        self.project_repository = project_repository

    def load_state(self, project_id: str) -> JsonDict:
        _, _, workspace_payload, _ = self.project_repository.load(project_id)
        state = workspace_payload.get("workspace_state")
        if isinstance(state, dict):
            return dict(state)
        return {}

    def save_state(self, project_id: str, state: JsonDict) -> None:
        _, _, workspace_payload, location = self.project_repository.load(project_id)
        workspace_payload["workspace_state"] = dict(state)
        workspace_payload["updated_at"] = _utc_now()
        self.project_repository._write_workspace(  # type: ignore[attr-defined]
            Path(location),
            workspace_payload,
        )


class LocalDocumentRepository(DocumentRepository):
    """Document import persisted in project intake and documents folders."""

    def __init__(self, project_repository: ProjectRepository) -> None:
        self.project_repository = project_repository

    def import_uploads(
        self,
        project_id: str,
        uploaded_files: list[tuple[str, bytes]],
    ) -> JsonDict:
        if not uploaded_files:
            raise ValueError("No uploaded files to import")

        _, _, _, location = self.project_repository.load(project_id)
        project_dir = Path(location)
        uploads = [
            UploadedIntakeFile(name=name, data=data) for name, data in uploaded_files
        ]

        intake_root = project_dir / "intake"
        intake_result = DocumentIntakeService().build_session_package_from_uploads(
            uploaded_files=uploads,
            uploads_root=intake_root,
            session_id="latest",
            project_id=project_id,
        )

        documents_root = project_dir / "documents"
        source_root = intake_result.package_path
        for folder in ["drawings", "specifications", "schedules", "addenda", "images"]:
            self._copy_group(source_root / folder, documents_root / folder)

        self._copy_group(source_root / "unsupported", documents_root / "other")

        self.project_repository.refresh_manifest(project_id)

        return {
            "intake_snapshot_path": str(intake_result.snapshot_path),
            "package_location": str(documents_root),
            "warnings": list(intake_result.warnings),
            "import_summary": dict(intake_result.import_summary),
        }

    @staticmethod
    def _file_sha1(path: Path) -> str:
        digest = hashlib.sha1()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _copy_group(source: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        if not source.exists() or not source.is_dir():
            return

        for file_path in source.rglob("*"):
            if not file_path.is_file():
                continue
            destination = target / file_path.name
            if destination.exists() and LocalDocumentRepository._file_sha1(
                destination
            ) == LocalDocumentRepository._file_sha1(file_path):
                continue
            shutil.copy2(file_path, destination)

        cleanup_duplicate_document_variants(target)


class LocalReviewRepository(ReviewRepository):
    """Review artifact persistence under project review/ folder."""

    def __init__(self, project_repository: ProjectRepository) -> None:
        self.project_repository = project_repository

    def save_artifact(
        self,
        project_id: str,
        artifact_name: str,
        payload: JsonDict,
    ) -> None:
        _, _, _, location = self.project_repository.load(project_id)
        project_dir = Path(location)
        file_name = _REVIEW_FILE_BY_ARTIFACT.get(artifact_name)
        if file_name is None:
            file_name = f"{_slugify(artifact_name)}.json"

        path = project_dir / "review" / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, sort_keys=True)

        self.project_repository.refresh_manifest(project_id)

    def load_artifact(self, project_id: str, artifact_name: str) -> JsonDict | None:
        _, _, _, location = self.project_repository.load(project_id)
        project_dir = Path(location)
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

    def __init__(self, project_repository: ProjectRepository) -> None:
        self.project_repository = project_repository

    def save_knowledge_graph(self, project_id: str, payload: JsonDict) -> None:
        LocalReviewRepository(self.project_repository).save_artifact(
            project_id,
            "knowledge_graph",
            payload,
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

    def __init__(self, project_repository: ProjectRepository) -> None:
        self.project_repository = project_repository

    def append_event(self, project_id: str, event_type: str, payload: JsonDict) -> None:
        _, _, _, location = self.project_repository.load(project_id)
        project_dir = Path(location)
        history_file = project_dir / _HISTORY_FILE
        history_file.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": _utc_now(),
            "event_type": event_type,
            "payload": dict(payload),
        }
        with history_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, sort_keys=True) + "\n")

        self.project_repository.refresh_manifest(project_id)

    def list_events(self, project_id: str, limit: int = 100) -> list[JsonDict]:
        _, _, _, location = self.project_repository.load(project_id)
        project_dir = Path(location)
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


class LocalJobRepository(JobRepository):
    """Local JSONL-backed storage for background jobs."""

    def __init__(self, project_repository: ProjectRepository) -> None:
        self.project_repository = project_repository

    def save_job(self, project_id: str, job_payload: JsonDict) -> None:
        rows = self.list_jobs(project_id, limit=10000)
        job_id = str(job_payload.get("job_id") or "").strip()
        if not job_id:
            raise ValueError("job_id is required")

        retained = [
            dict(item)
            for item in rows
            if str(item.get("job_id") or "").strip() != job_id
        ]
        retained.append(dict(job_payload))
        retained.sort(
            key=lambda item: (
                str(item.get("created_at") or ""),
                str(item.get("job_id") or ""),
            )
        )

        _, _, _, location = self.project_repository.load(project_id)
        project_dir = Path(location)
        jobs_file = project_dir / _JOBS_FILE
        jobs_file.parent.mkdir(parents=True, exist_ok=True)
        with jobs_file.open("w", encoding="utf-8") as file:
            for item in retained:
                file.write(json.dumps(item, sort_keys=True) + "\n")

        self.project_repository.refresh_manifest(project_id)

    def load_job(self, project_id: str, job_id: str) -> JsonDict | None:
        target_id = str(job_id or "").strip()
        if not target_id:
            return None
        for item in self.list_jobs(project_id, limit=10000):
            if str(item.get("job_id") or "").strip() == target_id:
                return dict(item)
        return None

    def list_jobs(self, project_id: str, limit: int = 200) -> list[JsonDict]:
        _, _, _, location = self.project_repository.load(project_id)
        project_dir = Path(location)
        jobs_file = project_dir / _JOBS_FILE
        if not jobs_file.exists():
            return []

        rows: list[JsonDict] = []
        with jobs_file.open(encoding="utf-8") as file:
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

        rows.sort(
            key=lambda item: (
                str(item.get("created_at") or ""),
                str(item.get("job_id") or ""),
            ),
            reverse=True,
        )
        return rows[:limit]


class LocalAttachmentRepository(AttachmentRepository):
    """Local tenant-scoped attachment repository with separate metadata and blob storage."""

    def __init__(self, project_repository: ProjectRepository) -> None:
        self.project_repository = project_repository
        root = getattr(project_repository, "root", Path("AtlasProjects"))
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_attachment(
        self,
        tenant_id: str,
        organization_id: str,
        attachment_payload: JsonDict,
    ) -> None:
        rows = self.list_attachments(
            tenant_id,
            organization_id,
            include_archived=True,
            limit=20000,
        )
        attachment_id = self._required_text(
            "attachment_id", attachment_payload.get("attachment_id")
        )
        retained = [
            dict(item)
            for item in rows
            if self._safe_text(item.get("attachment_id")) != attachment_id
        ]
        retained.append(dict(attachment_payload))
        retained.sort(
            key=lambda item: (
                self._safe_text(item.get("created_at")),
                self._safe_text(item.get("attachment_id")),
            )
        )
        self._write_jsonl(
            self._scope_dir(tenant_id, organization_id) / _ATTACHMENTS_FILE,
            retained,
        )

    def load_attachment(
        self,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
    ) -> JsonDict | None:
        target = self._safe_text(attachment_id)
        if not target:
            return None
        for item in self.list_attachments(
            tenant_id,
            organization_id,
            include_archived=True,
            limit=20000,
        ):
            if self._safe_text(item.get("attachment_id")) == target:
                return dict(item)
        return None

    def list_attachments(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        include_archived: bool = True,
        limit: int = 1000,
    ) -> list[JsonDict]:
        rows = self._read_jsonl(
            self._scope_dir(tenant_id, organization_id) / _ATTACHMENTS_FILE
        )
        if not include_archived:
            rows = [
                item
                for item in rows
                if self._safe_text(dict(item).get("status"), "active") != "archived"
            ]
        rows.sort(
            key=lambda item: (
                self._safe_text(item.get("created_at")),
                self._safe_text(item.get("attachment_id")),
            ),
            reverse=True,
        )
        return rows[: max(1, int(limit))]

    def find_attachment_by_hash(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        file_hash: str,
        size_bytes: int,
    ) -> JsonDict | None:
        target_hash = self._safe_text(file_hash).lower()
        target_size = int(size_bytes)
        for item in self.list_attachments(
            tenant_id,
            organization_id,
            include_archived=True,
            limit=20000,
        ):
            versions = list(dict(item).get("versions") or [])
            if not versions:
                continue
            latest = sorted(
                [dict(row) for row in versions if isinstance(row, dict)],
                key=lambda row: int(row.get("version_number") or 0),
            )[-1]
            metadata = dict(latest.get("metadata") or {})
            if (
                self._safe_text(metadata.get("file_hash")).lower() == target_hash
                and int(metadata.get("size_bytes") or 0) == target_size
            ):
                return dict(item)
        return None

    def write_blob(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        attachment_id: str,
        version_id: str,
        filename: str,
        data: bytes,
    ) -> str:
        safe_name = self._safe_blob_filename(filename)
        blob_dir = (
            self._scope_dir(tenant_id, organization_id)
            / "blobs"
            / self._safe_path_segment(attachment_id)
            / self._safe_path_segment(version_id)
        )
        blob_dir.mkdir(parents=True, exist_ok=True)
        path = blob_dir / safe_name
        with path.open("wb") as file:
            file.write(bytes(data or b""))
        return str(path.relative_to(self._scope_dir(tenant_id, organization_id)))

    def read_blob(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        storage_reference: str,
    ) -> bytes:
        scope = self._scope_dir(tenant_id, organization_id)
        reference = self._safe_text(storage_reference)
        if not reference:
            raise FileNotFoundError("storage_reference is required")
        path = (scope / reference).resolve()
        if scope.resolve() not in path.parents and path != scope.resolve():
            raise ValueError("storage_reference is outside tenant scope")
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("attachment blob was not found")
        return path.read_bytes()

    def save_link(
        self,
        tenant_id: str,
        organization_id: str,
        link_payload: JsonDict,
    ) -> None:
        rows = self.list_links(
            tenant_id,
            organization_id,
            include_inactive=True,
            limit=50000,
        )
        link_id = self._required_text("link_id", link_payload.get("link_id"))
        retained = [
            dict(item)
            for item in rows
            if self._safe_text(item.get("link_id")) != link_id
        ]
        retained.append(dict(link_payload))
        retained.sort(
            key=lambda item: (
                self._safe_text(item.get("linked_at")),
                self._safe_text(item.get("link_id")),
            )
        )
        self._write_jsonl(
            self._scope_dir(tenant_id, organization_id) / _ATTACHMENT_LINKS_FILE,
            retained,
        )

    def list_links(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        attachment_id: str | None = None,
        object_type: str | None = None,
        object_id: str | None = None,
        include_inactive: bool = False,
        limit: int = 5000,
    ) -> list[JsonDict]:
        target_attachment = self._safe_text(attachment_id)
        target_object_type = self._safe_text(object_type)
        target_object_id = self._safe_text(object_id)
        rows = self._read_jsonl(
            self._scope_dir(tenant_id, organization_id) / _ATTACHMENT_LINKS_FILE
        )
        filtered: list[JsonDict] = []
        for item in rows:
            if (
                target_attachment
                and self._safe_text(item.get("attachment_id")) != target_attachment
            ):
                continue
            if (
                target_object_type
                and self._safe_text(item.get("object_type")) != target_object_type
            ):
                continue
            if (
                target_object_id
                and self._safe_text(item.get("object_id")) != target_object_id
            ):
                continue
            if not include_inactive and not bool(item.get("active", True)):
                continue
            filtered.append(dict(item))
        filtered.sort(
            key=lambda item: (
                self._safe_text(item.get("linked_at")),
                self._safe_text(item.get("link_id")),
            ),
            reverse=True,
        )
        return filtered[: max(1, int(limit))]

    def save_activity(
        self,
        tenant_id: str,
        organization_id: str,
        activity_payload: JsonDict,
    ) -> None:
        rows = self.list_activity(
            tenant_id,
            organization_id,
            attachment_id=None,
            limit=100000,
        )
        activity_id = self._required_text(
            "activity_id", activity_payload.get("activity_id")
        )
        retained = [
            dict(item)
            for item in rows
            if self._safe_text(item.get("activity_id")) != activity_id
        ]
        retained.append(dict(activity_payload))
        retained.sort(
            key=lambda item: (
                self._safe_text(item.get("occurred_at")),
                self._safe_text(item.get("activity_id")),
            )
        )
        self._write_jsonl(
            self._scope_dir(tenant_id, organization_id) / _ATTACHMENT_ACTIVITY_FILE,
            retained,
        )

    def list_activity(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        attachment_id: str | None = None,
        limit: int = 200,
    ) -> list[JsonDict]:
        target = self._safe_text(attachment_id)
        rows = self._read_jsonl(
            self._scope_dir(tenant_id, organization_id) / _ATTACHMENT_ACTIVITY_FILE
        )
        filtered = [
            dict(item)
            for item in rows
            if (not target) or self._safe_text(item.get("attachment_id")) == target
        ]
        filtered.sort(
            key=lambda item: (
                self._safe_text(item.get("occurred_at")),
                self._safe_text(item.get("activity_id")),
            ),
            reverse=True,
        )
        return filtered[: max(1, int(limit))]

    def _scope_dir(self, tenant_id: str, organization_id: str) -> Path:
        tenant = self._safe_path_segment(tenant_id)
        organization = self._safe_path_segment(organization_id)
        path = self.root / _ATTACHMENTS_ROOT / tenant / organization
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _safe_path_segment(value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("path segment cannot be blank")
        cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", normalized)
        cleaned = cleaned.strip("._")
        if not cleaned:
            raise ValueError("path segment cannot be blank")
        return cleaned

    @staticmethod
    def _safe_blob_filename(filename: str) -> str:
        normalized = str(filename or "").strip()
        if not normalized:
            raise ValueError("filename is required")
        if "/" in normalized or "\\" in normalized or ".." in normalized:
            raise ValueError("unsafe filename")
        return normalized

    @staticmethod
    def _required_text(field_name: str, value: Any) -> str:
        normalized = LocalAttachmentRepository._safe_text(value)
        if not normalized:
            raise ValueError(f"{field_name} is required")
        return normalized

    @staticmethod
    def _safe_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        if not isinstance(value, str):
            value = str(value)
        normalized = value.strip()
        return normalized or default

    @staticmethod
    def _read_jsonl(path: Path) -> list[JsonDict]:
        if not path.exists() or not path.is_file():
            return []
        rows: list[JsonDict] = []
        with path.open(encoding="utf-8") as file:
            for line in file:
                value = line.strip()
                if not value:
                    continue
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    rows.append(parsed)
        return rows

    @staticmethod
    def _write_jsonl(path: Path, rows: list[JsonDict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            for item in rows:
                file.write(json.dumps(dict(item), sort_keys=True) + "\n")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "project"


def _sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha1_tree(path: Path) -> str:
    if not path.exists() or not path.is_dir():
        return ""

    digest = hashlib.sha1()
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        digest.update(str(file_path.relative_to(path)).encode("utf-8"))
        digest.update(_sha1_file(file_path).encode("utf-8"))
    return digest.hexdigest()

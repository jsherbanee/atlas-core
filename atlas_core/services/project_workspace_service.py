"""Local file-backed project workspace persistence for Atlas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
import re
from pathlib import Path
from typing import Any

from atlas_core.domain import Project


@dataclass
class ProjectWorkspaceRecord:
    workspace_id: str
    project: Project
    source_mode: str = "manual"
    source_label: str = "Manual Project"
    source_path: str | None = None
    intake_snapshot_path: str | None = None
    package_location: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    import_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    project_profile: dict[str, Any] = field(default_factory=dict)
    review_summary: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_opened_at: str | None = None

    def __post_init__(self) -> None:
        self.workspace_id = self._normalize_required_text(
            "workspace_id", self.workspace_id
        )
        self.source_mode = self._normalize_required_text("source_mode", self.source_mode)
        self.source_label = self._normalize_required_text(
            "source_label", self.source_label
        )
        self.source_path = self._normalize_optional_text(self.source_path)
        self.intake_snapshot_path = self._normalize_optional_text(
            self.intake_snapshot_path
        )
        self.package_location = self._normalize_optional_text(self.package_location)
        self.warnings = [self._normalize_required_text("warning", warning) for warning in self.warnings]
        self.metadata = dict(self.metadata)
        self.import_summary = dict(self.import_summary)
        self.project_profile = dict(self.project_profile)
        self.review_summary = dict(self.review_summary)
        self.created_at = self._normalize_optional_text(self.created_at) or datetime.now(
            UTC
        ).isoformat()
        self.updated_at = self._normalize_optional_text(self.updated_at) or self.created_at
        self.last_opened_at = self._normalize_optional_text(self.last_opened_at)

        if not isinstance(self.project, Project):
            self.project = Project.from_dict(self.project)

    @property
    def project_id(self) -> str:
        return self.project.project_id

    def touch(self) -> None:
        now = datetime.now(UTC).isoformat()
        self.last_opened_at = now
        self.updated_at = now

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "project": self.project.to_dict(),
            "source_mode": self.source_mode,
            "source_label": self.source_label,
            "source_path": self.source_path,
            "intake_snapshot_path": self.intake_snapshot_path,
            "package_location": self.package_location,
            "metadata": dict(self.metadata),
            "import_summary": dict(self.import_summary),
            "warnings": list(self.warnings),
            "project_profile": dict(self.project_profile),
            "review_summary": dict(self.review_summary),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_opened_at": self.last_opened_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectWorkspaceRecord":
        project_payload = payload.get("project") or {}
        return cls(
            workspace_id=str(payload.get("workspace_id") or project_payload.get("project_id") or ""),
            project=Project.from_dict(project_payload),
            source_mode=str(payload.get("source_mode") or "manual"),
            source_label=str(payload.get("source_label") or "Manual Project"),
            source_path=payload.get("source_path"),
            intake_snapshot_path=payload.get("intake_snapshot_path"),
            package_location=payload.get("package_location"),
            metadata=dict(payload.get("metadata") or {}),
            import_summary=dict(payload.get("import_summary") or {}),
            warnings=[str(item) for item in list(payload.get("warnings") or [])],
            project_profile=dict(payload.get("project_profile") or {}),
            review_summary=dict(payload.get("review_summary") or {}),
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            last_opened_at=payload.get("last_opened_at"),
        )

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            return None

        normalized = value.strip()
        return normalized or None


class ProjectWorkspaceService:
    def __init__(self, workspace_root: str | Path = "outputs/project_workspaces") -> None:
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def list_recent_workspaces(self, limit: int = 10) -> list[ProjectWorkspaceRecord]:
        records: list[ProjectWorkspaceRecord] = []
        for workspace_file in self.workspace_root.glob("*/workspace.json"):
            try:
                records.append(self.load_record(workspace_file))
            except Exception:
                continue

        records.sort(key=self._sort_key, reverse=True)
        return records[:limit]

    def load_record(self, workspace_path: str | Path) -> ProjectWorkspaceRecord:
        path = Path(workspace_path)
        if path.is_dir():
            path = path / "workspace.json"

        with path.open(encoding="utf-8") as file:
            payload = json.load(file)

        return ProjectWorkspaceRecord.from_dict(payload)

    def save_record(self, record: ProjectWorkspaceRecord) -> Path:
        record.touch()
        workspace_dir = self._workspace_dir(record.workspace_id)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        workspace_path = workspace_dir / "workspace.json"
        with workspace_path.open("w", encoding="utf-8") as file:
            json.dump(record.to_dict(), file, indent=2, sort_keys=True)

        return workspace_path

    def create_manual_record(
        self,
        *,
        project_id: str,
        name: str,
        client: str,
        location: str | None = None,
        bid_date: str | None = None,
        status: Any = None,
    ) -> ProjectWorkspaceRecord:
        project = Project(
            project_id=project_id,
            name=name,
            client=client,
            location=location,
            bid_date=bid_date,
            status=status or "intake",
        )
        return ProjectWorkspaceRecord(
            workspace_id=project.project_id,
            project=project,
            source_mode="manual",
            source_label="Manual Project",
        )

    def _workspace_dir(self, workspace_id: str) -> Path:
        return self.workspace_root / self._slugify(workspace_id)

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized or "workspace"

    @staticmethod
    def _sort_key(record: ProjectWorkspaceRecord) -> str:
        return record.last_opened_at or record.updated_at or record.created_at

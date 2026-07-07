"""Project repository-backed workspace persistence for Atlas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atlas_core import __version__
from atlas_core.domain import Project, ProjectStatus
from atlas_core.repository import AtlasProjectManager


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
    workspace_state: dict[str, Any] = field(default_factory=dict)
    pinned: bool = False
    is_reference: bool = False
    archived: bool = False
    project_root: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_opened_at: str | None = None

    def __post_init__(self) -> None:
        self.workspace_id = self._normalize_required_text(
            "workspace_id",
            self.workspace_id,
        )
        self.source_mode = self._normalize_required_text(
            "source_mode", self.source_mode
        )
        self.source_label = self._normalize_required_text(
            "source_label",
            self.source_label,
        )
        self.source_path = self._normalize_optional_text(self.source_path)
        self.intake_snapshot_path = self._normalize_optional_text(
            self.intake_snapshot_path
        )
        self.package_location = self._normalize_optional_text(self.package_location)
        self.warnings = [
            self._normalize_required_text("warning", warning)
            for warning in self.warnings
        ]
        self.metadata = dict(self.metadata)
        self.import_summary = dict(self.import_summary)
        self.project_profile = dict(self.project_profile)
        self.review_summary = dict(self.review_summary)
        self.workspace_state = dict(self.workspace_state)
        self.project_root = self._normalize_optional_text(self.project_root)
        self.created_at = (
            self._normalize_optional_text(self.created_at)
            or datetime.now(UTC).isoformat()
        )
        self.updated_at = (
            self._normalize_optional_text(self.updated_at) or self.created_at
        )
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
            "workspace_state": dict(self.workspace_state),
            "pinned": self.pinned,
            "is_reference": self.is_reference,
            "archived": self.archived,
            "project_root": self.project_root,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_opened_at": self.last_opened_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectWorkspaceRecord":
        project_payload = payload.get("project") or {}
        return cls(
            workspace_id=str(
                payload.get("workspace_id") or project_payload.get("project_id") or ""
            ),
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
            workspace_state=dict(payload.get("workspace_state") or {}),
            pinned=bool(payload.get("pinned", False)),
            is_reference=bool(payload.get("is_reference", False)),
            archived=bool(payload.get("archived", False)),
            project_root=payload.get("project_root"),
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
    def __init__(self, workspace_root: str | Path = "AtlasProjects") -> None:
        self.workspace_root = Path(workspace_root)
        self.manager = AtlasProjectManager(str(self.workspace_root))

    def list_recent_workspaces(self, limit: int = 10) -> list[ProjectWorkspaceRecord]:
        records = self.list_workspaces(include_archived=False)
        return records[:limit]

    def list_workspaces(
        self,
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[ProjectWorkspaceRecord]:
        rows = self.manager.project_repository.list_projects(
            include_archived=include_archived
        )
        records = [
            self._from_repository_payloads(
                project_payload,
                metadata_payload,
                workspace_payload,
                storage_location,
            )
            for (
                _,
                project_payload,
                metadata_payload,
                workspace_payload,
                storage_location,
            ) in rows
        ]
        records.sort(key=self._sort_key, reverse=True)
        if limit is None:
            return records
        return records[:limit]

    def list_pinned_workspaces(self, limit: int = 20) -> list[ProjectWorkspaceRecord]:
        return [record for record in self.list_workspaces() if record.pinned][:limit]

    def list_reference_workspaces(
        self,
        include_archived: bool = False,
    ) -> list[ProjectWorkspaceRecord]:
        return [
            record
            for record in self.list_workspaces(include_archived=include_archived)
            if record.is_reference
        ]

    def load_record(self, workspace_path: str | Path) -> ProjectWorkspaceRecord:
        project_payload, metadata_payload, workspace_payload, project_dir = (
            self.manager.project_repository.load(str(workspace_path))
        )
        return self._from_repository_payloads(
            project_payload,
            metadata_payload,
            workspace_payload,
            project_dir,
        )

    def save_record(self, record: ProjectWorkspaceRecord) -> Path:
        record.touch()
        metadata_payload = self._metadata_payload(record)
        workspace_payload = record.to_dict()
        workspace_payload["workspace_state"] = dict(record.workspace_state)

        project_root = Path(
            self.manager.project_repository.project_location(record.workspace_id)
        )
        if (project_root / "project.json").exists():
            self.manager.project_repository.save(
                record.workspace_id,
                record.project.to_dict(),
                metadata_payload,
                workspace_payload,
            )
        else:
            self.manager.project_repository.create(
                record.workspace_id,
                record.project.to_dict(),
                metadata_payload,
                workspace_payload,
            )
            self.manager.log(
                record.workspace_id,
                "project_created",
                {
                    "project_id": record.project.project_id,
                    "project_name": record.project.name,
                },
            )

        return project_root / "workspace.json"

    def create_manual_record(
        self,
        *,
        project_id: str,
        name: str,
        client: str,
        location: str | None = None,
        bid_date: str | None = None,
        status: ProjectStatus | None = None,
        consultant: str | None = None,
        architect: str | None = None,
        engineers: list[str] | None = None,
        project_number: str | None = None,
        issue_date: str | None = None,
        lifecycle_stage: str | None = None,
    ) -> ProjectWorkspaceRecord:
        lifecycle = status or ProjectStatus.INTAKE
        project = Project(
            project_id=project_id,
            name=name,
            client=client,
            location=location,
            bid_date=bid_date,
            status=lifecycle,
        )
        return ProjectWorkspaceRecord(
            workspace_id=project.project_id,
            project=project,
            source_mode="manual",
            source_label="Manual Project",
            metadata={
                "project_name": name,
                "owner": client,
                "consultant": consultant,
                "architect": architect,
                "engineers": list(engineers or []),
                "project_number": project_number or project_id,
                "issue_date": issue_date,
                "bid_date": bid_date,
                "status": lifecycle.value,
                "lifecycle_stage": lifecycle_stage or lifecycle.value,
                "atlas_version": __version__,
            },
        )

    def rename_project(
        self, workspace_id: str, new_name: str
    ) -> ProjectWorkspaceRecord:
        self.manager.project_repository.rename(workspace_id, new_name)
        self.manager.log(workspace_id, "project_renamed", {"new_name": new_name})
        return self.load_record(workspace_id)

    def archive_project(
        self,
        workspace_id: str,
        archived: bool = True,
    ) -> ProjectWorkspaceRecord:
        self.manager.project_repository.archive(workspace_id, archived=archived)
        self.manager.log(
            workspace_id,
            "project_archived" if archived else "project_unarchived",
            {"archived": archived},
        )
        return self.load_record(workspace_id)

    def delete_project(self, workspace_id: str) -> None:
        self.manager.project_repository.delete(workspace_id)

    def duplicate_project(
        self,
        workspace_id: str,
        new_workspace_id: str,
        new_name: str | None = None,
    ) -> ProjectWorkspaceRecord:
        self.manager.project_repository.duplicate(
            workspace_id,
            new_workspace_id,
            new_name=new_name,
        )
        self.manager.log(
            new_workspace_id,
            "project_duplicated",
            {"source_project_id": workspace_id},
        )
        return self.load_record(new_workspace_id)

    def pin_project(
        self, workspace_id: str, pinned: bool = True
    ) -> ProjectWorkspaceRecord:
        self.manager.project_repository.set_pinned(workspace_id, pinned)
        return self.load_record(workspace_id)

    def set_reference_project(
        self,
        workspace_id: str,
        reference: bool = True,
    ) -> ProjectWorkspaceRecord:
        self.manager.project_repository.set_reference(workspace_id, reference)
        return self.load_record(workspace_id)

    def load_workspace_state(self, workspace_id: str) -> dict[str, Any]:
        return self.manager.workspace_repository.load_state(workspace_id)

    def save_workspace_state(self, workspace_id: str, state: dict[str, Any]) -> None:
        self.manager.workspace_repository.save_state(workspace_id, state)
        self.manager.log(
            workspace_id,
            "workspace_opened",
            {"last_open_page": state.get("last_open_page")},
        )

    def import_uploaded_documents(
        self,
        workspace_id: str,
        uploaded_files: list[tuple[str, bytes]],
    ) -> ProjectWorkspaceRecord:
        result = self.manager.document_repository.import_uploads(
            workspace_id,
            uploaded_files,
        )
        record = self.load_record(workspace_id)
        record.source_mode = "project_documents"
        record.source_label = "Project Repository"
        record.package_location = str(result.get("package_location") or "") or None
        record.intake_snapshot_path = (
            str(result.get("intake_snapshot_path") or "") or None
        )
        record.import_summary = dict(result.get("import_summary") or {})
        record.warnings = [str(item) for item in list(result.get("warnings") or [])]
        self.save_record(record)
        self.manager.log(
            workspace_id,
            "documents_imported",
            {
                "uploaded_file_count": len(uploaded_files),
                "warnings": len(record.warnings),
            },
        )
        return record

    def save_review_artifact(
        self,
        workspace_id: str,
        artifact_name: str,
        payload: dict[str, Any],
    ) -> None:
        self.manager.review_repository.save_artifact(
            workspace_id, artifact_name, payload
        )

    def save_knowledge_graph(self, workspace_id: str, payload: dict[str, Any]) -> None:
        self.manager.knowledge_repository.save_knowledge_graph(workspace_id, payload)

    def save_engineering_intelligence(
        self,
        workspace_id: str,
        payload: dict[str, Any],
    ) -> None:
        self.manager.knowledge_repository.save_engineering_intelligence(
            workspace_id,
            payload,
        )

    def list_history(self, workspace_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self.manager.history_repository.list_events(workspace_id, limit=limit)

    def read_manifest(self, workspace_id: str) -> dict[str, Any]:
        return self.manager.read_manifest(workspace_id)

    def refresh_manifest(self, workspace_id: str) -> dict[str, Any]:
        return self.manager.refresh_manifest(workspace_id)

    def export_project_bundle(self, workspace_id: str, out_path: str) -> str:
        return self.manager.export_project_bundle(workspace_id, out_path)

    def import_project_bundle(self, bundle_path: str) -> ProjectWorkspaceRecord:
        workspace_id = self.manager.import_project_bundle(bundle_path)
        self.log_event(workspace_id, "project_imported", {"bundle_path": bundle_path})
        return self.load_record(workspace_id)

    def project_health(self, workspace_id: str) -> dict[str, Any]:
        return self.manager.health_check(workspace_id)

    def log_event(
        self,
        workspace_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        self.manager.log(workspace_id, event_type, payload)

    def project_location(self, workspace_id: str) -> str:
        return self.manager.project_repository.project_location(workspace_id)

    @staticmethod
    def _metadata_payload(record: ProjectWorkspaceRecord) -> dict[str, Any]:
        meta = dict(record.metadata)
        now = datetime.now(UTC).isoformat()
        return {
            "project_name": str(meta.get("project_name") or record.project.name),
            "owner": str(meta.get("owner") or record.project.client),
            "consultant": meta.get("consultant"),
            "architect": meta.get("architect"),
            "engineers": list(meta.get("engineers") or []),
            "project_number": str(
                meta.get("project_number") or record.project.project_id
            ),
            "issue_date": meta.get("issue_date"),
            "bid_date": meta.get("bid_date") or record.project.bid_date,
            "status": str(meta.get("status") or record.project.status.value),
            "lifecycle_stage": str(
                meta.get("lifecycle_stage") or record.project.status.value
            ),
            "created_at": str(meta.get("created_at") or record.created_at),
            "last_opened": record.last_opened_at,
            "last_modified": now,
            "atlas_version": str(meta.get("atlas_version") or __version__),
            "pinned": record.pinned,
            "reference": record.is_reference,
            "archived": record.archived,
        }

    @classmethod
    def _from_repository_payloads(
        cls,
        project_payload: dict[str, Any],
        metadata_payload: dict[str, Any],
        workspace_payload: dict[str, Any],
        project_location: str,
    ) -> ProjectWorkspaceRecord:
        project_dir = Path(project_location)
        payload = dict(workspace_payload)
        payload["project"] = project_payload
        payload["workspace_id"] = str(
            payload.get("workspace_id")
            or project_payload.get("project_id")
            or project_dir.name
        )
        payload["metadata"] = {
            **dict(payload.get("metadata") or {}),
            **dict(metadata_payload),
        }
        payload["workspace_state"] = dict(payload.get("workspace_state") or {})
        payload["pinned"] = bool(
            metadata_payload.get("pinned", payload.get("pinned", False))
        )
        payload["is_reference"] = bool(
            metadata_payload.get("reference", payload.get("is_reference", False))
        )
        payload["archived"] = bool(
            metadata_payload.get("archived", payload.get("archived", False))
        )
        payload["project_root"] = str(project_dir)
        payload["last_opened_at"] = (
            str(
                metadata_payload.get("last_opened")
                or payload.get("last_opened_at")
                or ""
            )
            or None
        )
        return ProjectWorkspaceRecord.from_dict(payload)

    @staticmethod
    def _sort_key(record: ProjectWorkspaceRecord) -> str:
        return record.last_opened_at or record.updated_at or record.created_at

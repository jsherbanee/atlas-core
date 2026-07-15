"""Project repository-backed workspace persistence for Atlas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
from pathlib import Path
import base64
import json
from typing import Any

from atlas_core import __version__
from atlas_core.domain import Project, ProjectLifecycleEvent, ProjectStatus
from atlas_core.domain import OrganizationRole, ProjectStakeholder
from atlas_core.domain.av_lifecycle import (
    AVLifecycleEngine,
    LifecycleHistoryEvent,
    LifecyclePlan,
    legacy_status_for_stage,
    normalize_stage_key,
    project_lifecycle_from_legacy,
)
from atlas_core.contracts.background_job_contracts import (
    JobCategory,
    JobDefinition,
    JobRequest,
    JobRetryPolicy,
    JobStatus,
)
from atlas_core.repository import AtlasProjectManager
from atlas_core.services.background_job_service import JobExecutionContext
from atlas_core.services.document_intake_service import (
    DocumentIntakeService,
    UploadInspectionResult,
    UploadedIntakeFile,
)
from atlas_core.services.organization_directory_service import (
    OrganizationDirectoryService,
)


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
            if isinstance(self.project, dict):
                payload = dict(self.project)
            else:
                payload = dict(getattr(self.project, "__dict__", {}) or {})
            self.project = Project.from_dict(payload)

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
        self.organization_directory = OrganizationDirectoryService(self.workspace_root)
        self.lifecycle_engine = AVLifecycleEngine.default()
        self.manager.background_job_service.register_handler(
            category=JobCategory.DOCUMENT_IMPORT,
            handler=self._execute_document_import_job,
        )
        self.manager.background_job_service.register_handler(
            category=JobCategory.EXPORT_GENERATION,
            handler=self._execute_project_export_job,
        )

    @staticmethod
    def _tenant_scope_for_record(record: ProjectWorkspaceRecord) -> tuple[str, str]:
        tenant_id = str(record.metadata.get("tenant_id") or "local").strip() or "local"
        organization_id = (
            str(record.metadata.get("organization_id") or "atlas").strip() or "atlas"
        )
        return tenant_id, organization_id

    def _record_audit(
        self,
        *,
        record: ProjectWorkspaceRecord,
        action: str,
        actor: str,
        target_type: str,
        target_id: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        source: str = "project_workspace_service",
    ) -> None:
        tenant_id, organization_id = self._tenant_scope_for_record(record)
        self.manager.record_audit_event(
            project_id=record.workspace_id,
            action=action,
            actor_id=actor,
            actor_type="user",
            tenant_id=tenant_id,
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            source=source,
            before=before,
            after=after,
            context=context,
        )

    @staticmethod
    def _canonical_payload_hash(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def _encode_uploaded_files(uploaded_files: list[tuple[str, bytes]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name, data in uploaded_files:
            rows.append(
                {
                    "name": str(name),
                    "size_bytes": len(data),
                    "sha1": hashlib.sha1(data).hexdigest(),
                    "data_b64": base64.b64encode(data).decode("ascii"),
                }
            )
        return rows

    @staticmethod
    def _decode_uploaded_files(payload_rows: list[dict[str, Any]]) -> list[tuple[str, bytes]]:
        rows: list[tuple[str, bytes]] = []
        for item in payload_rows:
            name = str(item.get("name") or "")
            encoded = str(item.get("data_b64") or "")
            if not name or not encoded:
                continue
            rows.append((name, base64.b64decode(encoded.encode("ascii"))))
        return rows

    def _execute_document_import_job(
        self,
        context: JobExecutionContext,
    ) -> dict[str, Any]:
        payload = dict(context.request.input_payload or {})
        workspace_id = str(payload.get("workspace_id") or context.project_id)
        uploaded = self._decode_uploaded_files(list(payload.get("uploaded_files") or []))
        context.progress(10, "Preparing import", "prepare", 0, max(len(uploaded), 1))
        updated_record = self.import_uploaded_documents(
            workspace_id=workspace_id,
            uploaded_files=uploaded,
        )
        context.progress(100, "Import completed", "completed", len(uploaded), len(uploaded))
        return {
            "summary": "Document import completed",
            "payload": {
                "workspace_id": updated_record.workspace_id,
                "uploaded_file_count": len(uploaded),
                "warning_count": len(updated_record.warnings),
                "import_summary": dict(updated_record.import_summary),
            },
        }

    def _execute_project_export_job(
        self,
        context: JobExecutionContext,
    ) -> dict[str, Any]:
        payload = dict(context.request.input_payload or {})
        workspace_id = str(payload.get("workspace_id") or context.project_id)
        out_path = str(payload.get("out_path") or "")
        if not out_path:
            raise ValueError("out_path is required for export job")
        context.progress(10, "Preparing export", "prepare")
        bundle_path = self.export_project_bundle(workspace_id, out_path)
        context.progress(100, "Export completed", "completed")
        return {
            "summary": "Project bundle export completed",
            "payload": {
                "workspace_id": workspace_id,
                "bundle_path": bundle_path,
            },
        }

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
        is_new_project = False
        record.touch()
        self._update_lifecycle_snapshot(record)
        project_root = Path(
            self.manager.project_repository.project_location(record.workspace_id)
        )
        if (project_root / "project.json").exists():
            existing_project_payload, existing_metadata_payload, _, _ = (
                self.manager.project_repository.load(record.workspace_id)
            )
            existing_atlas_bid_id = str(
                existing_metadata_payload.get("atlas_bid_id")
                or existing_project_payload.get("atlas_bid_id")
                or existing_project_payload.get("project_id")
                or record.workspace_id
            )
            requested_atlas_bid_id = str(
                record.metadata.get("atlas_bid_id")
                or record.project.atlas_bid_id
                or record.project.project_id
            )
            if requested_atlas_bid_id != existing_atlas_bid_id:
                raise ValueError(
                    "Atlas Bid ID is immutable once a project has been created"
                )
            record.project.atlas_bid_id = existing_atlas_bid_id
            record.metadata["atlas_bid_id"] = existing_atlas_bid_id
            record.metadata["project_number"] = existing_atlas_bid_id

        metadata_payload = self._metadata_payload(record)
        workspace_payload = record.to_dict()
        workspace_payload["workspace_state"] = dict(record.workspace_state)
        if (project_root / "project.json").exists():
            self.manager.project_repository.save(
                record.workspace_id,
                record.project.to_dict(),
                metadata_payload,
                workspace_payload,
            )
        else:
            is_new_project = True
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
        if is_new_project:
            self._record_audit(
                record=record,
                action="project.created",
                actor="atlas-ui",
                target_type="project",
                target_id=record.project.project_id,
                after={
                    "project_id": record.project.project_id,
                    "project_name": record.project.name,
                    "lifecycle_stage": record.metadata.get("lifecycle_stage"),
                },
            )

        return project_root / "workspace.json"

    def create_manual_record(
        self,
        *,
        project_id: str | None = None,
        name: str,
        client: str,
        location: str | None = None,
        bid_date: str | None = None,
        status: ProjectStatus | None = None,
        consultant: str | None = None,
        general_contractor: str | None = None,
        electrical_contractor: str | None = None,
        architect: str | None = None,
        engineers: list[str] | None = None,
        client_project_number: str | None = None,
        internal_project_number: str | None = None,
        issue_date: str | None = None,
        lifecycle_stage: str | None = None,
    ) -> ProjectWorkspaceRecord:
        atlas_bid_id = (
            self.manager.allocate_bid_id() if project_id is None else project_id
        )
        lifecycle_stage_value = normalize_stage_key(lifecycle_stage)
        legacy_status = status or (
            ProjectStatus(legacy_status_for_stage(lifecycle_stage_value))
            if lifecycle_stage_value
            else ProjectStatus.INTAKE
        )
        project = Project(
            project_id=atlas_bid_id,
            name=name,
            client=client,
            client_project_number=client_project_number,
            internal_project_number=internal_project_number,
            location=location,
            bid_date=bid_date,
            status=legacy_status,
        )
        return ProjectWorkspaceRecord(
            workspace_id=project.project_id,
            project=project,
            source_mode="manual",
            source_label="Manual Project",
            metadata={
                "project_name": name,
                "owner": client,
                "owner_client": client,
                "consultant": consultant,
                "general_contractor": general_contractor,
                "electrical_contractor": electrical_contractor,
                "architect": architect,
                "engineers": list(engineers or []),
                "atlas_bid_id": atlas_bid_id,
                "client_project_number": client_project_number,
                "internal_project_number": internal_project_number,
                "project_number": atlas_bid_id,
                "issue_date": issue_date,
                "bid_date": bid_date,
                "status": legacy_status.value,
                "lifecycle_stage": lifecycle_stage_value or legacy_status.value,
                "atlas_version": __version__,
            },
        )

    def preview_next_bid_id(self) -> str:
        return self.manager.preview_next_bid_id()

    def inspect_uploaded_documents(
        self,
        uploaded_files: list[tuple[str, bytes]],
    ) -> UploadInspectionResult:
        intake_files = [
            UploadedIntakeFile(name=name, data=data) for name, data in uploaded_files
        ]
        return DocumentIntakeService().inspect_uploaded_files(intake_files)

    def search_stakeholder_organizations(
        self,
        query: str,
        *,
        role: OrganizationRole | None = None,
        include_inactive: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        rows = self.organization_directory.search_organizations(
            query,
            role=role,
            include_inactive=include_inactive,
            limit=limit,
        )
        return [item.to_dict() for item in rows]

    def find_likely_organization_duplicates(self, name: str) -> list[dict[str, Any]]:
        rows = self.organization_directory.find_likely_duplicates(name)
        return [item.to_dict() for item in rows]

    def create_stakeholder_organization(
        self,
        *,
        name: str,
        role: OrganizationRole,
        website: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
        notes: str | None = None,
        aliases: list[str] | None = None,
    ) -> dict[str, Any]:
        created = self.organization_directory.create_organization(
            name=name,
            role=role,
            website=website,
            phone=phone,
            email=email,
            address=address,
            notes=notes,
            aliases=aliases,
        )
        return created.to_dict()

    def list_project_stakeholders(self, workspace_id: str) -> list[dict[str, Any]]:
        rows = self.organization_directory.list_project_stakeholders(workspace_id)
        organizations = {
            item.organization_id: item
            for item in self.organization_directory.list_organizations(
                include_inactive=True
            )
        }
        enriched: list[dict[str, Any]] = []
        for item in rows:
            payload = item.to_dict()
            org = organizations.get(item.organization_id)
            payload["organization_display_name"] = (
                org.display_name if org is not None else ""
            )
            payload["organization_aliases"] = list(org.aliases) if org else []
            enriched.append(payload)
        return enriched

    def replace_project_stakeholders(
        self,
        workspace_id: str,
        stakeholders: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        domain_rows: list[ProjectStakeholder] = [
            ProjectStakeholder.from_dict(item) for item in stakeholders
        ]
        updated = self.organization_directory.replace_project_stakeholders(
            workspace_id,
            domain_rows,
        )
        return [item.to_dict() for item in updated]

    def link_project_stakeholder(
        self,
        *,
        workspace_id: str,
        organization_id: str,
        role: OrganizationRole,
        is_primary: bool = False,
        contact_display: str | None = None,
        project_notes: str | None = None,
    ) -> dict[str, Any]:
        linked = self.organization_directory.link_organization_to_project(
            project_id=workspace_id,
            organization_id=organization_id,
            role=role,
            is_primary=is_primary,
            contact_display=contact_display,
            project_notes=project_notes,
        )
        return linked.to_dict()

    def update_project_identity_metadata(
        self,
        workspace_id: str,
        *,
        owner: str | None = None,
        lifecycle_stage: str | None = None,
        lifecycle_reason: str | None = None,
        lifecycle_actor: str | None = None,
        client_project_number: str | None = None,
        internal_project_number: str | None = None,
        consultant: str | None = None,
        general_contractor: str | None = None,
        electrical_contractor: str | None = None,
        architect: str | None = None,
        engineers: list[str] | None = None,
        issue_date: str | None = None,
        location: str | None = None,
        bid_date: str | None = None,
    ) -> ProjectWorkspaceRecord:
        record = self.load_record(workspace_id)
        before = {
            "owner": record.metadata.get("owner"),
            "lifecycle_stage": record.metadata.get("lifecycle_stage"),
            "client_project_number": record.project.client_project_number,
            "internal_project_number": record.project.internal_project_number,
            "location": record.project.location,
            "bid_date": record.project.bid_date,
        }

        if owner is not None:
            record.metadata["owner"] = owner
            record.project.client = owner
        if lifecycle_stage is not None:
            normalized_stage = lifecycle_stage.strip()
            if normalized_stage:
                lifecycle_key = normalize_stage_key(normalized_stage)
                current_plan = self._lifecycle_plan_for_record(record)
                if lifecycle_key != current_plan.current_stage_key and lifecycle_reason:
                    record = self._transition_record_lifecycle(
                        record,
                        target_stage_key=lifecycle_key,
                        reason=lifecycle_reason,
                        actor=lifecycle_actor or "atlas-ui",
                    )
                else:
                    record.metadata["lifecycle_stage"] = lifecycle_key
                    legacy_status_value = legacy_status_for_stage(lifecycle_key)
                    record.metadata["status"] = legacy_status_value
                    record.project.status = ProjectStatus(legacy_status_value)
                    self._update_lifecycle_snapshot(record, rebuild=True)
        else:
            self._update_lifecycle_snapshot(record)
        if client_project_number is not None:
            normalized_client_number = client_project_number.strip() or None
            record.metadata["client_project_number"] = normalized_client_number
            record.project.client_project_number = normalized_client_number
        if internal_project_number is not None:
            normalized_internal_number = internal_project_number.strip() or None
            record.metadata["internal_project_number"] = normalized_internal_number
            record.project.internal_project_number = normalized_internal_number
        if consultant is not None:
            record.metadata["consultant"] = consultant.strip() or None
        if general_contractor is not None:
            record.metadata["general_contractor"] = general_contractor.strip() or None
        if electrical_contractor is not None:
            record.metadata["electrical_contractor"] = (
                electrical_contractor.strip() or None
            )
        if architect is not None:
            record.metadata["architect"] = architect.strip() or None
        if engineers is not None:
            record.metadata["engineers"] = [
                item.strip()
                for item in engineers
                if isinstance(item, str) and item.strip()
            ]
        if issue_date is not None:
            record.metadata["issue_date"] = issue_date.strip() or None
        if location is not None:
            normalized_location = location.strip() or None
            record.project.location = normalized_location
        if bid_date is not None:
            normalized_bid_date = bid_date.strip() or None
            record.project.bid_date = normalized_bid_date
            record.metadata["bid_date"] = normalized_bid_date

        self.save_record(record)
        self.manager.log(
            workspace_id,
            "project_identity_updated",
            {
                "atlas_bid_id": record.project.project_id,
                "client_project_number": record.project.client_project_number,
                "internal_project_number": record.project.internal_project_number,
                "lifecycle_stage": record.metadata.get("lifecycle_stage"),
            },
        )
        refreshed = self.load_record(workspace_id)
        self._record_audit(
            record=refreshed,
            action="project.identity.updated",
            actor=lifecycle_actor or "atlas-ui",
            target_type="project",
            target_id=workspace_id,
            before=before,
            after={
                "owner": refreshed.metadata.get("owner"),
                "lifecycle_stage": refreshed.metadata.get("lifecycle_stage"),
                "client_project_number": refreshed.project.client_project_number,
                "internal_project_number": refreshed.project.internal_project_number,
                "location": refreshed.project.location,
                "bid_date": refreshed.project.bid_date,
            },
        )
        return refreshed

    def lifecycle_plan_for_record(
        self, record: ProjectWorkspaceRecord
    ) -> LifecyclePlan:
        return self._lifecycle_plan_for_record(record)

    def lifecycle_plan(self, workspace_id: str) -> LifecyclePlan:
        return self._lifecycle_plan_for_record(self.load_record(workspace_id))

    def available_project_lifecycle_transitions(
        self, workspace_id: str
    ) -> list[dict[str, Any]]:
        plan = self.lifecycle_plan(workspace_id)
        return [
            transition.to_dict()
            for transition in self.lifecycle_engine.available_transitions(plan)
        ]

    def transition_project_lifecycle(
        self,
        workspace_id: str,
        *,
        target_stage_key: str,
        reason: str,
        actor: str = "atlas-ui",
        tenant_id: str | None = None,
    ) -> ProjectWorkspaceRecord:
        record = self.load_record(workspace_id)
        before_stage = record.metadata.get("lifecycle_stage")
        record = self._transition_record_lifecycle(
            record,
            target_stage_key=target_stage_key,
            reason=reason,
            actor=actor,
            tenant_id=tenant_id,
        )
        self.save_record(record)
        refreshed = self.load_record(workspace_id)
        self._record_audit(
            record=refreshed,
            action="project.lifecycle.transitioned",
            actor=actor,
            target_type="project_lifecycle",
            target_id=workspace_id,
            before={"lifecycle_stage": before_stage},
            after={"lifecycle_stage": refreshed.metadata.get("lifecycle_stage")},
            context={"reason": reason},
        )
        return refreshed

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
        prior = self.load_record(workspace_id)
        self.manager.project_repository.archive(workspace_id, archived=archived)
        self.manager.log(
            workspace_id,
            "project_archived" if archived else "project_unarchived",
            {"archived": archived},
        )
        refreshed = self.load_record(workspace_id)
        self._record_audit(
            record=refreshed,
            action="project.archive.updated",
            actor="atlas-ui",
            target_type="project",
            target_id=workspace_id,
            before={"archived": prior.archived},
            after={"archived": refreshed.archived},
        )
        return refreshed

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
        record = self.load_record(workspace_id)
        self._record_audit(
            record=record,
            action="workspace.state.saved",
            actor="atlas-ui",
            target_type="workspace",
            target_id=workspace_id,
            after={"last_open_page": state.get("last_open_page")},
        )

    def import_uploaded_documents(
        self,
        workspace_id: str,
        uploaded_files: list[tuple[str, bytes]],
    ) -> ProjectWorkspaceRecord:
        baseline_record = self.load_record(workspace_id)
        result = self.manager.document_repository.import_uploads(
            workspace_id,
            uploaded_files,
        )
        record = self.load_record(workspace_id)
        record.project.name = baseline_record.project.name
        record.project.client = baseline_record.project.client
        record.project.atlas_bid_id = baseline_record.project.atlas_bid_id
        record.project.client_project_number = (
            baseline_record.project.client_project_number
        )
        record.project.internal_project_number = (
            baseline_record.project.internal_project_number
        )
        record.metadata["project_name"] = baseline_record.project.name
        record.metadata["owner"] = baseline_record.project.client
        record.metadata["owner_client"] = baseline_record.project.client
        record.metadata["atlas_bid_id"] = baseline_record.project.atlas_bid_id
        record.metadata["project_number"] = baseline_record.project.atlas_bid_id
        record.metadata["client_project_number"] = (
            baseline_record.project.client_project_number
        )
        record.metadata["internal_project_number"] = (
            baseline_record.project.internal_project_number
        )
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
        self._record_audit(
            record=record,
            action="project.documents.imported",
            actor="atlas-ui",
            target_type="project_documents",
            target_id=workspace_id,
            after={
                "uploaded_file_count": len(uploaded_files),
                "warning_count": len(record.warnings),
            },
            context={
                "uploaded_file_names": [name for name, _ in uploaded_files],
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

    def list_background_jobs(
        self,
        workspace_id: str,
        *,
        tenant_id: str | None = None,
        organization_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        record = self.load_record(workspace_id)
        resolved_tenant, resolved_org = self._tenant_scope_for_record(record)
        return self.manager.background_job_service.list_jobs(
            project_id=workspace_id,
            tenant_id=tenant_id or resolved_tenant,
            organization_id=organization_id or resolved_org,
            limit=limit,
        )

    def cancel_background_job(
        self,
        workspace_id: str,
        *,
        job_id: str,
        actor_id: str,
        reason: str,
        tenant_id: str | None = None,
        organization_id: str | None = None,
    ) -> dict[str, Any]:
        record = self.load_record(workspace_id)
        resolved_tenant, resolved_org = self._tenant_scope_for_record(record)
        return self.manager.background_job_service.cancel_job(
            project_id=workspace_id,
            job_id=job_id,
            tenant_id=tenant_id or resolved_tenant,
            organization_id=organization_id or resolved_org,
            actor_id=actor_id,
            reason=reason,
        )

    def retry_background_job(
        self,
        workspace_id: str,
        *,
        job_id: str,
        tenant_id: str | None = None,
        organization_id: str | None = None,
    ) -> dict[str, Any]:
        record = self.load_record(workspace_id)
        resolved_tenant, resolved_org = self._tenant_scope_for_record(record)
        return self.manager.background_job_service.retry_job(
            project_id=workspace_id,
            job_id=job_id,
            tenant_id=tenant_id or resolved_tenant,
            organization_id=organization_id or resolved_org,
        )

    def run_document_import_job(
        self,
        *,
        workspace_id: str,
        uploaded_files: list[tuple[str, bytes]],
        actor_id: str = "atlas-ui",
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        record = self.load_record(workspace_id)
        tenant_id, organization_id = self._tenant_scope_for_record(record)
        encoded_uploads = self._encode_uploaded_files(uploaded_files)
        deterministic_input = {
            "workspace_id": workspace_id,
            "uploaded_files": encoded_uploads,
        }
        job_request = JobRequest(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor_id=actor_id,
            category=JobCategory.DOCUMENT_IMPORT,
            definition=JobDefinition(
                category=JobCategory.DOCUMENT_IMPORT,
                handler_key="project_workspace.document_import",
                cancellable=False,
            ),
            input_payload=deterministic_input,
            related_object_type="project_documents",
            related_object_id=workspace_id,
            idempotency_key=idempotency_key
            or f"document_import:{self._canonical_payload_hash({'files': [{'name': item['name'], 'sha1': item['sha1']} for item in encoded_uploads]})}",
            correlation_id=correlation_id,
            retry_policy=JobRetryPolicy(max_attempts=2, retry_delay_seconds=0),
        )
        submitted = self.manager.background_job_service.submit_job(
            project_id=workspace_id,
            request=job_request,
        )
        if JobStatus(str(submitted.get("status") or JobStatus.QUEUED.value)) not in {
            JobStatus.QUEUED,
            JobStatus.RETRY_SCHEDULED,
            JobStatus.RUNNING,
        }:
            return submitted
        return self.manager.background_job_service.run_job(
            project_id=workspace_id,
            job_id=str(submitted.get("job_id") or ""),
            tenant_id=tenant_id,
            organization_id=organization_id,
        )

    def run_export_generation_job(
        self,
        *,
        workspace_id: str,
        out_path: str,
        actor_id: str = "atlas-ui",
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        record = self.load_record(workspace_id)
        tenant_id, organization_id = self._tenant_scope_for_record(record)
        deterministic_input = {
            "workspace_id": workspace_id,
            "out_path": out_path,
        }
        job_request = JobRequest(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor_id=actor_id,
            category=JobCategory.EXPORT_GENERATION,
            definition=JobDefinition(
                category=JobCategory.EXPORT_GENERATION,
                handler_key="project_workspace.export_generation",
                cancellable=False,
            ),
            input_payload=deterministic_input,
            related_object_type="project_bundle",
            related_object_id=workspace_id,
            idempotency_key=idempotency_key
            or f"export_generation:{self._canonical_payload_hash(deterministic_input)}",
            correlation_id=correlation_id,
            retry_policy=JobRetryPolicy(max_attempts=2, retry_delay_seconds=0),
        )
        submitted = self.manager.background_job_service.submit_job(
            project_id=workspace_id,
            request=job_request,
        )
        if JobStatus(str(submitted.get("status") or JobStatus.QUEUED.value)) not in {
            JobStatus.QUEUED,
            JobStatus.RETRY_SCHEDULED,
            JobStatus.RUNNING,
        }:
            return submitted
        return self.manager.background_job_service.run_job(
            project_id=workspace_id,
            job_id=str(submitted.get("job_id") or ""),
            tenant_id=tenant_id,
            organization_id=organization_id,
        )

    def read_manifest(self, workspace_id: str) -> dict[str, Any]:
        return self.manager.read_manifest(workspace_id)

    def refresh_manifest(self, workspace_id: str) -> dict[str, Any]:
        return self.manager.refresh_manifest(workspace_id)

    def export_project_bundle(self, workspace_id: str, out_path: str) -> str:
        bundle = self.manager.export_project_bundle(workspace_id, out_path)
        record = self.load_record(workspace_id)
        self._record_audit(
            record=record,
            action="project.bundle.exported",
            actor="atlas-ui",
            target_type="project_bundle",
            target_id=workspace_id,
            context={"out_path": out_path, "bundle_path": bundle},
        )
        return bundle

    def import_project_bundle(self, bundle_path: str) -> ProjectWorkspaceRecord:
        workspace_id = self.manager.import_project_bundle(bundle_path)
        self.log_event(workspace_id, "project_imported", {"bundle_path": bundle_path})
        record = self.load_record(workspace_id)
        self._record_audit(
            record=record,
            action="project.bundle.imported",
            actor="atlas-ui",
            target_type="project_bundle",
            target_id=workspace_id,
            context={"bundle_path": bundle_path},
        )
        return record

    def list_audit_history(
        self,
        workspace_id: str,
        *,
        tenant_id: str | None = None,
        organization_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        record = self.load_record(workspace_id)
        resolved_tenant_id, resolved_organization_id = self._tenant_scope_for_record(
            record
        )
        return self.manager.list_audit_events(
            project_id=workspace_id,
            tenant_id=tenant_id or resolved_tenant_id,
            organization_id=organization_id or resolved_organization_id,
            limit=limit,
        )

    def export_audit_history(
        self,
        workspace_id: str,
        *,
        tenant_id: str | None = None,
        organization_id: str | None = None,
        limit: int = 5000,
    ) -> dict[str, Any]:
        record = self.load_record(workspace_id)
        resolved_tenant_id, resolved_organization_id = self._tenant_scope_for_record(
            record
        )
        return self.manager.export_audit_events(
            project_id=workspace_id,
            tenant_id=tenant_id or resolved_tenant_id,
            organization_id=organization_id or resolved_organization_id,
            limit=limit,
        )

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
        atlas_bid_id = str(meta.get("atlas_bid_id") or record.project.project_id)
        client_project_number = (
            str(meta.get("client_project_number") or "")
            or record.project.client_project_number
        )
        internal_project_number = (
            str(meta.get("internal_project_number") or "")
            or record.project.internal_project_number
        )
        now = datetime.now(UTC).isoformat()
        payload = {
            "project_name": str(meta.get("project_name") or record.project.name),
            "owner": str(meta.get("owner") or record.project.client),
            "owner_client": str(meta.get("owner") or record.project.client),
            "consultant": meta.get("consultant"),
            "general_contractor": meta.get("general_contractor"),
            "electrical_contractor": meta.get("electrical_contractor"),
            "architect": meta.get("architect"),
            "engineers": list(meta.get("engineers") or []),
            "atlas_bid_id": atlas_bid_id,
            "client_project_number": client_project_number,
            "internal_project_number": internal_project_number,
            "project_number": atlas_bid_id,
            "issue_date": meta.get("issue_date"),
            "bid_date": meta.get("bid_date") or record.project.bid_date,
            "status": str(meta.get("status") or record.project.status.value),
            "lifecycle_stage": str(
                meta.get("lifecycle_stage") or record.project.status.value
            ),
            "lifecycle_plan": dict(meta.get("lifecycle_plan") or {}),
            "lifecycle_definition_key": str(
                meta.get("lifecycle_definition_key") or "atlas.av.lifecycle"
            ),
            "lifecycle_schema_version": str(
                meta.get("lifecycle_schema_version") or "1.0"
            ),
            "created_at": str(meta.get("created_at") or record.created_at),
            "last_opened": record.last_opened_at,
            "last_modified": now,
            "atlas_version": str(meta.get("atlas_version") or __version__),
            "pinned": record.pinned,
            "reference": record.is_reference,
            "archived": record.archived,
        }
        return payload

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
        normalized_meta = cls._normalized_identity_metadata(
            metadata_payload,
            project_payload,
            payload["workspace_id"],
        )
        project_payload["client_project_number"] = normalized_meta.get(
            "client_project_number"
        )
        project_payload["internal_project_number"] = normalized_meta.get(
            "internal_project_number"
        )
        payload["metadata"] = {
            **dict(payload.get("metadata") or {}),
            **normalized_meta,
        }
        lifecycle_plan_payload = normalized_meta.get("lifecycle_plan")
        if isinstance(lifecycle_plan_payload, dict) and lifecycle_plan_payload:
            payload["metadata"]["lifecycle_plan"] = lifecycle_plan_payload
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
    def _normalized_identity_metadata(
        metadata_payload: dict[str, Any],
        project_payload: dict[str, Any],
        workspace_id: str,
    ) -> dict[str, Any]:
        normalized = dict(metadata_payload)
        atlas_bid_id = str(
            normalized.get("atlas_bid_id")
            or normalized.get("project_number")
            or project_payload.get("project_id")
            or workspace_id
        )
        normalized["atlas_bid_id"] = atlas_bid_id
        normalized["project_number"] = atlas_bid_id

        if "client_project_number" not in normalized:
            normalized["client_project_number"] = (
                str(project_payload.get("client_project_number") or "") or None
            )
        if "internal_project_number" not in normalized:
            normalized["internal_project_number"] = (
                str(project_payload.get("internal_project_number") or "") or None
            )
        if "owner" not in normalized:
            normalized["owner"] = (
                str(normalized.get("owner_client") or "")
                or str(project_payload.get("client") or "")
                or None
            )
        if "owner_client" not in normalized:
            normalized["owner_client"] = normalized.get("owner")
        for field_name in [
            "consultant",
            "general_contractor",
            "electrical_contractor",
            "architect",
            "issue_date",
        ]:
            if field_name not in normalized:
                normalized[field_name] = None
        if "engineers" not in normalized:
            normalized["engineers"] = []
        if "lifecycle_plan" not in normalized:
            normalized["lifecycle_plan"] = {}
        if "lifecycle_definition_key" not in normalized:
            normalized["lifecycle_definition_key"] = "atlas.av.lifecycle"
        if "lifecycle_schema_version" not in normalized:
            normalized["lifecycle_schema_version"] = "1.0"
        return normalized

    def _update_lifecycle_snapshot(
        self,
        record: ProjectWorkspaceRecord,
        *,
        rebuild: bool = False,
    ) -> None:
        lifecycle_plan = self._build_lifecycle_plan(record, rebuild=rebuild)
        self._apply_lifecycle_plan(record, lifecycle_plan)

    def _build_lifecycle_plan(
        self,
        record: ProjectWorkspaceRecord,
        *,
        rebuild: bool = False,
    ) -> LifecyclePlan:
        if not rebuild:
            existing_payload = record.metadata.get("lifecycle_plan")
            if isinstance(existing_payload, dict) and existing_payload.get(
                "current_stage_key"
            ):
                return LifecyclePlan.from_dict(existing_payload)

        lifecycle_stage = str(
            record.metadata.get("lifecycle_stage")
            or record.metadata.get("status")
            or record.project.status.value
        )
        existing_payload = record.metadata.get("lifecycle_plan")
        history_events: list[LifecycleHistoryEvent] = []
        if isinstance(existing_payload, dict):
            history_events = [
                LifecycleHistoryEvent.from_dict(dict(item))
                for item in list(existing_payload.get("history_events") or [])
                if isinstance(item, dict)
            ]
        return project_lifecycle_from_legacy(
            record.project.project_id,
            record.metadata.get("tenant_id") or "default",
            legacy_status=record.project.status,
            lifecycle_stage=lifecycle_stage,
            history_events=history_events,
            resume_stage_key=(
                existing_payload.get("resume_stage_key")
                if isinstance(existing_payload, dict)
                else None
            ),
        )

    def _lifecycle_plan_for_record(
        self, record: ProjectWorkspaceRecord
    ) -> LifecyclePlan:
        return self._build_lifecycle_plan(record, rebuild=False)

    def _apply_lifecycle_plan(
        self,
        record: ProjectWorkspaceRecord,
        lifecycle_plan: LifecyclePlan,
    ) -> None:
        record.metadata["lifecycle_plan"] = lifecycle_plan.to_dict()
        record.metadata["lifecycle_definition_key"] = lifecycle_plan.definition_key
        record.metadata["lifecycle_schema_version"] = lifecycle_plan.schema_version
        record.metadata["lifecycle_stage"] = lifecycle_plan.current_stage_key
        legacy_status_value = (
            lifecycle_plan.legacy_project_status or record.project.status.value
        )
        record.metadata["status"] = legacy_status_value
        if record.project.status.value != legacy_status_value:
            record.project.status = ProjectStatus(legacy_status_value)

    def _transition_record_lifecycle(
        self,
        record: ProjectWorkspaceRecord,
        *,
        target_stage_key: str,
        reason: str,
        actor: str,
        tenant_id: str | None = None,
    ) -> ProjectWorkspaceRecord:
        current_plan = self._lifecycle_plan_for_record(record)
        tenant_scope = str(tenant_id or record.metadata.get("tenant_id") or "default")
        updated_plan, event = self.lifecycle_engine.set_stage(
            current_plan,
            target_stage_key,
            actor=actor,
            reason=reason,
            tenant_id=tenant_scope,
        )
        previous_status = record.project.status
        self._apply_lifecycle_plan(record, updated_plan)
        new_status = ProjectStatus(
            updated_plan.legacy_project_status or previous_status.value
        )
        if previous_status != new_status:
            record.project.lifecycle_events.append(
                ProjectLifecycleEvent(
                    from_status=previous_status,
                    to_status=new_status,
                    note=reason,
                    changed_by=actor,
                )
            )
        record.project.status = new_status
        self.manager.log(
            record.workspace_id,
            "project_lifecycle_transitioned",
            {
                "actor": actor,
                "reason": reason,
                "source_stage": event.source_stage,
                "destination_stage": event.destination_stage,
                "source_status": event.source_status,
                "destination_status": event.destination_status,
                "event_id": event.event_id,
            },
        )
        return record

    @staticmethod
    def _sort_key(record: ProjectWorkspaceRecord) -> tuple[str, str]:
        return (
            record.last_opened_at or record.updated_at or record.created_at,
            record.workspace_id,
        )

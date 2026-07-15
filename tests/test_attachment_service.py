from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from atlas_core.contracts.attachment_contracts import AttachmentAccessDecision
from atlas_core.repository.local import (
    LocalAttachmentRepository,
    LocalProjectRepository,
)
from atlas_core.services.attachment_service import AttachmentService
from atlas_core.services.project_workspace_service import ProjectWorkspaceService


def _build_attachment_service(
    tmp_path: Path,
    *,
    audit_events: list[dict[str, Any]] | None = None,
    hooks: list[dict[str, Any]] | None = None,
    max_size_bytes: int = 25 * 1024 * 1024,
) -> AttachmentService:
    project_repository = LocalProjectRepository(tmp_path / "AtlasProjects")
    repository = LocalAttachmentRepository(project_repository)

    def _audit_callback(**kwargs: Any) -> dict[str, Any]:
        if audit_events is not None:
            audit_events.append(dict(kwargs))
        return {"event_id": f"evt-{len(audit_events or [])}"}

    def _background_hook(payload: dict[str, Any]) -> None:
        if hooks is not None:
            hooks.append(dict(payload))

    return AttachmentService(
        repository=repository,
        audit_callback=_audit_callback,
        background_hook=_background_hook,
        max_size_bytes=max_size_bytes,
    )


def test_attachment_upload_deduplicates_by_hash_and_links_second_object(
    tmp_path: Path,
) -> None:
    service = _build_attachment_service(tmp_path)

    first = service.upload_attachment(
        tenant_id="tenant-a",
        organization_id="org-a",
        object_type="project",
        object_id="project-1",
        filename="bid.pdf",
        data=b"same-payload",
        mime_type="application/pdf",
        actor_id="user-a",
        project_id="project-1",
    )
    second = service.upload_attachment(
        tenant_id="tenant-a",
        organization_id="org-a",
        object_type="project",
        object_id="project-2",
        filename="bid-copy.pdf",
        data=b"same-payload",
        mime_type="application/pdf",
        actor_id="user-a",
        project_id="project-2",
    )

    assert first["duplicate_detected"] is False
    assert second["duplicate_detected"] is True
    assert first["attachment"]["attachment_id"] == second["attachment"]["attachment_id"]

    links = service.list_links(
        tenant_id="tenant-a",
        organization_id="org-a",
        attachment_id=first["attachment"]["attachment_id"],
    )
    assert len(links) == 2


def test_attachment_versioning_is_immutable_and_readable(tmp_path: Path) -> None:
    service = _build_attachment_service(tmp_path)

    uploaded = service.upload_attachment(
        tenant_id="tenant-a",
        organization_id="org-a",
        object_type="project",
        object_id="project-1",
        filename="scope.txt",
        data=b"v1",
        mime_type="text/plain",
        actor_id="user-a",
        project_id="project-1",
    )
    attachment_id = uploaded["attachment"]["attachment_id"]
    original_version_id = uploaded["attachment"]["current_version_id"]

    updated = service.create_attachment_version(
        tenant_id="tenant-a",
        organization_id="org-a",
        attachment_id=attachment_id,
        filename="scope.txt",
        data=b"v2",
        mime_type="text/plain",
        actor_id="user-a",
        project_id="project-1",
    )

    assert len(updated["attachment"]["versions"]) == 2
    assert updated["attachment"]["current_version_id"] != original_version_id

    latest = service.read_attachment_version(
        tenant_id="tenant-a",
        organization_id="org-a",
        attachment_id=attachment_id,
        actor_id="user-a",
        project_id="project-1",
    )
    original = service.read_attachment_version(
        tenant_id="tenant-a",
        organization_id="org-a",
        attachment_id=attachment_id,
        version_id=original_version_id,
        actor_id="user-a",
        project_id="project-1",
    )

    assert latest["data"] == b"v2"
    assert original["data"] == b"v1"


def test_attachment_archive_restore_unlink_and_purge_rules(tmp_path: Path) -> None:
    service = _build_attachment_service(tmp_path)

    uploaded = service.upload_attachment(
        tenant_id="tenant-a",
        organization_id="org-a",
        object_type="project",
        object_id="project-1",
        filename="archive-me.pdf",
        data=b"archive-me",
        mime_type="application/pdf",
        actor_id="user-a",
        project_id="project-1",
    )
    attachment_id = uploaded["attachment"]["attachment_id"]
    link_id = uploaded["link"]["link_id"]

    archived = service.archive_attachment(
        tenant_id="tenant-a",
        organization_id="org-a",
        attachment_id=attachment_id,
        actor_id="user-a",
        project_id="project-1",
    )
    restored = service.restore_attachment(
        tenant_id="tenant-a",
        organization_id="org-a",
        attachment_id=attachment_id,
        actor_id="user-a",
        project_id="project-1",
    )

    assert archived["status"] == "archived"
    assert restored["status"] == "active"

    with pytest.raises(ValueError, match="still referenced"):
        service.purge_attachment(
            tenant_id="tenant-a",
            organization_id="org-a",
            attachment_id=attachment_id,
        )

    service.unlink_attachment(
        tenant_id="tenant-a",
        organization_id="org-a",
        link_id=link_id,
        actor_id="user-a",
        project_id="project-1",
    )

    with pytest.raises(ValueError, match="intentionally unsupported"):
        service.purge_attachment(
            tenant_id="tenant-a",
            organization_id="org-a",
            attachment_id=attachment_id,
        )


def test_attachment_permissions_are_enforced(tmp_path: Path) -> None:
    service = _build_attachment_service(tmp_path)
    denied = AttachmentAccessDecision(
        allowed=False,
        permission_key="projects.edit",
        reason="denied",
    )

    with pytest.raises(PermissionError, match="denied"):
        service.upload_attachment(
            tenant_id="tenant-a",
            organization_id="org-a",
            object_type="project",
            object_id="project-1",
            filename="blocked.pdf",
            data=b"payload",
            mime_type="application/pdf",
            actor_id="user-a",
            access_decision=denied,
            project_id="project-1",
        )


def test_attachment_validation_rejects_unsafe_inputs(tmp_path: Path) -> None:
    service = _build_attachment_service(tmp_path, max_size_bytes=4)

    with pytest.raises(ValueError, match="prohibited credential material"):
        service.upload_attachment(
            tenant_id="tenant-a",
            organization_id="org-a",
            object_type="project",
            object_id="project-1",
            filename="id_rsa.txt",
            data=b"payload",
            mime_type="text/plain",
            actor_id="user-a",
        )

    with pytest.raises(ValueError, match="mime_type is not allowed"):
        service.upload_attachment(
            tenant_id="tenant-a",
            organization_id="org-a",
            object_type="project",
            object_id="project-1",
            filename="bad.pdf",
            data=b"payload",
            mime_type="application/x-msdownload",
            actor_id="user-a",
        )

    with pytest.raises(ValueError, match="file extension is not allowed"):
        service.upload_attachment(
            tenant_id="tenant-a",
            organization_id="org-a",
            object_type="project",
            object_id="project-1",
            filename="bad.exe",
            data=b"1234",
            mime_type="application/pdf",
            actor_id="user-a",
        )

    with pytest.raises(ValueError, match="cannot be empty"):
        service.upload_attachment(
            tenant_id="tenant-a",
            organization_id="org-a",
            object_type="project",
            object_id="project-1",
            filename="empty.txt",
            data=b"",
            mime_type="text/plain",
            actor_id="user-a",
        )

    with pytest.raises(ValueError, match="maximum allowed size"):
        service.upload_attachment(
            tenant_id="tenant-a",
            organization_id="org-a",
            object_type="project",
            object_id="project-1",
            filename="big.txt",
            data=b"12345",
            mime_type="text/plain",
            actor_id="user-a",
        )


def test_attachment_tenant_scope_isolation(tmp_path: Path) -> None:
    service = _build_attachment_service(tmp_path)

    uploaded = service.upload_attachment(
        tenant_id="tenant-a",
        organization_id="org-a",
        object_type="project",
        object_id="project-1",
        filename="tenant-a.pdf",
        data=b"tenant-a",
        mime_type="application/pdf",
        actor_id="user-a",
    )

    mismatched_rows = service.list_object_attachments(
        tenant_id="tenant-b",
        organization_id="org-a",
        object_type="project",
        object_id="project-1",
        include_archived=True,
        limit=50,
    )

    assert mismatched_rows == []

    with pytest.raises(ValueError, match="attachment was not found"):
        service.read_attachment_version(
            tenant_id="tenant-b",
            organization_id="org-a",
            attachment_id=uploaded["attachment"]["attachment_id"],
            actor_id="user-a",
        )


def test_attachment_audit_and_background_hooks_are_emitted(tmp_path: Path) -> None:
    audit_events: list[dict[str, Any]] = []
    hooks: list[dict[str, Any]] = []
    service = _build_attachment_service(
        tmp_path,
        audit_events=audit_events,
        hooks=hooks,
    )

    uploaded = service.upload_attachment(
        tenant_id="tenant-a",
        organization_id="org-a",
        object_type="project",
        object_id="project-1",
        filename="audit.pdf",
        data=b"audit",
        mime_type="application/pdf",
        actor_id="user-a",
        project_id="project-1",
    )
    service.read_attachment_version(
        tenant_id="tenant-a",
        organization_id="org-a",
        attachment_id=uploaded["attachment"]["attachment_id"],
        actor_id="user-a",
        project_id="project-1",
    )

    actions = {str(item.get("action")) for item in audit_events}
    assert "attachment.uploaded" in actions
    assert "attachment.linked" in actions
    assert "attachment.downloaded" in actions
    assert len(hooks) == 3
    assert {item.get("hook") for item in hooks} == {
        "malware_scan",
        "preview_generation",
        "search_indexing",
    }


def test_workspace_service_registers_existing_project_documents_as_attachments(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="project-doc-sync",
        name="Project Doc Sync",
        client="Atlas",
    )
    service.save_record(record)

    project_root = Path(service.project_location(record.workspace_id))
    document_file = project_root / "documents" / "other" / "legacy.pdf"
    document_file.parent.mkdir(parents=True, exist_ok=True)
    document_file.write_bytes(b"legacy-pdf")

    linked = service.link_existing_project_documents_as_attachments(record.workspace_id)
    rows = service.list_object_attachments(
        tenant_id="local",
        organization_id="atlas",
        object_type="project",
        object_id=record.workspace_id,
        include_archived=True,
        limit=50,
    )

    assert linked
    assert any(item.get("filename") == "legacy.pdf" for item in rows)


def test_import_uploaded_documents_populates_attachment_compatibility_links(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="project-import-sync",
        name="Project Import Sync",
        client="Atlas",
    )
    service.save_record(record)

    service.import_uploaded_documents(
        workspace_id=record.workspace_id,
        uploaded_files=[("imported.txt", b"hello")],
    )

    rows = service.list_object_attachments(
        tenant_id="local",
        organization_id="atlas",
        object_type="project",
        object_id=record.workspace_id,
        include_archived=True,
        limit=50,
    )

    assert any(item.get("filename") == "imported.txt" for item in rows)

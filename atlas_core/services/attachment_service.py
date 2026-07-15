"""Unified tenant-scoped attachment orchestration for Atlas objects."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Callable, Protocol

from atlas_core.contracts.attachment_contracts import (
    AttachmentAccessDecision,
    AttachmentActivity,
    AttachmentLink,
    AttachmentMetadata,
    AttachmentRecord,
    AttachmentScanStatus,
    AttachmentStatus,
    AttachmentVersion,
    now_iso,
)


class AttachmentRepositoryProtocol(Protocol):
    def save_attachment(
        self,
        tenant_id: str,
        organization_id: str,
        attachment_payload: dict[str, Any],
    ) -> None: ...

    def load_attachment(
        self,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
    ) -> dict[str, Any] | None: ...

    def list_attachments(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        include_archived: bool = True,
        limit: int = 1000,
    ) -> list[dict[str, Any]]: ...

    def find_attachment_by_hash(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        file_hash: str,
        size_bytes: int,
    ) -> dict[str, Any] | None: ...

    def write_blob(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        attachment_id: str,
        version_id: str,
        filename: str,
        data: bytes,
    ) -> str: ...

    def read_blob(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        storage_reference: str,
    ) -> bytes: ...

    def save_link(
        self,
        tenant_id: str,
        organization_id: str,
        link_payload: dict[str, Any],
    ) -> None: ...

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
    ) -> list[dict[str, Any]]: ...

    def save_activity(
        self,
        tenant_id: str,
        organization_id: str,
        activity_payload: dict[str, Any],
    ) -> None: ...

    def list_activity(
        self,
        tenant_id: str,
        organization_id: str,
        *,
        attachment_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]: ...


DEFAULT_ALLOWED_MIME_TYPES: tuple[str, ...] = (
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "image/png",
    "image/jpeg",
    "image/webp",
)

DEFAULT_ALLOWED_EXTENSIONS: tuple[str, ...] = (
    ".pdf",
    ".txt",
    ".csv",
    ".json",
    ".xlsx",
    ".xls",
    ".docx",
    ".doc",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
)

PROHIBITED_FILENAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(^|[._-])(id_rsa|id_dsa|id_ed25519)($|[._-])", re.IGNORECASE),
    re.compile(
        r"(^|[._-])(secret|token|password|credential|private[_-]?key)($|[._-])",
        re.IGNORECASE,
    ),
    re.compile(r"\.(pem|key|p12|pfx|env)$", re.IGNORECASE),
)


class AttachmentService:
    def __init__(
        self,
        *,
        repository: AttachmentRepositoryProtocol,
        audit_callback: Callable[..., dict[str, Any]] | None = None,
        background_hook: Callable[[dict[str, Any]], None] | None = None,
        max_size_bytes: int = 25 * 1024 * 1024,
        allowed_mime_types: tuple[str, ...] = DEFAULT_ALLOWED_MIME_TYPES,
        allowed_extensions: tuple[str, ...] = DEFAULT_ALLOWED_EXTENSIONS,
    ) -> None:
        self.repository = repository
        self.audit_callback = audit_callback
        self.background_hook = background_hook
        self.max_size_bytes = int(max_size_bytes)
        self.allowed_mime_types = {
            str(item).strip().lower() for item in allowed_mime_types
        }
        self.allowed_extensions = {
            str(item).strip().lower() for item in allowed_extensions
        }

    def upload_attachment(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        object_type: str,
        object_id: str,
        filename: str,
        data: bytes,
        mime_type: str,
        actor_id: str,
        source: str = "manual_upload",
        source_reference: str | None = None,
        provenance: dict[str, Any] | None = None,
        access_decision: AttachmentAccessDecision | None = None,
        project_id: str | None = None,
        allow_shared_reference: bool = True,
        emit_background_hooks: bool = True,
    ) -> dict[str, Any]:
        self._assert_scope(tenant_id=tenant_id, organization_id=organization_id)
        self._assert_access(access_decision)
        safe_name = self._validated_filename(filename)
        payload = bytes(data or b"")
        mime = self._validated_mime_type(mime_type)
        self._validate_size(len(payload))
        ext = self._extension_for_filename(safe_name)
        if ext not in self.allowed_extensions:
            raise ValueError("file extension is not allowed")

        file_hash = hashlib.sha1(payload).hexdigest()
        duplicate_payload = self.repository.find_attachment_by_hash(
            tenant_id,
            organization_id,
            file_hash=file_hash,
            size_bytes=len(payload),
        )
        duplicate_record = (
            AttachmentRecord.from_dict(duplicate_payload)
            if isinstance(duplicate_payload, dict)
            else None
        )

        if duplicate_record is not None:
            link = self.link_attachment(
                tenant_id=tenant_id,
                organization_id=organization_id,
                attachment_id=duplicate_record.attachment_id,
                object_type=object_type,
                object_id=object_id,
                actor_id=actor_id,
                provenance={
                    **dict(provenance or {}),
                    "link_reason": "duplicate_reuse",
                    "source": source,
                },
                access_decision=access_decision,
                project_id=project_id,
            )
            return {
                "attachment": duplicate_record.to_dict(),
                "link": link,
                "duplicate_detected": True,
                "background_hooks": [],
            }

        attachment_id = self._stable_attachment_id(
            tenant_id=tenant_id,
            organization_id=organization_id,
            file_hash=file_hash,
            mime_type=mime,
            size_bytes=len(payload),
        )
        version_id = self._stable_version_id(
            attachment_id=attachment_id,
            version_number=1,
            file_hash=file_hash,
        )
        storage_reference = self.repository.write_blob(
            tenant_id,
            organization_id,
            attachment_id=attachment_id,
            version_id=version_id,
            filename=safe_name,
            data=payload,
        )
        metadata = AttachmentMetadata(
            filename=safe_name,
            mime_type=mime,
            size_bytes=len(payload),
            file_hash=file_hash,
            source=source,
            source_reference=source_reference,
            uploaded_by=actor_id,
            uploaded_at=now_iso(),
            scan_status=AttachmentScanStatus.PENDING,
            extra={"original_filename": filename},
        )
        version = AttachmentVersion(
            version_id=version_id,
            version_number=1,
            metadata=metadata,
            storage_reference=storage_reference,
            created_by=actor_id,
        )
        record = AttachmentRecord(
            attachment_id=attachment_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            status=AttachmentStatus.ACTIVE,
            created_at=now_iso(),
            updated_at=now_iso(),
            created_by=actor_id,
            shared_reference_allowed=bool(allow_shared_reference),
            current_version_id=version_id,
            versions=[version],
            metadata={
                "object_origin": {
                    "object_type": object_type,
                    "object_id": object_id,
                }
            },
        )
        self.repository.save_attachment(tenant_id, organization_id, record.to_dict())

        link = self.link_attachment(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
            object_type=object_type,
            object_id=object_id,
            actor_id=actor_id,
            provenance=dict(provenance or {}),
            access_decision=access_decision,
            project_id=project_id,
        )

        audit_id = self._audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            action="attachment.uploaded",
            actor_id=actor_id,
            target_id=attachment_id,
            after={
                "object_type": object_type,
                "object_id": object_id,
                "filename": safe_name,
                "mime_type": mime,
                "size_bytes": len(payload),
                "file_hash": file_hash,
            },
        )
        self._append_activity(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
            event_type="attachment_uploaded",
            actor_id=actor_id,
            summary=f"Uploaded {safe_name}",
            context={
                "mime_type": mime,
                "size_bytes": len(payload),
                "object_type": object_type,
                "object_id": object_id,
            },
            audit_event_id=audit_id,
        )
        hooks = (
            self._emit_background_hooks(
                tenant_id=tenant_id,
                organization_id=organization_id,
                attachment_id=attachment_id,
                actor_id=actor_id,
                event_type="uploaded",
            )
            if emit_background_hooks
            else []
        )
        return {
            "attachment": record.to_dict(),
            "link": link,
            "duplicate_detected": False,
            "background_hooks": hooks,
        }

    def create_attachment_version(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
        filename: str,
        data: bytes,
        mime_type: str,
        actor_id: str,
        source: str = "version_upload",
        source_reference: str | None = None,
        access_decision: AttachmentAccessDecision | None = None,
        project_id: str | None = None,
        emit_background_hooks: bool = True,
    ) -> dict[str, Any]:
        self._assert_scope(tenant_id=tenant_id, organization_id=organization_id)
        self._assert_access(access_decision)
        safe_name = self._validated_filename(filename)
        payload = bytes(data or b"")
        mime = self._validated_mime_type(mime_type)
        self._validate_size(len(payload))
        ext = self._extension_for_filename(safe_name)
        if ext not in self.allowed_extensions:
            raise ValueError("file extension is not allowed")

        record = self._required_attachment(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
        )
        version_number = max(1, len(record.versions) + 1)
        file_hash = hashlib.sha1(payload).hexdigest()
        version_id = self._stable_version_id(
            attachment_id=attachment_id,
            version_number=version_number,
            file_hash=file_hash,
        )
        storage_reference = self.repository.write_blob(
            tenant_id,
            organization_id,
            attachment_id=attachment_id,
            version_id=version_id,
            filename=safe_name,
            data=payload,
        )
        metadata = AttachmentMetadata(
            filename=safe_name,
            mime_type=mime,
            size_bytes=len(payload),
            file_hash=file_hash,
            source=source,
            source_reference=source_reference,
            uploaded_by=actor_id,
            uploaded_at=now_iso(),
            scan_status=AttachmentScanStatus.PENDING,
            extra={"original_filename": filename},
        )
        version = AttachmentVersion(
            version_id=version_id,
            version_number=version_number,
            metadata=metadata,
            storage_reference=storage_reference,
            created_by=actor_id,
        )
        updated = AttachmentRecord.from_dict(
            {
                **record.to_dict(),
                "updated_at": now_iso(),
                "current_version_id": version_id,
                "versions": [
                    *[item.to_dict() for item in record.versions],
                    version.to_dict(),
                ],
            }
        )
        self.repository.save_attachment(tenant_id, organization_id, updated.to_dict())
        audit_id = self._audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            action="attachment.version.created",
            actor_id=actor_id,
            target_id=attachment_id,
            after={
                "version_id": version_id,
                "version_number": version_number,
                "filename": safe_name,
                "mime_type": mime,
            },
        )
        self._append_activity(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
            event_type="attachment_version_created",
            actor_id=actor_id,
            summary=f"Created version {version_number}",
            context={"version_id": version_id, "version_number": version_number},
            audit_event_id=audit_id,
        )
        hooks = (
            self._emit_background_hooks(
                tenant_id=tenant_id,
                organization_id=organization_id,
                attachment_id=attachment_id,
                actor_id=actor_id,
                event_type="version_created",
            )
            if emit_background_hooks
            else []
        )
        return {
            "attachment": updated.to_dict(),
            "version": version.to_dict(),
            "background_hooks": hooks,
        }

    def link_attachment(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
        object_type: str,
        object_id: str,
        actor_id: str,
        provenance: dict[str, Any] | None = None,
        access_decision: AttachmentAccessDecision | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        self._assert_scope(tenant_id=tenant_id, organization_id=organization_id)
        self._assert_access(access_decision)
        record = self._required_attachment(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
        )
        normalized_object_type = self._safe_text(object_type)
        normalized_object_id = self._safe_text(object_id)
        active_links = self.list_links(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
            include_inactive=False,
        )
        if not record.shared_reference_allowed:
            for item in active_links:
                if (
                    self._safe_text(item.get("object_type")) != normalized_object_type
                    or self._safe_text(item.get("object_id")) != normalized_object_id
                ):
                    raise ValueError("attachment does not allow shared references")

        existing = next(
            (
                item
                for item in active_links
                if self._safe_text(item.get("object_type")) == normalized_object_type
                and self._safe_text(item.get("object_id")) == normalized_object_id
            ),
            None,
        )
        if existing is not None:
            return dict(existing)

        link_id = self._stable_link_id(
            attachment_id=attachment_id,
            object_type=normalized_object_type,
            object_id=normalized_object_id,
        )
        link = AttachmentLink(
            link_id=link_id,
            attachment_id=attachment_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            object_type=normalized_object_type,
            object_id=normalized_object_id,
            linked_by=actor_id,
            linked_at=now_iso(),
            provenance=dict(provenance or {}),
            active=True,
        )
        self.repository.save_link(tenant_id, organization_id, link.to_dict())
        self._append_activity(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
            event_type="attachment_linked",
            actor_id=actor_id,
            summary=f"Linked to {normalized_object_type}:{normalized_object_id}",
            context={
                "link_id": link_id,
                "object_type": normalized_object_type,
                "object_id": normalized_object_id,
            },
            audit_event_id=self._audit(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                action="attachment.linked",
                actor_id=actor_id,
                target_id=attachment_id,
                after={
                    "link_id": link_id,
                    "object_type": normalized_object_type,
                    "object_id": normalized_object_id,
                },
            ),
        )
        return link.to_dict()

    def unlink_attachment(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        link_id: str,
        actor_id: str,
        access_decision: AttachmentAccessDecision | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        self._assert_scope(tenant_id=tenant_id, organization_id=organization_id)
        self._assert_access(access_decision)
        links = self.repository.list_links(
            tenant_id,
            organization_id,
            include_inactive=True,
            limit=5000,
        )
        current = next(
            (
                AttachmentLink.from_dict(item)
                for item in links
                if self._safe_text(dict(item).get("link_id"))
                == self._safe_text(link_id)
            ),
            None,
        )
        if current is None:
            raise ValueError("attachment link was not found")
        if not current.active:
            return current.to_dict()

        updated = AttachmentLink.from_dict(
            {
                **current.to_dict(),
                "active": False,
                "unlinked_at": now_iso(),
            }
        )
        self.repository.save_link(tenant_id, organization_id, updated.to_dict())
        self._append_activity(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=current.attachment_id,
            event_type="attachment_unlinked",
            actor_id=actor_id,
            summary=f"Unlinked {current.object_type}:{current.object_id}",
            context={"link_id": current.link_id},
            audit_event_id=self._audit(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                action="attachment.unlinked",
                actor_id=actor_id,
                target_id=current.attachment_id,
                after={"link_id": current.link_id},
            ),
        )
        return updated.to_dict()

    def archive_attachment(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
        actor_id: str,
        access_decision: AttachmentAccessDecision | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        return self._set_attachment_status(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
            actor_id=actor_id,
            status=AttachmentStatus.ARCHIVED,
            access_decision=access_decision,
            project_id=project_id,
            action="attachment.archived",
            event_type="attachment_archived",
        )

    def restore_attachment(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
        actor_id: str,
        access_decision: AttachmentAccessDecision | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        return self._set_attachment_status(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
            actor_id=actor_id,
            status=AttachmentStatus.ACTIVE,
            access_decision=access_decision,
            project_id=project_id,
            action="attachment.restored",
            event_type="attachment_restored",
        )

    def purge_attachment(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
    ) -> None:
        active_links = self.list_links(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
            include_inactive=False,
        )
        if active_links:
            raise ValueError("attachment is still referenced and cannot be deleted")
        raise ValueError(
            "attachment purge is intentionally unsupported in local deterministic mode"
        )

    def list_object_attachments(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        object_type: str,
        object_id: str,
        include_archived: bool = True,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        normalized_object_type = self._safe_text(object_type)
        normalized_object_id = self._safe_text(object_id)
        links = self.list_links(
            tenant_id=tenant_id,
            organization_id=organization_id,
            object_type=normalized_object_type,
            object_id=normalized_object_id,
            include_inactive=False,
        )
        by_attachment = {
            self._safe_text(item.get("attachment_id")): item for item in links
        }
        rows: list[dict[str, Any]] = []
        for attachment in self.repository.list_attachments(
            tenant_id,
            organization_id,
            include_archived=include_archived,
            limit=max(int(limit) * 5, 500),
        ):
            attachment_id = self._safe_text(dict(attachment).get("attachment_id"))
            link = by_attachment.get(attachment_id)
            if link is None:
                continue
            record = AttachmentRecord.from_dict(dict(attachment))
            current_version = self._current_version(record)
            if current_version is None:
                continue
            rows.append(
                {
                    "attachment_id": record.attachment_id,
                    "link_id": self._safe_text(link.get("link_id")),
                    "filename": current_version.metadata.filename,
                    "mime_type": current_version.metadata.mime_type,
                    "version_number": current_version.version_number,
                    "uploaded_by": current_version.created_by,
                    "uploaded_at": current_version.metadata.uploaded_at,
                    "status": record.status.value,
                    "linked_object": f"{normalized_object_type}:{normalized_object_id}",
                    "storage_reference": self._redacted_storage_reference(
                        current_version.storage_reference
                    ),
                    "scan_status": current_version.metadata.scan_status.value,
                }
            )
        rows.sort(
            key=lambda item: (
                self._safe_text(item.get("uploaded_at")),
                self._safe_text(item.get("attachment_id")),
            ),
            reverse=True,
        )
        return rows[: max(1, int(limit))]

    def list_links(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str | None = None,
        object_type: str | None = None,
        object_id: str | None = None,
        include_inactive: bool = False,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        rows = self.repository.list_links(
            tenant_id,
            organization_id,
            attachment_id=attachment_id,
            object_type=object_type,
            object_id=object_id,
            include_inactive=include_inactive,
            limit=limit,
        )
        return [AttachmentLink.from_dict(dict(item)).to_dict() for item in rows]

    def read_attachment_version(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
        version_id: str | None = None,
        access_decision: AttachmentAccessDecision | None = None,
        project_id: str | None = None,
        actor_id: str = "atlas-ui",
    ) -> dict[str, Any]:
        self._assert_access(access_decision)
        record = self._required_attachment(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
        )
        version = self._resolved_version(record, version_id)
        data = self.repository.read_blob(
            tenant_id,
            organization_id,
            storage_reference=version.storage_reference,
        )
        audit_id = self._audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            action="attachment.downloaded",
            actor_id=actor_id,
            target_id=attachment_id,
            after={"version_id": version.version_id},
        )
        self._append_activity(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
            event_type="attachment_downloaded",
            actor_id=actor_id,
            summary=f"Downloaded {version.metadata.filename}",
            context={"version_id": version.version_id},
            audit_event_id=audit_id,
        )
        return {
            "attachment_id": record.attachment_id,
            "version_id": version.version_id,
            "filename": version.metadata.filename,
            "mime_type": version.metadata.mime_type,
            "size_bytes": version.metadata.size_bytes,
            "data": data,
            "storage_reference": self._redacted_storage_reference(
                version.storage_reference
            ),
        }

    def register_existing_file_reference(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        object_type: str,
        object_id: str,
        filename: str,
        data: bytes,
        mime_type: str,
        actor_id: str,
        source_reference: str,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        return self.upload_attachment(
            tenant_id=tenant_id,
            organization_id=organization_id,
            object_type=object_type,
            object_id=object_id,
            filename=filename,
            data=data,
            mime_type=mime_type,
            actor_id=actor_id,
            source="legacy_project_documents",
            source_reference=source_reference,
            provenance={"compatibility_adapter": "project_documents"},
            project_id=project_id,
            allow_shared_reference=True,
            emit_background_hooks=False,
        )

    @staticmethod
    def decision_from_permissions(
        *,
        allowed: bool,
        permission_key: str,
        reason: str | None = None,
        decision_code: str | None = None,
        surface: str | None = None,
    ) -> AttachmentAccessDecision:
        return AttachmentAccessDecision(
            allowed=allowed,
            permission_key=permission_key,
            reason=reason,
            decision_code=decision_code,
            surface=surface,
        )

    def _required_attachment(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
    ) -> AttachmentRecord:
        payload = self.repository.load_attachment(
            tenant_id,
            organization_id,
            self._safe_text(attachment_id),
        )
        if not isinstance(payload, dict):
            raise ValueError("attachment was not found")
        return AttachmentRecord.from_dict(payload)

    @staticmethod
    def _safe_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        if not isinstance(value, str):
            value = str(value)
        normalized = value.strip()
        return normalized or default

    def _set_attachment_status(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
        actor_id: str,
        status: AttachmentStatus,
        access_decision: AttachmentAccessDecision | None,
        project_id: str | None,
        action: str,
        event_type: str,
    ) -> dict[str, Any]:
        self._assert_scope(tenant_id=tenant_id, organization_id=organization_id)
        self._assert_access(access_decision)
        record = self._required_attachment(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
        )
        if record.status == status:
            return record.to_dict()
        updated = AttachmentRecord.from_dict(
            {
                **record.to_dict(),
                "status": status.value,
                "updated_at": now_iso(),
            }
        )
        self.repository.save_attachment(tenant_id, organization_id, updated.to_dict())
        audit_id = self._audit(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            action=action,
            actor_id=actor_id,
            target_id=attachment_id,
            after={"status": status.value},
        )
        self._append_activity(
            tenant_id=tenant_id,
            organization_id=organization_id,
            attachment_id=attachment_id,
            event_type=event_type,
            actor_id=actor_id,
            summary=f"Attachment {status.value}",
            context={"status": status.value},
            audit_event_id=audit_id,
        )
        return updated.to_dict()

    def _assert_scope(self, *, tenant_id: str, organization_id: str) -> None:
        if not self._safe_text(tenant_id):
            raise ValueError("tenant_id is required")
        if not self._safe_text(organization_id):
            raise ValueError("organization_id is required")

    @staticmethod
    def _assert_access(access_decision: AttachmentAccessDecision | None) -> None:
        if access_decision is None:
            return
        if access_decision.allowed:
            return
        message = access_decision.reason or "attachment operation was denied"
        raise PermissionError(message)

    def _validated_filename(self, filename: str) -> str:
        normalized = self._safe_text(filename)
        if not normalized:
            raise ValueError("filename is required")
        if "/" in normalized or "\\" in normalized or ".." in normalized:
            raise ValueError("unsafe filename")
        for pattern in PROHIBITED_FILENAME_PATTERNS:
            if pattern.search(normalized):
                raise ValueError(
                    "filename appears to contain prohibited credential material"
                )
        return normalized

    def _validated_mime_type(self, mime_type: str) -> str:
        normalized = self._safe_text(mime_type).lower()
        if not normalized:
            raise ValueError("mime_type is required")
        if normalized not in self.allowed_mime_types:
            raise ValueError("mime_type is not allowed")
        return normalized

    def _validate_size(self, size_bytes: int) -> None:
        if int(size_bytes) <= 0:
            raise ValueError("attachment payload cannot be empty")
        if int(size_bytes) > self.max_size_bytes:
            raise ValueError("attachment exceeds maximum allowed size")

    @staticmethod
    def _extension_for_filename(filename: str) -> str:
        lowered = filename.lower()
        index = lowered.rfind(".")
        if index <= 0:
            return ""
        return lowered[index:]

    @staticmethod
    def _stable_attachment_id(
        *,
        tenant_id: str,
        organization_id: str,
        file_hash: str,
        mime_type: str,
        size_bytes: int,
    ) -> str:
        token = json.dumps(
            {
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "file_hash": file_hash,
                "mime_type": mime_type,
                "size_bytes": int(size_bytes),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return f"attachment:{hashlib.sha1(token.encode('utf-8')).hexdigest()[:20]}"

    @staticmethod
    def _stable_version_id(
        *,
        attachment_id: str,
        version_number: int,
        file_hash: str,
    ) -> str:
        token = f"{attachment_id}|{int(version_number)}|{file_hash}"
        return f"version:{hashlib.sha1(token.encode('utf-8')).hexdigest()[:20]}"

    @staticmethod
    def _stable_link_id(
        *,
        attachment_id: str,
        object_type: str,
        object_id: str,
    ) -> str:
        token = f"{attachment_id}|{object_type}|{object_id}"
        return f"link:{hashlib.sha1(token.encode('utf-8')).hexdigest()[:20]}"

    @staticmethod
    def _stable_activity_id(
        *,
        attachment_id: str,
        event_type: str,
        actor_id: str,
        occurred_at: str,
    ) -> str:
        token = f"{attachment_id}|{event_type}|{actor_id}|{occurred_at}"
        return f"attachment-activity:{hashlib.sha1(token.encode('utf-8')).hexdigest()[:20]}"

    @staticmethod
    def _redacted_storage_reference(storage_reference: str) -> str:
        value = str(storage_reference or "")
        if not value:
            return ""
        segments = [item for item in value.replace("\\", "/").split("/") if item]
        if len(segments) <= 2:
            return value
        return f".../{segments[-2]}/{segments[-1]}"

    @staticmethod
    def _current_version(record: AttachmentRecord) -> AttachmentVersion | None:
        if not record.versions:
            return None
        if record.current_version_id:
            for item in record.versions:
                if item.version_id == record.current_version_id:
                    return item
        return sorted(record.versions, key=lambda item: item.version_number)[-1]

    def _resolved_version(
        self,
        record: AttachmentRecord,
        version_id: str | None,
    ) -> AttachmentVersion:
        if version_id is not None:
            for item in record.versions:
                if item.version_id == self._safe_text(version_id):
                    return item
            raise ValueError("attachment version was not found")
        current = self._current_version(record)
        if current is None:
            raise ValueError("attachment has no versions")
        return current

    def _append_activity(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
        event_type: str,
        actor_id: str,
        summary: str,
        context: dict[str, Any],
        audit_event_id: str | None,
    ) -> None:
        occurred_at = now_iso()
        activity = AttachmentActivity(
            activity_id=self._stable_activity_id(
                attachment_id=attachment_id,
                event_type=event_type,
                actor_id=actor_id,
                occurred_at=occurred_at,
            ),
            attachment_id=attachment_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            event_type=event_type,
            actor_id=actor_id,
            occurred_at=occurred_at,
            summary=summary,
            context=deepcopy(context),
            audit_event_id=audit_event_id,
        )
        self.repository.save_activity(tenant_id, organization_id, activity.to_dict())

    def _audit(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str | None,
        action: str,
        actor_id: str,
        target_id: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> str | None:
        if self.audit_callback is None:
            return None
        if not self._safe_text(project_id):
            return None
        emitted = self.audit_callback(
            project_id=self._safe_text(project_id),
            action=action,
            actor_id=actor_id,
            actor_type="user",
            tenant_id=tenant_id,
            organization_id=organization_id,
            target_type="attachment",
            target_id=target_id,
            source="attachment_service",
            before=deepcopy(before or {}),
            after=deepcopy(after or {}),
            context=deepcopy(context or {}),
        )
        return self._safe_text(dict(emitted or {}).get("event_id"), "") or None

    def _emit_background_hooks(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        attachment_id: str,
        actor_id: str,
        event_type: str,
    ) -> list[dict[str, Any]]:
        hook_requests = [
            {
                "hook": "malware_scan",
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "attachment_id": attachment_id,
                "event_type": event_type,
                "actor_id": actor_id,
            },
            {
                "hook": "preview_generation",
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "attachment_id": attachment_id,
                "event_type": event_type,
                "actor_id": actor_id,
            },
            {
                "hook": "search_indexing",
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "attachment_id": attachment_id,
                "event_type": event_type,
                "actor_id": actor_id,
            },
        ]
        if self.background_hook is None:
            return hook_requests
        for item in hook_requests:
            self.background_hook(dict(item))
        return hook_requests

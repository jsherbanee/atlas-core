"""Unified tenant-scoped attachment contracts for Atlas objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def _required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    return normalized or None


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class AttachmentStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AttachmentScanStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True)
class AttachmentMetadata:
    filename: str
    mime_type: str
    size_bytes: int
    file_hash: str
    source: str = "manual_upload"
    source_reference: str | None = None
    uploaded_by: str | None = None
    uploaded_at: str = field(default_factory=now_iso)
    scan_status: AttachmentScanStatus = AttachmentScanStatus.NOT_REQUESTED
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "filename", _required_text("filename", self.filename))
        object.__setattr__(
            self, "mime_type", _required_text("mime_type", self.mime_type).lower()
        )
        if int(self.size_bytes) < 0:
            raise ValueError("size_bytes must be >= 0")
        object.__setattr__(self, "size_bytes", int(self.size_bytes))
        object.__setattr__(
            self, "file_hash", _required_text("file_hash", self.file_hash).lower()
        )
        object.__setattr__(self, "source", _required_text("source", self.source))
        object.__setattr__(
            self, "source_reference", _optional_text(self.source_reference)
        )
        object.__setattr__(self, "uploaded_by", _optional_text(self.uploaded_by))
        object.__setattr__(
            self, "uploaded_at", _required_text("uploaded_at", self.uploaded_at)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "mime_type": self.mime_type,
            "size_bytes": int(self.size_bytes),
            "file_hash": self.file_hash,
            "source": self.source,
            "source_reference": self.source_reference,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at,
            "scan_status": self.scan_status.value,
            "extra": dict(self.extra),
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "AttachmentMetadata":
        return AttachmentMetadata(
            filename=str(payload.get("filename") or ""),
            mime_type=str(payload.get("mime_type") or "application/octet-stream"),
            size_bytes=int(payload.get("size_bytes") or 0),
            file_hash=str(payload.get("file_hash") or ""),
            source=str(payload.get("source") or "manual_upload"),
            source_reference=payload.get("source_reference"),
            uploaded_by=payload.get("uploaded_by"),
            uploaded_at=str(payload.get("uploaded_at") or now_iso()),
            scan_status=AttachmentScanStatus(
                str(
                    payload.get("scan_status")
                    or AttachmentScanStatus.NOT_REQUESTED.value
                )
            ),
            extra=dict(payload.get("extra") or {}),
        )


@dataclass(frozen=True)
class AttachmentDiagnostic:
    code: str
    message: str
    severity: str = "error"
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _required_text("code", self.code))
        object.__setattr__(self, "message", _required_text("message", self.message))
        normalized = _required_text("severity", self.severity).lower()
        if normalized not in {"error", "warning", "informational"}:
            raise ValueError("severity must be error, warning, or informational")
        object.__setattr__(self, "severity", normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "details": dict(self.details),
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "AttachmentDiagnostic":
        return AttachmentDiagnostic(
            code=str(payload.get("code") or ""),
            message=str(payload.get("message") or ""),
            severity=str(payload.get("severity") or "error"),
            details=dict(payload.get("details") or {}),
        )


@dataclass(frozen=True)
class AttachmentVersion:
    version_id: str
    version_number: int
    metadata: AttachmentMetadata
    storage_reference: str
    created_at: str = field(default_factory=now_iso)
    created_by: str | None = None
    immutable: bool = True
    diagnostics: list[AttachmentDiagnostic] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "version_id", _required_text("version_id", self.version_id)
        )
        if int(self.version_number) <= 0:
            raise ValueError("version_number must be >= 1")
        object.__setattr__(self, "version_number", int(self.version_number))
        object.__setattr__(
            self,
            "storage_reference",
            _required_text("storage_reference", self.storage_reference),
        )
        object.__setattr__(
            self, "created_at", _required_text("created_at", self.created_at)
        )
        object.__setattr__(self, "created_by", _optional_text(self.created_by))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "version_number": int(self.version_number),
            "metadata": self.metadata.to_dict(),
            "storage_reference": self.storage_reference,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "immutable": bool(self.immutable),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "AttachmentVersion":
        return AttachmentVersion(
            version_id=str(payload.get("version_id") or ""),
            version_number=int(payload.get("version_number") or 1),
            metadata=AttachmentMetadata.from_dict(dict(payload.get("metadata") or {})),
            storage_reference=str(payload.get("storage_reference") or ""),
            created_at=str(payload.get("created_at") or now_iso()),
            created_by=payload.get("created_by"),
            immutable=bool(payload.get("immutable", True)),
            diagnostics=[
                AttachmentDiagnostic.from_dict(dict(item))
                for item in list(payload.get("diagnostics") or [])
                if isinstance(item, dict)
            ],
        )


@dataclass(frozen=True)
class AttachmentLink:
    link_id: str
    attachment_id: str
    tenant_id: str
    organization_id: str
    object_type: str
    object_id: str
    linked_by: str
    linked_at: str = field(default_factory=now_iso)
    provenance: dict[str, Any] = field(default_factory=dict)
    active: bool = True
    unlinked_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "link_id", _required_text("link_id", self.link_id))
        object.__setattr__(
            self, "attachment_id", _required_text("attachment_id", self.attachment_id)
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )
        object.__setattr__(
            self, "object_type", _required_text("object_type", self.object_type)
        )
        object.__setattr__(
            self, "object_id", _required_text("object_id", self.object_id)
        )
        object.__setattr__(
            self, "linked_by", _required_text("linked_by", self.linked_by)
        )
        object.__setattr__(
            self, "linked_at", _required_text("linked_at", self.linked_at)
        )
        object.__setattr__(self, "unlinked_at", _optional_text(self.unlinked_at))

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "attachment_id": self.attachment_id,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "linked_by": self.linked_by,
            "linked_at": self.linked_at,
            "provenance": dict(self.provenance),
            "active": bool(self.active),
            "unlinked_at": self.unlinked_at,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "AttachmentLink":
        return AttachmentLink(
            link_id=str(payload.get("link_id") or ""),
            attachment_id=str(payload.get("attachment_id") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            organization_id=str(payload.get("organization_id") or ""),
            object_type=str(payload.get("object_type") or ""),
            object_id=str(payload.get("object_id") or ""),
            linked_by=str(payload.get("linked_by") or "system"),
            linked_at=str(payload.get("linked_at") or now_iso()),
            provenance=dict(payload.get("provenance") or {}),
            active=bool(payload.get("active", True)),
            unlinked_at=payload.get("unlinked_at"),
        )


@dataclass(frozen=True)
class AttachmentAccessDecision:
    allowed: bool
    permission_key: str
    reason: str | None = None
    decision_code: str | None = None
    surface: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "permission_key",
            _required_text("permission_key", self.permission_key),
        )
        object.__setattr__(self, "reason", _optional_text(self.reason))
        object.__setattr__(self, "decision_code", _optional_text(self.decision_code))
        object.__setattr__(self, "surface", _optional_text(self.surface))

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": bool(self.allowed),
            "permission_key": self.permission_key,
            "reason": self.reason,
            "decision_code": self.decision_code,
            "surface": self.surface,
        }


@dataclass(frozen=True)
class AttachmentActivity:
    activity_id: str
    attachment_id: str
    tenant_id: str
    organization_id: str
    event_type: str
    actor_id: str
    occurred_at: str
    summary: str
    context: dict[str, Any] = field(default_factory=dict)
    audit_event_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "activity_id", _required_text("activity_id", self.activity_id)
        )
        object.__setattr__(
            self, "attachment_id", _required_text("attachment_id", self.attachment_id)
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )
        object.__setattr__(
            self, "event_type", _required_text("event_type", self.event_type)
        )
        object.__setattr__(self, "actor_id", _required_text("actor_id", self.actor_id))
        object.__setattr__(
            self, "occurred_at", _required_text("occurred_at", self.occurred_at)
        )
        object.__setattr__(self, "summary", _required_text("summary", self.summary))
        object.__setattr__(self, "audit_event_id", _optional_text(self.audit_event_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "activity_id": self.activity_id,
            "attachment_id": self.attachment_id,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at,
            "summary": self.summary,
            "context": dict(self.context),
            "audit_event_id": self.audit_event_id,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "AttachmentActivity":
        return AttachmentActivity(
            activity_id=str(payload.get("activity_id") or ""),
            attachment_id=str(payload.get("attachment_id") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            organization_id=str(payload.get("organization_id") or ""),
            event_type=str(payload.get("event_type") or ""),
            actor_id=str(payload.get("actor_id") or "system"),
            occurred_at=str(payload.get("occurred_at") or now_iso()),
            summary=str(payload.get("summary") or "Attachment activity"),
            context=dict(payload.get("context") or {}),
            audit_event_id=payload.get("audit_event_id"),
        )


@dataclass(frozen=True)
class AttachmentRecord:
    attachment_id: str
    tenant_id: str
    organization_id: str
    status: AttachmentStatus
    created_at: str
    updated_at: str
    created_by: str
    shared_reference_allowed: bool = True
    current_version_id: str | None = None
    versions: list[AttachmentVersion] = field(default_factory=list)
    diagnostics: list[AttachmentDiagnostic] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "attachment_id", _required_text("attachment_id", self.attachment_id)
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )
        object.__setattr__(
            self, "created_at", _required_text("created_at", self.created_at)
        )
        object.__setattr__(
            self, "updated_at", _required_text("updated_at", self.updated_at)
        )
        object.__setattr__(
            self, "created_by", _required_text("created_by", self.created_by)
        )
        object.__setattr__(
            self, "current_version_id", _optional_text(self.current_version_id)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attachment_id": self.attachment_id,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "shared_reference_allowed": bool(self.shared_reference_allowed),
            "current_version_id": self.current_version_id,
            "versions": [item.to_dict() for item in self.versions],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "labels": [str(item) for item in self.labels if str(item).strip()],
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "AttachmentRecord":
        return AttachmentRecord(
            attachment_id=str(payload.get("attachment_id") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            organization_id=str(payload.get("organization_id") or ""),
            status=AttachmentStatus(
                str(payload.get("status") or AttachmentStatus.ACTIVE.value)
            ),
            created_at=str(payload.get("created_at") or now_iso()),
            updated_at=str(payload.get("updated_at") or now_iso()),
            created_by=str(payload.get("created_by") or "system"),
            shared_reference_allowed=bool(
                payload.get("shared_reference_allowed", True)
            ),
            current_version_id=payload.get("current_version_id"),
            versions=[
                AttachmentVersion.from_dict(dict(item))
                for item in list(payload.get("versions") or [])
                if isinstance(item, dict)
            ],
            diagnostics=[
                AttachmentDiagnostic.from_dict(dict(item))
                for item in list(payload.get("diagnostics") or [])
                if isinstance(item, dict)
            ],
            labels=[str(item) for item in list(payload.get("labels") or [])],
            metadata=dict(payload.get("metadata") or {}),
        )

"""Contracts for deterministic document template resolution and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _required_text(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be blank")
    return normalized


def _optional_text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


class TemplateStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"


class TemplateSource(str, Enum):
    TRANSACTION = "transaction"
    PROJECT = "project"
    CUSTOMER = "customer"
    TENANT_DEFAULT = "tenant_default"
    APPLICATION_FALLBACK = "application_fallback"
    EXPLICIT = "explicit"
    REVISION_SNAPSHOT = "revision_snapshot"


class OutputFormat(str, Enum):
    PDF = "pdf"
    HTML = "html"


@dataclass(frozen=True)
class DocumentTemplateVersion:
    template_version_id: str
    version_number: int
    content: str
    content_hash: str
    section_config: dict[str, bool] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)
    created_by: str = "system"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "template_version_id",
            _required_text("template_version_id", self.template_version_id),
        )
        object.__setattr__(self, "version_number", int(self.version_number))
        if self.version_number <= 0:
            raise ValueError("version_number must be greater than 0")
        object.__setattr__(self, "content", _required_text("content", self.content))
        object.__setattr__(
            self, "content_hash", _required_text("content_hash", self.content_hash)
        )
        object.__setattr__(
            self, "created_at", _required_text("created_at", self.created_at)
        )
        object.__setattr__(
            self, "created_by", _required_text("created_by", self.created_by)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_version_id": self.template_version_id,
            "version_number": self.version_number,
            "content": self.content,
            "content_hash": self.content_hash,
            "section_config": dict(self.section_config),
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "DocumentTemplateVersion":
        return DocumentTemplateVersion(
            template_version_id=str(payload.get("template_version_id") or ""),
            version_number=int(payload.get("version_number") or 1),
            content=str(payload.get("content") or ""),
            content_hash=str(payload.get("content_hash") or ""),
            section_config=dict(payload.get("section_config") or {}),
            created_at=str(payload.get("created_at") or _now_iso()),
            created_by=str(payload.get("created_by") or "system"),
        )


@dataclass(frozen=True)
class DocumentTemplate:
    template_id: str
    tenant_id: str
    organization_id: str
    title: str
    document_family: str
    status: TemplateStatus
    is_default: bool
    customer_id: str | None = None
    project_id: str | None = None
    transaction_id: str | None = None
    archived: bool = False
    versions: list[DocumentTemplateVersion] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    created_by: str = "system"
    updated_at: str = field(default_factory=_now_iso)
    updated_by: str = "system"

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "template_id", _required_text("template_id", self.template_id)
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )
        object.__setattr__(self, "title", _required_text("title", self.title))
        object.__setattr__(
            self,
            "document_family",
            _required_text("document_family", self.document_family).lower(),
        )
        if not isinstance(self.status, TemplateStatus):
            object.__setattr__(self, "status", TemplateStatus(str(self.status)))
        object.__setattr__(self, "customer_id", _optional_text(self.customer_id))
        object.__setattr__(self, "project_id", _optional_text(self.project_id))
        object.__setattr__(self, "transaction_id", _optional_text(self.transaction_id))
        object.__setattr__(
            self, "created_at", _required_text("created_at", self.created_at)
        )
        object.__setattr__(
            self, "created_by", _required_text("created_by", self.created_by)
        )
        object.__setattr__(
            self, "updated_at", _required_text("updated_at", self.updated_at)
        )
        object.__setattr__(
            self, "updated_by", _required_text("updated_by", self.updated_by)
        )
        versions = [
            (
                item
                if isinstance(item, DocumentTemplateVersion)
                else DocumentTemplateVersion.from_dict(dict(item))
            )
            for item in list(self.versions or [])
        ]
        if not versions:
            raise ValueError("template must include at least one version")
        object.__setattr__(self, "versions", versions)

    @property
    def scope_rank(self) -> int:
        if self.transaction_id:
            return 4
        if self.project_id:
            return 3
        if self.customer_id:
            return 2
        return 1

    @property
    def current_version(self) -> DocumentTemplateVersion:
        return sorted(self.versions, key=lambda item: item.version_number)[-1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "title": self.title,
            "document_family": self.document_family,
            "status": self.status.value,
            "is_default": self.is_default,
            "customer_id": self.customer_id,
            "project_id": self.project_id,
            "transaction_id": self.transaction_id,
            "archived": self.archived,
            "versions": [item.to_dict() for item in self.versions],
            "created_at": self.created_at,
            "created_by": self.created_by,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "DocumentTemplate":
        return DocumentTemplate(
            template_id=str(payload.get("template_id") or ""),
            tenant_id=str(payload.get("tenant_id") or ""),
            organization_id=str(payload.get("organization_id") or ""),
            title=str(payload.get("title") or ""),
            document_family=str(payload.get("document_family") or ""),
            status=TemplateStatus(
                str(payload.get("status") or TemplateStatus.DRAFT.value)
            ),
            is_default=bool(payload.get("is_default", False)),
            customer_id=payload.get("customer_id"),
            project_id=payload.get("project_id"),
            transaction_id=payload.get("transaction_id"),
            archived=bool(payload.get("archived", False)),
            versions=[
                DocumentTemplateVersion.from_dict(dict(item))
                for item in list(payload.get("versions") or [])
                if isinstance(item, dict)
            ],
            created_at=str(payload.get("created_at") or _now_iso()),
            created_by=str(payload.get("created_by") or "system"),
            updated_at=str(payload.get("updated_at") or _now_iso()),
            updated_by=str(payload.get("updated_by") or "system"),
        )


@dataclass(frozen=True)
class TemplateAssignment:
    template_id: str
    template_version_id: str
    version_number: int
    source: TemplateSource

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "template_version_id": self.template_version_id,
            "version_number": self.version_number,
            "source": self.source.value,
        }


@dataclass(frozen=True)
class RenderRequest:
    tenant_id: str
    organization_id: str
    actor_id: str
    document_id: str
    revision_number: int
    document_family: str
    output_format: OutputFormat
    presentation: str
    explicit_template_id: str | None = None


@dataclass(frozen=True)
class RenderContext:
    document_snapshot: dict[str, Any]
    revision_snapshot: dict[str, Any]
    branding: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderSection:
    key: str
    included: bool


@dataclass(frozen=True)
class RenderDiagnostic:
    code: str
    message: str
    severity: str = "informational"


@dataclass(frozen=True)
class OutputArtifact:
    artifact_id: str
    file_name: str
    mime_type: str
    output_format: OutputFormat
    content_hash: str
    payload: bytes


@dataclass(frozen=True)
class RenderResult:
    assignment: TemplateAssignment
    template_version_snapshot: dict[str, Any]
    sections: list[RenderSection]
    artifact: OutputArtifact
    diagnostics: list[RenderDiagnostic] = field(default_factory=list)

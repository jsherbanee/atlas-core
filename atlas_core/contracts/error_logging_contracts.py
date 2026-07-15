"""Contracts for tenant-scoped application error logging."""

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


class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorResolutionStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    REOPENED = "reopened"


@dataclass(frozen=True)
class ErrorContext:
    workspace: str
    route: str
    related_object_id: str | None = None
    related_object_type: str | None = None
    correlation_id: str | None = None
    background_job_id: str | None = None
    request_or_session_ref: str | None = None
    integration_hook: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "workspace", _required_text("workspace", self.workspace)
        )
        object.__setattr__(self, "route", _required_text("route", self.route))
        object.__setattr__(
            self,
            "related_object_id",
            _optional_text(self.related_object_id),
        )
        object.__setattr__(
            self,
            "related_object_type",
            _optional_text(self.related_object_type),
        )
        object.__setattr__(self, "correlation_id", _optional_text(self.correlation_id))
        object.__setattr__(
            self,
            "background_job_id",
            _optional_text(self.background_job_id),
        )
        object.__setattr__(
            self,
            "request_or_session_ref",
            _optional_text(self.request_or_session_ref),
        )
        object.__setattr__(
            self, "integration_hook", _optional_text(self.integration_hook)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "route": self.route,
            "related_object_id": self.related_object_id,
            "related_object_type": self.related_object_type,
            "correlation_id": self.correlation_id,
            "background_job_id": self.background_job_id,
            "request_or_session_ref": self.request_or_session_ref,
            "integration_hook": self.integration_hook,
        }


@dataclass(frozen=True)
class ErrorOccurrence:
    occurrence_id: str
    error_id: str
    timestamp: str
    exception_type: str
    sanitized_message: str
    sanitized_stack_trace: str
    actor_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "occurrence_id",
            _required_text("occurrence_id", self.occurrence_id),
        )
        object.__setattr__(self, "error_id", _required_text("error_id", self.error_id))
        object.__setattr__(
            self, "timestamp", _required_text("timestamp", self.timestamp)
        )
        object.__setattr__(
            self,
            "exception_type",
            _required_text("exception_type", self.exception_type),
        )
        object.__setattr__(
            self,
            "sanitized_message",
            _required_text("sanitized_message", self.sanitized_message),
        )
        object.__setattr__(
            self,
            "sanitized_stack_trace",
            _required_text("sanitized_stack_trace", self.sanitized_stack_trace),
        )
        object.__setattr__(self, "actor_id", _optional_text(self.actor_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence_id": self.occurrence_id,
            "error_id": self.error_id,
            "timestamp": self.timestamp,
            "exception_type": self.exception_type,
            "sanitized_message": self.sanitized_message,
            "sanitized_stack_trace": self.sanitized_stack_trace,
            "actor_id": self.actor_id,
        }


@dataclass(frozen=True)
class ApplicationError:
    error_id: str
    fingerprint: str
    tenant_id: str
    actor_id: str | None
    environment_label: str
    application_version: str
    severity: ErrorSeverity
    status: ErrorResolutionStatus
    context: ErrorContext
    summary: str
    resolution_notes: str | None = None
    first_seen_at: str = field(default_factory=now_iso)
    last_seen_at: str = field(default_factory=now_iso)
    occurrence_count: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "error_id", _required_text("error_id", self.error_id))
        object.__setattr__(
            self,
            "fingerprint",
            _required_text("fingerprint", self.fingerprint),
        )
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(self, "actor_id", _optional_text(self.actor_id))
        object.__setattr__(
            self,
            "environment_label",
            _required_text("environment_label", self.environment_label),
        )
        object.__setattr__(
            self,
            "application_version",
            _required_text("application_version", self.application_version),
        )
        object.__setattr__(self, "summary", _required_text("summary", self.summary))
        object.__setattr__(
            self,
            "resolution_notes",
            _optional_text(self.resolution_notes),
        )
        object.__setattr__(
            self,
            "first_seen_at",
            _required_text("first_seen_at", self.first_seen_at),
        )
        object.__setattr__(
            self,
            "last_seen_at",
            _required_text("last_seen_at", self.last_seen_at),
        )
        object.__setattr__(self, "occurrence_count", max(1, int(self.occurrence_count)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_id": self.error_id,
            "fingerprint": self.fingerprint,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "environment_label": self.environment_label,
            "application_version": self.application_version,
            "severity": self.severity.value,
            "status": self.status.value,
            "summary": self.summary,
            "context": self.context.to_dict(),
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
            "occurrence_count": self.occurrence_count,
            "resolution_notes": self.resolution_notes,
        }

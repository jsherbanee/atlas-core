"""Deterministic background job contracts for Atlas operations."""

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


class JobCategory(str, Enum):
    DOCUMENT_IMPORT = "document_import"
    COMMERCIAL_IMPORT = "commercial_import"
    PDF_GENERATION = "pdf_generation"
    EXPORT_GENERATION = "export_generation"
    SEARCH_INDEXING = "search_indexing"
    INTEGRATION_SYNCHRONIZATION = "integration_synchronization"
    FUTURE_OCR = "future_ocr"
    FUTURE_AI_PREPROCESSING = "future_ai_preprocessing"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY_SCHEDULED = "retry_scheduled"


@dataclass(frozen=True)
class JobRetryPolicy:
    max_attempts: int = 1
    retry_delay_seconds: int = 0

    def __post_init__(self) -> None:
        if int(self.max_attempts) <= 0:
            raise ValueError("max_attempts must be >= 1")
        if int(self.retry_delay_seconds) < 0:
            raise ValueError("retry_delay_seconds must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_attempts": int(self.max_attempts),
            "retry_delay_seconds": int(self.retry_delay_seconds),
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "JobRetryPolicy":
        return JobRetryPolicy(
            max_attempts=int(payload.get("max_attempts", 1)),
            retry_delay_seconds=int(payload.get("retry_delay_seconds", 0)),
        )


@dataclass(frozen=True)
class JobAuditReference:
    event_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_ids": [str(item) for item in self.event_ids if str(item).strip()]
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "JobAuditReference":
        return JobAuditReference(
            event_ids=[str(item) for item in list(payload.get("event_ids") or [])]
        )


@dataclass(frozen=True)
class JobDefinition:
    category: JobCategory
    handler_key: str
    cancellable: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "handler_key", _required_text("handler_key", self.handler_key)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "handler_key": self.handler_key,
            "cancellable": bool(self.cancellable),
        }


@dataclass(frozen=True)
class JobDiagnostic:
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


@dataclass(frozen=True)
class JobProgress:
    percent: int
    message: str
    step: str | None = None
    current: int | None = None
    total: int | None = None
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        percent_value = int(self.percent)
        if percent_value < 0 or percent_value > 100:
            raise ValueError("percent must be between 0 and 100")
        object.__setattr__(self, "percent", percent_value)
        object.__setattr__(self, "message", _required_text("message", self.message))
        object.__setattr__(self, "step", _optional_text(self.step))
        object.__setattr__(
            self, "updated_at", _required_text("updated_at", self.updated_at)
        )
        if self.current is not None and int(self.current) < 0:
            raise ValueError("current cannot be negative")
        if self.total is not None and int(self.total) <= 0:
            raise ValueError("total must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "percent": int(self.percent),
            "message": self.message,
            "step": self.step,
            "current": self.current,
            "total": self.total,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class JobResult:
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _required_text("summary", self.summary))

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class JobAttempt:
    attempt_number: int
    status: JobStatus
    started_at: str
    completed_at: str | None = None
    diagnostics: list[JobDiagnostic] = field(default_factory=list)

    def __post_init__(self) -> None:
        if int(self.attempt_number) <= 0:
            raise ValueError("attempt_number must be >= 1")
        object.__setattr__(
            self, "started_at", _required_text("started_at", self.started_at)
        )
        object.__setattr__(self, "completed_at", _optional_text(self.completed_at))

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_number": int(self.attempt_number),
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "JobAttempt":
        diagnostics = [
            JobDiagnostic(
                code=str(item.get("code") or "unknown"),
                message=str(item.get("message") or ""),
                severity=str(item.get("severity") or "error"),
                details=dict(item.get("details") or {}),
            )
            for item in list(payload.get("diagnostics") or [])
            if isinstance(item, dict)
        ]
        return JobAttempt(
            attempt_number=int(payload.get("attempt_number", 1)),
            status=JobStatus(str(payload.get("status") or JobStatus.FAILED.value)),
            started_at=str(payload.get("started_at") or now_iso()),
            completed_at=payload.get("completed_at"),
            diagnostics=diagnostics,
        )


@dataclass(frozen=True)
class JobCancellation:
    requested: bool = False
    requested_at: str | None = None
    requested_by: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested": bool(self.requested),
            "requested_at": self.requested_at,
            "requested_by": self.requested_by,
            "reason": self.reason,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "JobCancellation":
        return JobCancellation(
            requested=bool(payload.get("requested", False)),
            requested_at=_optional_text(payload.get("requested_at")),
            requested_by=_optional_text(payload.get("requested_by")),
            reason=_optional_text(payload.get("reason")),
        )


@dataclass(frozen=True)
class JobRequest:
    tenant_id: str
    organization_id: str
    actor_id: str
    category: JobCategory
    definition: JobDefinition
    input_payload: dict[str, Any]
    related_object_type: str | None = None
    related_object_id: str | None = None
    idempotency_key: str | None = None
    correlation_id: str | None = None
    retry_policy: JobRetryPolicy = field(default_factory=JobRetryPolicy)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "tenant_id", _required_text("tenant_id", self.tenant_id)
        )
        object.__setattr__(
            self,
            "organization_id",
            _required_text("organization_id", self.organization_id),
        )
        object.__setattr__(self, "actor_id", _required_text("actor_id", self.actor_id))
        object.__setattr__(
            self, "idempotency_key", _optional_text(self.idempotency_key)
        )
        object.__setattr__(self, "correlation_id", _optional_text(self.correlation_id))
        object.__setattr__(
            self,
            "related_object_type",
            _optional_text(self.related_object_type),
        )
        object.__setattr__(
            self, "related_object_id", _optional_text(self.related_object_id)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "actor_id": self.actor_id,
            "category": self.category.value,
            "definition": self.definition.to_dict(),
            "input_payload": dict(self.input_payload),
            "related_object_type": self.related_object_type,
            "related_object_id": self.related_object_id,
            "idempotency_key": self.idempotency_key,
            "correlation_id": self.correlation_id,
            "retry_policy": self.retry_policy.to_dict(),
        }


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    project_id: str
    request: JobRequest
    status: JobStatus
    progress: JobProgress
    attempts: list[JobAttempt] = field(default_factory=list)
    result: JobResult | None = None
    diagnostics: list[JobDiagnostic] = field(default_factory=list)
    cancellation: JobCancellation = field(default_factory=JobCancellation)
    audit_reference: JobAuditReference = field(default_factory=JobAuditReference)
    created_at: str = field(default_factory=now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    retry_available: bool = False
    next_retry_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_id", _required_text("job_id", self.job_id))
        object.__setattr__(
            self, "project_id", _required_text("project_id", self.project_id)
        )
        object.__setattr__(
            self, "created_at", _required_text("created_at", self.created_at)
        )
        object.__setattr__(self, "started_at", _optional_text(self.started_at))
        object.__setattr__(self, "completed_at", _optional_text(self.completed_at))
        object.__setattr__(self, "next_retry_at", _optional_text(self.next_retry_at))

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "request": self.request.to_dict(),
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "attempts": [item.to_dict() for item in self.attempts],
            "result": self.result.to_dict() if self.result is not None else None,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "cancellation": self.cancellation.to_dict(),
            "audit_reference": self.audit_reference.to_dict(),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retry_available": bool(self.retry_available),
            "next_retry_at": self.next_retry_at,
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "JobRecord":
        request_payload = dict(payload.get("request") or {})
        definition_payload = dict(request_payload.get("definition") or {})
        progress_payload = dict(payload.get("progress") or {})
        result_payload = payload.get("result")
        return JobRecord(
            job_id=str(payload.get("job_id") or ""),
            project_id=str(payload.get("project_id") or ""),
            request=JobRequest(
                tenant_id=str(request_payload.get("tenant_id") or ""),
                organization_id=str(request_payload.get("organization_id") or ""),
                actor_id=str(request_payload.get("actor_id") or "system"),
                category=JobCategory(
                    str(request_payload.get("category") or JobCategory.FUTURE_OCR.value)
                ),
                definition=JobDefinition(
                    category=JobCategory(
                        str(
                            definition_payload.get("category")
                            or request_payload.get("category")
                            or JobCategory.FUTURE_OCR.value
                        )
                    ),
                    handler_key=str(definition_payload.get("handler_key") or "unknown"),
                    cancellable=bool(definition_payload.get("cancellable", False)),
                ),
                input_payload=dict(request_payload.get("input_payload") or {}),
                related_object_type=request_payload.get("related_object_type"),
                related_object_id=request_payload.get("related_object_id"),
                idempotency_key=request_payload.get("idempotency_key"),
                correlation_id=request_payload.get("correlation_id"),
                retry_policy=JobRetryPolicy.from_dict(
                    dict(request_payload.get("retry_policy") or {})
                ),
            ),
            status=JobStatus(str(payload.get("status") or JobStatus.QUEUED.value)),
            progress=JobProgress(
                percent=int(progress_payload.get("percent", 0)),
                message=str(progress_payload.get("message") or "Queued"),
                step=progress_payload.get("step"),
                current=progress_payload.get("current"),
                total=progress_payload.get("total"),
                updated_at=str(progress_payload.get("updated_at") or now_iso()),
            ),
            attempts=[
                JobAttempt.from_dict(dict(item))
                for item in list(payload.get("attempts") or [])
                if isinstance(item, dict)
            ],
            result=(
                JobResult(
                    summary=str(dict(result_payload).get("summary") or "completed"),
                    payload=dict(dict(result_payload).get("payload") or {}),
                )
                if isinstance(result_payload, dict)
                else None
            ),
            diagnostics=[
                JobDiagnostic(
                    code=str(item.get("code") or "unknown"),
                    message=str(item.get("message") or ""),
                    severity=str(item.get("severity") or "error"),
                    details=dict(item.get("details") or {}),
                )
                for item in list(payload.get("diagnostics") or [])
                if isinstance(item, dict)
            ],
            cancellation=JobCancellation.from_dict(
                dict(payload.get("cancellation") or {})
            ),
            audit_reference=JobAuditReference.from_dict(
                dict(payload.get("audit_reference") or {})
            ),
            created_at=str(payload.get("created_at") or now_iso()),
            started_at=payload.get("started_at"),
            completed_at=payload.get("completed_at"),
            retry_available=bool(payload.get("retry_available", False)),
            next_retry_at=payload.get("next_retry_at"),
        )

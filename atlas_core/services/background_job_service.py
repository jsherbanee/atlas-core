"""Deterministic background job orchestration with local execution support."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from enum import Enum
import hashlib
import json
from typing import Any, Callable, Protocol

from atlas_core.contracts.background_job_contracts import (
    JobAttempt,
    JobAuditReference,
    JobCancellation,
    JobCategory,
    JobDefinition,
    JobDiagnostic,
    JobProgress,
    JobRecord,
    JobRequest,
    JobResult,
    JobStatus,
    now_iso,
)


class BackgroundJobRepository(Protocol):
    def save_job(self, project_id: str, job_payload: dict[str, Any]) -> None: ...

    def load_job(self, project_id: str, job_id: str) -> dict[str, Any] | None: ...

    def list_jobs(self, project_id: str, limit: int = 200) -> list[dict[str, Any]]: ...


class BackgroundJobExecutor(Protocol):
    def execute(self, operation: Callable[["JobExecutionContext"], dict[str, Any]]) -> dict[str, Any]: ...


class LocalDeterministicExecutor:
    """In-process deterministic executor used by local development/runtime."""

    def execute(
        self,
        operation: Callable[["JobExecutionContext"], dict[str, Any]],
        context: "JobExecutionContext",
    ) -> dict[str, Any]:
        return dict(operation(context) or {})


class JobExecutionContext:
    def __init__(
        self,
        *,
        project_id: str,
        job_id: str,
        request: JobRequest,
        attempt_number: int,
        progress: Callable[[int, str, str | None, int | None, int | None], None],
        is_cancelled: Callable[[], bool],
    ) -> None:
        self.project_id = project_id
        self.job_id = job_id
        self.request = request
        self.attempt_number = attempt_number
        self.progress = progress
        self.is_cancelled = is_cancelled


class BackgroundJobService:
    def __init__(
        self,
        *,
        repository: BackgroundJobRepository,
        audit_callback: Callable[..., dict[str, Any]] | None = None,
        executor: LocalDeterministicExecutor | None = None,
    ) -> None:
        self.repository = repository
        self.executor = executor or LocalDeterministicExecutor()
        self.audit_callback = audit_callback
        self._handlers: dict[JobCategory, Callable[[JobExecutionContext], dict[str, Any]]] = {}

    @staticmethod
    def _active_statuses() -> set[JobStatus]:
        return {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.RETRY_SCHEDULED}

    def register_handler(
        self,
        *,
        category: JobCategory,
        handler: Callable[[JobExecutionContext], dict[str, Any]],
    ) -> None:
        self._handlers[category] = handler

    def submit_job(
        self,
        *,
        project_id: str,
        request: JobRequest,
    ) -> dict[str, Any]:
        active = self._find_active_idempotent_job(project_id=project_id, request=request)
        if active is not None:
            return active.to_dict()

        created_at = now_iso()
        job_id = self._stable_job_id(project_id=project_id, request=request, created_at=created_at)
        record = JobRecord(
            job_id=job_id,
            project_id=project_id,
            request=request,
            status=JobStatus.QUEUED,
            progress=JobProgress(percent=0, message="Queued", updated_at=created_at),
            attempts=[],
            diagnostics=[],
            cancellation=JobCancellation(requested=False),
            audit_reference=JobAuditReference(event_ids=[]),
            created_at=created_at,
            started_at=None,
            completed_at=None,
            retry_available=request.retry_policy.max_attempts > 1,
            next_retry_at=None,
        )
        self._save(record)
        self._audit(record, "background_job.created", context={"category": request.category.value})
        return record.to_dict()

    def list_jobs(
        self,
        *,
        project_id: str,
        tenant_id: str,
        organization_id: str,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        rows = [
            JobRecord.from_dict(item)
            for item in self.repository.list_jobs(project_id, limit=limit)
            if isinstance(item, dict)
        ]
        scoped = [
            item
            for item in rows
            if item.request.tenant_id == tenant_id
            and item.request.organization_id == organization_id
        ]
        scoped.sort(key=lambda item: (item.created_at, item.job_id))
        return [item.to_dict() for item in scoped]

    def run_job(
        self,
        *,
        project_id: str,
        job_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> dict[str, Any]:
        record = self._load_checked(
            project_id=project_id,
            job_id=job_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        if record.status == JobStatus.CANCELLED:
            return record.to_dict()
        if record.status == JobStatus.SUCCEEDED:
            return record.to_dict()

        handler = self._handlers.get(record.request.category)
        if handler is None:
            return self._finalize_failure(
                record,
                diagnostics=[
                    JobDiagnostic(
                        code="missing_handler",
                        message=f"No handler is registered for {record.request.category.value}",
                    )
                ],
                schedule_retry=False,
            ).to_dict()

        attempt_number = len(record.attempts) + 1
        started_at = now_iso()
        running_record = self._replace_record(
            record,
            status=JobStatus.RUNNING,
            started_at=record.started_at or started_at,
            completed_at=None,
            progress=JobProgress(
                percent=max(record.progress.percent, 1),
                message="Running",
                step="start",
                updated_at=started_at,
            ),
            retry_available=(attempt_number < record.request.retry_policy.max_attempts),
            next_retry_at=None,
        )
        self._save(running_record)

        def _progress(
            percent: int,
            message: str,
            step: str | None = None,
            current: int | None = None,
            total: int | None = None,
        ) -> None:
            latest = self._load_checked(
                project_id=project_id,
                job_id=job_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
            if latest.status == JobStatus.CANCELLED:
                return
            updated = self._replace_record(
                latest,
                progress=JobProgress(
                    percent=percent,
                    message=message,
                    step=step,
                    current=current,
                    total=total,
                ),
            )
            self._save(updated)

        context = JobExecutionContext(
            project_id=project_id,
            job_id=job_id,
            request=running_record.request,
            attempt_number=attempt_number,
            progress=_progress,
            is_cancelled=lambda: self._is_cancellation_requested(project_id=project_id, job_id=job_id),
        )

        try:
            payload = self.executor.execute(handler, context)
            result = JobResult(
                summary=str(payload.get("summary") or "Completed"),
                payload=dict(payload.get("payload") or {}),
            )
            attempt = JobAttempt(
                attempt_number=attempt_number,
                status=JobStatus.SUCCEEDED,
                started_at=started_at,
                completed_at=now_iso(),
                diagnostics=[],
            )
            succeeded = self._replace_record(
                self._load_checked(
                    project_id=project_id,
                    job_id=job_id,
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                ),
                status=JobStatus.SUCCEEDED,
                completed_at=attempt.completed_at,
                progress=JobProgress(
                    percent=100,
                    message="Completed",
                    step="completed",
                    updated_at=attempt.completed_at or now_iso(),
                ),
                attempts=[*running_record.attempts, attempt],
                diagnostics=[],
                result=result,
                retry_available=False,
                next_retry_at=None,
            )
            self._save(succeeded)
            self._audit(succeeded, "background_job.completed")
            return succeeded.to_dict()
        except Exception as exc:  # noqa: BLE001
            diagnostic = JobDiagnostic(
                code="execution_error",
                message=str(exc),
                severity="error",
            )
            should_retry = attempt_number < record.request.retry_policy.max_attempts
            failed = self._finalize_failure(
                self._load_checked(
                    project_id=project_id,
                    job_id=job_id,
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                ),
                diagnostics=[diagnostic],
                schedule_retry=should_retry,
                started_at=started_at,
                attempt_number=attempt_number,
            )
            return failed.to_dict()

    def retry_job(
        self,
        *,
        project_id: str,
        job_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> dict[str, Any]:
        record = self._load_checked(
            project_id=project_id,
            job_id=job_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        if not record.retry_available:
            return record.to_dict()
        if record.status not in {JobStatus.FAILED, JobStatus.RETRY_SCHEDULED}:
            return record.to_dict()

        queued = self._replace_record(
            record,
            status=JobStatus.QUEUED,
            progress=JobProgress(percent=0, message="Queued for retry"),
            next_retry_at=None,
        )
        self._save(queued)
        self._audit(queued, "background_job.retry_requested")
        return self.run_job(
            project_id=project_id,
            job_id=job_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
        )

    def cancel_job(
        self,
        *,
        project_id: str,
        job_id: str,
        tenant_id: str,
        organization_id: str,
        actor_id: str,
        reason: str,
    ) -> dict[str, Any]:
        record = self._load_checked(
            project_id=project_id,
            job_id=job_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
        if record.status not in {JobStatus.QUEUED, JobStatus.RETRY_SCHEDULED}:
            return record.to_dict()

        cancellation = JobCancellation(
            requested=True,
            requested_at=now_iso(),
            requested_by=actor_id,
            reason=reason,
        )
        cancelled = self._replace_record(
            record,
            status=JobStatus.CANCELLED,
            completed_at=cancellation.requested_at,
            cancellation=cancellation,
            progress=JobProgress(
                percent=record.progress.percent,
                message="Cancelled",
                step="cancelled",
                updated_at=cancellation.requested_at or now_iso(),
            ),
            retry_available=False,
            next_retry_at=None,
        )
        self._save(cancelled)
        self._audit(cancelled, "background_job.cancelled", context={"reason": reason})
        return cancelled.to_dict()

    def _finalize_failure(
        self,
        record: JobRecord,
        *,
        diagnostics: list[JobDiagnostic],
        schedule_retry: bool,
        started_at: str | None = None,
        attempt_number: int | None = None,
    ) -> JobRecord:
        now_text = now_iso()
        resolved_attempt = attempt_number or (len(record.attempts) + 1)
        attempt = JobAttempt(
            attempt_number=resolved_attempt,
            status=JobStatus.FAILED,
            started_at=started_at or record.started_at or now_text,
            completed_at=now_text,
            diagnostics=diagnostics,
        )

        if schedule_retry:
            retry_at = (
                datetime.now(UTC)
                + timedelta(seconds=int(record.request.retry_policy.retry_delay_seconds))
            ).isoformat()
            updated = self._replace_record(
                record,
                status=JobStatus.RETRY_SCHEDULED,
                completed_at=now_text,
                attempts=[*record.attempts, attempt],
                diagnostics=[*record.diagnostics, *diagnostics],
                retry_available=True,
                next_retry_at=retry_at,
                progress=JobProgress(
                    percent=max(record.progress.percent, 1),
                    message="Retry scheduled",
                    step="retry_scheduled",
                    updated_at=now_text,
                ),
            )
            self._save(updated)
            self._audit(updated, "background_job.retry_scheduled")
            self._audit(updated, "background_job.failed")
            return updated

        updated = self._replace_record(
            record,
            status=JobStatus.FAILED,
            completed_at=now_text,
            attempts=[*record.attempts, attempt],
            diagnostics=[*record.diagnostics, *diagnostics],
            retry_available=False,
            next_retry_at=None,
            progress=JobProgress(
                percent=max(record.progress.percent, 1),
                message="Failed",
                step="failed",
                updated_at=now_text,
            ),
        )
        self._save(updated)
        self._audit(updated, "background_job.failed")
        return updated

    def _find_active_idempotent_job(
        self,
        *,
        project_id: str,
        request: JobRequest,
    ) -> JobRecord | None:
        if not request.idempotency_key:
            return None
        rows = [
            JobRecord.from_dict(item)
            for item in self.repository.list_jobs(project_id, limit=1000)
            if isinstance(item, dict)
        ]
        for item in rows:
            if (
                item.request.tenant_id == request.tenant_id
                and item.request.organization_id == request.organization_id
                and item.request.idempotency_key == request.idempotency_key
                and item.status in self._active_statuses()
            ):
                return item
        return None

    def _stable_job_id(
        self,
        *,
        project_id: str,
        request: JobRequest,
        created_at: str,
    ) -> str:
        canonical_input = json.dumps(request.input_payload, sort_keys=True, separators=(",", ":"))
        token = json.dumps(
            {
                "project_id": project_id,
                "tenant_id": request.tenant_id,
                "organization_id": request.organization_id,
                "category": request.category.value,
                "idempotency_key": request.idempotency_key,
                "correlation_id": request.correlation_id,
                "input": canonical_input,
                "created_at": created_at,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:20]
        return f"job:{digest}"

    def _load_checked(
        self,
        *,
        project_id: str,
        job_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> JobRecord:
        payload = self.repository.load_job(project_id, job_id)
        if not isinstance(payload, dict):
            raise ValueError("job was not found")
        record = JobRecord.from_dict(payload)
        if record.request.tenant_id != tenant_id or record.request.organization_id != organization_id:
            raise ValueError("job tenant scope mismatch")
        return record

    def _save(self, record: JobRecord) -> None:
        self.repository.save_job(record.project_id, record.to_dict())

    def _replace_record(self, record: JobRecord, **updates: Any) -> JobRecord:
        payload = record.to_dict()
        for key, value in updates.items():
            if hasattr(value, "to_dict"):
                payload[key] = value.to_dict()
            elif isinstance(value, Enum):
                payload[key] = value.value
            elif key == "attempts":
                payload[key] = [
                    item.to_dict() if hasattr(item, "to_dict") else dict(item)
                    for item in list(value)
                ]
            elif key == "diagnostics":
                payload[key] = [
                    item.to_dict() if hasattr(item, "to_dict") else dict(item)
                    for item in list(value)
                ]
            elif key == "result" and value is None:
                payload[key] = None
            else:
                payload[key] = value
        return JobRecord.from_dict(payload)

    def _is_cancellation_requested(self, *, project_id: str, job_id: str) -> bool:
        payload = self.repository.load_job(project_id, job_id)
        if not isinstance(payload, dict):
            return False
        cancellation = dict(payload.get("cancellation") or {})
        return bool(cancellation.get("requested", False))

    def _audit(
        self,
        record: JobRecord,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        if self.audit_callback is None:
            return
        emitted = self.audit_callback(
            project_id=record.project_id,
            action=action,
            actor_id=record.request.actor_id,
            actor_type="user",
            tenant_id=record.request.tenant_id,
            organization_id=record.request.organization_id,
            target_type="background_job",
            target_id=record.job_id,
            source="background_job_service",
            correlation_id=record.request.correlation_id,
            after={
                "status": record.status.value,
                "category": record.request.category.value,
                "related_object_type": record.request.related_object_type,
                "related_object_id": record.request.related_object_id,
            },
            context=deepcopy(context or {}),
        )
        event_id = str(dict(emitted or {}).get("event_id") or "").strip()
        if not event_id:
            return
        if event_id in set(record.audit_reference.event_ids):
            return
        updated = self._replace_record(
            record,
            audit_reference=JobAuditReference(
                event_ids=[*record.audit_reference.event_ids, event_id]
            ),
        )
        self._save(updated)

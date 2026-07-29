"""Startup reconciliation service to rebuild scheduler state from job files."""
from __future__ import annotations

import json
import time
from pathlib import Path
import logging
from typing import List

try:
    import psutil
except Exception:
    psutil = None

from atlas_core.services.job_scheduler import get_global_scheduler
import atlas_core.config.resource_policy as rp

logger = logging.getLogger("atlas.reconciliation")

# Module-level helper for exactly-once startup
_STARTUP_LOCK = __import__("threading").Lock()
_STARTUP_STATUS: dict = {"ran": False, "degraded": False}


def ensure_startup_reconciliation(*, uploads_root: str | None = None, fail_closed: bool | None = None, enabled: bool | None = None, policy: rp.ResourcePolicy | None = None) -> dict:
    """Ensure reconciliation runs once per process and return structured status.

    Parameters override environment when provided. Reads env vars:
    - ATLAS_STARTUP_RECONCILIATION_ENABLED
    - ATLAS_RECONCILIATION_ROOT
    - ATLAS_RECONCILIATION_FAIL_CLOSED
    """
    env = __import__("os").environ
    if enabled is None:
        enabled = env.get("ATLAS_STARTUP_RECONCILIATION_ENABLED", "1") not in {"0", "false", "False"}
    if uploads_root is None:
        uploads_root = env.get("ATLAS_RECONCILIATION_ROOT", "outputs/uploads")
    if fail_closed is None:
        fail_closed = env.get("ATLAS_RECONCILIATION_FAIL_CLOSED", "0") in {"1", "true", "True"}

    # Mark as running under lock so other threads/processes skip doing work.
    from atlas_core.services.job_scheduler import get_global_scheduler as _get_sched

    with _STARTUP_LOCK:
        if _STARTUP_STATUS.get("ran"):
            # ensure explicit ran=False in returned dict (don't let internal state override)
            return {**_STARTUP_STATUS, "ran": False, "skipped_already_complete": True}
        if not enabled:
            _STARTUP_STATUS.update({"ran": False, "skipped_already_complete": True})
            return {**_STARTUP_STATUS, "ran": False, "skipped_already_complete": True}

        # mark as in-progress so concurrent callers skip
        _STARTUP_STATUS.update({"ran": True, "in_progress": True, "degraded": False})

    service = ReconciliationService(uploads_root=uploads_root, policy=policy)
    try:
        # run reconciliation; service.run sets scheduler blocking to queue then allow
        result = service.run()
        with _STARTUP_LOCK:
            _STARTUP_STATUS.update({"ran": True, "in_progress": False, "degraded": False, **result})
        return {"ran": True, "status": "ok", **result}
    except Exception as exc:
        # on failure, honor fail_closed: block admissions (reject) or allow (fail-open)
        try:
            sched = _get_sched()
            if fail_closed:
                try:
                    sched.set_reconciliation_blocking("reject")
                except Exception:
                    pass
            else:
                try:
                    sched.set_reconciliation_blocking("allow")
                except Exception:
                    pass
        except Exception:
            pass
        with _STARTUP_LOCK:
            _STARTUP_STATUS.update({"ran": True, "in_progress": False, "degraded": True, "error": str(exc)})
        logger.exception("startup reconciliation failed")
        return {"ran": True, "status": "failed", "error": str(exc), "degraded": True}


def reset_startup_reconciliation() -> None:
    """Reset the process-local startup reconciliation status (for tests/manual retry)."""
    with _STARTUP_LOCK:
        _STARTUP_STATUS.clear()
        _STARTUP_STATUS.update({"ran": False, "degraded": False})



class ReconciliationService:
    """Scans uploads root for .jobs and rebuilds scheduler queues and actives.

    Behavior is process-local and best-effort. It annotates job JSON with
    reconciliation metadata fields and emits structured log events.
    """

    def __init__(self, uploads_root: Path | str = "outputs/uploads", policy: rp.ResourcePolicy | None = None):
        self.uploads_root = Path(uploads_root)
        self.policy = policy or rp.DEFAULT_POLICY
        self.scheduler = get_global_scheduler()
        # startup guard
        import threading, os
        self._lock = threading.Lock()
        self._ran = False
        self._degraded = False

    def _iter_job_files(self) -> List[Path]:
        jobs: List[Path] = []
        if not self.uploads_root.exists():
            return jobs
        for session in self.uploads_root.iterdir():
            if not session.is_dir():
                continue
            jobs_dir = session / ".jobs"
            if not jobs_dir.exists():
                continue
            for jf in jobs_dir.glob("*.json"):
                jobs.append(jf)
        return jobs

    def run(self) -> dict:
        """Perform the startup scan and rebuild scheduler state.

        Returns a dict summary with keys: ran, jobs_scanned, jobs_requeued, jobs_failed, jobs_verified, elapsed_seconds
        """
        with self._lock:
            if self._ran:
                logger.info({"event": "reconciliation_startup_skipped"})
                return {"ran": False, "reason": "already_run"}
            self._ran = True

        # block admissions while reconstructing queues (queue mode by default)
        self.scheduler.set_reconciliation_blocking("queue")
        start = time.time()
        self.scheduler.reset()
        logger.info({"event": "reconciliation_startup_begin", "uploads_root": str(self.uploads_root), "pid": __import__("os").getpid(), "scheduler_generation": self.scheduler.get_generation()})
        job_files = self._iter_job_files()
        jobs_scanned = 0
        jobs_requeued = 0
        jobs_failed = 0
        jobs_verified = 0

        for jf in job_files:
            try:
                payload = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                logger.warning({"event": "malformed_job_json", "path": str(jf)})
                # annotate file and continue
                now = time.time()
                try:
                    jf.write_text(json.dumps({"reconciled_at": now, "reconciliation_reason": "malformed_json", "reconciliation_action": "ignored"}), encoding="utf-8")
                except Exception:
                    pass
                continue

            job_id = payload.get("job_id")
            stage = payload.get("stage")
            policy_tier = payload.get("policy_tier") or payload.get("classification_policy") or payload.get("processing_class") or "standard"
            updated_at = payload.get("updated_at") or payload.get("started_at") or 0
            now = time.time()

            # terminal states: ignore
            if stage in {"completed", "failed", "rejected", "cancelled"}:
                logger.info({"event": "job_ignored", "job_id": job_id, "stage": stage})
                # annotate
                payload.update({"reconciled_at": now, "reconciliation_reason": "terminal_state", "reconciliation_action": "ignored", "previous_scheduler_state": stage, "scheduler_generation": self.scheduler._generation})
                try:
                    jf.write_text(json.dumps(payload), encoding="utf-8")
                except Exception:
                    pass
                continue

            # Non-terminal handling
            worker_pid = payload.get("worker_pid")

            # queued
            if stage == "queued":
                # if this job has retry metadata and a next_retry_at in the future, skip admission
                next_retry = payload.get("next_retry_at")
                if next_retry and next_retry > now:
                    # annotate as pending retry and skip
                    payload.update({"reconciled_at": now, "reconciliation_reason": "retry_pending", "reconciliation_action": "deferred", "previous_scheduler_state": stage, "scheduler_generation": self.scheduler._generation})
                    try:
                        jf.write_text(json.dumps(payload), encoding="utf-8")
                    except Exception:
                        pass
                    logger.info({"event": "job_deferred_retry", "job_id": job_id, "next_retry_at": next_retry})
                    continue
                entered = payload.get("queue_entered_at") or updated_at or now
                age = now - entered
                if age > self.policy.reconciliation_stale_queue_seconds:
                    reason = "stale_queued"
                    action = "requeued"
                else:
                    reason = "queued_at_startup"
                    action = "requeued"
                payload.update({
                    "reconciled_at": now,
                    "reconciliation_reason": reason,
                    "reconciliation_action": action,
                    "previous_scheduler_state": stage,
                    "scheduler_generation": self.scheduler._generation,
                })
                try:
                    jf.write_text(json.dumps(payload), encoding="utf-8")
                except Exception:
                    pass
                # submit to scheduler (it will queue/admit accordingly)
                try:
                    res = self.scheduler.submit(str(jf))
                    if res == "queued":
                        jobs_requeued += 1
                except Exception:
                    pass
                logger.info({"event": "job_requeued", "job_id": job_id, "policy_tier": policy_tier, "reason": reason, "age": age})
                continue

            # admitted/spawning/running/terminating
            if stage in {"admitted", "spawning", "running", "terminating"}:
                age = now - (payload.get("updated_at") or updated_at or now)
                pid_alive = False
                if worker_pid:
                    if psutil:
                        try:
                            pid_alive = psutil.pid_exists(int(worker_pid))
                        except Exception:
                            pid_alive = False
                    else:
                        # fallback using os.kill(0) on POSIX to test existence
                        try:
                            import os

                            os.kill(int(worker_pid), 0)
                            pid_alive = True
                        except Exception:
                            pid_alive = False

                if worker_pid and pid_alive:
                    # verify and register active
                    registered = self.scheduler.register_active(job_id, policy_tier, int(worker_pid))
                    reason = "active_pid_verified"
                    action = "verified" if registered else "queued"
                    payload.update({"reconciled_at": now, "reconciliation_reason": reason, "reconciliation_action": action, "previous_scheduler_state": stage, "scheduler_generation": self.scheduler._generation})
                    try:
                        jf.write_text(json.dumps(payload), encoding="utf-8")
                    except Exception:
                        pass
                    jobs_verified += 1
                    logger.info({"event": "job_verified", "job_id": job_id, "policy_tier": policy_tier, "age": age, "action": action})
                    continue

                # worker PID not alive or missing
                if age > self.policy.reconciliation_stale_running_seconds:
                    reason = "orphaned_or_stale_running"
                    action = "failed"
                    payload.update({"reconciled_at": now, "reconciliation_reason": reason, "reconciliation_action": action, "previous_scheduler_state": stage, "scheduler_generation": self.scheduler._generation, "stage": "failed", "failure_reason": "orphaned_worker"})
                    try:
                        jf.write_text(json.dumps(payload), encoding="utf-8")
                    except Exception:
                        pass
                    jobs_failed += 1
                    logger.info({"event": "job_failed", "job_id": job_id, "policy_tier": policy_tier, "reason": reason, "age": age})
                    continue
                else:
                    # recent; requeue to be safe
                    reason = "recent_incomplete"
                    action = "requeued"
                    payload.update({"reconciled_at": now, "reconciliation_reason": reason, "reconciliation_action": action, "previous_scheduler_state": stage, "scheduler_generation": self.scheduler._generation})
                    try:
                        jf.write_text(json.dumps(payload), encoding="utf-8")
                    except Exception:
                        pass
                    try:
                        res = self.scheduler.submit(str(jf))
                        if res == "queued":
                            jobs_requeued += 1
                    except Exception:
                        pass
                    logger.info({"event": "job_requeued", "job_id": job_id, "policy_tier": policy_tier, "reason": reason, "age": age})
                    continue

            # fallback: requeue
            payload.update({"reconciled_at": now, "reconciliation_reason": "unknown_state", "reconciliation_action": "requeued", "previous_scheduler_state": stage, "scheduler_generation": self.scheduler._generation})
            try:
                jf.write_text(json.dumps(payload), encoding="utf-8")
            except Exception:
                pass
            try:
                res = self.scheduler.submit(str(jf))
                if res == "queued":
                    jobs_requeued += 1
            except Exception:
                pass
            logger.info({"event": "job_requeued", "job_id": job_id, "policy_tier": policy_tier, "reason": "fallback"})

        elapsed = time.time() - start
        # allow admissions after rebuild
        self.scheduler.set_reconciliation_blocking("allow")
        logger.info({"event": "reconciliation_startup_complete", "pid": __import__("os").getpid(), "scheduler_generation": self.scheduler.get_generation(), "jobs_scanned": jobs_scanned, "jobs_requeued": jobs_requeued, "jobs_failed": jobs_failed, "jobs_verified": jobs_verified, "elapsed_seconds": elapsed})
        return {"ran": True, "jobs_scanned": jobs_scanned, "jobs_requeued": jobs_requeued, "jobs_failed": jobs_failed, "jobs_verified": jobs_verified, "elapsed_seconds": elapsed}

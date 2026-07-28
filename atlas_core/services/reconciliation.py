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


class ReconciliationService:
    """Scans uploads root for .jobs and rebuilds scheduler queues and actives.

    Behavior is process-local and best-effort. It annotates job JSON with
    reconciliation metadata fields and emits structured log events.
    """

    def __init__(self, uploads_root: Path | str = "outputs/uploads", policy: rp.ResourcePolicy | None = None):
        self.uploads_root = Path(uploads_root)
        self.policy = policy or rp.DEFAULT_POLICY
        self.scheduler = get_global_scheduler()

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

    def run(self) -> None:
        """Perform the startup scan and rebuild scheduler state."""
        self.scheduler.reset()
        logger.info({"event": "startup_scan", "uploads_root": str(self.uploads_root)})
        job_files = self._iter_job_files()
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
                    self.scheduler.submit(str(jf))
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
                        self.scheduler.submit(str(jf))
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
                self.scheduler.submit(str(jf))
            except Exception:
                pass
            logger.info({"event": "job_requeued", "job_id": job_id, "policy_tier": policy_tier, "reason": "fallback"})

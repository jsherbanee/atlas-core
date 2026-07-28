"""Lightweight in-process job scheduler enforcing ResourcePolicy concurrency."""
from __future__ import annotations

from collections import deque, defaultdict
from dataclasses import dataclass
import threading
import time
import logging
from pathlib import Path
from typing import Deque, Dict, Optional, Tuple

import atlas_core.config.resource_policy as rp

logger = logging.getLogger("atlas.scheduler")


@dataclass
class SchedulerEvent:
    event: str
    job_id: str
    policy_tier: str
    wait_time: float
    active_count: int
    queue_length: int


class JobScheduler:
    """Process-local FIFO scheduler that enforces ResourcePolicy tiers.

    - Maintains separate FIFO queues per policy tier.
    - Uses separate concurrency slots for `standard` and `large` tiers.
    - `very_large` runs alone and blocks all other jobs while active.
    - `pathological` behavior driven by ResourcePolicy.pathological_file_behavior.
    """

    VERSION = "job-scheduler/1.0.0"

    def __init__(self, policy: rp.ResourcePolicy = rp.DEFAULT_POLICY):
        self.policy = policy
        self._lock = threading.Lock()
        self._queues: Dict[str, Deque[Tuple[str, float, Path]]] = defaultdict(deque)
        self._active: Dict[str, dict] = {}  # job_id -> {policy, pid}

    def reset(self) -> None:
        with self._lock:
            self._queues = defaultdict(deque)
            self._active = {}

    def _queue_length(self) -> int:
        return sum(len(q) for q in self._queues.values())

    def _active_count(self) -> int:
        return len(self._active)

    def submit(self, job_file: str | Path) -> str:
        """Attempt to admit a job described by `job_file`.

        Returns one of: 'admitted', 'queued', 'rejected'.
        Side-effects: updates job JSON with scheduler metadata.
        """
        path = Path(job_file)
        try:
            js = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return "rejected"

        job_id = js.get("job_id")
        tier = js.get("classification_policy") or js.get("processing_class") or "standard"
        tier = str(tier)
        now = time.time()

        # handle pathological behavior
        if tier == "pathological":
            beh = getattr(self.policy, "pathological_file_behavior", "quarantine")
            if beh == "reject":
                js.update({
                    "scheduler_state": "rejected",
                    "policy_tier": "pathological",
                    "updated_at": now,
                })
                try:
                    path.write_text(json.dumps(js), encoding="utf-8")
                except Exception:
                    pass
                self._emit_event("rejected", job_id, "pathological", 0.0)
                return "rejected"
            # else fallthrough to queue 'quarantine' or 'strict'

        with self._lock:
            # If a very_large job active, cannot admit any other
            very_large_active = any(v.get("policy") == "very_large" for v in self._active.values())

            if tier == "very_large":
                if self._active_count() == 0:
                    # admit and reserve active slot
                    self._active[job_id] = {"policy": "very_large", "pid": None}
                    js.update({
                        "scheduler_state": "admitted",
                        "admitted_at": now,
                        "policy_tier": "very_large",
                        "scheduler_version": self.VERSION,
                        "active_worker_count": self._active_count(),
                        "queue_position": None,
                    })
                    try:
                        path.write_text(json.dumps(js), encoding="utf-8")
                    except Exception:
                        pass
                    self._emit_event("admitted", job_id, "very_large", 0.0)
                    return "admitted"
                else:
                    # queue
                    self._queues["very_large"].append((job_id, now, path))
                    js.update({
                        "scheduler_state": "queued",
                        "queue_position": self._queue_length(),
                        "queue_entered_at": now,
                        "policy_tier": "very_large",
                        "scheduler_version": self.VERSION,
                    })
                    try:
                        path.write_text(json.dumps(js), encoding="utf-8")
                    except Exception:
                        pass
                    self._emit_event("queued", job_id, "very_large", 0.0)
                    return "queued"

            if very_large_active:
                # must wait until very_large completes
                self._queues[tier].append((job_id, now, path))
                js.update({
                    "scheduler_state": "queued",
                    "queue_position": self._queue_length(),
                    "queue_entered_at": now,
                    "policy_tier": tier,
                    "scheduler_version": self.VERSION,
                })
                try:
                    path.write_text(json.dumps(js), encoding="utf-8")
                except Exception:
                    pass
                self._emit_event("queued", job_id, tier, 0.0)
                return "queued"

            # tier-specific concurrency
            if tier == "large":
                large_active = sum(1 for v in self._active.values() if v.get("policy") == "large")
                if large_active < getattr(self.policy, "max_concurrent_large_documents", 1):
                    self._active[job_id] = {"policy": "large", "pid": None}
                    js.update({
                        "scheduler_state": "admitted",
                        "admitted_at": now,
                        "policy_tier": "large",
                        "scheduler_version": self.VERSION,
                        "active_worker_count": self._active_count(),
                        "queue_position": None,
                    })
                    try:
                        path.write_text(json.dumps(js), encoding="utf-8")
                    except Exception:
                        pass
                    self._emit_event("admitted", job_id, "large", 0.0)
                    return "admitted"
                else:
                    self._queues["large"].append((job_id, now, path))
                    js.update({
                        "scheduler_state": "queued",
                        "queue_position": self._queue_length(),
                        "queue_entered_at": now,
                        "policy_tier": "large",
                        "scheduler_version": self.VERSION,
                    })
                    try:
                        path.write_text(json.dumps(js), encoding="utf-8")
                    except Exception:
                        pass
                    self._emit_event("queued", job_id, "large", 0.0)
                    return "queued"

            # standard
            if tier == "standard":
                standard_active = sum(1 for v in self._active.values() if v.get("policy") == "standard")
                if standard_active < getattr(self.policy, "standard_job_concurrency", 1):
                    self._active[job_id] = {"policy": "standard", "pid": None}
                    js.update({
                        "scheduler_state": "admitted",
                        "admitted_at": now,
                        "policy_tier": "standard",
                        "scheduler_version": self.VERSION,
                        "active_worker_count": self._active_count(),
                        "queue_position": None,
                    })
                    try:
                        path.write_text(json.dumps(js), encoding="utf-8")
                    except Exception:
                        pass
                    self._emit_event("admitted", job_id, "standard", 0.0)
                    return "admitted"
                else:
                    self._queues["standard"].append((job_id, now, path))
                    js.update({
                        "scheduler_state": "queued",
                        "queue_position": self._queue_length(),
                        "queue_entered_at": now,
                        "policy_tier": "standard",
                        "scheduler_version": self.VERSION,
                    })
                    try:
                        path.write_text(json.dumps(js), encoding="utf-8")
                    except Exception:
                        pass
                    self._emit_event("queued", job_id, "standard", 0.0)
                    return "queued"

        return "rejected"

    def mark_started(self, job_id: str, pid: int) -> None:
        with self._lock:
            if job_id in self._active:
                self._active[job_id]["pid"] = pid
                # update job file if present
                # best-effort: try to find job file by job id via .jobs folders omitted
                self._emit_event("started", job_id, self._active[job_id]["policy"], 0.0)

    def worker_finished(self, job_id: str) -> None:
        """Call when a worker process completes to free slots and admit queued jobs."""
        with self._lock:
            removed = self._active.pop(job_id, None)
            self._emit_event("completed", job_id, removed.get("policy") if removed else "unknown", 0.0)
            # try to admit queued jobs in priority order: very_large -> large -> standard
            self._admit_queued()

    def _admit_queued(self) -> None:
        now = time.time()
        # very_large: only admit if no active
        if self._active_count() == 0 and self._queues.get("very_large"):
            job_id, entered, path = self._queues["very_large"].popleft()
            self._active[job_id] = {"policy": "very_large", "pid": None}
            try:
                js = json.loads(path.read_text(encoding="utf-8"))
                js.update({
                    "scheduler_state": "admitted",
                    "admitted_at": now,
                    "policy_tier": "very_large",
                    "scheduler_version": self.VERSION,
                    "active_worker_count": self._active_count(),
                    "queue_position": None,
                })
                path.write_text(json.dumps(js), encoding="utf-8")
            except Exception:
                pass
            self._emit_event("admitted", job_id, "very_large", now - entered)
            return

        # admit large up to limit (do not admit if a very_large is active)
        large_limit = getattr(self.policy, "max_concurrent_large_documents", 1)
        large_active = sum(1 for v in self._active.values() if v.get("policy") == "large")
        very_large_active = any(v.get("policy") == "very_large" for v in self._active.values())
        while self._queues.get("large") and large_active < large_limit and not very_large_active:
            job_id, entered, path = self._queues["large"].popleft()
            self._active[job_id] = {"policy": "large", "pid": None}
            try:
                js = json.loads(path.read_text(encoding="utf-8"))
                js.update({
                    "scheduler_state": "admitted",
                    "admitted_at": now,
                    "policy_tier": "large",
                    "scheduler_version": self.VERSION,
                    "active_worker_count": self._active_count(),
                    "queue_position": None,
                })
                path.write_text(json.dumps(js), encoding="utf-8")
            except Exception:
                pass
            self._emit_event("admitted", job_id, "large", now - entered)
            large_active += 1

        # admit standard up to limit
        std_limit = getattr(self.policy, "standard_job_concurrency", 1)
        while self._queues.get("standard") and sum(1 for v in self._active.values() if v.get("policy") == "standard") < std_limit and not any(v.get("policy")=="very_large" for v in self._active.values()):
            job_id, entered, path = self._queues["standard"].popleft()
            self._active[job_id] = {"policy": "standard", "pid": None}
            try:
                js = json.loads(path.read_text(encoding="utf-8"))
                js.update({
                    "scheduler_state": "admitted",
                    "admitted_at": now,
                    "policy_tier": "standard",
                    "scheduler_version": self.VERSION,
                    "active_worker_count": self._active_count(),
                    "queue_position": None,
                })
                path.write_text(json.dumps(js), encoding="utf-8")
            except Exception:
                pass
            self._emit_event("admitted", job_id, "standard", now - entered)

    def _emit_event(self, event: str, job_id: str, tier: str, wait_time: float) -> None:
        ev = SchedulerEvent(
            event=event,
            job_id=job_id,
            policy_tier=tier,
            wait_time=wait_time,
            active_count=self._active_count(),
            queue_length=self._queue_length(),
        )
        logger.info({"scheduler_event": ev.__dict__})


# module-level singleton
import json

_GLOBAL_SCHEDULER: Optional[JobScheduler] = None


def get_global_scheduler() -> JobScheduler:
    global _GLOBAL_SCHEDULER
    if _GLOBAL_SCHEDULER is None:
        _GLOBAL_SCHEDULER = JobScheduler()
    return _GLOBAL_SCHEDULER

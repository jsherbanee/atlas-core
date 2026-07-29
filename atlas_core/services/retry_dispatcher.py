"""Background retry dispatcher that submits due retries to the JobScheduler."""
from __future__ import annotations

import threading
import time
import json
from pathlib import Path
from typing import Optional

from atlas_core.services.job_scheduler import get_global_scheduler

_DISPATCHER_LOCK = threading.Lock()
_DISPATCHER_STATE: dict = {"running": False}


def start_retry_dispatcher(uploads_root: str = "outputs/uploads") -> None:
    with _DISPATCHER_LOCK:
        if _DISPATCHER_STATE.get("running"):
            return
        _DISPATCHER_STATE["running"] = True

    def _loop():
        scheduler = get_global_scheduler()
        root = Path(uploads_root)
        while _DISPATCHER_STATE.get("running"):
            now = time.time()
            next_due: Optional[float] = None
            # scan jobs
            if root.exists():
                for session in root.iterdir():
                    jobs_dir = session / ".jobs"
                    if not jobs_dir.exists():
                        continue
                    for jf in jobs_dir.glob("*.json"):
                        try:
                            js = json.loads(jf.read_text(encoding="utf-8"))
                        except Exception:
                            continue
                        # only consider scheduled retries
                        if js.get("retry_state") == "scheduled":
                            next_at = js.get("next_retry_at")
                            if not next_at:
                                continue
                            if next_at <= now:
                                try:
                                    # attempt to submit; scheduler will queue/admit per policy
                                    scheduler.submit(str(jf))
                                except Exception:
                                    pass
                            else:
                                if next_due is None or next_at < next_due:
                                    next_due = next_at
            # sleep until next_due or a small default
            sleep_for = max(1.0, (next_due - time.time()) if next_due else 5.0)
            time.sleep(sleep_for)

    t = threading.Thread(target=_loop, name="atlas-retry-dispatcher", daemon=True)
    t.start()


def stop_retry_dispatcher() -> None:
    with _DISPATCHER_LOCK:
        _DISPATCHER_STATE["running"] = False


def reset_retry_dispatcher() -> None:
    stop_retry_dispatcher()
    with _DISPATCHER_LOCK:
        _DISPATCHER_STATE.clear()
        _DISPATCHER_STATE["running"] = False

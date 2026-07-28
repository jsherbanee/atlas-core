import json
import time
from pathlib import Path
from atlas_core.services.reconciliation import ReconciliationService
from atlas_core.services.job_scheduler import get_global_scheduler


def test_reconciliation_defers_future_retry(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    session = uploads / "s1"
    session.mkdir()
    jobs = session / ".jobs"
    jobs.mkdir()
    job = jobs / "j1.json"
    now = time.time()
    payload = {
        "job_id": "j1",
        "stage": "queued",
        "queue_entered_at": now,
        "next_retry_at": now + 3600,
        "priority": "standard",
    }
    job.write_text(json.dumps(payload), encoding="utf-8")

    service = ReconciliationService(uploads_root=str(uploads))
    res = service.run()
    # should have inspected but not requeued
    assert res.get("jobs_requeued", 0) == 0

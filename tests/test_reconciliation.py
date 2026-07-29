import json
import time
from pathlib import Path

from atlas_core.services.reconciliation import ReconciliationService
from atlas_core.services.job_scheduler import get_global_scheduler
import atlas_core.config.resource_policy as rp
import os


def _write_job(jf: Path, payload: dict):
    jf.parent.mkdir(parents=True, exist_ok=True)
    jf.write_text(json.dumps(payload), encoding="utf-8")


def test_clean_restart(tmp_path):
    uploads = tmp_path / "uploads"
    session = uploads / "s1"
    jobs = session / ".jobs"
    jf = jobs / "job1.json"
    payload = {"job_id": "job1", "stage": "queued", "queue_entered_at": time.time()}
    _write_job(jf, payload)

    service = ReconciliationService(uploads_root=uploads, policy=rp.DEFAULT_POLICY)
    sched = get_global_scheduler()
    sched.reset()
    service.run()

    p = json.loads(jf.read_text(encoding="utf-8"))
    assert p.get("reconciliation_action") == "requeued"


def test_orphaned_worker(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    session = uploads / "s2"
    jobs = session / ".jobs"
    jf = jobs / "job2.json"
    payload = {"job_id": "job2", "stage": "running", "worker_pid": 999999, "updated_at": time.time() - 3600}
    _write_job(jf, payload)
    service = ReconciliationService(uploads_root=uploads, policy=rp.ResourcePolicy(reconciliation_stale_running_seconds=60))
    sched = get_global_scheduler()
    sched.reset()
    service.run()
    p = json.loads(jf.read_text(encoding="utf-8"))
    assert p.get("stage") == "failed"
    assert p.get("reconciliation_action") == "failed"


def test_active_pid_alive(tmp_path, monkeypatch):
    # create a fake pid by using current process pid
    pid = os.getpid()
    uploads = tmp_path / "uploads"
    session = uploads / "s3"
    jobs = session / ".jobs"
    jf = jobs / "job3.json"
    payload = {"job_id": "job3", "stage": "running", "worker_pid": pid, "updated_at": time.time()}
    _write_job(jf, payload)
    service = ReconciliationService(uploads_root=uploads, policy=rp.DEFAULT_POLICY)
    sched = get_global_scheduler()
    sched.reset()
    service.run()
    p = json.loads(jf.read_text(encoding="utf-8"))
    assert p.get("reconciliation_action") in {"verified", "queued"}


def test_completed_ignored(tmp_path):
    uploads = tmp_path / "uploads"
    session = uploads / "s4"
    jobs = session / ".jobs"
    jf = jobs / "job4.json"
    payload = {"job_id": "job4", "stage": "completed", "updated_at": time.time()}
    _write_job(jf, payload)
    service = ReconciliationService(uploads_root=uploads, policy=rp.DEFAULT_POLICY)
    sched = get_global_scheduler()
    sched.reset()
    service.run()
    p = json.loads(jf.read_text(encoding="utf-8"))
    assert p.get("reconciliation_action") == "ignored"

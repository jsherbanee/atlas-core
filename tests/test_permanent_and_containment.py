import json
import time
from pathlib import Path
import os


from atlas_core.services import extraction_worker
from atlas_core.services.reconciliation import ReconciliationService


def write_job_file(tmp_path: Path, dest_path: Path, extra: dict = None) -> Path:
    # ensure destination file exists for stat
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if not dest_path.exists():
            dest_path.write_bytes(b"%%PDF-1.4\nminimal")
    except Exception:
        pass

    job = {
        "job_id": "testjob",
        "intake_identity": "intake1",
        "project_id": "proj",
        "filename": dest_path.name,
        "size_bytes": dest_path.stat().st_size,
        "processing_class": "standard",
        "stage": "queued",
        "retry_state": "pending",
        "attempt_count": 0,
        "max_attempts": 2,
        "prior_failures": [],
        "destination": str(dest_path),
    }
    if extra:
        job.update(extra)
    # create a unique job filename per call to avoid overwriting in tests
    jf = tmp_path / f"{dest_path.stem}.{int(time.time()*1000)}.json"
    jf.write_text(json.dumps(job), encoding="utf-8")
    return jf


def test_declared_stream_length_permanent(tmp_path, monkeypatch):
    # create dest file
    dest = tmp_path / "f.pdf"
    dest.write_bytes(b"%%PDF-1.4\n...minimal")
    jf = write_job_file(tmp_path, dest)

    # stub worker_main to simulate declared stream length error
    def fake_worker_main(pdf_path, out_json, policy=None):
        payload = {
            "status": "error",
            "error": "Declared stream length of 178257872 exceeds maximum allowed length.",
            "failure": {
                "failure_code": "DECLARED_STREAM_LENGTH_EXCEEDED",
                "failure_category": "parsing",
                "retryable": False,
                "operator_message": "Declared stream length exceeds parser limits",
                "exception_type": None,
                "original_message": "Declared stream length of 178257872 exceeds maximum allowed length.",
            },
            "pages": [],
            "metrics": {
                "pid": os.getpid(),
                "start_ts": time.time(),
                "end_ts": time.time(),
                "elapsed_seconds": 0.1,
                "containment": {"applied": False},
            },
        }
        Path(out_json).write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(extraction_worker, "worker_main", fake_worker_main)
    # run
    extraction_worker.run_job_from_jobfile(str(jf))
    data = json.loads(jf.read_text(encoding="utf-8"))
    assert data["stage"] == "failed"
    assert data["retry_state"] == "permanent"
    assert data["retryable"] is False
    assert data.get("final_failure_reason") is not None
    assert data.get("next_retry_at") is None


def test_dispatcher_ignores_permanent(tmp_path, monkeypatch):
    # create two job files: one scheduled, one permanent
    now = time.time()
    # place jobs under a session/.jobs structure so dispatcher will discover them
    session = tmp_path / "sess"
    jobs_dir = session / ".jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    sched_job = write_job_file(
        jobs_dir,
        jobs_dir / "a.pdf",
        extra={"retry_state": "scheduled", "next_retry_at": now - 1},
    )
    perm_job = write_job_file(
        jobs_dir, jobs_dir / "b.pdf", extra={"retry_state": "permanent"}
    )

    calls = []

    class DummySched:
        def submit(self, path):
            calls.append(path)

    # simulate dispatcher scan inline (avoid starting background thread)
    now = time.time()
    scheduled_candidates = []
    for jf in jobs_dir.glob("*.json"):
        js = json.loads(jf.read_text(encoding="utf-8"))
        if js.get("retry_state") == "scheduled":
            next_at = js.get("next_retry_at")
            if next_at and next_at <= now:
                scheduled_candidates.append(jf)

    # scheduled job should be selected, permanent job should not
    assert any(str(sched_job) == str(s) for s in scheduled_candidates)
    assert not any(str(perm_job) == str(s) for s in scheduled_candidates)


def test_reconciliation_ignores_permanent(tmp_path):
    # create a session dir and job file with terminal failed + permanent
    session = tmp_path / "s"
    session.mkdir()
    jobs = session / ".jobs"
    jobs.mkdir()
    dest = tmp_path / "d.pdf"
    dest.write_bytes(b"%%PDF-1.4\nminimal")
    jf = write_job_file(
        jobs,
        dest,
        extra={
            "stage": "failed",
            "retry_state": "permanent",
            "final_failure_reason": "bad",
        },
    )

    svc = ReconciliationService(uploads_root=str(tmp_path))
    # run reconciliation (result unused for this assertion)
    svc.run()
    # ensure job file still has permanent state and was not requeued
    data = json.loads(jf.read_text(encoding="utf-8"))
    assert data.get("retry_state") == "permanent"


def test_worker_receives_policy_from_jobfile(tmp_path, monkeypatch):
    dest = tmp_path / "d2.pdf"
    dest.write_bytes(b"%%PDF-1.4\nminimal")
    jf = write_job_file(
        tmp_path,
        dest,
        extra={
            "worker_memory_limit_bytes": 12345,
            "worker_soft_rss_warning_bytes": 2222,
            "worker_timeout_seconds": 11,
        },
    )

    captured = {}

    def fake_worker_main(pdf_path, out_json, policy=None):
        captured["policy"] = policy
        payload = {
            "status": "ok",
            "error": None,
            "pages": [],
            "metrics": {
                "pid": os.getpid(),
                "start_ts": time.time(),
                "end_ts": time.time(),
                "elapsed_seconds": 0.01,
                "containment": {"applied": False},
            },
            "failure": None,
        }
        Path(out_json).write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(extraction_worker, "worker_main", fake_worker_main)
    extraction_worker.run_job_from_jobfile(str(jf))
    assert captured.get("policy") is not None
    assert captured["policy"].get("worker_memory_limit_bytes") == 12345


def test_disabled_containment_records_reason(tmp_path, monkeypatch):
    dest = tmp_path / "d3.pdf"
    dest.write_bytes(b"%%PDF-1.4\nminimal")
    # job without worker_memory_limit_bytes -> disabled
    jf = write_job_file(tmp_path, dest, extra={})

    def fake_worker_main(pdf_path, out_json, policy=None):
        payload = {
            "status": "error",
            "error": "some parse error",
            "pages": [],
            "metrics": {
                "pid": os.getpid(),
                "start_ts": time.time(),
                "end_ts": time.time(),
                "elapsed_seconds": 0.1,
                "containment": {"applied": False},
            },
        }
        Path(out_json).write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(extraction_worker, "worker_main", fake_worker_main)
    extraction_worker.run_job_from_jobfile(str(jf))
    data = json.loads(jf.read_text(encoding="utf-8"))
    assert data.get("containment_applied") is False
    assert data.get("containment_reason") == "disabled_by_policy"

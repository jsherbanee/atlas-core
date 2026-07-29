import json
import time
from pathlib import Path

import atlas_core.config.resource_policy as rp
from atlas_core.services.job_scheduler import get_global_scheduler


def _make_job_file(tmp_path: Path, job_id: str, tier: str) -> Path:
    jf = tmp_path / f"{job_id}.json"
    payload = {
        "job_id": job_id,
        "intake_identity": job_id,
        "filename": f"{job_id}.pdf",
        "processing_class": (
            tier
            if tier in {"standard", "large", "very_large", "pathological"}
            else "standard"
        ),
        "stage": "queued",
    }
    jf.write_text(json.dumps(payload), encoding="utf-8")
    return jf


def test_standard_concurrency(tmp_path, monkeypatch):
    policy = rp.ResourcePolicy(standard_job_concurrency=2)
    sched = get_global_scheduler()
    sched.policy = policy
    sched.reset()

    j1 = _make_job_file(tmp_path, "j1", "standard")
    j2 = _make_job_file(tmp_path, "j2", "standard")
    j3 = _make_job_file(tmp_path, "j3", "standard")

    assert sched.submit(j1) == "admitted"
    assert sched.submit(j2) == "admitted"
    assert sched.submit(j3) == "queued"

    # finish one and ensure next queued admits
    sched.worker_finished("j1")
    # allow scheduler to process
    time.sleep(0.01)
    # read j3 file to see it was admitted
    j3p = json.loads(j3.read_text(encoding="utf-8"))
    assert j3p.get("scheduler_state") == "admitted"


def test_large_concurrency(tmp_path):
    policy = rp.ResourcePolicy(max_concurrent_large_documents=1)
    sched = get_global_scheduler()
    sched.policy = policy
    sched.reset()

    a = _make_job_file(tmp_path, "L1", "large")
    b = _make_job_file(tmp_path, "L2", "large")

    assert sched.submit(a) == "admitted"
    assert sched.submit(b) == "queued"
    sched.worker_finished("L1")
    time.sleep(0.01)
    bp = json.loads(b.read_text(encoding="utf-8"))
    assert bp.get("scheduler_state") == "admitted"


def test_very_large_serialization(tmp_path):
    policy = rp.ResourcePolicy(
        standard_job_concurrency=2, max_concurrent_large_documents=1
    )
    sched = get_global_scheduler()
    sched.policy = policy
    sched.reset()

    s1 = _make_job_file(tmp_path, "s1", "standard")
    s2 = _make_job_file(tmp_path, "s2", "standard")
    v = _make_job_file(tmp_path, "V1", "very_large")

    assert sched.submit(s1) == "admitted"
    assert sched.submit(s2) == "admitted"
    # very large should be queued until active jobs complete
    assert sched.submit(v) == "queued"
    # finish both active
    sched.worker_finished("s1")
    sched.worker_finished("s2")
    time.sleep(0.01)
    vp = json.loads(v.read_text(encoding="utf-8"))
    assert vp.get("scheduler_state") == "admitted"


def test_fifo_within_tier(tmp_path):
    sched = get_global_scheduler()
    sched.policy = rp.ResourcePolicy(standard_job_concurrency=1)
    sched.reset()

    a = _make_job_file(tmp_path, "a", "standard")
    b = _make_job_file(tmp_path, "b", "standard")
    c = _make_job_file(tmp_path, "c", "standard")

    assert sched.submit(a) == "admitted"
    assert sched.submit(b) == "queued"
    assert sched.submit(c) == "queued"

    sched.worker_finished("a")
    time.sleep(0.01)
    bp = json.loads(b.read_text(encoding="utf-8"))
    assert bp.get("scheduler_state") == "admitted"


def test_pathological_rejection(tmp_path):
    policy = rp.ResourcePolicy(pathological_file_behavior="reject")
    sched = get_global_scheduler()
    sched.policy = policy
    sched.reset()

    p = _make_job_file(tmp_path, "p1", "pathological")
    assert sched.submit(p) == "rejected"
    pp = json.loads(p.read_text(encoding="utf-8"))
    assert pp.get("scheduler_state") == "rejected"

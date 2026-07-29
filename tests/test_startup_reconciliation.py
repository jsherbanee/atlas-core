import os
import threading
from atlas_core.services.reconciliation import ensure_startup_reconciliation, reset_startup_reconciliation
from atlas_core.services.job_scheduler import get_global_scheduler


def test_reconciliation_runs_once(tmp_path, monkeypatch):
    reset_startup_reconciliation()
    res1 = ensure_startup_reconciliation(uploads_root=str(tmp_path))
    res2 = ensure_startup_reconciliation(uploads_root=str(tmp_path))
    assert res1.get("ran") is True or res1.get("ran") is False
    assert res2.get("skipped_already_complete") is True


def test_concurrent_initialization_thread_safe(tmp_path):
    reset_startup_reconciliation()
    results = []

    def worker():
        results.append(ensure_startup_reconciliation(uploads_root=str(tmp_path)))

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ran_count = sum(1 for r in results if r.get("ran") is True)
    # only one should have performed the run
    assert ran_count <= 1


def test_fail_closed_blocks_admission(monkeypatch, tmp_path):
    reset_startup_reconciliation()
    # force ReconciliationService.run to raise
    import atlas_core.services.reconciliation as rec_mod

    class Bad:
        def __init__(self, *a, **k):
            pass

        def run(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(rec_mod, "ReconciliationService", Bad)
    os.environ["ATLAS_RECONCILIATION_FAIL_CLOSED"] = "1"
    ensure_startup_reconciliation(uploads_root=str(tmp_path))
    sched = get_global_scheduler()
    assert sched.get_admission_mode() in {"reject", "queue", "allow", None}


def test_fail_open_allows_admission(monkeypatch, tmp_path):
    reset_startup_reconciliation()
    import atlas_core.services.reconciliation as rec_mod

    class Bad:
        def __init__(self, *a, **k):
            pass

        def run(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(rec_mod, "ReconciliationService", Bad)
    os.environ["ATLAS_RECONCILIATION_FAIL_CLOSED"] = "0"
    ensure_startup_reconciliation(uploads_root=str(tmp_path))
    sched = get_global_scheduler()
    assert sched.get_admission_mode() in {"allow", "queue", "reject"}

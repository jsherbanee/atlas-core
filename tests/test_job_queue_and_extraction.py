import json
from pathlib import Path

from atlas_core.services.document_intake_service import DocumentIntakeService


def test_job_queue_and_spawn(tmp_path: Path) -> None:
    # create a fake session folder and job file
    session = tmp_path / "sess"
    jobs = session / ".jobs"
    jobs.mkdir(parents=True)
    job = jobs / "testjob.json"
    dest = tmp_path / "drawings" / "a.pdf"
    dest.parent.mkdir(parents=True)
    dest.write_text("x")
    job.write_text(
        json.dumps({"job_id": "j1", "destination": str(dest), "stage": "queued"})
    )

    service = DocumentIntakeService()
    pid = service.spawn_extraction_worker_for_job(job)
    assert isinstance(pid, int)
    # wait for worker to update (poll up to 5s)
    import time

    deadline = time.time() + 5.0
    updated = False
    while time.time() < deadline:
        data = json.loads(job.read_text(encoding="utf-8"))
        if data.get("stage") in {"classifying", "failed"}:
            updated = True
            break
        time.sleep(0.2)

    assert updated, f"job file did not update in time; final stage={data.get('stage')}"

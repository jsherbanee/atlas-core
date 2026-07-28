"""Validation harness that runs the reproduction as a normal script file.

This script exercises the production-like intake + background spawn model:
- builds session packages with `run_extraction=False`
- uses `DocumentIntakeService.spawn_extraction_worker_for_job` to start workers
- waits for worker PIDs, reads job JSON lifecycle, and also runs a direct
  `worker_main` invocation to capture the worker metrics (ru_maxrss) for
  recording.

Produces `docs/validation/artifacts/large-upload/validation_results.json`.
"""

from pathlib import Path
import json
import os
import time
import tempfile
import argparse

from atlas_core.services.document_intake_service import DocumentIntakeService
from atlas_core.services.extraction_worker import worker_main
from scripts.repro_large_uploads import create_minimal_pdf
import shutil
from atlas_core.utils.streaming import incremental_sha1_from_file


def wait_for_pid(pid: int, timeout: float = 120.0) -> int:
    """Wait for a child pid to exit and return exit code (blocks).

    Uses os.waitpid to wait on the child created by spawn_extraction_worker_for_job.
    """
    start = time.time()
    while True:
        try:
            pid_ret, status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            # already reaped
            return 0
        if pid_ret == 0:
            if time.time() - start > timeout:
                return -1
            time.sleep(0.1)
            continue
        # exited; decode status
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)
        if os.WIFSIGNALED(status):
            return -1 - os.WTERMSIG(status)
        return status


def run_case(service: DocumentIntakeService, output_dir: Path, files: list[tuple[str, Path]]):
    session_id = f"val-{int(time.time()*1000)}"
    result = service.build_session_package_from_file_paths(
        files, uploads_root=output_dir, session_id=session_id, project_id="repro", run_extraction=False
    )
    pkg = result.package_path
    jobs = list((pkg / ".jobs").glob("*.json"))
    records = []
    for job in jobs:
        # spawn production-style worker
        pid = service.spawn_extraction_worker_for_job(job)
        record = {"job_file": str(job), "spawn_pid": pid}

        # wait for the background worker to finish (child process)
        exit_code = None
        if pid and pid > 0:
            exit_code = wait_for_pid(pid, timeout=300.0)
        record["spawn_exit_code"] = exit_code

        # read job file after worker finishes
        try:
            data = json.loads(job.read_text(encoding="utf-8"))
            record["job_state_after"] = data
        except Exception as exc:
            record["job_read_error"] = str(exc)

        # run a direct worker_main to capture ru_maxrss/metrics without relying on jobfile
        dest = record.get("job_state_after", {}).get("destination")
        if dest:
            out = tempfile.NamedTemporaryFile(delete=False)
            out_path = out.name
            out.close()
            try:
                # run worker_main in-process (this will perform extraction and write metrics)
                start = time.time()
                worker_main(dest, out_path)
                elapsed = time.time() - start
                payload = json.loads(Path(out_path).read_text(encoding="utf-8"))
                record["direct_worker_payload"] = payload
                record["direct_worker_elapsed"] = elapsed
            except Exception as exc:
                record["direct_worker_error"] = str(exc)
            finally:
                try:
                    Path(out_path).unlink()
                except Exception:
                    pass

        # cleanup check: ensure temp files cleaned and canonical exists
        dest_path = record.get("job_state_after", {}).get("destination")
        record["destination_exists"] = Path(dest_path).exists() if dest_path else False
        records.append(record)

    return {"session": str(pkg), "jobs": records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Base output directory for validation runs. Defaults to .runtime/validation/large-upload/runs/<ts>",
        default=None,
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    if args.output_dir:
        base_out = Path(args.output_dir).absolute()
    else:
        base_out = repo_root / ".runtime" / "validation" / "large-upload" / "runs"
    ts = time.strftime("%Y-%m-%dT%H%M%S")
    run_dir = base_out / ts
    fixtures_dir = run_dir / "fixtures"
    run_dir.mkdir(parents=True, exist_ok=True)
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Small summary (kept under docs path) will be written later
    docs_summary_dir = repo_root / "docs" / "validation" / "artifacts" / "large-upload"
    docs_summary_dir.mkdir(parents=True, exist_ok=True)

    service = DocumentIntakeService()

    # create fixtures under the run-specific fixtures dir
    small = fixtures_dir / "small.pdf"
    medium = fixtures_dir / "medium.pdf"
    large = fixtures_dir / "large.pdf"
    if not small.exists():
        create_minimal_pdf(small, 10 * 1024 * 1024)
    if not medium.exists():
        create_minimal_pdf(medium, 50 * 1024 * 1024)
    if not large.exists():
        create_minimal_pdf(large, 170 * 1024 * 1024)

    results = []

    # create durable master fixtures we can copy from for each case
    small_master = fixtures_dir / "small.master.pdf"
    medium_master = fixtures_dir / "medium.master.pdf"
    large_master = fixtures_dir / "large.master.pdf"
    if not small_master.exists():
        create_minimal_pdf(small_master, 10 * 1024 * 1024)
    if not medium_master.exists():
        create_minimal_pdf(medium_master, 50 * 1024 * 1024)
    if not large_master.exists():
        create_minimal_pdf(large_master, 170 * 1024 * 1024)

    # helper to create a fresh copy for a case with a canonical filename
    def fresh_copy(master: Path, dest_name: str) -> Path:
        dest = fixtures_dir / dest_name
        shutil.copy2(master, dest)
        return dest

    # 1. small
    small_src = fresh_copy(small_master, "small.pdf")
    results.append({"case": "small", **run_case(service, run_dir, [("small.pdf", small_src)])})
    # 2. medium
    medium_src = fresh_copy(medium_master, "medium.pdf")
    results.append({"case": "medium", **run_case(service, run_dir, [("medium.pdf", medium_src)])})
    # 3. large
    large_src = fresh_copy(large_master, "large.pdf")
    results.append({"case": "large", **run_case(service, run_dir, [("large.pdf", large_src)])})
    # 4. duplicate upload (two identical entries)
    # create two fresh copies of the large master so the intake service can move
    # the first source without causing the second submission to see a missing
    # file. Preserve canonical filename and confirm checksum equality.
    large_a = fresh_copy(large_master, "large.dup.a.pdf")
    large_b = fresh_copy(large_master, "large.dup.b.pdf")
    try:
        orig_sum = incremental_sha1_from_file(large_a)
        copy_sum = incremental_sha1_from_file(large_b)
        if orig_sum != copy_sum:
            print("Warning: checksum mismatch for duplicate fixture copies")
    except Exception:
        pass
    results.append({"case": "duplicate", **run_case(service, run_dir, [("large.pdf", large_a), ("large.pdf", large_b)])})
    # 5. two large uploads (two different files)
    large2 = fresh_copy(large_master, "large2.pdf")
    results.append({"case": "two_large", **run_case(service, run_dir, [("large.pdf", large2), ("large2.pdf", fresh_copy(large_master, "large2.b.pdf") )])})

    # write compact summary back to docs (small, curated)
    out_file = docs_summary_dir / "validation_results.json"
    compact = [{"case": r["case"] if "case" in r else r, "session": r.get("session") , "jobs": [{"job_file": j.get("job_file"), "spawn_pid": j.get("spawn_pid"), "spawn_exit_code": j.get("spawn_exit_code") } for j in r.get("jobs",[])]} for r in results]
    out_file.write_text(json.dumps(compact, indent=2), encoding="utf-8")
    # also write full run details under run dir
    (run_dir / "validation_results.full.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote run details to {run_dir}")


if __name__ == "__main__":
    main()

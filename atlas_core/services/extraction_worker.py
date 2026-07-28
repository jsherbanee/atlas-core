"""Extraction worker invoked in a separate process to bound memory usage."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import resource
import time
import os
from atlas_core.services.pdf_text_extraction_service import PdfTextExtractionService


def worker_main(pdf_path: str, out_json: str) -> None:
    """Worker entrypoint run in a separate process.

    Produces a JSON payload containing extraction pages and resource measurements.
    """
    path = Path(pdf_path)
    start_ts = time.time()
    pid = os.getpid()
    _ = resource.getrusage(resource.RUSAGE_SELF)
    try:
        service = PdfTextExtractionService()
        pages = service.extract_pages(path)
        records = [page.to_dict() for page in pages]
        status = "ok"
        error = None
    except Exception as exc:
        records = []
        status = "error"
        error = str(exc)

    end_ts = time.time()
    rusage_after = resource.getrusage(resource.RUSAGE_SELF)

    payload = {
        "status": status,
        "error": error,
        "pages": records,
        "metrics": {
            "pid": pid,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "elapsed_seconds": end_ts - start_ts,
            # ru_maxrss units are platform dependent (bytes on Linux, kilobytes on macOS)
            "ru_maxrss": getattr(rusage_after, "ru_maxrss", None),
        },
    }

    Path(out_json).write_text(json.dumps(payload), encoding="utf-8")


def run_job_from_jobfile(job_file_path: str) -> None:
    """Run extraction for a job described by a job JSON file and update it.

    This function is safe to use as a multiprocessing target because it is
    defined at module level.
    """
    try:
        job_file = Path(job_file_path)
        data = json.loads(job_file.read_text(encoding="utf-8"))
        dest = data.get("destination")
        if not dest:
            return
        out_json = tempfile.NamedTemporaryFile(delete=False)
        out_json_path = out_json.name
        out_json.close()
        try:
            worker_main(dest, out_json_path)
            payload = json.loads(Path(out_json_path).read_text(encoding="utf-8"))
        except Exception as exc:
            payload = {"status": "error", "error": str(exc), "pages": []}
        finally:
            try:
                Path(out_json_path).unlink()
            except Exception:
                pass

        try:
            data["stage"] = "classifying" if payload.get("status") == "ok" else "failed"
            data["updated_at"] = time.time()
            data["completed_at"] = time.time()
            data["elapsed_time"] = (payload.get("metrics") or {}).get("elapsed_seconds")
            data["worker_pid"] = os.getpid()
            data["failure_reason"] = payload.get("error")
            job_file.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass
    except Exception:
        return


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        worker_main(sys.argv[1], sys.argv[2])

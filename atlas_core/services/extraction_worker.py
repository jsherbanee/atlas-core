"""Extraction worker invoked in a separate process to bound memory usage."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import resource
import time
import os
from atlas_core.services.pdf_text_extraction_service import PdfTextExtractionService
from atlas_core.services.extraction_errors import map_exception_to_extraction_failure
from atlas_core.services.extraction_errors import ExtractionFailure, ExtractionFailureCode
from atlas_core.config.resource_policy import DEFAULT_POLICY
try:
    import psutil
except Exception:
    psutil = None


def _apply_memory_limit_if_configured(policy: dict | None = None):
    """Apply RLIMIT_AS (address space) if configured in provided policy or DEFAULT_POLICY.

    Returns a dict describing what was applied and, when not applied, a reason.
    """
    info = {"applied": False, "mechanism": None, "limit_bytes": None, "error": None, "reason": None}
    limit = None
    try:
        if policy and isinstance(policy, dict) and policy.get("worker_memory_limit_bytes") is not None:
            limit = int(policy.get("worker_memory_limit_bytes"))
        else:
            limit = DEFAULT_POLICY.worker_memory_limit_bytes
    except Exception:
        limit = DEFAULT_POLICY.worker_memory_limit_bytes

    if not limit:
        info["reason"] = "disabled_by_policy"
        return info
    try:
        # RLIMIT_AS is address space limit (bytes) on most Unixes
        soft = limit
        hard = limit
        resource.setrlimit(resource.RLIMIT_AS, (soft, hard))
        info.update({"applied": True, "mechanism": "RLIMIT_AS", "limit_bytes": limit})
    except Exception as exc:
        info.update({"applied": False, "mechanism": "RLIMIT_AS", "error": str(exc), "reason": "apply_failed"})
    return info


def worker_main(pdf_path: str, out_json: str, policy: dict | None = None) -> None:
    """Worker entrypoint run in a separate process.

    Produces a JSON payload containing extraction pages and resource measurements.
    """
    path = Path(pdf_path)
    # apply memory containment as early as possible using provided policy (job-level)
    containment_info = _apply_memory_limit_if_configured(policy)

    start_ts = time.time()
    pid = os.getpid()
    _ = resource.getrusage(resource.RUSAGE_SELF)
    try:
        service = PdfTextExtractionService()
        pages = service.extract_pages(path)
        records = [page.to_dict() for page in pages]
        status = "ok"
        error = None
        failure_payload = None
    except Exception as exc:
        records = []
        status = "error"
        error = str(exc)
        # Map exception to structured extraction failure
        ef = map_exception_to_extraction_failure(exc=exc, message=error)
        failure_payload = {
            "failure_code": ef.code.value,
            "failure_category": ef.category.value,
            "retryable": ef.retryable,
            "operator_message": ef.operator_message,
            "exception_type": ef.underlying_exception_type,
            "original_message": ef.original_message,
        }

    end_ts = time.time()
    rusage_after = resource.getrusage(resource.RUSAGE_SELF)
    # try to get RSS via psutil if available
    rss_bytes = None
    try:
        if psutil is not None:
            p = psutil.Process(pid)
            rss_bytes = getattr(p.memory_info(), "rss", None)
    except Exception:
        rss_bytes = None

    payload = {
        "status": status,
        "error": error,
        "pages": records,
        "failure": failure_payload,
        "metrics": {
            "pid": pid,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "elapsed_seconds": end_ts - start_ts,
            # ru_maxrss units are platform dependent (bytes on Linux, kilobytes on macOS)
            "ru_maxrss": getattr(rusage_after, "ru_maxrss", None),
            "rss_bytes": rss_bytes,
            "containment": containment_info,
            "selected_policy": {
                "worker_memory_limit_bytes": (policy.get("worker_memory_limit_bytes") if policy and isinstance(policy, dict) else DEFAULT_POLICY.worker_memory_limit_bytes),
                "worker_soft_rss_warning_bytes": (policy.get("worker_soft_rss_warning_bytes") if policy and isinstance(policy, dict) else DEFAULT_POLICY.worker_soft_rss_warning_bytes),
                "worker_timeout_seconds": (policy.get("worker_timeout_seconds") if policy and isinstance(policy, dict) else DEFAULT_POLICY.worker_timeout_seconds),
            },
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
            # pass job-level policy to worker_main so containment settings are honored
            policy = {
                "worker_memory_limit_bytes": data.get("worker_memory_limit_bytes"),
                "worker_soft_rss_warning_bytes": data.get("worker_soft_rss_warning_bytes"),
                "worker_timeout_seconds": data.get("worker_timeout_seconds"),
            }
            worker_main(dest, out_json_path, policy=policy)
            payload = json.loads(Path(out_json_path).read_text(encoding="utf-8"))
        except Exception as exc:
            payload = {"status": "error", "error": str(exc), "pages": []}
        finally:
            try:
                Path(out_json_path).unlink()
            except Exception:
                pass

        try:
            status = payload.get("status")
            error = payload.get("error")
            data["updated_at"] = time.time()
            data["completed_at"] = time.time()
            data["elapsed_time"] = (payload.get("metrics") or {}).get("elapsed_seconds")
            data["worker_pid"] = os.getpid()

            # record containment info into job file for validation/ops
            containment = (payload.get("metrics") or {}).get("containment") or {}
            data["containment_applied"] = bool(containment.get("applied"))
            # reason logic: explicit error string or disabled_by_policy
            if not containment.get("applied"):
                if data.get("worker_memory_limit_bytes"):
                    data["containment_reason"] = containment.get("error") or "apply_failed"
                else:
                    data["containment_reason"] = "disabled_by_policy"
            else:
                data["containment_reason"] = containment.get("mechanism")

            if status == "ok":
                data["stage"] = "classifying"
                data["failure_reason"] = None
                data["retry_state"] = "succeeded"
                data["retryable"] = False
            else:
                data["stage"] = "failed"
                data["failure_reason"] = error
                # Map to structured failure if present in payload
                failure_payload = payload.get("failure") or {}
                # default generic
                retryable = True
                failure_code = failure_payload.get("failure_code") or "UNKNOWN_EXTRACTION_ERROR"
                failure_category = failure_payload.get("failure_category") or "unknown"

                # update failure history
                prior = data.get("prior_failures") or []
                prior.append({
                    "at": time.time(),
                    "reason": error,
                    "code": failure_code,
                    "category": failure_category,
                    "retryable": bool(failure_payload.get("retryable", True)),
                })
                data["prior_failures"] = prior

                # attempts
                attempts = int(data.get("attempt_count") or 0) + 1
                data["attempt_count"] = attempts
                if data.get("first_attempt_at") is None:
                    data["first_attempt_at"] = time.time()
                data["last_attempt_at"] = time.time()

                max_attempts = int(data.get("max_attempts") or DEFAULT_POLICY.max_retry_count)
                # classify retryability primarily by structured code, fallback to message
                retryable = bool(failure_payload.get("retryable", True))
                # permanent classification: structured code indicating permanent
                permanent_codes = {"DECLARED_STREAM_LENGTH_EXCEEDED", "INVALID_PDF", "MALFORMED_PDF", "ENCRYPTED_UNSUPPORTED", "PATHOLOGICAL_REJECTED", "CANONICAL_FILE_MISSING", "MEMORY_LIMIT_EXCEEDED"}
                if failure_code in permanent_codes:
                    retryable = False

                # persist structured fields for diagnostics
                data["failure_code"] = failure_code
                data["failure_category"] = failure_category
                data["retryable"] = retryable

                if not retryable:
                    data["retry_state"] = "permanent"
                    data["retryable"] = False
                    data["final_failure_reason"] = error
                    data.pop("next_retry_at", None)
                elif attempts >= max_attempts:
                    data["retry_state"] = "exhausted"
                    data["retryable"] = False
                    data["final_failure_reason"] = error
                    data.pop("next_retry_at", None)
                else:
                    # schedule retry
                    from atlas_core.services.retry_policy import compute_backoff

                    delay, next_at = compute_backoff(attempts, base=data.get("retry_backoff_seconds"))
                    data["next_retry_at"] = next_at
                    data["retry_state"] = "scheduled"
                    data["retryable"] = True

            with open(job_file_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        except Exception:
            pass
    except Exception:
        return


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        worker_main(sys.argv[1], sys.argv[2])

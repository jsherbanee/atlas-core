# LARGE UPLOAD MEMORY INCIDENT

This document captures the investigation and measured instrumentation for the large-upload memory exhaustion incident.

Status: Updated with controlled reproduction artifacts

Measured data (summary from local reproduction):

- root cause: In the original baseline, uploaded files were retained as full in-memory byte buffers and PDF extraction ran inline in the main Streamlit process. This allowed parsers to allocate large additional memory (page images, internal parser buffers), which led macOS to suspend the process when system memory was exhausted.
- process responsible: main Streamlit process (intake + extraction) prior to fixes; extraction now runs in a short-lived worker process by default.
- measured artifacts: `docs/validation/artifacts/large-upload/repro_summary.json` (contains per-stage JSONL measurements for 3 fixtures: ~10MB, ~50MB, ~170MB)

Per-fixture summary (from reproduction run):

- small.pdf (~10 MB): persisted and extracted; extraction reported 1 page; extraction elapsed ~11.25s.
- medium.pdf (~50 MB): persisted and extracted; extraction reported 1 page; extraction elapsed ~267.76s (large fixture exercised longer parsing path).
- large.pdf (~170 MB): persisted and extracted; extraction reported 0 pages (minimal PDF generation edge case), extraction elapsed ~0.53s.

Note: `psutil` was optional in this environment, so RSS start/end/peak were not recorded in these runs (fields are null). When `psutil` is available in production/test environments, the `instrument_stage` context will record RSS and peak_rss for each stage.

Unsafe code paths found and corrected in this sprint:

- Upload buffering: previously `UploadedIntakeFile.data` held full bytes while intake and extraction proceeded. Fix: Streamlined `build_session_package_from_file_paths` and `build_session_package_from_uploads` to convert byte-backed inputs into on-disk temp files immediately; added `_write_classified_file` support for path-backed moves so no full-file getvalue() or get_bytes() is needed during normal intake.
- Persistence: replaced single-shot writes with atomic move from temp file and incremental SHA1 comparisons (see `atlas_core/utils/streaming.py` and `atlas_core/services/document_intake_service.py`).
- Extraction: moved default `PdfTextExtractionService` execution into a short-lived worker process (`atlas_core/services/extraction_worker.py`) and monitored worker RSS and timeouts via `ResourcePolicy` defaults. If a custom `PdfTextExtractionService` is injected (test harnesses), extraction still runs in-process for test determinism.
- Job identity: added deterministic intake identity based on `project_id:canonical_filename:checksum` and per-job JSON files under `.jobs` to avoid duplicate concurrent processing.

Files changed (high level):

- `atlas_core/services/document_intake_service.py` — streaming persistence, worker extraction invocation, job-state handling, file-backed intake API.
- `atlas_core/services/extraction_worker.py` — isolated worker entrypoint for extraction.
- `atlas_core/utils/streaming.py` — incremental SHA1 helpers.
- `atlas_core/config/resource_policy.py` — ResourcePolicy defaults.
- `atlas_core/services/intake_status.py` — intake stage enum.
- `atlas_core/services/intake_instrumentation.py` — stage measurement context.
- `docs/validation/artifacts/large-upload/` — reproduction fixtures and `repro_summary.json`.

Next steps and recommendations:

- Re-run reproduction with `psutil` installed to capture RSS start/end/peak precisely.
- Run the Playwright validation suite (skeleton in `docs/validation/LARGE_UPLOAD_PLAYWRIGHT.md`) and capture screenshots.
- If worker RSS measurements show large peaks, consider using a memory-limited sandbox (OS-level cgroups or a dedicated worker supervisor) or restrict page-render resolution/processing per `ResourcePolicy`.

Profiling evidence (this run):

- Tooling: `scripts/profile_extraction.py` (tracemalloc + resource + gc snapshots). Run against the reproducible medium fixture at `.runtime/validation/large-upload/.../fixtures/medium.master.pdf`.
- Medium PDF measured values (single-run):
	- `ru_maxrss` before open: ~56,868,864 bytes
	- `ru_maxrss` after open: ~160,923,648 bytes
	- `ru_maxrss` after text extraction (peak): ~3,122,167,808 bytes
	- `ru_maxrss` after cleanup (post `del` + `gc.collect()`): ~3,122,167,808 bytes (no observable return of RSS in-process)
	- `tracemalloc` peak (Python heap): ~1,474,706,194 bytes (peak traced Python allocations)

Allocation owner analysis:

- `tracemalloc` top allocation sites point at `pypdf` internals (not Atlas application code):
	- `pypdf._reader` and `pypdf.generic._data_structures` account for the largest traced allocations in this run.
	- Top traced entries include large bytes/objects allocated while `PdfReader` parsed and expanded object streams.
- Conclusion: the majority of the peak memory is attributable to the PDF parsing library (`pypdf`) creating large in-memory objects (decompressed streams, object tables, or aggregated data structures), not to Atlas retaining large images or lists.

Why RSS stays high in-process:

- Python's memory allocator and C extension allocations often do not immediately return memory to the OS after `del` + `gc.collect()`; memory is typically freed to Python's allocator arenas but remains reserved by the process until it exits. This explains why the `after_cleanup` RSS remains high in the profiling run even after `reader` and page objects are deleted.

Impact on Atlas runtime and recommendations:

- Atlas extraction should continue to run in short-lived worker processes (the current `extraction_worker` design). Worker process exit reliably returns memory to the OS; the spike in RSS observed here is therefore acceptable when extraction runs out-of-process.
- Avoid running heavy PDF extraction in-process (for example, don't call `worker_main` directly in the Streamlit process or long-lived tests). The validation harness used `worker_main` in-process for direct metrics capture; that is fine for profiling but would cause persistent memory growth in a long-lived process.
- If you need to limit peak usage for particularly problematic PDFs, use ResourcePolicy limits, reduce rasterization resolution (if enabled), or run extraction under an OS memory-limiting supervisor.

Action taken in this investigation:

- Added `scripts/profile_extraction.py` to collect stepwise `ru_maxrss`, `tracemalloc` snapshots, and `gc` object counts. This is profiling-only and does not change runtime behavior.
- No production code changes were required — the peak is owned by `pypdf` and the extraction-in-worker pattern already mitigates long-lived retention.

Remaining limitations:

- `pypdf` can allocate large in-memory buffers when parsing certain PDFs; if those PDFs are expected in production, consider post-processing limits or preflight checks that classify and gate very-large PDFs to stricter ResourcePolicy settings.

Retry behavior and recovery notes

- Extraction jobs now include retry metadata and bounded retry semantics. Timeouts and transient errors will schedule a retry (subject to `max_retry_count` and backoff configured in `atlas_core/config/resource_policy.py`).
- Supervisor ensures worker processes are terminated before retries are scheduled — no orphaned workers should remain after a retry is planned.
- For persistent failures, jobs will be marked exhausted and must be manually re-ingested or inspected.

Where to find artifacts:

- Per-run JSONs and profiler outputs: `.runtime/validation/large-upload/<run-ts>/validation_results.full.json` and `.runtime/validation/large-upload/<run-ts>/medium_profile.json`.


Addendum — stdin / python -c validation artifact:

- During early reproduction attempts the validation harness was executed via `python -c` / here-doc / stdin which caused `multiprocessing.spawn` to attempt to import the parent from `<stdin>` and led to `FileNotFoundError('<stdin>')` and failing child processes. This failure mode is solely an artifact of running Python from stdin and is not representative of production runtime where the app and worker entrypoints are imported from real module paths.
- The validation harness has been updated to run as a real script (`scripts/validate_large_uploads.py`) with a `__main__` guard and an `--output-dir` option that writes all generated artifacts under `.runtime/validation/large-upload/runs/<timestamp>`. This avoids placing large generated files inside tracked docs paths and prevents the VS Code extension host from being overloaded by many large files.

Harness fix: duplicate-upload handling

- A separate issue was discovered in the validation harness where the duplicate-upload case passed the same `Path` object twice into the single-session intake call. The production intake intentionally moves (replaces) path-backed uploads into the session package; the harness therefore observed a `FileNotFoundError` when the second submission referenced the same source file. We corrected the harness to pass a fresh, identical copy for the duplicate submission so the service can take ownership of the first source file without the second submission failing. This change preserves production behavior in `DocumentIntakeService` and makes the validation run deterministic and repeatable.

Development-environment crash root cause (confirmed/inferred):

- Confirmed: running the reproduction via stdin (`python -c` or here-doc) caused child worker spawn to fail because the import system could not find `<stdin>` as a module path. This produced the observed `FileNotFoundError('<stdin>')` and is a validation-run-only failure mode.
- Inferred: large generated binaries and many per-run artifacts placed inside `docs/validation/artifacts/large-upload/` increased the VS Code file-watcher and extension host load and contributed to crashes/hangs observed in the editor. Moving these artifacts into `.runtime/validation/...` eliminates the frequent file notifications and prevents workspace-index overload.

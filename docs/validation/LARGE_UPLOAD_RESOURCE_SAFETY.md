# LARGE UPLOAD RESOURCE SAFETY

This document describes the resource-safety policy implemented for intake processing.

Key changes:
- Added configurable resource policy: atlas_core/config/resource_policy.py
- Added streaming helpers to compute checksums and write files without extra buffering: atlas_core/utils/streaming.py
- Added lightweight instrumentation to capture timing and resident set size (RSS): atlas_core/services/intake_instrumentation.py
- Added intake stage enum for UI and job status surfaces: atlas_core/services/intake_status.py

Defaults are conservative for local development. Further tuning is required for production.

Preflight classification:

- A lightweight PDF preflight classifier (`atlas_core/services/pdf_preflight.py`) inspects a small head/tail sample of the file to detect:
	- PDF header presence
	- encryption (`/Encrypt`), linearized flag (`/Linearized`)
	- estimated page count via `/Count` hints
	- declared stream lengths via `/Length` entries

- The classifier returns: `classification`, `reasons`, `attributes`, `confidence`, and a `recommended_policy` (one of `standard`, `large`, `very_large`, `pathological`).

- The classifier is intentionally conservative and does not load or render pages; it is designed to run quickly on ingestion and select a ResourcePolicy before spawning extraction workers.

Scheduler and Policy-Aware Execution

- A process-local scheduler (`atlas_core/services/job_scheduler.py`) now enforces ResourcePolicy before any extraction worker is spawned.
- The scheduler maintains FIFO queues per policy tier (`standard`, `large`, `very_large`, `pathological`) and a minimal in-memory active set.
- Concurrency slots are enforced per-tier:
	- `standard` limited by `standard_job_concurrency`.
	- `large` limited by `max_concurrent_large_documents`.
	- `very_large` runs alone and blocks all other extractions while active.
- `pathological` behavior is controlled by `ResourcePolicy.pathological_file_behavior` and may be `reject`, `quarantine`, or `strict`.
- Worker processes are only spawned after scheduler admission. The intake flow consults the scheduler and records scheduler metadata in the job JSON.

Queue & Serialization Guarantees

- FIFO ordering is preserved within each tier. When slots free, queued jobs are admitted in tier-priority order (very_large -> large -> standard), and large jobs are not starved by standard jobs.
- If a `very_large` job is waiting, it will not be admitted until all active workers complete; if a `very_large` job is running, no other jobs will be admitted.

Job metadata written to `.jobs/<intake_identity>.json` now includes scheduler fields:

- `scheduler_state` — one of `queued`, `admitted`, `rejected`.
- `queue_position` — numeric position in the queue when queued.
- `queue_entered_at` — timestamp when queued.
- `admitted_at` — timestamp when admitted.
- `active_worker_count` — best-effort count of active workers at admission time.
- `policy_tier` — selected policy tier for the job.
- `scheduler_version` — scheduler implementation version string.

Observability

- The scheduler emits structured events to the `atlas.scheduler` logger for `queued`, `admitted`, `started`, `completed`, and `rejected` events. Each event includes `job_id`, `policy_tier`, `wait_time`, `active_count`, and `queue_length`.

Startup Reconciliation

- A `ReconciliationService` (`atlas_core/services/reconciliation.py`) performs a deterministic startup scan of `outputs/uploads/*/.jobs/*.json` and rebuilds the in-memory scheduler state.
- Terminal jobs (`completed`, `failed`, `rejected`, `cancelled`) are ignored and annotated with `reconciled_at` and `reconciliation_action: ignored`.
- Non-terminal jobs are inspected for `worker_pid`, timestamps, and staleness thresholds. Actions include `verified` (active PID exists), `requeued` (placed back into scheduler), or `failed` (orphaned/stale worker).
- Reconciliation writes `reconciled_at`, `reconciliation_reason`, `reconciliation_action`, `previous_scheduler_state`, and `scheduler_generation` into job JSON.
- The reconciliation process emits structured events: `startup_scan`, `job_verified`, `job_requeued`, `job_failed`, and `scheduler_rebuilt`.

Automatic Streamlit Startup Reconciliation

- The Streamlit application automatically runs startup reconciliation once per process during application initialization to rebuild in-memory scheduler state before admitting new extraction jobs.
- The startup run is guarded by an exactly-once process-local lock: repeated Streamlit reruns in the same process will not re-run reconciliation.
- Environment variables to control behavior:
	- `ATLAS_STARTUP_RECONCILIATION_ENABLED` — if set to `0` or `false` the startup run is skipped (default: enabled).
	- `ATLAS_RECONCILIATION_ROOT` — path to uploads root scanned (default: `outputs/uploads`).
	- `ATLAS_RECONCILIATION_FAIL_CLOSED` — if set (`1`/`true`), a startup failure leaves admissions blocked (rejecting new submissions); otherwise the system fail-opens and allows new submissions while marking startup as degraded.
- While reconciliation runs the scheduler admission mode is deterministically set to `queue` so new submissions are queued until the rebuild completes. On success the scheduler is restored to `allow` admission. On failure the helper honors the `FAIL_CLOSED` flag to choose `reject` (closed) or `allow` (open).

Manual reset and retry

- For operational recovery or in tests, the process-local startup guard can be reset via `atlas_core.services.reconciliation.reset_startup_reconciliation()`; calling `ensure_startup_reconciliation()` after reset will run the startup scan again.

Limitations

- The automatic startup reconciliation is wired into the Streamlit UI startup path only. Other entrypoints (for example, worker-only processes or external supervisors) do not yet invoke reconciliation automatically and should call `ensure_startup_reconciliation()` if they require scheduler state reconstruction.
- Reconciliation is best-effort and process-local; it does not replace external durable coordination for high-availability deployments.

Implementation Notes & Limitations

- Reconciliation is process-local and best-effort. It annotates job JSON with `reconciled_at`, `reconciliation_reason`, `reconciliation_action`, `previous_scheduler_state`, and `scheduler_generation`.
- PID existence is detected via `psutil.pid_exists()` when `psutil` is available, or via `os.kill(pid, 0)` on POSIX as a fallback.
- Active jobs are restored only if PID checks pass and policy serialization rules allow it; otherwise the job is queued.
- The scheduler in-memory state is not durable across a process restart beyond this reconciliation step; operators should run reconciliation at startup and consider external orchestration for HA.

Retry & Failure Recovery

- Jobs now carry retry metadata in their job JSON; key fields include:
	- `attempt_count`, `max_attempts`
	- `first_attempt_at`, `last_attempt_at`, `next_retry_at`
	- `retry_backoff_seconds`, `prior_failures`, `retry_state`, `final_failure_reason`

- Failure classification distinguishes `retryable` vs `permanent` failures. Examples:
	- retryable: transient worker crash, temporary file access error, supervisor launch failure, recoverable timeout (when policy allows)
	- permanent: malformed/invalid PDF, encrypted unsupported PDF, pathological policy rejection, missing canonical source, exhausted retries

- Backoff calculation is deterministic by default: `delay = min(max_delay, base * multiplier^(attempt-1))`. Defaults come from `atlas_core.config.resource_policy.DEFAULT_POLICY` and are deterministic (no jitter) to keep tests reproducible.

- On a retryable failure the job JSON is updated (attempt_count, prior_failures, next_retry_at) and the job is marked `retry_state: scheduled`. The original job JSON and canonical files are preserved; no duplicate job files are created.

- A process-local retry dispatcher (`atlas_core/services/retry_dispatcher.py`) scans uploads for due retries and resubmits them to the scheduler when `next_retry_at` has elapsed. The dispatcher is started automatically in the Streamlit startup path and is singleton-per-process. It sleeps until the next due retry and is thread-safe.

- When retries are exhausted the job is marked `retry_state: exhausted` and `final_failure_reason` is set; the job becomes terminal and will not be requeued.

- Timeout behavior: timeouts are recorded as failures and treated as retryable by default (subject to `max_attempts`). Supervisor ensures worker termination before scheduler slots are released and retries are scheduled.

- Reconciliation integrates retry state:
	- Jobs with `next_retry_at` in the future are deferred during startup (not admitted) and annotated with `reconciliation_action: deferred`.
	- Jobs with `next_retry_at` past due are eligible for resubmission during reconciliation and will be submitted to the scheduler (which enforces policy and admission gating).
	- Reconciliation preserves prior failure history and does not duplicate scheduled retries across repeated startups in the same process.

	---

	**Large Document Processing v1.0 — Complete**

	- **Status:** Complete
	- **Summary:** Resource-safety mechanisms (ResourcePolicy propagation, worker memory containment via RLIMIT_AS, policy-aware scheduler tiers, startup reconciliation, bounded retry/backoff, and operational reporting) are implemented and validated. See `docs/validation/artifacts/large-upload/validation_results.json` for representative validation results.




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


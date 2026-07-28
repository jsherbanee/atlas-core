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

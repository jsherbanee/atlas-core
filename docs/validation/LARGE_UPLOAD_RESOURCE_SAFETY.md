# LARGE UPLOAD RESOURCE SAFETY

This document describes the resource-safety policy implemented for intake processing.

Key changes:
- Added configurable resource policy: atlas_core/config/resource_policy.py
- Added streaming helpers to compute checksums and write files without extra buffering: atlas_core/utils/streaming.py
- Added lightweight instrumentation to capture timing and resident set size (RSS): atlas_core/services/intake_instrumentation.py
- Added intake stage enum for UI and job status surfaces: atlas_core/services/intake_status.py

Defaults are conservative for local development. Further tuning is required for production.

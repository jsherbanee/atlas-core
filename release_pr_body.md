## Summary

This PR completes the production hardening of Atlas's large-document ingestion subsystem and marks Large Document Processing v1.0 complete.

## Major additions

- File-backed upload intake
- Deferred extraction workers
- ResourcePolicy propagation
- Worker memory containment
- Timeout supervision
- PDF preflight classification
- Policy-aware scheduling
- Startup reconciliation
- Deterministic retry and exponential backoff
- Structured extraction failure taxonomy
- Atomic permanent-failure transitions
- Operational reporting
- Large-upload validation harness

## Reliability improvements

- Permanent parser failures now terminate deterministically
- Structured failure codes drive retry decisions
- Legacy message-based classification remains only as a compatibility fallback
- Worker containment policy propagates from job metadata to worker startup
- Startup reconciliation restores queued and interrupted jobs
- Retry dispatch respects scheduler policy and backoff timing
- Permanent failures cannot be requeued by the dispatcher or reconciliation
- Declared-stream-length classification race was eliminated

## Validation

- `git diff --check`: passed
- Full test suite: 1688 passed
- Declared-stream permanent-failure stress test: 50/50 passed
- Large-upload validation harness completed successfully
- Structured error codes verified
- Retry classification verified
- Worker containment propagation verified

## Documentation

Updated:

- DEVELOPMENT_STATUS.md
- EPICS.md
- ENGINEERING_ROADMAP.md
- RELEASE_NOTES.md
- LARGE_UPLOAD_RESOURCE_SAFETY.md
- LARGE_UPLOAD_COMPLETION.md
- ALPHA_OPERATIONS.md

The roadmap now records:

**Large Document Processing v1.0 — Complete**

## Known limitations

- Retry dispatch and reconciliation remain process-local
- Multi-process or multi-host deployments require centralized coordination
- Parser-library limitations remain for some pathological PDFs
- RLIMIT_AS and RSS semantics vary by operating system
- Legacy substring mapping remains as a compatibility fallback
- Worker-only entrypoints must explicitly initialize reconciliation and retry dispatch when used outside the Streamlit process

## Next roadmap priorities

1. Complete Phase 2 — Bid Intelligence
2. Expand Knowledge entities and relationships
3. Advance deterministic estimating, assemblies, and labor
4. Build procurement and RFQ workflows
5. Continue construction, commissioning, and service lifecycle capabilities

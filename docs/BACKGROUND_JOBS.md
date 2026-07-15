# Deterministic Background Jobs

## Purpose
This document defines the Sprint P-03 deterministic background job framework used by Atlas for local, tenant-scoped, auditable job execution.

## P-05 Integration Note

Sprint P-05 document generation is designed to execute safely under the existing deterministic background-job contract.
Generation payloads and template snapshots are deterministic, so job retries and replays preserve output reproducibility for a fixed revision and template snapshot.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
- [OBSERVABILITY.md](OBSERVABILITY.md)
- [SECURITY.md](SECURITY.md)
- [AUDIT_ENGINE.md](AUDIT_ENGINE.md)

## Scope
P-03 introduces a storage-agnostic job orchestration contract and a deterministic local executor.

Implemented representative workflows:
- project document import
- project bundle export generation

## Explicit Constraints
- no AWS queue implementation
- no external worker deployment
- no cloud scheduler coupling

The current execution model is in-process and deterministic by design.

## Core Contracts
Primary contracts are defined in `atlas_core/contracts/background_job_contracts.py`.

Key entities:
- `JobRequest`
- `JobRecord`
- `JobAttempt`
- `JobProgress`
- `JobDiagnostic`
- `JobResult`
- `JobRetryPolicy`
- `JobCancellation`
- `JobAuditReference`

Status model:
- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`
- `retry_scheduled`

## Service Model
`BackgroundJobService` orchestrates lifecycle operations:
- submit
- run
- retry
- cancel
- list

Service behavior:
- deterministic job ID generation
- idempotency key duplicate suppression for active jobs
- immutable attempt append model
- tenant and organization scope checks on run/retry/cancel/list
- audit callback emission for lifecycle transitions

## Repository Model
Repository contract:
- `JobRepository` in `atlas_core/repository/contracts.py`

Local adapter:
- `LocalJobRepository` in `atlas_core/repository/local.py`
- persisted in `AtlasProjects/<project_id>/jobs/jobs.jsonl`

## Workspace Integration
`ProjectWorkspaceService` registers deterministic handlers for:
- `document_import`
- `export_generation`

Workspace API wrappers:
- `run_document_import_job`
- `run_export_generation_job`
- `list_background_jobs`
- `retry_background_job`
- `cancel_background_job`

## UI Integration
`apps/phase2_review_app.py` includes a Processing page that:
- lists jobs with progress and result/failure summaries
- enforces `jobs.view` and `jobs.manage` permissions
- provides retry and cancel actions where valid

Representative workflow migration:
- document upload now executes through background jobs
- export bundle action now executes through background jobs

## Security and Multi-Tenant Notes
Job operations require consistent `tenant_id` and `organization_id` scope.
Cross-scope job access fails by design.

Payloads must remain deterministic and safe for local persistence.

## Observability and Audit
Background job lifecycle transitions emit immutable audit events through the manager callback.

Job records store linked immutable audit event IDs via `JobAuditReference`.

## Future Evolution
Planned future adapters may add queue-backed dispatch and external workers without changing workspace-facing job contracts.

Contract compatibility requirements:
- preserve deterministic status semantics
- preserve audit linkage
- preserve tenant-scope enforcement
- preserve idempotency semantics

## P-04 Attachment Hook Integration

Sprint P-04 attachment lifecycle events emit deterministic background-hook request payloads for future processing.

Current emitted hook intents:
- malware scan
- preview generation
- search indexing

These hooks are callback payload emissions only in current implementation and do not introduce worker orchestration changes.
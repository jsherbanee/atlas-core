# Audit Engine

## Purpose
This document defines Atlas immutable audit behavior and the current engine implementation boundaries.

## P-05 Integration Note

Sprint P-05 document generation flows are audit-ready through existing immutable audit patterns.
Template assignment, template version snapshot, output hash, and revision identity are emitted in generation activity metadata so audit callbacks can persist deterministic provenance without introducing a second audit model.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [SECURITY.md](SECURITY.md)
- [OBSERVABILITY.md](OBSERVABILITY.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [BACKGROUND_JOBS.md](BACKGROUND_JOBS.md)

## Current Implementation
Atlas provides immutable audit contracts in `atlas_core/contracts/audit_contracts.py` and a service implementation in `atlas_core/services/immutable_audit_service.py`.

Current behavior:
- append-only event model persisted through project history
- deterministic event IDs
- tenant and organization scoping
- previous-event linkage for event-chain continuity
- redaction of sensitive payload keys
- export support for scoped audit bundles

## Event Model
Primary audit entities:
- `AuditActor`
- `AuditTarget`
- `AuditPermissionReference`
- `ImmutableAuditEvent`
- `AuditExportRecord`

Retention classes:
- `operational`
- `compliance`
- `security`

## Persistence and Compatibility
Audit events are stored through existing history persistence, preserving repository compatibility.

Compatibility behavior:
- native immutable audit events are persisted as `audit_event`
- legacy history events can be normalized to immutable audit shape for scoped listing/export

## Security Notes
Sensitive keys are redacted before persistence.

Redaction targets include common secret material such as:
- password
- token
- secret
- api_key
- private_key
- authorization

## P-03 Integration
Background job lifecycle transitions emit immutable audit events through manager callbacks.

Representative emitted actions:
- `background_job.created`
- `background_job.completed`
- `background_job.failed`
- `background_job.retry_scheduled`
- `background_job.retry_requested`
- `background_job.cancelled`

## Operational Boundaries
Current scope is deterministic local persistence and local listing/export.

Out of scope:
- external SIEM transport
- real-time streaming pipelines
- cloud-native audit bus deployment

## P-04 Attachment Audit Integration

Sprint P-04 unified attachment operations emit immutable audit actions when project context is available.

Representative attachment audit actions:
- `attachment.uploaded`
- `attachment.version.created`
- `attachment.linked`
- `attachment.unlinked`
- `attachment.archived`
- `attachment.restored`
- `attachment.downloaded`

Attachment activity records retain linked audit event IDs for deterministic traceability.
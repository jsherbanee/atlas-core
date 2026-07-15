# Error Logging

## Purpose
Define the controlled-alpha application error logging model used for tenant-scoped diagnostics, support triage, and resolution workflow.

This logging model augments, and does not replace, immutable audit events.

## Scope
Implemented in A-02 pt 2:
- reusable error contracts for severity, context, occurrence, and resolution status
- tenant-scoped application error records with deterministic fingerprint grouping
- per-occurrence history retained under grouped error records
- user-safe error reference IDs for support follow-up
- redaction of sensitive values in messages and stack traces
- status workflow support (new, acknowledged, investigating, resolved, ignored, reopened)
- audit events for error creation, status updates, and reopened errors
- platform-management Error Log review and diagnostics export surfaces

Out of scope:
- external APM or SIEM integrations
- cloud log streaming pipelines
- public stack-trace display

## Contracts
Primary contracts are defined in:
- atlas_core/contracts/error_logging_contracts.py

Contract entities:
- ApplicationError
- ErrorOccurrence
- ErrorSeverity
- ErrorResolutionStatus
- ErrorContext

Key fields:
- stable error_id (user-facing reference)
- deterministic fingerprint
- tenant_id
- actor_id
- environment_label
- application_version
- exception_type
- sanitized_message
- sanitized_stack_trace
- workspace and route
- related object type/id
- correlation_id
- background_job_id
- request_or_session_ref
- occurrence_count
- first_seen_at
- last_seen_at
- status
- resolution_notes

## Service Integration
Error logging operations are implemented on TenantManagerService:
- log_application_error
- list_application_errors
- get_application_error_details
- update_application_error_status
- export_application_error_diagnostics

Application shell integration:
- unhandled exceptions are logged before showing a user-safe message
- platform-management operational failures are explicitly logged with error IDs

## Redaction Rules
The sanitizer redacts or normalizes:
- secret references (`secret://...`)
- token/password/credential-like content
- API key / private key / authorization-like content
- filesystem paths
- email addresses

User-facing UI only shows sanitized summaries and Error IDs.

## Grouping And Occurrences
Errors are grouped by deterministic fingerprint derived from:
- tenant
- exception type
- sanitized message
- workspace and route
- related object context
- correlation/job references

Each group retains individual occurrences with timestamp, sanitized message, sanitized stack trace, and actor where available.

## Access Model
- Platform administrators in platform scope (`local`/`atlas`) may review cross-tenant metadata.
- Tenant-scoped users may review only their tenant.
- Suspended tenants are blocked from operational error-log access.

## Status Workflow
Supported statuses:
- new
- acknowledged
- investigating
- resolved
- ignored
- reopened

Status and notes updates emit tenant audit events.

## Health Check Integration
Alpha health-check summaries include:
- recent errors by severity
- unresolved error count
- sanitized recent error entries

No secrets, raw paths, or foreign-tenant details are exposed.

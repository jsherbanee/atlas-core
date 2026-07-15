# Alpha Operations (A-04)

## Purpose
Define controlled alpha deployment, tester onboarding, release triage, and stabilization behavior for repeatable tenant-isolated validation.

## Scope
A-04 extends controlled alpha operations with release and defect stabilization workflow controls without introducing new product workflows.

Implemented:
- controlled alpha environment marker and release-channel guard in the application shell
- visible alpha version identifier and environment labeling
- platform-management tenant workflow support for create/open/suspend/restore/archive/seed/reset/export/delete
- administrator-only alpha health-check surface
- tenant-scoped alpha feedback and defect records
- centralized tenant-scoped application error logging with deterministic fingerprint grouping
- platform-management error review workflow with status transitions and diagnostics export
- settings access for known limitations and operator checklist guidance
- defect-template download and environment-diagnostics capture
- tester profile assignment and lifecycle-state tracking
- onboarding acknowledgement recording (terms and known limitations)
- deterministic scenario assignment and completion tracking per tester
- sandbox reset/export request intake tied to tester profiles
- platform-admin operations dashboard for cross-tenant rollout visibility
- alpha release record lifecycle and stabilization release history
- tester cohort assignment to controlled alpha release records
- feedback triage queue and feedback-to-defect conversion workflow
- defect classification with reproduction and retest progression
- release-note and regression-test linkage for stabilization evidence

Out of scope:
- commercial workflow expansion
- inventory/procurement activation
- live QuickBooks transport execution
- hosted infrastructure automation
- SSO/Cognito, billing, or self-service signup
- external ticketing integration

## Operational Controls
### Environment and Release Guard
- Effective release channel is fixed to `controlled-alpha`.
- If `ATLAS_RELEASE_CHANNEL` is set to `production` or `prod`, Atlas shows a warning and blocks production designation.

### Platform Management Boundaries
- Tenant lifecycle actions remain gated by `platform.tenants.manage` in platform scope (`tenant_id=local`, `organization_id=atlas`).
- Sandbox reset and delete remain confirmation-guarded.
- Export-before-delete remains enforced.
- Tester assignment, onboarding acknowledgements, scenario updates, and tester status changes remain platform-admin-only in platform scope.

### Tenant Scope Boundaries
- Feedback records are tenant-scoped and reject cross-tenant diagnostics access.
- Alpha health-check output is tenant-specific and does not include internal storage paths or secret references.
- Application error logs are tenant-scoped by default; cross-tenant review is platform-admin-only in platform scope.
- Suspended tenants cannot access operational error-log surfaces.

### A-03 Tester Rollout Controls
- Tester states are explicit and auditable: `invited`, `onboarding`, `active`, `paused`, `completed`, `deactivated`.
- Deactivated and paused tester access checks are explicitly denied.
- Scenario tracking is deterministic with constrained statuses: `pending`, `in_progress`, `completed`.
- Sandbox reset/export requests are tracked per tester and surfaced in operations reporting.

### A-04 Release and Stabilization Controls
- Release records track version, date, commit hash, included fixes, known limitations, scenario coverage, cohort assignment, rollback reference, and release status.
- Defects support severity and lifecycle statuses required for controlled triage and retest handoff.
- Enhancements are classified as backlog/deferred work and do not enter stabilization by default.
- Severity, status, assignment, release, and closure changes are auditable.
- Tenant users may view status for their own submitted feedback/defects; cross-tenant triage remains platform-admin-only.

### Error Logging Controls
- Unhandled exceptions are logged before user-facing error messaging.
- Explicitly handled operational failures log structured, sanitized error records.
- Repeated failures are grouped by deterministic fingerprint and retain individual occurrence history.
- User-facing error messaging provides a referenceable Error ID and does not expose raw stack traces.
- Error status and resolution-note updates emit tenant audit events.

## Alpha Health Check Contract
Administrator-only health checks provide:
- application version
- environment label
- tenant ID and tenant status
- repository health summary
- seed-data status
- background-job health summary
- attachment storage health summary
- search-index status summary
- recent errors by severity (redacted)
- unresolved error count
- last backup or export metadata
- test-suite baseline reference

## Feedback And Defect Model
Structured tenant-scoped fields:
- tenant
- user
- workspace
- object or transaction
- severity
- reproduction steps
- expected result
- actual result
- attachment references
- environment diagnostics (redacted for sensitive keys)
- related Error ID
- status
- resolution notes

Supported statuses:
- `open`
- `in_review`
- `resolved`
- `closed`

## Operator Runbook Links
- [ALPHA_RELEASE_PROCESS.md](ALPHA_RELEASE_PROCESS.md)
- [ALPHA_TEST_PLAN.md](ALPHA_TEST_PLAN.md)
- [ALPHA_SANDBOX_GUIDE.md](ALPHA_SANDBOX_GUIDE.md)
- [ALPHA_TESTER_ONBOARDING.md](ALPHA_TESTER_ONBOARDING.md)
- [ALPHA_RELEASE_CHECKLIST.md](ALPHA_RELEASE_CHECKLIST.md)
- [ALPHA_KNOWN_LIMITATIONS.md](ALPHA_KNOWN_LIMITATIONS.md)
- [ERROR_LOGGING.md](ERROR_LOGGING.md)

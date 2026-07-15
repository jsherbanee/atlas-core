# Alpha Operations (A-02)

## Purpose
Define controlled alpha deployment and test-operations behavior for repeatable tenant-isolated validation.

## Scope
A-02 operationalizes controlled alpha testing without introducing new product workflows.

Implemented:
- controlled alpha environment marker and release-channel guard in the application shell
- visible alpha version identifier and environment labeling
- platform-management tenant workflow support for create/open/suspend/restore/archive/seed/reset/export/delete
- administrator-only alpha health-check surface
- tenant-scoped alpha feedback and defect records
- settings access for known limitations and operator checklist guidance
- defect-template download and environment-diagnostics capture

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

### Tenant Scope Boundaries
- Feedback records are tenant-scoped and reject cross-tenant diagnostics access.
- Alpha health-check output is tenant-specific and does not include internal storage paths or secret references.

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
- recent errors (redacted)
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
- status
- resolution notes

Supported statuses:
- `open`
- `in_review`
- `resolved`
- `closed`

## Operator Runbook Links
- [ALPHA_TEST_PLAN.md](ALPHA_TEST_PLAN.md)
- [ALPHA_SANDBOX_GUIDE.md](ALPHA_SANDBOX_GUIDE.md)
- [ALPHA_RELEASE_CHECKLIST.md](ALPHA_RELEASE_CHECKLIST.md)
- [ALPHA_KNOWN_LIMITATIONS.md](ALPHA_KNOWN_LIMITATIONS.md)

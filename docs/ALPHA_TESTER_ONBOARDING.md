# Alpha Tester Onboarding (A-03)

## Purpose
Define the controlled onboarding and rollout process for a small external alpha cohort using isolated sandbox tenants.

## Scope
In scope:
- assign named tester profiles to isolated tenant sandboxes
- record onboarding acknowledgements (terms and known limitations)
- assign and track deterministic scenario completion
- capture tester lifecycle state (`invited`, `onboarding`, `active`, `paused`, `completed`, `deactivated`)
- allow platform-admin reset/export request intake tied to tester profiles
- provide platform-admin operations dashboard visibility across sandbox tenants

Out of scope:
- public signup
- SSO or identity-provider automation
- billing or subscription workflows
- live QuickBooks transport execution
- new commercial workflow capability expansion

## Roles
- Platform admin (required): manages tester profile lifecycle and cross-tenant operations in platform scope (`local` / `atlas`).
- Tenant-scoped users: do not manage cross-tenant tester onboarding surfaces.

## Onboarding Checklist
1. Create or confirm sandbox tenant is active.
2. Assign tester profile (`tester_id`, display name, email, optional expiration).
3. Record required acknowledgements:
- terms acknowledgement
- known limitations acknowledgement
4. Assign baseline test scenarios.
5. Validate tester can access assigned sandbox while active.
6. Record scenario progress and completion evidence.
7. Link scenario completion to feedback and Error ID when defects are observed.

## Scenario Tracking Contract
Scenario status values:
- `pending`
- `in_progress`
- `completed`

Recommended minimum completion per tester for rollout acceptance:
- at least one completed baseline scenario with notes
- at least one feedback submission containing a related Error ID when issue reproduction occurs

## Tester Access Controls
- Deactivated testers must be blocked from sandbox access checks.
- Paused testers must be blocked from active participation until reactivated.
- Platform scope and permission checks remain mandatory for tester lifecycle operations.

## Request Intake
Platform admins can record:
- sandbox reset requests by tester
- tenant export requests by tester

Request records are tenant-scoped, auditable, and intended for controlled operational handling.

## Operational Reporting
Use Platform Management > Operations Dashboard to review:
- active tester totals
- per-tenant scenario completion counts
- open defect and unresolved error posture
- expiring sandbox attention signal
- reset and export request counts

## Evidence
Primary regression evidence:
- `tests/test_tenant_manager_service.py`
- `tests/test_phase2_settings_navigation.py`

Focus scenarios include:
- assignment and acknowledgement transitions
- scenario completion and linkage metadata
- tester deactivation and access denial
- dashboard permission enforcement
- cross-tenant and non-platform scope rejection

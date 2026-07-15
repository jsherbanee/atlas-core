# Alpha Release Process (A-04)

## Purpose
Define the repeatable controlled-alpha release, feedback triage, and stabilization operating loop.

## Scope
This process governs:
- alpha release record creation and lifecycle tracking
- tester cohort assignment to releases
- feedback triage queue operations
- conversion of confirmed feedback into tracked defects
- retest and verification workflow with regression evidence
- stabilization release history and release-note linkage

This process does not introduce product features.

## Release Record Contract
Each release record includes:
- version identifier
- release date
- commit hash
- included fixes
- known limitations
- supported test scenarios
- assigned tester cohorts
- rollback reference
- release status

Supported release states:
- Draft
- Approved
- Deployed to Sandbox
- Under Test
- Accepted
- Superseded
- Withdrawn

## Defect Model
Supported severities:
- Critical
- High
- Medium
- Low
- Enhancement

Supported defect statuses:
- New
- Needs Reproduction
- Confirmed
- In Progress
- Ready for Retest
- Verified
- Deferred
- Closed

Each confirmed defect must capture:
- tenant
- tester
- application version
- workspace
- related object
- related Error ID when available
- reproduction steps
- expected result
- actual result
- severity
- alpha-blocking status
- assigned sprint or release
- regression-test requirement
- resolution notes
- verification evidence

## Triage Rules
- Critical security, tenant-isolation, data-loss, and broken-core-workflow defects are alpha blocking by default.
- Every corrected confirmed defect must include regression-test reference where practical.
- Enhancements are backlog candidates and must not automatically enter stabilization.
- Tester requests must not be directly promoted to active sprint scope without governance review.
- Breadth-before-depth governance remains in force.

## Security Rules
- Platform scope (`local` / `atlas`) is required for cross-tenant triage and release operations.
- Tenant users may only view feedback/defect status linked to their own submissions.
- Sensitive diagnostics remain redacted.
- Cross-tenant content must not be exposed in tenant-scoped views or exports.
- Severity, status, assignment, release, and closure changes require audit events.

## Stabilization Loop
1. Create or update release record.
2. Assign tester cohorts and sandbox tenants.
3. Collect feedback and queue triage items.
4. Convert confirmed issues to defects.
5. Classify severity and alpha-blocking posture.
6. Assign release/sprint target and regression requirement.
7. Move defect to Ready for Retest after correction.
8. Verify with evidence and mark Verified.
9. Update release-note linkage and stabilization history.
10. Re-run quality gates and document outcomes.

## Reporting
Platform Management dashboard should summarize:
- current alpha version and release status
- active tester cohorts
- scenario completion
- new feedback
- confirmed defects
- alpha blockers
- ready-for-retest defects
- unresolved errors
- sandbox health

## Evidence
Primary validation coverage:
- `tests/test_tenant_manager_service.py`
- `tests/test_phase2_settings_navigation.py`

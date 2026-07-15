# Alpha Test Plan (A-04)

## Purpose
Define the controlled alpha launch, triage, and stabilization validation plan and record evidence for Sprint A-04.

## Scope Boundaries
In scope:
- tenant isolation and sandbox lifecycle controls
- alpha environment labeling and version identity
- authorization boundaries
- immutable audit behavior
- attachment security constraints
- background job reliability and idempotency behavior
- commercial transactions and document generation stability
- alpha health-check and diagnostics redaction behavior
- tenant-scoped feedback and defect workflow operations
- centralized application error logging capture, grouping, and status workflow
- user-safe Error ID behavior and diagnostics export controls
- navigation/state regression coverage for validated alpha surfaces
- alpha tester assignment, acknowledgement, and lifecycle transitions
- deterministic scenario assignment, progression, and completion tracking
- tester deactivation access denial and platform-admin-only dashboard enforcement
- alpha release records, cohort assignment, and stabilization history ordering
- feedback triage queue and feedback-to-defect conversion workflow
- defect lifecycle progression (confirmed -> ready for retest -> verified)
- tenant-user feedback/defect visibility constraints and cross-tenant denial

Out of scope:
- AWS infrastructure provisioning
- SSO/Cognito or invitation lifecycle
- billing/subscription provisioning
- inventory/procurement activation
- live QuickBooks transport execution

## Validation Matrix
| Domain | Objective | Evidence | Result |
|---|---|---|---|
| Tenant isolation | No cross-tenant leakage in create/read/reset/export flows | `tests/test_tenant_manager_service.py` | passing |
| Alpha environment labeling | Controlled-alpha marker and production designation guard | `tests/test_phase2_settings_navigation.py` | passing |
| Authorization boundaries | Deny-by-default, explicit platform-admin controls | `tests/test_permissions_service.py`, `tests/test_tenant_manager_service.py` | passing |
| Alpha health check | Administrator-only health surface and redacted diagnostics output | `tests/test_tenant_manager_service.py` | passing |
| Feedback and defect workflow | Structured tenant-scoped feedback lifecycle with status updates | `tests/test_tenant_manager_service.py` | passing |
| Application error logging | Fingerprint grouping, redaction, occurrence history, and user-facing IDs | `tests/test_tenant_manager_service.py` | passing |
| Error log access control | Tenant isolation, suspended-tenant rejection, and platform cross-tenant scope | `tests/test_tenant_manager_service.py` | passing |
| Error status workflow | Acknowledged/investigating/resolved/reopened transitions with audit coverage | `tests/test_tenant_manager_service.py` | passing |
| Alpha tester onboarding | Tester assignment, onboarding acknowledgement, scenario completion, and access checks | `tests/test_tenant_manager_service.py` | passing |
| Alpha operations dashboard | Platform-admin-only rollout summary and request counters | `tests/test_tenant_manager_service.py` | passing |
| Alpha release management | Release records, cohort assignment, deterministic ordering, and status history | `tests/test_tenant_manager_service.py` | passing |
| Defect triage lifecycle | Feedback conversion, severity/blocker rules, retest and verification evidence | `tests/test_tenant_manager_service.py` | passing |
| Tenant visibility constraints | Tenant user feedback/defect status restricted to own submissions | `tests/test_tenant_manager_service.py` | passing |
| Immutable audit | Append-only chain and deterministic filtering/export | `tests/test_immutable_audit_service.py` | passing |
| Attachment security | Tenant-scoped access and extension-policy enforcement | `tests/test_attachment_service.py` | passing |
| Job reliability | Deterministic lifecycle and idempotent retry/cancel semantics | `tests/test_project_workspace_service.py` | passing |
| Transactions safety | Scope enforcement and workflow regression stability | `tests/test_transactions_workspace_service.py` | passing |
| Document generation | Deterministic export/template behaviors | `tests/test_document_generation_service.py` | passing |
| Navigation/state stability | Settings/Transactions and search-working-set regression contracts | `tests/test_phase2_settings_navigation.py`, `tests/test_phase2_transactions_navigation.py`, `tests/test_phase2_global_search_working_set.py` | passing |
| Commercial seed workflow | Deterministic seed load/reset and transaction-chain validation | `tests/test_commercial_catalog_seed_service.py` | passing |
| Universal object tenant safety | Relationship/activity tenant-boundary enforcement | `tests/test_universal_object_contract.py` | passing |

## Executed Commands
Focused A-04 suites:
- `.venv/bin/pytest -q tests/test_tenant_manager_service.py tests/test_phase2_settings_navigation.py`
- Result: `25 passed`

Current Sprint A-04 validation commands executed in-session:
- `black atlas_core/services/tenant_manager_service.py apps/phase2_review_app.py tests/test_tenant_manager_service.py tests/test_phase2_settings_navigation.py`
- `ruff check atlas_core/services/tenant_manager_service.py apps/phase2_review_app.py tests/test_tenant_manager_service.py tests/test_phase2_settings_navigation.py`
- `mypy atlas_core/services/tenant_manager_service.py apps/phase2_review_app.py`
- `pytest tests/test_tenant_manager_service.py tests/test_phase2_settings_navigation.py -q`
- Result: `25 passed`

## A-04 Operations Verification
- Controlled-alpha environment marker is visible in shell header/status and blocks accidental production designation.
- Platform Management now includes alpha health-check, tenant-scoped feedback/defect capture, known-limitations access, and operator checklist guidance.
- Seed loading, reset, and export remain available as explicit sandbox lifecycle operations.
- Tenant feedback and diagnostics remain tenant-scoped with cross-tenant rejection and sensitive-key/path redaction.
- Platform Management now includes tester-onboarding and operations-dashboard tertiary actions.
- Platform Management now includes release and stabilization controls for cohort assignment, triage queue, and defect lifecycle updates.
- Tester profiles can be assigned, acknowledged, and moved through deterministic lifecycle states.
- Scenario assignments can be completed and linked to related feedback/Error IDs.
- Deactivated testers are blocked by access assertions.
- Release records support controlled status progression and deterministic release history ordering.
- Confirmed defects can move to Ready for Retest and Verified with regression/verification evidence.

## Validation Outcome
- Alpha blocker findings identified in A-02: 0
- Remaining confirmed alpha blockers: 0
- Recommendation: controlled alpha launch and stabilization loop operations are ready for sandbox-based external alpha execution under local deterministic constraints.

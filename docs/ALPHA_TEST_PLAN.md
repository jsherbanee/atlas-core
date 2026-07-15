# Alpha Test Plan (A-02)

## Purpose
Define the controlled alpha deployment and test-operations validation plan and record evidence for Sprint A-02.

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
- navigation/state regression coverage for validated alpha surfaces

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
| Immutable audit | Append-only chain and deterministic filtering/export | `tests/test_immutable_audit_service.py` | passing |
| Attachment security | Tenant-scoped access and extension-policy enforcement | `tests/test_attachment_service.py` | passing |
| Job reliability | Deterministic lifecycle and idempotent retry/cancel semantics | `tests/test_project_workspace_service.py` | passing |
| Transactions safety | Scope enforcement and workflow regression stability | `tests/test_transactions_workspace_service.py` | passing |
| Document generation | Deterministic export/template behaviors | `tests/test_document_generation_service.py` | passing |
| Navigation/state stability | Settings/Transactions and search-working-set regression contracts | `tests/test_phase2_settings_navigation.py`, `tests/test_phase2_transactions_navigation.py`, `tests/test_phase2_global_search_working_set.py` | passing |
| Commercial seed workflow | Deterministic seed load/reset and transaction-chain validation | `tests/test_commercial_catalog_seed_service.py` | passing |
| Universal object tenant safety | Relationship/activity tenant-boundary enforcement | `tests/test_universal_object_contract.py` | passing |

## Executed Commands
Focused A-02 suites:
- `.venv/bin/pytest -q tests/test_tenant_manager_service.py tests/test_phase2_settings_navigation.py`
- Result: `16 passed`

Explicit A-02 operational validation:
- `.venv/bin/pytest -q tests/test_tenant_manager_service.py -k "two_sandbox_alpha_operations_are_isolated or alpha_feedback_is_tenant_scoped_and_structured or alpha_health_check_requires_platform_admin_and_redacts"`
- Result: `3 passed`

Full quality gates:
- `.venv/bin/black --check .`
- `.venv/bin/ruff check .`
- `.venv/bin/mypy .`
- `.venv/bin/pytest -q`
- Result: `1412 passed`

## A-02 Operations Verification
- Controlled-alpha environment marker is visible in shell header/status and blocks accidental production designation.
- Platform Management now includes alpha health-check, tenant-scoped feedback/defect capture, known-limitations access, and operator checklist guidance.
- Seed loading, reset, and export remain available as explicit sandbox lifecycle operations.
- Tenant feedback and diagnostics remain tenant-scoped with cross-tenant rejection and sensitive-key/path redaction.

## Validation Outcome
- Alpha blocker findings identified in A-02: 0
- Remaining confirmed alpha blockers: 0
- Recommendation: controlled alpha deployment operations are ready for repeatable sandbox-based testing under local deterministic constraints.

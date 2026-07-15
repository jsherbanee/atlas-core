# Alpha Test Plan (A-01)

## Purpose
Define the final alpha release-candidate validation plan and record the evidence run in Sprint A-01.

## Scope Boundaries
In scope:
- tenant isolation and sandbox lifecycle controls
- authorization boundaries
- immutable audit behavior
- attachment security constraints
- background job reliability and idempotency behavior
- commercial transactions and document generation stability
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
| Authorization boundaries | Deny-by-default, explicit platform-admin controls | `tests/test_permissions_service.py`, `tests/test_tenant_manager_service.py` | passing |
| Immutable audit | Append-only chain and deterministic filtering/export | `tests/test_immutable_audit_service.py` | passing |
| Attachment security | Tenant-scoped access and extension-policy enforcement | `tests/test_attachment_service.py` | passing |
| Job reliability | Deterministic lifecycle and idempotent retry/cancel semantics | `tests/test_project_workspace_service.py` | passing |
| Transactions safety | Scope enforcement and workflow regression stability | `tests/test_transactions_workspace_service.py` | passing |
| Document generation | Deterministic export/template behaviors | `tests/test_document_generation_service.py` | passing |
| Navigation/state stability | Settings/Transactions and search-working-set regression contracts | `tests/test_phase2_settings_navigation.py`, `tests/test_phase2_transactions_navigation.py`, `tests/test_phase2_global_search_working_set.py` | passing |
| Commercial seed workflow | Deterministic seed load/reset and transaction-chain validation | `tests/test_commercial_catalog_seed_service.py` | passing |
| Universal object tenant safety | Relationship/activity tenant-boundary enforcement | `tests/test_universal_object_contract.py` | passing |

## Executed Commands
Focused A-01 suites:
- `.venv/bin/pytest -q tests/test_tenant_manager_service.py tests/test_permissions_service.py tests/test_immutable_audit_service.py tests/test_attachment_service.py tests/test_project_workspace_service.py tests/test_transactions_workspace_service.py tests/test_commercial_catalog_seed_service.py tests/test_document_generation_service.py tests/test_universal_object_contract.py tests/test_phase2_global_search_working_set.py tests/test_phase2_settings_navigation.py tests/test_phase2_transactions_navigation.py`
- Result: `258 passed`

Full quality gates:
- `.venv/bin/black --check .`
- `.venv/bin/ruff check .`
- `.venv/bin/mypy .`
- `.venv/bin/pytest -q`
- Result: `1408 passed`

## Blocker Remediation Verified In A-01
- Platform tenant-management operations are now restricted to explicit platform scope (`tenant_id=local`, `organization_id=atlas`).
- Suspended tenants are blocked from operational helper access (search/jobs/preferences/working-set and active-context assertion).
- Added targeted regressions in `tests/test_tenant_manager_service.py`.

## Validation Outcome
- Alpha blocker findings identified in A-01: 2
- Alpha blocker findings resolved in A-01: 2
- Remaining confirmed alpha blockers: 0
- Recommendation: release candidate approved for controlled alpha use under local deterministic architecture constraints.

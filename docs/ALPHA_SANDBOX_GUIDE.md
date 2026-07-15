# Alpha Sandbox Guide

## Purpose
Operator runbook for provisioning and validating isolated tenant sandboxes in the alpha environment.

## Preconditions
- Platform administrator identity with `platform.tenants.manage` permission in platform scope (`tenant_id=local`, `organization_id=atlas`).
- Local runtime workspace available.
- Atlas app initialized with Tenant Manager support.

## Provisioning Steps
1. Open Settings -> Platform Management -> Tenant Manager.
2. Create sandbox A:
- Set tenant label and owner.
- Optionally enable seed data.
- Confirm create.
3. Create sandbox B with a distinct tenant ID/label.
4. Confirm both tenants are listed as active and each has isolated repository paths.

## Isolation Validation Steps
1. Open sandbox A and seed/load representative records.
2. Open sandbox B and seed/load representative records.
3. Validate search index separation:
- Records created in sandbox A are not returned in sandbox B.
4. Validate job list separation:
- Jobs queued in sandbox A are not visible in sandbox B.
5. Validate preference and working-set separation:
- User preference and working-set values remain tenant-local.
6. Validate reset isolation:
- Reset sandbox A and confirm sandbox B data remains unchanged.
7. Validate export scope:
- Export sandbox B and verify payload includes only sandbox B identifiers.
8. Validate guarded delete workflow:
- Attempt delete with incorrect confirmation phrase (expect failure).
- Export tenant and then delete with exact confirmation phrase.

## Lifecycle Guardrails
- Suspended sandboxes should not accept operational helper access until restored.
- Archived sandboxes remain non-operational and should require explicit lifecycle action before operational use.
- Platform tenant-management actions must be run from platform scope only.

## Evidence Mapping
Primary automated evidence for this runbook:
- `tests/test_tenant_manager_service.py`
- `tests/test_permissions_service.py`
- `tests/test_universal_object_contract.py`

## Troubleshooting
- PermissionError for tenant manager actions:
- Verify platform scope (`local`/`atlas`) and role assignment.
- Reset/delete rejected:
- Verify exact confirmation phrase format (`RESET <tenant_id>` / `DELETE <tenant_id>`).
- Missing tenant data container:
- Re-open sandbox to force deterministic container initialization.

## Operational Notes
- This guide is for controlled alpha operations only.
- Cloud-provisioning, SSO, and billing workflows are intentionally out of scope.

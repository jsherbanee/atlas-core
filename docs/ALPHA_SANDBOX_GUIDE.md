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
5. Confirm shell header shows `Controlled Alpha` environment label and alpha version identifier.

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
9. Submit one feedback record from sandbox A and one feedback record from sandbox B.
10. Validate feedback lists are tenant-scoped and do not show cross-tenant records.
11. Run alpha health check for each tenant and verify tenant-specific output.
12. Trigger one controlled test error in sandbox A and one in sandbox B.
13. Validate Error Log view shows tenant-scoped records with Error IDs and grouped occurrence counts.
14. Verify stack traces/messages are sanitized and no raw paths/secrets are exposed.
15. Link one feedback record to a valid Error ID and verify persistence.

## Lifecycle Guardrails
- Suspended sandboxes should not accept operational helper access until restored.
- Archived sandboxes remain non-operational and should require explicit lifecycle action before operational use.
- Platform tenant-management actions must be run from platform scope only.
- Alpha health checks must be administrator-only and should never expose internal paths or secret references.
- Error logs must be tenant-scoped for tenant admins and cross-tenant metadata must remain platform-admin-only.

## Evidence Mapping
Primary automated evidence for this runbook:
- `tests/test_tenant_manager_service.py`
- `tests/test_permissions_service.py`
- `tests/test_universal_object_contract.py`
- `tests/test_phase2_settings_navigation.py`

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
- External ticketing integrations are intentionally out of scope; use tenant-scoped alpha feedback records.

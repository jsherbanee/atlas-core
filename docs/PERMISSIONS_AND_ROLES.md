# Permissions and Roles

## Purpose

This document defines the P-01 roles and permissions foundation for Atlas.

The foundation is deterministic, tenant-scoped, deny-by-default, and backward-compatible with the current local single-user development baseline.

## Related Documents

- [SECURITY.md](SECURITY.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [OBJECT_WORKSPACE.md](OBJECT_WORKSPACE.md)
- [SETTINGS_ARCHITECTURE.md](SETTINGS_ARCHITECTURE.md)
- [TRUST_CHARTER.md](TRUST_CHARTER.md)

## Scope (P-01)

Implemented in P-01:

- deterministic permission catalog and system-role contracts
- tenant-scoped role assignments
- project-scoped allow or deny overrides
- explicit allow and explicit deny evaluation behavior
- deny-by-default fallback
- human-readable denial reasons and diagnostics
- permission change audit events
- Universal Object action gating integration using permission hooks
- minimal Settings UI for viewing roles, assignments, and effective access

Explicitly out of scope:

- authentication implementation
- invitations, account lifecycle, or production provisioning
- SSO or cloud identity provider integration
- billing-permission model
- QuickBooks permission sync
- policy editor UX for arbitrary custom-rule authoring

## System Roles

Stable system roles shipped in P-01:

- Tenant Administrator
- Executive
- Estimator
- Project Manager
- Engineering
- Purchasing
- Finance
- Field Operations
- Service
- Read Only

Role keys are stable and deterministic. Display names are user-facing.

## Permission Categories

P-01 includes permissions across these categories:

- Projects
- Knowledge
- Transactions
- Settings
- Reports
- Integrations
- Users and roles
- Commercial documents
- Lifecycle transitions
- Export
- Archive and restore

## Contracts

P-01 contract types:

- `Permission`
- `Role`
- `RoleAssignment`
- `AccessRequest`
- `AccessDecision`
- `AccessDiagnostic`
- `TenantPolicy`
- `ProjectAccessOverride`
- `PermissionChangeEvent`

Contract behavior requirements:

- strict tenant and organization scope identity
- deterministic serialization ordering
- explicit enum-based allow and deny effects
- audit-event shape for role and override mutations

## Evaluation Behavior

Evaluation rules are deterministic and ordered:

1. Resolve tenant policy by `tenant_id` and `organization_id`.
2. Resolve matching assignments for principal and optional project scope.
3. Apply deny-by-default if no matching assignment exists.
4. Merge role allows and denies.
5. Apply matching project overrides.
6. Enforce deny precedence over allow.
7. Return explicit `AccessDecision` with reason and diagnostics.

Additional behavior:

- cross-tenant assignments do not grant access
- unknown permissions are denied explicitly
- project-scoped assignments only apply to the matching project

## Backward-Compatible Local Behavior

To preserve current local development workflows, evaluation includes a compatibility rule:

- when tenant is `local`, organization is `atlas`, and principal is `local-user`, Atlas can evaluate access as tenant-administrator-capable if no explicit assignment is present

This is an evaluation fallback for local development continuity, not a production identity model.

## Universal Object Integration

Universal Object actions now carry `permission_hook` values.

The action layer resolves each action into one of three states:

- visible and enabled
- visible but disabled with denial reason
- hidden

Authorization is centralized in shared action evaluation and is not implemented as scattered page-specific checks.

## Settings Surface

P-01 adds a minimal Settings > Organization > Roles and Permissions surface for:

- viewing stable system roles
- viewing permissions by role
- assigning roles to member IDs (including placeholder membership identifiers while user administration is still evolving)
- configuring project-scoped overrides
- evaluating effective access for a selected member/context

The Settings audit surface now includes permission change events.

## Future Direction

P-01 intentionally leaves room for future custom-role workflows without introducing a full policy editor in this sprint.

Future hardening targets include:

- formal membership lifecycle integration
- richer policy diagnostics and explainability views
- delegated administration boundaries
- stronger tenant-admin workflows with invitation and identity controls

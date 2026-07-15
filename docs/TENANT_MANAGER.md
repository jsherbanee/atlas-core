# Tenant Manager

## Purpose
Define the alpha tenant sandbox administration foundation for Atlas.

Sprint M-01 introduces deterministic local tenant sandbox provisioning and isolation controls for platform administrators.

This is a platform-management surface, not a tenant settings workflow.

## Scope
Implemented in M-01:
- tenant sandbox contracts for tenant, environment, membership, status, configuration, provisioning request/result, data boundary, and tenant audit event
- deterministic local sandbox provisioning with stable tenant IDs and isolated repository paths
- platform-admin restricted Tenant Manager UI controls for sandbox browse/create/open/suspend/restore/reset/export/archive/delete
- explicit guarded destructive flows for reset and delete with confirmation phrases
- export-before-delete guard for tenant deletion
- tenant-scoped data containers for projects, knowledge, catalog, transactions, settings, templates, attachments, audit, jobs, search indexes, working set, and user preferences
- tenant audit events for create/open/seed/reset/suspend/restore/export/archive/delete actions

Out of scope:
- AWS infrastructure provisioning
- Cognito or SSO
- billing provider integration
- production self-service signup
- cross-tenant analytics

## Tenant States
- draft
- provisioning
- active
- suspended
- archived
- failed

## Isolation Guarantees
M-01 enforces:
- active tenant context requirements for tenant-manager operations
- rejection of cross-tenant object references
- rejection of cross-tenant attachment references
- isolated local filesystem paths per tenant sandbox environment
- tenant-scoped search/job/preference/working-set containers
- no fallback to another tenant's records in tenant-manager export and lookup paths

## Permission Model
Tenant Manager actions require:
- `platform.tenants.manage`

Normal tenant users without this permission cannot access Tenant Manager actions.

## Provisioning Model
Local deterministic provisioning uses:
- `.atlas_tenants/<tenant_id>/<organization_id>/...` repository directories
- adapter-ready path contracts for future hosted deployment evolution

Provisioned isolated paths include:
- projects
- knowledge
- catalog
- transactions
- settings
- templates
- attachments
- audit
- jobs
- search_indexes
- working_set
- user_preferences

## Seed, Reset, Export, and Delete
M-01 behavior:
- optional seed profile load during provisioning
- reset affects only selected tenant and requires `RESET <tenant_id>` confirmation
- export payload includes only selected tenant data and records export metadata
- guarded delete requires `DELETE <tenant_id>` confirmation and export-before-delete evidence

## Validation Coverage
M-01 regression coverage includes:
- tenant creation and stable IDs
- repository-path isolation
- cross-tenant reference rejection
- search/job/settings/preference/working-set isolation
- seed-load and reset isolation across two tenants
- export scope isolation
- suspend/restore/archive/delete workflows
- platform-admin permission enforcement
- tenant audit event generation
- backward-compatible local default tenant availability

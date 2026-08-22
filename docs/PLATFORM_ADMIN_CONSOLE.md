# Platform Admin Console Direction

## Boundary

The future Platform Admin Console is separate from the tenant-facing Atlas application. It will have its own authorization boundary, navigation, audit expectations, and deployment review. It must not appear as a primary navigation item in the tenant-facing app.

## Future Responsibilities

- Tenant creation and provisioning
- Tenant access and lifecycle controls
- User invitations and role assignment
- Plan and subscription state
- Support and administrative access controls
- Audit visibility for administrative actions

## Security Direction

Platform operations require explicit platform scope and platform permissions. Tenant roles must not gain cross-tenant access through tenant-facing Settings or persisted project context. Support access should be time-bounded, attributable, least-privilege, and auditable.

## Current Status

This note defines architecture direction only. UI-FIX-01 does not implement a console, add tenant-facing navigation, or introduce authentication, billing, subscription, tenant-administration, or support-access workflows.
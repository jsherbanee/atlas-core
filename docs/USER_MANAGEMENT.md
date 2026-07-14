# User Management

## Purpose
This document defines the future user and organization administration model for Atlas.

It covers account lifecycle, invitations, membership, roles, seats, permissions, and identity-provider integration in implementation-neutral terms.

## Related Documents
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [SECURITY.md](SECURITY.md)
- [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)

## Scope
This document defines the administration model only.

It does not specify a final authentication vendor, database schema, or UI implementation.

Amazon Cognito is the current AWS direction, but the administration model should remain provider-neutral.

## Principles
- Users belong to one or more organizations through membership.
- Organizations own their operational data and settings.
- Roles should control access and responsibility.
- Seats should represent licensed access entitlements.
- Invitations should be explicit, auditable, and expirable.
- Deactivation should revoke access without destroying retained records.
- Recovery flows should preserve security and auditability.
- Identity-provider details should remain implementation-neutral.

## Core Concepts

| Concept | Meaning |
| --- | --- |
| Account | The user-facing identity and login record. |
| Organization | The tenant-scoped business boundary. |
| Invitation | A time-bounded request to join an organization. |
| Membership | The link between a user and an organization. |
| Role | A permission bundle within an organization. |
| Administrator Role | A role with elevated organization-management privileges. |
| Team | A group used for operational assignment. |
| Seat | A licensed entitlement consumed by an active member. |
| Service Account | A non-human identity used for automation or integration. |
| API Credential | A secret or token used by a service or integration. |

## Administration Flows

### Account Creation
Account creation should establish an identity that can later join one or more organizations.

### Organization Creation
Organization creation should initialize the tenant boundary, default settings, and initial administrative access.

### Invitations
Invitations should:
- expire after a configurable period
- be revocable
- be auditable
- support re-invitation when appropriate

### Membership Acceptance
Membership acceptance should bind a user to the target organization and apply the intended role and seat state.

### Role Assignment
Role assignment should be organization-aware and should support future custom roles.

### Project Access
Project access should flow through membership, role, and explicit project-level authorization.

### Team Membership
Teams should support operational grouping, project assignment, and reporting.

### Seat Assignment
Seat assignment should reflect active licensed usage, not merely invitation state.

### Seat Limits
Seat limits should be enforced per organization subscription and should support enterprise overrides where appropriate.

### User Deactivation
Deactivation should:
- block active access
- preserve historical audit data
- preserve organization records where retention requires it

### Organization Suspension
Suspension should disable access and integration activity according to policy while preserving data for recovery and audit.

### Account Recovery
Recovery should respect identity-provider rules, MFA or other security controls, and audit requirements.

### Ownership Transfer
Ownership transfer should support change in administrative control without losing organizational history.

### Session Management
Session management should support secure sign-in, sign-out, and token expiration semantics.

### Identity-Provider Integration
The eventual identity layer should integrate with an external identity provider and support delegated authentication.

### Future SSO
Future SSO support should work across enterprise organizations without weakening tenant isolation.

### API Credentials
API credentials should be managed per organization, be revocable, and never be shared across tenants.

### Service Accounts
Service accounts should be tenant-scoped and should be distinguishable from human accounts in audit logs and permissions.

### Auditability
All significant administrative actions should be auditable, including invitation changes, membership changes, deactivation, ownership transfer, and deletion-related actions.

### User Deletion
User deletion should follow retention and legal policy. Where possible, retained project history should preserve the operational record without exposing unnecessary personal data.

### Organization Deletion
Organization deletion should be gated by export, retention, and contractual policy requirements.

### Data Export Before Deletion
The administration model should support export before deletion or closure where required by policy or law.

### Billing Administrator Responsibilities
Billing administrators should manage:
- seat counts
- subscription state
- organization billing contact details
- invoice coordination
- payment status review

## Current Status
User and organization administration are future platform capabilities and not the current implementation baseline.

Current repository and workspace behavior should be treated as development scaffolding, not as the final administration system.

T-04 implementation note:
- initial personal-preference support is available for landing workspace, density, table size, date format, timezone, and reduced-motion preferences
- personal preferences are user-scoped and do not override tenant-controlled numbering, security, billing, retention, or integration policy controls

## Future Direction
Atlas should eventually support enterprise-ready administration with invitations, memberships, teams, billing roles, and SSO.

Future administrative controls related to AI enablement, retention, and provider approval should align with [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

## Unresolved Decisions
- Final administrator role taxonomy remains to be defined.
- The exact seat assignment model may vary by organization.
- The final balance between user-level and organization-level administration screens remains open.
- Final identity-provider provider selection remains implementation-dependent.

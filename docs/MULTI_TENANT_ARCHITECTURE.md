# Multi-Tenant Architecture

## Purpose
This document defines the authoritative multi-tenant architecture for Atlas.

It establishes tenant isolation, organization-scoped data, role-aware access, and the boundaries required for future SaaS operation.

## Related Documents
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [AV_LIFECYCLE.md](AV_LIFECYCLE.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [SECURITY.md](SECURITY.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)

## Scope
Atlas should be designed as a multi-tenant SaaS platform, but this does not mean the full tenant administration platform is already implemented.

This document records durable architectural requirements and boundaries only.

## Principles
- Each customer organization is isolated from every other organization.
- Users belong to organizations.
- Projects, documents, settings, workflows, integrations, reporting, and AI context are tenant-scoped.
- Permissions are organization-aware and role-aware.
- Tenant boundaries must be preserved in storage, APIs, search, AI, and integrations.
- Organization-scoped data should never leak across tenants.
- Shared platform services may exist, but tenant data must remain partitioned.

## Core Concepts

| Concept | Meaning | Boundary |
| --- | --- | --- |
| Tenant / Organization | The isolated customer boundary for Atlas data and configuration. | Owns tenant-scoped records and settings. |
| User | A person or service actor that can access one or more organizations. | Access is mediated through membership and permissions. |
| Membership | The relationship between a user and an organization. | Carries status, role assignment, and seat allocation. |
| Role | A named bundle of permissions. | Must remain organization-aware and configurable over time. |
| Permission | A specific allowed action or access right. | Evaluated against tenant, role, resource, and context. |
| Team | A working group inside an organization. | Useful for project and operational grouping, not tenant isolation. |
| Project | The tenant-scoped operational record for a job or pursuit. | Never crosses organization boundaries. |
| Workspace | The user-facing operating surface inside Atlas. | Always renders within a tenant context. |
| Subscription | The commercial plan and entitlement relationship for an organization. | Drives seats, access, and billing state. |
| Seat | A licensed user entitlement inside a subscription. | Seat counts may limit membership activation. |
| Integration Credential | An authorized connection to an external system. | Must be stored and evaluated per tenant. |
| Audit Event | A record of a user, system, or AI action. | Must be tenant-scoped and reviewable. |
| Organization Settings | Tenant-level configuration and policy state. | Controls naming, permissions, integrations, and defaults. |

## Tenant Isolation
Tenant isolation must exist at the architectural level in:

- repository contracts
- storage partitioning
- authorization checks
- search and discovery
- integration credentials
- audit logs
- AI context selection
- reporting and exports

Atlas must not assume that one organization can see another organization's records.

## Organization-Scoped Records
Records that should be tenant-scoped include, at minimum:

- projects
- workspaces
- documents
- settings
- workflows
- teams
- memberships
- subscriptions
- integration credentials
- audit events
- AI prompts and responses
- report outputs

## Tenant-Aware Repository Contracts
Repository contracts should accept tenant context explicitly or derive it from a tenant-safe boundary object.

Future repository implementations should avoid raw cross-tenant path access and should support partitioning by organization identifier or equivalent tenant key.

## Permission Evaluation
Permission checks should consider:

- tenant membership
- role assignment
- resource ownership
- resource type
- operation type
- context-specific policy

Role-based access control should be the baseline, with the ability to extend into fine-grained permissions as the platform matures.

## Organization Lifecycle
A future organization lifecycle should support:

- organization creation
- invitation and membership acceptance
- seat assignment
- role assignment
- suspension
- ownership transfer
- deletion subject to retention rules

## Ownership Transfer
Ownership transfer should be possible without destroying organization history.

The architecture should preserve auditability, billing continuity, and record retention during transfer events.

## Invitation Flow
Invitation flows should support:

- invite by email or equivalent identity attribute
- membership acceptance
- invitation expiration
- re-invitation after expiration or revocation

## User Deactivation and Tenant Deletion
Deactivation should remove active access without deleting historical operational records.

Tenant deletion and retention must respect legal, contractual, and customer policy requirements.

The architecture should support export, retention, and controlled destruction rules, but the final policy remains configurable.

## Enterprise Organization Support
Enterprise organizations may require:

- multiple teams
- custom roles
- custom permission bundles
- broader seat counts
- admin delegation
- SSO or identity-provider integration
- integration-specific credentials and policy controls

## Shared Platform Services
Shared services may include:

- authentication provider integration
- billing provider integration
- document storage services
- notification services
- background jobs
- search infrastructure
- AI services

Shared services must still enforce tenant boundaries before reading or writing organizational data.

## Prohibited Cross-Tenant Access
Atlas must never:

- expose one organization's data to another organization
- use one tenant's credentials for another tenant
- allow cross-tenant AI context leakage
- merge tenant histories without explicit migration or ownership transfer logic
- treat shared platform metadata as tenant-owned data

## AI Tenant Boundaries
AI features must respect:

- tenant isolation
- membership and role permissions
- document permissions
- data retention settings
- source attribution requirements

The AI layer should never infer access to material that the current organization has not been authorized to use.

AI privacy handling should also follow [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md) and [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

## Future AWS Implications
The intended AWS direction should support tenant-aware implementation choices such as:

- tenant-partitioned object storage
- tenant-aware relational records
- tenant-specific encryption or key management where appropriate
- isolated integration credentials
- scoped logs and audit trails
- tenant-aware queue processing

This document does not prescribe a final AWS deployment shape.

## Current Status
The multi-tenant operating model is an architectural requirement and a future implementation direction.

Current repository and workspace behavior should be interpreted in the context of a local development baseline, not as proof of the final SaaS tenancy architecture.

## Future Direction
Atlas should eventually support organization lifecycle administration, enterprise access patterns, and tenant-safe shared services across the full lifecycle platform.

## Unresolved Decisions
- Final role taxonomy remains to be defined.
- Final permission granularity remains to be defined.
- The exact partitioning mechanism for future persistence layers remains open.
- The interaction between tenant deletion, audit retention, and legal export requirements remains policy-driven.
- The final AWS implementation mix remains flexible.

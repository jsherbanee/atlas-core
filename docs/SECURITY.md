# Security

## Related Documents
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- [TRUST_CHARTER.md](TRUST_CHARTER.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)

## Purpose
This document defines Atlas's baseline security posture and expected security boundaries.

Atlas is a multi-tenant SaaS platform, so security must assume organization-level isolation, role-aware access, tenant-scoped integrations, and controlled sharing of operational data.

## Core Principles
- Protect tenant isolation.
- Use least privilege.
- Keep secrets out of source control.
- Prefer deterministic, auditable behavior.
- Keep access decisions explicit and reviewable.
- Treat production data as confidential.

## Expected Security Areas
- authentication and authorization
- role-based access control
- organization-aware permissions
- secure secret storage
- encryption in transit and at rest
- audit logging
- session management
- secure file handling
- dependency and supply-chain hygiene
- retention and deletion controls

Security boundaries should align with [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md) and [USER_MANAGEMENT.md](USER_MANAGEMENT.md).

## AI-Related Security Constraints
- AI features must respect tenant and project permissions.
- AI context must be limited to authorized organizational data.
- AI responses should not silently perform privileged actions.
- Any future write-capable AI workflow requires explicit user review and approval.

AI privacy handling should align with [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md) and [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

The broader trust commitment is defined in [TRUST_CHARTER.md](TRUST_CHARTER.md).

## Reporting and Escalation
Security issues should be reported through the normal project governance process and handled with urgency proportional to impact.

## P-01 Roles and Permissions Foundation

Sprint P-01 introduces deterministic tenant-scoped authorization foundations:

- deny-by-default permission evaluation
- explicit allow and explicit deny decisions
- explicit deny precedence over allow
- tenant and organization scope validation for assignments and policy records
- project-scoped access overrides
- human-readable denial reasons and diagnostic metadata
- audit-ready permission change events

Universal Object actions now evaluate permission hooks centrally and resolve to:

- visible and enabled
- visible but disabled with reason
- hidden

P-01 does not implement authentication, invitations, SSO, or production identity-provider provisioning.

## P-03 Deterministic Background Job Security Notes

Sprint P-03 introduces tenant-scoped job orchestration with deterministic local execution.

Security boundary expectations:
- job read/run/retry/cancel actions must enforce tenant and organization scope checks
- cross-tenant or cross-organization job access must fail by design
- job lifecycle actions should emit immutable audit events with scoped targets
- diagnostic payloads should remain redaction-safe and avoid sensitive credential material

Current P-03 constraints preserve local deterministic execution only:
- no external queue infrastructure
- no external worker deployment

## P-04 Unified Attachment Security Notes

Sprint P-04 adds tenant-scoped attachment controls with deterministic local enforcement.

Security controls include:
- tenant and organization scope validation for all attachment operations
- prohibited credential-like filename pattern blocking
- unsafe path and traversal protections for attachment filenames and blob references
- allow-list MIME and extension validation
- explicit maximum attachment size enforcement and empty-payload rejection

Current P-04 constraints:
- local deterministic persistence only
- no external malware scanner integration in this sprint
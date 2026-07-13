# Privacy and Data Ownership

## Related Documents
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [SECURITY.md](SECURITY.md)
- [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [TRUST_CHARTER.md](TRUST_CHARTER.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)

## Purpose
Atlas exists to help organizations leverage their own operational knowledge.

Atlas does not own customer knowledge.

Atlas helps organizations organize, retrieve, analyze, and preserve that knowledge.

## Customer Ownership
Customers retain ownership of their operational information, including:

- drawings
- specifications
- BIM exports
- CAD exports
- estimates
- pricing
- vendor relationships
- labor rates
- RFIs
- engineering notes
- reports
- project correspondence
- uploaded standards
- uploaded manufacturer documentation
- AI conversations
- organization knowledge
- workflow configuration
- project history
- operational records

Atlas stores this information solely to provide Atlas functionality.

Atlas should not imply transfer of ownership, title, or control over customer data.

## Data Portability
Organizations should not become locked into Atlas.

Future platform capabilities should support customer-controlled export of:

- project data
- documents
- reports
- AI conversations where retained
- operational history
- metadata
- audit history where applicable

Portability should preserve readability, provenance, and useful structure where practical.

## Data Retention
Future organization administrators may configure retention policies for tenant data and related records.

Examples include:

- project retention
- AI conversation retention
- deleted-object retention
- backup retention
- audit retention
- export availability

This document does not prescribe exact retention periods.

## Tenant Isolation
See [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md).

Atlas should treat tenant isolation as an architectural invariant across:

- tenant-aware repositories
- tenant-aware search
- tenant-aware object graphs
- tenant-aware AI retrieval
- tenant-aware caches
- tenant-aware indexes
- tenant-aware APIs
- tenant-aware integrations

No customer information should ever become visible outside the owning organization.

## Customer Privacy Commitment
Atlas exists to help organizations use their own knowledge, not to appropriate it.

Customer operational knowledge exists solely for the benefit of that organization.

Atlas should be designed so customers can trust that their project records, engineering knowledge, operational records, and confidential context remain theirs.

The system-level trust commitments that frame this document are defined in [TRUST_CHARTER.md](TRUST_CHARTER.md).

## Current Status
This is a governance document, not an implementation claim.

The platform should move toward these commitments as product and infrastructure capabilities mature.

## Unresolved Decisions
- exact retention defaults remain organization-configurable
- final export packaging and transport format remain open
- final deletion and legal-hold workflows remain policy-driven
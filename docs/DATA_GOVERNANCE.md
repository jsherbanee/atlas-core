# Data Governance

## Related Documents
- [AV_LIFECYCLE.md](AV_LIFECYCLE.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- [TRUST_CHARTER.md](TRUST_CHARTER.md)
- [SECURITY.md](SECURITY.md)

## Purpose
This document defines Atlas data ownership, stewardship, retention, and AI grounding expectations.

Atlas is an operational system of record. QuickBooks Online remains the financial system of record.

Data governance should respect tenant lifecycle, deletion, export, retention, and integration ownership policies documented in the related architecture and operations docs.

Customer ownership and AI privacy commitments are documented in [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md) and [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

The top-level trust charter that frames data governance is documented in [TRUST_CHARTER.md](TRUST_CHARTER.md).

## Data Ownership
- Organizations own their operational data.
- Projects and documents are tenant-scoped.
- Users act within organization permissions.
- Atlas should not imply ownership of imported customer content.

## Data Classification
Atlas data should be treated according to sensitivity and stewardship requirements, including:
- operational project records
- commercial records
- identity and access data
- documentation and evidence
- service and warranty history
- AI prompts, responses, and provenance metadata

## Retention and Auditability
- Retention policies should be configurable where practical.
- Important user actions should be auditable.
- Source attribution should be preserved when content is summarized or referenced.
- Historical records should remain reproducible where the domain requires it.

## AI Grounding
- AI features must use authorized organizational data only.
- AI outputs should distinguish sourced facts from inference.
- AI should expose source references when possible.
- AI should disclose uncertainty and source conflicts.

## External Integrations
Any integration that synchronizes data with external platforms should preserve ownership, tenant boundaries, and source-of-truth responsibilities.

Financial data synchronized from accounting systems must not be treated as authoritative operational data unless explicitly modeled that way.

## AI and Tenant Boundaries
AI grounding, response provenance, and source attribution should follow the rules in [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md) and [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md).

## P-04 Unified Attachment Governance Note

Sprint P-04 introduces a shared attachment framework with governance-aligned controls:
- tenant-scoped attachment ownership and linkage
- immutable version history for attachment revisions
- explicit provenance fields for source and source references
- activity and audit linkage for lifecycle events

Current implementation is deterministic local persistence and does not alter existing customer ownership boundaries.
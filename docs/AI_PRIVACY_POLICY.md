# AI Privacy Policy

## Related Documents
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [SECURITY.md](SECURITY.md)
- [TRUST_CHARTER.md](TRUST_CHARTER.md)
- [OBSERVABILITY.md](OBSERVABILITY.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)

## Purpose
This document defines how customer information is protected when AI is involved.

AI_ASSISTANT.md explains what the assistant does.
This document explains how customer information must be handled, protected, and isolated.

## AI Privacy Principles
Atlas AI must operate under the following principles:

- tenant isolation
- permission awareness
- least privilege
- customer ownership
- explicit consent
- transparency
- auditability

## AI Provider Requirements
Atlas should only integrate with providers that support enterprise privacy protections.

Preferred provider capabilities include:

- no customer-data training
- no model improvement using submitted customer data
- configurable zero-retention where available
- contractual enterprise privacy commitments
- encrypted transport
- enterprise authentication
- regional processing where applicable

Providers that cannot meet Atlas privacy expectations should not be eligible for production use.

This document intentionally does not name a specific vendor.

## AI Data Usage
Customer information is used only to answer questions on behalf of that customer.

Customer information must not become training data.

Customer information must not improve external models.

Customer information must never benefit another customer.

Future opt-in programs must require explicit organization-level consent.

Default behavior is opt-out.

## Conversation Isolation
Every AI interaction belongs to:

- one tenant
- one organization
- one user
- one conversation
- optionally one project
- one lifecycle stage

No conversation should ever become visible to another organization.

## AI Conversation Retention
Retention policies for AI conversations should be configurable.

Potential options include:

- retain everything
- retain prompts only
- retain responses only
- retain metadata only
- organization-defined retention
- automatic deletion
- immediate deletion after completion

This document does not prescribe defaults.

## AI Audit Trail
Future audit metadata may include:

- tenant ID
- organization ID
- user ID
- project ID
- workspace
- lifecycle stage
- model provider
- model version
- prompt template version
- retrieval sources
- knowledge libraries consulted
- timestamp
- token usage
- estimated cost
- approval events
- retention status

Storing complete prompts and responses should remain configurable.

Some organizations may prohibit long-term retention.

## AI Explainability
Future AI responses should support:

- citations
- source references
- retrieval transparency
- document references
- standards references
- manufacturer references
- confidence indicators
- provenance

## Customer Controls
Future administrative controls should support:

- AI enablement
- approved providers
- approved knowledge sources
- permitted standards libraries
- permitted manufacturer libraries
- AI retention
- conversation export
- conversation deletion
- prompt logging
- response logging
- regional restrictions

## AI Confidentiality Statement
Atlas AI works exclusively for your organization.

Your project data, engineering knowledge, operational records, pricing, and documents are never used to train foundation models or improve external AI systems without your organization's explicit consent.

The broader trust philosophy that frames this policy is documented in [TRUST_CHARTER.md](TRUST_CHARTER.md).

## Human Authority
AI recommendations never replace:

- licensed engineers
- certified designers
- certified installers
- project managers
- qualified technicians
- authorities having jurisdiction
- customer approvals

## Current Status
This is a policy document, not an implementation claim.

Atlas AI remains read-only by default, and no production AI workflow should imply broader access than the organization has authorized.

## Unresolved Decisions
- exact retention defaults remain policy-driven
- final provider approval workflow remains open
- final export and deletion handling remains configurable
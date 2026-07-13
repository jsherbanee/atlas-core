# AI Assistant

## Purpose
Atlas AI is a prominent future advisory capability embedded across the AV, lighting, and control system lifecycle.

It is intended to support users working in opportunity qualification, bid review, estimating, engineering, procurement preparation, project management, field installation, programming, commissioning, closeout, service, and asset lifecycle management.

This document defines future assistant behavior, context assembly, retrieval and grounding, permissions, user interaction boundaries, and audit expectations.

## Related Documents
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [STANDARDS_LIBRARY.md](STANDARDS_LIBRARY.md)
- [MANUFACTURER_KNOWLEDGE.md](MANUFACTURER_KNOWLEDGE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [SECURITY.md](SECURITY.md)
- [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- [TRUST_CHARTER.md](TRUST_CHARTER.md)
- [SEARCH_ARCHITECTURE.md](SEARCH_ARCHITECTURE.md)
- [OBJECT_GRAPH.md](OBJECT_GRAPH.md)
- [RULE_ENGINE.md](RULE_ENGINE.md)

## Assistant Role
Atlas AI may:

- answer questions using authorized Atlas data
- summarize project records
- compare documents and revisions
- identify missing information
- identify conflicting information
- explain deterministic findings
- explain standards-informed practices
- explain manufacturer requirements
- guide troubleshooting
- locate relevant records
- surface similar historical conditions
- recommend next actions
- draft proposed communications, RFIs, notes, reports, and operational actions for human review

Atlas AI must remain subordinate to human authority.

Customer ownership and AI privacy commitments are defined in [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md) and [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

The assistant must also operate within the trust commitments defined in [TRUST_CHARTER.md](TRUST_CHARTER.md).

## Read-Only Default
Atlas AI is read-only by default.

It may not autonomously:

- alter Atlas source code
- patch application code
- alter schemas
- change configuration
- deploy infrastructure
- change tenant settings
- modify authoritative project records
- issue purchase orders
- post financial transactions
- change billing
- write to QuickBooks
- write to Stripe
- send external communications
- bypass permissions
- approve regulated work

Any future write-capable workflow must require:

1. a clearly displayed proposed action
2. explicit user approval
3. permission validation
4. narrow action scope
5. audit recording
6. attribution to the approving user
7. confirmation of execution
8. reversal or correction support where practical

## Context Assembly Architecture
Future assistant requests should assemble context through a controlled pipeline that considers:

- tenant identity
- user identity
- role and permissions
- project access
- current workspace
- selected object
- active lifecycle stage
- relevant project records
- organization-maintained knowledge
- approved standards knowledge
- approved manufacturer knowledge
- deterministic findings and rule outputs
- source freshness
- source authority
- source version
- conversation context
- retrieval budget
- model context limits

Tenant and permission filtering must happen before content is submitted to any model.

## Retrieval and Grounding
Future AI retrieval should support:

- project-scoped retrieval
- object-aware retrieval
- metadata filtering
- full-text retrieval
- relationship-aware retrieval
- hybrid lexical and semantic retrieval
- authority-aware source ranking
- version-aware retrieval
- superseded-source handling
- citation generation
- page, section, record, and object references
- missing-source warnings
- source-conflict warnings
- response provenance

Deterministic application search remains separate from future semantic AI retrieval.

## Knowledge Hierarchy
Atlas AI should use the hierarchy documented in [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md).

Responses should generally distinguish among:

- law or code
- adopted standard
- manufacturer requirement
- project requirement
- organization policy
- certification-informed best practice
- historical project precedent
- assistant inference
- recommendation

## Deterministic Engine Relationship
Atlas AI may:

- explain deterministic rule outputs
- summarize findings
- group related findings
- identify supporting evidence
- help users interpret confidence and diagnostics
- recommend review actions

Atlas AI must not silently replace:

- deterministic rules
- cost-selection logic
- product-resolution logic
- estimate calculations
- immutable commercial history
- permissions
- validation gates
- lifecycle state transitions

## Conversation and Memory
Future assistant behavior should distinguish between:

- temporary conversation context
- saved conversation history
- user preferences
- organization-approved knowledge
- project records
- authoritative operational records

Conversation content must not silently become authoritative project truth.

Any future conversion of conversation content into an authoritative record must require a deliberate user-reviewed action.

## Provider Abstraction
Atlas should remain provider-neutral.

Future providers should be evaluated using:

- reasoning quality
- retrieval performance
- structured-output reliability
- tool-use reliability
- privacy
- enterprise data controls
- retention policy
- deployment geography
- context capacity
- latency
- availability
- cost
- model version stability

Do not select a permanent model provider in this sprint.

## Response Structure
Future responses should support visible classification where risk or authority matters.

Possible classifications:

- sourced fact
- code requirement
- standards requirement
- manufacturer requirement
- project requirement
- organization policy
- deterministic Atlas finding
- inference
- recommendation
- unresolved question

Responses should expose citations when possible.

## High-Risk Guidance
Atlas AI should require human verification messaging for guidance involving:

- electrical safety
- structural support
- seismic restraint
- overhead suspension
- rigging
- fall protection
- fire and life safety
- accessibility
- code compliance
- licensed engineering
- legal interpretation
- financial accounting
- regulated work
- authority-having-jurisdiction approval

## Assistant UX Direction
Future UI concepts may include:

- persistent assistant entry point
- project-aware conversation
- selected-object context
- source citation panel
- related-record navigation
- proposed-action preview
- clear separation between chat and authoritative records
- conversation history
- permission-aware availability
- tenant-level enable/disable controls
- project-level context controls
- visible AI status and limitations

The assistant should feel integrated into Atlas rather than added as an isolated chatbot.

## AI Administration
Potential future controls may include:

- organization-level enablement
- permitted providers
- permitted data classes
- approved knowledge sources
- retention policy
- prompt and response logging
- conversation export
- conversation deletion
- regional processing constraints
- standards editions
- preferred manufacturers
- restricted manufacturers
- confidence thresholds
- high-risk response policies
- future write-action permissions

## Audit and Provenance
Future audit metadata may include:

- tenant
- user
- project
- conversation
- model provider
- model version
- retrieval sources
- prompt template version
- response timestamp
- action proposal
- approval event
- execution result
- retention status

## Non-Goals
Atlas AI is not:

- a licensed engineer
- a code official
- an authority having jurisdiction
- a licensed electrician
- a licensed rigger
- an accountant
- an attorney
- an autonomous application developer
- an autonomous project manager
- a replacement for qualified human judgment

## Current Status
Atlas AI is conceptual and planned.

It is not implemented.

There is no production model connection.

There is no AI retrieval index.

There are no write-capable assistant workflows.

There is no assistant access to production tenant data.

The assistant remains read-only by default, and future AI privacy handling is governed by [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

## Open Decisions
Unresolved areas include:

- model providers
- retrieval infrastructure
- vector index technology
- conversation retention
- customer opt-in model
- regional data processing
- model evaluation framework
- cost controls
- response latency goals
- AI feature packaging and entitlements
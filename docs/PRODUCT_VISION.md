# Atlas Product Vision

## Product Position
Atlas is a commercial Software-as-a-Service platform for Audio Visual and Lighting Systems Integrators.

Atlas is an Intelligent Lifecycle Solutions Management Platform built for organizations that design, estimate, procure, deploy, commission, maintain, and service AV and lighting systems.

Atlas is vendor-neutral, company-agnostic, and multi-tenant.

Authoritative lifecycle, tenant, user-management, integration, and AI knowledge boundaries are documented in [AV_LIFECYCLE.md](AV_LIFECYCLE.md), [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md), [USER_MANAGEMENT.md](USER_MANAGEMENT.md), [INTEGRATIONS.md](INTEGRATIONS.md), and [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md).

The top-level trust philosophy is documented in [TRUST_CHARTER.md](TRUST_CHARTER.md).

Customer ownership and AI privacy commitments are documented in [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md) and [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

Assistant behavior is documented in [AI_ASSISTANT.md](AI_ASSISTANT.md).

AWS hosting direction is documented in [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md).

## Core Mission
Atlas exists to become the operational command center for an integration business.

Atlas manages operational truth.

Financial accounting systems manage financial truth.

Atlas should never attempt to replace accounting software.

Instead, Atlas is responsible for:
- project intelligence
- engineering
- estimating
- procurement
- project management
- field execution
- commissioning
- documentation
- service
- lifecycle management
- reporting
- operational analytics

## Financial System Philosophy
Atlas is the Operational System of Record.

QuickBooks Online is the Financial System of Record.

Atlas should synchronize data rather than duplicate accounting functionality.

Atlas should also originate and manage operational commercial documents before financial sync where configured.

Accounting functions that remain outside Atlas include:
- General Ledger
- Payroll
- Taxes
- Banking
- Financial reporting

Atlas will synchronize shared business entities where appropriate, including:
- customers
- vendors
- purchase orders
- invoices

Commercial-document operating boundary:
- Atlas should eventually own operational creation, review, approval, fulfillment, receiving, and pre-sync readiness for commercial documents such as estimates, proposals, sales orders, purchase orders, receiving records, vendor bills, and customer invoices.
- QuickBooks Online remains authoritative after sync for payable/receivable accounting, payment state, GL, taxes, banking, reconciliation, and statutory reporting.

## Product Scope
Phase 2 Bid Intelligence remains the current active development target.

Atlas's long-term lifecycle framework is defined in [AV_LIFECYCLE.md](AV_LIFECYCLE.md).

The business-facing capability horizon is defined in [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md).

The long-term roadmap expands Atlas from bid intelligence into a complete lifecycle platform spanning:
1. CRM / Opportunity Management
2. Bid Intelligence
3. Estimating
4. Commercial Transactions and Document Operations
5. Engineering
6. Procurement
7. Project Management
8. Field Installation
9. Commissioning
10. Service & Warranty
11. Asset Lifecycle Management
12. Executive Reporting & Business Intelligence

## Platform Philosophy
Atlas should feel like purpose-built software for professional systems integrators.

Target users include:
- Commercial AV Integrators
- Residential AV Integrators
- Lighting Integrators
- Design-Build Firms
- Integration Consultants
- Managed Service Providers

Atlas should remain configurable per organization and should not assume a specific company structure.

## Hosting Direction
Atlas's long-term hosting direction is AWS.

Target services may include:
- Amazon S3 for document storage
- CloudFront
- Amazon RDS or Aurora
- Amazon Cognito
- ECS/Fargate or Lambda where appropriate

The implementation mix remains flexible and should favor the best fit for a given capability.

## Subscription Platform
Stripe is the preferred subscription platform for future commercial operations.

Future capabilities may include:
- subscription management
- recurring billing
- organization licensing
- seat management
- plan upgrades
- payment history

## Commercial Model
The initial commercial strategy is:

Standard
- $99/month per user
- $999/year prepaid per user

Supported organization size:
- 1 to 9 users

Organizations with 10 to 49 users should contact Atlas for enterprise licensing and implementation discussions.

Free-trial strategy remains under evaluation.

## Atlas AI Assistant
Atlas will eventually include an embedded AI assistant as a strategic operational feature.

The assistant should act as a context-aware advisory layer for AV, lighting, and control systems integrators.

It should be knowledgeable in areas including:
- AV system design practices
- professional audio
- video distribution
- control systems
- lighting systems
- networked AV
- signal flow
- power and thermal considerations
- rack design
- cable infrastructure
- equipment compatibility
- commissioning practices
- service procedures
- procurement risk
- project documentation
- applicable codes, standards, and manufacturer guidance

The assistant should help users interpret and reason about information already available in their Atlas workspace.

Potential future capabilities include:
- answering questions about project documents
- identifying missing scope
- identifying potential compatibility issues
- explaining standards and best practices
- reviewing BOMs
- reviewing system topology
- identifying commissioning risks
- summarizing drawings, specifications, and correspondence
- locating relevant project records
- identifying contradictory project information
- guiding users through troubleshooting
- surfacing similar historical project conditions
- explaining the potential operational impact of project decisions
- drafting recommendations for human review

The assistant must remain advisory only.

It must not autonomously modify Atlas source code, application configuration, schemas, business logic, or deployment infrastructure.

It must not rewrite, patch, generate, or execute base application code from within the production user experience.

The assistant must not have authority to alter core Atlas behavior.

The knowledge-source policy for this assistant is defined in [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md).

## AI Data Boundary
The Atlas AI assistant should reason only from information the user or the user's organization is authorized to access.

Its accessible context may include:
- documents uploaded by the organization
- drawings
- specifications
- estimates
- BOMs
- project correspondence
- submittals
- RFIs
- field reports
- commissioning records
- service records
- organization-maintained knowledge
- approved standards libraries
- approved manufacturer documentation
- approved external reference sources

Tenant data must remain isolated.
One organization's data must never be exposed to another organization.

The assistant should respect:
- tenant boundaries
- project permissions
- user roles
- document permissions
- data retention policies
- source attribution
- audit requirements

Customer knowledge remains customer-owned, and AI use is governed by the privacy commitments in [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md) and [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

Customer sovereignty, transparency, and exit rights are defined in [TRUST_CHARTER.md](TRUST_CHARTER.md).

## AI Read-Only Principle
Atlas AI assistant behavior is read-only by default.

The assistant may analyze, summarize, compare, explain, and recommend.

It should not directly alter authoritative records unless a future workflow explicitly requires a user-reviewed and user-approved action.

Any future write-capable AI workflow must:
- be narrowly scoped
- require explicit user confirmation
- preserve a clear audit trail
- identify the user who approved the change
- show the proposed change before execution
- support reversal where practical
- respect organization permissions

## AI Source Grounding
The assistant should provide grounded answers wherever possible.

Future architecture should support:
- citations to source documents
- links to relevant project records
- page or section references
- confidence indicators
- clear separation between sourced facts and inferred recommendations
- disclosure when information is incomplete
- disclosure when sources conflict
- identification of outdated source material

Where standards, codes, or manufacturer requirements are involved, the assistant should identify the source and applicable edition or publication date where possible.

## AI Standards Knowledge
The assistant may eventually use curated knowledge sources covering relevant industry standards and guidance.

Potential areas include:
- AVIXA standards
- ANSI standards
- NFPA requirements
- NEC requirements
- UL requirements
- BICSI guidance
- SMPTE standards
- AES standards
- IEEE standards
- lighting control standards
- network standards
- accessibility requirements
- manufacturer technical documentation

Documentation must not claim that the assistant is a licensed engineer, code official, attorney, accountant, or authority having jurisdiction.

The assistant should advise users to verify high-risk or regulated decisions with the appropriate qualified professional.

## AI Governance and Safety
Future AI architecture should account for:
- role-based access control
- tenant isolation
- encryption
- data minimization
- audit logs
- model version tracking
- prompt and response logging policies
- configurable retention
- confidential data handling
- customer opt-in controls
- human review
- hallucination mitigation
- source validation
- restricted actions
- administrative controls

The assistant should never silently take action on behalf of a user.

The assistant should never be represented as infallible.

## AI Provider Flexibility
Document the AI layer in provider-neutral terms where possible.

Do not permanently couple the product architecture to a single model vendor.

The system should eventually support a replaceable or configurable model layer so Atlas can evaluate models based on:
- reasoning quality
- context capacity
- data privacy
- enterprise controls
- latency
- cost
- retrieval performance
- structured-output reliability
- tool-use reliability

Specific model providers may be evaluated later.

For the foundational knowledge policy behind the AI layer, see [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md).

## Why Atlas Exists
Integration teams often re-enter the same information across sales, bid, engineering, procurement, project execution, and service systems.

Atlas reduces that duplication by turning operational data into reusable, tenant-scoped lifecycle intelligence.

Atlas should be calm, professional, information-dense, responsive, deterministic, and low-friction. For the long-term visual and UX posture, see [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md).

## Current Scope
Atlas currently prioritizes deterministic bid-intelligence workflows and the supporting workspace hardening needed to keep that foundation reliable.

Current platform posture includes:
- drawing/spec/schedule intelligence
- scope reconciliation and risk surfacing
- deterministic product resolution between engineering scope and estimate readiness
- commercial knowledge foundation with immutable price-sheet version history
- engineering assumptions and RFI candidate generation
- estimator brief and final review outputs
- exportable data contracts (CSV, JSON, Markdown)

Product resolution posture:
- deterministic and explainable canonical product matching only
- no pricing logic
- no procurement logic
- no quote generation

Commercial knowledge posture:
- immutable commercial reference history for deterministic readiness
- every price-sheet import is permanent historical record
- no procurement execution
- no quote generation
- no purchase-order workflow

## Deferred Future Phases
The following lifecycle areas are in the long-term roadmap but are not current implementation priorities:
- CRM / Opportunity Management
- Procurement
- Project Management
- Field Installation
- Commissioning
- Service & Warranty
- Asset Lifecycle Management
- Executive Reporting & Business Intelligence
- AI-Assisted Operational Guidance

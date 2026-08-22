# Atlas Architecture

## Related Documents
- [README.md](README.md)
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [AV_LIFECYCLE.md](AV_LIFECYCLE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [MASTER_LIBRARY.md](MASTER_LIBRARY.md)
- [ROADMAP.md](ROADMAP.md)
- [TRUST_CHARTER.md](TRUST_CHARTER.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [SECURITY.md](SECURITY.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [BACKGROUND_JOBS.md](BACKGROUND_JOBS.md)
- [AUDIT_ENGINE.md](AUDIT_ENGINE.md)
- [ATTACHMENT_FRAMEWORK.md](ATTACHMENT_FRAMEWORK.md)

Future assistant behavior is documented in [AI_ASSISTANT.md](AI_ASSISTANT.md), and staged AWS hosting direction is documented in [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md).

## Source-of-Truth Hierarchy
Atlas documentation should be interpreted in this order when there is overlap:

1. [PRODUCT_VISION.md](PRODUCT_VISION.md) and [AV_LIFECYCLE.md](AV_LIFECYCLE.md) define what Atlas is and how the lifecycle should evolve.
2. [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md), [DOMAIN_MODEL.md](DOMAIN_MODEL.md), and this document define durable platform structure.
3. [USER_MANAGEMENT.md](USER_MANAGEMENT.md), [INTEGRATIONS.md](INTEGRATIONS.md), [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md), [SECURITY.md](SECURITY.md), and [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) define operational boundaries, access, storage, and integrations.
4. [ROADMAP.md](ROADMAP.md), [EPICS.md](EPICS.md), [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md), and [RELEASE_NOTES.md](RELEASE_NOTES.md) define sequencing and history.
5. [PRODUCT_GOVERNANCE.md](PRODUCT_GOVERNANCE.md) and [SCRUM_PROCESS.md](SCRUM_PROCESS.md) define work-selection discipline and Scrum execution rules.
6. [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md) and [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md) define the long-term experience and AI guidance posture.
7. [TRUST_CHARTER.md](TRUST_CHARTER.md) defines the permanent trust commitments that span all other documents.

## Platform Boundaries
Atlas is a multi-tenant SaaS platform for AV and lighting systems integrators.

Each customer organization is isolated.
Users belong to organizations.
Permissions are organization-aware.
Projects, documents, settings, workflows, and reporting are tenant-scoped.

Atlas manages operational truth.
QuickBooks Online remains the Financial System of Record.

Atlas must synchronize customers, vendors, purchase orders, and invoices where appropriate rather than duplicating accounting functionality.

Long-term hosting direction is AWS, with target services such as Amazon S3, CloudFront, Amazon RDS or Aurora, Amazon Cognito, and ECS/Fargate or Lambda where appropriate.

Repository composition is tenant-scoped even in local mode. Each tenant should be mapped to its own standalone repository root, with local development using a deterministic filesystem path such as `AtlasProjects/tenants/<tenant_id>/...`.

The current local repository composition root is the bridge between the platform data boundary and CM-01 commercial models. CM-01 introduces the lightweight commercial operating spine, while the repository boundary keeps per-tenant persistence isolated before deeper commercial persistence is added.

During migration, local and future AWS adapters must coexist behind the same composition boundary. The intended AWS mapping is tenant-partitioned object storage in S3, relational persistence in Postgres or Aurora, queueing through SQS, and worker execution through ECS/Fargate or Lambda.

Epic E work is not included in this slice.

Future subscription operations are expected to use Stripe for plan, seat, and billing management.

## AI Architecture Direction
Atlas will eventually include a read-only-by-default AI assistant as an advisory layer.

Assistant behavior, context architecture, response model, permissions, and user interaction boundaries are defined in [AI_ASSISTANT.md](AI_ASSISTANT.md).

This document retains only the high-level platform boundary: the assistant must remain tenant-aware, permission-aware, and grounded in authorized organizational context.

## Domain Alignment
Atlas lifecycle object definitions and cross-phase continuity rules are defined in [DOMAIN_MODEL.md](DOMAIN_MODEL.md).
Architecture and module design should align to that domain model so Phase 2 artifacts remain reusable in downstream phases.

Atlas's visual and UX philosophy is defined in [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md), which should be treated as a foundational architecture document alongside the domain model.

## Engine-First Architecture
Atlas is the deterministic engine layer for the platform.

Application surfaces, future API layers, and cloud adapters should call Atlas services and contracts rather than duplicating business logic in separate code paths.

Platform behavior should remain deterministic, tenant-scoped, and backward compatible.

Repository composition should treat tenant isolation as the first boundary, then compose local or future cloud adapters behind that boundary.

Governance note:
- architecture direction does not activate implementation work by itself
- major scope changes, persistence changes, tenancy changes, system-of-record changes, or security-boundary changes require explicit governance and ADR review before sprint execution

## Layers
- domain
  - Canonical dataclasses/enums and normalization rules.
- services
  - Orchestration and business workflows (review build, readiness, outputs).
- rules
  - Deterministic rule contracts, registries, and rule engine evaluation.
- registries
  - Reference datasets and lookup abstractions (manufacturer/vendor and similar).
- contracts
  - Stable payload/data shapes that downstream surfaces consume.
- exports
  - CSV/JSON/Markdown output adapters from engine outputs.
- CLI
  - Local execution entry point for running workflows against project inputs.

## Transactions Workspace Architecture Direction

Sprint A-07 defines Transactions as a future primary workspace and commercial-document architecture domain.

Architecture posture:
- Transactions is a workspace-level operational domain, not an accounting subsystem
- transaction objects are first-class Atlas objects with stable identity, relationships, approvals, activity, lifecycle, and sync metadata
- transaction families may link to Projects but do not require a Project to exist
- transaction workflows must remain tenant-scoped, auditable, and compatible with external financial-system synchronization

Boundary rules:
- Atlas owns operational document creation and workflow
- QuickBooks Online remains the Financial System of Record
- Atlas must not implement GL, tax, banking, reconciliation, or payment-processing behavior as part of Transactions architecture

## Commercial Document Framework Direction

Sprint A-08 defines one shared commercial-document architecture rather than separate document models for each transaction family.

Architecture posture:
- all commercial document families should inherit one common contract for identity, numbering, status, revision, approvals, lifecycle, activity, sync metadata, and external accounting references
- family-specific behavior should be additive, not a reason to break the shared contract
- issued revisions must be historically reproducible and immutable
- sync metadata must preserve operational ownership in Atlas while respecting QuickBooks financial ownership after sync

Sprint T-01 status:
- shared backend commercial-document domain/contracts/services are implemented in the engine layer for initial transaction families
- universal-object registry now includes commercial document adapter coverage for transaction-family object identities

T-01 boundary posture remains unchanged:
- no transactions UI implementation
- no QuickBooks API implementation
- no payment/ledger/accounting subsystem behavior

## Sprint P-04 Unified Attachment Framework

P-04 introduces a unified, tenant-scoped attachment architecture as an engine-first capability.

Architecture posture:
- one shared attachment contract set for metadata, versions, links, activity, and access decisions
- one shared attachment orchestration service reused by workspace and object surfaces
- repository abstraction with local deterministic adapter
- compatibility-safe bridging from legacy project document references into unified attachment links

Boundary notes:
- local deterministic persistence only in current implementation
- background hooks are emitted as callback payloads only
- no external worker, scanning engine, or cloud object store is introduced in this sprint

## Core Principle
Business logic should live once in the Atlas engine and be reused by all callers:
- CLI
- future API services
- future UI/web applications

## Sprint P-03 Deterministic Background Job Framework

P-03 introduces deterministic background-job orchestration as an engine-first capability, without introducing external queue infrastructure.

Architecture posture:
- storage-agnostic job contracts and repository boundaries
- local in-process deterministic executor for current runtime
- tenant-scoped lifecycle controls (submit/run/retry/cancel/list)
- immutable audit integration for lifecycle events

AV-00A extends this posture for project document intake:
- Streamlit upload callbacks perform only basic type/size validation, durable job creation, and rerun-safe feedback.
- Project document jobs are persisted before processing starts and are consumed by a local daemon worker that reads the same repository-backed queue.
- The local worker is intentionally replaceable by Celery, RQ, Dramatiq, or AWS queue/worker infrastructure because job state and inputs are not stored in Streamlit session state.
- Local development requires the Streamlit process to remain alive for the daemon worker to continue processing; queued jobs survive restart and resume when a worker is available.

Explicitly out of scope in P-03:
- AWS queue implementation
- external worker deployment
- cloud scheduler coupling

Representative workflow integration in current scope:
- document import
- export generation

## Rule Engine Direction
Atlas is moving to a registry-driven rule model where:
- Rule families register into a shared EngineeringRuleRegistry.
- EngineeringRuleEngine evaluates all relevant rules for a review context.
- Assumptions and related intelligence are deduplicated by stable IDs.
- New discipline coverage is added through modular rule files, not ad hoc service conditionals.

This keeps behavior deterministic, testable, and easy to extend as Phase 2 Bid Intelligence expands.

## Deterministic Estimating Foundation
Sprint 8 introduces deterministic estimating architecture as an engine-layer extension.

Design posture:
- Estimating remains object-driven and traceable to reviewed engineering entities.
- No hidden calculations and no black-box pricing.
- Unknown product resolution states do not receive deterministic pricing.
- Proposal/procurement/financial workflows remain out of scope.

## Sprint A-04 UX Consolidation Constraints

A-04 is a workstation UX consolidation sprint and preserves architecture boundaries:

- no new domain capabilities
- no D-03 scope/risk feature expansion
- no procurement/accounting/ERP or execution workflow introduction

Consolidation focus is UI composition consistency, deterministic recommendation presentation, and object-link continuity across existing pages.

## Sprint A-05 GUI Validation and Workflow Refinement Constraints (Closed)

A-05 is a product-refinement sprint and preserves architecture boundaries:

- no new engineering feature implementation
- no Epic E implementation start
- no Commercial Intelligence implementation
- no Sell Pricing or Proposal Generation implementation

A-05 focus is end-to-end workflow clarity, navigation continuity, table/form consistency, and low-risk UI helper refinements.

## Sprint X-01 Pilot Readiness Constraints (Closed)

X-01 continues product-hardening posture without adding architecture surface area:

- no new domain capability expansion
- no Epic E implementation start
- no Commercial Intelligence, Sell Pricing, or Proposal Generation implementation

X-01 focus is pilot-readiness validation, deterministic workflow clarity, and documentation/status synchronization.

## Sprint X-02 Project Creation and Bid Identity Refinement Constraints (Closed)

X-02 completed product-hardening without expanding architecture scope:

- no Epic E implementation start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation capability work

X-02 focus is project-identity clarity and deterministic project-creation behavior in existing architecture layers:

- repository-level deterministic Atlas Bid ID allocation and non-consuming preview contracts
- service-level metadata normalization for Atlas Bid ID, Client Project Number, and Internal Project Number
- UI discoverability consistency across create/open/list/search/settings flows

## Sprint X-03 Onboarding and Stakeholder Workflow Hardening Constraints (Active)

X-03 continues product-hardening without expanding architecture scope:

- no Epic E implementation start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation capability work

X-03 focus is deterministic refinement of existing create/open/settings/documents workflows:

- strict two-step create-then-upload onboarding flow
- pending-upload accumulation and explicit upload execution semantics
- shared organization directory plus project stakeholder relationship persistence
- legacy metadata compatibility behavior for older project records

## Sprint X-04 Home/Search Simplification Constraints (Closed)

X-04 continues product hardening without architecture expansion:

- Home is the only public landing-page term in Application Workspace.
- Mission Control remains an internal compatibility route key for existing navigation/state contracts.
- Header search submits on Enter, with deterministic grouped result presentation by object type.
- Home composition is reduced to primary actions plus prioritized Action Center and Recent Activity.

Explicitly out of scope:
- Epic E implementation start
- new domain services, persistence model expansion, or post-D capability work

## Sprint X-05 Navigation Consolidation Constraints (Closed)

X-05 continues product hardening without architecture expansion:

- no new domain capability
- no Epic E implementation start
- no Commercial Intelligence, Sell Pricing, or Proposal Generation implementation

X-05 focus is header-based navigation consolidation and terminology cleanup:

- move primary navigation into the header rather than a left-column rail
- expose Administration publicly as Settings from an upper-right hamburger menu
- replace Home Recent Activity with deterministic Recent Projects backed by existing workspace timestamps

## Sprint X-06 Responsive Shell Constraints (Closed)

X-06 continues product hardening without architecture expansion:

- no new domain capability
- no Epic E implementation start
- no Commercial Intelligence, Sell Pricing, or Proposal Generation implementation

X-06 focus is responsive shell simplification and width control:

- remove the public Home navigation button and keep Atlas as the only Home action
- simplify the global Search control to a label-free Search input
- expose Settings only through an icon-only hamburger dropdown trigger
- remove the History dropdown from the global header shell
- constrain the shell to a centered maximum width so the interface remains readable across common desktop and laptop sizes

This remains a UI-shell refinement only:

- internal Home and Mission Control routes remain compatible
- internal Administration routing remains intact
- project open/selection/search persistence remain unchanged

## Sprint X-07 Focused Search and Navigation Constraints (Closed)

## Sprint L-01 Lifecycle Engine Foundation

L-01 adds a deterministic lifecycle engine at the engine layer.

Architecture rules:
- lifecycle stage definitions, transition rules, readiness contracts, and lifecycle history logic live in the domain layer
- workspace services orchestrate persistence and compatibility projections but do not redefine lifecycle rules
- UI surfaces consume lifecycle-engine outputs and preserve legacy project status compatibility
- universal object projections expose lifecycle context through shared contracts rather than separate lifecycle-specific adapters

Persistence posture:
- `Project.status` remains compatibility status
- `metadata["lifecycle_stage"]` remains compatibility stage projection
- `metadata["lifecycle_plan"]` is the persisted engine snapshot
- `history/events.jsonl` carries explicit lifecycle transition events for repository-wide auditability

Explicit non-goals for L-01:
- no procurement, installation, commissioning, or service workflow modules
- no accounting or ERP lifecycle execution
- no replacement of authoritative project repository contracts

X-07 continues product hardening without architecture expansion:

- no new domain capability
- no Epic E implementation start
- no Commercial Intelligence, Sell Pricing, or Proposal Generation implementation

X-07 focus is focused search rendering and navigation polish:

- meaningful-query gating for focused search mode
- direct search-row open behavior
- shell behavior where focused search suppresses unrelated page content

## Sprint X-08 Visual System and Safe Search-Clear Constraints (Closed)

X-08 completed product hardening without architecture expansion:

- no new domain capability
- no Epic E implementation start
- no Commercial Intelligence, Sell Pricing, or Proposal Generation implementation

X-08 focus is visual-system consistency and Streamlit-safe search clear-state handling:

- global shell visual-system pass (#FAFAF9 background, #004225 primary accent, neutral surfaces)
- explicit separation of search widget-input state and submitted-query state
- generation-based safe widget-key reset for Clear Search and direct result-open flows


Implementation structure:
- domain: deterministic estimate entities and status enums
- services: deterministic estimate build, totals, dashboard, and confidence modeling
- UI shell: Estimate Workspace sections that surface deterministic model outputs

Extension boundaries are interface-only for future adapters:
- vendor/manufacturer/price/quote integrations
- labor rules and regional multipliers
- tax/currency
- proposal/RFQ generators

## Deterministic Product Resolution Engine
Sprint 9 adds a dedicated deterministic Product Resolution engine that sits between reviewed engineering objects and estimate preparation.

Design posture:
- No AI guessing; every match has explicit deterministic reason paths.
- Not pricing, not procurement, and not quote generation.
- Manual overrides are permitted only with reviewer/timestamp/reason audit fields while preserving original auto-match context.

Implementation structure:
- domain: product resolution models and override audit model
- services: deterministic candidate ranking and resolution assignment
- workspace shell: dedicated Product Resolution page with filters and manual override controls
- review/estimate integration: engineering summary metrics and estimate pricing gate enforcement

Source-of-truth references:
- [PRODUCT_RESOLUTION.md](PRODUCT_RESOLUTION.md)
- [MANUFACTURER_REGISTRY.md](MANUFACTURER_REGISTRY.md)

## Commercial Knowledge Foundation
Sprint 9 adds a commercial knowledge subsystem built around immutable price-sheet versioning.

Design posture:
- products do not own prices
- vendor offerings own commercial availability
- price records are immutable and tied to price-sheet versions
- every import creates a new permanent historical version
- commercial history supports deterministic readiness, not procurement execution

Implementation structure:
- domain: commercial object model (Vendor Offering, Price Sheet, Price Sheet Version, Price Record)
- service: immutable import, version comparison, change report generation, lifecycle/freshness metrics
- workspace shell: commercial health dashboard, import history page, and product-resolution commercial context panel

Source-of-truth references:
- [COMMERCIAL_KNOWLEDGE.md](COMMERCIAL_KNOWLEDGE.md)
- [PRICE_VERSIONING.md](PRICE_VERSIONING.md)

## D-01 Core Cost Selection Engine (Closed)
D-01 implementation is complete and validated.

In-scope architecture delivered:
- deterministic cost candidate construction over immutable commercial records
- deterministic selection API contracts and explainability outputs
- quantity normalization preview and confidence/provenance retrieval helpers
- BOM Review Cost Selection Inspector integration in existing workspace

## D-02 Estimate Engine and Cost Snapshot Architecture (Implemented)
D-02 implementation is complete.

Delivered architecture:
- estimate identity and revision history
- immutable cost snapshots built from D-01
- deterministic estimate totals and validation
- controlled refresh and replay workflows

Authoritative detail is maintained in [ESTIMATING.md](ESTIMATING.md), with D-01 dependencies in [COST_ENGINE.md](COST_ENGINE.md).

## D-03 Assemblies, Accessories, and Labor Rollups (Implemented)
D-03 implementation is complete and composes deterministic assembly expansion and labor rollups on top of D-02 revision ownership while preserving D-01 cost-selection authority.

Authoritative detail is maintained in [ASSEMBLIES_AND_LABOR.md](ASSEMBLIES_AND_LABOR.md).

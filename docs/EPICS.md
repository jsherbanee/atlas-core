# Atlas Epic Map

This document is the implementation planning source of truth for epics and sprint streams.

Use this file for planning and sprint decomposition.

Use [ROADMAP.md](ROADMAP.md) for executive milestone communication.

## Planning Rules

- Epics define durable product-domain work streams.
- Sprint items are tracked under epic IDs (for example, C-01, C-02).
- Keep this document implementation-oriented and current.
- Preserve architecture boundaries from [ARCHITECTURE.md](ARCHITECTURE.md) and [DOMAIN_MODEL.md](DOMAIN_MODEL.md).

Atlas's long-term product direction is a complete lifecycle platform for AV and lighting systems integrators. Current implementation remains centered on Phase 2 Bid Intelligence, with Epic E not started.

For executive milestone framing, see [ROADMAP.md](ROADMAP.md) and [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md).
For engineering sequencing and readiness gates, see [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md).

## Epic A: Core Platform

Status: Active

- A-01 Workspace Shell and Runtime Bootstrap
- A-02 Mission Control and Application Workspace
- A-03 Project Repository and Persistence Contracts
- A-04 Engineering Workstation UX Consolidation
- A-05 End-to-End GUI Validation and Workflow Refinement
- A-06 Quality Gates, CI, and Regression Baseline
- A-07 Transactions and Commercial Operations Architecture
- A-08 Commercial Document Framework
- T-01 Commercial Document Domain Foundation
- T-02 Transactions Workspace Foundation
- T-03 Estimate Transaction Integration
- T-04 Settings Foundation and Document Numbering Preferences
- T-05 Amendment Terms and Conditions Settings Integration
- T-05 Amendment Estimate and Sales Order Versioning, Duplication, and PDF Export
- T-06 Return Orders and Credit Memos
- T-07 Commercial Document Line Layout and Presentation
- P-01 Roles and Permissions Foundation
- P-02 Immutable Audit Foundation
- P-03 Deterministic Background Job Framework
- P-04 Unified Attachment Framework

### A-07 Scope

- define the Transactions workspace architecture before implementation
- define first-class commercial-document ownership and transaction-family boundaries
- define customer-side and vendor-side document flows
- define optional Project linkage and standalone transaction validity
- define future navigation model for Transactions as a primary workspace
- document Atlas versus QuickBooks ownership boundaries

Explicitly out of scope:
- transaction code
- QuickBooks integration implementation
- accounting ledger behavior
- payment processing
- procurement execution
- Epic E implementation

### A-08 Scope

- define one common framework for all commercial documents
- define shared contract fields, relationship rules, lifecycle model, revision philosophy, numbering philosophy, approval architecture, and sync metadata architecture
- keep Atlas as the operational owner and QuickBooks as the financial owner

Explicitly out of scope:
- production code
- QuickBooks implementation
- UI implementation
- Epic E implementation

### P-01 Scope

- implement deterministic tenant-scoped roles and permission contracts
- implement tenant-scoped role assignment and permission evaluation service behavior
- implement deny-by-default and explicit deny precedence behavior
- implement project-level allow and deny overrides
- integrate universal object action permission hooks into centralized action gating
- add minimal Settings surface for roles, assignments, and effective-access diagnostics

Explicitly out of scope:

- authentication and invitation implementation
- SSO or external identity-provider implementation
- billing-permission model
- QuickBooks integration scope expansion

### P-03 Scope

- implement deterministic background job contracts and orchestration service
- add repository contract and local adapter for job persistence
- integrate representative workflows (document import and export generation)
- provide permission-gated Processing surface for job visibility and control
- enforce tenant-scoped list/retry/cancel behavior

Explicitly out of scope:

- AWS queue implementation
- external worker deployment
- cloud scheduler orchestration

### P-04 Scope

- implement unified attachment contracts for metadata, versions, links, diagnostics, activity, and access decisions
- implement shared attachment orchestration service for upload/version/link/unlink/archive/restore/read behavior
- add tenant-scoped attachment repository contract and deterministic local adapter
- integrate Object Workspace Documents with permission-aware attachment actions
- add compatibility adapter that registers legacy project documents as unified attachments

Explicitly out of scope:

- cloud object-store adapters
- malware scanning engines
- external worker execution for attachment hooks

## Epic G: Product Governance And Delivery Discipline

Status: Implemented

- G-01 Product Governance and Progressive Refinement

### G-01 Scope

- define product-governance rules for work selection and refinement
- define Scrum process terminology, Definition of Ready, and Definition of Done
- clarify roadmap, status, and release-document responsibilities
- correct sprint-ID conflicts and paused-work visibility where needed

Explicitly out of scope:
- production feature implementation
- roadmap expansion beyond approved 1.0 areas
- activation of a new feature sprint

## Epic L: Lifecycle Engine

Status: Active

- L-01 AV Lifecycle Engine Foundation
- L-02 Lifecycle Dashboard

### L-01 Scope

- create deterministic lifecycle authority for project-stage sequencing
- define canonical lifecycle stages, stage-status model, transition contracts, readiness contracts, and lifecycle history model
- preserve backward compatibility with existing `ProjectStatus`, project serialization, repository manifests, search metadata, and settings flows
- expose lifecycle context through workspace services, project-facing UI, and project universal-object projections

Explicitly out of scope:
- procurement, installation, commissioning, training, warranty, service, and asset-lifecycle execution workflows
- accounting/ERP lifecycle workflows
- broad non-project object lifecycle migration

### L-02 Scope

- create the first reusable lifecycle dashboard for project records
- integrate lifecycle as a first-class tertiary Project Object Workspace view
- visualize lifecycle timeline, stage state, diagnostics, transitions, recent events, and responsible role using existing lifecycle-engine state

Explicitly out of scope:
- procurement, submittals, installation, service, or asset-management workflow implementation
- automatic advancement or workflow automation
- AI
- Epic E start

## Epic W: Workspace Intelligence

Status: Active (W-01, W-02, and W-03 completed; no active Epic W sprint)

- W-01 Context Persistence and Cross-Workspace Navigation
- W-02 Universal Object Contract
- W-03 Universal Object Workspace

### W-01 Scope

- preserve explicit working context across Projects, Knowledge, Search, and related object-detail views
- add deterministic return-context behavior and bounded navigation history using existing workspace persistence
- extend Working Set and breadcrumbs to behave coherently across project and application scopes

Explicitly out of scope:

- AI or semantic retrieval
- new business workflows or domain entities
- Epic E implementation start

### W-01 Closeout

- explicit context persistence shipped through existing workspace-state persistence
- return-context behavior is deterministic and one-click
- search handoff now carries return context and clearer scope labeling
- mixed project-object and Knowledge-entity Working Set continuity is supported

No Epic W sprint is currently active.

### W-02 Scope

- define one universal object contract as an adapter/interoperability layer, not a second source of truth
- cover identity, metadata, relationships, activity, actions, lifecycle, and presentation hints
- add registry-backed adapter lookup for representative project, knowledge, and engineering object families
- align search, Working Set, and W-01 context persistence with universal object identity where practical

Explicitly out of scope:

- Universal Object Workspace UI
- AI or semantic retrieval
- new business workflows or domain entities
- Epic E implementation start

### W-03 Scope

- implement reusable Universal Object Workspace UI inside existing shell
- migrate controlled object scope: Customer, Vendor, Manufacturer, Product, Service, Contact, Location, Project
- provide read-only shared-object-workspace support for Drawing, Specification, Equipment with direct open to authoritative engineering pages
- preserve existing create/edit/archive/import/export domain workflows and project-workspace behavior
- route supported search and Working Set opens through Universal Object Workspace while preserving continuity and backward compatibility
- render shared workspace ownership components: identity, context banner, action panels, bounded tertiary view controls, relationships, activity, and provenance
- keep object-level action availability registry-driven and compatibility-safe

Explicitly out of scope:

- migration of every object type
- new business workflows or domain entities
- AI or semantic retrieval
- Epic E implementation start

W-03 deferred migration note:
- broader lifecycle families (for example systems, rooms, risks, RFIs, and evidence) remain deferred and should migrate through the same shared object-workspace shell contract in future W-series planning

### A-04 Scope (Completed)

- standardize shared workspace section-header pattern
- normalize workstation terminology for core knowledge/commercial views
- deduplicate and prioritize recommendation tables in Mission Control flows
- keep object-centric linking continuity across estimate and review surfaces
- align filter and empty-state interaction patterns

Explicitly out of scope:

- D-03 implementation work
- new domain services or cross-system integrations

### A-05 Scope (Completed)

- validate complete user workflow from project intake through estimate lock and reporting
- refine navigation and recommendation affordances for existing deterministic workspaces
- improve table/form consistency and empty-state clarity across major pages
- apply low-risk helper-level UI organization improvements in `apps/phase2_review_app.py`

Explicitly out of scope:

- Epic E implementation
- Commercial Intelligence implementation
- Sell Pricing or separate customer-document generation implementation


## Epic B: Engineering Intelligence

Status: Active

- B-01 Drawing Intelligence
- B-02 Specification Intelligence
- B-03 Coordination Intelligence
- B-04 Engineering Resolver and Conflict Normalization
- B-05 Engineering Insights and Health Scoring
- B-06 Engineering Workbench and Investigation Flows
- B-07 Engineering Notebook and Decision Traceability

## Epic C: Commercial Knowledge

Status: Active

- C-01 Commercial Product Foundation
- C-02 Commercial Knowledge Completion
- C-03 Product Resolution

### C-01 Scope Boundaries

Implemented in C-01:
- Distinct manufacturer and vendor identities with deterministic duplicate checks.
- Canonical product identity by manufacturer plus normalized manufacturer part number.
- Vendor offerings separated from products, including purchasing channel classification.
- Price Sheet and Price Sheet Version split with immutable finalized versions.
- Price Records stored as immutable imported facts once finalized.
- Manual single-SKU workflow support without requiring full price-sheet import.
- Mission Control recommendations based on persisted commercial foundation conditions.

Business boundary rules:
- Manufacturer is the source producer identity.
- Vendor is the selling channel identity.
- Product is canonical and vendor-agnostic.
- Vendor Offering is vendor-specific commercial packaging for a canonical product.
- Price Sheet is a long-lived source container.
- Price Sheet Version is a point-in-time immutable import snapshot.

Normalization rules:
- Manufacturer and vendor duplicate checks use conservative normalized-name matching.
- Product uniqueness uses normalized manufacturer part number scoped by manufacturer.
- Vendor SKU matching uses normalized vendor SKU for search and reconciliation.

Compatibility and migration notes:
- C-01 extends existing commercial state structures without introducing a separate persistence subsystem.
- Existing deterministic pricing and cost services continue to consume commercial knowledge data through compatible state contracts.

Deferred to C-02 and later:
- Full commercial data completion and advanced reconciliation automation.
- Expanded resolution graph and confidence calibration for ambiguous vendor/manufacturer mappings.
- Additional procurement-domain and lifecycle extensions beyond C-01 foundation scope.

### C-02 Scope Boundaries

Implemented in C-02:
- Deterministic import lifecycle for tabular commercial sources: draft -> validated -> finalized.
- Deterministic PDF import inspection/extraction workflow with page-range, table-candidate, header-row, and mapping selection controls.
- Import diagnostics model with explicit severity handling (`error`, `warning`, `informational`).
- Deterministic mapping suggestions, worksheet/header-row selection support, and preview-record validation.
- Duplicate source hash detection against immutable finalized version history.
- Unresolved-record surfacing and completeness summary metrics for commercial health workflows.
- Manual draft/manual-record insertion support inside the same immutable finalization path.

Deferred beyond C-02:
- Product Resolution workflows (C-03).
- Deterministic Pricing/Costing workflow execution (D-series).
- Commercial Intelligence automation, procurement execution, accounting, and ERP integrations.

## Epic D: Deterministic Estimating

Status: Implemented and Closed for current roadmap baseline

- D-01 Core Cost Selection Engine (Closed)
- D-02 Estimate Engine and Cost Snapshot Architecture (Implemented)
- D-03 Assemblies, Accessories, and Labor Rollups (Implemented, Closed)
- D-03 Scope and Risk Diagnostics (Implemented through D-03 validation/readiness diagnostics)

## Epic T: Transactions Foundation

Status: Active

- T-01 Commercial Document Domain Foundation

### T-01 Scope

- implement shared backend domain/contracts/services for commercial documents
- support initial transaction families: Estimate, Sales Order, Purchase Order, RFQ, Vendor Quote, Receiving Record, Vendor Bill, Customer Invoice, Change Order
- implement stable document and line identity, optional project/project-code linkage, explicit lifecycle transitions, revision history, immutable issued revisions, decimal-safe totals, relationship traceability, and tenant/organization numbering preview/allocation behavior
- register commercial documents in the universal object registry and keep persistence compatibility through existing repository contracts

Explicitly out of scope:

- transactions UI
- QuickBooks API implementation
- payments, accounting ledger, or ERP behavior
- approval UI
- automatic document conversion
- D-04 Bid Completeness and Readiness Scoring
- D-05 Estimator Brief and Final Estimator Review
- D-06 Estimate Workflow Integration and Exports

## Epic X: Product Hardening

Status: Completed and Closed (X-01 through X-13 closed; no active Epic X sprint)

- X-01 Pilot Readiness and Application Walkthrough (Implemented, Closed)
- X-02 Project Creation and Bid Identity Refinement (Implemented, Closed)
- X-03 Onboarding and Stakeholder Workflow Hardening (Implemented, Closed)
- X-04 Home Page Simplification and Global Search Refinement (Implemented, Closed)
- X-05 Top-Header Navigation and Recent Projects (Implemented, Closed)
- X-06 Responsive Header and Navigation Simplification (Implemented, Closed)
- X-07 Fixed-Width Navigation and Focused Search Results (Implemented, Closed)
- X-08 Search Clear-State Runtime Fix and Visual-System Closeout (Implemented, Closed)
- X-09 Design System Foundation and Reusable UI Components (Implemented, Closed)
- X-10 Workspace Consistency and Information Density (Implemented, Closed)
- X-11 Typography System and Visual Polish (Implemented, Closed)
- X-12 Secondary and Tertiary Navigation Framework (Implemented, Closed)
- X-13 Navigation Clarity and UX Refinement (Implemented, Closed)

No Epic X sprint is currently active.

Epic X closeout notes:

- final validation pass completed across shell, navigation, search, responsive, and design-system migration surfaces
- Engineering Notebook discoverability is restored through existing guided workflow actions
- remaining UX debt is non-blocking and documented in status/release/design docs

Post-closeout planning note:

- Epic E remains Not Started and is the next candidate epic after architecture review and explicit sprint approval

### X-11 Scope (Completed)

- implement official typography families and centralized scale tokens in shared design-system authority
- centralize typography rhythm tokens (line heights and letter spacing) for deterministic hierarchy
- apply behavior-preserving visual polish to heading, table, badge, and control typography
- keep workflow logic, routing contracts, persistence, and domain behavior unchanged

Explicitly out of scope:

- Epic E implementation start
- new domain capability implementation

### X-12 Scope (Completed)

- introduce a reusable three-level navigation contract with explicit primary, secondary, and tertiary session state
- apply the framework to Knowledge first so search handoff can restore the correct workspace branch deterministically
- keep the implementation reusable for future workspace surfaces rather than hard-coding Knowledge-only behavior
- preserve existing Knowledge entity workflows and routing contracts

Explicitly out of scope:

- Epic E implementation start
- new domain capability implementation

### X-13 Scope (Completed)

- remove architecture-facing labels and duplicate navigation scaffolding from production UI surfaces
- keep primary navigation global while making secondary navigation contextual to application/project workspace state
- make tertiary navigation action-oriented rather than page-name repetition
- tighten page headers, Home information architecture, and Reports deliverable orientation without changing workflows

Explicitly out of scope:

- Epic E implementation start
- new domain capability implementation

### X-04 Scope (Completed)

- standardize public application landing terminology to Home
- retain Mission Control as internal compatibility route/state naming only
- simplify Home content to primary actions plus prioritized Action Center and Recent Activity
- streamline header search interaction to direct Enter submit with deterministic grouped results

Explicitly out of scope:

- Epic E implementation start
- new domain capability implementation

### X-05 Scope (Completed)

- move primary navigation into the top header
- expose Administration publicly as Settings via an upper-right hamburger menu
- replace Home Recent Activity with a deterministic Recent Projects list sourced from existing workspace timestamps

### X-06 Scope (Completed)

- remove the public Home navigation tab
- keep Atlas as the single Home action
- simplify the Search control and remove its visible label
- expose Settings only from an icon-only hamburger trigger
- remove the History dropdown from the global shell
- constrain the shell to a centered responsive width

### X-07 Scope (Completed)

- keep compact fixed-width top navigation readability under resize
- render focused search mode that suppresses unrelated page content while active
- preserve deterministic grouped search behavior with meaningful-query gating

### X-08 Scope (Completed)

- apply initial visual-system pass for shared shell/page consistency (#FAFAF9 background, #004225 primary accent)
- separate search widget-input and submitted-query state
- fix Clear Search runtime behavior through safe widget generation reset
- preserve route and project context when clearing or opening from focused search

Explicitly out of scope:

- Epic E implementation start
- new domain capability implementation

### X-09 Scope (Completed)

- establish a reusable design-system foundation for existing Streamlit shell surfaces
- centralize token authority and shared stylesheet output
- consolidate reusable page/UI primitives (section headings, notice panels, status badges, metric cards, table wrappers, responsive control groups)
- migrate representative pages (Home, Projects, Knowledge, Reports) without changing product behavior

Explicitly out of scope:

- Epic E implementation start
- new domain capability implementation

### X-10 Scope (Completed)

- complete shared-wrapper consistency migration across remaining primary project workspaces (Overview, Documents, BOM Review, Scope & Risk, Engineering Review, Estimate, Notebook)
- align section hierarchy, notice panels, table wrappers, and responsive control groups with X-09 design-system primitives
- preserve deterministic behavior, route flow, and project/workspace contracts

Explicitly out of scope:

- Epic E implementation start
- new domain capability implementation

## Epic E: Knowledge and Shared Objects

Status: Not Started

- E-01 Object-Centric Knowledge Graph and Relationships
- E-02 Cross-Project Shared Knowledge Reuse
- E-03 Global Search and Object Discovery
- E-04 Import History and Historical Reproducibility

## Epic F: Platform Hardening

Status: Active

## Epic K: Knowledge Entity Framework

Status: Active

- K-01 Knowledge Entity Framework
- K-02 Core Knowledge Entities and Operational Workflows

### K-01 Scope Boundaries

Implemented in K-01:
- Reusable knowledge-entity framework for `customer`, `vendor`, `manufacturer`, `product`, and `service` entities.
- Deterministic duplicate detection by entity type and normalized canonical name.
- Deterministic relationship model with stable relationship IDs derived from source, target, and relationship type.
- Import/export bundle foundation for entities, relationships, and audit records.
- Audit log foundation for entity upsert, activation changes, relationship upsert, and bundle import events.
- Backward-compatible synchronization from existing commercial foundation APIs (`create_manufacturer`, `create_vendor`, `create_product`).
- Global search integration for framework-managed customer/service entities.

Explicitly out of scope:
- Non-deterministic matching heuristics.
- Procurement execution, quote generation, and ERP/accounting workflows.

### K-02 Scope Boundaries

Implemented in K-02:
- Public operational workflows for framework entities (`create`, `update`, `archive`, `restore`) with deterministic behavior.
- Customer and service entity API surface expansion (`get`, `list`, `search`, `update`, activation controls).
- Framework-level summary metrics (entity counts, active/inactive split, relationship totals, per-type rollups).
- Product lifecycle synchronization into framework-backed product entities across update/discontinue/reactivate flows.
- Knowledge workspace controls for customer/service create/list/archive/restore operations.

Explicitly out of scope:
- Epic E implementation start.
- Procurement, purchase orders, service tickets, installed assets, sell pricing, and ERP workflows.
- Non-deterministic AI enrichment, cloud persistence, and authentication scope expansion.

- F-01 PDF Ingestion Robustness and Parsing Reliability
- F-02 Performance and Scalability for Large Project Sets
- F-03 Deterministic Regression Snapshot Expansion
- F-04 Documentation Consistency and Architecture Compliance

## Epic P: Procurement Domain Separation Readiness

Status: Deferred (Post-Phase 2)

- P-01 Procurement Workflow Boundaries (Non-ERP)
- P-02 Vendor Offering Lifecycle Extensions
- P-03 Receiving and Inventory Integration Hooks

Inventory note:
- P-03 remains visible but paused
- P-03 is not active work and must not be treated as an active sprint

## Epic H: Construction and Closeout Readiness

Status: Deferred (Post-Phase 2)

- H-01 Construction Execution Handoff Boundaries
- H-02 Closeout Data and Service History Handback
- H-03 Lifecycle Trace from Estimate to Completion

## Long-Term Platform Roadmap

The epic map is intentionally incremental. The broader Atlas platform should eventually span the full operational lifecycle:

- CRM / Opportunity Management
- Bid Intelligence
- Estimating
- Engineering
- Procurement
- Project Management
- Field Installation
- Commissioning
- Service & Warranty
- Asset Lifecycle Management
- Executive Reporting & Business Intelligence

The current plan keeps these domains separate until their boundaries are explicitly designed and validated.

## Usage in Codex Sessions

For implementation prompts:

1. Reference the relevant epic and sprint ID from this document.
2. Validate planned work against architecture docs before coding.
3. Keep implementation and docs synchronized in the same change.

For product-horizon prompts, use [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md).
For technical-execution prompts, use [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md).

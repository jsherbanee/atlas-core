# Atlas Epic Map

This document is the implementation planning source of truth for epics and sprint streams.

Use this file for planning and sprint decomposition.

Use [ROADMAP.md](ROADMAP.md) for executive milestone communication.

## Planning Rules

- Epics define durable product-domain work streams.
- Sprint items are tracked under epic IDs (for example, C-01, C-02).
- Keep this document implementation-oriented and current.
- Preserve architecture boundaries from [ARCHITECTURE.md](ARCHITECTURE.md) and [DOMAIN_MODEL.md](DOMAIN_MODEL.md).
- First-column secondary/tertiary navigation is an application-shell capability; sprint work must reuse the shared controlled accordion and must not introduce page-specific navigation expanders or independent open-state booleans.

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
- T-08 Customer Invoice Transactions
- P-01 Roles and Permissions Foundation
- P-02 Immutable Audit Foundation
- P-03 Deterministic Background Job Framework
- P-04 Unified Attachment Framework
- P-05 Document Generation and Template Engine
- P-06 Alpha Foundation Integrity Audit
- P-07 Alpha Blocker Remediation
- T-09 Change Order Tracking Convention
- S-01 Settings Workspace Completion
- U-01 Commercial Document Usability and Presentation Polish
- U-02 End-to-End Application UX and Workflow Polish
- M-01 Tenant Manager and Sandbox Provisioning
- A-01 Final Alpha Readiness Audit and Release Candidate
- A-02 Controlled Alpha Deployment and Test Operations
- A-03 Alpha Tester Onboarding and Controlled Rollout
- A-04 Alpha Launch, Feedback Triage, and Stabilization Loop
- K-04 Unified Organization Records and Entity Merge
- PX-01 Mission Control Tenant Operations Center
- PX-02 Project Operations Center
- PX-03 Commercial Transaction Workbench
- PX-04 Knowledge That Works
- PX-04A Interaction and Workflow Stabilization
- AV-00A Asynchronous Document Intake and Background Processing

### PX-01 Scope

- replace the prior Home composition with Mission Control as the application home
- present actionable tenant operations sections: My Work, Recent Activity,
  Business Risks, Continue Working, and Company Snapshot
- reuse existing workspace/project signals and services without adding business
  logic or new domain ownership
- preserve global search, Working Set, tenant isolation, permissions,
  navigation state, return context, and responsive shell behavior

Explicitly out of scope:
- decorative dashboard charts, gauges, and large metric tiles
- new workflow automation
- new commercial, procurement, accounting, or ERP behavior
- implementation-facing metadata on tenant surfaces

### PX-02 Scope

- transform active Project Overview into a Project Operations Center
- present operational project header, Project Health, Current Work, Project
  Timeline, Project Context, and Project Inspector
- organize active project navigation around work areas while preserving existing
  route targets and state compatibility
- reuse existing project review, document, timeline, lifecycle, and workspace
  services without adding business logic

Explicitly out of scope:
- new project business logic
- persistence redesign
- workflow redesign
- AI
- inventory
- procurement implementation
- accounting integration

### PX-03 Scope

- transform the selected-record Transactions experience into a Commercial
  Transaction Workbench for Estimates, Sales Orders, Return Orders, Invoices,
  and Credit Memos
- present document summary, commercial health, readiness checklist, decision
  panel, line item workspace, and relationship/lineage summary from existing
  commercial-document services
- preserve transaction family/action/document URL state for browser refresh,
  direct links, and workspace restoration
- keep deferred transaction families visible only as deferred scope

Explicitly out of scope:
- new commercial business logic
- persistence redesign
- accounting, payment, procurement, inventory, or QuickBooks transport behavior
- decorative dashboards, charts, gauges, and duplicate financial metrics

### PX-04 Scope

- transform Knowledge from record-directory pages into operational workbenches
  for Customers, Vendors, Manufacturers, Products, Services, Fees, and
  Assemblies
- present shared selected-record sections for Business Summary, Operational
  Health, Current Relationships, Recent Activity, Recommended Next Step, and
  Supporting Details
- derive deterministic findings and recommendations from existing Knowledge,
  catalog, offering, pricing, assembly, transaction, project, and activity data
- preserve Knowledge navigation, URL selection, Working Set, archive/restore,
  tenant isolation, permissions, and Universal Object compatibility
- provide a development/test-only representative Knowledge fixture invocation
  without automatic production seeding

Explicitly out of scope:
- new commercial rules
- new pricing calculations
- vendor-selection automation
- inventory, procurement, accounting, or QuickBooks transport behavior
- persistence redesign
- AI or predictive scoring
- production demo data

### PX-04A Scope

- stabilize visible primary actions so they complete, navigate, open a usable
  workflow, or show a clear disabled reason
- route Projects Create and Import actions to dedicated workflow surfaces
- preserve create/import feedback across Streamlit reruns and clean cancel
  returns
- prevent generic source-directory names from defaulting multiple project
  identity fields
- preserve PX-01 through PX-04 behavior without MAW parsing, new business
  logic, or persistence redesign

### AV-00A Scope

- persist and queue accepted project document uploads immediately
- create one durable processing job per accepted file
- move PDF inspection, OCR, extraction, classification, and evidence generation
  out of Streamlit upload callbacks
- consume persisted jobs through a local worker that is replaceable by a cloud
  queue/worker architecture
- expose durable Processing status, filters, retry, cancel, warnings, and
  failure diagnostics
- keep bid-package upload limits and supported file types governed by one
  shared policy: 200 MiB per file, 1 GiB per batch, 50 files per batch,
  PDF/DOC/DOCX/XLS/XLSX/CSV/image/TXT/RTF/ZIP formats, and no user-facing JSON
  intake
- open project workspaces through a lightweight bootstrap that avoids full
  document/review hydration, queued-job execution, and implicit manifest repair
  during navigation
- preserve existing drawing intelligence and OCR behavior without adding new
  extraction rules, AI, cloud infrastructure, procurement, or accounting scope

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

### T-09 Scope

- implement project-scoped change-order tracking over existing Sales Orders (additive) and Return Orders (deductive)
- enforce non-consuming preview and consuming `CO #n` allocation semantics with no duplicate reuse per project
- capture shared change-order metadata including owner change reference and internal notes
- provide project commercial summary rollups for base bid, additive/deductive totals, net/current contract values, and pending/approved/invoiced/outstanding change values

Explicitly out of scope:

- standalone Change Order document type workflow
- live QuickBooks synchronization transport
- inventory and procurement workflow activation

### S-01 Scope

- complete Settings alpha baseline across organization controls and personal-preference boundaries
- implement organization profile, tax/surcharge policy modeling and deterministic preview, and integration metadata hooks
- enforce secret-reference-only credential pointer storage for integration settings
- expand terms settings support to Return Order and Customer Invoice document families
- implement security policy metadata controls and broader settings UI contract coverage

Explicitly out of scope:

- live integration authentication/transport execution
- external tax engine integration
- identity lifecycle, SSO, and invitation workflows

### U-01 Scope

- standardize Transactions tertiary action contracts for commercial document families already in alpha scope
- remove dead or inconsistent export/action paths and align supported workflows to deterministic PDF/export controls
- improve line-presentation parity and usability for reorder/sort/group/comment/subtotal/visible-column controls
- strengthen commercial chain visibility through related-document/source-lineage presentation improvements
- add regression coverage for navigation/action parity and line-presentation sort parity

Explicitly out of scope:

- QuickBooks API transport execution
- payment processing
- inventory/procurement workflows
- new transaction families or roadmap expansion

### U-02 Scope

- perform a comprehensive usability and consistency pass across primary application workspaces (Home, Projects, Lifecycle-related project surfaces, Transactions, Knowledge, Reports, Settings)
- consolidate Knowledge around Customers, Vendors, Manufacturers, and Catalog while preserving existing entity, search, Universal Object, and commercial catalog authorities
- tighten secondary/tertiary navigation clarity and action-language consistency
- ensure pages expose clear purpose, clear primary actions, shared design-system framing, and guided empty-state behavior
- remove prototype/development-facing labels and redundant control language in user-facing UI
- validate responsive behavior and state stability under required viewport widths

Explicitly out of scope:

- new product feature development
- new transaction families or workflow-domain expansion
- QuickBooks transport execution, payment processing, inventory/procurement activation

### M-01 Scope

- implement tenant manager contracts and deterministic sandbox provisioning services
- enforce platform-admin-only sandbox lifecycle controls and audit coverage
- provision tenant-isolated local repository paths and per-tenant data containers
- validate reset/export/delete guardrails and cross-tenant rejection behavior with regression tests

Explicitly out of scope:

- AWS infrastructure provisioning
- SSO/Cognito identity lifecycle
- billing or self-service signup workflows

### A-01 Scope

- execute evidence-based alpha readiness audit and release-candidate classification across tenant isolation, authorization, auditability, attachment security, jobs, transactions, document generation, and workflow stability domains
- classify findings into ready, ready with known limitations, alpha blocker, or deferred-beyond-alpha categories with repository evidence
- remediate only confirmed alpha blocker defects in approved hardening categories without introducing new product capabilities
- produce alpha release-candidate package documentation (test plan, known limitations, release checklist, sandbox guide) and reconcile status/readiness/release records

Explicitly out of scope:

- new feature expansion beyond approved alpha scope
- AWS/SSO/billing/procurement/inventory/live QuickBooks transport activation
- roadmap expansion beyond approved Phase 2 and alpha hardening boundaries

### A-02 Scope

- implement controlled alpha environment labeling/version visibility and production-designation guard behavior
- operationalize sandbox test workflows for seed, reset, export, health checks, and tenant-scoped feedback capture
- provide administrator-only alpha health-check view with redacted diagnostics and tenant-boundary-safe summaries
- provide settings-accessible known-limitations and operator checklist guidance for repeatable alpha execution
- implement centralized tenant-scoped application error logging, deterministic fingerprint grouping, occurrence history, and user-safe Error ID responses
- provide authorized Error Log review workflows (filter/details/status transitions/resolution notes/export) with audit integration
- add regression coverage for environment labeling, health-check enforcement, diagnostics redaction, feedback scoping, and sandbox isolation operations

Explicitly out of scope:

- new commercial workflow capability expansion
- inventory/procurement activation
- live QuickBooks transport execution
- external ticketing integration
- hosted production deployment claims

### A-03 Scope

- implement controlled external tester onboarding for isolated sandbox tenants
- implement platform-admin tester profile assignment and lifecycle-state transitions
- implement onboarding acknowledgement capture for terms and known limitations
- implement deterministic scenario assignment and completion tracking per tester
- implement tester-linked sandbox reset/export request intake and operations dashboard summaries
- add regression coverage for tester onboarding, cross-tenant rejection, deactivation access denial, and dashboard permission enforcement

Explicitly out of scope:

- product feature expansion beyond approved alpha scope
- SSO, invitation automation, billing, or public signup flows
- live QuickBooks transport execution
- new commercial workflow-domain expansion

### A-04 Scope

- implement controlled alpha release records with lifecycle states and rollback references
- implement tester cohort assignment to alpha releases
- implement feedback triage queue and feedback-to-defect conversion workflow
- implement defect severity/status/reproduction/retest/resolution-priority tracking with release-note linkage
- implement platform-admin stabilization dashboard summaries and deterministic release history ordering
- add regression coverage for lifecycle transitions, blocker rules, release assignment, tenant isolation, and audit events

Explicitly out of scope:

- new product feature development
- inventory/procurement activation
- live integrations, billing, public signup, or AI feature scope
- enhancement-request auto-promotion into active sprint scope

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

### P-06 Scope

- perform repository-wide integrity audit for permissions, immutable audit, background jobs, attachments, document generation, settings, commercial documents, universal object framework, workspace continuity, lifecycle engine, tenant isolation, repository persistence, search/navigation, and documentation accuracy
- classify findings as implemented, partial, missing, blocking, and non-blocking with evidence
- apply only hardening-safe corrective fixes (security, tenant isolation, data integrity, compatibility, test correctness, documentation accuracy)
- publish Alpha readiness report with recommended sprint sequencing and evidence-backed readiness percentage

Explicitly out of scope:

- new product feature scope expansion
- Epic E implementation start
- cloud infrastructure expansion beyond current local deterministic adapters

### P-07 Scope

- remediate confirmed Alpha blocker-class findings from `ALPHA_READINESS.md`
- prioritize tenant isolation and authorization boundary hardening without introducing new feature scope
- require safe default scope behavior in transactions service boundaries and preserve deterministic compatibility behavior for explicit test-only opt-outs
- add regression coverage and documentation updates for all corrected blocker-class defects

Explicitly out of scope:

- new product capability expansion
- AI, procurement, receiving, or service workflow activation
- inventory reactivation

### P-05 Scope

- implement deterministic document-generation contracts and rendering orchestration
- implement template precedence resolution and fallback behavior
- implement revision-level template snapshot capture for immutable issued rendering
- implement settings-backed template version/default management and runtime export/replace sync
- integrate transactions export with generated artifact metadata and template provenance

Explicitly out of scope:

- cloud worker implementation changes
- external delivery transport execution
- e-signature workflow implementation

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
- C-03 Commercial Catalog Foundation
- C-04 Seed Catalog Import and Alpha Data Validation

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
- Product Resolution workflows (later C-series scope).
- Deterministic Pricing/Costing workflow execution (D-series).
- Commercial Intelligence automation, procurement execution, accounting, and ERP integrations.

### C-03 Scope Boundaries

Implemented in C-03:
- Unified commercial catalog item model with deterministic type support for `product`, `service`, `fee`, and `assembly` items.
- Catalog lifecycle controls for archive/restore without destructive mutation of historical references.
- Pricing policy foundation for MSRP, MAP, Cost+%, Margin%, Multiplier, and Manual semantics with explicit manual line override precedence.
- Nexus-based tax rule engine foundation with effective-date windows, deterministic priority ordering, compound-tax behavior, taxable item-type constraints, and exemption-flag filtering.
- Tenant-scoped organization commercial defaults for pricing policy, markup/margin, tax nexus, currency, and rounding policy.
- Deterministic PDF catalog price-list lifecycle with inspect/preview/finalize stages, diagnostics, explicit mapping controls, duplicate hash warning, immutable version snapshots, and partial-success rejection reporting.
- Catalog import workflows for manufacturers, vendors, products, services, fees, assemblies, and assembly components from CSV/XLSX sources.
- Assembly versioning with nested expansion, circular-reference rejection, deterministic component ordering, and rollup totals.
- Transaction integration for adding catalog-backed lines to Estimates, Sales Orders, Return Orders, Credit Memos, and Customer Invoices while preserving manual line behavior.

Deferred beyond C-03:
- Product Resolution workflows now move to later C-series scope.
- Procurement execution workflows, inventory activation, payment workflows, and external accounting transport.
- Commercial intelligence automation and ERP synchronization.

### C-04 Scope Boundaries

Implemented in C-04:
- Deterministic tenant-scoped seed package for commercial catalog alpha validation data.
- Representative seeded manufacturers, vendors, products, services, fees, assemblies, component maps, tax nexus rates, and price-sheet data.
- Repeatable seed load and duplicate suppression behavior.
- Seed-only reset preserving non-seed tenant records.
- Explicit seed provenance markers on seeded records.
- Representative import validation coverage for CSV/XLSX/PDF catalog sources.
- Scripted validation for Estimate -> Sales Order -> Customer Invoice and Return Order -> Credit Memo flows.

Deferred beyond C-04:
- Any production data ingestion workflows.
- Inventory, procurement execution, live tax-service integration, and QuickBooks transport execution.
- New commercial document family introduction.

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

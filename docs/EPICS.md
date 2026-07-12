# Atlas Epic Map

This document is the implementation planning source of truth for epics and sprint streams.

Use this file for planning and sprint decomposition.

Use [ROADMAP.md](ROADMAP.md) for executive milestone communication.

## Planning Rules

- Epics define durable product-domain work streams.
- Sprint items are tracked under epic IDs (for example, C-01, C-02).
- Keep this document implementation-oriented and current.
- Preserve architecture boundaries from [ARCHITECTURE.md](ARCHITECTURE.md) and [DOMAIN_MODEL.md](DOMAIN_MODEL.md).

## Epic A: Core Platform

Status: Active

- A-01 Workspace Shell and Runtime Bootstrap
- A-02 Mission Control and Application Workspace
- A-03 Project Repository and Persistence Contracts
- A-04 Engineering Workstation UX Consolidation
- A-05 End-to-End GUI Validation and Workflow Refinement
- A-06 Quality Gates, CI, and Regression Baseline

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
- Sell Pricing or Proposal Generation implementation


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
- D-04 Bid Completeness and Readiness Scoring
- D-05 Estimator Brief and Final Estimator Review
- D-06 Estimate Workflow Integration and Exports

## Epic X: Product Hardening

Status: Active (X-01 Closed, X-02 In Progress)

- X-01 Pilot Readiness and Application Walkthrough (Implemented, Closed)
- X-02 Project Creation and Bid Identity Refinement (In Progress)

## Epic E: Knowledge and Shared Objects

Status: Not Started

- E-01 Object-Centric Knowledge Graph and Relationships
- E-02 Cross-Project Shared Knowledge Reuse
- E-03 Global Search and Object Discovery
- E-04 Import History and Historical Reproducibility

## Epic F: Platform Hardening

Status: Active

- F-01 PDF Ingestion Robustness and Parsing Reliability
- F-02 Performance and Scalability for Large Project Sets
- F-03 Deterministic Regression Snapshot Expansion
- F-04 Documentation Consistency and Architecture Compliance

## Epic G: Procurement Domain Separation Readiness

Status: Deferred (Post-Phase 2)

- G-01 Procurement Workflow Boundaries (Non-ERP)
- G-02 Vendor Offering Lifecycle Extensions
- G-03 Receiving and Inventory Integration Hooks

## Epic H: Construction and Closeout Readiness

Status: Deferred (Post-Phase 2)

- H-01 Construction Execution Handoff Boundaries
- H-02 Closeout Data and Service History Handback
- H-03 Lifecycle Trace from Estimate to Completion

## Usage in Codex Sessions

For implementation prompts:

1. Reference the relevant epic and sprint ID from this document.
2. Validate planned work against architecture docs before coding.
3. Keep implementation and docs synchronized in the same change.

# Atlas Development Status

This document answers: Where is Atlas today?

It represents the current implementation state of Atlas.

## Related Documentation
- [README.md](README.md)
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
- [RELEASE_NOTES.md](RELEASE_NOTES.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)

## Current State
Atlas is in active Phase 2 Bid Intelligence development within the broader Atlas SaaS platform direction.

Atlas is being shaped as a multi-tenant Intelligent Lifecycle Solutions Management Platform for AV and lighting systems integrators, with QuickBooks Online as the Financial System of Record and AWS as the long-term hosting direction.

The AI assistant and broader lifecycle-platform capabilities are documented as future strategic direction rather than current implementation.

The current stabilization baseline candidate includes a project-specific Atlas workspace shell and the supporting bid-intelligence workspace surfaces.
Sprint 3 UX delivery added guided project review progression, explicit review status modeling, checklist visibility, and a concise project summary report center with deterministic exports.
Sprint 4 UI refinement adds repository-backed Open Existing Project, a stronger Projects library workflow, application-wide Knowledge scope, compact active-project identity, concise breadcrumbs, and a two-column Project Workspace layout (no persistent third context column).
Sprint 5 introduces an Equipment Object Workspace that treats equipment as first-class engineering objects with deterministic detail, relationship navigation, evidence, and recommended actions.
Sprint 6 implements the Atlas object navigation layer, adding shared object navigation patterns across Drawings, Specifications, Equipment, global object search, and Relationship Explorer.
Sprint 7 delivers persistent Global Object Search and Working Set workflows, including deterministic ranking, grouped result presentation, local search history, and object-context breadcrumbs.
Sprint 7.5 completes UI repair and runtime-state isolation with shared project context header rendering, configuration-driven navigation cleanup, shared object detail section scaffolding, and mutable runtime workspace storage outside immutable source fixtures.
Sprint 8 introduces the Deterministic Estimating Foundation: Estimate Workspace architecture, traceable estimate line entities, resolution/pricing status modeling, confidence scoring, and extension-point interfaces for future pricing engines.
Sprint 9 implements the Deterministic Product Resolution Engine: canonical product resolution domain/service models, dedicated Product Resolution workspace page, manual override audit behavior, engineering summary integration, and deterministic estimate pricing gate enforcement based on resolution completeness.
Sprint 9 Commercial Knowledge Foundation adds immutable price-sheet versioning, deterministic version comparison, product change reporting, and commercial freshness/lifecycle visibility without introducing procurement or quote-generation workflows.
Sprint 9.5 Commercial Knowledge Completion (C-02) adds deterministic draft/validate/finalize import lifecycle controls for CSV/XLSX/PDF imports, explicit diagnostic severity handling (`error|warning|informational`), unresolved-record surfacing, duplicate source-hash safeguards, mapping profile persistence, PDF page/table/header selection and correction review flow, and commercial completeness rollups without starting Product Resolution, deterministic costing, procurement, accounting, or ERP workflows.
Sprint 10 implements the Deterministic Pricing Engine: immutable price record selection, explainable candidate/rule traces, deterministic pricing snapshot IDs, manual pricing override audit model, advisory price-update impacts, export payloads, and Estimate/BOM pricing workspace integration.
Sprint D-01 Core Cost Selection Engine now establishes acquisition-cost-first deterministic selection, vendor-type-aware hierarchy, complete cost traceability, explicit selection APIs, quick-add product project isolation, optional promotion to immutable commercial knowledge, and cost-focused Estimate/BOM workspace views.
Sprint D-02 Estimate Engine and Cost Snapshot implementation is complete, including immutable revision lifecycle, line-item snapshots, replay/reselection workflows, and deterministic totals/validation.
Sprint D-03 Assemblies, Accessories, and Labor Rollups implementation is complete and formally closed.
Sprint A-04 consolidates Engineering Workstation UX consistency with shared workspace section headers, recommendation dedupe/grouping in Mission Control, terminology normalization for Products (Master Library), resettable dense-table filters, and source-object linking from estimate snapshot views.
Sprint A-05 performs end-to-end GUI validation and workflow refinement across Mission Control, Project Workspace, Knowledge, Estimate, and D-03 integration flows.
Sprint X-01 performs pilot-readiness walkthrough validation and usability hardening for existing workflows.
Sprint X-02 implements project creation and bid identity refinement with Atlas Bid ID allocation, explicit client/internal project identifiers, and metadata update workflows.
Sprint X-03 hardens onboarding and stakeholder workflows with strict two-step create-then-upload behavior, pending-upload accumulation semantics, shared organization directory linkage, and compatibility-safe stakeholder persistence.
Sprint X-04 completes Home/header/search simplification with Home terminology standardization, Enter-submit global search behavior, deterministic grouped search ordering, and removal of redundant Home portfolio sections.
Sprint X-05 continues shell hardening with header-based primary navigation, public Settings terminology for Administration, and deterministic Recent Projects on Home.
Sprint X-06 continues shell hardening with Atlas-only Home action, compact Search/menu controls, removal of the History dropdown, and centered responsive shell width.
Sprint X-07 continues shell hardening with fixed-width navigation, compact Home actions, meaningful search-query gating, and focused search results that replace the page body while active.
Sprint X-08 completed product hardening with visual-system consistency (#FAFAF9 workspace background, #004225 primary accent, neutralized surfaces) and a runtime-safe clear-search state model that separates widget input from submitted query state.
Sprint X-12 implements a reusable secondary and tertiary navigation framework for Knowledge, including deterministic Knowledge navigation state, search-handoff restoration, and reusable navigation contract modeling for future workspace reuse.
Sprint X-13 completes navigation clarity and UX refinement, removing architecture-facing UI artifacts, shifting contextual navigation ownership into the shared shell, and tightening Home/Reports information architecture without changing workflows.
Sprint W-01 completes Workspace Intelligence with deterministic context persistence and cross-workspace navigation continuity across Projects, Knowledge, Search, and object-detail flows.
Sprint W-02 defines the Universal Object contract, registry, and representative adapters that future object workspaces, search, graph traversal, and continuity flows will consume.
Sprint W-03 introduces the reusable Universal Object Workspace UI and controlled migration of selected Knowledge/Project object types onto the shared object workspace shell.
Sprint L-01 introduces the deterministic AV Lifecycle Engine foundation, including canonical lifecycle stages, transition/history/readiness contracts, compatibility-safe project persistence, and project-facing lifecycle UI integration without starting downstream execution workflows.
Sprint L-02 introduces the first Project Lifecycle Dashboard inside Universal Object Workspace, using the L-01 lifecycle engine as the single lifecycle authority.
Sprint A-07 defines the Transactions workspace and commercial-operations ownership model as architecture only, with no production implementation in this sprint.
Sprint A-08 defines the shared Commercial Document Framework for all future commercial documents as architecture only, with no production implementation in this sprint.
Sprint T-01 implements the Commercial Document Domain Foundation backend contracts/services, including lifecycle/revision rules, decimal-safe totals, organization-scoped numbering preview/allocation, commercial-document universal-object registry adapters, and compatibility-safe serialization behavior.
Sprint T-02 implements the Transactions Workspace Foundation UI/navigation layer, reusable transaction workspace service behavior, transaction-family search integration, and Object Workspace handoff for commercial-document kinds.
Sprint T-03 implements Estimate Transaction Integration, making Transactions > Estimates the first fully operational transaction family using the existing deterministic estimate engine for lines/revisions/issue workflows.
Sprint T-04 implements Settings Foundation and Document Numbering Preferences, including tenant-level commercial numbering policy configuration and user-level personal preferences boundaries.
Sprint T-05 amendment implements tenant Terms and Conditions settings blocks and integrates explicit terms snapshot behavior into Estimates and Sales Orders, including sales-order-from-estimate terms inheritance/default resolution and draft-only refresh controls.
Sprint T-05 amendment now also implements estimate and sales-order duplication, explicit revision lineage metadata, archive/restore revision-safe behavior, deterministic PDF export, and future email-delivery metadata hooks (non-executing).
Sprint T-06 implements Return Orders and Credit Memos, including customer-side return workflow, deterministic credit calculation, linked Credit Memo generation, and QuickBooks-boundary-safe sync metadata.
Sprint T-07 implements line presentation controls for commercial documents, including grouping, comment/spacer rows, explicit display ordering, presentation-aware sorting, and PDF layout preservation without changing authoritative totals.
Sprint P-01 implements the Roles and Permissions Foundation, including deterministic tenant-scoped role and permission contracts/services, deny-by-default evaluation with explicit deny precedence, universal-object action permission-hook gating, and a minimal Settings surface for role assignment and effective-access diagnostics.
Sprint P-02 introduces immutable audit contracts and service integration with compatibility-safe history persistence and scoped audit export behavior.
Sprint P-03 implements the Deterministic Background Job Framework with storage-agnostic contracts, local repository persistence, deterministic local execution, representative import/export workflow integration, Processing UI visibility, and permission-gated retry/cancel controls.
Sprint G-01 is documentation-only and codifies product governance, Scrum process discipline, roadmap responsibility boundaries, and progressive refinement without changing production code.

X-01 through X-13 are closed.

Epic X is completed and formally closed.

X-09 Design System Foundation is complete and formally closed.
X-10 Workspace Consistency and Information Density is complete and formally closed.
X-11 Typography System and Visual Polish is complete and closed.
X-12 Secondary and Tertiary Navigation Framework is complete and closed.
X-13 Navigation Clarity and UX Refinement is complete and closed.

X-09 scope remains behavior-preserving and does not start Epic E.
X-10 scope remains behavior-preserving and does not start Epic E.
X-11 scope remains behavior-preserving and does not start Epic E.

X-06/X-07/X-08/X-09/X-10/X-11 closeout status: completed.

## Quality Status (Latest Full Run)
- black .: passing
- ruff check .: passing
- mypy .: passing
- pytest: full suite passing (1332 tests baseline at P-03 start)

## Manual Validation (L-01)
- validated canonical project lifecycle display in Create Project, Project Settings, project lists, and Project Object Workspace compatibility surfaces
- validated applicable-stage sequence presentation and available-transition summary in Project Settings
- validated valid lifecycle transition behavior with required reason and persisted lifecycle history
- validated blocked invalid jump behavior with deterministic error messaging
- validated legacy project loading without forced project-file schema breakage
- validated project search/object identity metadata remains legacy-compatible while carrying canonical lifecycle stage context
- validated responsive lifecycle UI surfaces through existing shell-responsive contracts with no observed Streamlit state exceptions during targeted lifecycle flows

## Manual Validation (L-02)
- validated project object lifecycle view renders as a first-class tertiary Object Workspace view
- validated timeline, stage selection, transition summary, readiness diagnostics, and stage-history disclosure through focused dashboard paths
- validated lifecycle dashboard remains engine-backed and compatibility-safe without introducing separate project lifecycle state

## Manual UI Validation (W-01)
- validated project-to-Knowledge continuity from project reports summary into Knowledge Customers with visible return context
- validated shared-shell breadcrumb and return affordance behavior across the project-to-Knowledge continuity path
- validated focused search mode from an active project, including project/application scope labels and Clear Search return to the prior page
- validated active-project report breadcrumbs and meaningful return labels after continuity hops
- validated widths 820, 980, 1180, 1366, and large desktop on the continuity path with no horizontal overflow observed

## Manual UI Validation (X-13)
- validated Home, Projects, Knowledge, Reports, and active-project workspace navigation surfaces
- validated focused search mode and shared-shell navigation continuity
- viewport checks passed at widths 820, 980, 1180, and current desktop-width validation with no horizontal overflow observed on validated surfaces
- duplicate Knowledge page navigation scaffolding was removed so the shared shell now owns Knowledge navigation presentation

## Manual UI Validation (W-03)
- validated Object Workspace search handoff with visible context banner and deterministic return behavior
- validated shared Object Workspace identity and action composition behavior (including disabled-action reason presentation)
- validated object-level tertiary view controls are bounded to supported contract views only
- validated relationship and activity panels render through shared workspace sections with compatibility empty states where source history is sparse
- validated responsive widths (820, 980, 1180, 1366) with no horizontal overflow on validated Object Workspace surfaces
- validated no Streamlit state exceptions during repeated search-handoff and object-workspace return flows
- validated required object families in W-03 scope and compatibility surface set: Customer, Vendor, Manufacturer, Product, Service, Contact, Location, Project, Drawing, Specification, Equipment

## Tooling Status
- GitHub Actions configured
  - .github/workflows/python.yml
- Pre-commit configured
  - .pre-commit-config.yaml

## Active Focus
Phase 2 implementation remains the active product baseline.

Current governance posture:
- approved roadmap items govern future sprint selection
- no new feature sprint is activated by G-01
- inventory remains visible but paused

Broader product direction remains aligned to the lifecycle-platform roadmap, while implementation sequencing should follow the approved roadmap and progressive refinement model.

Secondary active focus:
- closeout regression monitoring and remaining page-migration debt triage for lower-priority advanced and object-detail surfaces.
- explicit identifier discoverability across project creation, listing, open flows, global search, and project settings.
- Epic E readiness assessment only (architecture review and sprint approval required; Epic E not started).
- K-01 follow-through validation for entity relationships, import/export compatibility, and search behavior.
- K-02 workflow completion for customer, service, manufacturer, vendor, and product entity operations.
- W-01 follow-through validation for deeper data-dependent continuity links and lower-priority object-detail adoption.
- W-02 follow-through validation for broader object-family adapters and future shared object workspace migration.
- W-03 follow-through validation for additional object families, deeper activity/history coverage, and legacy object-detail convergence.
- Working Set handoff coverage should continue expanding as broader object-family migration moves into future W-series scope.

Current implementation scope note:
- no Epic E implementation has started in this refinement pass
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or customer-estimate packaging features were introduced in X-02
- no Epic E implementation has started in X-03
- no Epic E implementation has started in X-04
- no Epic E implementation has started in X-05
- no Epic E implementation has started in X-06
- no Epic E implementation has started in X-07
- no Epic E implementation has started in X-08
- no Epic E implementation has started in X-09
- no Epic E implementation has started in X-10
- X-03 remains workflow hardening only and does not introduce new estimating/commercial/procurement/execution capabilities
- A-07 is documentation-only and does not introduce transaction code, QuickBooks integration, routing, or accounting behavior
- A-08 is documentation-only and does not introduce commercial-document code, UI, routing, or QuickBooks implementation
- T-01 implements backend commercial-document foundation only and does not introduce transactions UI, QuickBooks API transport, payments, or accounting-ledger behavior

## A-07 Architecture Validation Note
- Transactions and commercial-operations architecture are documented, not implemented
- QuickBooks remains the Financial System of Record
- Atlas ownership is limited to operational commercial-document creation and workflow before sync


Lifecycle object definitions and cross-phase module boundaries are documented in [DOMAIN_MODEL.md](DOMAIN_MODEL.md).

Current MAW reference-project behavior:
- Atlas attempts real package intake from examples/music_academy_of_the_west for the Reference Project view.
- Seed fixture data is retained as regression fallback only when real package intake is unavailable.
- GUI labels explicitly indicate whether Reference Project is using Real package intake or Seed fixture fallback.

Current workspace behavior:
- Atlas uses an Application Workspace for Home, project management, knowledge, reports, and administration.
- Opening a project switches Atlas into a dedicated Project Workspace with project-specific navigation.
- Local project records are stored under AtlasProjects/.
- Project Workspace emphasizes Overview, Documents, BOM Review, Scope & Risk, Engineering Review, Estimate (deterministic foundation), Notebook, Reports, and project details/settings pages.
- Equipment Workspace now provides object-first equipment investigation from canonical BOM lines with summary, list/detail workflow, relationship navigation, evidence/warnings, and deterministic recommended actions.
- Drawings, Specifications, and Equipment now use shared object headers plus deterministic References/Referenced By relationship groups for connected-object traversal.
- Relationship Explorer now supports relationship-type filtering, connected-object-type filtering, connected object cards, and richer edge context (originating document and warnings).
- Global object search is now persistent in the header, spans application and project object scopes, and uses deterministic ranking with project-first preference for non-exact matches.
- Search now persists recent queries and recently opened results in local workspace state.
- Pinned object UX is renamed to Working Set across object detail and search workflows, with add/remove/open/clear and compact reorder actions.
- Project Overview and header history now surface recently viewed objects and Working Set for fast return to active review objects.
- Runtime interactive workspace storage now defaults to a mutable local runtime path (`~/.atlas_core/runtime/AtlasProjects` unless overridden), preventing normal app execution from mutating tracked fixture data.
- Project navigation now includes explicit disabled future lifecycle sections and shared configuration-driven rendering.
- Shared object metadata/reference section helpers are reused across Equipment, Drawings, and Specifications detail views.
- Estimate Workspace now renders deterministic sections (Overview, Equipment Cost, Labor, Accessories, Freight, General Conditions, Engineering Allowances, Project Summary, Estimate Confidence).
- Estimate Workspace now includes deterministic pricing sections: Pricing Overview, Commercial Coverage, Priced Equipment, Unpriced Equipment, Stale Pricing, Allowances, Vendor Alternatives, Pricing Warnings, and Pricing History.
- Deterministic estimate lines now include required source traceability fields (source object, object type, manufacturer, model, description, quantity, pricing status, labor status, confidence, and source references).
- Estimate line navigation now supports Equipment, Specification, Drawing, Relationships, and Evidence traversal.
- Product resolution state now surfaces exact product, approved substitute, preferred alternate, generic allowance, and unknown product.
- Cost status now surfaces no pricing, estimated, quoted, verified, expired, and unavailable.
- Unknown products now remain no-pricing in deterministic mode.
- Estimate confidence now reports known pricing coverage, product resolution coverage, labor/pricing gaps, quantity uncertainty, and generic allowance exposure.
- Product Resolution workspace now provides deterministic filters (Unknown, Low Confidence, Needs Review, Resolved, Substituted), explainable candidate ranking, and manual override auditing.
- Engineering Review now includes Product Resolution summary metrics (resolved, unknown, generic allowance, substitutions, requiring review).
- Estimate workspace now consumes deterministic Product Resolution outputs and blocks pricing on unresolved/generic/low-confidence resolution states.
- Price List Library now imports into immutable Price Sheet Versions and Price Records through Commercial Knowledge services.
- Price List Library now supports C-02 structured commercial price-sheet ingestion for CSV, XLSX, and PDF through deterministic draft/validate/finalize controls with lifecycle diagnostics, unresolved-count visibility, and completeness metrics while preserving legacy fallback parsing for non-tabular imports.
- Knowledge workspace now supports K-02 operational customer/service entity workflows (create, list, archive, restore) and framework-backed summary metrics.
- Import History page now exposes deterministic version-level change summaries and historical replay of previous commercial versions.
- Knowledge workspace now includes Commercial Health metrics for coverage, freshness, missing pricing, stale pricing, and commercial confidence.
- Deterministic pricing lines now include selected price record/vendor offering/version traceability, freshness/status/warnings, confidence rationale, and manual override provenance.
- BOM Review now surfaces lightweight deterministic pricing fields and drill-down selection details.
- Deterministic pricing exports now provide Pricing Summary JSON, Priced BOM CSV, Commercial Coverage JSON, and Pricing Exceptions CSV.
- Deterministic cost lines now include vendor classification, source file/row traceability, import/effective/expiration dates, and confidence rationale.
- Estimate workspace now includes deterministic cost dashboard views and quick-add product workflow (project-only or promotion).
- Commercial coverage now tracks current/historical/allowance/missing/stale cost states with material cost confidence.
- BOM Review now includes an Open Equipment Detail action for selected BOM rows while preserving BOM table reconciliation behavior.
- Drawing and Specification workspaces now expose referenced equipment as human-readable objects that can open Equipment Workspace.
- Project Workspace now includes a non-blocking guided review sequence with statuses (not started/ready/needs review/blocked/complete).
- Overview and Reports expose a deterministic project review checklist and specific next-step navigation.
- Reports now provide Project Summary, Estimator Brief, BOM Export, Scope and Risk Export, and Engineering Review Export views.
- Project Summary report exports are deterministic Markdown/JSON/HTML for internal review use.
- Open Existing Project defaults to repository-backed project selection with search/sort/filter and archived visibility.
- Manual path entry remains available only as an advanced development/recovery option.
- Knowledge workspace is application-wide and excludes project-specific review pages.
- Workspace Intelligence now preserves explicit selected project-object and selected Knowledge-record context, bounded return context, and bounded navigation history through existing workspace persistence.
- Cross-workspace continuity now supports deterministic project-to-Knowledge and Knowledge-to-project movement where existing repository or reviewed-equipment data proves the relationship.
- Universal Object contracts now provide shared identity, metadata, relationship, activity, lifecycle, action, and presentation envelopes for representative project, knowledge, and engineering object families.
- Universal Object Workspace now provides a shared UI shell for migrated object families while preserving existing authoritative domain workflows.
- Active project identity is surfaced through a compact project header with lifecycle/status badges and recommended next action.
- Project Workspace desktop layout is two-column (navigation + working content), with inline/on-demand object detail.
- Home now contains primary project actions plus Action Center (critical/high deduplicated actions) and Recent Activity only.
- Mission Control naming remains internal-only for compatibility route/state keys.
- Global search executes directly on Enter and renders deterministic grouped result sections by user-facing type labels.

## Latest Completed Feature
- Estimator Brief Enhancements (deterministic executive summary, prioritized reviewer actions, and evidence traceability)

## Baseline Candidate Notes
- Conceptual label: phase-2-bid-intelligence-baseline-candidate (not a Git tag yet).
- Phase 2 snapshot-style tests cover representative MAW plan review and revision comparison outputs.
- MAW remains canonical sample/reference data only (not hardcoded product logic in core services).
- Phase 3+ workflows remain out of active orchestration scope for this baseline.

## Last Known Next Task Sequence
1. Drawing/spec intelligence refinements
2. PDF ingestion and indexing refinements
3. Device schedule extraction refinements

## Reference Documents for Current Baseline
- [PRODUCT_RESOLUTION.md](PRODUCT_RESOLUTION.md)
- [MANUFACTURER_REGISTRY.md](MANUFACTURER_REGISTRY.md)
- [COMMERCIAL_KNOWLEDGE.md](COMMERCIAL_KNOWLEDGE.md)
- [PRICE_VERSIONING.md](PRICE_VERSIONING.md)
- [PRICING_ENGINE.md](PRICING_ENGINE.md)
- [COST_ENGINE.md](COST_ENGINE.md)
- [ASSEMBLIES_AND_LABOR.md](ASSEMBLIES_AND_LABOR.md)

# Release Notes

This document answers: How did Atlas evolve?

It is the historical record of product milestones.

## See Also

- [README.md](README.md)
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- [ROADMAP.md](ROADMAP.md)
- [PRODUCT_VISION.md](PRODUCT_VISION.md)

This document tracks product-facing changes for Atlas Preview releases.

## Format

- Reverse chronological order (newest release first).
- Focus on user-visible behavior and workflow changes.
- Include quality gate status when relevant.

## Unreleased (Epic W Sprint W-03 Universal Object Workspace)

## Unreleased (Epic T Sprint T-01 Commercial Document Domain Foundation)

### Improved

- Atlas now includes shared commercial-document backend domain models and contracts for identity, revisions, line items, relationships, approval state, sync metadata, totals, diagnostics, and numbering policy.
- Initial transaction-family support is available for Estimate, Proposal, Sales Order, Purchase Order, RFQ, Vendor Quote, Receiving Record, Vendor Bill, Customer Invoice, and Change Order.
- Commercial-document lifecycle now uses explicit transition rules from Draft through Archived with immutable issued revision snapshots and revision history preservation.
- Numbering now supports tenant-scoped and organization-scoped preview/allocation semantics with no number reuse.
- Universal Object registry now includes commercial-document adapter registration for transaction-family identities.

### Scope Notes

- backend foundation only
- no transactions UI implementation
- no QuickBooks API implementation
- no accounting/payment/ledger subsystem behavior

## Unreleased (Epic L Sprint L-01 AV Lifecycle Engine Foundation)

## Unreleased (Epic L Sprint L-02 Lifecycle Dashboard)

### Improved

- Atlas now includes a first-class `Lifecycle` tertiary Project Object Workspace view for project records
- project lifecycle is visualized as a horizontal progress timeline with distinct complete, active, available, blocked, skipped, and archived states
- stage selection now reveals description, readiness diagnostics, transition requirements, stage-specific lifecycle history, and deterministic related objects when available
- lifecycle dashboard surfaces current stage, stage status, completed stages, blocked stages, upcoming stages, available transitions, recommended next action, and responsible role without duplicating lifecycle state

### Scope Notes

- dashboard visualization only
- no downstream workflow execution modules
- no automatic lifecycle advancement or workflow automation

### Validation

- focused lifecycle dashboard coverage validates project supported views, lifecycle dashboard rendering, and project universal-object lifecycle projection
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1255 tests

### Improved

- Atlas now includes a deterministic AV Lifecycle Engine with canonical lifecycle stages from lead through archived
- lifecycle state is now persisted through a compatibility-safe lifecycle plan snapshot while preserving legacy project status and lifecycle stage fields
- Project Settings now shows lifecycle-engine context, available transitions, applicable sequence, and recent lifecycle history
- project lifecycle transitions now require a reason and are auditable through repository history
- Project Object Workspace and shared universal-object projection paths now carry canonical lifecycle context for project records

### Scope Notes

- lifecycle foundation only
- no procurement, installation, commissioning, service, or asset-lifecycle execution workflows
- no Epic E start

### Validation

- focused lifecycle, project workspace, universal object, and object workspace tests passed for the new L-01 behavior
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1254 tests
- targeted validation confirmed compatibility-safe legacy project loading, deterministic invalid-transition blocking, required transition reasons, lifecycle history rendering, and no unexpected project-file rewrites in the validated service paths

### Deferred Lifecycle Notes

- downstream workflow modules remain intentionally deferred behind the new lifecycle-engine contracts

### Improved

- Atlas now includes a reusable Universal Object Workspace UI inside the existing shell, backed by the W-02 universal object contract and registry
- supported object opens from search and Working Set now route through Object Workspace for migrated object families
- migrated object scope includes Customer, Vendor, Manufacturer, Product, Service, Contact, Location, and Project
- Drawing, Specification, and Equipment now support read-only Universal Object Workspace rendering with direct open actions to authoritative engineering pages
- object workspace renders consistent identity, actions, tertiary view navigation, relationships, activity, provenance, and return-context banner behavior

### Scope Notes

- controlled migration only
- no redesign of unrelated workflows
- no new domain entities, AI, semantic retrieval, or Epic E start

### Validation

- focused W-03 tests cover object-workspace composition, search/working-set handoff, context-banner behavior, supported-view selection, disabled action reasons, and compatibility routing behavior
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1247 tests
- manual validation confirmed shared object-workspace behavior for Customer, Vendor, Manufacturer, Product, Service, Contact, Location, Project, Drawing, Specification, and Equipment
- manual validation confirmed consistent identity/action composition, bounded supported tertiary views, relationship/activity presentation, context banner/return behavior, search and Working Set handoff behavior, and no horizontal overflow at 820/980/1180/1366 widths
- manual validation observed no Streamlit state exceptions during repeated search handoff and return flows

### Deferred Migration Notes

- broader object-family migration remains intentionally deferred to future W-series planning
- existing authoritative domain workflows remain the source of truth for create/edit/archive/import/export behavior

## Unreleased (Epic W Sprint W-02 Universal Object Contract)

### Improved

- Atlas now defines a universal object adapter contract for identity, metadata, relationships, activity, lifecycle, actions, and presentation hints
- representative adapters are available for project, knowledge, and engineering object families without replacing existing domain models
- search references, Working Set-compatible records, and W-01 context persistence can now carry universal object identity where practical
- registry-backed adapter lookup and duplicate-registration validation provide deterministic object-contract resolution

### Scope Notes

- contract and interoperability layer only
- no Universal Object Workspace UI yet
- no AI, semantic retrieval, new workflows, or Epic E start

### Validation

- focused contract and interoperability tests now cover identity determinism, registry behavior, representative adapters, relationship validation, lifecycle/actions/presentation metadata, search compatibility, Working Set compatibility, and W-01 context compatibility
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1231 tests

## Unreleased (Epic W Sprint W-01 Context Persistence and Cross-Workspace Navigation) (Closed)

### Improved

- Atlas now preserves explicit working context across Projects, Knowledge, Search, and related object-detail surfaces through repository-backed workspace state
- cross-workspace opens now capture deterministic return context, visible breadcrumb context, and a one-click return affordance in the shared shell
- search results now show explicit project/application scope labels while preserving deterministic ranking and Clear Search return behavior
- Working Set continuity now supports both project objects and Knowledge entities under the existing compatibility model

### Scope Notes

- deterministic continuity only
- no AI, semantic retrieval, new business workflows, or Epic E start
- no parallel persistence system

### Validation

- focused continuity regression coverage increased the full-suite baseline to 1217 passing tests
- live validation confirmed project reports summary to Knowledge customer continuity, visible return context, readable breadcrumbs, and no horizontal overflow at 820, 980, 1180, 1366, and large desktop widths
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1217 tests

## Unreleased (Epic X Sprint X-13 Navigation Clarity and UX Refinement) (Closed)

### Improved

- architecture-facing navigation labels and implementation-only page notes were removed from validated production UI surfaces
- shared-shell secondary navigation is now contextual across application, project-library, and active-project modes
- Knowledge no longer renders a duplicate internal navigation panel; the shared shell owns visible navigation presentation
- Home now behaves as an operational landing page around Continue Working, Recent Projects, Action Center, Notifications, and Favorites
- Reports is now organized around deliverable readiness and output-oriented tables rather than a workflow-summary posture

### Scope Notes

- UX refinement only
- no routing, persistence, search-behavior, business-logic, or workflow changes
- no Epic E start

### Validation

- manual validation covered Home, Projects, Knowledge, Reports, active-project workspace navigation, focused search mode, and medium-width layout behavior
- validated surfaces showed no horizontal overflow during X-13 review widths
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1203 tests

## Unreleased (Epic K Sprint K-02 Core Knowledge Entities and Operational Workflows)

### Improved

- Knowledge Entity Framework now exposes operational workflows for customer and service entities (create, update, archive, restore, list/search/get).
- Product lifecycle updates now synchronize framework-backed product entities so activation/lifecycle state remains consistent across commercial and knowledge views.
- Knowledge workspace now includes customer and service operational controls for deterministic create/list/archive/restore workflows.
- Dashboard and service summaries now include framework-level metrics for entity totals, activity state, and relationship counts.

### Scope Notes

- deterministic framework/workflow hardening only
- no Epic E start
- no procurement, service-ticket, installed-asset, or sell-pricing workflow start

### Validation

- Focused validation passed for `tests/test_knowledge_entity_framework.py` and `tests/test_phase2_global_search_working_set.py`.
- Full quality gate baseline remains passing (`black`, `ruff`, `mypy`, `pytest`) with current full-suite count at 1182 tests.

## Unreleased (Epic X Sprint X-11 Typography System and Visual Polish) (Closed)

### Improved

- Atlas now uses an official centralized typography system with Inria Serif for display hierarchy and Fira Sans for interface/content hierarchy.
- Shared typography scale tokens now govern Display, Heading, Body, Caption, Label, and Value sizes from a single design-system source.
- Heading rhythm, table/header readability, status/label hierarchy, and control typography are polished across shared shell surfaces while preserving behavior.
- Font loading is now centralized through a single authoritative stylesheet path, with explicit guidance for enterprise self-hosting replacement.

### Scope Notes

- behavior-preserving visual hardening only
- no workflow, routing, business-logic, or persistence changes
- no Epic E start

### Validation

- Manual validation confirmed typography hierarchy and shell readability across Atlas, Projects, Knowledge, Reports, project workspaces, focused search mode, and Settings access.
- Responsive checks at 820, 980, 1180, 1366, and large desktop widths showed no horizontal overflow regressions.
- Full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count unchanged at 1177 tests.

## Unreleased (Epic X Closeout Validation and Closure) (Closed)

### Improved

- Engineering Notebook now has a validated normal-flow entry from Overview Guided Project Review actions (Open Notebook).
- Linked-object navigation from Notebook entries now reliably executes for generated entries by using stable linked-object action keys.
- Epic X closeout validation confirmed no blocking shell, navigation, search, responsive, or design-system defects across validated X-01 through X-10 surfaces.

### Scope Notes

- validation and closure hardening only
- no new domain capabilities
- no persistence/business-logic expansion
- no Epic E start

### Closeout Validation

- Manual validation covered Notebook entry path, list/empty-state behavior, filtering, linked-object navigation, decision-log tab, return navigation, context preservation, and medium-width layout behavior.
- X-09 and X-10 migrated surfaces remained intact during closeout checks.
- Full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count unchanged at 1177 tests.

### Remaining Non-Blocking UX Debt

- lower-priority advanced/object-detail surfaces still rely on older inline wrappers and should continue migration to shared primitives.
- broader notebook discoverability beyond guided Overview actions can be improved further in a future hardening sprint.

## Unreleased (Epic X Sprint X-10 Workspace Consistency and Information Density) (Closed)

### Improved

- Remaining primary project workspaces now use shared design-system wrappers for section hierarchy, notice panels, table presentation, and responsive control groups.
- Consistency migration now covers Overview, Documents, BOM Review, Scope & Risk, Engineering Review, Estimate, and Notebook surfaces without changing deterministic behavior.
- Project Summary and related report-facing project surfaces now use the same shared wrappers for reduced visual drift.

### Scope Notes

- UI consistency hardening only
- no business-logic or persistence changes
- no Epic E start

### Closeout Validation

- Manual validation confirmed primary workspace routing and rendering for Home, Projects, Knowledge, Reports, Overview, Documents, BOM Review, Scope & Risk, Engineering Review, Estimate, and Settings.
- Focused global search, clear-search behavior, and existing deterministic project context behavior remained intact.
- Full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count unchanged at 1177 tests.

### Remaining UX Debt

- Some lower-priority advanced/object-detail pages still rely on older inline wrappers and should continue migrating to shared primitives.
- Notebook discoverability from core guided-review entry points can be improved further in a future hardening pass.

## Unreleased (Epic X Sprint X-09 Design System Foundation and Reusable UI Components) (Closed)

### Improved

- Atlas shell styling now comes from a centralized design-system stylesheet source instead of a large inline CSS block in the app shell.
- Shared design tokens now provide consistent color, spacing, radius, control sizing, and bounded-layout authority.
- Shared UI primitives now back common rendering patterns (metric cards, empty/guided-empty states, workspace context banners, notice panels, status badges).
- Representative pages (Home, Projects, Knowledge, Reports) now use shared wrappers for section headings, responsive control groups, and table rendering to reduce visual inconsistency.

### Scope Notes

- UI architecture and visual hardening only
- no business-logic or persistence changes
- no Epic E start

### Closeout Validation

- Manual validation confirmed Home, Projects, Knowledge, Reports, Project Workspace shell, focused global search, clear-search behavior, direct search-result navigation, and Settings menu routing.
- Responsive checks at common desktop and split-screen widths showed no horizontal overflow regressions on migrated pages.

### Remaining Migration Debt

- Additional project-workspace pages still rely on legacy inline layout and table wrappers and remain candidates for future design-system primitive migration.

## Unreleased (Documentation Refresh for Atlas Product Direction Update)

### Improved

- Repository documentation now describes Atlas as a commercial SaaS platform for AV and lighting systems integrators.
- Product vision now frames Atlas as an Intelligent Lifecycle Solutions Management Platform with a broader lifecycle roadmap.
- Product vision now documents a future Atlas AI assistant, data boundary, and governance posture.
- Product vision now includes a dedicated foundational-knowledge policy for future AI features.
- Architecture documentation now states the operational-system-of-record vs financial-system-of-record boundary.
- Roadmap documentation now balances future lifecycle areas beyond bid intelligence.
- Onboarding and design guidance now reflect the multi-tenant, AWS, and Stripe direction without changing product behavior.

### Scope Notes

- documentation-only update
- no production code changes
- no change to current Phase 2 implementation priorities

## Unreleased (Sprint D-01 Core Cost Selection Engine)

## Unreleased (Epic A Sprint A-04 Engineering Workstation UX Consolidation)

## Unreleased (Epic X Sprint X-03 Onboarding and Stakeholder Workflow Hardening)

## Unreleased (Epic X Sprint X-06 Responsive Header and Navigation Simplification)

## Unreleased (Epic X Sprint X-08 Search Clear-State Runtime Fix and Visual-System Closeout)

Completion status:

- X-06 responsive shell refinement: completed
- X-07 focused search refinement: completed
- X-08 initial visual-system pass and safe clear-search remediation: completed

### Improved

- Visual-system hardening now standardizes workspace background #FAFAF9 and primary action accent #004225 across the bounded shell.
- Global search now uses separated runtime state for widget input and submitted query.
- Clear Search now performs a safe widget-key reset, exits focused search mode, and returns to the active page context without Streamlit widget-session mutation exceptions.
- Direct search-result navigation clears focused search mode through the same safe reset path.

### Scope Notes

- product hardening only for existing Home/header/search workflows
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

## Unreleased (Epic X Sprint X-07 Fixed-Width Navigation and Focused Search Results)

### Improved

- Global search now shows a focused results view while a meaningful query is active.
- Search result rows are directly clickable, and the results panel replaces the page body during search mode.
- Meaningless punctuation-only search strings no longer trigger broad search rendering.
- Home action buttons stay compact, and the shell navigation remains bounded.

### Scope Notes

- product hardening only for existing Home/header/search workflows

### Improved

- Atlas is now the sole Home action in the global shell.
- The public Home navigation tab has been removed.
- Global Search is now a label-free input with the Search placeholder.
- Settings is now exposed only from an icon-only hamburger trigger.
- The History dropdown has been removed from the global shell.
- The main shell is constrained to a centered workstation-style content width.

### Scope Notes

- product hardening only for existing Home/header/navigation workflows
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

## Unreleased (Epic X Sprint X-05 Top-Header Navigation and Recent Projects)

### Improved

- Primary navigation now lives in the top header rather than a left-column rail.
- Administration is exposed publicly as Settings through an upper-right hamburger menu.
- Home now shows a deterministic Recent Projects list sourced from existing workspace open timestamps.

### Scope Notes

- product hardening only for existing Home/header/navigation workflows
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

## Unreleased (Epic X Sprint X-04 Home Page Simplification and Global Search Refinement)

### Improved

- Application Workspace landing-page terminology is standardized to Home.
- Mission Control remains internal-only as a compatibility route name.
- Header global search now submits directly on Enter.
- Empty/whitespace-only search no longer executes or renders result panels.
- Search results are grouped by user-facing object type with deterministic preferred ordering and safe unknown-type fallback ordering.
- Home content is simplified to primary project actions plus Action Center and Recent Activity.
- Action Center now shows prioritized critical/high deduplicated actions only.

### Scope Notes

- product hardening only for existing Home/header/search workflows
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

### Improved

- Create New Project now enforces strict two-step onboarding: metadata-first create, then Documents upload.
- Create workflow now routes directly to Documents after successful project creation.
- Documents uploader now accumulates pending files across multiple chooser interactions instead of replacing prior selections.
- Pending upload queue now supports deterministic dedupe identity and explicit remove/clear behaviors.
- Upload execution is explicit through Upload Pending Files; no automatic upload on file selection.
- Create and Project Settings now support lookup-first stakeholder organization selection backed by shared organization records.
- Stakeholder workflow now supports inline organization creation with duplicate-warning confirmation.
- Malformed PDF uploads are handled safely by deterministic intake warnings (no UI traceback crash path).

### Scope Notes

- workflow hardening only for existing create/settings/documents flows
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

## Unreleased (Epic X Sprint X-02 Project Creation and Bid Identity Refinement) (Closed)

### Improved

- Create New Project now uses Atlas Bid ID allocation with deterministic non-consuming preview behavior.
- Project metadata now distinguishes Atlas Bid ID, Client Project Number, and Internal Project Number.
- Projects and Open Existing views now surface/search identifier fields for faster retrieval.
- Global search project records now include Atlas Bid ID and client/internal project-number match fields.
- Project Settings now supports controlled identity metadata updates, including lifecycle-stage-aware internal project number editing.
- Mission Control recommendations now include a deterministic prompt when awarded/execution lifecycle stages are missing an internal project number.
- Create New Project now includes an embedded bid-document upload panel with drag/drop, browse, review-before-submit, and explicit create/upload action controls.
- Create workflow now supports partial-success import behavior (accepted files import, rejected files are reported with diagnostics).
- ZIP onboarding now enforces deterministic safety checks (unsafe path rejection, encrypted-entry rejection, system-artifact filtering, depth/entry/expansion limits).

### Scope Notes

- product-hardening and project identity refinement only for existing capabilities
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

## Unreleased (Epic X Sprint X-01 Pilot Readiness and Application Walkthrough)

### Improved

- Mission Control recommendation selection now includes deterministic guidance framing (why seen, impact, ignore risk, and next action).
- Assembly Library now shows selected-version validation results inline after validation actions.
- Assembly Library state persistence writes are consolidated through shared helper logic for maintainability.

### Scope Notes

- product-hardening and usability refinement only for existing capabilities
- no Commercial Intelligence, Sell Pricing, Proposal Generation, or post-D architecture expansion

## Unreleased (Epic A Sprint A-05 End-to-End GUI Validation and Workflow Refinement)

### Improved

- Mission Control recommendation panel now includes priority summary counts and direct destination navigation.
- Assembly Library component add workflow now validates required reference inputs with clearer user-facing errors.
- Estimate D-03 refresh comparison workflow now supports explicit preview dismissal before apply.

### Scope Notes

- usability and workflow refinement only across existing capabilities
- no Epic E start and no Commercial Intelligence/Sell Pricing/Proposal Generation implementation

## Unreleased (Sprint D-03 Assemblies, Accessories, and Labor Rollups)

### Added

- D-03 assembly/labor domain contracts and deterministic expansion service.
- Estimate engine D-03 integration APIs for assembly insertion, refresh, recalculation, version upgrade comparison, and provenance inspection.
- Immutable labor snapshot persistence and generated-line provenance fields.
- Knowledge workspace Assembly Library tab and Estimate workspace D-03 controls.
- Mission Control recommendation ingestion from estimate engine D-03 readiness diagnostics.

### Scope Notes

- D-01 remains deterministic product cost selection authority.
- D-02 remains revision, lock, and cost snapshot authority.
- D-03 implementation is complete and closed with full quality gates and full-suite regressions passing.

### Improved

- Added shared workspace section-header orientation pattern across key workstation pages.
- Consolidated Mission Control recommendation surfaces into a deduplicated, prioritized recommendation table.
- Normalized Knowledge terminology to Products (Master Library).
- Added consistent filter reset controls in dense Knowledge and BOM table views.
- Added direct source-object navigation from estimate revision snapshot viewer.

### Scope Notes

- UX consolidation only.
- No D-03 capabilities introduced.

## Unreleased (Sprint D-01 Core Cost Selection Engine)

### Added

- Explicit deterministic core cost selection APIs:
  - `select_cost`
  - `list_eligible_candidates`
  - `evaluate_candidate`
  - `explain_candidate_rejection`
  - `compare_candidates`
  - `preview_quantity_normalization`
  - `get_selection_provenance`
  - `get_confidence_breakdown`
- New core selection contracts in cost engine domain:
  - `CostSelectionRequest`
  - `CostSelectionResult`
  - `CostProvenance`
  - `CostSelectionDiagnostic`
  - `CostSelectionResultStatus`
- BOM Review Cost Selection Inspector workflow with explicit request controls and deterministic diagnostics/provenance output.

### Scope Notes

- Current sprint scope is D-01 only.
- D-02 is implemented; D-03 is implemented and closed.

## Preview 0.5 (2026-07-07)

### Added

- Engineering Notebook workspace page for structured engineering documentation.
- Notebook entry model with support for:
  - Engineering notes
  - Observations
  - Decisions
  - Assumptions
  - Questions
  - Follow-ups
  - Clarifications
  - Internal coordination notes
  - Site visit notes
  - Meeting notes
  - Review summaries
- Engineering Decisions view as a focused decision log.
- Investigation Mode action to create pre-linked investigation notes.
- Notebook object linking with click-through navigation across relevant workspace pages.
- Notebook entries integrated into activity timeline.
- Context panel support for selected notebook entries.

### Improved

- Preview 0.5 workspace stabilization and UX consistency updates.
- Navigation and workflow continuity across core engineering review pages.

### Documentation

- Added Engineering Notebook reference documentation.
- Added Preview 0.5 stabilization checklist.

### Quality

- Quality gate passed:
  - black
  - ruff
  - mypy
  - pytest (917 passed)

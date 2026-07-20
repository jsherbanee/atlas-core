# Atlas

## Purpose
Provide the Atlas application workspace for bid-intelligence and lifecycle operations so users can create or open a project, upload documents, run analysis, review BOM and risk conclusions, and export an operational project summary.

This interface is local-first for development, while the product direction remains commercial SaaS:
- Local file-backed project repository persistence under `AtlasProjects/`.
- No procurement/RFQ/submittal/invoice/execution/closeout/vendor communication workflows in this phase.

Atlas Workspace v1 (Sprint 8) launches into a persistent interactive engineering shell.

Atlas Workspace UI Sprint 4 adds repository-first project access, a scoped application-wide Knowledge workspace, a compact active-project identity header, and a strict two-column Project Workspace layout.

Atlas Workspace UI Sprint 6 adds an object navigation layer that connects equipment, drawings, specifications, systems, rooms, risks, RFIs, and evidence through shared object headers, references/referenced-by groups, relationship explorer filters, and quick cross-object navigation actions.

Atlas Workspace UI Sprint 7 adds persistent Global Object Search and a project-scoped Working Set for active review objects.

Atlas Workspace Sprint 7.5 performs UI repair and runtime-state isolation: shared project context header rendering, configuration-driven navigation (including disabled future lifecycle sections), shared object detail section scaffolding, breadcrumb normalization, meaningful empty-state messaging, and mutable runtime project storage outside immutable repository fixtures.
Atlas Workspace UI Sprint X-05 moves primary navigation into the top header, exposes Settings as a normal primary destination, and replaces Home recent activity with a deterministic Recent Projects list.
Atlas Workspace UI Sprint X-06 keeps the header-based shell while removing the public Home button, simplifying the Search control, removing the History dropdown, and constraining the shell to a centered workstation-style width.
Atlas Workspace UI Sprint X-07 keeps the bounded shell but turns global search into a focused results mode with compact navigation, meaningful-query gating, and direct row-click navigation while active.
Atlas Workspace UI Sprint X-08 keeps the visual-system shell posture (background #FAFAF9, primary accent #004225, neutral surfaces) and fixes search clear-state runtime flow by separating widget input from submitted query state with safe widget-key reset on Clear Search.
Atlas Workspace UI Sprint X-09 establishes a reusable design-system foundation (shared tokens, centralized stylesheet authority, and reusable UI primitives) and migrates Home, Projects, Knowledge, and Reports to those primitives without changing workflow behavior.
Atlas Workspace UI Sprint X-10 completes consistency migration for remaining primary project workspaces using existing shared wrappers and deterministic behavior-preserving UI hardening.
Atlas Workspace UI Sprint X-12 introduces a reusable secondary and tertiary navigation framework for Knowledge and Projects modes, with deterministic state restore and search-handoff routing.
Atlas Workspace UI Sprint X-13 completes navigation clarity and UX refinement, removing production-facing implementation artifacts and consolidating contextual navigation into the shared shell.
Atlas Workspace Sprint T-02 adds the first Transactions workspace UI/navigation foundation with sectioned transaction families, action-oriented tertiary controls, and search/object-workspace handoff for commercial-document records.
Atlas Workspace Sprint T-03 makes Transactions > Estimates the first fully operational transaction family with estimate-specific tertiary controls (Lines, Revisions, Issue) while reusing the existing deterministic estimate engine.
Atlas Workspace Sprint T-04 introduces the Settings workspace foundation with reusable secondary/tertiary navigation, active Organization Settings and Personal Preferences content, and tenant-level commercial document numbering preferences.
Atlas Workspace Sprint T-05 amendment introduces tenant Terms and Conditions settings blocks (browse/add/edit/version/default/archive/preview), estimate internal/customer view presentation controls over a shared revision, explicit draft terms refresh behavior, and sales-order-from-estimate terms snapshot inheritance/default resolution.
Atlas Workspace Sprint T-08 operationalizes Transactions > Customer Invoices with add/browse/edit/lines/billing/revisions/approvals/issue/sync-status/activity/export flows and invoice-specific sync/payment metadata controls.
Atlas Workspace Sprint T-09 adds change-order tracking controls to Sales Order and Return Order creation/edit flows (mark-as-change-order, project-required guardrails, `CO #n` preview, reason/approval/base-bid fields, owner change reference, internal notes) and introduces a project commercial summary view for original contract, net additions, net deductions, current contract value, and pending/approved/invoiced/outstanding change totals.
Atlas Workspace Sprint S-01 completes Settings alpha scope with Organization Profile, Taxes and Surcharges, expanded Terms families (Return Order and Customer Invoice), Document Templates management (create/list/duplicate/preview), Integrations metadata hooks, and Security policy metadata controls with permission-gated mutation paths.
Atlas Workspace Sprint U-01 completes Transactions commercial-document usability polish by normalizing tertiary actions across active commercial families, unifying export controls onto deterministic `export_pdf` paths, extending line-sort parity for presentation controls, and surfacing explicit source/lineage context in Related Documents.
Atlas Workspace Sprint U-02 completes end-to-end UX and workflow polish across all primary workspaces with clearer page-purpose identity, tighter action language consistency, reduced prototype/developer terminology, improved settings roadmap-section guidance, and consistent responsive behavior validation at 820/980/1180/1366 widths.
Atlas Workspace Sprint C-03 extends Transactions catalog-backed line insertion for Product/Service/Fee/Assembly item types, including assembly `expand` and `grouped` insertion options and credit memo compatibility, while preserving deterministic no-mutation behavior for issued revisions.
Atlas Workspace Alpha UI Cleanup refines production-facing shell/navigation behavior by tightening active vs deferred route visibility, reducing duplicate action exposure, and removing tenant-facing implementation remnants without adding new business features.
Atlas Workspace Alpha UI Cleanup (Responsive Navigation and Estimate Creation UX) standardizes top-header primary navigation ordering to Transactions, Projects, Knowledge, Reports (with Atlas as the fixed Home control), restores tenant-facing footer copyright text, and provides a dedicated Transactions > Estimates > Add workflow with dropdown-driven estimate details and catalog-backed Product/Service/Fee/Assembly line insertion.
Atlas Workspace Alpha UI Cleanup (Header Consolidation and Copy Reduction) consolidates the shell to one shared header row of fixed-width controls (Atlas, Transactions, Projects, Knowledge, Reports, Settings, Search), routes navigation through the current Streamlit session, removes redundant tenant-facing shell metadata and repeated descriptive page copy, and preserves continuity-critical object breadcrumbs.
Atlas Workspace Alpha UI Cleanup (Navigation Simplification and Functional Knowledge Links) removes the burger/menu shell, simplifies Transactions to active and deferred family lists without overview/status-card noise, and restores direct same-window Knowledge workspaces for Vendors, Manufacturers, Products, and Services.
Atlas Workspace Alpha UI Cleanup (Accordion Navigation Refinement) keeps primary header navigation unchanged while moving tertiary actions into the left secondary navigation column as a deterministic accordion, removing the duplicate tertiary row above page content.
Atlas Workspace Knowledge Refinement consolidates Knowledge around Customers, Vendors, Manufacturers, and Catalog; removes duplicate central entity-family navigation; moves Price Lists under Vendors; and treats Contacts, Addresses, Imports, and Assemblies as contextual tertiary/catalog surfaces.
Atlas Workspace Knowledge Repair tightens the accordion into compact contextual navigation, removes redundant Knowledge/Customers content headings, restores Vendor/Manufacturer/Catalog routing expectations, and upgrades Customers with sortable browse rows, detail handoff, single-name creation, generated Customer IDs, and no tenant-facing JSON controls.
Atlas Workspace Knowledge Cleanup replaces the custom Knowledge accordion with controlled disclosure sections, removes redundant Customer sort buttons, and makes the compact Customer selector the primary browse/detail handoff.
Atlas Workspace App-Wide Navigation Refactor replaces widget-owned first-column expanders with a shared controlled accordion so Projects, active Project workspaces, Transactions, Knowledge, Reports, and Settings allow only one expanded secondary section at a time.
Atlas Workspace App-Wide Navigation Hotfix makes that accordion an application-shell capability with controlled chevron headers, indented tertiary links, collapse-cleared tertiary state, and no page-specific navigation expander implementations.
Atlas Workspace Organization Merge adds permission-gated Organization Merge controls to Customer, Vendor, and Manufacturer details, supports possible-duplicate review, source selection, preview, actor/reason capture, irreversible confirmation, and Organization Object Workspace role-profile/merge-history visibility.
X-09 closeout status: complete and closed.
X-10 closeout status: complete and closed.
X-13 closeout status: complete and closed.

Completion status:
- X-06 responsive shell refinement: completed
- X-07 focused search refinement: completed
- X-08 initial visual-system pass and safe clear-search remediation: completed
- X-09 design-system foundation and representative page migration: completed and closed
- X-10 remaining primary-workspace consistency migration: completed and closed

Atlas Workspace Sprint A-04 consolidates workstation UX: shared workspace section headers, recommendation deduplication/grouping, filter reset consistency in dense tables, object-link continuity from estimate snapshot context, and terminology normalization for Products (Master Library).
Atlas Workspace Sprint X-02 refines project creation and identity workflows with deterministic Atlas Bid ID preview/allocation and explicit project identifier surfaces.
Sprint X-03 hardens onboarding and stakeholder workflows with a strict two-step create-then-upload path, shared organization directory linking, and deterministic pending-upload behavior.
Sprint K-02 extends Knowledge workspace operations with framework-backed Customer and Service workflows (create/list/archive/restore) aligned to deterministic knowledge-entity state.

- Status bar

The shell remains visible while page content changes.

Shell contract notes:
- top-header primary navigation order is Transactions, Projects, Knowledge, Reports, Settings
- Atlas remains the far-left Home action
- tenant-facing footer text is `©2026 Corsa Systems. All rights reserved.`
- header composition is one shared row; primary links collapse predictably at narrow widths instead of wrapping to a second row
- primary navigation now uses fixed-width buttons routed through shared Streamlit callbacks, keeping same-window navigation and bounded search behavior intact
- Settings tertiary actions wrap into deliberate rows so the shell remains readable at medium widths
- dense tables remain contained inside the content shell with internal scrollbars instead of page-level overflow

## Workspace Modes
Atlas now operates in two navigation modes:
- Application Workspace
- Project Workspace

Application Workspace is used for Home and cross-project operations.
Project Workspace is entered only after opening a specific project.

Home remains application-level.
Opening a project switches Atlas into project-specific navigation.

Primary navigation is header-based in both workspace modes.
Administration remains an internal route name only and appears publicly as Settings.
Home now shows deterministic Recent Projects instead of Recent Activity.
Atlas is the sole Home action.
The header uses a compact centered content width so it does not stretch edge-to-edge on large monitors.
Clear Search exits focused search mode and returns to the current page context without mutating an already-instantiated widget-owned session key.

Sprint X-13 refines navigation clarity and information architecture without changing workflow behavior.

- primary navigation remains global
- secondary navigation is contextual to the active workspace
- tertiary navigation is presented as task-oriented actions rather than page-name repetition
- development-only labels, diagnostic phrasing, and redundant explanatory copy are removed where they do not create direct user value
- Home is treated as an operational landing page centered on continue-working context, recent projects, action triage, notifications, and favorites
- Reports is treated as an output-oriented workspace organized around deliverables and readiness

W-02 defines the Universal Object contract layer only.

- no universal object workspace UI is introduced yet
- future object surfaces can consume shared identity, action, relationship, activity, and presentation contracts
- existing page layouts remain authoritative until a later workspace-migration sprint adopts the shared object shell

W-03 introduces the first Universal Object Workspace UI migration.

- the shared Object Workspace now renders supported objects through the W-02 contract and registry
- migrated scope includes Customer, Vendor, Manufacturer, Product, Service, Contact, Location, and Project object routes
- Drawing, Specification, and Equipment are supported in read-only object-workspace mode with direct open to authoritative engineering pages
- search and Working Set open supported objects in Object Workspace while preserving existing continuity and return behavior
- existing authoritative create/edit/archive/import/export workflows remain in their original domain pages

W-03 shared workspace components:
- object identity block with canonical identity/provenance fields
- context banner with one-click return behavior
- contract-driven primary action rendering including disabled-action reasons
- object-level tertiary view selector limited to supported views only
- deterministic relationship and activity presentation blocks with compatibility empty states

W-03 compatibility boundaries:
- no redesign of unrelated project or knowledge workflows
- unsupported object families continue authoritative legacy routes
- read-only object families retain authoritative engineering-page open actions

## Design-System Foundation (X-09)

X-09 introduces shared UI authority for the Streamlit shell:

- token authority lives in `atlas_core/ui/design_system.py`
- `_inject_styles` now consumes centralized stylesheet output rather than a large local CSS literal
- page helpers consume shared HTML primitives for metric cards, empty states, guided empty states, workspace context, and status badges

Representative migration scope (behavior-preserving only):

- Home
- Projects
- Knowledge
- Reports

Out of scope for X-09:

- any business-logic or persistence changes
- new workflow capabilities
- Epic E initiation

Remaining migration debt after X-09 closeout:

- project-workspace pages beyond Home/Projects/Knowledge/Reports still rely on legacy inline table/layout wrappers
- shared section, notice, badge, and responsive-control wrappers should continue rollout across lower-priority project-workspace surfaces

## Workspace Consistency and Information Density (X-10)

X-10 completes migration of remaining primary project-workspace pages onto shared X-09 design-system wrappers while preserving behavior.

Completed migration scope:

- Overview
- Documents
- BOM Review
- Scope & Risk
- Engineering Review
- Estimate
- Notebook
- Project Summary report surface refinements

Consistency improvements applied:

- shared workspace notice/context panels for major project pages
- normalized section-title hierarchy and spacing wrappers
- shared table wrapper usage for data-dense sections
- shared responsive control-column helpers for action/filter groups

X-10 scope boundaries:

- behavior-preserving UI hardening only
- no routing/business-logic/workflow-contract changes
- no Epic E start

Remaining UX debt after X-10:

- lower-priority advanced/object-detail pages still need full shared-wrapper migration
- notebook entry-point discoverability should be further improved from primary workflow pages

## Typography System and Visual Polish (X-11)

X-11 completes official typography and hierarchy hardening across shared shell surfaces while preserving behavior.

Completed X-11 typography implementation:

- official font families are centralized in shared design-system tokens:
   - Display: Inria Serif (500/600/700)
   - Interface: Fira Sans (400/500/600)
   - Mono: existing mono stack for IDs/hashes/code surfaces
- shared typography scale now defines explicit tokens for Display XL/L, Heading 1/2/3, Body Large/Body/Small, Caption, Label, and Value
- line-height and letter-spacing tokens are centralized to keep heading/body rhythm deterministic across pages
- single authoritative font loading path is centralized in `atlas_core/ui/design_system.py`

Visual polish refinements in X-11 (behavior-preserving):

- stronger heading and section hierarchy consistency
- improved label, badge, and table-header readability in dense review surfaces
- refined control/button/tab type sizing and weights for visual clarity
- no workflow, routing, data, or business-logic changes

Enterprise font-hosting guidance:

- replace centralized Google Fonts import with self-hosted equivalents in the same stylesheet location
- keep token names unchanged so all consuming surfaces remain behaviorally stable

## Epic X Closeout Validation

Validation-only closeout pass completed for Epic X.

Engineering Notebook entry path:

- normal project workflow now includes Open Notebook from Overview Guided Project Review actions
- return path validated by navigating back to Overview and reopening Notebook while preserving project context

Notebook validation results:

- Notebook open from normal project flow: pass
- Notebook list and empty states: pass
- entry filtering (search/date): pass
- linked-object navigation: pass
- decision-log view (Engineering Decisions tab): pass
- return navigation: pass
- project context preservation: pass
- medium-width behavior: pass (no regressions observed during validation)

Closeout note:

- linked-object navigation reliability for generated entries was corrected by stabilizing linked-object action keys; no Notebook feature expansion was introduced

## Repository-Backed Open Existing Project
Open Existing Project now defaults to repository-backed project selection.

Primary behavior:
- searchable/sortable/filterable imported project list
- includes customer, lifecycle stage, status, last opened, last modified, document count, and review status
- supports archived visibility and pinning
- opens selected project directly into Project Workspace

Advanced behavior:
- an advanced expander provides Open from local path for development/recovery use only
- manual path entry is no longer the default workflow

## Sprint L-01 Lifecycle UI

L-01 adds lifecycle-engine awareness to existing project-facing GUI surfaces without introducing downstream execution workflows.

Current GUI behavior:
- Create New Project now uses canonical lifecycle stage options instead of only legacy project statuses
- Project Settings now shows lifecycle-engine summary context, applicable-stage sequence, available transitions, and recent lifecycle history
- lifecycle stage changes in Project Settings require a transition reason when the selected stage changes
- Project Object Workspace can display lifecycle context through shared universal object projection paths

Still deferred:
- dedicated lifecycle workspace pages for procurement, installation, commissioning, service, or asset-lifecycle operations

## Sprint L-02 Lifecycle Dashboard

L-02 extends the shared Project Object Workspace rather than adding a new page.

Current GUI behavior:
- Project Object Workspace now includes a `Lifecycle` tertiary view for project records
- lifecycle is visualized as a horizontal progress timeline with distinct complete, active, available, blocked, skipped, and archived states
- default view remains concise and uses progressive disclosure for diagnostics, requirements, history, and related-object detail
- lifecycle dashboard summary surfaces current stage, stage status, responsible role, next action, completed stages, blocked stages, upcoming stages, and available transitions

Explicit non-goals:
- no dedicated procurement, installation, commissioning, service, or asset-management pages
- no automatic lifecycle advancement or workflow automation

## Projects Library
Projects is the primary project library.

Primary actions:
- Open Project
- Create New Project
- Import Project Package
- Archive/Unarchive Project
- Duplicate Project
- Delete Project with explicit confirmation

Project persistence remains repository-backed through ProjectWorkspaceService.

Project identity display (X-02):
- Atlas Bid ID is shown as the primary repository identifier in project selectors and list tables.
- Client Project Number and Internal Project Number are shown as explicit secondary identifiers.
- Search across project libraries includes Atlas Bid ID, client project number, and internal project number.

## Create New Project (X-03)

Create New Project behavior is optimized for bid workspace startup:
- Atlas Bid ID is generated deterministically and shown as non-consuming preview.
- Manual Project ID entry is removed from primary workflow.
- Required inputs: Project Name and Owner/Client.
- Optional identity/detail inputs remain available through expandable details.
- Primary action label: Create Bid Workspace.

Create workflow behavior in X-03:
- Step 1 is metadata-first Quick Start only.
- Document uploader is not shown before workspace creation.
- Owner / Client lookup-first selection is available before create.
- Primary action remains Create Bid Workspace.
- Successful create routes directly to Documents (Step 2).

Step 2 upload behavior (Documents):
- Supported onboarding formats: PDF, CSV, XLS, XLSX, DOC, DOCX, ZIP, JPG, JPEG.
- Selections append to a pending upload queue across multiple chooser interactions.
- Pending queue uses deterministic dedupe identity (normalized filename + size + source hash).
- Users can remove selected pending files or clear all pending files.
- Upload execution is explicit through Upload Pending Files.
- Partial success is deterministic: accepted files import, rejected files remain visible via diagnostics/warnings.
- Failed/rejected files can be retried through subsequent pending selections.

ZIP handling behavior:
- Archive inspection occurs before extraction.
- Unsafe paths, encrypted entries, duplicate entries, and system artifacts are rejected.
- Entry count and expansion-size limits are enforced.
- Nested archive depth is bounded.
- Contained relative paths are preserved in intake-source metadata.

## Project Settings Identity Workflow (X-03)

Project Settings now includes controlled metadata editing for identity fields:
- Atlas Bid ID (read-only)
- Client Project Number (editable)
- Internal Project Number (lifecycle-stage-aware editable behavior)
- Lifecycle stage updates persisted through project identity metadata service path

If lifecycle stage is awarded/execution and internal project number is missing, deterministic advisory messaging is shown.

## Stakeholder Directory Workflow (X-03)

Project Settings includes stakeholder linkage backed by shared Organizations:
- lookup existing organizations by canonical name or aliases
- create organization inline when no existing match is suitable
- duplicate warning requires explicit confirmation before creating a likely duplicate
- link one organization across multiple project roles
- preserve legacy free-text stakeholder metadata for compatibility while new links are added

## Knowledge Workspace Scope
Knowledge is application-wide and cross-project.

Knowledge landing sections:
- Customers
- Contacts
- Locations
- Vendors
- Manufacturers
- Products
- Services
- Price Lists
- Imports
- Assemblies

Knowledge page excludes project-specific BOM/drawing/risk views.

## Active Project Identity Pattern
Project Workspace uses a compact identity header instead of a wide metadata table.

Primary identity:
- project name
- customer
- lifecycle and status badges

Secondary identity:
- last analysis timestamp
- confidence
- recommended next action control

Project context header is shared and rendered once by the shell for all Project Workspace pages.
Fields are restricted to:
- project name
- customer
- lifecycle stage
- current status
- last analysis
- confidence
- recommended next action

## Breadcrumb Rules
Breadcrumbs are concise and do not repeat workspace labels.

Examples:
- Atlas / Projects
- Atlas / Knowledge
- Atlas / Projects / MAW Music Education Center / Overview
- Atlas / Projects / MAW Music Education Center / Drawings


System metadata (version/commit/stage/status) remains available in the status bar.

- Drag your project here
- Supported formats: PDF, DOCX, DOC, XLSX, XLS, CSV, JPG, JPEG, PNG, TIFF, TXT, RTF, JSON, ZIP
Files are automatically classified into:
- drawings/
- unsupported/

After classification, Atlas runs deterministic intake, saves the workspace locally, and then executes the existing project review pipeline.

## Primary Workflow
The primary user workflow is:


Primary workspace navigation includes:
Project-management pages remain available separately for create/open/manage tasks.

- Relationship Explorer
- Resolver internals
- Detailed history and evidence drill-down
- Experimental or low-level engineering workspaces

- Data Source label shows `Seed fixture fallback` for fallback mode
- Fallback mode explicitly warns that curated fixture data is in use
- Extraction warnings are shown

Place the full MAW package under:
- examples/music_academy_of_the_west/
- examples/music_academy_of_the_west/metadata.json
- examples/music_academy_of_the_west/drawings/
- examples/music_academy_of_the_west/specifications/
- examples/music_academy_of_the_west/schedules/
- examples/music_academy_of_the_west/addenda/
- examples/music_academy_of_the_west/images/

If expected folders are missing, Atlas shows a warning and still attempts deterministic intake from available files.

## Run Instructions
1. Install GUI dependency:
   - pip install -e .[gui]
2. Launch app:
   - streamlit run apps/phase2_review_app.py
3. Open `Reference Project` to verify MAW source mode.

## Home Content
Home is a simple landing page that provides immediate access to:
- Create New Project
- Open Existing Project
- Manage Projects

Application navigation groups:
- Home
- Projects
- Knowledge
- Reports
- Administration

Home also shows:
- Continue Working
- Recent Projects
- Action Center
- Notifications
- Favorites

Project-specific engineering pages are not shown while no project is open.

Sprint X-04 home/search refinement notes:
- Home is the only user-facing landing-page term.
- Mission Control is retained only as an internal compatibility route key.
- Global search submits directly on Enter from the header input.
- Empty/whitespace-only search does not execute and does not render results.
- Search results are grouped by user-facing object type with deterministic preferred ordering.
- Unknown object types are rendered after preferred groups in alphabetical order.
- Removed Home sections: Application Areas, Portfolio Signals, Upcoming Timeline, Projects Requiring Attention, and Workspace Recommendations.
- Action Center is limited to critical/high-priority deduplicated actions.
- Home remains operational with compact Continue Working, Recent Projects, Action Center, Notifications, and Favorites sections.

Transactions alpha navigation posture:

- active families: Estimates, Sales Orders, Return Orders, Invoices, Credit Memos
- Change Orders remain a convention/filter inside Sales Orders and Return Orders (not a standalone secondary family)
- deferred families are visibly deferred/disabled: Purchase Orders, Vendor Quotes, Receiving, Vendor Bills

Settings alpha visibility posture:

- tenant-visible Settings avoids environment/build/test diagnostics
- platform diagnostics and alpha operations controls remain in Platform Management surfaces

## Project Workspace Navigation
When a project is opened, Atlas switches to project navigation.

Secondary navigation changes with workspace context:

- no active project: project-library navigation for create/open/manage flows
- active project: project-workspace navigation for review, detail, estimate, notebook, reports, and settings

Tertiary navigation is action-oriented and contextual.
It should present what the user can do in the current area, such as Browse, Add, Edit, Relationships, Import, Export, Summary, Decisions, Timeline, Equipment, or Labor.
It should not merely mirror page titles.

Project:
- Overview
- Documents
- BOM Review
- Scope & Risk
- Engineering Review
- Estimate
- Notebook
- Reports

Estimate Workspace (Sprint 8 deterministic foundation):
- Overview
- Equipment Cost
- Labor
- Accessories
- Freight
- General Conditions
- Engineering Allowances
- Project Summary
- Estimate Confidence

Estimate Workspace behavior:
- deterministic estimate lines are generated from reviewed engineering objects
- each estimate line preserves source object traceability and source references
- product resolution state is visible on every line (exact/approved substitute/preferred alternate/generic allowance/unknown)
- pricing status and labor status are visible on every line
- unknown products are flagged and remain no-pricing in deterministic mode
- line navigation supports Equipment, Specification, Drawing, Relationships, and Evidence routes
- object detail headers include Open Estimate Workspace for source-to-estimate return

D-03 Estimate Workspace additions:
- Assembly insertion workflow with explicit preview and accept actions
- generated assembly parent/product/labor line rendering
- provenance inspection and labor snapshot inspection
- assembly refresh preview and apply controls for product costs and labor rates

D-03 Knowledge workspace additions:
- Assembly Library tab with list/search/detail workflows
- version lifecycle actions (validate/activate/supersede/archive)
- component editor with product/nested/labor component types
- expansion/material/labor preview panels

D-03 Mission Control additions:
- recommendation rows now include estimate-engine D-03 readiness recommendations

A-05 workflow refinement additions:
- Mission Control recommendations include quick destination navigation controls
- recommendation summary counts reduce recommendation-fatigue during triage
- Assembly Library component entry validates required references before submit
- Estimate D-03 refresh preview includes explicit dismiss action before apply

A-05 deferred UX debt (non-blocking):
- very large deterministic recommendation lists still render as a single table
- table-level pagination patterns are not yet unified across all workspace pages

X-01 pilot-readiness refinements:
- Mission Control recommendation guidance now explains why each selected recommendation appears and what action to take.
- Assembly Library now surfaces validation results inline for the selected assembly version.
- Assembly Library persistence writes use shared helper logic to reduce repeated state-write code paths.

X-01 remaining UX debt (non-blocking):
- recommendation guidance remains table-based and could be further simplified into compact cards
- some high-density engineering evidence tables still require substantial scrolling on smaller displays

Price List Library (C-02) now includes PDF import review controls for:
- PDF source inspection
- page list/range selection
- table-candidate selection
- header-row confirmation
- column mapping confirmation
- raw extraction preview and transformed draft preview
- draft corrections before finalization
- diagnostics review with error/warning/informational severities

PDF finalization follows the same immutable draft -> validated -> finalized lifecycle used by CSV/XLSX imports.

Project Details:
- Drawings
- Specifications
- Equipment
- Schedules
- Addenda
- Evidence
- Timeline
- Relationships

Object navigation behavior in Project Workspace:
- object pages expose shared object headers with identity, project, status, relationship counts, and quick actions
- object pages expose deterministic `References` and `Referenced By` sections for cross-object movement
- breadcrumbs include selected object context when an object is active
- global search groups object results by type and supports open and pin/unpin actions
- overview surfaces Recently Viewed and Pinned object lists for fast context return
- Relationship Explorer provides relationship-type and connected-object-type filters with connected object cards

Object detail scaffolding:
- Equipment, Drawings, and Specifications use a shared section pattern for metadata, references/referenced-by, warnings/evidence, and recommended actions
- object-specific tabs remain configurable and do not force unrelated fields

Global Search behavior:
- persistent header search control visible in application and project workspaces
- search scope includes application objects (projects, manufacturers, vendors, customers, products, price lists) and project objects (equipment, drawings, specifications, systems, rooms, risks/findings, RFIs, evidence, notebook entries, relationships)
- deterministic ranking: exact identifier, exact name, exact model/drawing/spec number, prefix, then partial text
- when a project is open, project-scoped matches rank ahead of application-scoped partial matches
- results are grouped by object type and display name/type/secondary label/project/status/confidence/warnings
- selecting a result opens the target object or workspace route and preserves object context for breadcrumbs
- keyboard hint is always visible and supports Cmd+K on macOS / Ctrl+K on Windows/Linux where available; Esc closes active search panel

Search memory:
- recent search queries are persisted locally in workspace state
- recently opened search results are persisted locally in workspace state
- users can clear recent query and recent-opened history

Working Set behavior:
- replaces pinned object language with Working Set
- purpose statement: Keep important project objects close while you review the project.
- available in Project Overview, Global Search panel, object detail headers, and compact header history popover
- supports add/remove/open/clear and lightweight reordering controls

Navigation behavior:
- navigation rendering is configuration-driven using shared group definitions
- supports application-level and project-level navigation from the same renderer
- responsive navigation remains a compact top header shell with bounded content width
- disabled future lifecycle sections are visible but non-interactive

Status color rules:
- red is reserved for critical, blocked, failed, or destructive contexts
- normal actions and navigation use Atlas primary accent
- green indicates healthy/complete
- amber indicates needs review/attention
- gray indicates unknown/inactive context

Project Settings:
- Project Metadata
- Repository
- Workspace Settings

## Responsive Navigation
- Desktop: compact top-header navigation with bounded shell width
- Tablet: compact top-header navigation with bounded shell width
- Mobile: compact top-header navigation with bounded shell width

The current page, selected project, and breadcrumb remain visible in all modes.

Context behavior:
- Primary workflow pages emphasize summary conclusions first.
- Evidence and traceability remain available through drill-down pages.
- Desktop Project Workspace uses two columns only: navigation + main content.
- No persistent third context column is reserved.
- Object detail is surfaced inline with tabs/expanders/sectioned detail areas.

Responsive behavior:
- Desktop: top-header navigation with centered/bounded working content.
- Tablet: top-header navigation with centered/bounded working content.
- Mobile: top-header navigation with centered/bounded working content.

## Upload Flow (X-03)
1. Create workspace from Quick Start (Step 1).
2. Open Documents (automatic route after create).
3. Add first file selection.
4. Add second and later selections; pending queue accumulates rather than replacing prior pending files.
5. Review deterministic diagnostics/warnings and pending file list.
6. Remove selected pending files or clear all if needed.
7. Click Upload Pending Files for explicit intake execution.
8. Review imported-file status and continue into BOM Review, Scope & Risk, Engineering Review, and Reports.

## Deterministic Extraction Rules
- PDF: extract embedded text.
- PDF (optional local OCR): when enabled, Atlas attempts local OCR on PDF pages without embedded text.
- DOCX: extract paragraphs/headings/tables from document XML text runs.
- DOC: best-effort decode; warning requests DOCX/PDF for reliable extraction.
- XLSX/CSV: extract schedule-style rows.
- XLS: unsupported in deterministic parser; warning requests XLSX/CSV.
- Images (JPG/JPEG/PNG/TIFF): optional local OCR can be attempted; otherwise warning emitted when no extractable text is available.
- ZIP: automatically unpacked recursively and classified.

## Optional Local OCR
- Local OCR is optional and disabled by default.
- Quality gate and test runs do not require system OCR binaries.
- OCR-derived text is explicitly marked in diagnostics as `ocr_derived_text`.
- OCR failures are explicitly marked as `ocr_failed`.
- No cloud OCR or LLM interpretation is used.

## Snapshot Mode
For existing local intake snapshots, the sidebar includes `Use Existing Intake Snapshot` in uploaded mode.
This allows browsing `intake_snapshot.json` files already generated under local outputs/examples folders.

## Project Summary
Project Summary shows:
- project name
- customer
- project type
- document count
- analysis status
- BOM item count
- unresolved scope issue count
- high-risk issue count
- documents requiring OCR
- recommended next action

It also exposes one prominent action button:
- Run Project Analysis

## Overview
Overview displays current project health at a glance:
- a prominent Recommended Next Action block at top of page
- primary navigation actions for Documents, BOM Review, Scope & Risk, and Engineering Review
- critical issues table first (critical/high scope findings)
- project metadata and engineering summary after action/risk context
- recent activity and import summary for situational awareness

Hierarchy order is fixed:
1. recommended next action
2. primary actions
3. critical issues
4. project summary and metrics
5. recent activity and supporting detail

This keeps the first screen action-oriented rather than report-oriented.

## Guided Empty States
Workflow pages now use guided empty states instead of generic placeholders.

Each empty state explicitly answers:
- why data is empty
- what action will populate it
- where to go next

This pattern is used in Overview activity, Documents filters, BOM Review, Scope & Risk, and Engineering Review.

Sprint 4 extends guided empty states to:
- no projects imported
- no knowledge records
- no price lists
- no manufacturer/vendor/customer data
- no selected drawing/specification relationships

## Workflow Page Density
Primary workflow pages now default to summary views first and keep deep detail in optional drill-down sections.

- BOM Review:
   - priority summary appears above detailed line exploration
   - line evidence moved into a collapsed drill-down panel
- Scope & Risk:
   - priority risks (critical/high) are shown first
   - lower-priority categories are collapsed into drill-down
   - finding-level full detail is collapsed by default
- Engineering Review:
   - top-level "What Should Happen Next" action is promoted with direct page actions
   - full narrative sections remain available below

## Guided Project Review (Sprint 3)
Project Workspace now guides review as an ordered, non-blocking sequence:

1. Review Documents
2. Review BOM
3. Review Scope and Risk
4. Review Engineering Findings
5. Review Estimate Coverage
6. Generate Summary Report

Users can still navigate freely. Atlas does not enforce a rigid wizard.

Progress behavior:
- Overview and Reports display guided-step progress with status and detail.
- Each workflow page includes a local "mark reviewed" transition panel.
- Transition panel shows current step status, next recommended action, and a direct continue link.

## Review Status Model
Each guided step uses one status:
- not started
- ready
- needs review
- blocked
- complete

Status is derived from existing project data and current review completion markers.

Examples:
- Documents can be blocked when all files are OCR-required.
- BOM can be needs review when unresolved/conflicting lines remain.
- Scope and Risk can be needs review when critical gaps/ambiguities/RFIs are open.
- Summary Report is blocked until upstream analysis/review prerequisites are present.

## Project Review Checklist
Overview and Reports include a deterministic checklist:
- all documents processed
- OCR-required documents identified
- BOM reviewed
- unresolved BOM items reviewed
- critical scope gaps reviewed
- responsibility ambiguities reviewed
- high-risk engineering findings reviewed
- recommended RFIs reviewed
- estimate coverage reviewed
- summary report generated

Checklist status is traceable to current workspace data and review markers.

## Reports Center (Project Workspace)
Inside project Reports, navigation now explicitly includes:
- Project Summary
- Estimator Brief
- BOM Export
- Scope and Risk Export
- Engineering Review Export

## Project Summary Report
Project Summary is an operational summary report for the active organization, not a separate customer-document artifact.

## Transactions GUI: T-05 Amendment Versioning and Export Controls

Transactions Estimates and Sales Orders now expose tertiary actions for:
- Duplicate
- Create Revision
- Revision History
- Archive
- Restore
- Export PDF

Estimate-specific export presentations:
- Internal Estimate PDF
- Customer Estimate PDF

Sales-order export presentation:
- Sales Order PDF

Export workflows include non-executing future email metadata capture (provider/recipient/template/revision) and do not send email in this sprint.

## Transactions GUI: T-06 Return Orders and Credit Memos

Transactions now includes secondary sections for Return Orders and Credit Memos.

Return Order actions:
- Add
- Browse
- Edit
- Lines
- Approvals
- Receiving
- Inspection
- Process
- Activity
- Export

Credit Memo actions:
- Browse
- Details
- Related Documents
- Sync Status
- Activity
- Export PDF

## Transactions GUI: T-07 Line Presentation Controls

Line-based transaction views now expose presentation controls for:
- group creation and subtotal visibility
- comment and blank spacer rows
- manual order updates through explicit line-order lists
- preview sort, apply sort, and restore manual order
- visible-column selection for PDF output

Default sections:
- Project Overview
- Documents Reviewed
- BOM Summary
- Missing or Incomplete BOM Detail
- Scope Gaps
- Responsibility Risks
- Engineering Risks
- Recommended RFIs
- Estimate Coverage
- Recommended Next Actions
- Known Limitations

Concise-by-default behavior:
- Main report remains compact.
- Expanded detail is available via drill-down sections for evidence, long issue lists, BOM exceptions, and confidence calculations.

Export behavior:
- Project Summary export supports deterministic Markdown, JSON, and HTML.
- BOM Export supports deterministic CSV and JSON.
- Scope and Risk Export supports deterministic Markdown and JSON.
- Engineering Review Export supports deterministic Markdown, JSON, and HTML.

## Executive Summary
Executive Summary consolidates:
- overall health
- critical risks
- high-priority RFIs
- labor confidence
- scope gaps
- documents requiring OCR
- recommended next actions

## Interactive Engineering Review (Sprint 6)
Sprint 6 transforms the workspace from report viewing into object exploration.

First-class engineering objects:
- Drawings
- Specifications
- Equipment
- Systems
- RFIs
- Evidence

Object workspaces now expose properties plus linked relationships so users can traverse engineering context without leaving Atlas.

## Drawing Workspace
Drawing objects display:
- drawing number
- title
- revision
- issue date
- discipline
- referenced equipment
- referenced specifications
- referenced systems
- referenced RFIs
- referenced evidence
- extraction quality
- OCR status
- warnings

If a source PDF path is available, the Drawing Workspace shows preview metadata and source path; otherwise a preview placeholder is shown.

## Specification Workspace
Specification objects display:
- division
- section
- title
- referenced drawings
- referenced equipment
- referenced systems
- referenced RFIs
- referenced evidence
- cross references
- extraction confidence

## Equipment Object Workspace
Equipment Workspace is object-first and built from canonical BOM lines plus existing scope/risk/evidence data.

Structure:
- Search and Filters
- Equipment Summary
- Equipment List
- Selected Equipment Detail
- Related Objects
- Evidence and Warnings
- Recommended Actions

Filters:
- manufacturer
- system
- room
- completeness
- confidence
- responsibility
- lifecycle status
- items requiring review

Summary metrics:
- total equipment items
- complete items
- incomplete items
- unresolved items
- quantity conflicts
- missing manufacturer
- missing model
- discontinued or legacy references
- items without known cost
- items requiring review

Selected Equipment Detail sections:
- Overview
- Engineering
- References
- Scope and Risk
- Pricing
- Evidence

Recommended actions are deterministic from current object state and include:
- priority
- reason
- destination
- affected source references

## Systems Workspace
Systems Workspace includes:
- Audio
- Video
- Control
- Network
- Projection
- Lighting
- Assistive Listening
- Intercom
- Paging

Per-system metrics:
- equipment count
- drawing count
- specification count
- RFI count
- readiness
- labor
- confidence

## Evidence Workspace
Evidence is grouped by:
- Drawings
- Specifications
- Schedules
- Images
- Notes
- Addenda

Each evidence row displays:
- source file
- page
- sheet
- confidence
- referenced objects or excerpt

## Object Navigation
Atlas object navigation supports relationship-driven traversal.

Examples:
- equipment → drawings/specifications/systems/RFIs
- specification → drawings/equipment/systems/evidence
- drawing → equipment/specifications/systems/evidence/RFIs

BOM integration:
- BOM Review keeps project-wide reconciliation behavior
- selected BOM lines now include Open Equipment Detail action
- Open Equipment Detail navigates to Equipment Workspace with the selected object

Drawing and Specification integration:
- Drawing Workspace shows related equipment as human-readable object labels
- Specification Workspace shows related equipment as human-readable object labels
- related equipment links open Equipment Workspace and preserve origin context where practical

Context panel quick navigation allows one-click movement between related workspaces.

## Relationship Browsing
Context panel now shows:
- properties
- relationships
- evidence
- warnings
- related objects
- quick navigation

This allows Atlas to behave like a practical project knowledge graph while preserving deterministic Phase 2 review outputs.

## Global Search
Global project search now indexes:
- drawings
- specifications
- equipment
- systems
- rooms
- manufacturers
- models
- RFIs
- evidence

Search results include object type and subtitle metadata.
Results can be navigated with keyboard arrows via selector controls and opened directly into the corresponding workspace.

## Atlas Knowledge Graph (Sprint 7)
Atlas now builds a deterministic in-memory knowledge graph for each active project workspace.

Supported node types:
- Project
- Drawing
- Specification
- Equipment
- System
- Room
- Area
- Manufacturer
- Product
- Evidence
- Engineering Assumption
- RFI Candidate
- Labor Estimate
- Revision
- Document

Deterministic relationship examples include:
- Drawing to Equipment
- Equipment to Specification
- Equipment to System
- System to Room
- Specification to Drawing
- Drawing to Evidence
- RFI to Equipment
- Evidence to Assumption

No AI-generated relationships are used.

## Relationship Explorer
A dedicated Relationship Explorer page allows object-centric relationship navigation.

Features:
- object selection
- incoming relationships
- outgoing relationships
- relationship type
- confidence
- source evidence
- recursive expansion depth

## Relationship Visualization
Atlas includes a simple deterministic node-link relationship view.

Visualization behavior:
- selected object is the graph focus
- connected objects are displayed with labels
- relationship labels are shown between nodes
- node navigation is available via connected-node selection controls

## Object Detail Pages
Major object detail pages are now available:
- Project Detail
- Drawing Detail
- Specification Detail
- Equipment Detail
- System Detail
- Room Detail
- Manufacturer Detail
- Evidence Detail

Each page displays:
- properties
- relationships
- warnings
- evidence
- timeline

Each page includes traceability details and quick navigation to source evidence/originating documents.

## Timeline
Project Timeline page displays deterministic project events:
- project intake
- document imports
- review runs
- revision comparisons
- readiness updates
- estimator brief generation

Future events remain disabled in local deterministic mode.

## Metadata Inspector
Metadata Inspector is available as both a dedicated page and context panel section.

For selected objects, it displays:
- source file
- source page
- sheet number
- specification section
- extraction confidence
- creation timestamp
- last update
- relationship count
- evidence count

## Enhanced Search (Sprint 7)
Global search now supports:
- type filters
- manufacturer/model/drawing/specification/room/system/evidence lookups
- relationship search mode
- ranking with exact matches first

Search results preserve keyboard navigation behavior and cross-page navigation into object-focused views.

## Engineering Intelligence (Sprint 8)
Atlas now provides deterministic engineering decision support.

Engineering Intelligence page includes:
- top engineering insights
- critical risks
- coordination issues
- high-risk systems
- most referenced drawings
- most referenced specifications
- top equipment risks
- highest confidence recommendations

Insight controls:
- severity filters
- category filters
- sorting
- grouping by Severity, Category, System, Drawing, Specification

## Insight Engine
Engineering Intelligence is powered by deterministic outputs from:
- BidPackageReview
- Readiness
- Estimator Brief
- RFI Candidates
- Labor Estimate
- Revision Comparison
- Knowledge Graph

Each insight includes:
- insight_id
- category
- severity
- confidence
- title
- description
- recommended_action
- supporting_objects
- evidence_refs
- created_by_engine_version

## Project Health Model
Project Health is separate from readiness and scores engineering package quality from 0 to 100.

Weighted categories:
- engineering completeness
- package consistency
- cross-object coordination
- estimating confidence
- revision stability

The dashboard shows weighted rationale for score traceability.

## Systems Health
Systems Workspace now includes deterministic system health metrics:
- health score
- confidence
- equipment completeness
- specification coverage
- drawing coverage
- outstanding RFIs
- outstanding assumptions
- labor confidence
- warnings

## Recommendations and Traceability
Recommendations are deterministic and include explicit traceability back to source evidence and supporting objects.

The interface is designed to answer:
- what should be reviewed next
- why it matters
- where the observation came from

## Project Files Explorer
Project Files includes folder-based exploration:
- Drawings
- Specifications
- Schedules
- Addenda
- Images
- Other Documents

Per-file rows include:
- filename
- revision
- status
- pages
- references
- warning count

Explorer controls:
- sorting
- status filtering
- search
- folder selection

Selecting a file updates the Context Panel.

## Context Panel
The right panel is context-sensitive.

Examples:
- drawing/file selection: metadata, related equipment, RFIs, evidence hints
- specification selection: linked equipment and systems
- equipment selection: drawing/spec references, manufacturer, risk context

Drawing context includes:
- metadata
- equipment
- specifications
- RFIs
- revision history placeholder
- evidence references

Specification context includes:
- referenced drawings
- equipment
- systems
- related RFIs

Equipment context includes:
- manufacturer
- system
- drawing/specification references
- risk context

## Status Bar
The status bar is always visible and shows:
- current project
- lifecycle stage
- last intake
- last review timestamp
- Atlas version
- git commit (development)

## Notes
- The GUI reads deterministic outputs from existing services and sample data.
- The app does not mutate project data.
- Scanned/image-only PDFs can produce warnings when no embedded text is extractable.
- Atlas does not fabricate sheet/spec/equipment extraction when text is unavailable.
- Lifecycle modules beyond Phase 2 remain visible as disabled `Coming Soon` navigation only.

## Extraction Diagnostics
Atlas Intake surfaces the following diagnostics in the Import Summary:
- total files
- total pages (where page counts are available)
- pages with embedded text
- pages with OCR-derived text
- pages without embedded text
- documents requiring OCR
- extraction warning count

When `documents requiring OCR` is non-zero, Atlas displays guidance that OCR is needed before text-rich project intelligence can be extracted.
Per-file diagnostics include extraction mode to distinguish embedded text extraction, OCR-derived extraction, and OCR failures.

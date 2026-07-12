# Atlas

## Purpose
Provide a local project-analysis workspace for estimators and reviewers to create or open a project, upload documents, run analysis, review BOM and risk conclusions, and export a concise internal report.

This interface is local-only:
- Local file-backed project repository persistence under `AtlasProjects/`.
- No procurement/RFQ/submittal/invoice/execution/closeout/vendor communication workflows.

Atlas Workspace v1 (Sprint 8) launches into a persistent interactive engineering shell.

Atlas Workspace UI Sprint 4 adds repository-first project access, a scoped application-wide Knowledge workspace, a compact active-project identity header, and a strict two-column Project Workspace layout.

Atlas Workspace UI Sprint 6 adds an object navigation layer that connects equipment, drawings, specifications, systems, rooms, risks, RFIs, and evidence through shared object headers, references/referenced-by groups, relationship explorer filters, and quick cross-object navigation actions.

Atlas Workspace UI Sprint 7 adds persistent Global Object Search and a project-scoped Working Set for active review objects.

Atlas Workspace Sprint 7.5 performs UI repair and runtime-state isolation: shared project context header rendering, configuration-driven navigation (including disabled future lifecycle sections), shared object detail section scaffolding, breadcrumb normalization, meaningful empty-state messaging, and mutable runtime project storage outside immutable repository fixtures.

Atlas Workspace Sprint A-04 consolidates workstation UX: shared workspace section headers, recommendation deduplication/grouping, filter reset consistency in dense tables, object-link continuity from estimate snapshot context, and terminology normalization for Products (Master Library).

- Status bar

The shell remains visible while page content changes.

## Workspace Modes
Atlas now operates in two navigation modes:
- Application Workspace
- Project Workspace

Application Workspace is used for Mission Control and cross-project operations.
Project Workspace is entered only after opening a specific project.

Mission Control remains application-level.
Opening a project switches Atlas into project-specific navigation.

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

## Knowledge Workspace Scope
Knowledge is application-wide and cross-project.

Knowledge landing sections:
- Summary
- Manufacturers
- Vendors
- Customers
- Products
- Price Lists
- Imports

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

## Mission Control Content
Mission Control is now a simple landing page that explains the workflow and provides immediate access to:
- Create New Project
- Open Existing Project
- Manage Projects

Application navigation groups:
- Mission Control
- Projects
- Knowledge
- Reports
- Administration

Mission Control also shows the active project snapshot:
- project name
- customer
- project type
- analysis status
- recommended next action

Project-specific engineering pages are not shown while no project is open.

## Project Workspace Navigation
When a project is opened, Atlas switches to project navigation.

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
- responsive navigation remains Desktop sidebar, Tablet popover, and Mobile drawer-style popover
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
- Desktop: persistent sidebar
- Tablet: collapsible sidebar with navigation popover
- Mobile: drawer-style navigation popover

The current page, selected project, and breadcrumb remain visible in all modes.

Context behavior:
- Primary workflow pages emphasize summary conclusions first.
- Evidence and traceability remain available through drill-down pages.
- Desktop Project Workspace uses two columns only: navigation + main content.
- No persistent third context column is reserved.
- Object detail is surfaced inline with tabs/expanders/sectioned detail areas.

Responsive behavior:
- Desktop: persistent left navigation and full-width working content.
- Tablet: collapsible navigation popover and inline detail sections.
- Mobile: drawer-style navigation and stacked list/detail flow.

## Upload Flow
1. Open `Documents`.
2. Drag files into Atlas Intake (single file, many files, or ZIP).
3. Click `Run Project Analysis`.
4. Review import summary, warnings, and document status.
5. Continue into BOM Review, Scope & Risk, Engineering Review, and Reports.

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
Project Summary is an internal engineering report (not a proposal).

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

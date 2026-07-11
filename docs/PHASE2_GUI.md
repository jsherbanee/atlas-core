# Atlas

## Purpose
Provide a local project-analysis workspace for estimators and reviewers to create or open a project, upload documents, run analysis, review BOM and risk conclusions, and export a concise internal report.

This interface is local-only:
- Local file-backed project repository persistence under `AtlasProjects/`.
- No procurement/RFQ/submittal/invoice/execution/closeout/vendor communication workflows.

Atlas Workspace v1 (Sprint 8) launches into a persistent interactive engineering shell.

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

Project Details:
- Drawings
- Specifications
- Schedules
- Addenda
- Evidence
- Timeline
- Relationships

Project Settings:
- Project Metadata
- Repository
- Workspace Settings

## Responsive Navigation
- Desktop: persistent sidebar
- Tablet: collapsible sidebar with navigation popover
- Mobile: drawer-style navigation popover

The current page, selected project, and breadcrumb remain visible in all modes.

Context panel behavior:
- Primary workflow pages emphasize summary conclusions first.
- Evidence and traceability remain available through drill-down pages instead of appearing by default.
- Advanced pages continue to expose lower-level context and diagnostics when needed.
- Desktop now uses a conditional context column: it appears only when a specific object/evidence selection is active.
- Workflow pages default to two-column emphasis (navigation + main work area) unless context drill-down is requested.

Responsive behavior:
- Desktop: persistent navigation with summary-first workflow pages.
- Tablet and mobile: navigation collapses to popover/hamburger.

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

## Equipment Browser
Equipment Browser supports:
- search
- sorting
- filtering
- grouping

Equipment attributes include:
- manufacturer
- model
- description
- system
- room
- drawing references
- specification references
- current status
- confidence
- potential RFIs

Grouping options:
- System
- Manufacturer
- Room
- Discipline

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

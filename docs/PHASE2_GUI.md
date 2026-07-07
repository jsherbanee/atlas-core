# Atlas

## Purpose
Provide a local project-centric workspace shell for estimators to run Atlas Intake and inspect deterministic project review outputs.

This interface is local-only:
- No authentication.
- No cloud persistence.
- Local file-backed workspace persistence under `outputs/project_workspaces/`.
- No procurement/RFQ/submittal/invoice/execution/closeout/vendor communication workflows.

Atlas Workspace v1 (Sprint 6) launches into a persistent interactive engineering shell.

Shell layout:
- Header
- Sidebar navigation
- Main content
- Context panel
- Status bar

The shell remains visible while page content changes.

Header includes:
- Atlas logo/title
- Project selector
- Global Search (project-wide object search)
- Notifications placeholder
- Settings
- User/profile placeholder
- Atlas version
- Project lifecycle stage
- Project status
- breadcrumb trail for current workspace location

## Atlas Intake (Local)
The GUI now supports local drag-and-drop intake for estimator bid packages.

Atlas Intake panel:
- Drag your project here
- Supported formats: PDF, DOCX, DOC, XLSX, XLS, CSV, JPG, JPEG, PNG, TIFF, TXT, RTF, JSON, ZIP
- Or browse files

Uploaded files are staged under:
- outputs/uploads/<session_id>

Files are automatically classified into:
- drawings/
- specifications/
- schedules/
- addenda/
- images/
- metadata/
- unsupported/

After classification, Atlas runs deterministic intake, saves the workspace locally, and then executes the existing project review pipeline.

## Project Selector
Workspace v1 uses a project selector instead of separate home controls.

Selector options include:
- Recent Projects
- Reference Projects
- Create New Project
- Open Existing Project
- Reference Project: Music Academy of the West (`[Reference]` badge)

Selecting project actions routes to project-centric pages:
- Home
- Projects
- Reference Projects
- Recent Projects
- Create New Project
- Open Existing Project

## Data Sources
The workspace supports two explicit source modes.

Reference Project:
- Music Academy of the West (Reference Project)
- Default behavior attempts real package intake from examples/music_academy_of_the_west
- Data Source label shows `Real package intake` when loaded from full package files
- If package is missing/incomplete/unreadable, Atlas falls back to seed fixture data
- Data Source label shows `Seed fixture fallback` for fallback mode
- Fallback mode explicitly warns that curated fixture data is in use

Uploaded Project:
- User-provided files or ZIP package from Atlas Intake
- Banner shows detected project name when available
- Banner shows package location
- Import summary table is shown
- Extraction diagnostics are shown (pages with/without embedded text, files requiring OCR)
- Per-file extraction status is shown (`extracted`, `partial`, `requires_ocr`, `unsupported`, `failed`)
- Extraction warnings are shown

MAW remains reference data only and is not product-specific business logic.

## MAW Package Placement
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

## Navigation

Project Manager:
- Home
- Projects
- Reference Projects
- Recent Projects
- Create New Project
- Open Existing Project

Project:
- Overview
- Executive Summary
- Project Files
- Drawings
- Specifications
- Equipment
- Systems

Bid Intelligence:
- Readiness
- Estimator Brief
- RFI Candidates
- Labor Estimate
- Revision Comparison
- Engineering Assumptions
- Evidence

Project Lifecycle (disabled, Coming Soon):
- Engineering
- Procurement
- Financials
- Construction
- Closeout
- Service

Reports:
- Reports
- Exports

Settings:
- Project Settings
- Application Settings

## Responsive Navigation
- Desktop: persistent sidebar
- Tablet: collapsible sidebar with navigation popover
- Mobile: drawer-style navigation popover

The current page, selected project, and breadcrumb remain visible in all modes.

## Upload Flow
1. Open `Project Files`.
2. Drag files into Atlas Intake (single file, many files, or ZIP).
3. Click `Run Atlas Intake`.
4. Review import summary, warnings, and file explorer output.

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

## Overview (Mission Control)
Overview displays project health at a glance:
- project metadata (name, owner, architect/consultants, project number, dates)
- lifecycle stage and project status
- import status
- readiness score and readiness level
- confidence and top risk counts
- recent activity
- import summary
- quick actions

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

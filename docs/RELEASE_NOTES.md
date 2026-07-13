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

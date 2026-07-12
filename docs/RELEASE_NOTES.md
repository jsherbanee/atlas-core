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

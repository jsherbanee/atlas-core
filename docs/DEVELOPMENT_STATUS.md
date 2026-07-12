# Atlas Core Development Status

This document answers: Where is Atlas today?

It represents the current implementation state of Atlas Core.

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
Atlas Core is in active Phase 2 Bid Intelligence development with a stabilization baseline candidate prepared and a project-specific Atlas workspace shell implemented.
Sprint 3 UX delivery added guided project review progression, explicit review status modeling, checklist visibility, and a concise project summary report center with deterministic exports.
Sprint 4 UI refinement adds repository-backed Open Existing Project, a stronger Projects library workflow, application-wide Knowledge scope, compact active-project identity, concise breadcrumbs, and a two-column Project Workspace layout (no persistent third context column).
Sprint 5 introduces an Equipment Object Workspace that treats equipment as first-class engineering objects with deterministic detail, relationship navigation, evidence, and recommended actions.
Sprint 6 implements the Atlas object navigation layer, adding shared object navigation patterns across Drawings, Specifications, Equipment, global object search, and Relationship Explorer.
Sprint 7 delivers persistent Global Object Search and Working Set workflows, including deterministic ranking, grouped result presentation, local search history, and object-context breadcrumbs.
Sprint 7.5 completes UI repair and runtime-state isolation with shared project context header rendering, configuration-driven navigation cleanup, shared object detail section scaffolding, and mutable runtime workspace storage outside immutable source fixtures.
Sprint 8 introduces the Deterministic Estimating Foundation: Estimate Workspace architecture, traceable estimate line entities, resolution/pricing status modeling, confidence scoring, and extension-point interfaces for future pricing engines.

## Quality Status (Latest Full Run)
- black .: passing
- ruff check .: passing
- mypy .: passing
- pytest: 964 passed

## Tooling Status
- GitHub Actions configured
  - .github/workflows/python.yml
- Pre-commit configured
  - .pre-commit-config.yaml

## Active Focus
Finalize and harden the Phase 2 Bid Intelligence baseline before any downstream lifecycle expansion.

Lifecycle object definitions and cross-phase module boundaries are documented in [DOMAIN_MODEL.md](DOMAIN_MODEL.md).

Current MAW reference-project behavior:
- Atlas attempts real package intake from examples/music_academy_of_the_west for the Reference Project view.
- Seed fixture data is retained as regression fallback only when real package intake is unavailable.
- GUI labels explicitly indicate whether Reference Project is using Real package intake or Seed fixture fallback.

Current workspace behavior:
- Atlas uses an Application Workspace for Mission Control, project management, knowledge, reports, and administration.
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
- Deterministic estimate lines now include required source traceability fields (source object, object type, manufacturer, model, description, quantity, pricing status, labor status, confidence, and source references).
- Estimate line navigation now supports Equipment, Specification, Drawing, Relationships, and Evidence traversal.
- Product resolution state now surfaces exact product, approved substitute, preferred alternate, generic allowance, and unknown product.
- Cost status now surfaces no pricing, estimated, quoted, verified, expired, and unavailable.
- Unknown products now remain no-pricing in deterministic mode.
- Estimate confidence now reports known pricing coverage, product resolution coverage, labor/pricing gaps, quantity uncertainty, and generic allowance exposure.
- BOM Review now includes an Open Equipment Detail action for selected BOM rows while preserving BOM table reconciliation behavior.
- Drawing and Specification workspaces now expose referenced equipment as human-readable objects that can open Equipment Workspace.
- Project Workspace now includes a non-blocking guided review sequence with statuses (not started/ready/needs review/blocked/complete).
- Overview and Reports expose a deterministic project review checklist and specific next-step navigation.
- Reports now provide Project Summary, Estimator Brief, BOM Export, Scope and Risk Export, and Engineering Review Export views.
- Project Summary report exports are deterministic Markdown/JSON/HTML for internal review use.
- Open Existing Project defaults to repository-backed project selection with search/sort/filter and archived visibility.
- Manual path entry remains available only as an advanced development/recovery option.
- Knowledge workspace is application-wide and excludes project-specific review pages.
- Active project identity is surfaced through a compact project header with lifecycle/status badges and recommended next action.
- Project Workspace desktop layout is two-column (navigation + working content), with inline/on-demand object detail.

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

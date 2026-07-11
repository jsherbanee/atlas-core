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

## Quality Status (Latest Full Run)
- black .: passing
- ruff check .: passing
- mypy .: passing
- pytest: 917 passed

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
- Project Workspace emphasizes Overview, Documents, BOM Review, Scope & Risk, Engineering Review, Estimate (advisory), Notebook, Reports, and project details/settings pages.

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

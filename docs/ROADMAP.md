# Atlas Core Roadmap

Detailed implementation planning by epic and sprint stream is maintained in [EPICS.md](EPICS.md).

This roadmap is the executive milestone view.

Domain object continuity and lifecycle boundaries referenced in this roadmap are defined in [DOMAIN_MODEL.md](DOMAIN_MODEL.md).

## Product Milestones

Sprints describe implementation work.

Milestones describe customer-visible product capability.

### Preview 0.5 (Current)
- Engineering Intelligence Workspace

### Preview 0.6
- Engineering Understanding
- Master Library
- Manufacturer Registry
- Product Intelligence
- Equipment Resolution
- System Templates

### Preview 0.7
- Atlas Vision Foundations
- Drawing Intelligence maturation
- Specification Intelligence maturation
- Cross-sheet intelligence
- Symbol libraries
- Title block intelligence
- Future OCR integration points
- Commercial Knowledge Foundation with immutable price versioning
- Deterministic Pricing Engine with immutable record selection and explainable pricing traces
- Deterministic Cost Engine with acquisition-cost traceability and vendor hierarchy

### Beta 1.0
- Internal production-ready
- Real benchmark project validation
- Performance tuning
- Documentation complete

### RC1
- Release Candidate
- Final stabilization

### Atlas 1.0
- Commercial AV Bid Intelligence Platform

### Atlas 2.0
- Complete Project Lifecycle Platform

## Phase 1: Foundation (Completed)
Completed outcomes:
- Core domain model scaffolding
- Service orchestration baseline
- Initial export and workflow patterns
- Test-first quality gate and CI baseline

## Phase 2: Bid Intelligence (Active)
Current objective:
Sprint X-03 Onboarding and Stakeholder Workflow Hardening is active.

Current UX hardening stream:

- Epic X Product Hardening continuation (A-05 and X-01/X-02 complete, X-03 active)
- focused on estimator/project-engineer/design-engineer workflow usability hardening for existing capabilities
- preserves D-03 scope boundaries and does not start Epic E or Commercial Intelligence implementation
- includes onboarding/stakeholder hardening in existing project-management workflows and preserves prior X-02 identity model refinements

Implemented in current baseline candidate:
- Bid package review orchestration
- Drawing/spec indexing
- System and equipment detection
- Cross-reference/scoping diagnostics
- Scope reconciliation
- Engineering rule engine assumptions
- RFI candidate generation
- Labor estimation engine
- Bid completeness scoring
- Plan review readiness scoring
- Estimator brief enhancements
- Revision comparison engine
- Commercial knowledge model (vendor offerings, price sheets, immutable versions, and price records)
- Deterministic price version comparison and product change reporting
- Commercial freshness and lifecycle tracking for price recency and missing-from-latest detection

- Deterministic pricing engine for estimate lines with candidate/rule traces, manual override audit, and pricing snapshot reproducibility
- Advisory pricing impact detection without silent repricing
- Deterministic pricing exports for summary, priced BOM, coverage, and exceptions
- Deterministic cost engine for acquisition cost selection, cost traceability, commercial coverage, and project-only quick-add product support

Remaining Phase 2 refinements:
- D-03/A-05/X-01/X-02 closeout verified: full quality-gate validation and architecture review complete
- Epic E and post-D feature-epic implementation has not started in this pass
- remaining UX debt: table-density/pagination consistency, progressive disclosure, and smaller-screen ergonomics
- PDF ingestion and indexing robustness
- Drawing/spec intelligence quality refinements
- Device schedule extraction quality refinements
- Additional deterministic regression snapshots and export validations
- Additional pricing policy calibration and broader multi-vendor benchmark coverage
- Additional cost confidence calibration and larger quick-add promotion regression coverage

## Phase 3: Project Initialization (Deferred)
Deferred until Phase 2 completion.

## Phase 4: Procurement (Deferred)
Deferred until Phase 2 completion.

## Phase 5: Construction/Closeout (Deferred)
Deferred until Phase 2 completion.

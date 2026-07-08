# Atlas Preview 0.5 Stabilization Checklist

## Purpose

This checklist defines product-validation readiness for Atlas Preview 0.5.

Scope is stabilization only:

- usability
- workflow validation
- consistency
- perceived responsiveness
- visual polish
- regression confidence

No major new functionality is included in this sprint.

## Implemented Features (Preview 0.5)

- Project-centric Atlas Workspace shell
- Persistent local project repository and workspace state
- Project intake and deterministic document classification
- Drawing Intelligence and Drawing Explorer
- Specification Intelligence and Specification Explorer
- Knowledge Graph object and relationship model
- Engineering Resolver and conflict center
- Engineering Intelligence and system health surfaces
- Coordination Intelligence and coordination findings
- Engineering Workbench investigation mode
- Estimator Brief and readiness/advisory outputs
- Deterministic exports and report summary surfaces

## Known Limitations

The following are intentionally deferred and out of scope for Preview 0.5:

- OCR not implemented as a default production capability
- Computer Vision deferred
- Procurement deferred
- Financials deferred
- Construction deferred
- Cloud deferred
- Collaboration deferred
- Manual Resolver actions deferred
- Future AI assistance deferred

## Deferred Functionality

- Lifecycle modules beyond active bid intelligence and review surfaces
- Project execution write-back workflows
- Multi-user synchronization and conflict handling
- Cloud-native storage adapters and identity integration

## GUI Review Checklist

- [ ] Page headers are consistent and decision-focused
- [ ] Breadcrumb is visible and accurate on all pages
- [ ] Current project and current page remain visible
- [ ] Cards and tables use consistent spacing and hierarchy
- [ ] Filters/search controls are discoverable and predictable
- [ ] Empty states are explicit and actionable
- [ ] Placeholder pages provide non-dead-end navigation
- [ ] Context panel behavior is consistent by selection type
- [ ] Status chips are consistent across pages

## Performance Checklist

- [ ] Expensive view computations are cached per render context
- [ ] Loading indicators appear on major engineering views
- [ ] Global search remains responsive for larger packages
- [ ] Workspace navigation avoids redundant heavy recomputation
- [ ] Project explorer interactions remain responsive under larger file sets

## Regression Checklist

- [ ] black .
- [ ] ruff check .
- [ ] mypy .
- [ ] pytest
- [ ] No new critical warnings/errors introduced

## Benchmark Project Checklist

Reference benchmark projects should validate:

- [ ] MAW reference intake loads successfully
- [ ] Drawing/spec/object counts are coherent
- [ ] Resolver outputs are stable
- [ ] Coordination findings are generated and traceable
- [ ] Workbench investigation path is complete end-to-end
- [ ] Estimator Brief includes evidence-linked recommendations
- [ ] Reports summarize estimator-facing findings

## Workflow Validation Checklist

Intended workflow sequence:

New Project

-> Document Intake

-> Drawing Intelligence

-> Specification Intelligence

-> Knowledge Graph

-> Resolver

-> Engineering Intelligence

-> Coordination Review

-> Engineering Workbench

-> Estimator Brief

Validation criteria:

- [ ] Sequence is natural and discoverable from navigation and quick actions
- [ ] Each stage has clear decision context
- [ ] Traceability is preserved through evidence and relationships
- [ ] No dead-end pages in the active workflow path

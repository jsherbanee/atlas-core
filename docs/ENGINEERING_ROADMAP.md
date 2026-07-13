# Engineering Roadmap

## Purpose
This document is the engineering execution roadmap for Atlas.

It is separate from [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md), which is customer- and business-facing, and it is separate from [EPICS.md](EPICS.md), which remains the implementation planning source of truth for epic and sprint decomposition.

## Related Documents
- [ROADMAP.md](ROADMAP.md)
- [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)
- [EPICS.md](EPICS.md)
- [AV_LIFECYCLE.md](AV_LIFECYCLE.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [RULE_ENGINE.md](RULE_ENGINE.md)
- [SEARCH_ARCHITECTURE.md](SEARCH_ARCHITECTURE.md)
- [OBJECT_GRAPH.md](OBJECT_GRAPH.md)
- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
- [OBSERVABILITY.md](OBSERVABILITY.md)
- [PERFORMANCE.md](PERFORMANCE.md)
- [REPORTING.md](REPORTING.md)
- [BACKUP_RECOVERY.md](BACKUP_RECOVERY.md)
- [ENGINEERING_INTELLIGENCE.md](ENGINEERING_INTELLIGENCE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)
- [DRAWING_INTELLIGENCE.md](DRAWING_INTELLIGENCE.md)
- [SPECIFICATION_INTELLIGENCE.md](SPECIFICATION_INTELLIGENCE.md)
- [COORDINATION_INTELLIGENCE.md](COORDINATION_INTELLIGENCE.md)

## Role In The Documentation System
EPICS.md owns the implementation plan and sprint stream IDs.

This document summarizes the technical sequencing that supports those epics and identifies architectural gates that must be satisfied before broader platform expansion.

Use this document when planning engineering dependencies, infrastructure work, refactoring, migrations, test strategy, release engineering, and production-readiness gates.

## Current Position
Phase 2 Bid Intelligence remains active.

Epic X is complete and formally closed.

X-01 through X-13 are closed.

No Epic X sprint is active.

W-01 Workspace Intelligence continuity is implemented and closed.

W-02 Universal Object contract foundation is implemented.
W-03 Universal Object Workspace shared UI migration is implemented for controlled object scope.

Current engineering focus is post-W-03 validation, broader adapter coverage, deeper activity/history compatibility, and future object-family migration planning.

Epic E remains the next candidate epic only after architecture review and explicit sprint approval.

Epic E must not be started from this roadmap.

## Engineering Sequence

### 1. Foundation Hardening
- preserve deterministic Phase 2 behavior
- maintain existing test coverage and regression safety
- keep current UI and workspace behavior stable
- align documentation with current implementation boundaries

### 2. Repository and Import Stability
- harden repository contracts and project persistence behavior
- unify intake diagnostics and recovery-safe partial success handling
- support local-runtime and future adapter compatibility
- keep ingestion, preview, and finalization deterministic

### 3. Search and Object Graph Foundations
- preserve deterministic global search
- strengthen object graph construction and traversal
- keep relationship evidence and provenance explicit
- prepare for future relationship-aware search and visualization
- preserve explicit workspace context handoff and deterministic return-context behavior across workspace transitions
- establish a universal object identity and adapter layer so future workspace, graph, search, and AI surfaces can consume one stable object contract
- extend shared Object Workspace migration gradually without redesigning unrelated authoritative workflows

### 4. Rule and Intelligence Infrastructure
- keep deterministic rule evaluation auditable and reproducible
- extend rule registries and policy overlays without ad hoc conditionals
- ensure engineering intelligence, drawing intelligence, specification intelligence, and coordination intelligence remain traceable

### 5. Performance and Observability Foundations
- establish performance budgets for search, ingestion, graph traversal, and report generation
- introduce production-grade observability concepts without overstating current implementation
- define tenant-safe logging, metrics, traces, and audit paths

### 6. Cloud-Readiness and Security Hardening
- align repository and adapter boundaries for future AWS deployment options
- keep tenant isolation and security boundaries explicit
- preserve local development parity while enabling future cloud adapters

### 7. Reporting and Export Engineering
- define deterministic reporting contracts
- preserve reproducibility and source provenance
- distinguish operational reporting from financial summaries

### 8. Lifecycle Expansion Readiness
- prepare service, asset, and lifecycle subsystems for future implementation
- preserve current Phase 2 focus while documenting downstream architecture

## Cross-Epic Dependencies
- Epic A provides workspace and shell foundations used by later engineering surfaces.
- Epic B provides intelligence and relationship-analysis primitives.
- Epic C provides commercial knowledge, product resolution, and versioned pricing foundations.
- Epic D provides deterministic estimating and cost-selection infrastructure.
- Epic X provides UI hardening and validation constraints that must remain stable.
- Epic E depends on object graph, search, and shared-knowledge architecture maturity.
- Later lifecycle and service work depends on ingestion, search, reporting, and integration architecture being stable.

## Architectural Gates
Before introducing broader platform features, Atlas should have:
- stable domain boundaries
- deterministic rule execution
- repository-backed persistence contracts
- tenant-aware storage and access control
- reliable document ingestion and diagnostics
- explainable search and object relationships
- reproducible exports and reporting
- auditability for key actions

## Migration Gates
Any future migration work should be gated by:
- clear adapter compatibility
- reversible or recoverable data movement
- deterministic identity and versioning rules
- preservation of historical records
- tenant-safe migration paths
- explicit verification of source provenance

## Production-Readiness Gates
Production readiness should require:
- defined observability and alerting
- documented backup and recovery procedures
- performance budgets and load-testing expectations
- security hardening and secrets handling
- tenant-aware administrative workflows
- reproducible release engineering practices
- operational diagnostics for ingestion, search, and reporting

## Technical Milestones
- preserve Phase 2 stability and quality gates
- harden current repository-backed workspace behavior
- consolidate search and object-graph foundations
- formalize rule-engine and diagnostics contracts
- prepare cloud, observability, and recovery documentation
- support future lifecycle-expansion subsystems without starting Epic E

## Release Engineering
Release engineering should emphasize:
- reproducible builds
- deterministic test runs
- clear versioned documentation
- staged validation before wider rollout
- safe rollback and recovery planning

## Unresolved Decisions
- final cloud adapter shape remains open
- final search index implementation remains open
- final graph persistence model remains open
- final observability vendor/tooling remains open
- final production deployment topology remains open
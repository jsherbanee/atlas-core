# Lifecycle Engine

## Purpose
This document defines the deterministic AV Lifecycle Engine introduced in Epic L Sprint L-01.

It is the implementation-facing authority for:
- lifecycle authority boundaries
- canonical stage definitions
- stage-status semantics
- transition and readiness rules
- lifecycle history behavior
- project compatibility behavior
- tenant enforcement
- intentionally deferred downstream lifecycle workflows

Related documents:
- [AV_LIFECYCLE.md](AV_LIFECYCLE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [OBJECT_WORKSPACE.md](OBJECT_WORKSPACE.md)
- [WORKSPACE_INTELLIGENCE.md](WORKSPACE_INTELLIGENCE.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)

## Lifecycle Authority
Sprint L-01 establishes one deterministic lifecycle authority in `atlas_core/domain/av_lifecycle.py`.

Authority rules:
- the lifecycle engine is the source of truth for canonical stage keys, stage order, stage labels, stage owners, and transition rules
- `Project.status` remains the legacy compatibility status for existing project flows and serialization
- `metadata["lifecycle_stage"]` remains the compatibility stage field for existing repository/UI/search flows
- `metadata["lifecycle_plan"]` is the persisted lifecycle-engine snapshot for deterministic lifecycle state, readiness, and history
- UI and service layers should prefer the lifecycle plan when present and only fall back to legacy status/stage values for compatibility reads

## Canonical Stages
The current engine defines these stage keys in deterministic order:

1. `lead`
2. `opportunity`
3. `discovery`
4. `bid_intake`
5. `bid_intelligence`
6. `estimating`
7. `proposal`
8. `award`
9. `project_initialization`
10. `engineering`
11. `submittals`
12. `procurement`
13. `logistics_and_receiving`
14. `project_management`
15. `field_installation`
16. `programming_and_configuration`
17. `testing_and_commissioning`
18. `training`
19. `punch_and_completion`
20. `closeout`
21. `warranty`
22. `service_and_support`
23. `asset_lifecycle`
24. `upgrade_or_replacement`
25. `archived`

L-01 implementation scope note:
- the engine defines the full canonical sequence now so Atlas has one durable lifecycle vocabulary
- downstream workflows for procurement, installation, commissioning, warranty, service, and replacement are not implemented in L-01
- those later stages exist as lifecycle definitions and compatibility targets, not as active workflow modules

## Status Model
Stage status is independent from legacy project status.

The lifecycle engine currently uses:
- `not_started`
- `available`
- `active`
- `needs_review`
- `blocked`
- `complete`
- `skipped`
- `archived`

Status interpretation:
- `active` means the current working lifecycle stage
- `available` means next eligible stage in sequence
- `needs_review` means the stage requires human review or rework before forward progress
- `blocked` means deterministic transition rules are not satisfied
- `complete` means the stage has been completed and historical state is preserved
- `skipped` means an optional stage was intentionally bypassed with recorded reason
- `archived` is terminal until explicit restore

## Transition Rules
The engine exposes deterministic transitions instead of unconstrained direct stage mutation.

Current transition behaviors:
- `advance` to the next applicable stage
- `return` to the prior applicable stage
- `skip` for optional stages only
- `archive`
- `restore`
- `reopen`

Transition constraints:
- tenant scope must match the lifecycle plan tenant
- actor is required
- reason is required for explicit transition operations
- direct jumps outside the deterministic adjacent-path model are rejected
- optional-stage skip is rejected for non-optional stages
- archived plans must be restored before normal transitions continue

## Readiness And Diagnostics
L-01 introduces deterministic readiness evaluation structures even where later workflows are deferred.

Core contracts:
- `LifecycleTransitionRequirement`
- `LifecycleTransitionDiagnostic`
- `LifecycleReadiness`

Readiness outputs support:
- `ready`
- `needs_review`
- `blocked`
- explicit missing requirements
- explicit diagnostics
- recommended next action
- affected objects and evidence references

Current implementation note:
- L-01 provides the engine contracts and readiness evaluation mechanics
- later lifecycle workflow sprints will attach richer domain-specific requirements and evidence to downstream stages

## History Model
The engine persists lifecycle history through immutable `LifecycleHistoryEvent` records inside the lifecycle plan snapshot.

History event fields include:
- source stage and destination stage
- source status and destination status
- actor
- timestamp
- reason
- diagnostics snapshot
- related objects
- source references

Repository integration in L-01:
- lifecycle-plan history is stored in `metadata.json` through `metadata["lifecycle_plan"]`
- transition events are also logged into `history/events.jsonl` with event type `project_lifecycle_transitioned`
- Object Workspace activity/history surfaces can render transition reasons and before/after stage context from logged payloads

## Project Compatibility
L-01 is explicitly backward compatible.

Compatibility rules:
- existing `ProjectStatus` enum remains unchanged
- existing `ProjectLifecycleEvent` remains unchanged
- existing `status` and `lifecycle_stage` repository fields remain persisted
- legacy project loads without lifecycle plan continue to build a deterministic lifecycle plan from legacy fields
- the engine maps canonical stages to legacy statuses so current project serialization, search, manifests, and filters continue to work

Compatibility mappings currently include:
- `intake` -> `bid_intake`
- `submitted` -> `proposal`
- `awarded` -> `award`
- `active` -> `project_management`
- `closeout` -> `closeout`

## Tenant Enforcement
Lifecycle transitions are tenant-scoped.

Current enforcement rules:
- lifecycle plans carry `tenant_id`
- transition calls reject mismatched tenant IDs
- relationship and universal-object identity contracts remain cross-tenant safe
- Object Workspace and shared history flows should only render lifecycle state from the current tenant context

## Universal Object Integration
Project object projections now carry lifecycle-engine state through the universal object contract.

L-01 behavior:
- project identity uses legacy-compatible `status`
- project lifecycle state uses canonical `lifecycle_stage`
- universal lifecycle transitions are derived from available lifecycle-engine transitions when a lifecycle plan is present
- Project Object Workspace surfaces lifecycle context without replacing authoritative project workflows

## Deferred Lifecycle Work
Explicitly deferred from L-01:
- procurement execution workflows
- logistics workflows beyond lifecycle-state modeling
- field installation workflows
- commissioning workflows
- training workflows
- warranty and service execution workflows
- asset-lifecycle and replacement workflow modules
- non-project lifecycle domains such as billing, accounting, or ERP execution

L-01 only establishes the deterministic foundation these future workflows will build on.

## L-02 Lifecycle Dashboard

Sprint L-02 introduces the first reusable Lifecycle Dashboard for Project Object Workspace.

Dashboard rules:
- the dashboard consumes the persisted lifecycle plan and available engine transitions
- the dashboard must not duplicate or recompute lifecycle state outside the lifecycle engine and compatibility projections
- the dashboard is a tertiary Project Object Workspace view, not a standalone workspace or parallel route

Current dashboard coverage:
- current lifecycle stage
- stage status
- completed, blocked, and upcoming stages
- available transitions
- readiness diagnostics
- recent lifecycle events
- recommended next action
- responsible role when known

Progressive disclosure behavior:
- default lifecycle view stays concise with summary cards and a horizontal stage timeline
- stage-specific diagnostics, requirements, history, and related objects expand on demand

Still deferred in L-02:
- automatic advancement
- workflow automation
- downstream departmental execution modules

## Transactions Boundary Note

Project lifecycle and transaction lifecycle are separate concerns.

- the AV lifecycle engine is currently authoritative for Project lifecycle state
- future commercial-document transaction lifecycles should not be silently folded into Project lifecycle stages
- transaction families may participate in Project progress, but they require their own document-state models, approvals, sync metadata, and closeout semantics

Sprint A-07 defines that architecture boundary but does not introduce a transaction lifecycle engine implementation.

## A-08 Commercial Document Lifecycle Alignment

Sprint A-08 defines a common commercial-document lifecycle vocabulary:

Draft
→ In Review
→ Approved
→ Issued
→ Partially Fulfilled
→ Fulfilled
→ Closed
→ Archived

Alignment rule:
- this lifecycle is deterministic and explicit like the Project lifecycle engine
- it is not the same as the Project lifecycle stage model
- A-08 does not imply the existing Project lifecycle engine already implements commercial-document lifecycles
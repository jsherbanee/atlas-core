# Workspace Intelligence

## Purpose
Workspace Intelligence defines how Atlas preserves meaningful working context across Projects, Knowledge, Search, and related object views without introducing AI or new business workflows.

It is the continuity layer that makes the application feel like one connected operational workspace.

## Scope
W-01 implements the first deterministic Workspace Intelligence capability.

Implemented in W-01:
- explicit session-state context model for active workspace, active navigation branch, selected project object, and selected Knowledge entity
- bounded return context for cross-workspace movement
- bounded navigation history compatible with existing workspace persistence
- deterministic search handoff that preserves return context and selected-record context
- mixed-scope Working Set support for project objects and Knowledge entities
- breadcrumb and return affordances owned by the shared shell
- deterministic related-project sections for Knowledge records where existing repository and reviewed-equipment data prove the relationship

Implemented in W-02:
- universal object interoperability contract for identity, metadata, relationships, activity, lifecycle, actions, and presentation hints
- registry-backed adapter lookup for representative project, knowledge, and engineering object families
- compatibility alignment between W-01 context persistence and universal object identity payloads
- universal identity exposure in search references and Working Set-compatible records

Implemented in W-03:
- shared Universal Object Workspace rendering inside the existing shell for migrated object types
- consistent object-level tertiary navigation (Summary, Details, Relationships, Activity, Documents, History) based on supported view contracts
- reusable context banner and one-click return behavior in the object workspace using existing W-01 return-context state
- search and Working Set handoff into Universal Object Workspace for supported object types while preserving backward compatibility for unsupported and legacy entries

Out of scope:
- AI
- semantic retrieval
- automatic relationship discovery
- new business workflows
- cloud persistence
- Epic E implementation

## Core Context Model
The continuity model tracks:
- active primary workspace
- active secondary section
- active tertiary action
- active project ID
- selected project object type and ID
- selected Knowledge entity type and ID
- originating workspace
- originating route
- return context
- bounded navigation history
- Working Set membership
- tenant scope marker

The model remains:
- deterministic
- tenant-scoped
- presentation-neutral
- safe for Streamlit session state
- backward compatible with existing workspace state payloads

## Return Context
Return context is explicit and bounded.

Each contextual handoff may store:
- source workspace
- source route
- source label
- source project
- source object kind and ID
- source selection payload
- source secondary and tertiary branch
- tenant scope
- timestamp

Behavior rules:
- one-click return only
- no browser-history guessing
- no cross-tenant return targets
- safe fallback when a target project no longer exists
- bounded history size

## Search Continuity
Deterministic search remains global.

W-01 adds:
- explicit return-context capture when opening a search result
- project/application scope labels in result captions
- current workspace and selected Knowledge entity context as deterministic ranking inputs
- preservation of broad application results even while favoring strong project-context matches

W-03 continuity extension:
- supported search opens now route into Object Workspace for migrated object families
- context banner always reflects originating workspace and route label when available
- one-click return from object workspace restores deterministic prior route context
- unsupported/legacy object families continue using compatibility routes without breaking continuity

## Knowledge And Project Continuity
W-01 supports contextual movement from project workflows into Knowledge using explicit actions on validated surfaces.

Current validated paths include:
- project summary customer handoff
- project-to-Knowledge customer flow from project reports summary
- BOM, Estimate, and Product Resolution continuity hooks where source data exists

Knowledge-to-project continuity is deterministic only when existing repository or reviewed-equipment data proves the relationship.

## Persistence Boundaries
Workspace Intelligence uses existing repository-backed workspace state.

Persisted continuity state includes:
- selected project object type and ID
- selected Knowledge entity type and ID
- bounded return context
- bounded navigation history
- current primary/secondary/tertiary workspace state

Not persisted:
- transient widget-owned values
- speculative or inferred relationships
- browser-history state

## Working Set
Working Set now supports mixed continuity entries:
- project objects
- Knowledge entities

Compatibility rules:
- stable object identity
- stable object type
- deterministic ordering
- direct open support
- remove and clear support
- compatibility with older Working Set records

W-03 Working Set handoff note:
- opening a supported Working Set entry routes through Object Workspace and preserves the same return-context contract used by search handoff
- unsupported entries continue to open through authoritative legacy pages

## Remaining Non-Blocking Debt
- some continuity actions are still data-dependent and only appear when the underlying project or Knowledge payload proves the relationship
- deeper coverage for vendor and service project-backlinks depends on stronger deterministic relationship surfacing in existing repository artifacts
- additional object-detail pages can adopt the same return-context affordance in future W-series hardening
- broader object-family migration beyond W-03 controlled scope remains deferred

## L-01 Lifecycle Continuity Extension

Sprint L-01 keeps Workspace Intelligence deterministic while adding lifecycle-engine continuity for project records.

Current behavior:
- project workspace state now persists lifecycle-engine snapshot data through existing repository-backed metadata
- project object selection and Object Workspace handoff preserve canonical lifecycle stage and legacy-compatible status together
- lifecycle history and recommended next action are available to shared project-facing workspace surfaces without introducing a second continuity store

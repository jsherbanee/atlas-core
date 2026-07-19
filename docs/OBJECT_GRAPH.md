# Object Graph

## Purpose
This document defines the authoritative object relationship and knowledge-graph architecture for Atlas.

It reconciles [DOMAIN_MODEL.md](DOMAIN_MODEL.md) with Engineering Intelligence, Drawing Intelligence, Specification Intelligence, and Coordination Intelligence.

## Related Documents
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [ENGINEERING_INTELLIGENCE.md](ENGINEERING_INTELLIGENCE.md)
- [DRAWING_INTELLIGENCE.md](DRAWING_INTELLIGENCE.md)
- [SPECIFICATION_INTELLIGENCE.md](SPECIFICATION_INTELLIGENCE.md)
- [COORDINATION_INTELLIGENCE.md](COORDINATION_INTELLIGENCE.md)
- [SEARCH_ARCHITECTURE.md](SEARCH_ARCHITECTURE.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)

## Scope
The object graph should represent durable relationships among Atlas objects, evidence, and provenance.

It should support deterministic relationship construction today and more advanced graph persistence later.

## Core Concepts
- Node identity: a stable object identity within a tenant and often within a project.
- Edge identity: a stable relationship identity with type, source, target, and provenance.
- Relationship type: the semantic meaning of the connection.
- Directionality: source-to-target orientation should be explicit.
- Source evidence: the record or document that justified the relationship.
- Confidence: how strong or explicit the relationship is.
- Provenance: where the relationship came from and how it was derived.

W-02 contract note:
- universal object identity now provides a shared adapter-layer identity envelope for project, knowledge, and engineering objects without replacing existing domain models
- universal relationship contracts preserve tenant scope, source/target identity, direction, provenance, and effective timing in a reusable shape for graph traversal and future object rendering

W-03 workspace note:
- migrated object families now render relationships and activity through one shared object-workspace envelope
- relationship presentation remains source-backed and deterministic; no inference-only edges are introduced by the shared UI
- activity presentation is compatibility-first and may be sparse where source audit history is not yet deep

## Relationship Types
Representative relationship types include:
- contains
- references
- derived-from
- matches
- related-to
- supersedes
- supports
- conflicts-with
- depends-on
- located-in
- owned-by
- belongs-to
- produced-by
- approved-by

## Deterministic Construction
Relationships should be constructed deterministically from explicit evidence, parsing output, repository state, and reproducible rules.

When a relationship cannot be proven, the graph should preserve unresolved or low-confidence state rather than invent certainty.

K-02 implementation note:
- Framework-managed customer/service/manufacturer/vendor/product entities now expose deterministic operational relationship updates through stable relationship IDs and audited upsert events.

K-03 implementation note:
- Framework-managed contact, location, and project entities now participate in deterministic search, import/export, and explicit relationship upserts alongside the existing customer/service/manufacturer/vendor/product graph.

Organization merge implementation note:
- Customer, Vendor, and Manufacturer role records can be consolidated under a surviving Organization graph node.
- Supported Knowledge relationships are deterministically reassigned from merged source role records to the surviving Organization entity.
- Merge provenance preserves source entity IDs, actor, reason, conflict resolutions, and relationship reassignment counts.
- Cross-tenant or cross-organization-scope graph merges are rejected.

## Versioning
The graph should support versioned edges and nodes so historical context can be reproduced when inputs change.

## Project And Cross-Project Knowledge
Atlas should support project-scoped relationships and carefully bounded cross-project knowledge reuse.

Cross-project relationships should be explicit and tenant-safe.

## Tenant Boundaries
The graph must never cross tenant boundaries implicitly.

Any shared knowledge model must preserve tenant isolation and authorization rules.

## Conflicting And Unresolved Relationships
The graph should represent:
- conflicting relationships
- unresolved relationships
- ambiguous matches
- superseded relationships
- deleted or archived relationships

## Traversal And Search
The object graph should support:
- deterministic traversal
- graph-based search
- relationship-aware filtering
- graph visualization
- connected-object navigation

Connected-object navigation in W-03 is bounded by compatibility contracts:
- supported object families can be opened in shared Object Workspace
- unsupported families keep direct authoritative-route navigation

## Downstream AI Usage
Future AI features may use the object graph as a grounding and retrieval structure, but AI must not silently override deterministic graph logic.

## Future Persistence
The current desired model can remain service-built and repository-backed, but future persistence may introduce explicit graph storage if the product needs it.

## Lifecycle And Deletion
Graph records should support:
- lifecycle state
- soft deletion or archival where policy requires it
- source preservation
- replayable reconstruction where possible

## Performance Boundaries
Graph construction and traversal should remain bounded by project size, tenant partitioning, and index freshness. Large graphs should degrade gracefully.

## Unresolved Decisions
- whether a dedicated graph store is needed remains open
- how much cross-project knowledge reuse should be automatic remains open
- final graph visualization model remains open

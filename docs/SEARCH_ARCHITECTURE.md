# Search Architecture

## Purpose
This document defines search as a core Atlas capability.

Deterministic search is separate from future semantic AI retrieval.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [OBJECT_GRAPH.md](OBJECT_GRAPH.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)
- [ENGINEERING_INTELLIGENCE.md](ENGINEERING_INTELLIGENCE.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)

## Current Search Model
Atlas currently relies on deterministic global search behavior in the application shell and project workspaces.

That model should remain understandable, exact where possible, and fast enough to support workspace navigation.

## Search Scopes
Search should support:
- application-scoped search
- project-scoped search
- object-scoped search
- focused search mode
- recent searches
- recently opened records

## Deterministic Ranking Principles
Ranking should prefer:
- exact identifiers
- exact names
- explicit object types
- current project context
- recently opened objects
- highly relevant object relationships
- fresh indexed records

## Object Types
Search should be aware of object families such as:
- projects
- drawings
- specifications
- equipment
- documents
- contacts
- organizations
- opportunities
- estimates
- reports
- settings and admin records where permitted

K-02 search note:
- Application-scope search now includes framework-managed customer and service knowledge entities, and preserves deterministic object routing into Knowledge workflows.

## Permissions And Tenant Scope
Search results must respect:
- tenant boundaries
- project permissions
- object permissions
- document permissions
- role-aware access rules

Results must never expose unauthorized data from another tenant.

## Recent And Focused Behaviors
The search experience should support:
- recent searches
- recently opened records
- focused search mode that temporarily narrows the visible workspace
- deterministic search history behavior

## Future Search Architecture
Future search layers may include:
- full-text indexing
- metadata filtering
- relationship-aware search
- semantic retrieval
- AI retrieval
- source ranking
- indexing freshness controls
- deleted and archived record handling

Deterministic search must remain available even if semantic retrieval is introduced later.

## Result Explainability
Search results should be explainable through:
- query match reason
- object type
- source field or identifier match
- relationship context
- ranking rationale where practical

## Performance Goals
Search should degrade gracefully under larger workspaces by preserving acceptable response times, avoiding unnecessary reindexing, and keeping ranking rules deterministic.

## Auditability
Search interactions that matter to governance should be auditable where practical, especially for tenant-visible operational records or future sensitive queries.

## Unresolved Decisions
- final index implementation remains open
- final metadata-filter model remains open
- semantic retrieval boundaries remain open
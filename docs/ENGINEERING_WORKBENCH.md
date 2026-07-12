# Engineering Workbench

## Related Documents
- [README.md](README.md)
- [ENGINEERING_INTELLIGENCE.md](ENGINEERING_INTELLIGENCE.md)
- [ENGINEERING_RESOLVER.md](ENGINEERING_RESOLVER.md)
- [DRAWING_INTELLIGENCE.md](DRAWING_INTELLIGENCE.md)
- [SPECIFICATION_INTELLIGENCE.md](SPECIFICATION_INTELLIGENCE.md)
- [COORDINATION_INTELLIGENCE.md](COORDINATION_INTELLIGENCE.md)
- [ENGINEERING_NOTEBOOK.md](ENGINEERING_NOTEBOOK.md)

## Purpose

The Engineering Workbench is the primary Atlas workspace for estimator and systems-engineering investigation.

It is optimized for deterministic engineering review:

- investigate why Atlas generated a result
- inspect resolver conflicts and linked evidence
- trace recommendations to rules and source artifacts
- compare object relationships without leaving context

The Workbench is intentionally read-only for this sprint.

## Layout

The Workbench is organized into fixed, information-dense panels:

- Active Engineering Insights
- Resolver Conflicts
- Open RFI Candidates
- High-Risk Systems
- Recommended Actions
- Selected Object Detail
- Evidence Panel

Panel docking is a future capability. Current layout is fixed to preserve consistency.

## Investigation Mode

Investigation Mode activates when an object is selected from shared workspace selection state.

Supported selections:

- Drawing
- Specification
- Equipment
- System
- Room
- Manufacturer
- Evidence
- Resolver Conflict
- RFI Candidate
- Resolved Object

When active, the Workbench renders:

- Object Summary
- Relationship Graph
- Supporting Evidence
- Conflicting Evidence
- Engineering Insights
- Resolver Decisions
- Related Documents
- Related Drawings
- Related Specifications
- Recommended Actions
- Timeline

## Engineering Trace

Each selected insight includes an Engineering Trace block that answers "why Atlas generated this":

- why Atlas generated it (insight description)
- rules applied
- supporting evidence
- confidence
- related objects
- related drawings
- related specifications

## Sprint A-04 Workstation Consistency

Workbench and adjacent project workspaces now align to common UX conventions:

- shared workspace section header for objective/focus orientation
- object-centric navigation continuity from estimate and review pages into engineering investigation surfaces
- consistent recommendation phrasing and priority ordering across action-oriented tables


This sprint does not introduce new engineering-intelligence capabilities; it consolidates interaction consistency.

- resolver decisions remain traceable and reviewable in context
- knowledge-graph relationship visibility remains investigation-first


Traceability remains deterministic and derived from existing resolver/intelligence outputs.

## Sprint A-05 Workflow Validation Notes

Workbench validation in A-05 confirms:

- object-context retention remains stable when navigating from review, estimate, and recommendation flows
- deterministic recommendation wording remains aligned with action-oriented engineering language
- no new engineering capability was introduced; refinements are usability-only

Deferred non-blocking UX debt:

- selected-object detail density can still feel heavy on smaller laptop viewports
- additional progressive disclosure opportunities remain for long evidence tables

## Sprint X-02 Scope Boundary Note

X-02 introduces project identity and creation hardening in shared workspace flows and does not add new engineering intelligence behaviors in Engineering Workbench.

Workbench impact in X-02 is limited to consistent project identity context continuity from shared header/search/navigation surfaces.

## Sprint X-03 Scope Boundary Note

X-03 continues workflow hardening in project onboarding and stakeholder linkage and does not add new Engineering Workbench intelligence features.

Workbench impact in X-03 remains limited to context continuity from improved project identity and shared organization linkage in existing project shells.

## Sprint X-04 Scope Boundary Note

X-04 continues product hardening for application-shell terminology and navigation clarity only:

- Home is the public landing-page term in Application Workspace surfaces.
- Mission Control remains an internal compatibility route name.
- Header search interaction is refined (Enter submit and grouped result presentation) without introducing new engineering-intelligence capabilities.

Workbench capability scope is unchanged in X-04.

## Resolver Conflict Center

Resolver Conflict Center provides a dedicated conflict workspace.

Conflicts can be grouped by:

- Manufacturer
- Model
- Quantity
- Room
- System
- Specification
- Drawing

Status categories:

- Resolved
- Needs Review
- High Confidence
- Low Confidence

Manual conflict resolution actions are intentionally disabled in this sprint.

## Relationship Inspector

The relationship viewer supports direct relationship inspection:

- Relationship Type
- Source
- Target
- Confidence
- Supporting Evidence
- Connected Objects
- Related Engineering Insights

This keeps relationship exploration tied to engineering reasoning instead of isolated graph browsing.

## Engineering Timeline

The timeline is informational and captures deterministic engineering activity:

- Project Imported
- Review Executed
- Resolver Updated
- Engineering Insight Generated
- Revision Compared
- Readiness Updated
- Estimator Brief Generated
- Document Imports

## Cross-Filtering Behavior

Selection is global across the workspace.

Selecting an object filters Workbench panels and investigation outputs:

- engineering insights
- resolver conflicts
- evidence rows
- relationship graph slices
- recommended actions
- related drawings
- related specifications

This eliminates duplicated navigation and keeps the user in a single decision loop.

## Scope Guardrails

The Workbench does not implement:

- manual editing
- manual conflict resolution
- AI-generated engineering decisions
- procurement, financials, construction, closeout, or service workflows

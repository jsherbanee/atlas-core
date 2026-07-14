# Atlas Product Governance

## Purpose
This document defines how Atlas selects, sequences, refines, and closes work so implementation stays aligned with the intended 1.0 product.

It governs product planning discipline, not engineering implementation detail.

## Related Documents
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)
- [EPICS.md](EPICS.md)
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- [SCRUM_PROCESS.md](SCRUM_PROCESS.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [TRUST_CHARTER.md](TRUST_CHARTER.md)

## Governance Principles
- The Markdown repository is the product and architecture source of truth.
- New ideas are captured without automatically becoming active work.
- The approved roadmap governs sprint selection.
- Major scope changes require explicit roadmap review before sprint activation.
- Every sprint must have one primary objective.
- Platform capabilities are preferred over isolated features.
- Current implementation status must never be overstated.
- Future detail should be added only when decisions are sufficiently mature.
- Active work must be traceable to an approved roadmap item.

## Work-Item Lifecycle
Work items move through one controlled progression:

Idea
→ Candidate
→ Roadmap
→ Backlog
→ Sprint
→ Done

### Idea
Purpose:
Capture a possible product, platform, UX, workflow, or operational need without scheduling it.

Entry criteria:
- a new problem, request, gap, or opportunity is identified
- the concept is concrete enough to describe in plain language

Exit criteria:
- discarded as out of scope, duplicate, or not aligned
- promoted to Candidate for review

Decision owner:
- product owner or roadmap owner

Required documentation:
- concise idea note in the appropriate roadmap, epic, or governance backlog context

### Candidate
Purpose:
Hold a plausible future work item that merits evaluation but is not yet approved.

Entry criteria:
- problem statement exists
- product relevance is understood at a high level
- obvious conflicts or duplicates are reviewed

Exit criteria:
- promoted to Roadmap
- held as unresolved
- rejected explicitly

Decision owner:
- product owner with architecture input where needed

Required documentation:
- candidate summary
- rough value statement
- rough non-goals or exclusions where obvious

### Roadmap
Purpose:
Represent approved capability direction.

Entry criteria:
- roadmap review completed
- item fits product direction and 1.0 boundaries
- business or platform value is understood

Exit criteria:
- moved into Backlog for planning
- paused explicitly
- removed by roadmap review

Decision owner:
- product owner
- architecture owner when platform or boundary changes are involved

Required documentation:
- placement in [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) and/or [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)
- responsibility alignment with [EPICS.md](EPICS.md) where implementation planning is needed

### Backlog
Purpose:
Prepare approved work for future sprint selection without activating it.

Entry criteria:
- roadmap alignment is explicit
- major dependencies are known
- scope boundaries are understood well enough for planning

Exit criteria:
- meets Definition of Ready
- selected into Sprint
- returned to Roadmap or paused

Decision owner:
- product owner for backlog priority
- engineering/architecture leads for sequencing and dependency review

Required documentation:
- epic or sprint planning anchor in [EPICS.md](EPICS.md)
- dependency and compatibility notes when needed

### Sprint
Purpose:
Execute one approved objective with explicit scope, non-goals, validation, and documentation updates.

Entry criteria:
- Definition of Ready is satisfied
- one clear objective is named
- sprint is traceable to approved roadmap work

Exit criteria:
- Definition of Done is satisfied
- scope is closed or explicitly carried forward

Decision owner:
- product owner and engineering lead

Required documentation:
- sprint objective and scope anchor in [EPICS.md](EPICS.md)
- status updates in [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- historical entry in [RELEASE_NOTES.md](RELEASE_NOTES.md) when user-visible

### Done
Purpose:
Record completed, validated, and documented work.

Entry criteria:
- implementation or documentation change is complete
- validation is complete
- status and history are reconciled

Exit criteria:
- none; Done is terminal unless later refinement opens a new work item

Decision owner:
- engineering lead confirms implementation completion
- product owner confirms scope acceptance

Required documentation:
- closed sprint or epic status in [EPICS.md](EPICS.md)
- current-state update in [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- historical note in [RELEASE_NOTES.md](RELEASE_NOTES.md) where applicable

## Progressive Refinement Model
Atlas develops breadth before depth.

That means Atlas should:
1. work toward the complete approved 1.0 capability map
2. establish a minimal stable foundation across each required product area
3. return to the beginning for a planned refinement pass
4. repeat horizontal refinement passes until approved 1.0 capabilities meet release criteria
5. avoid driving one subsystem to excessive depth while major 1.0 areas remain absent

This principle does not permit weak foundations.

The following remain mandatory in every pass:
- security
- tenant isolation
- data ownership
- deterministic behavior
- auditability
- backward compatibility

## Roadmap Discipline
Roadmaps approve direction. They do not automatically schedule execution.

Responsibilities:
- [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) defines approved customer-facing capability horizons.
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md) defines technical sequencing and engineering gates.
- [EPICS.md](EPICS.md) owns epic and sprint status.
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) owns current implementation status.
- [RELEASE_NOTES.md](RELEASE_NOTES.md) is historical only.

Rules:
- ideas are not scheduled merely because they are documented
- active work must map back to an approved roadmap item
- paused items remain visible but must not be described as active
- major scope changes require explicit roadmap review before sprint activation

## Atlas 1.0 Capability Map
Atlas 1.0 should cover the approved major capability areas below, without speculative subfeature expansion.

Required major areas:
- Projects and lifecycle
- Knowledge
- Transactions
- Commercial documents
- Settings and tenant configuration
- Search and object navigation
- Reporting
- Security and tenant isolation
- Auditability
- Integrations foundation
- User and role administration
- Required operational workflows

This capability map is intentionally concise.
Detailed subsystem design belongs in the owning architecture and domain documents once decisions mature.

## Product Hardening Backlog
These areas are captured for governance and sequencing, but are not activated merely by appearing here.

### Required for 1.0
- Permissions and roles
- Audit engine
- Attachments

### Candidate for 1.0
- Background jobs
- Notifications
- Document generation
- Search refinement
- Settings refinement

### Post-1.0
- none are declared here beyond currently approved documentation boundaries

## ADR Governance
An Architecture Decision Record is required when work proposes any of the following:
- new system of record
- persistence change
- tenancy model change
- security boundary change
- external integration ownership change
- major domain-model change
- replacement of an authoritative engine
- irreversible migration
- significant roadmap change

Historical ADRs should not be created retroactively unless the repository already contains enough evidence to document them accurately.

## Open Governance Decisions
- whether Atlas should maintain a dedicated ADR directory now or wait until the first qualifying forward-looking decision arises
- whether future pause/resume states should be standardized visually across roadmap and epic documents beyond the rules defined here
- whether release-review signoff should be documented as a lightweight checklist inside sprint closeout or as a separate reusable template

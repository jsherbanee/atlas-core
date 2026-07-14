# Atlas Scrum Process

## Purpose
This document defines the Scrum process Atlas uses to select, prepare, execute, validate, and close work.

It standardizes terminology so sprint planning, execution, and closeout remain consistent with the roadmap and product-governance model.

## Related Documents
- [PRODUCT_GOVERNANCE.md](PRODUCT_GOVERNANCE.md)
- [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)
- [EPICS.md](EPICS.md)
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [TRUST_CHARTER.md](TRUST_CHARTER.md)

## Core Scrum Artifacts
### Product Backlog
The Product Backlog is the ordered list of approved future work that is eligible for refinement and later sprint selection.

Atlas interpretation:
- it must be traceable to the approved roadmap
- it may include platform, architecture, UX, and workflow work
- it does not imply sprint activation

### Sprint Backlog
The Sprint Backlog is the scoped set of work selected for one sprint objective.

Atlas interpretation:
- it must support one primary objective
- it must include explicit non-goals
- it must include validation and documentation obligations

### Sprint Objective
The Sprint objective is the single primary outcome the sprint is intended to achieve.

Atlas rule:
- every sprint has one primary objective
- secondary improvements are allowed only if they are directly required to complete the objective

## Supporting Reviews and Ceremonies
### Backlog Refinement
Backlog refinement prepares approved work for future sprint selection.

Output:
- clearer objective
- dependencies identified
- acceptance criteria improved
- non-goals stated
- documentation targets identified

### Architecture Review
Architecture review is required when work affects boundaries, persistence, tenancy, security, systems of record, or major domain contracts.

Output:
- architecture accepted as-is
- architecture changes requested
- ADR required
- scope deferred

### Sprint Review
Sprint review confirms whether the approved sprint objective was met and whether the scope matches what was promised.

Output:
- accepted
- partially accepted with documented remaining debt
- not accepted and returned for follow-up

### Retrospective
Retrospective captures process improvements, planning mistakes, validation gaps, and handoff friction.

Output:
- improvements to planning, validation, or documentation discipline

### Release Review
Release review confirms that completed work is ready to be represented as current state or historical release record.

Output:
- status documents updated
- release notes updated where appropriate
- blocking regressions or readiness concerns documented

## Definition of Ready
A work item is Ready for sprint selection only when all of the following are true:
- roadmap alignment is explicit
- one clear objective is defined
- dependencies are understood
- non-goals are explicit
- acceptance criteria exist
- security and tenant-impact review has been considered
- compatibility review has been considered
- documentation targets are listed
- test strategy is defined

Atlas interpretation:
- Ready means sufficiently understood to execute responsibly
- Ready does not mean every implementation detail is predetermined

## Definition of Done
A sprinted work item is Done only when all of the following are true:
- approved scope is implemented
- tests are passing
- quality gates are passing
- manual validation is complete where applicable
- documentation is reconciled
- no known blocking regressions remain
- remaining debt is documented
- scoped commit is created
- roadmap and status documents are updated

Atlas interpretation:
- Done requires implementation accuracy and documentation accuracy
- Done is not satisfied by code changes alone

## Sprint Flow
1. Select a roadmap-aligned backlog item.
2. Confirm Definition of Ready.
3. Activate a sprint with one primary objective.
4. Execute the scoped work.
5. Validate against tests, gates, manual checks, and documentation updates.
6. Conduct sprint review and retrospective.
7. Update status and historical records.
8. Close the sprint as Done.

## Role Expectations
### Product Owner
Owns:
- roadmap alignment
- backlog priority
- objective approval
- scope acceptance

### Engineering Lead
Owns:
- technical sequencing
- execution readiness
- quality gates
- implementation completion
- documented debt visibility

### Architecture Owner
Owns:
- boundary review
- ADR determination
- system-of-record decisions
- major contract and tenancy review

## Consistency Rules
- Product Roadmap is customer-facing and approval-oriented.
- Engineering Roadmap is technical and sequencing-oriented.
- EPICS.md is implementation planning and sprint-status oriented.
- DEVELOPMENT_STATUS.md is current-state oriented.
- RELEASE_NOTES.md is historical.
- Scrum terms should be used consistently with those document responsibilities.

## Open Process Decisions
- whether future sprint retrospectives should be documented in-repo or kept lightweight outside the product-doc set
- whether release review should become mandatory for all documentation-only sprints or only for state-changing milestones

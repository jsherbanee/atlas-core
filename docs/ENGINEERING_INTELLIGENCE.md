# Atlas Engineering Intelligence

## Related Documents
- [README.md](README.md)
- [ENGINEERING_RESOLVER.md](ENGINEERING_RESOLVER.md)
- [ENGINEERING_WORKBENCH.md](ENGINEERING_WORKBENCH.md)
- [COORDINATION_INTELLIGENCE.md](COORDINATION_INTELLIGENCE.md)
- [DRAWING_INTELLIGENCE.md](DRAWING_INTELLIGENCE.md)
- [SPECIFICATION_INTELLIGENCE.md](SPECIFICATION_INTELLIGENCE.md)

## Purpose
Sprint 8 introduces deterministic engineering decision support for Atlas.

Atlas Engineering Intelligence is designed to answer:
- What is risky?
- What is missing?
- What is inconsistent?
- What should be reviewed next?
- Where did this recommendation come from?

This capability is local, deterministic, and traceable.

## Insight Engine
Implementation:
- atlas_core/services/engineering_insights_service.py

Primary engine input:
- BidPackageReview
- Plan Review Readiness
- Estimator Brief
- RFI Candidates
- Labor Estimate
- Revision Comparison
- Knowledge Graph (nodes/edges)

Generated output:
- Engineering insights
- Insight priority ranking
- System health metrics
- Project health model
- Deterministic recommendations

Insight payload fields:
- insight_id
- category
- severity
- confidence
- title
- description
- recommended_action
- supporting_objects
- evidence_refs
- created_by_engine_version
- priority

Supported categories:
- Missing Information
- Scope Conflict
- Specification Conflict
- Drawing Conflict
- Labor Risk
- Procurement Risk (advisory)
- Schedule Risk (advisory)
- Revision Impact
- Coordination Issue
- Engineering Assumption
- Code / Standards Reminder
- General Recommendation

## Prioritization
Prioritization is deterministic.

Priority levels:
- Critical
- High
- Medium
- Low

Ranking factors:
- severity
- confidence
- relationship count
- affected systems
- affected drawings
- existing blockers

## Project Health
Project Health is separate from Readiness.

Readiness:
- Can I estimate?

Health:
- How healthy is the engineering package?

Score range:
- 0 to 100

Weighted health categories:
- Engineering Completeness
- Package Consistency
- Cross-Object Coordination
- Estimating Confidence
- Revision Stability

Each category includes rationale text and weighted contribution.

## Engineering Health
System-level engineering health is generated for each system.

System Health fields:
- health_score
- confidence
- equipment_completeness
- specification_coverage
- drawing_coverage
- outstanding_rfis
- outstanding_assumptions
- labor_confidence
- warnings

## Recommendations
Recommendations are deterministic and traceable.

Example recommendation patterns:
- Review drawing before final estimate.
- Verify mounting detail assumptions.
- Confirm OFCI responsibility.
- Resolve missing manufacturer/model.
- Review conflicting quantity/scope references.

Each recommendation includes:
- recommended action
- supporting objects
- evidence refs

## Relationship Analysis
Cross-object deterministic checks include:
- equipment referenced by many drawings but missing specification
- specification sections without drawing-linked products
- systems with incomplete equipment
- rooms with missing devices
- drawings without specification linkage
- evidence nodes with weak relationship links

These checks create insights and recommendations with explicit traceability.

## Workspace Integration
Engineering Intelligence is a first-class workspace page.

Dashboard sections include:
- Top Engineering Insights
- Critical Risks
- Coordination Issues
- High-Risk Systems
- Most Referenced Drawings
- Most Referenced Specifications
- Top Equipment Risks
- Highest Confidence Recommendations

UI controls include:
- severity/category filters
- sorting
- grouping by Severity, Category, System, Drawing, Specification

## Non-Goals
This sprint does not implement:
- LLM reasoning
- Generative AI
- Procurement execution
- Financial workflows
- Construction workflows
- Closeout workflows
- Service workflows
- Cloud persistence
- Authentication
- Database persistence

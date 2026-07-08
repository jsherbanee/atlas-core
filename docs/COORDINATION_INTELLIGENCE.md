# Coordination Intelligence

## Purpose

Sprint 15 introduces deterministic coordination intelligence for Atlas. The engine identifies where drawings, specifications, equipment references, systems, and requirement candidates agree, conflict, or leave gaps.

The output is advisory only and estimator-facing. It is not used for procurement, lifecycle automation, or customer-facing deliverables.

## Architecture

- Engine: `atlas_core/services/coordination_intelligence/engine.py`
- Models: `atlas_core/services/coordination_intelligence/models.py`
- Workspace integration: `apps/phase2_review_app.py`

The coordination engine consumes workspace object rows and emits:

- `CoordinationFinding`
- `CoordinationIssue`
- `CoordinationSummary`
- `CoordinationIntelligenceResult`

## Model Types

The model surface includes the required Sprint 15 types:

- `CoordinationIntelligenceEngine`
- `CoordinationIssue`
- `CoordinationFinding`
- `CoordinationCategory`
- `CoordinationSeverity`
- `CoordinationConfidence`
- `CoordinationEvidence`
- `CoordinationSummary`

## Deterministic Categories

Current deterministic checks include:

- Drawing-specification alignment
- Equipment-specification alignment
- System coordination
- Requirement candidate coverage
- RFI coordination signals
- Assumption traceability
- Evidence traceability

Each finding records category, severity, confidence band, related objects, and recommended action.

## Severity and Confidence

- Severity levels: `critical`, `high`, `medium`, `low`
- Confidence bands: `high`, `medium`, `low`

Summary aggregates counts by category, severity, and confidence. Summary also tracks conflict/gap/agreement counts and top recommended actions.

## Workspace and Graph Integration

Coordination intelligence is integrated into workspace object payloads:

- `coordination_findings`
- `coordination_issues`
- `coordination_summary`
- `coordination_confidence`

Graph integration adds:

- `Coordination Finding` nodes
- `Coordination Issue` nodes
- Edges from findings to related objects where available:
  - Drawing
  - Specification
  - Equipment
  - System
  - RFI candidate
  - Engineering assumption
  - Evidence

## UI Surfaces

Sprint 15 coordination outputs are exposed in:

- Engineering Workbench (coordination panel + metric)
- Engineering Intelligence (coordination summary section)
- Coordination Review page
- Readiness and Estimator Brief pages (coordination advisory signals)
- Reports page (estimator-facing coordination report summary)

## Boundaries

- Deterministic only. No LLM dependencies.
- Advisory only. No automatic resolution or workflow mutation.
- No customer-facing report language.
- No lifecycle or procurement execution behavior.

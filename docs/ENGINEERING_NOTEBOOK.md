# Engineering Notebook

## Purpose
The Engineering Notebook is the authoritative workspace for engineering observations, assumptions, clarifications, and decisions made during plan/spec review. It is scoped to technical review activity and traceability.

This module is intentionally not a project management system, issue tracker, procurement workflow, or financial workflow.

## Entry Model
Each notebook entry supports the following fields:

- entry_id: stable note identifier
- created_at: ISO timestamp
- author: entry author label
- title: short summary
- body: detailed engineering context
- entry_type: one of the supported entry categories
- priority: Critical, High, Medium, Low
- status: Open, In Review, Resolved, Approved
- related_objects: object references in Atlas object-id format
- evidence_refs: evidence links to source artifacts
- tags: freeform labels for filtering and retrieval
- created_by_engine_version: Atlas engine build marker for generated entries
- read_only: true for system-generated entries
- system_generated: true for Atlas-generated entries

## Supported Entry Types
Supported categories are:

- Engineering Note
- Observation
- Decision
- Assumption
- Question
- Follow-up
- Customer Clarification
- Consultant Clarification
- Internal Coordination
- Site Visit
- Meeting Note
- Review Summary

## Atlas-Generated Entries
The system generates read-only notebook entries from deterministic milestones:

- Engineering resolver execution
- Estimator brief generation
- Revision comparison activity
- Coordination review summary

Generated entries include related object references, tags, and confidence/trace context where available. They are immutable by design.

## Decision Log
Decision Log behavior is implemented as a filtered view of notebook entries where one of the following is true:

- entry_type is Decision
- status is Approved
- tags include Approved Assumption or Resolved Clarification

This keeps decision history in one data model while preserving a focused engineering decision surface.

## Investigation Journal Integration
From Engineering Workbench Investigation Mode, users can create an investigation note pre-linked to the active object. This captures context while the investigation is active and preserves object traceability.

## Search and Filtering
Notebook views support filtering by:

- full-text search across entry content
- entry type
- tags
- linked object references
- date window using entry creation date

## Timeline Integration
Notebook entries are merged into the Engineering Activity Timeline alongside revision and review milestones. This creates a chronological activity history across analysis, decisions, and evidence-driven findings.

## Object Linking and Click-Through
Notebook references use stable Atlas object identifiers (for example drawing:<id>, spec:<id>, resolver_conflict:<id>). Linked-object actions open the corresponding page and apply context selection so users can continue analysis without manual re-navigation.

## Context Panel Integration
When a notebook entry is selected, the Context Panel displays:

- entry metadata
- tags and status
- linked objects with open actions
- navigation shortcuts to Engineering Notebook and Timeline

## Phase 2 Boundaries
The Engineering Notebook for Atlas Preview 0.5 includes only deterministic, local, engineering-review functionality.

Excluded from scope:

- Multi-user editing and collaboration workflows
- Comments, threaded discussions, approvals routing, or notifications
- Assignment or task orchestration features
- Procurement, financial, lifecycle, or construction execution workflows
- Cloud sync, authentication, or external system dependencies

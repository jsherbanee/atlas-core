# Rule Engine

## Purpose
This document defines the deterministic rule-engine architecture for Atlas.

AI may explain deterministic rule outputs, but AI must not silently replace deterministic business rules.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ENGINEERING_INTELLIGENCE.md](ENGINEERING_INTELLIGENCE.md)
- [COORDINATION_INTELLIGENCE.md](COORDINATION_INTELLIGENCE.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)

## Core Principles
- Rules should be deterministic.
- Rule evaluation should be reproducible.
- Rule outputs should be auditable.
- Rule inputs should be explicit.
- Rule families should be identifiable and versioned.
- Rule families should be extendable without scattering ad hoc conditionals.

## Rule Registry
The registry should own:
- rule families
- rule IDs
- versions
- enabled/disabled status
- applicability metadata
- effective dates
- tenant or organization overlays

## Rule Families
Representative families may include:
- engineering checks
- coordination checks
- estimating checks
- pricing policy checks
- completeness checks
- workflow gating rules
- organization policy overlays

## Evaluation Context
Each rule should receive an explicit evaluation context that can include:
- tenant
- organization
- project
- object graph references
- documents and evidence
- current revision state
- user or role context when appropriate
- effective dates and policy overlays

## Ordering And Conflict Handling
Rules should have deterministic ordering when ordering matters.

If rules conflict, the system should emit diagnostics and preserve the evidence for both outcomes rather than silently discarding one.

## Inputs And Outputs
Inputs may include structured objects, repository-backed records, graph references, and document metadata.

Outputs may include:
- findings
- recommendations
- assumptions
- warnings
- gating decisions
- diagnostics
- audit records

## Reproducibility And Replay
Rule evaluation should be replayable against the same inputs and rule version set.

Replay support is important for audits, support, and historical troubleshooting.

## Organization Policy Overlays
Organizations may need tenant-specific policy overlays such as:
- preferred manufacturers
- approved workflow variants
- local business rules
- thresholds and acceptance criteria
- disabled rule families

Policy overlays should remain explicit and scoped.

## Diagnostics
Diagnostics should record:
- rule ID
- rule version
- input context summary
- decision path
- evidence references
- conflict notes
- recommendation text
- replay information

## Testing
Rule-engine testing should cover:
- deterministic output
- version changes
- conflict handling
- disabled rules
- policy overlays
- replay consistency
- boundary conditions

## Extension Patterns
New rules should be added through registry-driven extensions rather than embedded one-off conditionals.

This keeps the system testable and easier to reason about.

## AI Interaction
Future AI may explain why a deterministic rule fired, summarize supporting evidence, or draft human-readable narratives.

AI should not silently substitute its own judgment for the registered deterministic rule output.

## Unresolved Decisions
- final rule authoring format remains open
- final rule storage model remains open
- final policy overlay granularity remains open
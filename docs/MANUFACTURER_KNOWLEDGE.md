# Manufacturer Knowledge

## Purpose
This document defines the future architecture for manufacturer-specific technical knowledge in Atlas.

It is distinct from [MANUFACTURER_REGISTRY.md](MANUFACTURER_REGISTRY.md), which owns identity and classification.

## Related Documents
- [MANUFACTURER_REGISTRY.md](MANUFACTURER_REGISTRY.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [STANDARDS_LIBRARY.md](STANDARDS_LIBRARY.md)
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [SECURITY.md](SECURITY.md)

## Scope
Manufacturer Knowledge should own sourced technical material such as:
- manuals
- design guides
- application notes
- compatibility notes
- accessories
- firmware
- software
- licensing
- network requirements
- control APIs
- power requirements
- thermal requirements
- topology guidance
- commissioning procedures
- troubleshooting notes
- service guidance
- warranty notes
- lifecycle status
- replacement products
- training references

## Core Principles
- source provenance should be explicit
- licensing should be respected
- versioning should be preserved
- product and firmware applicability should be tracked
- supersession should be recorded
- tenant-approved sources should be respected
- neutrality should be maintained
- product-specific questions should prefer manufacturer documentation over generic assumptions

## Source Provenance
Each knowledge item should record:
- manufacturer
- source title
- source type
- version or revision
- product model applicability
- firmware applicability where relevant
- publication date
- access restrictions
- licensing status
- ingestion date
- verification status

## Licensing And Access
Atlas should only use manufacturer material that is legally and contractually permitted for the tenant or organization.

Restricted or unauthorized content must not be ingested or redistributed.

## AI Usage
AI may use manufacturer knowledge to explain compatibility, setup, commissioning, and service behavior.

AI should not fabricate manufacturer claims or present unsupported compatibility conclusions.

## Conflict Handling
When manufacturer sources conflict:
- prefer the most applicable and most recent verified source
- surface the conflict clearly
- preserve both sources in provenance metadata where appropriate
- avoid silently choosing a winning source without rationale

## Neutrality
Manufacturer Knowledge should not become a sales channel.

Recommendations should be driven by project requirements, supportability, lifecycle, and evidence.

## Future Direction
Manufacturer Knowledge should eventually support tenant-specific approved sources, versioned applicability, and relationships to standards and product-resolution workflows.

## Unresolved Decisions
- final source ingestion workflow remains open
- final conflict-resolution policy remains open
- final tenant approval workflow remains open
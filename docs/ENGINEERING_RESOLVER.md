# Engineering Resolver

## Purpose
The Engineering Resolver provides deterministic normalization and conflict-resolution support across drawing/specification/equipment/system data.

It is responsible for surfacing canonical values, confidence signals, and conflict rows that feed downstream engineering intelligence and workspace investigation.

## Audience
- Resolver and rule-engine contributors
- Engineering-intelligence contributors
- Workspace contributors

## When to Reference
- When changing canonicalization rules.
- When adding new conflict classes.
- When modifying resolver confidence and conflict-status semantics.

## Current Role in Atlas
- Supplies resolver conflict rows for investigation workflows.
- Provides deterministic resolution outputs consumed by intelligence surfaces.
- Maintains traceability to source evidence and related objects.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ENGINEERING_INTELLIGENCE.md](ENGINEERING_INTELLIGENCE.md)
- [ENGINEERING_WORKBENCH.md](ENGINEERING_WORKBENCH.md)
- [COORDINATION_INTELLIGENCE.md](COORDINATION_INTELLIGENCE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)

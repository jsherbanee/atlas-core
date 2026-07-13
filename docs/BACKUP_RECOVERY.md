# Backup and Recovery

## Purpose
This document defines backup and recovery architecture for Atlas.

It intentionally avoids inventing committed SLA values, recovery point objectives, or recovery time objectives.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- [SECURITY.md](SECURITY.md)
- [OBSERVABILITY.md](OBSERVABILITY.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)

## Backup Scope
Backups should consider:
- relational data
- object storage
- configuration
- audit data
- integration metadata
- search/index data where necessary
- project repository state

## Recovery Policy Questions
Future policy should define:
- recovery point objectives
- recovery time objectives
- backup frequency
- retention windows
- verification cadence
- restoration approval procedures

Those values remain future policy decisions.

## Versioning
Recovery design should preserve versioned records and historical project state wherever practical.

## Cross-Region Considerations
Future architecture may consider cross-region resilience or replication, but this document does not prescribe a final topology.

## Restoration Testing
Recovery should include regular restoration testing to confirm:
- backup integrity
- tenant-safe restoration behavior
- metadata integrity
- version preservation
- access-control correctness after restore

## Tenant-Level Export
Tenant export should be considered alongside backup and recovery so customer data can be retained, exported, or transitioned according to policy.

AI conversation retention and export behavior should follow [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

## Accidental Deletion
Recovery architecture should handle accidental deletion of:
- project data
- documents
- configuration
- integration metadata
- audit records where policy permits restoration

## Ransomware Considerations
Recovery design should anticipate:
- immutable or protected backups where practical
- offline or isolated recovery options
- recovery verification before reintroducing data
- tenant-safe restoration validation

## Disaster Recovery
Disaster recovery planning should be documented separately when production deployment details are finalized.

## Local Development Recovery
Local development should remain recoverable through deterministic repository and fixture handling.

## Immutable Project Bundles
Immutable project bundles remain useful for reproducible recovery, diagnostics, and support even when full production backup strategies are more advanced.

## Unresolved Decisions
- final backup storage implementation remains open
- final DR topology remains open
- final recovery objectives remain policy-driven
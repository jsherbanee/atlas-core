# Import Pipeline

## Purpose
This document defines the desired common architecture for Atlas document and data ingestion.

It reconciles current project document intake, commercial price-sheet intake, and future ingestion flows for service documents and correspondence without claiming that every flow already shares one implementation.

## Related Documents
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [SECURITY.md](SECURITY.md)
- [REPORTING.md](REPORTING.md)
- [SEARCH_ARCHITECTURE.md](SEARCH_ARCHITECTURE.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)

## Scope
The import pipeline should support:
- project document intake
- commercial price-sheet intake
- future service document intake
- future correspondence ingestion

Current adapters and flows may differ by content type, but the desired architecture should converge on shared stages where practical.

## Desired Pipeline Stages
1. Upload
2. Quarantine
3. Safety validation
4. File classification
5. Archive inspection
6. Hashing
7. Duplicate detection
8. Metadata extraction
9. Text extraction
10. OCR fallback
11. Table extraction
12. Normalization
13. Validation
14. Preview
15. User correction
16. Finalization
17. Indexing
18. Source provenance capture
19. Diagnostics
20. Retry and partial success handling
21. Versioning
22. Tenant isolation enforcement
23. Malicious file handling
24. Asynchronous future processing

## Architectural Principles
- Imported content should be tracked from original source to normalized record.
- Tenant boundaries must be enforced before finalization and indexing.
- Duplicate detection should be deterministic and explainable.
- Quarantine should prevent unsafe or unverified files from being treated as trusted inputs.
- Preview and user correction should be available where structured import is possible.
- Partial success should preserve valid inputs while surfacing rejected items and diagnostics.
- Future async processing should not break deterministic diagnostics or versioned source tracking.

## Common Architecture
A common architecture should eventually include:
- source intake adapters
- a quarantine and safety stage
- content-classification services
- extraction services for text, tables, and metadata
- normalization and validation services
- provenance and diagnostics models
- finalization and indexing adapters
- retry and replay support

## Existing Adapters And Flows
Current repository-backed flows already support deterministic project intake and commercial import behavior through existing repository and service layers.

Those flows should be treated as implementation-specific adapters rather than evidence that all future import types share one code path.

## Safety And Malicious File Handling
Import handling should consider:
- archive traversal and extraction safety
- invalid or malformed office/PDF content
- file-size and type restrictions
- suspicious executable or script content
- quarantine before trust
- tenant-safe failure reporting

## Diagnostics
Import diagnostics should record:
- severity
- source file or page reference
- classification result
- extraction issue
- normalization issue
- validation issue
- duplicate or superseded state
- retry guidance
- final disposition

## Versioning And Reprocessing
Versioning should preserve:
- source identity
- normalized record identity
- historical revisions
- provenance metadata
- supersession state

Reprocessing should be deterministic and should not overwrite historical facts without explicit version management.

## Future Direction
The desired architecture is a unified ingestion framework with content-type specific adapters for documents, price sheets, correspondence, and service artifacts.

## Current P-03 Execution Note
Sprint P-03 introduces deterministic background-job orchestration for representative import/export workflows.

Current implementation posture:
- local in-process job execution
- repository-backed job state
- deterministic retry/cancel/list semantics

Explicitly out of scope in the current pipeline implementation:
- external queue infrastructure
- external worker deployment

## Unresolved Decisions
- exact extraction stack remains flexible
- final OCR strategy remains open
- final table extraction stack remains open
- final async job model remains open
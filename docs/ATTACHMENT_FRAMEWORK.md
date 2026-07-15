# Unified Attachment Framework

## Purpose
This document defines the Sprint P-04 unified attachment framework for tenant-scoped file attachments across Atlas object families.

## P-05 Integration Note

Sprint P-05 document generation records deterministic output artifact metadata in commercial document attachment payloads.
This aligns generated export artifacts with the unified attachment model and preserves template/version provenance alongside output hashes for traceable retrieval workflows.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [OBJECT_WORKSPACE.md](OBJECT_WORKSPACE.md)
- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
- [SECURITY.md](SECURITY.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [AUDIT_ENGINE.md](AUDIT_ENGINE.md)
- [BACKGROUND_JOBS.md](BACKGROUND_JOBS.md)

## Scope
P-04 introduces one shared attachment domain and orchestration layer that can be reused by Project, Knowledge, Transactions, and Object Workspace surfaces.

Implemented in P-04:
- attachment contracts for metadata, versions, links, access decisions, diagnostics, activities, and record lifecycle
- unified attachment service for upload, versioning, linking, unlinking, archive/restore, and deterministic read/download
- tenant-scoped attachment repository contract and local adapter
- deterministic hash-based duplicate reuse behavior with link fan-out
- immutable append-only version model
- Object Workspace Documents integration for attachment listing and actions
- compatibility adapter that registers legacy project documents as unified attachments

Explicitly out of scope in P-04:
- cloud object-store adapters
- background worker execution
- malware scanning engines
- OCR or content extraction from attachment service

## Core Contracts
Primary contracts are defined in `atlas_core/contracts/attachment_contracts.py`.

Key entities:
- `AttachmentRecord`
- `AttachmentVersion`
- `AttachmentMetadata`
- `AttachmentLink`
- `AttachmentActivity`
- `AttachmentAccessDecision`
- `AttachmentDiagnostic`

Status entities:
- `AttachmentStatus` (`active`, `archived`)
- `AttachmentScanStatus` (`not_requested`, `pending`, `passed`, `failed`)

## Service Model
`AttachmentService` in `atlas_core/services/attachment_service.py` is the orchestrator for:
- upload and duplicate detection
- version creation
- attachment/object linking and unlinking
- archive and restore operations
- version reads/download payload retrieval

Service behavior:
- deterministic IDs for attachment/version/link/activity
- hash plus size duplicate matching
- immutable version append semantics
- permission-aware operation checks through `AttachmentAccessDecision`
- audit callback emission for attachment lifecycle actions
- background-hook request emission for scan/preview/indexing triggers

## Repository Model
Repository contract:
- `AttachmentRepository` in `atlas_core/repository/contracts.py`

Local adapter:
- `LocalAttachmentRepository` in `atlas_core/repository/local.py`

Local storage layout:
- `AtlasProjects/.atlas_attachments/<tenant_id>/<organization_id>/attachments.jsonl`
- `AtlasProjects/.atlas_attachments/<tenant_id>/<organization_id>/links.jsonl`
- `AtlasProjects/.atlas_attachments/<tenant_id>/<organization_id>/activity.jsonl`
- `AtlasProjects/.atlas_attachments/<tenant_id>/<organization_id>/blobs/...`

## Workspace And UI Integration
`ProjectWorkspaceService` exposes attachment wrappers for object-scoped attachment APIs and a compatibility function that links existing project documents into the unified attachment model.

`apps/phase2_review_app.py` Object Workspace Documents view now:
- shows unified attachment rows when available
- supports open/download, archive/restore, and unlink actions
- enforces permission-aware attachment decisions
- preserves legacy source-reference rendering for compatibility

## Security And Governance
Security controls in P-04 include:
- tenant and organization scope enforcement
- filename safety rules and prohibited credential-like filename patterns
- allowed MIME type and extension constraints
- size limits and empty-payload rejection

Data-governance controls include:
- immutable version history per attachment
- explicit provenance fields (`source`, `source_reference`)
- activity history with audit linkage

## Audit And Background Hooks
Attachment actions emit immutable audit events when project context is available, including representative actions:
- `attachment.uploaded`
- `attachment.version.created`
- `attachment.linked`
- `attachment.unlinked`
- `attachment.archived`
- `attachment.restored`
- `attachment.downloaded`

Background-hook requests are emitted for:
- `malware_scan`
- `preview_generation`
- `search_indexing`

Current execution remains callback-based and deterministic; external worker infrastructure is deferred.
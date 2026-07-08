# Atlas Project Repository

## Related Documents
- [README.md](README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [MASTER_LIBRARY.md](MASTER_LIBRARY.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [ROADMAP.md](ROADMAP.md)

## Overview
Sprint 9 introduced the Atlas Project Repository as the persistence layer for Atlas Workspace.

Sprint 10 hardens the repository interfaces to prepare for cloud-ready storage adapters without implementing cloud services.

Goals:
- Persist projects independently of the running session.
- Keep storage deterministic and portable.
- Decouple workspace logic from storage implementation using repository contracts.
- Enable future cloud adapters without changing workspace code paths.

Out of scope:
- AWS/S3
- Databases
- Authentication
- Collaboration

## Repository Architecture
Atlas uses adapter contracts in atlas_core/repository/contracts.py and local filesystem adapters in atlas_core/repository/local.py.

Contracts:
- ProjectRepository
- WorkspaceRepository
- DocumentRepository
- ReviewRepository
- KnowledgeRepository
- HistoryRepository

Storage-agnostic contract behavior:
- Callers work with project identifiers and storage locations (string references), not filesystem internals.
- Manifest, health check, and bundle operations are contract-level repository operations.
- Adapter implementations can map storage locations to local paths, object keys, or database references.

Current adapter implementation:
- LocalProjectRepository
- LocalWorkspaceRepository
- LocalDocumentRepository
- LocalReviewRepository
- LocalKnowledgeRepository
- LocalHistoryRepository

The service layer consumes an orchestrator (AtlasProjectManager in atlas_core/repository/project_manager.py) that composes all adapters.

Workspace integration is done by atlas_core/services/project_workspace_service.py, which now uses repository adapters instead of legacy outputs/project_workspaces records.

## Directory Layout
Projects are stored under:
- AtlasProjects/<project_id>/

Directory structure:

- AtlasProjects/
  - <project_id>/
    - project.json
    - metadata.json
    - workspace.json
    - project_manifest.json
    - intake/
    - documents/
      - drawings/
      - specifications/
      - schedules/
      - addenda/
      - images/
      - other/
    - review/
      - bid_package_review.json
      - readiness.json
      - estimator_brief.json
      - engineering_intelligence.json
      - labor_estimate.json
      - revision_comparison.json
      - rfi_candidates.json
      - knowledge_graph.json
    - exports/
    - history/
      - events.jsonl
    - cache/

## Canonical Manifest
Each project includes project_manifest.json with deterministic storage summary fields:

- project_id
- project_name
- owner
- status
- lifecycle_stage
- created_at
- updated_at
- last_opened_at
- atlas_version
- schema_version
- storage_version
- document_counts
- review_artifact_counts
- intelligence_artifact_counts
- history_event_count
- checksum_summary

Manifest notes:
- schema_version currently starts at 1.0.
- storage_version currently starts at 1.0.
- checksum_summary includes deterministic checksums for core payloads and content trees where practical.

## Persisted Data
project.json:
- Core project domain payload (id, name, client, status, etc.)

metadata.json:
- project name
- owner
- consultant
- architect
- engineers
- project number
- issue date
- bid date
- status
- lifecycle stage
- creation date
- last opened
- last modified
- atlas version
- pinned/reference/archive flags

workspace.json:
- Workspace record envelope
- Source mode/path fields
- Import summary and warnings
- Workspace state

review/*.json:
- Deterministic review outputs and intelligence artifacts

history/events.jsonl:
- Project timeline events (project_created, documents_imported, workspace_opened, review_executed, etc.)

project_manifest.json:
- Canonical deterministic repository summary for health checks, bundle validation, and future adapter migration.

## Workspace State Persistence
Atlas persists the following state to workspace.json:
- last open page
- selected drawing
- selected specification
- expanded navigation group
- filters
- search state
- window preferences
- context selection

On load, the workspace restores this state so the user returns to their last working context.

## Project Manager Operations
Project manager actions are repository-backed:
- Create Project
- Open Project
- Rename Project
- Archive Project
- Delete Project
- Duplicate Project
- Recent Projects
- Pinned Projects
- Reference Projects

Additional storage operations:
- Export Project Bundle (.atlaspkg)
- Import Project Bundle (.atlaspkg)
- Project Health Check

These actions are surfaced in the workspace UI and routed through ProjectWorkspaceService.

## Portable Bundle Format
Atlas supports portable bundle export/import using the .atlaspkg extension.

Bundle behavior:
- .atlaspkg is a ZIP archive with the full project directory tree.
- Bundle preserves metadata, documents, intake, review artifacts, knowledge graph, workspace state, history, and exports.
- Import validates bundle structure and rehydrates project manifest.

CLI commands:
- atlas-core project-export --project-id <id> --out <path>
- atlas-core project-import --path <file.atlaspkg>

## Repository Health Check
Atlas supports deterministic project repository validation.

Validation scope:
- required files/folders exist
- manifest readable
- metadata readable
- workspace readable
- review artifacts readable if present
- metadata referenced documents exist when declared
- history readable
- schema_version compatible

Health report model:
- status
- errors
- warnings
- missing_files
- orphaned_files
- repair_recommendations
- validated_at

CLI command:
- atlas-core project-health --project-id <id>

## GUI Storage Integration
Project Settings includes Project Repository / Storage details:
- repository location
- project count
- selected project storage path
- manifest summary
- health status
- last validation
- export bundle action
- import bundle action

## Adapter Pattern and Future Cloud Support
Workspace code depends on contracts, not filesystem details.

Future adapters can be introduced without changing workspace/UI flow:
- S3ProjectRepository
- DynamoProjectRepository
- AzureRepository
- GoogleCloudRepository

The repository contract boundary is the extension point; only adapter wiring should change.

Cloud migration path:
1. Implement cloud adapter classes that satisfy repository contracts.
2. Map project_location to cloud-native references.
3. Preserve project_manifest schema for deterministic compatibility.
4. Keep Workspace and service-layer orchestration unchanged.

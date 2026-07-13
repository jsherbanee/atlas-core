# Atlas Project Repository

## Related Documents
- [README.md](README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [MASTER_LIBRARY.md](MASTER_LIBRARY.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [ROADMAP.md](ROADMAP.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)

## Overview
Sprint 9 introduced the Atlas Project Repository as the persistence layer for Atlas Workspace.

Sprint 10 hardens the repository interfaces to prepare for cloud-ready storage adapters without implementing cloud services.

Atlas's long-term hosting direction is AWS-backed multi-tenant SaaS storage, but the current repository layer remains local and deterministic for development.

Goals:
- Persist projects independently of the running session.
- Keep storage deterministic and portable.
- Decouple workspace logic from storage implementation using repository contracts.
- Enable future cloud adapters without changing workspace code paths.
- Support deterministic Atlas Bid ID sequencing with non-consuming preview and consuming allocation behavior.
- Keep create-with-upload onboarding deterministic with explicit diagnostics and recovery-safe partial success.

Out of scope:
- Databases
- Authentication
- Collaboration

Future cloud-adapter targets may include:
- Amazon S3 for object/document storage
- CloudFront for delivery
- Amazon RDS or Aurora for relational persistence
- Amazon Cognito for identity
- ECS/Fargate or Lambda where appropriate

## Repository Architecture
Atlas uses adapter contracts in atlas_core/repository/contracts.py and local filesystem adapters in atlas_core/repository/local.py.

Contracts:
- ProjectRepository
- WorkspaceRepository
- DocumentRepository
- ReviewRepository
- KnowledgeRepository
- HistoryRepository

Project identity contract notes (X-02):
- `allocate_bid_id(year=None)` reserves the next available deterministic Atlas Bid ID.
- `peek_next_bid_id(year=None)` previews the next available deterministic Atlas Bid ID without advancing sequence state.

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

The local adapters are the development-time stand-in for future cloud-hosted tenant-scoped storage adapters.

The service layer consumes an orchestrator (AtlasProjectManager in atlas_core/repository/project_manager.py) that composes all adapters.

Workspace integration is done by atlas_core/services/project_workspace_service.py, which now uses repository adapters instead of legacy outputs/project_workspaces records.

## Directory Layout
Projects are stored under:
- AtlasProjects/<project_id>/

Runtime UI sessions use mutable workspace storage outside immutable source fixtures:
- default runtime path: ~/.atlas_core/runtime/AtlasProjects/
- optional override: ATLAS_RUNTIME_WORKSPACE_ROOT

Directory structure:

- AtlasProjects/
  - .atlas_bid_id_sequence.json
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
- general contractor
- electrical contractor
- architect
- engineers
- project number (Atlas Bid ID compatibility alias)
- atlas bid id
- client project number
- internal project number
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

## Create + Upload Recovery Behavior (X-03)

Project onboarding uses existing repository/intake paths and does not create a parallel upload subsystem.

Behavior guarantees:
- project identity creation and Atlas Bid ID assignment are deterministic and durable once the project is created
- document import failures do not corrupt or delete a successfully created project
- valid files remain associated with the new project even when other files are rejected
- rejected files surface structured diagnostics and can be retried from Documents workspace
- runtime upload artifacts are written only under controlled project intake locations

X-03 onboarding behavior:
- Create New Project is Step 1 metadata-only onboarding and routes to Documents for Step 2 upload.
- Upload execution is explicit from Documents (`Upload Pending Files`).
- Pending files accumulate across multiple chooser selections until removed or uploaded.
- Pending dedupe is deterministic by normalized filename + file size + source hash.
- CSV is accepted in onboarding and flows through the same repository/intake path as other supported files.
- Mixed valid/invalid pending batches preserve deterministic diagnostics/warnings.

## Shared Stakeholder Persistence (X-03)

X-03 introduces durable shared stakeholder records without replacing project metadata files:
- `AtlasProjects/.atlas_organizations.json`: canonical shared organizations directory.
- `AtlasProjects/.atlas_project_stakeholders.json`: project-to-organization role relationships.

Compatibility note:
- Legacy free-text stakeholder metadata fields remain supported and are preserved.

## ZIP Safety Rules (X-02 Amendment)

ZIP intake applies deterministic safety controls before extracting entries:
- path traversal rejection
- encrypted-entry rejection
- duplicate-entry rejection
- system artifact filtering (`__MACOSX`, `.DS_Store`)
- nested archive depth limit
- archive entry-count limit
- archive expansion-size limit
- contained relative-path preservation in source metadata

## Immutable Fixtures vs Mutable Runtime Storage
Atlas distinguishes fixture data from runtime state:

Immutable fixture data:
- canonical fixture/reference artifacts tracked in source control
- used for deterministic tests and baseline regression behavior
- should not be modified by normal interactive app execution

Mutable runtime data:
- interactive workspace state generated during local UI sessions
- stored under runtime workspace root (default: ~/.atlas_core/runtime/AtlasProjects)
- safe to recreate, clear, or discard without affecting tracked fixture baselines

Expected behavior:
- opening reference projects should not mutate tracked fixture trees
- workspace_opened and similar runtime events write to mutable runtime storage
- repeated app runs should not dirty repository fixture files

Cleanup behavior:
- runtime workspace data can be deleted and recreated automatically on next run
- immutable fixtures remain tracked and unchanged

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

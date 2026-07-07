# Atlas Project Repository

## Overview
Sprint 9 introduces the Atlas Project Repository as the persistence layer for Atlas Workspace.

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

These actions are surfaced in the workspace UI and routed through ProjectWorkspaceService.

## Adapter Pattern and Future Cloud Support
Workspace code depends on contracts, not filesystem details.

Future adapters can be introduced without changing workspace/UI flow:
- S3ProjectRepository
- DynamoProjectRepository
- AzureRepository
- GoogleCloudRepository

The repository contract boundary is the extension point; only adapter wiring should change.

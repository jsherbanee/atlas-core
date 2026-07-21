# Project Workspace

## Purpose

The Project Workspace is the operational center for a single active project.

It answers one question:

- What does the team need to know and do to move this project forward?

It is not a project database record view and it is not a decorative dashboard.

## PX-02 Project Operations Center

PX-02 turns the active Project Overview into the Project Operations Center while
preserving existing project services, persistence, lifecycle state, search,
Working Set, return context, tenant isolation, permissions, archive behavior,
and Universal Object compatibility.

The default surface answers:

- Where is this project?
- What has changed?
- What is blocking progress?
- What should happen next?
- What decisions need to be made?

## Default Composition

The project header presents:

- project name
- customer
- current phase
- overall status
- project manager
- last activity
- current revision
- current health
- Resume Work, Open Estimate, View Drawings, and More Actions

The operations center presents:

- Project Health: actionable conditions only, or `Project is progressing normally.`
- Current Work: supported work items derived from existing review/project data
- Project Timeline: grouped meaningful completed business events
- Project Context: compact operational summaries for customer, location,
  contacts, documents, estimate, transactions, issues, and decisions
- Project Inspector: Overview, Activity, Relationships, Documents, History, and
  Administration

Administration is secondary and keeps implementation-facing project details out
of the default view.

## Navigation

Active project navigation is organized around work:

- Overview
- Engineering
- Commercial
- Documents
- Construction
- Reporting
- Settings

Existing routes remain authoritative underneath those groupings. PX-02 does not
remove project pages or change persistence contracts.

## Documents And Processing

AV-00A makes document intake asynchronous for local Atlas:

- Documents accepts selected files into a pending list immediately.
- Upload Pending Files performs basic filename/type/size validation, persists each accepted file into a durable processing job, and returns control to the UI.
- Expensive document work such as PDF inspection, OCR, extraction, classification, drawing intelligence, and evidence generation runs from the persisted Processing queue, not inside the Streamlit button callback.
- Processing displays filename, folder, upload time, current stage, progress, elapsed time, warnings, failure reason, retry, and cancel controls.
- Active, Ready, Needs Attention, Failed, and All filters read persisted job state and survive reruns, refreshes, navigation, and local application restart where the queued job record is present.

Local limitation: the built-in worker is an in-process daemon. Jobs remain
durable on disk, but processing only advances while a local Atlas worker process
is running.

## Lightweight Project Open

AV-00B makes project opening a lightweight route transition.

Opening a project loads only:

- project identity and customer
- tenant/local workspace scope
- lifecycle/status metadata
- current navigation state
- cached manifest document counts
- non-blocking processing job counts

It does not load document contents, OCR results, extracted pages, evidence
collections, drawing intelligence, or full review context before the first
Project Operations Center render. Detail-heavy sections hydrate when users open
those sections. If processing-job details are temporarily unavailable, the
workspace opens and reports `Processing details are updating.`

Overview, Documents, and Processing are lightweight-safe routes. They may use
project identity, cached document counts, processing counts, navigation state,
and simple recommended actions. Detail-heavy engineering, evidence, BOM,
relationships, and commercial intelligence remain full-context boundaries and
hydrate only when their pages require them.

Repository reconciliation is not run implicitly during navigation. If a cached
manifest is missing or stale, the project still opens and Atlas surfaces a
maintenance-oriented diagnostic instead of blocking the route transition.

## Section Failure Isolation

Secondary Project Operations Center panels are isolated so one failed panel does
not take down the entire project workspace. A contained section failure shows
`This section could not be loaded.`, a concise explanation, a retry action, an
error reference, and administrator technical detail while leaving the remaining
workspace usable.

Unexpected application and section errors write searchable diagnostic records to
the runtime error log with timestamp, tenant, project, route, active page,
hydration mode, section, exception type, stack trace, and recent action context.

## Boundaries

PX-02 does not add:

- new project business logic
- persistence redesign
- workflow redesign
- AI behavior
- inventory
- procurement implementation
- accounting integration

Repository, manifest, storage version, schema version, internal identifiers, and
diagnostic metadata remain available only through Administration, Settings, or
authorized diagnostics paths.

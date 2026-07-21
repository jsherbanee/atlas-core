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

# Atlas Documentation

Atlas documentation defines the product vision, architecture, lifecycle roadmap, UX posture, and implementation status for Atlas, the Intelligent Lifecycle Solutions Management Platform for AV and lighting systems integrators.

Current implementation focus remains Phase 2 Bid Intelligence and the associated workspace-continuity/documentation workstream. Epic X is complete through X-13, Epic W has delivered W-01 Workspace Intelligence continuity, W-02 universal object contracts, and W-03 controlled Universal Object Workspace migration, and Epic E has not started.

Commercial Knowledge update: Epic C Sprint C-03 now includes expanded Commercial Catalog coverage for Product/Service/Fee/Assembly item types, deterministic PDF catalog price-list import preview/finalization behavior, and assembly lifecycle/versioning references. See [COMMERCIAL_CATALOG.md](COMMERCIAL_CATALOG.md).

Alpha data validation update: Epic C Sprint C-04 adds deterministic seed catalog loading/reset and scripted catalog-to-transaction validation coverage. See [SEED_DATA.md](SEED_DATA.md).

Alpha infrastructure update: Sprint M-01 adds platform-admin tenant sandbox provisioning and isolation controls for deterministic multi-tenant alpha environments. See [TENANT_MANAGER.md](TENANT_MANAGER.md).

Current workspace-continuity stream: Epic W Workspace Intelligence.
Scope: deterministic context persistence, cross-workspace continuity, search handoff, Working Set continuity, and repository-backed return context for already-implemented capabilities only.

These documents are intended to be used as a cohesive reference library, not isolated notes.

## How to Use This Library

- Start with Vision documents to understand product intent and domain boundaries.
- Use Architecture documents to understand system structure and persistence patterns.
- Use Engineering Intelligence documents to understand deterministic review capabilities.
- Use Development documents to understand current state, milestones, and release history.

The documentation set is intended for product, design, engineering, operations, and implementation stakeholders.

## Documentation Conventions

### Architecture Documents
Purpose:
Define stable platform structure, boundaries, and long-term system contracts.

Expected update frequency:
Lower frequency, primarily when architecture or system boundaries change.

### Implementation Documents
Purpose:
Describe engine behavior, workspace integrations, deterministic intelligence flows, and operational surfaces.

Expected update frequency:
Higher frequency as capabilities and integrations evolve.

### Status Documents
Purpose:
Describe what is currently implemented and where Atlas stands today.

Expected update frequency:
Updated continuously as implementation changes.

### Release Documents
Purpose:
Capture historical milestone evolution and customer-visible product changes over time.

Expected update frequency:
Updated at each milestone release.

Architecture documents should remain relatively stable. Implementation and status documents should evolve more frequently.

## Version Naming Convention

Atlas product lifecycle naming:

- Preview: early architectural validation and capability proving.
- Beta: feature complete and broad validation.
- Release Candidate: production stabilization and final hardening.
- Major Release: customer-ready platform milestone.

Future releases should follow this structure.

## Vision

### [PRODUCT_VISION.md](PRODUCT_VISION.md)
- Purpose: Defines Atlas product position, problem framing, and scope intent.
- Audience: Product leadership, architecture, engineering, operations, and implementation stakeholders.
- When to reference: When validating product direction or scope decisions.

### [TRUST_CHARTER.md](TRUST_CHARTER.md)
- Purpose: Defines the top-level trust philosophy, ownership commitments, transparency expectations, and permanent architectural invariants.
- Audience: Product, architecture, security, AI, legal, and platform contributors.
- When to reference: When making high-level trust, sovereignty, or customer-exit decisions.

### [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)
- Purpose: Defines customer-facing capability horizons and commercial evolution.
- Audience: Product, leadership, customer-success, and implementation stakeholders.
- When to reference: When discussing roadmap value, packaging, or launch readiness.

### [PRODUCT_GOVERNANCE.md](PRODUCT_GOVERNANCE.md)
- Purpose: Defines work-item states, roadmap discipline, progressive refinement, ADR triggers, and Atlas 1.0 governance rules.
- Audience: Product, architecture, engineering, and planning stakeholders.
- When to reference: Before selecting, activating, or materially reframing work.

### [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- Purpose: Defines enduring business entities, lifecycle relationships, and boundaries.
- Audience: Architects, domain owners, engine developers.
- When to reference: When introducing new lifecycle objects or cross-phase relationships.

### [AV_LIFECYCLE.md](AV_LIFECYCLE.md)
- Purpose: Defines the end-to-end AV, lighting, and control lifecycle from lead through replacement.
- Audience: Product, operations, lifecycle-planning, and implementation stakeholders.
- When to reference: When planning roadmap sequencing or lifecycle-stage coverage.

### [LIFECYCLE_ENGINE.md](LIFECYCLE_ENGINE.md)
- Purpose: Defines the deterministic lifecycle-engine implementation authority for canonical stages, statuses, transitions, readiness, history, tenant enforcement, and compatibility behavior.
- Audience: Engineers, architects, workspace contributors, and lifecycle-planning stakeholders.
- When to reference: When implementing or validating lifecycle-engine behavior and project lifecycle compatibility.

### [TRANSACTIONS_ARCHITECTURE.md](TRANSACTIONS_ARCHITECTURE.md)
- Purpose: Defines the future Transactions workspace, commercial-document ownership boundaries, transaction families, optional Project linkage model, and Atlas versus QuickBooks responsibilities.
- Audience: Product, architecture, integrations, commercial-operations, and platform contributors.
- When to reference: When planning transaction objects, document workflows, sync boundaries, or Transactions navigation.

### [COMMERCIAL_DOCUMENT_FRAMEWORK.md](COMMERCIAL_DOCUMENT_FRAMEWORK.md)
- Purpose: Defines the common contract, lifecycle, revision model, approval model, numbering philosophy, relationship rules, and sync metadata architecture for all future commercial documents.
- Audience: Product, architecture, integrations, commercial-operations, and platform contributors.
- When to reference: When planning any commercial document family or shared transaction-document behavior.

### [DOCUMENT_GENERATION.md](DOCUMENT_GENERATION.md)
- Purpose: Defines deterministic template resolution, template-version snapshot behavior, and document rendering/output artifact guarantees.
- Audience: Product, architecture, transactions, settings, and platform contributors.
- When to reference: When implementing template management, render reproducibility, or generated artifact workflows.

### [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)
- Purpose: Defines engineering execution sequencing, technical milestones, and production-readiness gates.
- Audience: Engineering, platform, architecture, and release stakeholders.
- When to reference: When planning implementation dependencies or readiness work.

### [SCRUM_PROCESS.md](SCRUM_PROCESS.md)
- Purpose: Defines Product Backlog, Sprint Backlog, sprint objective, Definition of Ready, Definition of Done, and review/refinement practices.
- Audience: Product, engineering, architecture, and release stakeholders.
- When to reference: During backlog refinement, sprint planning, sprint review, retrospective, and release review.

### [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- Purpose: Defines the permitted industry-knowledge foundation, source hierarchy, versioning, neutrality, and human-authority limits for future AI features.
- Audience: Product, AI, data, security, and platform contributors.
- When to reference: When planning AI grounding, content licensing, source hierarchy, or assistant behavior.

### [AI_ASSISTANT.md](AI_ASSISTANT.md)
- Purpose: Defines assistant behavior, context assembly, retrieval grounding, permissions, response classification, and future interaction architecture.
- Audience: Product, AI, data, security, and platform contributors.
- When to reference: When designing assistant UX, retrieval, or write-action boundaries.

### [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- Purpose: Defines customer ownership, privacy, portability, and the high-level trust commitment for customer knowledge.
- Audience: Product, legal, security, platform, and AI contributors.
- When to reference: When validating ownership, retention, portability, or customer trust language.

### [TRUST_CHARTER.md](TRUST_CHARTER.md)
- Purpose: Defines the system-level trust charter that sits above privacy and security detail.
- Audience: Product, architecture, security, AI, legal, and platform contributors.
- When to reference: When validating sovereignty, transparency, and customer-exit language.

### [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- Purpose: Defines AI-specific privacy protections, provider expectations, conversation isolation, and audit requirements.
- Audience: Product, AI, security, platform, and operations contributors.
- When to reference: When designing AI data handling, provider selection, or AI retention controls.

### [STANDARDS_LIBRARY.md](STANDARDS_LIBRARY.md)
- Purpose: Defines standards-oriented knowledge governance and edition handling.
- Audience: Product, AI, standards, security, and platform contributors.
- When to reference: When managing standards sources or citations.

### [MANUFACTURER_KNOWLEDGE.md](MANUFACTURER_KNOWLEDGE.md)
- Purpose: Defines manufacturer-specific technical knowledge governance and sourcing.
- Audience: Product, AI, commercial, and platform contributors.
- When to reference: When managing product-specific documentation or compatibility guidance.

### [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md)
- Purpose: Defines UX philosophy and long-term visual/interaction posture.
- Audience: Product design, frontend engineers, architecture owners.
- When to reference: When evaluating UI/UX direction and interaction consistency.


## Architecture

### [ARCHITECTURE.md](ARCHITECTURE.md)
- Purpose: Defines engine-first layering, contracts, and module responsibilities.
- Audience: Engineers and architects.
- When to reference: When adding services, rules, contracts, or orchestration patterns.

### [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)
- Purpose: Defines staged AWS hosting, workload, tenant-isolation, deployment, and migration direction.
- Audience: Platform, architecture, operations, and security contributors.
- When to reference: When planning cloud migration, hosting, or environment isolation.

### [OBJECT_GRAPH.md](OBJECT_GRAPH.md)
- Purpose: Defines the authoritative object relationship and knowledge-graph architecture.
- Audience: Engineering intelligence, search, AI, and architecture contributors.
- When to reference: When introducing graph traversal or cross-project relationship logic.

### [RULE_ENGINE.md](RULE_ENGINE.md)
- Purpose: Defines deterministic rule evaluation, registries, versions, and diagnostics.
- Audience: Engineering intelligence, estimating, and platform contributors.
- When to reference: When adding or changing deterministic business rules.

### [SEARCH_ARCHITECTURE.md](SEARCH_ARCHITECTURE.md)
- Purpose: Defines deterministic search and future retrieval architecture.
- Audience: Search, workspace, AI, and platform contributors.
- When to reference: When changing object discovery or retrieval behavior.

### [NAVIGATION_ARCHITECTURE.md](NAVIGATION_ARCHITECTURE.md)
- Purpose: Defines the reusable primary, secondary, and tertiary navigation contract used by Atlas workspace surfaces.
- Audience: Workspace, search, UI, and platform contributors.
- When to reference: When changing navigation state, breadcrumbs, or search-to-workspace handoff behavior.

### [SETTINGS_ARCHITECTURE.md](SETTINGS_ARCHITECTURE.md)
- Purpose: Defines the reusable Settings workspace contract, settings scope boundaries, and tenant/user settings behavior.
- Audience: Workspace, product, platform, and commercial-operations contributors.
- When to reference: When changing settings navigation, numbering preferences, or personal preference boundaries.

### [PERMISSIONS_AND_ROLES.md](PERMISSIONS_AND_ROLES.md)
- Purpose: Defines deterministic tenant-scoped permissions, system roles, assignment/override behavior, and access evaluation rules.
- Audience: Security, platform, workspace, and user-administration contributors.
- When to reference: When changing authorization decisions, role assignments, permission hooks, or settings role-management behavior.

### [WORKSPACE_INTELLIGENCE.md](WORKSPACE_INTELLIGENCE.md)
- Purpose: Defines the deterministic continuity layer for context persistence, return context, mixed-scope Working Set behavior, and cross-workspace handoff.
- Audience: Workspace, search, UI, and platform contributors.
- When to reference: When changing context persistence, return behavior, search handoff, or project/knowledge continuity flows.

### [OBJECT_WORKSPACE.md](OBJECT_WORKSPACE.md)
- Purpose: Defines shared Universal Object Workspace ownership, migrated object scope, compatibility boundaries, and deferred migration posture.
- Audience: Workspace, UI, search, and interoperability contributors.
- When to reference: When changing shared object identity/actions/views, context banner behavior, or object-workspace routing compatibility.

### [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
- Purpose: Defines the common ingestion and validation architecture for documents and data.
- Audience: Platform, repository, ingestion, and AI contributors.
- When to reference: When changing upload, extraction, or finalization flows.

### [BACKGROUND_JOBS.md](BACKGROUND_JOBS.md)
- Purpose: Defines deterministic background job contracts, local execution model, and job lifecycle integration boundaries.
- Audience: Platform, repository, workspace, and observability contributors.
- When to reference: When changing async-capable workflow orchestration or job execution semantics.

### [ATTACHMENT_FRAMEWORK.md](ATTACHMENT_FRAMEWORK.md)
- Purpose: Defines the unified tenant-scoped attachment contracts, service model, repository boundaries, and object-workspace integration behavior.
- Audience: Workspace, repository, platform, and security contributors.
- When to reference: When changing attachment lifecycle behavior, object document links, or attachment persistence boundaries.

### [AUDIT_ENGINE.md](AUDIT_ENGINE.md)
- Purpose: Defines immutable audit contracts, persistence model, redaction behavior, and compatibility normalization.
- Audience: Security, platform, observability, and workflow contributors.
- When to reference: When changing audit event shape, retention class usage, or lifecycle audit integrations.

### [REPORTING.md](REPORTING.md)
- Purpose: Defines operational and executive reporting architecture.
- Audience: Product, engineering, reporting, and platform contributors.
- When to reference: When changing export, templates, or reporting behavior.

### [PERFORMANCE.md](PERFORMANCE.md)
- Purpose: Defines performance principles and future targets.
- Audience: Engineering, platform, and architecture contributors.
- When to reference: When evaluating large-project behavior or load characteristics.

### [OBSERVABILITY.md](OBSERVABILITY.md)
- Purpose: Defines future production logging, metrics, traces, and alerting.
- Audience: Platform, security, and operations contributors.
- When to reference: When designing telemetry or incident response support.

### [BACKUP_RECOVERY.md](BACKUP_RECOVERY.md)
- Purpose: Defines backup, recovery, and disaster-recovery architecture.
- Audience: Platform, operations, security, and architecture contributors.
- When to reference: When planning restoreability or retention posture.

### [SERVICE_AND_ASSET_LIFECYCLE.md](SERVICE_AND_ASSET_LIFECYCLE.md)
- Purpose: Defines the future installed-system lifecycle and service continuity model.
- Audience: Product, service, operations, and platform contributors.
- When to reference: When planning service or asset-history capabilities.

### [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- Purpose: Defines tenant isolation, organization-scoped records, roles, memberships, and permission boundaries.
- Audience: Architecture, security, platform, and AI contributors.
- When to reference: When designing tenant-aware behavior or shared platform services.

### [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- Purpose: Defines future account, invitation, seat, and organization administration workflows.
- Audience: Product, platform, security, and identity contributors.
- When to reference: When planning administration or future SSO behavior.

### [INTEGRATIONS.md](INTEGRATIONS.md)
- Purpose: Defines synchronization boundaries for QuickBooks, Stripe, and future external systems.
- Audience: Platform, integration, product, and data contributors.
- When to reference: When designing sync, reconciliation, webhooks, or API behavior.

### [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- Purpose: Defines project storage architecture, repository contracts, and persistence behavior.
- Audience: Platform engineers, workspace/persistence contributors.
- When to reference: When changing storage, repository adapters, or workspace persistence.

### [MASTER_LIBRARY.md](MASTER_LIBRARY.md)
- Purpose: Defines the long-term reference-library direction for reusable manufacturer/product/standards knowledge.
- Audience: Architecture, data-model, and intelligence contributors.
- When to reference: When planning reusable knowledge assets and shared references.

## Engineering Intelligence

### [KNOWLEDGE_ENTITY_FRAMEWORK.md](KNOWLEDGE_ENTITY_FRAMEWORK.md)
- Purpose: Defines deterministic shared knowledge entity model/service contracts and W-series object-workspace integration boundaries.
- Audience: Knowledge domain, workspace, and search contributors.
- When to reference: When modifying customer/vendor/manufacturer/product/service/contact/location/project entity behavior or compatibility handoff rules.

### [DRAWING_INTELLIGENCE.md](DRAWING_INTELLIGENCE.md)
- Purpose: Index for drawing intelligence architecture and implementation references.
- Audience: Engineering-intelligence contributors.
- When to reference: When working on drawing interpretation, relationships, or explorer behavior.

### [SPECIFICATION_INTELLIGENCE.md](SPECIFICATION_INTELLIGENCE.md)
- Purpose: Defines deterministic specification interpretation and cross-reference behavior.
- Audience: Specification-intelligence and workspace contributors.
- When to reference: When changing section parsing, requirements, or spec-linked relationships.

### [COORDINATION_INTELLIGENCE.md](COORDINATION_INTELLIGENCE.md)
- Purpose: Defines deterministic coordination checks and findings model.
- Audience: Coordination engine and workspace contributors.
- When to reference: When changing conflict/gap/agreement logic and advisory findings.

### [ENGINEERING_RESOLVER.md](ENGINEERING_RESOLVER.md)
- Purpose: Documents resolver role and conflict-normalization behavior.
- Audience: Resolver, rule-engine, and intelligence contributors.
- When to reference: When modifying resolver conflict handling or canonicalization behavior.

### [ENGINEERING_INTELLIGENCE.md](ENGINEERING_INTELLIGENCE.md)
- Purpose: Defines engineering insight generation, health scoring, and recommendation outputs.
- Audience: Engineering-intelligence contributors.
- When to reference: When changing insights, priorities, risk signals, or health models.

### [ENGINEERING_WORKBENCH.md](ENGINEERING_WORKBENCH.md)
- Purpose: Defines workspace investigation surface and traceability workflows.
- Audience: Workspace and experience contributors.
- When to reference: When changing investigation behavior, panel composition, or trace UX.

### [ENGINEERING_NOTEBOOK.md](ENGINEERING_NOTEBOOK.md)
- Purpose: Defines engineering notebook data model, timeline integration, and boundaries.
- Audience: Workspace and engineering-review contributors.
- When to reference: When changing notebook entries, decision logs, or linked-object behavior.

### [SECURITY.md](SECURITY.md)
- Purpose: Defines baseline security posture, access-control expectations, and operational security boundaries.
- Audience: Platform, security, and implementation contributors.
- When to reference: When changing authentication, authorization, secrets, logging, or trust boundaries.

### [TRUST_CHARTER.md](TRUST_CHARTER.md)
- Purpose: Defines the permanent trust commitments that security and architecture should uphold.
- Audience: Product, security, architecture, AI, and platform contributors.
- When to reference: When validating customer trust, confidentiality, or tenant-isolation commitments.

### [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- Purpose: Defines data ownership, retention, tenant isolation, AI grounding, and source-authority expectations.
- Audience: Product, data, security, and AI contributors.
- When to reference: When changing data policies, AI context boundaries, or record stewardship rules.

### [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- Purpose: Defines customer ownership and portability commitments for operational knowledge.
- Audience: Product, security, legal, and platform contributors.
- When to reference: When making customer-data trust or ownership statements.

### [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- Purpose: Defines privacy expectations for AI providers, AI conversations, and auditability.
- Audience: Product, security, operations, and AI contributors.
- When to reference: When making AI privacy or retention decisions.

## Development

### [EPICS.md](EPICS.md)
- Purpose: Master implementation roadmap organized by epic and sprint stream IDs.
- Audience: Product and engineering planning stakeholders, plus Codex session operators.
- When to reference: Before drafting or executing sprint prompts to anchor work in the correct domain stream.

### [ROADMAP.md](ROADMAP.md)
- Purpose: Defines milestone trajectory and implementation planning direction.
- Audience: Product and engineering planning stakeholders.
- When to reference: During milestone planning and sequencing decisions.

### [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)
- Purpose: Defines engineering execution sequencing, gates, and dependencies.
- Audience: Engineering, platform, architecture, and release stakeholders.
- When to reference: During implementation planning or readiness reviews.

### [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)
- Purpose: Defines customer-facing capability horizons and commercial progression.
- Audience: Product, leadership, customer-success, and implementation stakeholders.
- When to reference: During product planning, launch readiness, or customer messaging.

### [PRODUCT_GOVERNANCE.md](PRODUCT_GOVERNANCE.md)
- Purpose: Defines work-item states, roadmap discipline, progressive refinement, ADR triggers, and Atlas 1.0 governance rules.
- Audience: Product, architecture, engineering, and planning stakeholders.
- When to reference: Before selecting, activating, or materially reframing work.

### [SCRUM_PROCESS.md](SCRUM_PROCESS.md)
- Purpose: Defines Product Backlog, Sprint Backlog, sprint objective, Definition of Ready, Definition of Done, and review/refinement practices.
- Audience: Product, engineering, architecture, and release stakeholders.
- When to reference: During backlog refinement, sprint planning, sprint review, retrospective, and release review.

### [ASSEMBLIES_AND_LABOR.md](ASSEMBLIES_AND_LABOR.md)
- Purpose: Defines D-03 architecture and implementation boundaries for deterministic assemblies, accessories, and labor rollups.
- Audience: Estimating architecture, service, and workspace contributors.
- When to reference: Before implementing D-03 composition, rollup, and revision-integration behavior.

### [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- Purpose: Captures the current implementation state only.
- Audience: Product, engineering, design, and operations stakeholders.
- When to reference: To answer where Atlas is today.

### [RELEASE_NOTES.md](RELEASE_NOTES.md)
- Purpose: Historical record of customer-visible milestone evolution.
- Audience: Product, engineering, and release stakeholders.
- When to reference: To understand how Atlas evolved across milestones.

### [CODEX_WORKFLOW.md](CODEX_WORKFLOW.md)
- Purpose: Defines AI-assisted engineering workflow and execution conventions.
- Audience: Contributors using Codex/Copilot-assisted development.
- When to reference: Before running sprint execution workflows or agent-driven development.

### [CODEX_SESSION_INIT.md](CODEX_SESSION_INIT.md)
- Purpose: Defines the required repository-initialization checklist for every new Codex session.
- Audience: Contributors starting a new Codex/Copilot coding session in Atlas.
- When to reference: At session start, before pasting sprint instructions or implementing code changes.

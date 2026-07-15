# Release Notes

This document answers: How did Atlas evolve?

It is the historical record of product milestones.

## See Also

- [README.md](README.md)
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- [ROADMAP.md](ROADMAP.md)
- [PRODUCT_VISION.md](PRODUCT_VISION.md)

This document tracks product-facing changes for Atlas Preview releases.

## Format

- Reverse chronological order (newest release first).
- Focus on user-visible behavior and workflow changes.
- Include quality gate status when relevant.

## Unreleased (Atlas Alpha Infrastructure Sprint M-01 Tenant Manager and Sandbox Provisioning)

### Improved

- Atlas now includes deterministic tenant-manager contracts and service foundations for alpha sandbox lifecycle administration.
- Platform administrators can provision isolated local tenant sandboxes with stable tenant IDs, owner assignment, seed profile controls, expiration metadata, and environment path provisioning.
- Tenant Manager now supports restricted sandbox actions for open, suspend, restore, reset, export, archive, and guarded delete workflows.
- Tenant isolation coverage now includes tenant-scoped search indexes, background jobs, settings/preferences, working-set state, and export payload scoping.
- Guarded destructive controls now require explicit confirmation phrases, and delete paths require export-before-delete evidence.

### Scope Notes

- no AWS infrastructure provisioning
- no Cognito/SSO implementation
- no billing or self-service tenant signup

## Unreleased (Sprint P-03 Deterministic Background Job Framework)

## Unreleased (Atlas Epic C Sprint C-04 Seed Catalog Import and Alpha Data Validation)

### Improved

- Atlas now supports deterministic tenant-scoped C-04 seed catalog loading for alpha validation with explicit provenance markers.
- Seed package coverage includes representative manufacturers, vendors, products, services, fees, assemblies, assembly components, tax nexus records, and price-sheet imports.
- Development/admin seed controls now support repeatable load, duplicate suppression, and seed-only reset preserving non-seed records.
- Seed validation now includes representative CSV/XLSX/PDF import paths and deterministic import diagnostics behavior.
- Scripted validation now covers catalog-backed Estimate -> Sales Order -> Customer Invoice, additive/deductive change-order tracking, and Return Order -> Credit Memo workflows, including representative PDF generation checks.

### Scope Notes

- non-production sample data only
- no inventory implementation
- no live tax service integration
- no QuickBooks sync execution
- no new transaction families

## Unreleased (Atlas Epic C Sprint C-03 Commercial Catalog, PDF Price Lists, and Assemblies)

### Improved

- Commercial Knowledge now includes a unified catalog item foundation supporting `product`, `service`, `fee`, and `assembly` item types with deterministic archive/restore behavior.
- Commercial catalog pricing now supports policy-based quote behavior (MSRP, MAP, Cost+%, Margin%, Multiplier, Manual), including explicit manual line override precedence.
- Nexus-based tax foundation now supports deterministic rule selection with effective date windows, priority ordering, compound behavior, item-type applicability, and exemption flags.
- Settings now supports tenant-scoped organization commercial defaults for pricing policy, markup/margin, default tax nexus, currency, and rounding behavior.
- Transactions now supports catalog-backed line insertion for Estimates, Sales Orders, Return Orders, Credit Memos, and Customer Invoices, including assembly `expand` and `grouped` insertion modes.
- Commercial catalog imports now support CSV/XLSX ingestion for manufacturers, vendors, products, services, fees, assemblies, and assembly components with deterministic import summaries.
- Commercial catalog price-list imports now support deterministic PDF inspection, explicit table mapping preview, diagnostics, partial-success finalization, and immutable version snapshots.

### Quality

- black --check .: passing
- ruff check .: passing
- mypy .: passing
- pytest: full suite passing (1398 tests)

## Unreleased (Atlas Alpha Completion Sprint U-02 End-to-End Application UX and Workflow Polish)

### Improved

- Major workspace pages now consistently expose clear purpose captions through shared page-header behavior.
- User-facing controls and workflow messaging now avoid implementation/prototype terminology in key settings and transactions surfaces.
- Settings roadmap-visible sections now provide explicit guidance and deterministic return paths into active configuration workflows.
- Transactions workflow language now uses clearer metadata-focused labels for queued email delivery metadata controls.
- Responsive usability walkthroughs confirmed major workspace stability and no horizontal overflow at 820, 980, 1180, and 1366 widths.

### Scope Notes

- no new product capabilities
- no new transaction families
- no QuickBooks transport execution
- no payment, inventory, or procurement workflow activation

## Unreleased (Atlas Alpha Completion Sprint U-01 Commercial Document Usability and Presentation Polish)

### Improved

- Transactions tertiary action contracts are now standardized across Sales Orders, Return Orders, Credit Memos, and Customer Invoices (including parity for duplicate/archive/restore/issue/export workflows where supported).
- Return Orders and Credit Memos now use the same deterministic `export_pdf` pathway as other commercial document families, removing legacy export-action divergence.
- Related Documents now surfaces explicit source/lineage references (`source_document`, linked sales-order/invoice IDs, and metadata-related links) even when relationship collections are sparse.
- Line-presentation sorting now includes `unit_cost`, `discount`, and `tax_rate` columns for preview/apply/restore workflows.
- Regression coverage now locks standardized transaction navigation action matrices and expanded line-presentation sort parity.

### Scope Notes

- no QuickBooks API transport execution
- no payment workflows
- no inventory or procurement activation
- no new transaction families or roadmap expansion

## Unreleased (Atlas Alpha Completion Sprint S-01 Settings Workspace Completion)

### Improved

- Settings now supports Organization Profile metadata management with deterministic tenant scoping.
- Settings now supports tax and surcharge rule management with decimal-safe preview calculation behavior.
- Terms and Conditions settings now support `return_order` and `customer_invoice` families in addition to existing estimate/sales-order families.
- Settings document templates now include duplicate and preview workflow support.
- Integrations section is now operational for metadata hooks, including provider/status metadata and secret-reference-only credential pointers.
- Security section is now operational for organization security policy metadata controls (MFA flag, session timeout, password policy reference, allowed IP ranges).
- Settings and integrations mutations are permission-gated by `settings.manage` and `integrations.manage` with deny-by-default behavior.

### Scope Notes

- metadata hooks only for integrations (no live provider authentication or sync transport)
- security policy metadata only (no live identity/session enforcement engine)
- no SSO, invitation lifecycle, or billing-provider implementation introduced

## Unreleased (Epic T Sprint T-08 Customer Invoice Transactions)

### Improved

- Transactions now supports Customer Invoice creation from standalone, project/milestone context, Sales Order, and Change Order source paths.
- Customer Invoice billing now supports deterministic strategy metadata, requested-vs-available enforcement, and explicit overbilling override diagnostics.
- Customer Invoice issue, revision, duplication, and deterministic PDF export paths are now available through existing commercial-document framework controls.
- Customer Invoice sync controls now capture invoice-specific external identifiers/revisions, reconciliation state, retry behavior, and returned QuickBooks payment-status metadata.

### Scope Notes

- no live QuickBooks transport execution
- no receivable-ledger ownership transfer from QuickBooks to Atlas
- no customer-payment processing implementation

## Unreleased (Sprint P-07 Alpha Blocker Remediation)

### Improved

- Transactions workspace service now enforces active tenant and organization scope by default, preventing unscoped multi-tenant mutation behavior in normal runtime usage.
- Transactions scoped creation now rejects cross-tenant draft creation when scope enforcement is active.
- Regression coverage now includes constructor scope enforcement and cross-tenant create rejection under enforced scope.

### Scope Notes

- no new roadmap feature scope was added
- no inventory reactivation
- no AI/procurement/receiving/service workflow activation

## Unreleased (Sprint P-06 Alpha Foundation Integrity Audit)

### Improved

- Completed evidence-based alpha integrity audit across permissions, immutable audit, jobs, attachments, document generation, settings, commercial documents, universal object framework, workspace continuity, lifecycle, tenancy, persistence, and search/navigation.
- Transactions workspace service now supports active tenant/organization scope enforcement for list/read flows and rejects cross-scope source-document linkage in return-order creation paths.
- Document generation explicit-template resolution now enforces tenant/organization/document-family and scope compatibility checks.
- Attachment version uploads now enforce the same extension allow-list as initial uploads.
- Added regression tests for tenant scope filtering, explicit template scope enforcement, and attachment version extension validation.

### Quality

- black --check .: passing
- ruff check .: passing
- mypy .: passing
- pytest: full suite passing (1366 tests)

## Unreleased (Epic T Sprint T-09 Change Order Tracking Convention)

### Improved

- Project change-order tracking now uses existing Sales Orders (additive) and Return Orders (deductive) instead of a standalone Change Order object.
- Sales Order and Return Order workflows now support shared change-order metadata (`is_change_order`, `CO #n`, type/direction, reason, approval fields, base-bid reference, owner change reference, internal notes, source/related documents).
- Change-order numbering is now project-scoped with non-consuming preview and consuming allocation semantics.
- Duplicate change-order sequence allocation is blocked within a project and archived numbers remain consumed.
- Transactions now includes a project commercial summary view with base bid, additive total, deductive total, net change, revised contract value, pending/approved/invoiced/outstanding values, and ordered change-list reporting.

### Scope Notes

- no standalone Change Order document workflow
- no automatic invoicing
- no live QuickBooks sync
- no inventory workflow implementation

## Unreleased (Sprint P-05 Document Generation and Template Engine)

### Improved

- Atlas now includes deterministic document-generation contracts and service orchestration for template resolution and reproducible rendering outputs.
- Settings now includes tenant-scoped document template records with versioning, default assignment, precedence-aware resolution, and export/replace synchronization support.
- Commercial document revisions now capture template assignment and template version snapshot metadata alongside terms snapshots.
- Transactions export now routes through the generation engine, recording generated artifact metadata and template provenance in export activity and attachments.
- Issued revision rendering now reuses immutable revision snapshots, preventing silent reassignment to newly edited templates.

### Scope Notes

- no cloud worker implementation changes
- no external delivery transport execution
- no e-signature workflow implementation

## Unreleased (Sprint P-04 Unified Attachment Framework)

### Improved

- Atlas now includes unified attachment contracts and orchestration for tenant-scoped attachment lifecycle operations.
- Project repository architecture now includes attachment repository contracts and deterministic local attachment adapter storage.
- Project Workspace now exposes object-scoped attachment wrappers for upload, versioning, listing, unlink, archive, restore, and read/download behavior.
- Object Workspace Documents now renders unified attachments and supports permission-aware open/download, archive/restore, and unlink actions.
- Project document compatibility paths now register legacy project files as unified attachments without replacing current intake flows.
- Attachment lifecycle actions now emit immutable audit-linked events and deterministic background-hook intents.

### Scope Notes

- no cloud object-store adapter implementation
- no external worker deployment for attachment hooks
- no malware-scanner engine integration

### Improved

- Atlas now includes deterministic background-job contracts and orchestration for tenant-scoped local execution.
- Project repository now persists job records through dedicated repository contracts and local job adapters.
- Project Workspace now exposes job submit/list/retry/cancel wrappers for representative workflow operations.
- Document upload and project bundle export now execute through deterministic background jobs.
- Project Workspace now includes a Processing page for job visibility and status tracking.
- Processing actions are permission-gated via `jobs.view` and `jobs.manage` permissions.
- Background job lifecycle transitions now emit immutable audit-linked events.

### Scope Notes

- no AWS queue implementation
- no external worker deployment
- no cloud scheduler orchestration

## Unreleased (Sprint P-01 Roles and Permissions Foundation)

### Improved

- Atlas now includes deterministic tenant-scoped roles and permissions contracts for role, assignment, policy, access decision, diagnostics, project overrides, and permission-change events.
- Permissions evaluation now enforces deny-by-default, explicit allow/deny behavior, deterministic ordering, and explicit deny precedence.
- Universal Object actions now use centralized permission-hook evaluation and resolve to visible-enabled, visible-disabled-with-reason, or hidden.
- Settings now includes a minimal Organization -> Roles and Permissions surface for viewing system roles, inspecting role permissions, assigning roles, applying project-scoped overrides, and previewing effective access.
- Local single-user development remains backward-compatible through scoped compatibility evaluation for local tenant context.

### Scope Notes

- no authentication implementation
- no invitations or production user provisioning
- no SSO or cloud identity-provider integration
- no billing permission model
- no QuickBooks permission integration

## Unreleased (Epic W Sprint W-03 Universal Object Workspace)

## Unreleased (Epic T Sprint T-05 Amendment Terms and Conditions Settings)

## Unreleased (Epic T Sprint T-05 Amendment Estimate and Sales Order Versioning, Duplication, and PDF Export)

### Improved

- Transactions Estimates and Sales Orders now support explicit duplicate, create revision, revision history, archive, and restore controls.
- Duplicate document behavior now assigns a new document identity/number, preserves source traceability, copies line items and terms snapshots, and starts as Draft.
- Revision model now records explicit revision reason/date/parent/superseded/current metadata and preserves immutable issued revisions.
- Deterministic PDF export is now supported for Internal Estimate, Customer Estimate, and Sales Order presentations.
- Export activity metadata is now recorded, and archived revisions remain exportable.
- Future email-delivery metadata hooks are now available for Microsoft 365, Google Workspace, SMTP, and approved providers (metadata only, no live send).

### Scope Notes

- no live email sending
- no electronic signatures
- no QuickBooks API transport implementation
- no automatic revision creation without explicit user intent

## Unreleased (Epic T Sprint T-06 Return Orders and Credit Memos)

### Improved

- Transactions now supports Return Orders for standalone or linked customer returns.
- Return Orders now support product and service return lines, partial approvals, restocking fees, and tax adjustments.
- Processing a Return Order now generates one linked Credit Memo with preserved source-document and source-line traceability.
- Credit Memos now use tenant numbering settings, preserve QuickBooks sync metadata boundaries, and support PDF export.

### Scope Notes

- no live QuickBooks sync
- no customer refund or payment-processing behavior
- no automated inventory disposition execution
- no vendor return workflow

## Unreleased (Epic T Sprint T-07 Commercial Document Line Layout and Presentation)

### Improved

- Line-based commercial documents now support named groups, group subtotals, comment lines, and blank spacer rows as presentation metadata.
- Presentation order is now explicitly persisted and can be updated independently of authoritative commercial values.
- Users can preview sort, apply sort to presentation order, and restore manual order.
- Commercial PDFs now preserve line order, group headings, optional subtotals, blank spacing, comment placement, and selected visible columns.

### Scope Notes

- no change to grand-total calculations
- no spreadsheet-style formulas
- no pricing or tax logic changes
- no automatic regrouping

### Improved

- Organization Settings now supports tenant-scoped Terms and Conditions content blocks for Estimates and Sales Orders.
- Terms blocks now support create/edit/version/archive/restore/default-assignment behavior with audit metadata.
- Transactions estimates now support explicit Terms snapshot refresh for mutable drafts only.
- Sales Orders can now be created from approved estimates with preserved line-level source traceability and terms source/snapshot continuity.
- Estimate presentation now includes Internal and Customer views over the same estimate revision identity.

### Scope Notes

- safe formatted text content only for terms blocks
- no signature workflow, legal advice, auto-acceptance, or contract approval engine
- no QuickBooks integration and no Epic E scope

## Unreleased (Epic T Sprint T-04 Settings Foundation and Numbering Preferences)

### Improved

- Atlas now includes a reusable Settings workspace navigation foundation with secondary and tertiary settings contracts.
- Organization Settings now supports tenant-level commercial document numbering preferences by document family.
- Numbering preferences now support configurable syntax tokens, optional prefix/suffix, sequence padding, starting sequence, separator, and sequence reset policy.
- Settings now provides deterministic non-consuming live preview and next-number preview for numbering policies.
- Personal Preferences now supports user-scoped defaults for landing workspace, density, table page size, date format, timezone, and reduced motion.

### Scope Notes

- active settings scope in this sprint: Organization Settings and Personal Preferences
- Integrations, Security, Billing, and Advanced are intentionally visible as future sections
- no authentication, billing implementation, QuickBooks implementation, or role-management implementation beyond future permission hooks

## Unreleased (Epic T Sprint T-03 Estimate Transaction Integration)

### Improved

- Transactions > Estimates now operates as the first fully functional transaction family with estimate-specific tertiary actions: Add, Browse, Edit, Lines, Revisions, Issue, Approvals, Related Documents, Activity, and Export.
- Estimate transaction workflows now reuse the existing deterministic estimate engine for line-item updates, revision lifecycle, validation, and readiness checks.
- Estimate issue flow now enforces approval-before-issue and lock-ready revision behavior while preserving issued immutability.
- Standalone estimate transaction creation/editing now requires customer identity when no project link is provided.

### Scope Notes

- estimate transaction family operationalization only
- no external financial transport execution
- no accounting/payment/ledger behavior

## Unreleased (Epic T Sprint T-02 Transactions Workspace Foundation)

### Improved

- Atlas now includes a first Transactions primary workspace in header navigation.
- Transactions workspace now provides sectioned navigation for Overview, Estimates, Sales Orders, Purchase Orders, RFQs, Vendor Quotes, Receiving, Vendor Bills, Customer Invoices, and Change Orders.
- Transactions tertiary actions now provide reusable Add, Browse, Edit, Related Documents, Approvals, Sync Status, Activity, and Export controls.
- A reusable transactions workspace service now supports in-session draft create/list/edit/archive/restore behavior and overview metrics.
- Global object search now indexes transaction-family commercial documents and opens supported transaction kinds in Object Workspace.

### Scope Notes

- transactions UI/navigation foundation only
- no QuickBooks API transport implementation
- no accounting/payment/ledger behavior

## Unreleased (Epic T Sprint T-01 Commercial Document Domain Foundation)

### Improved

- Atlas now includes shared commercial-document backend domain models and contracts for identity, revisions, line items, relationships, approval state, sync metadata, totals, diagnostics, and numbering policy.
- Initial transaction-family support is available for Estimate, Sales Order, Purchase Order, RFQ, Vendor Quote, Receiving Record, Vendor Bill, Customer Invoice, and Change Order.
- Commercial-document lifecycle now uses explicit transition rules from Draft through Archived with immutable issued revision snapshots and revision history preservation.
- Numbering now supports tenant-scoped and organization-scoped preview/allocation semantics with no number reuse.
- Universal Object registry now includes commercial-document adapter registration for transaction-family identities.

### Scope Notes

- backend foundation only
- no transactions UI implementation
- no QuickBooks API implementation
- no accounting/payment/ledger subsystem behavior

## Unreleased (Epic L Sprint L-01 AV Lifecycle Engine Foundation)

## Unreleased (Epic L Sprint L-02 Lifecycle Dashboard)

### Improved

- Atlas now includes a first-class `Lifecycle` tertiary Project Object Workspace view for project records
- project lifecycle is visualized as a horizontal progress timeline with distinct complete, active, available, blocked, skipped, and archived states
- stage selection now reveals description, readiness diagnostics, transition requirements, stage-specific lifecycle history, and deterministic related objects when available
- lifecycle dashboard surfaces current stage, stage status, completed stages, blocked stages, upcoming stages, available transitions, recommended next action, and responsible role without duplicating lifecycle state

### Scope Notes

- dashboard visualization only
- no downstream workflow execution modules
- no automatic lifecycle advancement or workflow automation

### Validation

- focused lifecycle dashboard coverage validates project supported views, lifecycle dashboard rendering, and project universal-object lifecycle projection
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1255 tests

### Improved

- Atlas now includes a deterministic AV Lifecycle Engine with canonical lifecycle stages from lead through archived
- lifecycle state is now persisted through a compatibility-safe lifecycle plan snapshot while preserving legacy project status and lifecycle stage fields
- Project Settings now shows lifecycle-engine context, available transitions, applicable sequence, and recent lifecycle history
- project lifecycle transitions now require a reason and are auditable through repository history
- Project Object Workspace and shared universal-object projection paths now carry canonical lifecycle context for project records

### Scope Notes

- lifecycle foundation only
- no procurement, installation, commissioning, service, or asset-lifecycle execution workflows
- no Epic E start

### Validation

- focused lifecycle, project workspace, universal object, and object workspace tests passed for the new L-01 behavior
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1254 tests
- targeted validation confirmed compatibility-safe legacy project loading, deterministic invalid-transition blocking, required transition reasons, lifecycle history rendering, and no unexpected project-file rewrites in the validated service paths

### Deferred Lifecycle Notes

- downstream workflow modules remain intentionally deferred behind the new lifecycle-engine contracts

### Improved

- Atlas now includes a reusable Universal Object Workspace UI inside the existing shell, backed by the W-02 universal object contract and registry
- supported object opens from search and Working Set now route through Object Workspace for migrated object families
- migrated object scope includes Customer, Vendor, Manufacturer, Product, Service, Contact, Location, and Project
- Drawing, Specification, and Equipment now support read-only Universal Object Workspace rendering with direct open actions to authoritative engineering pages
- object workspace renders consistent identity, actions, tertiary view navigation, relationships, activity, provenance, and return-context banner behavior

### Scope Notes

- controlled migration only
- no redesign of unrelated workflows
- no new domain entities, AI, semantic retrieval, or Epic E start

### Validation

- focused W-03 tests cover object-workspace composition, search/working-set handoff, context-banner behavior, supported-view selection, disabled action reasons, and compatibility routing behavior
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1247 tests
- manual validation confirmed shared object-workspace behavior for Customer, Vendor, Manufacturer, Product, Service, Contact, Location, Project, Drawing, Specification, and Equipment
- manual validation confirmed consistent identity/action composition, bounded supported tertiary views, relationship/activity presentation, context banner/return behavior, search and Working Set handoff behavior, and no horizontal overflow at 820/980/1180/1366 widths
- manual validation observed no Streamlit state exceptions during repeated search handoff and return flows

### Deferred Migration Notes

- broader object-family migration remains intentionally deferred to future W-series planning
- existing authoritative domain workflows remain the source of truth for create/edit/archive/import/export behavior

## Unreleased (Epic W Sprint W-02 Universal Object Contract)

### Improved

- Atlas now defines a universal object adapter contract for identity, metadata, relationships, activity, lifecycle, actions, and presentation hints
- representative adapters are available for project, knowledge, and engineering object families without replacing existing domain models
- search references, Working Set-compatible records, and W-01 context persistence can now carry universal object identity where practical
- registry-backed adapter lookup and duplicate-registration validation provide deterministic object-contract resolution

### Scope Notes

- contract and interoperability layer only
- no Universal Object Workspace UI yet
- no AI, semantic retrieval, new workflows, or Epic E start

### Validation

- focused contract and interoperability tests now cover identity determinism, registry behavior, representative adapters, relationship validation, lifecycle/actions/presentation metadata, search compatibility, Working Set compatibility, and W-01 context compatibility
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1231 tests

## Unreleased (Epic W Sprint W-01 Context Persistence and Cross-Workspace Navigation) (Closed)

### Improved

- Atlas now preserves explicit working context across Projects, Knowledge, Search, and related object-detail surfaces through repository-backed workspace state
- cross-workspace opens now capture deterministic return context, visible breadcrumb context, and a one-click return affordance in the shared shell
- search results now show explicit project/application scope labels while preserving deterministic ranking and Clear Search return behavior
- Working Set continuity now supports both project objects and Knowledge entities under the existing compatibility model

### Scope Notes

- deterministic continuity only
- no AI, semantic retrieval, new business workflows, or Epic E start
- no parallel persistence system

### Validation

- focused continuity regression coverage increased the full-suite baseline to 1217 passing tests
- live validation confirmed project reports summary to Knowledge customer continuity, visible return context, readable breadcrumbs, and no horizontal overflow at 820, 980, 1180, 1366, and large desktop widths
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1217 tests

## Unreleased (Epic X Sprint X-13 Navigation Clarity and UX Refinement) (Closed)

### Improved

- architecture-facing navigation labels and implementation-only page notes were removed from validated production UI surfaces
- shared-shell secondary navigation is now contextual across application, project-library, and active-project modes
- Knowledge no longer renders a duplicate internal navigation panel; the shared shell owns visible navigation presentation
- Home now behaves as an operational landing page around Continue Working, Recent Projects, Action Center, Notifications, and Favorites
- Reports is now organized around deliverable readiness and output-oriented tables rather than a workflow-summary posture

### Scope Notes

- UX refinement only
- no routing, persistence, search-behavior, business-logic, or workflow changes
- no Epic E start

### Validation

- manual validation covered Home, Projects, Knowledge, Reports, active-project workspace navigation, focused search mode, and medium-width layout behavior
- validated surfaces showed no horizontal overflow during X-13 review widths
- full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count at 1203 tests

## Unreleased (Epic K Sprint K-02 Core Knowledge Entities and Operational Workflows)

### Improved

- Knowledge Entity Framework now exposes operational workflows for customer and service entities (create, update, archive, restore, list/search/get).
- Product lifecycle updates now synchronize framework-backed product entities so activation/lifecycle state remains consistent across commercial and knowledge views.
- Knowledge workspace now includes customer and service operational controls for deterministic create/list/archive/restore workflows.
- Dashboard and service summaries now include framework-level metrics for entity totals, activity state, and relationship counts.

### Scope Notes

- deterministic framework/workflow hardening only
- no Epic E start
- no procurement, service-ticket, installed-asset, or sell-pricing workflow start

### Validation

- Focused validation passed for `tests/test_knowledge_entity_framework.py` and `tests/test_phase2_global_search_working_set.py`.
- Full quality gate baseline remains passing (`black`, `ruff`, `mypy`, `pytest`) with current full-suite count at 1182 tests.

## Unreleased (Epic X Sprint X-11 Typography System and Visual Polish) (Closed)

### Improved

- Atlas now uses an official centralized typography system with Inria Serif for display hierarchy and Fira Sans for interface/content hierarchy.
- Shared typography scale tokens now govern Display, Heading, Body, Caption, Label, and Value sizes from a single design-system source.
- Heading rhythm, table/header readability, status/label hierarchy, and control typography are polished across shared shell surfaces while preserving behavior.
- Font loading is now centralized through a single authoritative stylesheet path, with explicit guidance for enterprise self-hosting replacement.

### Scope Notes

- behavior-preserving visual hardening only
- no workflow, routing, business-logic, or persistence changes
- no Epic E start

### Validation

- Manual validation confirmed typography hierarchy and shell readability across Atlas, Projects, Knowledge, Reports, project workspaces, focused search mode, and Settings access.
- Responsive checks at 820, 980, 1180, 1366, and large desktop widths showed no horizontal overflow regressions.
- Full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count unchanged at 1177 tests.

## Unreleased (Epic X Closeout Validation and Closure) (Closed)

### Improved

- Engineering Notebook now has a validated normal-flow entry from Overview Guided Project Review actions (Open Notebook).
- Linked-object navigation from Notebook entries now reliably executes for generated entries by using stable linked-object action keys.
- Epic X closeout validation confirmed no blocking shell, navigation, search, responsive, or design-system defects across validated X-01 through X-10 surfaces.

### Scope Notes

- validation and closure hardening only
- no new domain capabilities
- no persistence/business-logic expansion
- no Epic E start

### Closeout Validation

- Manual validation covered Notebook entry path, list/empty-state behavior, filtering, linked-object navigation, decision-log tab, return navigation, context preservation, and medium-width layout behavior.
- X-09 and X-10 migrated surfaces remained intact during closeout checks.
- Full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count unchanged at 1177 tests.

### Remaining Non-Blocking UX Debt

- lower-priority advanced/object-detail surfaces still rely on older inline wrappers and should continue migration to shared primitives.
- broader notebook discoverability beyond guided Overview actions can be improved further in a future hardening sprint.

## Unreleased (Epic X Sprint X-10 Workspace Consistency and Information Density) (Closed)

### Improved

- Remaining primary project workspaces now use shared design-system wrappers for section hierarchy, notice panels, table presentation, and responsive control groups.
- Consistency migration now covers Overview, Documents, BOM Review, Scope & Risk, Engineering Review, Estimate, and Notebook surfaces without changing deterministic behavior.
- Project Summary and related report-facing project surfaces now use the same shared wrappers for reduced visual drift.

### Scope Notes

- UI consistency hardening only
- no business-logic or persistence changes
- no Epic E start

### Closeout Validation

- Manual validation confirmed primary workspace routing and rendering for Home, Projects, Knowledge, Reports, Overview, Documents, BOM Review, Scope & Risk, Engineering Review, Estimate, and Settings.
- Focused global search, clear-search behavior, and existing deterministic project context behavior remained intact.
- Full quality gates passed (`black`, `ruff`, `mypy`, `pytest`) with full-suite regression count unchanged at 1177 tests.

### Remaining UX Debt

- Some lower-priority advanced/object-detail pages still rely on older inline wrappers and should continue migrating to shared primitives.
- Notebook discoverability from core guided-review entry points can be improved further in a future hardening pass.

## Unreleased (Epic X Sprint X-09 Design System Foundation and Reusable UI Components) (Closed)

### Improved

- Atlas shell styling now comes from a centralized design-system stylesheet source instead of a large inline CSS block in the app shell.
- Shared design tokens now provide consistent color, spacing, radius, control sizing, and bounded-layout authority.
- Shared UI primitives now back common rendering patterns (metric cards, empty/guided-empty states, workspace context banners, notice panels, status badges).
- Representative pages (Home, Projects, Knowledge, Reports) now use shared wrappers for section headings, responsive control groups, and table rendering to reduce visual inconsistency.

### Scope Notes

- UI architecture and visual hardening only
- no business-logic or persistence changes
- no Epic E start

### Closeout Validation

- Manual validation confirmed Home, Projects, Knowledge, Reports, Project Workspace shell, focused global search, clear-search behavior, direct search-result navigation, and Settings menu routing.
- Responsive checks at common desktop and split-screen widths showed no horizontal overflow regressions on migrated pages.

### Remaining Migration Debt

- Additional project-workspace pages still rely on legacy inline layout and table wrappers and remain candidates for future design-system primitive migration.

## Unreleased (Documentation Refresh for Atlas Product Direction Update)

### Improved

- Repository documentation now describes Atlas as a commercial SaaS platform for AV and lighting systems integrators.
- Product vision now frames Atlas as an Intelligent Lifecycle Solutions Management Platform with a broader lifecycle roadmap.
- Product vision now documents a future Atlas AI assistant, data boundary, and governance posture.
- Product vision now includes a dedicated foundational-knowledge policy for future AI features.
- Architecture documentation now states the operational-system-of-record vs financial-system-of-record boundary.
- Roadmap documentation now balances future lifecycle areas beyond bid intelligence.
- Onboarding and design guidance now reflect the multi-tenant, AWS, and Stripe direction without changing product behavior.

### Scope Notes

- documentation-only update
- no production code changes
- no change to current Phase 2 implementation priorities

## Unreleased (Sprint D-01 Core Cost Selection Engine)

## Unreleased (Epic A Sprint A-04 Engineering Workstation UX Consolidation)

## Unreleased (Epic X Sprint X-03 Onboarding and Stakeholder Workflow Hardening)

## Unreleased (Epic X Sprint X-06 Responsive Header and Navigation Simplification)

## Unreleased (Epic X Sprint X-08 Search Clear-State Runtime Fix and Visual-System Closeout)

Completion status:

- X-06 responsive shell refinement: completed
- X-07 focused search refinement: completed
- X-08 initial visual-system pass and safe clear-search remediation: completed

### Improved

- Visual-system hardening now standardizes workspace background #FAFAF9 and primary action accent #004225 across the bounded shell.
- Global search now uses separated runtime state for widget input and submitted query.
- Clear Search now performs a safe widget-key reset, exits focused search mode, and returns to the active page context without Streamlit widget-session mutation exceptions.
- Direct search-result navigation clears focused search mode through the same safe reset path.

### Scope Notes

- product hardening only for existing Home/header/search workflows
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or separate customer-document generation workflows

## Unreleased (Epic X Sprint X-07 Fixed-Width Navigation and Focused Search Results)

### Improved

- Global search now shows a focused results view while a meaningful query is active.
- Search result rows are directly clickable, and the results panel replaces the page body during search mode.
- Meaningless punctuation-only search strings no longer trigger broad search rendering.
- Home action buttons stay compact, and the shell navigation remains bounded.

### Scope Notes

- product hardening only for existing Home/header/search workflows

### Improved

- Atlas is now the sole Home action in the global shell.
- The public Home navigation tab has been removed.
- Global Search is now a label-free input with the Search placeholder.
- Settings is now exposed only from an icon-only hamburger trigger.
- The History dropdown has been removed from the global shell.
- The main shell is constrained to a centered workstation-style content width.

### Scope Notes

- product hardening only for existing Home/header/navigation workflows
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or separate customer-document generation workflows

## Unreleased (Epic X Sprint X-05 Top-Header Navigation and Recent Projects)

### Improved

- Primary navigation now lives in the top header rather than a left-column rail.
- Administration is exposed publicly as Settings through an upper-right hamburger menu.
- Home now shows a deterministic Recent Projects list sourced from existing workspace open timestamps.

### Scope Notes

- product hardening only for existing Home/header/navigation workflows
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or separate customer-document generation workflows

## Unreleased (Epic X Sprint X-04 Home Page Simplification and Global Search Refinement)

### Improved

- Application Workspace landing-page terminology is standardized to Home.
- Mission Control remains internal-only as a compatibility route name.
- Header global search now submits directly on Enter.
- Empty/whitespace-only search no longer executes or renders result panels.
- Search results are grouped by user-facing object type with deterministic preferred ordering and safe unknown-type fallback ordering.
- Home content is simplified to primary project actions plus Action Center and Recent Activity.
- Action Center now shows prioritized critical/high deduplicated actions only.

### Scope Notes

- product hardening only for existing Home/header/search workflows
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or separate customer-document generation workflows

### Improved

- Create New Project now enforces strict two-step onboarding: metadata-first create, then Documents upload.
- Create workflow now routes directly to Documents after successful project creation.
- Documents uploader now accumulates pending files across multiple chooser interactions instead of replacing prior selections.
- Pending upload queue now supports deterministic dedupe identity and explicit remove/clear behaviors.
- Upload execution is explicit through Upload Pending Files; no automatic upload on file selection.
- Create and Project Settings now support lookup-first stakeholder organization selection backed by shared organization records.
- Stakeholder workflow now supports inline organization creation with duplicate-warning confirmation.
- Malformed PDF uploads are handled safely by deterministic intake warnings (no UI traceback crash path).

### Scope Notes

- workflow hardening only for existing create/settings/documents flows
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or separate customer-document generation workflows

## Unreleased (Epic X Sprint X-02 Project Creation and Bid Identity Refinement) (Closed)

### Improved

- Create New Project now uses Atlas Bid ID allocation with deterministic non-consuming preview behavior.
- Project metadata now distinguishes Atlas Bid ID, Client Project Number, and Internal Project Number.
- Projects and Open Existing views now surface/search identifier fields for faster retrieval.
- Global search project records now include Atlas Bid ID and client/internal project-number match fields.
- Project Settings now supports controlled identity metadata updates, including lifecycle-stage-aware internal project number editing.
- Mission Control recommendations now include a deterministic prompt when awarded/execution lifecycle stages are missing an internal project number.
- Create New Project now includes an embedded bid-document upload panel with drag/drop, browse, review-before-submit, and explicit create/upload action controls.
- Create workflow now supports partial-success import behavior (accepted files import, rejected files are reported with diagnostics).
- ZIP onboarding now enforces deterministic safety checks (unsafe path rejection, encrypted-entry rejection, system-artifact filtering, depth/entry/expansion limits).

### Scope Notes

- product-hardening and project identity refinement only for existing capabilities
- no Epic E start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or separate customer-document generation workflows

## Unreleased (Epic X Sprint X-01 Pilot Readiness and Application Walkthrough)

### Improved

- Mission Control recommendation selection now includes deterministic guidance framing (why seen, impact, ignore risk, and next action).
- Assembly Library now shows selected-version validation results inline after validation actions.
- Assembly Library state persistence writes are consolidated through shared helper logic for maintainability.

### Scope Notes

- product-hardening and usability refinement only for existing capabilities
- no Commercial Intelligence, Sell Pricing, separate customer-document generation, or post-D architecture expansion

## Unreleased (Epic A Sprint A-05 End-to-End GUI Validation and Workflow Refinement)

### Improved

- Mission Control recommendation panel now includes priority summary counts and direct destination navigation.
- Assembly Library component add workflow now validates required reference inputs with clearer user-facing errors.
- Estimate D-03 refresh comparison workflow now supports explicit preview dismissal before apply.

### Scope Notes

- usability and workflow refinement only across existing capabilities
- no Epic E start and no Commercial Intelligence/Sell Pricing/separate customer-document generation implementation

## Unreleased (Sprint D-03 Assemblies, Accessories, and Labor Rollups)

### Added

- D-03 assembly/labor domain contracts and deterministic expansion service.
- Estimate engine D-03 integration APIs for assembly insertion, refresh, recalculation, version upgrade comparison, and provenance inspection.
- Immutable labor snapshot persistence and generated-line provenance fields.
- Knowledge workspace Assembly Library tab and Estimate workspace D-03 controls.
- Mission Control recommendation ingestion from estimate engine D-03 readiness diagnostics.

### Scope Notes

- D-01 remains deterministic product cost selection authority.
- D-02 remains revision, lock, and cost snapshot authority.
- D-03 implementation is complete and closed with full quality gates and full-suite regressions passing.

### Improved

- Added shared workspace section-header orientation pattern across key workstation pages.
- Consolidated Mission Control recommendation surfaces into a deduplicated, prioritized recommendation table.
- Normalized Knowledge terminology to Products (Master Library).
- Added consistent filter reset controls in dense Knowledge and BOM table views.
- Added direct source-object navigation from estimate revision snapshot viewer.

### Scope Notes

- UX consolidation only.
- No D-03 capabilities introduced.

## Unreleased (Sprint D-01 Core Cost Selection Engine)

### Added

- Explicit deterministic core cost selection APIs:
  - `select_cost`
  - `list_eligible_candidates`
  - `evaluate_candidate`
  - `explain_candidate_rejection`
  - `compare_candidates`
  - `preview_quantity_normalization`
  - `get_selection_provenance`
  - `get_confidence_breakdown`
- New core selection contracts in cost engine domain:
  - `CostSelectionRequest`
  - `CostSelectionResult`
  - `CostProvenance`
  - `CostSelectionDiagnostic`
  - `CostSelectionResultStatus`
- BOM Review Cost Selection Inspector workflow with explicit request controls and deterministic diagnostics/provenance output.

### Scope Notes

- Current sprint scope is D-01 only.
- D-02 is implemented; D-03 is implemented and closed.

## Preview 0.5 (2026-07-07)

### Added

- Engineering Notebook workspace page for structured engineering documentation.
- Notebook entry model with support for:
  - Engineering notes
  - Observations
  - Decisions
  - Assumptions
  - Questions
  - Follow-ups
  - Clarifications
  - Internal coordination notes
  - Site visit notes
  - Meeting notes
  - Review summaries
- Engineering Decisions view as a focused decision log.
- Investigation Mode action to create pre-linked investigation notes.
- Notebook object linking with click-through navigation across relevant workspace pages.
- Notebook entries integrated into activity timeline.
- Context panel support for selected notebook entries.

### Improved

- Preview 0.5 workspace stabilization and UX consistency updates.
- Navigation and workflow continuity across core engineering review pages.

### Documentation

- Added Engineering Notebook reference documentation.
- Added Preview 0.5 stabilization checklist.

### Quality

- Quality gate passed:
  - black
  - ruff
  - mypy
  - pytest (917 passed)

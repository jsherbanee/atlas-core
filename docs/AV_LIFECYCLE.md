# AV Lifecycle

## Purpose
This document defines the authoritative lifecycle framework for Atlas across commercial AV, lighting, control, networked, infrastructure, and managed-service work.

It is the lifecycle counterpart to [DOMAIN_MODEL.md](DOMAIN_MODEL.md) and the lifecycle sequencing companion to [PRODUCT_VISION.md](PRODUCT_VISION.md).

## Related Documents
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [ROADMAP.md](ROADMAP.md)
- [EPICS.md](EPICS.md)

## Scope
Atlas should mature lifecycle stages in a balanced manner rather than disproportionately emphasizing engineering.

The lifecycle applies to both commercial and residential integration contexts and spans AV, lighting, control, networked systems, infrastructure, and managed-service use cases.

## Principles
- Atlas should manage operational truth across the full lifecycle.
- QuickBooks Online remains the Financial System of Record.
- Lifecycle stages should be represented as durable business concepts, not as one-off UI screens.
- Stages may be iterated independently, but the roadmap should mature them as a connected whole.
- Commercial and residential projects share the same core lifecycle with organization-specific configuration.
- Atlas should support human decision-making and approval gates, not replace them.

## Core Concepts
- Lead and opportunity stages capture pursuit and qualification.
- Bid and estimating stages convert requirements into structured commercial intent.
- Award, project initialization, engineering, procurement, and delivery stages carry the project into execution.
- Service, asset lifecycle, and renewal stages extend Atlas beyond project completion.
- Financial-system touchpoints should synchronize with accounting platforms rather than duplicate accounting behavior.

## Lifecycle Stages

### 1. Lead
- Purpose: capture an inbound or outbound sales prospect.
- Primary stakeholders: sales, business development, leadership.
- Atlas objects: Organization, Contact, Opportunity.
- Key inputs: referral, inbound inquiry, prospect profile.
- Key outputs: lead record, qualification tasks, next-step guidance.
- Decisions and approvals: pursue, nurture, disqualify.
- Operational risks: poor-fit pursuits, incomplete account data.
- Financial touchpoints: future customer synchronization in QuickBooks.
- Upstream and downstream dependencies: upstream from marketing; downstream to opportunity qualification.
- Current implementation status: conceptual.
- Future Atlas capabilities: lead scoring, AI-assisted qualification, pipeline analytics.
- Explicit boundaries: Atlas tracks operational pursuit data, not accounting entries.

### 2. Opportunity
- Purpose: represent a live commercial pursuit for a specific organization.
- Primary stakeholders: sales, estimators, project executives.
- Atlas objects: Organization, Contact, Opportunity, Notes, Documents.
- Key inputs: lead history, customer intent, timeline, budget context.
- Key outputs: qualified opportunity, bid/no-bid decision, pursuit plan.
- Decisions and approvals: bid/no-bid, pursuit ownership, target award path.
- Operational risks: stale qualification, duplicate pursuit records.
- Financial touchpoints: future customer and opportunity sync.
- Upstream and downstream dependencies: upstream from lead; downstream to discovery and qualification.
- Current implementation status: partially represented in current commercial and project workflows.
- Future Atlas capabilities: CRM-style pipeline, opportunity scoring, stage forecasting.
- Explicit boundaries: Atlas should not become a generic CRM clone.

### 3. Discovery and Qualification
- Purpose: gather the technical, commercial, and relationship context needed to decide whether to pursue.
- Primary stakeholders: sales, estimators, engineers, project leaders.
- Atlas objects: Opportunity, Contact, Notes, Requirements, Risks.
- Key inputs: stakeholder interviews, site notes, rough scope, budget range, schedule constraints.
- Key outputs: qualification summary, pursuit risk list, bid strategy.
- Decisions and approvals: proceed, hold, decline, re-scope.
- Operational risks: missed constraints, misaligned expectations, incomplete stakeholder mapping.
- Financial touchpoints: future opportunity value and forecast updates.
- Upstream and downstream dependencies: upstream from opportunity; downstream to bid package intake.
- Current implementation status: conceptual.
- Future Atlas capabilities: structured discovery checklists, AI-assisted qualification summaries.
- Explicit boundaries: this stage supports qualification only; it does not finalize scope or pricing.

### 4. Bid Package Intake
- Purpose: collect the source package that defines the formal bid request.
- Primary stakeholders: estimators, project administrators, engineers.
- Atlas objects: Bid Package, Documents, Drawings, Specifications, Schedules, Addenda.
- Key inputs: bid docs, drawings, specs, addenda, schedules, clarifications.
- Key outputs: normalized intake bundle, document inventory, readiness flags.
- Decisions and approvals: accept, defer, reject, request clarification.
- Operational risks: incomplete source package, outdated addenda, missing sheets.
- Financial touchpoints: future bid-document cost tracking and customer context.
- Upstream and downstream dependencies: upstream from discovery/qualification; downstream to bid intelligence.
- Current implementation status: active in current bid-intelligence workflow.
- Future Atlas capabilities: richer intake normalization, package completeness scoring.
- Explicit boundaries: Atlas ingests and indexes package content; it does not issue contractual acceptance by itself.

### 5. Bid Intelligence
- Purpose: extract structured understanding from bid materials.
- Primary stakeholders: estimators, engineers, reviewers.
- Atlas objects: Bid Package, Documents, Drawings, Specifications, Equipment, Evidence, RFI Candidates.
- Key inputs: intake bundle, source documents, historical project context.
- Key outputs: findings, risks, assumptions, clarifications, traceability.
- Decisions and approvals: accepted assumptions, clarification needs, review gating.
- Operational risks: misread scope, hidden exclusions, ambiguous requirements.
- Financial touchpoints: future estimate and proposal readiness.
- Upstream and downstream dependencies: upstream from bid package intake; downstream to estimating.
- Current implementation status: active.
- Future Atlas capabilities: stronger document intelligence, context-aware guidance, cross-project pattern reuse.
- Explicit boundaries: bid intelligence informs the work; it does not finalize a commercial offer.

### 6. Estimating
- Purpose: convert bid intelligence into a structured commercial model.
- Primary stakeholders: estimators, project leaders, commercial reviewers.
- Atlas objects: Estimate, Estimate Revision, Estimate Line Item, Cost Snapshot, Labor Estimate.
- Key inputs: bid intelligence findings, product resolution, commercial knowledge, labor rules.
- Key outputs: priced estimate, confidence indicators, revision history.
- Decisions and approvals: pricing selection, margin strategy, approval to propose.
- Operational risks: stale pricing, incomplete scope, unsupported assumptions.
- Financial touchpoints: future project, invoice, cost-code, and summary synchronization.
- Upstream and downstream dependencies: upstream from bid intelligence; downstream to proposal.
- Current implementation status: active foundation.
- Future Atlas capabilities: richer scenario modeling, pricing policy controls, organization-specific estimating rules.
- Explicit boundaries: Atlas should support estimating without becoming an accounting engine.

### 7. Proposal
- Purpose: present the commercial offer to the customer.
- Primary stakeholders: sales, estimators, leadership, customers.
- Atlas objects: Proposal, Estimate, Scope, Clarifications.
- Key inputs: estimate, scope narrative, commercial terms, exclusions.
- Key outputs: proposal package, approval-ready commercial summary.
- Decisions and approvals: approve, revise, submit.
- Operational risks: misaligned terms, unsupported scope, outdated assumptions.
- Financial touchpoints: future proposal-to-contract handoff and sales-order synchronization.
- Upstream and downstream dependencies: upstream from estimating; downstream to award and contract handoff.
- Current implementation status: partially represented through estimator brief and export outputs.
- Future Atlas capabilities: proposal assembly, pricing narrative, controlled redlines.
- Explicit boundaries: Atlas should support proposals without displacing dedicated document-assembly tools where they remain appropriate.

Transaction-architecture note:
- Proposal is a first-class commercial document family and should eventually participate in the Transactions workspace as a transaction object, not only as a project artifact.

### 8. Award and Contract Handoff
- Purpose: move from pursuit to executed project authority.
- Primary stakeholders: sales, project executives, operations, legal, customer.
- Atlas objects: Contract, Project, Opportunity, Hand-off checklist.
- Key inputs: approved proposal, award notice, contract terms.
- Key outputs: awarded project record, execution handoff package.
- Decisions and approvals: award acceptance, contract signature, handoff readiness.
- Operational risks: missing obligations, untracked exclusions, undefined responsibilities.
- Financial touchpoints: QuickBooks customer, contract, and billing setup.
- Upstream and downstream dependencies: upstream from proposal; downstream to project initialization.
- Current implementation status: conceptual.
- Future Atlas capabilities: award handoff checklists, contract-metadata extraction.
- Explicit boundaries: Atlas manages operational handoff; accounting-specific contract administration remains external where appropriate.

### 9. Project Initialization
- Purpose: establish the execution context for the awarded project.
- Primary stakeholders: project managers, coordinators, engineers, administrators.
- Atlas objects: Project, Project Workspace, Organization, Team, Budget.
- Key inputs: awarded contract, customer context, project identifiers.
- Key outputs: active project workspace, responsibility map, initial controls.
- Decisions and approvals: project opening, team assignment, baseline readiness.
- Operational risks: incorrect identifiers, missing stakeholder ownership, unbounded setup.
- Financial touchpoints: project synchronization, cost-code mapping, billing context.
- Upstream and downstream dependencies: upstream from award; downstream to engineering and procurement.
- Current implementation status: partially represented by the project workspace and identity workflows.
- Future Atlas capabilities: richer handoff workflows, project setup automation, team-aware controls.
- Explicit boundaries: Atlas should not conflate project initialization with financial setup.

### 10. Engineering
- Purpose: convert the award into coordinated design and execution intent.
- Primary stakeholders: engineers, designers, project managers, programmers.
- Atlas objects: Drawings, Specifications, Systems, Equipment, Engineering Assumptions.
- Key inputs: contract scope, submittals, site conditions, standards, manufacturer data.
- Key outputs: coordinated design intent, issue list, engineering records.
- Decisions and approvals: design approval, exception approval, assumptions accepted.
- Operational risks: incomplete coordination, unsupported product choices, lifecycle conflicts.
- Financial touchpoints: future labor, materials, and budget impacts.
- Upstream and downstream dependencies: upstream from project initialization; downstream to submittals and procurement.
- Current implementation status: active in the bid-intelligence and engineering-intelligence foundation.
- Future Atlas capabilities: deeper engineering workflows, better design traceability, structured design approval.
- Explicit boundaries: engineering remains a pillar, but it should not monopolize the roadmap.

### 11. Submittals and Approvals
- Purpose: formalize proposed products, methods, and exceptions for customer or stakeholder approval.
- Primary stakeholders: engineers, project managers, consultants, customers.
- Atlas objects: Submittal, Approval, Product, Specification.
- Key inputs: engineering intent, product selections, alternate requests.
- Key outputs: approved submittals, rejected items, change notes.
- Decisions and approvals: approve, revise, reject, defer.
- Operational risks: slow approvals, untracked deviations, scope drift.
- Financial touchpoints: QuickBooks-linked project cost impacts where relevant.
- Upstream and downstream dependencies: upstream from engineering; downstream to procurement.
- Current implementation status: conceptual.
- Future Atlas capabilities: submittal packages, approval workflow tracking, revision history.
- Explicit boundaries: Atlas should record approvals, not replace the external approval authority.

### 12. Procurement
- Purpose: translate approved project intent into buy-side commitments.
- Primary stakeholders: purchasing, project managers, operations, vendors.
- Atlas objects: Purchase Order, Vendor, Vendor Offering, Cost Code.
- Key inputs: approved submittals, schedule, estimate, vendor lead times.
- Key outputs: purchase orders, procurement status, order confirmations.
- Decisions and approvals: place order, change order, substitute, expedite.
- Operational risks: lead-time misses, substitutions, price changes, wrong quantities.
- Financial touchpoints: QuickBooks purchase order, bill, and payment synchronization.
- Upstream and downstream dependencies: upstream from submittals; downstream to logistics and receiving.
- Current implementation status: future.
- Future Atlas capabilities: procurement tracking, vendor communications, order-status visibility.
- Explicit boundaries: Atlas should not duplicate full accounting or inventory systems.

Transaction-architecture note:
- Purchase Orders, RFQs, Vendor Quotes, Receiving Records, Vendor Bills, and related closeout state belong to the commercial-operations transaction domain even when linked to a Project lifecycle stage.

### 13. Logistics and Receiving
- Purpose: track movement and receipt of ordered equipment and materials.
- Primary stakeholders: purchasing, warehouse, installers, project managers.
- Atlas objects: Shipment, Receiving Record, Purchase Order, Asset.
- Key inputs: purchase orders, shipment notices, receiving checks.
- Key outputs: received quantities, exceptions, damage records.
- Decisions and approvals: accept, reject, quarantine, expedite follow-up.
- Operational risks: lost shipments, damaged goods, partial deliveries.
- Financial touchpoints: receiving status, bill matching, payment readiness.
- Upstream and downstream dependencies: upstream from procurement; downstream to installation.
- Current implementation status: future.
- Future Atlas capabilities: receiving workflows, shipment traceability, exception handling.

## Sprint L-01 Lifecycle Engine Foundation

Sprint L-01 introduces the first deterministic lifecycle-engine implementation for Atlas.

Implemented in L-01:
- one canonical lifecycle authority for stage definitions and sequencing
- deterministic stage-status model separate from legacy `ProjectStatus`
- deterministic transition contracts with required reason and tenant enforcement
- lifecycle readiness, diagnostics, and history event contracts
- project compatibility mapping between canonical lifecycle stages and legacy project statuses
- lifecycle-plan persistence in project metadata and compatibility-safe UI/search/repository projections

Still deferred in L-01:
- procurement, installation, commissioning, training, warranty, service, and asset-lifecycle workflow execution
- downstream departmental automation beyond lifecycle-state modeling
- billing/accounting/ERP execution behavior

See [LIFECYCLE_ENGINE.md](LIFECYCLE_ENGINE.md) for the implementation-facing authority.

## Transactions Architecture Note

Atlas lifecycle and transaction architecture are related but distinct.

- lifecycle stages describe business progression across the full project/service journey
- transaction families describe operational commercial documents that may participate in those stages
- transactions may be linked to Projects, Customers, Vendors, and other transactions, but may also exist with no Project linkage

See [TRANSACTIONS_ARCHITECTURE.md](TRANSACTIONS_ARCHITECTURE.md) for the commercial-document ownership model.
- Explicit boundaries: Atlas should coordinate logistics state without becoming a warehouse management system.

### 14. Project Management
- Purpose: coordinate schedule, scope, and execution across the project.
- Primary stakeholders: project managers, coordinators, field leaders, operations.
- Atlas objects: Project, Forecast, Budget, Issue, Change Order.
- Key inputs: project plan, procurement status, field progress, risk signals.
- Key outputs: action plan, forecasts, issue tracking, status reporting.
- Decisions and approvals: reprioritize, escalate, approve change, recover schedule.
- Operational risks: unmanaged scope drift, schedule slippage, unresolved blockers.
- Financial touchpoints: budget updates, forecast changes, billing status.
- Upstream and downstream dependencies: upstream from project initialization; downstream to installation and commissioning.
- Current implementation status: partially represented through project workspace, reports, and issue tracking concepts.
- Future Atlas capabilities: project dashboards, milestones, operational controls, role-based views.
- Explicit boundaries: Atlas should support project management without becoming a generic PM suite.

### 15. Field Installation
- Purpose: execute the physical build and deployment work.
- Primary stakeholders: field technicians, installers, foremen, project managers.
- Atlas objects: Work Package, Installation Task, Room, Area, Equipment.
- Key inputs: approved design, shipment status, site readiness, installation plans.
- Key outputs: installed equipment, progress updates, field issues.
- Decisions and approvals: proceed, resequence, escalate, rework.
- Operational risks: site access, missing materials, install errors.
- Financial touchpoints: labor tracking, progress billing, change impacts.
- Upstream and downstream dependencies: upstream from logistics and project management; downstream to testing and commissioning.
- Current implementation status: future.
- Future Atlas capabilities: field work tracking, task assignment, progress capture.
- Explicit boundaries: Atlas should record field execution, not replace a field service labor system by default.

### 16. Programming and Configuration
- Purpose: load logic, tune system behavior, and configure integrated systems.
- Primary stakeholders: programmers, engineers, commissioning staff.
- Atlas objects: Configuration Record, System, Equipment, Firmware Notes.
- Key inputs: approved design, network plan, manufacturer requirements.
- Key outputs: programmed systems, configuration records, exceptions.
- Decisions and approvals: deploy configuration, roll back, re-sequence.
- Operational risks: version mismatch, unsupported features, access control issues.
- Financial touchpoints: change orders, service entitlements, vendor licensing.
- Upstream and downstream dependencies: upstream from installation; downstream to testing and commissioning.
- Current implementation status: future.
- Future Atlas capabilities: configuration tracking, programming provenance, firmware awareness.
- Explicit boundaries: Atlas should document configuration state, not replace manufacturer tools where they are required.

### 17. Testing and Commissioning
- Purpose: verify performance, functionality, and acceptance readiness.
- Primary stakeholders: commissioning agents, programmers, engineers, customer reps.
- Atlas objects: Commissioning Record, Test Plan, Punch Item, Issue.
- Key inputs: installed systems, test scripts, acceptance criteria.
- Key outputs: test results, deficiency list, acceptance recommendations.
- Decisions and approvals: pass, retest, accept with exceptions.
- Operational risks: failed tests, incomplete documentation, unresolved punch items.
- Financial touchpoints: milestone billing, closeout readiness, warranty start.
- Upstream and downstream dependencies: upstream from programming and installation; downstream to training and closeout.
- Current implementation status: future, with some readiness/review concepts already present.
- Future Atlas capabilities: test evidence capture, structured commissioning workflows, acceptance tracking.
- Explicit boundaries: Atlas should support verification, not impersonate the authority having jurisdiction.

### 18. Training
- Purpose: prepare owners, operators, and service teams to use the delivered system.
- Primary stakeholders: trainers, project managers, customer staff, service teams.
- Atlas objects: Training Record, Knowledge Article, Closeout Package.
- Key inputs: system configuration, operator needs, as-built documentation.
- Key outputs: training attendance, training materials, readiness signoff.
- Decisions and approvals: training complete, retraining needed.
- Operational risks: poor adoption, undocumented workflows, operator confusion.
- Financial touchpoints: warranty start, closeout billing milestones.
- Upstream and downstream dependencies: upstream from commissioning; downstream to closeout and warranty.
- Current implementation status: future.
- Future Atlas capabilities: training plans, attendance tracking, operator knowledge capture.
- Explicit boundaries: Atlas should capture training evidence without becoming a learning management system by default.

### 19. Punch and Completion
- Purpose: finish the last open items required for contractual completion.
- Primary stakeholders: field leaders, project managers, customers.
- Atlas objects: Punch Item, Issue, Project, Room, Area.
- Key inputs: commissioning results, site inspections, customer comments.
- Key outputs: completed punch list, completion signoff, residual risk log.
- Decisions and approvals: close item, reopen item, accept exception.
- Operational risks: lingering defects, incomplete follow-up, disputed completion.
- Financial touchpoints: retainage, final billing readiness, QuickBooks invoice status.
- Upstream and downstream dependencies: upstream from testing/commissioning; downstream to closeout.
- Current implementation status: future.
- Future Atlas capabilities: punch workflows, completion checklists, field follow-up tracking.
- Explicit boundaries: Atlas should support punch tracking without replacing structured construction management tooling if a customer already uses one.

### 20. Closeout
- Purpose: assemble the final turnover package and capture final project truth.
- Primary stakeholders: project managers, engineers, operations, customers.
- Atlas objects: Closeout Package, As-Built, Commissioning Record, Warranty.
- Key inputs: final drawings, manuals, test results, asset inventory, training records.
- Key outputs: turnover package, archive record, support handoff.
- Decisions and approvals: close project, accept turnover, archive records.
- Operational risks: missing documentation, untracked exceptions, incomplete asset records.
- Financial touchpoints: final invoice, retainage, project close in QuickBooks.
- Upstream and downstream dependencies: upstream from punch and completion; downstream to warranty and service.
- Current implementation status: partially represented through reports and closeout-related documentation.
- Future Atlas capabilities: structured closeout bundles, asset handover, document completeness scoring.
- Explicit boundaries: Atlas should manage operational closeout, not statutory accounting closeout.

### 21. Warranty
- Purpose: support the warranty period after turnover.
- Primary stakeholders: service teams, customers, manufacturers, project managers.
- Atlas objects: Warranty, Asset, Service Ticket, Issue.
- Key inputs: closeout package, warranty terms, serial numbers, service history.
- Key outputs: warranty claims, service actions, warranty status.
- Decisions and approvals: honor claim, route to vendor, bill out-of-scope work.
- Operational risks: lost claim evidence, unclear coverage, response delays.
- Financial touchpoints: service billing, warranty reimbursements, QuickBooks invoicing.
- Upstream and downstream dependencies: upstream from closeout; downstream to service and support.
- Current implementation status: future.
- Future Atlas capabilities: warranty tracking, claim history, coverage alerts.
- Explicit boundaries: Atlas should manage coverage and service history, not manufacture warranty policy.

### 22. Service and Support
- Purpose: handle post-install service requests and operational assistance.
- Primary stakeholders: service dispatch, technicians, customers, support staff.
- Atlas objects: Service Ticket, Asset, Site, Knowledge Record.
- Key inputs: customer calls, monitoring alerts, issue reports, warranty context.
- Key outputs: service resolution, replacement actions, support history.
- Decisions and approvals: triage, dispatch, remote support, replacement.
- Operational risks: repeated failures, poor documentation, SLA misses.
- Financial touchpoints: service invoices, support agreements, warranty reimbursements.
- Upstream and downstream dependencies: upstream from warranty and installed assets; downstream to asset lifecycle management.
- Current implementation status: future.
- Future Atlas capabilities: service queues, SLA tracking, support knowledge reuse.
- Explicit boundaries: Atlas should support service operations without becoming a generic help-desk clone.

### 23. Asset Lifecycle Management
- Purpose: maintain the enduring history of installed systems and components.
- Primary stakeholders: service teams, owners, operations, support, leadership.
- Atlas objects: Asset, Equipment, Site, Service Ticket, Warranty.
- Key inputs: installation records, serial numbers, configuration, service events.
- Key outputs: asset history, configuration lineage, replacement planning.
- Decisions and approvals: repair, replace, upgrade, retire.
- Operational risks: missing serial lineage, untracked changes, unsupported legacy systems.
- Financial touchpoints: service revenue, replacement estimates, renewals.
- Upstream and downstream dependencies: upstream from closeout and service; downstream to upgrade or replacement.
- Current implementation status: future.
- Future Atlas capabilities: asset registry, configuration history, lifecycle analytics.
- Explicit boundaries: Atlas should preserve operational asset history without replacing ERP asset accounting.

### 24. Upgrade, Replacement, and Renewal
- Purpose: support lifecycle decisions after the initial deployment period.
- Primary stakeholders: owners, service teams, sales, operations, finance.
- Atlas objects: Opportunity, Asset, Service History, Renewal Plan.
- Key inputs: asset history, service load, lifecycle risk, business strategy.
- Key outputs: upgrade proposal, replacement plan, renewal opportunity.
- Decisions and approvals: renew, replace, expand, defer.
- Operational risks: unsupported equipment, budget surprises, deferred refresh cycles.
- Financial touchpoints: renewal proposals, replacement estimates, future revenue planning.
- Upstream and downstream dependencies: upstream from asset lifecycle management; downstream to new opportunity and bid stages.
- Current implementation status: conceptual.
- Future Atlas capabilities: renewal forecasting, installed-base intelligence, upgrade planning.
- Explicit boundaries: Atlas should close the loop from opportunity through service and eventual system replacement.

## Current Status
Phase 2 Bid Intelligence is the active implementation target.

Most later lifecycle stages remain conceptual or future, while earlier bid-intelligence and estimating stages already have active repository and workspace representation.

## Future Direction
Atlas should expand lifecycle coverage in a balanced way so that sales, estimating, engineering, procurement, delivery, commissioning, and service mature together.

The lifecycle framework should guide roadmap sequencing, cross-team vocabulary, and future AI grounding.

## Unresolved Decisions
- Exact organization-specific lifecycle customization model remains to be defined.
- The split between Atlas operational records and QuickBooks financial records may vary by integration.
- Some stages will need organization-configurable subflows for commercial, residential, and managed-service use cases.
- Future AI support should align to this lifecycle framework without changing core stage authority.

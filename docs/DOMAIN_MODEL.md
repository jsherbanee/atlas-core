# Atlas Domain Model

## Related Documents
- [README.md](README.md)
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)

## 1. Purpose
This document defines Atlas business architecture as enduring business entities, relationships, lifecycle transitions, and module boundaries.

It is intentionally implementation-agnostic. It defines long-lived business objects that must remain valid across phases, even when services and interfaces evolve.

## 2. Atlas Vision
Atlas is a complete project lifecycle platform for commercial AV, theatrical, themed entertainment, and systems integration companies.

Atlas scope spans:
- Lead
- Opportunity
- Bid Intelligence
- Estimating
- Proposal
- Award
- Engineering
- Procurement
- Financials
- Construction
- Commissioning
- Closeout
- Warranty
- Service
- Knowledge Management

## 3. Lifecycle Diagram
```text
Lead [Future]
	|
	v
Opportunity [Implemented]
	|
	v
Bid Package [Implemented]
	|
	v
Estimate [Implemented - deterministic foundation]
	|
	v
Proposal [In Progress - estimator brief support]
	|
	v
Award [Future]
	|
	v
Project [In Progress - workspace prototype]
	|
	v
Engineering [Future]
	|
	v
Procurement [Future]
	|
	v
Receiving [Future]
	|
	v
Installation [Future]
	|
	v
Commissioning [Future]
	|
	v
Closeout [Future]
	|
	v
Warranty [Future]
	|
	v
Service [Future]
	|
	v
Knowledge Archive [Future]
```

Status legend:
- Implemented: available in active Phase 2 baseline path.
- In Progress: partially represented in current architecture or workspace prototype.
- Future: intentionally deferred to later phases.

## 4. Business Objects

### Organization
- Purpose: Business party container for owners, integrators, vendors, and manufacturers.
- Relationships: has many Contact, Opportunity, Project, Contract, Purchase Order.
- Lifecycle Role: Persistent legal and operational identity across all phases.

### Contact
- Purpose: Person-level stakeholder identity.
- Relationships: belongs to Organization; linked to Opportunity, Project, RFI, Service Ticket.
- Lifecycle Role: Maintains continuity of communication and accountability.

### Opportunity
- Purpose: Pre-award pursuit record.
- Relationships: linked to Organization, Contact, Bid Package, Estimate, Proposal.
- Lifecycle Role: Commercial entry point prior to award.

### Project
- Purpose: Post-award execution container.
- Relationships: derived from Opportunity; owns Project Phase, Contract, Budget, Forecast, Asset.
- Lifecycle Role: Master execution object from award through service.

### Project Phase
- Purpose: Tracks lifecycle stage state for a Project.
- Relationships: belongs to Project; references phase records in engineering, procurement, construction, and closeout.
- Lifecycle Role: Governs stage progression and controls.

### Project Workspace
- Purpose: User-facing project context for review and operations.
- Relationships: linked to Project, Bid Package, Document, Evidence, Estimate.
- Lifecycle Role: Operational lens for project-centric work, independent of single-document workflows.

### Bid Package
- Purpose: Intake bundle of bid source artifacts.
- Relationships: contains Document, Drawing, Specification, Addendum, Schedule.
- Lifecycle Role: Primary input package for bid intelligence.

### Document
- Purpose: Canonical document record and metadata envelope.
- Relationships: parent of Drawing, Specification, Addendum, Schedule; linked to Evidence.
- Lifecycle Role: Durable source artifact across project lifecycle.

### Drawing
- Purpose: Structured drawing sheet record.
- Relationships: belongs to Document and Bid Package; references Room, Area, System, Equipment.
- Lifecycle Role: Source of spatial and system scope.

### Specification
- Purpose: Structured requirements and standards record.
- Relationships: belongs to Document and Bid Package; references Product, Equipment, Contract constraints.
- Lifecycle Role: Compliance and scope authority.

### Addendum
- Purpose: Formal bid or contract revision artifact.
- Relationships: belongs to Document and Bid Package; affects Estimate, Proposal, Contract, Change Order.
- Lifecycle Role: Controlled scope and risk change input.

### Schedule
- Purpose: Structured schedule data (device, equipment, matrix, and similar).
- Relationships: belongs to Document and Bid Package; references Equipment, System, Room, Area.
- Lifecycle Role: Quantitative scope bridge from documents into estimate and execution.

### Equipment
- Purpose: Scoped item record for products and devices.
- Relationships: linked to Product, System, Room, Area, Estimate Line, Asset.
- Lifecycle Role: Survives from bid identification to installed serviceable asset.

### System
- Purpose: Functional grouping for integrated equipment and pathways.
- Relationships: contains Equipment; linked to Drawing, Room, Area, Commissioning Record.
- Lifecycle Role: Engineering and commissioning backbone.

### Room
- Purpose: Named physical room location.
- Relationships: linked to Drawing, Equipment, System, Asset, Punch Item.
- Lifecycle Role: Physical scope anchor for install and acceptance.

### Area
- Purpose: Broader physical area or zone grouping.
- Relationships: linked to Room, System, Equipment, Construction records.
- Lifecycle Role: Field planning and execution grouping.

### Evidence
- Purpose: Source trace record tying outputs to origin documents or records.
- Relationships: linked to Document, Engineering Assumption, RFI Candidate, Estimate, Issue, Knowledge Record.
- Lifecycle Role: Required auditability layer for advisory and execution decisions.

### Engineering Assumption
- Purpose: Deterministic assumption generated from bid analysis.
- Relationships: linked to Bid Package, Evidence, Estimate, RFI Candidate.
- Lifecycle Role: Advisory planning signal prior to final design and procurement.

### RFI Candidate
- Purpose: Candidate clarification item surfaced by intelligence workflows.
- Relationships: derived from Evidence and Bid Package; may promote to RFI.
- Lifecycle Role: Advisory risk reduction before formal question issuance.

### RFI
- Purpose: Formal clarification transaction.
- Relationships: linked to Project, Drawing, Specification, Issue, Change Order.
- Lifecycle Role: Converts ambiguity into approved direction.

### Estimate
- Purpose: Costed pre-award model of scope.
- Relationships: contains Estimate Line and Labor Estimate; informs Proposal.
- Lifecycle Role: Primary commercial model before award.

### Estimate Line
- Purpose: Atomic estimate scope/cost entry.
- Relationships: belongs to Estimate; references Equipment, Product, System, Room, Area.
- Lifecycle Role: Unit of continuity for downstream order and financial mapping.

### Product Resolution
- Purpose: Deterministic canonical-product mapping record between scoped Equipment and estimate preparation.
- Relationships: linked to Equipment, Product, Manufacturer, Evidence, and Estimate Line preparation context.
- Lifecycle Role: Explicit pre-pricing gate that enforces explainable product identity before any deterministic pricing workflow can proceed.

### Commercial Knowledge
- Purpose: Immutable commercial history layer for product availability and versioned pricing records.
- Relationships: links Manufacturer, Product, Vendor, Vendor Offering, Price Sheet, Price Sheet Version, and Price Record.
- Lifecycle Role: preserves historical commercial context for deterministic estimate readiness and historical bid recreation without mutating prior imports.

### Labor Estimate
- Purpose: Labor hours and confidence model.
- Relationships: belongs to Estimate; linked to Estimate Line and System.
- Lifecycle Role: Capacity and labor cost planning input.

### Proposal
- Purpose: Offer package presented to customer.
- Relationships: derived from Opportunity and Estimate; precedes Contract.
- Lifecycle Role: Commercial conversion artifact.

### Contract
- Purpose: Awarded legal agreement.
- Relationships: linked to Proposal, Project, Change Order, Invoice, Sales Order.
- Lifecycle Role: Authoritative execution and billing basis.

### Sales Order
- Purpose: Internal sell-side fulfillment order.
- Relationships: linked to Contract, Project, Invoice, Receipt.
- Lifecycle Role: Revenue fulfillment bridge.

### Purchase Order
- Purpose: Buy-side procurement commitment.
- Relationships: linked to Vendor, Product, Equipment, Shipment, Vendor Bill.
- Lifecycle Role: Procurement execution authority.

### Vendor
- Purpose: External supplier or subcontractor record.
- Relationships: linked to Organization, Purchase Order, Vendor Bill, Payment, Shipment.
- Lifecycle Role: Buy-side execution counterparty.

### Manufacturer
- Purpose: Product source and compliance origin.
- Relationships: linked to Product, Equipment, Submittal, Warranty.
- Lifecycle Role: Product authority and support source.

### Product
- Purpose: Catalog-level product definition.
- Relationships: linked to Manufacturer, Equipment, Estimate Line, Purchase Order, Asset.
- Lifecycle Role: Stable identity from design through service.

### Shipment
- Purpose: Delivery movement record for procured goods.
- Relationships: linked to Purchase Order, Vendor, Receiving Record.
- Lifecycle Role: Logistics traceability event.

### Receiving Record
- Purpose: Receipt verification and condition capture.
- Relationships: linked to Shipment, Purchase Order, Asset.
- Lifecycle Role: Inventory acceptance control.

### Invoice
- Purpose: Customer billing record.
- Relationships: linked to Contract, Sales Order, Payment, Receipt.
- Lifecycle Role: Revenue realization.

### Vendor Bill
- Purpose: Supplier payable record.
- Relationships: linked to Vendor, Purchase Order, Payment.
- Lifecycle Role: Cost recognition for payables.

### Payment
- Purpose: Monetary settlement record.
- Relationships: linked to Invoice or Vendor Bill; linked to Receipt.
- Lifecycle Role: Financial settlement event.

### Receipt
- Purpose: Allocation record confirming funds receipt.
- Relationships: linked to Invoice, Payment, Sales Order, Project.
- Lifecycle Role: Receivable closure and audit trace.

### Budget
- Purpose: Approved project financial plan.
- Relationships: linked to Project, Forecast, Estimate.
- Lifecycle Role: Financial governance baseline.

### Forecast
- Purpose: Forward projection of cost, margin, and cash outcomes.
- Relationships: linked to Project, Budget, Change Order, Issue.
- Lifecycle Role: Ongoing project control and risk prediction.

### Change Order
- Purpose: Controlled scope and value adjustment.
- Relationships: linked to Contract, Project, RFI, Issue, Forecast.
- Lifecycle Role: Formal change mechanism after award.

### Issue
- Purpose: Trackable blocker, risk, or defect.
- Relationships: linked to RFI, Submittal, Punch Item, Commissioning Record.
- Lifecycle Role: Execution quality and risk management.

### Punch Item
- Purpose: Outstanding completion defect or action item.
- Relationships: linked to Project, Room, Area, Issue, Closeout Package.
- Lifecycle Role: Pre-closeout completion control.

### Commissioning Record
- Purpose: Verification and acceptance test record.
- Relationships: linked to System, Equipment, Asset, Issue, Punch Item.
- Lifecycle Role: Operational readiness gate.

### Closeout Package
- Purpose: Turnover bundle of final project artifacts.
- Relationships: linked to Project, Commissioning Record, Asset, Warranty.
- Lifecycle Role: Completion and handover record.

### Warranty
- Purpose: Coverage terms and obligations.
- Relationships: linked to Contract, Product, Manufacturer, Asset, Service Ticket.
- Lifecycle Role: Post-closeout entitlement and risk transfer.

### Asset
- Purpose: Installed and maintainable operational instance.
- Relationships: derived from Equipment and Product; linked to Commissioning Record, Warranty, Service Ticket.
- Lifecycle Role: Long-lived field object through service lifecycle.

### Service Ticket
- Purpose: Post-install service work record.
- Relationships: linked to Asset, Warranty, Contact, Issue, Knowledge Record.
- Lifecycle Role: Service execution and customer support flow.

### Knowledge Record
- Purpose: Reusable knowledge from project and service outcomes.
- Relationships: linked to Project, Evidence, Issue, Service Ticket, Asset.
- Lifecycle Role: Knowledge archive and continuous improvement engine.

## 5. Object Relationships
```text
Organization
	|
	+-- Contact
	|
	+-- Opportunity
			 |
			 +-- Bid Package
			 |    +-- Document
			 |    |    +-- Drawing
			 |    |    +-- Specification
			 |    |    +-- Addendum
			 |    |    +-- Schedule
			 |    +-- Evidence
			 |    +-- Engineering Assumption
			 |    +-- RFI Candidate
			 |
			 +-- Estimate
						+-- Estimate Line
						+-- Labor Estimate
						+-- Proposal

Award
	|
	v
Project
	+-- Project Phase
	+-- Project Workspace
	+-- Systems
	+-- Equipment
	+-- Financials
	|    +-- Contract
	|    +-- Sales Order
	|    +-- Invoice
	|    +-- Vendor Bill
	|    +-- Payment
	|    +-- Receipt
	|    +-- Budget
	|    +-- Forecast
	+-- Procurement
	|    +-- Purchase Order
	|    +-- Vendor
	|    +-- Manufacturer
	|    +-- Product
	|    +-- Shipment
	|    +-- Receiving Record
	+-- Construction
	|    +-- Room
	|    +-- Area
	|    +-- Issue
	|    +-- Punch Item
	+-- Commissioning Record
	+-- Closeout Package
	+-- Warranty
	+-- Asset
	+-- Service Ticket
	+-- Knowledge Record
```

## 6. Object Continuity
Objects should evolve through lifecycle stages rather than being recreated as disconnected data.

Continuity example:
```text
Equipment
	|
	v
Estimate Line
	|
	v
Purchase Order
	|
	v
Receiving
	|
	v
Installed Asset
	|
	v
Commissioning
	|
	v
Warranty
	|
	v
Service
```

Same object. Different lifecycle stage.

## 7. Services vs Business Objects

### Business Objects
Business objects are persistent records that survive lifecycle transitions.

Examples:
- Project
- Equipment
- Estimate
- Purchase Order
- Asset
- Service Ticket
- Knowledge Record

### Services
Services execute workflows on top of business objects and should not replace durable object identity.

Service examples:
- Atlas Intake
- Bid Intelligence
- Estimator Review
- Revision Comparison
- Knowledge Graph
- Reporting
- Search

Services operate on business objects and emit derived outputs, but authoritative records remain in business object stores.

## 8. Atlas Modules

### Atlas Intake
- Purpose: Deterministic file intake and classification.
- Primary objects: Bid Package, Document, Drawing, Specification, Addendum, Schedule, Evidence.
- Implementation status: Implemented.

### Atlas Projects
- Purpose: Project-level workspace, lifecycle state, and continuity orchestration.
- Primary objects: Project, Project Phase, Project Workspace.
- Implementation status: Partial.

### Atlas Bid Intelligence
- Purpose: Risk, readiness, and advisory analysis during bidding.
- Primary objects: Bid Package, Engineering Assumption, RFI Candidate, Evidence.
- Implementation status: Implemented.

### Atlas Estimating
- Purpose: Scope-cost modeling and labor estimation.
- Primary objects: Estimate, Estimate Line, Labor Estimate, Equipment, System.
- Implementation status: Partial.

### Atlas Engineering
- Purpose: Technical development and approvals after award.
- Primary objects: Project Phase, System, Submittal, Issue.
- Implementation status: Planned.

### Atlas Procurement
- Purpose: Buy-side execution and supply coordination.
- Primary objects: Purchase Order, Vendor, Manufacturer, Product, Shipment, Receiving Record.
- Implementation status: Planned.

### Atlas Financials
- Purpose: Commercial and accounting records.
- Primary objects: Contract, Sales Order, Invoice, Vendor Bill, Payment, Receipt, Budget, Forecast.
- Implementation status: Planned.

### Atlas Construction
- Purpose: Field execution and installation controls.
- Primary objects: Project, Room, Area, Equipment, Issue, Punch Item.
- Implementation status: Planned.

### Atlas Closeout
- Purpose: Turnover and completion package management.
- Primary objects: Closeout Package, Commissioning Record, Asset, Warranty.
- Implementation status: Planned.

### Atlas Service
- Purpose: Post-closeout support operations.
- Primary objects: Service Ticket, Asset, Warranty, Knowledge Record.
- Implementation status: Planned.

### Atlas Knowledge Graph
- Purpose: Cross-project knowledge reuse and linkage.
- Primary objects: Knowledge Record, Evidence, Asset, Issue.
- Implementation status: Planned.

### Atlas Reporting
- Purpose: Cross-module analytics, dashboards, and exports.
- Primary objects: Estimate, Forecast, Issue, Service Ticket, Knowledge Record.
- Implementation status: Partial.

### Atlas Administration
- Purpose: Tenant configuration, policies, and access management.
- Primary objects: Organization, Contact, workspace policy objects.
- Implementation status: Deferred.

## 9. Phase Boundaries
Current implementation remains Phase 2 Bid Intelligence.

Implemented (Phase 2):
- Document Intake
- Project Snapshot
- Bid Package Review
- Engineering Assumptions
- Readiness
- Estimator Brief
- RFI Candidates
- Labor Estimate
- Revision Comparison
- Evidence
- Workspace Prototype

Deferred:
- Procurement
- Financials
- Project Execution
- Scheduling
- Receiving
- Commissioning
- Closeout
- Warranty
- Service

## 10. Source of Truth
Ownership expectations:
- Documents: canonical document and metadata records.
- Evidence: immutable trace links between outputs and sources.
- Project Metadata: authoritative project master profile.
- Estimate: authoritative pre-award estimating record with revisions.
- Financials: authoritative only after award conversion and financial execution.
- Assets: authoritative installed and maintained device records.
- Knowledge: reusable outcome and service intelligence records.

Clarifications:
- Phase 2 intelligence is advisory only.
- Financial records become authoritative only after project award and downstream execution workflows.

## 11. Cloud Architecture Considerations
Future architecture should support:
- Local Workspace
- Shared Workspace
- S3 Storage
- Project History
- Audit Trail
- Role-Based Access
- Organization Workspaces
- Remote Collaboration

These are architecture targets only and are not implemented in this phase.

## 12. UX Implications
Atlas Workspace should be project-centric rather than document-centric.

Long-term navigation should support:
1. Home
2. Projects
3. Documents
4. Estimating
5. Engineering
6. Procurement
7. Financials
8. Construction
9. Closeout
10. Service
11. Reports
12. Administration

Phase 2 interfaces may expose only implemented sections and omit or disable future sections.

## 13. Architecture Rules
- Business objects must survive lifecycle transitions.
- Services should remain stateless where practical.
- Source traceability must always be preserved.
- Do not duplicate durable objects.
- Do not hardcode reference projects.
- Cloud infrastructure should remain behind adapters.
- Maintain deterministic behavior whenever possible.

## Related Documents
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [ROADMAP.md](ROADMAP.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- [PHASE2_BASELINE.md](PHASE2_BASELINE.md)
- [PHASE2_GUI.md](PHASE2_GUI.md)
- [CODEX_WORKFLOW.md](CODEX_WORKFLOW.md)
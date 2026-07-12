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
- Bid Package
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

### Sprint X-02 Identity Refinement
- Atlas now separates workspace identity into explicit fields used together in project workflows:
	- Atlas Bid ID: deterministic bid/workspace identifier for repository and cross-workspace lookup.
	- Client Project Number: optional external/customer identifier.
	- Internal Project Number: optional internal execution identifier, typically assigned after award/execution transition.
- These fields refine identity clarity inside existing project/bid lifecycle surfaces and do not introduce new post-award execution workflows.

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

### Estimate Revision (D-02 Implemented)
- Purpose: Immutable-or-draft revision container for material estimate changes.
- Relationships: belongs to Estimate; owns Estimate Line Item, Cost Snapshot, Estimate Totals, Estimate Diagnostic.
- Lifecycle Role: Deterministic history and replay boundary for estimating decisions.

### Estimate Line Item (D-02 Implemented)
- Purpose: Revision-scoped atomic estimating entry with quantity intent and selected cost snapshot reference.
- Relationships: belongs to Estimate Revision; references Equipment, Product, System, Room, Area, Cost Snapshot.
- Lifecycle Role: Stable unit for revision comparison and lock readiness.

### Cost Snapshot (D-02 Implemented)
- Purpose: Immutable record of D-01 cost selection and provenance at line scope.
- Relationships: belongs to Estimate Revision and Estimate Line Item; references Vendor Offering, Price Sheet Version, Price Record.
- Lifecycle Role: Guarantees deterministic historical replay independent of mutable current commercial views.

### Assembly Definition (D-03 Implemented)
- Purpose: Deterministic reusable template describing component and accessory composition.
- Relationships: linked to Product, System context, and versioned Assembly Revision records.
- Lifecycle Role: Enables repeatable line-item composition without hidden inference.

### Assembly Revision (D-03 Implemented)
- Purpose: Immutable version of an Assembly Definition used for deterministic replay.
- Relationships: referenced by Estimate Revision expansion runs and generated Estimate Line Items.
- Lifecycle Role: Preserves historical composition logic over time.

### Labor Rollup (D-03 Implemented)
- Purpose: Revision-scoped deterministic labor output derived from estimate composition and labor rulesets.
- Relationships: belongs to Estimate Revision; references Labor RuleSet versions and generated labor categories.
- Lifecycle Role: Produces replayable labor planning outputs while preserving D-02 immutability boundaries.

### Estimate Diagnostic (D-02 Implemented)
- Purpose: Deterministic readiness and validation signal at estimate/revision/line scope.
- Relationships: belongs to Estimate Revision; references line and snapshot context when applicable.
- Lifecycle Role: Lock-blocking and advisory quality governance for revision transitions.

### Product Resolution
- Purpose: Deterministic canonical-product mapping record between scoped Equipment and estimate preparation.
- Relationships: linked to Equipment, Product, Manufacturer, Evidence, and Estimate Line preparation context.
- Lifecycle Role: Explicit pre-pricing gate that enforces explainable product identity before any deterministic pricing workflow can proceed.

### Commercial Knowledge
- Purpose: Immutable commercial history layer for product availability and versioned pricing records.
- Relationships: links Manufacturer, Product, Vendor, Vendor Offering, Price Sheet, Price Sheet Version, and Price Record.
- Lifecycle Role: preserves historical commercial context for deterministic estimate readiness and historical bid recreation without mutating prior imports.

### Cost Selection (D-01)
- Purpose: Deterministic acquisition cost selection contract layer for estimate lines and inspector workflows.
- Relationships: consumes Commercial Knowledge history and Product Resolution outputs; emits selected and rejected cost candidates plus provenance/diagnostics.
- Core objects: CostSelectionRequest, CostSelectionResult, CostProvenance, CostSelectionDiagnostic, CostSelectionResultStatus.
- Lifecycle Role: D-01 implementation object set and dependency contract for D-02 snapshots.

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

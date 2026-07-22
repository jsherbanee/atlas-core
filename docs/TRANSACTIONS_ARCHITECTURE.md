# Transactions Architecture

## Purpose

This document defines the architecture for the future Transactions workspace in Atlas.

Sprint A-07 is documentation-only.

No transaction code, routes, workflows, integrations, or accounting behavior are implemented in this sprint.

This document exists to define:
- transaction families
- ownership boundaries between Atlas and QuickBooks Online
- optional Project linkage rules
- customer-side and vendor-side document flows
- universal object expectations for transaction records
- future navigation model for the Transactions workspace

## T-01 Implementation Note

Sprint T-01 implements shared backend commercial-document foundation contracts/services for transaction-family objects.

Implemented in T-01:
- shared object contract behavior for document identity, line identity, lifecycle, revision, relationships, approval state, numbering policy, diagnostics, totals, and sync metadata
- tenant- and organization-scoped numbering preview/allocation semantics with no reuse
- mutable draft and immutable issued revision behavior through explicit lifecycle transitions
- universal-object registry integration for initial transaction families

Still deferred:
- transactions workspace UI pages
- QuickBooks transport APIs
- accounting/payment/ledger workflows

Related documents:
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [AV_LIFECYCLE.md](AV_LIFECYCLE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [NAVIGATION_ARCHITECTURE.md](NAVIGATION_ARCHITECTURE.md)
- [COMMERCIAL_DOCUMENT_FRAMEWORK.md](COMMERCIAL_DOCUMENT_FRAMEWORK.md)
- [validation/AV-00E_VALIDATION_TRANSCRIPT.md](validation/AV-00E_VALIDATION_TRANSCRIPT.md)

## AV-00E Validation Reference

AV-00E non-blocking project estimate-open route behavior, sandbox execution caveat, and legacy heavy-path timing evidence are documented in [validation/AV-00E_VALIDATION_TRANSCRIPT.md](validation/AV-00E_VALIDATION_TRANSCRIPT.md).

## Architectural Position

Transactions are first-class operational Atlas objects.

Transactions are not accounting-ledger entries.

Atlas owns operational document creation, review, approval, fulfillment coordination, receiving, sync-readiness evaluation, and closeout state.

QuickBooks Online remains the Financial System of Record.

Transactions therefore sit between:
- project and customer/vendor operational workflows inside Atlas
- financial posting, payment, and statutory reporting inside QuickBooks

## Transactions Workspace

Transactions is a future primary navigation area.

Primary navigation target model:
- Atlas
- Projects
- Knowledge
- Transactions
- Reports
- Search
- Settings

Transactions is intended to be workspace-scoped, not project-scoped.

## T-02 Implementation Note

Sprint T-02 implements the first Transactions workspace UI and navigation foundation.

Implemented in T-02:
- Transactions is now a primary application workspace in the shell navigation
- secondary sections are implemented for Overview, Estimates, Sales Orders, Purchase Orders, RFQs, Vendor Quotes, Receiving, Vendor Bills, Customer Invoices, and Change Orders
- tertiary actions are implemented as reusable transaction controls (Add, Browse, Edit, Related Documents, Approvals, Sync Status, Activity, Export)
- session-backed transaction draft management is implemented on top of the T-01 commercial-document backend foundation
- transactions are indexed in global search and route to Object Workspace for supported commercial-document kinds

Still deferred:
- QuickBooks transport and sync execution APIs
- accounting ledger, payments, and reconciliation behavior
- automatic document conversion workflows

## T-03 Implementation Note

Sprint T-03 operationalizes Estimates as the first full transaction family.

## U-01 Implementation Note

Sprint U-01 delivers usability and presentation polish for already-implemented commercial transaction families.

Implemented in U-01:
- standardized tertiary action contracts across Sales Orders, Return Orders, Credit Memos, and Customer Invoices to match active supported workflows
- unified export controls on deterministic `export_pdf` actions for commercial-document families in active scope
- expanded related-document visibility with explicit source and lineage references alongside relationship lists
- line-presentation sorting parity extension for additional numeric commercial columns (`unit_cost`, `discount`, `tax_rate`)

Still deferred:
- QuickBooks transport APIs
- accounting ledger and payment processing behavior
- inventory/procurement workflow activation

## C-03 Implementation Note

Sprint C-03 integrates commercial catalog foundation behavior into existing transaction families.

Implemented in C-03:
- catalog-backed line insertion for Estimates, Sales Orders, Return Orders, and Customer Invoices
- catalog line metadata persistence (`catalog_item_id`, pricing policy, manual override flag, tax nexus, applied tax rules)
- policy-based unit-price selection through catalog pricing defaults with explicit manual override precedence
- nexus-based tax-rate derivation for transaction line insertion
- compatibility-safe preservation of manual line workflows and existing line-presentation behavior

Still deferred:
- procurement execution and inventory activation
- live QuickBooks transport execution and accounting-ledger ownership

Implemented in T-03:
- estimate-specific tertiary workflow actions: Add, Browse, Edit, Lines, Revisions, Issue, Approvals, Related Documents, Activity, Export
- deterministic reuse of the existing estimate engine for estimate line editing, validation, revision history, and issue readiness
- issue gating that requires approval and lock-ready revision state before commercial-document issue transition
- post-issue draft revision support for estimate updates while preserving issued revision immutability
- standalone estimate creation/editing guardrails requiring customer identity when no project is linked

Still deferred:
- non-estimate transaction-family deep operational workflows
- external sync transport execution and financial posting behavior

## T-08 Implementation Note

Sprint T-08 operationalizes Customer Invoices as a deep transaction-family workflow.

Implemented in T-08:
- customer invoice creation from standalone, project, milestone-context, Sales Order, and Change Order origins
- billing controls for full/partial/milestone/progress/line/final strategies with deterministic requested-vs-available enforcement
- explicit overbilling override diagnostics with required reason/actor evidence
- approval and issue flow continuity with immutable issued behavior
- payment-state transitions (`partially_paid`, `paid`, `overdue`, `voided`) on customer invoices
- invoice-specific sync-status handling for external IDs/revisions, reconciliation state, retry behavior, and returned QuickBooks payment status
- transactions navigation and object-workspace/search continuity for customer invoice records

Still deferred:
- live QuickBooks API transport and webhook implementation
- receivable ledger ownership, payment application, and reconciliation accounting behavior

## T-09 Implementation Note

Sprint T-09 introduces project-scoped change-order tracking without introducing a standalone Change Order transaction object.

Implemented in T-09:
- additive changes are authored as Sales Orders and tracked with shared change-order metadata
- deductive changes are authored as Return Orders and tracked with shared change-order metadata
- change-order numbering is project-scoped (`CO #n`) with non-consuming preview and consuming allocation
- duplicate change-order sequence allocation is blocked within a project
- archived change-order numbers remain consumed and are not reused
- shared metadata now includes change-order type/direction, owner change reference, and internal notes on Sales/Return order change orders
- project commercial summary behavior is available for base bid, additive total, deductive total, net change, revised contract value, pending/approved/invoiced/outstanding change values, and ordered change list

Boundary preserved in T-09:
- no separate Change Order document family workflow
- no automatic invoicing behavior
- no live QuickBooks transport behavior

It must support documents that are:
- linked to a Project
- linked to a Customer or Vendor
- linked to another transaction
- standalone with no Project

## Transaction Families

Initial transaction families:
- Estimates
- Sales Orders
- Return Orders
- Purchase Orders
- RFQs
- Vendor Quotes
- Change Orders
- Receiving Records
- Vendor Bills
- Customer Invoices
- Credit Memos
- Subcontracts

Change-order tracking convention:
- Change Orders are represented operationally by Sales Orders (additive) and Return Orders (deductive)
- `change_orders` workspace views are aggregation/reporting views over those document families, not a separate authoritative document object

Each family should be modeled as a first-class business object rather than a one-off page artifact.

## Ownership Boundary

### Atlas Owns

Atlas owns operational creation and workflow for:
- Estimates
- Sales Orders
- Purchase Orders
- RFQs
- Vendor Quotes
- Change Orders
- Receiving Records
- Vendor Bills before sync
- Customer Invoices before sync

Atlas also owns:
- document drafting
- line-item review
- approval state
- receiving and fulfillment state
- variance review
- sync readiness
- sync status tracking
- sync failure handling
- operational closeout state

### QuickBooks Owns

QuickBooks Online owns after sync:
- Accounts Receivable
- Accounts Payable
- payment status
- vendor payments
- customer payments
- general ledger
- taxes
- banking
- reconciliation
- statutory financial reporting

### Boundary Rule

Atlas may originate commercial documents and track their operational lifecycle.

QuickBooks remains authoritative for financial posting and post-sync payment/accounting truth.

Atlas must not be documented or implemented as a general ledger, banking, tax, payment-processing, or reconciliation system.

## Project Linkage Model

Every transaction should support:
- optional Project reference
- optional Project Code

Project linkage must not be mandatory.

Transactions remain valid for:
- service work
- warranty replacement
- parts-only sales
- internal purchases
- recurring maintenance
- standalone consulting
- one-off customer requests

The architecture must allow Project-linked and non-Project-linked transaction workflows to coexist without separate document models.

## Relationship Model

Transactions may be related to:
- Project
- Customer
- Vendor
- Contact
- Organization
- another transaction
- receiving records
- bills or invoices
- source documents and supporting attachments

Examples:
- Sales Order derived from Estimate
- Invoice linked to Sales Order and Change Order
- Purchase Order derived from Vendor Quote or RFQ outcome
- Vendor Bill matched against Purchase Order and Receiving Record

## Customer-Side Flow

Required customer-side commercial flow:

Estimate
→ Sales Order
→ Invoice
→ Sync to QuickBooks
→ Payment status returns to Atlas

Extended customer-return flow:

Sales Order or Invoice
→ Return Order
→ Credit Memo
→ Sync to QuickBooks

Ownership interpretation:
- Atlas owns the operational authoring and approval path through Invoice sync readiness
- QuickBooks owns the financial receivable after sync
- Atlas may display returned payment status but does not become the financial source of truth

## Vendor-Side Flow

Required vendor-side commercial flow:

RFQ
→ Vendor Quote
→ Purchase Order
→ Receiving
→ Vendor Bill
→ Close PO
→ Sync open bill to QuickBooks
→ Payment status returns to Atlas

Ownership interpretation:
- Atlas owns sourcing, quote comparison, PO issuance, receiving, matching, approval, and sync-readiness behavior
- QuickBooks owns payable accounting and payment truth after sync

## Vendor Bill Requirements

Atlas must support, architecturally:
- bill entry or bill import
- matching bill lines to Purchase Order lines
- quantity variance review
- cost variance review
- partial receiving
- partial billing
- final receiving
- bill approval
- PO closeout
- QuickBooks sync readiness
- sync status
- sync failure handling
- payment-status return from QuickBooks

Design implication:
- vendor bill state must remain operationally expressive before sync
- receiving and billing cannot be assumed to be one-step or fully matched
- Purchase Order closeout is an operational state transition, not a financial-ledger action

## Customer Invoice Requirements

Atlas must support, architecturally:
- invoice generation from Sales Order, Project, milestone, Change Order, or standalone work
- line-item review
- billing schedule or milestone reference
- approval
- credit and adjustment handling as future scope
- QuickBooks sync readiness
- sync status
- sync failure handling
- payment-status return from QuickBooks

Design implication:
- invoice origin may be transaction-driven or Project/milestone-driven
- a future invoice object must support both linked and standalone operational billing work

## Universal Object Model For Transactions

The shared commercial-document contract is defined in [COMMERCIAL_DOCUMENT_FRAMEWORK.md](COMMERCIAL_DOCUMENT_FRAMEWORK.md).

Transactions should consume that common framework rather than invent family-specific object envelopes.

This includes the shared line-item contract, revision philosophy, numbering philosophy, approval model, and sync metadata architecture.

## Lifecycle Expectations For Transactions

Transaction lifecycle remains separate from Project lifecycle.

The shared commercial-document lifecycle vocabulary is defined in [COMMERCIAL_DOCUMENT_FRAMEWORK.md](COMMERCIAL_DOCUMENT_FRAMEWORK.md).

Sprint A-07 defined the separation.

Sprint A-08 defines the common commercial-document lifecycle contract.

## Transactions Navigation Model

### Primary Navigation
- Atlas
- Projects
- Knowledge
- Transactions
- Reports
- Search
- Settings

### Transactions Secondary Navigation
- Overview
- Estimates
- Sales Orders
- Purchase Orders
- RFQs
- Vendor Quotes
- Receiving
- Vendor Bills
- Customer Invoices
- Change Orders

### Transactions Tertiary Actions
Action-oriented tertiary actions should include combinations such as:
- Add
- Browse
- Edit
- Approvals
- Related Transactions
- Receiving
- Billing
- Sync Status
- Activity
- Export

These are action patterns, not a promise that every transaction family exposes every tertiary action.

## Transactions Overview Dashboard

Future Transactions Overview should summarize at least:
- Draft Estimates
- Pending Estimates
- Pending Estimates

## T-05 Amendment: Terms and Conditions Settings Integration

Transactions now consume tenant-scoped Terms and Conditions blocks for:
- Estimates
- Sales Orders

Behavior:
- estimate drafts can capture Terms and Conditions snapshots from resolved tenant/project/customer/transaction scope blocks
- sales orders created from estimates can inherit estimate Terms snapshots or resolve sales-order defaults explicitly
- draft terms refresh is explicit user action only; no silent replacement
- issued transaction documents preserve captured terms snapshot content/version immutably

## T-05 Amendment: Versioning, Duplication, Archive/Restore, and PDF Export

Transactions now supports explicit document controls for Estimates and Sales Orders:
- Duplicate
- Create Revision
- Revision History
- Archive
- Restore
- Export PDF

Behavior:
- duplication creates a new draft document with a new ID and number while preserving source traceability
- duplication is not treated as revision continuation of the source document
- revision creation is explicit and records revision reason/date/lineage
- issued revisions remain immutable
- archived documents and revisions remain readable and exportable

PDF export support:
- internal estimate presentation
- customer estimate presentation
- sales order presentation
- deterministic output from the same revision and section configuration

Future delivery hooks:
- non-executing metadata capture for Microsoft 365, Google Workspace, SMTP, and approved future providers
- no mail-provider transport implementation in this sprint

## T-06 Implementation: Return Orders and Credit Memos

Transactions now supports customer-return workflows through:
- Return Orders
- Credit Memos

Return Order behavior:
- supports standalone or linked return initiation
- preserves source-document and source-line traceability
- supports product and service return lines
- supports partial returns
- supports deterministic restocking-fee and tax-adjustment calculations
- supports processing into one linked Credit Memo only

Credit Memo behavior:
- generated from processed Return Orders
- retains QuickBooks sync metadata without implementing transport
- remains immutable once issued
- remains exportable through deterministic PDF export

## T-07 Implementation: Commercial Document Line Presentation

Line-based transaction families now support reusable presentation controls for:
- Estimates
- Sales Orders
- Return Orders
- Credit Memos where applicable

Behavior:
- line grouping and subgroup subtotal display are presentation-only
- manual reordering persists explicit display sequence
- temporary sort preview does not mutate authoritative order
- applied sort updates presentation order without changing financial calculations
- blank spacer and comment rows are stored as presentation metadata on shared line records
- Open Sales Orders
- Open Purchase Orders
- Partially Received POs
- Awaiting Vendor Bills
- Bills Pending Approval
- Bills Pending Sync
- Open Customer Invoices
- Invoices Pending Sync
- Overdue Customer Invoices
- Change Orders Awaiting Approval
- RFQs Awaiting Response

The intent is operational visibility, not financial reporting replacement.

## Integration Boundary With QuickBooks

QuickBooks Online remains the Financial System of Record.

Atlas synchronization should eventually cover selected shared entities such as:
- customers
- vendors
- purchase orders
- bills
- invoices
- payment status

But Atlas must not claim ownership of:
- financial posting
- GL balances
- tax computation authority
- banking and reconciliation
- final payable/receivable accounting truth

Returned QuickBooks status should be treated as synchronized financial-state reference data inside Atlas.

## Audit And Sync Expectations

Every future transaction object should support:
- explicit sync readiness state
- explicit sync status
- external QuickBooks identifiers
- error and retry metadata
- audit trail of operational approvals and state changes
- manual reconciliation support when sync conflicts occur

## Out Of Scope For Sprint A-07

- no production code
- no Transactions routes or UI implementation
- no QuickBooks integration implementation
- no ledger or accounting subsystem
- no payment processing
- no procurement execution module
- no Epic E implementation

## Open Architecture Decisions

The following remain intentionally unresolved:
- whether transactions belong to Epic A only or later split into a dedicated epic stream
- final canonical transaction-status taxonomies by family
- whether Subcontracts are modeled as a transaction family or a contract-family sibling with transaction interoperability
- final relationship rules between Change Orders, Sales Orders, and Invoices
- final sync granularity between Atlas transaction lines and QuickBooks line structures
- final approval-policy model by tenant and transaction type

## PX-03 Implementation: Commercial Transaction Workbench

Transactions now presents supported customer-side commercial documents through
a workbench-oriented selected-document view.

Supported workbench families:
- Estimates
- Sales Orders
- Return Orders
- Invoices
- Credit Memos

The workbench organizes existing authoritative transaction data into:
- document summary
- commercial health findings
- readiness checklist
- deterministic recommendation
- line item workspace
- commercial totals
- relationship and lineage summary

PX-03 does not change commercial-document persistence, numbering, lifecycle
rules, totals calculation, approval behavior, sync semantics, QuickBooks
ownership boundaries, procurement execution, or accounting authority.

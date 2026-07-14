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

Related documents:
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [AV_LIFECYCLE.md](AV_LIFECYCLE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [NAVIGATION_ARCHITECTURE.md](NAVIGATION_ARCHITECTURE.md)

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

It must support documents that are:
- linked to a Project
- linked to a Customer or Vendor
- linked to another transaction
- standalone with no Project

## Transaction Families

Initial transaction families:
- Estimates
- Proposals
- Sales Orders
- Purchase Orders
- RFQs
- Vendor Quotes
- Change Orders
- Receiving Records
- Vendor Bills
- Customer Invoices
- Subcontracts

Each family should be modeled as a first-class business object rather than a one-off page artifact.

## Ownership Boundary

### Atlas Owns

Atlas owns operational creation and workflow for:
- Estimates
- Proposals
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
- Proposal derived from Estimate
- Sales Order derived from Proposal
- Invoice linked to Sales Order and Change Order
- Purchase Order derived from Vendor Quote or RFQ outcome
- Vendor Bill matched against Purchase Order and Receiving Record

## Customer-Side Flow

Required customer-side commercial flow:

Estimate
→ Proposal
→ Sales Order
→ Invoice
→ Sync to QuickBooks
→ Payment status returns to Atlas

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

Each transaction family should be defined as a first-class Atlas object with:
- stable ID
- transaction type
- status
- customer or vendor
- optional Project
- optional Project Code
- line items
- totals
- approvals
- relationships
- activity
- documents
- lifecycle
- sync metadata
- external QuickBooks identifiers

This keeps transaction records compatible with Atlas object philosophy:
- stable identity
- explicit provenance
- relationship-aware navigation
- auditability
- tenant-safe integration behavior

## Lifecycle Expectations For Transactions

Transaction lifecycle is separate from Project lifecycle.

Project lifecycle tracks end-to-end project progress.

Transaction lifecycle should eventually track commercial-document state such as:
- draft
- under review
- approved
- issued
- partially fulfilled
- received
- billed
- synced
- closed
- canceled

Sprint A-07 does not define a transaction engine implementation.

It only establishes that transaction lifecycle must exist as a separate but compatible domain concern.

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
- Proposals
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
- Pending Proposals
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
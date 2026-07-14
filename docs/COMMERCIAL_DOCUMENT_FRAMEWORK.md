# Commercial Document Framework

## Purpose

This document defines the common architecture for future commercial documents in Atlas.

Sprint A-08 is documentation-only.

No production code, UI, QuickBooks integration, routing, or workflow implementation is introduced in this sprint.

This framework is the shared foundation for:
- Estimates
- Proposals
- Sales Orders
- Purchase Orders
- RFQs
- Vendor Quotes
- Receiving Records
- Vendor Bills
- Customer Invoices
- Change Orders
- Subcontracts

Related documents:
- [TRANSACTIONS_ARCHITECTURE.md](TRANSACTIONS_ARCHITECTURE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [LIFECYCLE_ENGINE.md](LIFECYCLE_ENGINE.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)

## Framework Role

Commercial documents are first-class Atlas operational objects.

They are not accounting-ledger records.

The framework exists to provide one reusable contract for document identity, revisions, approvals, relationships, lifecycle, and sync metadata across all transaction families.

The intent is to prevent each document family from inventing its own incompatible model.

## Shared Commercial Document Contract

Every commercial document family should support the following common contract:

- Document ID
- Document Number
- Document Type
- Status
- Revision
- Customer or Vendor
- Optional Project
- Optional Project Code
- Line Items
- Pricing
- Taxes
- Currency
- Attachments
- Notes
- Related Documents
- Related Objects
- Approval State
- Lifecycle
- Activity
- Sync Metadata
- External Accounting IDs

### Contract Interpretation

Document ID:
- stable internal Atlas identifier
- tenant-scoped
- not dependent on visible numbering format

Document Number:
- human-facing operational reference number
- may be tenant-configurable by document family
- must remain stable once issued for a specific revision

Document Type:
- explicit family identity such as estimate, proposal, purchase_order, or customer_invoice

Status:
- current business state for the active revision of the document

Revision:
- current revision reference for the active document view

Customer or Vendor:
- commercial counterparty reference
- may be customer-side or vendor-side depending on document family

Optional Project and Optional Project Code:
- linkage fields, not mandatory ownership requirements
- documents remain valid without a Project reference

Line Items:
- normalized document lines with quantities, pricing, references, and optional product/service associations

Pricing, Taxes, Currency:
- operational commercial values used for review and sync readiness
- not a substitute for accounting-system tax authority or ledger truth

Attachments and Notes:
- supporting operational evidence, redlines, source files, or coordination notes

Related Documents and Related Objects:
- deterministic linkage to predecessor/successor documents, Projects, Organizations, or other Atlas objects

Approval State:
- structured approval evidence and current approval posture

Lifecycle:
- document-state progression independent of Project lifecycle

Activity:
- immutable operational event history

Sync Metadata and External Accounting IDs:
- bridge fields for QuickBooks and future integrations
- never a reason to transfer accounting-system ownership into Atlas

## Standard Commercial Document Lifecycle

The standard architecture lifecycle for commercial documents is:

Draft
→ Review
→ Approved
→ Issued
→ Partially Fulfilled
→ Fulfilled
→ Closed
→ Archived

### Lifecycle Semantics

Draft:
- editable working state
- not yet approved for external issue or downstream fulfillment

Review:
- under structured human review, correction, or comparison
- may include commercial, operational, or approval review gates

Approved:
- approved for issue or downstream operational use
- commercial intent is accepted within Atlas workflow

Issued:
- formally transmitted or committed for operational use
- becomes revision-controlled

Partially Fulfilled:
- partial delivery, receiving, billing, or execution has occurred
- remaining obligations still open

Fulfilled:
- all expected document obligations completed operationally
- may still remain open for final sync, closeout, or archival rules

Closed:
- document is operationally complete and no longer active in normal workflow

Archived:
- retained as historical record with no active operational role

## Lifecycle Terminology Alignment

Commercial-document lifecycle is separate from the Project lifecycle engine.

Alignment rules:
- both domains should use deterministic, explicit state progression
- commercial-document lifecycle should not silently reuse Project stage keys
- commercial-document lifecycle should remain compatible with Atlas state terminology such as review, approval, fulfillment, closeout, and archival
- future implementation may reuse lifecycle-engine patterns, but this sprint does not define a commercial-document engine implementation

## Relationship Model

The framework defines deterministic relationship rules for common commercial-document progressions.

Required canonical relationships:
- Estimate → Proposal
- Proposal → Sales Order
- Sales Order → Invoice
- RFQ → Vendor Quote
- Vendor Quote → Purchase Order
- Purchase Order → Receiving
- Receiving → Vendor Bill
- Vendor Bill → QuickBooks
- Invoice → QuickBooks

### Relationship Principles

- predecessor/successor links should be explicit, not inferred from naming conventions alone
- a document may link to more than one related document where the business workflow requires it
- relationships should support one-to-many and many-to-one cases where operationally valid
- sync relationships to QuickBooks should be modeled as external-system relationships, not as ownership transfer inside Atlas

Examples:
- one Proposal may generate one or more Sales Orders
- one Sales Order may generate multiple invoices over time
- one Purchase Order may map to multiple receiving events and one or more vendor bills

## Revision Philosophy

Commercial documents should use a revision-safe model.

Principles:
- issued revisions are immutable
- revision history is preserved
- superseded revisions remain readable
- audit trail is required
- linked revisions should preserve predecessor/successor lineage

### Revision Rules

- Draft and Review states may allow mutable working revisions
- once a revision is Issued, that revision should become immutable
- changes after issue should create a new revision rather than rewriting prior issued content
- superseded revisions must remain historically reproducible
- linked revision chains must support deterministic audit and relationship traversal

## Document Numbering Philosophy

Document numbering is operational, human-facing, and tenant-aware.

Numbering principles:
- document numbering should be configurable by tenant and document family
- numbering format should remain separate from the immutable Document ID
- numbering should support revisions without changing the base document identity
- Project linkage may influence numbering but must not be required to produce a valid document number
- standalone documents must still receive valid numbers

Examples of future numbering influences:
- Project Code
- tenant prefix
- document family prefix
- sequence number
- revision suffix

Sprint A-08 does not prescribe one final numbering format.

It only defines the architectural rules that numbering must follow.

## Approval Workflow Architecture

Every commercial document family should support structured approval state.

Minimum architecture expectations:
- draft approval not assumed
- approver identity or role
- approval timestamp
- approval status
- rejection or revision-required state
- approval comments or reason
- audit trail of approval changes

Approval architecture should allow:
- single-step approvals
- multi-step approvals
- tenant-specific approval policy in the future

Sprint A-08 does not define a production approval engine.

It defines the required approval envelope for future implementation.

## Sync Metadata Architecture

Commercial documents that synchronize to QuickBooks should carry explicit sync metadata.

Expected sync metadata concepts:
- sync readiness
- sync status
- last sync attempt timestamp
- last sync success timestamp
- failure state
- failure reason
- retry eligibility
- external QuickBooks identifiers
- external revision/version reference where required

Sync principles:
- Atlas owns pre-sync document workflow
- QuickBooks owns financial truth after sync
- synchronization must be explicit, auditable, and idempotent
- sync failure must not destroy the operational document state in Atlas

## Atlas And QuickBooks Ownership Boundary

The framework does not change the A-07 ownership boundary.

Atlas remains the operational owner of document creation and workflow.

QuickBooks remains the financial owner after sync.

This means:
- Atlas may create vendor bills and customer invoices before sync
- Atlas may determine sync readiness and show sync status
- Atlas may show returned payment status from QuickBooks
- Atlas must not become the source of truth for AP, AR, GL, banking, taxes, reconciliation, or statutory reporting

## Optional Project Linkage

Project linkage remains optional for every commercial document.

The framework must support documents for:
- Projects
- service work
- warranty replacement
- parts-only sales
- internal purchases
- recurring maintenance
- standalone consulting
- one-off customer requests

This rule applies to every document family in scope.

## Universal Object Expectations

Commercial documents are expected to become future first-class Atlas objects.

That implies future support for:
- stable identity
- object relationships
- activity history
- lifecycle state
- approvals
- documents and attachments
- sync metadata
- optional Project linkage

Sprint A-08 does not implement those object routes or UI surfaces.

It only defines the common contract they should follow.

## Open Architecture Decisions

Still intentionally unresolved:
- final canonical status taxonomies by document family
- whether all document families share one revision model or allow family-specific overlays
- final tenant-configurable numbering policy surface
- final approval-policy configuration model by tenant and document type
- final QuickBooks sync granularity for line-level versus document-level linkage
- final representation of partially fulfilled states across customer-side and vendor-side documents
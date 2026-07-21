# Commercial Document Framework

## Purpose

This document defines the common architecture for future commercial documents in Atlas.

Sprint A-08 is documentation-only.

No production code, UI, QuickBooks integration, routing, or workflow implementation is introduced in this sprint.

This framework is the shared foundation for:
- Estimates
- Sales Orders
- Return Orders
- Purchase Orders
- RFQs
- Vendor Quotes
- Receiving Records
- Vendor Bills
- Customer Invoices
- Credit Memos
- Change Orders
- Subcontracts

## T-01 Implementation Status

Sprint T-01 implements the backend commercial-document foundation in the Atlas engine layer.

Implemented in T-01:
- shared commercial-document domain models and contracts for identity, lines, relationships, revisions, lifecycle, approval, sync metadata, diagnostics, totals, and numbering policy
- explicit lifecycle transition rules for Draft -> In Review -> Approved -> Issued -> Partially Fulfilled -> Fulfilled -> Closed -> Archived
- immutable issued revision snapshots and mutable pre-issue working revisions
- organization-scoped, tenant-scoped numbering preview/allocation with no number reuse
- decimal-safe totals behavior
- universal-object registry adapter coverage for commercial documents and initial transaction families

Not implemented in T-01:
- transactions UI flows
- QuickBooks API operations
- accounting, payments, or ledger behavior
- approval UI
- automatic document conversion

## T-02 Implementation Status

Sprint T-02 implements the first transactions UI/navigation layer using the T-01 shared contract.

Implemented in T-02:
- reusable transaction workspace service behavior for draft create/list/edit/archive/restore and overview metrics
- first application transactions workspace shell with section/action-oriented navigation
- transaction-family global search indexing and Object Workspace handoff for commercial-document kinds

Deferred in T-02:
- external financial transport integrations
- accounting/payment/ledger workflows

## T-03 Implementation Status

Sprint T-03 makes Estimates the first fully operational transaction family inside Transactions.

Implemented in T-03:
- estimate-specific tertiary actions for Add, Browse, Edit, Lines, Revisions, Issue, Approvals, Related Documents, Activity, and Export
- standalone estimate enforcement requiring customer identity when no project link is provided
- issue flow that preserves commercial-document lifecycle rules (approval required before issue and issued revision immutability)
- revision workflow support for post-issue estimate updates through explicit draft revision start behavior
- deterministic estimate-engine integration for transaction estimates without introducing a second estimate model

Deferred in T-03:
- external financial sync execution
- accounting/payment/ledger workflows

## T-04 Implementation Status

Sprint T-04 introduces tenant-level commercial document numbering preferences through the Settings workspace foundation.

Implemented in T-04:
- organization-scoped numbering policy configuration by commercial document family
- configurable numbering syntax using deterministic tokens (`{PREFIX}`, `{TYPE}`, `{YEAR}`, `{MONTH}`, `{PROJECT_CODE}`, `{SEQUENCE}`, `{SUFFIX}`)
- configurable prefix, suffix, separator, sequence padding, starting sequence, and reset policy
- non-consuming live and next-number previews
- validation for invalid templates and duplicate cross-family signatures that could collide
- audit metadata for settings edits and runtime numbering synchronization

Preserved guarantees in T-04:
- consuming allocation remains in the existing commercial numbering service
- no document number reuse
- previously allocated numbers are preserved when policy settings are edited

## P-05 Implementation Status

## U-01 Implementation Status

Sprint U-01 completes commercial document usability and presentation polish on top of existing T-series and P-series implementation.

Implemented in U-01:
- standardized tertiary workflow contracts for Sales Orders, Return Orders, Credit Memos, and Customer Invoices so supported actions align with implemented behavior
- deterministic PDF export action parity across line-based commercial families (including Return Orders and Credit Memos through the shared `export_pdf` pattern)
- source and related-document lineage visibility improvements in Transactions related-document views
- line-presentation sort parity extension (`unit_cost`, `discount`, `tax_rate`) while preserving authoritative totals semantics
- dedicated Transactions > Estimates > Add workspace for estimate draft creation with dropdown-driven customer/project/project-code capture and catalog-backed Product/Service/Fee/Assembly insertion
- tenant-facing estimate creation excludes Vendor ID while preserving estimate lifecycle and numbering rules

Preserved boundaries in U-01:
- no new commercial document families
- no payment ownership changes
- no inventory/procurement workflow activation
- no QuickBooks API transport execution

Sprint P-05 introduces deterministic document generation and template orchestration for commercial document revisions.

Implemented in P-05:
- shared document-generation contracts for template/version assignment, render context, diagnostics, sections, output artifacts, and render results
- deterministic template resolution with explicit precedence (transaction, project, customer, tenant default, fallback)
- revision-level template snapshot and terms snapshot capture for immutable issued rendering behavior
- settings template model support for template create/version/default/resolve and tenant-scoped export/replace synchronization
- transactions export integration that records template provenance and generated artifact metadata

Deferred in P-05:
- cloud worker implementation changes for generation jobs
- external delivery transport execution
- e-signature and approval workflow expansion

## C-03 Commercial Catalog Integration Note

Sprint C-03 commercial catalog integration now supports deterministic catalog-backed line insertion for Product, Service, Fee, and Assembly references on supported customer-facing commercial document families. Assembly insertion supports both expanded component insertion and grouped parent-plus-components presentation with line-level catalog snapshots.

C-03 preserves existing boundaries:
- no procurement/inventory execution activation
- no accounting ledger ownership change
- no issued-document mutation

## T-08 Implementation Status

Sprint T-08 operationalizes Customer Invoice transactions on top of the shared commercial-document framework.

Implemented in T-08:
- customer-invoice draft creation for standalone, project-driven, and source-linked flows (Sales Order and Change Order)
- billing-strategy metadata capture with available-to-bill and requested-amount controls
- explicit overbilling override diagnostics requiring actor and reason
- lifecycle/payment-state transitions for `partially_paid`, `paid`, `overdue`, and `voided`
- invoice-specific sync-event recording for external invoice IDs, reconciliation state, retry tracking, and returned payment-status metadata
- customer-invoice revision, duplication, and deterministic PDF export continuity through the shared framework

Out of scope in T-08:
- live QuickBooks transport execution
- accounting-ledger behavior
- credit/adjustment automation beyond existing return/credit workflows

## T-09 Implementation Status

Sprint T-09 implements project-scoped change-order tracking using existing Sales Orders and Return Orders instead of a separate Change Order document object.

Implemented in T-09:
- additive change orders are tracked on Sales Orders (`is_change_order=true`, direction `additive`)
- deductive change orders are tracked on Return Orders (`is_change_order=true`, direction `deductive`)
- shared change-order metadata contract on Sales Orders and Return Orders:
	- `is_change_order`
	- `change_order_number`
	- `change_order_sequence`
	- `change_order_type`
	- `change_order_direction`
	- `base_bid_reference`
	- `project_id`
	- `project_code`
	- `change_reason`
	- `requested_by`
	- `approved_by`
	- `approval_date`
	- `effective_date`
	- `owner_change_reference`
	- `internal_notes`
	- `source_document`
	- `related_documents`
- project-scoped authoritative sequence behavior for `CO #n` numbering with non-consuming preview and consuming allocation
- no change-order sequence reuse within a project, including archived documents
- project commercial summary contract for base-bid value, additive/deductive totals, net change, revised contract value, pending/approved/invoiced/outstanding change values, ordered change list, and change-order status

Out of scope in T-09:
- standalone Change Order document-type workflows
- automatic invoicing or live QuickBooks sync
- inventory workflows

## S-01 Settings Completion Status

Sprint S-01 completes the alpha settings baseline that commercial documents consume.

Implemented in S-01:
- terms-family support expanded for settings resolution/snapshot to include `return_order` and `customer_invoice`
- deterministic tax and surcharge rule modeling plus decimal-safe preview for commercial totals planning
- organization profile and security-policy metadata controls used by document governance surfaces
- integrations metadata hooks with secret-reference enforcement for future external-system bindings
- document template duplication and preview controls in settings

Out of scope in S-01:
- live integration transport/authentication behavior
- external tax-engine orchestration
- accounting-ledger ownership changes

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
- explicit family identity such as estimate, sales_order, purchase_order, or customer_invoice

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

## Shared Line-Item Contract

Every commercial document line item should support a shared line-level contract:

- stable line ID
- sequence
- product or service reference
- description
- quantity
- unit of measure
- unit cost
- unit price
- discount
- tax treatment
- extended amount
- project code
- source reference
- fulfillment or receiving state
- related transaction line
- accounting sync reference

T-07 presentation contract additions:
- line type (`item`, `service`, `group_header`, `subtotal`, `blank_spacer`, `comment`)
- display sequence
- manual display sequence snapshot
- optional group ID
- optional parent-line reference
- optional comment reference line
- visible-column configuration at document scope
- active sort configuration at document scope

### Line-Item Principles

- line identity should be stable inside the document revision it belongs to
- sequence should remain explicit rather than inferred from display order alone
- products remain vendor-neutral Atlas objects
- vendor-specific product details remain in Vendor Offerings rather than mutating the shared product identity
- project code may be present even when there is no linked Project object
- source references should preserve source-document and source-line traceability where the document derives from another document
- related transaction line references should support deterministic line-to-line traceability between predecessor and successor documents

## Standard Commercial Document Lifecycle

The standard architecture lifecycle for commercial documents is:

Draft
→ In Review
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

In Review:
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
- Estimate → Sales Order
- Return Order → Credit Memo
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
- one Estimate may generate one or more Sales Orders
- one Sales Order may generate multiple invoices over time
- one Purchase Order may map to multiple receiving events and one or more vendor bills
- source-document and source-line traceability must be preserved when a successor document is created from a predecessor document

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

## Estimate Presentation Views (T-05)

Estimate presentation supports two views over the same estimate revision:
- Internal Estimate
- Customer Estimate

Rules:
- both views reference the same estimate identity and revision identity
- no duplicate estimate data model is introduced for view rendering
- view differences are presentation/output controls only

## Terms and Conditions Snapshot Model (T-05 Amendment)

Commercial documents can carry a Terms and Conditions reference and immutable content snapshot.

Snapshot rules:
- draft/review documents may capture or refresh snapshots only through explicit user actions
- issued documents preserve captured Terms and Conditions content and version immutably
- changing tenant defaults does not retroactively mutate issued document snapshots
- override resolution is explicit and scope-aware (`transaction > project > customer > tenant default`)

Document numbering is operational, human-facing, and tenant-aware.

Numbering principles:
- document numbering should be configurable by tenant and document family
- numbering format should remain separate from the immutable Document ID
- numbering should support revisions without changing the base document identity
- numbering should support non-consuming preview and consuming allocation behavior
- document numbers must never be reused once allocated
- external accounting numbers should be preserved as external references rather than replacing Atlas numbering
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
- explicit reapproval after material revision

Sprint A-08 does not define a production approval engine.

It defines the required approval envelope for future implementation.

## Sync Metadata Architecture

Commercial documents that synchronize to QuickBooks should carry explicit sync metadata.

Expected sync metadata concepts:
- sync readiness
- sync status
- sync direction
- external object type
- last sync attempt timestamp
- last sync success timestamp
- failure code
- failure message
- retry count
- source hash
- reconciliation state
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

## T-05 Amendment: Estimate and Sales Order Versioning, Duplication, and Export

Implemented scope for `estimate` and `sales_order` families:
- explicit duplication as a new document identity (not a revision)
- explicit revision creation with parent/superseded/current metadata
- immutable issued revisions
- archived revisions remain readable and exportable
- deterministic PDF export for internal estimate, customer estimate, and sales order presentations

Duplication guarantees:
- duplicate gets a new document ID and new document number
- duplicate keeps source-document traceability (`duplicate_of` relationship and source metadata)
- duplicate copies current line items and terms snapshot content
- duplicate starts in Draft and records duplicated-by and duplicated-at metadata

Revision guarantees:
- revision creation is explicit user intent (no automatic revision creation)
- revision chain tracks parent revision, superseded revision, revision reason, and revision date
- issued revisions are immutable and cannot be edited in place

Export guarantees:
- PDF export is deterministic for the same revision and section configuration
- export filename includes document number and revision
- issued and archived revisions remain exportable
- export activity is recorded as document activity metadata

## T-06 Implementation: Return Orders and Credit Memos

Implemented scope for customer-side return workflows:
- Return Order transaction family
- Credit Memo transaction family
- source Sales Order and source Invoice traceability
- partial-return and service-adjustment handling
- deterministic approved-credit calculations with restocking-fee and tax-adjustment support
- duplicate Credit Memo prevention from the same Return Order

Return Order notes:
- may be standalone or linked to Sales Order/Invoice/Project
- processed revisions are immutable
- product-return inspection and inventory-disposition hooks are metadata only in this sprint

Credit Memo notes:
- generated from processed Return Orders
- references Return Order and original customer-side source document where available
- uses tenant numbering settings and QuickBooks-oriented sync metadata only
- remains immutable once issued

## T-07 Implementation: Line Layout and Presentation

Commercial value fields remain separate from presentation metadata.

Implemented T-07 scope:
- named groups
- group subtotals as presentation-only derived values
- blank spacer and comment rows without separate financial-record models
- explicit display-sequence persistence
- manual reorder and sortable preview/apply behavior
- duplicate/revision preservation of presentation metadata

Guardrails:
- only item and service lines contribute to authoritative totals
- presentation changes do not alter quantity, price, tax, surcharge, traceability, or grand totals

Still intentionally unresolved:
- final canonical status taxonomies by document family
- whether all document families share one revision model or allow family-specific overlays
- final tenant-configurable numbering policy surface
- final approval-policy configuration model by tenant and document type
- final QuickBooks sync granularity for line-level versus document-level linkage
- final representation of partially fulfilled states across customer-side and vendor-side documents

## PX-03 Presentation Contract

Commercial documents may be presented in the Transactions workspace as an
operational workbench. The workbench is a presentation and deterministic
decision-support layer over the existing document model.

Workbench presentation may derive:
- family label and document status from document type and lifecycle state
- commercial health from missing required document context, line presence,
  document diagnostics, and known downstream relationships
- readiness from existing document fields, line items, totals, taxes, dates,
  and diagnostics
- line grouping from line metadata, catalog metadata, and presentation line
  type
- totals and margin from authoritative document totals and line cost fields
- relationship summary from source, downstream, change-order, project, customer,
  and explicit commercial-document relationships

Workbench presentation must not mutate authoritative commercial-document data
or introduce new lifecycle, accounting, sync, procurement, inventory, tax, or
approval rules.

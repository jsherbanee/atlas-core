# Object Workspace

## Purpose
This document defines the future Universal Object Workspace for Atlas and the contract assumptions that make it possible.

W-02 does not implement the workspace UI itself.

It establishes the shared object contract, registry, and adapter layer that future object surfaces will consume.

## Universal Object Principle
Atlas should eventually open every supported object inside one stable object experience.

The object type changes.
The object workspace does not.

Examples include:
- Project
- Customer
- Vendor
- Manufacturer
- Product
- Service
- Contact
- Location
- Transaction
- Drawing
- Specification
- Equipment
- System
- Room
- Evidence
- RFI

## W-02 Scope
Implemented in W-02:
- universal object identity contract
- universal metadata contract
- universal relationship contract
- universal activity contract
- universal action contract
- universal lifecycle envelope
- universal presentation hints
- registry-backed adapter lookup for representative existing object families
- compatibility integration with search references, Working Set records, and W-01 context persistence

Explicitly not implemented in W-02:
- Universal Object Workspace UI
- page rendering migration
- AI or semantic retrieval
- new business workflows
- new domain entities

## W-03 Scope
Implemented in W-03:
- reusable Universal Object Workspace page inside existing Atlas shell
- shared workspace layout with identity header, actions, tertiary object navigation, content, relationships, activity, and provenance
- context banner using existing W-01 return context model
- registry-driven rendering for migrated object families
- controlled migration for Customer, Vendor, Manufacturer, Product, Service, Contact, Location, and Project object routes
- read-only validation support for Drawing, Specification, and Equipment through the shared object workspace with direct open to authoritative engineering views
- search and Working Set handoff into Universal Object Workspace for supported object types

Explicitly not implemented in W-03:
- migration of all object types
- replacement of existing authoritative domain workflows
- new business workflows, AI, or semantic retrieval

## Shared Workspace Ownership
The shared Universal Object Workspace owns only reusable presentation composition:
- identity framing and provenance presentation
- object-level action rendering and disabled-action reason presentation
- supported tertiary view navigation (Summary, Details, Relationships, Activity, Documents, History)
- context banner and deterministic return behavior
- compatibility routing into authoritative domain pages where required

The shared workspace does not own domain workflow truth:
- domain services remain authoritative for create/edit/archive/import/export behavior
- object adapters and registries expose interoperable shape, not replacement persistence
- object-specific engineering workflows remain on existing specialized pages

## Migrated Object Types
Primary migrated object families:
- Customer
- Vendor
- Manufacturer
- Product
- Service
- Contact
- Location
- Project

Read-only object-workspace compatibility families:
- Drawing
- Specification
- Equipment

## Compatibility Boundaries
- unsupported object types must continue to open through legacy authoritative routes
- read-only object families must expose direct open actions back to authoritative engineering pages
- search and Working Set compatibility must preserve W-01 return context and existing route safety checks
- object adapters must remain deterministic and backward compatible with older search and Working Set records

## T-03 Transactions Compatibility Note

Sprint T-03 extends Object Workspace continuity for transaction estimates by preserving estimate-record selection identity and route handoff from Transactions browse/actions into the shared Object Workspace shell.

## T-09 Transactions Compatibility Note

Sprint T-09 extends transaction-object continuity for project change-order tracking by indexing shared change-order metadata on Sales Orders and Return Orders (for example `CO #n`, direction, and base-bid reference) without introducing a standalone Change Order object route.

Projected metadata includes change-order number/sequence/type, owner change reference, internal notes, and related-source traceability through the existing Sales Order and Return Order object projections.

## T-08 Transactions Compatibility Note

Sprint T-08 extends transaction-object continuity for Customer Invoices by preserving customer-invoice kind routing through Transactions and Object Workspace handoff while maintaining customer-invoice-specific sync and payment-status metadata visibility.

## Universal Object Workspace Shape
Future workspace surfaces should be able to render a stable object shell using shared contract data for:
- breadcrumb
- context banner
- identity block
- status
- object actions
- object navigation
- working content
- relationship panel
- recent activity

W-02 delivers the contract that makes those sections consistent before the UI migration starts.

## Shared Rendering Targets
Future shared rendering should consume the universal object contract for:
- primary label and secondary label
- stable object identity fields
- status and lifecycle labels
- supported views
- supported actions
- grouped relationships
- activity availability
- document availability

The future UI should remain declarative and should not duplicate object-specific layouts for each domain type.

## Relationship Presentation
Relationships should be rendered through shared grouped sections such as:
- Related Projects
- Related Customers
- Related Vendors
- Related Manufacturers
- Related Products
- Related Services
- Related Contacts
- Related Locations

W-02 keeps relationship discovery deterministic and source-backed.

## Context Banner
When an object is opened from another workspace or object, the future object shell should present a compact origin banner using W-01 return context.

Examples:
- Opened from Project MAW Music Education Center
- Return to BOM Review

- Opened from Knowledge > Manufacturers
- Return to Manufacturer List

## Activity Presentation
Activity should be displayed through a shared event envelope rather than per-object custom history layouts.

Initial event classes include:
- created
- updated
- imported
- linked
- unlinked
- archived
- restored
- reviewed
- exported
- opened
- status changed

## Remaining Non-Blocking Debt
- representative adapters and workspace rendering are in place for migrated object families, but broader lifecycle object migration remains future work
- some object-detail surfaces still use legacy page-specific layouts outside the W-03 migration scope
- future permission-aware action gating should reuse the action contract without moving business logic into the registry layer
- activity/history depth remains source-dependent and should continue expanding through existing deterministic audit/history repositories
- full migration of additional lifecycle object families (for example systems, rooms, risks, RFIs, and evidence) remains deferred to future W-series hardening

## Future Transactions Object Scope

Transaction families are expected to become future first-class Atlas objects and eventual Universal Object Workspace candidates.

Representative future transaction object families include:
- Estimate
- Proposal
- Sales Order
- Return Order
- Purchase Order
- RFQ
- Vendor Quote
- Change Order
- Receiving Record
- Vendor Bill
- Customer Invoice
- Credit Memo
- Subcontract

These future transaction object families should share the common contract defined in [COMMERCIAL_DOCUMENT_FRAMEWORK.md](COMMERCIAL_DOCUMENT_FRAMEWORK.md).

Sprint A-07 does not implement these object routes or views.

It only defines the architecture direction.

## T-02 Transactions Object Workspace Handoff

Sprint T-02 adds first production handoff for commercial-document families through search and transactions selection context.

Implemented in T-02:
- transaction-family kinds are now supported Object Workspace selection kinds
- global search open routes transaction objects into Object Workspace
- authoritative open for transaction object kinds routes back to Transactions workspace

Implemented in T-06:
- Return Order and Credit Memo kinds are now included in the commercial-document object-workspace compatibility set

Scope boundaries remain:
- no replacement of authoritative transaction workflows
- no financial-system behavior introduced in Object Workspace

## P-04 Documents View Integration

Sprint P-04 extends Object Workspace `Documents` behavior with unified attachment integration.

Implemented in P-04:
- document listing can resolve unified object attachments through the shared attachment service
- Object Workspace exposes permission-aware attachment actions: open/download, archive/restore, and unlink
- legacy source-reference rendering remains as compatibility fallback for existing object adapters

Out of scope in this sprint:
- inline document preview rendering
- cloud-backed object storage
- AI/semantic extraction over attachment contents

## L-01 Project Lifecycle Context

Sprint L-01 extends Project Object Workspace compatibility by projecting lifecycle-engine context through the shared object shell.

Implemented in L-01:
- project object identity now preserves canonical lifecycle stage via shared lifecycle-state fields
- project activity/history can render lifecycle transition payloads with reason and before/after stage context
- project object routing continues using the shared object workspace without replacing authoritative project settings/actions

Deferred in L-01:
- generalized lifecycle-engine rendering for all object families
- object-specific lifecycle workflow controls outside Project

## L-02 Lifecycle Dashboard View

Sprint L-02 makes lifecycle a first-class Project Object Workspace tertiary view.

Implemented in L-02:
- `Lifecycle` is now a supported tertiary project view alongside Summary, Details, Relationships, Activity, Documents, and History
- Project lifecycle dashboard renders a horizontal timeline with distinct complete, active, available, blocked, skipped, and archived states
- stage selection reveals stage description, readiness diagnostics, transition requirements, stage history, and deterministic related objects where present

Boundary rules:
- lifecycle dashboard remains read-oriented visualization and inspection
- lifecycle automation and downstream workflow execution remain out of scope

## P-01 Permission Gating Note

Sprint P-01 wires Universal Object actions into centralized permission evaluation through action permission hooks.

Action rendering now resolves deterministically as:

- visible and enabled
- visible but disabled with explicit denial reason
- hidden

Authorization checks remain centralized in shared action evaluation and are not scattered across page-specific object UI code.
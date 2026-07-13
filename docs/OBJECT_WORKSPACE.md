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
- representative adapters exist for current project, knowledge, and engineering object families, but broader future lifecycle objects still need adapter definitions as those domains are implemented
- current UI surfaces still render object detail in page-specific layouts; W-02 does not migrate them yet
- future permission-aware action gating should reuse the action contract without moving business logic into the registry layer
# APP-01 Commercial MVP Application Facade

## Purpose

APP-01 defines the tenant-scoped application facade that presents the Commercial MVP as a coherent product surface.

The facade does not add UI routes, REST handlers, auth, billing, AWS adapters, or live QuickBooks calls. It composes the existing commercial services so future UI and API layers can call a single orchestration boundary instead of wiring every service directly.

## Responsibilities

The facade coordinates these tenant-scoped services:

- Commercial customer, opportunity, and estimate service
- Commercial proposal and sales-order workflow service
- Inventory service
- Customer invoice and vendor bill service
- Commercial reporting service
- QuickBooks sync service

It exposes product-level use cases such as:

- create customer/account
- create opportunity
- create estimate and manage estimate line items
- create, send, accept, and convert proposals into sales orders
- check inventory availability and reserve stock where possible
- generate customer invoices from sales orders
- create vendor bills manually
- mark invoice and vendor bill sync state as pending
- retrieve a commercial reporting snapshot

## Relationship To Lower-Level Services

APP-01 is intentionally thin.

It delegates record validation and business rules to the underlying services wherever possible. It only adds orchestration where more than one service must participate in the same use case, such as inventory reservation against an accepted sales order.

The lower-level services remain independently usable and testable. APP-01 is a product-facing convenience layer, not a replacement for the commercial service stack.

## Tenant Isolation

All facade operations use the tenant-scoped repository bundle passed into construction.

That means tenant A and tenant B can run the same workflow shape with the same record IDs without reading or mutating each other’s data.

## Out Of Scope

- UI implementation
- REST/FastAPI routing
- Streamlit screens
- live QuickBooks API transport
- OAuth and credential storage
- AWS adapter work
- auth and billing
- Epic E

## How This Prepares The First Product Surface

APP-01 gives future UI and API layers one place to call for the Commercial MVP workflow.

That makes the next surface easier to build because the view layer can stay focused on presentation and request mapping while the facade handles tenant-scoped orchestration of the existing commercial model.
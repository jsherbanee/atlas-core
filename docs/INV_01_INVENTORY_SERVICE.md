# INV-01 Catalog, Inventory Availability, Reservation, and Allocation

INV-01 adds the first inventory operating layer for the commercial MVP.

## Responsibilities

- Manage catalog items with tenant-scoped create, load, list, and update behavior.
- Manage inventory locations with tenant-scoped create, load, list, and update behavior.
- Manage inventory positions with on-hand, reserved, and available quantities.
- Create, update, cancel, and allocate inventory reservations.
- Validate practical demand references such as sales-order line items and change orders.
- Keep inventory availability deterministic within the active tenant repository boundary.

## Inventory Concepts

- Catalog items define the sellable or stockable item identity, pricing, and vendor/manufacturer metadata.
- Inventory locations define where stock is held.
- Inventory positions represent the stock state for a catalog item at a location.
- Inventory reservations hold quantity against a demand reference.
- Allocation and fulfillment are modeled as reservation state transitions.

## Availability Rules

- Available quantity is calculated as on-hand minus active reserved quantity.
- Cancelled, released, or fulfilled reservations do not count toward active reserved quantity.
- Reservation requests that exceed available quantity are rejected.
- Inventory position totals cannot go negative.

## Tenant Scope

All reads and writes flow through the tenant-scoped commercial repository boundary. Cross-tenant records should be invisible to a service instance for another tenant.

## Out of Scope

- Warehouse task execution.
- Receiving workflows beyond quantity updates.
- Procurement execution or RFQ handling.
- Purchase orders.
- Customer invoices.
- Vendor bills.
- QuickBooks API integration.
- UI and dashboards.
- Epic E.

## Relationship to Commercial Workflow

INV-01 consumes sales-order line items produced by CM-04 and can also attach to change orders or project/job links already modeled in the commercial spine.

## Related Docs

- [Commercial MVP operating spine](COMMERCIAL_MVP_OPERATING_SPINE.md)
- [Commercial repository](COMMERCIAL_REPOSITORY.md)
- [Commercial proposal and sales order workflow](COMMERCIAL_PROPOSAL_SALES_ORDER_WORKFLOW_SERVICE.md)
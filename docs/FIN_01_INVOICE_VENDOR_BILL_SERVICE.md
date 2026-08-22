# FIN-01 Customer Invoice and Vendor Bill Service

FIN-01 adds the first operational accounting layer owned by Atlas for customer invoices and vendor bills.

## Responsibilities

- Create, load, list, and update customer invoices.
- Generate customer invoices from sales orders when the commercial workflow provides a source order.
- Preserve invoice line-item identity when copying from sales orders.
- Create, load, list, and update vendor bills.
- Support manual vendor bill entry with procurement and project linkage where the model supports it.
- Track QuickBooks sync reference state on invoices and vendor bills.

QB-01 adds the internal QuickBooks sync coordinator and lifecycle management that operate on top of these invoice and vendor-bill records. See [QB_01_QUICKBOOKS_SYNC_ARCHITECTURE.md](QB_01_QUICKBOOKS_SYNC_ARCHITECTURE.md).

## Accounting Boundary

Atlas owns operational invoice and vendor bill workflow state. QuickBooks remains the accounting execution system for:

- payments and receipts
- tax accounting
- reconciliation
- ledger posting
- financial statements

FIN-01 does not call QuickBooks APIs.

## Lifecycle Rules

- Customer invoices support draft, ready, issued, and voided statuses.
- Vendor bills support draft, ready, entered, and voided statuses.
- Sync state is modeled only through the existing QuickBooks sync reference.
- Sync status changes are deterministic and persisted on the invoice or bill record.

## Totals

- Invoice and vendor-bill totals are computed deterministically from line items.
- No tax engine or discount engine is applied in this layer.

## Tenant Scope

All reads and writes are tenant scoped through the commercial repository bundle. Cross-tenant invoice, vendor-bill, customer, sales-order, procurement, or project references should be rejected or remain invisible.

## Out of Scope

- QuickBooks API calls.
- Payment receipt tracking.
- Vendor bill payment tracking.
- Tax calculation.
- Ledger accounting.
- Financial statements.
- UI.
- PDF generation.
- Procurement/RFQ execution.
- AWS adapters.
- Epic E.

## Related Docs

- [Commercial MVP operating spine](COMMERCIAL_MVP_OPERATING_SPINE.md)
- [Commercial proposal and sales order workflow](COMMERCIAL_PROPOSAL_SALES_ORDER_WORKFLOW_SERVICE.md)
- [INV-01 inventory service](INV_01_INVENTORY_SERVICE.md)
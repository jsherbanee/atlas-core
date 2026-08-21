# Commercial Repository

## Purpose

CM-02 adds local persistence for the CM-01 commercial operating spine without turning it into a workflow engine.

The repository layer is tenant-scoped. Each tenant uses its own local root, and the commercial repository lives underneath that tenant root so records cannot cross tenant boundaries by construction.

## Relationship To Earlier Work

- CM-01 defined the commercial domain skeleton: customers, opportunities, estimates, proposals, sales orders, change orders, inventory planning, procurement needs, Atlas-generated invoices and vendor bills, and QuickBooks sync references.
- AR-01 introduced the tenant-scoped repository bundle and composition root.
- CM-02 connects those two pieces by persisting CM-01 records inside the tenant-scoped local repository boundary.

## Local Persistence Layout

Tenant-scoped local commercial persistence is stored under the tenant root:

```text
AtlasProjects/
  tenants/
    <tenant_id>/
      commercial/
        customer_accounts.jsonl
        opportunities.jsonl
        proposals.jsonl
        estimates.jsonl
        sales_orders.jsonl
        change_orders.jsonl
        catalog_items.jsonl
        inventory_locations.jsonl
        inventory_positions.jsonl
        inventory_reservations.jsonl
        procurement_needs.jsonl
        customer_invoices.jsonl
        vendor_bills.jsonl
        quickbooks_sync_references.jsonl
```

Each file stores one JSON object per line. The local commercial repository uses simple upsert semantics keyed by the model identity field.

## System-Of-Record Boundaries

Atlas owns operational workflow state, estimating context, sales order status, project/job status, procurement planning, inventory planning/allocation, customer invoice generation, vendor bill entry, and reporting context.

REP-01 consumes that same tenant-scoped commercial repository as a read-only
aggregation layer. It does not introduce a separate reporting database or a
second source of truth.

QuickBooks owns accounting execution, customer receipts, vendor bill payments, tax accounting, reconciliation, general ledger, and financial statements.

Atlas persists QuickBooks external IDs, sync status, timestamps, and error state for customer invoices and vendor bills so later sync work can remain adapter-based.

QB-01 extends that persisted sync state with operation intent, idempotency keys, retry flags, and attempt counters. See [QB_01_QUICKBOOKS_SYNC_ARCHITECTURE.md](QB_01_QUICKBOOKS_SYNC_ARCHITECTURE.md).

## Explicitly Not Implemented Yet

- UI
- proposal generation workflows
- estimate-to-sales-order conversion workflows
- inventory allocation logic beyond persistence
- QuickBooks API calls
- AWS adapters
- auth and billing
- Epic E work
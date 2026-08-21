# Commercial MVP Operating Spine

## Purpose

This document defines the minimal commercial operating spine Atlas should own before deeper workflow implementation begins.

The focus is deliberately narrow: establish the commercial data shape, workflow boundaries, and system-of-record assumptions without implementing full estimating, inventory execution, procurement automation, invoicing, bill payment, or accounting transport.

## Intended Workflow

```mermaid
flowchart LR
    CA[Customer / Account] --> OP[Opportunity]
    OP --> EST[Estimate]
    EST --> PRO[Proposal]
    PRO --> SO[Sales Order]
    SO --> PJ[Project / Job]
    PJ --> INV[Procurement / Inventory]
    INV --> INVH[Atlas-generated Customer Invoice / Vendor Bill]
    INVH --> QB[QuickBooks Sync]
    QB --> RPT[Reporting]
```

## System-of-Record Boundaries

Atlas owns:
- operational workflow state
- estimating context
- sales order status
- project/job status
- procurement planning context
- inventory planning context
- inventory allocation context
- customer invoice generation
- vendor bill entry
- commercial reporting context

QuickBooks owns:
- ledger
- customer receipts
- vendor bill payments
- taxes
- reconciliation
- general ledger
- financial statements

Atlas stores QuickBooks external IDs, sync status, timestamps, and error states for customer invoices and vendor bills.

## Model Scope

The current skeleton is intentionally lightweight and future-proof. It includes:
- Customer / Account
- Opportunity
- Estimate and EstimateLineItem
- Proposal status
- SalesOrder and SalesOrderLineItem
- ChangeOrder
- Project / Job linkage
- CatalogItem
- InventoryLocation
- InventoryPosition
- InventoryReservation
- Vendor / Manufacturer reference
- ProcurementNeed
- CustomerInvoice and CustomerInvoiceLineItem
- VendorBill and VendorBillLineItem
- QuickBooksSyncReference

CM-02 persists these records in the tenant-scoped local repository boundary described in [COMMERCIAL_REPOSITORY.md](COMMERCIAL_REPOSITORY.md).

CM-03 layers tenant-scoped customer, opportunity, and estimate service behavior on top of that repository boundary. See [COMMERCIAL_CUSTOMER_OPPORTUNITY_ESTIMATE_SERVICE.md](COMMERCIAL_CUSTOMER_OPPORTUNITY_ESTIMATE_SERVICE.md).

CM-04 layers tenant-scoped proposal workflow and accepted-estimate-to-sales-order conversion on top of CM-03. See [COMMERCIAL_PROPOSAL_SALES_ORDER_WORKFLOW_SERVICE.md](COMMERCIAL_PROPOSAL_SALES_ORDER_WORKFLOW_SERVICE.md).

INV-01 layers tenant-scoped catalog, inventory availability, reservation, and allocation behavior on top of CM-04. See [INV_01_INVENTORY_SERVICE.md](INV_01_INVENTORY_SERVICE.md).

FIN-01 layers tenant-scoped customer invoice and vendor bill workflow on top of INV-01. See [FIN_01_INVOICE_VENDOR_BILL_SERVICE.md](FIN_01_INVOICE_VENDOR_BILL_SERVICE.md).

QB-01 layers internal QuickBooks sync architecture on top of FIN-01 without introducing live transport. See [QB_01_QUICKBOOKS_SYNC_ARCHITECTURE.md](QB_01_QUICKBOOKS_SYNC_ARCHITECTURE.md).

APP-01 layers the tenant-scoped Commercial MVP application facade on top of the service stack. See [APP_01_COMMERCIAL_MVP_APPLICATION_FACADE.md](APP_01_COMMERCIAL_MVP_APPLICATION_FACADE.md).

API-01 layers the first Commercial MVP API boundary on top of APP-01. See [API_01_COMMERCIAL_MVP_API_BOUNDARY.md](API_01_COMMERCIAL_MVP_API_BOUNDARY.md).

REP-01 layers tenant-scoped commercial reporting read models on top of FIN-01. See [COMMERCIAL_REPORTING_READ_MODELS.md](COMMERCIAL_REPORTING_READ_MODELS.md).

## Implementation Guardrails

- Keep tenant awareness in the model shape.
- Avoid workflow execution logic in the skeleton.
- Avoid QuickBooks transport calls.
- Avoid AWS adapter work.
- Use this document as the architectural reference for future commercial MVP work.
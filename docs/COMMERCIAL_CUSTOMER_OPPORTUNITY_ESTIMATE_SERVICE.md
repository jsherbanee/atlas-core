# CM-03 Customer, Opportunity, and Estimate Service

## Purpose

CM-03 adds the first commercial application service layer for the front half of the commercial workflow.

The service owns tenant-scoped CRUD and linkage behavior for:

- CustomerAccount
- Opportunity
- Estimate
- EstimateLineItem mutation
- simple estimate subtotal calculation
- basic opportunity status updates already represented in CM-01

It is intentionally narrow. It validates references, persists through the CM-02 tenant-scoped commercial repository, and keeps workflow orchestration out of the service layer.

## Responsibilities

- Create and update customer/account records.
- Create and update opportunity records.
- Create and update estimate records.
- Add, update, and remove estimate line items.
- Link estimates to customer/account and opportunity records.
- Enforce tenant-scoped persistence through the repository composition boundary.
- Reject invalid customer or opportunity references.
- Compute a simple estimate subtotal from line-item quantity and unit price.
- Support opportunity lifecycle updates when callers need them.

## Out Of Scope

- Proposal generation
- Sales order conversion
- Change order workflow
- Inventory allocation
- Procurement/RFQ workflow
- Customer invoices
- Vendor bills
- QuickBooks API calls
- AWS adapters
- auth and billing
- reporting
- UI
- Epic E

## How This Prepares Later Workflow

CM-03 makes customer, opportunity, and estimate records persistent and referentially safe before later workflow layers are added.

That gives future proposal and sales-order services stable inputs:

- Customer records already exist and can be validated before a proposal or estimate is created.
- Opportunity records can be updated and moved through their early lifecycle before downstream workflow begins.
- Estimate records already carry linked customer and opportunity identity plus line items and a deterministic subtotal.

The next workflow layers can therefore focus on proposal generation, estimate conversion, and sales-order orchestration without having to solve front-half record management first.
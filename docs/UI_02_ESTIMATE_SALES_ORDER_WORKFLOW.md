# UI-02 Estimate and Sales Order Workflow

## Purpose
UI-02 originally exercised the core revenue workflow through a standalone commercial page. UI-FIX-01 removes that page because it duplicated responsibilities now owned by existing tenant-facing areas.

Estimate, proposal, sales-order, invoice, and vendor-bill workflows belong in Transactions. Customer and catalog selection belong in Knowledge-backed controls. Reporting belongs in Reports.

## Scope
- Customer/account creation through APP-01 and API-01.
- Opportunity creation linked to an existing customer/account.
- Estimate creation linked to customer and opportunity records.
- Estimate line-item add/remove controls.
- Estimate subtotal display.
- Proposal status advancement controls.
- Accepted estimate to sales-order conversion.
- Resulting sales-order status display.

## Test Coverage
- Commercial backend, facade, API boundary, service, repository, and tenant-isolation tests remain intact.
- Transactions and related Phase 2 navigation tests cover the retained user-facing ownership boundaries.
- UI-FIX-01 tests prove the removed page cannot appear through primary navigation or shared-shell dispatch.

## Out Of Scope
- Broad visual redesign and final production polish.
- Proposal PDF generation.
- E-signature.
- Inventory allocation beyond the existing availability readout.
- Invoice workflow expansion.
- Procurement/RFQ execution.
- Live QuickBooks API calls.
- OAuth, AWS adapters, auth/billing, tenant administration, Epic E, and engineering intelligence.

## Next Slice
Address individual Transactions workflow gaps as focused slices. Do not recreate a combined commercial workspace.

## Entry Point
There is no standalone UI-02 entry point after UI-FIX-01. Retained and future user-facing commercial actions must use APP-01 and API-01 rather than repositories directly.
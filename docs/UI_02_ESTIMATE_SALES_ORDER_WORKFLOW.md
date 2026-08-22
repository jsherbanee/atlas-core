# UI-02 Estimate and Sales Order Workflow

## Purpose
UI-02 makes the Sales workspace usable for the core revenue workflow: create a customer/account, create an opportunity, create an estimate, manage estimate line items, advance proposal status, and convert the accepted revenue path into a sales order.

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
- Customer, opportunity, estimate, proposal, and sales-order controls render and call the facade/boundary seam.
- Estimate subtotal renders deterministically from the selected estimate line items.
- Proposal and sales-order workflow actions surface deterministic success and validation/error states.
- UI-01 Sales content, exclusive navigation state, and route-isolation regressions remain intact.

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
Add a minimal record drilldown for estimates and sales orders, keeping the same tenant-scoped boundary pattern.

## Entry Point
The workspace remains rendered from [apps/phase2_review_app.py](../apps/phase2_review_app.py) and uses APP-01 and API-01 as the only commercial mutation/read seams. The user-facing label is Sales; `Commercial Workspace` remains only as an internal compatibility route.
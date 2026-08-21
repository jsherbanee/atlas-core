# UI-01 Commercial Workspace MVP

## Purpose
UI-01 introduces the first user-facing Commercial Workspace surface for Atlas. It exposes a compact commercial MVP spine through the existing application facade and API boundary patterns.

## Scope
- Tenant-scoped Commercial Workspace entry point in the Streamlit shell.
- Compact commercial snapshot built from REP-01 reporting summaries.
- Minimal workflow panels for customer/account, opportunity, estimate, proposal, sales order, invoice, and vendor bill flows.
- Inventory availability and reservation panel driven through the existing commercial boundary.
- QuickBooks sync readiness/status panel for invoices and vendor bills.
- Deterministic create/mutate actions routed through APP-01 and API-01.

## Test Coverage
- The Commercial Workspace page title and header render deterministically.
- The snapshot, customer/account, opportunity, estimate, inventory, workflow, and sync panels render through the facade and boundary seams.
- Inventory availability is resolved from the tenant-scoped facade and boundary pair rather than repository internals.

## Out Of Scope
- Live QuickBooks connectivity.
- Authentication and authorization redesign.
- Broad dashboard redesign or multi-page commercial analytics.
- AWS deployment changes.

## Next Slice
Add a minimal record-detail drilldown for estimate and sales-order rows, keeping the same tenant-scoped boundary pattern.

## Entry Point
The workspace is rendered from [apps/phase2_review_app.py](../apps/phase2_review_app.py) and delegates commercial reads and writes through APP-01 and API-01.
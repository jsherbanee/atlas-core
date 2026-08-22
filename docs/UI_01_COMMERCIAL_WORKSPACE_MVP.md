# UI-01 Sales Workspace MVP

## Purpose
UI-01 introduces the first user-facing Sales surface for Atlas. It exposes a compact revenue workflow through the existing application facade and API boundary patterns.

## Navigation Decision
The workspace remains top-level but is labeled **Sales**, not **Commercial**. Sales maps directly to the opportunity-to-order intent of an AV/lighting integrator, while Transactions continues to own document-centric operational work. The internal `Commercial Workspace` route is retained for compatibility; it is not visible product copy.

## Scope
- Tenant-isolated Sales entry point in the Streamlit shell.
- Compact attention summary built from REP-01 reporting summaries.
- Minimal workflow panels for customer/account, opportunity, estimate, proposal, sales order, invoice, and vendor bill flows.
- Inventory availability and reservation panel driven through the existing commercial boundary.
- QuickBooks sync readiness/status panel for invoices and vendor bills.
- Deterministic create/mutate actions routed through APP-01 and API-01.

## Test Coverage
- Exactly one primary navigation item is active for every primary route, including when a project is open.
- Sales content is dispatched only from the Sales route and does not render on Home, Projects, Knowledge, Reports, Settings, or Transactions.
- The Sales page title, workflow labels, and plain-language copy render deterministically.
- The snapshot, customer/account, opportunity, estimate, inventory, workflow, and sync panels render through the facade and boundary seams.
- Inventory availability is resolved from the tenant-scoped facade and boundary pair rather than repository internals.
- Each commercial record family is loaded through the facade once per render.

## UI-FIX-01 Performance Notes
- A local one-shot import measured about `0.316s` before remediation and `0.308s` after remediation. These single-run values are directional, not a benchmark.
- Commercial UI contracts and services are now imported only when the Sales route renders; the module is not loaded during non-Sales app startup.
- Commercial service construction measured about `0.0002s`, so persistent service caching was not warranted.
- Repeated customer, opportunity, estimate, and sales-order facade reads were consolidated into one render-scoped data load per record family. Mutations still rerun the page and refresh the data.
- Interactive first-paint timing remains dependent on Streamlit and local data volume and was not treated as a production performance benchmark.

## Out Of Scope
- Live QuickBooks connectivity.
- Authentication and authorization redesign.
- Broad dashboard redesign or multi-page commercial analytics.
- AWS deployment changes.

## Next Slice
Add a minimal record-detail drilldown for estimate and sales-order rows, keeping the same tenant-scoped boundary pattern.

## Entry Point
The workspace is rendered from [apps/phase2_review_app.py](../apps/phase2_review_app.py) and delegates commercial reads and writes through APP-01 and API-01. UI-FIX-01 improves reviewability but does not establish broad visual or production readiness.
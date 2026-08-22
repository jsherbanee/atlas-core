# UI-01 Commercial Workspace Disposition

## Purpose
UI-FIX-01 removes the standalone Commercial Workspace from the tenant-facing application. The backend commercial spine remains available through its application facade and API boundary; this document records where user-facing commercial functions belong.

## Navigation Decision
Commercial and Sales are not primary navigation items, and `Commercial Workspace` is no longer an active route. No replacement primary item was added.

Commercial functions belong in existing product areas:
- Transactions: estimates, proposals, sales orders, invoices, and vendor bills
- Knowledge: customers, vendors, manufacturers, and catalog
- Reports: commercial reporting and read models
- Settings: tenant-facing commercial configuration where appropriate

Relocating the removed page's combined workflow would be too broad for a remediation pass. Existing safe capabilities in those product areas remain; additional relocation must be delivered as focused follow-up slices.

## Project Context Boundary
The global project selector, project header, project actions, project breadcrumbs, and project status context render only on Projects-owned routes. A selected project may remain in session for return navigation, but Transactions, Knowledge, Reports, Settings, and Home receive no project shell context. Future project filtering in those areas must be local to the page.

## Test Coverage
- No Commercial or Sales primary navigation item or active route exists.
- Exactly one remaining primary navigation item is active, including when a stale project selection exists.
- Non-Projects primary pages receive no project record or project context from the shared shell.
- Existing Transactions, Knowledge, Reports, Settings, Phase 2 navigation, and commercial backend tests remain authoritative.

## UI-FIX-01 Performance Notes
- Earlier local measurement placed a one-shot app import near `0.31s`; commercial service construction itself was about `0.0002s`. These values are directional, not production benchmarks.
- The removed page module, facade reads, reporting snapshot, and commercial service construction are no longer imported or executed by the tenant-facing shell.
- Non-Projects pages also avoid project analysis/header construction and workspace listing for the global project selector.
- Interactive first-paint timing remains dependent on Streamlit and local data volume and was not treated as a production performance benchmark.

## Out Of Scope
- Relocating the removed combined workflow into existing pages.
- Live QuickBooks connectivity.
- Authentication and authorization redesign.
- Broad dashboard redesign or multi-page commercial analytics.
- AWS deployment changes.

## Next Slice
Improve commercial workflows within their owning Transactions, Knowledge, Reports, or Settings area without introducing another primary workspace.

## Entry Point
There is no standalone Commercial Workspace entry point. User-facing commercial work must continue to use APP-01 and API-01 seams and preserve tenant isolation. UI-FIX-01 improves shell clarity but does not establish broad visual or production readiness.
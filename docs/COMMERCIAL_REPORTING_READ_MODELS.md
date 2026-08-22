# Commercial Reporting Read Models

## Purpose

REP-01 defines tenant-scoped commercial reporting read models for Atlas Core.
The service layer reads existing commercial records and produces deterministic
summaries for operational use cases without creating a separate reporting
database, dashboard layer, or export pipeline.

## Supported Summaries

The reporting read models currently cover:

- estimate pipeline summary
- proposal status summary
- sales order backlog summary
- invoice status summary
- vendor bill status summary
- inventory availability summary
- procurement need summary
- QuickBooks sync status summary for invoices and vendor bills

The summaries are intentionally simple:

- counts by status or stage
- totals where the underlying record already carries numeric values
- deterministic row ordering for availability and sync outputs
- no charts, forecasting, or business-intelligence aggregation

## Tenant Isolation

Reporting remains tenant-scoped by construction.

- each reporting service instance is created from a tenant-specific repository
  bundle
- read models only consume that tenant's commercial repository records
- organization filters are optional, but when provided they must match the
  tenant's stored organization-scoped records
- cross-tenant reporting should be impossible through normal service usage

## Out Of Scope

REP-01 does not introduce:

- UI dashboards
- chart rendering
- exports
- advanced forecasting
- gross-margin analytics beyond directly modeled totals
- QuickBooks API calls
- AWS adapters
- auth or billing changes
- Epic E work

## Relationship To Future Dashboards

These read models provide the deterministic commercial summaries that future UI
dashboards can consume. They make the operational state visible without baking
presentation concerns into the commercial workflow services themselves.

QuickBooks remains the accounting execution system. Atlas reporting surfaces the
sync state and the operational invoice/vendor-bill records needed for later
adapter-based accounting work.

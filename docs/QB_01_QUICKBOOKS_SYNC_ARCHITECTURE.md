# QB-01 QuickBooks Sync Architecture

## Purpose

QB-01 defines Atlas's internal QuickBooks sync architecture for customer invoices and vendor bills.

The goal is not live QuickBooks transport. The goal is to keep Atlas-owned invoice and bill records in a deterministic sync-ready state so transport adapters can be added later without changing the commercial domain model.

## Architecture

Atlas owns the operational record and its sync metadata:

- QuickBooks sync status
- sync operation intent
- idempotency key
- retry eligibility
- attempt count
- last attempt, sync, and error timestamps/messages

QuickBooks remains the financial system of record.

## Sync Lifecycle

Supported internal states:

- not_ready
- not_synced
- pending
- in_progress
- synced
- failed
- skipped

The lifecycle is deterministic and tenant-scoped. A sync task is derived from the operational record, not from a separate sync database.

## Idempotency And Retry

Atlas computes a stable idempotency key from the tenant-scoped operational record snapshot plus the intended QuickBooks operation.

Retryability is stored on the record so the system can distinguish:

- first-time sync candidates
- retryable failures or skips
- terminal synced states
- records that are explicitly blocked from sync

## Tenant Isolation

Sync state is persisted under the same tenant-scoped commercial repository boundary as invoices and vendor bills.

That keeps cross-tenant contamination out of the sync coordinator and allows reporting to summarize sync readiness directly from the operational store.

## Out Of Scope

- live QuickBooks API calls
- webhook handling
- polling adapters
- general ledger reconciliation
- payment processing
- tax accounting
- bank feeds
- accounting document ownership changes

## Related Documents

- [COMMERCIAL_MVP_OPERATING_SPINE.md](COMMERCIAL_MVP_OPERATING_SPINE.md)
- [COMMERCIAL_REPOSITORY.md](COMMERCIAL_REPOSITORY.md)
- [FIN_01_INVOICE_VENDOR_BILL_SERVICE.md](FIN_01_INVOICE_VENDOR_BILL_SERVICE.md)
- [COMMERCIAL_REPORTING_READ_MODELS.md](COMMERCIAL_REPORTING_READ_MODELS.md)
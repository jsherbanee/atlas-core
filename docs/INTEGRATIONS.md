# Integrations

## Purpose
This document defines the integration architecture for Atlas.

It covers principles for synchronizing Atlas with financial, operational, productivity, manufacturer, and external platform ecosystems.

## Related Documents
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [SECURITY.md](SECURITY.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)

## Scope
Atlas should support integrations as first-class architectural concerns, but the platform does not implement every listed integration today.

This document defines durable integration boundaries and synchronization principles.

## Principles
- Each integration should have a clear system of record.
- Atlas should synchronize operational data rather than duplicate external platform behavior.
- Identifiers should have a defined owner and mapping strategy.
- Integration writes should be explicit, auditable, and idempotent.
- Retry handling should be deterministic and safe.
- Conflicts should be surfaced, not hidden.
- Tenant scoping must apply to all credentials, events, and synced records.
- Rate limits and webhook failures should be handled intentionally.

## General Integration Requirements
Every integration should define:

- system of record
- direction of synchronization
- ownership of identifiers
- read/write boundaries
- conflict handling
- retry behavior
- idempotency
- webhook handling
- credential management
- tenant scoping
- audit logging
- failure recovery
- manual reconciliation
- versioning
- rate-limit considerations

## Integration Profiles

| Integration | System of Record | Sync Direction | Identifier Ownership | Read/Write Boundary | Conflict and Recovery |
| --- | --- | --- | --- | --- | --- |
| QuickBooks Online | QuickBooks Online is the Financial System of Record. | Atlas should sync operationally relevant records to and from QuickBooks as configured. | Atlas should own operational identifiers; QuickBooks owns financial identifiers where applicable. | Atlas must not duplicate general ledger, payroll, tax, banking, or statutory reporting behavior. Shared entities may include customers, vendors, purchase orders, bills, invoices, payment status, cost codes, and financial summaries. | Webhooks or polling should be idempotent, auditable, and configurable for manual reconciliation. |
| Stripe | Stripe is the payment and subscription billing system of record. | Stripe should send billing, payment, and subscription state to Atlas; Atlas should send organization entitlement changes where appropriate. | Stripe owns payment-method and billing identifiers; Atlas owns organization, seat, and entitlement identifiers. | Stripe manages payment methods, subscription billing, invoices, and payment status. Atlas manages access, seats, entitlements, and operational account state. | Webhooks must be idempotent, auditable, and recoverable. |
| Future CRM systems | External CRM or Atlas depending on customer strategy. | Usually bi-directional or externally sourced into Atlas. | CRM contact/opportunity IDs and Atlas org/project IDs must be mapped explicitly. | Atlas should not silently overwrite external CRM records without a configured policy. | Conflicts should surface for review; retries must preserve idempotency. |
| Email platforms | Usually external system of record for transport. | Primarily inbound capture plus selected outbound notifications. | Message IDs remain with the email platform; Atlas stores cross-reference metadata. | Atlas may read authorized mailboxes or send notifications, but should not duplicate mail hosting behavior. | Webhook and polling handlers must be idempotent and respect tenant-scoped credentials. |
| Calendar platforms | Calendar platform for event transport; Atlas for operational context. | Primarily bi-directional scheduling sync where enabled. | Calendar event IDs remain external; Atlas stores event references. | Atlas should not replace calendar scheduling. | Conflicts should preserve the user-visible schedule source of truth. |
| Google Workspace | Google services own docs, mail, and calendaring if used. | Typically selective sync of files, events, and notifications. | Google object IDs remain external. | Atlas may reference and index authorized content without duplicating the platform. | OAuth credentials, token refresh, and webhook handling must be tenant-scoped. |
| Microsoft 365 | Microsoft services own docs, mail, and calendaring if used. | Typically selective sync of files, events, and notifications. | Microsoft object IDs remain external. | Atlas may reference and index authorized content without duplicating the platform. | OAuth credentials, token refresh, and webhook handling must be tenant-scoped. |
| Cloud file storage | External file platform or Atlas depending on the deployment pattern. | Selective document synchronization and indexed references. | File and folder identifiers should be mapped explicitly. | Atlas should not assume ownership of externally hosted files beyond authorization and metadata. | Failures should preserve pointers, provenance, and re-sync ability. |
| Manufacturer and distributor data sources | Manufacturer or distributor source systems / documentation libraries. | Usually inbound reference sync into Atlas knowledge layers. | External product, model, and document identifiers should be preserved. | Atlas should ingest only licensed or authorized material. | Versioning, licensing, and source attribution are required. |
| External estimating or proposal platforms | Usually Atlas or external estimating platform depending on deployment pattern. | Selective export/import by customer policy. | Estimate and proposal identifiers should be mapped explicitly. | Atlas should not silently overwrite external commercial artifacts. | Conflict handling should favor explicit user review. |
| Field-service platforms | Usually external field system or Atlas depending on customer operating model. | Selective operational status and service-record sync. | Work-order and asset identifiers require explicit mapping. | Atlas should not duplicate dispatch, routing, or mobile field app behavior unless intentionally adopted. | Recovery must preserve service history and auditability. |
| Future public API consumers | Atlas when published. | Inbound and outbound according to the exposed API contract. | Atlas should define stable public IDs and external reference IDs. | Public API boundaries must enforce tenant-scoped access and permission checks. | Webhook/event and API operations must be idempotent and rate-limited. |

## QuickBooks Principles
QuickBooks Online is the Financial System of Record.

Atlas is the Operational System of Record.

Atlas must not duplicate general ledger, payroll, banking, tax, or statutory accounting functions.

Shared entities may include customers, vendors, purchase orders, bills, invoices, payment status, cost codes, and financial summaries.

Transactions architecture note:
- Atlas should eventually originate and manage operational commercial documents such as estimates, proposals, sales orders, purchase orders, receiving records, vendor bills, and customer invoices before sync.
- Atlas now also manages Return Order workflow and Credit Memo generation before sync.
- Atlas now tracks customer-invoice sync readiness/status and returned QuickBooks payment-state metadata as synchronized reference data without changing QuickBooks financial ownership.
- QuickBooks should own the post-sync financial state for payables, receivables, payments, ledger, and statutory reporting.
- payment status may return from QuickBooks into Atlas as synchronized financial reference state.

Return/credit boundary note:
- Atlas owns return approval, inspection, credit calculation, and Credit Memo creation.
- QuickBooks remains the system of record for receivable posting, customer balance, payment application, and reconciliation.

Commercial document framework note:
- future commercial documents should share one common sync-metadata architecture rather than family-specific ad hoc sync fields.
- shared sync metadata should cover readiness, status, direction, external object type, external object ID, attempt/success timestamps, failure code/message, retry count, source hash, reconciliation state, and external accounting references where applicable.

Exact future synchronization ownership should remain explicitly documented and configurable.

## Stripe Principles
Stripe manages payment methods, subscription billing, invoices, and payment status.

Atlas manages organization access, seats, entitlements, and operational account state.

Webhook processing must be idempotent and auditable.

## Credential and Security Expectations
- Credentials must be tenant-scoped.
- Secrets must not be stored in source control.
- Credential rotation should be supported where practical.
- Integration activity should be logged for audit and troubleshooting.

## Versioning and Rate Limits
- Integration payloads and mappings should be versioned where the external system supports it.
- Rate limits should be respected and surfaced.
- Backoff and retry policy should be explicit.
- Manual reconciliation should remain available when automation cannot resolve a conflict safely.

## Current Status
Most integrations described here are architectural direction rather than current implementation.

Current functionality should not be overstated.

S-01 implementation update (metadata hooks only):
- Settings now supports tenant-scoped integration connection metadata records for `quickbooks_online`, `xero`, `microsoft_365`, `google_workspace`, `generic_api`, and `generic_webhook`.
- Secret material is not stored directly in settings state; secret fields must be provided as secret references using `secret://` URIs.
- Integration audit events record provider/status and metadata/secret key names only; secret-reference values are not emitted into audit detail payloads.

Current boundary remains:
- no live provider authentication handshake
- no token exchange/refresh implementation
- no webhook registration or transport execution

## Future Direction
Atlas should eventually act as an operational hub that synchronizes with accounting, billing, productivity, storage, manufacturer, and field systems without becoming a duplicate of those systems.

## T-05 Amendment: Future Email Delivery Metadata Hooks

Commercial document export workflows now capture non-executing future email-delivery metadata for:
- Microsoft 365
- Google Workspace
- SMTP
- approved future providers

Captured metadata may include recipient, CC/BCC, subject, message template, attached revision, sent timestamp, delivery status, and provider message ID.

Current boundary:
- metadata capture only
- no live mail send
- no provider integration implementation in this sprint

## Unresolved Decisions
- The final sync direction for each shared entity remains configurable.
- The balance between polling and webhooks may vary by integration.
- The final public API surface remains a future design decision.
- The precise integration policy for each customer organization remains configurable.

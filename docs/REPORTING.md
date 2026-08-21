# Reporting

## Purpose
This document defines the reporting architecture for Atlas.

It distinguishes operational reporting from financial summaries and keeps AI-generated narrative draft-only.

## P-05 Implementation Note

Sprint P-05 introduces the first deterministic document-template engine implementation for commercial-document generation.
Template precedence, revision template snapshots, and output hash capture now provide a concrete reusable baseline for broader reporting-template evolution.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [OBSERVABILITY.md](OBSERVABILITY.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)

## Reporting Categories
Reporting should support:
- operational reports
- estimator reports
- project reports
- executive reports
- service reports
- audit reports

## Commercial Operational Read Models

REP-01 adds tenant-scoped commercial reporting read models on top of the
operational spine defined by CM-03, CM-04, INV-01, and FIN-01. These read
models stay deterministic and read-only: they summarize counts, totals, and
sync readiness from existing commercial repository records without creating a
separate reporting store.

Supported commercial summaries are documented in
[COMMERCIAL_REPORTING_READ_MODELS.md](COMMERCIAL_REPORTING_READ_MODELS.md).

## Deterministic Exports
Reports should be reproducible and versioned where practical.

Export formats may include:
- PDF
- HTML
- CSV
- JSON

## Report Templates
Templates should support:
- tenant branding
- permission-aware content
- filters
- snapshots
- source provenance
- stable layout behavior

## Operational Versus Financial Reports
Atlas operational reports should remain distinct from QuickBooks-derived financial summaries.

QuickBooks-derived summaries may be included where appropriate, but they should be labeled as financial data sourced from accounting systems rather than Atlas operational truth.

Commercial reporting read models should surface QuickBooks sync readiness and
invoice/vendor-bill operational status, not accounting-ledger truth.

The sync states and idempotency metadata summarized here are defined in
[QB_01_QUICKBOOKS_SYNC_ARCHITECTURE.md](QB_01_QUICKBOOKS_SYNC_ARCHITECTURE.md).

## Scheduling And Delivery
Reporting architecture should eventually support scheduled delivery and on-demand generation.

Delivery channels may include email, downloads, dashboards, and future integrations.

## Versioning And Reproducibility
Reports should record:
- template version
- data snapshot or source state
- filter criteria
- generation timestamp
- provenance references

## Permissions
Report generation and viewing should respect tenant and role permissions.

## AI Narrative
AI-generated narrative should be treated as draft-only until a human reviews it.

AI can help summarize or explain report contents, but it should not replace deterministic report data.

## Unresolved Decisions
- final template engine remains open
- final scheduling mechanisms remain open
- final delivery channels remain open

## T-05 Amendment: Commercial Document PDF Exports

Deterministic PDF export is now available for transaction-document revisions:
- Internal Estimate
- Customer Estimate
- Sales Order

Export guarantees:
- reproducible output from the same document revision and section configuration
- filename includes document number and revision
- issued and archived revisions remain exportable
- export activity metadata is recorded
- export generation does not mutate revision commercial content

## T-07 Implementation: Presentation-Aware Commercial PDFs

Commercial document PDFs now preserve presentation metadata where present:
- line order
- group headings
- optional group subtotals
- blank spacing rows
- comment rows
- selected visible columns

Grand totals remain sourced from authoritative commercial calculations rather than presentation rows.
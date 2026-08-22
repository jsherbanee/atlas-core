# Atlas Roadmap

This document is the executive milestone overview for Atlas.

For product-horizon detail, see [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md).
For engineering execution detail, see [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md).
For implementation planning and epic IDs, see [EPICS.md](EPICS.md).
For lifecycle sequencing, see [AV_LIFECYCLE.md](AV_LIFECYCLE.md).

## Executive Milestones

Atlas milestones describe customer-visible capability horizons rather than sprint-level implementation detail.

### Preview Line
- Preview 0.5: Engineering Intelligence Workspace
- Preview 0.6: Engineering Understanding, Master Library, Manufacturer Registry, Product Intelligence, Equipment Resolution, System Templates
- Preview 0.7: Drawing and specification maturation, commercial knowledge foundation, deterministic pricing and cost foundations

### Stabilization Line
- Beta 1.0: internal production readiness, benchmark validation, performance tuning, documentation completion
- RC1: release-candidate stabilization

### Platform Line
- Atlas 1.0: Intelligent Lifecycle Solutions Management Platform for AV and lighting systems integrators
- Atlas 2.0: Complete Operational Lifecycle Platform

## Roadmap Layering

- [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) describes business-facing capability horizons.
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md) describes technical sequencing, gates, and dependencies.
- [EPICS.md](EPICS.md) describes implementation planning and sprint streams.
- [AV_LIFECYCLE.md](AV_LIFECYCLE.md) defines the lifecycle model that informs both product and engineering roadmaps.

## Current Status

Phase 2 Bid Intelligence is closed.

Phase 2 completed Atlas's local project and persistence foundation, not the full Atlas commercial product.

Current planning has moved to Commercial MVP readiness, with staged AWS readiness as enabling architecture rather than the immediate product goal.

Epic X is completed and formally closed.

X-01 through X-11 are closed.

No Epic X sprint is active.

Current focus is Commercial MVP readiness.

Epic E remains the next candidate epic pending architecture review and sprint approval.

Epic E has not started.

## Commercial MVP Roadmap

Commercial MVP readiness is the near-term goal. It is the operating spine Atlas must establish before deeper engineering-intelligence work.

This roadmap is staged and adapter-based, not a rewrite. Local and future AWS adapters must coexist behind the same repository boundary.

- Tenant-scoped repository boundary: each tenant's data must remain isolated as a standalone Atlas repository boundary before major new product modules depend on persistence.
- Customer/account foundation: represent customers and commercial accounts as first-class operational records.
- Opportunity tracking: track pipeline opportunities and commercial progression.
- Estimating: support deterministic estimating as the core commercial entry point.
- Proposal workflow: generate and manage proposal-facing commercial workflows.
- Sales order management: manage sales orders as the operational system of record.
- Change order basics: support the minimum change-order flow needed for commercial operations.
- Project/job conversion: convert accepted commercial work into project/job execution state.
- Item/catalog foundation: maintain a strong item, catalog, and pricing foundation.
- Inventory availability, reservation, allocation, and receiving basics: introduce inventory-aware fulfillment behaviors.
- Vendor/manufacturer registry maturation: mature registry, lifecycle, and relationship workflows.
- Procurement/RFQ workflow: add procurement and RFQ capability after the core data boundary is in place.
- Commercial reporting: develop reporting that reflects the commercial operating spine.
- QuickBooks connector planning: define the connector boundary and sync ownership model before any transport work.
- Atlas API layer: introduce a durable API layer for future clients and adapters.
- AWS adapter migration: move staged, adapter-by-adapter, with local and AWS implementations able to coexist.
- Commercial tenant/account administration: add tenant and account administration capabilities for commercial operations.

Deep engineering intelligence remains deferred until the commercial operating spine is established, except for narrow design slices required to support estimating.

## Historical Context

Historical release and preview detail remains preserved in [RELEASE_NOTES.md](RELEASE_NOTES.md), [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md), and [PREVIEW_0_5_CHECKLIST.md](PREVIEW_0_5_CHECKLIST.md).

Do not use this executive roadmap as the source of truth for sprint-level scope or current implementation status.

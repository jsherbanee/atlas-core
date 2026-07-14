# Product Roadmap

## Purpose
This document is the customer- and business-facing product roadmap for Atlas.

It describes capability horizons without implementation-level sprint detail.

For lifecycle sequencing, see [AV_LIFECYCLE.md](AV_LIFECYCLE.md).
For engineering execution, see [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md).
For implementation planning and epic IDs, see [EPICS.md](EPICS.md).
For work-selection governance, see [PRODUCT_GOVERNANCE.md](PRODUCT_GOVERNANCE.md).

## Related Documents
- [ROADMAP.md](ROADMAP.md)
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)
- [EPICS.md](EPICS.md)
- [AV_LIFECYCLE.md](AV_LIFECYCLE.md)
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [SERVICE_AND_ASSET_LIFECYCLE.md](SERVICE_AND_ASSET_LIFECYCLE.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)

## Roadmap Principles
- Use capability horizons rather than unsupported dates.
- Preserve current Phase 2 Bid Intelligence as the active baseline.
- Document future value without claiming implementation that does not yet exist.
- Keep business milestones separate from technical sprint detail.
- Treat SaaS readiness, multi-tenant administration, integrations, and enterprise readiness as progressive horizons.
- Ideas do not become scheduled work merely because they are documented.
- Active work must be traceable to an approved roadmap item.

## Document Responsibility
- This document defines approved customer-facing capability horizons.
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md) defines technical sequencing and engineering gates.
- [EPICS.md](EPICS.md) defines epic and sprint status.
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) defines current implementation status.
- [RELEASE_NOTES.md](RELEASE_NOTES.md) remains historical.

## Atlas 1.0 Capability Map
Approved 1.0 major areas:
- Projects and lifecycle
- Knowledge
- Transactions
- Commercial documents
- Settings and tenant configuration
- Search and object navigation
- Reporting
- Security and tenant isolation
- Auditability
- Integrations foundation
- User and role administration
- Required operational workflows

## Capability Horizons

### Current Foundation
- Phase 2 Bid Intelligence remains the active implementation focus.
- Atlas provides deterministic workspace behavior for bid review and estimating foundations.
- Current value centers on review, traceability, and workspace hardening.

### Near-Term Platform Foundation
- stronger project onboarding and identity clarity
- better search and object discovery
- clearer document intake and diagnostics
- more robust report export and workspace navigation
- broader tenant-aware architecture foundations
- commercial transactions and document-operations architecture

### Lifecycle Expansion
- commercial document operations across customer-side and vendor-side workflows
- engineering maturity beyond bid review
- procurement readiness
- field execution support
- commissioning and closeout support
- service and warranty tracking
- asset lifecycle continuity from project to installed-system history

Inventory note:
- inventory remains on pause as a visible roadmap concern and is not active implementation work

## Transactions Architecture Note

Sprint A-07 defines the future Transactions workspace and commercial-document ownership model as architecture only.

This roadmap step means Atlas is expected to own operational transaction creation and workflow before financial sync, while QuickBooks remains the Financial System of Record after sync.

## Commercial Document Framework Note

Sprint A-08 adds the shared framework for commercial documents as architecture only.

This means Atlas now has a documented common contract for transaction-family document identity, revision philosophy, lifecycle, approvals, relationships, numbering, and sync metadata before implementation begins.

### SaaS Commercialization
- multi-tenant administration
- organization and seat management
- subscription readiness
- role-aware access and enterprise policy controls
- customer onboarding and validation milestones
- operational support for commercial launch readiness

### Enterprise and Ecosystem
- stronger integrations with accounting, billing, productivity, and field systems
- enterprise access controls and delegated administration
- tenant-specific policies and configuration
- public API and ecosystem readiness where appropriate

## Product Hardening Candidates
Required for 1.0:
- permissions and roles
- audit engine
- attachments

Candidate for 1.0:
- background jobs
- notifications
- document generation
- search refinement
- settings refinement

Post-1.0:
- deeper inventory execution beyond currently documented receiving hooks

### Long-Term Intelligence Platform
- AI-assisted guidance grounded in authorized organizational context
- standards-informed reasoning
- manufacturer-aware technical assistance
- relationship-aware search and knowledge discovery
- cross-project intelligence and lifecycle analytics

## Commercial Milestones
- validate current-phase product fit with real projects
- refine commercial packaging for the initial market segment
- support scalable onboarding and administration
- mature enterprise licensing and integration readiness

## Customer Validation Milestones
- successful bid-intelligence workflow adoption
- deterministic review and reporting confidence
- clear search and object-discovery experience
- dependable project intake and export behavior
- tenant-safe administration and support processes

## Roadmap Summary
Atlas is evolving from a bid-intelligence foundation into a complete lifecycle platform for AV and lighting systems integrators.

The roadmap should emphasize balanced progression across sales, engineering, delivery, service, and intelligence rather than overcommitting to any single workflow domain.

## Unresolved Decisions
- exact sequencing of later lifecycle capabilities remains flexible
- commercial launch packaging may evolve as customer validation continues
- enterprise readiness milestones will depend on architecture and support maturity

## L-01 Roadmap Note

Sprint L-01 establishes the lifecycle-engine foundation that future lifecycle-expansion milestones will rely on.

Business meaning:
- Atlas now has one canonical lifecycle vocabulary and deterministic transition model for project records
- downstream lifecycle workflows remain intentionally staged behind this foundation rather than shipping as partial execution tools
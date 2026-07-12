# Atlas Core Architecture

## Related Documents
- [README.md](README.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [MASTER_LIBRARY.md](MASTER_LIBRARY.md)
- [ROADMAP.md](ROADMAP.md)

## Domain Alignment
Atlas lifecycle object definitions and cross-phase continuity rules are defined in [DOMAIN_MODEL.md](DOMAIN_MODEL.md).
Architecture and module design should align to that domain model so Phase 2 artifacts remain reusable in downstream phases.

Atlas's visual and UX philosophy is defined in [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md), which should be treated as a foundational architecture document alongside the domain model.

## Engine-First Architecture
Atlas Core is the engine. Future web and API layers should call Atlas Core services and contracts rather than duplicating business logic in separate code paths.

## Layers
- domain
  - Canonical dataclasses/enums and normalization rules.
- services
  - Orchestration and business workflows (review build, readiness, outputs).
- rules
  - Deterministic rule contracts, registries, and rule engine evaluation.
- registries
  - Reference datasets and lookup abstractions (manufacturer/vendor and similar).
- contracts
  - Stable payload/data shapes that downstream surfaces consume.
- exports
  - CSV/JSON/Markdown output adapters from engine outputs.
- CLI
  - Local execution entry point for running workflows against project inputs.

## Core Principle
Business logic should live once in the Atlas Core engine and be reused by all callers:
- CLI
- future API services
- future UI/web applications

## Rule Engine Direction
Atlas is moving to a registry-driven rule model where:
- Rule families register into a shared EngineeringRuleRegistry.
- EngineeringRuleEngine evaluates all relevant rules for a review context.
- Assumptions and related intelligence are deduplicated by stable IDs.
- New discipline coverage is added through modular rule files, not ad hoc service conditionals.

This keeps behavior deterministic, testable, and easy to extend as Phase 2 Bid Intelligence expands.

## Deterministic Estimating Foundation
Sprint 8 introduces deterministic estimating architecture as an engine-layer extension.

Design posture:
- Estimating remains object-driven and traceable to reviewed engineering entities.
- No hidden calculations and no black-box pricing.
- Unknown product resolution states do not receive deterministic pricing.
- Proposal/procurement/financial workflows remain out of scope.

Implementation structure:
- domain: deterministic estimate entities and status enums
- services: deterministic estimate build, totals, dashboard, and confidence modeling
- UI shell: Estimate Workspace sections that surface deterministic model outputs

Extension boundaries are interface-only for future adapters:
- vendor/manufacturer/price/quote integrations
- labor rules and regional multipliers
- tax/currency
- proposal/RFQ generators

## Deterministic Product Resolution Engine
Sprint 9 adds a dedicated deterministic Product Resolution engine that sits between reviewed engineering objects and estimate preparation.

Design posture:
- No AI guessing; every match has explicit deterministic reason paths.
- Not pricing, not procurement, and not quote generation.
- Manual overrides are permitted only with reviewer/timestamp/reason audit fields while preserving original auto-match context.

Implementation structure:
- domain: product resolution models and override audit model
- services: deterministic candidate ranking and resolution assignment
- workspace shell: dedicated Product Resolution page with filters and manual override controls
- review/estimate integration: engineering summary metrics and estimate pricing gate enforcement

Source-of-truth references:
- [PRODUCT_RESOLUTION.md](PRODUCT_RESOLUTION.md)
- [MANUFACTURER_REGISTRY.md](MANUFACTURER_REGISTRY.md)

## Commercial Knowledge Foundation
Sprint 9 adds a commercial knowledge subsystem built around immutable price-sheet versioning.

Design posture:
- products do not own prices
- vendor offerings own commercial availability
- price records are immutable and tied to price-sheet versions
- every import creates a new permanent historical version
- commercial history supports deterministic readiness, not procurement execution

Implementation structure:
- domain: commercial object model (Vendor Offering, Price Sheet, Price Sheet Version, Price Record)
- service: immutable import, version comparison, change report generation, lifecycle/freshness metrics
- workspace shell: commercial health dashboard, import history page, and product-resolution commercial context panel

Source-of-truth references:
- [COMMERCIAL_KNOWLEDGE.md](COMMERCIAL_KNOWLEDGE.md)
- [PRICE_VERSIONING.md](PRICE_VERSIONING.md)

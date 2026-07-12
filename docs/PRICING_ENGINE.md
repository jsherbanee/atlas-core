# Atlas Deterministic Pricing Engine

## Related Documents
- [ESTIMATING.md](ESTIMATING.md)
- [COMMERCIAL_KNOWLEDGE.md](COMMERCIAL_KNOWLEDGE.md)
- [PRICE_VERSIONING.md](PRICE_VERSIONING.md)
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)

## Purpose
Sprint 10 introduces a deterministic pricing selection layer on top of deterministic estimate lines and immutable commercial knowledge.

Goal:
Assign a defensible material price to each resolved BOM/estimate line by selecting a specific immutable Price Record with explicit rule traceability.

Out of scope:
- procurement
- purchase ordering
- proposal generation
- accounting posting

## Core Objects
Domain objects are defined in atlas_core/domain/pricing_engine.py:
- PricingResult
- PricedEstimateLine
- PriceSelection
- PriceSelectionCandidate
- PricingRule
- PricingWarning
- PricingSummary
- CommercialCoverageSummary
- PriceManualOverride

## Deterministic Selection Workflow
Service implementation: atlas_core/services/pricing_engine_service.py (DeterministicPricingEngine)

Selection order:
1. active project quote candidates (exact match first)
2. preferred-vendor policy matches (project/product/manufacturer/organization scopes)
3. current/verified records from latest price sheet versions
4. historical records
5. stale/expired/missing-from-latest fallback records
6. generic allowance when explicitly configured
7. no_pricing when no deterministic candidate exists

All candidates are retained for audit in PriceSelection.candidates.

## Pricing Status Model
Pricing statuses:
- verified_current
- quoted
- current_price_sheet
- historical_price
- estimated_allowance
- stale_price
- expired_price
- missing_from_latest_price_sheet
- unavailable
- no_pricing
- manual_override

## Confidence and Coverage
Each priced line includes:
- pricing_confidence (0 to 1)
- confidence_rationale (explainability messages)
- freshness_status
- warnings
- source_refs (price sheet/version/record/import/comparison trace)

Commercial coverage summary reports:
- priced/unpriced coverage across resolved products
- material value distribution (current, quoted, stale/estimated)
- aggregate commercial confidence

## Manual Override Model
Manual overrides are advisory and auditable:
- preserve original automatic selection snapshot
- store manual unit cost, vendor, reason, reviewer placeholder, timestamp, source reference
- set line status to manual_override

## Snapshot and Rerun Behavior
Every pricing run produces:
- pricing_run_id (deterministic hash of estimate + resolutions + commercial state + policies)
- run_timestamp
- pricing_policy_version

Reruns with unchanged inputs produce the same pricing_run_id.

## Advisory Price Update Impacts
The engine provides non-mutating impact detection between snapshots:
- Price Increase Available
- Price Decrease Available
- Selected Price Became Stale
- Selected Product Missing From Latest Sheet
- New Vendor Offering Available

No automatic repricing is performed on prior snapshots.

## Exports
Built-in export helpers:
- Pricing Summary JSON
- Priced BOM CSV
- Commercial Coverage JSON
- Pricing Exceptions CSV

## UI Integration
Estimate and BOM Review workspaces now surface deterministic pricing fields:
- pricing run metadata and coverage
- selected deterministic unit cost/status/freshness
- vendor alternatives
- warnings/exceptions
- pricing history view by canonical product

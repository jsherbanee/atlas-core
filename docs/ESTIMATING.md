# Atlas Deterministic Estimating

## Related Documents
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [PHASE2_GUI.md](PHASE2_GUI.md)
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- [PRICING_ENGINE.md](PRICING_ENGINE.md)
- [COST_ENGINE.md](COST_ENGINE.md)

## Purpose
This document defines Atlas deterministic estimating architecture.

The goal is to convert reviewed engineering objects into estimate-ready line items where every dollar is traceable and reproducible.

Out of scope for this foundation:
- proposal generation
- purchasing/procurement workflows
- RFQ generation
- financial posting

## Deterministic Principles
- Every estimate line must reference a source engineering object.
- Every cost status must be explicit.
- Every product resolution state must be explicit.
- Confidence must explain why certainty is high or low.
- No hidden calculations or black-box pricing behavior.

## Estimate Architecture
Sprint 8 introduces a deterministic estimate model and service layer.
Sprint 10 adds deterministic acquisition cost selection over immutable commercial knowledge:
- domain entities in atlas_core/domain/deterministic_estimate.py
- deterministic estimate orchestration in atlas_core/services/estimate_service.py
- deterministic pricing entities in atlas_core/domain/pricing_engine.py
- deterministic cost entities in atlas_core/domain/cost_engine.py
- deterministic pricing orchestration in atlas_core/services/pricing_engine_service.py
- deterministic cost orchestration in atlas_core/services/cost_engine_service.py
- UI workspace integration in apps/phase2_review_app.py (Estimate page)

Core flow:
1. reviewed BOM/equipment objects are read from project context
2. deterministic estimate lines are generated
3. deterministic product resolution gates pricing eligibility
4. deterministic cost selection selects immutable price records and retains alternatives
5. each line records source traceability and resolution/pricing state
6. totals and confidence are calculated from explicit model state

## Estimate Object Model
Primary objects:
- Estimate
- EstimatePackage
- EstimateLine
- MaterialCost
- LaborCost
- AccessoryCost
- FreightCost
- Allowance
- Subtotal
- Markup
- Contingency
- GrandTotal

EstimateLine traceability fields:
- source_object
- object_type
- manufacturer
- model
- description
- quantity
- pricing_status
- labor_status
- confidence
- source_references

## Product Resolution States
Atlas currently models product resolution as:
- exact_product
- approved_substitute
- preferred_alternate
- generic_allowance
- unknown_product

Unknown products are not eligible for deterministic pricing.

## Cost Status Model
Line-level cost status:
- no_pricing
- estimated
- quoted
- verified
- expired
- unavailable

Labor status uses the same deterministic status model.

## Deterministic Pricing Engine (Sprint 10)
Pricing engine outputs are separate from baseline estimate-line material snapshots.

Pricing engine objects:
- PricingResult
- PricedEstimateLine
- PriceSelection
- PriceSelectionCandidate
- PricingRule
- PricingWarning
- PricingSummary
- CommercialCoverageSummary

Deterministic pricing statuses:
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

Deterministic pricing run metadata:
- pricing_run_id
- run_timestamp
- pricing_policy_version

Deterministic pricing exports:
- Pricing Summary JSON
- Priced BOM CSV
- Commercial Coverage JSON
- Pricing Exceptions CSV

Pricing update impacts are advisory only (no silent repricing).

## Deterministic Cost Engine (Sprint 10)
Cost engine outputs provide acquisition-cost-first deterministic selection with traceable vendor hierarchy.

Cost engine objects:
- CostResult
- CostLine
- CostSelection
- CostCandidate
- CostSummary
- CostConfidence

Cost statuses:
- verified
- quoted
- current
- historical
- allowance
- stale
- expired
- unavailable
- missing

Out of scope remains explicit:
- markup
- sell pricing
- margin strategy
- proposal generation

## Labor Architecture
Labor architecture categories are defined even when line-level labor values are empty:
- receiving
- staging
- rack_build
- installation
- termination
- programming
- commissioning
- testing
- training
- punch

## Accessory Architecture
Accessory generation is architecture-only in Sprint 8.

Placeholder categories:
- Mounts
- Cables
- Connectors
- Rack Hardware
- Faceplates
- Adapters
- Power Supplies
- Network Modules

No automatic accessory generation is executed in this sprint.

## Estimate Dashboard Model
Estimate dashboard fields:
- Material Cost
- Labor Cost
- Allowance Cost
- Freight
- Contingency
- Known Cost %
- Unknown Cost %
- Resolved Products
- Unresolved Products
- Pricing Confidence
- Overall Estimate Confidence

## Confidence Model
Estimate confidence combines:
- known pricing ratio
- resolved product ratio
- unpriced labor ratio
- unknown quantity ratio
- generic allowance ratio

Confidence output includes explanatory messages describing observed gaps.

## Navigation Model
Estimate line navigation actions target:
- Equipment
- Specification
- Drawing
- Relationships
- Evidence

Object detail headers include an explicit Open Estimate Workspace action to support source-to-estimate return navigation.

## Future Extension Points
The deterministic estimate service defines extension interfaces for future, non-implemented integrations:
- vendor registry
- manufacturer registry
- price lists
- quote imports
- labor rules
- regional multipliers
- sales tax
- currency conversion
- proposal generator
- RFQ generator
- accessory generation

These are interface-only placeholders in Sprint 8.

Pricing extension points are implemented for Sprint 10 inputs:
- preferred vendor policy hierarchy
- project quote candidate inputs
- explicit generic allowance map
- manual override audit model

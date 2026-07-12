# Atlas Deterministic Cost Engine

## Related Documents
- [ESTIMATING.md](ESTIMATING.md)
- [COMMERCIAL_KNOWLEDGE.md](COMMERCIAL_KNOWLEDGE.md)
- [PRICE_VERSIONING.md](PRICE_VERSIONING.md)
- [PRODUCT_RESOLUTION.md](PRODUCT_RESOLUTION.md)

## Cost Philosophy
Atlas computes acquisition cost only.

The deterministic cost engine answers:
- What does this item cost us?
- Where did this cost originate?
- Which vendor supplied it?
- Which price sheet version supplied it?
- How current is the information?
- How confident are we?

Out of scope:
- markup
- sell price
- gross margin strategy
- proposal pricing
- competitive positioning
- tax, procurement, RFQ, purchase order workflows

## Cost Object Model
Domain entities are implemented in atlas_core/domain/cost_engine.py:
- CostResult
- CostLine
- CostSelection
- CostCandidate
- CostSummary
- CostConfidence

Each CostLine references:
- equipment object
- resolved product
- vendor offering
- price record
- price sheet version

## Vendor Hierarchy
Vendor classifications:
- manufacturer_direct
- authorized_distributor
- regional_distributor
- buying_group
- marketplace
- integrator
- other

Deterministic selection order:
1. project-specific quoted cost
2. preferred vendor current cost
3. manufacturer direct current cost
4. authorized distributor current cost
5. other current vendor
6. historical current-equivalent cost
7. allowance
8. no cost

## Cost Status Model
- verified
- quoted
- current
- historical
- allowance
- stale
- expired
- unavailable
- missing

## Traceability
Each CostLine carries:
- vendor
- vendor type
- price sheet version
- import date
- effective date
- expiration date
- days since import
- source file
- source row
- confidence rationale

## Commercial Coverage
Coverage tracks:
- resolved products
- products with current cost
- products using historical cost
- products using allowances
- products missing cost
- products with stale/expired cost
- coverage percentage
- material cost confidence

## Quick Add Workflow
Quick Add Product supports one-off estimate SKUs.

Inputs:
- manufacturer
- model
- description
- vendor
- vendor type
- cost
- source
- project

After creation:
- Project Only: stores as project-scoped quick-add candidate
- Promote to Master Library: imports a single immutable commercial record into shared commercial knowledge

## Project-Only Products
Project-only quick-add products remain isolated to project session state and are considered during deterministic cost selection for that project.

## Product Promotion
Promoted quick-add products create immutable commercial artifacts through existing import architecture:
- product key
- vendor offering
- price sheet version
- price record

## Future Sell Pricing Boundary
The deterministic cost engine is a required foundation for future sell-pricing strategy but does not implement sell-side pricing behavior.

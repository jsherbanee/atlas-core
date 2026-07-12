# Product Resolution

## Purpose
Product Resolution is the deterministic bridge between reviewed engineering objects and estimate preparation.

It exists to answer one question before pricing:

- Which canonical product identity is this equipment row mapped to?

Product Resolution is intentionally:

- Not pricing
- Not procurement
- Not quote generation
- Not AI guessing

Every match path must be explainable and traceable.

## Deterministic Match Order
Product resolution candidates are ranked in this fixed order:

1. exact manufacturer + exact model
2. normalized manufacturer + normalized model
3. alias match
4. approved substitute
5. preferred alternate

If no deterministic candidate can be selected:

- generic allowance may be used when source completeness is partial
- unknown product is used when manufacturer/model evidence is missing or unresolved

## Resolution Statuses
- exact_product
- approved_substitute
- preferred_alternate
- generic_allowance
- unknown_product

Status drives estimate readiness:

- Pricing-ready: exact_product, approved_substitute, preferred_alternate
- Pricing-blocked: generic_allowance, unknown_product

## Traceability Requirements
Each resolution record includes:

- source_object_id
- canonical_product and canonical_product_id when available
- manufacturer and model used for deterministic evaluation
- candidate_matches with match_type, confidence, and reason
- resolution_reason
- source_evidence (document/drawing/spec references)

No opaque scoring is allowed. Confidence exists only as a deterministic aid and must be explainable.

## Manual Override
Manual override is supported for reviewer-driven selection and must preserve auditability.

Manual override stores:

- original_match snapshot (if present)
- manual_selection details
- reviewer
- timestamp
- reason

Manual override must not destroy the original deterministic result.

## Estimate Preparation Extension Fields
Resolution records include estimate-prep extension points:

- canonical_product_id
- manufacturer_id
- future_price_records
- future_vendor_records
- future_labor_templates

These fields are intentionally placeholders for future deterministic adapter integrations.

## Workspace Integration
The Product Resolution workspace page provides:

- Equipment-level resolution table
- Current Resolution badge
- Confidence and Reason
- Manufacturer and Model
- Candidate match count/top candidate
- Required Action signal
- Filters: Unknown, Low Confidence, Needs Review, Resolved, Substituted
- Manual override controls and audit summary

Engineering Review includes a Product Resolution summary with:

- Resolved Products
- Unknown Products
- Generic Allowances
- Substitutions
- Products Requiring Review

Estimate workspace consumes resolution output and enforces deterministic pricing gating.

Commercial knowledge integration on resolved products includes:

- known vendors
- current price-sheet lifecycle status
- latest commercial version
- historical commercial versions
- commercial freshness status
- pricing availability signal

This integration remains read-only in Sprint 9 and does not calculate estimate pricing.

## Source Files
- `atlas_core/domain/product_resolution.py`
- `atlas_core/services/product_resolution_service.py`
- `apps/phase2_review_app.py`
- `atlas_core/services/estimate_service.py`
- `atlas_core/services/commercial_knowledge_service.py`
- `tests/test_product_resolution_domain.py`
- `tests/test_product_resolution_service.py`

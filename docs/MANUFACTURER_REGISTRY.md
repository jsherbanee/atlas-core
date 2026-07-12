# Manufacturer Registry

## Purpose
Manufacturer Registry provides deterministic manufacturer normalization and discipline/tier relationships for Atlas workflows.

It is a reference layer used by:

- Product resolution candidate ranking
- Approved substitute checks
- Preferred alternate checks
- Future manufacturer-level policy decisions

## Scope
Manufacturer Registry is intentionally:

- deterministic reference data
- not a vendor catalog
- not procurement policy
- not pricing logic

## Core Concepts
- Manufacturer identity: stable manufacturer_id and name
- Discipline: audio, video, control, lighting, projection, infrastructure, or other mapped enums
- Tier: preferred, approved, legacy, restricted, unknown

## Resolution Usage
Product Resolution consumes registry data to classify candidates:

- approved_substitute: candidate manufacturer is approved in requested discipline
- preferred_alternate: candidate manufacturer is preferred in requested discipline

This logic is deterministic and explainable through explicit relationship checks.

## Commercial Knowledge Usage
Commercial knowledge uses manufacturer identity as the top-level anchor for immutable price-sheet history.

Registry identity supports deterministic grouping for:

- manufacturer-specific price sheets
- cross-version product presence/missing detection
- commercial freshness and coverage reporting

## Source Files
- `atlas_core/registry/manufacturer_registry.py`
- `atlas_core/sample_data/manufacturer_seed.py`
- `atlas_core/services/product_resolution_service.py`

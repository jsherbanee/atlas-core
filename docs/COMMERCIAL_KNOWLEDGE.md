# Commercial Knowledge

## Purpose
Commercial Knowledge is Atlas Core's immutable commercial reference layer for deterministic estimating readiness, historical bid recreation, and future procurement integrations.

This layer is intentionally:

- not procurement
- not quote generation
- not purchase ordering
- not estimate calculation

## Architectural Rule
Products do not own prices.

Commercial availability and pricing flow through this hierarchy:

- Manufacturer
- Product
- Vendor
- Vendor Offering
- Price Sheet
- Price Sheet Version
- Price Record

Each object has stable identifiers.

## Object Model

### Vendor Offering
Vendor Offering is the commercial availability object tied to vendor-specific product identity.

Key fields:

- vendor_offering_id
- vendor
- product
- manufacturer
- vendor_sku
- latest_version
- historical_versions

### Price Sheet
Price Sheet represents a named commercial source per vendor/manufacturer.

Key fields:

- price_sheet_id
- vendor
- manufacturer
- sheet_name
- description
- active_version
- created_date
- last_import_date
- status
- notes

### Price Sheet Version
Price Sheet Version is immutable and created for every import.

Key fields:

- version_id
- price_sheet_id
- version_name
- import_date
- effective_date
- expiration_date
- source_filename
- file_hash
- imported_by
- row_count
- added_products
- removed_products
- updated_products
- unchanged_products
- warnings

### Price Record
Price Record is immutable and tied to a version.

Key fields:

- price_record_id
- version_id
- vendor
- product
- vendor_sku
- cost
- list_price
- currency
- lead_time
- availability
- effective_date
- expiration_date
- confidence
- source_row
- notes

## Version Comparison
Each new version compares against prior active version for the same Price Sheet.

Detections:

- Products Added
- Products Removed
- Price Increased
- Price Decreased
- Description Changed
- Lead Time Changed
- Availability Changed
- Vendor SKU Changed

Comparison output is deterministic and included in import history and change reports.

## Lifecycle Handling
Missing products are not immediately discontinued.

Supported lifecycle states:

- active
- missing_from_latest_price_sheet
- suspected_discontinued
- confirmed_discontinued
- replacement_available
- obsolete
- unknown

Default missing transition:

- missing_from_latest_price_sheet

## Knowledge Freshness
Commercial freshness is tracked independently from engineering lifecycle.

Freshness statuses:

- fresh
- review_recommended
- stale
- missing

Rule:

- products without updated pricing for more than 365 days become stale

## Commercial Health Dashboard
Application-level dashboard summarizes:

- manufacturers
- vendors
- products
- vendor offerings
- active price sheets
- latest imports
- products missing pricing
- pricing stale
- recently updated
- products missing from latest version
- coverage percentage
- knowledge freshness
- commercial confidence

## Product Resolution Integration
When Product Resolution succeeds, commercial detail surfaces:

- known vendors
- current price sheet status
- latest version
- historical versions
- commercial freshness
- pricing availability

No estimate pricing calculation is performed in this layer.

## Source Files
- `atlas_core/domain/commercial_knowledge.py`
- `atlas_core/services/commercial_knowledge_service.py`
- `apps/phase2_review_app.py`
- `tests/test_commercial_knowledge_service.py`

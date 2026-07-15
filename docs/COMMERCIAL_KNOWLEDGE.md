# Commercial Knowledge

## Purpose
Commercial Knowledge is Atlas's immutable commercial reference layer for deterministic estimating readiness, historical bid recreation, and future procurement integrations.

C-03 extension note:
- Commercial Knowledge now includes a catalog foundation for deterministic item reuse across transactions and settings-driven pricing/tax defaults.

This layer is intentionally:

- not procurement
- not quote generation
- not purchase ordering
- not estimate calculation

K-02 integration note:
- Core commercial identities (manufacturer, vendor, product) are synchronized with the shared Knowledge Entity Framework so operational knowledge workflows and commercial state remain deterministic and aligned.

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

### Catalog Item (C-03)
Catalog Item is the reusable transaction-facing commercial identity for products, services, and fees.

Key fields:

- catalog_item_id
- item_type (`product`, `service`, `fee`)
- code
- name
- manufacturer
- vendor
- uom
- cost
- msrp
- map_price
- manual_unit_price
- taxable
- default_tax_nexus
- archived

Catalog items are deterministic references and do not mutate previously issued commercial-document snapshots.

### Tax Nexus Rule (C-03)
Tax Nexus Rule models deterministic tax selection by nexus and item applicability.

Key fields:

- tax_rule_id
- nexus
- title
- rate
- priority
- compound
- taxable_item_types
- exemption_flags
- effective_date
- expiration_date
- archived

Rules are evaluated by priority and filtered by effective window, item type, and exemption flags.

### Pricing Policy Defaults (C-03)
Commercial Knowledge stores tenant pricing defaults for deterministic quote behavior:

- default_policy (`msrp`, `map`, `cost_plus_percent`, `margin_percent`, `multiplier`, `manual`)
- default_markup_percent
- default_margin_percent
- default_multiplier
- rounding_policy

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

C-02 lifecycle adds explicit state transitions before immutable finalization:

- draft: parsed and mapped preview, may contain unresolved records and diagnostics
- validated: no blocking `error` diagnostics; `warning` diagnostics explicitly acknowledged
- finalized: immutable version and immutable price records created
- failed: import attempt could not be validated/finalized

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

## C-02 Import Validation Model

Supported import diagnostics:

- error (blocking finalize)
- warning (requires explicit acknowledgment)
- informational (non-blocking context)

Core C-02 controls:

- deterministic column mapping suggestions from normalized header synonyms
- worksheet/header-row selection for XLSX imports
- PDF inspection and staged extraction for text-native, table-based, multi-page, and scanned sources
- row-level preview records with resolved/unresolved status
- duplicate source file hash detection against immutable version history
- manual draft creation and manual record insertion for exceptional data entry

## PDF Import Support (C-02 Amendment)

Supported PDF types:

- text-native PDFs
- table-oriented PDFs
- multi-page PDFs
- PDFs with repeated page headers/footers
- scanned PDFs using existing OCR-capable intake infrastructure when available

Deterministic PDF workflow:

1. source inspection (validity, encryption, page count, rotation, text availability)
2. extraction (embedded text first, OCR fallback by page where required)
3. table candidate detection (page-aware regions, repeated header/footer awareness)
4. user-controlled page/table/header/column selection
5. row transformation into the shared draft preview model
6. diagnostics review and optional draft corrections
7. validation and immutable finalization

User-control requirements:

- page-range selection
- table-candidate selection
- header-row confirmation
- column mapping confirmation
- correction of extracted row values while draft is mutable

Finalized records remain immutable.
Post-finalization corrections require a new Price Sheet Version.

PDF diagnostics include deterministic `error`, `warning`, and `informational` severities for extraction uncertainty and mapping/validation failures.
Atlas does not silently accept uncertain OCR or ambiguous extraction output.

PDF limitations in C-02:

- common commercial table layouts are supported
- brochure-style or highly irregular catalog layouts may require manual page/region/header selection
- no generative interpretation or autonomous commercial judgment is performed

## C-02 Completeness Signals

Commercial completeness rollups include:

- products without offerings
- products without finalized price records
- products without currently effective pricing
- offerings without pricing and stale/expired/future-only freshness states
- vendors with unresolved records
- price sheets without finalized versions
- price sheets with pending drafts
- unresolved price record totals

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
- `atlas_core/domain/commercial_product.py`

## C-03 Import Coverage

Catalog foundation import coverage now includes:

- manufacturers (CSV/XLSX)
- vendors (CSV/XLSX)
- products (CSV/XLSX)
- services (CSV/XLSX)
- fees (CSV/XLSX)
- `atlas_core/services/master_library/commercial_product_service.py`
- `apps/phase2_review_app.py`
- `tests/test_commercial_knowledge_service.py`
- `tests/test_commercial_product_service.py`

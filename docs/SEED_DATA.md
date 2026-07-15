# Seed Data

## Purpose
Sprint C-04 introduces a deterministic, tenant-scoped seed data package for Commercial Catalog alpha validation.

The seed package is for development and validation only.
It is not production customer, vendor, or pricing data.

## Package Identity
- package_id: `atlas-c04-alpha-seed-v1`
- source marker: `seed_c04_alpha`
- import filename prefix: `c04_seed_`

Every seeded record includes explicit provenance markers.

## Included Seed Domains
- manufacturers
- vendors
- products
- services
- fees
- assemblies
- assembly components
- tax nexus rules and jurisdiction rates
- price sheets, versions, price records, and vendor offerings

## Dataset Coverage
C-04 seed package minimums:
- 5 manufacturers
- 3 vendors
- 25 products
- 10 services
- 5 fees
- 5 assemblies

Additional coverage:
- active, discontinued, and archived records
- taxable and non-taxable records
- MSRP/MAP/cost/default sales examples
- multiple vendor offerings via seeded price-sheet imports
- California nexus examples with city-level rates and effective dates

## Supported Seed Import Formats
The package provides representative imports for:
- CSV
- XLSX
- PDF price list (inspection and deterministic import validation path)

Validation scenarios include:
- column mapping
- duplicate detection
- row diagnostics
- partial success
- rejected-row export
- immutable price-list versions
- source provenance

## Deterministic Operations
`CommercialCatalogSeedService` supports:
- load_seed_data
- is_seed_loaded
- seed_summary
- reset_seed_data
- validate_catalog_to_transaction_workflow

## Safety and Scope Controls
- seed actions are intended for development/admin use only
- seed operations are isolated by tenant provenance markers
- reset operation removes seed-marked records only
- non-seed tenant records are preserved

## UI Controls
C-04 seed actions are hidden unless explicitly enabled:
- environment variable: `ATLAS_ENABLE_SEED_DATA_ACTIONS=true`
- location: Settings -> Organization Settings -> Overview
- access: settings manage permission required

Available UI actions:
- Load Seed Data
- Validate Seed Flow
- Reset Seed Data

## Non-Goals
- no inventory implementation
- no live tax service
- no QuickBooks sync
- no new transaction families
- no roadmap expansion

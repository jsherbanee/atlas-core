# Commercial Catalog

## Scope
Sprint C-03 introduces a tenant-scoped commercial catalog foundation that supports Product, Service, Fee, and Assembly item types with deterministic pricing/tax behavior and import provenance.

Knowledge workspace note:
- Catalog is the visible Knowledge secondary section for Products, Services, Fees, and Assemblies.
- Assemblies remain catalog items and are not a standalone Knowledge secondary route.
- Catalog import and activity surfaces preserve CSV, XLSX, PDF, provenance, diagnostics, and immutable version history without moving assembly logic into Transactions.

## Catalog Item Model
Catalog items include:
- stable catalog ID and code
- name, description, long description
- type, unit of measure, category/family/status
- manufacturer/vendor references
- taxability, tax category, default tax nexus
- cost/MSRP/MAP/default sales/manual unit pricing
- notes, tags, provenance, and archive/restore lifecycle

## Assembly Lifecycle
Assemblies are first-class catalog items with immutable versions:
- assembly version numbering (`assembly-vN`)
- deterministic component ordering by sequence and component ID
- required/optional components
- nested assembly expansion
- circular-reference prevention
- rollups for total cost and total sales price
- snapshot metadata preserved on document insertion

## Pricing Defaults
Organization-level pricing defaults support:
- default policy
- default markup/margin/multiplier
- default tax nexus
- default currency
- rounding policy

Manual unit price always overrides policy-generated pricing.

## Tax Nexus Behavior
Line tax quoting supports:
- nexus + item-type filtering
- effective/expiration windows
- priority and compound-rule calculation
- exemption flags

## PDF Price List Import
C-03 adds deterministic PDF catalog import lifecycle:
- inspect source hash, malformed/encrypted detection
- OCR/extraction diagnostics via intake pipeline
- table-candidate selection and explicit header/mapping control
- preview with accepted/rejected rows and diagnostics
- partial-success finalization
- immutable import version snapshots and duplicate hash warning

## Transactions Integration
Catalog lines can be inserted into:
- Estimate
- Sales Order
- Return Order
- Credit Memo
- Customer Invoice

Assembly insertion modes:
- `expand`: component lines only
- `grouped`: priced parent + visible component lines with snapshot metadata

Estimate-entry workflow note:
- Transactions > Estimates > Add uses a dedicated estimate-creation workspace rather than a generic transaction form
- estimate details are captured with dropdown-driven customer/project/project-code controls
- estimate add flow intentionally excludes Vendor ID on tenant-facing estimate entry
- line insertion remains catalog-backed for Product, Service, Fee, and Assembly item types

## C-04 Seed Catalog Import and Alpha Validation

Sprint C-04 adds a deterministic seed package and validation utility for alpha readiness.

Coverage:
- tenant-scoped non-production sample catalog data
- representative imports for CSV, XLSX, and PDF price list validation paths
- seeded manufacturers, vendors, products, services, fees, assemblies, component maps, tax rules, and price sheets
- deterministic load, duplicate suppression, seed-only reset, and provenance tracking

Workflow validation:
- estimate creation with product/service/fee/assembly lines
- estimate-to-sales-order conversion
- sales-order-linked customer invoice creation
- return-order processing and generated credit-memo traceability
- representative PDF generation for customer-facing commercial documents

See [SEED_DATA.md](SEED_DATA.md) for package identity, controls, and operational usage.

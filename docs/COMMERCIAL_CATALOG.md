# Commercial Catalog

## Scope
Sprint C-03 introduces a tenant-scoped commercial catalog foundation that supports Product, Service, Fee, and Assembly item types with deterministic pricing/tax behavior and import provenance.

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

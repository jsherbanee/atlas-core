# Price Versioning

## Philosophy
Price history must be permanent and reproducible.

Every import creates a new immutable Price Sheet Version.

No previous version is overwritten.

No previous Price Record is mutated.

## Import Model
Per import:

1. Parse and normalize rows.
2. Resolve Price Sheet identity.
3. Create new Price Sheet Version with source file hash.
4. Create immutable Price Records for each imported row.
5. Compare new version against previous active version.
6. Update active version pointer on the Price Sheet.
7. Emit Import History entry and Product Change Report.

## Immutability Guarantees
- Version IDs are unique per import.
- Price Record IDs are unique per version-row-product tuple.
- Previous version rows remain queryable for historical replay.
- Latest version is a pointer; history is append-only.

## Deterministic Comparison
Comparison key:

- product identity (manufacturer + model canonical key)

Change detection fields:

- cost
- description
- lead_time
- availability
- vendor_sku

Summary emits:

- products_added
- products_removed
- products_updated
- products_unchanged
- price_increased
- price_decreased
- description_changed
- lead_time_changed
- availability_changed
- vendor_sku_changed

## Product Change Report
Generated after each import:

- products added
- products removed
- price increases
- price decreases
- largest increase
- largest decrease
- products now missing
- products becoming stale
- products requiring review

## Freshness Interaction
Versioning and freshness are connected but distinct.

- Versioning controls historical permanence.
- Freshness evaluates recency of latest update per product.

A product can have rich history and still be stale when no recent version update exists.

## Future Integration
This model is designed to support future deterministic adapters for:

- estimating lookup and confidence weighting
- procurement workflows
- vendor quote ingestion
- historical bid reconstruction

These future workflows must consume immutable history and must not mutate prior version records.

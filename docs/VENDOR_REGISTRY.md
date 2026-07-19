# Vendor Registry

## Purpose
Vendor Registry defines vendor identity and commercial availability context for Atlas.

Vendors are entities the tenant buys from. They are not customers, manufacturers, or accounting vendors-of-record.

## Scope
Vendor Registry is intentionally:
- deterministic vendor reference data
- a Knowledge workspace entity family
- the contextual owner for vendor price-list visibility
- the source context for Vendor Offerings and purchasing-channel metadata

Vendor Registry is not:
- procurement execution
- purchase ordering
- inventory receiving
- accounting sync ownership
- CRM

## Knowledge Workspace Use
The visible Knowledge secondary navigation includes Vendors.

Vendor workspace tertiary actions include Browse, Add, Details, Contacts, Addresses, Price Lists, Products, Transactions, Activity, and Archive.

Price Lists are reached through Vendors, not Manufacturers, while manufacturer identity may still appear on individual price-list and product records.

## Compatibility
Existing Vendor entities, Vendor Offerings, Contact entities, Location entities, price-list imports, provenance, diagnostics, and Universal Object adapters remain compatible.

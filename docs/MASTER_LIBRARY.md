# Master Library

## Purpose
Master Library is the canonical engineering catalog for Atlas products and systems.

Master Library is not procurement, inventory, or ERP. It provides deterministic product identity and traceable engineering relationships used by Atlas intelligence and workspace review flows.

## Audience
- Platform architects
- Data model contributors
- Engineering-intelligence contributors

## When to Reference
- When designing reusable reference datasets.
- When planning manufacturer/product normalization patterns.
- When defining shared standards and system-template references.

## Scope (Current)
Atlas Preview 0.6 implements the Master Library foundation:

- Canonical product model
- Deterministic alias resolution
- Deterministic product matching
- Deterministic product-resolution candidate generation (engineering to estimate bridge)
- Workspace explorer integration for engineering review

K-02 operational alignment:
- Product lifecycle and state updates now synchronize with framework-backed knowledge entities so Master Library product behavior remains consistent with application-wide Knowledge workflows.

Excluded from scope:

- Purchasing workflows
- Pricing catalogs
- Inventory management
- Vendor catalog synchronization
- Cloud synchronization

## C-03 Boundary Clarification

Sprint C-03 introduces a separate Commercial Catalog surface for transactional pricing/tax/import and assembly sales composition behavior. Master Library remains the canonical engineering reference model and does not absorb transactional commercial ownership.

Cross-reference:
- [COMMERCIAL_CATALOG.md](COMMERCIAL_CATALOG.md)
- [COMMERCIAL_KNOWLEDGE.md](COMMERCIAL_KNOWLEDGE.md)

## Architecture

### Domain
- `atlas_core/domain/master_library.py`

Key entities:

- `MasterProduct`
- `ProductCategory`
- `ProductFamily`
- `ManufacturerReference`
- `ProductAlias`
- `ProductStatus`
- `EngineeringAttributes`
- `ProductRelationship`

### Services
- `atlas_core/services/master_library/repository.py`
- `atlas_core/services/master_library/resolver.py`
- `atlas_core/services/master_library/matcher.py`
- `atlas_core/services/master_library/service.py`

Service components:

- `MasterLibraryRepository`
- `AliasResolver`
- `ProductMatcher`
- `LibraryResolver`
- `MasterLibraryService`

### Workspace Integration
- `apps/phase2_review_app.py` includes `Master Library Explorer` with:
	- Search
	- Filters
	- Category browser
	- Manufacturer browser
	- Relationship browser
	- Alias-resolution trace panel

## Canonical Product Model

Every canonical product includes:

- manufacturer
- model
- normalized_model
- description
- category
- family
- status
- aliases
- engineering_attributes
- related_products
- confidence
- created_at
- updated_at

## Product Status

Supported product lifecycle states:

- Active
- Legacy
- Discontinued
- Unknown
- Planned

## Product Categories

Current category model includes:

- Loudspeaker
- Amplifier
- DSP
- Microphone
- Camera
- Projector
- Display
- LED
- Rack
- Control Processor
- Touch Panel
- Network Switch
- AV over IP
- Cable
- Connector
- Accessory
- Mount
- Furniture
- Other

## Alias Resolution

Alias resolution is deterministic:

- Alias strings are normalized with case-insensitive alphanumeric canonicalization.
- Exact manufacturer + normalized-model matches are preferred.
- Alias lookup fallback is supported with deterministic scoring and trace output.
- Aliases are preserved and never discarded to maintain auditability.

Examples supported by this model include variants such as:

- QSC / Q-SYS / QSYS
- Shure ULXD4Q / ULX-D4Q

## Future Manufacturer Registry Integration

Master Library is the foundational product identity layer for planned manufacturer registry expansion.

Planned integration direction:

- Link `MasterProduct.manufacturer` identities to canonical manufacturer registry records.
- Unify manufacturer alias mappings between registry and master-library resolvers.
- Preserve deterministic match traceability when registry-backed references are introduced.

## Future Capability Direction
- Manufacturer and vendor normalization references
- Product and equipment canonical mapping
- Commercial knowledge linkage to immutable price-sheet versions
- Standards and code reference indexing
- Reusable system-template knowledge
- Shared mappings used by drawing/specification/coordination intelligence

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [ROADMAP.md](ROADMAP.md)
- [PRODUCT_RESOLUTION.md](PRODUCT_RESOLUTION.md)
- [MANUFACTURER_REGISTRY.md](MANUFACTURER_REGISTRY.md)
- [COMMERCIAL_KNOWLEDGE.md](COMMERCIAL_KNOWLEDGE.md)
- [PRICE_VERSIONING.md](PRICE_VERSIONING.md)

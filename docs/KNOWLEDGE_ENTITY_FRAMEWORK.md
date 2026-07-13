# Knowledge Entity Framework

## Purpose
The Knowledge Entity Framework provides a deterministic, reusable entity layer for shared Atlas knowledge records.

It is the common foundation for customer, service, manufacturer, vendor, product, contact, location, and project knowledge objects used by the Knowledge workspace and search/indexing flows.

## Scope

Implemented in K-01:
- typed entity model (`customer`, `service`, `manufacturer`, `vendor`, `product`)
- deterministic duplicate detection by entity type and normalized canonical name
- deterministic relationship model with stable relationship IDs
- import/export bundle support for entities, relationships, and audit history
- compatibility synchronization from existing commercial create workflows

Implemented in K-02:
- operational lifecycle workflows for core entities (create, update, archive, restore)
- public service APIs for customer/service entity retrieval, search, and activation control
- entity-level summary metrics (counts by type, activity state, relationship totals)
- product lifecycle synchronization into framework-managed product entities
- Knowledge page operational controls for customer/service create and archive/restore

Implemented in K-03:
- reusable contact, location, and project entity support
- typed search/import/export for contact, location, and project records
- explicit relationship support for project-linked knowledge entities
- Knowledge page operational controls for contact, location, and project workflows

Out of scope:
- procurement execution and purchase-order workflows
- service ticketing and installed-asset lifecycle management
- sell-pricing/quoting workflows
- non-deterministic enrichment and autonomous AI graph mutation
- cloud persistence and authentication changes

## Data Model

### Entity
- `entity_id`: stable typed identifier (`type:id`)
- `entity_type`: one of the supported framework types
- `canonical_name`: deterministic canonical label
- `display_name`: UI-facing label
- `normalized_name`: normalized canonical-name key for duplicate checks
- `aliases`: alternate deterministic lookup terms
- `active`: lifecycle state (`true`/`false`)
- `notes`: operator notes
- `attributes`: typed extension payload
- `created_at`, `updated_at`: ISO timestamps

### Relationship
- `relationship_id`: deterministic ID from source + target + relationship type
- `source_entity_id`, `target_entity_id`
- `relationship_type`
- `confidence` (bounded 0.0..1.0)
- `evidence_refs`
- `notes`
- `created_at`, `updated_at`

### Audit Event
- `event_id`
- `event_type`
- `entity_id`
- `timestamp`
- `payload`

## Service Surface
Primary implementation: `atlas_core/services/master_library/commercial_product_service.py`.

Core APIs:
- create/get/update/list/search for customer/service entities
- create/update/list for manufacturer/vendor/product entities (compatibility-synced)
- archive/restore via entity activation toggles
- deterministic relationship upsert/list
- bundle export/import
- summary metrics via `knowledge_entity_summary`

## Backward Compatibility
- Existing manufacturer, vendor, and product commercial APIs remain the source of truth for commercial creation and still upsert into the framework.
- Existing serialized local state remains compatible via normalization defaults.

## UI Integration
The Knowledge workspace now supports:
- customer create/list/archive/restore
- service create/list/archive/restore
- existing manufacturer/vendor/product operational workflows
- global search object references for customer/service entity records
- reusable Knowledge secondary and tertiary navigation state for deterministic search handoff and future workspace reuse

X-12 navigation note:
- Knowledge is the first workspace to use the reusable three-level navigation contract while preserving the existing entity workflows and deterministic state model.

W-03 object-workspace note:
- framework-managed Customer, Vendor, Manufacturer, Product, Service, Contact, Location, and Project entities now support shared Object Workspace rendering
- entity create/edit/archive/import/export authority remains in existing Knowledge workflows and services
- search and Working Set opens for supported entities route through Object Workspace while preserving return-context continuity

## Validation
K-03 validation baseline:
- focused tests: `tests/test_knowledge_entity_framework.py`
- app/search regression: `tests/test_phase2_global_search_working_set.py`
- quality gates remain `black`, `ruff`, `mypy`, `pytest`
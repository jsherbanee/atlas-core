# Universal Workspace Framework

## Purpose

The Universal Workspace Framework defines the shared presentation layer used by Atlas workspace surfaces. It does not introduce new business rules. Instead, it standardizes page headers, object summaries, tables, empty states, and action bars so entity, project, transaction, report, and settings pages feel like one system.

## What It Covers

The framework currently provides shared helpers for:

- page headers and section titles
- data tables and object summaries
- empty states and guided empty states
- workspace context banners
- notice panels and status badges
- metric cards and object action bars

The canonical implementation lives in [atlas_core/ui/workspace_framework.py](../atlas_core/ui/workspace_framework.py).

## Design Goals

- Keep business logic inside the authoritative service layer.
- Keep shell composition thin and reusable.
- Preserve current routes, search behavior, Working Set continuity, and return-context behavior.
- Make workspace migrations incremental so existing pages can adopt the shared grammar without a rewrite.

## Migration Order

Use the framework when migrating or adding surfaces in this order:

1. Page framing and workspace context.
2. Object header and summary.
3. Browse/list presentation.
4. Inspector and action bar.
5. Empty-state and guided-empty-state handling.

This order keeps navigation and object selection stable while allowing presentation details to converge.

Projects and Transactions are the active migration targets using this order; both keep their service-layer behavior intact while converging on the shared shell grammar.

PX-04 extends the same migration order to Knowledge. Knowledge browse/list
surfaces remain service-backed, while selected records render through a shared
operational workbench structure:

1. Business Summary
2. Operational Health
3. Current Relationships
4. Recent Activity
5. Recommended Next Step
6. Supporting Details

Supporting Details is the home for edit/archive/import/export/admin mechanics
and is collapsed by default.

PX-04A adds an action-availability expectation for migrated surfaces: every
visible primary action must complete, navigate, open a usable workflow, or be
disabled with a clear business-language reason. Framework adopters should
preserve success, validation, cancel, and disabled-action feedback across
Streamlit reruns instead of relying on silent session-state changes.

## Compatibility Boundaries

The framework intentionally stays below the business-domain layer. It should not:

- create or mutate domain objects on its own
- duplicate service rules for customers, vendors, manufacturers, products, fees, or assemblies
- replace navigation state management
- bypass tenant, organization, or audit controls

Use domain services for data changes, and use the framework only to render them consistently.

PX-04 Knowledge adapters may normalize existing Customer, Vendor,
Manufacturer, Product, Service, Fee, and Assembly data into presentation
contracts. They must not create new commercial rules, new pricing calculations,
or independent health state.

## Related Documents

- [NAVIGATION_ARCHITECTURE.md](NAVIGATION_ARCHITECTURE.md)
- [OBJECT_WORKSPACE.md](OBJECT_WORKSPACE.md)
- [KNOWLEDGE_ENTITY_FRAMEWORK.md](KNOWLEDGE_ENTITY_FRAMEWORK.md)

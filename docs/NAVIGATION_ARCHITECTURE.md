# Navigation Architecture

## Purpose

Atlas navigation is deterministic, stateful, and workspace-aware.

This document defines the reusable navigation contract used by the shell and workspace surfaces.

## Navigation Levels

- Primary navigation: top-level application and workspace entry points
- Secondary navigation: grouped workspace sections or feature families
- Tertiary navigation: sub-sections, views, or object-focused panels within a selected secondary area

## Contract Principles

- Navigation state must be explicit in `session_state`
- Navigation selection should be reusable across workspaces, not hard-coded to one page
- Search handoff should restore the appropriate navigation context when opening a result
- Breadcrumbs should reflect the active workspace and selection context
- Disabled or future sections should remain visible only when they are intentionally part of the contract
- Primary navigation must stay within the current browser window and preserve session state
- Explicit browser routes may carry both `atlas_page` and `atlas_workspace_id`;
  the workspace id is accepted only when it resolves to an existing tenant-visible
  project workspace

## Current Implementation Notes

- The application shell still uses header-based primary navigation
- The shared shell uses one horizontal header row for Atlas, Transactions, Projects, Knowledge, Reports, Settings, and Search with fixed-width buttons and same-window callback routing
- At compact widths, primary buttons compress into a controlled overflow pattern rather than behaving like browser hyperlinks
- Knowledge is the first workspace using the reusable secondary/tertiary navigation framework
- Knowledge search results restore the active secondary group and tertiary page selection context
- The framework is intended to be extended to additional workspaces without changing the contract shape
- Shared workspace headers and object summaries are now factored into the reusable Universal Workspace Framework so page shells can reuse the same navigation and presentation grammar
- Application-level routes such as Mission Control render their content even when
  the active primary workspace has no secondary accordion sections
- Project workspace opens persist `atlas_workspace_id` alongside `atlas_page` so
  browser refreshes and validation links can restore the selected project context
- Project workspace opens use a lightweight bootstrap contract and must not
  synchronously hydrate full document/review context, process background jobs,
  or rebuild repository manifests before the route is visible
- Project Overview, Documents, and Processing remain lightweight-safe browser
  routes; full review, evidence, engineering, relationship, and commercial
  detail hydration belongs behind the pages that explicitly require it
- Project Operations Center secondary panels log contained section failures with
  searchable error references while preserving the rest of the active route
- Explicit URL page state continues to win after workspace-state restoration;
  project-open callbacks avoid duplicate reruns when the requested route is
  already active

## Transactions Navigation Direction

Sprint A-07 defines the future Transactions workspace navigation contract.

Primary navigation target model:
- Atlas
- Transactions
- Projects
- Knowledge
- Reports
- Settings
- Search

Transactions secondary navigation should include:
- Estimates
- Sales Orders
- Return Orders
- Invoices
- Credit Memos
- Purchase Orders (Deferred)
- Vendor Quotes
- Receiving
- Vendor Bills

Transactions tertiary actions should remain action-oriented, for example:
- Add
- Browse
- Edit
- Approvals
- Related Transactions
- Receiving
- Billing
- Sync Status
- Activity
- Export

This sprint defines the contract only.

No routes or production navigation implementation are introduced here.

## Transactions Navigation Implementation (T-02)

Sprint T-02 implements the first production Transactions navigation surface.

Implemented behavior:
- Transactions added to top-level primary header navigation
- top-header primary navigation order is Atlas (Home), Transactions, Projects, Knowledge, Reports, Settings
- at narrower widths, header primary links compress predictably instead of wrapping to a second row
- Transactions workspace uses the shared secondary/tertiary navigation contract model
- active secondary sections: Estimates, Sales Orders, Return Orders, Invoices, Credit Memos
- deferred secondary sections (visible but disabled/deferred): Purchase Orders, Vendor Quotes, Receiving, Vendor Bills
- Change Orders are not a standalone secondary route; change-order behavior is represented as a convention on Sales Orders and Return Orders
- tertiary actions are compact and context-driven, with record-required actions hidden until a draft/record context exists
- navigation continuity/state persistence uses existing shell state keys and workspace-state snapshot behavior
- Estimates `Add` uses a dedicated creation workspace with customer/project/project-code selection and catalog-backed line insertion for Product/Service/Fee/Assembly item types

## Settings Navigation Implementation (T-04)

Sprint T-04 introduces the first reusable Settings workspace navigation contract.

Implemented behavior:
- Settings remains the public label while internal routing continues to use `Administration`
- secondary settings groups: Organization Settings, Personal Preferences, Integrations, Security, Billing, Advanced
- tertiary settings pages are contract-driven per selected settings group
- active content is limited to Organization Settings, Personal Preferences, and authorized Platform Management surfaces
- Integrations, Security, Billing, and Advanced remain visible but disabled/deferred for controlled alpha clarity

W-03 implementation note:
- Object Workspace is now a shared route that owns object-level tertiary navigation for migrated object families
- object tertiary navigation is contract-driven and limited to supported views (Summary, Details, Relationships, Activity, Documents, History)
- context banner rendering and one-click return behavior in Object Workspace are driven by existing W-01 return-context state
- unsupported object families continue to route to legacy authoritative pages to preserve behavior compatibility

W-01 implementation note:
- navigation continuity now carries explicit context state for active workspace, active secondary/tertiary selection, active project, selected project object, selected Knowledge entity, bounded return context, and bounded navigation history
- return context is deterministic and one-click, not inferred from browser history
- the shared shell now owns visible breadcrumb and return affordances for cross-workspace movement
- Knowledge handoff now derives the correct secondary entity section and action row from the selected Knowledge entity context rather than falling back to overview

## Validation

- Search result opening preserves Knowledge navigation context
- Knowledge navigation defaults are deterministic
- Knowledge entity links resolve same-window into the functional Vendor, Manufacturer, Product, and Service workspaces
- shell-level breadcrumb suppression avoids redundant `Atlas / <workspace>` labels while preserving object-level continuity breadcrumbs
- migrated object opens preserve object-level navigation context inside Object Workspace
- context banner and return behavior remain deterministic across search and Working Set handoff paths
- primary navigation buttons preserve same-window session state and do not open new tabs or windows
- transaction deferred-route visibility and standalone Change Order removal are regression-covered
- settings deferred-section disable behavior and platform-diagnostic scoping are regression-covered
- The implementation is covered by app-level regression tests and full-suite validation

## Controlled Exclusive Accordion Navigation

The shared workspace shell presents secondary and tertiary navigation as a
controlled left-column accordion.

Implemented behavior:
- primary header navigation remains unchanged
- the accordion is an application-shell capability and is not owned by Knowledge or any individual page
- Projects, active Project workspaces, Transactions, Knowledge, Reports, and Settings use the same first-column disclosure renderer
- page-specific accordion implementations are prohibited for first-column navigation
- the selected secondary section is the single expanded section in the left column
- opening one secondary section closes the previously expanded section in the same workspace
- clicking the active secondary section collapses it, clears the active tertiary action, and does not open another section
- compact indented tertiary actions render directly beneath the active section and do not collapse their parent
- inactive secondary sections remain collapsed on rerender
- section headers use the shared controlled chevron/header treatment rather than native Streamlit expander state
- secondary and tertiary labels render as compact navigation text without literal disclosure markers
- the separate tertiary action row above main content is removed
- stale secondary selections are reset to the current workspace contract when switching primary workspaces
- search and return-context handoff continue using the existing primary/secondary/tertiary session-state keys
- the first-column accordion does not use independent widget-owned open booleans
- native expanders remain allowed only for record-content disclosures, not workspace navigation

## Knowledge Consolidation

Knowledge visible secondary navigation is now:
- Customers
- Vendors
- Manufacturers
- Catalog

Contacts, Locations, Price Lists, Imports, and Assemblies are removed from visible secondary navigation while their data remains reachable through contextual tertiary actions, vendor price-list surfaces, catalog import/provenance/activity, and Universal Object handoff.

Knowledge repair note:
- Knowledge keeps one expanded secondary section at a time: Customers, Vendors, Manufacturers, or Catalog
- record-specific tertiary links stay contextual and only become useful once the related record is selected
- Customer Browse defaults to Customer Name ascending, uses one compact Customer selector as the primary selection mechanism, and keeps the full table behind Browse All
- Customer Add uses a single Customer Name field with non-consuming Customer ID preview and consuming allocation on create
- normal tenant-facing Knowledge surfaces avoid JSON controls; CSV export remains available in contextual/advanced areas

## Transactions Workbench Routing

PX-03 keeps Transactions inside the shared primary/secondary/tertiary
workspace contract and adds browser-visible selected-document state.

Supported query parameters:
- `atlas_page=Transactions`
- `atlas_transaction_family`
- `atlas_transaction_action`
- `atlas_transaction_id`

`atlas_transaction_family` maps to the active commercial family:
- `estimates`
- `sales_orders`
- `return_orders`
- `customer_invoices`
- `credit_memos`

`atlas_transaction_action` maps to the active tertiary action for the selected
family. `atlas_transaction_id` selects the commercial document when the
document exists in the current tenant transaction service state.

Explicit URL state wins after workspace-state restoration so refreshed,
shared, or browser-authored Transactions links can reopen the intended family,
action, and selected document without breaking the shared return-context model.

## Knowledge Workbench Routing

PX-04 preserves the existing Knowledge secondary/tertiary navigation contract
and adds browser-visible selected-record state for Knowledge validation and
direct links.

Supported query parameters:
- `atlas_page=Knowledge`
- `atlas_knowledge_family`
- `atlas_knowledge_record`

`atlas_knowledge_family` maps to:
- `customers`
- `vendors`
- `manufacturers`
- `products`
- `services`
- `fees`
- `assemblies`
- `catalog`

Explicit URL family state updates the shared secondary/tertiary navigation
keys. `atlas_knowledge_record` selects a matching row when that record exists
in the current tenant-visible Knowledge state. URL state does not create,
seed, or mutate Knowledge records.

## Projects Action Routing

PX-04A stabilizes Projects secondary actions so visible create/import actions
resolve to their intended workflow surfaces instead of being shadowed by the
default Projects list route.

Supported project action routes:
- `atlas_page=Projects` opens the tenant project list.
- `atlas_page=Create New Project` opens the project creation workflow.
- `atlas_page=Import Project` opens the supported project import workflow.

Create and import actions update the same primary page state used by normal
navigation, preserve browser-visible `atlas_page` where available, and return
to the Projects list through the shared project-library state keys. Successful
project opens continue to persist both `atlas_workspace_id` and `atlas_page`.
Explicit URL page state remains authoritative after workspace-state
restoration.

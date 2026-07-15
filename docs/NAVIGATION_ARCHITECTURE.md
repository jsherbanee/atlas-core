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

## Current Implementation Notes

- The application shell still uses header-based primary navigation
- Knowledge is the first workspace using the reusable secondary/tertiary navigation framework
- Knowledge search results restore the active secondary group and tertiary page selection context
- The framework is intended to be extended to additional workspaces without changing the contract shape

## Transactions Navigation Direction

Sprint A-07 defines the future Transactions workspace navigation contract.

Primary navigation target model:
- Atlas
- Transactions
- Projects
- Knowledge
- Reports
- Search
- Settings

Transactions secondary navigation should include:
- Overview
- Estimates
- Proposals
- Sales Orders
- Purchase Orders
- RFQs
- Vendor Quotes
- Receiving
- Vendor Bills
- Customer Invoices
- Change Orders

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
- top-header primary navigation order is Atlas (Home), Transactions, Projects, Knowledge, Reports
- Transactions workspace uses the shared secondary/tertiary navigation contract model
- active secondary sections: Overview, Estimates, Sales Orders, Return Orders, Credit Memos, Customer Invoices
- deferred secondary sections (visible but disabled/deferred): Purchase Orders, RFQs, Vendor Quotes, Receiving, Vendor Bills
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
- migrated object opens preserve object-level navigation context inside Object Workspace
- context banner and return behavior remain deterministic across search and Working Set handoff paths
- transaction deferred-route visibility and standalone Change Order removal are regression-covered
- settings deferred-section disable behavior and platform-diagnostic scoping are regression-covered
- The implementation is covered by app-level regression tests and full-suite validation

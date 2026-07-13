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

W-01 implementation note:
- navigation continuity now carries explicit context state for active workspace, active secondary/tertiary selection, active project, selected project object, selected Knowledge entity, bounded return context, and bounded navigation history
- return context is deterministic and one-click, not inferred from browser history
- the shared shell now owns visible breadcrumb and return affordances for cross-workspace movement
- Knowledge handoff now derives the correct secondary entity section and action row from the selected Knowledge entity context rather than falling back to overview

## Validation

- Search result opening preserves Knowledge navigation context
- Knowledge navigation defaults are deterministic
- The implementation is covered by app-level regression tests and full-suite validation

# Phase 2 Mission Control Redesign

Validation date: 2026-07-27
Baseline: `4a18d3b`

## Summary

Mission Control now renders as a tenant-wide operational dashboard instead of a project launcher.

The page now summarizes:

- Projects
- Transactions
- Knowledge

It also answers the operational questions that matter at a glance:

- what needs attention today
- what is at risk financially, on schedule, by resource, by scope, and by data quality
- what is due or active this week
- which projects are open
- which purchase-order views still remain a future placeholder
- what recent activity occurred across project, transaction, and knowledge sources

## What Changed

- Removed the launcher-era controls:
  - `Create New Project`
  - `Open Existing Project`
  - `Manage Projects`
- Removed the old home-page KPI strip items:
  - `Continue Working`
  - `Active Projects`
  - `Pending Reviews`
  - `Recent Activity`
- Removed the `Continue active review` and `Continue Working` Mission Control emphasis.
- Added a compact dashboard layout with:
  - Tenant Header
  - Company Snapshot
  - Business Risks
  - This Week
  - Open Projects
  - Open Purchase Orders
  - Recent Activity

## Dashboard Contract

### Tenant Header

The page header remains the top-level entry point and identifies the tenant operations surface.

### Company Snapshot

The snapshot now uses backed metrics only:

- active projects
- open purchase orders
- pending approvals
- pricing coverage
- commercial confidence
- recent activity items
- projects in estimating
- setup incomplete

### Business Risks

Risks are grouped into the required operational categories:

- Financial
- Schedule
- Resource
- Scope
- Data Quality

Each row is actionable and can route to the appropriate next surface.

### This Week

This section is a polished placeholder when no real dated commitments are surfaced.

When dated evidence exists, it fills with those rows instead of fabricated work.

### Open Projects

Open projects now appear as compact row cards with:

- open project
- open risks
- open workflow

### Open Purchase Orders

This section remains a future placeholder. It now shows truthful summary metrics and a clear next action into Transactions.

### Recent Activity

Recent activity now classifies source context as:

- Project
- Transaction
- Knowledge

It also uses readable local timestamps instead of generic workspace labels.

## Validation Notes

- The page no longer presents itself as a project creation launcher.
- The layout is materially denser and more operational.
- The dashboard stays truthful when the tenant has no dated commitments or no open projects.
- The implementation avoids inventing new business facts.

## Remaining Future Placeholders

- Rich purchase-order detail surfaces
- More complete dated commitment tracking
- Additional transaction-level drill-down from Mission Control


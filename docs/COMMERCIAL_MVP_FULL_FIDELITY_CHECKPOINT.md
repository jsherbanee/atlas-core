# Commercial MVP Full-Fidelity Checkpoint

## Purpose
MVP-CHK-01 validates the current Commercial MVP end to end and records whether the product path is coherent before additional workflow slices are expanded.

## What Was Validated
- Customer/account creation.
- Opportunity creation and customer linkage.
- Estimate creation, line-item add/remove, and subtotal calculation.
- Proposal create, ready, send, and accept transitions.
- Accepted-estimate-to-sales-order conversion.
- Inventory availability and reservation against the sales-order path.
- Customer invoice generation from a sales order.
- Vendor bill creation.
- QuickBooks sync-pending readiness for invoices and vendor bills.
- Tenant-scoped reporting snapshots.
- Tenant isolation with a second tenant using the same record identifiers.

## What Works End To End Today
- The boundary-to-facade-to-service path supports the core commercial workflow inside one tenant.
- Proposal acceptance produces a draft sales order that can drive inventory availability and reservation.
- Customer invoices and vendor bills carry QuickBooks sync metadata and surface in reporting snapshots.
- The reporting read models summarize the workflow deterministically from the tenant-scoped commercial store.
- The current tree is validated by `black --check`, `ruff check`, the full commercial checkpoint test, the existing Commercial Workspace UI tests, the relevant Phase 2 navigation regressions, full `pytest`, and a repo-wide `mypy` comparison with no new diagnostics versus `origin/main`.

## What Is Thin Or Still Manual
- Inventory reservation is readiness-oriented and does not expand into warehouse execution.
- Customer invoice and vendor bill generation are operational records, not PDF or payment workflows.
- UI presentation remains intentionally compact and text-first.
- The commercial header now includes `Commercial` as a primary navigation item; this is reflected in the validated Phase 2 navigation contract.

## Medium/High-Priority Fixes Completed In This Slice
- Fixed the Commercial Workspace selector path so customer and opportunity creation use the correct row keys.
- Hardened the checkpoint and UI test fixtures so they remain deterministic under mypy and the facade/boundary contract.
- Restored Phase 2 commercial navigation compatibility while preserving the new Commercial Workspace entry point.

## Remaining Medium/High-Priority Gaps
- None identified in this checkpoint.

## Low-Priority Follow-Ups
- Refresh any stale next-slice notes in the earlier UI docs if future workflow slices change again.
- Consider a small UI smoke test that renders the commercial workspace with the real service bundle when a lightweight harness is available.
- Keep the Phase 2 navigation expectations aligned with the primary commercial header if that shell continues to evolve.

## Recommendation
Proceed to UI-03 Inventory and Invoice Workflow. No medium/high-priority blockers remain in the validated commercial path, and the current tree passes the required validation stack.

## Entry Point
The validated path runs through [apps/phase2_review_app.py](../apps/phase2_review_app.py) and the APP-01, API-01, INV-01, FIN-01, QB-01, and REP-01 layers.

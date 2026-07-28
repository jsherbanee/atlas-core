# Phase 2 Completion Backlog

This backlog has been reconciled against the current rendered product on 2026-07-27.
Only unfinished committed Phase 2 work remains below.

## Reconciled Status Summary

Resolved and removed from the backlog:

- blank or skeleton-only primary routes
- stray `documents` project contamination
- selected-project defaulting to the wrong project
- visually concatenated route labels and repeated action clusters
- the major whitespace and density complaints called out in the P1 validation passes

Still open:

- estimate decision actions are not yet exposed as a complete end-state workflow in the live UI
- major tables and work queues still need stronger drill-down, selection persistence, and evidence/history access
- some narrow-width table surfaces remain more compressed than ideal

## Remaining Committed Work

| ID | Title | Category | Severity | Affected Route or Workflow | Original Source | Current Evidence | Expected Behavior | Current Behavior | Recommended Correction | Estimated Effort | Dependency | Phase 2 Blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PH2-P1-001 | Expose the complete estimate decision workflow in the rendered UI | Workflow gap | P1 | Estimate, Transactions, bid-review journey | `PHASE2_P1_BID_ESTIMATE_JOURNEY.md`, `PHASE2_USER_JOURNEY_GAPS.md` | `docs/validation/screenshots/phase2/closeout/1366/estimate.png` shows the bid-review state stack and `Decision Not Started`, but no direct accept / decline end-state controls are visible | Users should be able to complete the estimate decision path from the rendered workspace | The journey is visible, but the decision step is still a state card rather than a completed, directly actionable workflow | Add the missing decision controls or a clearly exposed end-state interaction that closes the review loop | Medium | Estimate state wiring and transaction handoff | Yes |
| PH2-P2-001 | Add stronger row-level drill-down and selection persistence for major tables | Interaction gap | P2 | Projects, Transactions, Knowledge, Reports | `PHASE2_P1_TABLE_INTERACTIONS.md`, `PHASE2_P1_INFORMATION_DENSITY.md` | `docs/validation/screenshots/phase2/closeout/1366/projects.png`, `transactions.png`, `knowledge.png`, and `reports.png` show visible tables, but most interactions still happen through surrounding buttons and expanders rather than row-first exploration | Important rows should support fast inspection, stable selection, and visible evidence / history access | The tables are usable, but they are still closer to navigation lists than true interactive work surfaces | Add row click targets, preserved expansion state, and more direct evidence / history affordances where committed | Medium | Shared table interaction primitives | No |
| PH2-P2-002 | Improve narrow-width column prioritization on project and work tables | UI polish | P2 | Projects and related list views at 820px | `PHASE2_P1_INFORMATION_DENSITY.md`, `PHASE2_P1_DENSITY_PLAYWRIGHT.md` | `docs/validation/screenshots/phase2/closeout/820/projects.png` shows the layout is stable, but several table columns are still compressed and less readable than the primary fields | Lower-value columns should collapse or de-prioritize before important fields lose readability | The view no longer breaks, but the column hierarchy could still be smarter at tablet width | Hide or de-emphasize low-value columns first and preserve the most useful project fields | Small | Responsive table layout | No |

## Notes

- The previous P0 findings are no longer present in the rendered product and should not be carried forward.
- The completed Phase 2 shell now covers the project journey surfaces, but the remaining work is interaction depth rather than route existence.
- Later-phase work such as procurement, sales-order conversion, and new intelligence features remains out of scope for this backlog.

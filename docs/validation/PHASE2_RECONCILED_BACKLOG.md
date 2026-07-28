# Phase 2 Reconciled Backlog

This is the de-duplicated list of unfinished committed Phase 2 work after the closeout review.

## Backlog

| ID | Title | Category | Severity | Affected Route or Workflow | Original Source | Current Evidence | Expected Behavior | Current Behavior | Recommended Correction | Estimated Effort | Dependency | Phase 2 Blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PH2-P1-001 | Expose the complete estimate decision workflow in the rendered UI | Workflow gap | P1 | Estimate, Transactions, bid-review journey | `PHASE2_P1_BID_ESTIMATE_JOURNEY.md`, `PHASE2_USER_JOURNEY_GAPS.md` | `docs/validation/screenshots/phase2/closeout/1366/estimate.png` | The estimate journey should end in a directly actionable accept / decline decision state | The journey is visible, but the decision step remains a state card rather than a complete decision surface | Add the missing decision controls or an explicit end-state interaction | Medium | Estimate state wiring and transaction handoff | Yes |
| PH2-P2-001 | Add stronger row-level drill-down and selection persistence for major tables | Interaction gap | P2 | Projects, Transactions, Knowledge, Reports | `PHASE2_P1_TABLE_INTERACTIONS.md`, `PHASE2_P1_INFORMATION_DENSITY.md` | `docs/validation/screenshots/phase2/closeout/1366/projects.png`, `transactions.png`, `knowledge.png`, `reports.png` | Core list surfaces should support quick row-first inspection and stable state | The list surfaces are usable, but they still depend on surrounding buttons and expanders for deeper inspection | Add row click targets, stable expansion, and stronger evidence / history access | Medium | Shared table interaction primitives | No |
| PH2-P2-002 | Improve narrow-width column prioritization on project and work tables | UI polish | P2 | Projects and related list views at `820px` | `PHASE2_P1_INFORMATION_DENSITY.md`, `PHASE2_P1_DENSITY_PLAYWRIGHT.md` | `docs/validation/screenshots/phase2/closeout/820/projects.png` | Low-value columns should collapse before important fields lose readability | The layout is stable, but some columns are still compressed at tablet width | Reorder or hide low-value columns sooner | Small | Responsive table layout | No |

## Reconciled Out-of-Scope Items

These were present in earlier notes but are not current Phase 2 backlog items:

- sales-order workflow
- purchase-order generation
- procurement management
- service lifecycle
- new engineering intelligence
- new extraction logic
- new pricing logic
- new tenant policy management
- new AI capabilities

## Notes

- P0 items from the initial review are resolved and no longer appear in the reconciled backlog.
- The current backlog is now dominated by interaction depth rather than route existence.

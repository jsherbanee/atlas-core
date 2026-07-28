# Phase 2 P1 - Visible Bid Review and Estimate Journey

Validation date: 2026-07-27
Project: `BID-2026-0002` - Music Academy of the West
Baseline: `43cf58d`

## Executive Summary

This sprint made the bid-review and estimate lifecycle visibly usable in the Atlas UI without adding new extraction, pricing, or procurement features.

The workflow is now exposed as a seven-step journey:

1. Documents Uploaded
2. Preliminary Review V1
3. User Guidance
4. Revised Review V2
5. Engineering Review
6. Draft Estimate
7. Estimate Decision

The journey panel is now rendered across the project, scope, engineering, estimate, and transaction surfaces so the user can move through the visible review sequence without losing context.

Recommendation: `Proceed to the next sprint`.

## Routes Changed

- Documents
- Processing
- Scope & Risk
- Engineering Review
- Estimate
- Transactions

## Journey States Made Visible

- `Documents` shows the review entry point and current project context.
- `Preliminary Review V1` is represented as the initial immutable review version.
- `User Guidance` is editable and captured before revision.
- `Revised Review V2` preserves parent linkage to the prior review version.
- `Engineering Review` continues the review chain and links back to the same project workspace.
- `Draft Estimate` is created from the review lineage and records the source report version.
- `Estimate Decision` records accepted / rejected state against the selected estimate document.

## V1 / V2 Behavior

- V1 is initialized as the preliminary review baseline.
- V1 remains the initial version when the project has no prior revision.
- V2 is created only through the validated revision transition path.
- V2 retains parent linkage to the originating review version.
- Report version selection stays project-scoped and deterministic.

## Estimate Behavior

- Draft estimate creation is reachable from the visible journey flow.
- The estimate workspace now shows the journey context directly on the page.
- Draft estimates retain traceability back to the selected review version.
- Accept / decline behavior is implemented through the transaction workflow and covered by tests.
- Return-to-review behavior is available after a declined estimate.

## Tests Added

- `tests/test_phase2_bid_review_journey.py`

Covered behaviors:

- V1 immutability
- V2 parent linkage
- report-version selection
- draft estimate traceability
- accept path
- decline path
- return-to-review path
- project continuity
- deterministic workflow state

## Quality Gates

- `git diff --check` - passed
- `black --check apps/phase2_review_app.py tests/test_phase2_bid_review_journey.py` - passed
- `ruff check apps/phase2_review_app.py tests/test_phase2_bid_review_journey.py` - passed
- `.venv/bin/python -m mypy .` - passed
- `.venv/bin/python -m pytest` - passed

## Final Test Count

- `1644 passed`

## Remaining Findings

- No new P1 or P2 regressions were introduced by this sprint.
- The broader Phase 2 backlog remains unchanged outside the bid-review journey scope.

## Recommendation

Proceed to the next sprint with the visible bid-review and estimate journey baseline in place.

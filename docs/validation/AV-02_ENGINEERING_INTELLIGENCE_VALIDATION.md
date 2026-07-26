# Atlas AV-02 - Engineering Intelligence Validation

Validation date: 2026-07-26
Project: `BID-2026-0002` - Music Academy of the West
Baseline: fresh rebuild from the live `documents/` tree with project metadata bound to `BID-2026-0002`
Reference commit: `08618e44abdd6fc54a72c886738652e7d6156c05`

## Executive Summary

The current MAW engineering-intelligence baseline is correctly scoped to `BID-2026-0002` after a fresh rebuild from the cleaned live source set. The rebuild no longer relies on the older cached `documents`-scoped artifacts.

The package is rich enough for engineering validation, but it is not ready for pricing or final coordination. The dominant blockers are unresolved drawing/spec alignment, unresolved scope responsibility, and a large volume of equipment items that still lack deterministic drawing references.

Current headline metrics:

- Live source documents: `7`
- Rooms/spaces detected: `0`
- Systems detected: `4`
- Equipment items detected: `626`
- Direct connectivity references: `49`
- Resolver relationships: `19`
- Scope findings: `19`
- Conflicts and gaps: `648`
- RFI candidates: `638`
- Readiness score: `0.39` (`not_ready`)

Recommendation: `Repeat AV-02 after fixes`.

## Dataset Confirmation

Fresh rebuild inputs:

- `drawings/07_Electrical for AV Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `drawings/08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `drawings/09_Theater Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `drawings/MAW_MBD-018_Aurora Element - Design Narrative FINAL.pdf`
- `reports/2025.12.15 MAW 100DD Acoustics Narrative by Kirkegaard.pdf`
- `schedules/Div 11 Equipment.pdf`
- `specifications/Div 27 Communications.pdf`

The validation reran the review from the clean live source tree so the results reflect the current MAW package rather than the older cached `documents` artifact set.

## Intake Statistics

- Drawings discovered: `4`
- Reports discovered: `1`
- Schedules discovered: `1`
- Specifications discovered: `1`
- Addenda discovered: `0`
- Images discovered: `0`
- Unsupported files discovered: `0`
- Drawing sheets extracted: `133`
- Specification sections extracted: `309`
- Device schedule / equipment items detected: `626`
- Direct cross-reference links: `49`
- Resolver relationships: `19`

## Readiness Scorecard

Overall readiness score: `0.39`

Readiness level: `not_ready`

Blocking issues:

- Major drawing/specification alignment gaps remain unresolved.
- Scope responsibility is unresolved across key bid package items.

Warnings:

- High estimator risks require estimator review.
- High-priority recommendations require estimator review.
- Labor estimate confidence is below preferred threshold.
- Missing or ambiguous scope evidence was detected.
- RFI candidate risk profile reduces bid readiness.
- Review confidence is below `0.75`.
- Scope gaps require estimator review.

Category scores:

| Category | Score |
| --- | --- |
| `equipment_completeness` | `0.40` |
| `quantity_confidence` | `1.00` |
| `scope_responsibility_clarity` | `0.40` |
| `drawing_spec_alignment` | `0.00` |
| `assumptions_quality` | `0.50` |
| `rfi_candidate_risk` | `0.00` |
| `labor_estimate_confidence` | `0.05` |
| `revision_stability` | `1.00` |

## Engineering Health

The fresh review is still useful for engineering analysis even though it is not ready for pricing.

Fresh system coverage:

- `detected-audio`: Audio System (audio, confidence 0.75, equipment 0)
- `detected-control`: Control System (control, confidence 0.75, equipment 0)
- `detected-lighting`: Theatrical Lighting System (lighting, confidence 0.75, equipment 0)
- `detected-drapery`: Drapery System (drapery, confidence 0.75, equipment 0)

Equipment category mix:

- `unknown`: `580`
- `drapery`: `19`
- `rack`: `18`
- `lighting_fixture`: `2`
- `lighting_console`: `2`
- `display`: `2`
- `control_processor`: `1`
- `microphone`: `1`
- `projector`: `1`

RFI category mix:

- `missing_information`: `625`
- `add_alternate_clarification`: `7`
- `drawing_spec_mismatch`: `5`
- `responsibility_gap`: `1`

## Scope Distinction

The fresh rebuild identifies equal-weight primary engineering disciplines in the live package: audio, control, and theatrical lighting. Drapery is also detected and is driving most of the current scope-review burden.

Architectural-lighting-only content remains visible as secondary evidence where it appears, but it does not override the primary AV / control / theatrical-lighting scope in the current review.

## System Inventory

The four detected systems are the right place to start the next cleanup pass:

- Audio System
- Control System
- Theatrical Lighting System
- Drapery System

No rooms or spaces were detected, so the current package does not yet support room-by-room coordination.

## Equipment Evidence

The equipment set is broad, but most items are still undetermined or allowance-based.

Key observations:

- Total equipment items: `626`
- Unknown-category items: `580`
- Drapery items: `19`
- Rack items: `18`
- Lighting fixtures: `2`
- Lighting consoles: `2`
- Displays: `2`

That distribution explains why the review is still heavily dependent on manual reconciliation despite the good cross-reference density.

## Connectivity Evidence

The package has `49` direct cross-reference links.

That is enough to show the system is finding coordination, but not enough to overcome the unresolved drawing/spec gaps.

## Relationships

The resolver produced `19` live relationship actions. The dominant pattern is drapery scope being marked for review because track, hardware, support, and site conditions still need human confirmation.

## Scope Findings

The scope-finding report contains `19` items, all of which are current and explainable.

The strongest signal is the drapery review rule (`RULE-004`), repeated across multiple items with the same underlying concern: the scope exists, but the ownership and supporting details need review.

## Conflicts and Gaps

The combined conflict/gap export contains `648` rows:

- `21` scope gaps
- `615` reconciliation issues
- `3` estimator risks
- `2` readiness blockers
- `7` readiness warnings

The big picture is consistent across those rows: equipment lacks drawing references, scope responsibility is still fuzzy, and the package is not yet stable enough for pricing.

## RFI Candidates

The fresh review identified `638` RFI candidates.

Category mix:

- `missing_information`: `625`
- `add_alternate_clarification`: `7`
- `drawing_spec_mismatch`: `5`
- `responsibility_gap`: `1`

## Top 10 Findings

1. The review is now correctly project-scoped to `BID-2026-0002`, so the fresh validation does not inherit the older `documents` labeling problem.
2. Readiness is still `0.39`, which is firmly `not_ready`.
3. Drawing/spec alignment is the weakest readiness category at `0.00`.
4. Scope responsibility clarity is also weak at `0.40`.
5. Labor-estimate confidence is only `0.05`, which is a major pricing risk.
6. The equipment set is large (`626` items), but `580` of them remain unknown-category allowances.
7. There are `638` RFI candidates, which is a strong signal that the package still needs cleanup before pricing.
8. The live package contains `615` reconciliation issues, mostly missing drawing/spec references.
9. The system set clearly includes audio, control, theatrical lighting, and drapery, but there are no rooms/spaces to anchor the coordination.
10. The drapery scope dominates the current review and needs a human pass on track, hardware, infrastructure, and site conditions.

## Defects Found

- The package is not ready for pricing because the drawing/spec alignment is still incomplete.
- Scope responsibility is unresolved across multiple bid-package items.
- The equipment extraction still produces a large volume of unknown-category allowances.
- No rooms/spaces were detected, which limits coordination fidelity.

## Recommended Fixes

- Resolve the drawing/spec references for the high-volume equipment items that are currently missing references.
- Clarify responsibility ownership for the ambiguous scope items that are generating the RFI load.
- Review drapery track, hardware, infrastructure, and site-condition assumptions before pricing.
- If the older cached `documents` review artifacts are still present in the runtime, treat them as stale and regenerate from the live source tree before trusting them for any downstream analysis.

## Recommendation

`Repeat AV-02 after fixes`.

The fresh live rebuild is trustworthy enough for engineering review, but it is not yet stable enough for pricing or final bid confidence.

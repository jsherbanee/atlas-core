# Atlas Core Product Vision

## Product Position
Atlas Core is a bid intelligence and estimating engine for commercial AV and theatrical integration projects.

## Primary Focus
Atlas Core is focused on the front-end preconstruction workflow:
- Bid package analysis
- Estimating readiness
- Preserving estimate data so awarded bids can become projects without re-entry

This means the same structured data generated during bid review should carry forward to downstream project phases instead of being rebuilt manually.

## Why Atlas Core Exists
Estimating teams often re-enter the same information multiple times across bid, procurement, and project execution systems. Atlas Core reduces this waste by turning raw plan/spec inputs into normalized, reusable decision data.

Atlas is intentionally inspired by engineering discipline and decision support rather than consumer software paradigms. For the long-term visual and UX posture, see [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md).

## Current Scope
The engine currently prioritizes:
- Drawing/spec/schedule intelligence
- Scope reconciliation and risk surfacing
- Deterministic product resolution between engineering scope and estimate readiness
- Commercial knowledge foundation with immutable price sheet version history
- Engineering assumptions and RFI candidate generation
- Estimator brief/final review outputs
- Exportable data contracts (CSV, JSON, Markdown)

Product resolution posture:
- deterministic and explainable canonical product matching only
- no pricing logic
- no procurement logic
- no quote generation

Commercial knowledge posture:
- immutable commercial reference history for deterministic readiness
- every price-sheet import is permanent historical record
- no procurement execution
- no quote generation
- no purchase-order workflow

## Deferred Future Phases
The following areas are intentionally deferred until core bid intelligence is fully complete:
- Submittals
- Product document library
- Procurement
- Purchase orders
- Invoices
- Project execution
- Closeout

# Atlas Bid Review User Journey - Validation and Formalization

## Executive Summary

The proposed bid-review journey is directionally consistent with Atlas'"'"' existing lifecycle architecture, but it is not yet fully formalized as a single workflow. The right design is a layered model:

- project lifecycle for business progression
- bid-review report versions for analysis artifacts
- commercial document lifecycle for estimates, proposals, and sales orders
- tenant policy for reusable assumptions, rules, and thresholds

The journey should not be implemented as one monolithic state machine. Doing so would conflate report versions, project stages, commercial document states, and tenant policy into a single object, which would make auditing and revision control harder rather than easier.

## Validation Result

The journey is mostly valid, but several decisions remain unresolved:

- V1 and V2 are report versions, not project lifecycle stages.
- Accepted estimate handling exists at the commercial-document layer, but customer accepted, customer declined, expired, and revised estimate states are not yet first-class in the current enum model.
- Rejected draft retention policy is still a tenant decision.
- Reusable tenant assumptions and reusable tenant rules do not yet have a dedicated canonical persistence model.
- Allowance, lot, and contingency behavior needs explicit policy definitions before AV-03 should consume the journey as authoritative.

Recommendation: formalize the journey now, but keep AV-03 implementation constrained to report generation, guidance capture, and draft-estimate provenance rather than full workflow automation.

## Current Atlas Fit

### Project lifecycle

The current project lifecycle already includes the core path needed for the proposed journey:

- `bid_intake`
- `bid_intelligence`
- `estimating`
- `proposal`
- `award`
- `project_initialization`
- `engineering`
- `submittals`
- `procurement`

This is defined in `atlas_core/domain/av_lifecycle.py` and described in `docs/AV_LIFECYCLE.md`.

### Commercial document lifecycle

The commercial document layer already supports the document-level transitions needed for estimates, proposals, and sales orders:

- `draft`
- `in_review`
- `approved`
- `rejected`
- `issued`
- `archived`

The transactions workspace already blocks sales-order creation unless the source estimate is approved or issued.

### Baseline and revision support

The estimate baseline model already supports a draft/submitted/awarded/superseded/archived state model, but that is not the same thing as the bid-review journey. It is useful as a baseline record, not as the authoritative journey controller.

## Formalized Journey Model

### 1. Bid Intake

Purpose:
- create or select a project
- upload the source bid set
- preserve canonical files and upload provenance
- run asynchronous parsing and classification

Outputs:
- normalized intake bundle
- document inventory
- preliminary classification and source-fitness results

### 2. Preliminary Review V1

Purpose:
- produce the first review artifact from source evidence

Outputs:
- document inventory
- source-fitness assessment
- discipline and system detection
- preliminary rooms and spaces
- equipment and major-component findings
- scope-responsibility findings
- missing information
- conflicts and gaps
- preliminary RFI candidates
- unresolved items
- confidence and readiness scores

Important distinction:
- V1 is a report artifact version.
- V1 is not a project lifecycle stage.

### 3. User Guidance Capture

Purpose:
- capture project-specific judgment before reprocessing

Inputs may include:
- governing documents
- scope inclusions and exclusions
- procurement responsibility
- direct manufacturer vs distributor purchasing
- owner-furnished vs contractor-furnished equipment
- preferred manufacturers
- acceptable substitutions
- rooms or systems in scope
- documents or pages to ignore
- known alternates
- known allowances
- quantity assumptions
- labor assumptions
- pricing assumptions
- pending RFIs
- items to price despite uncertainty
- items to exclude until clarified

Recommended classification:
- project-specific guidance
- reusable tenant assumptions
- reusable tenant rules
- temporary estimate assumptions

Policy decision required:
- Atlas should ask whether a useful decision remains project-specific or should be promoted to a tenant rule.

### 4. Reprocessing V2

Purpose:
- rerun the project with the original evidence plus guidance, tenant policy, and commercial knowledge

Expected outcomes:
- fewer unresolved items
- better source precedence
- more consolidated gaps
- updated RFI candidates
- refined scope assignments
- improved equipment resolution
- improved pricing and labor readiness
- explicit change summary from V1 to V2

Constraint:
- V1 must remain immutable and visible.

### 5. Open Review State

Purpose:
- allow the user to continue resolving uncertainty without forcing a binary outcome

User actions:
- add guidance
- upload addenda or RFI responses
- wait for external information
- mark questions pending
- proceed with assumptions
- exclude unresolved scope
- request another report version
- proceed to draft estimate

Important principle:
- readiness is advisory, not an absolute gate.

### 6. Draft Estimate Generation

Purpose:
- generate a draft estimate from the latest accepted review baseline

The draft should include:
- equipment
- accessories
- labor
- programming
- commissioning
- engineering
- project management
- freight
- tax treatment
- allowances
- lots
- contingencies
- alternates
- exclusions
- qualifications
- unresolved risks
- pricing confidence
- margin assumptions
- source evidence and report version

Constraint:
- the draft estimate must not become the official estimate automatically.

### 7. Draft Estimate Review

Purpose:
- let the user validate the commercial draft before acceptance

User review areas:
- quantities
- products
- pricing
- procurement path
- labor
- margin
- allowances
- lots
- contingencies
- exclusions
- qualifications
- risks
- unresolved questions

### 8. Draft Decision

Accept:
- freeze the accepted review baseline
- convert the draft into the official estimate
- preserve the report version used
- preserve assumptions, overrides, rules, and evidence
- archive earlier reports without deleting history
- mark bid-review engineering complete for that estimate version

Decline:
- do not convert the draft into an official estimate
- preserve audit history that a draft was generated and rejected
- return the project to engineering review
- prompt the user to address unknowns, assumptions, or risks
- permit a new report version and a new draft estimate

Policy decision required:
- whether rejected drafts are archived only or may be permanently deleted under tenant policy.

### 9. Accepted Estimate Lifecycle

After acceptance:
- the official estimate becomes the commercial baseline
- bid-review reports and prior versions remain retained and archived
- engineering review is complete for that estimate version
- future addenda or customer changes create a revision rather than overwriting the accepted baseline
- internal approval can happen before customer acceptance

Recommended estimate states:
- internally approved estimate
- submitted estimate
- customer accepted estimate
- customer declined estimate
- expired estimate
- revised estimate

Current validation:
- the codebase already supports approved/issued gating for sales-order creation.

### 10. Sales Order Conversion

Purpose:
- create a sales order only from an appropriately accepted estimate

Traceability required:
- accepted estimate lines
- accepted quantities
- pricing
- margin
- allowances
- alternates selected
- exclusions
- qualifications
- scope responsibility
- procurement path
- source estimate version

Current validation:
- the transactions workspace already enforces approved-or-issued estimate input before creating a sales order.

### 11. Procurement

Purpose:
- use the sales order as the source for buy-side commitments

Required traceability chain:

`purchase order -> sales order -> estimate -> review report -> source evidence`

The transactions layer already supports the commercial-document families needed for this chain, but the policy and reporting expectations still need to be formalized before AV-03 should rely on them.

## Tenant Rules

Tenant policy should define:

- minimum margin
- margin by category
- markup versus margin calculation
- labor rates
- labor burden
- tax treatment
- freight treatment
- escalation
- rounding
- contingency percentage
- allowance presentation
- lot-item presentation
- alternates
- quote expiration
- stale pricing thresholds
- direct manufacturer purchasing
- distributor preference
- default procurement channels
- default exclusions
- default qualifications
- minimum confidence thresholds
- unresolved-item handling
- rejected-draft retention
- estimate approval authority
- sales-order conversion authority

## Allowance, Lot, and Contingency Formalization

Allowance:
- used when scope is expected but exact product, quantity, or price is unresolved
- must state basis, amount, included scope, and reconciliation method
- must remain traceable to the unresolved source issue

Lot:
- used to price grouped scope that should not be represented as false item-level detail
- must include description, scope boundary, basis, and exclusions
- must not disguise known quantities that Atlas could represent accurately

Contingency:
- used for bid-risk buffering, not as a substitute for unresolved scope
- should be governed by tenant policy and supported by an explicit rationale

## Contradictions and Missing Decisions

1. The journey mixes project lifecycle, artifact versioning, and transaction state. Those must remain separate concepts.
2. The journey asks for report versions V1 and V2, but the current lifecycle enums do not model report versions. Report artifact lineage needs to be explicit.
3. The journey asks for internal approval, submission, customer acceptance, customer decline, expiration, and revision states for estimates. The current commercial document model only partially covers that space.
4. The journey asks whether rejected drafts may be archived or permanently deleted. That is a tenant policy decision, not a universal rule.
5. The journey asks for reusable tenant rules and reusable tenant assumptions. The current codebase has policy-like structures, but not a single authoritative rule store for this purpose.
6. The journey asks for `items the user wants priced despite uncertainty`. That requires an explicit allowance/quote policy so Atlas does not invent commercial coverage.
7. The journey asks for `documents or pages to ignore`. That needs a durable review-exception mechanism, not an ad hoc UI-only filter.

## Architectural Implications

- AV-03 should consume the latest accepted review baseline, not raw intake evidence.
- Review artifacts should be immutable and versioned separately from project and transaction records.
- Tenant policy should be first-class so guidance can be promoted from one-off project decisions to reusable defaults.
- Commercial document conversion should preserve lineage from estimate to sales order and onward to procurement.
- Audit history must preserve rejected drafts, accepted reviews, and source evidence even when artifacts are archived.

## Recommendation

Proceed with formalizing the bid-review journey as an analysis and policy layer now.

Do not implement the full workflow yet.

The next build step should be:

1. capture guidance and tenant policy structures
2. version bid-review reports as immutable artifacts
3. generate a draft estimate from the latest accepted review baseline
4. preserve the transition contract from accepted estimate to sales order

That sequence keeps AV-03 grounded in a stable review baseline without collapsing report versions, commercial documents, and lifecycle state into one mutable object.

# Atlas Documentation

Atlas documentation defines the platform vision, architecture, engineering-intelligence surfaces, and implementation status for Atlas Core.

Current implementation sprint focus: D-01 Core Cost Selection Engine.
Deferred in current sprint scope: D-02 Bid Package Review Orchestration and D-03 Scope and Risk Diagnostics.

Current UX stream: Epic A Sprint A-04 Engineering Workstation UX Consolidation.
Scope: interaction and terminology consistency only, with no new D-03 capability introduction.

These documents are intended to be used as a cohesive reference library, not isolated notes.

## How to Use This Library

- Start with Vision documents to understand product intent and domain boundaries.
- Use Architecture documents to understand system structure and persistence patterns.
- Use Engineering Intelligence documents to understand deterministic review capabilities.
- Use Development documents to understand current state, milestones, and release history.

## Documentation Conventions

### Architecture Documents
Purpose:
Define stable platform structure, boundaries, and long-term system contracts.

Expected update frequency:
Lower frequency, primarily when architecture or system boundaries change.

### Implementation Documents
Purpose:
Describe engine behavior, workspace integrations, deterministic intelligence flows, and operational surfaces.

Expected update frequency:
Higher frequency as capabilities and integrations evolve.

### Status Documents
Purpose:
Describe what is currently implemented and where Atlas stands today.

Expected update frequency:
Updated continuously as implementation changes.

### Release Documents
Purpose:
Capture historical milestone evolution and customer-visible product changes over time.

Expected update frequency:
Updated at each milestone release.

Architecture documents should remain relatively stable. Implementation and status documents should evolve more frequently.

## Version Naming Convention

Atlas product lifecycle naming:

- Preview: early architectural validation and capability proving.
- Beta: feature complete and broad validation.
- Release Candidate: production stabilization and final hardening.
- Major Release: customer-ready platform milestone.

Future releases should follow this structure.

## Vision

### [PRODUCT_VISION.md](PRODUCT_VISION.md)
- Purpose: Defines Atlas product position, problem framing, and scope intent.
- Audience: Product leadership, architecture, engineering stakeholders.
- When to reference: When validating product direction or scope decisions.

### [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- Purpose: Defines enduring business entities, lifecycle relationships, and boundaries.
- Audience: Architects, domain owners, engine developers.
- When to reference: When introducing new lifecycle objects or cross-phase relationships.

### [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md)
- Purpose: Defines UX philosophy and long-term visual/interaction posture.
- Audience: Product design, frontend engineers, architecture owners.
- When to reference: When evaluating UI/UX direction and interaction consistency.


## Architecture

### [ARCHITECTURE.md](ARCHITECTURE.md)
- Purpose: Defines engine-first layering, contracts, and module responsibilities.
- Audience: Engineers and architects.
- When to reference: When adding services, rules, contracts, or orchestration patterns.

### [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- Purpose: Defines project storage architecture, repository contracts, and persistence behavior.
- Audience: Platform engineers, workspace/persistence contributors.
- When to reference: When changing storage, repository adapters, or workspace persistence.

### [MASTER_LIBRARY.md](MASTER_LIBRARY.md)
- Purpose: Defines the long-term reference-library direction for reusable manufacturer/product/standards knowledge.
- Audience: Architecture, data-model, and intelligence contributors.
- When to reference: When planning reusable knowledge assets and shared references.

## Engineering Intelligence

### [DRAWING_INTELLIGENCE.md](DRAWING_INTELLIGENCE.md)
- Purpose: Index for drawing intelligence architecture and implementation references.
- Audience: Engineering-intelligence contributors.
- When to reference: When working on drawing interpretation, relationships, or explorer behavior.

### [SPECIFICATION_INTELLIGENCE.md](SPECIFICATION_INTELLIGENCE.md)
- Purpose: Defines deterministic specification interpretation and cross-reference behavior.
- Audience: Specification-intelligence and workspace contributors.
- When to reference: When changing section parsing, requirements, or spec-linked relationships.

### [COORDINATION_INTELLIGENCE.md](COORDINATION_INTELLIGENCE.md)
- Purpose: Defines deterministic coordination checks and findings model.
- Audience: Coordination engine and workspace contributors.
- When to reference: When changing conflict/gap/agreement logic and advisory findings.

### [ENGINEERING_RESOLVER.md](ENGINEERING_RESOLVER.md)
- Purpose: Documents resolver role and conflict-normalization behavior.
- Audience: Resolver, rule-engine, and intelligence contributors.
- When to reference: When modifying resolver conflict handling or canonicalization behavior.

### [ENGINEERING_INTELLIGENCE.md](ENGINEERING_INTELLIGENCE.md)
- Purpose: Defines engineering insight generation, health scoring, and recommendation outputs.
- Audience: Engineering-intelligence contributors.
- When to reference: When changing insights, priorities, risk signals, or health models.

### [ENGINEERING_WORKBENCH.md](ENGINEERING_WORKBENCH.md)
- Purpose: Defines workspace investigation surface and traceability workflows.
- Audience: Workspace and experience contributors.
- When to reference: When changing investigation behavior, panel composition, or trace UX.

### [ENGINEERING_NOTEBOOK.md](ENGINEERING_NOTEBOOK.md)
- Purpose: Defines engineering notebook data model, timeline integration, and boundaries.
- Audience: Workspace and engineering-review contributors.
- When to reference: When changing notebook entries, decision logs, or linked-object behavior.

## Development

### [EPICS.md](EPICS.md)
- Purpose: Master implementation roadmap organized by epic and sprint stream IDs.
- Audience: Product and engineering planning stakeholders, plus Codex session operators.
- When to reference: Before drafting or executing sprint prompts to anchor work in the correct domain stream.

### [ROADMAP.md](ROADMAP.md)
- Purpose: Defines milestone trajectory and implementation planning direction.
- Audience: Product and engineering planning stakeholders.
- When to reference: During milestone planning and sequencing decisions.

### [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)
- Purpose: Captures the current implementation state and active focus.
- Audience: Internal engineering and product stakeholders.
- When to reference: To answer where Atlas is today.

### [RELEASE_NOTES.md](RELEASE_NOTES.md)
- Purpose: Historical record of customer-visible milestone evolution.
- Audience: Product, engineering, and release stakeholders.
- When to reference: To understand how Atlas evolved across milestones.

### [CODEX_WORKFLOW.md](CODEX_WORKFLOW.md)
- Purpose: Defines AI-assisted engineering workflow and execution conventions.
- Audience: Contributors using Codex/Copilot-assisted development.
- When to reference: Before running sprint execution workflows or agent-driven development.

### [CODEX_SESSION_INIT.md](CODEX_SESSION_INIT.md)
- Purpose: Defines the required repository-initialization checklist for every new Codex session.
- Audience: Contributors starting a new Codex/Copilot coding session in Atlas.
- When to reference: At session start, before pasting sprint instructions or implementing code changes.

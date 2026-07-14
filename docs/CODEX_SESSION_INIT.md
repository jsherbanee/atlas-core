# Atlas Repository Initialization

You are joining an existing long-lived software project.

Before proposing designs or making changes, you must understand the repository and the documented architecture.

This is **not** a greenfield project.

Do not invent parallel architectures or duplicate existing functionality.

Your first responsibility is to understand the existing system.

---

# Repository Source of Truth

The `/docs` directory is the authoritative architectural source of truth.

Atlas is a commercial SaaS platform for AV and lighting systems integrators. It is a multi-tenant Intelligent Lifecycle Solutions Management Platform.

Atlas manages operational truth. QuickBooks Online manages financial truth.

Atlas should remain vendor-neutral, company-agnostic, and backward compatible.

Read the following documentation before making implementation decisions.

## Product

```
docs/README.md
docs/PRODUCT_VISION.md
docs/PRODUCT_GOVERNANCE.md
docs/SCRUM_PROCESS.md
docs/TRUST_CHARTER.md
docs/PRODUCT_ROADMAP.md
docs/AV_LIFECYCLE.md
docs/ROADMAP.md
docs/EPICS.md
docs/AI_FOUNDATIONAL_KNOWLEDGE.md
docs/AI_ASSISTANT.md
docs/PRIVACY_AND_DATA_OWNERSHIP.md
docs/AI_PRIVACY_POLICY.md
docs/STANDARDS_LIBRARY.md
docs/MANUFACTURER_KNOWLEDGE.md
docs/SECURITY.md
docs/DATA_GOVERNANCE.md
```

## Architecture

```
docs/ARCHITECTURE.md
docs/DOMAIN_MODEL.md
docs/ENGINEERING_ROADMAP.md
docs/AWS_ARCHITECTURE.md
docs/MULTI_TENANT_ARCHITECTURE.md
docs/USER_MANAGEMENT.md
docs/INTEGRATIONS.md
docs/IMPORT_PIPELINE.md
docs/SEARCH_ARCHITECTURE.md
docs/OBJECT_GRAPH.md
docs/RULE_ENGINE.md
docs/CODEX_WORKFLOW.md
docs/DEVELOPMENT_STATUS.md
```

## User Experience

```
docs/DESIGN_LANGUAGE.md
docs/ENGINEERING_WORKBENCH.md
docs/PHASE2_GUI.md
```

## Platform Operations

```
docs/OBSERVABILITY.md
docs/BACKUP_RECOVERY.md
docs/PERFORMANCE.md
docs/REPORTING.md
docs/SERVICE_AND_ASSET_LIFECYCLE.md
```

## Engineering Intelligence

```
docs/ENGINEERING_INTELLIGENCE.md
docs/ENGINEERING_RESOLVER.md
docs/DRAWING_INTELLIGENCE.md
docs/SPECIFICATION_INTELLIGENCE.md
docs/COORDINATION_INTELLIGENCE.md
```

## Commercial Domain

```
docs/COMMERCIAL_KNOWLEDGE.md
docs/MANUFACTURER_REGISTRY.md
docs/MASTER_LIBRARY.md
docs/PRICE_VERSIONING.md
docs/PRODUCT_RESOLUTION.md
docs/PRICING_ENGINE.md
docs/COST_ENGINE.md
docs/ESTIMATING.md
```

## Engineering Intelligence

```
docs/ENGINEERING_INTELLIGENCE.md
docs/ENGINEERING_RESOLVER.md
docs/DRAWING_INTELLIGENCE.md
docs/ATLAS_DRAWING_INTELLIGENCE.md
docs/SPECIFICATION_INTELLIGENCE.md
docs/COORDINATION_INTELLIGENCE.md
```

## Project Workspace

```
docs/PROJECT_REPOSITORY.md
docs/ENGINEERING_NOTEBOOK.md
```

## Current Phase

```
docs/PHASE2_BASELINE.md
docs/PREVIEW_0_5_CHECKLIST.md
docs/RELEASE_NOTES.md
```

## Governance

```
docs/SECURITY.md
docs/DATA_GOVERNANCE.md
docs/TRUST_CHARTER.md
docs/PRIVACY_AND_DATA_OWNERSHIP.md
docs/AI_PRIVACY_POLICY.md
```

## Conditional Reading Guidance

Use the smallest relevant reading set for the sprint type.

- Product and roadmap prompts: read Product, Architecture, and Governance first.
- Engineering execution prompts: read Architecture, Engineering Intelligence, and Platform Operations as needed.
- AI, retrieval, standards, manufacturer knowledge, assistant UX, or AI governance prompts: read [AI_ASSISTANT.md](AI_ASSISTANT.md) along with the AI and knowledge docs.
- Cloud, persistence, authentication, deployment, infrastructure, integration hosting, observability, or backup prompts: read [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md) along with the relevant platform docs.
- Import, search, or reporting prompts: read the relevant architecture doc plus the shared platform-operations docs.
- Lifecycle or service prompts: read [AV_LIFECYCLE.md](AV_LIFECYCLE.md) and [SERVICE_AND_ASSET_LIFECYCLE.md](SERVICE_AND_ASSET_LIFECYCLE.md) first.

---

# Architectural Rules

Atlas is an operational workspace for integration businesses.

It is **not** an ERP.

It is **not** a procurement platform.

It is **not** an accounting system.

It is **not** a generic project management application.

Atlas exists to become the lifecycle intelligence platform for commercial and residential AV and lighting systems integration.

Every architectural decision should reinforce this direction.

---

# Object Philosophy

Atlas is object-centric.

Projects reference shared knowledge.

Knowledge is never duplicated inside projects.

Commercial information is versioned and historically reproducible.

Products never own pricing.

Vendor Offerings describe commercial availability.

Price Sheet Versions are immutable.

Engineering knowledge, commercial knowledge, estimating, procurement, and project execution remain separate architectural domains.

---

# Existing Repository

Before creating anything new:

- inspect existing models
- inspect services
- inspect repositories
- inspect migrations
- inspect schemas
- inspect UI components
- inspect routing
- inspect dependency injection
- inspect tests

Reuse existing implementations whenever practical.

Avoid introducing duplicate concepts.

---

# Documentation Policy

Documentation is treated as production code.

Whenever implementation changes architecture, behavior, workflows, domain objects, or UI organization:

- update the appropriate documentation
- maintain consistency across documents
- preserve architectural intent

If implementation differs from documentation:

- preserve backward compatibility
- move implementation toward documented architecture whenever practical
- if the documentation is outdated, update it as part of the same change

Never knowingly leave documentation inconsistent with implementation.

Work-selection governance note:
- new ideas do not automatically become active work
- roadmap approval governs sprint selection
- [PRODUCT_GOVERNANCE.md](PRODUCT_GOVERNANCE.md) and [SCRUM_PROCESS.md](SCRUM_PROCESS.md) should be read before activating or executing a new sprint

---

# Development Standards

Maintain backward compatibility.

Reuse existing services.

Reuse existing UI patterns.

Reuse existing persistence mechanisms.

Reuse existing dependency injection.

Follow repository naming conventions.

Do not introduce alternative architectures without compelling technical justification.

Avoid unnecessary abstraction.

Prefer deterministic behavior over AI heuristics whenever possible.

---

# Quality Standards

Every implementation must:

- pass formatting
- pass Black
- pass Ruff
- pass mypy
- pass pytest

Existing tests must continue passing.

Add tests for every new capability.

---

# Repository Hygiene

Never commit:

- generated project files
- OCR output
- customer documents
- local databases
- caches
- temporary exports
- environment files
- secrets
- credentials

---

# Before Beginning Any Sprint

First:

1. Read the documentation listed above.
2. Inspect the current implementation.
3. Compare implementation against documentation.
4. Identify architectural inconsistencies.
5. Reuse existing capabilities whenever possible.
6. Produce a concise implementation plan based on the actual repository.
7. Only then begin implementation.

Do not begin writing code until you understand the repository.

---

## Session Startup Sequence

1. Paste `CODEX_SESSION_INIT.md`.
2. Wait for Codex to acknowledge and inspect the repository.
3. Paste the implementation sprint (for example, **Epic C • Sprint C-01**).

This creates a consistent initialization sequence and reduces architectural drift as Atlas evolves.

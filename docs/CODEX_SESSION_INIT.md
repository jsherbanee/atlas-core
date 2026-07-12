# AKJ Atlas Repository Initialization

You are joining an existing long-lived software project.

Before proposing designs or making changes, you must understand the repository and the documented architecture.

This is **not** a greenfield project.

Do not invent parallel architectures or duplicate existing functionality.

Your first responsibility is to understand the existing system.

---

# Repository Source of Truth

The `/docs` directory is the authoritative architectural source of truth.

Read the following documentation before making implementation decisions.

## Product

```
docs/README.md
docs/PRODUCT_VISION.md
docs/ROADMAP.md
docs/EPICS.md
```

## Architecture

```
docs/ARCHITECTURE.md
docs/DOMAIN_MODEL.md
docs/CODEX_WORKFLOW.md
docs/DEVELOPMENT_STATUS.md
```

## User Experience

```
docs/DESIGN_LANGUAGE.md
docs/ENGINEERING_WORKBENCH.md
docs/PHASE2_GUI.md
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

---

# Architectural Rules

Atlas is an engineering workstation.

It is **not** an ERP.

It is **not** a procurement platform.

It is **not** an accounting system.

It is **not** a project management application.

Atlas exists to become the engineering and estimating intelligence platform for commercial systems integration.

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

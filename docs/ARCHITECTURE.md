# Atlas Core Architecture

## Domain Alignment
Atlas lifecycle object definitions and cross-phase continuity rules are defined in [DOMAIN_MODEL.md](DOMAIN_MODEL.md).
Architecture and module design should align to that domain model so Phase 2 artifacts remain reusable in downstream phases.

## Engine-First Architecture
Atlas Core is the engine. Future web and API layers should call Atlas Core services and contracts rather than duplicating business logic in separate code paths.

## Layers
- domain
  - Canonical dataclasses/enums and normalization rules.
- services
  - Orchestration and business workflows (review build, readiness, outputs).
- rules
  - Deterministic rule contracts, registries, and rule engine evaluation.
- registries
  - Reference datasets and lookup abstractions (manufacturer/vendor and similar).
- contracts
  - Stable payload/data shapes that downstream surfaces consume.
- exports
  - CSV/JSON/Markdown output adapters from engine outputs.
- CLI
  - Local execution entry point for running workflows against project inputs.

## Core Principle
Business logic should live once in the Atlas Core engine and be reused by all callers:
- CLI
- future API services
- future UI/web applications

## Rule Engine Direction
Atlas is moving to a registry-driven rule model where:
- Rule families register into a shared EngineeringRuleRegistry.
- EngineeringRuleEngine evaluates all relevant rules for a review context.
- Assumptions and related intelligence are deduplicated by stable IDs.
- New discipline coverage is added through modular rule files, not ad hoc service conditionals.

This keeps behavior deterministic, testable, and easy to extend as Phase 2 Bid Intelligence expands.

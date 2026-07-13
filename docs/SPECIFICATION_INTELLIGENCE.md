# Atlas Specification Intelligence Foundation

## Related Documents
- [README.md](README.md)
- [DRAWING_INTELLIGENCE.md](DRAWING_INTELLIGENCE.md)
- [COORDINATION_INTELLIGENCE.md](COORDINATION_INTELLIGENCE.md)
- [ENGINEERING_WORKBENCH.md](ENGINEERING_WORKBENCH.md)
- [ENGINEERING_INTELLIGENCE.md](ENGINEERING_INTELLIGENCE.md)
- [OBJECT_GRAPH.md](OBJECT_GRAPH.md)
- [RULE_ENGINE.md](RULE_ENGINE.md)

Sprint 14 introduces deterministic specification interpretation for Phase 2 Bid Intelligence.

## Purpose

Atlas now treats specifications as structured engineering objects rather than plain documents.

This sprint remains strictly deterministic and local:

- no LLM/AI interpretation
- no procurement/financial/closeout workflow activation
- no cloud/database/authentication features

## Architecture

Path: atlas_core/services/specification_intelligence

Modules:

- models.py
  - SpecificationDiscipline
  - SpecificationMetadata
  - SpecificationSection
  - SpecificationPart
  - SpecificationArticle
  - SpecificationReference
  - SpecificationRelationship
  - SpecificationIndex
  - SpecificationIntelligenceResult
- analyzer.py
  - deterministic metadata extraction
  - discipline classification
  - part/article extraction
  - requirement candidate extraction
  - reference extraction
- engine.py
  - orchestrates section analysis
  - builds section index
  - emits deterministic relationships

## Metadata Model

For each section, Atlas extracts deterministic fields only when present in source content:

- section number
- section title
- division
- revision
- issue date
- addendum references
- part blocks (Part 1 General, Part 2 Products, Part 3 Execution)
- article headings
- referenced standards
- referenced manufacturers
- referenced products
- referenced systems
- referenced drawings
- related schedules

Source traceability is preserved on each section metadata payload.

## Classification Model

Minimum supported classes in this sprint:

- Division 01 General Requirements
- Division 26 Electrical
- Division 27 Communications
- Division 28 Electronic Safety and Security
- AV Systems
- Audio Systems
- Video Systems
- Control Systems
- Network Systems
- Telecom
- Security
- Theatrical Systems
- Lighting Systems
- Rigging
- Acoustics
- Other

## Requirement Candidate Extraction

Deterministic advisory requirement candidates are extracted from explicit source text patterns:

- warranty requirements
- submittal requirements
- training requirements
- testing requirements
- commissioning requirements
- closeout requirements
- mockup requirements
- quality assurance requirements
- manufacturer qualifications
- installer qualifications
- coordination requirements
- power responsibility
- network responsibility
- conduit responsibility
- owner-furnished responsibility
- contractor-furnished responsibility

These are intelligence signals only and do not trigger workflows.

## Cross-Reference Model

Sprint 14 introduces deterministic drawing/specification cross-reference warnings:

- specification references drawing but drawing object missing
- drawing references specification but specification object missing
- equipment appears in drawing but not spec
- equipment appears in spec but not drawing
- system appears in spec with no drawing coverage
- drawing detail references section with execution requirement candidates

Warnings are first-class graph nodes and shown in Specification Explorer.

## Knowledge Graph Integration

Specifications are first-class graph nodes with deterministic edges such as:

- Specification to Specification Part
- Specification to Requirement Candidate
- Specification to Equipment
- Specification to Drawing
- Specification to Manufacturer
- Specification to Product
- Specification to System
- Specification to RFI Candidate
- Specification to Evidence
- Specification to Addendum
- Specification to Standard
- Specification to Engineering Insight

## Workspace Integration

New and updated UI surfaces:

- Specifications page enriched with:
  - section metadata
  - standards/manufacturers/products/addenda
  - requirement candidates
  - cross-reference warning summary
- Specification Explorer page added with:
  - grouping/filtering by division, section, discipline, system, status, revision
  - search and sorting
  - section navigation (previous/next)
  - deterministic linked-object navigation
  - metadata, parts, articles, requirements, relationships, insights, evidence panes

## Future Boundaries

The following remain intentionally deferred:

- procurement workflows
- submittal workflows
- closeout workflows
- financial workflows
- AI/LLM interpretation
- cloud persistence
- database persistence
- authentication

# Atlas Drawing Intelligence Foundation

## Related Documents
- [README.md](README.md)
- [DRAWING_INTELLIGENCE.md](DRAWING_INTELLIGENCE.md)
- [SPECIFICATION_INTELLIGENCE.md](SPECIFICATION_INTELLIGENCE.md)
- [COORDINATION_INTELLIGENCE.md](COORDINATION_INTELLIGENCE.md)
- [ENGINEERING_WORKBENCH.md](ENGINEERING_WORKBENCH.md)
- [ENGINEERING_INTELLIGENCE.md](ENGINEERING_INTELLIGENCE.md)

Sprint 13 introduces deterministic drawing interpretation for the Phase 2 workspace.

## Scope

- Deterministic sheet metadata extraction from review drawing objects.
- Deterministic sheet reference parsing and relationship construction.
- Drawing hierarchy/index generation for explorer workflows.
- Graph integration for drawing-to-drawing/detail/spec/system/evidence/engineering insight edges.
- Dedicated Drawing Explorer page with hierarchy, filters, and sheet navigation.

## Service Layer

Path: atlas_core/services/drawing_intelligence

- models.py: canonical drawing intelligence models:
  - DrawingDiscipline
  - DrawingSheetCategory
  - DrawingReference / DrawingRelationship
  - DrawingMetadata / DrawingIndex / DrawingHierarchy
  - DrawingIntelligenceResult
- analyzer.py: deterministic parsing/classification logic for sheet metadata and references.
- engine.py: orchestrates analyzer output into index/hierarchy/relationships.

### Deterministic Inputs

- Drawing sheet number, title, discipline, notes, revision, issue date.
- Existing review artifacts and source references.

### Deterministic Outputs

- Sheet category (for example floor plan, schedule, legend, detail).
- Referenced sheets/details/views/sections/callouts.
- Discipline hierarchy grouped by drawing set.
- Relationship records for graph use.

## Workspace Integration

The workspace object model now carries drawing intelligence payloads:

- drawing_index
- drawing_hierarchy
- drawing_relationships
- drawing_intelligence_confidence

Each drawing object also carries:

- referenced_drawings
- detail_references
- view_references
- sheet_category
- sheet_sequence
- drawing_scale
- keynotes
- general_notes
- drawing_intelligence_confidence
- intelligence_relationships

## UI Integration

- Drawings page now includes deterministic navigation and intelligence metadata.
- New Drawing Explorer page adds:
  - discipline/category filters
  - search/sort
  - discipline hierarchy view
  - previous/next/reference navigation
- Global search routes drawing results to Drawing Explorer.

## Knowledge Graph Integration

New/expanded deterministic edges include:

- Drawing to Drawing
- Drawing to Detail
- Drawing to Specification
- Drawing to System
- Drawing to Evidence
- Drawing to Engineering Insight

## Validation

Tests added in tests/test_drawing_intelligence_service.py cover:

- analyzer metadata/reference extraction
- engine index/hierarchy/relationship construction

All behavior remains deterministic and local-only; no OCR/CV/ML/LLM/cloud/database features were introduced.

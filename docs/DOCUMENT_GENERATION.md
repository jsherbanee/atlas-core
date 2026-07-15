# Document Generation and Template Engine

## Purpose

Sprint P-05 introduces a deterministic document generation engine for commercial documents.

The engine resolves templates through explicit precedence, captures immutable template snapshots on revisions, and generates reproducible output artifacts.

## Core Contracts

The engine is modeled through shared contracts in atlas_core/contracts/document_generation_contracts.py:

- DocumentTemplate
- DocumentTemplateVersion
- TemplateAssignment
- RenderRequest
- RenderContext
- RenderSection
- RenderDiagnostic
- OutputArtifact
- RenderResult

## Template Precedence

Template resolution order is deterministic and enforced exactly:

1. Transaction-specific template
2. Project-specific template
3. Customer-specific template
4. Tenant default template
5. Application fallback template

No silent reassignment is allowed for issued revisions. If a revision has a captured template snapshot, rendering always reuses that snapshot.

## Deterministic Rendering Guarantees

For a fixed document revision and fixed template version snapshot:

- generated payload bytes are deterministic
- output hash is deterministic
- template assignment metadata is deterministic

Generated output currently supports:

- PDF via existing deterministic commercial PDF exporter
- HTML preview via deterministic token rendering

## Revision Immutability

Commercial revision snapshots now capture:

- terms_and_conditions_reference
- terms_and_conditions_snapshot
- template_assignment
- template_version_snapshot

When a revision is issued and immutable, generation reuses revision-level snapshots even if newer template versions are created later.

## Settings Integration

Settings now supports tenant-scoped document templates with:

- create/list
- version creation
- default assignment
- precedence-aware resolve
- export/replace for runtime sync

This is implemented in atlas_core/services/settings_service.py using DocumentTemplateBlock records.

## Transactions Integration

TransactionsWorkspaceService now routes export and generation through the new generation engine.

Key behavior:

- export_document_pdf delegates to generate_document_artifact when no legacy section override is provided
- generation records template assignment and template snapshot metadata in export activity
- generation records output artifact metadata in document attachments
- customer-invoice presentation exports use the same deterministic generation path and revision snapshot guarantees
- sales-order and return-order revisions marked as change orders render explicit change-order labels in PDF output (`CHANGE ORDER`, `CO #n`, project/base-bid references, and change summary context) while preserving existing template-resolution behavior

## Background Job and Audit Alignment

The generation service is deterministic and job-safe by design.

Generation actions emit activity payloads that can be wrapped by existing background job and immutable audit orchestration layers without introducing a separate rendering model.

## Scope Notes

Included in P-05:

- deterministic template model and rendering pipeline
- template precedence and fallback behavior
- immutable revision snapshot reuse for generated outputs
- settings template CRUD/versioning/default/resolve support
- transactions export integration and generated artifact metadata

Not included in P-05:

- cloud worker execution changes
- external storage adapter changes
- e-signature workflow
- external delivery transport execution

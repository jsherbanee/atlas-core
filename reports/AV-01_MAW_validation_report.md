# Atlas AV-01
## MAW Reference Project - Document Intelligence Validation

Validation date: 2026-07-26
Repository commit: `e54a13c`
Package evaluated: `examples/music_academy_of_the_west`

## Executive Summary

Atlas can currently ingest this MAW package, classify the supported files at the folder level, and produce a usable review package. The package is small, but the strongest signal from this validation is that the current pipeline is still relying heavily on filename heuristics and a thin amount of embedded text. It is not yet extracting robust document intelligence from the content itself.

Key outcomes:

- 4 supported documents processed successfully.
- 1 non-document file (`images/.gitkeep`) was marked unsupported.
- 3 PDF files are byte-for-byte identical, so duplicate detection is currently missing.
- The PDF documents each expose only one text-bearing page and one blank page.
- No OCR was attempted or required in this package.
- No title-block-grade metadata was extracted beyond sheet/section labels inferred from filenames.

Overall assessment: promising intake mechanics, weak true document intelligence. The biggest gaps are duplicate detection, metadata extraction, and relationship grounding.

## Scope And Method

I evaluated the current MAW example package and the exported phase-2 review artifacts produced by the existing deterministic intake pipeline.

Artifacts inspected:

- `examples/music_academy_of_the_west`
- `/private/tmp/maw_phase2_review/intake_snapshot.json`
- `/private/tmp/maw_phase2_review/phase2_review_summary.md`
- `/private/tmp/maw_phase2_review/phase2_review_plan_review.json`
- `/private/tmp/maw_phase2_review/phase2_review_drawing_index.csv`
- `/private/tmp/maw_phase2_review/phase2_review_specification_index.csv`
- `/private/tmp/maw_phase2_review/phase2_review_device_schedules.csv`
- `/private/tmp/maw_phase2_review/phase2_review_review_report.csv`
- `/private/tmp/maw_phase2_review/phase2_review_scope_gaps.csv`
- `/private/tmp/maw_phase2_review/phase2_review_reconciliation_issues.csv`

## Package Summary

Processed files:

- `drawings/AV-101_Audio_Plan.pdf`
- `specifications/27_41_16_Integrated_Audio_Systems.pdf`
- `schedules/maw_audio_schedule.csv`
- `addenda/ADD-1_AV_Addendum.pdf`
- `images/.gitkeep` - unsupported marker file, not a real document

Counts from intake:

- Drawings: 1
- Specifications: 1
- Schedules: 1
- Addenda: 1
- Images: 1
- Total files in diagnostics: 5
- Total extracted pages across PDFs: 6
- Pages with embedded text: 3
- Pages with OCR text: 0
- Pages without embedded text: 3

## Validation Findings

### 1. Document Classification

Supported-file classification is correct at the top level:

- `AV-101_Audio_Plan.pdf` classified as a drawing.
- `27_41_16_Integrated_Audio_Systems.pdf` classified as a specification.
- `ADD-1_AV_Addendum.pdf` classified as addenda.
- `maw_audio_schedule.csv` classified as a schedule.
- `images/.gitkeep` correctly rejected as unsupported.

Notes:

- The addendum is also indexed like a drawing sheet (`ADD-1`) for downstream cross-reference purposes. That is not necessarily wrong, but it does blur the distinction between a true drawing sheet and an addendum document.
- No other supported document shows a clear misclassification.

Incorrect classifications found:

- None at the folder/document-group level for supported files.
- The `.gitkeep` file is not a document and was correctly rejected.

### 2. Discipline Recognition

Observed discipline labels:

- `AV-101_Audio_Plan.pdf` -> `audiovisual`
- `27_41_16_Integrated_Audio_Systems.pdf` -> `audiovisual`
- `ADD-1_AV_Addendum.pdf` -> `architectural`

Assessment:

- AV discipline recognition is correct for the audio drawing.
- Section 27 41 16 was recognized correctly as audiovisual.
- The addendum's `architectural` discipline appears to be a heuristic folder-level assignment, not a content-based determination.

Confidence:

- The emitted confidence for extracted sheet and section records was `0.75`.
- No lower-confidence discipline conflicts were surfaced in this package.

### 3. Sheet Recognition

Recognized sheet/section IDs:

- `AV-101`
- `ADD-1`
- `27 41 16`

Successes:

- Sheet number `AV-101` was extracted.
- Sheet title `Audio Plan` was extracted.
- Section number `27 41 16` was extracted.
- Section title `Integrated Audio Systems` was extracted.
- Addendum sheet label `ADD-1` was extracted.
- Discipline prefix `AV` was recovered for the drawing.

Failures:

- Revision field not extracted.
- Revision date not extracted.
- Discipline prefix is not separately surfaced as a structured field.
- No page-level sheet differentiation was extracted for the blank second page in each PDF.

Important note:

- The drawing and addendum sheet metadata are duplicated across the two page records in each PDF. That suggests page-level repetition rather than true multi-sheet discovery.

### 4. Drawing Metadata

What Atlas extracted:

- Project name: not extracted from document content.
- Owner: not extracted from document content.
- Architect: not extracted.
- Engineer: not extracted.
- Issue date: not extracted.
- Revision number: not extracted.
- Scale: not extracted.
- Drawing index: `AV-101` was recovered.
- Title block: not extracted as a structured object.
- Consultant: not extracted.
- Page size: not surfaced.
- North arrow: not detected.

Assessment:

- Current metadata extraction is very shallow.
- The pipeline is inferring sheet identity from filenames and sparse text, not from a robust title block read.
- For a release-grade document intelligence system, this is the clearest gap in the package.

### 5. OCR Quality

Observed quality:

- Pages with usable OCR: 0
- Pages requiring OCR: 0
- Pages with poor OCR: 0
- Blank pages: 3
- Scanned raster pages: 0 observed
- Rotated pages: 0 observed
- Unreadable pages: 0 observed
- Mixed vector/raster pages: 0 observed

Interpretation:

- OCR was not needed because each PDF exposed one embedded-text page.
- The extracted pages are very sparse: page 1 contains only `First page`, while page 2 is blank.
- If these PDFs were intended to model real production documents, this fixture is far too weak for OCR stress testing.

### 6. Document Relationships

Observed cross-document links:

- `detected-audio` -> `27 41 16`
- `AV-101` -> `27 41 16`
- `ADD-1` -> `27 41 16`

What was not found:

- No drawing revision relationships.
- No referenced-sheet relationships.
- No detail references.
- No callout references.
- No general notes relationships.
- No specification references beyond the basic drawing/spec alignment link.
- No schedule-to-drawing or schedule-to-specification linkage.

Assessment:

- Atlas can express a small number of high-level alignment edges, but it is not yet building a rich relationship graph from the package.
- The schedule is parsed, but it is not connected back to the drawing/spec ecosystem.

### 7. Duplicate Detection

Exact duplicate files:

- `drawings/AV-101_Audio_Plan.pdf`
- `specifications/27_41_16_Integrated_Audio_Systems.pdf`
- `addenda/ADD-1_AV_Addendum.pdf`

These three PDFs have the same SHA1 hash:

- `d947dc9a495970776cc22e03aab96ceec51a0724`

Other duplicate findings:

- `schedules/maw_audio_schedule.csv` is unique.
- No near-duplicate files were surfaced by Atlas.
- No superseded revisions were identified because revision metadata is empty.

Assessment:

- Duplicate detection is currently missing a major case: three completely identical PDFs with different filenames and different folder labels.
- This is the highest-priority correctness issue in the package.

### 8. Folder Assignment

Validation:

- `drawings/AV-101_Audio_Plan.pdf` is in the correct folder.
- `specifications/27_41_16_Integrated_Audio_Systems.pdf` is in the correct folder.
- `schedules/maw_audio_schedule.csv` is in the correct folder.
- `addenda/ADD-1_AV_Addendum.pdf` is in the correct folder.
- `images/.gitkeep` is a placeholder marker, not a real image asset.

Assessment:

- Folder assignment is correct for the actual content package.
- The only issue is that the image folder contains a non-document placeholder and no real imagery.

### 9. Processing Diagnostics

Per-file status:

- `AV-101_Audio_Plan.pdf` - succeeded with warnings / partial extraction
- `27_41_16_Integrated_Audio_Systems.pdf` - succeeded with warnings / partial extraction
- `maw_audio_schedule.csv` - succeeded
- `ADD-1_AV_Addendum.pdf` - succeeded with warnings / partial extraction
- `images/.gitkeep` - failed / unsupported

Diagnostics notes:

- The three PDFs each parsed as 2-page documents with 1 text-bearing page and 1 blank page.
- The schedule CSV parsed cleanly into 3 rows.
- The unsupported `.gitkeep` marker produced the only package warning.

## Prioritized Improvement Backlog

1. Add package-level duplicate detection.

   - Flag byte-identical PDFs immediately.
   - Add page-level duplicate detection for repeated pages.
   - Surface duplicate and near-duplicate warnings in intake diagnostics.

2. Ground classification in content, not just filenames.

   - Use title block text, page labels, and OCR when needed.
   - Reduce dependence on folder names and filename tokens.
   - Add confidence and evidence fields for sheet/document type decisions.

3. Improve title-block metadata extraction.

   - Extract project name, owner, architect, engineer, consultant, issue date, revision, scale, page size, and north arrow when present.
   - Preserve unknown values explicitly instead of leaving them implicit.

4. Expand relationship extraction.

   - Detect referenced sheets, detail callouts, general notes, and schedule references.
   - Link schedules back to source drawings/specifications.
   - Capture revision relationships where applicable.

5. Make addenda handling more explicit.

   - Keep addenda classification distinct from drawing-sheet indexing.
   - Avoid implying a full drawing sheet when the source is an addendum unless the content really supports it.

6. Add real OCR validation coverage.

   - Include scanned, rotated, raster-heavy, and mixed-content fixtures.
   - Emit clearer page-level OCR quality flags.
   - Distinguish embedded text, OCR-derived text, and unreadable pages.

## Conclusion

Atlas successfully processed the MAW example package, but the review is still mostly a structural intake with shallow text parsing. The package is small enough that it hides some weaknesses, but the duplicate PDFs expose a real problem: the current pipeline is not yet robust enough to distinguish distinct documents from repeated fixtures or to produce reliable document intelligence without stronger content grounding.

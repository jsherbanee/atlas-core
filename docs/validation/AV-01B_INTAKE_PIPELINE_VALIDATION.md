# Atlas AV-01B - Intake Pipeline Validation

Validation date: 2026-07-26
Project: `BID-2026-0002` - Music Academy of the West

## Executive Summary

The current intake pipeline successfully processed the real MAW project workspace end to end after one validation-only correction: the `reports/` folder was not originally part of document discovery, so the acoustics narrative was invisible to intake. That defect was fixed during validation by adding report-folder discovery, upload routing, snapshot extraction, and report counts.

Current outcome:

- 7 physical source documents are present in the live MAW workspace.
- Intake now discovers and classifies all 7 documents.
- The pipeline produces page-level relevance assessments with explainable evidence.
- No stalled jobs or orphaned records were found.
- Quality gates passed after formatting and export fixes.

Recommendation: `Proceed to AV-02`.

## Intake Statistics

Live MAW document set:

- `drawings/07_Electrical for AV Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `drawings/08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `drawings/09_Theater Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `drawings/MAW_MBD-018_Aurora Element - Design Narrative FINAL.pdf`
- `reports/2025.12.15 MAW 100DD Acoustics Narrative by Kirkegaard.pdf`
- `schedules/Div 11 Equipment.pdf`
- `specifications/Div 27 Communications.pdf`

Snapshot totals from the live MAW workspace:

- Files discovered: `7`
- Drawings: `4`
- Reports: `1`
- Schedules: `1`
- Specifications: `1`
- Addenda: `0`
- Images: `0`
- Unsupported: `0`
- Total extracted pages: `306`
- Pages with embedded text: `303`
- Pages without embedded text: `3`
- OCR attempted: `0`
- OCR required: `0`
- Drawing sheet detections: `92`
- Specification section detections: `56`
- Device schedule detections: `48`
- Relevance assessments: `7`

## Duplicate Validation

The live `documents/` tree contains only the canonical MAW source set.

Validated results:

- No duplicate canonical filenames remain in the live workspace.
- No exact-content duplicate physical files remain in the live workspace.
- Retry artifacts and internal validation artifacts remain excluded from the current source set.
- Canonical source documents are preserved under their expected names.

Notes:

- Earlier validation artifacts show the historical retry cleanup was already completed.
- The live workspace now reflects the 7-document canonical MAW package.

## Processing Validation

Background job and status review:

- The latest document import job completed successfully.
- Queue latency was approximately `10.0s`.
- Processing latency was approximately `31.0s`.
- No currently stalled jobs were found.
- Failed historical attempts exist in the job log, but they have actionable diagnostics and are superseded by the final successful run.

Observed status transitions for the latest successful import:

- `queued`
- `running`
- `succeeded`

## Classification Accuracy

Folder and document classification are now aligned with the live MAW workspace:

- 4 drawing documents are recognized.
- 1 report document is recognized.
- 1 schedule document is recognized.
- 1 specification document is recognized.

Validation notes:

- The acoustics narrative now routes through the `reports/` folder instead of being silently omitted.
- The coordination narrative `MAW_MBD-018_Aurora Element - Design Narrative FINAL.pdf` remains visible in intake and is assessed independently rather than being merged into the main drawing set.
- Unknown or incidental material continues to be visible for review instead of being deleted.

## Relevance Validation

The relevance layer now emits explainable document and page assessments.

Verified behavior:

- AV, AV control systems, integrated control systems, theatrical lighting, theatrical lighting control, show control, and performance-system controls are treated as equal primary disciplines when supported by evidence.
- Architectural lighting is detected and flagged with `Possible Architectural Lighting Scope` unless evidence clearly pushes it otherwise.
- Page-level relevance includes:
  - page number
  - detected sheet number
  - detected discipline
  - relevance score
  - workflow relevance
  - evidence
  - review flags
- Every relevance score is backed by textual reasons and evidence references.

Representative outcomes from the live MAW workspace:

- `07_Electrical...pdf` - audiovisual, governing, score `100`
- `08_Audio Visual...pdf` - audiovisual, governing, score `100`
- `09_Theater...pdf` - theatrical lighting, governing, score `100`, with architectural-lighting review flags
- `2025.12.15 MAW 100DD Acoustics Narrative...pdf` - high relevance with page-level coordination evidence and mixed governing signals where explicit AV/control references appear
- `Div 27 Communications.pdf` - audiovisual, governing, score `100`

## Performance Metrics

Measured on the live MAW workspace:

- Upload/package assembly: `81.604s`
- Classification/extraction: `81.557s`
- Relevance analysis: `0.049s`
- Review generation: `0.103s`
- OCR time: `0.000s`
- Queue latency: `~10.0s`
- Processing latency: `~31.0s`

Largest bottleneck:

- PDF extraction and page parsing dominate runtime.
- The 132-page `Div 11 Equipment.pdf` and the 26-page acoustics narrative account for most of the wall-clock cost.
- Relevance analysis is effectively negligible compared with extraction.

## Defects Found

1. `reports/` was not included in intake discovery.

   - Impact: the acoustics narrative was omitted from the live MAW intake set.
   - Fix: added `reports/` to package discovery, upload folder creation, upload routing, snapshot extraction, and summary counts.

2. Upload summary reporting did not include report counts.

   - Impact: report documents were under-reported in intake summaries.
   - Fix: added `report_count` to session-package summary output.

## Recommended Fixes

No additional blocking fixes are required for validation trustworthiness.

Optional follow-up:

- Break long-running PDF extraction into smaller background steps if further throughput improvement is needed.

## Recommendation

Proceed to `AV-02`.

The intake pipeline is now validating the real MAW project as a canonical 7-document workspace with explainable relevance and no orphaned or duplicate source records in the live set.

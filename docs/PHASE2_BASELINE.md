# Phase 2 Bid Intelligence Baseline Candidate

## Conceptual Label
- phase-2-bid-intelligence-baseline-candidate

This is a conceptual milestone label for communication and planning.
It is not a Git tag at this time.
Treat it as a versioned Git tag only when serialized outputs are intentionally managed as versioned contracts.

## Scope
This baseline candidate covers deterministic bid intelligence and estimator-readiness workflows only.

Included features:
- Bid package review orchestration across drawings, specifications, systems, equipment, and cross-references.
- Scope-gap and estimator-risk surfacing.
- Engineering assumption generation via rule engine.
- RFI candidate generation.
- Labor estimation output for bid-intelligence ranges.
- Bid completeness scoring.
- Plan review readiness scoring with blockers, warnings, diagnostics, and recommended reviewer actions.
- Estimator brief generation with executive summary, prioritized actions, and evidence references.
- Revision comparison for baseline vs. comparison review deltas.
- CSV/JSON/Markdown exports from plan review workflows.

Excluded features in this baseline:
- Procurement workflows.
- RFQ workflows.
- Submittal workflows.
- Invoice workflows.
- Purchase order workflows.
- Change order workflows.
- Project execution workflows.
- Closeout workflows.
- Vendor communication workflows.
- Customer-facing proposal generation.

## MAW Reference Project
Music Academy of the West (MAW) is used as canonical sample/reference data for deterministic demos and regression tests.

MAW is not product logic:
- MAW seed data is isolated in atlas_core/sample_data.
- MAW-specific commands are demo CLI entry points.
- Core services consume generic domain models and do not branch on MAW identifiers.

## CLI Demo Commands
- python -m atlas_core.cli demo-maw
- python -m atlas_core.cli demo-maw-plan-review --output-dir <path>
- python -m atlas_core.cli demo-maw-rfi-candidates
- python -m atlas_core.cli demo-maw-labor-estimate
- python -m atlas_core.cli demo-maw-revision-comparison

## Local GUI Prototype
- Streamlit entry point: apps/phase2_review_app.py
- Run: streamlit run apps/phase2_review_app.py
- GUI usage and details: docs/PHASE2_GUI.md

## Local Package Intake (Deterministic)
- Build intake snapshot from local folder package:
	- atlas-core package-intake --path examples/music_academy_of_the_west --out outputs/maw_intake
- Run review from package intake:
	- atlas-core phase2-review --package examples/music_academy_of_the_west --out outputs/maw_review
- Run review from an existing snapshot:
	- atlas-core phase2-review --snapshot outputs/maw_intake/intake_snapshot.json --out outputs/maw_review

## Atlas Intake Drag-and-Drop (GUI)
Phase 2 Local Review GUI supports deterministic local uploads:
- One file, many files, or ZIP package drag-and-drop
- Session package created at outputs/uploads/<session_id>
- Files auto-classified into drawings/specifications/schedules/addenda/images/metadata/unsupported
- Deterministic intake snapshot built and review pipeline executed from that session package

Supported formats:
- Documents: PDF, DOCX, DOC, TXT, RTF
- Spreadsheets: XLSX, XLS, CSV
- Images: JPG, JPEG, PNG, TIFF
- Metadata: JSON
- Archives: ZIP

Import summary includes:
- drawing count
- specification count
- schedule count
- addenda count
- image count
- unsupported file count
- extraction warnings

Expected package structure:
- examples/music_academy_of_the_west/drawings/*.pdf
- examples/music_academy_of_the_west/specifications/*.pdf
- examples/music_academy_of_the_west/schedules/*.pdf|*.csv|*.xlsx
- examples/music_academy_of_the_west/addenda/*.pdf
- examples/music_academy_of_the_west/metadata.json

## Expected Outputs
Representative output characteristics from MAW snapshots:
- Plan review pipeline returns coherent review, readiness, brief, and final review artifacts.
- Readiness includes deterministic score/level, warnings, diagnostics, and recommendations.
- Estimator brief includes deterministic executive summary and prioritized reviewer actions.
- Revision comparison reports deterministic delta summaries and categorized change records.

## Known Limitations
- Scoring and action prioritization are deterministic heuristics, not empirically calibrated.
- Downstream lifecycle domain scaffolding may exist in repository history but is not part of the active Phase 2 review pipeline.
- Revision comparison depends on availability of both baseline and comparison review snapshots.

## Quality Gate
Baseline candidate requires all checks green:
- black .
- ruff check .
- mypy .
- pytest

## Recommended Next Enhancements
- Drawing/spec intelligence refinements (higher fidelity link confidence and mismatch diagnostics).
- PDF ingestion/indexing robustness and traceability improvements.
- Device schedule extraction and reconciliation quality improvements.
- Additional snapshot coverage for export artifacts.
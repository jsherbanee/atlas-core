# Atlas

## Purpose
Provide a local read-only interface for estimators to run Atlas Intake and inspect deterministic project review outputs.

This interface is for review only:
- No authentication.
- No database persistence.
- No procurement/RFQ/submittal/invoice/execution/closeout/vendor communication workflows.

## Atlas Intake (Local)
The GUI now supports local drag-and-drop intake for estimator bid packages.

Atlas Intake panel:
- Drag your project here
- Supported formats: PDF, DOCX, DOC, XLSX, XLS, CSV, JPG, JPEG, PNG, TIFF, TXT, RTF, JSON, ZIP
- Or browse files

Uploaded files are staged under:
- outputs/uploads/<session_id>

Files are automatically classified into:
- drawings/
- specifications/
- schedules/
- addenda/
- images/
- metadata/
- unsupported/

After classification, Atlas runs deterministic intake and then executes the existing project review pipeline.

## Data Sources
The GUI supports two explicit source modes.

Reference Project:
- Music Academy of the West (Reference Project)

Uploaded Project:
- User-provided files or ZIP package from Atlas Intake
- Banner shows detected project name when available
- Banner shows package location
- Import summary table is shown
- Extraction warnings are shown

MAW remains reference data only and is not product-specific business logic.

## Run Instructions
1. Install GUI dependency:
   - pip install -e .[gui]
2. Launch app:
   - streamlit run apps/phase2_review_app.py

## Upload Flow
1. Select `Uploaded Project` in the sidebar.
2. Drag files into Atlas Intake (single file, many files, or ZIP).
3. Click `Run Atlas Intake`.
4. Review import summary, warnings, and project review tabs.

## Deterministic Extraction Rules
- PDF: extract embedded text.
- DOCX: extract paragraphs/headings/tables from document XML text runs.
- DOC: best-effort decode; warning requests DOCX/PDF for reliable extraction.
- XLSX/CSV: extract schedule-style rows.
- XLS: unsupported in deterministic parser; warning requests XLSX/CSV.
- Images (JPG/JPEG/PNG/TIFF): no OCR fabrication; warning emitted when no extractable text is available.
- ZIP: automatically unpacked recursively and classified.

## Snapshot Mode
For existing local intake snapshots, the sidebar includes `Use Existing Intake Snapshot` in uploaded mode.
This allows browsing `intake_snapshot.json` files already generated under local outputs/examples folders.

## Visible Sections
- Project Overview
- Readiness Score and Readiness Level
- Section Scores
- Top Blocking Issues
- Warnings
- Estimator Brief
- Prioritized Reviewer Actions
- RFI Candidates
- Labor Estimate Summary
- Revision Comparison Summary
- Engineering Assumptions
- Evidence / Source References

## Notes
- The GUI reads deterministic outputs from existing services and sample data.
- The app does not mutate project data.

# Atlas

## Purpose
Provide a local workspace interface for estimators to run Atlas Intake and inspect deterministic project review outputs.

This interface is local-only:
- No authentication.
- No cloud persistence.
- Local file-backed workspace persistence under `outputs/project_workspaces/`.
- No procurement/RFQ/submittal/invoice/execution/closeout/vendor communication workflows.

Atlas launches to a Home screen with:
- `+ New Project`
- `Open Project`
- `Recent Projects`

The active workspace uses left navigation for the project sections.

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

After classification, Atlas runs deterministic intake, saves the workspace locally, and then executes the existing project review pipeline.

## Data Sources
The GUI supports two explicit source modes.

Reference Project:
- Music Academy of the West (Reference Project)
- Default behavior attempts real package intake from examples/music_academy_of_the_west
- Data Source label shows `Real package intake` when loaded from full package files
- If package is missing/incomplete/unreadable, Atlas falls back to seed fixture data
- Data Source label shows `Seed fixture fallback` for fallback mode
- Fallback mode explicitly warns that curated fixture data is in use

Uploaded Project:
- User-provided files or ZIP package from Atlas Intake
- Banner shows detected project name when available
- Banner shows package location
- Import summary table is shown
- Extraction diagnostics are shown (pages with/without embedded text, files requiring OCR)
- Per-file extraction status is shown (`extracted`, `partial`, `requires_ocr`, `unsupported`, `failed`)
- Extraction warnings are shown

MAW remains reference data only and is not product-specific business logic.

## MAW Package Placement
Place the full MAW package under:
- examples/music_academy_of_the_west/
- examples/music_academy_of_the_west/metadata.json
- examples/music_academy_of_the_west/drawings/
- examples/music_academy_of_the_west/specifications/
- examples/music_academy_of_the_west/schedules/
- examples/music_academy_of_the_west/addenda/
- examples/music_academy_of_the_west/images/

If expected folders are missing, Atlas shows a warning and still attempts deterministic intake from available files.

## Run Instructions
1. Install GUI dependency:
   - pip install -e .[gui]
2. Launch app:
   - streamlit run apps/phase2_review_app.py
3. Open `Reference Project` to verify MAW source mode.

## Upload Flow
1. Select `Uploaded Project` in the sidebar.
2. Drag files into Atlas Intake (single file, many files, or ZIP).
3. Click `Run Atlas Intake`.
4. Review import summary, warnings, and workspace sections.

## Deterministic Extraction Rules
- PDF: extract embedded text.
- PDF (optional local OCR): when enabled, Atlas attempts local OCR on PDF pages without embedded text.
- DOCX: extract paragraphs/headings/tables from document XML text runs.
- DOC: best-effort decode; warning requests DOCX/PDF for reliable extraction.
- XLSX/CSV: extract schedule-style rows.
- XLS: unsupported in deterministic parser; warning requests XLSX/CSV.
- Images (JPG/JPEG/PNG/TIFF): optional local OCR can be attempted; otherwise warning emitted when no extractable text is available.
- ZIP: automatically unpacked recursively and classified.

## Optional Local OCR
- Local OCR is optional and disabled by default.
- Quality gate and test runs do not require system OCR binaries.
- OCR-derived text is explicitly marked in diagnostics as `ocr_derived_text`.
- OCR failures are explicitly marked as `ocr_failed`.
- No cloud OCR or LLM interpretation is used.

## Snapshot Mode
For existing local intake snapshots, the sidebar includes `Use Existing Intake Snapshot` in uploaded mode.
This allows browsing `intake_snapshot.json` files already generated under local outputs/examples folders.

## Visible Sections
- Overview
- Executive Summary
- Project Files
- Readiness
- Estimator Brief
- RFI Candidates
- Labor Estimate
- Revision Comparison
- Engineering Assumptions
- Evidence

## Notes
- The GUI reads deterministic outputs from existing services and sample data.
- The app does not mutate project data.
- Scanned/image-only PDFs can produce warnings when no embedded text is extractable.
- Atlas does not fabricate sheet/spec/equipment extraction when text is unavailable.

## Extraction Diagnostics
Atlas Intake surfaces the following diagnostics in the Import Summary:
- total files
- total pages (where page counts are available)
- pages with embedded text
- pages with OCR-derived text
- pages without embedded text
- documents requiring OCR
- extraction warning count

When `documents requiring OCR` is non-zero, Atlas displays guidance that OCR is needed before text-rich project intelligence can be extracted.
Per-file diagnostics include extraction mode to distinguish embedded text extraction, OCR-derived extraction, and OCR failures.

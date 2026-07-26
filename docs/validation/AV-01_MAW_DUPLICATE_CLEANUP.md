# AV-01 MAW Duplicate Cleanup

Date: 2026-07-26

Scope:

- Project ID: `BID-2026-0002`
- Project name: `Music Academy of the West`
- Runtime project directory: `~/.atlas_core/runtime/AtlasProjects/BID-2026-0002`
- Workspace source mode: `project_documents`
- Workspace source label: `Project Repository`

## What We Verified

The live MAW runtime project is real and populated, not the placeholder fixture.

Pre-cleanup inventory:

- Physical files under `documents/`: `51`
- Unique exact-content groups after recursive retry normalization: `7`
- Duplicate groups: `6`
- Dry-run delete candidates: `44`

Artifacts:

- Full per-file inventory: [`docs/validation/artifacts/AV-01_MAW_DUPLICATE_CLEANUP.inventory.json`](./artifacts/AV-01_MAW_DUPLICATE_CLEANUP.inventory.json)
- Dry-run cleanup plan: [`docs/validation/artifacts/AV-01_MAW_DUPLICATE_CLEANUP.dry_run.json`](./artifacts/AV-01_MAW_DUPLICATE_CLEANUP.dry_run.json)

## Cleanup Rule

Use a checksum-backed canonicalization rule:

- Strip trailing retry suffixes recursively until the filename stabilizes.
- Treat `_<digits>` and `-<YYYYMMDDHHMMSS>` endings as retry suffixes.
- Group files by canonical filename plus SHA-1 checksum.
- Keep one canonical unsuffixed file when it exists.
- Remove only byte-identical retry copies.
- Leave non-identical variants, missing files, and uncertain extras untouched.

This rule is intentionally conservative. It is designed to remove historical retry noise without deleting anything that might represent a distinct document.

## Current Unique Uploaded Document Groups

These are the logical documents currently represented in the live workspace after deduping exact retry copies:

- `07_Electrical for AV Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `Div 11 Equipment.pdf`
- `Div 27 Communications.pdf`
- `MAW_MBD-013_Interior Scaffold Phasing.pdf`
- `MAW_MBD-018_Aurora Element - Design Narrative FINAL.pdf`
- `av00c-navigation-refresh-validation.pdf`

## Expected MAW 7-Document Target

The reference set shown by the user contains these expected documents:

- `07_Electrical for AV Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `09_Theater Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `Div 11 Equipment.pdf`
- `Div 27 Communications.pdf`
- `2025.12.15 MAW 100DD Acoustics Narrative by Kirkegaard.pdf`
- `MAW_MBD-018_Aurora Element - Design Narrative FINAL.pdf`

Gap check against the current live workspace:

- Missing from the live workspace: `09_Theater Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- Missing from the live workspace: `2025.12.15 MAW 100DD Acoustics Narrative by Kirkegaard.pdf`
- Unexpected current logical docs: `MAW_MBD-013_Interior Scaffold Phasing.pdf`
- Unexpected current logical docs: `av00c-navigation-refresh-validation.pdf`

## Cleanup Outcome

The approved cleanup has now been applied.

What changed:

- Exact duplicate retry copies were deleted from the live `documents/` tree.
- Downstream references in the intake snapshot, bid package review, knowledge graph, and event log were reconciled to the canonical unsuffixed filenames for the duplicate groups.
- The internal validation PDF `av00c-navigation-refresh-validation.pdf` was moved out of the project `documents/` tree into `review/validation_artifacts/` so it no longer counts as source material.
- The project manifest was refreshed to reflect the cleaned document inventory.

Post-cleanup runtime state:

- Physical files under `documents/`: `7`
- Unique exact-content groups: `7`
- Duplicate groups remaining: `0`
- Retry copies remaining: `0`

## Implementation Status

The code fix is already in place so future uploads do not recreate the same retry duplicates:

- `atlas_core/services/document_intake_service.py` now normalizes nested retry suffixes recursively and cleans duplicate variants after package writes.
- `atlas_core/repository/local.py` now skips exact byte-identical copies during import and re-runs duplicate cleanup on the destination folders.
- Regression tests were added for retry reuse and nested suffix cleanup.

## Current Live Document Set

The live project document set now contains:

- `07_Electrical for AV Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `09_Theater Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `MAW_MBD-018_Aurora Element - Design Narrative FINAL.pdf`
- `Div 11 Equipment.pdf`
- `Div 27 Communications.pdf`
- `2025.12.15 MAW 100DD Acoustics Narrative by Kirkegaard.pdf`

The 100DD acoustics narrative is stored in `documents/reports/` because it is a report, not a drawing.
The accidental `MAW_MBD-013_Interior Scaffold Phasing.pdf` has been removed from the live source set and parked in `review/validation_artifacts/`.

Historical provenance for the internal validation artifact remains in the intake snapshot and event log, but the artifact no longer lives in the project document tree.

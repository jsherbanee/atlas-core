# Drawing Intake

## AV-00A Async Boundary

Project document upload no longer performs drawing intelligence, OCR, PDF page
inspection, classification, or evidence generation inside the Streamlit render
cycle.

Upload now separates:

- upload acceptance
- durable file/job persistence
- document-processing job creation
- local worker execution
- Processing-page status presentation

Each accepted file receives a persisted document-processing job. The current
local worker consumes those jobs from the repository-backed queue and can be
replaced later by Celery, RQ, Dramatiq, or AWS queue/worker infrastructure.

## Upload Policy

Bid-package intake uses one shared upload policy for the Streamlit uploader,
pending-file validation, intake validation, queued background jobs, help text,
and rejection diagnostics.

- Maximum size: 200 MB per file, interpreted as 200,000,000 bytes.
- Supported formats: PDF, DOCX, DOC, XLSX, XLS, CSV, JPG, JPEG, PNG, TIF, TIFF, TXT, RTF, ZIP.
- JSON is not a supported user-facing bid-package upload format.
- Rejections include the observed file size and the maximum supported size.
- ZIP remains a container boundary only; existing entry-count, expansion-size,
  nested-depth, unsafe-path, encrypted-entry, duplicate-entry, and system-file
  protections continue to govern archive contents.

## Status Lifecycle

Document jobs present user-facing stages:

- Queued
- Inspecting
- Extracting
- Processing
- Ready
- Needs Attention
- Failed
- Cancelled

Failed jobs retain diagnostics and can be retried from Processing when retry is
available. A failed file does not block other queued files.

## Scope Boundary

AV-00A does not add drawing extraction rules, OCR algorithms, AI behavior, or
new drawing intelligence semantics. Existing drawing/document services remain
the processing authority.

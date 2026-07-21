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

AV-00B keeps project opening isolated from that worker. Opening a project reads
cached document and processing counts only; it does not claim jobs, wait for job
completion, inspect PDFs, run OCR, extract text, classify documents, or generate
evidence during the Streamlit route transition.

## Upload Policy

Bid-package intake uses one shared upload policy for the Streamlit uploader,
pending-file validation, intake validation, queued background jobs, help text,
and rejection diagnostics.

- Maximum file size: 200 MiB per file, interpreted as 209,715,200 bytes.
- Maximum batch size: 1 GiB per batch, interpreted as 1,073,741,824 bytes.
- Maximum files per batch: 50.
- Supported formats: PDF, DOCX, DOC, XLSX, XLS, CSV, JPG, JPEG, PNG, TIF, TIFF, TXT, RTF, ZIP.
- JSON is not a supported user-facing bid-package upload format.
- Rejections include the observed file size, projected batch size where
  relevant, and the maximum supported size.
- ZIP remains a container boundary only; uploaded batch totals use the compressed
  ZIP size. ZIP processing enforces a 2 GiB expanded-size limit, 500 contained
  files, unsafe-path rejection, symbolic-link rejection, encrypted-entry
  rejection, duplicate-entry rejection, system-file filtering, and bounded
  nested-archive behavior.

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

# Phase 2 Local Review GUI

## Purpose
Provide a local read-only interface for estimators to inspect deterministic Phase 2 Bid Intelligence outputs.

This interface is for review only:
- No authentication.
- No file upload.
- No database persistence.
- No procurement/RFQ/submittal/invoice/execution/closeout/vendor communication workflows.

## Sample Project
The GUI currently exposes one canonical sample project:
- Music Academy of the West (MAW)

MAW remains sample/reference data only and is not product-specific business logic.

## Run Instructions
1. Install GUI dependency:
   - pip install -e .[gui]
2. Launch app:
   - streamlit run apps/phase2_review_app.py

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

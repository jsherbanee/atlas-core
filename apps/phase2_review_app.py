"""Local read-only Streamlit GUI for Atlas project intake and review."""

from __future__ import annotations

import hashlib
from typing import Any

from atlas_core.services.phase2_review_context_service import (
    build_reference_project_context,
    build_uploaded_review_context,
    build_intake_review_context,
    discover_local_intake_snapshots,
)
from atlas_core.services.document_intake_service import UploadedIntakeFile


def _load_streamlit() -> Any:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Streamlit is not installed. Install with: pip install -e .[gui]"
        ) from exc

    return st


def _empty_state(st: Any, message: str) -> None:
    st.info(message)


def _to_rows(items: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        if hasattr(item, "to_dict"):
            rows.append(item.to_dict())
        elif isinstance(item, dict):
            rows.append(item)
        else:
            rows.append({"value": str(item)})

    return rows


def _uploaded_file_signature(uploaded_files: list[Any]) -> str:
    digest = hashlib.sha1()
    for file in uploaded_files:
        digest.update(str(getattr(file, "name", "")).encode("utf-8"))
        digest.update(str(getattr(file, "size", 0)).encode("utf-8"))

    return digest.hexdigest()


def _render_intake_box(st: Any) -> None:
    st.subheader("Atlas Intake")
    st.markdown("**Drag your project here**")
    st.markdown("Supported formats")
    st.markdown(
        "PDF, DOCX, DOC, XLSX, XLS, CSV, JPG, JPEG, PNG, TIFF, TXT, RTF, JSON, ZIP"
    )
    st.caption("or Browse Files")


def main() -> None:
    st = _load_streamlit()
    st.set_page_config(page_title="Atlas", layout="wide")

    st.title("Atlas")
    st.subheader("Atlas Intake")
    st.caption(
        "Upload a complete project package to run deterministic intake and project review."
    )

    source_mode = st.sidebar.radio(
        "Project",
        options=["Reference Project", "Uploaded Project"],
        index=0,
    )

    if source_mode == "Reference Project":
        st.sidebar.caption("Music Academy of the West")
        context = build_reference_project_context()
    else:
        _render_intake_box(st)
        uploaded_files = st.file_uploader(
            "Project package files",
            type=[
                "pdf",
                "docx",
                "doc",
                "xlsx",
                "xls",
                "csv",
                "jpg",
                "jpeg",
                "png",
                "tiff",
                "txt",
                "rtf",
                "json",
                "zip",
            ],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

        if uploaded_files:
            upload_signature = _uploaded_file_signature(uploaded_files)
            current_signature = st.session_state.get("atlas_upload_signature")
            if current_signature != upload_signature:
                st.session_state.pop("atlas_uploaded_context", None)
                st.session_state["atlas_upload_signature"] = upload_signature

        process_upload = st.button(
            "Run Atlas Intake",
            type="primary",
            disabled=not uploaded_files,
        )

        if process_upload and uploaded_files:
            intake_files = [
                UploadedIntakeFile(name=file.name, data=file.getvalue())
                for file in uploaded_files
            ]
            with st.spinner("Classifying files and running deterministic review..."):
                st.session_state["atlas_uploaded_context"] = (
                    build_uploaded_review_context(
                        uploaded_files=intake_files,
                    )
                )

        context = st.session_state.get("atlas_uploaded_context")
        if context is None:
            _empty_state(
                st,
                "Upload one or more project files (or a ZIP) and run Atlas Intake.",
            )
            return

    # Keep legacy snapshot mode available for existing local outputs.
    if source_mode == "Uploaded Project" and st.sidebar.checkbox(
        "Use Existing Intake Snapshot",
        value=False,
    ):
        intake_snapshots = discover_local_intake_snapshots()
        if intake_snapshots:
            snapshot_options = {
                item["label"]: item["path"] for item in intake_snapshots
            }
            selected_snapshot_label = st.sidebar.selectbox(
                "Intake Snapshot",
                options=list(snapshot_options.keys()),
                index=0,
            )
            context = build_intake_review_context(
                snapshot_options[selected_snapshot_label]
            )
        else:
            st.sidebar.warning(
                "No intake snapshots discovered under outputs/ or examples/."
            )

    review = context["review"]
    brief = context["brief"]
    revision = context["revision_comparison"]
    readiness = getattr(review, "readiness", None)
    labor = getattr(review, "labor_estimate", None)

    if source_mode == "Reference Project":
        st.info("Reference Project\nMusic Academy of the West")
    else:
        project_name = str(context.get("sample_project_name") or "Uploaded Project")
        st.success(f"Uploaded Project\n{project_name}")

    st.markdown("Data Source:")
    st.write(f"- {context.get('data_source_label', 'unknown')}")
    if context.get("data_source_mode") == "seed_fixture_fallback":
        st.warning(
            "This view is using curated seed fixture data, not the full drawing/specification package."
        )

    package_location = str(context.get("package_location") or "")
    if package_location:
        st.caption(f"Package Location: {package_location}")

    import_summary = dict(context.get("import_summary") or {})
    if import_summary:
        st.markdown("Import Summary")
        summary_rows = [
            {"metric": "total files", "value": import_summary.get("total_files", 0)},
            {"metric": "total pages", "value": import_summary.get("total_pages", 0)},
            {
                "metric": "pages with embedded text",
                "value": import_summary.get("pages_with_embedded_text", 0),
            },
            {
                "metric": "pages without embedded text",
                "value": import_summary.get("pages_without_embedded_text", 0),
            },
            {
                "metric": "documents requiring OCR",
                "value": import_summary.get("documents_requiring_ocr", 0),
            },
            {
                "metric": "drawing count",
                "value": import_summary.get("drawing_count", 0),
            },
            {
                "metric": "specification count",
                "value": import_summary.get("specification_count", 0),
            },
            {
                "metric": "schedule count",
                "value": import_summary.get("schedule_count", 0),
            },
            {
                "metric": "addenda count",
                "value": import_summary.get("addenda_count", 0),
            },
            {"metric": "image count", "value": import_summary.get("image_count", 0)},
            {
                "metric": "unsupported file count",
                "value": import_summary.get("unsupported_file_count", 0),
            },
            {
                "metric": "extraction warning count",
                "value": import_summary.get(
                    "extraction_warning_count", len(context.get("warnings") or [])
                ),
            },
        ]
        st.dataframe(summary_rows, use_container_width=True, hide_index=True)

        file_diagnostics = list(import_summary.get("file_diagnostics") or [])
        if file_diagnostics:
            st.markdown("Per-File Extraction Status")
            st.dataframe(
                [
                    {
                        "file": item.get("file_name"),
                        "group": item.get("document_group"),
                        "status": item.get("status"),
                        "pages": item.get("total_pages"),
                        "pages_with_text": item.get("pages_with_embedded_text"),
                        "pages_without_text": item.get("pages_without_embedded_text"),
                    }
                    for item in file_diagnostics
                ],
                use_container_width=True,
                hide_index=True,
            )

    if int(import_summary.get("documents_requiring_ocr", 0) or 0) > 0:
        st.warning(
            "Some files require OCR before Atlas can extract text-rich project intelligence. "
            "Atlas does not fabricate sheet/spec/equipment extraction from image-only files."
        )

    st.markdown("Extraction Warnings")
    for warning in list(context.get("warnings") or []):
        st.warning(warning)

    readiness_score = getattr(readiness, "readiness_score", None)
    readiness_level = getattr(
        getattr(readiness, "readiness_level", None), "value", None
    )

    score_col, level_col, issue_col = st.columns(3)
    score_col.metric(
        "Readiness Score",
        f"{readiness_score:.2f}" if readiness_score is not None else "n/a",
    )
    level_col.metric("Readiness Level", readiness_level or "n/a")
    issue_col.metric("Review Issues", str(review.issue_count()))

    tabs = st.tabs(
        [
            "Project Review",
            "Readiness",
            "Estimator Brief",
            "RFI Candidates",
            "Labor Estimate",
            "Revision Comparison",
            "Assumptions",
            "Evidence",
        ]
    )

    with tabs[0]:
        st.subheader("Project Overview")
        overview_rows = [
            {"field": "Project ID", "value": review.project_id},
            {"field": "Review ID", "value": review.review_id},
            {"field": "Project Name", "value": review.name},
            {"field": "Drawing Count", "value": review.drawing_count()},
            {"field": "Specification Count", "value": review.specification_count()},
            {"field": "System Count", "value": len(review.systems)},
            {"field": "Equipment Count", "value": review.equipment_count()},
            {"field": "Cross Reference Count", "value": review.cross_reference_count()},
            {"field": "Scope Gap Count", "value": review.scope_gap_count()},
            {"field": "Estimator Risk Count", "value": review.estimator_risk_count()},
            {"field": "Confidence", "value": review.confidence},
        ]
        st.dataframe(overview_rows, use_container_width=True, hide_index=True)

    with tabs[1]:
        st.subheader("Readiness")
        if readiness is None:
            _empty_state(st, "No readiness assessment available.")
        else:
            st.write(getattr(readiness, "message", ""))

            st.markdown("Section Scores")
            section_scores = getattr(readiness, "section_scores", {}) or {}
            if section_scores:
                st.dataframe(
                    [
                        {"section": section_name, "score": score}
                        for section_name, score in sorted(section_scores.items())
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                _empty_state(st, "No section scores available.")

            st.markdown("Top Blocking Issues")
            blockers = list(getattr(readiness, "blocking_issues", []) or [])
            if blockers:
                st.dataframe(
                    [{"blocking_issue": item} for item in blockers],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                _empty_state(st, "No blocking issues detected.")

            st.markdown("Warnings")
            warnings = list(getattr(readiness, "warnings", []) or [])
            if warnings:
                st.dataframe(
                    [{"warning": item} for item in warnings],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                _empty_state(st, "No warnings detected.")

    with tabs[2]:
        st.subheader("Estimator Brief")
        st.markdown(f"**Title:** {brief.brief_title}")
        st.markdown(f"**Executive Summary:** {brief.executive_summary}")

        st.markdown("Prioritized Reviewer Actions")
        actions = list(brief.prioritized_reviewer_actions or [])
        if actions:
            st.dataframe(actions, use_container_width=True, hide_index=True)
        else:
            _empty_state(st, "No prioritized reviewer actions available.")

    with tabs[3]:
        st.subheader("RFI Candidates")
        candidates = _to_rows(list(getattr(review, "rfi_candidates", []) or []))
        if candidates:
            st.dataframe(candidates, use_container_width=True, hide_index=True)
        else:
            _empty_state(st, "No RFI candidates detected.")

    with tabs[4]:
        st.subheader("Labor Estimate Summary")
        if labor is None:
            _empty_state(st, "No labor estimate is available.")
        else:
            labor_summary_rows = [
                {
                    "field": "Total Labor Hours Low",
                    "value": getattr(labor, "total_labor_hours_low", None),
                },
                {
                    "field": "Total Labor Hours Expected",
                    "value": getattr(labor, "total_labor_hours_expected", None),
                },
                {
                    "field": "Total Labor Hours High",
                    "value": getattr(labor, "total_labor_hours_high", None),
                },
                {"field": "Confidence", "value": getattr(labor, "confidence", None)},
            ]
            st.dataframe(labor_summary_rows, use_container_width=True, hide_index=True)

            categories = _to_rows(list(getattr(labor, "labor_categories", []) or []))
            st.markdown("Labor Category Breakdown")
            if categories:
                st.dataframe(categories, use_container_width=True, hide_index=True)
            else:
                _empty_state(st, "No labor category details available.")

    with tabs[5]:
        st.subheader("Revision Comparison Summary")
        if revision is None:
            _empty_state(st, "No revision comparison available for this source.")
        else:
            st.dataframe(
                [
                    {
                        "field": "Baseline Revision ID",
                        "value": revision.baseline_revision_id,
                    },
                    {
                        "field": "Comparison Revision ID",
                        "value": revision.comparison_revision_id,
                    },
                    {"field": "Change Count", "value": len(revision.changes)},
                    {"field": "Added Items", "value": len(revision.added_items)},
                    {
                        "field": "Removed Items",
                        "value": len(revision.removed_items),
                    },
                    {
                        "field": "Modified Items",
                        "value": len(revision.modified_items),
                    },
                    {
                        "field": "Labor Impact Flags",
                        "value": len(revision.labor_impact_flags),
                    },
                    {"field": "RFI Impacts", "value": len(revision.rfi_impacts)},
                    {"field": "Confidence", "value": revision.confidence},
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("Revision Changes")
            changes = _to_rows(list(revision.changes or []))
            if changes:
                st.dataframe(changes, use_container_width=True, hide_index=True)
            else:
                _empty_state(st, "No revision changes available.")

    with tabs[6]:
        st.subheader("Engineering Assumptions")
        assumptions = _to_rows(
            list(getattr(review, "engineering_assumptions", []) or [])
        )
        if assumptions:
            st.dataframe(assumptions, use_container_width=True, hide_index=True)
        else:
            _empty_state(st, "No engineering assumptions available.")

    with tabs[7]:
        st.subheader("Evidence / Source References")
        brief_refs = list(brief.evidence_refs or [])
        if brief_refs:
            st.markdown("Brief Evidence")
            st.dataframe(brief_refs, use_container_width=True, hide_index=True)
        else:
            _empty_state(st, "No estimator brief evidence references available.")

        readiness_refs = _to_rows(list(getattr(readiness, "evidence_refs", []) or []))
        if readiness_refs:
            st.markdown("Readiness Evidence")
            st.dataframe(readiness_refs, use_container_width=True, hide_index=True)
        else:
            _empty_state(st, "No readiness evidence references available.")


if __name__ == "__main__":
    main()

"""Local read-only Streamlit GUI for Phase 2 Bid Intelligence review."""

from __future__ import annotations

from typing import Any

from atlas_core.services.phase2_review_context_service import (
    build_sample_review_context,
    get_sample_projects,
)


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


def main() -> None:
    st = _load_streamlit()
    st.set_page_config(
        page_title="Atlas Phase 2 Bid Intelligence Review", layout="wide"
    )

    st.title("Atlas Phase 2 Bid Intelligence Review")
    st.caption(
        "Read-only local prototype for inspecting deterministic Phase 2 outputs."
    )

    sample_projects = get_sample_projects()
    options = {project["label"]: project["id"] for project in sample_projects}

    selected_label = st.sidebar.selectbox(
        "Sample Project",
        options=list(options.keys()),
        index=0,
    )
    st.sidebar.caption("MAW is canonical sample/reference data only.")

    context = build_sample_review_context(options[selected_label])
    review = context["review"]
    brief = context["brief"]
    revision = context["revision_comparison"]
    readiness = getattr(review, "readiness", None)
    labor = getattr(review, "labor_estimate", None)

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
            "Overview",
            "Readiness",
            "Estimator Brief",
            "RFIs",
            "Labor",
            "Revisions",
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
                {"field": "Removed Items", "value": len(revision.removed_items)},
                {"field": "Modified Items", "value": len(revision.modified_items)},
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

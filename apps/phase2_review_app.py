"""Local read-only Streamlit GUI for Atlas project workspace review."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from atlas_core.domain import Project, ProjectStatus
from atlas_core.services.document_intake_service import UploadedIntakeFile
from atlas_core.services.phase2_review_context_service import (
    DEFAULT_MAW_REFERENCE_PACKAGE,
    build_intake_review_context,
    build_reference_project_context,
    build_uploaded_review_context,
    discover_local_intake_snapshots,
)
from atlas_core.services.project_workspace_service import (
    ProjectWorkspaceRecord,
    ProjectWorkspaceService,
)


WORKSPACE_SECTIONS = [
    "Overview",
    "Executive Summary",
    "Project Files",
    "Readiness",
    "Estimator Brief",
    "RFI Candidates",
    "Labor Estimate",
    "Revision Comparison",
    "Engineering Assumptions",
    "Evidence",
]


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


def _init_session_state(st: Any) -> None:
    st.session_state.setdefault("atlas_home_mode", "recent")
    st.session_state.setdefault("atlas_active_workspace_id", None)
    st.session_state.setdefault("atlas_pending_open_path", "")
    st.session_state.setdefault("atlas_new_project_id", "")
    st.session_state.setdefault("atlas_new_project_name", "")
    st.session_state.setdefault("atlas_new_project_client", "")
    st.session_state.setdefault("atlas_new_project_location", "")
    st.session_state.setdefault("atlas_new_project_bid_date", "")


def _set_home_mode(mode: str):
    def _setter() -> None:
        st = _load_streamlit()
        st.session_state["atlas_home_mode"] = mode

    return _setter


def _set_active_workspace(st: Any, workspace_id: str) -> None:
    st.session_state["atlas_active_workspace_id"] = workspace_id
    st.session_state["atlas_home_mode"] = "workspace"


def _return_home(st: Any) -> None:
    st.session_state["atlas_active_workspace_id"] = None
    st.session_state["atlas_home_mode"] = "recent"


def _normalize_text(value: Any) -> str:
    if value is None:
        return "n/a"

    if isinstance(value, str):
        normalized = value.strip()
        return normalized or "n/a"

    if isinstance(value, list):
        items = [_normalize_text(item) for item in value]
        filtered = [item for item in items if item != "n/a"]
        return ", ".join(filtered) if filtered else "n/a"

    return str(value)


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized

    return None


def _project_profile_rows(record: ProjectWorkspaceRecord, context: dict[str, Any] | None) -> list[dict[str, Any]]:
    metadata = dict(getattr(context.get("intake_snapshot"), "metadata", {}) or {}) if context else {}
    project = record.project

    rows = [
        {"field": "Project Name", "value": _first_text(metadata.get("project_name"), metadata.get("name"), project.name) or "n/a"},
        {"field": "Project Number", "value": _first_text(metadata.get("project_number"), metadata.get("project_id"), project.project_id) or "n/a"},
        {"field": "Owner", "value": _first_text(metadata.get("owner"), metadata.get("client"), project.client) or "n/a"},
        {"field": "Architect", "value": _first_text(metadata.get("architect")) or "n/a"},
        {"field": "AV Consultant", "value": _first_text(metadata.get("av_consultant"), metadata.get("consultant_av")) or "n/a"},
        {"field": "Electrical Engineer", "value": _first_text(metadata.get("electrical_engineer"), metadata.get("consultant_electrical")) or "n/a"},
        {"field": "MEP", "value": _first_text(metadata.get("mep"), metadata.get("mep_consultant")) or "n/a"},
        {"field": "Structural", "value": _first_text(metadata.get("structural"), metadata.get("structural_engineer")) or "n/a"},
        {"field": "Campus", "value": _first_text(metadata.get("campus"), metadata.get("campus_name")) or "n/a"},
        {"field": "Building", "value": _first_text(metadata.get("building"), metadata.get("building_name")) or "n/a"},
        {"field": "Issue Date", "value": _first_text(metadata.get("issue_date")) or "n/a"},
        {"field": "Bid Date", "value": _first_text(metadata.get("bid_date"), project.bid_date) or "n/a"},
        {"field": "Revision", "value": _first_text(metadata.get("revision"), metadata.get("revision_id")) or "n/a"},
        {"field": "Addenda", "value": _normalize_text(metadata.get("addenda"))},
        {"field": "Consultants", "value": _normalize_text(metadata.get("consultants"))},
        {"field": "Stakeholders", "value": _normalize_text(metadata.get("stakeholders"))},
        {"field": "Project Status", "value": project.status.value if isinstance(project.status, ProjectStatus) else str(project.status)},
        {"field": "Source Mode", "value": context.get("data_source_label", record.source_label) if context else record.source_label},
        {"field": "Package Location", "value": record.package_location or record.source_path or "n/a"},
    ]
    return rows


def _review_summary_rows(review: Any, brief: Any, revision: Any) -> list[dict[str, Any]]:
    if review is None:
        return []

    return [
        {"field": "Review ID", "value": review.review_id},
        {"field": "Project ID", "value": review.project_id},
        {"field": "Project Name", "value": review.name},
        {"field": "Drawing Count", "value": review.drawing_count()},
        {"field": "Specification Count", "value": review.specification_count()},
        {"field": "System Count", "value": len(review.systems)},
        {"field": "Equipment Count", "value": review.equipment_count()},
        {"field": "Cross Reference Count", "value": review.cross_reference_count()},
        {"field": "Scope Gap Count", "value": review.scope_gap_count()},
        {"field": "Estimator Risk Count", "value": review.estimator_risk_count()},
        {"field": "Confidence", "value": review.confidence},
        {"field": "Readiness Score", "value": getattr(getattr(review, "readiness", None), "readiness_score", None)},
        {"field": "Readiness Level", "value": getattr(getattr(getattr(review, "readiness", None), "readiness_level", None), "value", None)},
        {"field": "Brief Title", "value": getattr(brief, "brief_title", None)},
        {"field": "Revision Changes", "value": len(getattr(revision, "changes", []) or []) if revision is not None else 0},
    ]


def _workspace_summary(record: ProjectWorkspaceRecord, context: dict[str, Any] | None) -> list[dict[str, Any]]:
    review = context.get("review") if context else None
    brief = context.get("brief") if context else None
    revision = context.get("revision_comparison") if context else None
    summary = list(_review_summary_rows(review, brief, revision))
    summary.extend(
        [
            {"field": "Workspace ID", "value": record.workspace_id},
            {"field": "Source Label", "value": record.source_label},
            {"field": "Last Opened", "value": record.last_opened_at or "n/a"},
            {"field": "Updated", "value": record.updated_at},
        ]
    )
    return summary


def _workspace_context(record: ProjectWorkspaceRecord) -> dict[str, Any] | None:
    if record.intake_snapshot_path:
        snapshot_path = Path(record.intake_snapshot_path)
        if snapshot_path.exists():
            return build_intake_review_context(snapshot_path)

    if record.package_location and record.source_mode in {
        "reference_project_real_intake",
        "seed_fixture_fallback",
    }:
        return build_reference_project_context(record.package_location)

    return None


def _build_record_from_context(
    context: dict[str, Any],
    existing_record: ProjectWorkspaceRecord | None = None,
) -> ProjectWorkspaceRecord:
    snapshot = context.get("intake_snapshot")
    metadata = dict(getattr(snapshot, "metadata", {}) or {}) if snapshot is not None else {}
    review = context.get("review")
    project_id = _first_text(
        metadata.get("project_id"),
        getattr(review, "project_id", None),
        context.get("sample_project_id"),
    ) or (existing_record.project_id if existing_record is not None else "atlas-project")
    name = _first_text(
        metadata.get("project_name"),
        metadata.get("name"),
        getattr(review, "name", None),
        context.get("sample_project_name"),
    ) or project_id
    client = _first_text(metadata.get("client"), metadata.get("owner"), name) or name

    project = Project(
        project_id=project_id,
        name=name,
        client=client,
        location=_first_text(metadata.get("location")),
        bid_date=_first_text(metadata.get("bid_date"), metadata.get("issue_date")),
        status=metadata.get("status") or ProjectStatus.INTAKE,
    )

    package_location = context.get("package_location")
    snapshot_path = None
    if package_location:
        candidate = Path(str(package_location)) / "intake_snapshot.json"
        if candidate.exists():
            snapshot_path = str(candidate)

    project_profile = {
        "project_name": _first_text(metadata.get("project_name"), metadata.get("name"), project.name),
        "project_number": _first_text(metadata.get("project_number"), metadata.get("project_id"), project.project_id),
        "owner": _first_text(metadata.get("owner"), metadata.get("client"), project.client),
        "architect": _first_text(metadata.get("architect")),
        "av_consultant": _first_text(metadata.get("av_consultant"), metadata.get("consultant_av")),
        "electrical_engineer": _first_text(metadata.get("electrical_engineer"), metadata.get("consultant_electrical")),
        "mep": _first_text(metadata.get("mep"), metadata.get("mep_consultant")),
        "structural": _first_text(metadata.get("structural"), metadata.get("structural_engineer")),
        "campus": _first_text(metadata.get("campus"), metadata.get("campus_name")),
        "building": _first_text(metadata.get("building"), metadata.get("building_name")),
        "issue_date": _first_text(metadata.get("issue_date")),
        "bid_date": _first_text(metadata.get("bid_date"), project.bid_date),
        "revision": _first_text(metadata.get("revision"), metadata.get("revision_id")),
        "addenda": metadata.get("addenda"),
        "consultants": metadata.get("consultants"),
        "stakeholders": metadata.get("stakeholders"),
    }

    return ProjectWorkspaceRecord(
        workspace_id=existing_record.workspace_id if existing_record is not None else project.project_id,
        project=project,
        source_mode=str(context.get("data_source_mode") or "manual"),
        source_label=str(context.get("data_source_label") or "Manual Project"),
        source_path=str(package_location) if package_location else None,
        intake_snapshot_path=snapshot_path,
        package_location=str(package_location) if package_location else None,
        metadata=metadata,
        import_summary=dict(context.get("import_summary") or {}),
        warnings=[str(item) for item in list(context.get("warnings") or [])],
        project_profile=project_profile,
        review_summary={
            "review_id": getattr(review, "review_id", None),
            "readiness_score": getattr(getattr(review, "readiness", None), "readiness_score", None),
            "readiness_level": getattr(getattr(getattr(review, "readiness", None), "readiness_level", None), "value", None),
            "issue_count": review.issue_count() if review is not None else 0,
            "equipment_count": review.equipment_count() if review is not None else 0,
            "rfi_count": review.rfi_candidate_count() if review is not None else 0,
            "brief_title": getattr(context.get("brief"), "brief_title", None),
        },
    )


def _load_context_for_record(record: ProjectWorkspaceRecord) -> dict[str, Any] | None:
    context = _workspace_context(record)
    if context is not None:
        return context

    if record.source_mode == "manual":
        return None

    if record.package_location:
        package_path = Path(record.package_location)
        if package_path.exists() and package_path.is_dir():
            return build_reference_project_context(package_path)

    return None


def _render_top_actions(st: Any) -> None:
    st.subheader("Atlas")
    st.caption("Local project workspace for deterministic bid intelligence review.")

    cols = st.columns(3)
    cols[0].button("+ New Project", type="primary", on_click=_set_home_mode("new"))
    cols[1].button("Open Project", on_click=_set_home_mode("open"))
    cols[2].button("Recent Projects", on_click=_set_home_mode("recent"))


def _render_new_project_form(st: Any, workspace_service: ProjectWorkspaceService) -> None:
    st.markdown("### New Project")
    with st.form("new_project_form", clear_on_submit=False):
        project_id = st.text_input(
            "Project ID",
            value=st.session_state.get("atlas_new_project_id", ""),
        )
        name = st.text_input(
            "Project Name",
            value=st.session_state.get("atlas_new_project_name", ""),
        )
        client = st.text_input(
            "Owner / Client",
            value=st.session_state.get("atlas_new_project_client", ""),
        )
        location = st.text_input(
            "Location",
            value=st.session_state.get("atlas_new_project_location", ""),
        )
        bid_date = st.text_input(
            "Bid Date",
            value=st.session_state.get("atlas_new_project_bid_date", ""),
        )

        submitted = st.form_submit_button("Create Workspace")

    if not submitted:
        return

    if not project_id.strip() or not name.strip() or not client.strip():
        st.error("Project ID, Project Name, and Owner / Client are required.")
        return

    record = workspace_service.create_manual_record(
        project_id=project_id.strip(),
        name=name.strip(),
        client=client.strip(),
        location=location.strip() or None,
        bid_date=bid_date.strip() or None,
    )
    workspace_service.save_record(record)
    _set_active_workspace(st, record.workspace_id)
    st.success(f"Created workspace for {record.project.name}.")
    st.rerun()


def _open_workspace_from_path(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    path_text: str,
) -> None:
    path = Path(path_text).expanduser()
    if not path.exists():
        st.error(f"Path not found: {path}")
        return

    if path.is_dir() and (path / "workspace.json").exists():
        record = workspace_service.load_record(path / "workspace.json")
        workspace_service.save_record(record)
        _set_active_workspace(st, record.workspace_id)
        st.rerun()
        return

    if path.name == "workspace.json":
        record = workspace_service.load_record(path)
        workspace_service.save_record(record)
        _set_active_workspace(st, record.workspace_id)
        st.rerun()
        return

    if path.name == "intake_snapshot.json":
        context = build_intake_review_context(path)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        _set_active_workspace(st, record.workspace_id)
        st.rerun()
        return

    if path.is_dir():
        context = build_reference_project_context(path)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        _set_active_workspace(st, record.workspace_id)
        st.rerun()
        return

    st.error("Open a workspace.json file, an intake_snapshot.json file, or a project folder.")


def _render_open_project_form(st: Any, workspace_service: ProjectWorkspaceService) -> None:
    st.markdown("### Open Project")
    path_text = st.text_input(
        "Workspace file, snapshot file, or project folder",
        value=st.session_state.get("atlas_pending_open_path", ""),
        placeholder="outputs/project_workspaces/example/workspace.json",
    )
    if st.button("Open"):
        st.session_state["atlas_pending_open_path"] = path_text
        _open_workspace_from_path(st, workspace_service, path_text)


def _render_recent_projects(st: Any, workspace_service: ProjectWorkspaceService) -> None:
    st.markdown("### Recent Projects")
    recent = workspace_service.list_recent_workspaces()
    if not recent:
        _empty_state(st, "No saved workspaces yet. Create a project or open a package to begin.")
        return

    for record in recent:
        with st.container(border=True):
            st.markdown(f"**{record.project.name}**")
            st.caption(f"{record.source_label} · {record.project.project_id}")
            if record.package_location:
                st.caption(record.package_location)
            st.button(
                "Open workspace",
                key=f"open_recent_{record.workspace_id}",
                on_click=_set_active_workspace,
                args=(st, record.workspace_id),
            )


def _render_home(st: Any, workspace_service: ProjectWorkspaceService) -> None:
    _render_top_actions(st)
    mode = st.session_state.get("atlas_home_mode", "recent")

    if mode == "new":
        _render_new_project_form(st, workspace_service)
    elif mode == "open":
        _render_open_project_form(st, workspace_service)
    elif mode == "recent":
        _render_recent_projects(st, workspace_service)

    st.markdown("### Reference Project")
    st.write("Music Academy of the West")
    if st.button("Open Reference Project"):
        context = build_reference_project_context(DEFAULT_MAW_REFERENCE_PACKAGE)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        _set_active_workspace(st, record.workspace_id)
        st.rerun()


def _render_upload_panel(st: Any, workspace_service: ProjectWorkspaceService) -> None:
    st.subheader("Project Files")
    st.caption("Attach a local package or ZIP to create a workspace from deterministic intake.")
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
        key="atlas_project_package_uploader",
    )

    if uploaded_files:
        upload_signature = _uploaded_file_signature(uploaded_files)
        current_signature = st.session_state.get("atlas_upload_signature")
        if current_signature != upload_signature:
            st.session_state.pop("atlas_uploaded_context", None)
            st.session_state["atlas_upload_signature"] = upload_signature

    if st.button("Run Atlas Intake", type="primary", disabled=not uploaded_files):
        intake_files = [UploadedIntakeFile(name=file.name, data=file.getvalue()) for file in uploaded_files]
        with st.spinner("Classifying files and running deterministic review..."):
            st.session_state["atlas_uploaded_context"] = build_uploaded_review_context(
                uploaded_files=intake_files,
            )
        context = st.session_state.get("atlas_uploaded_context")
        if context is not None:
            record = _build_record_from_context(context)
            workspace_service.save_record(record)
            _set_active_workspace(st, record.workspace_id)
            st.rerun()


def _render_workspace_shell(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
) -> None:
    context = _load_context_for_record(record)
    review = context.get("review") if context else None
    brief = context.get("brief") if context else None
    revision = context.get("revision_comparison") if context else None
    readiness = getattr(review, "readiness", None) if review is not None else None
    labor = getattr(review, "labor_estimate", None) if review is not None else None

    if context is not None:
        record = _build_record_from_context(context, existing_record=record)
        workspace_service.save_record(record)

    st.sidebar.header(record.project.name)
    st.sidebar.caption(record.project.project_id)
    st.sidebar.caption(record.source_label)
    st.sidebar.button("Home", on_click=_return_home, args=(st,))

    selected_section = st.sidebar.radio("Workspace", WORKSPACE_SECTIONS, index=0)

    st.title("Atlas")
    st.caption("Persistent project workspace for deterministic bid intelligence review.")
    header_cols = st.columns(3)
    header_cols[0].metric("Workspace", record.workspace_id)
    header_cols[1].metric(
        "Readiness Score",
        f"{getattr(readiness, 'readiness_score', None):.2f}"
        if getattr(readiness, "readiness_score", None) is not None
        else "n/a",
    )
    header_cols[2].metric("Review Issues", str(review.issue_count()) if review is not None else "n/a")

    st.markdown("### Project Metadata")
    st.dataframe(_project_profile_rows(record, context), use_container_width=True, hide_index=True)

    st.markdown("### Workspace Summary")
    st.dataframe(_workspace_summary(record, context), use_container_width=True, hide_index=True)

    if selected_section == "Overview":
        st.subheader("Project Overview")
        if review is None:
            _empty_state(st, "Create a workspace or attach a project package to populate Atlas outputs.")
        else:
            overview_rows = [
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

    elif selected_section == "Executive Summary":
        st.subheader("Executive Summary")
        if brief is None:
            _empty_state(st, "No estimator brief is available for this workspace.")
        else:
            st.markdown(f"**{brief.brief_title}**")
            st.write(brief.executive_summary)
            st.markdown("Prioritized Reviewer Actions")
            actions = list(brief.prioritized_reviewer_actions or [])
            if actions:
                st.dataframe(actions, use_container_width=True, hide_index=True)
            else:
                _empty_state(st, "No prioritized reviewer actions available.")

    elif selected_section == "Project Files":
        _render_upload_panel(st, workspace_service)
        if context is None:
            _empty_state(st, "No imported package is attached to this workspace yet.")
        else:
            import_summary = dict(context.get("import_summary") or {})
            st.markdown("Import Summary")
            if import_summary:
                st.dataframe(
                    [
                        {"metric": "total files", "value": import_summary.get("total_files", 0)},
                        {"metric": "total pages", "value": import_summary.get("total_pages", 0)},
                        {"metric": "pages with embedded text", "value": import_summary.get("pages_with_embedded_text", 0)},
                        {"metric": "pages with OCR-derived text", "value": import_summary.get("pages_with_ocr_text", 0)},
                        {"metric": "pages without embedded text", "value": import_summary.get("pages_without_embedded_text", 0)},
                        {"metric": "documents requiring OCR", "value": import_summary.get("documents_requiring_ocr", 0)},
                        {"metric": "drawing count", "value": import_summary.get("drawing_count", 0)},
                        {"metric": "specification count", "value": import_summary.get("specification_count", 0)},
                        {"metric": "schedule count", "value": import_summary.get("schedule_count", 0)},
                        {"metric": "addenda count", "value": import_summary.get("addenda_count", 0)},
                        {"metric": "image count", "value": import_summary.get("image_count", 0)},
                        {"metric": "unsupported file count", "value": import_summary.get("unsupported_file_count", 0)},
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            discovered_files = list((context.get("intake_snapshot").discovered_files if context.get("intake_snapshot") is not None else {}).items())
            if discovered_files:
                st.markdown("Discovered Files")
                st.dataframe(
                    [
                        {"group": group_name, "files": ", ".join(files)}
                        for group_name, files in discovered_files
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            file_diagnostics = list(import_summary.get("file_diagnostics") or [])
            if file_diagnostics:
                st.markdown("Per-File Extraction Status")
                st.dataframe(
                    [
                        {
                            "file": item.get("file_name"),
                            "group": item.get("document_group"),
                            "status": item.get("status"),
                            "mode": item.get("extraction_mode"),
                            "ocr_attempted": item.get("ocr_attempted"),
                            "pages": item.get("total_pages"),
                        }
                        for item in file_diagnostics
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

    elif selected_section == "Readiness":
        st.subheader("Readiness")
        if readiness is None:
            _empty_state(st, "No readiness assessment available.")
        else:
            st.write(getattr(readiness, "message", ""))
            section_scores = getattr(readiness, "section_scores", {}) or {}
            if section_scores:
                st.markdown("Section Scores")
                st.dataframe(
                    [
                        {"section": section_name, "score": score}
                        for section_name, score in sorted(section_scores.items())
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            blockers = list(getattr(readiness, "blocking_issues", []) or [])
            if blockers:
                st.markdown("Top Blocking Issues")
                st.dataframe(
                    [{"blocking_issue": item} for item in blockers],
                    use_container_width=True,
                    hide_index=True,
                )

            warnings = list(getattr(readiness, "warnings", []) or [])
            if warnings:
                st.markdown("Warnings")
                st.dataframe(
                    [{"warning": item} for item in warnings],
                    use_container_width=True,
                    hide_index=True,
                )

    elif selected_section == "Estimator Brief":
        st.subheader("Estimator Brief")
        if brief is None:
            _empty_state(st, "No estimator brief available.")
        else:
            st.markdown(f"**Title:** {brief.brief_title}")
            st.markdown(f"**Executive Summary:** {brief.executive_summary}")
            st.markdown("Prioritized Reviewer Actions")
            actions = list(brief.prioritized_reviewer_actions or [])
            if actions:
                st.dataframe(actions, use_container_width=True, hide_index=True)
            else:
                _empty_state(st, "No prioritized reviewer actions available.")

    elif selected_section == "RFI Candidates":
        st.subheader("RFI Candidates")
        candidates = _to_rows(list(getattr(review, "rfi_candidates", []) or [])) if review is not None else []
        if candidates:
            st.dataframe(candidates, use_container_width=True, hide_index=True)
        else:
            _empty_state(st, "No RFI candidates detected.")

    elif selected_section == "Labor Estimate":
        st.subheader("Labor Estimate Summary")
        if labor is None:
            _empty_state(st, "No labor estimate is available.")
        else:
            st.dataframe(
                [
                    {"field": "Total Labor Hours Low", "value": getattr(labor, "total_labor_hours_low", None)},
                    {"field": "Total Labor Hours Expected", "value": getattr(labor, "total_labor_hours_expected", None)},
                    {"field": "Total Labor Hours High", "value": getattr(labor, "total_labor_hours_high", None)},
                    {"field": "Confidence", "value": getattr(labor, "confidence", None)},
                ],
                use_container_width=True,
                hide_index=True,
            )
            categories = _to_rows(list(getattr(labor, "labor_categories", []) or []))
            if categories:
                st.markdown("Labor Category Breakdown")
                st.dataframe(categories, use_container_width=True, hide_index=True)

    elif selected_section == "Revision Comparison":
        st.subheader("Revision Comparison Summary")
        if revision is None:
            _empty_state(st, "No revision comparison available for this workspace.")
        else:
            st.dataframe(
                [
                    {"field": "Baseline Revision ID", "value": revision.baseline_revision_id},
                    {"field": "Comparison Revision ID", "value": revision.comparison_revision_id},
                    {"field": "Change Count", "value": len(revision.changes)},
                    {"field": "Added Items", "value": len(revision.added_items)},
                    {"field": "Removed Items", "value": len(revision.removed_items)},
                    {"field": "Modified Items", "value": len(revision.modified_items)},
                    {"field": "Labor Impact Flags", "value": len(revision.labor_impact_flags)},
                    {"field": "RFI Impacts", "value": len(revision.rfi_impacts)},
                    {"field": "Confidence", "value": revision.confidence},
                ],
                use_container_width=True,
                hide_index=True,
            )
            changes = _to_rows(list(revision.changes or []))
            if changes:
                st.markdown("Revision Changes")
                st.dataframe(changes, use_container_width=True, hide_index=True)

    elif selected_section == "Engineering Assumptions":
        st.subheader("Engineering Assumptions")
        assumptions = _to_rows(list(getattr(review, "engineering_assumptions", []) or [])) if review is not None else []
        if assumptions:
            st.dataframe(assumptions, use_container_width=True, hide_index=True)
        else:
            _empty_state(st, "No engineering assumptions available.")

    elif selected_section == "Evidence":
        st.subheader("Evidence")
        brief_refs = list(getattr(brief, "evidence_refs", []) or []) if brief is not None else []
        if brief_refs:
            st.markdown("Brief Evidence")
            st.dataframe(brief_refs, use_container_width=True, hide_index=True)
        else:
            _empty_state(st, "No estimator brief evidence references available.")

        if context is not None:
            source_refs = _to_rows(list(getattr(context.get("intake_snapshot"), "source_references", []) or []))
            if source_refs:
                st.markdown("Intake Source References")
                st.dataframe(source_refs, use_container_width=True, hide_index=True)

        readiness_refs = _to_rows(list(getattr(readiness, "evidence_refs", []) or [])) if readiness is not None else []
        if readiness_refs:
            st.markdown("Readiness Evidence")
            st.dataframe(readiness_refs, use_container_width=True, hide_index=True)


def main() -> None:
    st = _load_streamlit()
    st.set_page_config(page_title="Atlas", layout="wide")
    _init_session_state(st)

    workspace_service = ProjectWorkspaceService()
    active_workspace_id = st.session_state.get("atlas_active_workspace_id")

    if active_workspace_id:
        recent = {record.workspace_id: record for record in workspace_service.list_recent_workspaces(limit=200)}
        record = recent.get(active_workspace_id)
        if record is None:
            st.session_state["atlas_active_workspace_id"] = None
            st.session_state["atlas_home_mode"] = "recent"
        else:
            _render_workspace_shell(st, workspace_service, record)
            return

    _render_home(st, workspace_service)


if __name__ == "__main__":
    main()
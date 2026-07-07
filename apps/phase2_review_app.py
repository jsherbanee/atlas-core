"""Atlas Workspace v1 Streamlit application shell."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import subprocess
from typing import Any

from atlas_core import __version__
from atlas_core.domain import Project, ProjectStatus
from atlas_core.services.document_intake_service import UploadedIntakeFile
from atlas_core.services.phase2_review_context_service import (
    DEFAULT_MAW_REFERENCE_PACKAGE,
    build_intake_review_context,
    build_reference_project_context,
    build_uploaded_review_context,
)
from atlas_core.services.project_workspace_service import (
    ProjectWorkspaceRecord,
    ProjectWorkspaceService,
)

ACTIVE_NAVIGATION = {
    "PROJECT": [
        "Overview",
        "Executive Summary",
        "Project Files",
        "Drawings",
        "Specifications",
        "Equipment",
        "Systems",
    ],
    "BID INTELLIGENCE": [
        "Readiness",
        "Estimator Brief",
        "RFI Candidates",
        "Labor Estimate",
        "Revision Comparison",
        "Engineering Assumptions",
        "Evidence",
    ],
    "REPORTS": ["Reports", "Exports"],
    "SETTINGS": ["Project Settings", "Application Settings"],
}

DISABLED_NAVIGATION = {
    "PROJECT LIFECYCLE": [
        "Engineering",
        "Procurement",
        "Financials",
        "Construction",
        "Closeout",
        "Service",
    ]
}

SUPPORTED_UPLOAD_TYPES = [
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
]


@dataclass
class SelectorOption:
    label: str
    kind: str
    value: str | None = None


def _load_streamlit() -> Any:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Streamlit is not installed. Install with: pip install -e .[gui]"
        ) from exc

    return st


def _inject_styles(st: Any) -> None:
    st.markdown(
        """
        <style>
        .atlas-shell-title {font-size: 1.1rem; font-weight: 600; letter-spacing: 0.02rem;}
        .atlas-meta {color: #6b7280; font-size: 0.85rem;}
        .atlas-chip {padding: 2px 8px; border-radius: 999px; font-size: 0.78rem; border: 1px solid #d1d5db; display: inline-block; margin-right: 6px;}
        .atlas-muted {color: #6b7280;}
        .atlas-context h4 {margin-top: 0.2rem;}
        .atlas-statusbar {padding-top: 0.35rem; border-top: 1px solid #e5e7eb;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_session_state(st: Any) -> None:
    st.session_state.setdefault("atlas_active_workspace_id", None)
    st.session_state.setdefault("atlas_active_page", "Overview")
    st.session_state.setdefault("atlas_layout_mode", "Desktop")
    st.session_state.setdefault("atlas_navigation_collapsed", False)
    st.session_state.setdefault("atlas_project_selector", "Recent Projects")
    st.session_state.setdefault("atlas_workspace_action", "")
    st.session_state.setdefault("atlas_pending_open_path", "")
    st.session_state.setdefault("atlas_new_project_id", "")
    st.session_state.setdefault("atlas_new_project_name", "")
    st.session_state.setdefault("atlas_new_project_client", "")
    st.session_state.setdefault("atlas_new_project_location", "")
    st.session_state.setdefault("atlas_new_project_bid_date", "")
    st.session_state.setdefault("atlas_upload_signature", "")
    st.session_state.setdefault("atlas_uploaded_context", None)
    st.session_state.setdefault("atlas_context_selection", {"kind": "project"})


def _uploaded_file_signature(uploaded_files: list[Any]) -> str:
    digest = hashlib.sha1()
    for file in uploaded_files:
        digest.update(str(getattr(file, "name", "")).encode("utf-8"))
        digest.update(str(getattr(file, "size", 0)).encode("utf-8"))

    return digest.hexdigest()


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


def _first_text(*values: Any) -> str | None:
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if normalized:
            return normalized

    return None


def _safe_text(value: Any, default: str = "Unknown") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or default
    return str(value)


def _current_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return "n/a"

    return result.stdout.strip() or "n/a"


def _project_stage(record: ProjectWorkspaceRecord) -> str:
    status = record.project.status
    if isinstance(status, ProjectStatus):
        return status.value.replace("_", " ").title()
    return str(status).replace("_", " ").title()


def _project_status(
    record: ProjectWorkspaceRecord, context: dict[str, Any] | None
) -> str:
    if context is None:
        return "Unknown"

    readiness = getattr(context.get("review"), "readiness", None)
    level = getattr(getattr(readiness, "readiness_level", None), "value", None)
    return _safe_text(level, "Needs Review").title()


def _build_record_from_context(
    context: dict[str, Any],
    existing_record: ProjectWorkspaceRecord | None = None,
) -> ProjectWorkspaceRecord:
    snapshot = context.get("intake_snapshot")
    metadata = (
        dict(getattr(snapshot, "metadata", {}) or {}) if snapshot is not None else {}
    )
    review = context.get("review")

    project_id = _first_text(
        metadata.get("project_id"),
        getattr(review, "project_id", None),
        context.get("sample_project_id"),
    ) or (
        existing_record.project_id if existing_record is not None else "atlas-project"
    )

    name = (
        _first_text(
            metadata.get("project_name"),
            metadata.get("name"),
            getattr(review, "name", None),
            context.get("sample_project_name"),
            project_id,
        )
        or project_id
    )

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

    return ProjectWorkspaceRecord(
        workspace_id=(
            existing_record.workspace_id
            if existing_record is not None
            else project.project_id
        ),
        project=project,
        source_mode=str(context.get("data_source_mode") or "manual"),
        source_label=str(context.get("data_source_label") or "Manual Project"),
        source_path=str(package_location) if package_location else None,
        intake_snapshot_path=snapshot_path,
        package_location=str(package_location) if package_location else None,
        metadata=metadata,
        import_summary=dict(context.get("import_summary") or {}),
        warnings=[str(item) for item in list(context.get("warnings") or [])],
        review_summary={
            "review_id": getattr(review, "review_id", None),
            "readiness_score": getattr(
                getattr(review, "readiness", None), "readiness_score", None
            ),
            "readiness_level": getattr(
                getattr(getattr(review, "readiness", None), "readiness_level", None),
                "value",
                None,
            ),
            "issue_count": review.issue_count() if review is not None else 0,
            "confidence": getattr(review, "confidence", None),
        },
    )


def _load_context_for_record(record: ProjectWorkspaceRecord) -> dict[str, Any] | None:
    if record.intake_snapshot_path:
        snapshot_path = Path(record.intake_snapshot_path)
        if snapshot_path.exists():
            return build_intake_review_context(snapshot_path)

    if record.package_location and record.source_mode in {
        "reference_project_real_intake",
        "seed_fixture_fallback",
    }:
        return build_reference_project_context(record.package_location)

    if record.source_mode == "manual":
        return None

    return None


def _ensure_active_workspace(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    active_id = st.session_state.get("atlas_active_workspace_id")
    if active_id:
        return

    recent = workspace_service.list_recent_workspaces(limit=1)
    if recent:
        st.session_state["atlas_active_workspace_id"] = recent[0].workspace_id
        return

    context = build_reference_project_context(DEFAULT_MAW_REFERENCE_PACKAGE)
    record = _build_record_from_context(context)
    workspace_service.save_record(record)
    st.session_state["atlas_active_workspace_id"] = record.workspace_id


def _load_active_record(
    st: Any,
    workspace_service: ProjectWorkspaceService,
) -> ProjectWorkspaceRecord | None:
    active_id = st.session_state.get("atlas_active_workspace_id")
    if not active_id:
        return None

    records = {
        record.workspace_id: record
        for record in workspace_service.list_recent_workspaces(limit=500)
    }
    return records.get(active_id)


def _selector_options(recent: list[ProjectWorkspaceRecord]) -> list[SelectorOption]:
    options = [SelectorOption(label="Recent Projects", kind="category")]
    options.extend(
        SelectorOption(
            label=f"Recent · {record.project.name}",
            kind="recent",
            value=record.workspace_id,
        )
        for record in recent[:15]
    )
    options.append(SelectorOption(label="Reference Projects", kind="category"))
    options.append(
        SelectorOption(
            label="Reference Project · Music Academy of the West [Reference]",
            kind="reference",
            value="maw-reference",
        )
    )
    options.append(SelectorOption(label="Create New Project", kind="create"))
    options.append(SelectorOption(label="Open Existing Project", kind="open"))
    return options


def _apply_selector_choice(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    selected_label: str,
    options: list[SelectorOption],
) -> None:
    choice = next((item for item in options if item.label == selected_label), None)
    if choice is None:
        return

    if choice.kind == "recent" and choice.value:
        st.session_state["atlas_active_workspace_id"] = choice.value
        st.session_state["atlas_workspace_action"] = ""
    elif choice.kind == "reference":
        context = build_reference_project_context(DEFAULT_MAW_REFERENCE_PACKAGE)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_workspace_action"] = ""
    elif choice.kind in {"create", "open"}:
        st.session_state["atlas_workspace_action"] = choice.kind


def _render_header(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    recent = workspace_service.list_recent_workspaces(limit=25)
    options = _selector_options(recent)
    labels = [item.label for item in options]

    if st.session_state.get("atlas_project_selector") not in labels:
        st.session_state["atlas_project_selector"] = labels[0]

    st.markdown("<div class='atlas-shell-title'>Atlas</div>", unsafe_allow_html=True)
    header_cols = st.columns([2.9, 2.8, 3.3, 0.9, 0.9, 1.2, 1.4, 1.8, 1.8])

    selected = header_cols[0].selectbox(
        "Current Project",
        options=labels,
        index=labels.index(st.session_state["atlas_project_selector"]),
        key="atlas_project_selector",
    )
    _apply_selector_choice(st, workspace_service, selected, options)

    header_cols[1].selectbox(
        "Layout",
        options=["Desktop", "Tablet", "Mobile"],
        key="atlas_layout_mode",
    )

    header_cols[2].text_input(
        "Global Search", value="", placeholder="Search (coming soon)"
    )
    header_cols[3].button("Notifications", disabled=True, use_container_width=True)
    header_cols[4].button("Settings", use_container_width=True)
    header_cols[5].selectbox(
        "Profile",
        options=["User"],
        index=0,
        label_visibility="visible",
    )

    version_text = f"Atlas v{__version__}"
    stage_text = f"Stage: {_project_stage(record)}"
    status_text = f"Status: {_project_status(record, context)}"
    header_cols[6].markdown(
        f"<div class='atlas-meta'>{version_text}</div>", unsafe_allow_html=True
    )
    header_cols[7].markdown(
        f"<div class='atlas-meta'>{stage_text}</div>", unsafe_allow_html=True
    )
    header_cols[8].markdown(
        f"<div class='atlas-meta'>{status_text}</div>", unsafe_allow_html=True
    )


def _render_navigation_controls(st: Any, container: Any, mode: str) -> None:
    container.markdown("### Navigation")

    active_page = st.session_state.get("atlas_active_page", "Overview")

    for group_name, pages in ACTIVE_NAVIGATION.items():
        with container.expander(group_name, expanded=active_page in pages):
            for page in pages:
                if container.button(
                    page,
                    key=f"atlas_nav_{mode}_{group_name}_{page}",
                    use_container_width=True,
                    type="primary" if active_page == page else "secondary",
                ):
                    st.session_state["atlas_active_page"] = page

    for group_name, pages in DISABLED_NAVIGATION.items():
        with container.expander(group_name, expanded=False):
            for page in pages:
                container.button(
                    f"{page} · Coming Soon",
                    disabled=True,
                    key=f"atlas_nav_disabled_{mode}_{group_name}_{page}",
                    use_container_width=True,
                )


def _set_context_selection(st: Any, kind: str, data: dict[str, Any]) -> None:
    st.session_state["atlas_context_selection"] = {"kind": kind, "data": data}


def _render_quick_actions(st: Any) -> None:
    st.markdown("Quick Actions")
    cols = st.columns(4)
    if cols[0].button("Open Project Files", use_container_width=True):
        st.session_state["atlas_active_page"] = "Project Files"
    if cols[1].button("Review Readiness", use_container_width=True):
        st.session_state["atlas_active_page"] = "Readiness"
    if cols[2].button("Open Executive Summary", use_container_width=True):
        st.session_state["atlas_active_page"] = "Executive Summary"
    if cols[3].button("Review RFIs", use_container_width=True):
        st.session_state["atlas_active_page"] = "RFI Candidates"


def _render_overview_page(
    st: Any, record: ProjectWorkspaceRecord, context: dict[str, Any] | None
) -> None:
    st.subheader("Mission Control")
    review = context.get("review") if context else None
    readiness = getattr(review, "readiness", None) if review is not None else None
    import_summary = dict(context.get("import_summary") or {}) if context else {}
    metadata = (
        dict(getattr(context.get("intake_snapshot"), "metadata", {}) or {})
        if context
        else {}
    )

    cards = st.columns(4)
    cards[0].metric("Project Name", record.project.name)
    cards[1].metric("Lifecycle Stage", _project_stage(record))
    cards[2].metric("Project Status", _project_status(record, context))
    cards[3].metric(
        "Import Status",
        context.get("data_source_label", "Manual") if context else "Manual",
    )

    cards2 = st.columns(4)
    cards2[0].metric(
        "Readiness Score",
        (
            f"{getattr(readiness, 'readiness_score', None):.2f}"
            if getattr(readiness, "readiness_score", None) is not None
            else "n/a"
        ),
    )
    cards2[1].metric(
        "Readiness Level",
        _safe_text(
            getattr(getattr(readiness, "readiness_level", None), "value", None), "n/a"
        ).title(),
    )
    cards2[2].metric("Confidence", str(getattr(review, "confidence", "n/a")))
    cards2[3].metric(
        "Top Risks",
        str(len(getattr(review, "estimator_risks", []) or [])) if review else "0",
    )

    profile_rows = [
        (
            "Owner",
            _safe_text(
                _first_text(
                    metadata.get("owner"), metadata.get("client"), record.project.client
                )
            ),
        ),
        ("Architect", _safe_text(metadata.get("architect"))),
        (
            "Consultants",
            (
                _safe_text(metadata.get("consultants"), "n/a")
                if metadata.get("consultants")
                else "n/a"
            ),
        ),
        (
            "Project Number",
            _safe_text(
                _first_text(
                    metadata.get("project_number"),
                    metadata.get("project_id"),
                    record.project.project_id,
                )
            ),
        ),
        ("Issue Date", _safe_text(metadata.get("issue_date"))),
        (
            "Bid Date",
            _safe_text(_first_text(metadata.get("bid_date"), record.project.bid_date)),
        ),
    ]
    st.dataframe(
        [{"field": field, "value": value} for field, value in profile_rows],
        use_container_width=True,
        hide_index=True,
    )

    risk_rows = [
        {"risk": item.get("title", "risk"), "level": item.get("risk_level", "unknown")}
        for item in _to_rows(list(getattr(review, "estimator_risks", []) or []))[:5]
    ]
    if risk_rows:
        st.markdown("Top Risks")
        st.dataframe(risk_rows, use_container_width=True, hide_index=True)

    recent_activity = [
        {
            "event": "Workspace opened",
            "timestamp": record.last_opened_at or record.updated_at,
        },
        {
            "event": "Last intake",
            "timestamp": _safe_text(import_summary.get("package_location"), "n/a"),
        },
        {
            "event": "Last review",
            "timestamp": record.updated_at,
        },
    ]
    st.markdown("Recent Activity")
    st.dataframe(recent_activity, use_container_width=True, hide_index=True)

    if import_summary:
        st.markdown("Import Summary")
        st.dataframe(
            [
                {
                    "metric": "total files",
                    "value": import_summary.get("total_files", 0),
                },
                {
                    "metric": "total pages",
                    "value": import_summary.get("total_pages", 0),
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
            ],
            use_container_width=True,
            hide_index=True,
        )

    _render_quick_actions(st)


def _render_executive_summary_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Executive Summary")
    if context is None:
        st.info("No review context available for this project.")
        return

    review = context.get("review")
    brief = context.get("brief")
    readiness = getattr(review, "readiness", None) if review is not None else None
    import_summary = dict(context.get("import_summary") or {})

    row1 = st.columns(3)
    row1[0].metric(
        "Overall Health",
        _safe_text(
            getattr(getattr(readiness, "readiness_level", None), "value", None), "n/a"
        ).title(),
    )
    row1[1].metric(
        "Critical Risks", str(len(getattr(review, "estimator_risks", []) or []))
    )
    row1[2].metric(
        "High Priority RFIs", str(len(getattr(review, "rfi_candidates", []) or []))
    )

    row2 = st.columns(3)
    row2[0].metric(
        "Labor Confidence",
        str(getattr(getattr(review, "labor_estimate", None), "confidence", "n/a")),
    )
    row2[1].metric("Scope Gaps", str(getattr(review, "scope_gap_count", lambda: 0)()))
    row2[2].metric(
        "Documents Requiring OCR", str(import_summary.get("documents_requiring_ocr", 0))
    )

    st.markdown("Critical Risks")
    risk_rows = _to_rows(list(getattr(review, "estimator_risks", []) or []))[:8]
    if risk_rows:
        st.dataframe(risk_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No critical risks detected.")

    st.markdown("Recommended Next Actions")
    actions = list(getattr(brief, "prioritized_reviewer_actions", []) or [])
    if actions:
        st.dataframe(actions, use_container_width=True, hide_index=True)
    else:
        st.info("No prioritized reviewer actions available.")


def _files_by_folder(context: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    folder_map: dict[str, list[dict[str, Any]]] = {
        "Drawings": [],
        "Specifications": [],
        "Schedules": [],
        "Addenda": [],
        "Images": [],
        "Other": [],
    }
    if context is None:
        return folder_map

    import_summary = dict(context.get("import_summary") or {})
    diagnostics = list(import_summary.get("file_diagnostics") or [])
    source_refs = list(
        getattr(context.get("intake_snapshot"), "source_references", []) or []
    )

    for item in diagnostics:
        group = str(item.get("document_group") or "unsupported").lower()
        if group == "drawings":
            folder = "Drawings"
        elif group == "specifications":
            folder = "Specifications"
        elif group == "schedules":
            folder = "Schedules"
        elif group == "addenda":
            folder = "Addenda"
        elif group == "images":
            folder = "Images"
        else:
            folder = "Other"

        file_name = str(item.get("file_name") or "unknown")
        ref_count = sum(
            1
            for ref in source_refs
            if Path(str(ref.get("source_file") or "")).name == file_name
        )
        warnings = item.get("warnings") or []
        folder_map[folder].append(
            {
                "filename": file_name,
                "revision": "unknown",
                "status": _safe_text(item.get("status"), "unknown"),
                "pages": item.get("total_pages"),
                "references": ref_count,
                "warnings": len(list(warnings)),
                "group": folder,
            }
        )

    return folder_map


def _render_upload_panel(st: Any, workspace_service: ProjectWorkspaceService) -> None:
    uploaded_files = st.file_uploader(
        "Upload package files",
        type=SUPPORTED_UPLOAD_TYPES,
        accept_multiple_files=True,
        help="Upload one or more files or a ZIP package to run Atlas Intake.",
    )

    if uploaded_files:
        signature = _uploaded_file_signature(uploaded_files)
        if st.session_state.get("atlas_upload_signature") != signature:
            st.session_state["atlas_upload_signature"] = signature
            st.session_state.pop("atlas_uploaded_context", None)

    if st.button("Run Atlas Intake", type="primary", disabled=not uploaded_files):
        intake_files = [
            UploadedIntakeFile(name=file.name, data=file.getvalue())
            for file in uploaded_files or []
        ]
        with st.spinner("Running deterministic intake and review..."):
            st.session_state["atlas_uploaded_context"] = build_uploaded_review_context(
                uploaded_files=intake_files
            )

        context = st.session_state.get("atlas_uploaded_context")
        if context is not None:
            record = _build_record_from_context(context)
            workspace_service.save_record(record)
            st.session_state["atlas_active_workspace_id"] = record.workspace_id
            st.success("Atlas Intake completed and workspace updated.")
            st.rerun()


def _render_project_files_page(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Project Files")
    _render_upload_panel(st, workspace_service)

    folders = _files_by_folder(context)
    folder_name = st.selectbox("Folder", options=list(folders.keys()))
    records = folders.get(folder_name, [])

    if records:
        st.dataframe(records, use_container_width=True, hide_index=True)
        file_names = [str(item.get("filename") or "") for item in records]
        selected_file = st.selectbox(
            "Select file",
            options=file_names,
            key=f"atlas_file_selector_{folder_name}",
        )
        selected = next(
            (item for item in records if str(item.get("filename")) == selected_file),
            None,
        )
        if selected is not None:
            _set_context_selection(
                st,
                "file",
                {"folder": folder_name, "file": selected},
            )
    else:
        st.info("No files found in this folder.")


def _render_drawings_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Drawings")
    if context is None:
        st.info("No drawing context available.")
        return

    review = context.get("review")
    rows = _to_rows(list(getattr(review, "drawing_sheets", []) or []))
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        labels = [
            _safe_text(
                item.get("sheet_number"), _safe_text(item.get("source_file"), "Drawing")
            )
            for item in rows
        ]
        selected = st.selectbox("Drawing", options=labels)
        item = rows[labels.index(selected)]
        _set_context_selection(st, "drawing", item)
        return

    discovered = list(
        (getattr(context.get("intake_snapshot"), "discovered_files", {}) or {}).get(
            "drawings", []
        )
    )
    if discovered:
        st.dataframe(
            [{"drawing_file": name} for name in discovered],
            use_container_width=True,
            hide_index=True,
        )
        selected = st.selectbox("Drawing file", options=discovered)
        _set_context_selection(st, "drawing", {"source_file": selected})
    else:
        st.info("No drawings discovered.")


def _render_specifications_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Specifications")
    if context is None:
        st.info("No specification context available.")
        return

    review = context.get("review")
    rows = _to_rows(list(getattr(review, "specification_sections", []) or []))
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        labels = [
            _safe_text(
                item.get("section_number"),
                _safe_text(item.get("source_file"), "Specification"),
            )
            for item in rows
        ]
        selected = st.selectbox("Specification", options=labels)
        _set_context_selection(st, "specification", rows[labels.index(selected)])
    else:
        discovered = list(
            (getattr(context.get("intake_snapshot"), "discovered_files", {}) or {}).get(
                "specifications", []
            )
        )
        if discovered:
            st.dataframe(
                [{"specification_file": name} for name in discovered],
                use_container_width=True,
                hide_index=True,
            )
            selected = st.selectbox("Specification file", options=discovered)
            _set_context_selection(st, "specification", {"source_file": selected})
        else:
            st.info("No specifications discovered.")


def _render_equipment_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Equipment")
    review = context.get("review") if context else None
    rows = _to_rows(list(getattr(review, "equipment", []) or []))
    if not rows:
        st.info("No equipment detected.")
        return

    st.dataframe(rows, use_container_width=True, hide_index=True)
    labels = [
        f"{_safe_text(item.get('equipment_id'), 'item')} · {_safe_text(item.get('description'), '')}"
        for item in rows
    ]
    selected = st.selectbox("Equipment", options=labels)
    _set_context_selection(st, "equipment", rows[labels.index(selected)])


def _render_systems_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Systems")
    review = context.get("review") if context else None
    rows = _to_rows(list(getattr(review, "systems", []) or []))
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        labels = [
            f"{_safe_text(item.get('system_id'), 'system')} · {_safe_text(item.get('name'), '')}"
            for item in rows
        ]
        selected = st.selectbox("System", options=labels)
        _set_context_selection(st, "system", rows[labels.index(selected)])
    else:
        st.info("No systems detected.")


def _render_bid_page(st: Any, page: str, context: dict[str, Any] | None) -> None:
    review = context.get("review") if context else None
    brief = context.get("brief") if context else None
    revision = context.get("revision_comparison") if context else None
    readiness = getattr(review, "readiness", None) if review is not None else None
    labor = getattr(review, "labor_estimate", None) if review is not None else None

    if page == "Readiness":
        st.subheader("Readiness")
        if readiness is None:
            st.info("No readiness assessment available.")
            return
        st.write(getattr(readiness, "message", ""))
        section_scores = getattr(readiness, "section_scores", {}) or {}
        if section_scores:
            st.dataframe(
                [
                    {"section": key, "score": value}
                    for key, value in sorted(section_scores.items())
                ],
                use_container_width=True,
                hide_index=True,
            )
        blockers = list(getattr(readiness, "blocking_issues", []) or [])
        if blockers:
            st.markdown("Blocking Issues")
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
        return

    if page == "Estimator Brief":
        st.subheader("Estimator Brief")
        if brief is None:
            st.info("No estimator brief available.")
            return
        st.markdown(f"**{brief.brief_title}**")
        st.write(brief.executive_summary)
        actions = list(brief.prioritized_reviewer_actions or [])
        if actions:
            st.dataframe(actions, use_container_width=True, hide_index=True)
        return

    if page == "RFI Candidates":
        st.subheader("RFI Candidates")
        rows = (
            _to_rows(list(getattr(review, "rfi_candidates", []) or []))
            if review
            else []
        )
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No RFI candidates detected.")
        return

    if page == "Labor Estimate":
        st.subheader("Labor Estimate")
        if labor is None:
            st.info("No labor estimate available.")
            return
        st.dataframe(
            [
                {
                    "field": "Total Labor Hours Expected",
                    "value": getattr(labor, "total_labor_hours_expected", None),
                },
                {
                    "field": "Confidence",
                    "value": getattr(labor, "confidence", None),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )
        categories = _to_rows(list(getattr(labor, "labor_categories", []) or []))
        if categories:
            st.dataframe(categories, use_container_width=True, hide_index=True)
        return

    if page == "Revision Comparison":
        st.subheader("Revision Comparison")
        if revision is None:
            st.info("No revision comparison available.")
            return
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
            ],
            use_container_width=True,
            hide_index=True,
        )
        changes = _to_rows(list(revision.changes or []))
        if changes:
            st.dataframe(changes, use_container_width=True, hide_index=True)
        return

    if page == "Engineering Assumptions":
        st.subheader("Engineering Assumptions")
        rows = (
            _to_rows(list(getattr(review, "engineering_assumptions", []) or []))
            if review
            else []
        )
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No engineering assumptions available.")
        return

    if page == "Evidence":
        st.subheader("Evidence")
        brief_refs = list(getattr(brief, "evidence_refs", []) or []) if brief else []
        if brief_refs:
            st.markdown("Brief Evidence")
            st.dataframe(brief_refs, use_container_width=True, hide_index=True)

        source_refs = (
            _to_rows(
                list(
                    getattr(context.get("intake_snapshot"), "source_references", [])
                    or []
                )
            )
            if context
            else []
        )
        if source_refs:
            st.markdown("Source References")
            st.dataframe(source_refs, use_container_width=True, hide_index=True)
        return


def _render_reports_page(st: Any, page: str) -> None:
    st.subheader(page)
    if page == "Reports":
        st.info(
            "Reporting workspace is planned. Core bid intelligence outputs remain available in current sections."
        )
    else:
        st.info(
            "Export workspace is planned. Use current deterministic exports from existing workflows."
        )


def _render_settings_page(st: Any, page: str) -> None:
    st.subheader(page)
    if page == "Project Settings":
        st.info(
            "Project settings controls are scaffolded in Workspace v1 and will expand in later phases."
        )
    else:
        st.info("Application settings controls are scaffolded in Workspace v1.")


def _render_workspace_action_panel(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    action = st.session_state.get("atlas_workspace_action", "")
    if action == "create":
        with st.expander("Create New Project", expanded=True):
            with st.form("atlas_create_project_form", clear_on_submit=False):
                project_id = st.text_input("Project ID", key="atlas_new_project_id")
                name = st.text_input("Project Name", key="atlas_new_project_name")
                client = st.text_input("Owner / Client", key="atlas_new_project_client")
                location = st.text_input("Location", key="atlas_new_project_location")
                bid_date = st.text_input("Bid Date", key="atlas_new_project_bid_date")
                submitted = st.form_submit_button("Create")

            if submitted:
                if not project_id.strip() or not name.strip() or not client.strip():
                    st.error(
                        "Project ID, Project Name, and Owner / Client are required."
                    )
                else:
                    record = workspace_service.create_manual_record(
                        project_id=project_id.strip(),
                        name=name.strip(),
                        client=client.strip(),
                        location=location.strip() or None,
                        bid_date=bid_date.strip() or None,
                    )
                    workspace_service.save_record(record)
                    st.session_state["atlas_active_workspace_id"] = record.workspace_id
                    st.session_state["atlas_workspace_action"] = ""
                    st.success(f"Created project workspace for {record.project.name}.")
                    st.rerun()

    if action == "open":
        with st.expander("Open Existing Project", expanded=True):
            path_text = st.text_input(
                "Workspace file, snapshot file, or project folder",
                key="atlas_pending_open_path",
                placeholder="outputs/project_workspaces/example/workspace.json",
            )
            if st.button("Open Path", use_container_width=True):
                path = Path(path_text).expanduser()
                if not path.exists():
                    st.error(f"Path not found: {path}")
                elif path.is_dir() and (path / "workspace.json").exists():
                    record = workspace_service.load_record(path / "workspace.json")
                    workspace_service.save_record(record)
                    st.session_state["atlas_active_workspace_id"] = record.workspace_id
                    st.session_state["atlas_workspace_action"] = ""
                    st.rerun()
                elif path.name == "workspace.json":
                    record = workspace_service.load_record(path)
                    workspace_service.save_record(record)
                    st.session_state["atlas_active_workspace_id"] = record.workspace_id
                    st.session_state["atlas_workspace_action"] = ""
                    st.rerun()
                elif path.name == "intake_snapshot.json":
                    context = build_intake_review_context(path)
                    record = _build_record_from_context(context)
                    workspace_service.save_record(record)
                    st.session_state["atlas_active_workspace_id"] = record.workspace_id
                    st.session_state["atlas_workspace_action"] = ""
                    st.rerun()
                elif path.is_dir():
                    context = build_reference_project_context(path)
                    record = _build_record_from_context(context)
                    workspace_service.save_record(record)
                    st.session_state["atlas_active_workspace_id"] = record.workspace_id
                    st.session_state["atlas_workspace_action"] = ""
                    st.rerun()
                else:
                    st.error(
                        "Open a workspace.json file, an intake_snapshot.json file, or a project folder."
                    )


def _render_main_content(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_workspace_action_panel(st, workspace_service)

    page = st.session_state.get("atlas_active_page", "Overview")
    if page == "Overview":
        _render_overview_page(st, record, context)
    elif page == "Executive Summary":
        _render_executive_summary_page(st, context)
    elif page == "Project Files":
        _render_project_files_page(st, workspace_service, context)
    elif page == "Drawings":
        _render_drawings_page(st, context)
    elif page == "Specifications":
        _render_specifications_page(st, context)
    elif page == "Equipment":
        _render_equipment_page(st, context)
    elif page == "Systems":
        _render_systems_page(st, context)
    elif page in ACTIVE_NAVIGATION["BID INTELLIGENCE"]:
        _render_bid_page(st, page, context)
    elif page in ACTIVE_NAVIGATION["REPORTS"]:
        _render_reports_page(st, page)
    elif page in ACTIVE_NAVIGATION["SETTINGS"]:
        _render_settings_page(st, page)


def _render_context_panel(st: Any, context: dict[str, Any] | None) -> None:
    st.markdown("<div class='atlas-context'>", unsafe_allow_html=True)
    st.markdown("### Context Panel")

    selection = dict(
        st.session_state.get("atlas_context_selection") or {"kind": "project"}
    )
    kind = str(selection.get("kind") or "project")
    data = dict(selection.get("data") or {})

    review = context.get("review") if context else None

    if kind == "file":
        file_data = dict(data.get("file") or {})
        st.markdown(f"#### {_safe_text(file_data.get('filename'))}")
        st.dataframe(
            [
                {"field": "Folder", "value": _safe_text(file_data.get("group"))},
                {"field": "Status", "value": _safe_text(file_data.get("status"))},
                {"field": "Pages", "value": file_data.get("pages")},
                {"field": "References", "value": file_data.get("references")},
                {"field": "Warnings", "value": file_data.get("warnings")},
            ],
            use_container_width=True,
            hide_index=True,
        )

        if str(file_data.get("group", "")).lower() == "drawings" and review is not None:
            equipment = [
                item
                for item in _to_rows(list(getattr(review, "equipment", []) or []))
                if _safe_text(item.get("drawing_reference"), "").lower() != ""
            ]
            if equipment:
                st.markdown("Equipment")
                st.dataframe(equipment[:8], use_container_width=True, hide_index=True)

        st.markdown("Revision History")
        st.info("Revision timeline will be added in a future phase.")

    elif kind == "drawing":
        st.markdown("#### Drawing")
        st.dataframe([data], use_container_width=True, hide_index=True)
        if review is not None:
            related_equipment = [
                item
                for item in _to_rows(list(getattr(review, "equipment", []) or []))
                if _safe_text(item.get("drawing_reference"), "").strip()
            ]
            if related_equipment:
                st.markdown("Equipment")
                st.dataframe(
                    related_equipment[:8], use_container_width=True, hide_index=True
                )

            st.markdown("RFIs")
            rfi_rows = _to_rows(list(getattr(review, "rfi_candidates", []) or []))
            if rfi_rows:
                st.dataframe(rfi_rows[:5], use_container_width=True, hide_index=True)

    elif kind == "specification":
        st.markdown("#### Specification")
        st.dataframe([data], use_container_width=True, hide_index=True)
        if review is not None:
            related = [
                item
                for item in _to_rows(list(getattr(review, "equipment", []) or []))
                if _safe_text(item.get("specification_reference"), "").strip()
            ]
            if related:
                st.markdown("Equipment")
                st.dataframe(related[:8], use_container_width=True, hide_index=True)

            systems = _to_rows(list(getattr(review, "systems", []) or []))
            if systems:
                st.markdown("Systems")
                st.dataframe(systems[:8], use_container_width=True, hide_index=True)

    elif kind == "equipment":
        st.markdown("#### Equipment")
        st.dataframe([data], use_container_width=True, hide_index=True)
        st.markdown("Drawing References")
        st.write(_safe_text(data.get("drawing_reference"), "n/a"))
        st.markdown("Specifications")
        st.write(_safe_text(data.get("specification_reference"), "n/a"))
        st.markdown("Manufacturer")
        st.write(_safe_text(data.get("manufacturer"), "n/a"))
        st.markdown("Risks")
        st.write("Risk links are derived from readiness and estimator risk outputs.")

    else:
        st.markdown("#### Project")
        if context is None:
            st.info("Select a project element to view contextual details.")
        else:
            st.dataframe(
                [
                    {
                        "field": "Data Source",
                        "value": _safe_text(context.get("data_source_label"), "Manual"),
                    },
                    {
                        "field": "Package Location",
                        "value": _safe_text(context.get("package_location"), "n/a"),
                    },
                    {
                        "field": "Warnings",
                        "value": len(list(context.get("warnings") or [])),
                    },
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_status_bar(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.markdown("<div class='atlas-statusbar'></div>", unsafe_allow_html=True)
    last_intake = _safe_text(
        context.get("package_location") if context else None, "n/a"
    )
    last_review = record.updated_at
    commit = _current_commit()

    cols = st.columns(5)
    cols[0].caption(f"Current project: {record.project.name}")
    cols[1].caption(f"Lifecycle stage: {_project_stage(record)}")
    cols[2].caption(f"Last intake: {last_intake}")
    cols[3].caption(f"Last review: {last_review}")
    cols[4].caption(f"Atlas v{__version__} · commit {commit}")


def _render_shell(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_header(st, workspace_service, record, context)

    layout_mode = st.session_state.get("atlas_layout_mode", "Desktop")
    nav_collapsed = bool(st.session_state.get("atlas_navigation_collapsed", False))

    if layout_mode == "Desktop":
        nav_col, main_col, context_col = st.columns([2.4, 6.2, 2.4])
        with nav_col:
            _render_navigation_controls(st, st, "desktop")
        with main_col:
            _render_main_content(st, workspace_service, record, context)
        with context_col:
            _render_context_panel(st, context)
    elif layout_mode == "Tablet":
        toolbar = st.columns([2.3, 7.7])
        with toolbar[0]:
            st.checkbox("Collapse Sidebar", key="atlas_navigation_collapsed")
        if nav_collapsed:
            main_col, context_col = st.columns([7.2, 2.8])
            with main_col:
                nav_popover = st.popover("Navigation")
                _render_navigation_controls(st, nav_popover, "tablet")
                _render_main_content(st, workspace_service, record, context)
            with context_col:
                _render_context_panel(st, context)
        else:
            nav_col, main_col, context_col = st.columns([2.4, 5.6, 2.0])
            with nav_col:
                _render_navigation_controls(st, st, "tablet")
            with main_col:
                _render_main_content(st, workspace_service, record, context)
            with context_col:
                _render_context_panel(st, context)
    else:
        drawer = st.popover("Open Navigation")
        _render_navigation_controls(st, drawer, "mobile")
        main_col, context_col = st.columns([6.8, 3.2])
        with main_col:
            _render_main_content(st, workspace_service, record, context)
        with context_col:
            _render_context_panel(st, context)

    _render_status_bar(st, record, context)


def main() -> None:
    st = _load_streamlit()
    st.set_page_config(page_title="Atlas Workspace", layout="wide")
    _inject_styles(st)
    _init_session_state(st)

    workspace_service = ProjectWorkspaceService()
    _ensure_active_workspace(st, workspace_service)

    active_record = _load_active_record(st, workspace_service)
    if active_record is None:
        st.error("No active workspace was found. Open or create a project.")
        return

    context = _load_context_for_record(active_record)
    if context is not None:
        active_record = _build_record_from_context(
            context, existing_record=active_record
        )
        workspace_service.save_record(active_record)

    _render_shell(st, workspace_service, active_record, context)


if __name__ == "__main__":
    main()

"""Atlas Workspace v1.5 project-centric shell for Phase 2 review outputs."""

from __future__ import annotations

from collections import defaultdict
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

PROJECT_MANAGER_PAGES = [
    "Home",
    "Projects",
    "Reference Projects",
    "Recent Projects",
    "Create New Project",
    "Open Existing Project",
]

PROJECT_PAGES = [
    "Overview",
    "Executive Summary",
    "Project Files",
    "Drawings",
    "Specifications",
    "Equipment",
    "Systems",
]

BID_INTELLIGENCE_PAGES = [
    "Readiness",
    "Estimator Brief",
    "RFI Candidates",
    "Labor Estimate",
    "Revision Comparison",
    "Engineering Assumptions",
    "Evidence",
]

DISABLED_LIFECYCLE_PAGES = [
    "Engineering",
    "Procurement",
    "Financials",
    "Construction",
    "Closeout",
    "Service",
]

REPORT_PAGES = ["Reports", "Exports"]
SETTINGS_PAGES = ["Project Settings", "Application Settings"]

ALL_ACTIVE_PAGES = (
    PROJECT_MANAGER_PAGES
    + PROJECT_PAGES
    + BID_INTELLIGENCE_PAGES
    + REPORT_PAGES
    + SETTINGS_PAGES
)

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
        :root {
            --atlas-gray: #6b7280;
            --atlas-blue: #2563eb;
            --atlas-green: #16a34a;
            --atlas-amber: #d97706;
            --atlas-red: #dc2626;
        }
        .atlas-title {
            font-size: 1.12rem;
            font-weight: 650;
            letter-spacing: 0.02rem;
            margin-bottom: 0.2rem;
        }
        .atlas-muted {
            color: var(--atlas-gray);
            font-size: 0.86rem;
        }
        .atlas-breadcrumb {
            color: var(--atlas-gray);
            font-size: 0.82rem;
            margin-bottom: 0.4rem;
        }
        .atlas-card {
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 0.55rem 0.7rem;
            margin-bottom: 0.45rem;
            background: #ffffff;
        }
        .atlas-card-title {
            color: var(--atlas-gray);
            font-size: 0.76rem;
            margin-bottom: 0.2rem;
        }
        .atlas-card-value {
            font-size: 1.02rem;
            font-weight: 600;
        }
        .atlas-statusbar {
            border-top: 1px solid #e5e7eb;
            margin-top: 0.7rem;
            padding-top: 0.4rem;
        }
        .atlas-chip {
            border-radius: 999px;
            padding: 2px 8px;
            border: 1px solid #d1d5db;
            font-size: 0.75rem;
            display: inline-block;
            margin-right: 4px;
            margin-top: 2px;
        }
        .atlas-object-card {
            border: 1px solid #dbe3ee;
            border-radius: 12px;
            padding: 0.55rem 0.7rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            transition: all 120ms ease-in-out;
        }
        .atlas-object-card:hover {
            border-color: #93c5fd;
            box-shadow: 0 2px 10px rgba(37, 99, 235, 0.12);
        }
        .atlas-object-header {
            font-size: 0.82rem;
            color: #334155;
            font-weight: 600;
            margin-bottom: 0.15rem;
        }
        .atlas-loading {
            color: #1d4ed8;
            font-size: 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _status_chip(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"healthy", "ready", "high", "extracted", "green"}:
        return "🟢 " + value
    if normalized in {"processing", "in progress", "blue"}:
        return "🔵 " + value
    if normalized in {"needs review", "warning", "partial", "amber"}:
        return "🟠 " + value
    if normalized in {"critical", "failed", "requires_ocr", "red"}:
        return "🔴 " + value
    return "⚪ " + value


def _safe_text(value: Any, default: str = "Unknown") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or default
    return str(value)


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized

    return None


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


def _init_session_state(st: Any) -> None:
    st.session_state.setdefault("atlas_active_workspace_id", None)
    st.session_state.setdefault("atlas_active_page", "Home")
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
    st.session_state.setdefault("atlas_file_search", "")
    st.session_state.setdefault("atlas_global_search", "")
    st.session_state.setdefault("atlas_global_search_index", 0)
    st.session_state.setdefault("atlas_equipment_search", "")


def _project_stage(record: ProjectWorkspaceRecord) -> str:
    status = record.project.status
    if isinstance(status, ProjectStatus):
        return status.value.replace("_", " ").title()
    return str(status).replace("_", " ").title()


def _project_status(context: dict[str, Any] | None) -> str:
    if context is None:
        return "Unknown"

    review = context.get("review")
    readiness = getattr(review, "readiness", None) if review is not None else None
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
    if st.session_state.get("atlas_active_workspace_id"):
        return

    recent = workspace_service.list_recent_workspaces(limit=1)
    if recent:
        st.session_state["atlas_active_workspace_id"] = recent[0].workspace_id
        return

    context = build_reference_project_context(DEFAULT_MAW_REFERENCE_PACKAGE)
    record = _build_record_from_context(context)
    workspace_service.save_record(record)
    st.session_state["atlas_active_workspace_id"] = record.workspace_id


def _active_record(
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
        for record in recent[:20]
    )
    options.append(SelectorOption(label="Reference Projects", kind="category"))
    options.append(
        SelectorOption(
            label="Reference · Music Academy of the West [Reference]",
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
    option = next((item for item in options if item.label == selected_label), None)
    if option is None:
        return

    if option.kind == "recent" and option.value:
        st.session_state["atlas_active_workspace_id"] = option.value
        st.session_state["atlas_workspace_action"] = ""
    elif option.kind == "reference":
        context = build_reference_project_context(DEFAULT_MAW_REFERENCE_PACKAGE)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_workspace_action"] = ""
    elif option.kind == "create":
        st.session_state["atlas_active_page"] = "Create New Project"
    elif option.kind == "open":
        st.session_state["atlas_active_page"] = "Open Existing Project"


def _group_for_page(page: str) -> str:
    if page in PROJECT_MANAGER_PAGES:
        return "Project Manager"
    if page in PROJECT_PAGES:
        return "Project"
    if page in BID_INTELLIGENCE_PAGES:
        return "Bid Intelligence"
    if page in REPORT_PAGES:
        return "Reports"
    if page in SETTINGS_PAGES:
        return "Settings"
    return "Workspace"


def _breadcrumb(record: ProjectWorkspaceRecord, page: str) -> str:
    return f"Projects / {record.project.name} / {_group_for_page(page)} / {page}"


def _render_header(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    recent = workspace_service.list_recent_workspaces(limit=30)
    options = _selector_options(recent)
    labels = [item.label for item in options]

    if st.session_state.get("atlas_project_selector") not in labels:
        st.session_state["atlas_project_selector"] = labels[0]

    st.markdown(
        "<div class='atlas-title'>Atlas Workspace</div>", unsafe_allow_html=True
    )

    cols = st.columns([2.8, 1.2, 3.2, 1.0, 1.0, 1.2, 1.4, 1.6, 1.7])
    selected = cols[0].selectbox(
        "Current Project",
        options=labels,
        key="atlas_project_selector",
    )
    _apply_selector_choice(st, workspace_service, selected, options)

    cols[1].selectbox(
        "Layout", ["Desktop", "Tablet", "Mobile"], key="atlas_layout_mode"
    )
    cols[2].text_input(
        "Global Search",
        key="atlas_global_search",
        placeholder="Search drawings, specs, equipment, systems, RFIs, evidence",
    )
    cols[3].button("Alerts", disabled=True, use_container_width=True)
    cols[4].button("Settings", use_container_width=True)
    cols[5].selectbox("Profile", ["User"], index=0)
    cols[6].markdown(
        f"<div class='atlas-muted'>Atlas v{__version__}</div>", unsafe_allow_html=True
    )
    cols[7].markdown(
        f"<div class='atlas-muted'>Stage: {_project_stage(record)}</div>",
        unsafe_allow_html=True,
    )
    cols[8].markdown(
        f"<div class='atlas-muted'>Status: {_project_status(context)}</div>",
        unsafe_allow_html=True,
    )


def _nav_buttons(st: Any, host: Any, mode: str) -> None:
    active_page = st.session_state.get("atlas_active_page", "Home")

    host.markdown("### Navigation")
    groups: list[tuple[str, list[str]]] = [
        ("PROJECT MANAGER", PROJECT_MANAGER_PAGES),
        ("PROJECT", PROJECT_PAGES),
        ("BID INTELLIGENCE", BID_INTELLIGENCE_PAGES),
        ("REPORTS", REPORT_PAGES),
        ("SETTINGS", SETTINGS_PAGES),
    ]

    for group_name, pages in groups:
        with host.expander(group_name, expanded=active_page in pages):
            for page in pages:
                if host.button(
                    page,
                    key=f"atlas_nav_{mode}_{group_name}_{page}",
                    type="primary" if active_page == page else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["atlas_active_page"] = page

    with host.expander("PROJECT LIFECYCLE", expanded=False):
        for page in DISABLED_LIFECYCLE_PAGES:
            host.button(
                f"{page} · Coming Soon",
                key=f"atlas_nav_disabled_{mode}_{page}",
                disabled=True,
                use_container_width=True,
            )


def _set_context_selection(st: Any, kind: str, data: dict[str, Any]) -> None:
    st.session_state["atlas_context_selection"] = {"kind": kind, "data": data}


def _metric_card(st: Any, title: str, value: str) -> None:
    st.markdown(
        "<div class='atlas-card'>"
        f"<div class='atlas-card-title'>{title}</div>"
        f"<div class='atlas-card-value'>{value}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_home_page(st: Any, workspace_service: ProjectWorkspaceService) -> None:
    st.subheader("Home")
    st.caption("Project-centric launch point for Atlas Workspace.")

    recent = workspace_service.list_recent_workspaces(limit=8)
    summary_cols = st.columns(4)
    _metric_card(summary_cols[0], "Recent Projects", str(len(recent)))
    _metric_card(summary_cols[1], "Reference Projects", "1")
    _metric_card(summary_cols[2], "Active Modules", "Phase 2")
    _metric_card(summary_cols[3], "Lifecycle Modules", "Coming Soon")

    st.markdown("Quick Start")
    quick_cols = st.columns(4)
    if quick_cols[0].button("Projects", use_container_width=True):
        st.session_state["atlas_active_page"] = "Projects"
    if quick_cols[1].button("Reference Projects", use_container_width=True):
        st.session_state["atlas_active_page"] = "Reference Projects"
    if quick_cols[2].button("Create New Project", use_container_width=True):
        st.session_state["atlas_active_page"] = "Create New Project"
    if quick_cols[3].button("Open Existing Project", use_container_width=True):
        st.session_state["atlas_active_page"] = "Open Existing Project"

    if recent:
        st.markdown("Recent Projects")
        st.dataframe(
            [
                {
                    "project": record.project.name,
                    "id": record.project.project_id,
                    "status": _project_stage(record),
                    "source": record.source_label,
                    "updated": record.updated_at,
                }
                for record in recent
            ],
            use_container_width=True,
            hide_index=True,
        )


def _render_projects_page(st: Any, workspace_service: ProjectWorkspaceService) -> None:
    st.subheader("Projects")
    records = workspace_service.list_recent_workspaces(limit=200)
    if not records:
        st.info("No projects available yet.")
        return

    search = st.text_input("Search Projects", value="")
    filtered = [
        record
        for record in records
        if search.strip().lower() in record.project.name.lower()
        or search.strip().lower() in record.project.project_id.lower()
        or not search.strip()
    ]

    st.dataframe(
        [
            {
                "project": record.project.name,
                "project_id": record.project.project_id,
                "source": record.source_label,
                "status": _project_stage(record),
                "updated": record.updated_at,
            }
            for record in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )

    labels = [
        f"{record.project.name} · {record.project.project_id}" for record in filtered
    ]
    if labels:
        selected_label = st.selectbox("Open Project", options=labels)
        selected = filtered[labels.index(selected_label)]
        if st.button("Open Selected Project", type="primary"):
            st.session_state["atlas_active_workspace_id"] = selected.workspace_id
            st.session_state["atlas_active_page"] = "Overview"
            st.rerun()


def _render_reference_projects_page(
    st: Any,
    workspace_service: ProjectWorkspaceService,
) -> None:
    st.subheader("Reference Projects")
    st.markdown(
        "<span class='atlas-chip'>Reference</span> Music Academy of the West",
        unsafe_allow_html=True,
    )
    st.caption("Canonical deterministic reference project for local review.")
    if st.button("Open Music Academy of the West", type="primary"):
        context = build_reference_project_context(DEFAULT_MAW_REFERENCE_PACKAGE)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Overview"
        st.rerun()


def _render_recent_projects_page(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    st.subheader("Recent Projects")
    records = workspace_service.list_recent_workspaces(limit=20)
    if not records:
        st.info("No recent projects yet.")
        return

    for record in records:
        with st.container(border=True):
            st.markdown(f"**{record.project.name}**")
            st.caption(
                f"{record.project.project_id} · {_project_stage(record)} · {record.source_label}"
            )
            if st.button(
                "Open",
                key=f"atlas_recent_open_{record.workspace_id}",
                use_container_width=True,
            ):
                st.session_state["atlas_active_workspace_id"] = record.workspace_id
                st.session_state["atlas_active_page"] = "Overview"
                st.rerun()


def _render_create_project_page(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    st.subheader("Create New Project")
    with st.form("atlas_create_project_form", clear_on_submit=False):
        project_id = st.text_input("Project ID", key="atlas_new_project_id")
        name = st.text_input("Project Name", key="atlas_new_project_name")
        client = st.text_input("Owner / Client", key="atlas_new_project_client")
        location = st.text_input("Location", key="atlas_new_project_location")
        bid_date = st.text_input("Bid Date", key="atlas_new_project_bid_date")
        submitted = st.form_submit_button("Create Project")

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
    st.session_state["atlas_active_workspace_id"] = record.workspace_id
    st.session_state["atlas_active_page"] = "Overview"
    st.success(f"Created project {record.project.name}.")
    st.rerun()


def _render_open_existing_page(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    st.subheader("Open Existing Project")
    path_text = st.text_input(
        "Workspace file, intake snapshot, or package folder",
        key="atlas_pending_open_path",
        placeholder="outputs/project_workspaces/example/workspace.json",
    )

    if not st.button("Open Path", type="primary"):
        return

    path = Path(path_text).expanduser()
    if not path.exists():
        st.error(f"Path not found: {path}")
        return

    if path.is_dir() and (path / "workspace.json").exists():
        record = workspace_service.load_record(path / "workspace.json")
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Overview"
        st.rerun()
        return

    if path.name == "workspace.json":
        record = workspace_service.load_record(path)
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Overview"
        st.rerun()
        return

    if path.name == "intake_snapshot.json":
        context = build_intake_review_context(path)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Overview"
        st.rerun()
        return

    if path.is_dir():
        context = build_reference_project_context(path)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Overview"
        st.rerun()
        return

    st.error(
        "Open a workspace.json file, intake_snapshot.json file, or package folder."
    )


def _render_overview_page(
    st: Any, record: ProjectWorkspaceRecord, context: dict[str, Any] | None
) -> None:
    st.subheader("Mission Control")

    review = context.get("review") if context else None
    readiness = getattr(review, "readiness", None) if review is not None else None
    import_summary = dict(context.get("import_summary") or {}) if context else {}
    warnings = list(context.get("warnings") or []) if context else []
    metadata = (
        dict(getattr(context.get("intake_snapshot"), "metadata", {}) or {})
        if context
        else {}
    )

    row1 = st.columns(4)
    _metric_card(row1[0], "Project", _safe_text(record.project.name, "n/a"))
    _metric_card(row1[1], "Lifecycle Stage", _project_stage(record))
    _metric_card(row1[2], "Current Status", _status_chip(_project_status(context)))
    _metric_card(
        row1[3],
        "Import Status",
        _safe_text(context.get("data_source_label") if context else "Manual", "Manual"),
    )

    row2 = st.columns(4)
    readiness_score = getattr(readiness, "readiness_score", None)
    readiness_level = _safe_text(
        getattr(getattr(readiness, "readiness_level", None), "value", None),
        "n/a",
    ).title()
    _metric_card(
        row2[0],
        "Readiness",
        f"{readiness_score:.2f}" if readiness_score is not None else "n/a",
    )
    _metric_card(row2[1], "Readiness Level", _status_chip(readiness_level))
    _metric_card(
        row2[2], "Current Confidence", str(getattr(review, "confidence", "n/a"))
    )
    _metric_card(
        row2[3],
        "Top Risks",
        str(len(getattr(review, "estimator_risks", []) or [])) if review else "0",
    )

    metadata_rows = [
        {
            "field": "Owner",
            "value": _safe_text(
                _first_text(
                    metadata.get("owner"), metadata.get("client"), record.project.client
                ),
                "n/a",
            ),
        },
        {
            "field": "Architect",
            "value": _safe_text(metadata.get("architect"), "n/a"),
        },
        {
            "field": "Consultants",
            "value": _safe_text(metadata.get("consultants"), "n/a"),
        },
        {
            "field": "Project Number",
            "value": _safe_text(
                _first_text(
                    metadata.get("project_number"),
                    metadata.get("project_id"),
                    record.project.project_id,
                ),
                "n/a",
            ),
        },
        {
            "field": "Issue Date",
            "value": _safe_text(metadata.get("issue_date"), "n/a"),
        },
        {
            "field": "Bid Date",
            "value": _safe_text(
                _first_text(metadata.get("bid_date"), record.project.bid_date), "n/a"
            ),
        },
    ]
    st.dataframe(metadata_rows, use_container_width=True, hide_index=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("Top Blockers")
        blockers = list(getattr(readiness, "blocking_issues", []) or [])
        if blockers:
            st.dataframe(
                [{"blocker": item} for item in blockers[:8]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No active blockers.")

        st.markdown("Top Risks")
        risks = (
            _to_rows(list(getattr(review, "estimator_risks", []) or []))
            if review
            else []
        )
        if risks:
            st.dataframe(risks[:8], use_container_width=True, hide_index=True)
        else:
            st.info("No active risks.")

    with col_b:
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

        st.markdown("Current Warnings")
        if warnings:
            st.dataframe(
                [{"warning": item} for item in warnings[:8]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No warnings.")

    st.markdown("Recent Activity")
    st.dataframe(
        [
            {
                "event": "Workspace opened",
                "timestamp": record.last_opened_at or record.updated_at,
            },
            {
                "event": "Last intake",
                "timestamp": _safe_text(import_summary.get("package_location"), "n/a"),
            },
            {"event": "Last review", "timestamp": record.updated_at},
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("Quick Actions")
    quick = st.columns(4)
    if quick[0].button("Project Files", use_container_width=True):
        st.session_state["atlas_active_page"] = "Project Files"
    if quick[1].button("Readiness", use_container_width=True):
        st.session_state["atlas_active_page"] = "Readiness"
    if quick[2].button("Executive Summary", use_container_width=True):
        st.session_state["atlas_active_page"] = "Executive Summary"
    if quick[3].button("RFI Candidates", use_container_width=True):
        st.session_state["atlas_active_page"] = "RFI Candidates"


def _render_executive_summary_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Executive Summary")
    if context is None:
        st.info("No review context available.")
        return

    review = context.get("review")
    brief = context.get("brief")
    readiness = getattr(review, "readiness", None) if review is not None else None
    import_summary = dict(context.get("import_summary") or {})

    cards = st.columns(3)
    _metric_card(
        cards[0],
        "Overall Health",
        _status_chip(
            _safe_text(
                getattr(getattr(readiness, "readiness_level", None), "value", None),
                "n/a",
            ).title()
        ),
    )
    _metric_card(
        cards[1],
        "Critical Risks",
        str(len(getattr(review, "estimator_risks", []) or [])),
    )
    _metric_card(
        cards[2],
        "Labor Confidence",
        str(getattr(getattr(review, "labor_estimate", None), "confidence", "n/a")),
    )

    cards2 = st.columns(4)
    _metric_card(
        cards2[0], "Scope Gaps", str(getattr(review, "scope_gap_count", lambda: 0)())
    )
    _metric_card(
        cards2[1],
        "Documents Requiring OCR",
        str(import_summary.get("documents_requiring_ocr", 0)),
    )
    _metric_card(
        cards2[2],
        "Priority RFIs",
        str(len(getattr(review, "rfi_candidates", []) or [])),
    )
    _metric_card(
        cards2[3],
        "Recommended Actions",
        str(len(list(getattr(brief, "prioritized_reviewer_actions", []) or []))),
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
        "Other Documents": [],
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
            folder = "Other Documents"

        file_name = str(item.get("file_name") or "unknown")
        references = sum(
            1
            for ref in source_refs
            if Path(str(ref.get("source_file") or "")).name == file_name
        )
        warnings = list(item.get("warnings") or [])

        folder_map[folder].append(
            {
                "filename": file_name,
                "revision": _safe_text(item.get("revision"), "unknown"),
                "status": _safe_text(item.get("status"), "unknown"),
                "pages": item.get("total_pages"),
                "references": references,
                "warnings": len(warnings),
                "folder": folder,
                "group": group,
            }
        )

    return folder_map


def _split_refs(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).replace("|", ",").replace(";", ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def _evidence_group_for_file(source_file: str) -> str:
    suffix = Path(source_file).suffix.lower()
    if suffix in {".dwg", ".pdf"}:
        lower = source_file.lower()
        if "spec" in lower:
            return "Specifications"
        if "schedule" in lower:
            return "Schedules"
        if "addenda" in lower:
            return "Addenda"
        return "Drawings"
    if suffix in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        return "Images"
    if suffix in {".txt", ".rtf", ".doc", ".docx"}:
        return "Notes"
    return "Addenda"


def _in_text(haystack: Any, needle: str) -> bool:
    return needle.lower() in str(haystack or "").lower()


def _contains_any(haystack: Any, values: list[str]) -> bool:
    hay = str(haystack or "").lower()
    return any(value.lower() in hay for value in values if value)


def _workspace_objects(
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    if context is None:
        return {
            "drawings": [],
            "specifications": [],
            "equipment": [],
            "systems": [],
            "rfis": [],
            "evidence": [],
            "rooms": [],
            "manufacturers": [],
            "models": [],
        }

    review = context.get("review")
    snapshot = context.get("intake_snapshot")
    readiness = getattr(review, "readiness", None) if review is not None else None
    labor = getattr(review, "labor_estimate", None) if review is not None else None

    drawing_rows = _to_rows(list(getattr(review, "drawing_sheets", []) or []))
    spec_rows = _to_rows(list(getattr(review, "specification_sections", []) or []))
    equipment_rows = _to_rows(list(getattr(review, "equipment", []) or []))
    rfi_rows = _to_rows(list(getattr(review, "rfi_candidates", []) or []))
    source_refs = _to_rows(list(getattr(snapshot, "source_references", []) or []))

    evidence_rows = [
        {
            "source_file": _safe_text(item.get("source_file"), "Unknown"),
            "page": item.get("page", item.get("page_number", "n/a")),
            "sheet": _safe_text(item.get("sheet_number"), "n/a"),
            "confidence": item.get("confidence", "n/a"),
            "text_excerpt": _safe_text(item.get("excerpt"), "n/a"),
            "group": _evidence_group_for_file(_safe_text(item.get("source_file"), "")),
        }
        for item in source_refs
    ]

    drawing_ids = [
        _safe_text(item.get("sheet_number"), _safe_text(item.get("source_file"), ""))
        for item in drawing_rows
    ]
    spec_ids = [
        _safe_text(item.get("section_number"), _safe_text(item.get("source_file"), ""))
        for item in spec_rows
    ]
    system_ids = [
        _safe_text(item.get("system_id"), _safe_text(item.get("name"), ""))
        for item in _to_rows(list(getattr(review, "systems", []) or []))
    ]

    drawings: list[dict[str, Any]] = []
    for item in drawing_rows:
        drawing_number = _safe_text(
            item.get("sheet_number"), _safe_text(item.get("drawing_number"), "Unknown")
        )
        title = _safe_text(item.get("title"), "Untitled Drawing")
        source_file = _safe_text(item.get("source_file"), "")
        ref_equipment = [
            eq
            for eq in equipment_rows
            if _contains_any(
                eq.get("drawing_reference"), [drawing_number, source_file, title]
            )
        ]
        ref_specs = [
            spec
            for spec in spec_rows
            if _contains_any(
                spec.get("drawing_reference"), [drawing_number, source_file, title]
            )
            or _contains_any(spec.get("source_file"), [drawing_number])
        ]
        ref_systems = sorted(
            {
                _safe_text(eq.get("system_id"), "Unknown")
                for eq in ref_equipment
                if _safe_text(eq.get("system_id"), "")
            }
        )
        ref_rfis = [
            rfi
            for rfi in rfi_rows
            if _contains_any(
                str(rfi),
                [drawing_number, source_file, title],
            )
        ]
        ref_evidence = [
            evidence
            for evidence in evidence_rows
            if _contains_any(evidence.get("source_file"), [source_file, drawing_number])
        ]
        warnings = _split_refs(item.get("warnings"))
        drawings.append(
            {
                "drawing_number": drawing_number,
                "title": title,
                "revision": _safe_text(item.get("revision"), "n/a"),
                "issue_date": _safe_text(item.get("issue_date"), "n/a"),
                "discipline": _safe_text(item.get("discipline"), "General"),
                "source_file": source_file,
                "referenced_equipment": [
                    _safe_text(
                        eq.get("equipment_id"),
                        _safe_text(eq.get("description"), "equipment"),
                    )
                    for eq in ref_equipment
                ],
                "referenced_specifications": [
                    _safe_text(
                        spec.get("section_number"),
                        _safe_text(spec.get("source_file"), "spec"),
                    )
                    for spec in ref_specs
                ],
                "referenced_systems": ref_systems,
                "referenced_rfis": [
                    _safe_text(rfi.get("rfi_id"), _safe_text(rfi.get("title"), "rfi"))
                    for rfi in ref_rfis
                ],
                "referenced_evidence": [
                    f"{_safe_text(evidence.get('source_file'), 'file')} p.{evidence.get('page', 'n/a')}"
                    for evidence in ref_evidence
                ],
                "extraction_quality": _safe_text(item.get("confidence"), "n/a"),
                "ocr_status": _safe_text(item.get("ocr_status"), "unknown"),
                "warnings": warnings,
            }
        )

    specifications: list[dict[str, Any]] = []
    for item in spec_rows:
        section = _safe_text(item.get("section_number"), "Unknown")
        title = _safe_text(item.get("title"), "Untitled Section")
        source_file = _safe_text(item.get("source_file"), "")
        ref_drawings = [
            drawing
            for drawing in drawings
            if _contains_any(
                item.get("drawing_reference"),
                [drawing.get("drawing_number", ""), drawing.get("source_file", "")],
            )
            or _contains_any(source_file, [drawing.get("drawing_number", "")])
        ]
        ref_equipment = [
            eq
            for eq in equipment_rows
            if _contains_any(
                eq.get("specification_reference"),
                [section, title, source_file],
            )
        ]
        ref_systems = sorted(
            {
                _safe_text(eq.get("system_id"), "Unknown")
                for eq in ref_equipment
                if _safe_text(eq.get("system_id"), "")
            }
        )
        ref_rfis = [
            rfi
            for rfi in rfi_rows
            if _contains_any(str(rfi), [section, title, source_file])
        ]
        ref_evidence = [
            evidence
            for evidence in evidence_rows
            if _contains_any(evidence.get("source_file"), [source_file, section])
        ]

        cross_refs = _split_refs(item.get("cross_references"))
        if not cross_refs:
            cross_refs = [
                _safe_text(ref.get("section_number"), "")
                for ref in ref_drawings
                if _safe_text(ref.get("section_number"), "")
            ]

        specifications.append(
            {
                "division": _safe_text(item.get("division"), "n/a"),
                "section": section,
                "title": title,
                "source_file": source_file,
                "referenced_drawings": [
                    _safe_text(drawing.get("drawing_number"), "drawing")
                    for drawing in ref_drawings
                ],
                "referenced_equipment": [
                    _safe_text(eq.get("equipment_id"), "equipment")
                    for eq in ref_equipment
                ],
                "referenced_systems": ref_systems,
                "referenced_rfis": [
                    _safe_text(rfi.get("rfi_id"), _safe_text(rfi.get("title"), "rfi"))
                    for rfi in ref_rfis
                ],
                "referenced_evidence": [
                    f"{_safe_text(evidence.get('source_file'), 'file')} p.{evidence.get('page', 'n/a')}"
                    for evidence in ref_evidence
                ],
                "cross_references": [item for item in cross_refs if item],
                "extraction_confidence": _safe_text(item.get("confidence"), "n/a"),
            }
        )

    equipment: list[dict[str, Any]] = []
    for item in equipment_rows:
        drawing_refs = _split_refs(item.get("drawing_reference"))
        spec_refs = _split_refs(item.get("specification_reference"))
        equipment_id = _safe_text(item.get("equipment_id"), "Unknown")
        potential_rfis = [
            rfi
            for rfi in rfi_rows
            if _contains_any(
                str(rfi), [equipment_id, _safe_text(item.get("model"), "")]
            )
        ]

        equipment.append(
            {
                "equipment_id": equipment_id,
                "manufacturer": _safe_text(item.get("manufacturer"), "Unknown"),
                "model": _safe_text(item.get("model"), "Unknown"),
                "description": _safe_text(item.get("description"), "n/a"),
                "system": _safe_text(item.get("system_id"), "Unknown"),
                "room": _safe_text(
                    _first_text(
                        item.get("room"), item.get("room_id"), item.get("space")
                    ),
                    "Unknown",
                ),
                "discipline": _safe_text(item.get("discipline"), "General"),
                "drawing_references": drawing_refs,
                "specification_references": spec_refs,
                "current_status": _safe_text(item.get("status"), "Needs Review"),
                "confidence": _safe_text(item.get("confidence"), "n/a"),
                "potential_rfis": [
                    _safe_text(rfi.get("rfi_id"), _safe_text(rfi.get("title"), "rfi"))
                    for rfi in potential_rfis
                ],
            }
        )

    system_map: dict[str, dict[str, Any]] = {}
    known_systems = [
        "Audio",
        "Video",
        "Control",
        "Network",
        "Projection",
        "Lighting",
        "Assistive Listening",
        "Intercom",
        "Paging",
    ]
    for name in known_systems + system_ids:
        key = _safe_text(name, "Unknown")
        if key not in system_map:
            system_map[key] = {
                "system": key,
                "equipment_count": 0,
                "drawing_count": 0,
                "specification_count": 0,
                "rfi_count": 0,
                "readiness": _safe_text(
                    getattr(getattr(readiness, "readiness_level", None), "value", None),
                    "n/a",
                ).title(),
                "labor": _safe_text(
                    getattr(labor, "total_labor_hours_expected", None), "n/a"
                ),
                "confidence": _safe_text(getattr(review, "confidence", None), "n/a"),
            }

    for item in equipment:
        key = item["system"]
        system_map.setdefault(
            key,
            {
                "system": key,
                "equipment_count": 0,
                "drawing_count": 0,
                "specification_count": 0,
                "rfi_count": 0,
                "readiness": "n/a",
                "labor": "n/a",
                "confidence": "n/a",
            },
        )
        system_map[key]["equipment_count"] += 1
        system_map[key]["drawing_count"] += len(item["drawing_references"])
        system_map[key]["specification_count"] += len(item["specification_references"])
        system_map[key]["rfi_count"] += len(item["potential_rfis"])

    systems = [value for value in system_map.values()]

    rooms = sorted({item["room"] for item in equipment if item["room"]})
    manufacturers = sorted(
        {item["manufacturer"] for item in equipment if item["manufacturer"]}
    )
    models = sorted({item["model"] for item in equipment if item["model"]})

    return {
        "drawings": drawings,
        "specifications": specifications,
        "equipment": equipment,
        "systems": systems,
        "rfis": rfi_rows,
        "evidence": evidence_rows,
        "rooms": [{"room": item} for item in rooms],
        "manufacturers": [{"manufacturer": item} for item in manufacturers],
        "models": [{"model": item} for item in models],
        "drawing_ids": drawing_ids,
        "spec_ids": spec_ids,
    }


def _global_search_entries(context: dict[str, Any] | None) -> list[dict[str, Any]]:
    objects = _workspace_objects(context)
    entries: list[dict[str, Any]] = []

    for item in objects["drawings"]:
        entries.append(
            {
                "kind": "Drawing",
                "name": _safe_text(item.get("drawing_number"), "Drawing"),
                "subtitle": _safe_text(item.get("title"), ""),
                "page": "Drawings",
                "selection_kind": "drawing",
                "data": item,
            }
        )
    for item in objects["specifications"]:
        entries.append(
            {
                "kind": "Specification",
                "name": _safe_text(item.get("section"), "Specification"),
                "subtitle": _safe_text(item.get("title"), ""),
                "page": "Specifications",
                "selection_kind": "specification",
                "data": item,
            }
        )
    for item in objects["equipment"]:
        entries.append(
            {
                "kind": "Equipment",
                "name": _safe_text(item.get("equipment_id"), "Equipment"),
                "subtitle": f"{_safe_text(item.get('manufacturer'), '')} {_safe_text(item.get('model'), '')}".strip(),
                "page": "Equipment",
                "selection_kind": "equipment",
                "data": item,
            }
        )
    for item in objects["systems"]:
        entries.append(
            {
                "kind": "System",
                "name": _safe_text(item.get("system"), "System"),
                "subtitle": f"equipment {item.get('equipment_count', 0)}",
                "page": "Systems",
                "selection_kind": "system",
                "data": item,
            }
        )
    for item in objects["rooms"]:
        entries.append(
            {
                "kind": "Room",
                "name": _safe_text(item.get("room"), "Room"),
                "subtitle": "equipment location",
                "page": "Equipment",
                "selection_kind": "room",
                "data": item,
            }
        )
    for item in objects["manufacturers"]:
        entries.append(
            {
                "kind": "Manufacturer",
                "name": _safe_text(item.get("manufacturer"), "Manufacturer"),
                "subtitle": "equipment manufacturer",
                "page": "Equipment",
                "selection_kind": "manufacturer",
                "data": item,
            }
        )
    for item in objects["models"]:
        entries.append(
            {
                "kind": "Model",
                "name": _safe_text(item.get("model"), "Model"),
                "subtitle": "equipment model",
                "page": "Equipment",
                "selection_kind": "model",
                "data": item,
            }
        )
    for item in objects["rfis"]:
        entries.append(
            {
                "kind": "RFI",
                "name": _safe_text(
                    item.get("rfi_id"), _safe_text(item.get("title"), "RFI")
                ),
                "subtitle": _safe_text(item.get("title"), ""),
                "page": "RFI Candidates",
                "selection_kind": "rfi",
                "data": item,
            }
        )
    for item in objects["evidence"]:
        entries.append(
            {
                "kind": "Evidence",
                "name": _safe_text(item.get("source_file"), "Evidence"),
                "subtitle": f"page {item.get('page', 'n/a')}",
                "page": "Evidence",
                "selection_kind": "evidence",
                "data": item,
            }
        )

    return entries


def _render_global_search_panel(st: Any, context: dict[str, Any] | None) -> None:
    query = str(st.session_state.get("atlas_global_search") or "").strip()
    if not query:
        return

    entries = _global_search_entries(context)
    filtered = [
        item
        for item in entries
        if _in_text(item.get("name"), query)
        or _in_text(item.get("subtitle"), query)
        or _in_text(item.get("kind"), query)
    ]

    with st.expander(f"Global Search Results ({len(filtered)})", expanded=True):
        st.caption(
            "Use arrow keys in the result selector for keyboard navigation, then press Enter."
        )
        if not filtered:
            st.info("No objects match the current project search.")
            return

        labels = [
            f"{item['kind']}: {item['name']}  |  {item['subtitle']}"
            for item in filtered
        ]
        selected_label = st.selectbox(
            "Results", options=labels, key="atlas_search_result"
        )
        selected = filtered[labels.index(selected_label)]

        st.markdown(
            "<div class='atlas-object-card'>"
            f"<div class='atlas-object-header'>Selected Result: {selected['kind']}</div>"
            f"{selected['name']}<br/><span class='atlas-muted'>{selected['subtitle']}</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        if st.button("Open Result", key="atlas_open_search_result", type="primary"):
            st.session_state["atlas_active_page"] = selected["page"]
            _set_context_selection(
                st,
                str(selected.get("selection_kind") or "project"),
                dict(selected.get("data") or {}),
            )
            st.rerun()


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
    st.subheader("Project Explorer")
    _render_upload_panel(st, workspace_service)

    folders = _files_by_folder(context)
    folder_name = st.selectbox("Folder", options=list(folders.keys()))
    records = list(folders.get(folder_name, []))

    search = st.text_input(
        "Search files",
        key="atlas_file_search",
        value=st.session_state.get("atlas_file_search", ""),
    )
    status_options = sorted({item["status"] for item in records})
    status_filter = st.multiselect(
        "Filter by status", options=status_options, default=[]
    )
    sort_field = st.selectbox(
        "Sort by", options=["filename", "status", "pages", "warnings", "references"]
    )
    sort_dir = (
        st.selectbox("Order", options=["Ascending", "Descending"]) == "Descending"
    )

    filtered = [
        item
        for item in records
        if (search.strip().lower() in item["filename"].lower() or not search.strip())
        and (item["status"] in status_filter if status_filter else True)
    ]
    filtered.sort(key=lambda item: str(item.get(sort_field) or ""), reverse=sort_dir)

    display_rows = [
        {
            "filename": item["filename"],
            "revision": item["revision"],
            "status": _status_chip(item["status"]),
            "pages": item["pages"],
            "references": item["references"],
            "warnings": item["warnings"],
        }
        for item in filtered
    ]

    if not display_rows:
        st.info("No files match the current filters.")
        return

    st.dataframe(display_rows, use_container_width=True, hide_index=True)

    file_labels = [item["filename"] for item in filtered]
    selected_file = st.selectbox("Select file", options=file_labels)
    selected = next(item for item in filtered if item["filename"] == selected_file)
    _set_context_selection(st, "file", {"folder": folder_name, "file": selected})


def _render_drawings_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Drawing Workspace")
    objects = _workspace_objects(context)
    rows = list(objects.get("drawings", []))
    if not rows:
        st.info("No drawing objects available.")
        return

    st.caption("Each drawing is a first-class object with relationship links.")
    summary_rows = [
        {
            "drawing number": item["drawing_number"],
            "title": item["title"],
            "revision": item["revision"],
            "issue date": item["issue_date"],
            "discipline": item["discipline"],
            "equipment": len(item["referenced_equipment"]),
            "specifications": len(item["referenced_specifications"]),
            "systems": len(item["referenced_systems"]),
            "rfis": len(item["referenced_rfis"]),
            "evidence": len(item["referenced_evidence"]),
            "extraction quality": item["extraction_quality"],
            "ocr status": item["ocr_status"],
            "warnings": len(item["warnings"]),
        }
        for item in rows
    ]
    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    labels = [f"{item['drawing_number']} · {item['title']}" for item in rows]
    selected_label = st.selectbox("Select Drawing Object", options=labels)
    selected = rows[labels.index(selected_label)]
    _set_context_selection(st, "drawing", selected)

    detail_col, nav_col = st.columns([2.6, 1.4])
    with detail_col:
        st.markdown("#### Drawing Detail")
        st.dataframe(
            [
                {"property": "Drawing Number", "value": selected["drawing_number"]},
                {"property": "Title", "value": selected["title"]},
                {"property": "Revision", "value": selected["revision"]},
                {"property": "Issue Date", "value": selected["issue_date"]},
                {"property": "Discipline", "value": selected["discipline"]},
                {"property": "OCR Status", "value": selected["ocr_status"]},
                {
                    "property": "Extraction Quality",
                    "value": selected["extraction_quality"],
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("Referenced Objects")
        st.dataframe(
            [
                {
                    "relationship": "Equipment",
                    "objects": ", ".join(selected["referenced_equipment"]) or "n/a",
                },
                {
                    "relationship": "Specifications",
                    "objects": ", ".join(selected["referenced_specifications"])
                    or "n/a",
                },
                {
                    "relationship": "Systems",
                    "objects": ", ".join(selected["referenced_systems"]) or "n/a",
                },
                {
                    "relationship": "RFIs",
                    "objects": ", ".join(selected["referenced_rfis"]) or "n/a",
                },
                {
                    "relationship": "Evidence",
                    "objects": ", ".join(selected["referenced_evidence"]) or "n/a",
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

        source_file = _safe_text(selected.get("source_file"), "")
        if source_file.lower().endswith(".pdf"):
            st.markdown("#### PDF Preview")
            st.caption(
                "Embedded preview available when the source PDF is available locally."
            )
            st.code(source_file)
        else:
            st.markdown("#### Preview")
            st.info(
                "Preview placeholder: drawing metadata available, source preview not embedded."
            )

    with nav_col:
        st.markdown("#### Quick Navigation")
        if st.button("Open Equipment", use_container_width=True):
            st.session_state["atlas_active_page"] = "Equipment"
            st.rerun()
        if st.button("Open Specifications", use_container_width=True):
            st.session_state["atlas_active_page"] = "Specifications"
            st.rerun()
        if st.button("Open Systems", use_container_width=True):
            st.session_state["atlas_active_page"] = "Systems"
            st.rerun()
        if st.button("Open Evidence", use_container_width=True):
            st.session_state["atlas_active_page"] = "Evidence"
            st.rerun()


def _render_specifications_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Specification Workspace")
    objects = _workspace_objects(context)
    rows = list(objects.get("specifications", []))
    if not rows:
        st.info("No specification objects available.")
        return

    st.caption(
        "Each specification section is a first-class object with linked relationships."
    )
    st.dataframe(
        [
            {
                "division": item["division"],
                "section": item["section"],
                "title": item["title"],
                "drawings": len(item["referenced_drawings"]),
                "equipment": len(item["referenced_equipment"]),
                "systems": len(item["referenced_systems"]),
                "rfis": len(item["referenced_rfis"]),
                "evidence": len(item["referenced_evidence"]),
                "cross refs": len(item["cross_references"]),
                "extraction confidence": item["extraction_confidence"],
            }
            for item in rows
        ],
        use_container_width=True,
        hide_index=True,
    )

    labels = [f"{item['section']} · {item['title']}" for item in rows]
    selected_label = st.selectbox("Select Specification Object", options=labels)
    selected = rows[labels.index(selected_label)]
    _set_context_selection(st, "specification", selected)

    st.markdown("#### Specification Detail")
    st.dataframe(
        [
            {"property": "Division", "value": selected["division"]},
            {"property": "Section", "value": selected["section"]},
            {"property": "Title", "value": selected["title"]},
            {
                "property": "Cross References",
                "value": ", ".join(selected["cross_references"]) or "n/a",
            },
            {
                "property": "Extraction Confidence",
                "value": selected["extraction_confidence"],
            },
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("Relationships")
    st.dataframe(
        [
            {
                "relationship": "Drawings",
                "objects": ", ".join(selected["referenced_drawings"]) or "n/a",
            },
            {
                "relationship": "Equipment",
                "objects": ", ".join(selected["referenced_equipment"]) or "n/a",
            },
            {
                "relationship": "Systems",
                "objects": ", ".join(selected["referenced_systems"]) or "n/a",
            },
            {
                "relationship": "RFIs",
                "objects": ", ".join(selected["referenced_rfis"]) or "n/a",
            },
            {
                "relationship": "Evidence",
                "objects": ", ".join(selected["referenced_evidence"]) or "n/a",
            },
        ],
        use_container_width=True,
        hide_index=True,
    )

    nav_cols = st.columns(4)
    if nav_cols[0].button("Go to Drawings", use_container_width=True):
        st.session_state["atlas_active_page"] = "Drawings"
        st.rerun()
    if nav_cols[1].button("Go to Equipment", use_container_width=True):
        st.session_state["atlas_active_page"] = "Equipment"
        st.rerun()
    if nav_cols[2].button("Go to Systems", use_container_width=True):
        st.session_state["atlas_active_page"] = "Systems"
        st.rerun()
    if nav_cols[3].button("Go to Evidence", use_container_width=True):
        st.session_state["atlas_active_page"] = "Evidence"
        st.rerun()


def _render_equipment_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Equipment Browser")
    objects = _workspace_objects(context)
    rows = list(objects.get("equipment", []))
    if not rows:
        st.info("No equipment objects available.")
        return

    filter_cols = st.columns([2.0, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
    search = filter_cols[0].text_input(
        "Search",
        key="atlas_equipment_search",
        placeholder="manufacturer, model, description, system, room",
    )
    system_filter = filter_cols[1].selectbox(
        "System",
        options=["All"] + sorted({item["system"] for item in rows}),
    )
    manufacturer_filter = filter_cols[2].selectbox(
        "Manufacturer",
        options=["All"] + sorted({item["manufacturer"] for item in rows}),
    )
    room_filter = filter_cols[3].selectbox(
        "Room",
        options=["All"] + sorted({item["room"] for item in rows}),
    )
    discipline_filter = filter_cols[4].selectbox(
        "Discipline",
        options=["All"] + sorted({item["discipline"] for item in rows}),
    )
    sort_field = filter_cols[5].selectbox(
        "Sort",
        options=[
            "equipment_id",
            "manufacturer",
            "model",
            "system",
            "room",
            "current_status",
            "confidence",
        ],
    )
    group_by = filter_cols[6].selectbox(
        "Group By",
        options=["System", "Manufacturer", "Room", "Discipline", "None"],
    )

    filtered = [
        item
        for item in rows
        if (
            not search
            or _contains_any(
                str(item),
                [search],
            )
        )
        and (system_filter == "All" or item["system"] == system_filter)
        and (
            manufacturer_filter == "All" or item["manufacturer"] == manufacturer_filter
        )
        and (room_filter == "All" or item["room"] == room_filter)
        and (discipline_filter == "All" or item["discipline"] == discipline_filter)
    ]

    filtered.sort(key=lambda item: str(item.get(sort_field) or "").lower())

    if not filtered:
        st.info("No equipment matches current filters.")
        return

    display_rows = [
        {
            "equipment": item["equipment_id"],
            "manufacturer": item["manufacturer"],
            "model": item["model"],
            "description": item["description"],
            "system": item["system"],
            "room": item["room"],
            "drawing refs": ", ".join(item["drawing_references"]) or "n/a",
            "spec refs": ", ".join(item["specification_references"]) or "n/a",
            "status": item["current_status"],
            "confidence": item["confidence"],
            "potential rfis": len(item["potential_rfis"]),
        }
        for item in filtered
    ]

    if group_by != "None":
        bucket_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
        key_map = {
            "System": "system",
            "Manufacturer": "manufacturer",
            "Room": "room",
            "Discipline": "discipline",
        }
        group_key = key_map[group_by]
        for row in display_rows:
            bucket_map[str(row[group_key]).strip() or "Unassigned"].append(row)

        for bucket_name in sorted(bucket_map.keys()):
            st.markdown(f"#### {group_by}: {bucket_name}")
            st.dataframe(
                bucket_map[bucket_name], use_container_width=True, hide_index=True
            )
    else:
        st.dataframe(display_rows, use_container_width=True, hide_index=True)

    labels = [
        f"{item['equipment_id']} · {item['manufacturer']} {item['model']}"
        for item in filtered
    ]
    selected_label = st.selectbox("Select Equipment Object", options=labels)
    selected = filtered[labels.index(selected_label)]
    _set_context_selection(st, "equipment", selected)


def _render_systems_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Systems Workspace")
    rows = list(_workspace_objects(context).get("systems", []))
    if not rows:
        st.info("No systems available.")
        return

    st.dataframe(
        [
            {
                "system": item["system"],
                "equipment count": item["equipment_count"],
                "drawing count": item["drawing_count"],
                "specification count": item["specification_count"],
                "rfi count": item["rfi_count"],
                "readiness": item["readiness"],
                "labor": item["labor"],
                "confidence": item["confidence"],
            }
            for item in rows
        ],
        use_container_width=True,
        hide_index=True,
    )

    labels = [item["system"] for item in rows]
    selected_label = st.selectbox("Select System Object", options=labels)
    selected = rows[labels.index(selected_label)]
    _set_context_selection(st, "system", selected)


def _render_bid_page(st: Any, page: str, context: dict[str, Any] | None) -> None:
    review = context.get("review") if context else None
    brief = context.get("brief") if context else None
    revision = context.get("revision_comparison") if context else None
    readiness = getattr(review, "readiness", None) if review is not None else None
    labor = getattr(review, "labor_estimate", None) if review is not None else None

    st.subheader(page)

    if page == "Readiness":
        if readiness is None:
            st.info("No readiness assessment available.")
            return
        st.write(getattr(readiness, "message", ""))
        section_scores = dict(getattr(readiness, "section_scores", {}) or {})
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
        if labor is None:
            st.info("No labor estimate available.")
            return
        st.dataframe(
            [
                {
                    "field": "Total Labor Hours Expected",
                    "value": getattr(labor, "total_labor_hours_expected", None),
                },
                {"field": "Confidence", "value": getattr(labor, "confidence", None)},
            ],
            use_container_width=True,
            hide_index=True,
        )
        categories = _to_rows(list(getattr(labor, "labor_categories", []) or []))
        if categories:
            st.dataframe(categories, use_container_width=True, hide_index=True)
        return

    if page == "Revision Comparison":
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
        objects = _workspace_objects(context)
        evidence_rows = list(objects.get("evidence", []))
        if not evidence_rows:
            st.info("No evidence references available.")
            return

        evidence_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in evidence_rows:
            evidence_by_group[str(item.get("group") or "Other")].append(item)

        st.caption(
            "Evidence grouped by Drawings, Specifications, Schedules, Images, Notes, and Addenda."
        )
        for group in [
            "Drawings",
            "Specifications",
            "Schedules",
            "Images",
            "Notes",
            "Addenda",
        ]:
            rows = evidence_by_group.get(group, [])
            st.markdown(f"#### {group}")
            if not rows:
                st.info("No evidence in this group.")
                continue

            st.dataframe(
                [
                    {
                        "source file": item.get("source_file"),
                        "page": item.get("page"),
                        "sheet": item.get("sheet"),
                        "confidence": item.get("confidence"),
                        "referenced objects": item.get("text_excerpt"),
                    }
                    for item in rows
                ],
                use_container_width=True,
                hide_index=True,
            )

        brief_refs = list(getattr(brief, "evidence_refs", []) or []) if brief else []
        if brief_refs:
            st.markdown("Brief Evidence")
            st.dataframe(brief_refs, use_container_width=True, hide_index=True)
        return


def _render_reports_page(st: Any, page: str) -> None:
    st.subheader(page)
    if page == "Reports":
        st.info(
            "Reporting module scaffolded. Use active Phase 2 pages for current outputs."
        )
    else:
        st.info(
            "Exports module scaffolded. Current deterministic export services remain unchanged."
        )


def _render_settings_page(st: Any, page: str) -> None:
    st.subheader(page)
    if page == "Project Settings":
        st.info("Project settings scaffold is available for future expansion.")
    else:
        st.info("Application settings scaffold is available for future expansion.")


def _render_context_panel(st: Any, context: dict[str, Any] | None) -> None:
    st.markdown("### Context Panel")
    selection = dict(
        st.session_state.get("atlas_context_selection") or {"kind": "project"}
    )
    kind = str(selection.get("kind") or "project")
    data = dict(selection.get("data") or {})

    def _render_object_context(
        title: str,
        object_data: dict[str, Any],
        nav_targets: list[tuple[str, str]],
    ) -> None:
        st.markdown(f"#### {title}")

        relationship_keys = [
            "referenced_drawings",
            "referenced_equipment",
            "referenced_specifications",
            "referenced_systems",
            "referenced_rfis",
            "referenced_evidence",
            "drawing_references",
            "specification_references",
            "potential_rfis",
        ]
        warning_keys = ["warnings"]

        property_rows = [
            {"property": key.replace("_", " "), "value": _safe_text(value, "n/a")}
            for key, value in object_data.items()
            if key not in relationship_keys + warning_keys
            and not isinstance(value, (dict, list))
        ]
        if property_rows:
            st.markdown("Properties")
            st.dataframe(property_rows[:12], use_container_width=True, hide_index=True)

        relationship_rows = [
            {
                "relationship": key.replace("_", " "),
                "objects": ", ".join(
                    [str(item) for item in list(object_data.get(key) or [])]
                )
                or "n/a",
            }
            for key in relationship_keys
            if list(object_data.get(key) or [])
        ]
        if relationship_rows:
            st.markdown("Relationships")
            st.dataframe(relationship_rows, use_container_width=True, hide_index=True)

        evidence_values = list(object_data.get("referenced_evidence") or [])
        if evidence_values:
            st.markdown("Evidence")
            st.dataframe(
                [{"evidence": str(item)} for item in evidence_values[:10]],
                use_container_width=True,
                hide_index=True,
            )

        warnings = list(object_data.get("warnings") or [])
        if warnings:
            st.markdown("Warnings")
            st.dataframe(
                [{"warning": str(item)} for item in warnings[:10]],
                use_container_width=True,
                hide_index=True,
            )

        related_rows = relationship_rows[:6]
        if related_rows:
            st.markdown("Related Objects")
            st.dataframe(related_rows, use_container_width=True, hide_index=True)

        st.markdown("Quick Navigation")
        for page, label in nav_targets:
            if st.button(
                label, key=f"atlas_ctx_nav_{title}_{page}", use_container_width=True
            ):
                st.session_state["atlas_active_page"] = page
                st.rerun()

    if kind == "drawing":
        _render_object_context(
            "Drawing",
            data,
            [
                ("Specifications", "Go to Specifications"),
                ("Equipment", "Go to Equipment"),
                ("Systems", "Go to Systems"),
                ("Evidence", "Go to Evidence"),
                ("RFI Candidates", "Go to RFIs"),
            ],
        )
        return

    if kind == "specification":
        _render_object_context(
            "Specification",
            data,
            [
                ("Drawings", "Go to Drawings"),
                ("Equipment", "Go to Equipment"),
                ("Systems", "Go to Systems"),
                ("Evidence", "Go to Evidence"),
            ],
        )
        return

    if kind == "equipment":
        _render_object_context(
            "Equipment",
            data,
            [
                ("Drawings", "Go to Drawings"),
                ("Specifications", "Go to Specifications"),
                ("Systems", "Go to Systems"),
                ("RFI Candidates", "Go to RFIs"),
            ],
        )
        return

    if kind == "system":
        _render_object_context(
            "System",
            data,
            [
                ("Equipment", "Go to Equipment"),
                ("Drawings", "Go to Drawings"),
                ("Specifications", "Go to Specifications"),
                ("RFI Candidates", "Go to RFIs"),
            ],
        )
        return

    if kind == "evidence":
        _render_object_context(
            "Evidence",
            data,
            [
                ("Drawings", "Go to Drawings"),
                ("Specifications", "Go to Specifications"),
                ("Evidence", "Refresh Evidence"),
            ],
        )
        return

    if kind == "file":
        file_item = dict(data.get("file") or {})
        folder = _safe_text(data.get("folder"), "Unknown")
        _render_object_context(
            f"File ({folder})",
            file_item,
            [
                ("Project Files", "Back to Project Files"),
                ("Drawings", "Open Drawings"),
                ("Specifications", "Open Specifications"),
            ],
        )
        return

    st.markdown("#### Project")
    if context is None:
        st.info(
            "Select a drawing, specification, equipment item, or file to inspect context."
        )
        return

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
            {"field": "Warnings", "value": len(list(context.get("warnings") or []))},
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_status_bar(
    st: Any, record: ProjectWorkspaceRecord, context: dict[str, Any] | None
) -> None:
    st.markdown("<div class='atlas-statusbar'></div>", unsafe_allow_html=True)
    intake = _safe_text(context.get("package_location") if context else None, "n/a")
    review_time = record.updated_at
    commit = _current_commit()

    cols = st.columns(5)
    cols[0].caption(f"Current project: {record.project.name}")
    cols[1].caption(f"Lifecycle stage: {_project_stage(record)}")
    cols[2].caption(f"Last intake: {intake}")
    cols[3].caption(f"Last review: {review_time}")
    cols[4].caption(f"Atlas v{__version__} · commit {commit}")


def _render_main_content(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    page = st.session_state.get("atlas_active_page", "Home")

    if page == "Home":
        _render_home_page(st, workspace_service)
    elif page == "Projects":
        _render_projects_page(st, workspace_service)
    elif page == "Reference Projects":
        _render_reference_projects_page(st, workspace_service)
    elif page == "Recent Projects":
        _render_recent_projects_page(st, workspace_service)
    elif page == "Create New Project":
        _render_create_project_page(st, workspace_service)
    elif page == "Open Existing Project":
        _render_open_existing_page(st, workspace_service)
    elif page == "Overview":
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
    elif page in BID_INTELLIGENCE_PAGES:
        _render_bid_page(st, page, context)
    elif page in REPORT_PAGES:
        _render_reports_page(st, page)
    elif page in SETTINGS_PAGES:
        _render_settings_page(st, page)


def _render_shell(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_header(st, workspace_service, record, context)
    _render_global_search_panel(st, context)

    current_page = st.session_state.get("atlas_active_page", "Home")
    st.markdown(
        f"<div class='atlas-breadcrumb'>{_breadcrumb(record, current_page)}</div>",
        unsafe_allow_html=True,
    )

    layout_mode = st.session_state.get("atlas_layout_mode", "Desktop")
    collapsed = bool(st.session_state.get("atlas_navigation_collapsed", False))

    if layout_mode == "Desktop":
        nav_col, main_col, context_col = st.columns([2.3, 6.4, 2.3])
        with nav_col:
            _nav_buttons(st, st, "desktop")
        with main_col:
            _render_main_content(st, workspace_service, record, context)
        with context_col:
            _render_context_panel(st, context)

    elif layout_mode == "Tablet":
        ctrl_cols = st.columns([2.2, 7.8])
        with ctrl_cols[0]:
            st.checkbox("Collapse Sidebar", key="atlas_navigation_collapsed")

        if collapsed:
            nav_popover = st.popover("Navigation")
            _nav_buttons(st, nav_popover, "tablet")
            main_col, context_col = st.columns([7.1, 2.9])
            with main_col:
                _render_main_content(st, workspace_service, record, context)
            with context_col:
                _render_context_panel(st, context)
        else:
            nav_col, main_col, context_col = st.columns([2.3, 5.5, 2.2])
            with nav_col:
                _nav_buttons(st, st, "tablet")
            with main_col:
                _render_main_content(st, workspace_service, record, context)
            with context_col:
                _render_context_panel(st, context)

    else:
        nav_drawer = st.popover("Open Navigation")
        _nav_buttons(st, nav_drawer, "mobile")
        main_col, context_col = st.columns([6.7, 3.3])
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

    record = _active_record(st, workspace_service)
    if record is None:
        st.error("No active project workspace available.")
        return

    context = _load_context_for_record(record)
    if context is not None:
        record = _build_record_from_context(context, existing_record=record)
        workspace_service.save_record(record)

    if st.session_state.get("atlas_active_page") not in ALL_ACTIVE_PAGES:
        st.session_state["atlas_active_page"] = "Home"

    _render_shell(st, workspace_service, record, context)


if __name__ == "__main__":
    main()

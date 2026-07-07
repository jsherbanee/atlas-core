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
from atlas_core.services.phase2_review_context_service import (
    DEFAULT_MAW_REFERENCE_PACKAGE,
    build_intake_review_context,
    build_reference_project_context,
)
from atlas_core.services.project_workspace_service import (
    ProjectWorkspaceRecord,
    ProjectWorkspaceService,
)
from atlas_core.services.engineering_insights_service import (
    EngineeringIntelligenceResult,
    EngineeringInsightsService,
)

PROJECT_MANAGER_PAGES = [
    "Home",
    "Projects",
    "Pinned Projects",
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
    "Engineering Intelligence",
    "Relationship Explorer",
    "Relationship Visualization",
    "Timeline",
    "Project Detail",
    "Drawing Detail",
    "Specification Detail",
    "Equipment Detail",
    "System Detail",
    "Room Detail",
    "Manufacturer Detail",
    "Evidence Detail",
    "Metadata Inspector",
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
    st.session_state.setdefault("atlas_search_type_filters", [])
    st.session_state.setdefault("atlas_relationship_search_enabled", False)
    st.session_state.setdefault("atlas_rename_project_name", "")
    st.session_state.setdefault("atlas_duplicate_project_id", "")
    st.session_state.setdefault("atlas_duplicate_project_name", "")
    st.session_state.setdefault("atlas_loaded_workspace_state_for", None)


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
    if record.package_location:
        package_path = Path(record.package_location)
        if package_path.exists() and package_path.is_dir():
            return build_reference_project_context(package_path)

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
    record.is_reference = True
    record.source_label = "Reference Project"
    workspace_service.save_record(record)
    workspace_service.set_reference_project(record.workspace_id, reference=True)
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
        for record in workspace_service.list_workspaces(
            include_archived=True,
            limit=1000,
        )
    }
    return records.get(active_id)


def _selector_options(
    recent: list[ProjectWorkspaceRecord],
    pinned: list[ProjectWorkspaceRecord],
    references: list[ProjectWorkspaceRecord],
) -> list[SelectorOption]:
    options = [SelectorOption(label="Recent Projects", kind="category")]
    options.extend(
        SelectorOption(
            label=f"Recent · {record.project.name}",
            kind="recent",
            value=record.workspace_id,
        )
        for record in recent[:20]
    )
    options.append(SelectorOption(label="Pinned Projects", kind="category"))
    options.extend(
        SelectorOption(
            label=f"Pinned · {record.project.name}",
            kind="recent",
            value=record.workspace_id,
        )
        for record in pinned[:20]
    )
    options.append(SelectorOption(label="Reference Projects", kind="category"))
    options.extend(
        SelectorOption(
            label=f"Reference · {record.project.name}",
            kind="recent",
            value=record.workspace_id,
        )
        for record in references[:20]
    )
    if not references:
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
        record.is_reference = True
        record.source_label = "Reference Project"
        workspace_service.save_record(record)
        workspace_service.set_reference_project(record.workspace_id, reference=True)
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
    pinned = workspace_service.list_pinned_workspaces(limit=30)
    references = workspace_service.list_reference_workspaces()
    options = _selector_options(recent, pinned, references)
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


def _workspace_state_snapshot(st: Any) -> dict[str, Any]:
    selection = dict(st.session_state.get("atlas_context_selection") or {})
    selected_kind = str(selection.get("kind") or "")
    selected_data = dict(selection.get("data") or {})
    selected_drawing = selected_data if selected_kind == "drawing" else None
    selected_specification = selected_data if selected_kind == "specification" else None

    return {
        "last_open_page": str(st.session_state.get("atlas_active_page") or "Home"),
        "selected_drawing": selected_drawing,
        "selected_specification": selected_specification,
        "expanded_navigation": [
            _group_for_page(str(st.session_state.get("atlas_active_page") or "Home"))
        ],
        "filters": {
            "file_search": str(st.session_state.get("atlas_file_search") or ""),
            "equipment_search": str(
                st.session_state.get("atlas_equipment_search") or ""
            ),
            "search_type_filters": list(
                st.session_state.get("atlas_search_type_filters") or []
            ),
            "relationship_search": bool(
                st.session_state.get("atlas_relationship_search_enabled", False)
            ),
        },
        "search_state": {
            "global_search": str(st.session_state.get("atlas_global_search") or ""),
            "result_index": int(st.session_state.get("atlas_global_search_index") or 0),
        },
        "window_preferences": {
            "layout_mode": str(st.session_state.get("atlas_layout_mode") or "Desktop"),
            "navigation_collapsed": bool(
                st.session_state.get("atlas_navigation_collapsed", False)
            ),
        },
        "context_selection": selection,
    }


def _restore_workspace_state(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
) -> None:
    marker = st.session_state.get("atlas_loaded_workspace_state_for")
    if marker == record.workspace_id:
        return

    state = workspace_service.load_workspace_state(record.workspace_id)
    if not state:
        st.session_state["atlas_loaded_workspace_state_for"] = record.workspace_id
        return

    st.session_state["atlas_active_page"] = str(state.get("last_open_page") or "Home")

    filters = dict(state.get("filters") or {})
    st.session_state["atlas_file_search"] = str(filters.get("file_search") or "")
    st.session_state["atlas_equipment_search"] = str(
        filters.get("equipment_search") or ""
    )
    st.session_state["atlas_search_type_filters"] = list(
        filters.get("search_type_filters") or []
    )
    st.session_state["atlas_relationship_search_enabled"] = bool(
        filters.get("relationship_search", False)
    )

    search_state = dict(state.get("search_state") or {})
    st.session_state["atlas_global_search"] = str(
        search_state.get("global_search") or ""
    )
    st.session_state["atlas_global_search_index"] = int(
        search_state.get("result_index") or 0
    )

    window_preferences = dict(state.get("window_preferences") or {})
    st.session_state["atlas_layout_mode"] = str(
        window_preferences.get("layout_mode") or "Desktop"
    )
    st.session_state["atlas_navigation_collapsed"] = bool(
        window_preferences.get("navigation_collapsed", False)
    )

    context_selection = state.get("context_selection")
    if isinstance(context_selection, dict):
        st.session_state["atlas_context_selection"] = dict(context_selection)

    st.session_state["atlas_loaded_workspace_state_for"] = record.workspace_id


def _persist_repository_artifacts(
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    if context is None:
        return

    review = context.get("review")
    if review is not None and hasattr(review, "to_dict"):
        workspace_service.save_review_artifact(
            record.workspace_id,
            "bid_package_review",
            dict(review.to_dict()),
        )

        readiness = getattr(review, "readiness", None)
        if readiness is not None and hasattr(readiness, "to_dict"):
            workspace_service.save_review_artifact(
                record.workspace_id,
                "readiness",
                dict(readiness.to_dict()),
            )

        rfi_candidates = [
            item.to_dict() if hasattr(item, "to_dict") else item
            for item in list(getattr(review, "rfi_candidates", []) or [])
        ]
        workspace_service.save_review_artifact(
            record.workspace_id,
            "rfi_candidates",
            {"items": rfi_candidates},
        )

        labor_estimate = getattr(review, "labor_estimate", None)
        if labor_estimate is not None and hasattr(labor_estimate, "to_dict"):
            workspace_service.save_review_artifact(
                record.workspace_id,
                "labor_estimate",
                dict(labor_estimate.to_dict()),
            )

    brief = context.get("brief")
    if brief is not None and hasattr(brief, "to_dict"):
        workspace_service.save_review_artifact(
            record.workspace_id,
            "estimator_brief",
            dict(brief.to_dict()),
        )

    revision_comparison = context.get("revision_comparison")
    if revision_comparison is not None and hasattr(revision_comparison, "to_dict"):
        workspace_service.save_review_artifact(
            record.workspace_id,
            "revision_comparison",
            dict(revision_comparison.to_dict()),
        )

    graph = _build_knowledge_graph(record, context)
    workspace_service.save_knowledge_graph(record.workspace_id, graph)

    intelligence = _build_engineering_intelligence(record, context)
    if intelligence is not None:
        workspace_service.save_engineering_intelligence(
            record.workspace_id,
            intelligence.to_dict(),
        )


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
    references = workspace_service.list_reference_workspaces()
    summary_cols = st.columns(4)
    _metric_card(summary_cols[0], "Recent Projects", str(len(recent)))
    _metric_card(summary_cols[1], "Reference Projects", str(len(references)))
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
    include_archived = st.checkbox("Show archived projects", value=False)
    records = workspace_service.list_workspaces(
        include_archived=include_archived,
        limit=500,
    )
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
                "pinned": record.pinned,
                "reference": record.is_reference,
                "archived": record.archived,
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

        action_cols = st.columns(4)
        if action_cols[0].button("Open Selected Project", type="primary"):
            st.session_state["atlas_active_workspace_id"] = selected.workspace_id
            st.session_state["atlas_active_page"] = "Overview"
            st.rerun()

        pin_label = "Unpin" if selected.pinned else "Pin"
        if action_cols[1].button(pin_label, use_container_width=True):
            workspace_service.pin_project(
                selected.workspace_id, pinned=not selected.pinned
            )
            st.rerun()

        reference_label = (
            "Unmark Reference" if selected.is_reference else "Mark Reference"
        )
        if action_cols[2].button(reference_label, use_container_width=True):
            workspace_service.set_reference_project(
                selected.workspace_id,
                reference=not selected.is_reference,
            )
            st.rerun()

        archive_label = "Unarchive" if selected.archived else "Archive"
        if action_cols[3].button(archive_label, use_container_width=True):
            workspace_service.archive_project(
                selected.workspace_id,
                archived=not selected.archived,
            )
            if selected.workspace_id == st.session_state.get(
                "atlas_active_workspace_id"
            ):
                st.session_state["atlas_active_workspace_id"] = None
                st.session_state["atlas_active_page"] = "Home"
            st.rerun()

        st.markdown("#### Rename Project")
        rename_name = st.text_input(
            "New project name",
            value=selected.project.name,
            key=f"atlas_rename_name_{selected.workspace_id}",
        )
        if st.button("Rename Project", key=f"atlas_rename_btn_{selected.workspace_id}"):
            if rename_name.strip():
                workspace_service.rename_project(
                    selected.workspace_id, rename_name.strip()
                )
                st.rerun()

        st.markdown("#### Duplicate Project")
        duplicate_id = st.text_input(
            "Duplicate project ID",
            value=f"{selected.workspace_id}-copy",
            key=f"atlas_duplicate_id_{selected.workspace_id}",
        )
        duplicate_name = st.text_input(
            "Duplicate project name",
            value=f"{selected.project.name} Copy",
            key=f"atlas_duplicate_name_{selected.workspace_id}",
        )
        if st.button(
            "Duplicate Project",
            key=f"atlas_duplicate_btn_{selected.workspace_id}",
        ):
            workspace_service.duplicate_project(
                selected.workspace_id,
                new_workspace_id=duplicate_id.strip(),
                new_name=duplicate_name.strip() or None,
            )
            st.rerun()

        if st.button(
            "Delete Project",
            key=f"atlas_delete_btn_{selected.workspace_id}",
            type="secondary",
        ):
            workspace_service.delete_project(selected.workspace_id)
            if selected.workspace_id == st.session_state.get(
                "atlas_active_workspace_id"
            ):
                st.session_state["atlas_active_workspace_id"] = None
                st.session_state["atlas_active_page"] = "Home"
            st.rerun()


def _render_pinned_projects_page(
    st: Any,
    workspace_service: ProjectWorkspaceService,
) -> None:
    st.subheader("Pinned Projects")
    records = workspace_service.list_pinned_workspaces(limit=200)
    if not records:
        st.info("No pinned projects yet.")
        return

    st.dataframe(
        [
            {
                "project": record.project.name,
                "project_id": record.project.project_id,
                "status": _project_stage(record),
                "updated": record.updated_at,
            }
            for record in records
        ],
        use_container_width=True,
        hide_index=True,
    )

    labels = [
        f"{record.project.name} · {record.project.project_id}" for record in records
    ]
    selected_label = st.selectbox("Open Pinned Project", options=labels)
    selected = records[labels.index(selected_label)]
    if st.button("Open Pinned Project", type="primary"):
        st.session_state["atlas_active_workspace_id"] = selected.workspace_id
        st.session_state["atlas_active_page"] = "Overview"
        st.rerun()


def _render_reference_projects_page(
    st: Any,
    workspace_service: ProjectWorkspaceService,
) -> None:
    st.subheader("Reference Projects")
    references = workspace_service.list_reference_workspaces(include_archived=False)
    if references:
        st.dataframe(
            [
                {
                    "project": record.project.name,
                    "project_id": record.workspace_id,
                    "status": _project_stage(record),
                    "updated": record.updated_at,
                }
                for record in references
            ],
            use_container_width=True,
            hide_index=True,
        )
        labels = [
            f"{record.project.name} · {record.workspace_id}" for record in references
        ]
        selected_label = st.selectbox("Open Reference Project", options=labels)
        selected = references[labels.index(selected_label)]
        if st.button("Open Selected Reference", type="primary"):
            st.session_state["atlas_active_workspace_id"] = selected.workspace_id
            st.session_state["atlas_active_page"] = "Overview"
            st.rerun()

    st.markdown(
        "<span class='atlas-chip'>Reference</span> Music Academy of the West",
        unsafe_allow_html=True,
    )
    st.caption("Canonical deterministic reference project for local review.")
    if st.button("Import MAW Reference", type="primary"):
        context = build_reference_project_context(DEFAULT_MAW_REFERENCE_PACKAGE)
        record = _build_record_from_context(context)
        record.is_reference = True
        record.source_label = "Reference Project"
        workspace_service.save_record(record)
        workspace_service.set_reference_project(record.workspace_id, reference=True)
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
        consultant = st.text_input("Consultant")
        architect = st.text_input("Architect")
        engineers_text = st.text_input("Engineers (comma-separated)")
        project_number = st.text_input("Project Number")
        issue_date = st.text_input("Issue Date")
        location = st.text_input("Location", key="atlas_new_project_location")
        bid_date = st.text_input("Bid Date", key="atlas_new_project_bid_date")
        lifecycle_stage = st.selectbox(
            "Lifecycle Stage",
            options=[status.value for status in ProjectStatus],
            index=1,
        )
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
        consultant=consultant.strip() or None,
        architect=architect.strip() or None,
        engineers=[
            item.strip()
            for item in engineers_text.split(",")
            if isinstance(item, str) and item.strip()
        ],
        project_number=project_number.strip() or None,
        issue_date=issue_date.strip() or None,
        location=location.strip() or None,
        bid_date=bid_date.strip() or None,
        status=ProjectStatus(lifecycle_stage),
        lifecycle_stage=lifecycle_stage,
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
        placeholder="AtlasProjects/example-project/project.json",
    )

    if not st.button("Open Path", type="primary"):
        return

    path = Path(path_text).expanduser()
    if not path.exists():
        st.error(f"Path not found: {path}")
        return

    if path.is_dir() and (path / "project.json").exists():
        record = workspace_service.load_record(path / "project.json")
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Overview"
        st.rerun()
        return

    if path.is_dir() and (path / "workspace.json").exists():
        record = workspace_service.load_record(path / "workspace.json")
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Overview"
        st.rerun()
        return

    if path.name in {"workspace.json", "project.json", "metadata.json"}:
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
        "Open a project.json/workspace.json file, intake_snapshot.json file, or project folder."
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


def _timeline_events(
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    import_summary = dict(context.get("import_summary") or {}) if context else {}
    review = context.get("review") if context else None
    brief = context.get("brief") if context else None
    revision = context.get("revision_comparison") if context else None

    events = [
        {
            "event": "Project intake",
            "timestamp": record.created_at,
            "status": "Completed",
            "details": _safe_text(
                context.get("data_source_label") if context else "Manual", "Manual"
            ),
        },
        {
            "event": "Document imports",
            "timestamp": record.updated_at,
            "status": "Completed",
            "details": f"{import_summary.get('total_files', 0)} files",
        },
        {
            "event": "Review run",
            "timestamp": record.updated_at,
            "status": "Completed" if review is not None else "Pending",
            "details": _safe_text(getattr(review, "review_id", None), "n/a"),
        },
        {
            "event": "Revision comparison",
            "timestamp": record.updated_at,
            "status": "Completed" if revision is not None else "Not Available",
            "details": _safe_text(
                getattr(revision, "comparison_revision_id", None),
                "No revision comparison",
            ),
        },
        {
            "event": "Readiness update",
            "timestamp": record.updated_at,
            "status": "Completed" if review is not None else "Pending",
            "details": _safe_text(
                getattr(
                    getattr(
                        getattr(review, "readiness", None), "readiness_level", None
                    ),
                    "value",
                    None,
                ),
                "n/a",
            ),
        },
        {
            "event": "Estimator brief generation",
            "timestamp": record.updated_at,
            "status": "Completed" if brief is not None else "Pending",
            "details": _safe_text(getattr(brief, "brief_title", None), "n/a"),
        },
        {
            "event": "Future collaboration milestones",
            "timestamp": "n/a",
            "status": "Disabled",
            "details": "Future events are intentionally disabled for local deterministic mode.",
        },
    ]
    return events


def _build_knowledge_graph(
    record: ProjectWorkspaceRecord | None,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    objects = _workspace_objects(context)
    import_summary = dict(context.get("import_summary") or {}) if context else {}
    review = context.get("review") if context else None
    revision = context.get("revision_comparison") if context else None

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    def _add_node(
        node_id: str,
        node_type: str,
        label: str,
        page: str,
        selection_kind: str,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "label": label,
                "page": page,
                "selection_kind": selection_kind,
                "data": dict(data or {}),
                "metadata": dict(metadata or {}),
            }
        )

    def _add_edge(
        source: str,
        target: str,
        relationship: str,
        confidence: str = "n/a",
        source_evidence: str = "n/a",
    ) -> None:
        edge_key = (source, target, relationship)
        if edge_key in seen_edges:
            return
        seen_edges.add(edge_key)
        edges.append(
            {
                "source": source,
                "target": target,
                "relationship": relationship,
                "confidence": confidence,
                "source_evidence": source_evidence,
            }
        )

    created_at = _safe_text(getattr(record, "created_at", None), "n/a")
    updated_at = _safe_text(getattr(record, "updated_at", None), "n/a")
    project_record = getattr(record, "project", None)
    project_key = _safe_text(
        getattr(project_record, "project_id", None),
        _safe_text(
            context.get("sample_project_id") if context else None, "atlas-project"
        ),
    )
    project_name = _safe_text(
        getattr(project_record, "name", None),
        _safe_text(
            context.get("sample_project_name") if context else None, "Atlas Project"
        ),
    )
    project_client = _safe_text(getattr(project_record, "client", None), "Atlas")

    project_id = f"project:{project_key}"
    _add_node(
        project_id,
        "Project",
        project_name,
        "Project Detail",
        "project",
        data={
            "project_id": project_key,
            "name": project_name,
            "client": project_client,
            "location": _safe_text(getattr(project_record, "location", None), "n/a"),
            "bid_date": _safe_text(getattr(project_record, "bid_date", None), "n/a"),
            "status": _project_stage(record) if record is not None else "Intake",
        },
        metadata={
            "source_file": _safe_text(
                context.get("package_location") if context else None, "n/a"
            ),
            "source_page": "n/a",
            "sheet_number": "n/a",
            "specification_section": "n/a",
            "extraction_confidence": "n/a",
            "creation_timestamp": created_at,
            "last_update": updated_at,
        },
    )

    for item in objects.get("drawings", []):
        drawing_node = f"drawing:{item.get('drawing_number', 'unknown')}"
        _add_node(
            drawing_node,
            "Drawing",
            _safe_text(item.get("drawing_number"), "Drawing"),
            "Drawing Detail",
            "drawing",
            data=item,
            metadata={
                "source_file": _safe_text(item.get("source_file"), "n/a"),
                "source_page": "n/a",
                "sheet_number": _safe_text(item.get("drawing_number"), "n/a"),
                "specification_section": "n/a",
                "extraction_confidence": _safe_text(
                    item.get("extraction_quality"), "n/a"
                ),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            drawing_node,
            "Project contains Drawing",
            "high",
            _safe_text(item.get("source_file"), "n/a"),
        )

    for item in objects.get("specifications", []):
        spec_node = f"spec:{item.get('section', 'unknown')}"
        _add_node(
            spec_node,
            "Specification",
            _safe_text(item.get("section"), "Specification"),
            "Specification Detail",
            "specification",
            data=item,
            metadata={
                "source_file": _safe_text(item.get("source_file"), "n/a"),
                "source_page": "n/a",
                "sheet_number": "n/a",
                "specification_section": _safe_text(item.get("section"), "n/a"),
                "extraction_confidence": _safe_text(
                    item.get("extraction_confidence"), "n/a"
                ),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            spec_node,
            "Project contains Specification",
            "high",
            _safe_text(item.get("source_file"), "n/a"),
        )

    for item in objects.get("equipment", []):
        eq_node = f"equipment:{item.get('equipment_id', 'unknown')}"
        _add_node(
            eq_node,
            "Equipment",
            _safe_text(item.get("equipment_id"), "Equipment"),
            "Equipment Detail",
            "equipment",
            data=item,
            metadata={
                "source_file": ", ".join(item.get("drawing_references", [])) or "n/a",
                "source_page": "n/a",
                "sheet_number": ", ".join(item.get("drawing_references", [])) or "n/a",
                "specification_section": ", ".join(
                    item.get("specification_references", [])
                )
                or "n/a",
                "extraction_confidence": _safe_text(item.get("confidence"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            eq_node,
            "Project contains Equipment",
            "high",
            ", ".join(item.get("drawing_references", [])) or "n/a",
        )

        system_node = f"system:{item.get('system', 'unknown')}"
        _add_node(
            system_node,
            "System",
            _safe_text(item.get("system"), "System"),
            "System Detail",
            "system",
            data={"system": _safe_text(item.get("system"), "Unknown")},
            metadata={
                "source_file": ", ".join(item.get("drawing_references", [])) or "n/a",
                "source_page": "n/a",
                "sheet_number": ", ".join(item.get("drawing_references", [])) or "n/a",
                "specification_section": ", ".join(
                    item.get("specification_references", [])
                )
                or "n/a",
                "extraction_confidence": _safe_text(item.get("confidence"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )

        room_name = _safe_text(item.get("room"), "Unknown")
        room_node = f"room:{room_name}"
        _add_node(
            room_node,
            "Room",
            room_name,
            "Room Detail",
            "room",
            data={"room": room_name},
            metadata={
                "source_file": ", ".join(item.get("drawing_references", [])) or "n/a",
                "source_page": "n/a",
                "sheet_number": ", ".join(item.get("drawing_references", [])) or "n/a",
                "specification_section": ", ".join(
                    item.get("specification_references", [])
                )
                or "n/a",
                "extraction_confidence": _safe_text(item.get("confidence"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )

        area_name = room_name.split("-")[0].strip() if room_name else "General"
        area_node = f"area:{area_name or 'General'}"
        _add_node(
            area_node,
            "Area",
            area_name or "General",
            "Room Detail",
            "room",
            data={"area": area_name or "General"},
            metadata={
                "source_file": _safe_text(
                    context.get("package_location") if context else None, "n/a"
                ),
                "source_page": "n/a",
                "sheet_number": "n/a",
                "specification_section": "n/a",
                "extraction_confidence": "n/a",
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )

        manufacturer = _safe_text(item.get("manufacturer"), "Unknown")
        manufacturer_node = f"manufacturer:{manufacturer}"
        _add_node(
            manufacturer_node,
            "Manufacturer",
            manufacturer,
            "Manufacturer Detail",
            "manufacturer",
            data={"manufacturer": manufacturer},
            metadata={
                "source_file": _safe_text(
                    context.get("package_location") if context else None, "n/a"
                ),
                "source_page": "n/a",
                "sheet_number": "n/a",
                "specification_section": "n/a",
                "extraction_confidence": _safe_text(item.get("confidence"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )

        product = _safe_text(item.get("model"), "Unknown")
        product_node = f"product:{manufacturer}:{product}"
        _add_node(
            product_node,
            "Product",
            product,
            "Equipment Detail",
            "model",
            data={"manufacturer": manufacturer, "model": product},
            metadata={
                "source_file": ", ".join(item.get("drawing_references", [])) or "n/a",
                "source_page": "n/a",
                "sheet_number": ", ".join(item.get("drawing_references", [])) or "n/a",
                "specification_section": ", ".join(
                    item.get("specification_references", [])
                )
                or "n/a",
                "extraction_confidence": _safe_text(item.get("confidence"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )

        _add_edge(
            eq_node,
            system_node,
            "Equipment to System",
            _safe_text(item.get("confidence"), "n/a"),
            ", ".join(item.get("drawing_references", [])) or "n/a",
        )
        _add_edge(
            system_node,
            room_node,
            "System to Room",
            _safe_text(item.get("confidence"), "n/a"),
            ", ".join(item.get("drawing_references", [])) or "n/a",
        )
        _add_edge(
            room_node,
            area_node,
            "Room to Area",
            "high",
            _safe_text(context.get("package_location") if context else None, "n/a"),
        )
        _add_edge(
            manufacturer_node,
            product_node,
            "Manufacturer to Product",
            "high",
            _safe_text(context.get("package_location") if context else None, "n/a"),
        )
        _add_edge(
            product_node,
            eq_node,
            "Product to Equipment",
            _safe_text(item.get("confidence"), "n/a"),
            ", ".join(item.get("drawing_references", [])) or "n/a",
        )

        for drawing_ref in item.get("drawing_references", []):
            drawing_node = f"drawing:{drawing_ref}"
            _add_edge(
                drawing_node,
                eq_node,
                "Drawing to Equipment",
                _safe_text(item.get("confidence"), "n/a"),
                drawing_ref,
            )
        for spec_ref in item.get("specification_references", []):
            spec_node = f"spec:{spec_ref}"
            _add_edge(
                eq_node,
                spec_node,
                "Equipment to Specification",
                _safe_text(item.get("confidence"), "n/a"),
                spec_ref,
            )

    for item in objects.get("specifications", []):
        spec_node = f"spec:{item.get('section', 'unknown')}"
        for drawing_ref in item.get("referenced_drawings", []):
            drawing_node = f"drawing:{drawing_ref}"
            _add_edge(
                spec_node,
                drawing_node,
                "Specification to Drawing",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                _safe_text(item.get("source_file"), "n/a"),
            )

    for item in objects.get("evidence", []):
        evidence_id = f"evidence:{_safe_text(item.get('source_file'), 'file')}:{item.get('page', 'n/a')}"
        _add_node(
            evidence_id,
            "Evidence",
            f"{_safe_text(item.get('source_file'), 'Evidence')} p.{item.get('page', 'n/a')}",
            "Evidence Detail",
            "evidence",
            data=item,
            metadata={
                "source_file": _safe_text(item.get("source_file"), "n/a"),
                "source_page": _safe_text(item.get("page"), "n/a"),
                "sheet_number": _safe_text(item.get("sheet"), "n/a"),
                "specification_section": "n/a",
                "extraction_confidence": _safe_text(item.get("confidence"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )

        document_id = f"document:{_safe_text(item.get('source_file'), 'unknown')}"
        _add_node(
            document_id,
            "Document",
            _safe_text(item.get("source_file"), "Document"),
            "Evidence Detail",
            "evidence",
            data={"source_file": _safe_text(item.get("source_file"), "n/a")},
            metadata={
                "source_file": _safe_text(item.get("source_file"), "n/a"),
                "source_page": _safe_text(item.get("page"), "n/a"),
                "sheet_number": _safe_text(item.get("sheet"), "n/a"),
                "specification_section": "n/a",
                "extraction_confidence": _safe_text(item.get("confidence"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            document_id,
            evidence_id,
            "Document to Evidence",
            _safe_text(item.get("confidence"), "n/a"),
            _safe_text(item.get("source_file"), "n/a"),
        )

        for drawing in objects.get("drawings", []):
            if _contains_any(
                item.get("source_file"),
                [drawing.get("source_file", ""), drawing.get("drawing_number", "")],
            ):
                _add_edge(
                    f"drawing:{drawing.get('drawing_number', 'unknown')}",
                    evidence_id,
                    "Drawing to Evidence",
                    _safe_text(item.get("confidence"), "n/a"),
                    _safe_text(item.get("source_file"), "n/a"),
                )

    for item in _to_rows(list(getattr(review, "engineering_assumptions", []) or [])):
        assumption_id = _safe_text(
            item.get("assumption_id"), _safe_text(item.get("title"), "assumption")
        )
        node_id = f"assumption:{assumption_id}"
        _add_node(
            node_id,
            "Engineering Assumption",
            assumption_id,
            "Engineering Assumptions",
            "assumption",
            data=item,
            metadata={
                "source_file": _safe_text(item.get("source_file"), "n/a"),
                "source_page": _safe_text(item.get("page"), "n/a"),
                "sheet_number": _safe_text(item.get("sheet"), "n/a"),
                "specification_section": _safe_text(item.get("section"), "n/a"),
                "extraction_confidence": _safe_text(item.get("confidence"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            node_id,
            "Project to Assumption",
            _safe_text(item.get("confidence"), "n/a"),
            _safe_text(item.get("source_file"), "n/a"),
        )

        for evidence in objects.get("evidence", []):
            evidence_id = f"evidence:{_safe_text(evidence.get('source_file'), 'file')}:{evidence.get('page', 'n/a')}"
            if _contains_any(str(item), [_safe_text(evidence.get("source_file"), "")]):
                _add_edge(
                    evidence_id,
                    node_id,
                    "Evidence to Assumption",
                    _safe_text(evidence.get("confidence"), "n/a"),
                    _safe_text(evidence.get("source_file"), "n/a"),
                )

    for item in objects.get("rfis", []):
        rfi_id = _safe_text(item.get("rfi_id"), _safe_text(item.get("title"), "rfi"))
        node_id = f"rfi:{rfi_id}"
        _add_node(
            node_id,
            "RFI Candidate",
            rfi_id,
            "RFI Candidates",
            "rfi",
            data=item,
            metadata={
                "source_file": _safe_text(item.get("source_file"), "n/a"),
                "source_page": _safe_text(item.get("page"), "n/a"),
                "sheet_number": _safe_text(item.get("sheet_number"), "n/a"),
                "specification_section": _safe_text(item.get("section"), "n/a"),
                "extraction_confidence": _safe_text(item.get("confidence"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )

        for equipment in objects.get("equipment", []):
            if _contains_any(
                str(item),
                [equipment.get("equipment_id", ""), equipment.get("model", "")],
            ):
                _add_edge(
                    node_id,
                    f"equipment:{equipment.get('equipment_id', 'unknown')}",
                    "RFI to Equipment",
                    _safe_text(item.get("confidence"), "n/a"),
                    _safe_text(item.get("source_file"), "n/a"),
                )

    labor_estimate = (
        getattr(review, "labor_estimate", None) if review is not None else None
    )
    if labor_estimate is not None:
        labor_node = "labor_estimate:current"
        _add_node(
            labor_node,
            "Labor Estimate",
            "Current Labor Estimate",
            "Labor Estimate",
            "labor",
            data={
                "total_labor_hours_expected": getattr(
                    labor_estimate, "total_labor_hours_expected", None
                ),
                "confidence": getattr(labor_estimate, "confidence", None),
            },
            metadata={
                "source_file": _safe_text(
                    context.get("package_location") if context else None, "n/a"
                ),
                "source_page": "n/a",
                "sheet_number": "n/a",
                "specification_section": "n/a",
                "extraction_confidence": _safe_text(
                    getattr(labor_estimate, "confidence", None), "n/a"
                ),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            labor_node,
            "Project to Labor Estimate",
            _safe_text(getattr(labor_estimate, "confidence", None), "n/a"),
            _safe_text(context.get("package_location") if context else None, "n/a"),
        )

    if revision is not None:
        revision_node = f"revision:{_safe_text(getattr(revision, 'comparison_revision_id', 'current'), 'current')}"
        _add_node(
            revision_node,
            "Revision",
            _safe_text(
                getattr(revision, "comparison_revision_id", None), "Current Revision"
            ),
            "Revision Comparison",
            "revision",
            data={
                "baseline_revision_id": _safe_text(
                    getattr(revision, "baseline_revision_id", None), "n/a"
                ),
                "comparison_revision_id": _safe_text(
                    getattr(revision, "comparison_revision_id", None), "n/a"
                ),
                "change_count": len(getattr(revision, "changes", []) or []),
            },
            metadata={
                "source_file": _safe_text(
                    context.get("package_location") if context else None, "n/a"
                ),
                "source_page": "n/a",
                "sheet_number": "n/a",
                "specification_section": "n/a",
                "extraction_confidence": "high",
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            revision_node,
            "Project to Revision",
            "high",
            _safe_text(context.get("package_location") if context else None, "n/a"),
        )

    file_diags = list(import_summary.get("file_diagnostics") or [])
    for diag in file_diags:
        file_name = _safe_text(diag.get("file_name"), "unknown")
        node_id = f"document:{file_name}"
        _add_node(
            node_id,
            "Document",
            file_name,
            "Project Files",
            "file",
            data=diag,
            metadata={
                "source_file": file_name,
                "source_page": "n/a",
                "sheet_number": "n/a",
                "specification_section": "n/a",
                "extraction_confidence": _safe_text(diag.get("status"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            node_id,
            "Project to Document",
            _safe_text(diag.get("status"), "n/a"),
            file_name,
        )

    id_to_index = {node["id"]: index for index, node in enumerate(nodes)}
    relationship_counts: defaultdict[str, int] = defaultdict(int)
    evidence_counts: defaultdict[str, int] = defaultdict(int)
    for edge in edges:
        relationship_counts[edge["source"]] += 1
        relationship_counts[edge["target"]] += 1
        if "Evidence" in edge["relationship"]:
            evidence_counts[edge["source"]] += 1
            evidence_counts[edge["target"]] += 1

    for node_id, count in relationship_counts.items():
        node = nodes[id_to_index[node_id]]
        node.setdefault("metadata", {})["relationship_count"] = count
        node.setdefault("metadata", {})["evidence_count"] = evidence_counts[node_id]

    return {"nodes": nodes, "edges": edges}


def _node_by_id(graph: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for node in graph.get("nodes", []):
        if node.get("id") == node_id:
            return node
    return None


def _node_label(graph: dict[str, Any], node_id: str) -> str:
    node = _node_by_id(graph, node_id)
    if node is None:
        return node_id
    return _safe_text(node.get("label"), node_id)


def _node_relationships(
    graph: dict[str, Any], node_id: str
) -> dict[str, list[dict[str, Any]]]:
    incoming = [
        edge for edge in graph.get("edges", []) if edge.get("target") == node_id
    ]
    outgoing = [
        edge for edge in graph.get("edges", []) if edge.get("source") == node_id
    ]
    return {"incoming": incoming, "outgoing": outgoing}


def _relationship_subgraph(
    graph: dict[str, Any],
    root_node_id: str,
    depth: int,
) -> dict[str, Any]:
    visited = {root_node_id}
    frontier = {root_node_id}
    selected_edges: list[dict[str, Any]] = []

    for _ in range(max(depth, 1)):
        next_frontier: set[str] = set()
        for edge in graph.get("edges", []):
            source = str(edge.get("source"))
            target = str(edge.get("target"))
            if source in frontier or target in frontier:
                selected_edges.append(edge)
                next_frontier.add(source)
                next_frontier.add(target)
        frontier = next_frontier - visited
        visited.update(next_frontier)
        if not frontier:
            break

    selected_nodes = [
        node for node in graph.get("nodes", []) if node.get("id") in visited
    ]
    dedup_edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for edge in selected_edges:
        key = (
            str(edge.get("source")),
            str(edge.get("target")),
            str(edge.get("relationship")),
        )
        if key in seen:
            continue
        seen.add(key)
        dedup_edges.append(edge)

    return {"nodes": selected_nodes, "edges": dedup_edges}


def _metadata_for_selection(
    graph: dict[str, Any],
    selection: dict[str, Any],
) -> dict[str, Any] | None:
    kind = str(selection.get("kind") or "")
    data = dict(selection.get("data") or {})
    if not kind:
        return None

    candidates: list[str] = []
    if kind == "drawing":
        candidates.append(f"drawing:{_safe_text(data.get('drawing_number'), '')}")
    elif kind == "specification":
        candidates.append(f"spec:{_safe_text(data.get('section'), '')}")
    elif kind == "equipment":
        candidates.append(f"equipment:{_safe_text(data.get('equipment_id'), '')}")
    elif kind == "system":
        candidates.append(f"system:{_safe_text(data.get('system'), '')}")
    elif kind == "room":
        candidates.append(f"room:{_safe_text(data.get('room'), '')}")
    elif kind == "manufacturer":
        candidates.append(f"manufacturer:{_safe_text(data.get('manufacturer'), '')}")
    elif kind == "evidence":
        candidates.append(
            f"evidence:{_safe_text(data.get('source_file'), 'file')}:{data.get('page', 'n/a')}"
        )
    elif kind == "project":
        project_id = _safe_text(data.get("project_id"), "")
        if project_id:
            candidates.append(f"project:{project_id}")

    for node_id in candidates:
        node = _node_by_id(graph, node_id)
        if node is not None:
            metadata = dict(node.get("metadata") or {})
            metadata["label"] = _safe_text(node.get("label"), "n/a")
            metadata["type"] = _safe_text(node.get("type"), "n/a")
            return metadata
    return None


def _build_engineering_intelligence(
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> EngineeringIntelligenceResult | None:
    if context is None:
        return None

    review = context.get("review")
    if review is None:
        return None

    brief = context.get("brief")
    graph = _build_knowledge_graph(record=record, context=context)
    return EngineeringInsightsService().build(
        review=review,
        knowledge_graph=graph,
        estimator_brief=brief,
    )


def _top_reference_counts(
    graph: dict[str, Any],
    node_prefix: str,
    relationship_contains: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    counts: defaultdict[str, int] = defaultdict(int)
    for edge in list(graph.get("edges", [])):
        source = _safe_text(edge.get("source"), "")
        relationship = _safe_text(edge.get("relationship"), "")
        if not source.startswith(node_prefix):
            continue
        if relationship_contains.lower() not in relationship.lower():
            continue
        counts[source] += 1

    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [
        {"object": item[0].split(":", 1)[1], "references": item[1]}
        for item in ranked[:limit]
    ]


def _render_engineering_intelligence_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Engineering Intelligence")
    intelligence = _build_engineering_intelligence(record, context)
    if intelligence is None:
        st.info(
            "Engineering insights are unavailable until a project review context is loaded."
        )
        return

    graph = _build_knowledge_graph(record=record, context=context)
    insights = list(intelligence.insights)
    systems = list(intelligence.system_health)
    recommendations = list(intelligence.recommendations)

    st.markdown("#### Project Health")
    st.dataframe(
        [
            {
                "project health score": intelligence.project_health.score,
                "created by": intelligence.project_health.created_by_engine_version,
                "rationale": " | ".join(intelligence.project_health.rationale[:3]),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.dataframe(
        [item.to_dict() for item in intelligence.project_health.categories],
        use_container_width=True,
        hide_index=True,
    )

    filter_cols = st.columns([1.2, 1.4, 1.4, 1.2, 1.2])
    severity_filter = filter_cols[0].multiselect(
        "Severity",
        options=sorted({item.severity for item in insights}),
        default=[],
    )
    category_filter = filter_cols[1].multiselect(
        "Category",
        options=sorted({item.category for item in insights}),
        default=[],
    )
    sort_key = filter_cols[2].selectbox(
        "Sort",
        options=["priority", "severity", "confidence", "category"],
    )
    sort_order = filter_cols[3].selectbox("Order", options=["Descending", "Ascending"])
    group_by = filter_cols[4].selectbox(
        "Group By",
        options=["Severity", "Category", "System", "Drawing", "Specification", "None"],
    )

    filtered = [
        item
        for item in insights
        if (not severity_filter or item.severity in severity_filter)
        and (not category_filter or item.category in category_filter)
    ]

    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    priority_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

    def _sort_value(item: Any) -> Any:
        if sort_key == "priority":
            return priority_rank.get(item.priority, 0)
        if sort_key == "severity":
            return severity_rank.get(item.severity.lower(), 0)
        if sort_key == "confidence":
            return item.confidence
        return item.category

    filtered.sort(key=_sort_value, reverse=sort_order == "Descending")

    st.markdown("#### Top Engineering Insights")
    if not filtered:
        st.info("No insights match the selected filters.")
    else:
        rows = [
            {
                "priority": item.priority,
                "severity": item.severity,
                "category": item.category,
                "confidence": round(item.confidence, 2),
                "title": item.title,
                "recommended action": item.recommended_action,
                "supporting objects": ", ".join(item.supporting_objects[:4]),
                "evidence refs": ", ".join(item.evidence_refs[:4]),
            }
            for item in filtered
        ]

        if group_by != "None":
            grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in rows:
                if group_by == "Severity":
                    key = _safe_text(row["severity"], "Unknown")
                elif group_by == "Category":
                    key = _safe_text(row["category"], "Unknown")
                elif group_by == "System":
                    key = next(
                        (
                            token
                            for token in _split_refs(row["supporting objects"])
                            if "sys" in token.lower() or "system" in token.lower()
                        ),
                        "Unassigned",
                    )
                elif group_by == "Drawing":
                    key = next(
                        (
                            token
                            for token in _split_refs(row["supporting objects"])
                            if "av-" in token.lower() or "drawing" in token.lower()
                        ),
                        "Unassigned",
                    )
                else:
                    key = next(
                        (
                            token
                            for token in _split_refs(row["supporting objects"])
                            if "27 " in token or "spec" in token.lower()
                        ),
                        "Unassigned",
                    )
                grouped[key].append(row)

            for key in sorted(grouped.keys()):
                st.markdown(f"##### {group_by}: {key}")
                st.dataframe(grouped[key], use_container_width=True, hide_index=True)
        else:
            st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("#### Critical Risks")
    critical = [item for item in insights if item.priority == "Critical"][:8]
    st.dataframe(
        [
            {
                "title": item.title,
                "category": item.category,
                "confidence": round(item.confidence, 2),
                "action": item.recommended_action,
            }
            for item in critical
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Coordination Issues")
    coordination = [item for item in insights if item.category == "Coordination Issue"][
        :8
    ]
    st.dataframe(
        [
            {
                "title": item.title,
                "severity": item.severity,
                "supporting objects": ", ".join(item.supporting_objects[:5]),
            }
            for item in coordination
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### High-Risk Systems")
    risk_systems = sorted(systems, key=lambda item: item.health_score)[:8]
    st.dataframe(
        [
            {
                "system": item.system_name,
                "health score": item.health_score,
                "confidence": item.confidence,
                "outstanding rfis": item.outstanding_rfis,
                "outstanding assumptions": item.outstanding_assumptions,
                "warnings": " | ".join(item.warnings[:2]),
            }
            for item in risk_systems
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Most Referenced Drawings")
    drawing_refs = _top_reference_counts(graph, "drawing:", "Drawing")
    st.dataframe(drawing_refs, use_container_width=True, hide_index=True)

    st.markdown("#### Most Referenced Specifications")
    spec_refs = _top_reference_counts(graph, "spec:", "Specification")
    st.dataframe(spec_refs, use_container_width=True, hide_index=True)

    st.markdown("#### Top Equipment Risks")
    equipment_risk = [
        item
        for item in insights
        if "equipment" in " ".join(item.supporting_objects).lower()
    ][:8]
    st.dataframe(
        [
            {
                "title": item.title,
                "severity": item.severity,
                "priority": item.priority,
                "action": item.recommended_action,
            }
            for item in equipment_risk
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Highest Confidence Recommendations")
    best = sorted(recommendations, key=lambda item: item.confidence, reverse=True)[:10]
    st.dataframe(
        [
            {
                "title": item.title,
                "confidence": round(item.confidence, 2),
                "recommended action": item.recommended_action,
                "traceability": ", ".join(item.evidence_refs[:3]),
            }
            for item in best
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_global_search_panel(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    query = str(st.session_state.get("atlas_global_search") or "").strip()
    if not query:
        return

    entries = _global_search_entries(context)
    kind_options = sorted(
        {str(item.get("kind") or "") for item in entries if item.get("kind")}
    )

    with st.expander("Search Filters", expanded=False):
        selected_types = st.multiselect(
            "Type filters",
            options=kind_options,
            default=[],
            key="atlas_search_type_filters",
            help="Filter by object type (drawing, specification, room, system, manufacturer, model, evidence, etc.).",
        )
        relationship_search = st.checkbox(
            "Enable relationship search",
            key="atlas_relationship_search_enabled",
            value=False,
        )

    graph = (
        _build_knowledge_graph(record=record, context=context)
        if context
        else {"nodes": [], "edges": []}
    )

    def _score(item: dict[str, Any]) -> int:
        name = _safe_text(item.get("name"), "").lower()
        subtitle = _safe_text(item.get("subtitle"), "").lower()
        q = query.lower()
        if name == q:
            return 0
        if name.startswith(q):
            return 1
        if q in name:
            return 2
        if subtitle == q:
            return 3
        if q in subtitle:
            return 4
        if _in_text(item.get("kind"), query):
            return 5
        return 9

    filtered = []
    for item in entries:
        if selected_types and str(item.get("kind")) not in selected_types:
            continue

        text_match = (
            _in_text(item.get("name"), query)
            or _in_text(item.get("subtitle"), query)
            or _in_text(item.get("kind"), query)
        )

        if relationship_search and not text_match:
            node_label = _safe_text(item.get("name"), "")
            node_matches = [
                node
                for node in graph.get("nodes", [])
                if _in_text(node.get("label"), node_label)
            ]
            for node in node_matches:
                relationships = _node_relationships(
                    graph, _safe_text(node.get("id"), "")
                )
                related_text = " ".join(
                    [
                        _safe_text(edge.get("relationship"), "")
                        + " "
                        + _safe_text(edge.get("source_evidence"), "")
                        for edge in relationships.get("incoming", [])
                        + relationships.get("outgoing", [])
                    ]
                )
                if _in_text(related_text, query):
                    text_match = True
                    break

        if text_match:
            filtered.append(item)

    filtered.sort(key=_score)

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


def _render_upload_panel(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
) -> None:
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
        with st.spinner("Running deterministic intake and review..."):
            updated_record = workspace_service.import_uploaded_documents(
                workspace_id=record.workspace_id,
                uploaded_files=[
                    (str(file.name), bytes(file.getvalue()))
                    for file in uploaded_files or []
                ],
            )
            st.session_state["atlas_uploaded_context"] = (
                build_reference_project_context(
                    updated_record.package_location
                    if updated_record.package_location is not None
                    else Path(
                        workspace_service.project_location(updated_record.workspace_id)
                    )
                    / "documents"
                )
            )

        context = st.session_state.get("atlas_uploaded_context")
        if context is not None:
            refreshed_record = _build_record_from_context(
                context,
                existing_record=updated_record,
            )
            refreshed_record.workspace_state = dict(updated_record.workspace_state)
            refreshed_record.pinned = updated_record.pinned
            refreshed_record.is_reference = updated_record.is_reference
            refreshed_record.archived = updated_record.archived
            workspace_service.save_record(refreshed_record)
            st.session_state["atlas_active_workspace_id"] = (
                refreshed_record.workspace_id
            )
            st.success("Atlas Intake completed and workspace updated.")
            st.rerun()


def _render_project_files_page(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Project Explorer")
    _render_upload_panel(st, workspace_service, record)

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


def _render_systems_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Systems Workspace")
    rows = list(_workspace_objects(context).get("systems", []))
    intelligence = _build_engineering_intelligence(record, context)
    system_health_map = (
        {item.system_id: item for item in list(intelligence.system_health)}
        if intelligence is not None
        else {}
    )

    def _system_row(item: dict[str, Any]) -> dict[str, Any]:
        health = system_health_map.get(item["system"])
        return {
            "system": item["system"],
            "equipment count": item["equipment_count"],
            "drawing count": item["drawing_count"],
            "specification count": item["specification_count"],
            "rfi count": item["rfi_count"],
            "readiness": item["readiness"],
            "labor": item["labor"],
            "confidence": item["confidence"],
            "health score": health.health_score if health is not None else "n/a",
            "equipment completeness": (
                health.equipment_completeness if health is not None else "n/a"
            ),
            "specification coverage": (
                health.specification_coverage if health is not None else "n/a"
            ),
            "drawing coverage": (
                health.drawing_coverage if health is not None else "n/a"
            ),
            "outstanding assumptions": (
                health.outstanding_assumptions if health is not None else "n/a"
            ),
            "labor confidence": (
                health.labor_confidence if health is not None else "n/a"
            ),
            "warnings": " | ".join(health.warnings[:2]) if health is not None else "",
        }

    if not rows:
        st.info("No systems available.")
        return

    st.dataframe(
        [_system_row(item) for item in rows],
        use_container_width=True,
        hide_index=True,
    )

    labels = [item["system"] for item in rows]
    selected_label = st.selectbox("Select System Object", options=labels)
    selected = rows[labels.index(selected_label)]
    _set_context_selection(st, "system", selected)


def _render_relationship_explorer_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Relationship Explorer")
    graph = _build_knowledge_graph(record, context)
    nodes = list(graph.get("nodes", []))
    if not nodes:
        st.info("No relationship graph nodes are available yet.")
        return

    labels = [f"{node['type']}: {node['label']}" for node in nodes]
    selected_label = st.selectbox("Select Object", options=labels)
    selected_node = nodes[labels.index(selected_label)]
    depth = st.slider("Recursive expansion depth", min_value=1, max_value=4, value=2)

    relationships = _node_relationships(graph, _safe_text(selected_node.get("id"), ""))
    incoming = relationships.get("incoming", [])
    outgoing = relationships.get("outgoing", [])

    st.markdown("#### Incoming Relationships")
    if incoming:
        st.dataframe(
            [
                {
                    "from": _node_label(graph, _safe_text(edge["source"], "n/a")),
                    "relationship": edge.get("relationship"),
                    "confidence": edge.get("confidence"),
                    "source evidence": edge.get("source_evidence"),
                }
                for edge in incoming
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No incoming relationships.")

    st.markdown("#### Outgoing Relationships")
    if outgoing:
        st.dataframe(
            [
                {
                    "to": _node_label(graph, _safe_text(edge["target"], "n/a")),
                    "relationship": edge.get("relationship"),
                    "confidence": edge.get("confidence"),
                    "source evidence": edge.get("source_evidence"),
                }
                for edge in outgoing
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No outgoing relationships.")

    subgraph = _relationship_subgraph(
        graph, _safe_text(selected_node.get("id"), ""), depth
    )
    st.markdown(f"#### Expanded Relationships (Depth {depth})")
    st.dataframe(
        [
            {
                "source": _node_label(graph, _safe_text(edge["source"], "n/a")),
                "target": _node_label(graph, _safe_text(edge["target"], "n/a")),
                "relationship": edge.get("relationship"),
                "confidence": edge.get("confidence"),
                "source evidence": edge.get("source_evidence"),
            }
            for edge in subgraph.get("edges", [])
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_relationship_visualization_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Relationship Visualization")
    graph = _build_knowledge_graph(record, context)
    nodes = list(graph.get("nodes", []))
    if not nodes:
        st.info("No relationships available for visualization.")
        return

    labels = [f"{node['type']}: {node['label']}" for node in nodes]
    selected_label = st.selectbox("Selected Object", options=labels)
    selected_node = nodes[labels.index(selected_label)]
    node_id = _safe_text(selected_node.get("id"), "")
    relationships = _node_relationships(graph, node_id)
    connected_ids = {node_id}
    connected_edges = list(relationships.get("incoming", [])) + list(
        relationships.get("outgoing", [])
    )
    for edge in connected_edges:
        connected_ids.add(_safe_text(edge.get("source"), ""))
        connected_ids.add(_safe_text(edge.get("target"), ""))

    connected_nodes = [node for node in nodes if node.get("id") in connected_ids]
    id_to_label = {
        _safe_text(node.get("id"), ""): f"{node.get('type')} {node.get('label')}"
        for node in connected_nodes
    }

    mermaid_lines = ["graph LR"]
    for edge in connected_edges[:40]:
        source = _safe_text(edge.get("source"), "")
        target = _safe_text(edge.get("target"), "")
        source_label = id_to_label.get(source, source).replace('"', "")
        target_label = id_to_label.get(target, target).replace('"', "")
        rel = _safe_text(edge.get("relationship"), "linked").replace('"', "")
        mermaid_lines.append(f'    "{source_label}" -->|"{rel}"| "{target_label}"')

    st.markdown("```mermaid\n" + "\n".join(mermaid_lines) + "\n```")

    st.markdown("Connected Objects")
    st.dataframe(
        [
            {
                "type": node.get("type"),
                "label": node.get("label"),
                "page": node.get("page"),
            }
            for node in connected_nodes
        ],
        use_container_width=True,
        hide_index=True,
    )

    node_options = [
        f"{node.get('type')}: {node.get('label')}" for node in connected_nodes
    ]
    selected_nav = st.selectbox("Navigate to Node", options=node_options)
    target_node = connected_nodes[node_options.index(selected_nav)]
    if st.button("Open Node", type="primary"):
        st.session_state["atlas_active_page"] = _safe_text(
            target_node.get("page"), "Overview"
        )
        _set_context_selection(
            st,
            _safe_text(target_node.get("selection_kind"), "project"),
            dict(target_node.get("data") or {}),
        )
        st.rerun()


def _render_timeline_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Project Timeline")
    events = _timeline_events(record, context)
    st.dataframe(events, use_container_width=True, hide_index=True)


def _select_first_node(graph: dict[str, Any], node_type: str) -> dict[str, Any] | None:
    for node in graph.get("nodes", []):
        if _safe_text(node.get("type"), "") == node_type:
            return node
    return None


def _node_for_current_selection(
    graph: dict[str, Any],
    kind: str,
    data: dict[str, Any],
    fallback_type: str,
) -> dict[str, Any] | None:
    if kind == "drawing":
        node_id = f"drawing:{_safe_text(data.get('drawing_number'), '')}"
        return _node_by_id(graph, node_id)
    if kind == "specification":
        node_id = f"spec:{_safe_text(data.get('section'), '')}"
        return _node_by_id(graph, node_id)
    if kind == "equipment":
        node_id = f"equipment:{_safe_text(data.get('equipment_id'), '')}"
        return _node_by_id(graph, node_id)
    if kind == "system":
        node_id = f"system:{_safe_text(data.get('system'), '')}"
        return _node_by_id(graph, node_id)
    if kind == "room":
        node_id = f"room:{_safe_text(data.get('room'), '')}"
        return _node_by_id(graph, node_id)
    if kind == "manufacturer":
        node_id = f"manufacturer:{_safe_text(data.get('manufacturer'), '')}"
        return _node_by_id(graph, node_id)
    if kind == "evidence":
        node_id = f"evidence:{_safe_text(data.get('source_file'), 'file')}:{data.get('page', 'n/a')}"
        return _node_by_id(graph, node_id)
    if kind == "project":
        node_id = f"project:{_safe_text(data.get('project_id'), '')}"
        return _node_by_id(graph, node_id)
    return _select_first_node(graph, fallback_type)


def _render_object_detail_page(
    st: Any,
    title: str,
    node_type: str,
    fallback_kind: str,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader(title)
    graph = _build_knowledge_graph(record, context)
    selection = dict(st.session_state.get("atlas_context_selection") or {})
    selected = _node_for_current_selection(
        graph,
        _safe_text(selection.get("kind"), fallback_kind),
        dict(selection.get("data") or {}),
        node_type,
    )
    if selected is None:
        selected = _select_first_node(graph, node_type)
    if selected is None:
        st.info(f"No {node_type.lower()} objects are available.")
        return

    relationships = _node_relationships(graph, _safe_text(selected.get("id"), ""))
    incoming = relationships.get("incoming", [])
    outgoing = relationships.get("outgoing", [])
    node_data = dict(selected.get("data") or {})
    metadata = dict(selected.get("metadata") or {})

    st.markdown("Properties")
    props = [
        {"property": key.replace("_", " "), "value": _safe_text(value, "n/a")}
        for key, value in node_data.items()
        if not isinstance(value, (list, dict))
    ]
    st.dataframe(props[:20], use_container_width=True, hide_index=True)

    st.markdown("Relationships")
    rel_rows = [
        {
            "direction": "Incoming",
            "object": _node_label(graph, _safe_text(edge["source"], "n/a")),
            "relationship": edge.get("relationship"),
            "confidence": edge.get("confidence"),
            "source evidence": edge.get("source_evidence"),
        }
        for edge in incoming
    ] + [
        {
            "direction": "Outgoing",
            "object": _node_label(graph, _safe_text(edge["target"], "n/a")),
            "relationship": edge.get("relationship"),
            "confidence": edge.get("confidence"),
            "source evidence": edge.get("source_evidence"),
        }
        for edge in outgoing
    ]
    if rel_rows:
        st.dataframe(rel_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No relationships available.")

    warnings = list(node_data.get("warnings") or [])
    st.markdown("Warnings")
    if warnings:
        st.dataframe(
            [{"warning": str(item)} for item in warnings],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No warnings for this object.")

    st.markdown("Evidence")
    evidence_rows = [
        {
            "source evidence": edge.get("source_evidence"),
            "relationship": edge.get("relationship"),
        }
        for edge in rel_rows
        if _safe_text(edge.get("source evidence"), "n/a") != "n/a"
    ]
    if evidence_rows:
        st.dataframe(evidence_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No evidence references attached.")

    st.markdown("Traceability")
    st.caption("Every recommendation links back to deterministic source evidence.")
    source_file = _safe_text(metadata.get("source_file"), "n/a")
    st.dataframe(
        [
            {"field": "Source file", "value": source_file},
            {
                "field": "Source page",
                "value": _safe_text(metadata.get("source_page"), "n/a"),
            },
            {
                "field": "Sheet number",
                "value": _safe_text(metadata.get("sheet_number"), "n/a"),
            },
            {
                "field": "Specification section",
                "value": _safe_text(metadata.get("specification_section"), "n/a"),
            },
        ],
        use_container_width=True,
        hide_index=True,
    )
    if st.button("Open Originating Evidence", key=f"atlas_trace_{title}"):
        st.session_state["atlas_active_page"] = "Evidence"
        st.rerun()

    st.markdown("Timeline")
    st.dataframe(
        _timeline_events(record, context)[:6], use_container_width=True, hide_index=True
    )


def _render_metadata_inspector_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Metadata Inspector")
    graph = _build_knowledge_graph(record, context)
    selection = dict(
        st.session_state.get("atlas_context_selection")
        or {"kind": "project", "data": {"project_id": record.project.project_id}}
    )
    metadata = _metadata_for_selection(graph, selection)
    if metadata is None:
        st.info("Select an object to inspect metadata.")
        return

    st.dataframe(
        [
            {"field": "Object", "value": _safe_text(metadata.get("label"), "n/a")},
            {"field": "Type", "value": _safe_text(metadata.get("type"), "n/a")},
            {
                "field": "Source file",
                "value": _safe_text(metadata.get("source_file"), "n/a"),
            },
            {
                "field": "Source page",
                "value": _safe_text(metadata.get("source_page"), "n/a"),
            },
            {
                "field": "Sheet number",
                "value": _safe_text(metadata.get("sheet_number"), "n/a"),
            },
            {
                "field": "Specification section",
                "value": _safe_text(metadata.get("specification_section"), "n/a"),
            },
            {
                "field": "Extraction confidence",
                "value": _safe_text(metadata.get("extraction_confidence"), "n/a"),
            },
            {
                "field": "Creation timestamp",
                "value": _safe_text(metadata.get("creation_timestamp"), "n/a"),
            },
            {
                "field": "Last update",
                "value": _safe_text(metadata.get("last_update"), "n/a"),
            },
            {
                "field": "Relationship count",
                "value": _safe_text(metadata.get("relationship_count"), "0"),
            },
            {
                "field": "Evidence count",
                "value": _safe_text(metadata.get("evidence_count"), "0"),
            },
        ],
        use_container_width=True,
        hide_index=True,
    )


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
        st.caption(
            "Traceability: readiness signals are derived from deterministic extraction outputs and linked source evidence."
        )
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
        st.caption("Where did Atlas get this? See traceability references below.")
        st.write(brief.executive_summary)
        actions = list(brief.prioritized_reviewer_actions or [])
        if actions:
            st.dataframe(actions, use_container_width=True, hide_index=True)
        evidence_refs = list(getattr(brief, "evidence_refs", []) or [])
        if evidence_refs:
            st.markdown("Traceability References")
            st.dataframe(evidence_refs, use_container_width=True, hide_index=True)
            if st.button("Open Evidence Workspace", key="atlas_brief_open_evidence"):
                st.session_state["atlas_active_page"] = "Evidence"
                st.rerun()
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


def _render_settings_page(
    st: Any,
    page: str,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
) -> None:
    st.subheader(page)
    if page == "Project Settings":
        manifest = workspace_service.read_manifest(record.workspace_id)
        health = workspace_service.project_health(record.workspace_id)

        st.markdown("### Project Repository / Storage")
        st.dataframe(
            [
                {
                    "field": "Repository Location",
                    "value": str(workspace_service.workspace_root),
                },
                {
                    "field": "Project Count",
                    "value": len(
                        workspace_service.list_workspaces(
                            include_archived=True,
                            limit=2000,
                        )
                    ),
                },
                {
                    "field": "Selected Project Storage Path",
                    "value": workspace_service.project_location(record.workspace_id),
                },
                {
                    "field": "Manifest Schema Version",
                    "value": manifest.get("schema_version", "n/a"),
                },
                {
                    "field": "Manifest Storage Version",
                    "value": manifest.get("storage_version", "n/a"),
                },
                {
                    "field": "Health Status",
                    "value": health.get("status", "unknown"),
                },
                {
                    "field": "Last Validation",
                    "value": health.get("validated_at", "n/a"),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("Manifest Summary")
        st.dataframe(
            [
                {
                    "project_id": manifest.get("project_id", record.workspace_id),
                    "project_name": manifest.get("project_name", record.project.name),
                    "status": manifest.get("status", "n/a"),
                    "lifecycle_stage": manifest.get("lifecycle_stage", "n/a"),
                    "updated_at": manifest.get("updated_at", "n/a"),
                    "documents": sum(
                        int(value)
                        for value in dict(
                            manifest.get("document_counts") or {}
                        ).values()
                    ),
                    "review_artifacts": sum(
                        int(value)
                        for value in dict(
                            manifest.get("review_artifact_counts") or {}
                        ).values()
                    ),
                    "history_events": manifest.get("history_event_count", 0),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

        bundle_name = f"{record.workspace_id}.atlaspkg"
        bundle_output = st.text_input(
            "Export bundle path",
            value=str(Path("outputs") / bundle_name),
            key="atlas_project_export_path",
        )
        if st.button("Export Project Bundle", key="atlas_export_bundle_btn"):
            written = workspace_service.export_project_bundle(
                record.workspace_id,
                bundle_output,
            )
            st.success(f"Exported bundle to {written}")

        import_path = st.text_input(
            "Import bundle path (.atlaspkg)",
            value="",
            key="atlas_project_import_path",
        )
        if st.button("Import Project Bundle", key="atlas_import_bundle_btn"):
            imported = workspace_service.import_project_bundle(import_path)
            st.session_state["atlas_active_workspace_id"] = imported.workspace_id
            st.success(f"Imported project {imported.workspace_id}")
            st.rerun()

        if health.get("errors"):
            st.markdown("Health Errors")
            st.dataframe(
                [{"error": item} for item in list(health.get("errors") or [])],
                use_container_width=True,
                hide_index=True,
            )
        if health.get("warnings"):
            st.markdown("Health Warnings")
            st.dataframe(
                [{"warning": item} for item in list(health.get("warnings") or [])],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("Application settings scaffold is available for future expansion.")


def _render_context_panel(st: Any, context: dict[str, Any] | None) -> None:
    st.markdown("### Context Panel")
    selection = dict(
        st.session_state.get("atlas_context_selection") or {"kind": "project"}
    )
    kind = str(selection.get("kind") or "project")
    data = dict(selection.get("data") or {})
    graph = (
        _build_knowledge_graph(record=None, context=context)
        if context
        else {"nodes": [], "edges": []}
    )

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

    st.markdown("Metadata Inspector")
    metadata = _metadata_for_selection(graph, {"kind": kind, "data": data})
    if metadata is None and kind == "project":
        metadata = {
            "source_file": _safe_text(context.get("package_location"), "n/a"),
            "source_page": "n/a",
            "sheet_number": "n/a",
            "specification_section": "n/a",
            "extraction_confidence": "n/a",
            "creation_timestamp": "n/a",
            "last_update": "n/a",
            "relationship_count": 0,
            "evidence_count": 0,
            "label": "Project",
            "type": "Project",
        }
    if metadata:
        st.dataframe(
            [
                {"field": "Object", "value": _safe_text(metadata.get("label"), "n/a")},
                {"field": "Type", "value": _safe_text(metadata.get("type"), "n/a")},
                {
                    "field": "Source file",
                    "value": _safe_text(metadata.get("source_file"), "n/a"),
                },
                {
                    "field": "Source page",
                    "value": _safe_text(metadata.get("source_page"), "n/a"),
                },
                {
                    "field": "Sheet",
                    "value": _safe_text(metadata.get("sheet_number"), "n/a"),
                },
                {
                    "field": "Specification section",
                    "value": _safe_text(metadata.get("specification_section"), "n/a"),
                },
                {
                    "field": "Extraction confidence",
                    "value": _safe_text(metadata.get("extraction_confidence"), "n/a"),
                },
                {
                    "field": "Creation timestamp",
                    "value": _safe_text(metadata.get("creation_timestamp"), "n/a"),
                },
                {
                    "field": "Last update",
                    "value": _safe_text(metadata.get("last_update"), "n/a"),
                },
                {
                    "field": "Relationship count",
                    "value": _safe_text(metadata.get("relationship_count"), "0"),
                },
                {
                    "field": "Evidence count",
                    "value": _safe_text(metadata.get("evidence_count"), "0"),
                },
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
    elif page == "Pinned Projects":
        _render_pinned_projects_page(st, workspace_service)
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
        _render_project_files_page(st, workspace_service, record, context)
    elif page == "Drawings":
        _render_drawings_page(st, context)
    elif page == "Specifications":
        _render_specifications_page(st, context)
    elif page == "Equipment":
        _render_equipment_page(st, context)
    elif page == "Systems":
        _render_systems_page(st, record, context)
    elif page == "Engineering Intelligence":
        _render_engineering_intelligence_page(st, record, context)
    elif page == "Relationship Explorer":
        _render_relationship_explorer_page(st, record, context)
    elif page == "Relationship Visualization":
        _render_relationship_visualization_page(st, record, context)
    elif page == "Timeline":
        _render_timeline_page(st, record, context)
    elif page == "Project Detail":
        _render_object_detail_page(
            st,
            title="Project Detail",
            node_type="Project",
            fallback_kind="project",
            record=record,
            context=context,
        )
    elif page == "Drawing Detail":
        _render_object_detail_page(
            st,
            title="Drawing Detail",
            node_type="Drawing",
            fallback_kind="drawing",
            record=record,
            context=context,
        )
    elif page == "Specification Detail":
        _render_object_detail_page(
            st,
            title="Specification Detail",
            node_type="Specification",
            fallback_kind="specification",
            record=record,
            context=context,
        )
    elif page == "Equipment Detail":
        _render_object_detail_page(
            st,
            title="Equipment Detail",
            node_type="Equipment",
            fallback_kind="equipment",
            record=record,
            context=context,
        )
    elif page == "System Detail":
        _render_object_detail_page(
            st,
            title="System Detail",
            node_type="System",
            fallback_kind="system",
            record=record,
            context=context,
        )
    elif page == "Room Detail":
        _render_object_detail_page(
            st,
            title="Room Detail",
            node_type="Room",
            fallback_kind="room",
            record=record,
            context=context,
        )
    elif page == "Manufacturer Detail":
        _render_object_detail_page(
            st,
            title="Manufacturer Detail",
            node_type="Manufacturer",
            fallback_kind="manufacturer",
            record=record,
            context=context,
        )
    elif page == "Evidence Detail":
        _render_object_detail_page(
            st,
            title="Evidence Detail",
            node_type="Evidence",
            fallback_kind="evidence",
            record=record,
            context=context,
        )
    elif page == "Metadata Inspector":
        _render_metadata_inspector_page(st, record, context)
    elif page in BID_INTELLIGENCE_PAGES:
        _render_bid_page(st, page, context)
    elif page in REPORT_PAGES:
        _render_reports_page(st, page)
    elif page in SETTINGS_PAGES:
        _render_settings_page(st, page, workspace_service, record)


def _render_shell(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_header(st, workspace_service, record, context)
    _render_global_search_panel(st, record, context)

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

    _restore_workspace_state(st, workspace_service, record)

    context = _load_context_for_record(record)
    if context is not None:
        record = _build_record_from_context(context, existing_record=record)
        record.workspace_state = workspace_service.load_workspace_state(
            record.workspace_id
        )
        record.pinned = bool(record.metadata.get("pinned", record.pinned))
        record.is_reference = bool(
            record.metadata.get("reference", record.is_reference)
        )
        record.archived = bool(record.metadata.get("archived", record.archived))
        workspace_service.save_record(record)
        _persist_repository_artifacts(workspace_service, record, context)
        workspace_service.log_event(
            record.workspace_id,
            "review_executed",
            {"source_mode": record.source_mode, "project_id": record.project_id},
        )

    if st.session_state.get("atlas_active_page") not in ALL_ACTIVE_PAGES:
        st.session_state["atlas_active_page"] = "Home"

    _render_shell(st, workspace_service, record, context)
    workspace_service.save_workspace_state(
        record.workspace_id,
        _workspace_state_snapshot(st),
    )


if __name__ == "__main__":
    main()

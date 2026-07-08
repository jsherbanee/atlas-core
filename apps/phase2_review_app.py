"""Atlas Workspace v1.5 project-centric shell for Phase 2 review outputs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
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
from atlas_core.services.drawing_intelligence import DrawingIntelligenceEngine
from atlas_core.services.specification_intelligence import (
    SpecificationIntelligenceEngine,
    SpecificationReferenceType,
)
from atlas_core.services.coordination_intelligence import CoordinationIntelligenceEngine
from atlas_core.services.resolver import EngineeringResolver, ResolverContext
from atlas_core.services.master_library import MasterLibraryService

PROJECT_MANAGER_PAGES = [
    "Mission Control",
    "Projects",
    "Pinned Projects",
    "Reference Projects",
    "Recent Projects",
    "Create New Project",
    "Open Existing Project",
]

NAV_DROPDOWN_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Projects",
        [
            ("Projects", "Projects"),
            ("Pinned Projects", "Pinned Projects"),
            ("Reference Projects", "Reference Projects"),
            ("Recent Projects", "Recent Projects"),
            ("Create New Project", "Create New Project"),
            ("Open Existing Project", "Open Existing Project"),
        ],
    ),
    (
        "Knowledge",
        [
            ("Knowledge Graph", "Relationship Visualization"),
            ("Relationships", "Relationship Explorer"),
            ("Evidence", "Evidence"),
            ("History", "History"),
            ("Master Library", "Master Library Explorer"),
        ],
    ),
    (
        "Reports",
        [
            ("Reports", "Reports"),
            ("Estimator Brief", "Estimator Brief"),
            ("Readiness", "Readiness"),
            ("Labor Estimate", "Labor Estimate"),
            ("Revision Comparison", "Revision Comparison"),
            ("Exports", "Exports"),
        ],
    ),
    (
        "Administration",
        [
            ("Project Settings", "Project Settings"),
            ("Application Settings", "Application Settings"),
        ],
    ),
]

ENGINEERING_PAGES = [
    "Overview",
    "Engineering Workbench",
    "Engineering Notebook",
    "Project Files",
    "Drawings",
    "Drawing Explorer",
    "Specifications",
    "Specification Explorer",
    "Equipment",
    "Systems",
    "Engineering Resolver",
    "Resolver Conflict Center",
    "Engineering Intelligence",
    "Coordination Review",
]

KNOWLEDGE_PAGES = [
    "Relationship Visualization",
    "Relationship Explorer",
    "Evidence",
    "History",
    "Master Library Explorer",
    "Metadata Inspector",
]

PROJECT_PAGES = (
    ENGINEERING_PAGES
    + KNOWLEDGE_PAGES
    + [
        "Executive Summary",
        "Project Detail",
        "Drawing Detail",
        "Specification Detail",
        "Equipment Detail",
        "System Detail",
        "Room Detail",
        "Manufacturer Detail",
        "Evidence Detail",
    ]
)

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

REPORT_PAGES = [
    "Reports",
    "Estimator Brief",
    "Readiness",
    "Labor Estimate",
    "Revision Comparison",
    "Exports",
]
SETTINGS_PAGES = ["Project Settings", "Application Settings"]

NOTEBOOK_ENTRY_TYPES = [
    "Engineering Note",
    "Observation",
    "Decision",
    "Assumption",
    "Question",
    "Follow-up",
    "Customer Clarification",
    "Consultant Clarification",
    "Internal Coordination",
    "Site Visit",
    "Meeting Note",
    "Review Summary",
]

NOTEBOOK_PRIORITIES = ["Critical", "High", "Medium", "Low"]
NOTEBOOK_STATUSES = ["Open", "In Review", "Resolved", "Approved"]

INVESTIGATION_SELECTION_KINDS = {
    "drawing",
    "specification",
    "equipment",
    "system",
    "room",
    "manufacturer",
    "evidence",
    "resolved",
    "resolver_conflict",
    "rfi",
}

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


def _render_page_header(st: Any, title: str, subtitle: str) -> None:
    st.subheader(title)
    st.caption(subtitle)


def _render_empty_state(st: Any, message: str) -> None:
    st.info(message)


def _context_cache_bucket(context: dict[str, Any] | None) -> dict[str, Any]:
    if context is None:
        return {}
    bucket = context.get("_atlas_ui_cache")
    if isinstance(bucket, dict):
        return bucket
    bucket = {}
    context["_atlas_ui_cache"] = bucket
    return bucket


def _context_cached(
    context: dict[str, Any] | None,
    cache_key: str,
) -> Any | None:
    bucket = _context_cache_bucket(context)
    return bucket.get(cache_key)


def _set_context_cached(
    context: dict[str, Any] | None,
    cache_key: str,
    value: Any,
) -> None:
    bucket = _context_cache_bucket(context)
    if bucket is not None:
        bucket[cache_key] = value


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _date_prefix(value: Any) -> str:
    text = _safe_text(value, "")
    if len(text) >= 10:
        return text[:10]
    return ""


def _notebook_sort_key(entry: dict[str, Any]) -> str:
    return _safe_text(entry.get("created_at"), "")


def _is_decision_log_entry(entry: dict[str, Any]) -> bool:
    entry_type = _safe_text(entry.get("entry_type"), "").strip().lower()
    status = _safe_text(entry.get("status"), "").strip().lower()
    if entry_type == "decision":
        return True
    if entry_type == "assumption" and status == "approved":
        return True
    if entry_type in {"customer clarification", "consultant clarification"}:
        return status == "resolved"
    return False


def _atlas_generated_notebook_entries(
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if context is None:
        return []

    review = context.get("review")
    readiness = getattr(review, "readiness", None) if review is not None else None
    brief = context.get("brief")
    revision = context.get("revision_comparison")
    resolver = _build_engineering_resolver(record=None, context=context)
    objects = _workspace_objects(context)

    entries: list[dict[str, Any]] = []
    created_at = _safe_text(record.updated_at, _now_iso())
    project_ref = f"project:{record.project.project_id}"

    def _add(
        key: str,
        title: str,
        body: str,
        entry_type: str = "Review Summary",
        priority: str = "Medium",
        status: str = "Resolved",
        related_objects: list[str] | None = None,
        evidence_refs: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        entries.append(
            {
                "entry_id": f"atlas:{key}:{_safe_text(record.updated_at, 'current')}",
                "created_at": created_at,
                "author": "Atlas",
                "title": title,
                "body": body,
                "entry_type": entry_type,
                "priority": priority,
                "status": status,
                "related_objects": sorted({project_ref, *(related_objects or [])}),
                "evidence_refs": list(evidence_refs or []),
                "tags": ["Atlas Generated", *(tags or [])],
                "created_by_engine_version": f"atlas-workspace/{__version__}",
                "read_only": True,
                "system_generated": True,
            }
        )

    if review is not None:
        _add(
            key="engineering-review-completed",
            title="Engineering Review Completed",
            body="Deterministic engineering review outputs were generated for the active project context.",
            related_objects=[project_ref],
            tags=["Milestone"],
        )

    if resolver is not None:
        conflicts = list(getattr(resolver, "conflicts", []) or [])
        if conflicts:
            _add(
                key="resolver-conflicts",
                title="Resolver Generated Conflicts",
                body=f"Engineering Resolver generated {len(conflicts)} conflict records requiring review.",
                priority="High",
                related_objects=[
                    f"resolver_conflict:{_safe_text(item.conflict_id, 'conflict')}"
                    for item in conflicts[:6]
                ],
                tags=["Resolver"],
            )

    if readiness is not None:
        blockers = list(getattr(readiness, "blocking_issues", []) or [])
        _add(
            key="readiness-updated",
            title="Readiness Updated",
            body=(
                f"Readiness level is {_safe_text(getattr(getattr(readiness, 'readiness_level', None), 'value', None), 'unknown')} "
                f"with {len(blockers)} blocking issues."
            ),
            priority="High" if blockers else "Medium",
            status="In Review" if blockers else "Resolved",
            tags=["Readiness"],
        )

    if brief is not None:
        _add(
            key="estimator-brief",
            title="Estimator Brief Generated",
            body="Estimator brief was generated with prioritized reviewer actions and traceability references.",
            related_objects=["labor_estimate:current"],
            tags=["Estimator Brief"],
        )

    if revision is not None:
        _add(
            key="revision-comparison",
            title="Revision Comparison Executed",
            body=(
                f"Revision comparison completed with {len(list(getattr(revision, 'changes', []) or []))} tracked changes."
            ),
            related_objects=[
                f"revision:{_safe_text(getattr(revision, 'comparison_revision_id', None), 'current')}"
            ],
            tags=["Revision"],
        )

    coordination_findings = list(objects.get("coordination_findings") or [])
    if coordination_findings:
        _add(
            key="coordination-review",
            title="Coordination Review Completed",
            body=(
                f"Coordination review generated {len(coordination_findings)} findings across drawing/spec/equipment/system relationships."
            ),
            entry_type="Observation",
            priority="High",
            related_objects=[
                f"coordination_finding:{_safe_text(item.get('finding_id'), 'finding')}"
                for item in coordination_findings[:6]
            ],
            tags=["Coordination"],
        )

    entries.sort(key=_notebook_sort_key, reverse=True)
    return entries


def _notebook_entries(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    user_entries = list(st.session_state.get("atlas_notebook_entries") or [])
    generated = _atlas_generated_notebook_entries(record, context)
    merged = {str(item.get("entry_id")): dict(item) for item in generated}
    for item in user_entries:
        merged[str(item.get("entry_id"))] = dict(item)
    entries = list(merged.values())
    entries.sort(key=_notebook_sort_key, reverse=True)
    return entries


def _sync_notebook_state_to_context(st: Any, context: dict[str, Any] | None) -> None:
    if context is None:
        return
    _set_context_cached(
        context,
        "notebook_user_entries",
        list(st.session_state.get("atlas_notebook_entries") or []),
    )


def _entry_matches_date_window(
    entry: dict[str, Any],
    start_date: str,
    end_date: str,
) -> bool:
    date_value = _date_prefix(entry.get("created_at"))
    if not date_value:
        return True
    if start_date and date_value < start_date:
        return False
    if end_date and date_value > end_date:
        return False
    return True


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
    st.session_state.setdefault("atlas_active_page", "Mission Control")
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
    st.session_state.setdefault("atlas_quick_jump", "Current Page")
    st.session_state.setdefault("atlas_equipment_search", "")
    st.session_state.setdefault("atlas_search_type_filters", [])
    st.session_state.setdefault("atlas_relationship_search_enabled", False)
    st.session_state.setdefault("atlas_rename_project_name", "")
    st.session_state.setdefault("atlas_duplicate_project_id", "")
    st.session_state.setdefault("atlas_duplicate_project_name", "")
    st.session_state.setdefault("atlas_loaded_workspace_state_for", None)
    st.session_state.setdefault("atlas_notebook_entries", [])
    st.session_state.setdefault("atlas_notebook_search", "")
    st.session_state.setdefault("atlas_notebook_draft", {})
    st.session_state.setdefault("atlas_master_library_search", "")


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
    if page == "Mission Control":
        return "Mission Control"
    if page in {
        "Projects",
        "Pinned Projects",
        "Reference Projects",
        "Recent Projects",
        "Create New Project",
        "Open Existing Project",
    }:
        return "Projects"
    if page in ENGINEERING_PAGES:
        return "Engineering"
    if page in KNOWLEDGE_PAGES:
        return "Knowledge"
    if page in BID_INTELLIGENCE_PAGES:
        return "Reports"
    if page in REPORT_PAGES:
        return "Reports"
    if page in SETTINGS_PAGES:
        return "Administration"
    return "Workspace"


def _breadcrumb(record: ProjectWorkspaceRecord, page: str) -> str:
    if page == "Mission Control":
        return "Atlas / Mission Control"
    return f"Atlas / {record.project.name} / {_group_for_page(page)} / {page}"


def _render_header(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    cols = st.columns([2.2, 0.9, 0.9])
    if cols[0].button("Atlas", use_container_width=True, type="secondary"):
        st.session_state["atlas_active_page"] = "Mission Control"
        st.rerun()

    if cols[2].button("History", use_container_width=True):
        st.session_state["atlas_active_page"] = "History"
        st.rerun()
    if cols[2].button("Settings", use_container_width=True):
        st.session_state["atlas_active_page"] = "Application Settings"
        st.rerun()


def _nav_buttons(st: Any, host: Any, mode: str) -> None:
    active_page = st.session_state.get("atlas_active_page", "Mission Control")

    for group_name, entries in NAV_DROPDOWN_GROUPS:
        with host.expander(
            group_name,
            expanded=active_page in [item[1] for item in entries],
        ):
            for label, page in entries:
                if host.button(
                    label,
                    key=f"atlas_nav_{mode}_{group_name}_{label}_{page}",
                    type="primary" if active_page == page else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["atlas_active_page"] = page
                    st.rerun()


def _set_context_selection(st: Any, kind: str, data: dict[str, Any]) -> None:
    st.session_state["atlas_context_selection"] = {"kind": kind, "data": data}


def _workspace_state_snapshot(st: Any) -> dict[str, Any]:
    selection = dict(st.session_state.get("atlas_context_selection") or {})
    selected_kind = str(selection.get("kind") or "")
    selected_data = dict(selection.get("data") or {})
    selected_drawing = selected_data if selected_kind == "drawing" else None
    selected_specification = selected_data if selected_kind == "specification" else None

    return {
        "last_open_page": str(
            st.session_state.get("atlas_active_page") or "Mission Control"
        ),
        "selected_drawing": selected_drawing,
        "selected_specification": selected_specification,
        "expanded_navigation": [
            _group_for_page(
                str(st.session_state.get("atlas_active_page") or "Mission Control")
            )
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
        "engineering_notebook_entries": list(
            st.session_state.get("atlas_notebook_entries") or []
        ),
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

    restored_page = str(state.get("last_open_page") or "Mission Control")
    if restored_page == "Timeline":
        restored_page = "History"
    st.session_state["atlas_active_page"] = restored_page

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

    notebook_entries = state.get("engineering_notebook_entries")
    if isinstance(notebook_entries, list):
        st.session_state["atlas_notebook_entries"] = list(notebook_entries)

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


def _priority_rank(value: str) -> int:
    normalized = value.strip().lower()
    if normalized == "critical":
        return 0
    if normalized == "high":
        return 1
    if normalized == "medium":
        return 2
    return 3


def _collect_workspace_signals(
    workspace_service: ProjectWorkspaceService,
    limit: int = 12,
) -> list[dict[str, Any]]:
    records = workspace_service.list_recent_workspaces(limit=limit)
    signals: list[dict[str, Any]] = []
    for record in records:
        manifest: dict[str, Any] = {}
        health: dict[str, Any] = {}
        history: list[dict[str, Any]] = []
        try:
            manifest = workspace_service.read_manifest(record.workspace_id)
        except Exception:
            manifest = {}
        try:
            health = workspace_service.project_health(record.workspace_id)
        except Exception:
            health = {}
        try:
            history = workspace_service.list_history(record.workspace_id, limit=8)
        except Exception:
            history = []

        errors = len(list(health.get("errors") or []))
        warnings = len(list(health.get("warnings") or []))
        document_count = sum(
            int(value) for value in dict(manifest.get("document_counts") or {}).values()
        )
        review_artifacts = sum(
            int(value)
            for value in dict(manifest.get("review_artifact_counts") or {}).values()
        )
        last_event = dict(history[0]) if history else {}

        attention_score = 0
        if errors > 0:
            attention_score += 90
        if warnings > 0:
            attention_score += 20
        if review_artifacts == 0:
            attention_score += 50
        if document_count == 0:
            attention_score += 35

        status = "Active"
        reason = "Ready for engineering review."
        destination = "Engineering Workbench"
        if errors > 0:
            status = "Blocked"
            reason = "Repository health errors need attention."
            destination = "Project Settings"
        elif warnings > 0:
            status = "Needs Attention"
            reason = "Repository warnings should be resolved."
            destination = "Project Settings"
        elif review_artifacts == 0:
            status = "Needs Review"
            reason = "No review artifacts available yet."
            destination = "Engineering Workbench"

        signals.append(
            {
                "workspace_id": record.workspace_id,
                "project": record.project.name,
                "project_id": record.project.project_id,
                "status": status,
                "stage": _project_stage(record),
                "updated_at": record.updated_at,
                "errors": errors,
                "warnings": warnings,
                "documents": document_count,
                "review_artifacts": review_artifacts,
                "attention_score": attention_score,
                "reason": reason,
                "destination": destination,
                "last_event": _safe_text(last_event.get("event_type"), "n/a"),
                "last_event_at": _safe_text(last_event.get("timestamp"), "n/a"),
                "history_events": len(history),
                "manifest": manifest,
            }
        )

    signals.sort(
        key=lambda item: (
            int(item.get("attention_score", 0)),
            _safe_text(item.get("updated_at"), ""),
        ),
        reverse=True,
    )
    return signals


def _build_mission_control_payload(
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    signals = _collect_workspace_signals(workspace_service, limit=12)
    signal_by_id = {item["workspace_id"]: item for item in signals}
    active_signal = signal_by_id.get(record.workspace_id)

    actions: list[dict[str, Any]] = []
    workspace_state = workspace_service.load_workspace_state(record.workspace_id)
    last_page = _safe_text(
        workspace_state.get("last_open_page"), "Engineering Workbench"
    )
    actions.append(
        {
            "title": "Continue active review",
            "project": record.project.name,
            "priority": "High",
            "reason": f"Resume work where you left off on {last_page}.",
            "count": "",
            "related_page": last_page,
            "destination": last_page,
        }
    )

    review = context.get("review") if context else None
    import_summary = dict(context.get("import_summary") or {}) if context else {}
    resolver_result = _build_engineering_resolver(record, context)
    objects = _workspace_objects(context)
    revision = context.get("revision_comparison") if context else None
    brief = context.get("brief") if context else None

    conflicts = []
    if resolver_result is not None:
        conflicts = [
            item.to_dict()
            for item in list(getattr(resolver_result, "conflicts", []) or [])
        ]
    manufacturer_model_conflicts = [
        item
        for item in conflicts
        if "manufacturer" in _safe_text(item.get("message"), "").lower()
        or "model" in _safe_text(item.get("message"), "").lower()
    ]
    if manufacturer_model_conflicts:
        actions.append(
            {
                "title": "Resolve manufacturer/model conflicts",
                "project": record.project.name,
                "priority": "Critical",
                "reason": "Resolver found canonical conflicts that may affect takeoff accuracy.",
                "count": str(len(manufacturer_model_conflicts)),
                "related_page": "Resolver Conflict Center",
                "destination": "Resolver Conflict Center",
            }
        )

    coordination_findings = list(objects.get("coordination_findings") or [])
    critical_coordination = [
        item
        for item in coordination_findings
        if _safe_text(item.get("severity"), "").lower() in {"critical", "high"}
    ]
    if critical_coordination:
        actions.append(
            {
                "title": "Review critical coordination findings",
                "project": record.project.name,
                "priority": "Critical",
                "reason": "Cross-discipline conflicts require engineering resolution.",
                "count": str(len(critical_coordination)),
                "related_page": "Coordination Review",
                "destination": "Coordination Review",
            }
        )

    documents_requiring_ocr = int(import_summary.get("documents_requiring_ocr", 0) or 0)
    if documents_requiring_ocr > 0:
        actions.append(
            {
                "title": "Process OCR-required documents",
                "project": record.project.name,
                "priority": "High",
                "reason": "Some documents need OCR before extraction can complete.",
                "count": str(documents_requiring_ocr),
                "related_page": "Project Files",
                "destination": "Project Files",
            }
        )

    if review is not None and brief is None:
        actions.append(
            {
                "title": "Generate estimator brief",
                "project": record.project.name,
                "priority": "Medium",
                "reason": "Estimator brief is missing for bid planning.",
                "count": "",
                "related_page": "Estimator Brief",
                "destination": "Estimator Brief",
            }
        )

    if review is not None and revision is None:
        actions.append(
            {
                "title": "Run revision comparison",
                "project": record.project.name,
                "priority": "Medium",
                "reason": "No revision delta is available in this workspace.",
                "count": "",
                "related_page": "Revision Comparison",
                "destination": "Revision Comparison",
            }
        )

    for signal in signals:
        if signal["workspace_id"] == record.workspace_id:
            continue
        if signal["status"] not in {"Blocked", "Needs Attention"}:
            continue
        actions.append(
            {
                "title": f"Unblock {signal['project']}",
                "project": signal["project"],
                "priority": "Critical" if signal["errors"] > 0 else "High",
                "reason": signal["reason"],
                "count": str(signal["errors"] or signal["warnings"]),
                "related_page": signal["destination"],
                "destination": signal["destination"],
            }
        )

    actions.sort(
        key=lambda item: (_priority_rank(_safe_text(item.get("priority"), "Low"))),
    )

    timeline = _timeline_events(record, context)
    pending_timeline = [
        item
        for item in timeline
        if _safe_text(item.get("status"), "").lower() in {"pending", "not available"}
    ]

    return {
        "signals": signals,
        "active_signal": active_signal,
        "actions": actions,
        "timeline": timeline,
        "pending_timeline": pending_timeline,
    }


def _render_home_page(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
    mission_control_payload: dict[str, Any] | None = None,
) -> None:
    payload = mission_control_payload or _build_mission_control_payload(
        workspace_service,
        record,
        context,
    )
    signals = list(payload.get("signals") or [])
    actions = list(payload.get("actions") or [])
    pending_timeline = list(payload.get("pending_timeline") or [])
    active_signal = dict(payload.get("active_signal") or {})

    attention_projects = [
        item for item in signals if item.get("status") in {"Blocked", "Needs Attention"}
    ]
    active_projects = [item for item in signals if item.get("status") == "Active"]

    summary_cols = st.columns(4)
    _metric_card(summary_cols[0], "Action Items", str(len(actions)))
    _metric_card(summary_cols[1], "Active Projects", str(len(active_projects)))
    _metric_card(summary_cols[2], "Needs Attention", str(len(attention_projects)))
    _metric_card(summary_cols[3], "Upcoming This Week", str(len(pending_timeline)))

    st.markdown("### Continue Working")
    if signals:
        for item in signals[:3]:
            with st.container(border=True):
                st.markdown(f"**{_safe_text(item.get('project'), 'Project')}**")
                st.caption(
                    f"{_safe_text(item.get('stage'), 'n/a')} · "
                    f"{_safe_text(item.get('status'), 'Active')}"
                )
                cols = st.columns([2.3, 1.7, 1.8])
                cols[0].caption(
                    f"Health: {int(item.get('errors', 0))} errors, "
                    f"{int(item.get('warnings', 0))} warnings"
                )
                cols[1].caption(f"Artifacts: {int(item.get('review_artifacts', 0))}")
                if cols[2].button(
                    "Continue Review",
                    key=f"atlas_mc_continue_{item.get('workspace_id')}",
                    use_container_width=True,
                    type="primary",
                ):
                    st.session_state["atlas_active_workspace_id"] = _safe_text(
                        item.get("workspace_id"),
                        "",
                    )
                    st.session_state["atlas_active_page"] = "Engineering Workbench"
                    st.rerun()
    else:
        st.info("No recent projects to continue yet.")

    st.markdown("### Action Center")
    if actions:
        st.dataframe(
            [
                {
                    "Priority": item["priority"],
                    "Action": item["title"],
                    "Project": item["project"],
                    "Reason": item["reason"],
                    "Count": item["count"],
                    "Next Step": item["destination"],
                }
                for item in actions[:14]
            ],
            use_container_width=True,
            hide_index=True,
        )

        action_targets = [
            item["destination"]
            for item in actions
            if item["destination"] in ALL_ACTIVE_PAGES
        ]
        if action_targets:
            selected_destination = st.selectbox(
                "Take action",
                options=action_targets,
                index=0,
                key="atlas_mission_control_action_target",
            )
            if st.button("Go to selected action", type="primary"):
                st.session_state["atlas_active_page"] = selected_destination
                st.rerun()
        if st.button("View all action items", key="atlas_mc_view_all_actions"):
            st.session_state["atlas_active_page"] = "Engineering Workbench"
            st.rerun()
    else:
        st.info("No priority actions detected. Continue from Engineering Workbench.")

    st.markdown("### Active Projects")
    if signals:
        st.dataframe(
            [
                {
                    "Project": item["project"],
                    "Status": item["status"],
                    "Lifecycle": item["stage"],
                    "Reason": item["reason"],
                    "Documents": item["documents"],
                    "Review Artifacts": item["review_artifacts"],
                    "Updated": item["updated_at"],
                }
                for item in signals[:12]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No recent projects available.")

    if active_signal:
        st.caption(
            "Current workspace status: "
            f"{active_signal.get('status', 'Active')} · "
            f"{active_signal.get('reason', 'Ready for engineering review.')}",
        )


def _render_projects_page(st: Any, workspace_service: ProjectWorkspaceService) -> None:
    _render_page_header(
        st, "Projects", "Open, manage, and curate local Atlas projects."
    )
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
            st.session_state["atlas_active_page"] = "Engineering Workbench"
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
                st.session_state["atlas_active_page"] = "Mission Control"
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
                st.session_state["atlas_active_page"] = "Mission Control"
            st.rerun()


def _render_pinned_projects_page(
    st: Any,
    workspace_service: ProjectWorkspaceService,
) -> None:
    _render_page_header(st, "Pinned Projects", "Fast access to prioritized projects.")
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
        st.session_state["atlas_active_page"] = "Engineering Workbench"
        st.rerun()


def _render_reference_projects_page(
    st: Any,
    workspace_service: ProjectWorkspaceService,
) -> None:
    _render_page_header(
        st,
        "Reference Projects",
        "Load deterministic benchmark reference workspaces.",
    )
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
            st.session_state["atlas_active_page"] = "Engineering Workbench"
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
        st.session_state["atlas_active_page"] = "Engineering Workbench"
        st.rerun()


def _render_recent_projects_page(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    _render_page_header(st, "Recent Projects", "Resume recent project investigations.")
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
                st.session_state["atlas_active_page"] = "Engineering Workbench"
                st.rerun()


def _render_create_project_page(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    _render_page_header(
        st,
        "Create New Project",
        "Initialize a local project workspace for deterministic intake and review.",
    )
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
    st.session_state["atlas_active_page"] = "Engineering Workbench"
    st.success(f"Created project {record.project.name}.")
    st.rerun()


def _render_open_existing_page(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    _render_page_header(
        st,
        "Open Existing Project",
        "Open an existing project record, snapshot, or package directory.",
    )
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
        st.session_state["atlas_active_page"] = "Engineering Workbench"
        st.rerun()
        return

    if path.is_dir() and (path / "workspace.json").exists():
        record = workspace_service.load_record(path / "workspace.json")
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Engineering Workbench"
        st.rerun()
        return

    if path.name in {"workspace.json", "project.json", "metadata.json"}:
        record = workspace_service.load_record(path)
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Engineering Workbench"
        st.rerun()
        return

    if path.name == "intake_snapshot.json":
        context = build_intake_review_context(path)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Engineering Workbench"
        st.rerun()
        return

    if path.is_dir():
        context = build_reference_project_context(path)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        st.session_state["atlas_active_workspace_id"] = record.workspace_id
        st.session_state["atlas_active_page"] = "Engineering Workbench"
        st.rerun()
        return

    st.error(
        "Open a project.json/workspace.json file, intake_snapshot.json file, or project folder."
    )


def _workflow_validation_rows(context: dict[str, Any] | None) -> list[dict[str, Any]]:
    objects = _workspace_objects(context)
    review = context.get("review") if context else None
    readiness = getattr(review, "readiness", None) if review is not None else None
    resolver = _build_engineering_resolver(record=None, context=context)
    intelligence = _build_engineering_intelligence(record=None, context=context)

    stages = [
        ("New Project", True),
        ("Document Intake", int(context is not None)),
        (
            "Drawing Intelligence",
            int(len(list(objects.get("drawings") or [])) > 0),
        ),
        (
            "Specification Intelligence",
            int(len(list(objects.get("specifications") or [])) > 0),
        ),
        (
            "Knowledge Graph",
            int(
                len(
                    list(
                        _build_knowledge_graph(record=None, context=context).get(
                            "nodes"
                        )
                        or []
                    )
                )
                > 0
            ),
        ),
        (
            "Resolver",
            int(resolver is not None),
        ),
        (
            "Engineering Intelligence",
            int(intelligence is not None),
        ),
        (
            "Coordination Review",
            int(len(list(objects.get("coordination_findings") or [])) > 0),
        ),
        ("Engineering Workbench", 1),
        (
            "Estimator Brief",
            int(context is not None and context.get("brief") is not None),
        ),
    ]

    rows: list[dict[str, Any]] = []
    for stage, status in stages:
        rows.append(
            {
                "stage": stage,
                "status": _status_chip("Ready" if status else "Needs Review"),
                "decision focus": (
                    "Proceed"
                    if status
                    else "Review source coverage and traceability before proceeding"
                ),
            }
        )

    rows.append(
        {
            "stage": "Readiness State",
            "status": _status_chip(
                _safe_text(
                    getattr(getattr(readiness, "readiness_level", None), "value", None),
                    "Needs Review",
                ).title()
            ),
            "decision focus": "Confirm blockers and reviewer actions before final estimate",
        }
    )
    return rows


def _render_overview_page(
    st: Any, record: ProjectWorkspaceRecord, context: dict[str, Any] | None
) -> None:
    _render_page_header(
        st,
        "Mission Control",
        "Decision-focused project overview for estimator and engineering review.",
    )

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

    st.markdown("Workflow Validation")
    st.dataframe(
        _workflow_validation_rows(context),
        use_container_width=True,
        hide_index=True,
    )


def _render_executive_summary_page(st: Any, context: dict[str, Any] | None) -> None:
    _render_page_header(
        st,
        "Executive Summary",
        "Action-ready summary of package health, risks, and reviewer priorities.",
    )
    if context is None:
        _render_empty_state(st, "No review context available.")
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
        _render_empty_state(st, "No prioritized reviewer actions available.")

    objects = _workspace_objects(context)
    coordination = list(objects.get("coordination_findings") or [])
    high_priority = [
        item
        for item in coordination
        if _safe_text(item.get("severity"), "") in {"critical", "high"}
    ]
    st.markdown("Decision Queue")
    if high_priority:
        st.dataframe(
            [
                {
                    "severity": _safe_text(item.get("severity"), "n/a"),
                    "decision": _safe_text(item.get("title"), "n/a"),
                    "action": _safe_text(item.get("recommended_action"), "n/a"),
                }
                for item in high_priority[:8]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        _render_empty_state(
            st,
            "No high-severity coordination decisions are currently open.",
        )


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


def _section_sort_value(section_number: str) -> int:
    digits = "".join(
        character for character in str(section_number) if character.isdigit()
    )
    if not digits:
        return 10**9
    return int(digits)


def _specification_cross_reference_warnings(
    drawings: list[dict[str, Any]],
    specifications: list[dict[str, Any]],
    equipment: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []

    def _add_warning(
        warning_id: str,
        category: str,
        severity: str,
        message: str,
        related_objects: list[str],
    ) -> None:
        warnings.append(
            {
                "warning_id": warning_id,
                "category": category,
                "severity": severity,
                "message": message,
                "related_objects": [item for item in related_objects if item],
            }
        )

    drawing_numbers = {_safe_text(item.get("drawing_number"), "") for item in drawings}
    spec_sections = {_safe_text(item.get("section"), "") for item in specifications}

    for item in specifications:
        section = _safe_text(item.get("section"), "")
        for drawing_ref in list(item.get("referenced_drawings") or []):
            if drawing_ref in drawing_numbers:
                continue
            _add_warning(
                warning_id=f"spec-drawing-missing:{section}:{drawing_ref}",
                category="spec_to_drawing_missing",
                severity="high",
                message=(
                    f"Specification {section} references drawing {drawing_ref}, "
                    "but no matching drawing object was found."
                ),
                related_objects=[section, drawing_ref],
            )

    for item in drawings:
        drawing_number = _safe_text(item.get("drawing_number"), "")
        for section in list(item.get("referenced_specifications") or []):
            if section in spec_sections:
                continue
            _add_warning(
                warning_id=f"drawing-spec-missing:{drawing_number}:{section}",
                category="drawing_to_spec_missing",
                severity="high",
                message=(
                    f"Drawing {drawing_number} references specification {section}, "
                    "but no matching specification object was found."
                ),
                related_objects=[drawing_number, section],
            )

    for item in equipment:
        equipment_id = _safe_text(item.get("equipment_id"), "")
        drawing_refs = list(item.get("drawing_references") or [])
        spec_refs = list(item.get("specification_references") or [])
        if drawing_refs and not spec_refs:
            _add_warning(
                warning_id=f"equipment-drawing-no-spec:{equipment_id}",
                category="equipment_in_drawing_not_in_spec",
                severity="medium",
                message=(
                    f"Equipment {equipment_id} appears in drawing references but has no "
                    "specification reference."
                ),
                related_objects=[equipment_id] + drawing_refs[:3],
            )
        if spec_refs and not drawing_refs:
            _add_warning(
                warning_id=f"equipment-spec-no-drawing:{equipment_id}",
                category="equipment_in_spec_not_in_drawing",
                severity="medium",
                message=(
                    f"Equipment {equipment_id} appears in specification references but has "
                    "no drawing reference."
                ),
                related_objects=[equipment_id] + spec_refs[:3],
            )

    spec_systems = {
        _safe_text(system, "")
        for item in specifications
        for system in list(item.get("referenced_systems") or [])
    }
    drawing_systems = {
        _safe_text(system, "")
        for item in drawings
        for system in list(item.get("referenced_systems") or [])
    }
    for system in sorted(spec_systems - drawing_systems):
        _add_warning(
            warning_id=f"system-spec-no-drawing:{system}",
            category="system_in_spec_without_drawing_coverage",
            severity="high",
            message=(
                f"System {system} appears in specifications but has no drawing coverage."
            ),
            related_objects=[system],
        )

    execution_requirement_types = {
        "testing_requirements",
        "commissioning_requirements",
        "coordination_requirements",
        "quality_assurance_requirements",
    }
    for drawing in drawings:
        detail_refs = list(drawing.get("detail_references") or [])
        if not detail_refs:
            continue
        drawing_number = _safe_text(drawing.get("drawing_number"), "")
        for section in list(drawing.get("referenced_specifications") or []):
            spec = next(
                (
                    item
                    for item in specifications
                    if _safe_text(item.get("section"), "") == section
                ),
                None,
            )
            if spec is None:
                continue
            requirement_types = {
                _safe_text(item.get("requirement_type"), "")
                for item in list(spec.get("requirement_candidates") or [])
            }
            if requirement_types.isdisjoint(execution_requirement_types):
                continue
            _add_warning(
                warning_id=f"drawing-detail-spec-execution:{drawing_number}:{section}",
                category="drawing_detail_references_spec_execution_requirement",
                severity="medium",
                message=(
                    f"Drawing {drawing_number} detail references align with execution "
                    f"requirements in specification {section}; verify field coordination."
                ),
                related_objects=[drawing_number, section] + detail_refs[:2],
            )

    return warnings


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
            "drawing_index": {},
            "drawing_hierarchy": {"project_id": "", "disciplines": {}},
            "drawing_relationships": [],
            "drawing_intelligence_confidence": "n/a",
            "specification_index": {},
            "specification_relationships": [],
            "specification_intelligence_confidence": "n/a",
            "specification_cross_reference_warnings": [],
            "coordination_findings": [],
            "coordination_issues": [],
            "coordination_summary": {},
            "coordination_confidence": "n/a",
        }

    cached = _context_cached(context, "workspace_objects")
    if isinstance(cached, dict):
        return cached

    review = context.get("review")
    snapshot = context.get("intake_snapshot")
    readiness = getattr(review, "readiness", None) if review is not None else None
    labor = getattr(review, "labor_estimate", None) if review is not None else None

    drawing_rows = _to_rows(list(getattr(review, "drawing_sheets", []) or []))
    spec_rows = _to_rows(list(getattr(review, "specification_sections", []) or []))
    equipment_rows = _to_rows(list(getattr(review, "equipment", []) or []))
    rfi_rows = _to_rows(list(getattr(review, "rfi_candidates", []) or []))
    source_refs = _to_rows(list(getattr(snapshot, "source_references", []) or []))

    drawing_intelligence_result = None
    specification_intelligence_result = None
    if review is not None:
        try:
            drawing_intelligence_result = DrawingIntelligenceEngine().build(review)
        except Exception:
            drawing_intelligence_result = None
        try:
            specification_intelligence_result = SpecificationIntelligenceEngine().build(
                review
            )
        except Exception:
            specification_intelligence_result = None

    metadata_by_sheet: dict[str, Any] = {}
    relationships_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    drawing_index_payload: dict[str, Any] = {}
    drawing_hierarchy_payload: dict[str, Any] = {
        "project_id": _safe_text(getattr(review, "project_id", ""), ""),
        "disciplines": {},
    }
    drawing_relationship_payload: list[dict[str, Any]] = []
    drawing_intelligence_confidence: str | float = "n/a"
    section_by_number: dict[str, Any] = {}
    specification_relationships_by_source: dict[str, list[dict[str, Any]]] = (
        defaultdict(list)
    )
    specification_index_payload: dict[str, Any] = {}
    specification_relationship_payload: list[dict[str, Any]] = []
    specification_intelligence_confidence: str | float = "n/a"

    if drawing_intelligence_result is not None:
        metadata_by_sheet = {
            key.upper(): value
            for key, value in drawing_intelligence_result.drawing_index.by_sheet_number.items()
        }
        drawing_index_payload = drawing_intelligence_result.drawing_index.to_dict()
        drawing_hierarchy_payload = drawing_intelligence_result.hierarchy.to_dict()
        drawing_relationship_payload = [
            item.to_dict() for item in drawing_intelligence_result.relationships
        ]
        drawing_intelligence_confidence = round(
            float(drawing_intelligence_result.confidence), 3
        )
        for relationship in drawing_intelligence_result.relationships:
            relationships_by_source[relationship.source_id.upper()].append(
                relationship.to_dict()
            )

    if specification_intelligence_result is not None:
        section_by_number = {
            section.section_number: section
            for section in specification_intelligence_result.sections
        }
        specification_index_payload = (
            specification_intelligence_result.specification_index.to_dict()
        )
        specification_relationship_payload = [
            item.to_dict() for item in specification_intelligence_result.relationships
        ]
        specification_intelligence_confidence = round(
            float(specification_intelligence_result.confidence),
            3,
        )
        for spec_relationship in specification_intelligence_result.relationships:
            specification_relationships_by_source[spec_relationship.source_id].append(
                spec_relationship.to_dict()
            )

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
        drawing_key = drawing_number.upper()
        title = _safe_text(item.get("title"), "Untitled Drawing")
        source_file = _safe_text(item.get("source_file"), "")
        intelligence_metadata = metadata_by_sheet.get(drawing_key)
        referenced_drawings: list[str] = []
        detail_references: list[str] = []
        view_references: list[str] = []
        sheet_category = "other"
        sheet_sequence: int | str = "n/a"
        drawing_scale = "n/a"
        keynotes: list[str] = []
        general_notes: list[str] = []
        intelligence_confidence: float | str = "n/a"
        if intelligence_metadata is not None:
            referenced_drawings = sorted(
                {
                    ref.target_id
                    for ref in intelligence_metadata.references
                    if ref.reference_type.value == "sheet"
                }
            )
            detail_references = list(intelligence_metadata.detail_references)
            view_references = list(intelligence_metadata.view_references)
            sheet_category = intelligence_metadata.sheet_category.value
            sheet_sequence = (
                intelligence_metadata.sheet_sequence
                if intelligence_metadata.sheet_sequence is not None
                else "n/a"
            )
            drawing_scale = _safe_text(intelligence_metadata.scale, "n/a")
            keynotes = list(intelligence_metadata.keynotes)
            general_notes = list(intelligence_metadata.general_notes)
            intelligence_confidence = round(float(intelligence_metadata.confidence), 3)

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
                "referenced_drawings": referenced_drawings,
                "detail_references": detail_references,
                "view_references": view_references,
                "sheet_category": sheet_category,
                "sheet_sequence": sheet_sequence,
                "drawing_scale": drawing_scale,
                "keynotes": keynotes,
                "general_notes": general_notes,
                "drawing_intelligence_confidence": intelligence_confidence,
                "intelligence_relationships": relationships_by_source.get(
                    drawing_key, []
                ),
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
        intelligence_section = section_by_number.get(section)
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

        referenced_standards: list[str] = []
        referenced_manufacturers: list[str] = []
        referenced_products: list[str] = []
        referenced_schedules: list[str] = []
        addendum_references: list[str] = []
        requirement_candidates: list[dict[str, Any]] = []
        part_rows: list[dict[str, Any]] = []
        article_rows: list[dict[str, Any]] = []
        section_relationships: list[dict[str, Any]] = []
        discipline = _safe_text(item.get("discipline"), "other")
        status = "indexed"
        revision = _safe_text(item.get("revision"), "n/a")
        issue_date = _safe_text(item.get("issue_date"), "n/a")
        section_sequence: int | str = _section_sort_value(section)
        extraction_confidence: str | float = _safe_text(item.get("confidence"), "n/a")
        division = _safe_text(item.get("division"), "n/a")

        if intelligence_section is not None:
            metadata = intelligence_section.metadata
            referenced_standards = list(metadata.referenced_standards)
            referenced_manufacturers = list(metadata.referenced_manufacturers)
            referenced_products = list(metadata.referenced_products)
            referenced_schedules = list(metadata.related_schedules)
            addendum_references = list(metadata.addendum_references)
            requirement_candidates = [
                dict(candidate)
                for candidate in intelligence_section.requirement_candidates
            ]
            part_rows = [item.to_dict() for item in intelligence_section.parts]
            article_rows = [item.to_dict() for item in intelligence_section.articles]
            section_relationships = specification_relationships_by_source.get(
                section,
                [],
            )
            discipline = metadata.discipline.value
            status = intelligence_section.status
            revision = _safe_text(intelligence_section.revision, "n/a")
            issue_date = _safe_text(intelligence_section.issue_date, "n/a")
            extraction_confidence = round(float(intelligence_section.confidence), 3)
            division = metadata.division
            section_sequence = _section_sort_value(section)

            for reference in intelligence_section.references:
                if reference.reference_type == SpecificationReferenceType.DRAWING:
                    cross_refs.append(reference.target_id)
                elif reference.reference_type == SpecificationReferenceType.SYSTEM:
                    ref_systems.append(reference.target_id)
                elif reference.reference_type == SpecificationReferenceType.EQUIPMENT:
                    ref_equipment.append({"equipment_id": reference.target_id})
                elif reference.reference_type == SpecificationReferenceType.SECTION:
                    cross_refs.append(reference.target_id)

        specifications.append(
            {
                "division": division,
                "section": section,
                "title": title,
                "discipline": discipline,
                "status": status,
                "revision": revision,
                "issue_date": issue_date,
                "section_sequence": section_sequence,
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
                "referenced_standards": referenced_standards,
                "referenced_manufacturers": referenced_manufacturers,
                "referenced_products": referenced_products,
                "related_schedules": referenced_schedules,
                "addendum_references": addendum_references,
                "parts": part_rows,
                "articles": article_rows,
                "requirement_candidates": requirement_candidates,
                "intelligence_relationships": section_relationships,
                "extraction_confidence": extraction_confidence,
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
    specification_cross_reference_warnings = _specification_cross_reference_warnings(
        drawings=drawings,
        specifications=specifications,
        equipment=equipment,
    )
    coordination_result = None
    if review is not None:
        try:
            coordination_result = CoordinationIntelligenceEngine().build(
                review=review,
                drawings=drawings,
                specifications=specifications,
                equipment=equipment,
                systems=systems,
                rfis=rfi_rows,
                assumptions=_to_rows(
                    list(getattr(review, "engineering_assumptions", []) or [])
                ),
                evidence=evidence_rows,
            )
        except Exception:
            coordination_result = None

    result = {
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
        "drawing_index": drawing_index_payload,
        "drawing_hierarchy": drawing_hierarchy_payload,
        "drawing_relationships": drawing_relationship_payload,
        "drawing_intelligence_confidence": drawing_intelligence_confidence,
        "specification_index": specification_index_payload,
        "specification_relationships": specification_relationship_payload,
        "specification_intelligence_confidence": specification_intelligence_confidence,
        "specification_cross_reference_warnings": specification_cross_reference_warnings,
        "coordination_findings": (
            [item.to_dict() for item in coordination_result.findings]
            if coordination_result is not None
            else []
        ),
        "coordination_issues": (
            [item.to_dict() for item in coordination_result.issues]
            if coordination_result is not None
            else []
        ),
        "coordination_summary": (
            coordination_result.summary.to_dict()
            if coordination_result is not None
            else {}
        ),
        "coordination_confidence": (
            round(float(coordination_result.confidence), 3)
            if coordination_result is not None
            else "n/a"
        ),
    }
    _set_context_cached(context, "workspace_objects", result)
    return result


def _master_library_rows(context: dict[str, Any] | None) -> list[dict[str, Any]]:
    cached = _context_cached(context, "master_library_rows")
    if isinstance(cached, list):
        return cached

    objects = _workspace_objects(context)
    service = MasterLibraryService()
    service.import_workspace_equipment(list(objects.get("equipment") or []))
    rows = service.explorer_rows()
    _set_context_cached(context, "master_library_rows", rows)
    return rows


def _global_search_entries(context: dict[str, Any] | None) -> list[dict[str, Any]]:
    cached = _context_cached(context, "global_search_entries")
    if isinstance(cached, list):
        return cached

    objects = _workspace_objects(context)
    resolver_result = _build_engineering_resolver(record=None, context=context)
    entries: list[dict[str, Any]] = []

    for item in objects["drawings"]:
        entries.append(
            {
                "kind": "Drawing",
                "name": _safe_text(item.get("drawing_number"), "Drawing"),
                "subtitle": _safe_text(item.get("title"), ""),
                "page": "Drawing Explorer",
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
                "page": "Specification Explorer",
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
    for item in _master_library_rows(context):
        entries.append(
            {
                "kind": "Master Product",
                "name": _safe_text(item.get("model"), "Product"),
                "subtitle": (
                    f"{_safe_text(item.get('manufacturer'), '')}"
                    f" · {_safe_text(item.get('category'), 'other')}"
                ),
                "page": "Master Library Explorer",
                "selection_kind": "master_product",
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
    for item in objects["coordination_findings"]:
        entries.append(
            {
                "kind": "Coordination Finding",
                "name": _safe_text(item.get("title"), "Coordination Finding"),
                "subtitle": _safe_text(item.get("category"), ""),
                "page": "Coordination Review",
                "selection_kind": "project",
                "data": item,
            }
        )
    user_notebook_entries = list(
        _context_cached(context, "notebook_user_entries") or []
    )
    for item in user_notebook_entries:
        entries.append(
            {
                "kind": "Notebook Entry",
                "name": _safe_text(item.get("title"), "Notebook Entry"),
                "subtitle": _safe_text(item.get("entry_type"), ""),
                "page": "Engineering Notebook",
                "selection_kind": "notebook_entry",
                "data": item,
            }
        )
    if resolver_result is not None:
        for item in list(getattr(resolver_result, "resolved_objects", []) or []):
            item_dict = item.to_dict()
            entries.append(
                {
                    "kind": "Resolved Object",
                    "name": _safe_text(item_dict.get("object_id"), "Resolved"),
                    "subtitle": _safe_text(item_dict.get("object_type"), "object"),
                    "page": "Engineering Workbench",
                    "selection_kind": "resolved",
                    "data": item_dict,
                }
            )
        for item in list(getattr(resolver_result, "conflicts", []) or []):
            item_dict = item.to_dict()
            entries.append(
                {
                    "kind": "Resolver Conflict",
                    "name": _safe_text(item_dict.get("conflict_id"), "Conflict"),
                    "subtitle": _safe_text(item_dict.get("message"), ""),
                    "page": "Resolver Conflict Center",
                    "selection_kind": "resolver_conflict",
                    "data": item_dict,
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

    _set_context_cached(context, "global_search_entries", entries)
    return entries


def _timeline_events(
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    import_summary = dict(context.get("import_summary") or {}) if context else {}
    review = context.get("review") if context else None
    brief = context.get("brief") if context else None
    revision = context.get("revision_comparison") if context else None
    resolver_result = _build_engineering_resolver(record, context)
    intelligence = _build_engineering_intelligence(record, context)
    coordination_summary = dict(
        _workspace_objects(context).get("coordination_summary") or {}
    )
    user_notebook_entries = list(
        _context_cached(context, "notebook_user_entries")
        or list(
            (record.workspace_state or {}).get("engineering_notebook_entries") or []
        )
    )
    generated_notebook_entries = _atlas_generated_notebook_entries(record, context)

    events = [
        {
            "event": "Project Imported",
            "timestamp": record.created_at,
            "status": "Completed",
            "details": _safe_text(
                context.get("data_source_label") if context else "Manual", "Manual"
            ),
        },
        {
            "event": "Review Executed",
            "timestamp": record.updated_at,
            "status": "Completed" if review is not None else "Pending",
            "details": _safe_text(getattr(review, "review_id", None), "n/a"),
        },
        {
            "event": "Resolver Updated",
            "timestamp": record.updated_at,
            "status": "Completed" if resolver_result is not None else "Pending",
            "details": _safe_text(
                (
                    getattr(resolver_result, "summary", {}).get("resolved_count")
                    if resolver_result is not None
                    else None
                ),
                "n/a",
            ),
        },
        {
            "event": "Engineering Insight Generated",
            "timestamp": record.updated_at,
            "status": "Completed" if intelligence is not None else "Pending",
            "details": _safe_text(
                (
                    len(list(getattr(intelligence, "insights", []) or []))
                    if intelligence is not None
                    else None
                ),
                "n/a",
            ),
        },
        {
            "event": "Coordination Intelligence Generated",
            "timestamp": record.updated_at,
            "status": (
                "Completed"
                if int(coordination_summary.get("total_findings", 0) or 0) > 0
                else "Pending"
            ),
            "details": _safe_text(coordination_summary.get("total_findings"), "0"),
        },
        {
            "event": "Revision Compared",
            "timestamp": record.updated_at,
            "status": "Completed" if revision is not None else "Not Available",
            "details": _safe_text(
                getattr(revision, "comparison_revision_id", None),
                "No revision comparison",
            ),
        },
        {
            "event": "Readiness Updated",
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
            "event": "Estimator Brief Generated",
            "timestamp": record.updated_at,
            "status": "Completed" if brief is not None else "Pending",
            "details": _safe_text(getattr(brief, "brief_title", None), "n/a"),
        },
        {
            "event": "Document Imports",
            "timestamp": record.updated_at,
            "status": "Completed",
            "details": f"{import_summary.get('total_files', 0)} files",
        },
    ]

    for item in list(getattr(revision, "changes", []) or [])[:8]:
        events.append(
            {
                "event": "Revision Change Detected",
                "timestamp": record.updated_at,
                "status": _safe_text(getattr(item, "severity", None), "medium").title(),
                "details": _safe_text(getattr(item, "title", None), "revision change"),
            }
        )

    for entry in generated_notebook_entries + user_notebook_entries:
        events.append(
            {
                "event": f"Notebook · {_safe_text(entry.get('title'), 'Entry')}",
                "timestamp": _safe_text(entry.get("created_at"), record.updated_at),
                "status": _safe_text(entry.get("status"), "Open"),
                "details": _safe_text(entry.get("entry_type"), "Engineering Note"),
            }
        )

    events.sort(key=lambda item: _safe_text(item.get("timestamp"), ""), reverse=True)
    return events[:80]


def _build_knowledge_graph(
    record: ProjectWorkspaceRecord | None,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    cached = _context_cached(context, "knowledge_graph")
    if isinstance(cached, dict):
        return cached

    objects = _workspace_objects(context)
    import_summary = dict(context.get("import_summary") or {}) if context else {}
    review = context.get("review") if context else None
    revision = context.get("revision_comparison") if context else None
    resolver_result = _build_engineering_resolver(record=record, context=context)

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

    for item in objects.get("drawings", []):
        drawing_id = _safe_text(item.get("drawing_number"), "unknown")
        drawing_node = f"drawing:{drawing_id}"
        relationship_confidence = _safe_text(
            item.get("drawing_intelligence_confidence"),
            _safe_text(item.get("extraction_quality"), "n/a"),
        )

        for target_sheet in list(item.get("referenced_drawings") or []):
            target_node = f"drawing:{target_sheet}"
            _add_edge(
                drawing_node,
                target_node,
                "Drawing to Drawing",
                relationship_confidence,
                drawing_id,
            )

        for detail_ref in list(item.get("detail_references") or []):
            detail_node = f"drawing_detail:{drawing_id}:{detail_ref}"
            _add_node(
                detail_node,
                "Drawing Detail",
                f"{drawing_id} · Detail {detail_ref}",
                "Drawing Explorer",
                "drawing",
                data={
                    "drawing_number": drawing_id,
                    "detail_reference": detail_ref,
                },
                metadata={
                    "source_file": _safe_text(item.get("source_file"), "n/a"),
                    "source_page": "n/a",
                    "sheet_number": drawing_id,
                    "specification_section": "n/a",
                    "extraction_confidence": relationship_confidence,
                    "creation_timestamp": created_at,
                    "last_update": updated_at,
                },
            )
            _add_edge(
                drawing_node,
                detail_node,
                "Drawing to Detail",
                relationship_confidence,
                detail_ref,
            )

        for spec_ref in list(item.get("referenced_specifications") or []):
            spec_node = f"spec:{spec_ref}"
            _add_edge(
                drawing_node,
                spec_node,
                "Drawing to Specification",
                relationship_confidence,
                _safe_text(item.get("source_file"), "n/a"),
            )

        for system_ref in list(item.get("referenced_systems") or []):
            system_node = f"system:{system_ref}"
            _add_edge(
                drawing_node,
                system_node,
                "Drawing to System",
                relationship_confidence,
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

        for part in list(item.get("parts") or []):
            part_number = _safe_text(part.get("part_number"), "part")
            part_node = f"spec_part:{_safe_text(item.get('section'), '')}:{part_number}"
            _add_node(
                part_node,
                "Specification Part",
                f"{_safe_text(item.get('section'), 'Spec')} {part_number}",
                "Specification Explorer",
                "specification",
                data={
                    "section": _safe_text(item.get("section"), "n/a"),
                    "part_number": part_number,
                    "title": _safe_text(part.get("title"), "n/a"),
                },
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
                spec_node,
                part_node,
                "Specification to Part",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                _safe_text(part.get("title"), "n/a"),
            )

        for requirement in list(item.get("requirement_candidates") or []):
            req_type = _safe_text(requirement.get("requirement_type"), "requirement")
            req_node = (
                f"spec_requirement:{_safe_text(item.get('section'), '')}:{req_type}"
            )
            _add_node(
                req_node,
                "Requirement Candidate",
                req_type,
                "Specification Explorer",
                "specification",
                data={
                    "section": _safe_text(item.get("section"), "n/a"),
                    "requirement_type": req_type,
                    "text": _safe_text(requirement.get("text"), "n/a"),
                },
                metadata={
                    "source_file": _safe_text(item.get("source_file"), "n/a"),
                    "source_page": "n/a",
                    "sheet_number": "n/a",
                    "specification_section": _safe_text(item.get("section"), "n/a"),
                    "extraction_confidence": _safe_text(
                        requirement.get("confidence"),
                        _safe_text(item.get("extraction_confidence"), "n/a"),
                    ),
                    "creation_timestamp": created_at,
                    "last_update": updated_at,
                },
            )
            _add_edge(
                spec_node,
                req_node,
                "Specification to Requirement Candidate",
                _safe_text(
                    requirement.get("confidence"),
                    _safe_text(item.get("extraction_confidence"), "n/a"),
                ),
                _safe_text(requirement.get("text"), "n/a"),
            )

        for manufacturer in list(item.get("referenced_manufacturers") or []):
            manufacturer_node = f"manufacturer:{manufacturer}"
            _add_edge(
                spec_node,
                manufacturer_node,
                "Specification to Manufacturer",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                _safe_text(item.get("section"), "n/a"),
            )

        for product in list(item.get("referenced_products") or []):
            product_node = f"product:spec:{product}"
            _add_node(
                product_node,
                "Product",
                product,
                "Specification Explorer",
                "specification",
                data={
                    "product": product,
                    "section": _safe_text(item.get("section"), ""),
                },
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
                spec_node,
                product_node,
                "Specification to Product",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                _safe_text(item.get("section"), "n/a"),
            )

        for addendum in list(item.get("addendum_references") or []):
            addendum_node = f"addendum:{addendum}"
            _add_node(
                addendum_node,
                "Addendum",
                addendum,
                "Project Files",
                "file",
                data={"addendum": addendum},
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
                spec_node,
                addendum_node,
                "Specification to Addendum",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                addendum,
            )

        for part in list(item.get("parts") or []):
            part_number = _safe_text(part.get("part_number"), "Part")
            part_id = (
                f"spec_part:{_safe_text(item.get('section'), 'unknown')}:{part_number}"
            )
            _add_node(
                part_id,
                "Specification Part",
                f"{_safe_text(item.get('section'), 'Section')} {part_number}",
                "Specification Explorer",
                "specification",
                data={
                    "section": _safe_text(item.get("section"), ""),
                    "part_number": part_number,
                    "title": _safe_text(part.get("title"), ""),
                },
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
                spec_node,
                part_id,
                "Specification to Specification Part",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                _safe_text(part.get("title"), "n/a"),
            )

        for article in list(item.get("articles") or []):
            article_id = f"spec_article:{_safe_text(item.get('section'), 'unknown')}:{_safe_text(article.get('identifier'), 'article')}"
            _add_node(
                article_id,
                "Specification Article",
                _safe_text(article.get("heading"), "Article"),
                "Specification Explorer",
                "specification",
                data={
                    "section": _safe_text(item.get("section"), ""),
                    "identifier": _safe_text(article.get("identifier"), ""),
                    "heading": _safe_text(article.get("heading"), ""),
                },
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
                spec_node,
                article_id,
                "Specification to Article",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                _safe_text(article.get("heading"), "n/a"),
            )

        for requirement in list(item.get("requirement_candidates") or []):
            req_type = _safe_text(requirement.get("requirement_type"), "requirement")
            req_id = f"spec_requirement:{_safe_text(item.get('section'), 'unknown')}:{req_type}"
            _add_node(
                req_id,
                "Requirement Candidate",
                req_type,
                "Specification Explorer",
                "specification",
                data={
                    "section": _safe_text(item.get("section"), ""),
                    "requirement_type": req_type,
                    "text": _safe_text(requirement.get("text"), ""),
                },
                metadata={
                    "source_file": _safe_text(item.get("source_file"), "n/a"),
                    "source_page": "n/a",
                    "sheet_number": "n/a",
                    "specification_section": _safe_text(item.get("section"), "n/a"),
                    "extraction_confidence": _safe_text(
                        requirement.get("confidence"), "n/a"
                    ),
                    "creation_timestamp": created_at,
                    "last_update": updated_at,
                },
            )
            _add_edge(
                spec_node,
                req_id,
                "Specification to Requirement Candidate",
                _safe_text(requirement.get("confidence"), "n/a"),
                _safe_text(requirement.get("text"), "n/a"),
            )

        for standard in list(item.get("referenced_standards") or []):
            standard_id = f"standard:{standard}"
            _add_node(
                standard_id,
                "Standard",
                standard,
                "Specification Explorer",
                "specification",
                data={"standard": standard},
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
                spec_node,
                standard_id,
                "Specification to Standard",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                standard,
            )

        for addendum in list(item.get("addendum_references") or []):
            addendum_id = f"addendum:{addendum}"
            _add_node(
                addendum_id,
                "Addendum",
                addendum,
                "Specification Explorer",
                "specification",
                data={"addendum": addendum},
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
                spec_node,
                addendum_id,
                "Specification to Addendum",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                addendum,
            )

        for manufacturer in list(item.get("referenced_manufacturers") or []):
            _add_edge(
                spec_node,
                f"manufacturer:{manufacturer}",
                "Specification to Manufacturer",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                manufacturer,
            )

        for product in list(item.get("referenced_products") or []):
            _add_edge(
                spec_node,
                f"product:unknown:{product}",
                "Specification to Product",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                product,
            )

        for system in list(item.get("referenced_systems") or []):
            _add_edge(
                spec_node,
                f"system:{system}",
                "Specification to System",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                system,
            )

        for rfi in list(item.get("referenced_rfis") or []):
            _add_edge(
                spec_node,
                f"rfi:{rfi}",
                "Specification to RFI Candidate",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                rfi,
            )

        for evidence in list(item.get("referenced_evidence") or []):
            _add_edge(
                spec_node,
                f"evidence:{evidence}",
                "Specification to Evidence",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                evidence,
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
        for system_ref in item.get("referenced_systems", []):
            _add_edge(
                spec_node,
                f"system:{system_ref}",
                "Specification to System",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                _safe_text(item.get("section"), "n/a"),
            )
        for equipment_ref in item.get("referenced_equipment", []):
            _add_edge(
                spec_node,
                f"equipment:{equipment_ref}",
                "Specification to Equipment",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                _safe_text(item.get("section"), "n/a"),
            )
        for rfi_ref in item.get("referenced_rfis", []):
            _add_edge(
                spec_node,
                f"rfi:{rfi_ref}",
                "Specification to RFI Candidate",
                _safe_text(item.get("extraction_confidence"), "n/a"),
                _safe_text(item.get("section"), "n/a"),
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

        for specification in objects.get("specifications", []):
            section = _safe_text(specification.get("section"), "")
            title = _safe_text(specification.get("title"), "")
            if not section:
                continue
            if _contains_any(str(item), [section, title]):
                _add_edge(
                    f"spec:{section}",
                    node_id,
                    "Specification to Engineering Assumption",
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

    if resolver_result is not None:
        summary_node = "resolver:summary"
        _add_node(
            summary_node,
            "Resolver Summary",
            "Engineering Resolver",
            "Engineering Resolver",
            "resolved",
            data={
                **dict(resolver_result.summary),
                "confidence": resolver_result.confidence,
            },
            metadata={
                "source_file": _safe_text(
                    context.get("package_location") if context else None, "n/a"
                ),
                "source_page": "n/a",
                "sheet_number": "n/a",
                "specification_section": "n/a",
                "extraction_confidence": _safe_text(resolver_result.confidence, "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            summary_node,
            "Project to Resolver Summary",
            _safe_text(resolver_result.confidence, "n/a"),
            _safe_text(context.get("package_location") if context else None, "n/a"),
        )

        for resolved in resolver_result.resolved_objects:
            resolved_node = f"resolved:{resolved.object_type}:{resolved.object_id}"
            label = _safe_text(
                resolved.canonical_values.get("name")
                or resolved.canonical_values.get("title")
                or resolved.object_id,
                resolved.object_id,
            )
            _add_node(
                resolved_node,
                "Resolved Object",
                label,
                "Engineering Resolver",
                "resolved",
                data=resolved.to_dict(),
                metadata={
                    "source_file": _safe_text(
                        context.get("package_location") if context else None, "n/a"
                    ),
                    "source_page": "n/a",
                    "sheet_number": "n/a",
                    "specification_section": "n/a",
                    "extraction_confidence": _safe_text(resolved.confidence, "n/a"),
                    "creation_timestamp": created_at,
                    "last_update": updated_at,
                    "manual_review_required": resolved.manual_review_required,
                },
            )
            _add_edge(
                summary_node,
                resolved_node,
                "Resolver summary to resolved object",
                _safe_text(resolved.confidence, "n/a"),
                ", ".join(resolved.evidence_ids) or "n/a",
            )

            original_prefix = {
                "equipment": "equipment",
                "system": "system",
                "room": "room",
                "drawing": "drawing",
                "specification": "spec",
                "manufacturer": "manufacturer",
            }.get(resolved.object_type)
            if original_prefix is not None:
                original_node = f"{original_prefix}:{resolved.object_id}"
                if _node_by_id({"nodes": nodes}, original_node) is not None:
                    _add_edge(
                        original_node,
                        resolved_node,
                        "Resolved to canonical object",
                        _safe_text(resolved.confidence, "n/a"),
                        ", ".join(resolved.evidence_ids) or "n/a",
                    )

        for conflict in resolver_result.conflicts:
            conflict_node = f"resolver_conflict:{conflict.conflict_id}"
            _add_node(
                conflict_node,
                "Resolver Conflict",
                _safe_text(conflict.field_name, "conflict"),
                "Resolver Conflict Center",
                "resolver_conflict",
                data=conflict.to_dict(),
                metadata={
                    "source_file": _safe_text(
                        context.get("package_location") if context else None, "n/a"
                    ),
                    "source_page": "n/a",
                    "sheet_number": "n/a",
                    "specification_section": "n/a",
                    "extraction_confidence": _safe_text(
                        resolver_result.confidence, "n/a"
                    ),
                    "creation_timestamp": created_at,
                    "last_update": updated_at,
                },
            )
            _add_edge(
                summary_node,
                conflict_node,
                "Resolver summary to conflict",
                _safe_text(resolver_result.confidence, "n/a"),
                ", ".join(conflict.evidence_ids) or "n/a",
            )
            _add_edge(
                conflict_node,
                _safe_text(conflict.target_id, "n/a"),
                "Conflict targets object",
                _safe_text(conflict.severity, "n/a"),
                ", ".join(conflict.evidence_ids) or "n/a",
            )

    intelligence_result = None
    if review is not None:
        try:
            intelligence_result = EngineeringInsightsService().build(
                review=review,
                knowledge_graph={"nodes": list(nodes), "edges": list(edges)},
                estimator_brief=context.get("brief") if context else None,
            )
        except Exception:
            intelligence_result = None

    if intelligence_result is not None:
        for insight in list(intelligence_result.insights or []):
            insight_node = f"engineering_insight:{insight.insight_id}"
            _add_node(
                insight_node,
                "Engineering Insight",
                _safe_text(insight.title, "Engineering Insight"),
                "Engineering Intelligence",
                "project",
                data=insight.to_dict(),
                metadata={
                    "source_file": _safe_text(
                        context.get("package_location") if context else None, "n/a"
                    ),
                    "source_page": "n/a",
                    "sheet_number": "n/a",
                    "specification_section": "n/a",
                    "extraction_confidence": _safe_text(insight.confidence, "n/a"),
                    "creation_timestamp": created_at,
                    "last_update": updated_at,
                },
            )
            _add_edge(
                project_id,
                insight_node,
                "Project to Engineering Insight",
                _safe_text(insight.confidence, "n/a"),
                _safe_text(insight.title, "n/a"),
            )

            support_blob = " ".join(
                [
                    str(item)
                    for item in list(insight.supporting_objects or [])
                    + list(insight.evidence_refs or [])
                ]
            )
            for drawing in objects.get("drawings", []):
                drawing_number = _safe_text(drawing.get("drawing_number"), "")
                if not drawing_number:
                    continue
                if _contains_any(
                    support_blob,
                    [
                        drawing_number,
                        _safe_text(drawing.get("source_file"), ""),
                        _safe_text(drawing.get("title"), ""),
                    ],
                ):
                    _add_edge(
                        f"drawing:{drawing_number}",
                        insight_node,
                        "Drawing to Engineering Insight",
                        _safe_text(insight.confidence, "n/a"),
                        _safe_text(insight.title, "n/a"),
                    )

            for specification in objects.get("specifications", []):
                section = _safe_text(specification.get("section"), "")
                if not section:
                    continue
                if _contains_any(
                    support_blob,
                    [
                        section,
                        _safe_text(specification.get("title"), ""),
                        _safe_text(specification.get("division"), ""),
                    ],
                ):
                    _add_edge(
                        f"spec:{section}",
                        insight_node,
                        "Specification to Engineering Insight",
                        _safe_text(insight.confidence, "n/a"),
                        _safe_text(insight.title, "n/a"),
                    )

    for warning in list(objects.get("specification_cross_reference_warnings") or []):
        warning_id = _safe_text(warning.get("warning_id"), "warning")
        warning_node = f"crossref_warning:{warning_id}"
        _add_node(
            warning_node,
            "Cross-Reference Warning",
            _safe_text(warning.get("category"), "cross-reference warning"),
            "Specification Explorer",
            "specification",
            data=warning,
            metadata={
                "source_file": _safe_text(
                    context.get("package_location") if context else None,
                    "n/a",
                ),
                "source_page": "n/a",
                "sheet_number": "n/a",
                "specification_section": "n/a",
                "extraction_confidence": _safe_text(warning.get("severity"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            warning_node,
            "Project to Cross-Reference Warning",
            _safe_text(warning.get("severity"), "n/a"),
            _safe_text(warning.get("message"), "n/a"),
        )
        for related in list(warning.get("related_objects") or []):
            related_text = _safe_text(related, "")
            if not related_text:
                continue
            _add_edge(
                warning_node,
                related_text,
                "Warning references object",
                _safe_text(warning.get("severity"), "n/a"),
                _safe_text(warning.get("message"), "n/a"),
            )

    for finding in list(objects.get("coordination_findings") or []):
        finding_id = _safe_text(finding.get("finding_id"), "finding")
        finding_node = f"coordination_finding:{finding_id}"
        _add_node(
            finding_node,
            "Coordination Finding",
            _safe_text(finding.get("title"), "Coordination Finding"),
            "Coordination Review",
            "project",
            data=finding,
            metadata={
                "source_file": _safe_text(
                    context.get("package_location") if context else None,
                    "n/a",
                ),
                "source_page": "n/a",
                "sheet_number": "n/a",
                "specification_section": "n/a",
                "extraction_confidence": _safe_text(finding.get("confidence"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            finding_node,
            "Project to Coordination Finding",
            _safe_text(finding.get("confidence"), "n/a"),
            _safe_text(finding.get("description"), "n/a"),
        )

        for ref in list(finding.get("related_objects") or []):
            related_id = _safe_text(ref, "")
            if not related_id:
                continue
            if ":" not in related_id:
                continue
            prefix, value = related_id.split(":", 1)
            normalized_target = ""
            if prefix == "drawing":
                normalized_target = f"drawing:{value}"
            elif prefix == "spec":
                normalized_target = f"spec:{value}"
            elif prefix == "equipment":
                normalized_target = f"equipment:{value}"
            elif prefix == "system":
                normalized_target = f"system:{value}"
            elif prefix == "rfi":
                normalized_target = f"rfi:{value}"
            elif prefix == "assumption":
                normalized_target = f"assumption:{value}"
            elif prefix == "evidence":
                normalized_target = related_id

            if not normalized_target:
                continue
            if _node_by_id({"nodes": nodes}, normalized_target) is None:
                continue
            _add_edge(
                finding_node,
                normalized_target,
                "Coordination finding references object",
                _safe_text(finding.get("confidence"), "n/a"),
                _safe_text(finding.get("title"), "n/a"),
            )

        for evidence_row in list(finding.get("evidence") or []):
            evidence_id = _safe_text(evidence_row.get("object_id"), "")
            if (
                evidence_id.startswith("evidence:")
                and _node_by_id({"nodes": nodes}, evidence_id) is not None
            ):
                _add_edge(
                    finding_node,
                    evidence_id,
                    "Coordination finding to evidence",
                    _safe_text(evidence_row.get("confidence"), "n/a"),
                    _safe_text(evidence_row.get("source_ref"), "n/a"),
                )

    for issue in list(objects.get("coordination_issues") or []):
        issue_id = _safe_text(issue.get("issue_id"), "issue")
        issue_node = f"coordination_issue:{issue_id}"
        _add_node(
            issue_node,
            "Coordination Issue",
            _safe_text(issue.get("category"), "Coordination Issue"),
            "Coordination Review",
            "project",
            data=issue,
            metadata={
                "source_file": _safe_text(
                    context.get("package_location") if context else None,
                    "n/a",
                ),
                "source_page": "n/a",
                "sheet_number": "n/a",
                "specification_section": "n/a",
                "extraction_confidence": _safe_text(issue.get("severity"), "n/a"),
                "creation_timestamp": created_at,
                "last_update": updated_at,
            },
        )
        _add_edge(
            project_id,
            issue_node,
            "Project to Coordination Issue",
            _safe_text(issue.get("severity"), "n/a"),
            issue_id,
        )
        for finding_id in list(issue.get("finding_ids") or []):
            _add_edge(
                issue_node,
                f"coordination_finding:{finding_id}",
                "Coordination issue to finding",
                _safe_text(issue.get("severity"), "n/a"),
                issue_id,
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
        node_index = id_to_index.get(node_id)
        if node_index is None:
            continue
        node = nodes[node_index]
        node.setdefault("metadata", {})["relationship_count"] = count
        node.setdefault("metadata", {})["evidence_count"] = evidence_counts[node_id]

    graph = {
        "nodes": nodes,
        "edges": edges,
        "resolver_result": (
            resolver_result.to_dict() if resolver_result is not None else None
        ),
        "resolver_summary": (
            resolver_result.summary if resolver_result is not None else {}
        ),
    }
    _set_context_cached(context, "knowledge_graph", graph)
    return graph


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
    elif kind == "resolved":
        candidates.append(
            f"resolved:{_safe_text(data.get('object_type'), '')}:{_safe_text(data.get('object_id'), '')}"
        )
    elif kind == "rfi":
        rfi_id = _safe_text(data.get("rfi_id"), _safe_text(data.get("title"), "rfi"))
        candidates.append(f"rfi:{rfi_id}")
    elif kind == "resolver_conflict":
        candidates.append(
            f"resolver_conflict:{_safe_text(data.get('conflict_id'), '')}"
        )
    elif kind == "evidence":
        candidates.append(
            f"evidence:{_safe_text(data.get('source_file'), 'file')}:{data.get('page', 'n/a')}"
        )
    elif kind == "project":
        project_id = _safe_text(data.get("project_id"), "")
        if project_id:
            candidates.append(f"project:{project_id}")
    elif kind == "notebook_entry":
        return {
            "label": _safe_text(data.get("title"), "Notebook Entry"),
            "type": _safe_text(data.get("entry_type"), "Notebook Entry"),
            "source_file": "Engineering Notebook",
            "source_page": _safe_text(data.get("created_at"), "n/a"),
            "sheet_number": "n/a",
            "specification_section": "n/a",
            "extraction_confidence": "n/a",
            "creation_timestamp": _safe_text(data.get("created_at"), "n/a"),
            "last_update": _safe_text(data.get("updated_at"), "n/a"),
            "relationship_count": len(list(data.get("related_objects") or [])),
            "evidence_count": len(list(data.get("evidence_refs") or [])),
        }
    elif kind == "master_product":
        return {
            "label": _safe_text(data.get("model"), "Master Product"),
            "type": "Master Product",
            "source_file": "Master Library Explorer",
            "source_page": _safe_text(data.get("product_id"), "n/a"),
            "sheet_number": "n/a",
            "specification_section": "n/a",
            "extraction_confidence": _safe_text(data.get("confidence"), "n/a"),
            "creation_timestamp": _safe_text(data.get("created_at"), "n/a"),
            "last_update": _safe_text(data.get("updated_at"), "n/a"),
            "relationship_count": len(list(data.get("related_products") or [])),
            "evidence_count": len(list(data.get("aliases") or [])),
        }

    for node_id in candidates:
        node = _node_by_id(graph, node_id)
        if node is not None:
            metadata = dict(node.get("metadata") or {})
            metadata["label"] = _safe_text(node.get("label"), "n/a")
            metadata["type"] = _safe_text(node.get("type"), "n/a")
            return metadata
    return None


def _build_engineering_intelligence(
    record: ProjectWorkspaceRecord | None,
    context: dict[str, Any] | None,
) -> EngineeringIntelligenceResult | None:
    if context is None:
        return None

    review = context.get("review")
    if review is None:
        return None

    cached = _context_cached(context, "engineering_intelligence")
    if cached is not None:
        return cached

    brief = context.get("brief")
    graph = _build_knowledge_graph(record=record, context=context)
    result = EngineeringInsightsService().build(
        review=review,
        knowledge_graph=graph,
        estimator_brief=brief,
    )
    _set_context_cached(context, "engineering_intelligence", result)
    return result


def _build_engineering_resolver(
    record: ProjectWorkspaceRecord | None,
    context: dict[str, Any] | None,
) -> Any | None:
    if context is None:
        return None

    review = context.get("review")
    if review is None:
        return None

    cached = _context_cached(context, "engineering_resolver")
    if cached is not None:
        return cached

    result = EngineeringResolver().resolve(
        ResolverContext(review=review, knowledge_graph=context.get("knowledge_graph"))
    )
    _set_context_cached(context, "engineering_resolver", result)
    return result


def _selection_node_id(kind: str, data: dict[str, Any]) -> str | None:
    if kind == "drawing":
        return f"drawing:{_safe_text(data.get('drawing_number'), '')}"
    if kind == "specification":
        return f"spec:{_safe_text(data.get('section'), '')}"
    if kind == "equipment":
        return f"equipment:{_safe_text(data.get('equipment_id'), '')}"
    if kind == "system":
        return f"system:{_safe_text(data.get('system'), '')}"
    if kind == "room":
        return f"room:{_safe_text(data.get('room'), '')}"
    if kind == "manufacturer":
        return f"manufacturer:{_safe_text(data.get('manufacturer'), '')}"
    if kind == "evidence":
        return (
            f"evidence:{_safe_text(data.get('source_file'), 'file')}"
            f":{data.get('page', 'n/a')}"
        )
    if kind == "resolved":
        return (
            f"resolved:{_safe_text(data.get('object_type'), '')}"
            f":{_safe_text(data.get('object_id'), '')}"
        )
    if kind == "rfi":
        rfi_id = _safe_text(data.get("rfi_id"), _safe_text(data.get("title"), "rfi"))
        return f"rfi:{rfi_id}"
    if kind == "resolver_conflict":
        return f"resolver_conflict:{_safe_text(data.get('conflict_id'), '')}"
    if kind == "project":
        return f"project:{_safe_text(data.get('project_id'), '')}"
    if kind == "notebook_entry":
        return f"notebook:{_safe_text(data.get('entry_id'), '')}"
    if kind == "master_product":
        return f"master_product:{_safe_text(data.get('product_id'), '')}"
    return None


def _notebook_object_reference_options(
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> list[str]:
    objects = _workspace_objects(context)
    options: list[str] = [f"project:{record.project.project_id}"]
    options.extend(
        [
            f"drawing:{_safe_text(item.get('drawing_number'), '')}"
            for item in list(objects.get("drawings") or [])
            if _safe_text(item.get("drawing_number"), "")
        ]
    )
    options.extend(
        [
            f"spec:{_safe_text(item.get('section'), '')}"
            for item in list(objects.get("specifications") or [])
            if _safe_text(item.get("section"), "")
        ]
    )
    options.extend(
        [
            f"equipment:{_safe_text(item.get('equipment_id'), '')}"
            for item in list(objects.get("equipment") or [])
            if _safe_text(item.get("equipment_id"), "")
        ]
    )
    options.extend(
        [
            f"system:{_safe_text(item.get('system'), '')}"
            for item in list(objects.get("systems") or [])
            if _safe_text(item.get("system"), "")
        ]
    )
    options.extend(
        [
            f"room:{_safe_text(item.get('room'), '')}"
            for item in list(objects.get("rooms") or [])
            if _safe_text(item.get("room"), "")
        ]
    )
    options.extend(
        [
            f"rfi:{_safe_text(item.get('rfi_id'), _safe_text(item.get('title'), 'rfi'))}"
            for item in list(objects.get("rfis") or [])
        ]
    )
    options.extend(
        [
            f"resolver_conflict:{_safe_text(item.get('conflict_id'), '')}"
            for item in _build_resolver_conflict_rows(
                _build_engineering_resolver(record=None, context=context)
            )
            if _safe_text(item.get("conflict_id"), "")
        ]
    )
    options.extend(
        [
            f"coordination_finding:{_safe_text(item.get('finding_id'), '')}"
            for item in list(objects.get("coordination_findings") or [])
            if _safe_text(item.get("finding_id"), "")
        ]
    )
    intelligence = _build_engineering_intelligence(record=None, context=context)
    if intelligence is not None:
        options.extend(
            [
                f"engineering_insight:{_safe_text(item.insight_id, '')}"
                for item in list(getattr(intelligence, "insights", []) or [])
                if _safe_text(getattr(item, "insight_id", None), "")
            ]
        )
    options.append("labor_estimate:current")
    options.extend(
        [
            f"evidence:{_safe_text(item.get('source_file'), 'file')}:{item.get('page', 'n/a')}"
            for item in list(objects.get("evidence") or [])
        ]
    )
    return sorted({item for item in options if item and not item.endswith(":")})


def _open_linked_object(st: Any, ref: str) -> None:
    value = _safe_text(ref, "")
    if not value or ":" not in value:
        return
    prefix, object_id = value.split(":", 1)

    if prefix == "project":
        st.session_state["atlas_active_page"] = "Overview"
        _set_context_selection(st, "project", {"project_id": object_id})
    elif prefix == "drawing":
        st.session_state["atlas_active_page"] = "Drawing Explorer"
        _set_context_selection(st, "drawing", {"drawing_number": object_id})
    elif prefix == "spec":
        st.session_state["atlas_active_page"] = "Specification Explorer"
        _set_context_selection(st, "specification", {"section": object_id})
    elif prefix == "equipment":
        st.session_state["atlas_active_page"] = "Equipment"
        _set_context_selection(st, "equipment", {"equipment_id": object_id})
    elif prefix == "system":
        st.session_state["atlas_active_page"] = "Systems"
        _set_context_selection(st, "system", {"system": object_id})
    elif prefix == "room":
        st.session_state["atlas_active_page"] = "Equipment"
        _set_context_selection(st, "room", {"room": object_id})
    elif prefix == "rfi":
        st.session_state["atlas_active_page"] = "RFI Candidates"
        _set_context_selection(st, "rfi", {"rfi_id": object_id})
    elif prefix == "resolver_conflict":
        st.session_state["atlas_active_page"] = "Resolver Conflict Center"
        _set_context_selection(st, "resolver_conflict", {"conflict_id": object_id})
    elif prefix == "engineering_insight":
        st.session_state["atlas_active_page"] = "Engineering Intelligence"
        _set_context_selection(st, "project", {"insight_id": object_id})
    elif prefix == "coordination_finding":
        st.session_state["atlas_active_page"] = "Coordination Review"
        _set_context_selection(st, "project", {"finding_id": object_id})
    elif prefix == "labor_estimate":
        st.session_state["atlas_active_page"] = "Labor Estimate"
        _set_context_selection(st, "project", {"project_id": object_id})
    elif prefix == "evidence":
        parts = value.split(":")
        source_file = parts[1] if len(parts) > 1 else "file"
        page = parts[2] if len(parts) > 2 else "n/a"
        st.session_state["atlas_active_page"] = "Evidence"
        _set_context_selection(
            st,
            "evidence",
            {"source_file": source_file, "page": page},
        )
    st.rerun()


def _scope_tokens(
    selection: dict[str, Any], selected_node: dict[str, Any] | None
) -> set[str]:
    tokens: set[str] = set()
    data = dict(selection.get("data") or {})
    raw_values = [
        selection.get("kind"),
        selected_node.get("id") if isinstance(selected_node, dict) else None,
        selected_node.get("label") if isinstance(selected_node, dict) else None,
        data.get("equipment_id"),
        data.get("system"),
        data.get("room"),
        data.get("manufacturer"),
        data.get("model"),
        data.get("section"),
        data.get("drawing_number"),
        data.get("object_id"),
        data.get("object_type"),
        data.get("target_id"),
        data.get("source_file"),
        data.get("title"),
        data.get("rfi_id"),
        data.get("conflict_id"),
    ]
    for value in raw_values:
        text = _safe_text(value, "").strip().lower()
        if text:
            tokens.add(text)
            if ":" in text:
                pieces = [part.strip() for part in text.split(":") if part.strip()]
                tokens.update(pieces)
    return tokens


def _filter_rows_by_scope(
    rows: list[dict[str, Any]],
    scope_tokens: set[str],
    enabled: bool,
) -> list[dict[str, Any]]:
    if not enabled or not scope_tokens:
        return rows
    filtered: list[dict[str, Any]] = []
    for row in rows:
        text = str(row).lower()
        if any(token in text for token in scope_tokens):
            filtered.append(row)
    return filtered


def _resolver_conflict_status(
    conflict: Any,
    resolved_by_target: dict[str, Any],
) -> tuple[str, float]:
    target_id = _safe_text(getattr(conflict, "target_id", None), "")
    target = resolved_by_target.get(target_id)
    target_confidence = float(getattr(target, "confidence", 0.0) or 0.0)
    if target is None:
        return "Needs Review", 0.0
    if (
        not getattr(target, "manual_review_required", True)
        and target_confidence >= 0.85
    ):
        return "High Confidence", target_confidence
    if getattr(target, "manual_review_required", False):
        if target_confidence < 0.7:
            return "Low Confidence", target_confidence
        return "Needs Review", target_confidence
    if target_confidence < 0.7:
        return "Low Confidence", target_confidence
    return "Resolved", target_confidence


def _build_resolver_conflict_rows(
    resolver_result: Any,
) -> list[dict[str, Any]]:
    if resolver_result is None:
        return []
    resolved_objects = list(getattr(resolver_result, "resolved_objects", []) or [])
    resolved_by_target = {
        f"{_safe_text(item.object_type, 'object')}:{_safe_text(item.object_id, '')}": item
        for item in resolved_objects
    }
    rows: list[dict[str, Any]] = []
    for conflict in list(getattr(resolver_result, "conflicts", []) or []):
        status, target_confidence = _resolver_conflict_status(
            conflict, resolved_by_target
        )
        target_id = _safe_text(getattr(conflict, "target_id", None), "")
        target = resolved_by_target.get(target_id)
        canonical = (
            dict(getattr(target, "canonical_values", {}) or {}) if target else {}
        )
        observed_values = list(getattr(conflict, "observed_values", []) or [])
        observed_text = ", ".join(str(item) for item in observed_values)
        rows.append(
            {
                "conflict_id": _safe_text(
                    getattr(conflict, "conflict_id", None), "n/a"
                ),
                "target_id": target_id,
                "field": _safe_text(getattr(conflict, "field_name", None), "n/a"),
                "severity": _safe_text(getattr(conflict, "severity", None), "medium"),
                "message": _safe_text(getattr(conflict, "message", None), ""),
                "observed_values": observed_text,
                "status": status,
                "status_chip": _status_chip(status),
                "confidence": round(target_confidence, 2),
                "manufacturer": _safe_text(canonical.get("manufacturer"), "n/a"),
                "model": _safe_text(canonical.get("model"), "n/a"),
                "quantity": _safe_text(canonical.get("quantity"), "n/a"),
                "room": _safe_text(canonical.get("room_id"), "n/a"),
                "system": _safe_text(canonical.get("system_id"), "n/a"),
                "specification": ", ".join(
                    [
                        str(item)
                        for item in list(
                            canonical.get("specification_references") or []
                        )
                    ]
                )
                or "n/a",
                "drawing": ", ".join(
                    [
                        str(item)
                        for item in list(canonical.get("drawing_references") or [])
                    ]
                )
                or "n/a",
            }
        )
    return rows


def _render_engineering_trace_panel(
    st: Any,
    graph: dict[str, Any],
    resolver_result: Any,
    selected_insight: Any | None,
) -> None:
    st.markdown("#### Engineering Trace")
    if selected_insight is None:
        st.info("Select an insight to inspect engineering trace details.")
        return

    support_ids = [
        str(item)
        for item in list(getattr(selected_insight, "supporting_objects", []) or [])
    ]
    evidence_refs = [
        str(item) for item in list(getattr(selected_insight, "evidence_refs", []) or [])
    ]

    related_resolved = []
    related_conflicts = []
    related_rules = set()
    if resolver_result is not None:
        for resolved in list(getattr(resolver_result, "resolved_objects", []) or []):
            if any(token and token in str(resolved.to_dict()) for token in support_ids):
                related_resolved.append(resolved)
                for rule_id in list(getattr(resolved, "rules_applied", []) or []):
                    related_rules.add(str(rule_id))
        for conflict in list(getattr(resolver_result, "conflicts", []) or []):
            if any(token and token in str(conflict.to_dict()) for token in support_ids):
                related_conflicts.append(conflict)

    related_drawings = sorted(
        {
            _safe_text(edge.get("source"), "")
            for edge in list(graph.get("edges", []))
            if "drawing:" in _safe_text(edge.get("source"), "")
            and any(token and token in str(edge) for token in support_ids)
        }
    )
    related_specs = sorted(
        {
            _safe_text(edge.get("target"), "")
            for edge in list(graph.get("edges", []))
            if "spec:" in _safe_text(edge.get("target"), "")
            and any(token and token in str(edge) for token in support_ids)
        }
    )

    st.dataframe(
        [
            {
                "why atlas generated it": _safe_text(
                    getattr(selected_insight, "description", None), "n/a"
                ),
                "confidence": round(
                    float(getattr(selected_insight, "confidence", 0.0) or 0.0), 2
                ),
                "related objects": ", ".join(support_ids[:8]) or "n/a",
            }
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.dataframe(
        [
            {
                "trace field": "Rules Applied",
                "value": ", ".join(sorted(related_rules)) or "n/a",
            },
            {
                "trace field": "Supporting Evidence",
                "value": " | ".join(evidence_refs[:6]) or "n/a",
            },
            {
                "trace field": "Related Drawings",
                "value": ", ".join(related_drawings[:6]) or "n/a",
            },
            {
                "trace field": "Related Specifications",
                "value": ", ".join(related_specs[:6]) or "n/a",
            },
            {
                "trace field": "Resolver Decisions",
                "value": ", ".join(
                    [
                        f"{item.object_type}:{item.object_id}"
                        for item in related_resolved[:6]
                    ]
                )
                or "n/a",
            },
            {
                "trace field": "Knowledge Graph Relationships",
                "value": str(
                    sum(
                        1
                        for edge in list(graph.get("edges", []))
                        if any(token and token in str(edge) for token in support_ids)
                    )
                ),
            },
        ],
        use_container_width=True,
        hide_index=True,
    )
    if related_conflicts:
        st.markdown("Trace Conflicts")
        st.dataframe(
            [item.to_dict() for item in related_conflicts],
            use_container_width=True,
            hide_index=True,
        )


def _render_engineering_workbench_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Engineering Workbench",
        "Investigate conflicts, trace evidence, and prioritize engineering decisions.",
    )
    if context is None:
        _render_empty_state(
            st, "Engineering Workbench requires a loaded project review context."
        )
        return

    with st.spinner("Loading engineering workspace..."):
        graph = _build_knowledge_graph(record, context)
        resolver_result = _build_engineering_resolver(record, context)
        intelligence = _build_engineering_intelligence(record, context)
        objects = _workspace_objects(context)
    brief = context.get("brief")

    selection = dict(
        st.session_state.get("atlas_context_selection")
        or {"kind": "project", "data": {}}
    )
    selected_kind = _safe_text(selection.get("kind"), "project")
    selected_data = dict(selection.get("data") or {})
    selected_node = _node_for_current_selection(
        graph,
        selected_kind,
        selected_data,
        "Project",
    )
    if selected_node is None:
        selected_node = _select_first_node(graph, "Project")

    selected_node_id = _safe_text(selected_node.get("id"), "") if selected_node else ""
    scope_tokens = _scope_tokens(selection, selected_node)
    scope_filter_enabled = selected_kind in INVESTIGATION_SELECTION_KINDS

    insights = (
        list(getattr(intelligence, "insights", []) or [])
        if intelligence is not None
        else []
    )
    insight_rows = [item.to_dict() for item in insights]
    insight_rows = _filter_rows_by_scope(
        insight_rows, scope_tokens, scope_filter_enabled
    )

    conflict_rows = _build_resolver_conflict_rows(resolver_result)
    conflict_rows = _filter_rows_by_scope(
        conflict_rows, scope_tokens, scope_filter_enabled
    )

    rfi_rows = list(objects.get("rfis", []))
    rfi_rows = _filter_rows_by_scope(rfi_rows, scope_tokens, scope_filter_enabled)

    system_rows = (
        list(getattr(intelligence, "system_health", []) or [])
        if intelligence is not None
        else []
    )
    high_risk_system_rows = sorted(
        [
            item.to_dict() if hasattr(item, "to_dict") else dict(item)
            for item in system_rows
        ],
        key=lambda item: int(item.get("health_score", 0) or 0),
    )[:8]
    high_risk_system_rows = _filter_rows_by_scope(
        high_risk_system_rows,
        scope_tokens,
        scope_filter_enabled,
    )

    recommended_rows = []
    recommendations = (
        list(getattr(intelligence, "recommendations", []) or [])
        if intelligence is not None
        else []
    )
    for item in recommendations:
        recommended_rows.append(item.to_dict())
    for item in list(getattr(brief, "prioritized_reviewer_actions", []) or []):
        recommended_rows.append(
            item.to_dict() if hasattr(item, "to_dict") else dict(item)
        )
    recommended_rows = _filter_rows_by_scope(
        recommended_rows,
        scope_tokens,
        scope_filter_enabled,
    )

    evidence_rows = _filter_rows_by_scope(
        list(objects.get("evidence", [])),
        scope_tokens,
        scope_filter_enabled,
    )
    coordination_rows = _filter_rows_by_scope(
        list(objects.get("coordination_findings", [])),
        scope_tokens,
        scope_filter_enabled,
    )

    top_row = st.columns(4)
    _metric_card(top_row[0], "Active Engineering Insights", str(len(insight_rows)))
    _metric_card(top_row[1], "Resolver Conflicts", str(len(conflict_rows)))
    _metric_card(top_row[2], "Open RFI Candidates", str(len(rfi_rows)))
    _metric_card(top_row[3], "Coordination Findings", str(len(coordination_rows)))

    row_a = st.columns([3.6, 3.2, 3.2])
    with row_a[0]:
        st.markdown("#### Active Engineering Insights")
        if insight_rows:
            st.dataframe(insight_rows[:12], use_container_width=True, hide_index=True)
            insight_labels = [
                _safe_text(item.get("title"), f"Insight {index + 1}")
                for index, item in enumerate(insight_rows[:12])
            ]
            selected_insight_label = st.selectbox(
                "Select Insight",
                options=insight_labels,
                key="atlas_workbench_insight",
            )
            selected_insight_row = insight_rows[
                insight_labels.index(selected_insight_label)
            ]
            selected_insight_obj = next(
                (
                    item
                    for item in insights
                    if _safe_text(getattr(item, "title", None), "")
                    == _safe_text(selected_insight_row.get("title"), "")
                ),
                None,
            )
            _render_engineering_trace_panel(
                st, graph, resolver_result, selected_insight_obj
            )
        else:
            st.info("No engineering insights match the current scope.")

    with row_a[1]:
        st.markdown("#### Resolver Conflicts")
        if conflict_rows:
            st.dataframe(conflict_rows[:12], use_container_width=True, hide_index=True)
            labels = [
                f"{_safe_text(item.get('field'), 'field')} · {_safe_text(item.get('target_id'), 'target')}"
                for item in conflict_rows[:12]
            ]
            selected_label = st.selectbox(
                "Select Resolver Conflict",
                options=labels,
                key="atlas_workbench_conflict",
            )
            selected = conflict_rows[labels.index(selected_label)]
            if st.button(
                "Investigate Conflict",
                key="atlas_investigate_conflict",
                use_container_width=True,
            ):
                _set_context_selection(st, "resolver_conflict", selected)
                st.rerun()
        else:
            st.info("No resolver conflicts for the current scope.")

    with row_a[2]:
        st.markdown("#### Open RFI Candidates")
        if rfi_rows:
            st.dataframe(rfi_rows[:12], use_container_width=True, hide_index=True)
            labels = [
                _safe_text(item.get("title"), _safe_text(item.get("rfi_id"), "RFI"))
                for item in rfi_rows[:12]
            ]
            selected_label = st.selectbox(
                "Select RFI Candidate",
                options=labels,
                key="atlas_workbench_rfi",
            )
            selected = rfi_rows[labels.index(selected_label)]
            if st.button(
                "Investigate RFI", key="atlas_investigate_rfi", use_container_width=True
            ):
                _set_context_selection(st, "rfi", selected)
                st.rerun()
        else:
            st.info("No RFI candidates match the current scope.")

    row_b = st.columns([3.6, 3.2, 3.2])
    with row_b[0]:
        st.markdown("#### High-Risk Systems")
        if high_risk_system_rows:
            st.dataframe(
                high_risk_system_rows, use_container_width=True, hide_index=True
            )
        else:
            st.info("No high-risk systems match the current scope.")

    with row_b[1]:
        st.markdown("#### Recommended Actions")
        if recommended_rows:
            st.dataframe(
                recommended_rows[:12], use_container_width=True, hide_index=True
            )
        else:
            st.info("No recommended actions match the current scope.")

    with row_b[2]:
        st.markdown("#### Selected Object Detail")
        if selected_node is None:
            st.info("Select an object to inspect details.")
        else:
            st.dataframe(
                [
                    {
                        "field": "Object",
                        "value": _safe_text(selected_node.get("label"), "n/a"),
                    },
                    {
                        "field": "Type",
                        "value": _safe_text(selected_node.get("type"), "n/a"),
                    },
                    {
                        "field": "Selection Kind",
                        "value": selected_kind,
                    },
                    {
                        "field": "Node ID",
                        "value": selected_node_id or "n/a",
                    },
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("#### Coordination Findings")
    if coordination_rows:
        st.dataframe(
            [
                {
                    "severity": _safe_text(item.get("severity"), "n/a"),
                    "category": _safe_text(item.get("category"), "n/a"),
                    "title": _safe_text(item.get("title"), "n/a"),
                    "recommended action": _safe_text(
                        item.get("recommended_action"),
                        "n/a",
                    ),
                }
                for item in coordination_rows[:12]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No coordination findings match the current scope.")

    st.markdown("#### Evidence Panel")
    if evidence_rows:
        st.dataframe(evidence_rows[:20], use_container_width=True, hide_index=True)
    else:
        st.info("No evidence rows match the current scope.")

    if selected_kind in INVESTIGATION_SELECTION_KINDS and selected_node is not None:
        st.markdown("### Investigation Mode")
        subgraph = _relationship_subgraph(graph, selected_node_id, depth=2)

        if st.button(
            "Create Investigation Note",
            key="atlas_create_investigation_note",
            use_container_width=True,
        ):
            st.session_state["atlas_notebook_draft"] = {
                "title": f"Investigation Note · {_safe_text(selected_node.get('label'), 'Object')}",
                "body": "Document observations, assumptions, and follow-up actions for this object.",
                "related_objects": [selected_node_id],
                "entry_type": "Engineering Note",
                "priority": "Medium",
                "status": "Open",
                "tags": ["Investigation"],
            }
            st.session_state["atlas_active_page"] = "Engineering Notebook"
            st.rerun()

        st.markdown("#### Object Summary")
        st.dataframe(
            [dict(selected_node.get("data") or {})],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Relationship Graph")
        connected_edges = list(subgraph.get("edges", []))[:24]
        if connected_edges:
            mermaid_lines = ["graph LR"]
            for edge in connected_edges:
                source = _node_label(
                    graph, _safe_text(edge.get("source"), "n/a")
                ).replace('"', "")
                target = _node_label(
                    graph, _safe_text(edge.get("target"), "n/a")
                ).replace('"', "")
                rel = _safe_text(edge.get("relationship"), "linked").replace('"', "")
                mermaid_lines.append(f'    "{source}" -->|"{rel}"| "{target}"')
            st.markdown("```mermaid\n" + "\n".join(mermaid_lines) + "\n```")
        else:
            st.info("No relationship graph edges found for this selection.")

        st.markdown("#### Supporting Evidence")
        supporting_evidence = [
            {
                "relationship": edge.get("relationship"),
                "source evidence": edge.get("source_evidence"),
                "from": _node_label(graph, _safe_text(edge.get("source"), "n/a")),
                "to": _node_label(graph, _safe_text(edge.get("target"), "n/a")),
            }
            for edge in connected_edges
            if _safe_text(edge.get("source_evidence"), "n/a") != "n/a"
        ]
        if supporting_evidence:
            st.dataframe(supporting_evidence, use_container_width=True, hide_index=True)
        else:
            st.info("No explicit supporting evidence references were found.")

        st.markdown("#### Conflicting Evidence")
        conflicting_rows = [
            row
            for row in conflict_rows
            if selected_node_id
            and selected_node_id in _safe_text(row.get("target_id"), "")
        ]
        if conflicting_rows:
            st.dataframe(conflicting_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No conflicting evidence detected for this selection.")

        st.markdown("#### Engineering Insights")
        if insight_rows:
            st.dataframe(insight_rows[:10], use_container_width=True, hide_index=True)
        else:
            st.info("No engineering insights linked to this selection.")

        st.markdown("#### Resolver Decisions")
        resolver_rows = []
        if resolver_result is not None:
            for item in list(getattr(resolver_result, "resolved_objects", []) or []):
                if selected_node_id and selected_node_id in str(item.to_dict()):
                    resolver_rows.append(item.to_dict())
        if resolver_rows:
            st.dataframe(resolver_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No resolver decisions mapped to this selection.")

        st.markdown("#### Related Documents")
        related_docs = sorted(
            {
                _safe_text(item.get("source_file"), "")
                for item in evidence_rows
                if _safe_text(item.get("source_file"), "")
            }
        )
        if related_docs:
            st.dataframe(
                [{"document": item} for item in related_docs],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No related documents were found.")

        st.markdown("#### Related Drawings")
        related_drawings = sorted(
            {
                _safe_text(edge.get("source"), "")
                for edge in connected_edges
                if _safe_text(edge.get("source"), "").startswith("drawing:")
            }
            | {
                _safe_text(edge.get("target"), "")
                for edge in connected_edges
                if _safe_text(edge.get("target"), "").startswith("drawing:")
            }
        )
        if related_drawings:
            st.dataframe(
                [{"drawing": item} for item in related_drawings],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No related drawings were found.")

        st.markdown("#### Related Specifications")
        related_specs = sorted(
            {
                _safe_text(edge.get("source"), "")
                for edge in connected_edges
                if _safe_text(edge.get("source"), "").startswith("spec:")
            }
            | {
                _safe_text(edge.get("target"), "")
                for edge in connected_edges
                if _safe_text(edge.get("target"), "").startswith("spec:")
            }
        )
        if related_specs:
            st.dataframe(
                [{"specification": item} for item in related_specs],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No related specifications were found.")

        st.markdown("#### Recommended Actions")
        if recommended_rows:
            st.dataframe(
                recommended_rows[:10], use_container_width=True, hide_index=True
            )
        else:
            st.info("No recommended actions linked to this selection.")

        st.markdown("#### History")
        st.dataframe(
            _timeline_events(record, context),
            use_container_width=True,
            hide_index=True,
        )


def _render_resolver_conflict_center_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Resolver Conflict Center")
    resolver_result = _build_engineering_resolver(record, context)
    rows = _build_resolver_conflict_rows(resolver_result)
    if not rows:
        st.info("No resolver conflicts are currently available.")
        return

    cols = st.columns([1.8, 2.4, 1.8])
    group_by = cols[0].selectbox(
        "Group By",
        options=[
            "Manufacturer",
            "Model",
            "Quantity",
            "Room",
            "System",
            "Specification",
            "Drawing",
        ],
    )
    status_filter = cols[1].multiselect(
        "Status",
        options=["Resolved", "Needs Review", "High Confidence", "Low Confidence"],
        default=[],
    )
    severity_filter = cols[2].multiselect(
        "Severity",
        options=sorted({str(item.get("severity") or "medium") for item in rows}),
        default=[],
    )

    key_map = {
        "Manufacturer": "manufacturer",
        "Model": "model",
        "Quantity": "quantity",
        "Room": "room",
        "System": "system",
        "Specification": "specification",
        "Drawing": "drawing",
    }
    group_key = key_map[group_by]

    filtered = [
        item
        for item in rows
        if (not status_filter or item.get("status") in status_filter)
        and (not severity_filter or item.get("severity") in severity_filter)
    ]
    if not filtered:
        st.info("No conflicts match the current filters.")
        return

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in filtered:
        group_value = _safe_text(item.get(group_key), "n/a")
        grouped[group_value].append(item)

    for group_value in sorted(grouped.keys()):
        st.markdown(f"#### {group_by}: {group_value}")
        st.dataframe(grouped[group_value], use_container_width=True, hide_index=True)

    labels = [
        f"{_safe_text(item.get('field'), 'field')} · {_safe_text(item.get('target_id'), 'target')}"
        for item in filtered
    ]
    selected_label = st.selectbox("Select Conflict", options=labels)
    selected = filtered[labels.index(selected_label)]
    if st.button("Open Conflict in Workbench", type="primary"):
        _set_context_selection(st, "resolver_conflict", selected)
        st.session_state["atlas_active_page"] = "Engineering Workbench"
        st.rerun()


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


def _upsert_notebook_entry(st: Any, entry: dict[str, Any]) -> None:
    entries = list(st.session_state.get("atlas_notebook_entries") or [])
    existing_index = next(
        (
            index
            for index, item in enumerate(entries)
            if _safe_text(item.get("entry_id"), "")
            == _safe_text(entry.get("entry_id"), "")
        ),
        None,
    )
    if existing_index is None:
        entries.append(entry)
    else:
        entries[existing_index] = entry
    st.session_state["atlas_notebook_entries"] = entries


def _render_engineering_notebook_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Engineering Notebook",
        "Record engineering observations, decisions, assumptions, and review history with traceability.",
    )

    draft = dict(st.session_state.get("atlas_notebook_draft") or {})
    entries = _notebook_entries(st, record, context)
    entry_types = sorted(
        {
            _safe_text(item.get("entry_type"), "")
            for item in entries
            if _safe_text(item.get("entry_type"), "")
        }
    )
    tags = sorted(
        {
            _safe_text(tag, "")
            for item in entries
            for tag in list(item.get("tags") or [])
            if _safe_text(tag, "")
        }
    )
    object_options = sorted(
        {
            _safe_text(ref, "")
            for item in entries
            for ref in list(item.get("related_objects") or [])
            if _safe_text(ref, "")
        }
        | set(_notebook_object_reference_options(record, context))
    )

    filter_cols = st.columns([2.0, 1.5, 1.4, 1.4, 1.2, 1.2])
    search_query = filter_cols[0].text_input(
        "Search",
        value=st.session_state.get("atlas_notebook_search", ""),
        key="atlas_notebook_search",
        placeholder="title, body, tags, linked objects",
    )
    type_filter = filter_cols[1].multiselect(
        "Entry Type",
        options=entry_types,
        default=[],
    )
    tag_filter = filter_cols[2].multiselect(
        "Tags",
        options=tags,
        default=[],
    )
    object_filter = filter_cols[3].multiselect(
        "Object",
        options=object_options,
        default=[],
    )
    start_date = filter_cols[4].text_input(
        "Start Date", value="", placeholder="YYYY-MM-DD"
    )
    end_date = filter_cols[5].text_input("End Date", value="", placeholder="YYYY-MM-DD")

    filtered = [
        item
        for item in entries
        if (
            (
                not search_query
                or _contains_any(
                    str(item),
                    [search_query],
                )
            )
            and (
                not type_filter or _safe_text(item.get("entry_type"), "") in type_filter
            )
            and (
                not tag_filter
                or any(
                    _safe_text(tag, "") in tag_filter
                    for tag in list(item.get("tags") or [])
                )
            )
            and (
                not object_filter
                or any(
                    _safe_text(ref, "") in object_filter
                    for ref in list(item.get("related_objects") or [])
                )
            )
            and _entry_matches_date_window(item, start_date.strip(), end_date.strip())
        )
    ]

    filtered.sort(key=_notebook_sort_key, reverse=True)

    tabs = st.tabs(["Notebook Entries", "Engineering Decisions"])

    with tabs[0]:
        st.dataframe(
            [
                {
                    "created": _safe_text(item.get("created_at"), "n/a"),
                    "type": _safe_text(item.get("entry_type"), "n/a"),
                    "priority": _safe_text(item.get("priority"), "n/a"),
                    "status": _safe_text(item.get("status"), "n/a"),
                    "title": _safe_text(item.get("title"), "n/a"),
                    "author": _safe_text(item.get("author"), "n/a"),
                    "objects": len(list(item.get("related_objects") or [])),
                    "read only": "yes" if item.get("read_only") else "no",
                }
                for item in filtered
            ],
            use_container_width=True,
            hide_index=True,
        )

        if filtered:
            labels = [
                f"{_safe_text(item.get('created_at'), 'n/a')} · {_safe_text(item.get('entry_type'), 'Entry')} · {_safe_text(item.get('title'), 'Untitled')}"
                for item in filtered
            ]
            selected_label = st.selectbox(
                "Select Notebook Entry",
                options=labels,
                key="atlas_notebook_selected",
            )
            selected_entry = filtered[labels.index(selected_label)]
            _set_context_selection(st, "notebook_entry", selected_entry)

            detail_col, link_col = st.columns([2.3, 1.7])
            with detail_col:
                st.markdown("#### Entry Detail")
                st.dataframe(
                    [
                        {
                            "field": "Entry ID",
                            "value": _safe_text(selected_entry.get("entry_id"), "n/a"),
                        },
                        {
                            "field": "Created",
                            "value": _safe_text(
                                selected_entry.get("created_at"), "n/a"
                            ),
                        },
                        {
                            "field": "Author",
                            "value": _safe_text(selected_entry.get("author"), "n/a"),
                        },
                        {
                            "field": "Type",
                            "value": _safe_text(
                                selected_entry.get("entry_type"), "n/a"
                            ),
                        },
                        {
                            "field": "Priority",
                            "value": _safe_text(selected_entry.get("priority"), "n/a"),
                        },
                        {
                            "field": "Status",
                            "value": _safe_text(selected_entry.get("status"), "n/a"),
                        },
                        {
                            "field": "Title",
                            "value": _safe_text(selected_entry.get("title"), "n/a"),
                        },
                        {
                            "field": "Body",
                            "value": _safe_text(selected_entry.get("body"), "n/a"),
                        },
                        {
                            "field": "Tags",
                            "value": ", ".join(list(selected_entry.get("tags") or []))
                            or "n/a",
                        },
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                if not bool(selected_entry.get("read_only", False)):
                    st.markdown("#### Edit Entry")
                    edited_title = st.text_input(
                        "Title",
                        value=_safe_text(selected_entry.get("title"), ""),
                        key=f"atlas_notebook_edit_title_{_safe_text(selected_entry.get('entry_id'), 'entry')}",
                    )
                    edited_body = st.text_area(
                        "Body",
                        value=_safe_text(selected_entry.get("body"), ""),
                        key=f"atlas_notebook_edit_body_{_safe_text(selected_entry.get('entry_id'), 'entry')}",
                    )
                    edited_type = st.selectbox(
                        "Entry Type",
                        options=NOTEBOOK_ENTRY_TYPES,
                        index=max(
                            (
                                NOTEBOOK_ENTRY_TYPES.index(
                                    _safe_text(
                                        selected_entry.get("entry_type"),
                                        "Engineering Note",
                                    )
                                )
                                if _safe_text(
                                    selected_entry.get("entry_type"), "Engineering Note"
                                )
                                in NOTEBOOK_ENTRY_TYPES
                                else 0
                            ),
                            0,
                        ),
                        key=f"atlas_notebook_edit_type_{_safe_text(selected_entry.get('entry_id'), 'entry')}",
                    )
                    edited_priority = st.selectbox(
                        "Priority",
                        options=NOTEBOOK_PRIORITIES,
                        index=max(
                            (
                                NOTEBOOK_PRIORITIES.index(
                                    _safe_text(selected_entry.get("priority"), "Medium")
                                )
                                if _safe_text(selected_entry.get("priority"), "Medium")
                                in NOTEBOOK_PRIORITIES
                                else 2
                            ),
                            0,
                        ),
                        key=f"atlas_notebook_edit_priority_{_safe_text(selected_entry.get('entry_id'), 'entry')}",
                    )
                    edited_status = st.selectbox(
                        "Status",
                        options=NOTEBOOK_STATUSES,
                        index=max(
                            (
                                NOTEBOOK_STATUSES.index(
                                    _safe_text(selected_entry.get("status"), "Open")
                                )
                                if _safe_text(selected_entry.get("status"), "Open")
                                in NOTEBOOK_STATUSES
                                else 0
                            ),
                            0,
                        ),
                        key=f"atlas_notebook_edit_status_{_safe_text(selected_entry.get('entry_id'), 'entry')}",
                    )
                    edited_tags_text = st.text_input(
                        "Tags (comma-separated)",
                        value=", ".join(list(selected_entry.get("tags") or [])),
                        key=f"atlas_notebook_edit_tags_{_safe_text(selected_entry.get('entry_id'), 'entry')}",
                    )

                    if st.button(
                        "Save Entry",
                        key=f"atlas_notebook_save_{_safe_text(selected_entry.get('entry_id'), 'entry')}",
                    ):
                        updated_entry = dict(selected_entry)
                        updated_entry["title"] = edited_title.strip() or _safe_text(
                            selected_entry.get("title"), "Untitled"
                        )
                        updated_entry["body"] = edited_body.strip()
                        updated_entry["entry_type"] = edited_type
                        updated_entry["priority"] = edited_priority
                        updated_entry["status"] = edited_status
                        updated_entry["tags"] = [
                            item.strip()
                            for item in edited_tags_text.split(",")
                            if item.strip()
                        ]
                        _upsert_notebook_entry(st, updated_entry)
                        st.success("Notebook entry updated.")
                        st.rerun()
                else:
                    st.caption("Atlas-generated entries are read-only.")

            with link_col:
                st.markdown("#### Linked Objects")
                related_objects = list(selected_entry.get("related_objects") or [])
                if related_objects:
                    for ref in related_objects[:20]:
                        if st.button(
                            f"Open {_safe_text(ref, 'object')}",
                            key=f"atlas_note_open_{_safe_text(selected_entry.get('entry_id'), 'entry')}_{_safe_text(ref, 'ref')}",
                            use_container_width=True,
                        ):
                            _open_linked_object(st, ref)
                else:
                    st.info("No linked objects.")

                st.markdown("#### Evidence Refs")
                evidence_refs = list(selected_entry.get("evidence_refs") or [])
                if evidence_refs:
                    st.dataframe(
                        [{"evidence_ref": item} for item in evidence_refs],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("No evidence references.")

        st.markdown("#### Create Entry")
        create_col1, create_col2 = st.columns([2.2, 1.8])
        with create_col1:
            title = st.text_input(
                "Title",
                value=_safe_text(draft.get("title"), ""),
                key="atlas_notebook_create_title",
            )
            body = st.text_area(
                "Body",
                value=_safe_text(draft.get("body"), ""),
                key="atlas_notebook_create_body",
            )
            entry_type = st.selectbox(
                "Entry Type",
                options=NOTEBOOK_ENTRY_TYPES,
                index=(
                    NOTEBOOK_ENTRY_TYPES.index(
                        _safe_text(draft.get("entry_type"), "Engineering Note")
                    )
                    if _safe_text(draft.get("entry_type"), "Engineering Note")
                    in NOTEBOOK_ENTRY_TYPES
                    else 0
                ),
                key="atlas_notebook_create_type",
            )
            priority = st.selectbox(
                "Priority",
                options=NOTEBOOK_PRIORITIES,
                index=(
                    NOTEBOOK_PRIORITIES.index(
                        _safe_text(draft.get("priority"), "Medium")
                    )
                    if _safe_text(draft.get("priority"), "Medium")
                    in NOTEBOOK_PRIORITIES
                    else 2
                ),
                key="atlas_notebook_create_priority",
            )
            status = st.selectbox(
                "Status",
                options=NOTEBOOK_STATUSES,
                index=(
                    NOTEBOOK_STATUSES.index(_safe_text(draft.get("status"), "Open"))
                    if _safe_text(draft.get("status"), "Open") in NOTEBOOK_STATUSES
                    else 0
                ),
                key="atlas_notebook_create_status",
            )

        with create_col2:
            default_related = [
                item
                for item in list(draft.get("related_objects") or [])
                if item in object_options
            ]
            related_objects = st.multiselect(
                "Related Objects",
                options=object_options,
                default=default_related,
                key="atlas_notebook_create_related",
            )
            evidence_options = [
                f"{_safe_text(item.get('source_file'), 'file')} p.{item.get('page', 'n/a')}"
                for item in list(_workspace_objects(context).get("evidence") or [])
            ]
            evidence_refs = st.multiselect(
                "Evidence Refs",
                options=sorted(set(evidence_options)),
                default=[],
                key="atlas_notebook_create_evidence_refs",
            )
            tags_text = st.text_input(
                "Tags (comma-separated)",
                value=", ".join(list(draft.get("tags") or [])),
                key="atlas_notebook_create_tags",
            )

        create_actions = st.columns(3)
        if create_actions[0].button(
            "Create Note", type="primary", use_container_width=True
        ):
            entry_id = f"note:{record.workspace_id}:{hashlib.sha1(f'{title}|{_now_iso()}'.encode('utf-8')).hexdigest()[:10]}"
            new_entry = {
                "entry_id": entry_id,
                "created_at": _now_iso(),
                "author": "Engineer",
                "title": title.strip() or "Untitled Note",
                "body": body.strip(),
                "entry_type": entry_type,
                "priority": priority,
                "status": status,
                "related_objects": list(related_objects),
                "evidence_refs": list(evidence_refs),
                "tags": [item.strip() for item in tags_text.split(",") if item.strip()],
                "created_by_engine_version": "",
                "read_only": False,
                "system_generated": False,
            }
            _upsert_notebook_entry(st, new_entry)
            st.session_state["atlas_notebook_draft"] = {}
            st.success("Notebook entry created.")
            st.rerun()
        if create_actions[1].button("Clear Draft", use_container_width=True):
            st.session_state["atlas_notebook_draft"] = {}
            st.rerun()
        if create_actions[2].button("Open History", use_container_width=True):
            st.session_state["atlas_active_page"] = "History"
            st.rerun()

    with tabs[1]:
        decision_rows = [item for item in filtered if _is_decision_log_entry(item)]
        st.dataframe(
            [
                {
                    "created": _safe_text(item.get("created_at"), "n/a"),
                    "type": _safe_text(item.get("entry_type"), "n/a"),
                    "status": _safe_text(item.get("status"), "n/a"),
                    "priority": _safe_text(item.get("priority"), "n/a"),
                    "title": _safe_text(item.get("title"), "n/a"),
                    "author": _safe_text(item.get("author"), "n/a"),
                }
                for item in decision_rows
            ],
            use_container_width=True,
            hide_index=True,
        )
        if not decision_rows:
            _render_empty_state(
                st,
                "No decision-log entries found. Decision Log includes Decision, Approved Assumption, and Resolved Clarification.",
            )


def _render_coordination_review_page(
    st: Any,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Coordination Review",
        "Validate drawing/spec/equipment/system agreement, conflicts, and gaps.",
    )
    with st.spinner("Loading coordination findings..."):
        objects = _workspace_objects(context)
    findings = list(objects.get("coordination_findings", []))
    issues = list(objects.get("coordination_issues", []))
    summary = dict(objects.get("coordination_summary") or {})

    if not findings:
        _render_empty_state(
            st,
            "No coordination findings are available for the current project context.",
        )
        return

    top_row = st.columns(4)
    _metric_card(top_row[0], "Coordination Findings", str(len(findings)))
    _metric_card(
        top_row[1],
        "Conflicts",
        str(summary.get("conflict_count", 0)),
    )
    _metric_card(top_row[2], "Gaps", str(summary.get("gap_count", 0)))
    _metric_card(
        top_row[3],
        "Coordination Confidence",
        _safe_text(objects.get("coordination_confidence"), "n/a"),
    )

    filters = st.columns([1.6, 1.3, 1.3, 1.8])
    category_filter = filters[0].multiselect(
        "Category",
        options=sorted({_safe_text(item.get("category"), "") for item in findings}),
        default=[],
    )
    severity_filter = filters[1].multiselect(
        "Severity",
        options=["critical", "high", "medium", "low"],
        default=[],
    )
    confidence_filter = filters[2].multiselect(
        "Confidence",
        options=["high", "medium", "low"],
        default=[],
    )
    query = filters[3].text_input(
        "Search Findings",
        value=st.session_state.get("atlas_coordination_search", ""),
        key="atlas_coordination_search",
        placeholder="title, object id, category",
    )

    filtered = [
        item
        for item in findings
        if (
            (
                not category_filter
                or _safe_text(item.get("category"), "") in category_filter
            )
            and (
                not severity_filter
                or _safe_text(item.get("severity"), "") in severity_filter
            )
            and (
                not confidence_filter
                or _safe_text(item.get("confidence"), "") in confidence_filter
            )
            and (not query or _contains_any(str(item), [query]))
        )
    ]

    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    filtered.sort(
        key=lambda item: severity_rank.get(_safe_text(item.get("severity"), ""), 0),
        reverse=True,
    )

    st.markdown("#### Findings")
    st.dataframe(
        [
            {
                "severity": _safe_text(item.get("severity"), "n/a"),
                "category": _safe_text(item.get("category"), "n/a"),
                "confidence": _safe_text(item.get("confidence"), "n/a"),
                "title": _safe_text(item.get("title"), "n/a"),
                "recommended action": _safe_text(
                    item.get("recommended_action"),
                    "n/a",
                ),
                "related objects": ", ".join(
                    list(item.get("related_objects") or [])[:6]
                )
                or "n/a",
            }
            for item in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )

    if filtered:
        labels = [
            f"{_safe_text(item.get('severity'), 'n/a')} · {_safe_text(item.get('title'), 'finding')}"
            for item in filtered
        ]
        selected_label = st.selectbox(
            "Select Finding",
            options=labels,
            key="atlas_coordination_finding",
        )
        selected = filtered[labels.index(selected_label)]

        detail_col, issue_col = st.columns([2.3, 1.7])
        with detail_col:
            st.markdown("#### Finding Detail")
            st.dataframe(
                [
                    {
                        "field": "Finding ID",
                        "value": _safe_text(selected.get("finding_id"), "n/a"),
                    },
                    {
                        "field": "Category",
                        "value": _safe_text(selected.get("category"), "n/a"),
                    },
                    {
                        "field": "Severity",
                        "value": _safe_text(selected.get("severity"), "n/a"),
                    },
                    {
                        "field": "Confidence",
                        "value": _safe_text(selected.get("confidence"), "n/a"),
                    },
                    {
                        "field": "Description",
                        "value": _safe_text(selected.get("description"), "n/a"),
                    },
                    {
                        "field": "Recommended Action",
                        "value": _safe_text(
                            selected.get("recommended_action"),
                            "n/a",
                        ),
                    },
                ],
                use_container_width=True,
                hide_index=True,
            )

            evidence_rows = list(selected.get("evidence") or [])
            st.markdown("#### Supporting Evidence")
            if evidence_rows:
                st.dataframe(evidence_rows, use_container_width=True, hide_index=True)
            else:
                st.info("No explicit evidence rows were attached to this finding.")

        with issue_col:
            st.markdown("#### Coordination Issues")
            related_issues = [
                item
                for item in issues
                if _safe_text(selected.get("finding_id"), "")
                in list(item.get("finding_ids") or [])
            ]
            if related_issues:
                st.dataframe(related_issues, use_container_width=True, hide_index=True)
            else:
                st.info("No grouped issue currently references this finding.")

            st.markdown("#### Summary")
            st.dataframe(
                [
                    {
                        "field": "Total Findings",
                        "value": summary.get("total_findings", 0),
                    },
                    {
                        "field": "Agreement",
                        "value": summary.get("agreement_count", 0),
                    },
                    {
                        "field": "Conflict",
                        "value": summary.get("conflict_count", 0),
                    },
                    {
                        "field": "Gap",
                        "value": summary.get("gap_count", 0),
                    },
                ],
                use_container_width=True,
                hide_index=True,
            )


def _render_engineering_intelligence_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Engineering Intelligence",
        "Decision-oriented engineering health, risks, and recommendations.",
    )
    with st.spinner("Loading engineering intelligence..."):
        intelligence = _build_engineering_intelligence(record, context)
    if intelligence is None:
        _render_empty_state(
            st,
            "Engineering insights are unavailable until a project review context is loaded.",
        )
        return

    graph = _build_knowledge_graph(record=record, context=context)
    objects = _workspace_objects(context)
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

    coordination_summary = dict(objects.get("coordination_summary") or {})
    coordination_findings = list(objects.get("coordination_findings") or [])
    st.markdown("#### Coordination Intelligence Summary")
    st.dataframe(
        [
            {
                "total findings": coordination_summary.get("total_findings", 0),
                "conflicts": coordination_summary.get("conflict_count", 0),
                "gaps": coordination_summary.get("gap_count", 0),
                "agreements": coordination_summary.get("agreement_count", 0),
                "confidence": _safe_text(
                    objects.get("coordination_confidence"),
                    "n/a",
                ),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.dataframe(
        [
            {
                "severity": _safe_text(item.get("severity"), "n/a"),
                "category": _safe_text(item.get("category"), "n/a"),
                "title": _safe_text(item.get("title"), "n/a"),
                "action": _safe_text(item.get("recommended_action"), "n/a"),
            }
            for item in coordination_findings[:10]
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


def _render_engineering_resolver_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Engineering Resolver")
    resolver_result = _build_engineering_resolver(record, context)
    if resolver_result is None:
        st.info(
            "Engineering resolution is unavailable until a project review context is loaded."
        )
        return

    summary = dict(resolver_result.summary or {})
    st.dataframe(
        [
            {
                "resolved objects": summary.get("resolved_count", 0),
                "conflicts": summary.get("conflict_count", 0),
                "manual review required": summary.get("manual_review_count", 0),
                "confidence": round(float(summary.get("confidence", 0.0) or 0.0), 2),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Resolved Objects")
    st.dataframe(
        [item.to_dict() for item in resolver_result.resolved_objects],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Conflicts")
    conflict_rows = [item.to_dict() for item in resolver_result.conflicts]
    if conflict_rows:
        st.dataframe(conflict_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No deterministic conflicts were detected.")

    st.markdown("#### Resolution Rules")
    st.dataframe(
        [item.to_dict() for item in resolver_result.rules_applied],
        use_container_width=True,
        hide_index=True,
    )

    manual_review_rows = [
        item.to_dict()
        for item in resolver_result.resolved_objects
        if item.manual_review_required
    ]
    st.markdown("#### Manual Review Required")
    if manual_review_rows:
        st.dataframe(manual_review_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No resolved objects currently require manual review.")


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
    _render_page_header(
        st,
        "Project Explorer",
        "Inspect intake artifacts, extraction health, and file-level traceability.",
    )
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
        _render_empty_state(st, "No files match the current filters.")
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

    explorer_col, confidence_col = st.columns([3, 2])
    with explorer_col:
        st.caption("Each drawing is a first-class object with relationship links.")
    with confidence_col:
        st.caption(
            f"Drawing intelligence confidence: {_safe_text(objects.get('drawing_intelligence_confidence'), 'n/a')}"
        )

    summary_rows = [
        {
            "drawing number": item["drawing_number"],
            "title": item["title"],
            "revision": item["revision"],
            "issue date": item["issue_date"],
            "discipline": item["discipline"],
            "category": item.get("sheet_category", "other"),
            "sequence": item.get("sheet_sequence", "n/a"),
            "drawing refs": len(item.get("referenced_drawings", [])),
            "detail refs": len(item.get("detail_references", [])),
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
                {
                    "property": "Sheet Category",
                    "value": _safe_text(selected.get("sheet_category"), "other"),
                },
                {
                    "property": "Sheet Sequence",
                    "value": _safe_text(selected.get("sheet_sequence"), "n/a"),
                },
                {
                    "property": "Drawing Scale",
                    "value": _safe_text(selected.get("drawing_scale"), "n/a"),
                },
                {"property": "OCR Status", "value": selected["ocr_status"]},
                {
                    "property": "Extraction Quality",
                    "value": selected["extraction_quality"],
                },
                {
                    "property": "Intelligence Confidence",
                    "value": _safe_text(
                        selected.get("drawing_intelligence_confidence"), "n/a"
                    ),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("Referenced Objects")
        st.dataframe(
            [
                {
                    "relationship": "Drawings",
                    "objects": ", ".join(selected.get("referenced_drawings", []))
                    or "n/a",
                },
                {
                    "relationship": "Details",
                    "objects": ", ".join(selected.get("detail_references", []))
                    or "n/a",
                },
                {
                    "relationship": "Views",
                    "objects": ", ".join(selected.get("view_references", [])) or "n/a",
                },
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

        st.markdown("#### Deterministic Sheet Navigation")
        ordered_rows = sorted(
            rows,
            key=lambda item: (
                (
                    10**6
                    if not isinstance(item.get("sheet_sequence"), int)
                    else int(item.get("sheet_sequence", 0))
                ),
                _safe_text(item.get("drawing_number"), ""),
            ),
        )
        selected_index = next(
            (
                index
                for index, item in enumerate(ordered_rows)
                if _safe_text(item.get("drawing_number"), "")
                == _safe_text(selected.get("drawing_number"), "")
            ),
            0,
        )
        previous_sheet = (
            ordered_rows[selected_index - 1] if selected_index > 0 else None
        )
        next_sheet = (
            ordered_rows[selected_index + 1]
            if selected_index + 1 < len(ordered_rows)
            else None
        )
        nav_rows = [
            {
                "target": "Previous",
                "drawing": _safe_text(
                    previous_sheet.get("drawing_number") if previous_sheet else None,
                    "n/a",
                ),
            },
            {
                "target": "Next",
                "drawing": _safe_text(
                    next_sheet.get("drawing_number") if next_sheet else None,
                    "n/a",
                ),
            },
            {
                "target": "Referenced Sheets",
                "drawing": ", ".join(selected.get("referenced_drawings", [])) or "n/a",
            },
            {
                "target": "Referenced Details",
                "drawing": ", ".join(selected.get("detail_references", [])) or "n/a",
            },
            {
                "target": "Referenced Views",
                "drawing": ", ".join(selected.get("view_references", [])) or "n/a",
            },
        ]
        st.dataframe(nav_rows, use_container_width=True, hide_index=True)

    with nav_col:
        st.markdown("#### Quick Navigation")
        if st.button("Open Drawing Explorer", use_container_width=True):
            st.session_state["atlas_active_page"] = "Drawing Explorer"
            st.rerun()
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


def _render_drawing_explorer_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Drawing Explorer")
    objects = _workspace_objects(context)
    rows = list(objects.get("drawings", []))
    if not rows:
        st.info("No drawing objects available.")
        return

    hierarchy = dict(objects.get("drawing_hierarchy") or {})
    discipline_options = sorted(
        {_safe_text(item.get("discipline"), "unknown") for item in rows}
    )
    category_options = sorted(
        {_safe_text(item.get("sheet_category"), "other") for item in rows}
    )

    filter_col, search_col, sort_col = st.columns([1.6, 1.6, 1.2])
    with filter_col:
        discipline_filter = st.multiselect(
            "Discipline",
            options=discipline_options,
            default=[],
            key="atlas_drawing_explorer_discipline",
        )
        category_filter = st.multiselect(
            "Sheet Category",
            options=category_options,
            default=[],
            key="atlas_drawing_explorer_category",
        )
    with search_col:
        query = (
            st.text_input(
                "Search sheets",
                key="atlas_drawing_explorer_search",
                value=st.session_state.get("atlas_drawing_explorer_search", ""),
            )
            .strip()
            .lower()
        )
    with sort_col:
        sort_field = st.selectbox(
            "Sort by",
            options=["sheet_sequence", "drawing_number", "title", "discipline"],
            key="atlas_drawing_explorer_sort",
        )
        descending = (
            st.selectbox(
                "Order",
                options=["Ascending", "Descending"],
                key="atlas_drawing_explorer_order",
            )
            == "Descending"
        )

    def _sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
        if sort_field == "sheet_sequence":
            sequence = item.get("sheet_sequence")
            normalized = 10**6 if not isinstance(sequence, int) else int(sequence)
            return (normalized, _safe_text(item.get("drawing_number"), ""))
        return (_safe_text(item.get(sort_field), ""),)

    filtered = [
        item
        for item in rows
        if (
            (
                _safe_text(item.get("discipline"), "unknown") in discipline_filter
                if discipline_filter
                else True
            )
            and (
                _safe_text(item.get("sheet_category"), "other") in category_filter
                if category_filter
                else True
            )
            and (
                not query
                or _contains_any(
                    f"{_safe_text(item.get('drawing_number'), '')} {_safe_text(item.get('title'), '')} {_safe_text(item.get('discipline'), '')} {_safe_text(item.get('sheet_category'), '')}",
                    [query],
                )
            )
        )
    ]
    filtered.sort(key=_sort_key, reverse=descending)

    st.dataframe(
        [
            {
                "drawing number": item["drawing_number"],
                "title": item["title"],
                "discipline": item["discipline"],
                "category": item.get("sheet_category", "other"),
                "sequence": item.get("sheet_sequence", "n/a"),
                "drawing refs": len(item.get("referenced_drawings", [])),
                "detail refs": len(item.get("detail_references", [])),
                "view refs": len(item.get("view_references", [])),
                "systems": len(item.get("referenced_systems", [])),
                "specs": len(item.get("referenced_specifications", [])),
                "evidence": len(item.get("referenced_evidence", [])),
            }
            for item in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )

    if not filtered:
        st.info("No drawings match current filters.")
        return

    labels = [f"{item['drawing_number']} · {item['title']}" for item in filtered]
    selected_label = st.selectbox("Select Sheet", options=labels)
    selected = filtered[labels.index(selected_label)]
    _set_context_selection(st, "drawing", selected)

    detail_col, hierarchy_col = st.columns([2.2, 1.8])
    with detail_col:
        st.markdown("#### Sheet Navigation")
        ordered = sorted(
            rows,
            key=lambda item: (
                (
                    10**6
                    if not isinstance(item.get("sheet_sequence"), int)
                    else int(item.get("sheet_sequence", 0))
                ),
                _safe_text(item.get("drawing_number"), ""),
            ),
        )
        index = next(
            (
                pos
                for pos, item in enumerate(ordered)
                if _safe_text(item.get("drawing_number"), "")
                == _safe_text(selected.get("drawing_number"), "")
            ),
            0,
        )
        prev_sheet = ordered[index - 1] if index > 0 else None
        next_sheet = ordered[index + 1] if index + 1 < len(ordered) else None

        nav_rows = [
            {
                "target": "Previous",
                "sheet": _safe_text(
                    prev_sheet.get("drawing_number") if prev_sheet else None,
                    "n/a",
                ),
            },
            {
                "target": "Next",
                "sheet": _safe_text(
                    next_sheet.get("drawing_number") if next_sheet else None,
                    "n/a",
                ),
            },
            {
                "target": "References",
                "sheet": ", ".join(selected.get("referenced_drawings", [])) or "n/a",
            },
        ]
        st.dataframe(nav_rows, use_container_width=True, hide_index=True)

        st.markdown("#### Detail / View / Schedule Links")
        st.dataframe(
            [
                {
                    "type": "Detail",
                    "values": ", ".join(selected.get("detail_references", [])) or "n/a",
                },
                {
                    "type": "View",
                    "values": ", ".join(selected.get("view_references", [])) or "n/a",
                },
                {
                    "type": "Systems",
                    "values": ", ".join(selected.get("referenced_systems", []))
                    or "n/a",
                },
                {
                    "type": "Specifications",
                    "values": ", ".join(selected.get("referenced_specifications", []))
                    or "n/a",
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

    with hierarchy_col:
        st.markdown("#### Discipline Hierarchy")
        discipline_sets = dict(hierarchy.get("disciplines") or {})
        hierarchy_rows = [
            {
                "discipline": discipline,
                "drawing set": drawing_set,
                "sheets": ", ".join(sheets),
            }
            for discipline, sets in discipline_sets.items()
            for drawing_set, sheets in dict(sets or {}).items()
        ]
        if hierarchy_rows:
            st.dataframe(hierarchy_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No hierarchy groups available yet.")


def _render_specifications_page(st: Any, context: dict[str, Any] | None) -> None:
    st.subheader("Specification Workspace")
    objects = _workspace_objects(context)
    rows = list(objects.get("specifications", []))
    if not rows:
        st.info("No specification objects available.")
        return

    head_cols = st.columns([2.5, 1.5, 1.5])
    head_cols[0].caption(
        "Each specification section is a first-class object with linked relationships."
    )
    head_cols[1].caption(
        f"Spec intelligence confidence: {_safe_text(objects.get('specification_intelligence_confidence'), 'n/a')}"
    )
    head_cols[2].caption(
        f"Cross-reference warnings: {len(list(objects.get('specification_cross_reference_warnings') or []))}"
    )

    st.dataframe(
        [
            {
                "division": item["division"],
                "section": item["section"],
                "title": item["title"],
                "discipline": _safe_text(item.get("discipline"), "other"),
                "status": _safe_text(item.get("status"), "indexed"),
                "revision": _safe_text(item.get("revision"), "n/a"),
                "drawings": len(item["referenced_drawings"]),
                "equipment": len(item["referenced_equipment"]),
                "systems": len(item["referenced_systems"]),
                "standards": len(item.get("referenced_standards", [])),
                "requirements": len(item.get("requirement_candidates", [])),
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
                "property": "Discipline",
                "value": _safe_text(selected.get("discipline"), "other"),
            },
            {
                "property": "Status",
                "value": _safe_text(selected.get("status"), "indexed"),
            },
            {
                "property": "Revision",
                "value": _safe_text(selected.get("revision"), "n/a"),
            },
            {
                "property": "Issue Date",
                "value": _safe_text(selected.get("issue_date"), "n/a"),
            },
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
            {
                "relationship": "Standards",
                "objects": ", ".join(selected.get("referenced_standards", [])) or "n/a",
            },
            {
                "relationship": "Manufacturers",
                "objects": ", ".join(selected.get("referenced_manufacturers", []))
                or "n/a",
            },
            {
                "relationship": "Products",
                "objects": ", ".join(selected.get("referenced_products", [])) or "n/a",
            },
            {
                "relationship": "Addenda",
                "objects": ", ".join(selected.get("addendum_references", [])) or "n/a",
            },
        ],
        use_container_width=True,
        hide_index=True,
    )

    requirement_rows = list(selected.get("requirement_candidates") or [])
    st.markdown("Requirement Candidates")
    if requirement_rows:
        st.dataframe(requirement_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No deterministic requirement candidates detected for this section.")

    warning_rows = list(objects.get("specification_cross_reference_warnings") or [])
    st.markdown("Cross-Reference Warnings")
    if warning_rows:
        st.dataframe(warning_rows[:12], use_container_width=True, hide_index=True)
    else:
        st.info("No cross-reference warnings currently detected.")

    nav_cols = st.columns(5)
    if nav_cols[0].button("Open Specification Explorer", use_container_width=True):
        st.session_state["atlas_active_page"] = "Specification Explorer"
        st.rerun()
    if nav_cols[1].button("Go to Drawings", use_container_width=True):
        st.session_state["atlas_active_page"] = "Drawing Explorer"
        st.rerun()
    if nav_cols[2].button("Go to Equipment", use_container_width=True):
        st.session_state["atlas_active_page"] = "Equipment"
        st.rerun()
    if nav_cols[3].button("Go to Systems", use_container_width=True):
        st.session_state["atlas_active_page"] = "Systems"
        st.rerun()
    if nav_cols[4].button("Go to Evidence", use_container_width=True):
        st.session_state["atlas_active_page"] = "Evidence"
        st.rerun()


def _render_specification_explorer_page(
    st: Any, context: dict[str, Any] | None
) -> None:
    st.subheader("Specification Explorer")
    objects = _workspace_objects(context)
    rows = list(objects.get("specifications", []))
    if not rows:
        st.info("No specification objects available.")
        return

    index = dict(objects.get("specification_index") or {})
    warnings = list(objects.get("specification_cross_reference_warnings") or [])

    filter_cols = st.columns([1.5, 1.4, 1.2, 1.2, 1.2, 1.2])
    search = filter_cols[0].text_input(
        "Search",
        key="atlas_spec_explorer_search",
        placeholder="section, title, standards, manufacturers",
    )
    division_filter = filter_cols[1].selectbox(
        "Division",
        options=["All"]
        + sorted({_safe_text(item.get("division"), "n/a") for item in rows}),
    )
    discipline_filter = filter_cols[2].selectbox(
        "Discipline",
        options=["All"]
        + sorted({_safe_text(item.get("discipline"), "other") for item in rows}),
    )
    system_filter = filter_cols[3].selectbox(
        "System",
        options=["All"]
        + sorted(
            {
                _safe_text(system, "")
                for item in rows
                for system in list(item.get("referenced_systems") or [])
                if _safe_text(system, "")
            }
        ),
    )
    status_filter = filter_cols[4].selectbox(
        "Status",
        options=["All"]
        + sorted({_safe_text(item.get("status"), "indexed") for item in rows}),
    )
    revision_filter = filter_cols[5].selectbox(
        "Revision",
        options=["All"]
        + sorted({_safe_text(item.get("revision"), "n/a") for item in rows}),
    )

    sort_cols = st.columns([1.2, 1.2, 1.2])
    sort_field = sort_cols[0].selectbox(
        "Sort by",
        options=["section_sequence", "section", "title", "division", "discipline"],
        key="atlas_spec_explorer_sort",
    )
    descending = (
        sort_cols[1].selectbox(
            "Order",
            options=["Ascending", "Descending"],
            key="atlas_spec_explorer_order",
        )
        == "Descending"
    )
    only_with_warnings = sort_cols[2].checkbox(
        "Only With Warnings",
        key="atlas_spec_explorer_warnings_only",
        value=False,
    )

    warning_sections = {
        token
        for item in warnings
        for token in list(item.get("related_objects") or [])
        if token in {_safe_text(section.get("section"), "") for section in rows}
    }

    filtered = [
        item
        for item in rows
        if (
            (not search or _contains_any(str(item), [search]))
            and (
                division_filter == "All"
                or _safe_text(item.get("division"), "n/a") == division_filter
            )
            and (
                discipline_filter == "All"
                or _safe_text(item.get("discipline"), "other") == discipline_filter
            )
            and (
                system_filter == "All"
                or system_filter in list(item.get("referenced_systems") or [])
            )
            and (
                status_filter == "All"
                or _safe_text(item.get("status"), "indexed") == status_filter
            )
            and (
                revision_filter == "All"
                or _safe_text(item.get("revision"), "n/a") == revision_filter
            )
            and (
                not only_with_warnings
                or _safe_text(item.get("section"), "") in warning_sections
            )
        )
    ]

    def _sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
        if sort_field == "section_sequence":
            return (
                (
                    10**9
                    if not isinstance(item.get("section_sequence"), int)
                    else int(item.get("section_sequence", 0))
                ),
                _safe_text(item.get("section"), ""),
            )
        return (_safe_text(item.get(sort_field), ""),)

    filtered.sort(key=_sort_key, reverse=descending)

    st.dataframe(
        [
            {
                "division": item.get("division"),
                "section": item.get("section"),
                "title": item.get("title"),
                "discipline": item.get("discipline"),
                "system": ", ".join(item.get("referenced_systems", [])) or "n/a",
                "status": item.get("status"),
                "revision": item.get("revision"),
                "requirements": len(item.get("requirement_candidates", [])),
                "warnings": (
                    "yes"
                    if _safe_text(item.get("section"), "") in warning_sections
                    else "no"
                ),
                "confidence": item.get("extraction_confidence"),
            }
            for item in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )

    if not filtered:
        st.info("No sections match current filters.")
        return

    labels = [f"{item['section']} · {item['title']}" for item in filtered]
    selected_label = st.selectbox("Select Section", options=labels)
    selected = filtered[labels.index(selected_label)]
    _set_context_selection(st, "specification", selected)

    detail_col, nav_col = st.columns([2.5, 1.5])
    with detail_col:
        st.markdown("#### Metadata")
        st.dataframe(
            [
                {
                    "field": "Division",
                    "value": _safe_text(selected.get("division"), "n/a"),
                },
                {
                    "field": "Section",
                    "value": _safe_text(selected.get("section"), "n/a"),
                },
                {"field": "Title", "value": _safe_text(selected.get("title"), "n/a")},
                {
                    "field": "Discipline",
                    "value": _safe_text(selected.get("discipline"), "other"),
                },
                {
                    "field": "Status",
                    "value": _safe_text(selected.get("status"), "indexed"),
                },
                {
                    "field": "Revision",
                    "value": _safe_text(selected.get("revision"), "n/a"),
                },
                {
                    "field": "Issue Date",
                    "value": _safe_text(selected.get("issue_date"), "n/a"),
                },
                {
                    "field": "Confidence",
                    "value": _safe_text(selected.get("extraction_confidence"), "n/a"),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Parts and Articles")
        part_rows = list(selected.get("parts") or [])
        article_rows = list(selected.get("articles") or [])
        if part_rows:
            st.dataframe(part_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No Part sections were detected.")
        if article_rows:
            st.dataframe(article_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No article headings were detected.")

        st.markdown("#### Requirement Candidates")
        requirement_rows = list(selected.get("requirement_candidates") or [])
        if requirement_rows:
            st.dataframe(requirement_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No deterministic requirement candidates detected.")

        st.markdown("#### Relationships")
        st.dataframe(
            [
                {
                    "relationship": "Linked Drawings",
                    "values": ", ".join(selected.get("referenced_drawings", []))
                    or "n/a",
                },
                {
                    "relationship": "Linked Equipment",
                    "values": ", ".join(selected.get("referenced_equipment", []))
                    or "n/a",
                },
                {
                    "relationship": "Linked Systems",
                    "values": ", ".join(selected.get("referenced_systems", []))
                    or "n/a",
                },
                {
                    "relationship": "Linked RFIs",
                    "values": ", ".join(selected.get("referenced_rfis", [])) or "n/a",
                },
                {
                    "relationship": "Linked Evidence",
                    "values": ", ".join(selected.get("referenced_evidence", []))
                    or "n/a",
                },
                {
                    "relationship": "Referenced Standards",
                    "values": ", ".join(selected.get("referenced_standards", []))
                    or "n/a",
                },
                {
                    "relationship": "Referenced Addenda",
                    "values": ", ".join(selected.get("addendum_references", []))
                    or "n/a",
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

        insight_result = (
            _build_engineering_intelligence(record=None, context=context)
            if context
            else None
        )
        st.markdown("#### Engineering Insights")
        if insight_result is None:
            st.info("No engineering insights available.")
        else:
            insight_rows = [
                item.to_dict()
                for item in list(getattr(insight_result, "insights", []) or [])
                if _contains_any(str(item), [_safe_text(selected.get("section"), "")])
            ]
            if insight_rows:
                st.dataframe(
                    insight_rows[:8], use_container_width=True, hide_index=True
                )
            else:
                st.info("No engineering insights currently reference this section.")

    with nav_col:
        st.markdown("#### Section Navigation")
        ordered_rows = sorted(
            rows,
            key=lambda item: (
                (
                    10**9
                    if not isinstance(item.get("section_sequence"), int)
                    else int(item.get("section_sequence", 0))
                ),
                _safe_text(item.get("section"), ""),
            ),
        )
        selected_index = next(
            (
                index
                for index, item in enumerate(ordered_rows)
                if _safe_text(item.get("section"), "")
                == _safe_text(selected.get("section"), "")
            ),
            0,
        )
        previous_section = (
            ordered_rows[selected_index - 1] if selected_index > 0 else None
        )
        next_section = (
            ordered_rows[selected_index + 1]
            if selected_index + 1 < len(ordered_rows)
            else None
        )
        st.dataframe(
            [
                {
                    "target": "Previous Section",
                    "value": _safe_text(
                        previous_section.get("section") if previous_section else None,
                        "n/a",
                    ),
                },
                {
                    "target": "Next Section",
                    "value": _safe_text(
                        next_section.get("section") if next_section else None,
                        "n/a",
                    ),
                },
                {
                    "target": "Referenced Drawings",
                    "value": ", ".join(selected.get("referenced_drawings", []))
                    or "n/a",
                },
                {
                    "target": "Referenced Equipment",
                    "value": ", ".join(selected.get("referenced_equipment", []))
                    or "n/a",
                },
                {
                    "target": "Referenced Systems",
                    "value": ", ".join(selected.get("referenced_systems", [])) or "n/a",
                },
                {
                    "target": "Referenced Standards",
                    "value": ", ".join(selected.get("referenced_standards", []))
                    or "n/a",
                },
                {
                    "target": "Referenced Addenda",
                    "value": ", ".join(selected.get("addendum_references", []))
                    or "n/a",
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

        if st.button("Open Drawings", use_container_width=True):
            st.session_state["atlas_active_page"] = "Drawing Explorer"
            st.rerun()
        if st.button("Open Equipment", use_container_width=True):
            st.session_state["atlas_active_page"] = "Equipment"
            st.rerun()
        if st.button("Open Systems", use_container_width=True):
            st.session_state["atlas_active_page"] = "Systems"
            st.rerun()
        if st.button("Open Evidence", use_container_width=True):
            st.session_state["atlas_active_page"] = "Evidence"
            st.rerun()

    st.markdown("#### Cross-Reference Warnings")
    if warnings:
        st.dataframe(warnings, use_container_width=True, hide_index=True)
    else:
        st.info("No cross-reference warnings currently detected.")

    index_summary = {
        "division groups": len(dict(index.get("by_division") or {})),
        "discipline groups": len(dict(index.get("by_discipline") or {})),
        "status groups": len(dict(index.get("by_status") or {})),
        "revision groups": len(dict(index.get("by_revision") or {})),
    }
    st.caption(
        "Specification index summary: "
        + ", ".join(f"{key}={value}" for key, value in index_summary.items())
    )


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


def _render_master_library_explorer_page(
    st: Any,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Master Library Explorer",
        "Canonical engineering catalog for products and systems. This is not procurement, inventory, or ERP.",
    )

    if context is None:
        _render_empty_state(
            st,
            "Master Library Explorer requires a loaded project context.",
        )
        return

    rows = _master_library_rows(context)
    if not rows:
        _render_empty_state(
            st,
            "No products available. Import project files to build deterministic product mappings.",
        )
        return

    categories = sorted(
        {str(item.get("category") or "other") for item in rows if item.get("category")}
    )
    manufacturers = sorted(
        {
            str(item.get("manufacturer") or "Unknown")
            for item in rows
            if item.get("manufacturer")
        }
    )
    statuses = sorted(
        {str(item.get("status") or "unknown") for item in rows if item.get("status")}
    )

    filter_cols = st.columns([2.4, 1.6, 1.6, 1.4])
    search_query = filter_cols[0].text_input(
        "Search Products",
        value=st.session_state.get("atlas_master_library_search", ""),
        key="atlas_master_library_search",
        placeholder="manufacturer, model, alias, family",
    )
    selected_categories = filter_cols[1].multiselect(
        "Category",
        options=categories,
        default=[],
    )
    selected_manufacturers = filter_cols[2].multiselect(
        "Manufacturer",
        options=manufacturers,
        default=[],
    )
    selected_statuses = filter_cols[3].multiselect(
        "Status",
        options=statuses,
        default=[],
    )

    q = search_query.strip().lower()
    filtered = [
        item
        for item in rows
        if (
            (
                not q
                or q
                in " ".join(
                    [
                        str(item.get("product_id") or ""),
                        str(item.get("manufacturer") or ""),
                        str(item.get("model") or ""),
                        str(item.get("description") or ""),
                        str(item.get("family") or ""),
                        " ".join(list(item.get("aliases") or [])),
                    ]
                ).lower()
            )
            and (
                not selected_categories
                or str(item.get("category") or "other") in selected_categories
            )
            and (
                not selected_manufacturers
                or str(item.get("manufacturer") or "Unknown") in selected_manufacturers
            )
            and (
                not selected_statuses
                or str(item.get("status") or "unknown") in selected_statuses
            )
        )
    ]

    summary_cols = st.columns(3)
    with summary_cols[0]:
        st.markdown("#### Category Browser")
        category_counts: dict[str, int] = defaultdict(int)
        for item in filtered:
            category_counts[str(item.get("category") or "other")] += 1
        st.dataframe(
            [
                {"category": key, "products": value}
                for key, value in sorted(category_counts.items())
            ],
            use_container_width=True,
            hide_index=True,
        )
    with summary_cols[1]:
        st.markdown("#### Manufacturer Browser")
        manufacturer_counts: dict[str, int] = defaultdict(int)
        for item in filtered:
            manufacturer_counts[str(item.get("manufacturer") or "Unknown")] += 1
        st.dataframe(
            [
                {"manufacturer": key, "products": value}
                for key, value in sorted(manufacturer_counts.items())
            ],
            use_container_width=True,
            hide_index=True,
        )
    with summary_cols[2]:
        st.markdown("#### Status")
        status_counts: dict[str, int] = defaultdict(int)
        for item in filtered:
            status_counts[str(item.get("status") or "unknown")] += 1
        st.dataframe(
            [
                {"status": key, "products": value}
                for key, value in sorted(status_counts.items())
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("#### Canonical Product Model")
    st.dataframe(
        [
            {
                "manufacturer": item.get("manufacturer"),
                "model": item.get("model"),
                "normalized_model": item.get("normalized_model"),
                "description": item.get("description"),
                "category": item.get("category"),
                "family": item.get("family"),
                "status": item.get("status"),
                "aliases": len(list(item.get("aliases") or [])),
                "relationships": len(list(item.get("related_products") or [])),
                "confidence": item.get("confidence"),
            }
            for item in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )

    if not filtered:
        _render_empty_state(st, "No master library products match the current filters.")
        return

    labels = [
        (
            f"{_safe_text(item.get('manufacturer'), 'Unknown')}"
            f" · {_safe_text(item.get('model'), 'Unknown')}"
            f" · {_safe_text(item.get('category'), 'other')}"
        )
        for item in filtered
    ]
    selected_label = st.selectbox("Select Master Product", options=labels)
    selected = filtered[labels.index(selected_label)]
    _set_context_selection(st, "master_product", selected)

    detail_cols = st.columns([2.5, 1.5])
    with detail_cols[0]:
        st.markdown("#### Product Detail")
        st.dataframe(
            [
                {
                    "field": "Product ID",
                    "value": _safe_text(selected.get("product_id"), "n/a"),
                },
                {
                    "field": "Manufacturer",
                    "value": _safe_text(selected.get("manufacturer"), "n/a"),
                },
                {"field": "Model", "value": _safe_text(selected.get("model"), "n/a")},
                {
                    "field": "Normalized Model",
                    "value": _safe_text(selected.get("normalized_model"), "n/a"),
                },
                {
                    "field": "Description",
                    "value": _safe_text(selected.get("description"), "n/a"),
                },
                {
                    "field": "Category",
                    "value": _safe_text(selected.get("category"), "n/a"),
                },
                {"field": "Family", "value": _safe_text(selected.get("family"), "n/a")},
                {"field": "Status", "value": _safe_text(selected.get("status"), "n/a")},
                {
                    "field": "Confidence",
                    "value": _safe_text(selected.get("confidence"), "n/a"),
                },
                {
                    "field": "Created",
                    "value": _safe_text(selected.get("created_at"), "n/a"),
                },
                {
                    "field": "Updated",
                    "value": _safe_text(selected.get("updated_at"), "n/a"),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("#### Aliases")
        aliases = list(selected.get("aliases") or [])
        st.dataframe(
            [{"alias": str(item)} for item in aliases],
            use_container_width=True,
            hide_index=True,
        )

    with detail_cols[1]:
        st.markdown("#### Relationship Browser")
        relationships = list(selected.get("related_products") or [])
        if relationships:
            st.dataframe(
                [
                    {
                        "relationship": _safe_text(
                            item.get("relationship_type"), "n/a"
                        ),
                        "target": _safe_text(item.get("target_product_id"), "n/a"),
                        "confidence": _safe_text(item.get("confidence"), "n/a"),
                    }
                    for item in relationships
                ],
                use_container_width=True,
                hide_index=True,
            )
            for item in relationships[:8]:
                target = _safe_text(item.get("target_product_id"), "")
                if st.button(
                    f"Open {target}",
                    key=f"atlas_master_library_target_{_safe_text(selected.get('product_id'), 'product')}_{target}",
                    use_container_width=True,
                ):
                    _open_linked_object(st, target)
        else:
            st.info("No related products mapped yet.")

    st.markdown("#### Alias Resolution")
    resolver_cols = st.columns([2.1, 2.1, 3.8])
    test_manufacturer = resolver_cols[0].text_input(
        "Manufacturer Input",
        value=_safe_text(selected.get("manufacturer"), ""),
        key="atlas_master_library_resolve_manufacturer",
    )
    test_model = resolver_cols[1].text_input(
        "Model/Alias Input",
        value=_safe_text(selected.get("model"), ""),
        key="atlas_master_library_resolve_model",
    )
    test_description = resolver_cols[2].text_input(
        "Description Input",
        value=_safe_text(selected.get("description"), ""),
        key="atlas_master_library_resolve_description",
    )

    if st.button("Resolve Product", key="atlas_master_library_resolve_button"):
        service = MasterLibraryService()
        service.import_workspace_equipment(
            list(_workspace_objects(context).get("equipment") or [])
        )
        resolution = service.resolve_product(
            manufacturer=test_manufacturer,
            model=test_model,
            description=test_description,
        )
        matched = dict(resolution.get("matched") or {})
        st.dataframe(
            [
                {
                    "matched product": _safe_text(
                        matched.get("product_id"), "No match"
                    ),
                    "manufacturer": _safe_text(matched.get("manufacturer"), "n/a"),
                    "model": _safe_text(matched.get("model"), "n/a"),
                    "confidence": _safe_text(resolution.get("confidence"), "0.0"),
                    "trace": " | ".join(list(resolution.get("trace") or [])),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )


def _render_relationship_explorer_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    st.subheader("Relationship Inspector")
    graph = _build_knowledge_graph(record, context)
    nodes = list(graph.get("nodes", []))
    if not nodes:
        st.info("No relationship graph nodes are available yet.")
        return

    intelligence = _build_engineering_intelligence(record, context)
    insights = list(getattr(intelligence, "insights", []) or []) if intelligence else []

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

    all_relationships = incoming + outgoing
    st.markdown("#### Relationship Details")
    if not all_relationships:
        st.info("No relationship rows available for this object.")
    else:
        relation_labels = [
            (
                f"{_safe_text(edge.get('relationship'), 'link')} · "
                f"{_node_label(graph, _safe_text(edge.get('source'), 'n/a'))} -> "
                f"{_node_label(graph, _safe_text(edge.get('target'), 'n/a'))}"
            )
            for edge in all_relationships
        ]
        selected_relation_label = st.selectbox(
            "Select Relationship",
            options=relation_labels,
            key="atlas_relationship_inspector_selection",
        )
        selected_edge = all_relationships[
            relation_labels.index(selected_relation_label)
        ]

        source_node = _node_by_id(graph, _safe_text(selected_edge.get("source"), ""))
        target_node = _node_by_id(graph, _safe_text(selected_edge.get("target"), ""))
        related_insight_rows = [
            item.to_dict() if hasattr(item, "to_dict") else dict(item)
            for item in insights
            if _contains_any(
                str(item),
                [
                    _safe_text(selected_edge.get("source"), ""),
                    _safe_text(selected_edge.get("target"), ""),
                    _safe_text(source_node.get("label") if source_node else None, ""),
                    _safe_text(target_node.get("label") if target_node else None, ""),
                ],
            )
        ]

        st.dataframe(
            [
                {
                    "relationship type": _safe_text(
                        selected_edge.get("relationship"), "n/a"
                    ),
                    "source": _node_label(
                        graph, _safe_text(selected_edge.get("source"), "n/a")
                    ),
                    "target": _node_label(
                        graph, _safe_text(selected_edge.get("target"), "n/a")
                    ),
                    "confidence": _safe_text(selected_edge.get("confidence"), "n/a"),
                    "supporting evidence": _safe_text(
                        selected_edge.get("source_evidence"), "n/a"
                    ),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("Connected Objects")
        st.dataframe(
            [
                {
                    "object": _node_label(
                        graph, _safe_text(selected_edge.get("source"), "n/a")
                    ),
                    "type": _safe_text(
                        source_node.get("type") if source_node else None, "n/a"
                    ),
                },
                {
                    "object": _node_label(
                        graph, _safe_text(selected_edge.get("target"), "n/a")
                    ),
                    "type": _safe_text(
                        target_node.get("type") if target_node else None, "n/a"
                    ),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("Related Engineering Insights")
        if related_insight_rows:
            st.dataframe(
                related_insight_rows[:8], use_container_width=True, hide_index=True
            )
        else:
            st.info("No engineering insights reference this relationship.")

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
    st.subheader("Engineering Activity History")
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
    if kind == "resolved":
        node_id = f"resolved:{_safe_text(data.get('object_type'), '')}:{_safe_text(data.get('object_id'), '')}"
        return _node_by_id(graph, node_id)
    if kind == "rfi":
        rfi_id = _safe_text(data.get("rfi_id"), _safe_text(data.get("title"), "rfi"))
        node_id = f"rfi:{rfi_id}"
        return _node_by_id(graph, node_id)
    if kind == "resolver_conflict":
        node_id = f"resolver_conflict:{_safe_text(data.get('conflict_id'), '')}"
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

    st.markdown("History")
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
    coordination_objects = _workspace_objects(context)
    coordination_summary = dict(coordination_objects.get("coordination_summary") or {})
    coordination_findings = list(
        coordination_objects.get("coordination_findings") or []
    )

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
        st.markdown("Coordination Summary")
        st.dataframe(
            [
                {
                    "total findings": coordination_summary.get("total_findings", 0),
                    "conflicts": coordination_summary.get("conflict_count", 0),
                    "gaps": coordination_summary.get("gap_count", 0),
                    "agreements": coordination_summary.get("agreement_count", 0),
                    "confidence": _safe_text(
                        coordination_objects.get("coordination_confidence"),
                        "n/a",
                    ),
                }
            ],
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

        high_priority_coordination = [
            item
            for item in coordination_findings
            if _safe_text(item.get("severity"), "") in {"critical", "high"}
        ]
        st.markdown("Coordination Advisory")
        if high_priority_coordination:
            st.dataframe(
                [
                    {
                        "severity": _safe_text(item.get("severity"), "n/a"),
                        "title": _safe_text(item.get("title"), "n/a"),
                        "action": _safe_text(item.get("recommended_action"), "n/a"),
                    }
                    for item in high_priority_coordination[:6]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No critical coordination advisories for the current brief.")
        return

    if page == "RFI Candidates":
        rows = (
            _to_rows(list(getattr(review, "rfi_candidates", []) or []))
            if review
            else []
        )
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
            labels = [
                _safe_text(item.get("title"), _safe_text(item.get("rfi_id"), "RFI"))
                for item in rows
            ]
            selected_label = st.selectbox("Select RFI Object", options=labels)
            selected = rows[labels.index(selected_label)]
            _set_context_selection(st, "rfi", selected)
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


def _render_reports_page(
    st: Any,
    page: str,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        page,
        "Estimator-facing summary outputs and export navigation.",
    )
    if page == "Reports":
        objects = _workspace_objects(context)
        summary = dict(objects.get("coordination_summary") or {})
        findings = list(objects.get("coordination_findings") or [])
        st.caption(
            "Estimator-facing report summary. Atlas coordination findings are advisory and traceable."
        )
        st.dataframe(
            [
                {
                    "coordination findings": summary.get("total_findings", 0),
                    "conflicts": summary.get("conflict_count", 0),
                    "gaps": summary.get("gap_count", 0),
                    "agreements": summary.get("agreement_count", 0),
                    "confidence": _safe_text(
                        objects.get("coordination_confidence"),
                        "n/a",
                    ),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.dataframe(
            [
                {
                    "severity": _safe_text(item.get("severity"), "n/a"),
                    "category": _safe_text(item.get("category"), "n/a"),
                    "title": _safe_text(item.get("title"), "n/a"),
                    "recommended action": _safe_text(
                        item.get("recommended_action"),
                        "n/a",
                    ),
                }
                for item in findings[:12]
            ],
            use_container_width=True,
            hide_index=True,
        )
        nav_cols = st.columns(3)
        if nav_cols[0].button("Open Coordination Review", use_container_width=True):
            st.session_state["atlas_active_page"] = "Coordination Review"
            st.rerun()
        if nav_cols[1].button("Open Engineering Workbench", use_container_width=True):
            st.session_state["atlas_active_page"] = "Engineering Workbench"
            st.rerun()
        if nav_cols[2].button("Open Estimator Brief", use_container_width=True):
            st.session_state["atlas_active_page"] = "Estimator Brief"
            st.rerun()
    else:
        _render_empty_state(
            st,
            "Exports module scaffolded. Use Reports, Estimator Brief, or Evidence for current review outputs.",
        )
        nav_cols = st.columns(3)
        if nav_cols[0].button("Open Reports", use_container_width=True):
            st.session_state["atlas_active_page"] = "Reports"
            st.rerun()
        if nav_cols[1].button("Open Evidence", use_container_width=True):
            st.session_state["atlas_active_page"] = "Evidence"
            st.rerun()
        if nav_cols[2].button("Open Project Files", use_container_width=True):
            st.session_state["atlas_active_page"] = "Project Files"
            st.rerun()


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

    project_name = _safe_text(
        context.get("sample_project_name") if context else None,
        "Project",
    )
    current_page = _safe_text(
        st.session_state.get("atlas_active_page"),
        "Mission Control",
    )
    st.dataframe(
        [
            {"field": "Current Project", "value": project_name},
            {"field": "Current Page", "value": current_page},
        ],
        use_container_width=True,
        hide_index=True,
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
            "evidence_ids",
            "conflict_ids",
            "rules_applied",
            "potential_rfis",
        ]
        warning_keys = ["warnings"]

        resolved_values = dict(object_data.get("canonical_values") or {})
        if resolved_values:
            st.markdown("Resolved Values")
            st.dataframe(
                [
                    {"field": key.replace("_", " "), "value": _safe_text(value, "n/a")}
                    for key, value in resolved_values.items()
                ],
                use_container_width=True,
                hide_index=True,
            )

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

    if kind == "resolved":
        _render_object_context(
            f"Resolved {_safe_text(data.get('object_type'), 'Object')}",
            data,
            [
                ("Engineering Resolver", "Go to Resolver"),
                ("Engineering Workbench", "Open Workbench"),
                ("Equipment", "Go to Equipment"),
                ("Systems", "Go to Systems"),
                ("Specifications", "Go to Specifications"),
            ],
        )
        return

    if kind == "resolver_conflict":
        _render_object_context(
            "Resolver Conflict",
            data,
            [
                ("Resolver Conflict Center", "Open Conflict Center"),
                ("Engineering Workbench", "Open Workbench"),
                ("Engineering Resolver", "Open Resolver"),
            ],
        )
        return

    if kind == "rfi":
        _render_object_context(
            "RFI Candidate",
            data,
            [
                ("Engineering Workbench", "Open Workbench"),
                ("RFI Candidates", "Open RFIs"),
                ("Evidence", "Open Evidence"),
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

    if kind == "notebook_entry":
        st.markdown("#### Notebook Entry")
        st.dataframe(
            [
                {"field": "Entry ID", "value": _safe_text(data.get("entry_id"), "n/a")},
                {
                    "field": "Created",
                    "value": _safe_text(data.get("created_at"), "n/a"),
                },
                {"field": "Author", "value": _safe_text(data.get("author"), "n/a")},
                {"field": "Type", "value": _safe_text(data.get("entry_type"), "n/a")},
                {"field": "Priority", "value": _safe_text(data.get("priority"), "n/a")},
                {"field": "Status", "value": _safe_text(data.get("status"), "n/a")},
                {"field": "Title", "value": _safe_text(data.get("title"), "n/a")},
                {"field": "Body", "value": _safe_text(data.get("body"), "n/a")},
                {
                    "field": "Tags",
                    "value": ", ".join(list(data.get("tags") or [])) or "n/a",
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

        linked = list(data.get("related_objects") or [])
        if linked:
            st.markdown("Linked Objects")
            for ref in linked[:12]:
                if st.button(
                    f"Open {_safe_text(ref, 'object')}",
                    key=f"atlas_ctx_notebook_open_{_safe_text(data.get('entry_id'), 'entry')}_{_safe_text(ref, 'ref')}",
                    use_container_width=True,
                ):
                    _open_linked_object(st, ref)

        nav_cols = st.columns(2)
        if nav_cols[0].button("Open Notebook", use_container_width=True):
            st.session_state["atlas_active_page"] = "Engineering Notebook"
            st.rerun()
        if nav_cols[1].button("Open History", use_container_width=True):
            st.session_state["atlas_active_page"] = "History"
            st.rerun()
        return

    if kind == "master_product":
        st.markdown("#### Master Product")
        st.dataframe(
            [
                {
                    "field": "Product ID",
                    "value": _safe_text(data.get("product_id"), "n/a"),
                },
                {
                    "field": "Manufacturer",
                    "value": _safe_text(data.get("manufacturer"), "n/a"),
                },
                {"field": "Model", "value": _safe_text(data.get("model"), "n/a")},
                {
                    "field": "Normalized Model",
                    "value": _safe_text(data.get("normalized_model"), "n/a"),
                },
                {
                    "field": "Description",
                    "value": _safe_text(data.get("description"), "n/a"),
                },
                {
                    "field": "Category",
                    "value": _safe_text(data.get("category"), "n/a"),
                },
                {"field": "Family", "value": _safe_text(data.get("family"), "n/a")},
                {"field": "Status", "value": _safe_text(data.get("status"), "n/a")},
                {
                    "field": "Confidence",
                    "value": _safe_text(data.get("confidence"), "n/a"),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

        aliases = list(data.get("aliases") or [])
        if aliases:
            st.markdown("Aliases")
            st.dataframe(
                [{"alias": str(item)} for item in aliases],
                use_container_width=True,
                hide_index=True,
            )

        relationships = list(data.get("related_products") or [])
        if relationships:
            st.markdown("Relationships")
            st.dataframe(
                [
                    {
                        "relationship": _safe_text(
                            item.get("relationship_type"),
                            "n/a",
                        ),
                        "target": _safe_text(item.get("target_product_id"), "n/a"),
                    }
                    for item in relationships
                ],
                use_container_width=True,
                hide_index=True,
            )

        nav_cols = st.columns(2)
        if nav_cols[0].button("Open Master Library", use_container_width=True):
            st.session_state["atlas_active_page"] = "Master Library Explorer"
            st.rerun()
        if nav_cols[1].button("Open Equipment", use_container_width=True):
            st.session_state["atlas_active_page"] = "Equipment"
            st.rerun()
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
    mission_control_payload: dict[str, Any] | None = None,
) -> None:
    page = st.session_state.get("atlas_active_page", "Mission Control")

    if page == "Mission Control":
        _render_home_page(
            st,
            workspace_service,
            record,
            context,
            mission_control_payload,
        )
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
    elif page == "Engineering Workbench":
        _render_engineering_workbench_page(st, record, context)
    elif page == "Engineering Notebook":
        _render_engineering_notebook_page(st, record, context)
    elif page == "Master Library Explorer":
        _render_master_library_explorer_page(st, context)
    elif page == "Executive Summary":
        _render_executive_summary_page(st, context)
    elif page == "Project Files":
        _render_project_files_page(st, workspace_service, record, context)
    elif page == "Drawings":
        _render_drawings_page(st, context)
    elif page == "Drawing Explorer":
        _render_drawing_explorer_page(st, context)
    elif page == "Specifications":
        _render_specifications_page(st, context)
    elif page == "Specification Explorer":
        _render_specification_explorer_page(st, context)
    elif page == "Equipment":
        _render_equipment_page(st, context)
    elif page == "Systems":
        _render_systems_page(st, record, context)
    elif page == "Engineering Resolver":
        _render_engineering_resolver_page(st, record, context)
    elif page == "Resolver Conflict Center":
        _render_resolver_conflict_center_page(st, record, context)
    elif page == "Engineering Intelligence":
        _render_engineering_intelligence_page(st, record, context)
    elif page == "Coordination Review":
        _render_coordination_review_page(st, context)
    elif page == "Relationship Explorer":
        _render_relationship_explorer_page(st, record, context)
    elif page == "Relationship Visualization":
        _render_relationship_visualization_page(st, record, context)
    elif page == "History":
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
        _render_reports_page(st, page, context)
    elif page in SETTINGS_PAGES:
        _render_settings_page(st, page, workspace_service, record)


def _render_mission_control_panels(
    st: Any,
    mission_control_payload: dict[str, Any] | None,
) -> None:
    payload = mission_control_payload or {}
    actions = list(payload.get("actions") or [])
    signals = list(payload.get("signals") or [])
    timeline = list(payload.get("timeline") or [])
    pending_timeline = list(payload.get("pending_timeline") or [])

    st.markdown("### Action Center")
    if actions:
        st.dataframe(
            [
                {
                    "Priority": item.get("priority"),
                    "Action": item.get("title"),
                    "Project": item.get("project"),
                }
                for item in actions[:5]
            ],
            use_container_width=True,
            hide_index=True,
        )
        if st.button("View all action items", key="atlas_side_view_actions"):
            st.session_state["atlas_active_page"] = "Engineering Workbench"
            st.rerun()
    else:
        st.caption("No high-priority actions detected.")

    st.markdown("### Recent Activity")
    if timeline:
        st.dataframe(
            [
                {
                    "Event": item.get("event"),
                    "Status": item.get("status"),
                    "Timestamp": item.get("timestamp"),
                }
                for item in timeline[:8]
            ],
            use_container_width=True,
            hide_index=True,
        )
        if st.button("View full activity", key="atlas_side_view_activity"):
            st.session_state["atlas_active_page"] = "History"
            st.rerun()
    else:
        st.caption("No activity yet.")

    st.markdown("### Upcoming Timeline")
    if pending_timeline:
        st.dataframe(
            [
                {
                    "Event": item.get("event"),
                    "Status": item.get("status"),
                    "Details": item.get("details"),
                }
                for item in pending_timeline[:5]
            ],
            use_container_width=True,
            hide_index=True,
        )
        if st.button("View full timeline", key="atlas_side_view_timeline"):
            st.session_state["atlas_active_page"] = "History"
            st.rerun()
    else:
        st.caption("No pending timeline items.")

    st.markdown("### Projects Requiring Attention")
    attention = [
        item for item in signals if item.get("status") in {"Blocked", "Needs Attention"}
    ]
    if attention:
        st.dataframe(
            [
                {
                    "Project": item.get("project"),
                    "Status": item.get("status"),
                    "Reason": item.get("reason"),
                }
                for item in attention[:5]
            ],
            use_container_width=True,
            hide_index=True,
        )
        if st.button("View all projects", key="atlas_side_view_projects"):
            st.session_state["atlas_active_page"] = "Projects"
            st.rerun()
    else:
        st.caption("No blocked projects in recent workspaces.")


def _render_shell(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_header(st, workspace_service, record, context)
    _sync_notebook_state_to_context(st, context)

    current_page = st.session_state.get("atlas_active_page", "Mission Control")
    mission_control_payload = None
    if current_page == "Mission Control":
        mission_control_payload = _build_mission_control_payload(
            workspace_service,
            record,
            context,
        )

    st.markdown(
        f"<div class='atlas-breadcrumb'>{_breadcrumb(record, current_page)}</div>",
        unsafe_allow_html=True,
    )

    layout_mode = st.session_state.get("atlas_layout_mode", "Desktop")

    if layout_mode == "Desktop":
        if current_page == "Mission Control":
            nav_col, main_col = st.columns([2.4, 7.6])
            with nav_col:
                _nav_buttons(st, st, "desktop")
            with main_col:
                _render_main_content(
                    st,
                    workspace_service,
                    record,
                    context,
                    mission_control_payload,
                )
        else:
            nav_col, main_col, context_col = st.columns([2.3, 6.4, 2.3])
            with nav_col:
                _nav_buttons(st, st, "desktop")
            with main_col:
                _render_main_content(
                    st,
                    workspace_service,
                    record,
                    context,
                    mission_control_payload,
                )
            with context_col:
                _render_context_panel(st, context)

    elif layout_mode == "Tablet":
        nav_popover = st.popover("Navigation")
        _nav_buttons(st, nav_popover, "tablet")
        _render_main_content(
            st,
            workspace_service,
            record,
            context,
            mission_control_payload,
        )
        if current_page != "Mission Control":
            st.markdown("---")
            _render_context_panel(st, context)

    else:
        nav_drawer = st.popover("Open Navigation")
        _nav_buttons(st, nav_drawer, "mobile")
        _render_main_content(
            st,
            workspace_service,
            record,
            context,
            mission_control_payload,
        )
        if current_page != "Mission Control":
            st.markdown("---")
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
        st.session_state["atlas_active_page"] = "Mission Control"

    _render_shell(st, workspace_service, record, context)
    workspace_service.save_workspace_state(
        record.workspace_id,
        _workspace_state_snapshot(st),
    )


if __name__ == "__main__":
    main()

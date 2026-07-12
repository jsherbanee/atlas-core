"""Atlas Workspace v1.5 project-centric shell for Phase 2 review outputs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import platform
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
from atlas_core.services.master_library import (
    CommercialProductService,
    MasterLibraryService,
)
from atlas_core.services.master_library.commercial_product_service import (
    ALLOWED_PURCHASING_CHANNELS,
)
from atlas_core.services.product_resolution_service import ProductResolutionService
from atlas_core.services.bom_review_service import BomReviewService
from atlas_core.services.pricing_service import PricingService
from atlas_core.services.sales_design_review_service import SalesDesignReviewService
from atlas_core.services.scope_risk_review_service import ScopeRiskReviewService
from atlas_core.services.estimate_service import DeterministicEstimateService
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
from atlas_core.services.cost_engine_service import DeterministicCostEngine
from atlas_core.registry import ManufacturerRegistry
from atlas_core.sample_data.manufacturer_seed import build_manufacturer_seed_data
from atlas_core.sample_data.vendor_seed import build_vendor_seed_data
from atlas_core.services.runtime_workspace import ensure_runtime_workspace_root

PROJECT_MANAGER_PAGES = [
    "Mission Control",
    "Projects",
    "Pinned Projects",
    "Reference Projects",
    "Recent Projects",
    "Create New Project",
    "Open Existing Project",
]

WORKFLOW_PAGES = [
    "Project Summary",
    "Documents",
    "Price List Library",
    "Import History",
    "BOM Review",
    "Scope & Risk",
    "Engineering Review",
    "Product Resolution",
    "Reports",
]

NAV_DROPDOWN_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Workflow",
        [
            ("Project Summary", "Project Summary"),
            ("Documents", "Documents"),
            ("Price List Library", "Price List Library"),
            ("Import History", "Import History"),
            ("BOM Review", "BOM Review"),
            ("Scope & Risk", "Scope & Risk"),
            ("Engineering Review", "Engineering Review"),
            ("Product Resolution", "Product Resolution"),
            ("Reports", "Reports"),
        ],
    ),
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
        "Advanced",
        [
            ("Engineering Workbench", "Engineering Workbench"),
            ("Engineering Notebook", "Engineering Notebook"),
            ("Drawings", "Drawings"),
            ("Drawing Explorer", "Drawing Explorer"),
            ("Specifications", "Specifications"),
            ("Specification Explorer", "Specification Explorer"),
            ("Equipment", "Equipment"),
            ("Systems", "Systems"),
            ("Engineering Resolver", "Engineering Resolver"),
            ("Resolver Conflict Center", "Resolver Conflict Center"),
            ("Engineering Intelligence", "Engineering Intelligence"),
            ("Coordination Review", "Coordination Review"),
            ("Knowledge Graph", "Relationship Visualization"),
            ("Relationships", "Relationship Explorer"),
            ("Evidence", "Evidence"),
            ("History", "History"),
            ("Master Library", "Master Library Explorer"),
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
    + WORKFLOW_PAGES
    + PROJECT_PAGES
    + BID_INTELLIGENCE_PAGES
    + REPORT_PAGES
    + SETTINGS_PAGES
    + [
        "Knowledge",
        "Administration",
        "Product Resolution",
        "Estimate",
        "Notebook",
        "Timeline",
        "Relationships",
        "Project Metadata",
        "Repository",
        "Workspace Settings",
        "Schedules",
        "Addenda",
    ]
)

APPLICATION_NAV_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Application Workspace",
        [
            ("Mission Control", "Mission Control"),
            ("Projects", "Projects"),
            ("Knowledge", "Knowledge"),
            ("Reports", "Reports"),
            ("Administration", "Administration"),
        ],
    )
]

PROJECT_NAV_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Project",
        [
            ("Overview", "Overview"),
            ("Documents", "Documents"),
            ("Price List Library", "Price List Library"),
            ("Import History", "Import History"),
            ("BOM Review", "BOM Review"),
            ("Scope & Risk", "Scope & Risk"),
            ("Engineering Review", "Engineering Review"),
            ("Product Resolution", "Product Resolution"),
            ("Estimate", "Estimate"),
            ("Notebook", "Notebook"),
            ("Reports", "Reports"),
        ],
    ),
    (
        "Project Details",
        [
            ("Drawings", "Drawings"),
            ("Specifications", "Specifications"),
            ("Equipment", "Equipment"),
            ("Schedules", "Schedules"),
            ("Addenda", "Addenda"),
            ("Evidence", "Evidence"),
            ("Timeline", "Timeline"),
            ("Relationships", "Relationships"),
        ],
    ),
    (
        "Project Settings",
        [
            ("Project Metadata", "Project Metadata"),
            ("Repository", "Repository"),
            ("Workspace Settings", "Workspace Settings"),
        ],
    ),
    (
        "Future Lifecycle (Disabled)",
        [(item, item) for item in DISABLED_LIFECYCLE_PAGES],
    ),
]

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


@dataclass
class ProjectContextHeader:
    project_name: str
    customer: str
    lifecycle_stage: str
    current_status: str
    last_analysis: str
    confidence: str
    recommended_next_action: str


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
            --atlas-primary: #2563eb;
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
        .atlas-primary-action {
            border: 1px solid #bfdbfe;
            background: #eff6ff;
            border-radius: 10px;
            padding: 0.7rem 0.85rem;
            margin: 0.45rem 0 0.6rem 0;
        }
        .atlas-primary-action strong {
            display: block;
            color: #1e3a8a;
            font-size: 0.78rem;
            margin-bottom: 0.2rem;
            letter-spacing: 0.01rem;
        }
        .atlas-project-header {
            position: sticky;
            top: 0;
            z-index: 10;
            border: 1px solid #dbe3ee;
            background: #f8fafc;
            border-radius: 12px;
            padding: 0.7rem 0.85rem;
            margin: 0.35rem 0 0.55rem 0;
        }
        .atlas-project-name {
            font-size: 1.2rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.05rem;
        }
        .atlas-project-customer {
            color: #334155;
            font-size: 0.88rem;
            margin-bottom: 0.3rem;
        }
        .atlas-project-meta {
            color: #475569;
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _status_chip(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {
        "healthy",
        "ready",
        "high",
        "extracted",
        "green",
        "complete",
    }:
        return "🟢 " + value
    if normalized in {"processing", "in progress", "blue"}:
        return "🔵 " + value
    if normalized in {"needs review", "warning", "partial", "amber"}:
        return "🟠 " + value
    if normalized in {"critical", "failed", "red", "blocked"}:
        return "🔴 " + value
    if normalized in {"requires_ocr", "unknown", "inactive"}:
        return "🟠 " + value
    if normalized in {"not started"}:
        return "⚪ " + value
    return "⚪ " + value


def _estimate_resolution_chip(value: str) -> str:
    normalized = _safe_text(value, "").replace("_", " ").lower()
    if normalized == "exact product":
        return "🟢 Exact Product"
    if normalized == "approved substitute":
        return "🟢 Approved Substitute"
    if normalized == "preferred alternate":
        return "🟠 Preferred Alternate"
    if normalized == "generic allowance":
        return "🟠 Generic Allowance"
    if normalized == "unknown product":
        return "🔴 Unknown Product"
    return "⚪ " + _safe_text(value, "Unknown")


def _estimate_cost_status_chip(value: str) -> str:
    normalized = _safe_text(value, "").replace("_", " ").lower()
    if normalized == "verified":
        return "🟢 Verified"
    if normalized == "quoted":
        return "🟢 Quoted"
    if normalized == "estimated":
        return "🟠 Estimated"
    if normalized == "no pricing":
        return "⚪ No Pricing"
    if normalized == "expired":
        return "🔴 Expired"
    if normalized == "unavailable":
        return "🔴 Unavailable"
    return "⚪ " + _safe_text(value, "Unknown")


def _product_resolution_badge(value: str) -> str:
    normalized = _safe_text(value, "").replace("_", " ").lower()
    if normalized in {"exact product", "approved substitute"}:
        return "🟢 " + normalized.title()
    if normalized == "preferred alternate":
        return "🔵 Preferred Alternate"
    if normalized == "generic allowance":
        return "🟠 Generic Allowance"
    if normalized == "unknown product":
        return "🔴 Unknown Product"
    return "⚪ " + _safe_text(value, "Unknown")


def _open_estimate_navigation_target(
    st: Any,
    *,
    target_kind: str,
    target_value: str,
) -> None:
    value = _safe_text(target_value, "")
    if not value:
        return

    if target_kind == "equipment":
        st.session_state["atlas_active_page"] = "Equipment"
        _set_context_selection(st, "equipment", {"equipment_id": value})
    elif target_kind == "specification":
        st.session_state["atlas_active_page"] = "Specifications"
        _set_context_selection(st, "specification", {"section": value})
    elif target_kind == "drawing":
        st.session_state["atlas_active_page"] = "Drawings"
        _set_context_selection(st, "drawing", {"drawing_number": value})
    elif target_kind == "relationships":
        st.session_state["atlas_active_page"] = "Relationships"
        _set_context_selection(st, "equipment", {"equipment_id": value})
    elif target_kind == "evidence":
        st.session_state["atlas_active_page"] = "Evidence"
        _set_context_selection(st, "evidence", {"source_file": value, "page": "n/a"})
    else:
        return
    st.rerun()


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


def _render_guided_empty_state(
    st: Any,
    *,
    why_empty: str,
    action_to_populate: str,
    next_location: str,
) -> None:
    st.info(
        f"What is missing: {why_empty}\n\n"
        f"Why it matters: this view cannot provide reliable review context until data exists.\n\n"
        f"Action to populate: {action_to_populate}\n\n"
        f"Next: {next_location}"
    )


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
    return datetime.now(UTC).replace(microsecond=0).isoformat()


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


def _keyword_count(
    rows: list[dict[str, Any]],
    keywords: list[str],
    fields: list[str],
) -> int:
    count = 0
    for row in rows:
        haystack = " ".join(_safe_text(row.get(field), "") for field in fields).lower()
        if any(keyword in haystack for keyword in keywords):
            count += 1
    return count


def _review_flags_state(st: Any) -> dict[str, Any]:
    state = st.session_state.get("atlas_review_flags")
    if isinstance(state, dict):
        return state
    state = {}
    st.session_state["atlas_review_flags"] = state
    return state


def _set_review_flag(st: Any, key: str, value: Any) -> None:
    flags = dict(_review_flags_state(st))
    flags[key] = value
    st.session_state["atlas_review_flags"] = flags


def _review_step_definitions() -> list[dict[str, str]]:
    return [
        {
            "key": "documents",
            "step": "Review Documents",
            "page": "Documents",
            "why": "Document processing quality determines all downstream review confidence.",
        },
        {
            "key": "bom",
            "step": "Review BOM",
            "page": "BOM Review",
            "why": "BOM completeness and conflicts drive coverage and scope certainty.",
        },
        {
            "key": "scope_risk",
            "step": "Review Scope and Risk",
            "page": "Scope & Risk",
            "why": "Scope gaps and ownership ambiguity are primary estimate and execution risks.",
        },
        {
            "key": "engineering",
            "step": "Review Engineering Findings",
            "page": "Engineering Review",
            "why": "Engineering findings consolidate major concerns and required clarifications.",
        },
        {
            "key": "estimate",
            "step": "Review Estimate Coverage",
            "page": "Estimate",
            "why": "Coverage validates whether pricing/labor assumptions are usable for planning.",
        },
        {
            "key": "summary_report",
            "step": "Generate Summary Report",
            "page": "Reports",
            "why": "A concise project summary aligns reviewers on decisions, risks, and limitations.",
        },
    ]


def _review_step_status_rows(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> list[dict[str, str]]:
    flags = _review_flags_state(st)
    review = context.get("review") if context else None
    review_exists = review is not None
    summary = _build_project_analysis_summary(record, context)
    document_count = int(summary.get("document_count", 0) or 0)
    documents_requiring_ocr = int(summary.get("documents_requiring_ocr", 0) or 0)

    bom_rows = _enriched_bom_rows(st, _canonical_bom_items(context))
    bom_metrics = _canonical_bom_metrics(bom_rows)
    unresolved_bom_count = int(bom_metrics.get("unresolved_items", 0) or 0) + int(
        bom_metrics.get("conflicting_lines", 0) or 0
    )

    scope_rows = _scope_risk_findings(context)
    critical_scope_count = sum(
        1
        for item in scope_rows
        if _safe_text(item.get("severity"), "").lower() in {"critical", "high"}
    )
    responsibility_ambiguity_count = _keyword_count(
        scope_rows,
        ["responsib", "owner", "ownership", "delegat", "by others"],
        ["section", "category", "title", "recommended_action"],
    )
    recommended_rfi_count = sum(
        1 for item in scope_rows if _safe_text(item.get("candidate_rfi_text"), "")
    )

    engineering_review = _sales_design_review(st, record, context)
    engineering_risk_count = len(
        list((engineering_review or {}).get("major_risk_areas") or [])
    ) + len(list((engineering_review or {}).get("product_lifecycle_warnings") or []))

    total_bom_lines = len(bom_rows)
    known_cost_lines = sum(1 for row in bom_rows if row.get("known_cost") is not None)

    rows: list[dict[str, str]] = []
    for step in _review_step_definitions():
        key = _safe_text(step.get("key"), "")
        status = "ready"
        detail = ""

        if key == "documents":
            if document_count == 0:
                status = "not started"
                detail = "No project documents uploaded yet."
            elif documents_requiring_ocr == document_count and document_count > 0:
                status = "blocked"
                detail = "All uploaded documents currently require OCR handling."
            elif flags.get("documents_reviewed"):
                status = "complete"
                detail = "Documents and extraction status were reviewed."
            elif documents_requiring_ocr > 0:
                status = "needs review"
                detail = "OCR-required documents are present and should be reviewed."
            else:
                status = "ready"
                detail = "Documents are available for review."

        elif key == "bom":
            if not review_exists or total_bom_lines == 0:
                status = "blocked"
                detail = "Run project analysis to generate canonical BOM lines."
            elif flags.get("bom_reviewed"):
                status = "complete"
                detail = "BOM lines and exceptions were reviewed."
            elif unresolved_bom_count > 0:
                status = "needs review"
                detail = "Unresolved or conflicting BOM lines need review."
            else:
                status = "ready"
                detail = "BOM appears complete and is ready for confirmation."

        elif key == "scope_risk":
            if not review_exists:
                status = "blocked"
                detail = "Run project analysis to produce scope and risk findings."
            elif flags.get("scope_risk_reviewed"):
                status = "complete"
                detail = (
                    "Scope gaps, ownership ambiguity, and RFI candidates were reviewed."
                )
            elif (
                critical_scope_count > 0
                or responsibility_ambiguity_count > 0
                or recommended_rfi_count > 0
            ):
                status = "needs review"
                detail = "Critical scope findings or clarifications are still open."
            else:
                status = "ready"
                detail = "Scope and risk findings are ready for reviewer confirmation."

        elif key == "engineering":
            if engineering_review is None:
                status = "blocked"
                detail = "Engineering review output is not available yet."
            elif flags.get("engineering_reviewed"):
                status = "complete"
                detail = "Engineering findings and recommendations were reviewed."
            elif engineering_risk_count > 0:
                status = "needs review"
                detail = "High-priority engineering findings still need attention."
            else:
                status = "ready"
                detail = "Engineering findings are ready for final review."

        elif key == "estimate":
            if not review_exists or total_bom_lines == 0:
                status = "blocked"
                detail = "Estimate coverage requires BOM output from analysis."
            elif flags.get("estimate_reviewed"):
                status = "complete"
                detail = "Estimate coverage assumptions were reviewed."
            elif known_cost_lines < total_bom_lines:
                status = "needs review"
                detail = "Cost coverage is partial and should be reviewed."
            else:
                status = "ready"
                detail = "Estimate coverage appears complete for current data."

        elif key == "summary_report":
            if not review_exists:
                status = "blocked"
                detail = (
                    "Summary report generation requires completed project analysis."
                )
            elif bool(flags.get("summary_report_generated")):
                status = "complete"
                detail = "Project summary report was generated/exported."
            else:
                prior_rows = list(rows)
                if any(
                    item.get("status") in {"not started", "blocked"}
                    for item in prior_rows
                ):
                    status = "blocked"
                    detail = "Complete upstream review steps before generating final summary."
                elif any(
                    item.get("status") in {"ready", "needs review"}
                    for item in prior_rows
                ):
                    status = "needs review"
                    detail = (
                        "Generate summary after reviewer confirmation of key sections."
                    )
                else:
                    status = "ready"
                    detail = "Ready to generate the concise project summary report."

        rows.append(
            {
                "key": key,
                "step": _safe_text(step.get("step"), "Step"),
                "page": _safe_text(step.get("page"), "Overview"),
                "status": status,
                "why_it_matters": _safe_text(step.get("why"), ""),
                "detail": detail,
            }
        )

    return rows


def _next_review_action(
    step_rows: list[dict[str, str]],
) -> dict[str, str]:
    for row in step_rows:
        status = _safe_text(row.get("status"), "").lower()
        if status != "complete":
            return {
                "step": _safe_text(row.get("step"), "Review Step"),
                "page": _safe_text(row.get("page"), "Overview"),
                "status": status,
                "why": _safe_text(row.get("why_it_matters"), ""),
                "detail": _safe_text(row.get("detail"), ""),
            }

    return {
        "step": "Generate Summary Report",
        "page": "Reports",
        "status": "complete",
        "why": "All guided review steps are complete.",
        "detail": "Project summary report can be regenerated any time for updated context.",
    }


def _review_checklist_rows(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
    step_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    review = context.get("review") if context else None
    summary = _build_project_analysis_summary(record, context)
    document_count = int(summary.get("document_count", 0) or 0)
    documents_requiring_ocr = int(summary.get("documents_requiring_ocr", 0) or 0)

    status_by_key = {
        row.get("key"): _safe_text(row.get("status"), "") for row in step_rows
    }
    scope_rows = _scope_risk_findings(context)
    critical_scope_count = sum(
        1
        for item in scope_rows
        if _safe_text(item.get("severity"), "").lower() in {"critical", "high"}
    )
    responsibility_ambiguity_count = _keyword_count(
        scope_rows,
        ["responsib", "owner", "ownership", "delegat", "by others"],
        ["section", "category", "title", "recommended_action"],
    )
    recommended_rfi_count = sum(
        1 for item in scope_rows if _safe_text(item.get("candidate_rfi_text"), "")
    )

    bom_rows = _enriched_bom_rows(st, _canonical_bom_items(context))
    bom_metrics = _canonical_bom_metrics(bom_rows)
    unresolved_bom_count = int(bom_metrics.get("unresolved_items", 0) or 0) + int(
        bom_metrics.get("conflicting_lines", 0) or 0
    )

    engineering_review = _sales_design_review(st, record, context)
    high_risk_engineering_count = len(
        list((engineering_review or {}).get("major_risk_areas") or [])
    ) + len(list((engineering_review or {}).get("product_lifecycle_warnings") or []))

    known_cost_lines = sum(1 for row in bom_rows if row.get("known_cost") is not None)
    total_bom_lines = len(bom_rows)

    checklist = [
        {
            "Checklist Item": "all documents processed",
            "Status": (
                "complete"
                if review is not None and document_count > 0
                else "needs review" if document_count > 0 else "not started"
            ),
            "Detail": f"documents={document_count}",
        },
        {
            "Checklist Item": "OCR-required documents identified",
            "Status": (
                "complete"
                if review is not None and document_count > 0
                else "not started" if document_count == 0 else "ready"
            ),
            "Detail": f"documents_requiring_ocr={documents_requiring_ocr}",
        },
        {
            "Checklist Item": "BOM reviewed",
            "Status": status_by_key.get("bom", "not started"),
            "Detail": f"candidate_lines={total_bom_lines}",
        },
        {
            "Checklist Item": "unresolved BOM items reviewed",
            "Status": (
                "complete"
                if unresolved_bom_count == 0
                else status_by_key.get("bom", "needs review")
            ),
            "Detail": f"unresolved_or_conflicting={unresolved_bom_count}",
        },
        {
            "Checklist Item": "critical scope gaps reviewed",
            "Status": (
                "complete"
                if critical_scope_count == 0
                else status_by_key.get("scope_risk", "needs review")
            ),
            "Detail": f"critical_or_high_scope_findings={critical_scope_count}",
        },
        {
            "Checklist Item": "responsibility ambiguities reviewed",
            "Status": (
                "complete"
                if responsibility_ambiguity_count == 0
                else status_by_key.get("scope_risk", "needs review")
            ),
            "Detail": f"responsibility_ambiguities={responsibility_ambiguity_count}",
        },
        {
            "Checklist Item": "high-risk engineering findings reviewed",
            "Status": (
                "complete"
                if high_risk_engineering_count == 0
                else status_by_key.get("engineering", "needs review")
            ),
            "Detail": f"high_risk_engineering_findings={high_risk_engineering_count}",
        },
        {
            "Checklist Item": "recommended RFIs reviewed",
            "Status": (
                "complete"
                if recommended_rfi_count == 0
                else status_by_key.get("scope_risk", "needs review")
            ),
            "Detail": f"recommended_rfis={recommended_rfi_count}",
        },
        {
            "Checklist Item": "estimate coverage reviewed",
            "Status": status_by_key.get("estimate", "not started"),
            "Detail": f"known_cost_lines={known_cost_lines}/{total_bom_lines}",
        },
        {
            "Checklist Item": "summary report generated",
            "Status": status_by_key.get("summary_report", "not started"),
            "Detail": _safe_text(
                _review_flags_state(st).get("summary_report_generated_at"),
                "not generated",
            ),
        },
    ]

    return checklist


def _summary_report_payload(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = _build_project_analysis_summary(record, context)
    step_rows = _review_step_status_rows(st, record, context)
    checklist = _review_checklist_rows(st, record, context, step_rows)
    next_action = _next_review_action(step_rows)

    import_summary = dict(context.get("import_summary") or {}) if context else {}
    bom_rows = _enriched_bom_rows(st, _canonical_bom_items(context))
    bom_metrics = _canonical_bom_metrics(bom_rows)
    missing_bom_rows = [
        row
        for row in bom_rows
        if _safe_text(row.get("completeness_status"), "").lower()
        not in {"complete", "drawing_only", "specification_only"}
    ]

    scope_rows = _scope_risk_findings(context)
    sections = _scope_risk_sections(scope_rows)
    scope_gaps = list(sections.get("Missing Scope") or [])
    responsibility_risks = list(sections.get("Responsibility Gaps") or [])
    engineering_risks = list(sections.get("Engineering Gaps") or []) + list(
        sections.get("Commercial Risks") or []
    )
    recommended_rfis = [
        item for item in scope_rows if _safe_text(item.get("candidate_rfi_text"), "")
    ]

    engineering_review = _sales_design_review(st, record, context) or {}
    known_limitations = list(engineering_review.get("limitations") or [])
    known_limitations.extend(list(context.get("warnings") or []) if context else [])

    known_cost_lines = sum(1 for row in bom_rows if row.get("known_cost") is not None)
    total_lines = len(bom_rows)
    review = context.get("review") if context else None
    labor_estimate = getattr(review, "labor_estimate", None) if review else None
    labor_confidence = _safe_text(getattr(labor_estimate, "confidence", None), "n/a")
    estimate_coverage = {
        "total_bom_lines": total_lines,
        "known_cost_lines": known_cost_lines,
        "coverage_percent": (
            int((known_cost_lines / total_lines) * 100) if total_lines else 0
        ),
        "labor_confidence": labor_confidence,
    }

    return {
        "project_overview": {
            "project_name": summary.get("project_name"),
            "customer": summary.get("customer"),
            "project_type": summary.get("project_type"),
            "analysis_status": summary.get("analysis_status"),
        },
        "documents_reviewed": {
            "total_files": int(import_summary.get("total_files", 0) or 0),
            "documents_requiring_ocr": int(
                import_summary.get("documents_requiring_ocr", 0) or 0
            ),
            "supported_files": int(import_summary.get("supported_files", 0) or 0),
            "unsupported_files": int(import_summary.get("unsupported_files", 0) or 0),
        },
        "bom_summary": bom_metrics,
        "missing_or_incomplete_bom_detail": missing_bom_rows,
        "scope_gaps": scope_gaps,
        "responsibility_risks": responsibility_risks,
        "engineering_risks": engineering_risks,
        "recommended_rfis": recommended_rfis,
        "estimate_coverage": estimate_coverage,
        "recommended_next_actions": [
            {
                "step": item.get("step"),
                "page": item.get("page"),
                "status": item.get("status"),
                "detail": item.get("detail"),
            }
            for item in step_rows
            if _safe_text(item.get("status"), "") != "complete"
        ],
        "known_limitations": sorted(
            {_safe_text(item, "") for item in known_limitations}
        ),
        "guided_review_steps": step_rows,
        "review_checklist": checklist,
        "recommended_next_action": next_action,
        "generated_at": _now_iso(),
    }


def _summary_report_markdown(payload: dict[str, Any]) -> str:
    overview = dict(payload.get("project_overview") or {})
    documents = dict(payload.get("documents_reviewed") or {})
    bom_summary = dict(payload.get("bom_summary") or {})
    estimate = dict(payload.get("estimate_coverage") or {})

    lines = [
        "# Project Summary Report",
        "",
        "## Project Overview",
        f"- Project: {_safe_text(overview.get('project_name'), 'n/a')}",
        f"- Customer: {_safe_text(overview.get('customer'), 'n/a')}",
        f"- Project Type: {_safe_text(overview.get('project_type'), 'n/a')}",
        f"- Analysis Status: {_safe_text(overview.get('analysis_status'), 'n/a')}",
        "",
        "## Documents Reviewed",
        f"- Total files: {int(documents.get('total_files', 0) or 0)}",
        f"- Documents requiring OCR: {int(documents.get('documents_requiring_ocr', 0) or 0)}",
        f"- Supported files: {int(documents.get('supported_files', 0) or 0)}",
        f"- Unsupported files: {int(documents.get('unsupported_files', 0) or 0)}",
        "",
        "## BOM Summary",
        f"- Candidate lines: {int(bom_summary.get('total_candidate_bom_lines', 0) or 0)}",
        f"- Complete lines: {int(bom_summary.get('complete_lines', 0) or 0)}",
        f"- Incomplete lines: {int(bom_summary.get('incomplete_lines', 0) or 0)}",
        f"- Conflicting lines: {int(bom_summary.get('conflicting_lines', 0) or 0)}",
        "",
        "## Missing or Incomplete BOM Detail",
    ]

    for row in list(payload.get("missing_or_incomplete_bom_detail") or [])[:15]:
        lines.append(
            "- "
            + _safe_text(row.get("bom_item_id"), "Unknown BOM line")
            + " | "
            + _safe_text(row.get("completeness_status"), "unresolved")
            + " | "
            + _safe_text(row.get("description"), "n/a")
        )

    lines.extend(["", "## Scope Gaps"])
    for row in list(payload.get("scope_gaps") or [])[:15]:
        lines.append(
            "- "
            + _safe_text(row.get("title"), "Scope finding")
            + " | "
            + _safe_text(row.get("recommended_action"), "review required")
        )

    lines.extend(["", "## Responsibility Risks"])
    for row in list(payload.get("responsibility_risks") or [])[:15]:
        lines.append(
            "- "
            + _safe_text(row.get("title"), "Responsibility finding")
            + " | "
            + _safe_text(row.get("likely_owner"), "owner not assigned")
        )

    lines.extend(["", "## Engineering Risks"])
    for row in list(payload.get("engineering_risks") or [])[:15]:
        lines.append(
            "- "
            + _safe_text(row.get("title"), "Engineering risk")
            + " | "
            + _safe_text(row.get("recommended_action"), "review required")
        )

    lines.extend(["", "## Recommended RFIs"])
    for row in list(payload.get("recommended_rfis") or [])[:15]:
        lines.append(
            "- "
            + _safe_text(row.get("title"), "RFI")
            + " | "
            + _safe_text(row.get("candidate_rfi_text"), "internal draft")
        )

    lines.extend(
        [
            "",
            "## Estimate Coverage",
            f"- Total BOM lines: {int(estimate.get('total_bom_lines', 0) or 0)}",
            f"- Known cost lines: {int(estimate.get('known_cost_lines', 0) or 0)}",
            f"- Coverage percent: {int(estimate.get('coverage_percent', 0) or 0)}%",
            f"- Labor confidence: {_safe_text(estimate.get('labor_confidence'), 'n/a')}",
            "",
            "## Recommended Next Actions",
        ]
    )
    for row in list(payload.get("recommended_next_actions") or [])[:12]:
        lines.append(
            "- "
            + _safe_text(row.get("step"), "Next step")
            + " ("
            + _safe_text(row.get("page"), "Overview")
            + "): "
            + _safe_text(row.get("detail"), "review required")
        )

    lines.extend(["", "## Known Limitations"])
    for item in list(payload.get("known_limitations") or []):
        lines.append("- " + _safe_text(item, "n/a"))

    return "\n".join(lines) + "\n"


def _summary_report_html(payload: dict[str, Any]) -> str:
    import html

    markdown = _summary_report_markdown(payload)
    return (
        "<html><head><meta charset='utf-8'><title>Project Summary Report</title></head><body>"
        + "<pre>"
        + html.escape(markdown)
        + "</pre></body></html>"
    )


def _render_review_transition(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
    step_key: str,
    *,
    mark_label: str,
) -> None:
    step_rows = _review_step_status_rows(st, record, context)
    current = next((row for row in step_rows if row.get("key") == step_key), None)
    next_action = _next_review_action(step_rows)

    if current is None:
        return

    st.markdown("### Review Progress")
    st.dataframe(
        [
            {
                "Current Step": current.get("step"),
                "Status": _status_chip(_safe_text(current.get("status"), "").title()),
                "Detail": current.get("detail"),
            },
            {
                "Current Step": "Recommended Next",
                "Status": _status_chip(
                    _safe_text(next_action.get("status"), "").title()
                ),
                "Detail": _safe_text(next_action.get("step"), "")
                + " - "
                + _safe_text(next_action.get("detail"), ""),
            },
        ],
        use_container_width=True,
        hide_index=True,
    )

    action_cols = st.columns(2)
    if action_cols[0].button(mark_label, use_container_width=True):
        _set_review_flag(st, f"{step_key}_reviewed", True)
        st.rerun()

    if action_cols[1].button(
        f"Continue to {_safe_text(next_action.get('step'), 'Next Step')}",
        use_container_width=True,
    ):
        st.session_state["atlas_active_page"] = _safe_text(
            next_action.get("page"),
            "Overview",
        )
        st.rerun()


def _build_project_analysis_summary(
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    review = context.get("review") if context else None
    brief = context.get("brief") if context else None
    metadata = (
        dict(getattr(context.get("intake_snapshot"), "metadata", {}) or {})
        if context
        else {}
    )
    import_summary = dict(context.get("import_summary") or {}) if context else {}
    objects = _workspace_objects(context)
    equipment = list(objects.get("equipment") or [])
    coordination_findings = list(objects.get("coordination_findings") or [])
    resolver_rows = _build_resolver_conflict_rows(
        _build_engineering_resolver(record, context)
    )
    risk_rows = (
        _to_rows(list(getattr(review, "estimator_risks", []) or [])) if review else []
    )
    prioritized_actions = list(getattr(brief, "prioritized_reviewer_actions", []) or [])
    scope_gap_count = int(
        getattr(review, "scope_gap_count", lambda: 0)() if review else 0
    )
    high_severity_findings = [
        item
        for item in coordination_findings
        if _safe_text(item.get("severity"), "").lower() in {"critical", "high"}
    ]
    high_risk_issue_count = len(risk_rows) + len(high_severity_findings)
    quantity_conflict_count = _keyword_count(
        resolver_rows,
        ["quantity"],
        ["field", "message"],
    )
    responsibility_ambiguity_count = _keyword_count(
        coordination_findings,
        ["responsib", "owner", "ownership", "by others", "delegat"],
        ["category", "title", "recommended_action"],
    )
    unresolved_manufacturer_model_refs = _keyword_count(
        resolver_rows,
        ["manufacturer", "model"],
        ["field", "message"],
    )
    missing_specifications = len(
        [
            item
            for item in equipment
            if not list(item.get("specification_references") or [])
        ]
    )
    document_count = int(import_summary.get("total_files", 0) or 0)
    documents_requiring_ocr = int(import_summary.get("documents_requiring_ocr", 0) or 0)
    equipment_items_found = len(equipment)
    possible_bom_items = len(
        [
            item
            for item in equipment
            if _first_text(
                item.get("equipment_id"),
                item.get("manufacturer"),
                item.get("model"),
                item.get("description"),
            )
        ]
    )
    unresolved_scope_issue_count = (
        scope_gap_count + quantity_conflict_count + responsibility_ambiguity_count
    )

    if review is None and document_count == 0:
        analysis_status = "Awaiting documents"
    elif review is None:
        analysis_status = "Ready to run"
    else:
        analysis_status = "Analysis complete"

    if document_count == 0:
        recommended_next_action = (
            "Open Documents to upload files and start deterministic project analysis."
        )
    elif review is None:
        recommended_next_action = "Open Documents and run Project Analysis."
    elif documents_requiring_ocr > 0:
        recommended_next_action = (
            "Open Documents to review OCR-required files before finalizing conclusions."
        )
    elif unresolved_scope_issue_count > 0:
        recommended_next_action = "Open Scope & Risk to review critical gaps, ownership ambiguity, and draft RFIs."
    elif high_risk_issue_count > 0:
        recommended_next_action = "Open Engineering Review to resolve high-risk findings and recommended actions."
    else:
        recommended_next_action = (
            "Open Reports to generate and export the concise project summary report."
        )

    return {
        "project_name": record.project.name,
        "customer": _first_text(
            metadata.get("owner"),
            metadata.get("client"),
            record.project.client,
        )
        or record.project.client,
        "project_type": _first_text(
            metadata.get("project_type"),
            metadata.get("building_type"),
            metadata.get("market_sector"),
        )
        or "Unspecified",
        "document_count": document_count,
        "analysis_status": analysis_status,
        "bom_item_count": equipment_items_found,
        "possible_bom_items": possible_bom_items,
        "unresolved_scope_issue_count": unresolved_scope_issue_count,
        "high_risk_issue_count": high_risk_issue_count,
        "documents_requiring_ocr": documents_requiring_ocr,
        "recommended_next_action": recommended_next_action,
        "equipment_items_found": equipment_items_found,
        "scope_gaps": scope_gap_count,
        "quantity_conflicts": quantity_conflict_count,
        "responsibility_ambiguities": responsibility_ambiguity_count,
        "missing_specifications": missing_specifications,
        "unresolved_manufacturer_model_refs": unresolved_manufacturer_model_refs,
        "recommended_actions": prioritized_actions,
        "risk_rows": risk_rows,
        "coordination_findings": coordination_findings,
        "resolver_rows": resolver_rows,
    }


def _canonical_bom_items(context: dict[str, Any] | None) -> list[dict[str, Any]]:
    if context is None:
        return []

    cached = _context_cached(context, "canonical_bom_items")
    if isinstance(cached, list):
        return cached

    review = context.get("review")
    snapshot = context.get("intake_snapshot")
    equipment_rows = _to_rows(list(getattr(review, "equipment", []) or []))
    rfi_rows = _to_rows(list(getattr(review, "rfi_candidates", []) or []))
    source_references = _to_rows(list(getattr(snapshot, "source_references", []) or []))
    resolver_rows = _build_resolver_conflict_rows(
        _build_engineering_resolver(record=None, context=context)
    )
    items = BomReviewService().build_items(
        equipment_rows=equipment_rows,
        resolver_rows=resolver_rows,
        source_references=source_references,
        rfi_rows=rfi_rows,
    )
    rows = [item.to_dict() for item in items]
    _set_context_cached(context, "canonical_bom_items", rows)
    return rows


def _canonical_bom_metrics(bom_rows: list[dict[str, Any]]) -> dict[str, int]:
    total = len(bom_rows)
    complete = sum(
        1 for item in bom_rows if item.get("completeness_status") == "complete"
    )
    conflicting = sum(
        1
        for item in bom_rows
        if item.get("completeness_status") == "conflicting_quantity"
    )
    incomplete = sum(
        1
        for item in bom_rows
        if item.get("completeness_status") not in {"complete", "conflicting_quantity"}
    )
    return {
        "total_candidate_bom_lines": total,
        "complete_lines": complete,
        "incomplete_lines": incomplete,
        "conflicting_lines": conflicting,
        "drawing_only_items": sum(
            1 for item in bom_rows if item.get("completeness_status") == "drawing_only"
        ),
        "specification_only_items": sum(
            1
            for item in bom_rows
            if item.get("completeness_status") == "specification_only"
        ),
        "unresolved_items": sum(
            1 for item in bom_rows if item.get("completeness_status") == "unresolved"
        ),
    }


def _canonical_bom_export_payload(
    bom_rows: list[dict[str, Any]],
) -> tuple[str, str]:
    ordered = sorted(
        [dict(item) for item in bom_rows],
        key=lambda row: _safe_text(row.get("bom_item_id"), ""),
    )

    headers = [
        "bom_item_id",
        "manufacturer",
        "model",
        "description",
        "quantity",
        "system",
        "room_or_area",
        "source_documents",
        "source_pages",
        "drawing_references",
        "specification_references",
        "confidence",
        "quantity_confidence",
        "scope_status",
        "responsibility",
        "completeness_status",
        "warnings",
        "related_rfi_candidates",
    ]

    csv_rows = []
    for row in ordered:
        csv_rows.append(
            {
                "bom_item_id": _safe_text(row.get("bom_item_id"), ""),
                "manufacturer": _safe_text(row.get("manufacturer"), ""),
                "model": _safe_text(row.get("model"), ""),
                "description": _safe_text(row.get("description"), ""),
                "quantity": _safe_text(row.get("quantity"), ""),
                "system": _safe_text(row.get("system"), ""),
                "room_or_area": _safe_text(row.get("room_or_area"), ""),
                "source_documents": "|".join(sorted(row.get("source_documents") or [])),
                "source_pages": "|".join(sorted(row.get("source_pages") or [])),
                "drawing_references": "|".join(
                    sorted(row.get("drawing_references") or [])
                ),
                "specification_references": "|".join(
                    sorted(row.get("specification_references") or [])
                ),
                "confidence": row.get("confidence", 0.0),
                "quantity_confidence": row.get("quantity_confidence", 0.0),
                "scope_status": _safe_text(row.get("scope_status"), ""),
                "responsibility": _safe_text(row.get("responsibility"), ""),
                "completeness_status": _safe_text(row.get("completeness_status"), ""),
                "warnings": "|".join(sorted(row.get("warnings") or [])),
                "related_rfi_candidates": "|".join(
                    sorted(row.get("related_rfi_candidates") or [])
                ),
            }
        )

    import csv
    import io
    import json

    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=headers)
    writer.writeheader()
    writer.writerows(csv_rows)

    json_payload = {
        "bom_items": csv_rows,
        "metrics": _canonical_bom_metrics(ordered),
    }
    return csv_buffer.getvalue(), json.dumps(json_payload, indent=2, sort_keys=True)


def _equipment_lookup_by_id(
    context: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows = list(_workspace_objects(context).get("equipment") or [])
    return {
        _safe_text(item.get("equipment_id"), ""): item
        for item in rows
        if _safe_text(item.get("equipment_id"), "")
    }


def _equipment_human_label(context: dict[str, Any] | None, equipment_id: str) -> str:
    equipment = _equipment_lookup_by_id(context).get(_safe_text(equipment_id, ""))
    if equipment is None:
        return _safe_text(equipment_id, "Equipment")
    manufacturer = _safe_text(equipment.get("manufacturer"), "Unknown")
    model = _safe_text(equipment.get("model"), "Unknown")
    description = _safe_text(equipment.get("description"), "")
    descriptor = " ".join(
        part for part in [manufacturer, model] if _safe_text(part, "")
    ).strip()
    if description and description.lower() not in descriptor.lower():
        return f"{descriptor} - {description} ({equipment_id})"
    return f"{descriptor} ({equipment_id})".strip()


def _equipment_lifecycle_status(
    manufacturer: str,
    model: str,
    warnings: list[str],
    master_rows: list[dict[str, Any]],
) -> str:
    matched_status = ""
    for row in master_rows:
        if _safe_text(row.get("manufacturer"), "").lower() != manufacturer.lower():
            continue
        if _safe_text(row.get("model"), "").lower() != model.lower():
            continue
        matched_status = _safe_text(row.get("status"), "")
        if matched_status:
            break

    warning_text = " ".join(warnings).lower()
    if "discontinued" in warning_text:
        return "Discontinued"
    if "legacy" in warning_text:
        return "Legacy"
    if matched_status:
        normalized = matched_status.replace("_", " ").strip().lower()
        if normalized in {"discontinued", "legacy", "obsolete"}:
            return normalized.title()
        if normalized in {"active", "current", "supported"}:
            return "Active"
        return matched_status.replace("_", " ").title()
    return "Active"


def _equipment_workspace_rows(
    st: Any,
    context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if context is None:
        return []

    bom_rows = _enriched_bom_rows(st, _canonical_bom_items(context))
    if not bom_rows:
        return []

    objects = _workspace_objects(context)
    evidence_rows = list(objects.get("evidence") or [])
    scope_findings = _scope_risk_findings(context)
    rfi_rows = list(objects.get("rfis") or [])
    spec_rows = list(objects.get("specifications") or [])
    master_rows = _master_library_rows(st, context)

    result: list[dict[str, Any]] = []
    for row in bom_rows:
        equipment_id = _safe_text(
            row.get("bom_item_id"),
            _safe_text(row.get("equipment_id"), "Unknown Equipment"),
        )
        manufacturer = _safe_text(row.get("manufacturer"), "Unknown")
        model = _safe_text(row.get("model"), "Unknown")
        drawing_refs = list(row.get("drawing_references") or [])
        specification_refs = list(row.get("specification_references") or [])
        source_documents = list(row.get("source_documents") or [])
        source_pages = list(row.get("source_pages") or [])
        warnings = list(row.get("warnings") or [])
        pricing_warning = _safe_text(row.get("pricing_warning"), "")
        if pricing_warning:
            warnings.append(pricing_warning)

        schedule_refs = sorted(
            {
                _safe_text(schedule, "")
                for spec_row in spec_rows
                if _safe_text(spec_row.get("section"), "") in specification_refs
                for schedule in list(spec_row.get("related_schedules") or [])
                if _safe_text(schedule, "")
            }
        )

        related_risks = [
            _safe_text(item.get("title"), "Risk")
            for item in scope_findings
            if _contains_any(
                str(item),
                [equipment_id, model, manufacturer],
            )
        ]

        related_rfis = sorted(
            {
                *[
                    _safe_text(item, "")
                    for item in list(row.get("related_rfi_candidates") or [])
                    if _safe_text(item, "")
                ],
                *[
                    _safe_text(
                        rfi.get("rfi_id"),
                        _safe_text(rfi.get("title"), "rfi"),
                    )
                    for rfi in rfi_rows
                    if _contains_any(str(rfi), [equipment_id, model])
                ],
            }
        )

        evidence_refs = sorted(
            {
                *[
                    f"{source} p.{page}"
                    for source in source_documents
                    for page in source_pages or ["n/a"]
                ],
                *[
                    f"{_safe_text(item.get('source_file'), 'file')} p.{item.get('page', 'n/a')}"
                    for item in evidence_rows
                    if _contains_any(
                        item.get("source_file"),
                        [*source_documents, *drawing_refs, *specification_refs],
                    )
                ],
            }
        )

        completeness_status = _safe_text(
            row.get("completeness_status"),
            "unresolved",
        )
        missing_components: list[str] = []
        if completeness_status == "missing_manufacturer":
            missing_components.append("manufacturer")
        if completeness_status == "missing_model":
            missing_components.append("model")
        if completeness_status == "unresolved":
            missing_components.append("equipment mapping")
        if completeness_status == "conflicting_quantity":
            missing_components.append("quantity confirmation")

        confidence_value = row.get("confidence")
        confidence = (
            float(confidence_value)
            if isinstance(confidence_value, (int, float))
            else 0.0
        )

        responsibility = _safe_text(row.get("responsibility"), "Needs Review")
        lifecycle_status = _equipment_lifecycle_status(
            manufacturer,
            model,
            warnings,
            master_rows,
        )

        requires_review = (
            completeness_status
            not in {"complete", "drawing_only", "specification_only"}
            or confidence < 0.65
            or bool(warnings)
            or bool(related_risks)
            or "unknown" in responsibility.lower()
        )

        result.append(
            {
                "equipment_id": equipment_id,
                "manufacturer": manufacturer,
                "model": model,
                "description": _safe_text(row.get("description"), "n/a"),
                "quantity": row.get("quantity"),
                "system": _safe_text(row.get("system"), "Unknown"),
                "room_or_area": _safe_text(row.get("room_or_area"), "Unknown"),
                "confidence": confidence,
                "completeness_status": completeness_status,
                "responsibility": responsibility,
                "lifecycle_status": lifecycle_status,
                "source_documents": source_documents,
                "drawing_references": drawing_refs,
                "specification_references": specification_refs,
                "schedule_references": schedule_refs,
                "related_risks": related_risks,
                "related_rfi_candidates": related_rfis,
                "labor_allowance": None,
                "known_cost": row.get("known_cost"),
                "pricing_source": _safe_text(row.get("pricing_source"), ""),
                "missing_components": missing_components,
                "warnings": warnings,
                "evidence_refs": evidence_refs,
                "requires_review": requires_review,
            }
        )

    result.sort(key=lambda item: _safe_text(item.get("equipment_id"), ""))
    return result


def _equipment_recommended_actions(item: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    def _add(
        priority: str,
        action: str,
        reason: str,
        destination: str,
        refs: list[str],
    ) -> None:
        actions.append(
            {
                "priority": priority,
                "action": action,
                "reason": reason,
                "destination": destination,
                "affected_sources": ", ".join(refs[:4]) or "n/a",
            }
        )

    references = list(item.get("evidence_refs") or [])
    completeness = _safe_text(item.get("completeness_status"), "")
    manufacturer = _safe_text(item.get("manufacturer"), "")
    model = _safe_text(item.get("model"), "")
    quantity = _safe_text(item.get("quantity"), "")
    responsibility = _safe_text(item.get("responsibility"), "")
    lifecycle = _safe_text(item.get("lifecycle_status"), "")
    known_cost = item.get("known_cost")
    confidence = float(item.get("confidence", 0.0) or 0.0)

    if completeness == "missing_manufacturer" or manufacturer.lower() in {
        "",
        "unknown",
    }:
        _add(
            "Critical",
            "Confirm manufacturer",
            "Manufacturer is missing or unresolved in canonical BOM data.",
            "BOM Review",
            references,
        )
    if completeness == "missing_model" or model.lower() in {"", "unknown"}:
        _add(
            "Critical",
            "Confirm model number",
            "Model is missing or unresolved for this equipment object.",
            "BOM Review",
            references,
        )
    if completeness == "conflicting_quantity" or "conflict" in quantity.lower():
        _add(
            "High",
            "Verify quantity",
            "Quantity evidence is conflicting across source references.",
            "Scope & Risk",
            references,
        )
    if list(item.get("missing_components") or []):
        _add(
            "High",
            "Add missing accessories to BOM",
            "Completeness status indicates missing equipment components.",
            "BOM Review",
            references,
        )
    if "unknown" in responsibility.lower() or "review" in responsibility.lower():
        _add(
            "High",
            "Confirm OFCI/CFCI responsibility",
            "Responsibility assignment is ambiguous for this item.",
            "Scope & Risk",
            references,
        )
    if lifecycle.lower() in {"discontinued", "legacy", "obsolete"}:
        _add(
            "High",
            "Review discontinued product substitution",
            "Lifecycle status indicates legacy or discontinued product risk.",
            "Engineering Review",
            references,
        )
    if known_cost is None:
        _add(
            "Medium",
            "Review pricing source",
            "Known cost is not available in deterministic price matching.",
            "Price List Library",
            references,
        )
    if confidence < 0.7:
        _add(
            "Medium",
            "Match to manufacturer product",
            "Object confidence is below preferred engineering review threshold.",
            "Master Library Explorer",
            references,
        )
    if not actions:
        _add(
            "Low",
            "No immediate action",
            "Equipment object appears complete for current project evidence.",
            "Equipment",
            references,
        )

    rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    actions.sort(key=lambda item: rank.get(_safe_text(item.get("priority"), "Low"), 3))
    return actions


def _open_equipment_detail(
    st: Any,
    *,
    equipment_id: str,
    origin_page: str,
    origin_key: str,
) -> None:
    st.session_state["atlas_equipment_origin"] = {
        "page": origin_page,
        "key": origin_key,
    }
    st.session_state["atlas_active_page"] = "Equipment"
    _set_context_selection(st, "equipment", {"equipment_id": equipment_id})
    st.rerun()


def _scope_risk_findings(context: dict[str, Any] | None) -> list[dict[str, Any]]:
    if context is None:
        return []

    cached = _context_cached(context, "scope_risk_findings")
    if isinstance(cached, list):
        return cached

    review = context.get("review")
    bom_rows = _canonical_bom_items(context)
    resolver_rows = _build_resolver_conflict_rows(
        _build_engineering_resolver(record=None, context=context)
    )
    objects = _workspace_objects(context)
    coordination = list(objects.get("coordination_findings") or [])
    risk_rows = _to_rows(list(getattr(review, "estimator_risks", []) or []))
    rfi_rows = _to_rows(list(getattr(review, "rfi_candidates", []) or []))

    findings = ScopeRiskReviewService().build_findings(
        bom_rows=bom_rows,
        resolver_rows=resolver_rows,
        coordination_findings=coordination,
        risk_rows=risk_rows,
        rfi_rows=rfi_rows,
    )
    rows = [finding.to_dict() for finding in findings]
    _set_context_cached(context, "scope_risk_findings", rows)
    return rows


def _scope_risk_metrics(finding_rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(finding_rows),
        "critical": sum(
            1
            for item in finding_rows
            if _safe_text(item.get("severity"), "").lower() == "critical"
        ),
        "high": sum(
            1
            for item in finding_rows
            if _safe_text(item.get("severity"), "").lower() == "high"
        ),
        "quantity_conflicts": sum(
            1
            for item in finding_rows
            if _safe_text(item.get("category"), "") == "quantity_conflict"
        ),
    }


def _scope_risk_sections(
    finding_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    ordered = [
        "Critical Issues",
        "Missing Scope",
        "Responsibility Gaps",
        "Quantity Conflicts",
        "Engineering Gaps",
        "Commercial Risks",
        "Recommended RFIs",
    ]
    grouped: dict[str, list[dict[str, Any]]] = {section: [] for section in ordered}
    for row in finding_rows:
        section = _safe_text(row.get("section"), "Engineering Gaps")
        grouped.setdefault(section, [])
        grouped[section].append(row)

    grouped["Recommended RFIs"] = [
        {
            "Finding": item.get("title"),
            "Severity": item.get("severity"),
            "Likely Owner": item.get("likely_owner"),
            "Candidate RFI (Internal Draft)": item.get("candidate_rfi_text"),
        }
        for item in finding_rows
        if _safe_text(item.get("candidate_rfi_text"), "")
    ]
    return grouped


def _default_price_list_library_state() -> dict[str, Any]:
    return {
        "uploaded_price_lists": [],
        "manufacturer_products": [],
        "vendor_offers": [],
        "import_warnings": [],
        "commercial_knowledge": CommercialKnowledgeService.empty_state(),
        "commercial_products": CommercialProductService.empty_state(),
        "commercial_import_results": [],
    }


def _price_list_library_state(st: Any) -> dict[str, Any]:
    state = st.session_state.get("atlas_price_list_library")
    if isinstance(state, dict):
        return state
    state = _default_price_list_library_state()
    st.session_state["atlas_price_list_library"] = state
    return state


def _commercial_knowledge_state(st: Any) -> dict[str, Any]:
    library = _price_list_library_state(st)
    state = library.get("commercial_knowledge")
    if isinstance(state, dict):
        return dict(state)
    return CommercialKnowledgeService.empty_state()


def _commercial_service(st: Any) -> CommercialKnowledgeService:
    return CommercialKnowledgeService(state=_commercial_knowledge_state(st))


def _commercial_product_state(st: Any) -> dict[str, Any]:
    library = _price_list_library_state(st)
    state = library.get("commercial_products")
    if isinstance(state, dict):
        return dict(state)
    return CommercialProductService.empty_state()


def _commercial_product_service(st: Any) -> CommercialProductService:
    return CommercialProductService(state=_commercial_product_state(st))


def _save_commercial_product_state(st: Any, service: CommercialProductService) -> None:
    library = _price_list_library_state(st)
    library["commercial_products"] = service.to_dict()
    st.session_state["atlas_price_list_library"] = library


def _ensure_commercial_seed_data(st: Any) -> CommercialProductService:
    service = _commercial_product_service(st)
    if service.list_manufacturers() and service.list_vendors():
        return service

    for manufacturer_seed in build_manufacturer_seed_data():
        payload = manufacturer_seed.to_dict()
        try:
            service.create_manufacturer(
                manufacturer_id=_safe_text(payload.get("manufacturer_id"), ""),
                canonical_name=_safe_text(payload.get("name"), ""),
                display_name=_safe_text(payload.get("name"), ""),
                manufacturer_code=_safe_text(payload.get("manufacturer_id"), ""),
                website="",
                aliases=[],
                notes="seed",
                active=bool(payload.get("active", True)),
            )
        except Exception:
            continue

    for vendor_seed in build_vendor_seed_data():
        payload = vendor_seed.to_dict()
        try:
            service.create_vendor(
                vendor_id=_safe_text(payload.get("vendor_id"), ""),
                canonical_name=_safe_text(payload.get("name"), ""),
                display_name=_safe_text(payload.get("name"), ""),
                vendor_code=_safe_text(payload.get("vendor_id"), ""),
                website="",
                aliases=[],
                notes="seed",
                active=bool(payload.get("active", True)),
            )
        except Exception:
            continue

    _save_commercial_product_state(st, service)
    return service


def _commercial_recommendation_rows(st: Any) -> list[dict[str, Any]]:
    service = _commercial_product_service(st)
    dashboard = service.dashboard_summary()
    products = service.list_products(include_inactive=True)
    offerings = list(service.to_dict().get("vendor_offerings", {}).values())
    sheets = service.list_price_sheets()

    recommendations: list[dict[str, Any]] = []
    products_without_offerings = [
        item
        for item in products
        if not service.list_vendor_offerings_by_product(
            _safe_text(item.get("atlas_product_uuid"), "")
        )
    ]
    if products_without_offerings:
        recommendations.append(
            {
                "Priority": "High",
                "Recommendation": "Add a vendor source for products without vendor offerings.",
                "Count": len(products_without_offerings),
                "Destination": "Knowledge",
            }
        )

    unclassified = [
        item
        for item in offerings
        if _safe_text(item.get("purchasing_channel"), "")
        not in ALLOWED_PURCHASING_CHANNELS
    ]
    if unclassified:
        recommendations.append(
            {
                "Priority": "High",
                "Recommendation": "Classify vendor offerings as direct, distributor, dealer/reseller, or other.",
                "Count": len(unclassified),
                "Destination": "Knowledge",
            }
        )

    if int(dashboard.get("missing_preferred_vendor", 0) or 0) > 0:
        recommendations.append(
            {
                "Priority": "Medium",
                "Recommendation": "Assign preferred vendor metadata for active products.",
                "Count": int(dashboard.get("missing_preferred_vendor", 0) or 0),
                "Destination": "Knowledge",
            }
        )

    if offerings and not sheets:
        recommendations.append(
            {
                "Priority": "Medium",
                "Recommendation": "Create a Price Sheet for active vendors to anchor immutable versions.",
                "Count": 1,
                "Destination": "Price List Library",
            }
        )

    return recommendations


def _record_by_id(
    rows: list[dict[str, Any]],
    *,
    id_field: str,
    selected_id: str,
) -> dict[str, Any] | None:
    for row in rows:
        if _safe_text(row.get(id_field), "") == _safe_text(selected_id, ""):
            return row
    return None


def _commercial_product_key(
    *,
    manufacturer: str,
    model: str,
) -> str:
    mfr = _safe_text(manufacturer, "Unknown")
    mdl = _safe_text(model, "Unknown")
    return f"{mfr}::{mdl}"


def _enriched_bom_rows(st: Any, bom_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    library = _price_list_library_state(st)
    return PricingService().enrich_bom_rows(
        bom_rows=bom_rows,
        manufacturer_products=list(library.get("manufacturer_products") or []),
        vendor_offers=list(library.get("vendor_offers") or []),
    )


def _sales_design_review(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if context is None:
        return None

    summary = _build_project_analysis_summary(record, context)
    bom_rows = _enriched_bom_rows(st, _canonical_bom_items(context))
    findings = _scope_risk_findings(context)

    review = SalesDesignReviewService().build_review(
        summary=summary,
        bom_rows=bom_rows,
        scope_findings=findings,
    )
    return review.to_dict()


def _product_resolution_overrides(st: Any) -> dict[str, dict[str, Any]]:
    raw = st.session_state.get("atlas_product_resolution_overrides")
    if isinstance(raw, dict):
        return {str(key): dict(value or {}) for key, value in raw.items()}
    return {}


def _resolution_source_id(row: dict[str, Any]) -> str:
    return _safe_text(
        row.get("bom_item_id"),
        _safe_text(row.get("equipment_id"), "unknown_equipment"),
    )


def _resolved_product_rows(st: Any, bom_rows: list[dict[str, Any]]) -> list[Any]:
    if not bom_rows:
        return []

    overrides = _product_resolution_overrides(st)
    signature_payload = {
        "rows": [
            {
                "source": _resolution_source_id(row),
                "manufacturer": _safe_text(row.get("manufacturer"), "Unknown"),
                "model": _safe_text(row.get("model"), "Unknown"),
                "description": _safe_text(row.get("description"), ""),
                "completeness_status": _safe_text(row.get("completeness_status"), ""),
            }
            for row in bom_rows
        ],
        "overrides": overrides,
    }
    signature = hashlib.sha1(
        json.dumps(signature_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    cache_key = "atlas_product_resolution_cache"
    cached = st.session_state.get(cache_key)
    if isinstance(cached, dict) and cached.get("signature") == signature:
        return list(cached.get("resolutions") or [])

    registry = ManufacturerRegistry(build_manufacturer_seed_data())
    service = ProductResolutionService(
        master_library_service=MasterLibraryService(),
        manufacturer_registry=registry,
    )
    resolutions = service.resolve_equipment_rows(
        list(bom_rows),
        manual_overrides=overrides,
    )
    st.session_state[cache_key] = {
        "signature": signature,
        "resolutions": resolutions,
    }
    return resolutions


def _pricing_manual_overrides(st: Any) -> dict[str, dict[str, Any]]:
    raw = st.session_state.get("atlas_pricing_manual_overrides")
    if isinstance(raw, dict):
        return {str(key): dict(value or {}) for key, value in raw.items()}
    return {}


def _pricing_policy(st: Any) -> dict[str, Any]:
    raw = st.session_state.get("atlas_preferred_vendor_policy")
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _pricing_quotes(st: Any) -> list[dict[str, Any]]:
    raw = st.session_state.get("atlas_project_quotes")
    if isinstance(raw, list):
        return [dict(item or {}) for item in raw if isinstance(item, dict)]
    return []


def _pricing_allowances(st: Any) -> dict[str, float]:
    raw = st.session_state.get("atlas_generic_allowances")
    if not isinstance(raw, dict):
        return {}
    allowances: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, (int, float)):
            allowances[str(key)] = float(value)
    return allowances


def _quick_add_products_by_project(st: Any) -> dict[str, list[dict[str, Any]]]:
    raw = st.session_state.get("atlas_quick_add_products")
    if not isinstance(raw, dict):
        return {}
    result: dict[str, list[dict[str, Any]]] = {}
    for project_id, rows in raw.items():
        if isinstance(rows, list):
            result[str(project_id)] = [
                dict(item or {}) for item in rows if isinstance(item, dict)
            ]
    return result


def _quick_add_products_for_project(st: Any, project_id: str) -> list[dict[str, Any]]:
    return list(_quick_add_products_by_project(st).get(project_id, []))


def _apply_deterministic_pricing(
    st: Any,
    record: ProjectWorkspaceRecord,
    *,
    bom_rows: list[dict[str, Any]],
    product_resolutions: list[Any],
    estimate: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    preferred_vendor_policy = _pricing_policy(st)
    project_quotes = _pricing_quotes(st)
    generic_allowances = _pricing_allowances(st)
    commercial_state = _commercial_knowledge_state(st)
    quick_add_products = _quick_add_products_for_project(st, record.project.project_id)

    resolution_rows = [
        item.to_dict() if hasattr(item, "to_dict") else dict(item or {})
        for item in list(product_resolutions or [])
    ]
    signature_payload = {
        "project_id": record.project.project_id,
        "estimate": estimate.to_dict() if hasattr(estimate, "to_dict") else {},
        "resolutions": resolution_rows,
        "commercial_state": commercial_state,
        "preferred_vendor_policy": preferred_vendor_policy,
        "project_quotes": project_quotes,
        "generic_allowances": generic_allowances,
        "quick_add_products": quick_add_products,
    }
    signature = hashlib.sha1(
        json.dumps(signature_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    cache_key = "atlas_deterministic_pricing_cache"
    cached = st.session_state.get(cache_key)
    if isinstance(cached, dict) and cached.get("signature") == signature:
        cost_result = dict(cached.get("result") or {})
    else:
        engine = DeterministicCostEngine()
        cost_result = engine.run(
            estimate=estimate,
            product_resolutions=product_resolutions,
            commercial_state=commercial_state,
            project_id=record.project.project_id,
            preferred_vendor_policy=preferred_vendor_policy,
            project_quotes=project_quotes,
            allowances=generic_allowances,
            quick_add_products=quick_add_products,
        ).to_dict()
        st.session_state[cache_key] = {"signature": signature, "result": cost_result}

    st.session_state["atlas_last_cost_result"] = cost_result

    priced_lines = []
    for item in list(cost_result.get("lines") or []):
        confidence = dict(item.get("confidence") or {})
        selection = dict(item.get("selection") or {})
        status = _safe_text(item.get("status"), "missing")
        priced_lines.append(
            {
                "estimate_line_id": item.get("estimate_line_id"),
                "source_equipment_id": item.get("equipment_object_id"),
                "canonical_product_id": item.get("resolved_product_id"),
                "selected_price_record_id": item.get("price_record_id"),
                "selected_vendor_offering_id": item.get("vendor_offering_id"),
                "selected_price_sheet_version_id": item.get("price_sheet_version_id"),
                "unit_cost": item.get("unit_cost"),
                "extended_cost": item.get("extended_cost"),
                "currency": item.get("currency"),
                "pricing_status": status,
                "pricing_confidence": confidence.get("score"),
                "selection_method": selection.get("method"),
                "selection_reason": selection.get("reason"),
                "effective_date": item.get("effective_date"),
                "expiration_date": item.get("expiration_date"),
                "import_date": item.get("import_date"),
                "days_since_import": item.get("days_since_import"),
                "freshness_status": item.get("freshness"),
                "warnings": [
                    {"code": "cost_warning", "message": warning, "severity": "warning"}
                    for warning in list(item.get("warnings") or [])
                ],
                "source_refs": [
                    {
                        "vendor": item.get("vendor"),
                        "vendor_type": item.get("vendor_type"),
                        "price_sheet_version_id": item.get("price_sheet_version_id"),
                        "price_record_id": item.get("price_record_id"),
                        "source_file": item.get("source_file"),
                        "source_row": item.get("source_row"),
                    }
                ],
                "selection": {
                    "selected_candidate_id": selection.get("selected_candidate_id"),
                    "selection_method": selection.get("method"),
                    "selection_reason": selection.get("reason"),
                    "candidates": list(selection.get("candidates") or []),
                    "applied_rules": [
                        {
                            "rule_id": f"decision:{index + 1}",
                            "name": "Cost decision trace",
                            "priority": index + 1,
                            "matched": True,
                            "detail": detail,
                        }
                        for index, detail in enumerate(
                            list(selection.get("decision_trace") or [])
                        )
                    ],
                },
                "confidence_rationale": list(confidence.get("rationale") or []),
            }
        )

    pricing_result = {
        "pricing_run_id": cost_result.get("cost_run_id"),
        "run_timestamp": cost_result.get("run_timestamp"),
        "pricing_policy_version": cost_result.get("cost_policy_version"),
        "priced_lines": priced_lines,
        "summary": dict(
            (cost_result.get("summary") or {}).get("project_summary") or {}
        ),
        "commercial_coverage": dict(cost_result.get("commercial_coverage") or {}),
    }
    st.session_state["atlas_last_pricing_result"] = pricing_result

    by_source_id = {
        _safe_text(item.get("source_equipment_id"), ""): item
        for item in list(pricing_result.get("priced_lines") or [])
    }

    enriched_rows: list[dict[str, Any]] = []
    for row in bom_rows:
        source_id = _safe_text(
            row.get("bom_item_id"),
            _safe_text(row.get("equipment_id"), ""),
        )
        priced = dict(by_source_id.get(source_id) or {})
        entry = dict(row)
        entry["det_cost_status"] = priced.get("pricing_status")
        entry["det_acquisition_cost"] = priced.get("unit_cost")
        entry["det_cost_extended"] = priced.get("extended_cost")
        entry["det_cost_confidence"] = priced.get("pricing_confidence")
        entry["det_vendor_type"] = _safe_text(
            ((priced.get("source_refs") or [{}])[0]).get("vendor_type"),
            "",
        )
        entry["det_source_file"] = _safe_text(
            ((priced.get("source_refs") or [{}])[0]).get("source_file"),
            "",
        )
        entry["det_source_row"] = ((priced.get("source_refs") or [{}])[0]).get(
            "source_row"
        )
        entry["det_pricing_status"] = priced.get("pricing_status")
        entry["det_selected_unit_cost"] = priced.get("unit_cost")
        entry["det_extended_cost"] = priced.get("extended_cost")
        entry["det_pricing_confidence"] = priced.get("pricing_confidence")
        entry["det_freshness_status"] = priced.get("freshness_status")
        entry["det_selection_reason"] = priced.get("selection_reason")
        entry["det_selection_method"] = priced.get("selection_method")
        entry["det_selected_price_record_id"] = priced.get("selected_price_record_id")
        entry["det_selected_price_sheet_version_id"] = priced.get(
            "selected_price_sheet_version_id"
        )
        entry["det_selected_vendor_offering_id"] = priced.get(
            "selected_vendor_offering_id"
        )
        entry["det_pricing_warnings"] = ", ".join(
            warning.get("code", "")
            for warning in list(priced.get("warnings") or [])
            if isinstance(warning, dict)
        )
        enriched_rows.append(entry)

    return enriched_rows, pricing_result


def _resolution_summary_rows(resolutions: list[Any]) -> dict[str, int]:
    summary = {
        "resolved_products": 0,
        "unknown_products": 0,
        "generic_allowances": 0,
        "substitutions": 0,
        "requires_review": 0,
    }
    for item in resolutions:
        status = _normalized_resolution_status(item)
        confidence = float(getattr(item, "resolution_confidence", 0.0) or 0.0)

        if status in {
            "exact_product",
            "approved_substitute",
            "preferred_alternate",
        }:
            summary["resolved_products"] += 1
        if status == "unknown_product":
            summary["unknown_products"] += 1
        if status == "generic_allowance":
            summary["generic_allowances"] += 1
        if status in {"approved_substitute", "preferred_alternate"}:
            summary["substitutions"] += 1
        if status in {"unknown_product", "generic_allowance"} or confidence < 0.75:
            summary["requires_review"] += 1
    return summary


def _normalized_resolution_status(item: Any) -> str:
    raw_status = getattr(item, "resolution_status", "")
    value = getattr(raw_status, "value", raw_status)
    return _safe_text(value, "").replace("ProductResolutionStatus.", "").lower()


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
    st.session_state.setdefault(
        "atlas_price_list_library", _default_price_list_library_state()
    )
    st.session_state.setdefault("atlas_price_list_signature", "")
    st.session_state.setdefault("atlas_review_flags", {})
    st.session_state.setdefault("atlas_equipment_origin", {})
    st.session_state.setdefault("atlas_recently_viewed_objects", [])
    st.session_state.setdefault("atlas_pinned_objects", [])
    st.session_state.setdefault("atlas_recent_search_queries", [])
    st.session_state.setdefault("atlas_recent_opened_results", [])
    st.session_state.setdefault("atlas_product_resolution_overrides", {})
    st.session_state.setdefault("atlas_product_resolution_cache", {})
    st.session_state.setdefault("atlas_quick_add_products", {})
    st.session_state.setdefault("atlas_global_search_open", False)
    st.session_state.setdefault("atlas_active_project_name", "")
    st.session_state.setdefault(
        "atlas_os",
        "macos" if platform.system().lower() == "darwin" else "other",
    )


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
    active_id = st.session_state.get("atlas_active_workspace_id")
    if not active_id:
        return

    exists = any(
        item.workspace_id == active_id
        for item in workspace_service.list_workspaces(include_archived=True, limit=2000)
    )
    if not exists:
        st.session_state["atlas_active_workspace_id"] = None
        st.session_state["atlas_active_page"] = "Mission Control"


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


def _navigation_groups(
    record: ProjectWorkspaceRecord | None,
) -> list[tuple[str, list[tuple[str, str]]]]:
    if record is None:
        return APPLICATION_NAV_GROUPS
    return PROJECT_NAV_GROUPS


def _group_for_page(page: str, record: ProjectWorkspaceRecord | None) -> str:
    if record is None:
        for group_name, entries in APPLICATION_NAV_GROUPS:
            if page in [item[1] for item in entries]:
                return group_name
        return "Application Workspace"

    for group_name, entries in PROJECT_NAV_GROUPS:
        if page in [item[1] for item in entries]:
            return group_name

    if page == "Mission Control":
        return "Mission Control"
    if page in WORKFLOW_PAGES:
        return "Workflow"
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
        return "Advanced"
    if page in KNOWLEDGE_PAGES:
        return "Advanced"
    if page in BID_INTELLIGENCE_PAGES:
        return "Advanced"
    if page in REPORT_PAGES:
        return "Reports"
    if page in SETTINGS_PAGES:
        return "Advanced"
    return "Project Workspace"


def _breadcrumb_page_label(page: str) -> str:
    mapping = {
        "Project Metadata": "Project Settings",
        "Workspace Settings": "Workspace Settings",
        "Relationship Visualization": "Relationship Graph",
        "RFI Candidates": "RFI Candidates",
    }
    return mapping.get(page, page)


def _breadcrumb(record: ProjectWorkspaceRecord | None, page: str) -> str:
    page_label = _breadcrumb_page_label(page)
    if record is None:
        return f"Atlas / {page_label}"
    if page in {
        "Projects",
        "Pinned Projects",
        "Reference Projects",
        "Recent Projects",
        "Create New Project",
        "Open Existing Project",
    }:
        return f"Atlas / Projects / {page_label}"
    if page in {"Mission Control", "Reports", "Administration"}:
        return f"Atlas / {page_label}"

    st_module: Any | None = None
    try:
        import streamlit as _st

        st_module = _st
    except Exception:
        st_module = None

    selection = (
        dict(st_module.session_state.get("atlas_context_selection") or {})
        if st_module is not None
        else {}
    )
    kind = _safe_text(selection.get("kind"), "")
    data = dict(selection.get("data") or {})
    object_pages = {
        "Equipment": "equipment",
        "Drawings": "drawing",
        "Specifications": "specification",
    }
    expected_kind = object_pages.get(page)
    if expected_kind is not None and kind == expected_kind:
        name = _object_display_name(kind, data)
        return f"Atlas / Projects / {record.project.name} / {page_label} / {name}"

    if page == "Knowledge":
        knowledge_segments = {
            "manufacturer": "Manufacturers",
            "vendor": "Vendors",
            "customer": "Customers",
            "master_product": "Products",
            "price_list": "Price Lists",
        }
        segment = knowledge_segments.get(kind)
        if segment:
            name = _object_display_name(kind, data)
            return f"Atlas / Knowledge / {segment} / {name}"
        return "Atlas / Knowledge"

    return f"Atlas / Projects / {record.project.name} / {page_label}"


def _build_project_context_header(
    record: ProjectWorkspaceRecord,
    *,
    customer: str,
    confidence: str,
    recommended_next_action: str,
) -> ProjectContextHeader:
    return ProjectContextHeader(
        project_name=record.project.name,
        customer=customer,
        lifecycle_stage=_project_stage(record),
        current_status=_safe_text(record.metadata.get("status"), "needs review")
        .replace("_", " ")
        .title(),
        last_analysis=_safe_text(record.updated_at, "Not available"),
        confidence=confidence,
        recommended_next_action=recommended_next_action,
    )


def _render_project_context_header(st: Any, header: ProjectContextHeader) -> None:
    st.markdown(
        "<div class='atlas-project-header'>"
        f"<div class='atlas-project-name'>{header.project_name}</div>"
        f"<div class='atlas-project-customer'>{header.customer}</div>"
        f"<span class='atlas-chip'>{header.lifecycle_stage}</span>"
        f"<span class='atlas-chip'>{header.current_status}</span>"
        f"<div class='atlas-project-meta'>Last analysis: {header.last_analysis} · Confidence: {header.confidence}</div>"
        f"<div class='atlas-project-meta'>Recommended next action: {header.recommended_next_action}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def _open_project_record(st: Any, record: ProjectWorkspaceRecord) -> None:
    st.session_state["atlas_active_workspace_id"] = record.workspace_id
    st.session_state["atlas_active_page"] = "Overview"
    st.rerun()


def _project_review_status(
    record: ProjectWorkspaceRecord,
    manifest: dict[str, Any],
) -> str:
    readiness = _safe_text(record.review_summary.get("readiness_level"), "")
    if readiness:
        return readiness.replace("_", " ").title()
    review_artifacts = sum(
        int(value)
        for value in dict(manifest.get("review_artifact_counts") or {}).values()
    )
    if review_artifacts == 0:
        return "Not Started"
    return "Needs Review"


def _project_library_rows(
    workspace_service: ProjectWorkspaceService,
    *,
    include_archived: bool,
    limit: int = 500,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in workspace_service.list_workspaces(
        include_archived=include_archived,
        limit=limit,
    ):
        manifest = workspace_service.read_manifest(record.workspace_id)
        document_count = sum(
            int(value) for value in dict(manifest.get("document_counts") or {}).values()
        )
        rows.append(
            {
                "record": record,
                "workspace_id": record.workspace_id,
                "project_name": record.project.name,
                "customer": _safe_text(
                    record.metadata.get("owner"), record.project.client
                ),
                "lifecycle_stage": _safe_text(
                    record.metadata.get("lifecycle_stage"),
                    _project_stage(record),
                )
                .replace("_", " ")
                .title(),
                "current_status": _safe_text(
                    record.metadata.get("status"),
                    record.project.status.value,
                )
                .replace("_", " ")
                .title(),
                "last_opened": _safe_text(
                    record.last_opened_at,
                    _safe_text(record.metadata.get("last_opened"), "n/a"),
                ),
                "last_modified": _safe_text(
                    record.metadata.get("last_modified"),
                    record.updated_at,
                ),
                "document_count": document_count,
                "review_status": _project_review_status(record, manifest),
                "reference": record.is_reference,
                "archived": record.archived,
                "pinned": record.pinned,
                "source": record.source_label,
            }
        )
    return rows


def _open_project_from_local_path(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    path_text: str,
) -> None:
    path = Path(path_text).expanduser()
    if not path.exists():
        st.error(f"Path not found: {path}")
        return

    if path.is_dir() and (path / "project.json").exists():
        _open_project_record(st, workspace_service.load_record(path / "project.json"))
        return

    if path.is_dir() and (path / "workspace.json").exists():
        _open_project_record(st, workspace_service.load_record(path / "workspace.json"))
        return

    if path.name in {"workspace.json", "project.json", "metadata.json"}:
        _open_project_record(st, workspace_service.load_record(path))
        return

    if path.name == "intake_snapshot.json":
        context = build_intake_review_context(path)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        _open_project_record(st, record)
        return

    if path.is_dir():
        context = build_reference_project_context(path)
        record = _build_record_from_context(context)
        workspace_service.save_record(record)
        _open_project_record(st, record)
        return

    st.error(
        "Open a project.json/workspace.json file, intake_snapshot.json file, or project folder."
    )


def _keyboard_shortcut_label(st: Any) -> str:
    return (
        "Cmd+K"
        if _safe_text(st.session_state.get("atlas_os"), "macos") == "macos"
        else "Ctrl+K"
    )


def _render_global_search_control(st: Any, host: Any) -> None:
    host.text_input(
        "Global Object Search",
        key="atlas_global_search",
        placeholder="Search projects, equipment, drawings, specs, systems, rooms, RFIs, risks, manufacturers, products...",
    )
    control_cols = host.columns([1, 1])
    if control_cols[0].button(
        "Open Search",
        key="atlas_open_global_search",
        use_container_width=True,
    ):
        st.session_state["atlas_global_search_open"] = True
    if control_cols[1].button(
        "Close",
        key="atlas_close_global_search",
        use_container_width=True,
    ):
        st.session_state["atlas_global_search_open"] = False
        st.session_state["atlas_global_search"] = ""

    host.caption(
        f"Shortcut: {_keyboard_shortcut_label(st)} to focus/open search where supported. Press Esc to close search."
    )


def _render_header_history_popover(
    st: Any,
    workspace_service: ProjectWorkspaceService,
) -> None:
    popover = st.popover("History")
    popover.markdown("#### Recently Viewed")
    recent = list(st.session_state.get("atlas_recently_viewed_objects") or [])
    if recent:
        labels = [
            f"{_safe_text(item.get('object_type'), '')}: {_safe_text(item.get('display_name'), '')}"
            for item in recent[:8]
        ]
        selected_label = popover.selectbox(
            "Open recent",
            options=labels,
            key="atlas_header_recent_open",
        )
        selected = recent[:8][labels.index(selected_label)]
        if popover.button(
            "Open",
            key="atlas_header_open_recent",
            use_container_width=True,
        ):
            _open_search_reference(st, workspace_service, selected)
    else:
        popover.caption("No recently viewed objects.")

    popover.markdown("#### Working Set")
    working_set = _working_set(st)
    if working_set:
        labels = [
            f"{_safe_text(item.get('object_type'), '')}: {_safe_text(item.get('display_name'), '')}"
            for item in working_set[:8]
        ]
        selected_label = popover.selectbox(
            "Open working set object",
            options=labels,
            key="atlas_header_working_set_open",
        )
        selected = working_set[:8][labels.index(selected_label)]
        if popover.button(
            "Open Working Set Object",
            key="atlas_header_open_working_set",
            use_container_width=True,
        ):
            _open_search_reference(st, workspace_service, selected)
    else:
        popover.caption("Working Set is empty.")


def _render_header(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord | None,
    context: dict[str, Any] | None,
) -> None:
    records = workspace_service.list_workspaces(include_archived=True, limit=200)
    current_page = _safe_text(
        st.session_state.get("atlas_active_page"), "Mission Control"
    )

    header_cols = st.columns([1.1, 2.0, 2.8, 1.6])
    if header_cols[0].button("Atlas", use_container_width=True, type="secondary"):
        st.session_state["atlas_active_page"] = "Mission Control"
        st.rerun()

    _render_global_search_control(st, header_cols[2])

    if record is None:
        st.session_state["atlas_active_project_name"] = ""
        header_cols[1].caption(f"Application Workspace · {current_page}")
        if header_cols[3].button("Open Projects", use_container_width=True):
            st.session_state["atlas_active_page"] = "Projects"
            st.rerun()
        _render_header_history_popover(st, workspace_service)
        return

    summary = _build_project_analysis_summary(record, context)
    st.session_state["atlas_active_project_name"] = record.project.name
    next_action = _next_review_action(_review_step_status_rows(st, record, context))
    review = context.get("review") if context else None
    confidence = getattr(review, "confidence", None)
    confidence_text = "n/a"
    if isinstance(confidence, (int, float)):
        confidence_text = f"{int(confidence * 100)}%"
    elif confidence is not None:
        confidence_text = _safe_text(confidence, "n/a")

    selector_options = {
        f"{item.project.name} · {item.workspace_id}": item for item in records
    }
    if selector_options:
        active_label = next(
            (
                label
                for label, item in selector_options.items()
                if item.workspace_id == record.workspace_id
            ),
            None,
        )
        selected_label = header_cols[1].selectbox(
            "Project",
            options=list(selector_options.keys()),
            index=(
                list(selector_options.keys()).index(active_label)
                if active_label in selector_options
                else 0
            ),
            key="atlas_header_project_selector",
        )
        selected_record = selector_options.get(selected_label)
        if (
            selected_record is not None
            and selected_record.workspace_id != record.workspace_id
        ):
            _open_project_record(st, selected_record)
    else:
        header_cols[1].caption("Project selector unavailable.")

    if header_cols[3].button("Back to Projects", use_container_width=True):
        st.session_state["atlas_active_page"] = "Projects"
        st.rerun()

    _render_header_history_popover(st, workspace_service)

    project_header = _build_project_context_header(
        record,
        customer=_safe_text(summary.get("customer"), "Not available"),
        confidence=confidence_text,
        recommended_next_action=_safe_text(
            next_action.get("step"),
            "Review project overview",
        ),
    )
    _render_project_context_header(st, project_header)

    if st.button(
        f"Recommended Next: {_safe_text(next_action.get('step'), 'Review project overview')}",
        type="primary",
        use_container_width=True,
    ):
        st.session_state["atlas_active_page"] = _safe_text(
            next_action.get("page"),
            "Overview",
        )
        st.rerun()


def _nav_buttons(
    st: Any,
    host: Any,
    mode: str,
    record: ProjectWorkspaceRecord | None,
) -> None:
    active_page = st.session_state.get("atlas_active_page", "Mission Control")
    nav_groups = (
        APPLICATION_NAV_GROUPS
        if active_page == "Mission Control"
        else _navigation_groups(record)
    )

    if record is not None and active_page != "Mission Control":
        host.markdown("### Active Project")
        host.caption("Project workspace")
        host.markdown("---")

    for group_name, entries in nav_groups:
        with host.expander(
            group_name,
            expanded=active_page in [item[1] for item in entries],
        ):
            for label, page in entries:
                is_future_disabled = page in DISABLED_LIFECYCLE_PAGES
                if host.button(
                    label,
                    key=f"atlas_nav_{mode}_{group_name}_{label}_{page}",
                    type="primary" if active_page == page else "secondary",
                    disabled=is_future_disabled,
                    use_container_width=True,
                ):
                    st.session_state["atlas_active_page"] = page
                    st.rerun()
                if is_future_disabled:
                    host.caption(f"{label} is reserved for future lifecycle scope.")


def _render_object_metadata_table(
    st: Any,
    title: str,
    rows: list[dict[str, Any]],
) -> None:
    st.markdown(f"### {title}")
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_object_reference_sections(
    st: Any,
    *,
    record: ProjectWorkspaceRecord,
    graph: dict[str, Any],
    kind: str,
    selected: dict[str, Any],
    key_prefix: str,
) -> None:
    st.markdown("### References and Referenced By")
    references, referenced_by = _reference_groups_for_selection(
        record,
        graph,
        kind,
        selected,
    )
    reference_cols = st.columns(2)
    with reference_cols[0]:
        _render_reference_group(
            st,
            title="References",
            references=references,
            empty_message=f"This {_object_type_label(kind).lower()} has no outgoing references yet.",
            key_prefix=f"{key_prefix}_refs",
        )
    with reference_cols[1]:
        _render_reference_group(
            st,
            title="Referenced By",
            references=referenced_by,
            empty_message=f"No objects currently reference this {_object_type_label(kind).lower()}.",
            key_prefix=f"{key_prefix}_refby",
        )


def _object_recommended_actions(
    kind: str, data: dict[str, Any]
) -> list[dict[str, str]]:
    if kind == "equipment":
        return _equipment_recommended_actions(data)

    warnings = list(data.get("warnings") or [])
    has_links = any(
        list(data.get(field) or [])
        for field in [
            "referenced_equipment",
            "referenced_specifications",
            "referenced_drawings",
            "referenced_systems",
            "referenced_evidence",
        ]
    )

    actions: list[dict[str, str]] = []
    if warnings:
        actions.append(
            {
                "priority": "High",
                "action": "Review warnings and evidence",
                "destination": "Evidence",
                "reason": "Warnings indicate unresolved review context for this object.",
            }
        )
    if not has_links:
        actions.append(
            {
                "priority": "Medium",
                "action": "Validate cross-object references",
                "destination": "Relationships",
                "reason": "No connected objects were detected for this item.",
            }
        )
    if not actions:
        actions.append(
            {
                "priority": "Low",
                "action": "Continue review",
                "destination": "Relationships",
                "reason": "Object has linked context and no active warnings.",
            }
        )
    return actions


def _object_type_label(kind: str) -> str:
    mapping = {
        "equipment": "Equipment",
        "drawing": "Drawing",
        "specification": "Specification",
        "system": "System",
        "room": "Room",
        "risk": "Risk / Finding",
        "rfi": "RFI Candidate",
        "evidence": "Evidence",
        "manufacturer": "Manufacturer",
        "vendor": "Vendor",
        "customer": "Customer",
        "price_list": "Price List",
        "project_record": "Project",
        "notebook_entry": "Notebook Entry",
        "master_product": "Product",
        "model": "Product",
    }
    return mapping.get(kind, kind.replace("_", " ").title())


def _object_id_for_selection(kind: str, data: dict[str, Any]) -> str:
    if kind == "equipment":
        return _safe_text(data.get("equipment_id"), "")
    if kind == "drawing":
        return _safe_text(data.get("drawing_number"), "")
    if kind == "specification":
        return _safe_text(data.get("section"), "")
    if kind == "system":
        return _safe_text(data.get("system"), "")
    if kind == "room":
        return _safe_text(data.get("room"), _safe_text(data.get("room_or_area"), ""))
    if kind == "rfi":
        return _safe_text(data.get("rfi_id"), _safe_text(data.get("title"), ""))
    if kind == "evidence":
        source_file = _safe_text(data.get("source_file"), "file")
        page = _safe_text(data.get("page"), "n/a")
        return f"{source_file}:{page}"
    if kind == "manufacturer":
        return _safe_text(data.get("manufacturer"), "")
    if kind == "vendor":
        return _safe_text(data.get("vendor"), _safe_text(data.get("name"), ""))
    if kind == "customer":
        return _safe_text(data.get("customer"), "")
    if kind == "price_list":
        return _safe_text(data.get("source_file"), "Price List")
    if kind == "project_record":
        return _safe_text(data.get("workspace_id"), "")
    if kind == "notebook_entry":
        return _safe_text(data.get("entry_id"), _safe_text(data.get("title"), ""))
    if kind == "master_product":
        return _safe_text(
            data.get("atlas_product_uuid"),
            _safe_text(data.get("product_id"), _safe_text(data.get("model"), "")),
        )
    return _safe_text(data.get("object_id"), "")


def _object_display_name(kind: str, data: dict[str, Any]) -> str:
    if kind == "equipment":
        manufacturer = _safe_text(data.get("manufacturer"), "")
        model = _safe_text(data.get("model"), "")
        equipment_id = _safe_text(data.get("equipment_id"), "Equipment")
        merged = " ".join([part for part in [manufacturer, model] if part]).strip()
        return merged or equipment_id
    if kind == "drawing":
        return _safe_text(data.get("drawing_number"), "Drawing")
    if kind == "specification":
        return _safe_text(data.get("section"), "Specification")
    if kind == "system":
        return _safe_text(data.get("system"), "System")
    if kind == "room":
        return _safe_text(
            data.get("room"), _safe_text(data.get("room_or_area"), "Room")
        )
    if kind == "rfi":
        return _safe_text(data.get("title"), _safe_text(data.get("rfi_id"), "RFI"))
    if kind == "evidence":
        return _safe_text(data.get("source_file"), "Evidence")
    if kind == "manufacturer":
        return _safe_text(data.get("manufacturer"), "Manufacturer")
    if kind == "vendor":
        return _safe_text(data.get("vendor"), _safe_text(data.get("name"), "Vendor"))
    if kind == "customer":
        return _safe_text(data.get("customer"), "Customer")
    if kind == "price_list":
        return _safe_text(data.get("source_file"), "Price List")
    if kind == "project_record":
        return _safe_text(data.get("project_name"), "Project")
    if kind == "notebook_entry":
        return _safe_text(data.get("title"), "Notebook Entry")
    if kind == "master_product":
        model = _safe_text(
            data.get("canonical_sku"), _safe_text(data.get("model"), "Product")
        )
        manufacturer = _safe_text(data.get("manufacturer"), "")
        return (
            " ".join([item for item in [manufacturer, model] if item]).strip()
            or "Product"
        )
    return _safe_text(data.get("title"), _safe_text(data.get("object_id"), "Object"))


def _object_secondary_label(kind: str, data: dict[str, Any]) -> str:
    if kind == "equipment":
        return _safe_text(data.get("description"), "")
    if kind == "drawing":
        return _safe_text(data.get("title"), "")
    if kind == "specification":
        return _safe_text(data.get("title"), "")
    if kind == "system":
        return f"equipment {_safe_text(data.get('equipment_count'), 'n/a')}"
    if kind == "room":
        return _safe_text(data.get("system"), "")
    if kind == "rfi":
        return _safe_text(data.get("category"), "")
    if kind == "evidence":
        return f"page {_safe_text(data.get('page'), 'n/a')}"
    if kind == "master_product":
        lifecycle = _safe_text(
            data.get("lifecycle_status"), _safe_text(data.get("status"), "")
        )
        vendor = _safe_text(data.get("vendor"), "")
        confidence = _safe_text(
            dict(data.get("confidence") or data.get("confidence_summary") or {}).get(
                "overall_confidence"
            ),
            "",
        )
        return " | ".join(
            [
                item
                for item in [
                    lifecycle,
                    vendor,
                    f"confidence {confidence}" if confidence else "",
                ]
                if item
            ]
        )
    if kind == "vendor":
        return _safe_text(data.get("vendor_type"), _safe_text(data.get("status"), ""))
    if kind == "customer":
        return _safe_text(data.get("portfolio"), "")
    if kind == "price_list":
        return _safe_text(data.get("vendor"), _safe_text(data.get("manufacturer"), ""))
    if kind == "project_record":
        return _safe_text(data.get("customer"), "")
    if kind == "notebook_entry":
        return _safe_text(data.get("entry_type"), "")
    return ""


def _selection_route(kind: str) -> str:
    mapping = {
        "equipment": "Equipment",
        "drawing": "Drawings",
        "specification": "Specifications",
        "system": "Systems",
        "room": "Equipment",
        "rfi": "RFI Candidates",
        "evidence": "Evidence",
        "manufacturer": "Master Library Explorer",
        "vendor": "Knowledge",
        "customer": "Knowledge",
        "price_list": "Knowledge",
        "project_record": "Overview",
        "notebook_entry": "Notebook",
        "master_product": "Master Library Explorer",
    }
    return mapping.get(kind, "Overview")


def _build_object_reference(
    *,
    kind: str,
    data: dict[str, Any],
    project_id: str,
    project_name: str | None = None,
    route: str,
    relationship_count: int = 0,
    warning_count: int = 0,
) -> dict[str, Any]:
    status = _safe_text(
        data.get("completeness_status"),
        _safe_text(data.get("status"), _safe_text(data.get("current_status"), "n/a")),
    )
    confidence_value = data.get("confidence")
    confidence_text = (
        str(round(float(confidence_value), 2))
        if isinstance(confidence_value, (int, float))
        else _safe_text(confidence_value, "n/a")
    )
    source_refs = list(data.get("source_documents") or [])
    if not source_refs and kind == "evidence":
        source_refs = [_safe_text(data.get("source_file"), "")]
    return {
        "object_id": _object_id_for_selection(kind, data),
        "object_type": _object_type_label(kind),
        "display_name": _object_display_name(kind, data),
        "secondary_label": _object_secondary_label(kind, data),
        "status": status,
        "confidence": confidence_text,
        "project_id": project_id,
        "project_name": _safe_text(project_name, project_id),
        "route": route,
        "source_refs": [item for item in source_refs if _safe_text(item, "")],
        "relationship_count": int(relationship_count),
        "warning_count": int(warning_count),
        "selection_kind": kind,
        "selection_data": dict(data),
    }


def _track_recently_viewed(st: Any, reference: dict[str, Any]) -> None:
    object_id = _safe_text(reference.get("object_id"), "")
    object_type = _safe_text(reference.get("object_type"), "")
    if not object_id or not object_type:
        return
    existing = list(st.session_state.get("atlas_recently_viewed_objects") or [])
    filtered = [
        item
        for item in existing
        if not (
            _safe_text(item.get("object_id"), "") == object_id
            and _safe_text(item.get("object_type"), "") == object_type
        )
    ]
    entry = dict(reference)
    entry["last_viewed_at"] = _now_iso()
    filtered.insert(0, entry)
    st.session_state["atlas_recently_viewed_objects"] = filtered[:30]


def _working_set(st: Any) -> list[dict[str, Any]]:
    return list(st.session_state.get("atlas_pinned_objects") or [])


def _toggle_pin_reference(st: Any, reference: dict[str, Any], should_pin: bool) -> None:
    object_id = _safe_text(reference.get("object_id"), "")
    object_type = _safe_text(reference.get("object_type"), "")
    if not object_id or not object_type:
        return
    existing = list(st.session_state.get("atlas_pinned_objects") or [])
    filtered = [
        item
        for item in existing
        if not (
            _safe_text(item.get("object_id"), "") == object_id
            and _safe_text(item.get("object_type"), "") == object_type
        )
    ]
    if should_pin:
        filtered.insert(0, dict(reference))
    st.session_state["atlas_pinned_objects"] = filtered[:40]


def _move_working_set_item(
    st: Any,
    *,
    object_id: str,
    object_type: str,
    direction: int,
) -> None:
    items = _working_set(st)
    index = next(
        (
            i
            for i, item in enumerate(items)
            if _safe_text(item.get("object_id"), "") == object_id
            and _safe_text(item.get("object_type"), "") == object_type
        ),
        None,
    )
    if index is None:
        return
    target = index + direction
    if target < 0 or target >= len(items):
        return
    items[index], items[target] = items[target], items[index]
    st.session_state["atlas_pinned_objects"] = items


def _record_recent_search_query(st: Any, query: str) -> None:
    normalized = query.strip()
    if len(normalized) < 2:
        return
    existing = [
        str(item)
        for item in list(st.session_state.get("atlas_recent_search_queries") or [])
    ]
    deduped = [item for item in existing if item.lower() != normalized.lower()]
    deduped.insert(0, normalized)
    st.session_state["atlas_recent_search_queries"] = deduped[:12]


def _record_recent_search_open(st: Any, reference: dict[str, Any]) -> None:
    object_id = _safe_text(reference.get("object_id"), "")
    object_type = _safe_text(reference.get("object_type"), "")
    if not object_id or not object_type:
        return
    existing = list(st.session_state.get("atlas_recent_opened_results") or [])
    filtered = [
        item
        for item in existing
        if not (
            _safe_text(item.get("object_id"), "") == object_id
            and _safe_text(item.get("object_type"), "") == object_type
        )
    ]
    updated = dict(reference)
    updated["last_opened_at"] = _now_iso()
    filtered.insert(0, updated)
    st.session_state["atlas_recent_opened_results"] = filtered[:15]


def _is_reference_pinned(st: Any, reference: dict[str, Any]) -> bool:
    object_id = _safe_text(reference.get("object_id"), "")
    object_type = _safe_text(reference.get("object_type"), "")
    for item in list(st.session_state.get("atlas_pinned_objects") or []):
        if (
            _safe_text(item.get("object_id"), "") == object_id
            and _safe_text(item.get("object_type"), "") == object_type
        ):
            return True
    return False


def _set_context_selection(st: Any, kind: str, data: dict[str, Any]) -> None:
    st.session_state["atlas_context_selection"] = {"kind": kind, "data": data}
    if kind not in {
        "equipment",
        "drawing",
        "specification",
        "system",
        "room",
        "rfi",
        "evidence",
        "manufacturer",
        "vendor",
        "customer",
        "price_list",
        "project_record",
        "master_product",
        "resolver_conflict",
        "resolved",
        "notebook_entry",
    }:
        return

    route = _selection_route(kind)
    project_id = _safe_text(st.session_state.get("atlas_active_workspace_id"), "")
    warnings = list(data.get("warnings") or [])
    reference = _build_object_reference(
        kind=kind,
        data=data,
        project_id=project_id,
        project_name=_safe_text(
            st.session_state.get("atlas_active_project_name"), project_id
        ),
        route=route,
        relationship_count=0,
        warning_count=len(warnings),
    )
    _track_recently_viewed(st, reference)


def _render_object_card(
    st: Any,
    reference: dict[str, Any],
    *,
    key_prefix: str,
) -> None:
    status = _safe_text(reference.get("status"), "n/a")
    confidence = _safe_text(reference.get("confidence"), "n/a")
    relations = int(reference.get("relationship_count", 0) or 0)
    warnings = int(reference.get("warning_count", 0) or 0)
    secondary = _safe_text(reference.get("secondary_label"), "")
    st.markdown(
        "<div class='atlas-object-card'>"
        f"<div class='atlas-object-header'>{_safe_text(reference.get('object_type'), 'Object')}</div>"
        f"{_safe_text(reference.get('display_name'), 'Object')}"
        f"<br/><span class='atlas-muted'>{secondary}</span>"
        f"<br/><span class='atlas-muted'>Status: {status} · Confidence: {confidence} · Links: {relations} · Warnings: {warnings}</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    if cols[0].button(
        f"Open {_safe_text(reference.get('display_name'), 'Object')}",
        key=f"{key_prefix}_open_{_safe_text(reference.get('object_type'), 'obj')}_{_safe_text(reference.get('object_id'), 'id')}",
        use_container_width=True,
    ):
        st.session_state["atlas_active_page"] = _safe_text(
            reference.get("route"), "Overview"
        )
        _set_context_selection(
            st,
            _safe_text(reference.get("selection_kind"), "project")
            .lower()
            .replace(" / ", "_"),
            dict(reference.get("selection_data") or {}),
        )
        st.rerun()

    pinned = _is_reference_pinned(st, reference)
    if cols[1].button(
        "Remove" if pinned else "Add to Working Set",
        key=f"{key_prefix}_pin_{_safe_text(reference.get('object_type'), 'obj')}_{_safe_text(reference.get('object_id'), 'id')}",
        use_container_width=True,
    ):
        _toggle_pin_reference(st, reference, should_pin=not pinned)
        st.rerun()


def _render_object_header(
    st: Any,
    record: ProjectWorkspaceRecord,
    reference: dict[str, Any],
    *,
    description: str,
    recommended_action: str,
) -> None:
    st.markdown(f"#### {_safe_text(reference.get('display_name'), 'Object')}")
    st.caption(description)
    badges = [
        _safe_text(reference.get("object_type"), "Object"),
        _safe_text(reference.get("status"), "n/a").replace("_", " ").title(),
        f"Confidence {_safe_text(reference.get('confidence'), 'n/a')}",
        f"Project {_safe_text(record.project.name, 'Project')}",
    ]
    st.markdown(" ".join([f"`{badge}`" for badge in badges]))
    header_cols = st.columns([5.5, 2.25, 2.25])
    header_cols[0].caption(f"Recommended action: {recommended_action}")
    if header_cols[1].button(
        "Open Estimate Workspace",
        key=f"atlas_object_header_open_estimate_{_safe_text(reference.get('object_type'), 'obj')}_{_safe_text(reference.get('object_id'), 'id')}",
        use_container_width=True,
    ):
        st.session_state["atlas_active_page"] = "Estimate"
        st.rerun()
    pinned = _is_reference_pinned(st, reference)
    if header_cols[2].button(
        "Remove from Working Set" if pinned else "Add to Working Set",
        key=f"atlas_object_header_pin_{_safe_text(reference.get('object_type'), 'obj')}_{_safe_text(reference.get('object_id'), 'id')}",
        use_container_width=True,
    ):
        _toggle_pin_reference(st, reference, should_pin=not pinned)
        st.rerun()


def _open_search_reference(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    reference: dict[str, Any],
) -> None:
    selection_kind = _safe_text(reference.get("selection_kind"), "project")
    selection_data = dict(reference.get("selection_data") or {})
    if selection_kind == "project_record":
        workspace_id = _safe_text(selection_data.get("workspace_id"), "")
        if workspace_id:
            records = {
                item.workspace_id: item
                for item in workspace_service.list_workspaces(
                    include_archived=True,
                    limit=1000,
                )
            }
            selected_record = records.get(workspace_id)
            if selected_record is not None:
                _record_recent_search_open(st, reference)
                _open_project_record(st, selected_record)
                return

    st.session_state["atlas_active_page"] = _safe_text(
        reference.get("route"), "Overview"
    )
    _set_context_selection(st, selection_kind, selection_data)
    _record_recent_search_open(st, reference)
    st.rerun()


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
                str(st.session_state.get("atlas_active_page") or "Mission Control"),
                None,
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
        "review_flags": dict(st.session_state.get("atlas_review_flags") or {}),
        "price_list_library": dict(_price_list_library_state(st)),
        "product_resolution_overrides": dict(
            st.session_state.get("atlas_product_resolution_overrides") or {}
        ),
        "product_resolution_filters": list(
            st.session_state.get("atlas_product_resolution_filters") or []
        ),
        "recently_viewed_objects": list(
            st.session_state.get("atlas_recently_viewed_objects") or []
        ),
        "pinned_objects": list(st.session_state.get("atlas_pinned_objects") or []),
        "recent_search_queries": list(
            st.session_state.get("atlas_recent_search_queries") or []
        ),
        "recent_opened_results": list(
            st.session_state.get("atlas_recent_opened_results") or []
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
    if restored_page == "History":
        restored_page = "Timeline"
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

    review_flags = state.get("review_flags")
    if isinstance(review_flags, dict):
        st.session_state["atlas_review_flags"] = dict(review_flags)

    price_list_library = state.get("price_list_library")
    if isinstance(price_list_library, dict):
        st.session_state["atlas_price_list_library"] = dict(price_list_library)

    product_resolution_overrides = state.get("product_resolution_overrides")
    if isinstance(product_resolution_overrides, dict):
        st.session_state["atlas_product_resolution_overrides"] = dict(
            product_resolution_overrides
        )

    product_resolution_filters = state.get("product_resolution_filters")
    if isinstance(product_resolution_filters, list):
        st.session_state["atlas_product_resolution_filters"] = list(
            product_resolution_filters
        )

    recently_viewed = state.get("recently_viewed_objects")
    if isinstance(recently_viewed, list):
        st.session_state["atlas_recently_viewed_objects"] = list(recently_viewed)

    pinned_objects = state.get("pinned_objects")
    if isinstance(pinned_objects, list):
        st.session_state["atlas_pinned_objects"] = list(pinned_objects)

    recent_search_queries = state.get("recent_search_queries")
    if isinstance(recent_search_queries, list):
        st.session_state["atlas_recent_search_queries"] = list(recent_search_queries)

    recent_opened_results = state.get("recent_opened_results")
    if isinstance(recent_opened_results, list):
        st.session_state["atlas_recent_opened_results"] = list(recent_opened_results)

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
    record: ProjectWorkspaceRecord | None,
    context: dict[str, Any] | None,
    mission_control_payload: dict[str, Any] | None = None,
) -> None:
    _render_page_header(
        st,
        "Mission Control",
        "Application-level workspace for project selection, portfolio awareness, and administration.",
    )

    action_cols = st.columns(3)
    if action_cols[0].button(
        "Create New Project",
        type="primary",
        use_container_width=True,
    ):
        st.session_state["atlas_active_page"] = "Create New Project"
        st.rerun()
    if action_cols[1].button("Open Existing Project", use_container_width=True):
        st.session_state["atlas_active_page"] = "Open Existing Project"
        st.rerun()
    if action_cols[2].button("Manage Projects", use_container_width=True):
        st.session_state["atlas_active_page"] = "Projects"
        st.rerun()

    st.markdown("### Application Areas")
    st.dataframe(
        [
            {"Area": "Mission Control", "Purpose": "Portfolio-level action center."},
            {
                "Area": "Projects",
                "Purpose": "Create, open, and manage project workspaces.",
            },
            {"Area": "Knowledge", "Purpose": "Cross-project references and standards."},
            {"Area": "Reports", "Purpose": "Cross-project reporting and signals."},
            {
                "Area": "Administration",
                "Purpose": "Workspace preferences and repository controls.",
            },
        ],
        use_container_width=True,
        hide_index=True,
    )

    if record is not None:
        summary = _build_project_analysis_summary(record, context)
        st.markdown("### Active Project Snapshot")
        st.dataframe(
            [
                {
                    "Project": summary["project_name"],
                    "Customer": summary["customer"],
                    "Project Type": summary["project_type"],
                    "Analysis Status": summary["analysis_status"],
                    "Recommended Next Action": summary["recommended_next_action"],
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
        if st.button(
            "Open Project Workspace", type="primary", use_container_width=True
        ):
            st.session_state["atlas_active_page"] = "Overview"
            st.rerun()
    else:
        st.info(
            "No project is open. Open a project to enter Project Workspace navigation."
        )

    if mission_control_payload:
        st.markdown("### Portfolio Signals")
        _render_mission_control_panels(st, mission_control_payload)

    st.markdown("### Commercial Knowledge Recommendations")
    recommendations = _commercial_recommendation_rows(st)
    if recommendations:
        st.dataframe(recommendations, use_container_width=True, hide_index=True)
    else:
        st.caption("No deterministic commercial foundation recommendations right now.")


def _render_application_knowledge_page(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    _render_page_header(
        st,
        "Knowledge",
        "Application-wide reusable knowledge. Project-specific review data is intentionally excluded.",
    )

    project_rows = _project_library_rows(
        workspace_service,
        include_archived=True,
        limit=500,
    )
    product_service = _ensure_commercial_seed_data(st)
    manufacturer_rows = product_service.list_manufacturers()
    vendor_rows = product_service.list_vendors()
    customers = sorted(
        {_safe_text(item.get("customer"), "n/a") for item in project_rows}
    )

    product_rows: list[dict[str, Any]] = []
    for item in project_rows:
        record = item["record"]
        try:
            artifact = workspace_service.manager.review_repository.load_artifact(
                record.workspace_id,
                "bid_package_review",
            )
        except Exception:
            artifact = None
        if not isinstance(artifact, dict):
            continue
        equipment_rows = list(artifact.get("equipment") or [])
        if not equipment_rows:
            continue
        service = MasterLibraryService()
        service.import_workspace_equipment(equipment_rows)
        product_rows.extend(service.explorer_rows())

    product_rows.extend(product_service.product_rows(include_project_only=True))

    # Deduplicate by canonical product id.
    deduped_products: dict[str, dict[str, Any]] = {}
    for row in product_rows:
        key = _safe_text(
            row.get("product_id"),
            _safe_text(
                row.get("atlas_product_uuid"),
                f"{_safe_text(row.get('manufacturer'), '')}::{_safe_text(row.get('canonical_sku'), _safe_text(row.get('model'), ''))}",
            ),
        )
        if key and key not in deduped_products:
            deduped_products[key] = row
    product_rows = list(deduped_products.values())

    library_state = _price_list_library_state(st)
    uploaded_price_lists = list(library_state.get("uploaded_price_lists") or [])
    manufacturer_products = list(library_state.get("manufacturer_products") or [])
    vendor_offers = list(library_state.get("vendor_offers") or [])
    commercial_service = _commercial_service(st)
    commercial_dashboard = commercial_service.dashboard_summary()
    product_dashboard = product_service.dashboard_summary()
    commercial_import_history = commercial_service.import_history_rows()

    import_history: list[dict[str, Any]] = []
    for item in project_rows:
        record = item["record"]
        try:
            events = workspace_service.list_history(record.workspace_id, limit=20)
        except Exception:
            events = []
        for event in events:
            event_type = _safe_text(event.get("event_type"), "")
            if event_type in {"project_imported", "documents_imported"}:
                import_history.append(
                    {
                        "project": record.project.name,
                        "project_id": record.workspace_id,
                        "event": event_type.replace("_", " ").title(),
                        "timestamp": _safe_text(event.get("timestamp"), "n/a"),
                    }
                )
    import_history.sort(
        key=lambda row: _safe_text(row.get("timestamp"), ""), reverse=True
    )

    cards = st.columns(8)
    _metric_card(cards[0], "Manufacturers", str(len(manufacturer_rows)))
    _metric_card(cards[1], "Vendors", str(len(vendor_rows)))
    _metric_card(cards[2], "Products", str(commercial_dashboard.get("products", 0)))
    _metric_card(
        cards[3],
        "Vendor Offerings",
        str(commercial_dashboard.get("vendor_offerings", 0)),
    )
    _metric_card(
        cards[4],
        "Active Price Lists",
        str(commercial_dashboard.get("active_price_sheets", 0)),
    )
    _metric_card(
        cards[5],
        "Pricing Stale",
        str(commercial_dashboard.get("pricing_stale", 0)),
    )
    _metric_card(
        cards[6],
        "Missing From Latest",
        str(commercial_dashboard.get("products_missing_from_latest_version", 0)),
    )
    _metric_card(
        cards[7],
        "Avg Confidence",
        str(product_dashboard.get("average_confidence", 0.0)),
    )

    tabs = st.tabs(
        [
            "Summary",
            "Commercial Health",
            "Manufacturers",
            "Vendors",
            "Customers",
            "Products",
            "Price Lists",
            "Imports",
            "Import History",
        ]
    )

    with tabs[0]:
        st.dataframe(
            [
                {
                    "Knowledge Area": "Manufacturers",
                    "State": (
                        "Available" if manufacturer_rows else "Foundation in progress"
                    ),
                    "Why It Matters": "Standardized manufacturer identity supports deterministic product matching.",
                    "Next Action": "Review manufacturer tiers and preferred vendor paths.",
                },
                {
                    "Knowledge Area": "Vendors",
                    "State": "Available" if vendor_rows else "Foundation in progress",
                    "Why It Matters": "Vendor normalization improves price list reconciliation and availability context.",
                    "Next Action": "Review vendor types and active status.",
                },
                {
                    "Knowledge Area": "Customers",
                    "State": "Available" if customers else "Foundation in progress",
                    "Why It Matters": "Customer history supports portfolio-level context and repeatability.",
                    "Next Action": "Import or create projects to populate customer records.",
                },
                {
                    "Knowledge Area": "Products / Master Library",
                    "State": "Available" if product_rows else "Foundation in progress",
                    "Why It Matters": "Canonical products reduce alias ambiguity across projects.",
                    "Next Action": "Run project analysis to generate equipment rows and master product mappings.",
                },
                {
                    "Knowledge Area": "Commercial Knowledge",
                    "State": (
                        "Available"
                        if commercial_dashboard.get("active_price_sheets", 0)
                        else "Foundation in progress"
                    ),
                    "Why It Matters": "Immutable price-sheet versions preserve historical commercial context for deterministic bid recreation.",
                    "Next Action": "Upload manufacturer/vendor price lists and review Import History change reports.",
                },
                {
                    "Knowledge Area": "Knowledge Imports",
                    "State": (
                        "Available" if import_history else "Foundation in progress"
                    ),
                    "Why It Matters": "Import history provides auditability for reusable knowledge.",
                    "Next Action": "Import project packages or document sets to create import events.",
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[1]:
        freshness = commercial_dashboard.get("knowledge_freshness", {})
        st.dataframe(
            [
                {
                    "Manufacturers": commercial_dashboard.get("manufacturers", 0),
                    "Vendors": commercial_dashboard.get("vendors", 0),
                    "Products": commercial_dashboard.get("products", 0),
                    "Vendor Offerings": commercial_dashboard.get("vendor_offerings", 0),
                    "Active Price Sheets": commercial_dashboard.get(
                        "active_price_sheets", 0
                    ),
                    "Latest Imports": len(
                        commercial_dashboard.get("latest_imports") or []
                    ),
                    "Products Missing Pricing": commercial_dashboard.get(
                        "products_missing_pricing", 0
                    ),
                    "Pricing Stale": commercial_dashboard.get("pricing_stale", 0),
                    "Recently Updated": commercial_dashboard.get("recently_updated", 0),
                    "Missing From Latest Version": commercial_dashboard.get(
                        "products_missing_from_latest_version", 0
                    ),
                    "Coverage Percentage": commercial_dashboard.get(
                        "coverage_percentage", 0.0
                    ),
                    "Knowledge Freshness": f"fresh={freshness.get('fresh', 0)} review={freshness.get('review_recommended', 0)} stale={freshness.get('stale', 0)} missing={freshness.get('missing', 0)}",
                    "Commercial Confidence": commercial_dashboard.get(
                        "commercial_confidence", 0.0
                    ),
                    "Active Products": product_dashboard.get("active_products", 0),
                    "Missing Preferred Vendor": product_dashboard.get(
                        "missing_preferred_vendor", 0
                    ),
                    "Recent Price Changes": product_dashboard.get(
                        "recent_price_changes", 0
                    ),
                    "New Products": product_dashboard.get("new_products", 0),
                    "EOL/Obsolete": product_dashboard.get("end_of_life_products", 0),
                    "Replacement Candidates": product_dashboard.get(
                        "replacement_candidates", 0
                    ),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[2]:
        st.markdown("### Manufacturers")
        with st.expander("Add Manufacturer", expanded=False):
            m_cols = st.columns(2)
            m_id = m_cols[0].text_input("Manufacturer ID", key="atlas_ck_mfr_id")
            m_name = m_cols[1].text_input("Canonical Name", key="atlas_ck_mfr_name")
            m_display = m_cols[0].text_input("Display Name", key="atlas_ck_mfr_display")
            m_code = m_cols[1].text_input("Code", key="atlas_ck_mfr_code")
            m_site = st.text_input("Website", key="atlas_ck_mfr_site")
            m_notes = st.text_input("Notes", key="atlas_ck_mfr_notes")
            duplicates = product_service.detect_duplicate_manufacturers(
                canonical_name=m_name,
                normalized_name=product_service.normalize_name(m_name),
            )
            if duplicates:
                st.warning("Potential duplicate manufacturer names detected.")
            if st.button(
                "Create Manufacturer",
                key="atlas_ck_create_manufacturer",
                use_container_width=True,
            ):
                try:
                    product_service.create_manufacturer(
                        manufacturer_id=m_id,
                        canonical_name=m_name,
                        display_name=m_display,
                        manufacturer_code=m_code,
                        website=m_site,
                        notes=m_notes,
                    )
                    _save_commercial_product_state(st, product_service)
                    st.success("Manufacturer created.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Unable to create manufacturer: {exc}")

        if not manufacturer_rows:
            _render_guided_empty_state(
                st,
                why_empty="No manufacturer records are currently available.",
                action_to_populate="Load manufacturer seed records or import curated manufacturer data.",
                next_location="Use Knowledge Imports to initialize manufacturer data.",
            )
        else:
            st.dataframe(
                [
                    {
                        "Manufacturer": _safe_text(
                            item.get("canonical_name"),
                            _safe_text(item.get("name"), "n/a"),
                        ),
                        "Code": _safe_text(
                            item.get("manufacturer_code"),
                            _safe_text(item.get("manufacturer_id"), "n/a"),
                        ),
                        "Website": _safe_text(item.get("website"), ""),
                        "Active": bool(item.get("active", True)),
                        "Aliases": len(list(item.get("aliases") or [])),
                    }
                    for item in manufacturer_rows
                ],
                use_container_width=True,
                hide_index=True,
            )

    with tabs[3]:
        st.markdown("### Vendors")
        with st.expander("Add Vendor", expanded=False):
            v_cols = st.columns(2)
            v_id = v_cols[0].text_input("Vendor ID", key="atlas_ck_vendor_id")
            v_name = v_cols[1].text_input("Canonical Name", key="atlas_ck_vendor_name")
            v_display = v_cols[0].text_input(
                "Display Name", key="atlas_ck_vendor_display"
            )
            v_code = v_cols[1].text_input("Code", key="atlas_ck_vendor_code")
            v_site = st.text_input("Website", key="atlas_ck_vendor_site")
            v_notes = st.text_input("Notes", key="atlas_ck_vendor_notes")
            duplicates = product_service.detect_duplicate_vendors(
                canonical_name=v_name,
                normalized_name=product_service.normalize_name(v_name),
            )
            if duplicates:
                st.warning("Potential duplicate vendor names detected.")
            if st.button(
                "Create Vendor",
                key="atlas_ck_create_vendor",
                use_container_width=True,
            ):
                try:
                    product_service.create_vendor(
                        vendor_id=v_id,
                        canonical_name=v_name,
                        display_name=v_display,
                        vendor_code=v_code,
                        website=v_site,
                        notes=v_notes,
                    )
                    _save_commercial_product_state(st, product_service)
                    st.success("Vendor created.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Unable to create vendor: {exc}")

        if not vendor_rows:
            _render_guided_empty_state(
                st,
                why_empty="No vendor records are currently available.",
                action_to_populate="Load vendor seed records or import curated vendor data.",
                next_location="Use Knowledge Imports to initialize vendor data.",
            )
        else:
            st.dataframe(
                [
                    {
                        "Vendor": _safe_text(
                            item.get("canonical_name"),
                            _safe_text(item.get("name"), "n/a"),
                        ),
                        "Code": _safe_text(
                            item.get("vendor_code"),
                            _safe_text(item.get("vendor_id"), "n/a"),
                        ),
                        "Website": _safe_text(item.get("website"), ""),
                        "Active": bool(item.get("active", True)),
                    }
                    for item in vendor_rows
                ],
                use_container_width=True,
                hide_index=True,
            )

    with tabs[4]:
        st.markdown("### Customers")
        if not customers:
            _render_guided_empty_state(
                st,
                why_empty="No customer records are currently available.",
                action_to_populate="Create or import projects so Atlas can index customer ownership.",
                next_location="Go to Projects and create/import a project.",
            )
        else:
            st.dataframe(
                [
                    {
                        "Customer": customer,
                        "Projects": sum(
                            1
                            for item in project_rows
                            if item.get("customer") == customer
                        ),
                    }
                    for customer in customers
                ],
                use_container_width=True,
                hide_index=True,
            )

    with tabs[5]:
        st.markdown("### Products / Master Library")
        with st.expander("Manual Single-SKU Workflow", expanded=False):
            st.caption(
                "Add one isolated SKU without requiring full catalog or price-sheet import."
            )
            p_cols = st.columns(2)
            manufacturer_options = sorted(
                {
                    _safe_text(item.get("manufacturer_id"), "")
                    for item in manufacturer_rows
                    if _safe_text(item.get("manufacturer_id"), "")
                }
            )
            vendor_options = sorted(
                {
                    _safe_text(item.get("vendor_id"), "")
                    for item in vendor_rows
                    if _safe_text(item.get("vendor_id"), "")
                }
            )

            selected_mfr = p_cols[0].selectbox(
                "Manufacturer",
                options=manufacturer_options,
                key="atlas_ck_product_mfr_id",
            )
            selected_vendor = p_cols[1].selectbox(
                "Vendor",
                options=vendor_options,
                key="atlas_ck_product_vendor_id",
            )
            part_number = p_cols[0].text_input(
                "Manufacturer Part Number",
                key="atlas_ck_product_part_number",
            )
            product_name = p_cols[1].text_input(
                "Product Name",
                key="atlas_ck_product_name",
            )
            product_desc = st.text_input(
                "Description", key="atlas_ck_product_description"
            )
            channel = st.selectbox(
                "Purchasing Channel",
                options=[
                    "direct_from_manufacturer",
                    "distributor",
                    "dealer_reseller",
                    "other",
                ],
                key="atlas_ck_offering_channel",
            )
            vendor_sku = st.text_input("Vendor SKU", key="atlas_ck_offering_vendor_sku")
            uom_cols = st.columns(3)
            uom = uom_cols[0].text_input(
                "Unit of Measure", value="ea", key="atlas_ck_offering_uom"
            )
            moq = uom_cols[1].number_input(
                "Minimum Order Qty",
                min_value=0,
                value=0,
                step=1,
                key="atlas_ck_offering_moq",
            )
            pack_qty = uom_cols[2].number_input(
                "Pack Quantity",
                min_value=0,
                value=0,
                step=1,
                key="atlas_ck_offering_pack_qty",
            )

            selected_manufacturer = _record_by_id(
                manufacturer_rows,
                id_field="manufacturer_id",
                selected_id=selected_mfr,
            )
            selected_vendor_record = _record_by_id(
                vendor_rows,
                id_field="vendor_id",
                selected_id=selected_vendor,
            )

            existing_duplicate = product_service.find_product_by_identity(
                manufacturer=_safe_text(
                    dict(selected_manufacturer or {}).get("canonical_name"),
                    "",
                ),
                normalized_part_number=product_service.normalize_part_number(
                    part_number
                ),
            )
            if existing_duplicate:
                st.warning(
                    "Potential duplicate product detected for manufacturer + normalized part number."
                )

            if st.button(
                "Create Product and Vendor Offering",
                key="atlas_ck_create_product_and_offering",
                use_container_width=True,
            ):
                try:
                    mfr_record = selected_manufacturer
                    vendor_record = selected_vendor_record
                    if not isinstance(mfr_record, dict) or not isinstance(
                        vendor_record, dict
                    ):
                        raise ValueError("Select valid manufacturer and vendor records")

                    product = product_service.create_product(
                        manufacturer_id=_safe_text(
                            mfr_record.get("manufacturer_id"), ""
                        ),
                        manufacturer=_safe_text(mfr_record.get("canonical_name"), ""),
                        manufacturer_part_number=part_number,
                        product_name=product_name,
                        product_description=product_desc,
                        category="other",
                        lifecycle_status="pending_verification",
                        active=True,
                        notes="manual_single_sku",
                    )
                    product_service.create_vendor_offering(
                        vendor_id=_safe_text(vendor_record.get("vendor_id"), ""),
                        vendor=_safe_text(vendor_record.get("canonical_name"), ""),
                        atlas_product_uuid=_safe_text(
                            product.get("atlas_product_uuid"), ""
                        ),
                        vendor_sku=vendor_sku or part_number,
                        purchasing_channel=channel,
                        direct_from_manufacturer=(
                            channel == "direct_from_manufacturer"
                        ),
                        authorization_status="unknown",
                        minimum_order_quantity=int(moq),
                        order_multiple=1,
                        unit_of_measure=uom,
                        pack_quantity=int(pack_qty),
                        lead_time_notes="",
                        active=True,
                        notes="manual_single_sku",
                    )
                    _save_commercial_product_state(st, product_service)
                    st.success("Created Product and Vendor Offering.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Unable to create Product/Offering: {exc}")

        if not product_rows:
            _render_guided_empty_state(
                st,
                why_empty="No reusable products are indexed yet.",
                action_to_populate="Run project analysis to generate equipment mappings and canonical products.",
                next_location="Open a project and run Documents analysis.",
            )
        else:
            filter_cols = st.columns(6)
            query = filter_cols[0].text_input(
                "Search",
                key="atlas_ck_product_search",
                placeholder="part number, name, description",
            )
            manufacturer_filter = filter_cols[1].multiselect(
                "Manufacturer",
                options=sorted(
                    {
                        _safe_text(item.get("manufacturer"), "")
                        for item in product_rows
                        if _safe_text(item.get("manufacturer"), "")
                    }
                ),
                default=[],
                key="atlas_ck_product_mfr_filter",
            )
            lifecycle_filter = filter_cols[2].multiselect(
                "Lifecycle",
                options=sorted(
                    {
                        _safe_text(
                            item.get("lifecycle_status"),
                            _safe_text(item.get("status"), ""),
                        )
                        for item in product_rows
                    }
                ),
                default=[],
                key="atlas_ck_product_lifecycle_filter",
            )
            active_filter = filter_cols[3].selectbox(
                "Active",
                options=["All", "Active", "Inactive"],
                key="atlas_ck_product_active_filter",
            )
            missing_commercial_filter = filter_cols[4].selectbox(
                "Missing Commercial",
                options=["All", "Yes", "No"],
                key="atlas_ck_product_missing_commercial_filter",
            )
            sort_field = filter_cols[5].selectbox(
                "Sort",
                options=["manufacturer", "model", "status", "updated_at"],
                key="atlas_ck_product_sort",
            )

            filtered_products: list[dict[str, Any]] = []
            for item in product_rows:
                if (
                    manufacturer_filter
                    and _safe_text(item.get("manufacturer"), "")
                    not in manufacturer_filter
                ):
                    continue
                lifecycle_value = _safe_text(
                    item.get("lifecycle_status"),
                    _safe_text(item.get("status"), ""),
                )
                if lifecycle_filter and lifecycle_value not in lifecycle_filter:
                    continue
                if active_filter == "Active" and not bool(item.get("active", True)):
                    continue
                if active_filter == "Inactive" and bool(item.get("active", True)):
                    continue

                offerings = product_service.list_vendor_offerings_by_product(
                    _safe_text(item.get("atlas_product_uuid"), "")
                )
                missing_commercial = len(offerings) == 0
                if missing_commercial_filter == "Yes" and not missing_commercial:
                    continue
                if missing_commercial_filter == "No" and missing_commercial:
                    continue

                searchable = " ".join(
                    [
                        _safe_text(
                            item.get("manufacturer_part_number"),
                            _safe_text(item.get("model"), ""),
                        ),
                        _safe_text(item.get("product_name"), ""),
                        _safe_text(
                            item.get("product_description"),
                            _safe_text(item.get("description"), ""),
                        ),
                    ]
                ).lower()
                if query.strip() and query.strip().lower() not in searchable:
                    continue
                filtered_products.append(
                    {**item, "_missing_commercial": missing_commercial}
                )

            filtered_products.sort(
                key=lambda item: _safe_text(item.get(sort_field), "")
            )
            page_size = 50
            max_page = max((len(filtered_products) - 1) // page_size, 0)
            page = st.number_input(
                "Page",
                min_value=1,
                max_value=max_page + 1,
                value=1,
                step=1,
                key="atlas_ck_product_page",
            )
            start = (int(page) - 1) * page_size
            visible = filtered_products[start : start + page_size]
            st.dataframe(
                [
                    {
                        "Manufacturer": _safe_text(item.get("manufacturer"), "n/a"),
                        "Part Number": _safe_text(
                            item.get("manufacturer_part_number"),
                            _safe_text(item.get("model"), "n/a"),
                        ),
                        "Name": _safe_text(
                            item.get("product_name"),
                            _safe_text(item.get("model"), "n/a"),
                        ),
                        "Category": _safe_text(item.get("category"), "n/a"),
                        "Lifecycle": _safe_text(
                            item.get("lifecycle_status"),
                            _safe_text(item.get("status"), "n/a"),
                        ),
                        "Active": bool(item.get("active", True)),
                        "Missing Commercial": bool(
                            item.get("_missing_commercial", False)
                        ),
                    }
                    for item in visible
                ],
                use_container_width=True,
                hide_index=True,
            )

    with tabs[6]:
        st.markdown("### Price Lists")
        st.caption(
            "Price list uploads are discoverable here and managed in Project Workspace Price List Library."
        )
        if not uploaded_price_lists:
            _render_guided_empty_state(
                st,
                why_empty="No price lists are imported.",
                action_to_populate="Upload manufacturer or vendor price lists.",
                next_location="Open a project and go to Price List Library.",
            )
        else:
            st.dataframe(
                uploaded_price_lists, use_container_width=True, hide_index=True
            )
            with st.expander("Manufacturer Price Sheets", expanded=False):
                if manufacturer_products:
                    st.dataframe(
                        manufacturer_products[:300],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("No manufacturer price sheets are indexed yet.")
            with st.expander("Vendor Price Lists", expanded=False):
                if vendor_offers:
                    st.dataframe(
                        vendor_offers[:300], use_container_width=True, hide_index=True
                    )
                else:
                    st.info("No vendor price lists are indexed yet.")

    with tabs[7]:
        st.markdown("### Knowledge Imports")
        if not import_history:
            _render_guided_empty_state(
                st,
                why_empty="No knowledge imports have been recorded.",
                action_to_populate="Import project packages or upload project documents.",
                next_location="Use Projects to import project bundles.",
            )
        else:
            st.dataframe(
                import_history[:100], use_container_width=True, hide_index=True
            )

    with tabs[8]:
        st.markdown("### Commercial Import History")
        if not commercial_import_history:
            st.info("No commercial import history available.")
        else:
            st.dataframe(
                [
                    {
                        "Import Date": item.get("import_date"),
                        "Vendor": item.get("vendor"),
                        "Manufacturer": item.get("manufacturer"),
                        "Version": item.get("version"),
                        "Rows Imported": item.get("rows_imported"),
                        "Products Added": item.get("products_added"),
                        "Products Removed": item.get("products_removed"),
                        "Products Changed": item.get("products_changed"),
                    }
                    for item in commercial_import_history
                ],
                use_container_width=True,
                hide_index=True,
            )


def _render_application_reports_page(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    _render_page_header(
        st,
        "Reports",
        "Application-level project pipeline and health reporting.",
    )
    rows = _collect_workspace_signals(workspace_service, limit=30)
    if not rows:
        st.info("No projects available for application-level reporting.")
        return
    st.dataframe(
        [
            {
                "Project": item.get("project"),
                "Status": item.get("status"),
                "Stage": item.get("stage"),
                "Reason": item.get("reason"),
                "Documents": item.get("documents"),
                "Review Artifacts": item.get("review_artifacts"),
                "Updated": item.get("updated_at"),
            }
            for item in rows
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_application_administration_page(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    _render_page_header(
        st,
        "Administration",
        "Application-level settings and local repository controls.",
    )
    st.dataframe(
        [
            {
                "Setting": "Workspace Root",
                "Value": str(workspace_service.workspace_root),
            },
            {
                "Setting": "Layout Mode",
                "Value": _safe_text(
                    st.session_state.get("atlas_layout_mode"), "Desktop"
                ),
            },
            {
                "Setting": "Navigation Behavior",
                "Value": (
                    "Persistent sidebar"
                    if _safe_text(st.session_state.get("atlas_layout_mode"), "Desktop")
                    == "Desktop"
                    else "Collapsed navigation"
                ),
            },
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_projects_page(st: Any, workspace_service: ProjectWorkspaceService) -> None:
    _render_page_header(
        st,
        "Projects",
        "Primary project library for opening, creating, importing, and managing repository projects.",
    )

    include_archived = st.checkbox("Show archived projects", value=False)
    rows = _project_library_rows(
        workspace_service,
        include_archived=include_archived,
        limit=500,
    )
    if not rows:
        _render_guided_empty_state(
            st,
            why_empty="No projects are imported into the Atlas Project Repository.",
            action_to_populate="Create a new project or import a .atlaspkg bundle.",
            next_location="Use Create New Project or Import Project Package below.",
        )
        return

    action_cols = st.columns(3)
    if action_cols[0].button(
        "Create New Project", type="primary", use_container_width=True
    ):
        st.session_state["atlas_active_page"] = "Create New Project"
        st.rerun()

    project_bundle = action_cols[1].file_uploader(
        "Import Project Package",
        type=["atlaspkg"],
        accept_multiple_files=False,
        key="atlas_projects_import_bundle",
        label_visibility="collapsed",
    )
    if project_bundle is not None:
        temp_path = Path("/tmp") / f"atlas-import-{project_bundle.name}"
        temp_path.write_bytes(project_bundle.getvalue())
        imported = workspace_service.import_project_bundle(str(temp_path))
        _open_project_record(st, imported)

    if action_cols[2].button("Open Existing Project", use_container_width=True):
        st.session_state["atlas_active_page"] = "Open Existing Project"
        st.rerun()

    filter_cols = st.columns(5)
    search = filter_cols[0].text_input("Search", value="")
    lifecycle_filter = filter_cols[1].selectbox(
        "Lifecycle",
        options=["All"] + sorted({str(item["lifecycle_stage"]) for item in rows}),
    )
    status_filter = filter_cols[2].selectbox(
        "Status",
        options=["All"] + sorted({str(item["current_status"]) for item in rows}),
    )
    reference_filter = filter_cols[3].selectbox(
        "Reference",
        options=["All", "Reference Only", "Standard Only"],
    )
    sort_field = filter_cols[4].selectbox(
        "Sort",
        options=[
            "project_name",
            "customer",
            "lifecycle_stage",
            "current_status",
            "last_opened",
            "last_modified",
            "document_count",
            "review_status",
        ],
    )

    filtered = [
        item
        for item in rows
        if (
            (
                not search.strip()
                or _contains_any(
                    " ".join(
                        [
                            _safe_text(item.get("project_name"), ""),
                            _safe_text(item.get("workspace_id"), ""),
                            _safe_text(item.get("customer"), ""),
                        ]
                    ),
                    [search.strip().lower()],
                )
            )
            and (
                lifecycle_filter == "All"
                or _safe_text(item.get("lifecycle_stage"), "") == lifecycle_filter
            )
            and (
                status_filter == "All"
                or _safe_text(item.get("current_status"), "") == status_filter
            )
            and (
                reference_filter == "All"
                or (
                    reference_filter == "Reference Only" and bool(item.get("reference"))
                )
                or (
                    reference_filter == "Standard Only"
                    and not bool(item.get("reference"))
                )
            )
        )
    ]
    filtered.sort(key=lambda item: _safe_text(item.get(sort_field), ""), reverse=True)

    st.dataframe(
        [
            {
                "Project": item["project_name"],
                "Customer": item["customer"],
                "Lifecycle": item["lifecycle_stage"],
                "Status": item["current_status"],
                "Last Opened": item["last_opened"],
                "Last Modified": item["last_modified"],
                "Documents": item["document_count"],
                "Review Status": item["review_status"],
                "Reference": "Yes" if item["reference"] else "No",
                "Archived": "Yes" if item["archived"] else "No",
                "Pinned": "Yes" if item["pinned"] else "No",
            }
            for item in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )

    labels = [f"{item['project_name']} · {item['workspace_id']}" for item in filtered]
    if labels:
        selected_label = st.selectbox("Open Project", options=labels)
        selected_item = filtered[labels.index(selected_label)]
        selected = selected_item["record"]

        action_cols = st.columns(5)
        if action_cols[0].button(
            "Open Project", type="primary", use_container_width=True
        ):
            _open_project_record(st, selected)

        pin_label = "Unpin" if selected.pinned else "Pin"
        if action_cols[1].button(pin_label, use_container_width=True):
            workspace_service.pin_project(
                selected.workspace_id, pinned=not selected.pinned
            )
            st.rerun()

        if action_cols[2].button("Duplicate Project", use_container_width=True):
            workspace_service.duplicate_project(
                selected.workspace_id,
                new_workspace_id=f"{selected.workspace_id}-copy",
                new_name=f"{selected.project.name} Copy",
            )
            st.rerun()

        archive_label = "Unarchive Project" if selected.archived else "Archive Project"
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

        delete_confirm = action_cols[4].checkbox(
            "Confirm Delete",
            key=f"atlas_confirm_delete_{selected.workspace_id}",
        )
        if action_cols[4].button("Delete Project", use_container_width=True):
            if not delete_confirm:
                st.warning("Enable Confirm Delete before deleting a project.")
            else:
                workspace_service.delete_project(selected.workspace_id)
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


def _render_project_folder_page(
    st: Any,
    context: dict[str, Any] | None,
    folder_name: str,
    title: str,
) -> None:
    _render_page_header(
        st,
        title,
        f"Project document explorer for {folder_name.lower()} files.",
    )
    folders = _files_by_folder(context)
    rows = list(folders.get(folder_name, []))
    if not rows:
        st.info(f"No files are currently classified under {folder_name}.")
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)
    file_labels = [item.get("filename") for item in rows]
    selected_file = st.selectbox("Select file", options=file_labels)
    selected = next(item for item in rows if item.get("filename") == selected_file)
    _set_context_selection(st, "file", {"folder": folder_name, "file": selected})


def _render_estimate_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Estimate",
        "Deterministic estimate workspace with explicit traceability from engineering objects to estimate lines.",
    )
    review = context.get("review") if context else None
    labor_estimate = getattr(review, "labor_estimate", None) if review else None
    bom_rows = _enriched_bom_rows(st, _canonical_bom_items(context))
    product_resolutions = _resolved_product_rows(st, bom_rows)
    service = DeterministicEstimateService()
    estimate = service.build(
        project_id=record.project.project_id,
        project_name=record.project.name,
        bom_rows=bom_rows,
        labor_estimate=labor_estimate,
        product_resolutions=product_resolutions,
    )
    bom_rows, pricing_result = _apply_deterministic_pricing(
        st,
        record,
        bom_rows=bom_rows,
        product_resolutions=product_resolutions,
        estimate=estimate,
    )
    priced_lines = list(pricing_result.get("priced_lines") or [])
    pricing_by_line_id = {
        _safe_text(item.get("estimate_line_id"), ""): item for item in priced_lines
    }
    pricing_summary = dict(pricing_result.get("summary") or {})
    pricing_coverage = dict(pricing_result.get("commercial_coverage") or {})

    dashboard = service.build_dashboard(estimate)
    confidence_model = estimate.confidence_model
    line_rows = estimate.all_lines()

    tabs = st.tabs(
        [
            "Overview",
            "Equipment Cost",
            "Labor",
            "Accessories",
            "Freight",
            "General Conditions",
            "Engineering Allowances",
            "Project Summary",
            "Estimate Confidence",
            "Cost Overview",
            "Commercial Coverage",
            "Priced Equipment",
            "Unpriced Equipment",
            "Stale Cost",
            "Allowances",
            "Vendor Alternatives",
            "Cost Warnings",
            "Cost History",
        ]
    )

    with tabs[0]:
        st.dataframe(
            [
                {
                    "Project": record.project.name,
                    "Estimate Lines": dashboard["line_count"],
                    "Material Cost": dashboard["material_cost"],
                    "Labor Cost": dashboard["labor_cost"],
                    "Allowance Cost": dashboard["allowance_cost"],
                    "Freight": dashboard["freight"],
                    "Known Cost %": f"{dashboard['known_cost_percent']}%",
                    "Unknown Cost %": f"{dashboard['unknown_cost_percent']}%",
                    "Resolved Products": dashboard["resolved_products"],
                    "Unresolved Products": dashboard["unresolved_products"],
                    "Pricing Confidence": f"{dashboard['pricing_confidence']}%",
                    "Overall Estimate Confidence": f"{dashboard['overall_estimate_confidence']}%",
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Every estimate line is traceable to source engineering objects. Proposal, RFQ, and purchasing output is intentionally out of scope."
        )
        resolution_summary = _resolution_summary_rows(product_resolutions)
        st.dataframe(
            [
                {
                    "Resolved Products": resolution_summary["resolved_products"],
                    "Unknown Products": resolution_summary["unknown_products"],
                    "Generic Allowances": resolution_summary["generic_allowances"],
                    "Substitutions": resolution_summary["substitutions"],
                    "Requires Review": resolution_summary["requires_review"],
                    "Pricing Gate": (
                        "Blocked"
                        if resolution_summary["requires_review"] > 0
                        else "Ready"
                    ),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Acquisition cost remains deterministic and blocked for unresolved, generic allowance, or low-confidence product resolution lines."
        )

    with tabs[1]:
        if not line_rows:
            _render_guided_empty_state(
                st,
                why_empty="No estimate lines are available yet.",
                action_to_populate="Run project analysis to produce reviewed BOM/equipment objects.",
                next_location="Open Documents and execute Project Analysis.",
            )
        else:
            display_rows = []
            for line in line_rows:
                priced = dict(pricing_by_line_id.get(line.line_id) or {})
                display_rows.append(
                    {
                        "Line": line.line_id,
                        "Source Object": line.source_object,
                        "Object Type": line.object_type.title(),
                        "Manufacturer": line.manufacturer,
                        "Model": line.model,
                        "Description": line.description,
                        "Quantity": line.quantity,
                        "Product Resolution": _estimate_resolution_chip(
                            line.product_resolution_status.value
                        ),
                        "Pricing Status": _estimate_cost_status_chip(
                            line.pricing_status.value
                        ),
                        "Labor Status": _estimate_cost_status_chip(
                            line.labor_status.value
                        ),
                        "Deterministic Pricing": _safe_text(
                            priced.get("pricing_status"), "no_pricing"
                        ),
                        "Selected Unit Cost": priced.get("unit_cost"),
                        "Selected Vendor Offering": priced.get(
                            "selected_vendor_offering_id"
                        ),
                        "Commercial Freshness": priced.get("freshness_status"),
                        "Cost Confidence": priced.get("pricing_confidence"),
                        "Confidence": f"{int(line.confidence * 100)}%",
                        "Material": line.material_cost.amount,
                        "Labor": line.labor_cost.amount,
                        "Accessories": line.accessory_cost.amount,
                        "Line Total": line.line_total(),
                    }
                )
            st.dataframe(display_rows, use_container_width=True, hide_index=True)

            selected_line_id = st.selectbox(
                "Select estimate line",
                options=[line.line_id for line in line_rows],
                key="atlas_estimate_selected_line",
            )
            selected_line = next(
                line for line in line_rows if line.line_id == selected_line_id
            )

            st.markdown("#### Estimate Line Traceability")
            selected_priced = dict(pricing_by_line_id.get(selected_line.line_id) or {})
            trace_rows = [
                {
                    "Source Object": selected_line.source_object,
                    "Object Type": selected_line.object_type,
                    "Manufacturer": selected_line.manufacturer,
                    "Model": selected_line.model,
                    "Description": selected_line.description,
                    "Quantity": selected_line.quantity,
                    "Pricing Status": selected_line.pricing_status.value,
                    "Deterministic Pricing Status": selected_priced.get(
                        "pricing_status"
                    ),
                    "Deterministic Selection": selected_priced.get("selection_reason"),
                    "Selected Unit Cost": selected_priced.get("unit_cost"),
                    "Extended Cost": selected_priced.get("extended_cost"),
                    "Freshness": selected_priced.get("freshness_status"),
                    "Price Record": selected_priced.get("selected_price_record_id"),
                    "Sheet Version": selected_priced.get(
                        "selected_price_sheet_version_id"
                    ),
                    "Vendor Offering": selected_priced.get(
                        "selected_vendor_offering_id"
                    ),
                    "Labor Status": selected_line.labor_status.value,
                    "Confidence": f"{int(selected_line.confidence * 100)}%",
                    "Source References": ", ".join(
                        f"{ref.source_type}:{ref.source_id}"
                        for ref in selected_line.source_references
                    )
                    or "n/a",
                }
            ]
            st.dataframe(trace_rows, use_container_width=True, hide_index=True)

            nav_cols = st.columns(5)
            target_map = {
                item.get("kind"): item.get("value")
                for item in selected_line.navigation_refs
            }
            button_targets = [
                ("equipment", "Open Equipment"),
                ("specification", "Open Specification"),
                ("drawing", "Open Drawing"),
                ("relationships", "Open Relationship"),
                ("evidence", "Open Evidence"),
            ]
            for index, (kind, label) in enumerate(button_targets):
                value = _safe_text(target_map.get(kind), "")
                if nav_cols[index].button(
                    label,
                    key=f"atlas_estimate_nav_{selected_line.line_id}_{kind}",
                    disabled=not value,
                    use_container_width=True,
                ):
                    _open_estimate_navigation_target(
                        st,
                        target_kind=kind,
                        target_value=value,
                    )

    with tabs[2]:
        st.dataframe(
            service.labor_architecture_rows(estimate),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Labor categories are architected for deterministic expansion. Labor hours and rates can remain empty during foundation stage."
        )

    with tabs[3]:
        st.dataframe(
            [
                {
                    "Category": category,
                    "Generation Status": "Placeholder",
                    "Estimated Cost": 0.0,
                }
                for category in service.ACCESSORY_PLACEHOLDER_CATEGORIES
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[4]:
        st.dataframe(
            [
                {
                    "Freight Cost": estimate.freight_cost.amount,
                    "Freight Status": _estimate_cost_status_chip(
                        estimate.freight_cost.status.value
                    ),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[5]:
        st.dataframe(
            [
                {
                    "Subtotal": estimate.subtotal().amount,
                    "Markup %": round(estimate.markup.percent * 100, 2),
                    "Markup Amount": estimate.markup_amount(),
                    "Contingency %": round(estimate.contingency.percent * 100, 2),
                    "Contingency Amount": estimate.contingency_amount(),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[6]:
        allowance_rows = [item.to_dict() for item in estimate.allowances]
        if allowance_rows:
            st.dataframe(allowance_rows, use_container_width=True, hide_index=True)
        else:
            st.info(
                "No engineering allowances were created from current reviewed objects."
            )

    with tabs[7]:
        st.dataframe(
            [
                {
                    "Subtotal": estimate.subtotal().amount,
                    "Markup": estimate.markup_amount(),
                    "Contingency": estimate.contingency_amount(),
                    "Grand Total": estimate.grand_total().amount,
                    "Resolved Products": dashboard["resolved_products"],
                    "Unresolved Products": dashboard["unresolved_products"],
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[8]:
        confidence = confidence_model.to_dict() if confidence_model is not None else {}
        st.dataframe(
            [
                {
                    "Overall Confidence": f"{int(float(confidence.get('score', 0.0)) * 100)}%",
                    "Known Pricing": f"{int(float(confidence.get('known_pricing_ratio', 0.0)) * 100)}%",
                    "Resolved Products": f"{int(float(confidence.get('resolved_product_ratio', 0.0)) * 100)}%",
                    "Unpriced Labor": f"{int(float(confidence.get('unpriced_labor_ratio', 0.0)) * 100)}%",
                    "Unknown Quantity": f"{int(float(confidence.get('unknown_quantity_ratio', 0.0)) * 100)}%",
                    "Generic Allowance": f"{int(float(confidence.get('generic_allowance_ratio', 0.0)) * 100)}%",
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("#### Confidence Explanations")
        for message in list(confidence.get("messages") or []):
            st.markdown(f"- {message}")

    with tabs[9]:
        st.dataframe(
            [
                {
                    "Cost Run ID": pricing_result.get("pricing_run_id"),
                    "Run Timestamp": pricing_result.get("run_timestamp"),
                    "Policy Version": pricing_result.get("pricing_policy_version"),
                    "Equipment Cost": pricing_summary.get("equipment_cost", 0.0),
                    "Accessory Cost": pricing_summary.get("accessory_cost", 0.0),
                    "Software Cost": pricing_summary.get("software_cost", 0.0),
                    "Known Cost": pricing_summary.get("known_cost", 0.0),
                    "Unknown Cost": pricing_summary.get("unknown_cost", 0.0),
                    "Known Cost %": pricing_summary.get("known_cost_percent", 0.0),
                    "Unknown Cost %": pricing_summary.get("unknown_cost_percent", 0.0),
                    "Allowance Cost": pricing_summary.get("allowance_cost", 0.0),
                    "Products Without Cost": pricing_summary.get(
                        "products_without_cost", 0
                    ),
                    "Pricing Freshness": pricing_summary.get(
                        "pricing_freshness", "unknown"
                    ),
                    "Commercial Confidence": pricing_summary.get(
                        "commercial_confidence", 0.0
                    ),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Quick Add Product", expanded=False):
            qa_mfr = st.text_input("Manufacturer", key="atlas_quick_add_mfr")
            qa_model = st.text_input("Model", key="atlas_quick_add_model")
            qa_desc = st.text_input("Description", key="atlas_quick_add_desc")
            qa_vendor = st.text_input("Vendor", key="atlas_quick_add_vendor")
            qa_vendor_type = st.selectbox(
                "Vendor Type",
                options=[
                    "manufacturer_direct",
                    "authorized_distributor",
                    "regional_distributor",
                    "buying_group",
                    "marketplace",
                    "integrator",
                    "other",
                ],
                key="atlas_quick_add_vendor_type",
            )
            qa_cost = st.number_input(
                "Acquisition Cost",
                min_value=0.0,
                value=0.0,
                step=1.0,
                key="atlas_quick_add_cost",
            )
            qa_source = st.text_input(
                "Source",
                value="manual entry",
                key="atlas_quick_add_source",
            )
            qa_mode = st.radio(
                "After creation",
                options=["Project Only", "Promote to Master Library"],
                horizontal=True,
                key="atlas_quick_add_mode",
            )

            if st.button(
                "Create Quick Add Product",
                key="atlas_quick_add_create",
                use_container_width=True,
            ):
                if not qa_mfr.strip() or not qa_model.strip() or not qa_vendor.strip():
                    st.warning("Manufacturer, model, and vendor are required.")
                else:
                    engine = DeterministicCostEngine()
                    if qa_mode == "Project Only":
                        result = engine.quick_add_product(
                            project_id=record.project.project_id,
                            manufacturer=qa_mfr,
                            model=qa_model,
                            description=qa_desc,
                            vendor=qa_vendor,
                            vendor_type=qa_vendor_type,
                            cost=float(qa_cost),
                            source=qa_source,
                            project_only=True,
                            project_state={
                                "quick_add_products": _quick_add_products_by_project(st)
                            },
                        )
                        st.session_state["atlas_quick_add_products"] = dict(
                            result.get("project_state", {}).get("quick_add_products")
                            or {}
                        )
                    else:
                        result = engine.quick_add_product(
                            project_id=record.project.project_id,
                            manufacturer=qa_mfr,
                            model=qa_model,
                            description=qa_desc,
                            vendor=qa_vendor,
                            vendor_type=qa_vendor_type,
                            cost=float(qa_cost),
                            source=qa_source,
                            project_only=False,
                            commercial_state=_commercial_knowledge_state(st),
                        )
                        library = _price_list_library_state(st)
                        library["commercial_knowledge"] = dict(
                            result.get("commercial_state") or {}
                        )
                        st.session_state["atlas_price_list_library"] = library
                    st.rerun()

        engine = DeterministicCostEngine()
        export_cols = st.columns(2)
        export_cols[0].download_button(
            "Download Cost Summary JSON",
            data=engine.export_cost_summary_json(
                st.session_state.get("atlas_last_cost_result") or {}
            ),
            file_name=f"{record.project.project_id}_cost_summary.json",
            mime="application/json",
            use_container_width=True,
        )
        export_cols[1].download_button(
            "Download Cost Lines CSV",
            data=engine.export_cost_lines_csv(
                st.session_state.get("atlas_last_cost_result") or {}
            ),
            file_name=f"{record.project.project_id}_cost_lines.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tabs[10]:
        st.dataframe(
            [
                {
                    "Resolved Products": pricing_coverage.get("resolved_products", 0),
                    "Products With Current Cost": pricing_coverage.get(
                        "products_with_current_cost", 0
                    ),
                    "Products Using Historical Cost": pricing_coverage.get(
                        "products_using_historical_cost", 0
                    ),
                    "Products Using Allowances": pricing_coverage.get(
                        "products_using_allowances", 0
                    ),
                    "Products Missing Cost": pricing_coverage.get(
                        "products_missing_cost", 0
                    ),
                    "Products With Stale Cost": pricing_coverage.get(
                        "products_with_stale_cost", 0
                    ),
                    "Coverage %": pricing_coverage.get("coverage_percent", 0.0),
                    "Material Cost Confidence": pricing_coverage.get(
                        "material_cost_confidence", 0.0
                    ),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Download Commercial Coverage JSON",
            data=DeterministicCostEngine().export_commercial_coverage_json(
                st.session_state.get("atlas_last_cost_result") or {}
            ),
            file_name=f"{record.project.project_id}_commercial_coverage.json",
            mime="application/json",
            use_container_width=True,
        )

    with tabs[11]:
        st.dataframe(
            [
                item
                for item in priced_lines
                if _safe_text(item.get("pricing_status"), "")
                not in {"missing", "unavailable"}
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[12]:
        st.dataframe(
            [
                item
                for item in priced_lines
                if _safe_text(item.get("pricing_status"), "")
                in {
                    "missing",
                    "unavailable",
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[13]:
        stale_rows = [
            item
            for item in priced_lines
            if _safe_text(item.get("pricing_status"), "")
            in {
                "stale",
                "expired",
                "historical",
            }
        ]
        st.dataframe(stale_rows, use_container_width=True, hide_index=True)

    with tabs[14]:
        st.dataframe(
            [
                item
                for item in priced_lines
                if _safe_text(item.get("pricing_status"), "") in {"allowance"}
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[15]:
        line_options = [
            _safe_text(item.get("estimate_line_id"), "") for item in priced_lines
        ]
        if not line_options:
            st.info("No priced lines are available for vendor alternative review.")
        else:
            selected_alt_line = st.selectbox(
                "Select priced line",
                options=line_options,
                key="atlas_pricing_alternative_line",
            )
            selected_priced_line = next(
                (
                    item
                    for item in priced_lines
                    if _safe_text(item.get("estimate_line_id"), "") == selected_alt_line
                ),
                None,
            )
            selection = (
                dict(selected_priced_line.get("selection") or {})
                if isinstance(selected_priced_line, dict)
                else {}
            )
            st.dataframe(
                list(selection.get("candidates") or []),
                use_container_width=True,
                hide_index=True,
            )

    with tabs[16]:
        warning_rows: list[dict[str, Any]] = []
        for item in priced_lines:
            for warning in list(item.get("warnings") or []):
                warning_rows.append(
                    {
                        "Estimate Line": item.get("estimate_line_id"),
                        "Cost Status": item.get("pricing_status"),
                        "Warning Code": warning.get("code"),
                        "Warning": warning.get("message"),
                        "Severity": warning.get("severity"),
                    }
                )
        st.dataframe(warning_rows, use_container_width=True, hide_index=True)
        st.download_button(
            "Download Cost Exceptions CSV",
            data=DeterministicCostEngine().export_cost_exceptions_csv(
                st.session_state.get("atlas_last_cost_result") or {}
            ),
            file_name=f"{record.project.project_id}_cost_exceptions.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tabs[17]:
        commercial_service = _commercial_service(st)
        product_options = sorted(
            {
                _safe_text(item.get("canonical_product_id"), "")
                for item in priced_lines
                if _safe_text(item.get("canonical_product_id"), "")
            }
        )
        if not product_options:
            st.info("No canonical product history is available for cost history view.")
        else:
            selected_product = st.selectbox(
                "Select canonical product",
                options=product_options,
                key="atlas_pricing_history_product",
            )
            st.dataframe(
                commercial_service.price_history_for_product(selected_product),
                use_container_width=True,
                hide_index=True,
            )

    _render_review_transition(
        st,
        record,
        context,
        "estimate",
        mark_label="Mark Estimate Coverage Reviewed",
    )


def _render_product_resolution_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Product Resolution",
        "Deterministic bridge between reviewed engineering objects and estimate-ready canonical products.",
    )

    bom_rows = _enriched_bom_rows(st, _canonical_bom_items(context))
    if not bom_rows:
        _render_guided_empty_state(
            st,
            why_empty="No BOM/equipment rows are available for deterministic product resolution.",
            action_to_populate="Run project analysis to build reviewed equipment rows.",
            next_location="Go to Documents and execute Project Analysis.",
        )
        return

    resolutions = _resolved_product_rows(st, bom_rows)
    by_source = {getattr(item, "source_object_id", ""): item for item in resolutions}

    filter_map = {
        "Unknown": lambda item: _normalized_resolution_status(item)
        == "unknown_product",
        "Low Confidence": lambda item: float(
            getattr(item, "resolution_confidence", 0.0) or 0.0
        )
        < 0.75,
        "Needs Review": lambda item: _normalized_resolution_status(item)
        in {"unknown_product", "generic_allowance"}
        or float(getattr(item, "resolution_confidence", 0.0) or 0.0) < 0.75,
        "Resolved": lambda item: _normalized_resolution_status(item)
        in {"exact_product", "approved_substitute", "preferred_alternate"},
        "Substituted": lambda item: _normalized_resolution_status(item)
        in {"approved_substitute", "preferred_alternate"},
    }
    selected_filters = st.multiselect(
        "Filters",
        options=list(filter_map.keys()),
        default=["Needs Review"],
        key="atlas_product_resolution_filters",
    )

    filtered = list(resolutions)
    for filter_name in selected_filters:
        predicate = filter_map.get(filter_name)
        if predicate is not None:
            filtered = [item for item in filtered if predicate(item)]

    display_rows = []
    for row in bom_rows:
        source_id = _resolution_source_id(row)
        resolution = by_source.get(source_id)
        if resolution is None or resolution not in filtered:
            continue

        normalized_status = _normalized_resolution_status(resolution)
        confidence = float(getattr(resolution, "resolution_confidence", 0.0) or 0.0)
        candidates = list(getattr(resolution, "candidate_matches", []) or [])
        top = candidates[0] if candidates else None
        display_rows.append(
            {
                "Equipment": source_id,
                "Current Resolution": _product_resolution_badge(normalized_status),
                "Confidence": f"{int(confidence * 100)}%",
                "Reason": _safe_text(getattr(resolution, "resolution_reason", ""), ""),
                "Manufacturer": _safe_text(row.get("manufacturer"), "Unknown"),
                "Model": _safe_text(row.get("model"), "Unknown"),
                "Candidate Matches": (
                    f"{len(candidates)} candidates"
                    if top is None
                    else f"{len(candidates)} candidates · top={_safe_text(getattr(top, 'product_id', ''), '')}"
                ),
                "Required Action": (
                    "Review Required"
                    if (
                        normalized_status in {"unknown_product", "generic_allowance"}
                        or confidence < 0.75
                    )
                    else "Ready"
                ),
            }
        )

    if display_rows:
        st.dataframe(display_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No rows match the active filter set.")

    available_sources = [
        _resolution_source_id(row)
        for row in bom_rows
        if _resolution_source_id(row) in by_source
    ]
    selected_source = st.selectbox(
        "Select equipment row for manual review",
        options=available_sources,
        key="atlas_product_resolution_selected_source",
    )
    selected_resolution = by_source.get(selected_source)
    if selected_resolution is None:
        return

    candidates = list(getattr(selected_resolution, "candidate_matches", []) or [])
    candidate_rows = [
        {
            "product_id": _safe_text(getattr(item, "product_id", ""), ""),
            "manufacturer": _safe_text(getattr(item, "manufacturer", ""), ""),
            "model": _safe_text(getattr(item, "model", ""), ""),
            "match_type": _safe_text(getattr(item, "match_type", ""), ""),
            "confidence": float(getattr(item, "confidence", 0.0) or 0.0),
            "reason": _safe_text(getattr(item, "reason", ""), ""),
        }
        for item in candidates
    ]

    st.markdown("### Candidate Matches")
    if candidate_rows:
        st.dataframe(candidate_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No deterministic candidates were found for this row.")

    override_state = _product_resolution_overrides(st)
    existing_override = dict(override_state.get(selected_source) or {})
    selected_product_option = st.selectbox(
        "Manual selection",
        options=[row["product_id"] for row in candidate_rows] or [""],
        index=0,
        key=f"atlas_product_resolution_manual_select_{selected_source}",
    )
    status_option = st.selectbox(
        "Manual status",
        options=[
            "exact_product",
            "approved_substitute",
            "preferred_alternate",
            "generic_allowance",
            "unknown_product",
        ],
        index=0,
        key=f"atlas_product_resolution_manual_status_{selected_source}",
    )
    reviewer = st.text_input(
        "Reviewer",
        value=_safe_text(existing_override.get("reviewer"), "Engineering Reviewer"),
        key=f"atlas_product_resolution_manual_reviewer_{selected_source}",
    )
    reason = st.text_input(
        "Manual override reason",
        value=_safe_text(
            existing_override.get("reason"),
            "Deterministic manual selection for project standards.",
        ),
        key=f"atlas_product_resolution_manual_reason_{selected_source}",
    )

    action_cols = st.columns(2)
    if action_cols[0].button(
        "Apply Manual Override",
        use_container_width=True,
        disabled=not selected_product_option,
        key=f"atlas_product_resolution_manual_apply_{selected_source}",
    ):
        override_state[selected_source] = {
            "selected_product_id": selected_product_option,
            "resolution_status": status_option,
            "reviewer": _safe_text(reviewer, "Engineering Reviewer"),
            "timestamp": _now_iso(),
            "reason": _safe_text(
                reason,
                "Deterministic manual selection for project standards.",
            ),
        }
        st.session_state["atlas_product_resolution_overrides"] = override_state
        st.session_state["atlas_product_resolution_cache"] = {}
        st.rerun()

    if action_cols[1].button(
        "Clear Manual Override",
        use_container_width=True,
        key=f"atlas_product_resolution_manual_clear_{selected_source}",
    ):
        if selected_source in override_state:
            del override_state[selected_source]
            st.session_state["atlas_product_resolution_overrides"] = override_state
            st.session_state["atlas_product_resolution_cache"] = {}
            st.rerun()

    manual_override = getattr(selected_resolution, "manual_override", None)
    st.markdown("### Override Audit")
    if manual_override is None:
        st.caption("No manual override is currently applied for this row.")
    else:
        st.dataframe(
            [
                {
                    "Reviewer": _safe_text(
                        getattr(manual_override, "reviewer", ""),
                        "n/a",
                    ),
                    "Timestamp": _safe_text(
                        getattr(manual_override, "timestamp", ""),
                        "n/a",
                    ),
                    "Reason": _safe_text(
                        getattr(manual_override, "reason", ""),
                        "n/a",
                    ),
                    "Original Match": _safe_text(
                        str(getattr(manual_override, "original_match", None) or {}),
                        "{}",
                    ),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    canonical = dict(getattr(selected_resolution, "canonical_product", {}) or {})
    commercial_product = _commercial_product_key(
        manufacturer=_safe_text(
            canonical.get("manufacturer"), selected_resolution.manufacturer
        ),
        model=_safe_text(canonical.get("model"), selected_resolution.model),
    )
    commercial_service = _commercial_service(st)
    product_history = commercial_service.price_history_for_product(commercial_product)
    freshness_by_product = {
        item.get("product"): item for item in commercial_service.freshness_rows()
    }
    freshness = dict(freshness_by_product.get(commercial_product) or {})
    lifecycle = (
        commercial_service.to_dict()
        .get("product_lifecycle", {})
        .get(commercial_product, {})
    )

    st.markdown("### Commercial Knowledge")
    st.dataframe(
        [
            {
                "Known Vendors": ", ".join(product_history.get("known_vendors") or [])
                or "None",
                "Current Price Sheet Status": _safe_text(
                    lifecycle.get("lifecycle_status"), "unknown"
                ),
                "Latest Version": _safe_text(
                    product_history.get("latest_version"), "n/a"
                ),
                "Historical Versions": len(
                    list(product_history.get("historical_versions") or [])
                ),
                "Commercial Freshness": _safe_text(
                    freshness.get("current_status"), "missing"
                ),
                "Pricing Availability": (
                    "Available"
                    if list(product_history.get("historical_prices") or [])
                    else "Missing"
                ),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )


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
        st.session_state["atlas_active_page"] = "Overview"
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
                st.session_state["atlas_active_page"] = "Overview"
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
    st.session_state["atlas_active_page"] = "Overview"
    st.success(f"Created project {record.project.name}.")
    st.rerun()


def _render_open_existing_page(
    st: Any, workspace_service: ProjectWorkspaceService
) -> None:
    _render_page_header(
        st,
        "Open Existing Project",
        "Open imported repository projects. Path-based opening is available in Advanced options.",
    )

    include_archived = st.checkbox("Show archived projects", value=False)
    rows = _project_library_rows(
        workspace_service,
        include_archived=include_archived,
        limit=500,
    )
    if not rows:
        _render_guided_empty_state(
            st,
            why_empty="No repository projects are currently imported.",
            action_to_populate="Create a project or import a .atlaspkg bundle.",
            next_location="Use Projects page actions to create/import projects.",
        )
    else:
        filters = st.columns(4)
        search = filters[0].text_input("Search Projects", value="")
        lifecycle_filter = filters[1].selectbox(
            "Lifecycle",
            options=["All"] + sorted({str(item["lifecycle_stage"]) for item in rows}),
        )
        status_filter = filters[2].selectbox(
            "Status",
            options=["All"] + sorted({str(item["current_status"]) for item in rows}),
        )
        sort_field = filters[3].selectbox(
            "Sort",
            options=[
                "last_opened",
                "last_modified",
                "project_name",
                "customer",
                "review_status",
            ],
        )

        filtered = [
            item
            for item in rows
            if (
                (
                    not search.strip()
                    or _contains_any(
                        " ".join(
                            [
                                _safe_text(item.get("project_name"), ""),
                                _safe_text(item.get("workspace_id"), ""),
                                _safe_text(item.get("customer"), ""),
                            ]
                        ),
                        [search.strip().lower()],
                    )
                )
                and (
                    lifecycle_filter == "All"
                    or _safe_text(item.get("lifecycle_stage"), "") == lifecycle_filter
                )
                and (
                    status_filter == "All"
                    or _safe_text(item.get("current_status"), "") == status_filter
                )
            )
        ]
        filtered.sort(
            key=lambda item: _safe_text(item.get(sort_field), ""), reverse=True
        )

        st.dataframe(
            [
                {
                    "Project": item["project_name"],
                    "Customer": item["customer"],
                    "Lifecycle": item["lifecycle_stage"],
                    "Status": item["current_status"],
                    "Last Opened": item["last_opened"],
                    "Last Modified": item["last_modified"],
                    "Documents": item["document_count"],
                    "Review Status": item["review_status"],
                    "Reference": "Reference" if item["reference"] else "",
                    "Archived": "Archived" if item["archived"] else "",
                }
                for item in filtered
            ],
            use_container_width=True,
            hide_index=True,
        )

        labels = [
            f"{item['project_name']} · {item['workspace_id']}" for item in filtered
        ]
        if labels:
            selected_label = st.selectbox("Select Project", options=labels)
            selected_item = filtered[labels.index(selected_label)]
            selected = selected_item["record"]

            actions = st.columns(2)
            if actions[0].button(
                "Open Project", type="primary", use_container_width=True
            ):
                _open_project_record(st, selected)
            pin_label = "Unpin" if selected.pinned else "Pin"
            if actions[1].button(pin_label, use_container_width=True):
                workspace_service.pin_project(
                    selected.workspace_id,
                    pinned=not selected.pinned,
                )
                st.rerun()

    with st.expander("Advanced: Open from local path", expanded=False):
        path_text = st.text_input(
            "Workspace file, intake snapshot, or package folder",
            key="atlas_pending_open_path",
            placeholder="AtlasProjects/example-project/project.json",
        )
        if st.button("Open from local path", use_container_width=True):
            _open_project_from_local_path(st, workspace_service, path_text)


def _render_project_summary_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    summary = _build_project_analysis_summary(record, context)
    _render_page_header(
        st,
        "Project Summary",
        "Project health, analysis status, and the next recommended action.",
    )

    cards = st.columns(5)
    _metric_card(cards[0], "Document Count", str(summary["document_count"]))
    _metric_card(cards[1], "Analysis Status", summary["analysis_status"])
    _metric_card(cards[2], "BOM Items", str(summary["bom_item_count"]))
    _metric_card(cards[3], "Scope Issues", str(summary["unresolved_scope_issue_count"]))
    _metric_card(cards[4], "High-Risk Issues", str(summary["high_risk_issue_count"]))

    st.dataframe(
        [
            {
                "Project Name": summary["project_name"],
                "Customer": summary["customer"],
                "Project Type": summary["project_type"],
                "Documents Requiring OCR": summary["documents_requiring_ocr"],
                "Recommended Next Action": summary["recommended_next_action"],
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    if st.button("Run Project Analysis", type="primary", use_container_width=True):
        st.session_state["atlas_active_page"] = "Documents"
        st.rerun()

    if context is None:
        st.info(
            "Upload project documents and run analysis to populate BOM, scope, risk, and reporting results."
        )
        return

    st.markdown("### Analysis Result Summary")
    st.dataframe(
        [
            {
                "Equipment Items Found": summary["equipment_items_found"],
                "Possible BOM Items": summary["possible_bom_items"],
                "Scope Gaps": summary["scope_gaps"],
                "Quantity Conflicts": summary["quantity_conflicts"],
                "Responsibility Ambiguities": summary["responsibility_ambiguities"],
                "Missing Specifications": summary["missing_specifications"],
                "Unresolved Manufacturer/Model References": summary[
                    "unresolved_manufacturer_model_refs"
                ],
            }
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_bom_review_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "BOM Review",
        "Review canonical candidate BOM lines with completeness status, conflict visibility, and source traceability.",
    )

    bom_rows = _canonical_bom_items(context)
    if not bom_rows:
        _render_guided_empty_state(
            st,
            why_empty="No BOM items are available because Atlas has not produced canonical BOM lines yet.",
            action_to_populate="Upload documents and run project analysis from Documents.",
            next_location="Go to Documents and run project analysis.",
        )
        return

    bom_rows = _enriched_bom_rows(st, bom_rows)
    product_resolutions = _resolved_product_rows(st, bom_rows)
    pricing_estimate = DeterministicEstimateService().build(
        project_id=record.project.project_id,
        project_name=record.project.name,
        bom_rows=bom_rows,
        labor_estimate=None,
        product_resolutions=product_resolutions,
    )
    bom_rows, _ = _apply_deterministic_pricing(
        st,
        record,
        bom_rows=bom_rows,
        product_resolutions=product_resolutions,
        estimate=pricing_estimate,
    )

    metrics = _canonical_bom_metrics(bom_rows)
    cards_top = st.columns(4)
    _metric_card(
        cards_top[0],
        "Total Candidate BOM Lines",
        str(metrics["total_candidate_bom_lines"]),
    )
    _metric_card(cards_top[1], "Complete Lines", str(metrics["complete_lines"]))
    _metric_card(cards_top[2], "Incomplete Lines", str(metrics["incomplete_lines"]))
    _metric_card(cards_top[3], "Conflicting Lines", str(metrics["conflicting_lines"]))

    cards_bottom = st.columns(3)
    _metric_card(
        cards_bottom[0], "Drawing-only Items", str(metrics["drawing_only_items"])
    )
    _metric_card(
        cards_bottom[1],
        "Specification-only Items",
        str(metrics["specification_only_items"]),
    )
    _metric_card(cards_bottom[2], "Unresolved Items", str(metrics["unresolved_items"]))

    missing_manufacturer = sum(
        1
        for item in bom_rows
        if item.get("completeness_status") == "missing_manufacturer"
    )
    missing_model = sum(
        1 for item in bom_rows if item.get("completeness_status") == "missing_model"
    )
    needing_review = sum(
        1
        for item in bom_rows
        if item.get("completeness_status")
        not in {"complete", "drawing_only", "specification_only"}
    )

    st.markdown("### Priority Summary")
    st.dataframe(
        [
            {
                "Complete Items": metrics["complete_lines"],
                "Incomplete Items": metrics["incomplete_lines"],
                "Unresolved Items": metrics["unresolved_items"],
                "Quantity Conflicts": metrics["conflicting_lines"],
                "Missing Manufacturer": missing_manufacturer,
                "Missing Model": missing_model,
                "Items Requiring Review": needing_review,
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Candidate BOM Lines")
    search_text = st.text_input(
        "Search BOM lines",
        key="atlas_bom_search",
        placeholder="equipment id, manufacturer, model, description, system, room",
    ).strip()

    filter_cols = st.columns(5)
    systems = sorted(
        {
            _safe_text(item.get("system"), "Unknown")
            for item in bom_rows
            if _safe_text(item.get("system"), "")
        }
    )
    rooms = sorted(
        {
            _safe_text(item.get("room_or_area"), "Unknown")
            for item in bom_rows
            if _safe_text(item.get("room_or_area"), "")
        }
    )
    manufacturers = sorted(
        {
            _safe_text(item.get("manufacturer"), "Unknown")
            for item in bom_rows
            if _safe_text(item.get("manufacturer"), "")
        }
    )
    completeness_states = sorted(
        {_safe_text(item.get("completeness_status"), "unresolved") for item in bom_rows}
    )

    selected_systems = filter_cols[0].multiselect(
        "System",
        options=systems,
        key="atlas_bom_filter_system",
    )
    selected_rooms = filter_cols[1].multiselect(
        "Room",
        options=rooms,
        key="atlas_bom_filter_room",
    )
    selected_manufacturers = filter_cols[2].multiselect(
        "Manufacturer",
        options=manufacturers,
        key="atlas_bom_filter_manufacturer",
    )
    selected_completeness = filter_cols[3].multiselect(
        "Completeness",
        options=completeness_states,
        key="atlas_bom_filter_completeness",
    )
    confidence_threshold = filter_cols[4].slider(
        "Min Confidence",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.05,
        key="atlas_bom_confidence_threshold",
    )

    filtered_rows: list[dict[str, Any]] = []
    for row in bom_rows:
        if (
            selected_systems
            and _safe_text(row.get("system"), "") not in selected_systems
        ):
            continue
        if (
            selected_rooms
            and _safe_text(row.get("room_or_area"), "") not in selected_rooms
        ):
            continue
        if (
            selected_manufacturers
            and _safe_text(row.get("manufacturer"), "") not in selected_manufacturers
        ):
            continue
        if (
            selected_completeness
            and _safe_text(row.get("completeness_status"), "")
            not in selected_completeness
        ):
            continue
        confidence = row.get("confidence")
        numeric_confidence = (
            float(confidence) if isinstance(confidence, (int, float)) else 0.0
        )
        if numeric_confidence < confidence_threshold:
            continue
        if search_text and search_text.lower() not in str(row).lower():
            continue
        filtered_rows.append(row)

    if not filtered_rows:
        _render_guided_empty_state(
            st,
            why_empty="No BOM lines match the current filters.",
            action_to_populate="Relax search/filter criteria or clear completeness and confidence filters.",
            next_location="Use the filter controls above to broaden results.",
        )
        return

    view_mode = st.radio(
        "View",
        options=["Table", "Group by System", "Group by Room", "Group by Manufacturer"],
        horizontal=True,
        key="atlas_bom_view_mode",
    )

    if view_mode == "Table":
        st.dataframe(
            [
                {
                    "BOM Item ID": row.get("bom_item_id"),
                    "Manufacturer": row.get("manufacturer"),
                    "Model": row.get("model"),
                    "Description": row.get("description"),
                    "Quantity": row.get("quantity"),
                    "System": row.get("system"),
                    "Room/Area": row.get("room_or_area"),
                    "Confidence": row.get("confidence"),
                    "Quantity Confidence": row.get("quantity_confidence"),
                    "Completeness": row.get("completeness_status"),
                    "Scope Status": row.get("scope_status"),
                    "Matched Manufacturer Product": row.get(
                        "matched_manufacturer_product"
                    ),
                    "Matched Vendor Offer": row.get("matched_vendor_offer"),
                    "List Price": row.get("list_price"),
                    "Known Cost": row.get("known_cost"),
                    "Deterministic Cost": row.get("det_cost_status"),
                    "Acquisition Cost": row.get("det_acquisition_cost"),
                    "Vendor Type": row.get("det_vendor_type"),
                    "Freshness": row.get("det_freshness_status"),
                    "Cost Confidence": row.get("det_cost_confidence"),
                    "Pricing Source": row.get("pricing_source"),
                    "Pricing Effective Date": row.get("pricing_effective_date"),
                    "Match Confidence": row.get("match_confidence"),
                    "Pricing Warning": row.get("pricing_warning"),
                }
                for row in filtered_rows
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        group_key = "system"
        group_label = "System"
        if view_mode == "Group by Room":
            group_key = "room_or_area"
            group_label = "Room"
        elif view_mode == "Group by Manufacturer":
            group_key = "manufacturer"
            group_label = "Manufacturer"

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in filtered_rows:
            grouped[_safe_text(row.get(group_key), "Unknown")].append(row)

        st.dataframe(
            [
                {
                    group_label: name,
                    "Line Count": len(rows),
                    "Complete": sum(
                        1
                        for item in rows
                        if item.get("completeness_status") == "complete"
                    ),
                    "Conflicting": sum(
                        1
                        for item in rows
                        if item.get("completeness_status") == "conflicting_quantity"
                    ),
                    "Incomplete": sum(
                        1
                        for item in rows
                        if item.get("completeness_status")
                        not in {"complete", "conflicting_quantity"}
                    ),
                }
                for name, rows in sorted(grouped.items())
            ],
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Line Evidence (Drill-down)", expanded=False):
        selected_bom_id = st.selectbox(
            "Select BOM line",
            options=[_safe_text(item.get("bom_item_id"), "") for item in filtered_rows],
            key="atlas_bom_selected_item",
        )
        selected_row = next(
            (row for row in filtered_rows if row.get("bom_item_id") == selected_bom_id),
            None,
        )
        if selected_row is not None:
            st.dataframe(
                [
                    {
                        "BOM Item ID": selected_row.get("bom_item_id"),
                        "Completeness": selected_row.get("completeness_status"),
                        "Warnings": ", ".join(list(selected_row.get("warnings") or []))
                        or "None",
                        "Related RFIs": ", ".join(
                            list(selected_row.get("related_rfi_candidates") or [])
                        )
                        or "None",
                        "Matched Manufacturer Product": selected_row.get(
                            "matched_manufacturer_product"
                        )
                        or "None",
                        "Matched Vendor Offer": selected_row.get("matched_vendor_offer")
                        or "None",
                        "List Price": selected_row.get("list_price"),
                        "Known Cost": selected_row.get("known_cost"),
                        "Deterministic Cost": selected_row.get("det_cost_status")
                        or "None",
                        "Acquisition Cost": selected_row.get("det_acquisition_cost"),
                        "Extended Cost": selected_row.get("det_cost_extended"),
                        "Vendor Type": selected_row.get("det_vendor_type") or "None",
                        "Source File": selected_row.get("det_source_file") or "None",
                        "Source Row": selected_row.get("det_source_row"),
                        "Freshness": selected_row.get("det_freshness_status") or "None",
                        "Cost Confidence": selected_row.get("det_cost_confidence"),
                        "Selection Method": selected_row.get("det_selection_method")
                        or "None",
                        "Selection Reason": selected_row.get("det_selection_reason")
                        or "None",
                        "Price Record": selected_row.get("det_selected_price_record_id")
                        or "None",
                        "Price Sheet Version": selected_row.get(
                            "det_selected_price_sheet_version_id"
                        )
                        or "None",
                        "Vendor Offering": selected_row.get(
                            "det_selected_vendor_offering_id"
                        )
                        or "None",
                        "Cost Warnings": selected_row.get("det_pricing_warnings")
                        or "None",
                        "Pricing Source": selected_row.get("pricing_source") or "None",
                        "Pricing Effective Date": selected_row.get(
                            "pricing_effective_date"
                        )
                        or "None",
                        "Match Confidence": selected_row.get("match_confidence"),
                        "Pricing Warning": selected_row.get("pricing_warning")
                        or "None",
                    }
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.dataframe(
                [
                    {
                        "Source Document": source_file,
                        "Page": page,
                        "Drawing References": ", ".join(
                            list(selected_row.get("drawing_references") or [])
                        ),
                        "Specification References": ", ".join(
                            list(selected_row.get("specification_references") or [])
                        ),
                    }
                    for source_file in list(
                        selected_row.get("source_documents") or ["n/a"]
                    )
                    for page in list(selected_row.get("source_pages") or ["n/a"])
                ],
                use_container_width=True,
                hide_index=True,
            )

            equipment_target_id = _safe_text(
                selected_row.get("bom_item_id"),
                _safe_text(selected_row.get("equipment_id"), ""),
            )
            if equipment_target_id and st.button(
                "Open Equipment Detail",
                key=f"atlas_bom_open_equipment_{equipment_target_id}",
                use_container_width=True,
            ):
                _open_equipment_detail(
                    st,
                    equipment_id=equipment_target_id,
                    origin_page="BOM Review",
                    origin_key=equipment_target_id,
                )

    st.markdown("### Export")
    export_csv, export_json = _canonical_bom_export_payload(filtered_rows)
    export_cols = st.columns(2)
    export_cols[0].download_button(
        "Download Candidate BOM CSV",
        data=export_csv,
        file_name=f"{record.project.project_id}_candidate_bom.csv",
        mime="text/csv",
        use_container_width=True,
    )
    export_cols[1].download_button(
        "Download Candidate BOM JSON",
        data=export_json,
        file_name=f"{record.project.project_id}_candidate_bom.json",
        mime="application/json",
        use_container_width=True,
    )

    _render_review_transition(
        st,
        record,
        context,
        "bom",
        mark_label="Mark BOM Review Complete",
    )


def _render_scope_risk_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Scope & Risk",
        "Focused bid risk review for incomplete scope, contradictions, ownership gaps, and commercial exposure.",
    )

    finding_rows = _scope_risk_findings(context)
    if not finding_rows:
        _render_guided_empty_state(
            st,
            why_empty="No scope and risk findings are available yet.",
            action_to_populate="Run project analysis and then return to Scope and Risk.",
            next_location="Go to Documents and run project analysis.",
        )
        return

    metrics = _scope_risk_metrics(finding_rows)
    cards = st.columns(4)
    _metric_card(cards[0], "Total Findings", str(metrics["total"]))
    _metric_card(cards[1], "Critical Issues", str(metrics["critical"]))
    _metric_card(cards[2], "High Severity", str(metrics["high"]))
    _metric_card(cards[3], "Quantity Conflicts", str(metrics["quantity_conflicts"]))

    st.caption("Internal draft RFIs should be reviewed before external issue.")

    st.markdown("### Priority Risks")
    priority_rows = [
        item
        for item in finding_rows
        if _safe_text(item.get("severity"), "").lower() in {"critical", "high"}
    ]
    if priority_rows:
        st.dataframe(
            [
                {
                    "Severity": item.get("severity"),
                    "Category": item.get("category"),
                    "Title": item.get("title"),
                    "Impact": item.get("estimating_impact"),
                    "Action": item.get("recommended_action"),
                }
                for item in priority_rows[:15]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No critical or high-priority findings are currently open.")

    sections = _scope_risk_sections(finding_rows)

    for section in [
        "Critical Issues",
        "Missing Scope",
        "Responsibility Gaps",
        "Quantity Conflicts",
    ]:
        st.markdown(f"### {section}")
        rows = list(sections.get(section) or [])
        if not rows:
            st.info(f"No findings currently classified under {section}.")
            continue
        st.dataframe(
            [
                {
                    "Finding ID": item.get("finding_id"),
                    "Severity": item.get("severity"),
                    "Title": item.get("title"),
                    "Impact": item.get("estimating_impact"),
                    "Recommended Action": item.get("recommended_action"),
                    "Likely Owner": item.get("likely_owner"),
                }
                for item in rows[:12]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Lower Priority Findings", expanded=False):
        for section in ["Engineering Gaps", "Commercial Risks"]:
            st.markdown(f"#### {section}")
            rows = list(sections.get(section) or [])
            if not rows:
                st.caption(f"No findings currently classified under {section}.")
                continue
            st.dataframe(
                [
                    {
                        "Finding ID": item.get("finding_id"),
                        "Severity": item.get("severity"),
                        "Title": item.get("title"),
                        "Impact": item.get("estimating_impact"),
                        "Recommended Action": item.get("recommended_action"),
                    }
                    for item in rows[:12]
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("### Recommended RFIs")
    recommended_rfis = list(sections.get("Recommended RFIs") or [])
    if recommended_rfis:
        st.dataframe(
            recommended_rfis[:12],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No internal draft RFI language generated yet.")

    with st.expander("Finding Drill-down", expanded=False):
        finding_ids = [_safe_text(item.get("finding_id"), "") for item in finding_rows]
        selected_finding_id = st.selectbox(
            "Select finding",
            options=finding_ids,
            key="atlas_scope_risk_selected_finding",
        )
        selected_row = next(
            (
                item
                for item in finding_rows
                if item.get("finding_id") == selected_finding_id
            ),
            None,
        )

        if selected_row is not None:
            st.dataframe(
                [
                    {
                        "Finding ID": selected_row.get("finding_id"),
                        "Category": selected_row.get("category"),
                        "Severity": selected_row.get("severity"),
                        "Confidence": selected_row.get("confidence"),
                        "Title": selected_row.get("title"),
                        "Explanation": selected_row.get("concise_explanation"),
                        "Estimating Impact": selected_row.get("estimating_impact"),
                        "Recommended Action": selected_row.get("recommended_action"),
                        "Likely Owner": selected_row.get("likely_owner"),
                        "Candidate RFI (Internal Draft)": selected_row.get(
                            "candidate_rfi_text"
                        ),
                    }
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.dataframe(
                [
                    {
                        "Affected BOM Items": ", ".join(
                            selected_row.get("affected_bom_items") or []
                        )
                        or "None",
                        "Affected Systems": ", ".join(
                            selected_row.get("affected_systems") or []
                        )
                        or "None",
                        "Affected Rooms": ", ".join(
                            selected_row.get("affected_rooms") or []
                        )
                        or "None",
                        "Source References": ", ".join(
                            selected_row.get("source_references") or []
                        )
                        or "None",
                    }
                ],
                use_container_width=True,
                hide_index=True,
            )

    _render_review_transition(
        st,
        record,
        context,
        "scope_risk",
        mark_label="Mark Scope and Risk Reviewed",
    )


def _render_price_list_library_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Price List Library",
        "Ingest manufacturer and vendor price lists and deterministically enrich BOM review.",
    )
    st.caption(
        "This foundation is for pricing knowledge only. Procurement execution workflows are intentionally out of scope."
    )

    uploaded_files = st.file_uploader(
        "Upload manufacturer/vendor price lists",
        type=["xlsx", "xls", "csv", "pdf", "docx"],
        accept_multiple_files=True,
        key="atlas_price_list_uploads",
        help="Supports XLSX, XLS, CSV, PDF (text/table extraction where practical), and DOCX where applicable.",
    )
    if uploaded_files:
        signature = _uploaded_file_signature(uploaded_files)
        if st.session_state.get("atlas_price_list_signature") != signature:
            st.session_state["atlas_price_list_signature"] = signature

    pdf_uploaded_files = [
        file
        for file in list(uploaded_files or [])
        if Path(str(file.name)).suffix.lower() == ".pdf"
    ]
    non_pdf_uploaded_files = [
        file
        for file in list(uploaded_files or [])
        if Path(str(file.name)).suffix.lower() != ".pdf"
    ]

    if pdf_uploaded_files:
        st.markdown("### PDF Import Review (C-02)")
        st.caption(
            "Review page ranges, table candidates, header row, and column mapping before creating a draft."
        )
        pdf_service = _commercial_product_service(st)
        pdf_source_options = [str(file.name) for file in pdf_uploaded_files]
        selected_pdf_source = st.selectbox(
            "PDF Source File",
            options=pdf_source_options,
            key="atlas_pdf_source_file",
        )
        selected_pdf_file = next(
            (
                item
                for item in pdf_uploaded_files
                if str(item.name) == selected_pdf_source
            ),
            pdf_uploaded_files[0],
        )
        selected_pdf_bytes = bytes(selected_pdf_file.getvalue())

        pdf_inspection_key = f"atlas_pdf_inspection::{selected_pdf_source}"
        if st.button(
            "Inspect PDF Source",
            key="atlas_pdf_inspect_source",
            use_container_width=True,
        ):
            st.session_state[pdf_inspection_key] = (
                pdf_service.inspect_pdf_import_source(
                    source_filename=selected_pdf_source,
                    file_bytes=selected_pdf_bytes,
                )
            )
            _save_commercial_product_state(st, pdf_service)

        inspected = dict(st.session_state.get(pdf_inspection_key) or {})
        if inspected:
            page_rows = list(inspected.get("pages") or [])
            st.dataframe(
                [
                    {
                        "Page": item.get("page_number"),
                        "Text Source": item.get("text_source"),
                        "OCR Derived": bool(item.get("ocr_derived", False)),
                        "Rotation": item.get("rotation"),
                        "Line Count": item.get("line_count"),
                        "Preview": item.get("preview"),
                    }
                    for item in page_rows
                ],
                use_container_width=True,
                hide_index=True,
            )
            selectable_pages = [
                int(item.get("page_number") or 0)
                for item in page_rows
                if int(item.get("page_number") or 0) > 0
            ]
            selected_pages = st.multiselect(
                "Page Range",
                options=selectable_pages,
                default=selectable_pages,
                key="atlas_pdf_selected_pages",
            )

            candidates = list(inspected.get("table_candidates") or [])
            if candidates:
                candidate_lookup = {
                    f"{item.get('candidate_id')} | pages={','.join(str(v) for v in list(item.get('page_numbers') or []))} | rows={item.get('row_count', 0)}": item
                    for item in candidates
                }
                selected_candidate_label = st.selectbox(
                    "Table Candidate",
                    options=list(candidate_lookup.keys()),
                    key="atlas_pdf_selected_candidate",
                )
                selected_candidate = dict(candidate_lookup[selected_candidate_label])
                candidate_rows = [
                    row
                    for row in list(selected_candidate.get("rows") or [])
                    if int(row.get("page_number") or 0) in set(selected_pages or [])
                ]
                max_cell_count = max(
                    (len(list(row.get("cells") or [])) for row in candidate_rows),
                    default=0,
                )
                candidate_preview_rows = []
                for row in candidate_rows:
                    candidate_preview_rows.append(
                        {
                            "sequence_number": int(row.get("sequence_number") or 0),
                            "page_number": int(row.get("page_number") or 0),
                            "region_id": row.get("region_id"),
                            **{
                                f"column_{idx + 1}": (
                                    list(row.get("cells") or [""] * max_cell_count)[idx]
                                    if idx < len(list(row.get("cells") or []))
                                    else ""
                                )
                                for idx in range(max_cell_count)
                            },
                        }
                    )

                header_row_index = st.number_input(
                    "Header Row Index (within selected candidate rows)",
                    min_value=0,
                    max_value=max(len(candidate_preview_rows) - 1, 0),
                    value=0,
                    step=1,
                    key="atlas_pdf_header_row_index",
                )
                editable_candidate = st.data_editor(
                    candidate_preview_rows,
                    use_container_width=True,
                    hide_index=True,
                    key="atlas_pdf_candidate_editor",
                )

                detected_headers = (
                    [
                        str(
                            (editable_candidate[int(header_row_index)] or {}).get(
                                f"column_{idx + 1}", ""
                            )
                        ).strip()
                        or f"column_{idx + 1}"
                        for idx in range(max_cell_count)
                    ]
                    if editable_candidate
                    else [f"column_{idx + 1}" for idx in range(max_cell_count)]
                )

                mapping_targets = [
                    "manufacturer_part_number",
                    "vendor_sku",
                    "description",
                    "unit_cost",
                    "list_price",
                    "currency",
                    "unit_of_measure",
                    "pack_quantity",
                    "minimum_order_quantity",
                    "effective_date_override",
                    "source_category",
                    "notes",
                ]
                suggested_mapping = pdf_service.suggest_column_mapping(detected_headers)
                mapping: dict[str, str] = {}
                mapping_cols = st.columns(3)
                for index, target in enumerate(mapping_targets):
                    options = [""] + detected_headers
                    default_value = suggested_mapping.get(target, "")
                    if default_value not in options:
                        default_value = ""
                    mapping[target] = mapping_cols[index % 3].selectbox(
                        f"Map {target}",
                        options=options,
                        index=options.index(default_value),
                        key=f"atlas_pdf_map_{target}",
                    )

                info_cols = st.columns(4)
                vendor_name = info_cols[0].text_input(
                    "Vendor",
                    value="Unknown Vendor",
                    key="atlas_pdf_vendor_name",
                )
                manufacturer_name = info_cols[1].text_input(
                    "Manufacturer",
                    value="Unknown Manufacturer",
                    key="atlas_pdf_manufacturer_name",
                )
                effective_date_value = info_cols[2].text_input(
                    "Effective Date",
                    value=datetime.now(UTC).date().isoformat(),
                    key="atlas_pdf_effective_date",
                )
                version_label = info_cols[3].text_input(
                    "Version Label",
                    value=f"{selected_pdf_source} - pdf",
                    key="atlas_pdf_version_label",
                )

                vendor_id = f"vendor-{hashlib.sha1(vendor_name.lower().encode('utf-8')).hexdigest()[:12]}"
                manufacturer_id = f"mfr-{hashlib.sha1(manufacturer_name.lower().encode('utf-8')).hexdigest()[:12]}"
                matching_sheets = [
                    item
                    for item in pdf_service.list_price_sheets(
                        vendor_id=vendor_id, manufacturer_id=manufacturer_id
                    )
                    if _safe_text(item.get("name"), "") == selected_pdf_source
                ]
                if matching_sheets:
                    pdf_sheet = matching_sheets[0]
                else:
                    pdf_sheet = pdf_service.create_price_sheet(
                        name=selected_pdf_source,
                        vendor_id=vendor_id,
                        vendor=vendor_name,
                        manufacturer_id=manufacturer_id,
                        manufacturer=manufacturer_name,
                        purchasing_channel="other",
                        currency="USD",
                        notes="PDF import review",
                    )

                row_corrections: dict[int, dict[str, Any]] = {}
                for row in editable_candidate:
                    seq = int(row.get("sequence_number") or 0)
                    if seq <= 0:
                        continue
                    correction_payload: dict[str, Any] = {}
                    for idx, header in enumerate(detected_headers):
                        correction_payload[header] = row.get(f"column_{idx + 1}", "")
                    row_corrections[seq] = correction_payload

                if st.button(
                    "Create PDF Draft",
                    key="atlas_pdf_create_draft",
                    use_container_width=True,
                ):
                    draft = pdf_service.create_pdf_import_draft(
                        price_sheet_id=_safe_text(pdf_sheet.get("price_sheet_id"), ""),
                        source_filename=selected_pdf_source,
                        file_bytes=selected_pdf_bytes,
                        version_label=version_label,
                        effective_date=effective_date_value,
                        expiration_date="",
                        currency="USD",
                        selected_pages=[
                            int(value) for value in list(selected_pages or [])
                        ],
                        table_candidate_id=_safe_text(
                            selected_candidate.get("candidate_id"), ""
                        ),
                        header_row_index=int(header_row_index),
                        column_mapping=mapping,
                        row_corrections=row_corrections,
                        imported_by="Atlas Workspace",
                    )
                    st.session_state[f"atlas_pdf_draft::{selected_pdf_source}"] = (
                        draft.get("draft_id")
                    )
                    _save_commercial_product_state(st, pdf_service)

                current_draft_id = _safe_text(
                    st.session_state.get(f"atlas_pdf_draft::{selected_pdf_source}"), ""
                )
                current_draft = (
                    pdf_service.get_price_sheet_draft(current_draft_id)
                    if current_draft_id
                    else None
                )
                if current_draft:
                    st.markdown("#### PDF Draft Preview")
                    preview_rows = list(current_draft.get("preview_rows") or [])
                    editable_preview = st.data_editor(
                        preview_rows,
                        use_container_width=True,
                        hide_index=True,
                        key=f"atlas_pdf_preview_editor::{selected_pdf_source}",
                    )
                    correction_cols = st.columns(3)
                    if correction_cols[0].button(
                        "Apply Draft Corrections",
                        key="atlas_pdf_apply_draft_corrections",
                        use_container_width=True,
                    ):
                        updated = pdf_service.update_price_sheet_draft_preview_rows(
                            current_draft_id,
                            preview_rows=list(editable_preview or []),
                        )
                        st.session_state[f"atlas_pdf_draft::{selected_pdf_source}"] = (
                            _safe_text(updated.get("draft_id"), "")
                        )
                        _save_commercial_product_state(st, pdf_service)
                    acknowledge_warnings = correction_cols[1].checkbox(
                        "Acknowledge Warnings",
                        value=True,
                        key="atlas_pdf_ack_warnings",
                    )
                    if correction_cols[1].button(
                        "Validate Draft",
                        key="atlas_pdf_validate_draft",
                        use_container_width=True,
                    ):
                        try:
                            validated = pdf_service.validate_price_sheet_draft(
                                current_draft_id,
                                acknowledge_warnings=bool(acknowledge_warnings),
                            )
                            st.session_state[
                                f"atlas_pdf_draft::{selected_pdf_source}"
                            ] = _safe_text(validated.get("draft_id"), "")
                            _save_commercial_product_state(st, pdf_service)
                            st.success("Draft validated.")
                        except ValueError as exc:
                            st.error(f"Validation failed: {exc}")
                    if correction_cols[2].button(
                        "Finalize PDF Draft",
                        key="atlas_pdf_finalize_draft",
                        use_container_width=True,
                    ):
                        try:
                            pdf_service.finalize_price_sheet_draft(
                                current_draft_id,
                                imported_by="Atlas Workspace",
                                block_duplicate_hash=False,
                            )
                            _save_commercial_product_state(st, pdf_service)
                            st.success(
                                "PDF draft finalized into immutable version and records."
                            )
                        except ValueError as exc:
                            st.error(f"Finalize failed: {exc}")

                    st.dataframe(
                        list(current_draft.get("diagnostics") or []),
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.warning(
                    "No table candidates detected for this PDF. Adjust page selection or use OCR-capable source."
                )

    if st.button(
        "Import Price Lists",
        type="primary",
        disabled=not non_pdf_uploaded_files,
        use_container_width=True,
    ):
        with st.spinner("Importing and normalizing price lists..."):
            existing_library = _price_list_library_state(st)
            file_payload_by_name = {
                str(file.name): bytes(file.getvalue())
                for file in list(non_pdf_uploaded_files or [])
            }
            result = PricingService().ingest_price_lists(
                [
                    (str(file.name), file_payload_by_name[str(file.name)])
                    for file in list(non_pdf_uploaded_files or [])
                ]
            )

            commercial_service = CommercialKnowledgeService(
                state=dict(existing_library.get("commercial_knowledge") or {})
            )
            commercial_product_service = CommercialProductService(
                state=dict(existing_library.get("commercial_products") or {})
            )

            import_results: list[dict[str, Any]] = []
            c02_import_results: list[dict[str, Any]] = []
            vendor_offers = list(result.get("vendor_offers") or [])
            manufacturer_products = list(result.get("manufacturer_products") or [])

            for summary in list(result.get("uploaded_price_lists") or []):
                source_file = _safe_text(summary.get("source_file"), "uploaded")
                source_extension = Path(source_file).suffix.lower()
                import_rows = [
                    item
                    for item in vendor_offers
                    if _safe_text(item.get("source_file"), "") == source_file
                ]
                if not import_rows:
                    import_rows = [
                        {
                            "vendor": _safe_text(
                                summary.get("vendor"),
                                "Manufacturer Catalog",
                            ),
                            "manufacturer": _safe_text(
                                item.get("manufacturer"),
                                _safe_text(summary.get("manufacturer"), "Unknown"),
                            ),
                            "model": _safe_text(item.get("model"), "Unknown"),
                            "vendor_sku": _safe_text(item.get("model"), "Unknown"),
                            "unit_cost": item.get("list_price"),
                            "list_price": item.get("list_price"),
                            "currency": "USD",
                            "lead_time": "unknown",
                            "availability_status": "unknown",
                            "effective_date": item.get("effective_date"),
                            "expiration_date": item.get("discontinued_date"),
                            "description": item.get("description"),
                            "confidence": item.get("confidence", 0.8),
                            "notes": "Manufacturer price-sheet import",
                        }
                        for item in manufacturer_products
                        if _safe_text(item.get("source_file"), "") == source_file
                    ]

                import_results.append(
                    commercial_service.import_price_sheet(
                        vendor=_safe_text(summary.get("vendor"), "Unknown Vendor"),
                        manufacturer=_safe_text(
                            summary.get("manufacturer"),
                            "Unknown Manufacturer",
                        ),
                        sheet_name=source_file,
                        description="Imported from Price List Library",
                        source_filename=source_file,
                        file_bytes=file_payload_by_name.get(source_file, b""),
                        imported_by="Atlas Workspace",
                        rows=import_rows,
                        effective_date=_safe_text(summary.get("effective_date"), ""),
                    )
                )

                if source_extension in {".csv", ".xlsx", ".xls"}:
                    vendor_name = _safe_text(summary.get("vendor"), "Unknown Vendor")
                    manufacturer_name = _safe_text(
                        summary.get("manufacturer"),
                        "Unknown Manufacturer",
                    )
                    vendor_id = f"vendor-{hashlib.sha1(vendor_name.lower().encode('utf-8')).hexdigest()[:12]}"
                    manufacturer_id = f"mfr-{hashlib.sha1(manufacturer_name.lower().encode('utf-8')).hexdigest()[:12]}"

                    sheets = [
                        item
                        for item in commercial_product_service.list_price_sheets(
                            vendor_id=vendor_id,
                            manufacturer_id=manufacturer_id,
                        )
                        if _safe_text(item.get("name"), "") == source_file
                    ]
                    if sheets:
                        sheet = sheets[0]
                    else:
                        sheet = commercial_product_service.create_price_sheet(
                            name=source_file,
                            vendor_id=vendor_id,
                            vendor=vendor_name,
                            manufacturer_id=manufacturer_id,
                            manufacturer=manufacturer_name,
                            purchasing_channel="other",
                            currency="USD",
                            notes="Imported from Price List Library",
                        )

                    try:
                        parsed = commercial_product_service.parse_import_source(
                            source_filename=source_file,
                            file_bytes=file_payload_by_name.get(source_file, b""),
                            worksheet=None,
                            header_row_index=0,
                        )
                        mapping = commercial_product_service.suggest_column_mapping(
                            list(parsed.get("headers") or [])
                        )
                        draft = commercial_product_service.create_import_draft(
                            price_sheet_id=_safe_text(sheet.get("price_sheet_id"), ""),
                            source_filename=source_file,
                            file_bytes=file_payload_by_name.get(source_file, b""),
                            version_label=f"{source_file} - auto",
                            effective_date=_safe_text(summary.get("effective_date"), "")
                            or datetime.now(UTC).date().isoformat(),
                            expiration_date="",
                            currency="USD",
                            worksheet=_safe_text(parsed.get("selected_worksheet"), "")
                            or None,
                            header_row_index=int(
                                parsed.get("header_row_index", 0) or 0
                            ),
                            column_mapping=mapping,
                            imported_by="Atlas Workspace",
                        )
                        draft = commercial_product_service.validate_price_sheet_draft(
                            _safe_text(draft.get("draft_id"), ""),
                            acknowledge_warnings=True,
                        )
                        finalized = (
                            commercial_product_service.finalize_price_sheet_draft(
                                _safe_text(draft.get("draft_id"), ""),
                                imported_by="Atlas Workspace",
                                block_duplicate_hash=False,
                            )
                        )
                        c02_import_results.append(
                            {
                                "source_file": source_file,
                                "draft_id": _safe_text(draft.get("draft_id"), ""),
                                "draft_status": _safe_text(draft.get("status"), ""),
                                "diagnostics": list(draft.get("diagnostics") or []),
                                "record_count": int(draft.get("record_count", 0) or 0),
                                "unresolved_count": int(
                                    draft.get("unresolved_count", 0) or 0
                                ),
                                "finalized_version_id": _safe_text(
                                    dict(finalized.get("version") or {}).get(
                                        "version_id"
                                    ),
                                    "",
                                ),
                            }
                        )
                    except ValueError as exc:
                        c02_import_results.append(
                            {
                                "source_file": source_file,
                                "draft_id": "",
                                "draft_status": "failed",
                                "diagnostics": [
                                    {
                                        "severity": "error",
                                        "code": "import_failed",
                                        "message": _safe_text(
                                            str(exc), "Import failed"
                                        ),
                                        "row_number": None,
                                    }
                                ],
                                "record_count": 0,
                                "unresolved_count": 0,
                                "finalized_version_id": "",
                            }
                        )
                else:
                    commercial_product_rows = [
                        {
                            "vendor": _safe_text(
                                item.get("vendor"),
                                _safe_text(summary.get("vendor"), "Unknown Vendor"),
                            ),
                            "manufacturer": _safe_text(
                                item.get("manufacturer"),
                                _safe_text(
                                    summary.get("manufacturer"), "Unknown Manufacturer"
                                ),
                            ),
                            "canonical_sku": _safe_text(
                                item.get("model"),
                                _safe_text(item.get("vendor_sku"), "Unknown"),
                            ),
                            "manufacturer_sku": _safe_text(
                                item.get("model"),
                                _safe_text(item.get("vendor_sku"), "Unknown"),
                            ),
                            "alternate_skus": (
                                [_safe_text(item.get("vendor_sku"), "")]
                                if _safe_text(item.get("vendor_sku"), "")
                                else []
                            ),
                            "description": _safe_text(item.get("description"), ""),
                            "category": _safe_text(item.get("category"), "other"),
                            "discipline": _safe_text(
                                item.get("discipline"),
                                _safe_text(summary.get("discipline"), "general"),
                            ),
                            "preferred_cost": item.get("unit_cost"),
                            "msrp": item.get("list_price"),
                            "currency": _safe_text(item.get("currency"), "USD"),
                            "lead_time": _safe_text(item.get("lead_time"), ""),
                            "availability_status": _safe_text(
                                item.get("availability_status"), "unknown"
                            ),
                            "effective_date": _safe_text(
                                item.get("effective_date"),
                                _safe_text(summary.get("effective_date"), ""),
                            ),
                            "vendor_sku": _safe_text(
                                item.get("vendor_sku"),
                                _safe_text(item.get("model"), "Unknown"),
                            ),
                            "vendor_type": _safe_text(item.get("vendor_type"), "other"),
                            "comments": _safe_text(item.get("notes"), ""),
                        }
                        for item in import_rows
                    ]
                    commercial_product_service.import_price_list_version(
                        manufacturer=_safe_text(
                            summary.get("manufacturer"),
                            "Unknown Manufacturer",
                        ),
                        vendor=_safe_text(summary.get("vendor"), "Unknown Vendor"),
                        source_file=source_file,
                        file_bytes=file_payload_by_name.get(source_file, b""),
                        import_user="Atlas Workspace",
                        rows=commercial_product_rows,
                        effective_date=_safe_text(summary.get("effective_date"), ""),
                        version_notes="Imported from Price List Library",
                    )

            st.session_state["atlas_price_list_library"] = {
                "uploaded_price_lists": list(
                    existing_library.get("uploaded_price_lists") or []
                )
                + list(result.get("uploaded_price_lists") or []),
                "manufacturer_products": list(
                    existing_library.get("manufacturer_products") or []
                )
                + list(result.get("manufacturer_products") or []),
                "vendor_offers": list(existing_library.get("vendor_offers") or [])
                + list(result.get("vendor_offers") or []),
                "import_warnings": list(existing_library.get("import_warnings") or [])
                + list(result.get("import_warnings") or []),
                "commercial_knowledge": commercial_service.to_dict(),
                "commercial_products": commercial_product_service.to_dict(),
                "commercial_import_results": import_results,
                "commercial_c02_import_results": c02_import_results,
                "commercial_c02_completeness": commercial_product_service.commercial_completeness_summary(),
            }

    library = _price_list_library_state(st)
    summaries = list(library.get("uploaded_price_lists") or [])
    manufacturer_products = list(library.get("manufacturer_products") or [])
    vendor_offers = list(library.get("vendor_offers") or [])
    c02_results = list(library.get("commercial_c02_import_results") or [])
    c02_completeness = dict(library.get("commercial_c02_completeness") or {})

    cards = st.columns(4)
    _metric_card(cards[0], "Uploaded Price Lists", str(len(summaries)))
    _metric_card(cards[1], "Manufacturer Products", str(len(manufacturer_products)))
    _metric_card(cards[2], "Vendor Offers", str(len(vendor_offers)))
    _metric_card(
        cards[3],
        "Expired Pricing",
        str(sum(int(item.get("expired_pricing", 0) or 0) for item in summaries)),
    )

    commercial_dashboard = _commercial_service(st).dashboard_summary()
    product_dashboard = _commercial_product_service(st).dashboard_summary()
    st.markdown("### Commercial Health")
    st.dataframe(
        [
            {
                "Manufacturers": commercial_dashboard.get("manufacturers", 0),
                "Vendors": commercial_dashboard.get("vendors", 0),
                "Products": commercial_dashboard.get("products", 0),
                "Vendor Offerings": commercial_dashboard.get("vendor_offerings", 0),
                "Active Price Sheets": commercial_dashboard.get(
                    "active_price_sheets", 0
                ),
                "Products Missing Pricing": commercial_dashboard.get(
                    "products_missing_pricing", 0
                ),
                "Pricing Stale": commercial_dashboard.get("pricing_stale", 0),
                "Coverage %": commercial_dashboard.get("coverage_percentage", 0.0),
                "Commercial Confidence": commercial_dashboard.get(
                    "commercial_confidence", 0.0
                ),
                "Active Products": product_dashboard.get("active_products", 0),
                "Missing Preferred Vendor": product_dashboard.get(
                    "missing_preferred_vendor", 0
                ),
                "Recent Price Changes": product_dashboard.get(
                    "recent_price_changes", 0
                ),
                "Average Product Confidence": product_dashboard.get(
                    "average_confidence", 0.0
                ),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    if c02_completeness:
        st.markdown("### C-02 Completeness")
        st.dataframe([c02_completeness], use_container_width=True, hide_index=True)

    if c02_results:
        st.markdown("### C-02 Import Lifecycle")
        st.dataframe(
            [
                {
                    "Source File": item.get("source_file"),
                    "Draft ID": item.get("draft_id"),
                    "Draft Status": item.get("draft_status"),
                    "Record Count": item.get("record_count"),
                    "Unresolved Count": item.get("unresolved_count"),
                    "Finalized Version": item.get("finalized_version_id"),
                    "Diagnostics": "; ".join(
                        [
                            f"{diag.get('severity')}: {diag.get('message')}"
                            for diag in list(item.get("diagnostics") or [])
                        ]
                    ),
                }
                for item in c02_results
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Upload Summary")
    if summaries:
        st.dataframe(
            [
                {
                    "Uploaded Price List": item.get("source_file"),
                    "Manufacturer": item.get("manufacturer"),
                    "Vendor": item.get("vendor"),
                    "Effective Date": item.get("effective_date"),
                    "Product Count": item.get("product_count"),
                    "Unmatched Rows": item.get("unmatched_rows"),
                    "Duplicate Rows": item.get("duplicate_rows"),
                    "Expired Pricing": item.get("expired_pricing"),
                    "Import Warnings": "; ".join(item.get("import_warnings") or []),
                }
                for item in summaries
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No price lists imported yet.")

    import_warnings = list(library.get("import_warnings") or [])
    if import_warnings:
        st.markdown("### Import Warnings")
        st.dataframe(
            [{"warning": warning} for warning in import_warnings],
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Manufacturer Product Records", expanded=False):
        if manufacturer_products:
            st.dataframe(
                manufacturer_products[:500], use_container_width=True, hide_index=True
            )
        else:
            st.info("No manufacturer products imported.")

    with st.expander("Vendor Product Offers", expanded=False):
        if vendor_offers:
            st.dataframe(vendor_offers[:500], use_container_width=True, hide_index=True)
        else:
            st.info("No vendor offers imported.")


def _render_engineering_review_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    review = _sales_design_review(st, record, context)
    _render_page_header(
        st,
        "Engineering Review",
        "Internal Sales / Design Engineer review with concise conclusions, risks, and actionable next steps.",
    )

    if review is None:
        _render_guided_empty_state(
            st,
            why_empty="Engineering review is empty because Atlas does not yet have synthesized project conclusions.",
            action_to_populate="Run project analysis and revisit Engineering Review.",
            next_location="Go to Documents and run project analysis.",
        )
        return

    summary = dict(review.get("project_summary") or {})
    bom_summary = dict(review.get("bom_summary") or {})
    cost_coverage = dict(review.get("preliminary_cost_coverage") or {})
    product_resolutions = _resolved_product_rows(
        st,
        _enriched_bom_rows(st, _canonical_bom_items(context)),
    )
    resolution_summary = _resolution_summary_rows(product_resolutions)

    st.dataframe(
        [
            {
                "Project": _safe_text(summary.get("project_name"), "n/a"),
                "Project Type": _safe_text(review.get("project_type"), "Unspecified"),
                "Overall Confidence": f"{int(float(review.get('overall_confidence', 0.0)) * 100)}%",
                "Primary Action": _safe_text(
                    summary.get("recommended_next_action"),
                    "Review project findings",
                ),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    prominent_next_actions = list(review.get("recommended_next_actions") or [])
    st.markdown("### What Should Happen Next")
    st.markdown(
        "<div class='atlas-primary-action'>"
        "<strong>Primary Recommended Action</strong>"
        f"{_safe_text(prominent_next_actions[0] if prominent_next_actions else summary.get('recommended_next_action'), 'Review project findings and close critical gaps.')}"
        "</div>",
        unsafe_allow_html=True,
    )
    action_cols = st.columns(3)
    if action_cols[0].button("Open Scope & Risk", use_container_width=True):
        st.session_state["atlas_active_page"] = "Scope & Risk"
        st.rerun()
    if action_cols[1].button("Open BOM Review", use_container_width=True):
        st.session_state["atlas_active_page"] = "BOM Review"
        st.rerun()
    if action_cols[2].button("Open Estimate", use_container_width=True):
        st.session_state["atlas_active_page"] = "Estimate"
        st.rerun()

    st.markdown("### 1. What Atlas Found")
    st.dataframe(
        [
            {
                "Stakeholders (Inferred)": ", ".join(
                    list(
                        review.get("inferred_customer_and_stakeholder_information")
                        or []
                    )
                )
                or "None",
                "Major Systems": ", ".join(list(review.get("major_systems") or []))
                or "None",
                "BOM Summary": (
                    f"total={int(bom_summary.get('total_lines', 0) or 0)}, "
                    f"complete={int(bom_summary.get('complete_lines', 0) or 0)}, "
                    f"incomplete={int(bom_summary.get('incomplete_lines', 0) or 0)}, "
                    f"conflicts={int(bom_summary.get('conflicting_lines', 0) or 0)}"
                ),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 2. What Appears Complete")
    st.dataframe(
        [
            {
                "Complete BOM Lines": int(bom_summary.get("complete_lines", 0) or 0),
                "Known Cost Coverage": _safe_text(
                    cost_coverage.get("known_cost_coverage_ratio"),
                    "0%",
                ),
                "Labor Confidence": _safe_text(review.get("labor_confidence"), "n/a"),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Product Resolution Summary")
    st.dataframe(
        [
            {
                "Resolved Products": resolution_summary["resolved_products"],
                "Unknown Products": resolution_summary["unknown_products"],
                "Generic Allowances": resolution_summary["generic_allowances"],
                "Substitutions": resolution_summary["substitutions"],
                "Products Requiring Review": resolution_summary["requires_review"],
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 3. What Is Missing")
    missing_rows = [
        {"Missing Detail": item}
        for item in (
            list(review.get("missing_bom_detail") or [])
            + list(review.get("undeveloped_scope") or [])
        )
    ]
    if missing_rows:
        st.dataframe(missing_rows[:20], use_container_width=True, hide_index=True)
    else:
        st.info("No major missing scope or BOM details detected.")

    st.markdown("### 4. What Is Risky")
    risky_rows = [
        {"Major Risk Area": item}
        for item in (
            list(review.get("major_risk_areas") or [])
            + list(review.get("product_lifecycle_warnings") or [])
        )
    ]
    if risky_rows:
        st.dataframe(risky_rows[:20], use_container_width=True, hide_index=True)
    else:
        st.info("No major risk areas detected from available evidence.")

    st.markdown("### 5. What Needs Clarification")
    clarification_rows = [
        {"Clarification Needed": item}
        for item in (
            list(review.get("responsibility_gaps") or [])
            + [
                f"Quantity conflict: {item}"
                for item in list(review.get("quantity_conflicts") or [])
            ]
            + [
                f"Drawing/specification coordination: {item}"
                for item in list(
                    review.get("drawing_specification_coordination_issues") or []
                )
            ]
        )
    ]
    if clarification_rows:
        st.dataframe(clarification_rows[:20], use_container_width=True, hide_index=True)
    else:
        st.info("No major clarification items detected.")

    st.markdown("### 6. What Should Happen Next")
    next_action_rows = [
        {"Recommended Next Action": item}
        for item in list(review.get("recommended_next_actions") or [])
    ]
    if next_action_rows:
        st.dataframe(next_action_rows[:12], use_container_width=True, hide_index=True)
    else:
        st.info("No recommended next actions generated.")

    st.markdown("### Recommended RFIs")
    rfi_rows = [
        {"RFI (Internal Draft)": item}
        for item in list(review.get("recommended_rfis") or [])
    ]
    if rfi_rows:
        st.dataframe(rfi_rows[:12], use_container_width=True, hide_index=True)
    else:
        st.info("No recommended RFIs generated.")

    st.markdown("### Limitations")
    st.dataframe(
        [{"Limitation": item} for item in list(review.get("limitations") or [])],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Export")
    review_obj = SalesDesignReviewService().build_review(
        summary=_build_project_analysis_summary(record, context),
        bom_rows=_enriched_bom_rows(st, _canonical_bom_items(context)),
        scope_findings=_scope_risk_findings(context),
    )
    export_cols = st.columns(3)
    project_id = _safe_text(record.project.project_id, "project")
    export_cols[0].download_button(
        "Download Review Markdown",
        data=SalesDesignReviewService().to_markdown(review_obj),
        file_name=f"{project_id}_sales_design_review.md",
        mime="text/markdown",
        use_container_width=True,
    )
    export_cols[1].download_button(
        "Download Review JSON",
        data=SalesDesignReviewService().to_json(review_obj),
        file_name=f"{project_id}_sales_design_review.json",
        mime="application/json",
        use_container_width=True,
    )
    export_cols[2].download_button(
        "Download Review HTML",
        data=SalesDesignReviewService().to_html(review_obj),
        file_name=f"{project_id}_sales_design_review.html",
        mime="text/html",
        use_container_width=True,
    )

    _render_review_transition(
        st,
        record,
        context,
        "engineering",
        mark_label="Mark Engineering Findings Reviewed",
    )


def _render_import_history_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    del record, context
    _render_page_header(
        st,
        "Import History",
        "Immutable price sheet import history with deterministic version comparisons.",
    )

    commercial_service = _commercial_service(st)
    history_rows = commercial_service.import_history_rows()
    if not history_rows:
        _render_guided_empty_state(
            st,
            why_empty="No commercial import history exists yet.",
            action_to_populate="Upload and import one or more price lists in Price List Library.",
            next_location="Open Price List Library and run Import Price Lists.",
        )
        return

    st.dataframe(
        [
            {
                "Import Date": row.get("import_date"),
                "Vendor": row.get("vendor"),
                "Manufacturer": row.get("manufacturer"),
                "Version": row.get("version"),
                "Rows Imported": row.get("rows_imported"),
                "Products Added": row.get("products_added"),
                "Products Removed": row.get("products_removed"),
                "Products Changed": row.get("products_changed"),
                "Warnings": "; ".join(list(row.get("warnings") or [])),
                "Comparison Summary": (
                    f"+{len((row.get('comparison_summary') or {}).get('products_added') or [])} "
                    f"-{len((row.get('comparison_summary') or {}).get('products_removed') or [])} "
                    f"~{len((row.get('comparison_summary') or {}).get('products_updated') or [])}"
                ),
            }
            for row in history_rows
        ],
        use_container_width=True,
        hide_index=True,
    )

    version_lookup = {
        f"{row.get('version')} | {row.get('vendor')} | {row.get('manufacturer')} | {row.get('import_date')}": row
        for row in history_rows
    }
    selected = st.selectbox(
        "Open previous version",
        options=list(version_lookup.keys()),
        key="atlas_commercial_history_selected_version",
    )
    selected_row = dict(version_lookup[selected])
    comparison = dict(selected_row.get("comparison_summary") or {})

    st.markdown("### Selected Version Detail")
    st.dataframe(
        [
            {
                "Version": selected_row.get("version"),
                "Vendor": selected_row.get("vendor"),
                "Manufacturer": selected_row.get("manufacturer"),
                "Rows Imported": selected_row.get("rows_imported"),
                "Products Added": len(comparison.get("products_added") or []),
                "Products Removed": len(comparison.get("products_removed") or []),
                "Price Increased": len(comparison.get("price_increased") or []),
                "Price Decreased": len(comparison.get("price_decreased") or []),
                "Lead Time Changed": len(comparison.get("lead_time_changed") or []),
                "Availability Changed": len(
                    comparison.get("availability_changed") or []
                ),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_workflow_reports_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    import json

    summary = _build_project_analysis_summary(record, context)
    step_rows = _review_step_status_rows(st, record, context)
    checklist_rows = _review_checklist_rows(st, record, context, step_rows)
    next_action = _next_review_action(step_rows)
    completed_steps = sum(
        1 for row in step_rows if _safe_text(row.get("status"), "") == "complete"
    )

    _render_page_header(
        st,
        "Reports",
        "Project report center for guided review completion and deterministic exports.",
    )

    st.markdown("### Guided Review Progress")
    st.progress(completed_steps / max(len(step_rows), 1))
    st.dataframe(
        [
            {
                "Step": row.get("step"),
                "Status": _status_chip(_safe_text(row.get("status"), "").title()),
                "Page": row.get("page"),
                "Detail": row.get("detail"),
            }
            for row in step_rows
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Recommended Next Action")
    st.markdown(
        "<div class='atlas-primary-action'>"
        "<strong>Next Review Step</strong>"
        f"{_safe_text(next_action.get('step'), 'Generate Summary Report')}"
        "<br/>"
        f"{_safe_text(next_action.get('detail'), _safe_text(summary.get('recommended_next_action'), 'Generate project summary report.'))}"
        "</div>",
        unsafe_allow_html=True,
    )
    action_cols = st.columns(2)
    if action_cols[0].button(
        f"Open {_safe_text(next_action.get('page'), 'Overview')}",
        use_container_width=True,
        type="primary",
    ):
        st.session_state["atlas_active_page"] = _safe_text(
            next_action.get("page"),
            "Overview",
        )
        st.rerun()
    action_cols[1].caption(_safe_text(next_action.get("why"), ""))

    st.markdown("### Project Review Checklist")
    st.dataframe(
        [
            {
                "Checklist": row.get("Checklist Item"),
                "Status": _status_chip(_safe_text(row.get("Status"), "").title()),
                "Detail": row.get("Detail"),
            }
            for row in checklist_rows
        ],
        use_container_width=True,
        hide_index=True,
    )

    report_views = [
        "Project Summary",
        "Estimator Brief",
        "BOM Export",
        "Scope and Risk Export",
        "Engineering Review Export",
    ]
    report_view = st.radio(
        "Reports Navigation",
        options=report_views,
        horizontal=True,
        key="atlas_reports_view",
    )

    if report_view == "Project Summary":
        payload = _summary_report_payload(st, record, context)
        markdown_report = _summary_report_markdown(payload)
        json_report = json.dumps(payload, indent=2, sort_keys=True)
        html_report = _summary_report_html(payload)

        st.markdown("### Project Overview")
        st.dataframe(
            [dict(payload.get("project_overview") or {})],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Documents Reviewed")
        st.dataframe(
            [dict(payload.get("documents_reviewed") or {})],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### BOM Summary")
        st.dataframe(
            [dict(payload.get("bom_summary") or {})],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Missing or Incomplete BOM Detail")
        missing_bom = list(payload.get("missing_or_incomplete_bom_detail") or [])
        if missing_bom:
            st.dataframe(
                [
                    {
                        "BOM Item ID": item.get("bom_item_id"),
                        "Completeness": item.get("completeness_status"),
                        "Description": item.get("description"),
                        "Warnings": ", ".join(list(item.get("warnings") or []))
                        or "None",
                    }
                    for item in missing_bom[:12]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No incomplete BOM details are currently open.")

        st.markdown("### Scope Gaps")
        scope_gaps = list(payload.get("scope_gaps") or [])
        if scope_gaps:
            st.dataframe(
                [
                    {
                        "Severity": item.get("severity"),
                        "Title": item.get("title"),
                        "Action": item.get("recommended_action"),
                    }
                    for item in scope_gaps[:10]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No scope gaps currently open.")

        st.markdown("### Responsibility Risks")
        responsibility = list(payload.get("responsibility_risks") or [])
        if responsibility:
            st.dataframe(
                [
                    {
                        "Severity": item.get("severity"),
                        "Title": item.get("title"),
                        "Likely Owner": item.get("likely_owner"),
                    }
                    for item in responsibility[:10]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No responsibility risks currently open.")

        st.markdown("### Engineering Risks")
        engineering_risks = list(payload.get("engineering_risks") or [])
        if engineering_risks:
            st.dataframe(
                [
                    {
                        "Severity": item.get("severity"),
                        "Title": item.get("title"),
                        "Action": item.get("recommended_action"),
                    }
                    for item in engineering_risks[:10]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No engineering risks currently open.")

        st.markdown("### Recommended RFIs")
        rfis = list(payload.get("recommended_rfis") or [])
        if rfis:
            st.dataframe(
                [
                    {
                        "Title": item.get("title"),
                        "Severity": item.get("severity"),
                        "Internal Draft": item.get("candidate_rfi_text"),
                    }
                    for item in rfis[:10]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No recommended RFIs currently open.")

        st.markdown("### Estimate Coverage")
        st.dataframe(
            [dict(payload.get("estimate_coverage") or {})],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Recommended Next Actions")
        st.dataframe(
            list(payload.get("recommended_next_actions") or [])[:12],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Known Limitations")
        limitations = list(payload.get("known_limitations") or [])
        if limitations:
            st.dataframe(
                [{"limitation": item} for item in limitations],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No known limitations were captured.")

        with st.expander("Expanded Detail", expanded=False):
            st.markdown("#### Guided Review Steps")
            st.dataframe(
                list(payload.get("guided_review_steps") or []),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("#### Full Checklist")
            st.dataframe(
                list(payload.get("review_checklist") or []),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("#### BOM Exception Detail")
            st.dataframe(
                list(payload.get("missing_or_incomplete_bom_detail") or [])[:100],
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("#### Confidence Calculations")
            st.dataframe(
                [
                    {
                        "Analysis Status": summary.get("analysis_status"),
                        "Unresolved Scope Issues": summary.get(
                            "unresolved_scope_issue_count"
                        ),
                        "High Risk Issues": summary.get("high_risk_issue_count"),
                        "Documents Requiring OCR": summary.get(
                            "documents_requiring_ocr"
                        ),
                    }
                ],
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("### Export Project Summary")
        export_cols = st.columns(3)
        exported_md = export_cols[0].download_button(
            "Download Project Summary Markdown",
            data=markdown_report,
            file_name=f"{record.project.project_id}_project_summary_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        exported_json = export_cols[1].download_button(
            "Download Project Summary JSON",
            data=json_report,
            file_name=f"{record.project.project_id}_project_summary_report.json",
            mime="application/json",
            use_container_width=True,
        )
        exported_html = export_cols[2].download_button(
            "Download Project Summary HTML",
            data=html_report,
            file_name=f"{record.project.project_id}_project_summary_report.html",
            mime="text/html",
            use_container_width=True,
        )
        if exported_md or exported_json or exported_html:
            _set_review_flag(st, "summary_report_generated", True)
            _set_review_flag(st, "summary_report_generated_at", _now_iso())

        _render_review_transition(
            st,
            record,
            context,
            "summary_report",
            mark_label="Mark Summary Report Generated",
        )

    elif report_view == "Estimator Brief":
        brief = context.get("brief") if context else None
        if brief is None:
            _render_guided_empty_state(
                st,
                why_empty="Estimator brief is not available for this project context.",
                action_to_populate="Run project analysis and revisit Reports.",
                next_location="Go to Documents and run project analysis.",
            )
        else:
            brief_dict = brief.to_dict() if hasattr(brief, "to_dict") else {}
            st.dataframe([brief_dict], use_container_width=True, hide_index=True)
            brief_json = json.dumps(brief_dict, indent=2, sort_keys=True)
            brief_markdown = "# Estimator Brief\n\n```json\n" + brief_json + "\n```\n"
            export_cols = st.columns(2)
            export_cols[0].download_button(
                "Download Estimator Brief Markdown",
                data=brief_markdown,
                file_name=f"{record.project.project_id}_estimator_brief.md",
                mime="text/markdown",
                use_container_width=True,
            )
            export_cols[1].download_button(
                "Download Estimator Brief JSON",
                data=brief_json,
                file_name=f"{record.project.project_id}_estimator_brief.json",
                mime="application/json",
                use_container_width=True,
            )

    elif report_view == "BOM Export":
        bom_rows = _enriched_bom_rows(st, _canonical_bom_items(context))
        if not bom_rows:
            _render_guided_empty_state(
                st,
                why_empty="BOM export is unavailable because no BOM lines exist yet.",
                action_to_populate="Run project analysis and review BOM lines.",
                next_location="Go to Documents, run analysis, then BOM Review.",
            )
        else:
            st.dataframe(
                [dict(_canonical_bom_metrics(bom_rows))],
                use_container_width=True,
                hide_index=True,
            )
            export_csv, export_json = _canonical_bom_export_payload(bom_rows)
            export_cols = st.columns(2)
            export_cols[0].download_button(
                "Download Candidate BOM CSV",
                data=export_csv,
                file_name=f"{record.project.project_id}_candidate_bom.csv",
                mime="text/csv",
                use_container_width=True,
            )
            export_cols[1].download_button(
                "Download Candidate BOM JSON",
                data=export_json,
                file_name=f"{record.project.project_id}_candidate_bom.json",
                mime="application/json",
                use_container_width=True,
            )

    elif report_view == "Scope and Risk Export":
        findings = _scope_risk_findings(context)
        if not findings:
            _render_guided_empty_state(
                st,
                why_empty="Scope and risk export is unavailable because no findings were generated.",
                action_to_populate="Run project analysis and review Scope & Risk.",
                next_location="Go to Documents, run analysis, then Scope & Risk.",
            )
        else:
            metrics = _scope_risk_metrics(findings)
            export_payload = {
                "metrics": metrics,
                "findings": findings,
            }
            json_payload = json.dumps(export_payload, indent=2, sort_keys=True)
            markdown_lines = [
                "# Scope and Risk Export",
                "",
                f"- Total findings: {int(metrics.get('total', 0) or 0)}",
                f"- Critical findings: {int(metrics.get('critical', 0) or 0)}",
                f"- High severity findings: {int(metrics.get('high', 0) or 0)}",
                "",
                "## Findings",
            ]
            for item in findings[:40]:
                markdown_lines.append(
                    "- "
                    + _safe_text(item.get("finding_id"), "finding")
                    + " | "
                    + _safe_text(item.get("severity"), "n/a")
                    + " | "
                    + _safe_text(item.get("title"), "n/a")
                )
            markdown_payload = "\n".join(markdown_lines) + "\n"
            st.dataframe(findings[:20], use_container_width=True, hide_index=True)
            export_cols = st.columns(2)
            export_cols[0].download_button(
                "Download Scope and Risk Markdown",
                data=markdown_payload,
                file_name=f"{record.project.project_id}_scope_risk.md",
                mime="text/markdown",
                use_container_width=True,
            )
            export_cols[1].download_button(
                "Download Scope and Risk JSON",
                data=json_payload,
                file_name=f"{record.project.project_id}_scope_risk.json",
                mime="application/json",
                use_container_width=True,
            )

    else:
        review_obj = SalesDesignReviewService().build_review(
            summary=_build_project_analysis_summary(record, context),
            bom_rows=_enriched_bom_rows(st, _canonical_bom_items(context)),
            scope_findings=_scope_risk_findings(context),
        )
        st.dataframe(
            [review_obj.to_dict() if hasattr(review_obj, "to_dict") else {}],
            use_container_width=True,
            hide_index=True,
        )
        export_cols = st.columns(3)
        project_id = _safe_text(record.project.project_id, "project")
        export_cols[0].download_button(
            "Download Engineering Review Markdown",
            data=SalesDesignReviewService().to_markdown(review_obj),
            file_name=f"{project_id}_sales_design_review.md",
            mime="text/markdown",
            use_container_width=True,
        )
        export_cols[1].download_button(
            "Download Engineering Review JSON",
            data=SalesDesignReviewService().to_json(review_obj),
            file_name=f"{project_id}_sales_design_review.json",
            mime="application/json",
            use_container_width=True,
        )
        export_cols[2].download_button(
            "Download Engineering Review HTML",
            data=SalesDesignReviewService().to_html(review_obj),
            file_name=f"{project_id}_sales_design_review.html",
            mime="text/html",
            use_container_width=True,
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
        "Overview",
        "Concise project workspace landing page with status, readiness, and next actions.",
    )

    summary = _build_project_analysis_summary(record, context)
    import_summary = dict(context.get("import_summary") or {}) if context else {}
    bom_rows = _enriched_bom_rows(st, _canonical_bom_items(context))
    bom_metrics = _canonical_bom_metrics(bom_rows)
    scope_rows = _scope_risk_findings(context)
    engineering_review = _sales_design_review(st, record, context)
    timeline = _timeline_events(record, context)
    step_rows = _review_step_status_rows(st, record, context)
    checklist_rows = _review_checklist_rows(st, record, context, step_rows)
    next_action = _next_review_action(step_rows)
    completed_steps = sum(
        1 for row in step_rows if _safe_text(row.get("status"), "") == "complete"
    )

    st.markdown("### Recommended Next Action")
    st.markdown(
        "<div class='atlas-primary-action'>"
        "<strong>Do This Next</strong>"
        f"{_safe_text(next_action.get('step'), 'Review Documents')}"
        "<br/>"
        f"{_safe_text(next_action.get('detail'), _safe_text(summary.get('recommended_next_action'), 'Open Documents and run project analysis.'))}"
        "</div>",
        unsafe_allow_html=True,
    )
    link_cols = st.columns(2)
    if link_cols[0].button(
        f"Open {_safe_text(next_action.get('page'), 'Documents')}",
        use_container_width=True,
        type="primary",
    ):
        st.session_state["atlas_active_page"] = _safe_text(
            next_action.get("page"),
            "Documents",
        )
        st.rerun()
    link_cols[1].caption(_safe_text(next_action.get("why"), ""))

    st.markdown("### Guided Project Review")
    st.progress(completed_steps / max(len(step_rows), 1))
    st.caption(f"{completed_steps} of {len(step_rows)} steps complete")
    st.dataframe(
        [
            {
                "Step": row.get("step"),
                "Status": _status_chip(_safe_text(row.get("status"), "").title()),
                "Page": row.get("page"),
                "Detail": row.get("detail"),
            }
            for row in step_rows
        ],
        use_container_width=True,
        hide_index=True,
    )

    primary_actions = st.columns(4)
    if primary_actions[0].button("Open Documents", use_container_width=True):
        st.session_state["atlas_active_page"] = "Documents"
        st.rerun()
    if primary_actions[1].button("Open BOM Review", use_container_width=True):
        st.session_state["atlas_active_page"] = "BOM Review"
        st.rerun()
    if primary_actions[2].button("Open Scope & Risk", use_container_width=True):
        st.session_state["atlas_active_page"] = "Scope & Risk"
        st.rerun()
    if primary_actions[3].button("Open Engineering Review", use_container_width=True):
        st.session_state["atlas_active_page"] = "Engineering Review"
        st.rerun()

    st.markdown("### Object Navigation")
    nav_cols = st.columns(2)
    recent = list(st.session_state.get("atlas_recently_viewed_objects") or [])
    working_set = _working_set(st)

    with nav_cols[0]:
        st.markdown("#### Recently Viewed Objects")
        if recent:
            st.dataframe(
                [
                    {
                        "Object": _safe_text(item.get("display_name"), "Object"),
                        "Type": _safe_text(item.get("object_type"), "n/a"),
                        "Project": _safe_text(item.get("project_name"), "n/a"),
                        "Last Viewed": _safe_text(item.get("last_viewed_at"), "n/a"),
                    }
                    for item in recent[:10]
                ],
                use_container_width=True,
                hide_index=True,
            )
            target = st.selectbox(
                "Open recently viewed",
                options=[
                    f"{_safe_text(item.get('object_type'), '')}: {_safe_text(item.get('display_name'), '')}"
                    for item in recent[:10]
                ],
                key="atlas_overview_recent_open",
            )
            selected = recent[:10][
                [
                    f"{_safe_text(item.get('object_type'), '')}: {_safe_text(item.get('display_name'), '')}"
                    for item in recent[:10]
                ].index(target)
            ]
            if st.button(
                "Open Recently Viewed",
                key="atlas_overview_open_recent",
                use_container_width=True,
            ):
                st.session_state["atlas_active_page"] = _safe_text(
                    selected.get("route"),
                    "Overview",
                )
                _set_context_selection(
                    st,
                    _safe_text(selected.get("selection_kind"), "project"),
                    dict(selected.get("selection_data") or {}),
                )
                st.rerun()
        else:
            _render_guided_empty_state(
                st,
                why_empty="No recently viewed objects yet.",
                action_to_populate="Open an equipment, drawing, specification, or related object detail.",
                next_location="Navigate through object pages to build recent history.",
            )

    with nav_cols[1]:
        st.markdown("#### Working Set")
        st.caption("Keep important project objects close while you review the project.")
        if working_set:
            st.dataframe(
                [
                    {
                        "Object": _safe_text(item.get("display_name"), "Object"),
                        "Type": _safe_text(item.get("object_type"), "n/a"),
                        "Project": _safe_text(item.get("project_name"), "n/a"),
                        "Route": _safe_text(item.get("route"), "Overview"),
                    }
                    for item in working_set[:10]
                ],
                use_container_width=True,
                hide_index=True,
            )
            target = st.selectbox(
                "Open Working Set object",
                options=[
                    f"{_safe_text(item.get('object_type'), '')}: {_safe_text(item.get('display_name'), '')}"
                    for item in working_set[:10]
                ],
                key="atlas_overview_pinned_open",
            )
            selected = working_set[:10][
                [
                    f"{_safe_text(item.get('object_type'), '')}: {_safe_text(item.get('display_name'), '')}"
                    for item in working_set[:10]
                ].index(target)
            ]
            open_col, remove_col, up_col, down_col = st.columns(4)
            if open_col.button(
                "Open",
                key="atlas_overview_open_pinned",
                use_container_width=True,
            ):
                st.session_state["atlas_active_page"] = _safe_text(
                    selected.get("route"),
                    "Overview",
                )
                _set_context_selection(
                    st,
                    _safe_text(selected.get("selection_kind"), "project"),
                    dict(selected.get("selection_data") or {}),
                )
                st.rerun()
            if remove_col.button(
                "Remove",
                key="atlas_overview_unpin_selected",
                use_container_width=True,
            ):
                _toggle_pin_reference(st, selected, should_pin=False)
                st.rerun()
            if up_col.button(
                "Move Up",
                key="atlas_overview_working_set_up",
                use_container_width=True,
            ):
                _move_working_set_item(
                    st,
                    object_id=_safe_text(selected.get("object_id"), ""),
                    object_type=_safe_text(selected.get("object_type"), ""),
                    direction=-1,
                )
                st.rerun()
            if down_col.button(
                "Move Down",
                key="atlas_overview_working_set_down",
                use_container_width=True,
            ):
                _move_working_set_item(
                    st,
                    object_id=_safe_text(selected.get("object_id"), ""),
                    object_type=_safe_text(selected.get("object_type"), ""),
                    direction=1,
                )
                st.rerun()

            if st.button(
                "Clear Working Set",
                key="atlas_overview_clear_working_set",
                use_container_width=True,
            ):
                st.session_state["atlas_pinned_objects"] = []
                st.rerun()
        else:
            _render_guided_empty_state(
                st,
                why_empty="Working Set is empty.",
                action_to_populate="Add important objects from search or object detail pages.",
                next_location="Use Add to Working Set on object cards and detail headers.",
            )

    st.markdown("### Project Review Checklist")
    st.dataframe(
        [
            {
                "Checklist": row.get("Checklist Item"),
                "Status": _status_chip(_safe_text(row.get("Status"), "").title()),
                "Detail": row.get("Detail"),
            }
            for row in checklist_rows
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Critical Issues")
    critical_scope = [
        item
        for item in scope_rows
        if _safe_text(item.get("severity"), "").lower() in {"critical", "high"}
    ]
    if critical_scope:
        st.dataframe(
            [
                {
                    "Severity": item.get("severity"),
                    "Issue": item.get("title"),
                    "Impact": item.get("estimating_impact"),
                    "Recommended Action": item.get("recommended_action"),
                }
                for item in critical_scope[:10]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No critical issues are currently open.")

    st.markdown("### Project Summary")
    st.dataframe(
        [
            {
                "Project": summary["project_name"],
                "Customer": summary["customer"],
                "Project Type": summary["project_type"],
                "Current Status": summary["analysis_status"],
                "Recommended Next Action": summary["recommended_next_action"],
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    cards = st.columns(4)
    _metric_card(cards[0], "BOM Status", str(bom_metrics["total_candidate_bom_lines"]))
    _metric_card(cards[1], "Scope & Risk", str(len(scope_rows)))
    _metric_card(cards[2], "Document Health", str(summary["document_count"]))
    _metric_card(
        cards[3],
        "Engineering Review Status",
        "Ready" if engineering_review else "Needs Review",
    )

    st.markdown("### Estimate Status")
    known_cost_lines = sum(1 for row in bom_rows if row.get("known_cost") is not None)
    st.dataframe(
        [
            {
                "Lines With Known Cost": known_cost_lines,
                "Preliminary Cost Coverage": (
                    f"{int((known_cost_lines / max(len(bom_rows), 1)) * 100)}%"
                    if bom_rows
                    else "0%"
                ),
                "Advisory Mode": "Enabled",
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Recent Project Activity")
    if timeline:
        st.dataframe(timeline[:10], use_container_width=True, hide_index=True)
    else:
        _render_guided_empty_state(
            st,
            why_empty="Recent activity is empty because this workspace has no recorded events yet.",
            action_to_populate="Upload documents or run project analysis to generate activity.",
            next_location="Go to Documents and run project analysis.",
        )

    st.caption(
        f"Document status snapshot: total files={import_summary.get('total_files', 0)}, drawings={import_summary.get('drawing_count', 0)}, specifications={import_summary.get('specification_count', 0)}, schedules={import_summary.get('schedule_count', 0)}."
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


def _master_library_rows(
    st: Any, context: dict[str, Any] | None
) -> list[dict[str, Any]]:
    cached = _context_cached(context, "master_library_rows")
    if isinstance(cached, list):
        return cached

    objects = _workspace_objects(context)
    master_service = MasterLibraryService()
    master_service.import_workspace_equipment(list(objects.get("equipment") or []))
    rows = master_service.explorer_rows()

    commercial_service = _commercial_product_service(st)
    commercial_rows = commercial_service.product_rows(include_project_only=True)
    commercial_state = commercial_service.to_dict()
    all_vendor_offerings = list(commercial_state.get("vendor_offerings", {}).values())
    commercial_by_model: dict[str, dict[str, Any]] = {}
    for item in commercial_rows:
        manufacturer = _safe_text(item.get("manufacturer"), "").upper()
        for sku in [
            _safe_text(item.get("canonical_sku"), ""),
            _safe_text(item.get("manufacturer_sku"), ""),
        ] + list(item.get("alternate_skus") or []):
            if manufacturer and _safe_text(sku, ""):
                commercial_by_model[
                    f"{manufacturer}::{_safe_text(sku, '').upper()}"
                ] = item

    enriched_rows: list[dict[str, Any]] = []
    for row in rows:
        key = (
            f"{_safe_text(row.get('manufacturer'), '').upper()}::"
            f"{_safe_text(row.get('model'), '').upper()}"
        )
        commercial = dict(commercial_by_model.get(key) or {})
        enriched_rows.append(
            {
                **row,
                "atlas_product_uuid": _safe_text(
                    commercial.get("atlas_product_uuid"), ""
                ),
                "canonical_sku": _safe_text(
                    commercial.get("canonical_sku"), _safe_text(row.get("model"), "")
                ),
                "alternate_skus": list(commercial.get("alternate_skus") or []),
                "discipline": _safe_text(commercial.get("discipline"), "general"),
                "lifecycle_status": _safe_text(
                    commercial.get("lifecycle_status"),
                    _safe_text(row.get("status"), "pending_verification"),
                ),
                "vendor": _safe_text(
                    dict(commercial.get("commercial") or {}).get("preferred_vendor"),
                    "",
                ),
                "commercial_metadata": dict(commercial.get("commercial") or {}),
                "commercial_health": dict(commercial.get("commercial_health") or {}),
                "product_intelligence": dict(
                    commercial.get("product_intelligence") or {}
                ),
                "confidence_summary": dict(commercial.get("confidence") or {}),
                "vendor_offerings": [
                    item
                    for item in all_vendor_offerings
                    if _safe_text(item.get("atlas_product_uuid"), "")
                    == _safe_text(commercial.get("atlas_product_uuid"), "")
                ],
                "price_history": list(commercial.get("price_history") or []),
                "import_history": list(commercial.get("import_history") or []),
                "project_references": list(commercial.get("project_references") or []),
                "project_only": bool(commercial.get("project_only", False)),
            }
        )

    rows = enriched_rows
    _set_context_cached(context, "master_library_rows", rows)
    return rows


def _search_match_candidates(reference: dict[str, Any]) -> tuple[str, str, str, str]:
    object_id = _safe_text(reference.get("object_id"), "").lower()
    name = _safe_text(reference.get("display_name"), "").lower()
    secondary = _safe_text(reference.get("secondary_label"), "").lower()
    extra = " ".join(
        _safe_text(item, "")
        for item in list(reference.get("match_fields") or [])
        if _safe_text(item, "")
    ).lower()
    return object_id, name, secondary, extra


def _search_rank(
    reference: dict[str, Any],
    query: str,
    *,
    project_open: bool,
) -> tuple[int, int, str, str]:
    normalized_query = query.strip().lower()
    object_id, name, secondary, extra = _search_match_candidates(reference)
    exact_fields = {item for item in [object_id, name] + extra.split(" ") if item}

    tier = 9
    if normalized_query and normalized_query == object_id:
        tier = 0
    elif normalized_query and normalized_query == name:
        tier = 1
    elif normalized_query and normalized_query in exact_fields:
        tier = 2
    elif normalized_query and any(
        value.startswith(normalized_query)
        for value in [object_id, name, secondary, extra]
        if value
    ):
        tier = 3
    elif normalized_query and normalized_query in " ".join(
        [object_id, name, secondary, extra]
    ):
        tier = 4

    scope = _safe_text(reference.get("scope"), "application")
    scope_penalty = 0
    if project_open and scope != "project" and tier > 2:
        scope_penalty = 1

    return (
        tier,
        scope_penalty,
        _safe_text(reference.get("object_type"), "Object"),
        _safe_text(reference.get("display_name"), "Object"),
    )


def _filter_search_results(
    references: list[dict[str, Any]],
    *,
    query: str,
    selected_types: list[str],
    project_open: bool,
) -> list[dict[str, Any]]:
    filtered = [
        item
        for item in references
        if (
            not selected_types
            or _safe_text(item.get("object_type"), "") in selected_types
        )
    ]
    if query:
        filtered = [
            item
            for item in filtered
            if _search_rank(item, query, project_open=project_open)[0] <= 4
        ]
    filtered.sort(
        key=lambda item: _search_rank(
            item,
            query,
            project_open=project_open,
        )
    )
    return filtered


def _group_search_results(
    references: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped_refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reference in references:
        grouped_refs[_safe_text(reference.get("object_type"), "Object")].append(
            reference
        )
    return grouped_refs


def _application_search_entries(
    st: Any,
    workspace_service: ProjectWorkspaceService,
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    project_rows = _project_library_rows(
        workspace_service,
        include_archived=True,
        limit=500,
    )
    for item in project_rows:
        record = item["record"]
        data = {
            "workspace_id": record.workspace_id,
            "project_name": record.project.name,
            "customer": _safe_text(item.get("customer"), "n/a"),
            "status": _safe_text(item.get("review_status"), "Needs Review"),
        }
        reference = _build_object_reference(
            kind="project_record",
            data=data,
            project_id=record.workspace_id,
            route="Overview",
            relationship_count=0,
            warning_count=0,
        )
        reference["project_name"] = record.project.name
        reference["scope"] = "application"
        reference["match_fields"] = [
            record.workspace_id,
            record.project.name,
            _safe_text(item.get("customer"), ""),
        ]
        references.append(reference)

    manufacturer_rows = [item.to_dict() for item in build_manufacturer_seed_data()]
    for item in manufacturer_rows:
        data = {
            "manufacturer": _safe_text(item.get("name"), "Manufacturer"),
            "status": "active" if bool(item.get("active", True)) else "inactive",
            "discipline": _safe_text(item.get("discipline"), "n/a"),
        }
        reference = _build_object_reference(
            kind="manufacturer",
            data=data,
            project_id="application",
            route="Knowledge",
            relationship_count=0,
            warning_count=0,
        )
        reference["project_name"] = "Knowledge"
        reference["scope"] = "application"
        reference["match_fields"] = [
            _safe_text(item.get("name"), ""),
            _safe_text(item.get("discipline"), ""),
        ]
        references.append(reference)

    vendor_rows = [item.to_dict() for item in build_vendor_seed_data()]
    for item in vendor_rows:
        data = {
            "vendor": _safe_text(item.get("name"), "Vendor"),
            "vendor_type": _safe_text(item.get("vendor_type"), "n/a"),
            "status": _safe_text(item.get("status"), "n/a"),
        }
        reference = _build_object_reference(
            kind="vendor",
            data=data,
            project_id="application",
            route="Knowledge",
            relationship_count=0,
            warning_count=0,
        )
        reference["project_name"] = "Knowledge"
        reference["scope"] = "application"
        reference["match_fields"] = [
            _safe_text(item.get("name"), ""),
            _safe_text(item.get("vendor_type"), ""),
        ]
        references.append(reference)

    customers = sorted(
        {_safe_text(item.get("customer"), "n/a") for item in project_rows}
    )
    for customer in customers:
        data = {
            "customer": customer,
            "portfolio": f"projects {sum(1 for row in project_rows if _safe_text(row.get('customer'), '') == customer)}",
            "status": "indexed",
        }
        reference = _build_object_reference(
            kind="customer",
            data=data,
            project_id="application",
            route="Knowledge",
            relationship_count=0,
            warning_count=0,
        )
        reference["project_name"] = "Knowledge"
        reference["scope"] = "application"
        reference["match_fields"] = [customer]
        references.append(reference)

    product_rows: list[dict[str, Any]] = []
    for item in project_rows:
        project_record = item["record"]
        try:
            artifact = workspace_service.manager.review_repository.load_artifact(
                project_record.workspace_id,
                "bid_package_review",
            )
        except Exception:
            artifact = None
        if not isinstance(artifact, dict):
            continue
        equipment_rows = list(artifact.get("equipment") or [])
        if not equipment_rows:
            continue
        service = MasterLibraryService()
        service.import_workspace_equipment(equipment_rows)
        product_rows.extend(service.explorer_rows())

    deduped_products: dict[str, dict[str, Any]] = {}
    for row in product_rows:
        key = _safe_text(row.get("product_id"), "")
        if key and key not in deduped_products:
            deduped_products[key] = row

    for item in list(deduped_products.values()):
        reference = _build_object_reference(
            kind="master_product",
            data=item,
            project_id="application",
            route="Knowledge",
            relationship_count=0,
            warning_count=0,
        )
        reference["project_name"] = "Knowledge"
        reference["scope"] = "application"
        reference["match_fields"] = [
            _safe_text(item.get("product_id"), ""),
            _safe_text(item.get("atlas_product_uuid"), ""),
            _safe_text(item.get("model"), ""),
            _safe_text(item.get("canonical_sku"), ""),
            _safe_text(item.get("manufacturer_sku"), ""),
            _safe_text(item.get("manufacturer"), ""),
            _safe_text(item.get("category"), ""),
            _safe_text(item.get("discipline"), ""),
            _safe_text(item.get("product_family"), _safe_text(item.get("family"), "")),
            _safe_text(
                item.get("lifecycle_status"), _safe_text(item.get("status"), "")
            ),
            _safe_text(item.get("vendor"), ""),
            _safe_text(item.get("price_version"), ""),
            str(
                dict(
                    item.get("confidence") or item.get("confidence_summary") or {}
                ).get("overall_confidence", "")
            ),
            " ".join(list(item.get("alternate_skus") or [])),
        ]
        references.append(reference)

    library_state = _price_list_library_state(st)
    for item in list(library_state.get("uploaded_price_lists") or []):
        data = {
            "source_file": _safe_text(item.get("source_file"), "Price List"),
            "manufacturer": _safe_text(item.get("manufacturer"), ""),
            "vendor": _safe_text(item.get("vendor"), ""),
            "status": _safe_text(item.get("status"), "indexed"),
            "confidence": item.get("confidence", "n/a"),
        }
        reference = _build_object_reference(
            kind="price_list",
            data=data,
            project_id="application",
            route="Knowledge",
            relationship_count=0,
            warning_count=int(item.get("unmatched_rows", 0) or 0),
        )
        reference["project_name"] = "Knowledge"
        reference["scope"] = "application"
        reference["match_fields"] = [
            _safe_text(item.get("source_file"), ""),
            _safe_text(item.get("manufacturer"), ""),
            _safe_text(item.get("vendor"), ""),
        ]
        references.append(reference)

    return references


def _global_search_entries(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord | None,
    context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = _application_search_entries(st, workspace_service)

    if record is None or context is None:
        return entries

    objects = _workspace_objects(context)
    resolver_result = _build_engineering_resolver(record=None, context=context)

    def _append_project_reference(
        *,
        kind: str,
        data: dict[str, Any],
        route: str,
        warning_count: int = 0,
        match_fields: list[str] | None = None,
    ) -> None:
        reference = _build_object_reference(
            kind=kind,
            data=data,
            project_id=record.project.project_id,
            route=route,
            relationship_count=0,
            warning_count=warning_count,
        )
        reference["project_name"] = record.project.name
        reference["scope"] = "project"
        reference["match_fields"] = list(match_fields or [])
        entries.append(reference)

    for item in objects["equipment"]:
        _append_project_reference(
            kind="equipment",
            data=item,
            route="Equipment",
            warning_count=len(list(item.get("warnings") or [])),
            match_fields=[
                _safe_text(item.get("equipment_id"), ""),
                _safe_text(item.get("manufacturer"), ""),
                _safe_text(item.get("model"), ""),
            ],
        )
    for item in objects["drawings"]:
        _append_project_reference(
            kind="drawing",
            data=item,
            route="Drawings",
            warning_count=len(list(item.get("warnings") or [])),
            match_fields=[
                _safe_text(item.get("drawing_number"), ""),
                _safe_text(item.get("title"), ""),
            ],
        )
    for item in objects["specifications"]:
        _append_project_reference(
            kind="specification",
            data=item,
            route="Specifications",
            warning_count=0,
            match_fields=[
                _safe_text(item.get("section"), ""),
                _safe_text(item.get("title"), ""),
            ],
        )
    for item in objects["systems"]:
        _append_project_reference(
            kind="system",
            data=item,
            route="Systems",
            match_fields=[_safe_text(item.get("system"), "")],
        )
    for item in objects["rooms"]:
        _append_project_reference(
            kind="room",
            data=item,
            route="Equipment",
            match_fields=[
                _safe_text(item.get("room"), ""),
                _safe_text(item.get("room_or_area"), ""),
            ],
        )
    for item in objects["coordination_findings"]:
        data = {
            "title": _safe_text(item.get("title"), "Risk"),
            "status": _safe_text(item.get("severity"), "needs review"),
            "category": _safe_text(item.get("category"), ""),
        }
        _append_project_reference(
            kind="risk",
            data=data,
            route="Scope & Risk",
            warning_count=(
                1
                if _safe_text(item.get("severity"), "").lower() in {"high", "critical"}
                else 0
            ),
            match_fields=[
                _safe_text(item.get("title"), ""),
                _safe_text(item.get("category"), ""),
                _safe_text(item.get("severity"), ""),
            ],
        )
    for item in objects["rfis"]:
        _append_project_reference(
            kind="rfi",
            data=item,
            route="Scope & Risk",
            match_fields=[
                _safe_text(item.get("rfi_id"), ""),
                _safe_text(item.get("title"), ""),
            ],
        )
    for item in objects["evidence"]:
        _append_project_reference(
            kind="evidence",
            data=item,
            route="Evidence",
            match_fields=[
                _safe_text(item.get("source_file"), ""),
                _safe_text(item.get("excerpt"), ""),
            ],
        )

    for item in list(st.session_state.get("atlas_notebook_entries") or []):
        _append_project_reference(
            kind="notebook_entry",
            data=item,
            route="Notebook",
            match_fields=[
                _safe_text(item.get("title"), ""),
                _safe_text(item.get("entry_type"), ""),
                _safe_text(item.get("summary"), ""),
            ],
        )

    if resolver_result is not None:
        for item in list(getattr(resolver_result, "conflicts", []) or []):
            item_dict = item.to_dict()
            _append_project_reference(
                kind="risk",
                data={
                    "title": _safe_text(item_dict.get("message"), "Resolver Conflict"),
                    "status": "needs review",
                    "category": "resolver",
                },
                route="Relationships",
                warning_count=1,
                match_fields=[
                    _safe_text(item_dict.get("conflict_id"), ""),
                    _safe_text(item_dict.get("message"), ""),
                ],
            )

    graph = _build_knowledge_graph(record, context)
    for edge in list(graph.get("edges") or []):
        rel_type = _safe_text(edge.get("relationship"), "relationship")
        source = _node_label(graph, _safe_text(edge.get("source"), "source"))
        target = _node_label(graph, _safe_text(edge.get("target"), "target"))
        _append_project_reference(
            kind="risk",
            data={
                "title": f"{source} -> {target}",
                "status": "linked",
                "category": rel_type,
            },
            route="Relationships",
            match_fields=[
                source,
                target,
                rel_type,
                _safe_text(edge.get("source_evidence"), ""),
            ],
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


def _selection_kind_from_node(node: dict[str, Any]) -> str:
    node_kind = _safe_text(node.get("selection_kind"), "")
    if node_kind:
        return node_kind
    node_type = _safe_text(node.get("type"), "").lower()
    mapping = {
        "drawing": "drawing",
        "specification": "specification",
        "equipment": "equipment",
        "system": "system",
        "room": "room",
        "rfi candidate": "rfi",
        "evidence": "evidence",
        "manufacturer": "manufacturer",
        "product": "master_product",
    }
    return mapping.get(node_type, "project")


def _object_reference_from_node(
    node: dict[str, Any],
    *,
    record: ProjectWorkspaceRecord,
) -> dict[str, Any]:
    data = dict(node.get("data") or {})
    kind = _selection_kind_from_node(node)
    route = _safe_text(node.get("page"), _selection_route(kind))
    metadata = dict(node.get("metadata") or {})
    return _build_object_reference(
        kind=kind,
        data=data,
        project_id=record.project.project_id,
        route=route,
        relationship_count=int(metadata.get("relationship_count", 0) or 0),
        warning_count=int(
            metadata.get("warning_count", len(list(data.get("warnings") or [])) or 0)
        ),
    )


def _reference_groups_for_selection(
    record: ProjectWorkspaceRecord,
    graph: dict[str, Any],
    kind: str,
    data: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    node_id = _selection_node_id(kind, data)
    if not node_id:
        return [], []
    relationships = _node_relationships(graph, node_id)
    outgoing = []
    for edge in list(relationships.get("outgoing") or []):
        target = _node_by_id(graph, _safe_text(edge.get("target"), ""))
        if target is None:
            continue
        outgoing.append(_object_reference_from_node(target, record=record))
    incoming = []
    for edge in list(relationships.get("incoming") or []):
        source = _node_by_id(graph, _safe_text(edge.get("source"), ""))
        if source is None:
            continue
        incoming.append(_object_reference_from_node(source, record=record))
    return outgoing, incoming


def _render_reference_group(
    st: Any,
    *,
    title: str,
    references: list[dict[str, Any]],
    empty_message: str,
    key_prefix: str,
) -> None:
    st.markdown(f"#### {title}")
    if not references:
        _render_guided_empty_state(
            st,
            why_empty=empty_message,
            action_to_populate="Import or analyze source documents that establish object links.",
            next_location="Review Documents, Drawings, Specifications, and Equipment mappings.",
        )
        return
    for index, reference in enumerate(references[:12]):
        _render_object_card(st, reference, key_prefix=f"{key_prefix}_{index}")


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
    review = _sales_design_review(st, record, context)
    resolver_result = _build_engineering_resolver(record, context)
    rows = _build_resolver_conflict_rows(resolver_result)
    if not rows:
        "Internal Sales / Design Engineer Review for estimator, sales engineering, design engineering, and bid strategy workflows.",
        return

    if review is None:
        st.info("Run project analysis to generate an internal engineering review.")
        return

    summary = dict(review.get("project_summary") or {})
    bom_summary = dict(review.get("bom_summary") or {})
    cost_coverage = dict(review.get("preliminary_cost_coverage") or {})

    cards = st.columns(4)
    _metric_card(cards[0], "Project", _safe_text(summary.get("project_name"), "n/a"))
    _metric_card(
        cards[1],
        "Analysis Status",
        _safe_text(summary.get("analysis_status"), "n/a"),
    )
    _metric_card(
        cards[2],
        "Overall Confidence",
        f"{int(float(review.get('overall_confidence', 0.0)) * 100)}%",
    )
    _metric_card(
        cards[3],
        "BOM Lines",
        str(int(bom_summary.get("total_lines", 0) or 0)),
    )

    st.caption(
        "Conclusions are traceable to BOM, scope/risk findings, resolver conflicts, and source references. Unsupported conclusions are labeled under limitations."
    )

    st.markdown("### 1. What Atlas Found")
    st.dataframe(
        [
            {
                "Project Summary": _safe_text(summary.get("project_name"), "n/a"),
                "Project Type": _safe_text(review.get("project_type"), "Unspecified"),
                "Stakeholders (Inferred)": ", ".join(
                    list(
                        review.get("inferred_customer_and_stakeholder_information")
                        or []
                    )
                )
                or "None",
                "Major Systems": ", ".join(list(review.get("major_systems") or []))
                or "None",
                "BOM Summary": (
                    f"total={int(bom_summary.get('total_lines', 0) or 0)}, "
                    f"complete={int(bom_summary.get('complete_lines', 0) or 0)}, "
                    f"incomplete={int(bom_summary.get('incomplete_lines', 0) or 0)}, "
                    f"conflicts={int(bom_summary.get('conflicting_lines', 0) or 0)}"
                ),
                "Preliminary Cost Coverage": _safe_text(
                    cost_coverage.get("known_cost_coverage_ratio"),
                    "0%",
                ),
                "Labor Confidence": _safe_text(review.get("labor_confidence"), "n/a"),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 2. What Appears Complete")
    st.dataframe(
        [
            {
                "Complete BOM Lines": int(bom_summary.get("complete_lines", 0) or 0),
                "Known Cost Lines": int(
                    cost_coverage.get("lines_with_known_cost", 0) or 0
                ),
                "List Price Lines": int(
                    cost_coverage.get("lines_with_list_price", 0) or 0
                ),
                "Labor Confidence": _safe_text(review.get("labor_confidence"), "n/a"),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 3. What Is Missing")
    missing_rows = [
        {"Missing Detail": item}
        for item in (
            list(review.get("missing_bom_detail") or [])
            + list(review.get("undeveloped_scope") or [])
        )
    ]
    if missing_rows:
        st.dataframe(missing_rows[:20], use_container_width=True, hide_index=True)
    else:
        st.info("No major missing scope or BOM detail detected.")

    st.markdown("### 4. What Is Risky")
    risk_rows = [
        {"Major Risk Area": item}
        for item in (
            list(review.get("major_risk_areas") or [])
            + list(review.get("product_lifecycle_warnings") or [])
        )
    ]
    if risk_rows:
        st.dataframe(risk_rows[:20], use_container_width=True, hide_index=True)
    else:
        st.info("No major risk areas detected from current evidence.")

    st.markdown("### 5. What Needs Clarification")
    clarification_rows = [
        {"Clarification Needed": item}
        for item in (
            list(review.get("responsibility_gaps") or [])
            + [
                f"Quantity conflict: {item}"
                for item in list(review.get("quantity_conflicts") or [])
            ]
            + [
                f"Drawing/spec coordination: {item}"
                for item in list(
                    review.get("drawing_specification_coordination_issues") or []
                )
            ]
        )
    ]
    if clarification_rows:
        st.dataframe(
            clarification_rows[:24],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No major clarification gaps detected.")

    st.markdown("### 6. What Should Happen Next")
    next_action_rows = [
        {"Action": item} for item in list(review.get("recommended_next_actions") or [])
    ]
    if next_action_rows:
        st.dataframe(next_action_rows[:12], use_container_width=True, hide_index=True)
    else:
        st.info("No next actions generated yet.")

    st.markdown("### Recommended RFIs")
    rfi_rows = [
        {"RFI (Internal Draft)": item}
        for item in list(review.get("recommended_rfis") or [])
    ]
    if rfi_rows:
        st.dataframe(rfi_rows[:12], use_container_width=True, hide_index=True)
    else:
        st.info("No recommended RFIs generated.")

    st.markdown("### Limitations")
    limitation_rows = [
        {"Limitation": item} for item in list(review.get("limitations") or [])
    ]
    st.dataframe(limitation_rows, use_container_width=True, hide_index=True)

    st.markdown("### Export")
    review_obj = SalesDesignReviewService().build_review(
        summary=_build_project_analysis_summary(record, context),
        bom_rows=_enriched_bom_rows(st, _canonical_bom_items(context)),
        scope_findings=_scope_risk_findings(context),
    )
    markdown_payload = SalesDesignReviewService().to_markdown(review_obj)
    json_payload = SalesDesignReviewService().to_json(review_obj)
    html_payload = SalesDesignReviewService().to_html(review_obj)

    export_cols = st.columns(3)
    project_id = _safe_text(record.project.project_id, "project")
    export_cols[0].download_button(
        "Download Review Markdown",
        data=markdown_payload,
        file_name=f"{project_id}_sales_design_review.md",
        mime="text/markdown",
        use_container_width=True,
    )
    export_cols[1].download_button(
        "Download Review JSON",
        data=json_payload,
        file_name=f"{project_id}_sales_design_review.json",
        mime="application/json",
        use_container_width=True,
    )
    export_cols[2].download_button(
        "Download Review HTML",
        data=html_payload,
        file_name=f"{project_id}_sales_design_review.html",
        mime="text/html",
        use_container_width=True,
    )

    with st.expander("Appendix: Detailed Evidence", expanded=False):
        traceability = [
            {"Traceability Note": item}
            for item in list(review.get("traceability_notes") or [])
        ]
        if traceability:
            st.dataframe(traceability, use_container_width=True, hide_index=True)

        bom_rows = _enriched_bom_rows(st, _canonical_bom_items(context))
        if bom_rows:
            st.markdown("#### Canonical BOM Evidence")
            st.dataframe(
                [
                    {
                        "BOM Item": row.get("bom_item_id"),
                        "System": row.get("system"),
                        "Manufacturer": row.get("manufacturer"),
                        "Model": row.get("model"),
                        "Quantity": row.get("quantity"),
                        "Completeness": row.get("completeness_status"),
                        "Sources": ", ".join(row.get("source_documents") or []),
                    }
                    for row in bom_rows[:30]
                ],
                use_container_width=True,
                hide_index=True,
            )

        findings = _scope_risk_findings(context)
        if findings:
            st.markdown("#### Scope & Risk Evidence")
            st.dataframe(
                [
                    {
                        "Finding ID": row.get("finding_id"),
                        "Category": row.get("category"),
                        "Severity": row.get("severity"),
                        "Title": row.get("title"),
                        "References": ", ".join(row.get("source_references") or []),
                    }
                    for row in findings[:30]
                ],
                use_container_width=True,
                hide_index=True,
            )
        return


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
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord | None,
    context: dict[str, Any] | None,
) -> None:
    query = str(st.session_state.get("atlas_global_search") or "").strip()
    is_open = bool(st.session_state.get("atlas_global_search_open", False))
    if not is_open and not query:
        return

    references = _global_search_entries(st, workspace_service, record, context)
    object_types = sorted(
        {
            _safe_text(item.get("object_type"), "")
            for item in references
            if item.get("object_type")
        }
    )

    if query:
        _record_recent_search_query(st, query)

    with st.expander("Search Filters", expanded=False):
        selected_types = st.multiselect(
            "Type filters",
            options=object_types,
            default=[],
            key="atlas_search_type_filters",
            help="Filter by object type.",
        )

    filtered = _filter_search_results(
        references,
        query=query,
        selected_types=list(selected_types),
        project_open=record is not None,
    )
    grouped_refs = _group_search_results(filtered)

    with st.expander(f"Global Search Results ({len(filtered)})", expanded=True):
        st.caption(
            "Ranking: exact identifier, exact name, exact model/drawing/spec number, prefix, then partial matches."
        )
        if not filtered:
            _render_guided_empty_state(
                st,
                why_empty=f"No search results match \"{query or 'current filters'}\".",
                action_to_populate="Try broader terms, remove type filters, or search by identifier/model/drawing/spec number.",
                next_location="Atlas searched projects, knowledge objects, equipment, drawings, specifications, systems, rooms, risks, RFIs, evidence, notebook entries, and relationships.",
            )
            if st.button(
                "Clear Search Filters",
                key="atlas_search_clear_filters",
                use_container_width=True,
            ):
                st.session_state["atlas_search_type_filters"] = []
                st.rerun()
            return

        for object_type in sorted(grouped_refs.keys()):
            st.markdown(f"#### {object_type}")
            st.dataframe(
                [
                    {
                        "Display Name": _safe_text(item.get("display_name"), "Object"),
                        "Type": _safe_text(item.get("object_type"), "Object"),
                        "Secondary": _safe_text(item.get("secondary_label"), "n/a"),
                        "Project": _safe_text(item.get("project_name"), "n/a"),
                        "Status": _safe_text(item.get("status"), "n/a"),
                        "Confidence": _safe_text(item.get("confidence"), "n/a"),
                        "Warnings": int(item.get("warning_count", 0) or 0),
                    }
                    for item in grouped_refs[object_type][:15]
                ],
                use_container_width=True,
                hide_index=True,
            )

        labels = [
            f"{_safe_text(item.get('object_type'), 'Object')}: {_safe_text(item.get('display_name'), 'Object')} | {_safe_text(item.get('secondary_label'), '')}"
            for item in filtered
        ]
        selected_label = st.selectbox(
            "Results", options=labels, key="atlas_search_result"
        )
        selected = filtered[labels.index(selected_label)]

        st.markdown(
            "<div class='atlas-object-card'>"
            f"<div class='atlas-object-header'>Selected Result: {_safe_text(selected.get('object_type'), 'Object')}</div>"
            f"{_safe_text(selected.get('display_name'), 'Object')}<br/><span class='atlas-muted'>{_safe_text(selected.get('secondary_label'), '')}</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        action_cols = st.columns(3)
        if action_cols[0].button(
            "Open Result",
            key="atlas_open_search_result",
            type="primary",
            use_container_width=True,
        ):
            _open_search_reference(st, workspace_service, selected)

        pinned = _is_reference_pinned(st, selected)
        if action_cols[1].button(
            "Remove from Working Set" if pinned else "Add to Working Set",
            key="atlas_search_pin_result",
            use_container_width=True,
        ):
            _toggle_pin_reference(st, selected, should_pin=not pinned)
            st.rerun()

        if action_cols[2].button(
            "Clear Working Set",
            key="atlas_search_clear_working_set",
            use_container_width=True,
        ):
            st.session_state["atlas_pinned_objects"] = []
            st.rerun()

        st.markdown("#### Working Set")
        st.caption("Keep important project objects close while you review the project.")
        working_set = _working_set(st)
        if working_set:
            st.dataframe(
                [
                    {
                        "Object": _safe_text(item.get("display_name"), "Object"),
                        "Type": _safe_text(item.get("object_type"), "n/a"),
                        "Project": _safe_text(item.get("project_name"), "n/a"),
                    }
                    for item in working_set[:12]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("Working Set is empty.")

        st.markdown("#### Recent Searches")
        recent_queries = list(st.session_state.get("atlas_recent_search_queries") or [])
        recent_opened = list(st.session_state.get("atlas_recent_opened_results") or [])
        if recent_queries:
            st.dataframe(
                [{"Query": item} for item in recent_queries[:8]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No recent queries.")

        if recent_opened:
            st.dataframe(
                [
                    {
                        "Object": _safe_text(item.get("display_name"), "Object"),
                        "Type": _safe_text(item.get("object_type"), "n/a"),
                        "Opened": _safe_text(item.get("last_opened_at"), "n/a"),
                    }
                    for item in recent_opened[:8]
                ],
                use_container_width=True,
                hide_index=True,
            )

        clear_cols = st.columns(2)
        if clear_cols[0].button(
            "Clear Recent Queries",
            key="atlas_clear_recent_queries",
            use_container_width=True,
        ):
            st.session_state["atlas_recent_search_queries"] = []
            st.rerun()
        if clear_cols[1].button(
            "Clear Recently Opened",
            key="atlas_clear_recent_opened",
            use_container_width=True,
        ):
            st.session_state["atlas_recent_opened_results"] = []
            st.rerun()

        st.markdown("#### Recently Viewed")
        recent = list(st.session_state.get("atlas_recently_viewed_objects") or [])
        if recent:
            st.dataframe(
                [
                    {
                        "Object": _safe_text(item.get("display_name"), "Object"),
                        "Type": _safe_text(item.get("object_type"), "n/a"),
                        "Project": _safe_text(item.get("project_name"), "n/a"),
                        "Last Viewed": _safe_text(item.get("last_viewed_at"), "n/a"),
                    }
                    for item in recent[:8]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No recently viewed objects.")


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

    if st.button("Run Project Analysis", type="primary", disabled=not uploaded_files):
        with st.spinner("Running project analysis..."):
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
            st.success("Project analysis completed and workspace updated.")
            st.rerun()


def _render_project_files_page(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Documents",
        "Upload project documents, review extraction health, and run project analysis.",
    )

    folder_counts = {
        key: len(value) for key, value in _files_by_folder(context).items()
    }
    st.markdown("### Summary")
    st.dataframe(
        [
            {
                "Drawings": folder_counts.get("Drawings", 0),
                "Specifications": folder_counts.get("Specifications", 0),
                "Schedules": folder_counts.get("Schedules", 0),
                "Addenda": folder_counts.get("Addenda", 0),
                "Images": folder_counts.get("Images", 0),
                "Other Documents": folder_counts.get("Other Documents", 0),
            }
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Primary Action")
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
        _render_guided_empty_state(
            st,
            why_empty="No files match your current folder filters.",
            action_to_populate="Clear filters or select another document folder.",
            next_location="Use Folder and status filters above.",
        )
        return

    st.dataframe(display_rows, use_container_width=True, hide_index=True)

    file_labels = [item["filename"] for item in filtered]
    selected_file = st.selectbox("Select file", options=file_labels)
    selected = next(item for item in filtered if item["filename"] == selected_file)
    _set_context_selection(st, "file", {"folder": folder_name, "file": selected})

    _render_review_transition(
        st,
        record,
        context,
        "documents",
        mark_label="Mark Documents Reviewed",
    )


def _render_drawings_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Drawing Workspace",
        "Search, inspect, and validate drawing relationships without leaving the workspace.",
    )
    objects = _workspace_objects(context)
    rows = list(objects.get("drawings", []))
    if not rows:
        _render_guided_empty_state(
            st,
            why_empty="No drawing objects are available.",
            action_to_populate="Upload drawings and run project analysis.",
            next_location="Go to Documents and run project analysis.",
        )
        return

    st.markdown("### Search and Filters")
    filter_cols = st.columns([2.8, 1.6, 1.6])
    query = filter_cols[0].text_input(
        "Search drawings",
        value=st.session_state.get("atlas_drawings_search", ""),
        key="atlas_drawings_search",
        placeholder="drawing number, title, discipline",
    )
    discipline_filter = filter_cols[1].multiselect(
        "Discipline",
        options=sorted(
            {_safe_text(item.get("discipline"), "General") for item in rows}
        ),
        default=[],
    )
    extraction_filter = filter_cols[2].selectbox(
        "Extraction",
        options=["All", "High", "Medium", "Low"],
    )

    filtered = [
        item
        for item in rows
        if (
            (not query.strip() or _contains_any(str(item), [query]))
            and (
                not discipline_filter
                or _safe_text(item.get("discipline"), "General") in discipline_filter
            )
            and (
                extraction_filter == "All"
                or _safe_text(item.get("extraction_quality"), "").lower()
                == extraction_filter.lower()
            )
        )
    ]

    st.markdown("### Drawing List")
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
        for item in filtered
    ]
    if not summary_rows:
        _render_guided_empty_state(
            st,
            why_empty="No drawings match the current filters.",
            action_to_populate="Clear filters or broaden your search.",
            next_location="Use Search and Filters above.",
        )
        return
    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    labels = [f"{item['drawing_number']} · {item['title']}" for item in filtered]
    selected_label = st.selectbox("Select Drawing Object", options=labels)
    selected = filtered[labels.index(selected_label)]
    _set_context_selection(st, "drawing", selected)

    graph = _build_knowledge_graph(record, context)
    drawing_reference = _build_object_reference(
        kind="drawing",
        data=selected,
        project_id=record.project.project_id,
        route="Drawings",
        relationship_count=0,
        warning_count=len(list(selected.get("warnings") or [])),
    )

    st.markdown("### Selected Drawing Detail")
    _render_object_header(
        st,
        record,
        drawing_reference,
        description=_safe_text(selected.get("title"), "Drawing object"),
        recommended_action="Review related equipment, specifications, and evidence.",
    )

    _render_object_metadata_table(
        st,
        "Metadata",
        [
            {"Property": "Drawing Number", "Value": selected["drawing_number"]},
            {"Property": "Title", "Value": selected["title"]},
            {"Property": "Revision", "Value": selected["revision"]},
            {"Property": "Issue Date", "Value": selected["issue_date"]},
            {"Property": "Discipline", "Value": selected["discipline"]},
            {
                "Property": "Sheet Category",
                "Value": _safe_text(selected.get("sheet_category"), "other"),
            },
            {
                "Property": "Sheet Sequence",
                "Value": _safe_text(selected.get("sheet_sequence"), "Not available"),
            },
            {
                "Property": "Drawing Scale",
                "Value": _safe_text(selected.get("drawing_scale"), "Not available"),
            },
            {"Property": "OCR Status", "Value": selected["ocr_status"]},
            {"Property": "Extraction Quality", "Value": selected["extraction_quality"]},
        ],
    )

    _render_object_reference_sections(
        st,
        record=record,
        graph=graph,
        kind="drawing",
        selected=selected,
        key_prefix=f"atlas_drawing_{_safe_text(selected.get('drawing_number'), 'drawing')}",
    )

    st.markdown("### Related Objects")
    related_tabs = st.tabs(
        [
            "Related Equipment",
            "Related Specifications",
            "Related Systems",
            "Evidence and Warnings",
            "Quick Navigation",
        ]
    )

    with related_tabs[0]:
        equipment_refs = list(selected.get("referenced_equipment") or [])
        if equipment_refs:
            st.dataframe(
                [
                    {
                        "Equipment": _equipment_human_label(context, ref),
                        "ID": ref,
                    }
                    for ref in equipment_refs
                ],
                use_container_width=True,
                hide_index=True,
            )
            for ref in equipment_refs[:12]:
                label = _equipment_human_label(context, ref)
                if st.button(
                    f"Open {label}",
                    key=f"atlas_drawing_open_equipment_{_safe_text(selected.get('drawing_number'), 'drawing')}_{ref}",
                    use_container_width=True,
                ):
                    _open_equipment_detail(
                        st,
                        equipment_id=ref,
                        origin_page="Drawings",
                        origin_key=_safe_text(selected.get("drawing_number"), ""),
                    )
        else:
            _render_guided_empty_state(
                st,
                why_empty="No related equipment is linked to this drawing.",
                action_to_populate="Verify equipment-to-drawing references in project files.",
                next_location="Review Equipment and Drawing Explorer links.",
            )

    with related_tabs[1]:
        specification_rows = [
            {"Specification": value}
            for value in list(selected.get("referenced_specifications") or [])
        ]
        if specification_rows:
            st.dataframe(specification_rows, use_container_width=True, hide_index=True)
        else:
            _render_guided_empty_state(
                st,
                why_empty="No related specifications are linked to this drawing.",
                action_to_populate="Verify cross references between drawing callouts and specs.",
                next_location="Review Specifications and cross-reference warnings.",
            )

    with related_tabs[2]:
        system_rows = [
            {"System": value}
            for value in list(selected.get("referenced_systems") or [])
        ]
        if system_rows:
            st.dataframe(system_rows, use_container_width=True, hide_index=True)
        else:
            _render_guided_empty_state(
                st,
                why_empty="No related systems are linked to this drawing.",
                action_to_populate="Run analysis after drawing/spec imports to resolve system links.",
                next_location="Review Systems workspace.",
            )

    with related_tabs[3]:
        evidence_rows = [
            {"Evidence": value}
            for value in list(selected.get("referenced_evidence") or [])
        ]
        warning_rows = [
            {"Warning": value} for value in list(selected.get("warnings") or [])
        ]
        st.markdown("#### Evidence")
        if evidence_rows:
            st.dataframe(evidence_rows, use_container_width=True, hide_index=True)
        else:
            _render_guided_empty_state(
                st,
                why_empty="No evidence is currently linked to this drawing.",
                action_to_populate="Confirm source references during document intake.",
                next_location="Open Evidence workspace for additional traceability.",
            )
        st.markdown("#### Warnings")
        if warning_rows:
            st.dataframe(warning_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No warnings are currently associated with this drawing.")

    with related_tabs[4]:
        nav_cols = st.columns(5)
        if nav_cols[0].button("Drawing Explorer", use_container_width=True):
            st.session_state["atlas_active_page"] = "Drawing Explorer"
            st.rerun()
        if nav_cols[1].button("Equipment", use_container_width=True):
            st.session_state["atlas_active_page"] = "Equipment"
            st.rerun()
        if nav_cols[2].button("Specifications", use_container_width=True):
            st.session_state["atlas_active_page"] = "Specifications"
            st.rerun()
        if nav_cols[3].button("Systems", use_container_width=True):
            st.session_state["atlas_active_page"] = "Systems"
            st.rerun()
        if nav_cols[4].button("Evidence", use_container_width=True):
            st.session_state["atlas_active_page"] = "Evidence"
            st.rerun()

    st.markdown("### Recommended Actions")
    drawing_actions = _object_recommended_actions("drawing", selected)
    st.dataframe(drawing_actions, use_container_width=True, hide_index=True)


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


def _render_specifications_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Specification Workspace",
        "Search, inspect, and validate specification relationships with deterministic traceability.",
    )
    objects = _workspace_objects(context)
    rows = list(objects.get("specifications", []))
    if not rows:
        _render_guided_empty_state(
            st,
            why_empty="No specification objects are available.",
            action_to_populate="Upload specification files and run project analysis.",
            next_location="Go to Documents and run project analysis.",
        )
        return

    st.markdown("### Search and Filters")
    filter_cols = st.columns([2.5, 1.4, 1.4, 1.4])
    query = filter_cols[0].text_input(
        "Search specifications",
        value=st.session_state.get("atlas_spec_search", ""),
        key="atlas_spec_search",
        placeholder="section, title, standards, manufacturers",
    )
    discipline_filter = filter_cols[1].selectbox(
        "Discipline",
        options=["All"]
        + sorted({_safe_text(item.get("discipline"), "other") for item in rows}),
    )
    status_filter = filter_cols[2].selectbox(
        "Status",
        options=["All"]
        + sorted({_safe_text(item.get("status"), "indexed") for item in rows}),
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

    filtered = [
        item
        for item in rows
        if (
            (not query.strip() or _contains_any(str(item), [query]))
            and (
                discipline_filter == "All"
                or _safe_text(item.get("discipline"), "other") == discipline_filter
            )
            and (
                status_filter == "All"
                or _safe_text(item.get("status"), "indexed") == status_filter
            )
            and (
                system_filter == "All"
                or system_filter in list(item.get("referenced_systems") or [])
            )
        )
    ]

    st.markdown("### Specification List")
    st.caption(
        f"Spec intelligence confidence: {_safe_text(objects.get('specification_intelligence_confidence'), 'n/a')} · "
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
            for item in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )

    if not filtered:
        _render_guided_empty_state(
            st,
            why_empty="No specifications match the current filters.",
            action_to_populate="Clear filters or broaden your search.",
            next_location="Use Search and Filters above.",
        )
        return

    labels = [f"{item['section']} · {item['title']}" for item in filtered]
    selected_label = st.selectbox("Select Specification Object", options=labels)
    selected = filtered[labels.index(selected_label)]
    _set_context_selection(st, "specification", selected)

    graph = _build_knowledge_graph(record, context)
    specification_reference = _build_object_reference(
        kind="specification",
        data=selected,
        project_id=record.project.project_id,
        route="Specifications",
        relationship_count=0,
        warning_count=0,
    )

    st.markdown("### Selected Specification Detail")
    _render_object_header(
        st,
        record,
        specification_reference,
        description=_safe_text(selected.get("title"), "Specification object"),
        recommended_action="Review references, requirements, and evidence consistency.",
    )

    _render_object_metadata_table(
        st,
        "Metadata",
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
                "value": _safe_text(selected.get("revision"), "Not available"),
            },
            {
                "property": "Issue Date",
                "value": _safe_text(selected.get("issue_date"), "Not available"),
            },
            {
                "property": "Cross References",
                "value": ", ".join(selected["cross_references"]) or "Not linked",
            },
            {
                "property": "Extraction Confidence",
                "value": selected["extraction_confidence"],
            },
        ],
    )

    _render_object_reference_sections(
        st,
        record=record,
        graph=graph,
        kind="specification",
        selected=selected,
        key_prefix=f"atlas_spec_{_safe_text(selected.get('section'), 'spec')}",
    )

    relationship_tabs = st.tabs(
        [
            "Requirement Candidates",
            "Related Drawings",
            "Related Equipment",
            "Related Systems",
            "Evidence and Warnings",
            "Quick Navigation",
        ]
    )

    with relationship_tabs[0]:
        requirement_rows = list(selected.get("requirement_candidates") or [])
        if requirement_rows:
            st.dataframe(requirement_rows, use_container_width=True, hide_index=True)
        else:
            _render_guided_empty_state(
                st,
                why_empty="No requirement candidates were detected for this section.",
                action_to_populate="Validate specification extraction and section indexing.",
                next_location="Review Specification Explorer and source files.",
            )

    with relationship_tabs[1]:
        drawing_rows = [
            {"Drawing": value}
            for value in list(selected.get("referenced_drawings") or [])
        ]
        if drawing_rows:
            st.dataframe(drawing_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No related drawings were detected for this specification section.")

    with relationship_tabs[2]:
        equipment_refs = list(selected.get("referenced_equipment") or [])
        if equipment_refs:
            st.dataframe(
                [
                    {
                        "Equipment": _equipment_human_label(context, ref),
                        "ID": ref,
                    }
                    for ref in equipment_refs
                ],
                use_container_width=True,
                hide_index=True,
            )
            for ref in equipment_refs[:12]:
                label = _equipment_human_label(context, ref)
                if st.button(
                    f"Open {label}",
                    key=f"atlas_spec_open_equipment_{_safe_text(selected.get('section'), 'section')}_{ref}",
                    use_container_width=True,
                ):
                    _open_equipment_detail(
                        st,
                        equipment_id=ref,
                        origin_page="Specifications",
                        origin_key=_safe_text(selected.get("section"), ""),
                    )
        else:
            st.info("No related equipment was detected for this specification section.")

    with relationship_tabs[3]:
        system_rows = [
            {"System": value}
            for value in list(selected.get("referenced_systems") or [])
        ]
        if system_rows:
            st.dataframe(system_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No related systems were detected for this specification section.")

    with relationship_tabs[4]:
        evidence_rows = [
            {"Evidence": value}
            for value in list(selected.get("referenced_evidence") or [])
        ]
        warning_rows = list(objects.get("specification_cross_reference_warnings") or [])
        st.markdown("#### Evidence")
        if evidence_rows:
            st.dataframe(evidence_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No evidence references are linked to this specification section.")
        st.markdown("#### Cross-Reference Warnings")
        if warning_rows:
            st.dataframe(warning_rows[:12], use_container_width=True, hide_index=True)
        else:
            st.info("No cross-reference warnings are currently detected.")

    with relationship_tabs[5]:
        nav_cols = st.columns(5)
        if nav_cols[0].button("Specification Explorer", use_container_width=True):
            st.session_state["atlas_active_page"] = "Specification Explorer"
            st.rerun()
        if nav_cols[1].button("Drawings", use_container_width=True):
            st.session_state["atlas_active_page"] = "Drawing Explorer"
            st.rerun()
        if nav_cols[2].button("Equipment", use_container_width=True):
            st.session_state["atlas_active_page"] = "Equipment"
            st.rerun()
        if nav_cols[3].button("Systems", use_container_width=True):
            st.session_state["atlas_active_page"] = "Systems"
            st.rerun()
        if nav_cols[4].button("Evidence", use_container_width=True):
            st.session_state["atlas_active_page"] = "Evidence"
            st.rerun()

    st.markdown("### Recommended Actions")
    spec_actions = _object_recommended_actions("specification", selected)
    st.dataframe(spec_actions, use_container_width=True, hide_index=True)


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


def _render_equipment_page(
    st: Any,
    record: ProjectWorkspaceRecord,
    context: dict[str, Any] | None,
) -> None:
    _render_page_header(
        st,
        "Equipment Workspace",
        "Object-first engineering view built from canonical BOM lines, scope findings, and source evidence.",
    )

    rows = _equipment_workspace_rows(st, context)
    if not rows:
        _render_guided_empty_state(
            st,
            why_empty="No equipment objects are available yet.",
            action_to_populate="Run project analysis to build canonical BOM lines and equipment relationships.",
            next_location="Go to Documents and run project analysis.",
        )
        return

    st.markdown("### Search and Filters")
    filter_cols = st.columns([2.3, 1.2, 1.1, 1.1, 1.1, 1.1, 1.1, 1.2])
    search_text = (
        filter_cols[0]
        .text_input(
            "Search equipment",
            key="atlas_equipment_search",
            placeholder="equipment id, manufacturer, model, description, system, room",
        )
        .strip()
        .lower()
    )
    manufacturer_filter = filter_cols[1].selectbox(
        "Manufacturer",
        options=["All"]
        + sorted({_safe_text(item.get("manufacturer"), "") for item in rows}),
        key="atlas_equipment_filter_manufacturer",
    )
    system_filter = filter_cols[2].selectbox(
        "System",
        options=["All"] + sorted({_safe_text(item.get("system"), "") for item in rows}),
        key="atlas_equipment_filter_system",
    )
    room_filter = filter_cols[3].selectbox(
        "Room",
        options=["All"]
        + sorted({_safe_text(item.get("room_or_area"), "") for item in rows}),
        key="atlas_equipment_filter_room",
    )
    completeness_filter = filter_cols[4].selectbox(
        "Completeness",
        options=["All"]
        + sorted({_safe_text(item.get("completeness_status"), "") for item in rows}),
        key="atlas_equipment_filter_completeness",
    )
    responsibility_filter = filter_cols[5].selectbox(
        "Responsibility",
        options=["All"]
        + sorted({_safe_text(item.get("responsibility"), "") for item in rows}),
        key="atlas_equipment_filter_responsibility",
    )
    lifecycle_filter = filter_cols[6].selectbox(
        "Lifecycle",
        options=["All"]
        + sorted({_safe_text(item.get("lifecycle_status"), "") for item in rows}),
        key="atlas_equipment_filter_lifecycle",
    )
    review_only = filter_cols[7].checkbox(
        "Requires review",
        key="atlas_equipment_filter_review_only",
        value=False,
    )

    confidence_min = st.slider(
        "Minimum confidence",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.05,
        key="atlas_equipment_filter_confidence",
    )

    filtered = [
        item
        for item in rows
        if (not search_text or search_text in str(item).lower())
        and (
            manufacturer_filter == "All"
            or _safe_text(item.get("manufacturer"), "") == manufacturer_filter
        )
        and (
            system_filter == "All"
            or _safe_text(item.get("system"), "") == system_filter
        )
        and (
            room_filter == "All"
            or _safe_text(item.get("room_or_area"), "") == room_filter
        )
        and (
            completeness_filter == "All"
            or _safe_text(item.get("completeness_status"), "") == completeness_filter
        )
        and (
            responsibility_filter == "All"
            or _safe_text(item.get("responsibility"), "") == responsibility_filter
        )
        and (
            lifecycle_filter == "All"
            or _safe_text(item.get("lifecycle_status"), "") == lifecycle_filter
        )
        and (float(item.get("confidence", 0.0) or 0.0) >= confidence_min)
        and (not review_only or bool(item.get("requires_review")))
    ]

    if not filtered:
        _render_guided_empty_state(
            st,
            why_empty="No equipment objects match the current filters.",
            action_to_populate="Relax filter settings or clear the search query.",
            next_location="Use Search and Filters above to broaden results.",
        )
        return

    st.markdown("### Equipment Summary")
    quantity_conflicts = sum(
        1
        for item in filtered
        if _safe_text(item.get("completeness_status"), "") == "conflicting_quantity"
    )
    discontinued_or_legacy = sum(
        1
        for item in filtered
        if _safe_text(item.get("lifecycle_status"), "").lower()
        in {"discontinued", "legacy", "obsolete"}
    )
    summary_row = {
        "total equipment items": len(filtered),
        "complete items": sum(
            1
            for item in filtered
            if _safe_text(item.get("completeness_status"), "") == "complete"
        ),
        "incomplete items": sum(
            1
            for item in filtered
            if _safe_text(item.get("completeness_status"), "")
            not in {"complete", "drawing_only", "specification_only"}
        ),
        "unresolved items": sum(
            1
            for item in filtered
            if _safe_text(item.get("completeness_status"), "") == "unresolved"
        ),
        "quantity conflicts": quantity_conflicts,
        "missing manufacturer": sum(
            1
            for item in filtered
            if _safe_text(item.get("completeness_status"), "") == "missing_manufacturer"
        ),
        "missing model": sum(
            1
            for item in filtered
            if _safe_text(item.get("completeness_status"), "") == "missing_model"
        ),
        "discontinued or legacy references": discontinued_or_legacy,
        "items without known cost": sum(
            1 for item in filtered if item.get("known_cost") is None
        ),
        "items requiring review": sum(
            1 for item in filtered if bool(item.get("requires_review"))
        ),
    }
    st.dataframe([summary_row], use_container_width=True, hide_index=True)

    st.markdown("### Equipment List")
    list_rows = [
        {
            "equipment": item.get("equipment_id"),
            "manufacturer": item.get("manufacturer"),
            "model": item.get("model"),
            "description": item.get("description"),
            "quantity": item.get("quantity"),
            "system": item.get("system"),
            "room": item.get("room_or_area"),
            "confidence": round(float(item.get("confidence", 0.0) or 0.0), 2),
            "completeness": item.get("completeness_status"),
            "responsibility": item.get("responsibility"),
            "lifecycle": item.get("lifecycle_status"),
            "requires review": bool(item.get("requires_review")),
        }
        for item in filtered
    ]
    st.dataframe(list_rows, use_container_width=True, hide_index=True)

    selection_labels = [
        f"{_safe_text(item.get('equipment_id'), '')} - {_safe_text(item.get('manufacturer'), '')} {_safe_text(item.get('model'), '')}".strip()
        for item in filtered
    ]

    default_index = 0
    current_selection = dict(st.session_state.get("atlas_context_selection") or {})
    current_equipment_id = _safe_text(
        dict(current_selection.get("data") or {}).get("equipment_id"),
        "",
    )
    if current_equipment_id:
        default_index = next(
            (
                idx
                for idx, item in enumerate(filtered)
                if _safe_text(item.get("equipment_id"), "") == current_equipment_id
            ),
            0,
        )

    selected_label = st.selectbox(
        "Select Equipment Detail",
        options=selection_labels,
        index=default_index,
        key="atlas_equipment_selected_label",
    )
    selected = filtered[selection_labels.index(selected_label)]
    _set_context_selection(st, "equipment", selected)

    origin = dict(st.session_state.get("atlas_equipment_origin") or {})
    origin_page = _safe_text(origin.get("page"), "")
    if origin_page:
        origin_cols = st.columns([7.5, 2.5])
        origin_cols[0].caption(
            f"Opened from {origin_page} ({_safe_text(origin.get('key'), 'context')})."
        )
        if origin_cols[1].button(
            f"Back to {origin_page}",
            key="atlas_equipment_back_to_origin",
            use_container_width=True,
        ):
            st.session_state["atlas_active_page"] = origin_page
            st.rerun()

    st.markdown("### Selected Equipment Detail")
    graph = _build_knowledge_graph(record, context)
    equipment_ref = _build_object_reference(
        kind="equipment",
        data=selected,
        project_id=record.project.project_id,
        route="Equipment",
        relationship_count=0,
        warning_count=len(list(selected.get("warnings") or [])),
    )
    _render_object_header(
        st,
        record,
        equipment_ref,
        description=_safe_text(selected.get("description"), "Equipment item"),
        recommended_action=_safe_text(
            (
                _equipment_recommended_actions(selected)[0]
                if _equipment_recommended_actions(selected)
                else {}
            ).get("action"),
            "Review equipment object",
        ),
    )

    detail_tabs = st.tabs(
        [
            "Overview",
            "Engineering",
            "References",
            "Scope and Risk",
            "Pricing",
            "Evidence",
        ]
    )

    with detail_tabs[0]:
        st.dataframe(
            [
                {
                    "manufacturer": selected.get("manufacturer"),
                    "model": selected.get("model"),
                    "description": selected.get("description"),
                    "quantity": selected.get("quantity"),
                    "system": selected.get("system"),
                    "room": selected.get("room_or_area"),
                    "completeness": selected.get("completeness_status"),
                    "responsibility": selected.get("responsibility"),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    with detail_tabs[1]:
        engineering_rows = [
            {
                "signal type": "n/a",
                "power": "n/a",
                "network": "n/a",
                "mounting": "n/a",
                "accessories": ", ".join(list(selected.get("missing_components") or []))
                or "None flagged",
                "labor": _safe_text(selected.get("labor_allowance"), "n/a"),
                "known requirements": ", ".join(list(selected.get("warnings") or []))
                or "n/a",
            }
        ]
        st.dataframe(engineering_rows, use_container_width=True, hide_index=True)

    with detail_tabs[2]:
        refs = {
            "drawings": list(selected.get("drawing_references") or []),
            "specifications": list(selected.get("specification_references") or []),
            "schedules": list(selected.get("schedule_references") or []),
            "addenda": [],
        }
        if any(refs.values()):
            st.dataframe(
                [
                    {
                        "drawings": ", ".join(refs["drawings"]) or "n/a",
                        "specifications": ", ".join(refs["specifications"]) or "n/a",
                        "schedules": ", ".join(refs["schedules"]) or "n/a",
                        "addenda": ", ".join(refs["addenda"]) or "n/a",
                    }
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            _render_guided_empty_state(
                st,
                why_empty="No source references are linked to this equipment object.",
                action_to_populate="Review BOM extraction and source mapping for this item.",
                next_location="Open BOM Review and Documents for source validation.",
            )

    with detail_tabs[3]:
        st.dataframe(
            [
                {
                    "missing accessories": ", ".join(
                        list(selected.get("missing_components") or [])
                    )
                    or "none",
                    "quantity conflict": (
                        "yes"
                        if _safe_text(selected.get("completeness_status"), "")
                        == "conflicting_quantity"
                        else "no"
                    ),
                    "discontinued status": selected.get("lifecycle_status"),
                    "responsibility ambiguity": (
                        "yes"
                        if "unknown"
                        in _safe_text(selected.get("responsibility"), "").lower()
                        else "no"
                    ),
                    "related scope findings": ", ".join(
                        list(selected.get("related_risks") or [])
                    )
                    or "none",
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    with detail_tabs[4]:
        st.dataframe(
            [
                {
                    "known cost": selected.get("known_cost"),
                    "list price": "n/a",
                    "vendor source": _safe_text(selected.get("pricing_source"), "n/a"),
                    "effective date": "n/a",
                    "match confidence": round(
                        float(selected.get("confidence", 0.0) or 0.0), 2
                    ),
                    "pricing warnings": ", ".join(
                        [
                            item
                            for item in list(selected.get("warnings") or [])
                            if "price" in item.lower()
                        ]
                    )
                    or "none",
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    with detail_tabs[5]:
        evidence_refs = list(selected.get("evidence_refs") or [])
        if evidence_refs:
            st.dataframe(
                [
                    {
                        "reference": ref,
                    }
                    for ref in evidence_refs[:25]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            _render_guided_empty_state(
                st,
                why_empty="No evidence references are currently linked to this equipment object.",
                action_to_populate="Confirm source document mapping for equipment extraction.",
                next_location="Review Documents and BOM evidence drill-down.",
            )

    _render_object_reference_sections(
        st,
        record=record,
        graph=graph,
        kind="equipment",
        selected=selected,
        key_prefix=f"atlas_equipment_{_safe_text(selected.get('equipment_id'), 'eq')}",
    )

    st.markdown("### Related Objects")
    related_cols = st.columns(2)
    with related_cols[0]:
        st.markdown("Referenced Drawings")
        drawing_refs = list(selected.get("drawing_references") or [])
        if drawing_refs:
            for drawing_ref in drawing_refs[:12]:
                if st.button(
                    f"Open {drawing_ref}",
                    key=f"atlas_equipment_open_drawing_{_safe_text(selected.get('equipment_id'), 'eq')}_{drawing_ref}",
                    use_container_width=True,
                ):
                    st.session_state["atlas_active_page"] = "Drawings"
                    _set_context_selection(
                        st, "drawing", {"drawing_number": drawing_ref}
                    )
                    st.rerun()
        else:
            st.caption("No drawing references.")

        st.markdown("Referenced Specifications")
        spec_refs = list(selected.get("specification_references") or [])
        if spec_refs:
            for spec_ref in spec_refs[:12]:
                if st.button(
                    f"Open {spec_ref}",
                    key=f"atlas_equipment_open_spec_{_safe_text(selected.get('equipment_id'), 'eq')}_{spec_ref}",
                    use_container_width=True,
                ):
                    st.session_state["atlas_active_page"] = "Specifications"
                    _set_context_selection(st, "specification", {"section": spec_ref})
                    st.rerun()
        else:
            st.caption("No specification references.")

    with related_cols[1]:
        st.markdown("System")
        system_name = _safe_text(selected.get("system"), "Unknown")
        if st.button(
            f"Open {system_name}",
            key=f"atlas_equipment_open_system_{_safe_text(selected.get('equipment_id'), 'eq')}",
            use_container_width=True,
        ):
            st.session_state["atlas_active_page"] = "Systems"
            _set_context_selection(st, "system", {"system": system_name})
            st.rerun()

        st.markdown("Room")
        room_name = _safe_text(selected.get("room_or_area"), "Unknown")
        st.caption(room_name)

        st.markdown("Related Risks")
        related_risks = list(selected.get("related_risks") or [])
        if related_risks:
            st.dataframe(
                [{"risk": value} for value in related_risks[:12]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No related risks linked.")

        st.markdown("Related RFIs")
        related_rfis = list(selected.get("related_rfi_candidates") or [])
        if related_rfis:
            st.dataframe(
                [{"rfi": value} for value in related_rfis[:12]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No related RFI candidates linked.")

    st.markdown("### Evidence and Warnings")
    warn_cols = st.columns(2)
    with warn_cols[0]:
        warnings = list(selected.get("warnings") or [])
        if warnings:
            st.dataframe(
                [{"warning": value} for value in warnings[:20]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No warnings.")
    with warn_cols[1]:
        st.dataframe(
            [
                {"evidence": value}
                for value in list(selected.get("evidence_refs") or [])[:20]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Recommended Actions")
    actions = _equipment_recommended_actions(selected)
    st.dataframe(actions, use_container_width=True, hide_index=True)
    if st.button(
        "Open Relationship Explorer",
        key=f"atlas_equipment_open_relationships_{_safe_text(selected.get('equipment_id'), 'eq')}",
        use_container_width=True,
    ):
        st.session_state["atlas_active_page"] = "Relationships"
        st.rerun()
    action_destinations = sorted(
        {
            _safe_text(item.get("destination"), "")
            for item in actions
            if _safe_text(item.get("destination"), "")
        }
    )
    if action_destinations:
        selected_destination = st.selectbox(
            "Navigate to action destination",
            options=action_destinations,
            key="atlas_equipment_action_destination",
        )
        if st.button("Open Action Destination", use_container_width=True):
            st.session_state["atlas_active_page"] = selected_destination
            st.rerun()


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

    rows = _master_library_rows(st, context)
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
        {
            str(
                item.get("lifecycle_status")
                or item.get("status")
                or "pending_verification"
            )
            for item in rows
        }
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
                or str(
                    item.get("lifecycle_status")
                    or item.get("status")
                    or "pending_verification"
                )
                in selected_statuses
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
            status_counts[
                str(
                    item.get("lifecycle_status")
                    or item.get("status")
                    or "pending_verification"
                )
            ] += 1
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
                "status": item.get("lifecycle_status") or item.get("status"),
                "vendor": item.get("vendor"),
                "aliases": len(list(item.get("aliases") or [])),
                "relationships": len(list(item.get("related_products") or [])),
                "confidence": dict(item.get("confidence_summary") or {}).get(
                    "overall_confidence",
                    item.get("confidence"),
                ),
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

    tabs = st.tabs(
        [
            "Overview",
            "Commercial",
            "Vendor Pricing",
            "Price History",
            "Engineering",
            "Compatibility",
            "Documents",
            "Lifecycle",
            "Related Products",
            "Project References",
            "Import History",
        ]
    )

    commercial_metadata = dict(selected.get("commercial_metadata") or {})
    engineering_metadata = dict(selected.get("engineering_attributes") or {})
    commercial_health = dict(selected.get("commercial_health") or {})
    product_intelligence = dict(selected.get("product_intelligence") or {})
    confidence_summary = dict(selected.get("confidence_summary") or {})
    vendor_offerings = list(selected.get("vendor_offerings") or [])
    price_history = list(selected.get("price_history") or [])
    import_history = list(selected.get("import_history") or [])
    project_refs = list(selected.get("project_references") or [])
    relationships = list(selected.get("related_products") or [])
    aliases = list(selected.get("aliases") or [])

    with tabs[0]:
        st.dataframe(
            [
                {
                    "Atlas Product UUID": _safe_text(
                        selected.get("atlas_product_uuid"), "n/a"
                    ),
                    "Product ID": _safe_text(selected.get("product_id"), "n/a"),
                    "Manufacturer": _safe_text(selected.get("manufacturer"), "n/a"),
                    "Model": _safe_text(selected.get("model"), "n/a"),
                    "Canonical SKU": _safe_text(
                        selected.get("canonical_sku"),
                        _safe_text(selected.get("model"), "n/a"),
                    ),
                    "Category": _safe_text(selected.get("category"), "n/a"),
                    "Family": _safe_text(
                        selected.get("product_family"),
                        _safe_text(selected.get("family"), "n/a"),
                    ),
                    "Discipline": _safe_text(selected.get("discipline"), "n/a"),
                    "Description": _safe_text(selected.get("description"), "n/a"),
                    "Confidence": _safe_text(
                        confidence_summary.get("overall_confidence"),
                        _safe_text(selected.get("confidence"), "n/a"),
                    ),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("#### Aliases")
        st.dataframe(
            [{"alias": str(item)} for item in aliases],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[1]:
        st.dataframe(
            [commercial_metadata or {"status": "No commercial metadata"}],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("#### Commercial Health")
        st.dataframe(
            [commercial_health or {"status": "No health metrics"}],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[2]:
        if vendor_offerings:
            st.dataframe(vendor_offerings, use_container_width=True, hide_index=True)
        else:
            st.info("No vendor offerings recorded for this product.")

    with tabs[3]:
        if price_history:
            st.dataframe(price_history, use_container_width=True, hide_index=True)
        else:
            st.info("No price history available.")

    with tabs[4]:
        st.dataframe(
            [engineering_metadata or {"status": "No engineering metadata"}],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[5]:
        st.dataframe(
            [
                {
                    "compatible_products": " | ".join(
                        list(product_intelligence.get("compatible_products") or [])
                    )
                    or "None",
                    "related_accessories": " | ".join(
                        list(product_intelligence.get("related_accessories") or [])
                    )
                    or "None",
                    "replacement_product": _safe_text(
                        product_intelligence.get("replacement_product"),
                        _safe_text(selected.get("replacement_product_uuid"), "None"),
                    ),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[6]:
        st.dataframe(
            [
                {
                    "product_image": _safe_text(selected.get("product_image"), ""),
                    "datasheet": _safe_text(selected.get("datasheet"), ""),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[7]:
        st.dataframe(
            [
                {
                    "lifecycle_status": _safe_text(
                        selected.get("lifecycle_status"),
                        _safe_text(selected.get("status"), "n/a"),
                    ),
                    "active": bool(selected.get("active", True)),
                    "replacement_product_uuid": _safe_text(
                        selected.get("replacement_product_uuid"),
                        "",
                    ),
                    "project_only": bool(selected.get("project_only", False)),
                    "created_at": _safe_text(selected.get("created_at"), "n/a"),
                    "updated_at": _safe_text(selected.get("updated_at"), "n/a"),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("#### Confidence Breakdown")
        st.dataframe(
            [
                confidence_summary
                or {"overall_confidence": _safe_text(selected.get("confidence"), "n/a")}
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[8]:
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

    with tabs[9]:
        if project_refs:
            st.dataframe(
                [{"project_reference": item} for item in project_refs],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No project references recorded.")

    with tabs[10]:
        if import_history:
            st.dataframe(import_history, use_container_width=True, hide_index=True)
        else:
            st.caption("No import history available.")

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
    st.subheader("Relationship Explorer")
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

    outgoing_type_options = sorted(
        {
            _safe_text(edge.get("relationship"), "")
            for edge in list(graph.get("edges") or [])
            if _safe_text(edge.get("relationship"), "")
        }
    )
    object_type_options = sorted({_safe_text(node.get("type"), "") for node in nodes})
    filter_cols = st.columns(2)
    relationship_filter = filter_cols[0].multiselect(
        "Relationship Type",
        options=outgoing_type_options,
        default=[],
        key="atlas_relationship_type_filter",
    )
    object_type_filter = filter_cols[1].multiselect(
        "Connected Object Type",
        options=object_type_options,
        default=[],
        key="atlas_relationship_object_type_filter",
    )

    relationships = _node_relationships(graph, _safe_text(selected_node.get("id"), ""))
    incoming = list(relationships.get("incoming", []))
    outgoing = list(relationships.get("outgoing", []))

    def _allowed(edge: dict[str, Any], connected_node: dict[str, Any] | None) -> bool:
        if (
            relationship_filter
            and _safe_text(edge.get("relationship"), "") not in relationship_filter
        ):
            return False
        if object_type_filter and connected_node is not None:
            return _safe_text(connected_node.get("type"), "") in object_type_filter
        return True

    incoming = [
        edge
        for edge in incoming
        if _allowed(edge, _node_by_id(graph, _safe_text(edge.get("source"), "")))
    ]
    outgoing = [
        edge
        for edge in outgoing
        if _allowed(edge, _node_by_id(graph, _safe_text(edge.get("target"), "")))
    ]

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

    st.markdown("#### Connected Objects")
    connected_refs: list[dict[str, Any]] = []
    for edge in outgoing:
        target = _node_by_id(graph, _safe_text(edge.get("target"), ""))
        if target is None:
            continue
        connected_refs.append(_object_reference_from_node(target, record=record))
    for edge in incoming:
        source = _node_by_id(graph, _safe_text(edge.get("source"), ""))
        if source is None:
            continue
        connected_refs.append(_object_reference_from_node(source, record=record))

    deduped_connected: list[dict[str, Any]] = []
    seen_connected: set[tuple[str, str]] = set()
    for item in connected_refs:
        key = (
            _safe_text(item.get("object_type"), ""),
            _safe_text(item.get("object_id"), ""),
        )
        if key in seen_connected:
            continue
        seen_connected.add(key)
        deduped_connected.append(item)

    if deduped_connected:
        for index, reference in enumerate(deduped_connected[:12]):
            _render_object_card(
                st, reference, key_prefix=f"atlas_rel_connected_{index}"
            )
    else:
        _render_guided_empty_state(
            st,
            why_empty="No connected objects match current relationship filters.",
            action_to_populate="Adjust relationship type/object type filters.",
            next_location="Use filters above to widen the connected object set.",
        )

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
                    "originating document": _safe_text(
                        (
                            dict(source_node.get("metadata") or {}).get("source_file")
                            if source_node is not None
                            else None
                        ),
                        "n/a",
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
        st.markdown("Warnings")
        source_data = dict(source_node.get("data") or {}) if source_node else {}
        target_data = dict(target_node.get("data") or {}) if target_node else {}
        warning_rows = [
            {
                "object": _safe_text(
                    source_node.get("label") if source_node else None, "n/a"
                ),
                "warnings": ", ".join(list(source_data.get("warnings") or []))
                or "None",
            },
            {
                "object": _safe_text(
                    target_node.get("label") if target_node else None, "n/a"
                ),
                "warnings": ", ".join(list(target_data.get("warnings") or []))
                or "None",
            },
        ]
        st.dataframe(warning_rows, use_container_width=True, hide_index=True)
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
        if nav_cols[0].button("Open Scope & Risk", use_container_width=True):
            st.session_state["atlas_active_page"] = "Scope & Risk"
            st.rerun()
        if nav_cols[1].button("Open Engineering Review", use_container_width=True):
            st.session_state["atlas_active_page"] = "Engineering Review"
            st.rerun()
        if nav_cols[2].button("Open Estimate", use_container_width=True):
            st.session_state["atlas_active_page"] = "Estimate"
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
            st.session_state["atlas_active_page"] = "Documents"
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
            st.session_state["atlas_active_page"] = "Notebook"
            st.rerun()
        if nav_cols[1].button("Open History", use_container_width=True):
            st.session_state["atlas_active_page"] = "Timeline"
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
    st: Any,
    record: ProjectWorkspaceRecord | None,
    context: dict[str, Any] | None,
) -> None:
    st.markdown("<div class='atlas-statusbar'></div>", unsafe_allow_html=True)
    intake = _safe_text(context.get("package_location") if context else None, "n/a")
    review_time = _safe_text(record.updated_at if record else None, "n/a")
    commit = _current_commit()

    cols = st.columns(5)
    cols[0].caption(
        f"Current project: {record.project.name if record is not None else 'None selected'}"
    )
    cols[1].caption(
        f"Lifecycle stage: {_project_stage(record) if record is not None else 'Application Workspace'}"
    )
    cols[2].caption(f"Last intake: {intake}")
    cols[3].caption(f"Last review: {review_time}")
    cols[4].caption(f"Atlas v{__version__} · commit {commit}")


def _render_main_content(
    st: Any,
    workspace_service: ProjectWorkspaceService,
    record: ProjectWorkspaceRecord | None,
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
        return

    if page == "Knowledge":
        _render_application_knowledge_page(st, workspace_service)
        return

    if page == "Administration":
        _render_application_administration_page(st, workspace_service)
        return

    if page == "Reports" and record is None:
        _render_application_reports_page(st, workspace_service)
        return

    if page in {
        "Projects",
        "Pinned Projects",
        "Reference Projects",
        "Recent Projects",
        "Create New Project",
        "Open Existing Project",
    }:
        if page == "Projects":
            _render_projects_page(st, workspace_service)
        elif page == "Pinned Projects":
            _render_pinned_projects_page(st, workspace_service)
        elif page == "Reference Projects":
            _render_reference_projects_page(st, workspace_service)
        elif page == "Recent Projects":
            _render_recent_projects_page(st, workspace_service)
        elif page == "Create New Project":
            _render_create_project_page(st, workspace_service)
        else:
            _render_open_existing_page(st, workspace_service)
        return

    if record is None:
        st.info(
            "Open a project from Projects or Mission Control to enter Project Workspace."
        )
        return

    if page == "Project Summary" or page == "Project Metadata":
        _render_project_summary_page(st, record, context)
    elif page == "Documents":
        _render_project_files_page(st, workspace_service, record, context)
    elif page == "Price List Library":
        _render_price_list_library_page(st, record, context)
    elif page == "Import History":
        _render_import_history_page(st, record, context)
    elif page == "BOM Review":
        _render_bom_review_page(st, record, context)
    elif page == "Scope & Risk":
        _render_scope_risk_page(st, record, context)
    elif page == "Engineering Review":
        _render_engineering_review_page(st, record, context)
    elif page == "Product Resolution":
        _render_product_resolution_page(st, record, context)
    elif page == "Estimate":
        _render_estimate_page(st, record, context)
    elif page == "Notebook":
        _render_engineering_notebook_page(st, record, context)
    elif page == "Overview":
        _render_overview_page(st, record, context)
    elif page == "Drawings":
        _render_drawings_page(st, record, context)
    elif page == "Specifications":
        _render_specifications_page(st, record, context)
    elif page == "Equipment":
        _render_equipment_page(st, record, context)
    elif page == "Schedules":
        _render_project_folder_page(st, context, "Schedules", "Schedules")
    elif page == "Addenda":
        _render_project_folder_page(st, context, "Addenda", "Addenda")
    elif page == "Relationships":
        _render_relationship_explorer_page(st, record, context)
    elif page == "Timeline":
        _render_timeline_page(st, record, context)
    elif page == "Repository":
        _render_settings_page(st, "Project Settings", workspace_service, record)
    elif page == "Workspace Settings":
        _render_settings_page(st, "Application Settings", workspace_service, record)
    elif page == "Reports":
        _render_workflow_reports_page(st, record, context)
    else:
        _render_empty_state(st, "Page is not available in the current workspace mode.")


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
            st.session_state["atlas_active_page"] = "Overview"
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
            st.session_state["atlas_active_page"] = "Timeline"
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
            st.session_state["atlas_active_page"] = "Timeline"
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
    record: ProjectWorkspaceRecord | None,
    context: dict[str, Any] | None,
) -> None:
    _render_header(st, workspace_service, record, context)
    _sync_notebook_state_to_context(st, context)

    current_page = st.session_state.get("atlas_active_page", "Mission Control")
    mission_control_payload = None
    if current_page == "Mission Control":
        if record is not None:
            mission_control_payload = _build_mission_control_payload(
                workspace_service,
                record,
                context,
            )
        else:
            mission_control_payload = {
                "signals": _collect_workspace_signals(workspace_service, limit=12),
                "actions": [],
                "timeline": [],
                "pending_timeline": [],
            }

    st.markdown(
        f"<div class='atlas-breadcrumb'>{_breadcrumb(record, current_page)}</div>",
        unsafe_allow_html=True,
    )

    _render_global_search_panel(
        st,
        workspace_service,
        record,
        context,
    )

    layout_mode = st.session_state.get("atlas_layout_mode", "Desktop")

    if layout_mode == "Desktop":
        nav_col, main_col = st.columns([2.3, 7.7])
        with nav_col:
            _nav_buttons(st, st, "desktop", record)
        with main_col:
            _render_main_content(
                st,
                workspace_service,
                record,
                context,
                mission_control_payload,
            )

    elif layout_mode == "Tablet":
        nav_popover = st.popover("Open Navigation")
        _nav_buttons(st, nav_popover, "tablet", record)
        _render_main_content(
            st,
            workspace_service,
            record,
            context,
            mission_control_payload,
        )

    else:
        nav_drawer = st.popover("Open Navigation")
        _nav_buttons(st, nav_drawer, "mobile", record)
        _render_main_content(
            st,
            workspace_service,
            record,
            context,
            mission_control_payload,
        )

    _render_status_bar(st, record, context)


def _build_workspace_service() -> ProjectWorkspaceService:
    runtime_root = ensure_runtime_workspace_root()
    return ProjectWorkspaceService(runtime_root)


def main() -> None:
    st = _load_streamlit()
    st.set_page_config(page_title="Atlas Workspace", layout="wide")
    _inject_styles(st)
    _init_session_state(st)

    workspace_service = _build_workspace_service()
    _ensure_active_workspace(st, workspace_service)

    record = _active_record(st, workspace_service)
    if record is not None:
        _restore_workspace_state(st, workspace_service, record)

    context = _load_context_for_record(record) if record is not None else None
    if record is not None and context is not None:
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

    if record is None and st.session_state.get("atlas_active_page") not in {
        "Mission Control",
        "Projects",
        "Pinned Projects",
        "Reference Projects",
        "Recent Projects",
        "Create New Project",
        "Open Existing Project",
        "Knowledge",
        "Reports",
        "Administration",
    }:
        st.session_state["atlas_active_page"] = "Mission Control"

    _render_shell(st, workspace_service, record, context)
    if record is not None:
        workspace_service.save_workspace_state(
            record.workspace_id,
            _workspace_state_snapshot(st),
        )


if __name__ == "__main__":
    main()

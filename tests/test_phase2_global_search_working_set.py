from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any

from atlas_core.domain import Project, ProjectStatus
from atlas_core.services.project_workspace_service import ProjectWorkspaceRecord
import pytest

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_test_module", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


@dataclass
class _FakeStreamlit:
    session_state: dict[str, Any]
    rerun_called: bool = False

    def rerun(self) -> None:
        self.rerun_called = True


class _FakeWorkspaceService:
    def __init__(self, records: list[ProjectWorkspaceRecord]) -> None:
        self._records = records

    def list_workspaces(
        self,
        include_archived: bool = True,
        limit: int = 1000,
    ) -> list[ProjectWorkspaceRecord]:
        return list(self._records)[:limit]


def _reference(
    *,
    object_id: str,
    display_name: str,
    object_type: str,
    scope: str,
    route: str = "Overview",
    match_fields: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "object_id": object_id,
        "display_name": display_name,
        "object_type": object_type,
        "secondary_label": "",
        "match_fields": list(match_fields or []),
        "scope": scope,
        "route": route,
        "selection_kind": "equipment",
        "selection_data": {"equipment_id": object_id},
    }


def _project_record(workspace_id: str, project_name: str) -> ProjectWorkspaceRecord:
    return ProjectWorkspaceRecord(
        workspace_id=workspace_id,
        project=Project(
            project_id=workspace_id,
            name=project_name,
            client="Client",
            status=ProjectStatus.INTAKE,
        ),
    )


def test_exact_identifier_match_ranks_first() -> None:
    exact = _reference(
        object_id="AV-601",
        display_name="Drawing AV-601",
        object_type="Drawing",
        scope="project",
        match_fields=["AV-601"],
    )
    partial = _reference(
        object_id="AV-602",
        display_name="Drawing AV-602",
        object_type="Drawing",
        scope="project",
        match_fields=["AV-602"],
    )

    filtered = app._filter_search_results(
        [partial, exact],
        query="AV-601",
        selected_types=[],
        project_open=True,
    )

    assert filtered[0]["object_id"] == "AV-601"


def test_partial_match_ranks_after_prefix() -> None:
    prefix = _reference(
        object_id="SPK-1",
        display_name="Speaker One",
        object_type="Equipment",
        scope="project",
        match_fields=["Speaker One"],
    )
    partial = _reference(
        object_id="SPK-2",
        display_name="Main Speaker Cluster",
        object_type="Equipment",
        scope="project",
        match_fields=["Main Speaker Cluster"],
    )

    filtered = app._filter_search_results(
        [partial, prefix],
        query="speak",
        selected_types=[],
        project_open=True,
    )

    assert filtered[0]["object_id"] == "SPK-1"


def test_project_scope_preferred_for_non_exact_matches() -> None:
    project_item = _reference(
        object_id="eq-1",
        display_name="Sony Display",
        object_type="Equipment",
        scope="project",
    )
    app_item = _reference(
        object_id="prod-sony-display",
        display_name="Sony Display",
        object_type="Product",
        scope="application",
    )

    filtered = app._filter_search_results(
        [app_item, project_item],
        query="sony",
        selected_types=[],
        project_open=True,
    )

    assert filtered[0]["scope"] == "project"


def test_search_grouping_uses_object_type() -> None:
    grouped = app._group_search_results(
        [
            _reference(
                object_id="d1",
                display_name="AV-601",
                object_type="Drawing",
                scope="project",
            ),
            _reference(
                object_id="e1",
                display_name="QSC Core",
                object_type="Equipment",
                scope="project",
            ),
        ]
    )

    assert set(grouped.keys()) == {"Drawing", "Equipment"}
    assert len(grouped["Drawing"]) == 1


def test_open_search_reference_routes_to_target_page() -> None:
    st = _FakeStreamlit(session_state={})
    service = _FakeWorkspaceService(records=[])
    reference = {
        "route": "Drawings",
        "selection_kind": "drawing",
        "selection_data": {"drawing_number": "AV-601"},
        "object_id": "AV-601",
        "object_type": "Drawing",
    }

    app._open_search_reference(st, service, reference)

    assert st.session_state["atlas_active_page"] == "Drawings"
    assert st.session_state["atlas_context_selection"]["kind"] == "drawing"
    assert st.rerun_called is True


def test_recent_search_queries_are_deduplicated() -> None:
    st = _FakeStreamlit(session_state={"atlas_recent_search_queries": ["AV-601"]})

    app._record_recent_search_query(st, "av-601")
    app._record_recent_search_query(st, "QSC")

    assert st.session_state["atlas_recent_search_queries"][0] == "QSC"
    assert len(st.session_state["atlas_recent_search_queries"]) == 2


def test_working_set_add_remove_and_move() -> None:
    st = _FakeStreamlit(session_state={"atlas_pinned_objects": []})
    first = {
        "object_id": "A",
        "object_type": "Equipment",
        "display_name": "A",
    }
    second = {
        "object_id": "B",
        "object_type": "Equipment",
        "display_name": "B",
    }

    app._toggle_pin_reference(st, first, should_pin=True)
    app._toggle_pin_reference(st, second, should_pin=True)
    app._move_working_set_item(
        st,
        object_id="A",
        object_type="Equipment",
        direction=-1,
    )

    assert st.session_state["atlas_pinned_objects"][0]["object_id"] == "A"

    app._toggle_pin_reference(st, first, should_pin=False)
    assert all(
        item["object_id"] != "A" for item in st.session_state["atlas_pinned_objects"]
    )


def test_workspace_snapshot_persists_working_set_and_search_history() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_active_page": "Overview",
            "atlas_context_selection": {"kind": "project", "data": {}},
            "atlas_file_search": "",
            "atlas_equipment_search": "",
            "atlas_search_type_filters": [],
            "atlas_relationship_search_enabled": False,
            "atlas_global_search": "sony",
            "atlas_global_search_index": 0,
            "atlas_layout_mode": "Desktop",
            "atlas_navigation_collapsed": False,
            "atlas_notebook_entries": [],
            "atlas_review_flags": {},
            "atlas_recently_viewed_objects": [],
            "atlas_pinned_objects": [{"object_id": "EQ-1", "object_type": "Equipment"}],
            "atlas_recent_search_queries": ["sony"],
            "atlas_recent_opened_results": [
                {"object_id": "EQ-1", "object_type": "Equipment"}
            ],
        }
    )

    snapshot = app._workspace_state_snapshot(st)

    assert snapshot["pinned_objects"][0]["object_id"] == "EQ-1"
    assert snapshot["recent_search_queries"] == ["sony"]
    assert snapshot["recent_opened_results"][0]["object_id"] == "EQ-1"


def test_breadcrumb_generates_object_specific_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _project_record("maw-demo", "MAW")
    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        SimpleNamespace(
            session_state={
                "atlas_context_selection": {
                    "kind": "drawing",
                    "data": {"drawing_number": "AV-601", "title": "Audio Plan"},
                }
            }
        ),
    )

    breadcrumb = app._breadcrumb(record, "Drawings")

    assert breadcrumb == "Atlas / Projects / MAW / Drawings / AV-601"


def test_filter_returns_empty_for_non_matching_query() -> None:
    filtered = app._filter_search_results(
        [
            _reference(
                object_id="EQ-100",
                display_name="Sony FW-65BZ40L",
                object_type="Equipment",
                scope="project",
            )
        ],
        query="no-match-term",
        selected_types=[],
        project_open=True,
    )

    assert filtered == []


def test_open_project_result_activates_workspace() -> None:
    record = _project_record("maw-demo", "MAW")
    st = _FakeStreamlit(session_state={})
    service = _FakeWorkspaceService(records=[record])
    reference = {
        "selection_kind": "project_record",
        "selection_data": {"workspace_id": "maw-demo"},
        "object_id": "maw-demo",
        "object_type": "Project",
    }

    app._open_search_reference(st, service, reference)

    assert st.session_state["atlas_active_workspace_id"] == "maw-demo"
    assert st.session_state["atlas_active_page"] == "Overview"

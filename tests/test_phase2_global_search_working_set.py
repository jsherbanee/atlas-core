from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any, Literal

from atlas_core.domain import Project, ProjectStatus
from atlas_core.services.project_workspace_service import (
    ProjectWorkspaceRecord,
    ProjectWorkspaceService,
)
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

    def preview_next_bid_id(self) -> str:
        return "BID-2099-0001"


class _NullContext:
    def __enter__(self) -> _NullContext:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
        _ = (exc_type, exc, tb)
        return False


class _CreatePageStreamlit:
    def __init__(
        self,
        *,
        submit: bool,
        project_name: str = "",
        client_name: str = "",
        uploaded_files: list[Any] | None = None,
        button_presses: dict[str, bool] | None = None,
        select_values: dict[str, str] | None = None,
    ) -> None:
        self.submit = submit
        self.project_name = project_name
        self.client_name = client_name
        self.uploaded_files = list(uploaded_files or [])
        self.button_presses = dict(button_presses or {})
        self.select_values = dict(select_values or {})
        self.session_state: dict[str, Any] = {}
        self.select_options: dict[str, list[str]] = {}
        self.infos: list[str] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.successes: list[str] = []
        self.captions: list[str] = []
        self.rerun_called = False

    def subheader(self, _text: str) -> None:
        return None

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def info(self, text: str) -> None:
        self.infos.append(text)

    def error(self, text: str) -> None:
        self.errors.append(text)

    def warning(self, text: str) -> None:
        self.warnings.append(text)

    def success(self, text: str) -> None:
        self.successes.append(text)

    def markdown(self, _text: str) -> None:
        return None

    def button(
        self,
        label: str,
        disabled: bool = False,
        use_container_width: bool = False,
    ) -> bool:
        _ = (disabled, use_container_width)
        return bool(self.button_presses.get(label, False))

    def form(self, _key: str, clear_on_submit: bool = False) -> _NullContext:
        _ = clear_on_submit
        return _NullContext()

    def text_input(self, label: str, key: str | None = None, **kwargs: Any) -> str:
        _ = (key, kwargs)
        if label == "Project Name":
            return self.project_name
        if label == "Owner / Client":
            return self.client_name
        if label == "Owner / Client stakeholder lookup":
            return self.client_name
        return ""

    def selectbox(
        self,
        _label: str,
        options: list[str],
        index: int = 0,
        **kwargs: Any,
    ) -> str:
        _ = kwargs
        self.select_options[_label] = list(options)
        selected_value = self.select_values.get(_label)
        if selected_value in options:
            return str(selected_value)
        return str(options[index])

    def file_uploader(self, *args: Any, **kwargs: Any) -> list[Any]:
        _ = (args, kwargs)
        return list(self.uploaded_files)

    def multiselect(self, *args: Any, **kwargs: Any) -> list[str]:
        _ = (args, kwargs)
        return []

    def expander(self, _label: str, expanded: bool = False) -> _NullContext:
        _ = expanded
        return _NullContext()

    def form_submit_button(
        self,
        _label: str,
        type: str = "secondary",
        disabled: bool = False,
    ) -> bool:
        _ = type
        if disabled:
            return False
        return self.submit

    def columns(self, count: int) -> list[_CreatePageStreamlit]:
        return [self for _ in range(count)]

    def metric(self, _label: str, _value: str) -> None:
        return None

    def dataframe(self, *args: Any, **kwargs: Any) -> None:
        _ = (args, kwargs)
        return None

    def rerun(self) -> None:
        self.rerun_called = True


class _CreatePageWorkspaceServiceWithoutPreview:
    def __init__(self) -> None:
        self.created: list[ProjectWorkspaceRecord] = []
        self.logged_events: list[tuple[str, str, dict[str, Any]]] = []
        self.import_calls: list[tuple[str, list[tuple[str, bytes]]]] = []
        self.inspect_calls = 0
        self.search_queries: list[str] = []
        self.link_calls: list[dict[str, Any]] = []

    def inspect_uploaded_documents(
        self,
        uploaded_files: list[tuple[str, bytes]],
    ) -> Any:
        self.inspect_calls += 1
        accepted_files = []
        diagnostics = []
        warnings: list[str] = []
        seen_names: set[str] = set()
        for name, data in uploaded_files:
            extension = Path(name).suffix.lower()
            duplicate = name.lower() in seen_names
            accepted = (
                extension in {".pdf", ".jpg", ".jpeg", ".xls", ".xlsx", ".doc", ".docx"}
                and len(data) > 0
                and not duplicate
            )
            if accepted:
                messages = ["accepted"]
            elif len(data) == 0:
                messages = ["empty file"]
            elif extension == ".zip":
                messages = ["unsupported extension"]
                warnings.append("could not unpack ZIP archive")
            else:
                messages = ["invalid"]
            diagnostics.append(
                {
                    "name": name,
                    "source_type": "file",
                    "size_bytes": len(data),
                    "zip_source": extension == ".zip",
                    "duplicate_name": duplicate,
                    "duplicate_source_hash": False,
                    "accepted": accepted,
                    "messages": messages,
                }
            )
            if accepted:
                accepted_files.append(SimpleNamespace(name=name, data=data))
            seen_names.add(name.lower())

        return SimpleNamespace(
            accepted_files=accepted_files,
            diagnostics=diagnostics,
            warnings=warnings,
        )

    def create_manual_record(self, **kwargs: Any) -> ProjectWorkspaceRecord:
        name = str(kwargs.get("name") or "")
        client = str(kwargs.get("client") or "")
        record = ProjectWorkspaceRecord(
            workspace_id="BID-2099-0001",
            project=Project(
                project_id="BID-2099-0001",
                name=name,
                client=client,
                status=ProjectStatus.INTAKE,
            ),
        )
        self.created.append(record)
        return record

    def save_record(self, _record: ProjectWorkspaceRecord) -> Path:
        return Path("workspace.json")

    def import_uploaded_documents(
        self,
        workspace_id: str,
        uploaded_files: list[tuple[str, bytes]],
    ) -> ProjectWorkspaceRecord:
        self.import_calls.append((workspace_id, list(uploaded_files)))
        return self.created[-1]

    def log_event(
        self,
        workspace_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        self.logged_events.append((workspace_id, event_type, dict(payload)))

    def search_stakeholder_organizations(
        self,
        query: str,
        *,
        role: Any = None,
        include_inactive: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        _ = (role, include_inactive, limit)
        self.search_queries.append(query)
        if not query.strip():
            return []
        return [
            {
                "organization_id": "org-lookup-owner",
                "canonical_name": "Lookup Owner LLC",
                "display_name": "Lookup Owner LLC",
            }
        ]

    def link_project_stakeholder(
        self,
        *,
        workspace_id: str,
        organization_id: str,
        role: Any,
        is_primary: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "workspace_id": workspace_id,
            "organization_id": organization_id,
            "role": role,
            "is_primary": is_primary,
        }
        self.link_calls.append(payload)
        return payload


class _CreatePageWorkspaceServiceWithPreview(_CreatePageWorkspaceServiceWithoutPreview):
    def preview_next_bid_id(self) -> str:
        return "BID-2099-0009"


class _CreatePageWorkspaceServiceInspectionFailure(
    _CreatePageWorkspaceServiceWithoutPreview
):
    def inspect_uploaded_documents(
        self,
        uploaded_files: list[tuple[str, bytes]],
    ) -> Any:
        _ = uploaded_files
        raise AttributeError("inspect_uploaded_files missing")


@dataclass
class _FakeUploadedFile:
    name: str
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)

    def getvalue(self) -> bytes:
        return self.data


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


def test_project_record_identifier_and_secondary_labels() -> None:
    reference = app._build_object_reference(
        kind="project_record",
        data={
            "workspace_id": "legacy-workspace-id",
            "atlas_bid_id": "BID-2026-0012",
            "project_name": "Campus AV Refresh",
            "customer": "City Schools",
            "client_project_number": "CS-4421",
            "internal_project_number": "INT-0902",
            "status": "In Progress",
        },
        project_id="legacy-workspace-id",
        route="Overview",
    )

    assert reference["object_id"] == "BID-2026-0012"
    assert reference["secondary_label"] == (
        "City Schools | Client #CS-4421 | Internal #INT-0902"
    )


def test_project_identifier_match_fields_rank_for_client_and_internal_numbers() -> None:
    reference = {
        "object_id": "BID-2026-0012",
        "display_name": "Campus AV Refresh",
        "object_type": "Project",
        "secondary_label": "City Schools | Client #CS-4421 | Internal #INT-0902",
        "scope": "application",
        "match_fields": [
            "BID-2026-0012",
            "legacy-workspace-id",
            "Campus AV Refresh",
            "City Schools",
            "CS-4421",
            "INT-0902",
        ],
        "selection_kind": "project_record",
        "selection_data": {},
    }

    client_filtered = app._filter_search_results(
        [reference],
        query="CS-4421",
        selected_types=[],
        project_open=False,
    )
    internal_filtered = app._filter_search_results(
        [reference],
        query="INT-0902",
        selected_types=[],
        project_open=False,
    )

    assert len(client_filtered) == 1
    assert len(internal_filtered) == 1


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


def test_project_context_header_builder_returns_expected_fields() -> None:
    record = _project_record("maw-demo", "MAW")

    header = app._build_project_context_header(
        record,
        customer="Music Academy of the West",
        confidence="84%",
        recommended_next_action="Review Documents",
    )

    assert header.project_name == "MAW"
    assert header.customer == "Music Academy of the West"
    assert header.confidence == "84%"
    assert header.recommended_next_action == "Review Documents"


def test_project_navigation_contains_disabled_future_lifecycle_group() -> None:
    group_names = [name for name, _ in app.PROJECT_NAV_GROUPS]

    assert "Future Lifecycle (Disabled)" in group_names
    assert set(app.DISABLED_LIFECYCLE_PAGES) <= {
        page for _, entries in app.PROJECT_NAV_GROUPS for _, page in entries
    }


def test_build_workspace_service_runtime_path_exposes_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_root = tmp_path / "AtlasProjects"
    monkeypatch.setattr(app, "ensure_runtime_workspace_root", lambda: runtime_root)

    service = app._build_workspace_service()

    assert isinstance(service, ProjectWorkspaceService)
    assert callable(getattr(service, "preview_next_bid_id", None))
    assert callable(getattr(service.manager, "preview_next_bid_id", None))
    assert callable(
        getattr(service.manager.project_repository, "peek_next_bid_id", None)
    )


def test_create_project_primary_action_label_changes_with_selection() -> None:
    assert app._create_project_primary_action_label(False) == "Create Bid Workspace"
    assert app._create_project_primary_action_label(True) == "Create Bid Workspace"


def test_create_project_required_fields_only_name_and_client() -> None:
    assert app._create_project_missing_required_fields("", "") == [
        "Project Name",
        "Owner / Client",
    ]
    assert app._create_project_missing_required_fields("Project", "") == [
        "Owner / Client"
    ]
    assert app._create_project_missing_required_fields("Project", "Client") == []


def test_create_project_post_create_route_depends_on_upload_selection() -> None:
    assert app._create_project_post_create_page(False) == "Documents"
    assert app._create_project_post_create_page(True) == "Documents"


def test_create_project_effective_uploads_supports_individual_removal() -> None:
    uploads = [
        _FakeUploadedFile(name="a.pdf", data=b"a"),
        _FakeUploadedFile(name="b.pdf", data=b"b"),
        _FakeUploadedFile(name="c.pdf", data=b"c"),
    ]

    kept = app._create_project_effective_uploads(uploads, ["2. b.pdf"])
    kept_names = [item.name for item in kept]
    assert kept_names == ["a.pdf", "c.pdf"]


def test_create_project_clear_upload_state_resets_session_keys() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_create_project_uploads": ["x"],
            "atlas_create_project_remove_selection": ["1. x"],
            "atlas_create_project_uploads_token": 1,
        }
    )

    app._reset_create_project_upload_state(st)
    assert st.session_state["atlas_create_project_uploads"] == ["x"]
    assert st.session_state["atlas_create_project_uploads_token"] == 2
    assert "atlas_create_project_remove_selection" not in st.session_state


def test_create_project_upload_inspection_rows_include_required_columns() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [
        _FakeUploadedFile(name="bid.pdf", data=b"pdf-bytes"),
        _FakeUploadedFile(name="bad.exe", data=b"x"),
    ]

    inspected = app._create_project_upload_inspection(service, uploads)

    assert inspected["total_selected_count"] == 2
    assert inspected["total_selected_size"] > 0
    assert inspected["accepted_count"] >= 1
    assert inspected["rejected_count"] >= 1
    assert inspected["has_any_selected_invalid"] is True
    assert inspected["all_selected_invalid"] is False
    assert inspected["accepted_payload"]
    assert inspected["rows"]

    row = inspected["rows"][0]
    assert set(
        [
            "Name",
            "Source Type",
            "File Size",
            "ZIP Source",
            "Duplicate",
            "Validation",
            "Messages",
        ]
    ) <= set(row.keys())


def test_create_project_upload_inspection_keeps_invalid_diagnostics_visible() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [
        _FakeUploadedFile(name="empty.pdf", data=b""),
        _FakeUploadedFile(name="ok.jpg", data=b"img"),
    ]

    inspected = app._create_project_upload_inspection(service, uploads)

    rejected_rows = [
        row for row in inspected["rows"] if row.get("Validation") == "rejected"
    ]
    accepted_rows = [
        row for row in inspected["rows"] if row.get("Validation") == "accepted"
    ]
    assert rejected_rows
    assert accepted_rows
    assert any("empty file" in str(row.get("Messages", "")) for row in rejected_rows)


def test_create_project_upload_inspection_all_invalid_selection_is_blockable() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [_FakeUploadedFile(name="bad.exe", data=b"x")]
    inspected = app._create_project_upload_inspection(service, uploads)

    assert inspected["has_selected_files"] is True
    assert inspected["all_selected_invalid"] is True
    assert inspected["accepted_count"] == 0


def test_create_project_upload_inspection_zip_warnings_have_zip_indicator() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [_FakeUploadedFile(name="bad.zip", data=b"not-a-real-zip")]
    inspected = app._create_project_upload_inspection(service, uploads)

    warning_rows = [
        row for row in inspected["rows"] if row.get("Validation") == "warning"
    ]
    assert warning_rows
    assert all(row.get("ZIP Source") == "Yes" for row in warning_rows)


def test_create_project_upload_inspection_marks_duplicate_state() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [
        _FakeUploadedFile(name="dup.pdf", data=b"same"),
        _FakeUploadedFile(name="dup.pdf", data=b"same2"),
    ]
    inspected = app._create_project_upload_inspection(service, uploads)

    assert any(row.get("Duplicate") == "Yes" for row in inspected["rows"])


def test_preview_next_bid_id_helper_returns_value_when_supported() -> None:
    service = _CreatePageWorkspaceServiceWithPreview()

    assert app._preview_next_bid_id(service) == "BID-2099-0009"


def test_preview_next_bid_id_helper_returns_none_when_unsupported() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()

    assert app._preview_next_bid_id(service) is None


def test_create_project_page_renders_when_preview_unavailable() -> None:
    st = _CreatePageStreamlit(submit=False)
    service = _CreatePageWorkspaceServiceWithoutPreview()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert not st.errors
    assert any(
        "assigned when the workspace is created" in message for message in st.infos
    )


def test_create_project_page_owner_lookup_populates_existing_options() -> None:
    st = _CreatePageStreamlit(
        submit=False,
        client_name="Lookup Owner",
    )
    service = _CreatePageWorkspaceServiceWithoutPreview()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.search_queries == ["Lookup Owner"]
    options = st.select_options.get("Select existing Owner / Client") or []
    assert "Lookup Owner LLC · org-lookup-owner" in options


def test_create_project_page_creation_still_works_without_preview() -> None:
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Create Without Preview",
        client_name="Client",
    )
    service = _CreatePageWorkspaceServiceWithoutPreview()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    assert st.session_state["atlas_active_workspace_id"] == "BID-2099-0001"
    assert "atlas_header_project_selector" not in st.session_state
    assert st.session_state["atlas_active_page"] == "Documents"
    assert st.rerun_called is True


def test_create_project_page_existing_owner_selection_uses_canonical_owner_and_links() -> (
    None
):
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Create With Existing Owner",
        client_name="Lookup Owner",
        select_values={
            "Select existing Owner / Client": "Lookup Owner LLC · org-lookup-owner"
        },
    )
    service = _CreatePageWorkspaceServiceWithoutPreview()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    created = service.created[-1]
    assert created.project.client == "Lookup Owner LLC"
    assert service.link_calls
    assert service.link_calls[-1]["organization_id"] == "org-lookup-owner"
    assert st.session_state["atlas_active_page"] == "Documents"
    assert st.rerun_called is True


def test_build_record_from_context_preserves_existing_identity_fields() -> None:
    existing = ProjectWorkspaceRecord(
        workspace_id="BID-2026-0005",
        project=Project(
            project_id="BID-2026-0005",
            name="X03 Validation Main",
            client="Northstar Owner Group",
            atlas_bid_id="BID-2026-0005",
            client_project_number="CLIENT-123",
            internal_project_number="INT-789",
            status=ProjectStatus.INTAKE,
        ),
        metadata={
            "project_name": "X03 Validation Main",
            "owner": "Northstar Owner Group",
            "atlas_bid_id": "BID-2026-0005",
            "client_project_number": "CLIENT-123",
            "internal_project_number": "INT-789",
        },
    )
    context = {
        "sample_project_id": "documents",
        "sample_project_name": "documents",
        "intake_snapshot": SimpleNamespace(
            metadata={
                "project_name": "documents",
                "atlas_bid_id": "documents",
                "owner": "documents",
                "client_project_number": "documents",
                "internal_project_number": "documents",
            }
        ),
    }

    rebuilt = app._build_record_from_context(context, existing_record=existing)

    assert rebuilt.project.project_id == "BID-2026-0005"
    assert rebuilt.project.name == "X03 Validation Main"
    assert rebuilt.project.atlas_bid_id == "BID-2026-0005"
    assert rebuilt.project.client_project_number == "CLIENT-123"
    assert rebuilt.project.internal_project_number == "INT-789"
    assert rebuilt.metadata["project_name"] == "X03 Validation Main"
    assert rebuilt.metadata["owner"] == "Northstar Owner Group"
    assert rebuilt.metadata["owner_client"] == "Northstar Owner Group"
    assert rebuilt.metadata["atlas_bid_id"] == "BID-2026-0005"


def test_create_project_upload_inspection_helper_uses_service_public_api() -> None:
    service = _CreatePageWorkspaceServiceWithoutPreview()
    uploads = [_FakeUploadedFile(name="bid.pdf", data=b"pdf")]

    _ = app._create_project_upload_inspection(service, uploads)

    assert service.inspect_calls == 1


def test_create_project_page_graceful_when_inspection_unavailable() -> None:
    st = _CreatePageStreamlit(
        submit=False,
        uploaded_files=[_FakeUploadedFile(name="bid.pdf", data=b"pdf")],
    )
    service = _CreatePageWorkspaceServiceInspectionFailure()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert not st.errors
    assert not st.warnings


def test_create_project_page_create_and_upload_with_valid_file() -> None:
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Create With File",
        client_name="Client",
        uploaded_files=[_FakeUploadedFile(name="bid.pdf", data=b"pdf")],
    )
    service = _CreatePageWorkspaceServiceWithPreview()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    assert not service.import_calls
    assert st.session_state["atlas_active_page"] == "Documents"
    assert st.rerun_called is True


def test_create_project_page_inspection_failure_with_files_blocks_submission() -> None:
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Blocked",
        client_name="Client",
        uploaded_files=[_FakeUploadedFile(name="bid.pdf", data=b"pdf")],
    )
    service = _CreatePageWorkspaceServiceInspectionFailure()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    assert st.session_state["atlas_active_page"] == "Documents"


def test_create_project_page_clear_files_allows_project_only_create() -> None:
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Project Only",
        client_name="Client",
        uploaded_files=[_FakeUploadedFile(name="bid.pdf", data=b"pdf")],
        button_presses={"Clear File Selection": True},
    )
    service = _CreatePageWorkspaceServiceInspectionFailure()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    assert st.session_state["atlas_active_page"] == "Documents"


def test_create_project_page_project_only_create_succeeds_without_files() -> None:
    st = _CreatePageStreamlit(
        submit=True,
        project_name="Project Only",
        client_name="Client",
        uploaded_files=[],
    )
    service = _CreatePageWorkspaceServiceInspectionFailure()

    app._render_create_project_page(st, service)  # type: ignore[arg-type]

    assert service.created
    assert not service.import_calls
    assert st.session_state["atlas_active_page"] == "Documents"


def test_documents_pending_uploads_append_across_selections() -> None:
    st = _FakeStreamlit(session_state={})
    first = [_FakeUploadedFile(name="a.pdf", data=b"a")]
    second = [_FakeUploadedFile(name="b.csv", data=b"b")]

    first_added, _ = app._append_pending_upload_selection(st, "BID-1", first)
    second_added, _ = app._append_pending_upload_selection(st, "BID-1", second)
    pending = app._pending_upload_state(st, "BID-1")

    assert first_added == 1
    assert second_added == 1
    assert [item["name"] for item in pending] == ["a.pdf", "b.csv"]


def test_documents_pending_uploads_deduplicate_same_identity() -> None:
    st = _FakeStreamlit(session_state={})
    selection = [_FakeUploadedFile(name="a.pdf", data=b"same")]

    app._append_pending_upload_selection(st, "BID-1", selection)
    # Simulate a new event signature with identical file data.
    st.session_state["atlas_documents_pending_selection_signature"] = {}
    added, duplicates = app._append_pending_upload_selection(st, "BID-1", selection)

    pending = app._pending_upload_state(st, "BID-1")
    assert added == 0
    assert duplicates == 1
    assert len(pending) == 1


def test_documents_pending_uploads_remove_and_clear() -> None:
    st = _FakeStreamlit(session_state={})
    app._append_pending_upload_selection(
        st,
        "BID-1",
        [
            _FakeUploadedFile(name="a.pdf", data=b"a"),
            _FakeUploadedFile(name="b.pdf", data=b"b"),
        ],
    )
    pending = app._pending_upload_state(st, "BID-1")
    removed = app._remove_pending_uploads(
        st,
        "BID-1",
        [str(pending[0]["identity_key"])],
    )
    assert removed == 1
    assert len(app._pending_upload_state(st, "BID-1")) == 1

    app._clear_pending_uploads(st, "BID-1")
    assert app._pending_upload_state(st, "BID-1") == []


def test_pending_identity_keys_to_remove_after_upload_keeps_rejected_pending() -> None:
    pending = [
        {
            "identity_key": app._pending_upload_identity("good.pdf", b"good"),
            "name": "good.pdf",
            "data": b"good",
            "size": 4,
        },
        {
            "identity_key": app._pending_upload_identity("bad.exe", b"bad"),
            "name": "bad.exe",
            "data": b"bad",
            "size": 3,
        },
    ]
    inspection = SimpleNamespace(
        accepted_files=[SimpleNamespace(name="good.pdf", data=b"good")],
        diagnostics=[
            {"name": "good.pdf", "accepted": True, "zip_source": False},
            {
                "name": "bad.exe",
                "accepted": False,
                "zip_source": False,
                "messages": ["unsupported extension"],
            },
        ],
    )

    removable = app._pending_identity_keys_to_remove_after_upload(pending, inspection)

    assert removable == {pending[0]["identity_key"]}


def test_pending_identity_keys_to_remove_after_upload_handles_zip_partitions() -> None:
    zip_pending = {
        "identity_key": app._pending_upload_identity("bundle.zip", b"zip-data"),
        "name": "bundle.zip",
        "data": b"zip-data",
        "size": 8,
    }

    all_accepted = SimpleNamespace(
        accepted_files=[],
        diagnostics=[
            {
                "name": "bundle.zip/nested/one.pdf",
                "accepted": True,
                "zip_source": True,
            },
            {
                "name": "bundle.zip/nested/two.csv",
                "accepted": True,
                "zip_source": True,
            },
        ],
    )
    mixed = SimpleNamespace(
        accepted_files=[],
        diagnostics=[
            {
                "name": "bundle.zip/nested/one.pdf",
                "accepted": True,
                "zip_source": True,
            },
            {
                "name": "bundle.zip/nested/two.exe",
                "accepted": False,
                "zip_source": True,
            },
        ],
    )

    removable_all = app._pending_identity_keys_to_remove_after_upload(
        [zip_pending],
        all_accepted,
    )
    removable_mixed = app._pending_identity_keys_to_remove_after_upload(
        [zip_pending],
        mixed,
    )

    assert removable_all == {zip_pending["identity_key"]}
    assert removable_mixed == set()


def test_documents_upload_picker_reset_increments_token_and_clears_signature() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_documents_upload_picker_tokens": {"BID-1": 2, "BID-2": 1},
            "atlas_documents_pending_selection_signature": {
                "BID-1": "abc",
                "BID-2": "xyz",
            },
        }
    )

    app._reset_documents_upload_picker(st, "BID-1")

    assert st.session_state["atlas_documents_upload_picker_tokens"]["BID-1"] == 3
    assert st.session_state["atlas_documents_upload_picker_tokens"]["BID-2"] == 1
    assert (
        "BID-1" not in st.session_state["atlas_documents_pending_selection_signature"]
    )
    assert (
        st.session_state["atlas_documents_pending_selection_signature"]["BID-2"]
        == "xyz"
    )

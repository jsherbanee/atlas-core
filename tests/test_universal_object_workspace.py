from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any, Literal

from atlas_core.domain import Project, ProjectStatus
from atlas_core.domain.av_lifecycle import build_default_lifecycle_plan
from atlas_core.services.project_workspace_service import ProjectWorkspaceRecord

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_universal_workspace_tests", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


class _FakeWorkspaceService:
    def __init__(self, records: list[ProjectWorkspaceRecord]) -> None:
        self._records = records
        self.restored_entry: dict[str, Any] | None = None

    def list_workspaces(
        self,
        include_archived: bool = True,
        limit: int = 1000,
    ) -> list[ProjectWorkspaceRecord]:
        _ = include_archived
        return list(self._records)[:limit]

    def list_history(self, workspace_id: str, limit: int = 100) -> list[dict[str, Any]]:
        _ = limit
        return [
            {
                "event_type": "project_created",
                "timestamp": "2026-07-13T00:00:00+00:00",
                "actor": "system",
                "workspace_id": workspace_id,
            }
        ]

    def archive_project(
        self,
        workspace_id: str,
        archived: bool = True,
    ) -> ProjectWorkspaceRecord:
        _ = archived
        for record in self._records:
            if record.workspace_id == workspace_id:
                return record
        raise ValueError("workspace not found")

    def lifecycle_plan_for_record(self, record: ProjectWorkspaceRecord) -> Any:
        return build_default_lifecycle_plan(
            project_id=record.workspace_id,
            tenant_id="local",
            current_stage_key="project_management",
        )

    def available_project_lifecycle_transitions(
        self, workspace_id: str
    ) -> list[dict[str, Any]]:
        _ = workspace_id
        return [
            {
                "to_stage_key": "field_installation",
                "label": "Advance to Field Installation",
            }
        ]


class _FakeSt:
    def __init__(self, *, session_state: dict[str, Any] | None = None) -> None:
        self.session_state = dict(session_state or {})
        self.dataframes: list[Any] = []
        self.captions: list[str] = []
        self.markdowns: list[str] = []
        self.info_messages: list[str] = []
        self.success_messages: list[str] = []
        self.error_messages: list[str] = []
        self.button_calls: list[dict[str, Any]] = []
        self.radio_calls: list[dict[str, Any]] = []
        self.download_calls: list[dict[str, Any]] = []
        self.rerun_called = False

    def subheader(self, _text: str) -> None:
        return None

    def markdown(self, text: str, **kwargs: Any) -> None:
        _ = kwargs
        self.markdowns.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def info(self, text: str) -> None:
        self.info_messages.append(text)

    def success(self, text: str) -> None:
        self.success_messages.append(text)

    def error(self, text: str) -> None:
        self.error_messages.append(text)

    def dataframe(self, data: Any, **kwargs: Any) -> None:
        _ = kwargs
        self.dataframes.append(data)

    def columns(self, count: int | list[Any]) -> list[_FakeSt]:
        size = len(count) if isinstance(count, list) else int(count)
        return [self for _ in range(size)]

    def selectbox(
        self,
        _label: str,
        options: list[Any],
        index: int = 0,
        key: str | None = None,
        format_func: Any | None = None,
    ) -> Any:
        _ = format_func
        if key and key in self.session_state and self.session_state[key] in options:
            return self.session_state[key]
        return options[index]

    def expander(self, _label: str, expanded: bool = False) -> "_FakeSt":
        _ = expanded
        return self

    def __enter__(self) -> "_FakeSt":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
        _ = exc_type
        _ = exc
        _ = tb
        return False

    def button(
        self,
        label: str,
        key: str | None = None,
        width: str | None = None,
        type: str = "secondary",
        disabled: bool = False,
    ) -> bool:
        self.button_calls.append(
            {
                "label": label,
                "key": key,
                "width": width,
                "type": type,
                "disabled": disabled,
            }
        )
        return False

    def radio(
        self,
        label: str,
        options: list[str],
        horizontal: bool = False,
        key: str | None = None,
        index: int = 0,
    ) -> str:
        self.radio_calls.append(
            {
                "label": label,
                "options": list(options),
                "horizontal": horizontal,
                "key": key,
                "index": index,
            }
        )
        return options[index]

    def download_button(
        self,
        label: str,
        data: str,
        file_name: str,
        mime: str,
        width: str | None = None,
    ) -> bool:
        self.download_calls.append(
            {
                "label": label,
                "file_name": file_name,
                "mime": mime,
                "width": width,
                "data": data,
            }
        )
        return False

    def rerun(self) -> None:
        self.rerun_called = True


def _record() -> ProjectWorkspaceRecord:
    lifecycle_plan = build_default_lifecycle_plan(
        project_id="maw-demo",
        tenant_id="local",
        current_stage_key="project_management",
    )
    return ProjectWorkspaceRecord(
        workspace_id="maw-demo",
        project=Project(
            project_id="maw-demo",
            name="MAW",
            client="MAW",
            status=ProjectStatus.INTAKE,
        ),
        metadata={
            "status": "active",
            "lifecycle_stage": "project_management",
            "lifecycle_plan": lifecycle_plan.to_dict(),
        },
    )


def test_selection_route_uses_object_workspace_for_supported_kinds() -> None:
    assert app._selection_route("customer") == "Object Workspace"
    assert app._selection_route("vendor") == "Object Workspace"
    assert app._selection_route("project") == "Object Workspace"


def test_selection_route_keeps_legacy_route_for_unsupported_kind() -> None:
    assert app._selection_route("notebook_entry") == "Notebook"


def test_open_search_reference_routes_supported_kind_to_object_workspace() -> None:
    st = _FakeSt(
        session_state={
            "atlas_active_page": "Knowledge",
            "atlas_tenant_scope": "local",
            "atlas_context_selection": {},
            "atlas_active_workspace_id": "",
            "atlas_active_project_name": "",
            "atlas_navigation_history": [],
        }
    )
    workspace_service = _FakeWorkspaceService([])
    reference = {
        "route": "Knowledge",
        "selection_kind": "vendor",
        "selection_data": {"vendor": "ADI", "vendor_id": "vendor-adi"},
        "display_name": "ADI",
        "object_type": "Vendor",
        "object_id": "vendor-adi",
    }

    app._open_search_reference(st, workspace_service, reference)

    assert st.session_state["atlas_active_page"] == "Object Workspace"
    assert st.session_state["atlas_context_selection"]["kind"] == "vendor"
    assert st.session_state["atlas_object_workspace_view"] == "Summary"
    assert st.rerun_called is True


def test_open_search_reference_keeps_legacy_route_for_unsupported_kind() -> None:
    st = _FakeSt(
        session_state={
            "atlas_active_page": "Knowledge",
            "atlas_tenant_scope": "local",
            "atlas_context_selection": {},
            "atlas_navigation_history": [],
        }
    )
    workspace_service = _FakeWorkspaceService([])
    reference = {
        "route": "Notebook",
        "selection_kind": "notebook_entry",
        "selection_data": {"entry_id": "note-1", "title": "Note"},
        "display_name": "Note",
        "object_type": "Notebook Entry",
        "object_id": "note-1",
    }

    app._open_search_reference(st, workspace_service, reference)

    assert st.session_state["atlas_active_page"] == "Notebook"


def test_object_workspace_supported_views_for_migrated_kind() -> None:
    obj = app._universal_object_registry().adapt(
        "vendor",
        {"vendor": "ADI", "vendor_id": "vendor-adi"},
        tenant_id="local",
        owning_workspace="Knowledge",
    )

    views = app._object_workspace_supported_views(obj, kind="vendor")

    assert "Summary" in views
    assert "Details" in views
    assert "Relationships" in views


def test_object_workspace_supported_views_for_read_only_engineering_kind() -> None:
    obj = app._universal_object_registry().adapt(
        "drawing",
        {"drawing_number": "AV-601", "title": "Plan"},
        tenant_id="local",
        owning_workspace="Projects",
        owning_project_id="maw-demo",
    )

    views = app._object_workspace_supported_views(obj, kind="drawing")

    assert "Documents" not in views
    assert "Summary" in views


def test_universal_relationship_rejects_cross_tenant_mismatch() -> None:
    import pytest
    from atlas_core.contracts.universal_object_contract import (
        UniversalObjectIdentity,
        UniversalObjectRelationship,
    )

    source = UniversalObjectIdentity(
        object_id="vendor-adi",
        object_type="vendor",
        tenant_id="tenant-a",
        owning_workspace="Knowledge",
        canonical_display_name="ADI",
        source_authority="atlas",
    )
    target = UniversalObjectIdentity(
        object_id="project-1",
        object_type="project",
        tenant_id="tenant-b",
        owning_workspace="Projects",
        canonical_display_name="Project 1",
        source_authority="atlas",
    )

    with pytest.raises(ValueError):
        UniversalObjectRelationship(
            relationship_id="rel-1",
            source_identity=source,
            target_identity=target,
            relationship_type="used-in-project",
            direction="outgoing",
            tenant_id="tenant-a",
        )


def test_render_universal_object_workspace_shows_context_banner_when_return_exists() -> (
    None
):
    st = _FakeSt(
        session_state={
            "atlas_context_selection": {
                "kind": "vendor",
                "data": {"vendor": "ADI", "vendor_id": "vendor-adi"},
            },
            "atlas_tenant_scope": "local",
            "atlas_active_workspace_id": "",
            "atlas_return_context": {
                "source_workspace": "Projects",
                "source_route": "BOM Review",
                "source_label": "BOM Review",
                "tenant_scope": "local",
            },
            "atlas_navigation_history": [],
        }
    )
    workspace_service = _FakeWorkspaceService([_record()])

    app._render_universal_object_workspace_page(st, workspace_service, _record(), None)

    assert any("Opened from Projects / BOM Review" in text for text in st.captions)


def test_object_workspace_actions_show_disabled_reason_for_restore_on_active_vendor() -> (
    None
):
    st = _FakeSt(
        session_state={
            "atlas_context_selection": {
                "kind": "vendor",
                "data": {
                    "vendor": "ADI",
                    "vendor_id": "vendor-adi",
                    "active": True,
                    "status": "active",
                },
            },
            "atlas_tenant_scope": "local",
            "atlas_active_workspace_id": "",
            "atlas_navigation_history": [],
            "atlas_return_context": {},
        }
    )
    workspace_service = _FakeWorkspaceService([])

    app._render_universal_object_workspace_page(st, workspace_service, None, None)

    disabled_restore = [
        call
        for call in st.button_calls
        if call["label"] == "Restore" and call["disabled"]
    ]
    assert disabled_restore
    assert any("Object is active" in text for text in st.captions)


def test_object_workspace_project_compatibility_uses_record_context() -> None:
    st = _FakeSt(
        session_state={
            "atlas_context_selection": {
                "kind": "project_record",
                "data": {
                    "workspace_id": "maw-demo",
                    "project_name": "MAW",
                    "status": "intake",
                },
            },
            "atlas_tenant_scope": "local",
            "atlas_active_workspace_id": "maw-demo",
            "atlas_active_project_name": "MAW",
            "atlas_navigation_history": [],
            "atlas_return_context": {},
        }
    )
    record = _record()
    workspace_service = _FakeWorkspaceService([record])

    app._render_universal_object_workspace_page(st, workspace_service, record, None)

    flattened = "\n".join(str(item) for item in st.dataframes)
    assert "MAW" in flattened
    assert "project" in flattened.lower()
    assert "project_management" in flattened.lower()


def test_project_object_workspace_renders_lifecycle_dashboard_view() -> None:
    st = _FakeSt(
        session_state={
            "atlas_context_selection": {
                "kind": "project_record",
                "data": {
                    "workspace_id": "maw-demo",
                    "project_name": "MAW",
                    "status": "active",
                    "lifecycle_stage": "project_management",
                },
            },
            "atlas_tenant_scope": "local",
            "atlas_active_workspace_id": "maw-demo",
            "atlas_active_project_name": "MAW",
            "atlas_navigation_history": [],
            "atlas_return_context": {},
            "atlas_object_workspace_view": "Lifecycle",
        }
    )
    record = _record()
    workspace_service = _FakeWorkspaceService([record])

    app._render_universal_object_workspace_page(st, workspace_service, record, None)

    assert any("Lifecycle Dashboard" in text for text in st.markdowns)
    assert any("atlas-lifecycle-timeline" in text for text in st.markdowns)
    flattened = "\n".join(str(item) for item in st.dataframes)
    assert "Available Transitions" in flattened
    assert "Field Installation" in flattened

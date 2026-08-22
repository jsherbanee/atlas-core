from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_commercial_nav_tests",
    _MODULE_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


class _FakeStreamlit:
    def __init__(self, active_page: str = "Transactions") -> None:
        self.session_state: dict[str, object] = {"atlas_active_page": active_page}


def test_commercial_workspace_is_removed_from_primary_navigation_and_routes() -> None:
    primary_labels = [label for label, _ in app.PRIMARY_HEADER_NAV_ITEMS]
    primary_routes = [route for _, route in app.PRIMARY_HEADER_NAV_ITEMS]
    application_routes = [
        route for _, entries in app.APPLICATION_NAV_GROUPS for _, route in entries
    ]

    assert "Sales" not in primary_labels
    assert "Commercial" not in primary_labels
    assert "Commercial Workspace" not in primary_routes
    assert "Commercial Workspace" not in application_routes
    assert "Commercial Workspace" not in app.ALL_ACTIVE_PAGES
    assert not hasattr(app, "_render_commercial_workspace_page")


@pytest.mark.parametrize(
    ("active_page", "expected_label"),
    [
        ("Mission Control", "Atlas"),
        ("Transactions", "Transactions"),
        ("Projects", "Projects"),
        ("Knowledge", "Knowledge"),
        ("Reports", "Reports"),
        ("Administration", "Settings"),
    ],
)
def test_primary_navigation_has_exactly_one_active_item(
    active_page: str,
    expected_label: str,
) -> None:
    labels = ["Atlas", *(label for label, _ in app.PRIMARY_HEADER_NAV_ITEMS)]
    active_labels = [
        label
        for label in labels
        if app._primary_navigation_is_active(
            label,
            active_page=active_page,
            record=SimpleNamespace(),
        )
    ]

    assert active_labels == [expected_label]


@pytest.mark.parametrize(
    "active_page",
    [
        "Mission Control",
        "Transactions",
        "Knowledge",
        "Reports",
        "Administration",
    ],
)
def test_non_projects_shell_drops_stale_project_context(
    monkeypatch: pytest.MonkeyPatch,
    active_page: str,
) -> None:
    fake_st = _FakeStreamlit(active_page)
    stale_record = SimpleNamespace(workspace_id="project-1")
    stale_context = {"project": "context"}
    records_seen: list[object | None] = []
    contexts_seen: list[object | None] = []

    def record_project_context(
        _st: object,
        _service: object,
        record: object | None,
        context: object | None,
    ) -> None:
        records_seen.append(record)
        contexts_seen.append(context)

    def record_status_context(
        _st: object,
        record: object | None,
        context: object | None,
    ) -> None:
        records_seen.append(record)
        contexts_seen.append(context)

    monkeypatch.setattr(
        app,
        "_render_header",
        record_project_context,
    )
    monkeypatch.setattr(app, "_sync_notebook_state_to_context", lambda *_args: None)
    monkeypatch.setattr(app, "_active_global_search_query", lambda _st: "")
    monkeypatch.setattr(app, "_should_render_shell_breadcrumb", lambda *_args: False)
    monkeypatch.setattr(app, "_collect_workspace_signals", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(app, "_render_return_context_action", lambda *_args: None)
    monkeypatch.setattr(app, "_sync_workspace_navigation_state", lambda *_args: None)
    monkeypatch.setattr(
        app,
        "_render_workspace_navigation",
        lambda _st, record, content_renderer=None: records_seen.append(record),
    )
    monkeypatch.setattr(
        app,
        "_render_status_bar",
        record_status_context,
    )

    app._render_shell(
        fake_st,
        SimpleNamespace(),
        stale_record,
        stale_context,
    )

    assert records_seen and all(record is None for record in records_seen)
    assert contexts_seen and all(context is None for context in contexts_seen)

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
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {
            "atlas_active_page": "Commercial Workspace"
        }


def test_commercial_workspace_is_registered_as_an_active_page() -> None:
    assert "Commercial Workspace" in app.ALL_ACTIVE_PAGES
    assert app._active_primary_workspace("Commercial Workspace", None) == "Sales"
    assert app._active_workspace_mode("Commercial Workspace", None) == "application"


def test_commercial_workspace_top_navigation_is_primary_active() -> None:
    assert app._primary_navigation_is_active(
        "Sales",
        active_page="Commercial Workspace",
        record=None,
    )


@pytest.mark.parametrize(
    ("active_page", "expected_label"),
    [
        ("Mission Control", "Atlas"),
        ("Transactions", "Transactions"),
        ("Commercial Workspace", "Sales"),
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


def test_main_content_dispatches_commercial_workspace_page(monkeypatch) -> None:
    rendered: list[str] = []

    monkeypatch.setattr(app, "_render_project_action_feedback", lambda _st: None)
    monkeypatch.setattr(
        app,
        "_render_commercial_workspace_page",
        lambda _st, _service: rendered.append("commercial"),
    )

    fake_st = _FakeStreamlit()
    app._render_main_content(fake_st, SimpleNamespace(), None, None)

    assert rendered == ["commercial"]


@pytest.mark.parametrize(
    ("active_page", "renderer_name"),
    [
        ("Mission Control", "_render_home_page"),
        ("Projects", "_render_projects_page"),
        ("Knowledge", "_render_application_knowledge_page"),
        ("Reports", "_render_application_reports_page"),
        ("Administration", "_render_application_administration_page"),
        ("Transactions", "_render_transactions_workspace_page"),
    ],
)
def test_non_commercial_pages_do_not_render_commercial_workspace(
    monkeypatch,
    active_page: str,
    renderer_name: str,
) -> None:
    rendered: list[str] = []
    fake_st = _FakeStreamlit()
    fake_st.session_state["atlas_active_page"] = active_page

    monkeypatch.setattr(app, "_render_project_action_feedback", lambda _st: None)
    monkeypatch.setattr(
        app,
        "_render_commercial_workspace_page",
        lambda _st, _service: rendered.append("commercial"),
    )
    monkeypatch.setattr(app, renderer_name, lambda *_args, **_kwargs: None)

    app._render_main_content(fake_st, SimpleNamespace(), None, None)

    assert rendered == []

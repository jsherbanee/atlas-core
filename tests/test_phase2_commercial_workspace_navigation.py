from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

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
    assert app._active_primary_workspace("Commercial Workspace", None) == "Commercial"
    assert app._active_workspace_mode("Commercial Workspace", None) == "application"


def test_commercial_workspace_top_navigation_is_primary_active() -> None:
    assert app._primary_navigation_is_active(
        "Commercial",
        active_page="Commercial Workspace",
        record=None,
    )


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

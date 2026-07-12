from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_estimate_nav_test_module", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}
        self.rerun_called = False

    def rerun(self) -> None:
        self.rerun_called = True


def test_open_estimate_navigation_target_equipment() -> None:
    st = _FakeStreamlit()

    app._open_estimate_navigation_target(
        st,
        target_kind="equipment",
        target_value="EQ-1",
    )

    assert st.session_state["atlas_active_page"] == "Equipment"
    assert st.session_state["atlas_context_selection"]["kind"] == "equipment"
    assert st.session_state["atlas_context_selection"]["data"]["equipment_id"] == "EQ-1"


def test_open_estimate_navigation_target_specification() -> None:
    st = _FakeStreamlit()

    app._open_estimate_navigation_target(
        st,
        target_kind="specification",
        target_value="27 41 16",
    )

    assert st.session_state["atlas_active_page"] == "Specifications"
    assert st.session_state["atlas_context_selection"]["kind"] == "specification"


def test_open_estimate_navigation_target_drawing_relationships_and_evidence() -> None:
    st = _FakeStreamlit()

    app._open_estimate_navigation_target(
        st,
        target_kind="drawing",
        target_value="AV-601",
    )
    assert st.session_state["atlas_active_page"] == "Drawings"

    app._open_estimate_navigation_target(
        st,
        target_kind="relationships",
        target_value="EQ-1",
    )
    assert st.session_state["atlas_active_page"] == "Relationships"

    app._open_estimate_navigation_target(
        st,
        target_kind="evidence",
        target_value="bid-set.pdf",
    )
    assert st.session_state["atlas_active_page"] == "Evidence"
    assert st.session_state["atlas_context_selection"]["kind"] == "evidence"

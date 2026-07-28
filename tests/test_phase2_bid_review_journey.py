from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_bid_journey_test_module", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


class _FakeStreamlit:
    def __init__(self, *, pressed: set[str] | None = None) -> None:
        self.session_state: dict[str, Any] = {}
        self._pressed = set(pressed or set())
        self.button_calls: list[dict[str, Any]] = []
        self.selectbox_values: dict[str, Any] = {}
        self.markdowns: list[str] = []
        self.dataframes: list[Any] = []
        self.captions: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.successes: list[str] = []
        self.text_areas: list[dict[str, Any]] = []
        self.columns_requested: list[Any] = []
        self.rerun_called = False

    def markdown(self, text: str, **kwargs: Any) -> None:
        _ = kwargs
        self.markdowns.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def info(self, text: str) -> None:
        self.infos.append(text)

    def warning(self, text: str) -> None:
        self.warnings.append(text)

    def success(self, text: str) -> None:
        self.successes.append(text)

    def dataframe(self, data: Any, **kwargs: Any) -> None:
        _ = kwargs
        self.dataframes.append(data)

    def text_area(self, label: str, value: str = "", **kwargs: Any) -> str:
        self.text_areas.append({"label": label, "value": value, **kwargs})
        key = kwargs.get("key")
        if isinstance(key, str):
            current = self.session_state.get(key)
            if isinstance(current, str):
                return current
        return value

    def selectbox(
        self,
        label: str,
        options: list[Any],
        index: int = 0,
        **kwargs: Any,
    ) -> Any:
        self.columns_requested.append({"label": label, "options": list(options)})
        key = kwargs.get("key")
        if isinstance(key, str) and key in self.selectbox_values:
            return self.selectbox_values[key]
        if not options:
            return ""
        if 0 <= index < len(options):
            return options[index]
        return options[0]

    def button(
        self,
        label: str,
        *,
        key: str | None = None,
        **kwargs: Any,
    ) -> bool:
        _ = kwargs
        self.button_calls.append({"label": label, "key": key})
        return label in self._pressed or (key is not None and key in self._pressed)

    def columns(self, count: int | list[Any], **kwargs: Any) -> list[_FakeStreamlit]:
        _ = kwargs
        self.columns_requested.append(count)
        size = len(count) if isinstance(count, list) else count
        return [self for _ in range(size)]

    def rerun(self) -> None:
        self.rerun_called = True


def _summary() -> dict[str, Any]:
    return {
        "project_name": "Music Academy of the West",
        "analysis_status": "Analysis complete",
        "document_count": 7,
        "project_type": "AV / Theatrical",
        "recommended_next_action": "Open Engineering Review.",
        "unresolved_scope_issue_count": 3,
        "high_risk_issue_count": 2,
        "documents_requiring_ocr": 1,
        "equipment_items_found": 24,
        "possible_bom_items": 18,
        "scope_gaps": 2,
        "quantity_conflicts": 1,
        "responsibility_ambiguities": 1,
        "missing_specifications": 1,
        "unresolved_manufacturer_model_refs": 2,
        "recommended_actions": [
            {"step": "Open Engineering Review"},
            {"step": "Create Draft Estimate"},
        ],
        "coordination_findings": [],
        "overall_confidence": "0.61",
    }


def test_bid_review_panel_shows_visible_journey_steps() -> None:
    st = _FakeStreamlit()

    app._render_bid_review_journey_panel(
        st,
        project_id="BID-2026-0002",
        project_name="Music Academy of the West",
        summary=_summary(),
        route_name="Documents",
    )

    rendered_text = "\n".join([*st.markdowns, *st.captions, *st.infos])
    assert "Bid Review Journey" in rendered_text
    assert any(
        "Documents Uploaded" in str(row)
        for row in st.dataframes[0]
        if isinstance(st.dataframes[0], list)
    )
    assert any(
        "Revised Review V2" in str(row)
        for row in st.dataframes[0]
        if isinstance(st.dataframes[0], list)
    )


def test_bid_review_revised_review_keeps_parent_linkage_and_selection() -> None:
    st = _FakeStreamlit()

    state = app._bid_review_journey_project_state(
        st,
        "BID-2026-0002",
        project_name="Music Academy of the West",
        summary=_summary(),
    )
    created = app._bid_review_create_revised_review(
        st,
        "BID-2026-0002",
        guidance_text="Confirm room names\nClarify lighting scope",
    )
    updated = st.session_state["atlas_bid_review_journeys"]["BID-2026-0002"]
    versions = app._bid_review_report_versions(updated)

    assert created is True
    assert len(versions) == 2
    assert versions[0].version == 1
    assert versions[1].version == 2
    assert versions[1].parent_version == 1
    assert versions[1].status == app.BidReviewReportStatus.REVISED
    assert "Confirm room names" in versions[1].guidance_inputs
    assert updated["selected_report_version"] == 2
    assert state["selected_report_version"] == 2


def test_bid_review_estimate_traceability_records_selected_report_version() -> None:
    st = _FakeStreamlit()
    app._bid_review_journey_project_state(
        st,
        "BID-2026-0002",
        project_name="Music Academy of the West",
        summary=_summary(),
    )
    app._record_bid_review_estimate_creation(
        st,
        project_id="BID-2026-0002",
        estimate_document_id="estimate-123",
        report_version=2,
    )
    state = st.session_state["atlas_bid_review_journeys"]["BID-2026-0002"]

    assert state["estimate_document_id"] == "estimate-123"
    assert state["estimate_source_report_version"] == 2
    assert state["estimate_decision_state"] == "draft"


def test_bid_review_estimate_decision_can_return_to_review() -> None:
    st = _FakeStreamlit(pressed={"atlas_bid_review_return_review_BID-2026-0002"})
    app._bid_review_journey_project_state(
        st,
        "BID-2026-0002",
        project_name="Music Academy of the West",
        summary=_summary(),
    )
    app._record_bid_review_estimate_decision(
        st,
        project_id="BID-2026-0002",
        approval_state=app.ApprovalState.REJECTED,
    )
    fake_estimate = SimpleNamespace(
        approval_state=app.ApprovalState.REJECTED,
        document_number="EST-001",
        project_id="BID-2026-0002",
        project_code="BID-2026-0002",
    )
    original_estimate_document = getattr(app, "_bid_review_estimate_document")
    setattr(
        app,
        "_bid_review_estimate_document",
        lambda st, project_id: fake_estimate,
    )
    try:
        app._render_bid_review_journey_panel(
            st,
            project_id="BID-2026-0002",
            project_name="Music Academy of the West",
            summary=_summary(),
            route_name="Transactions",
        )
    finally:
        setattr(app, "_bid_review_estimate_document", original_estimate_document)

    assert st.session_state["atlas_active_page"] == "Engineering Review"


def test_bid_review_estimate_acceptance_records_decision() -> None:
    st = _FakeStreamlit()
    app._bid_review_journey_project_state(
        st,
        "BID-2026-0002",
        project_name="Music Academy of the West",
        summary=_summary(),
    )
    app._record_bid_review_estimate_decision(
        st,
        project_id="BID-2026-0002",
        approval_state=app.ApprovalState.APPROVED,
    )
    state = st.session_state["atlas_bid_review_journeys"]["BID-2026-0002"]

    assert state["estimate_decision_state"] == "approved"


def test_bid_review_journey_state_stays_project_scoped() -> None:
    st = _FakeStreamlit()
    state_a = app._bid_review_journey_project_state(
        st,
        "BID-2026-0002",
        project_name="Music Academy of the West",
        summary=_summary(),
    )
    app._bid_review_select_report_version(st, "BID-2026-0002", 1)
    state_b = app._bid_review_journey_project_state(
        st,
        "BID-2026-0003",
        project_name="Another Project",
        summary={**_summary(), "project_name": "Another Project"},
    )

    journeys = st.session_state["atlas_bid_review_journeys"]
    assert journeys["BID-2026-0002"]["selected_report_version"] == 1
    assert journeys["BID-2026-0003"]["selected_report_version"] == 1
    assert state_a["project_id"] == "BID-2026-0002"
    assert state_b["project_id"] == "BID-2026-0003"

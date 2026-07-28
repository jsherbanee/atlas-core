from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_density_tests",
    _MODULE_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


def test_project_context_header_summary_items_omit_empty_fields() -> None:
    header = app.ProjectContextHeader(
        project_id="BID-2026-0002",
        project_name="Music Academy of the West",
        customer="Morley Builders",
        location="",
        bid_date="",
        current_phase="Bid Intake",
        overall_status="Intake",
        project_manager="Alex",
        last_activity="Jul 26, 2026",
        current_revision="Current",
        current_health="Normal",
        estimate_status="Create Estimate",
        recommended_next_action="Review Documents",
    )

    items = app._project_context_summary_items(header)

    labels = [label for label, _ in items]
    assert labels == [
        "Project ID",
        "Customer",
        "Current Revision",
        "Readiness",
        "Estimate",
        "Project Manager",
        "Last Activity",
    ]


def test_project_context_header_html_keeps_status_tokens_separated() -> None:
    header = app.ProjectContextHeader(
        project_id="BID-2026-0002",
        project_name="Music Academy of the West",
        customer="Morley Builders",
        location="Los Angeles",
        bid_date="2026-07-26",
        current_phase="Bid Intake",
        overall_status="Intake",
        project_manager="Alex",
        last_activity="Jul 26, 2026",
        current_revision="Current",
        current_health="Normal",
        estimate_status="Continue Estimate",
        recommended_next_action="Review Documents",
    )

    html = app._project_context_header_html(header)

    assert "Bid IntakeIntakeNormal" not in html
    assert "Bid Intake" in html
    assert "Intake" in html
    assert "Normal" in html
    assert "Los Angeles" in html
    assert "Continue Estimate" in html

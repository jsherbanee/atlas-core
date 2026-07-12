from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_recommendation_test_module", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


def test_dedupe_recommendation_rows_merges_priority_count_and_sources() -> None:
    rows = [
        {
            "Priority": "Medium",
            "Recommendation": "Refresh stale deterministic costs before estimate lock.",
            "Count": 2,
            "Destination": "Estimate",
            "Source": "Deterministic Cost",
        },
        {
            "Priority": "High",
            "Recommendation": "  Refresh stale deterministic costs before estimate lock. ",
            "Count": 1,
            "Destination": "Estimate",
            "Source": "Commercial Knowledge",
        },
    ]

    deduped = app._dedupe_recommendation_rows(rows)

    assert len(deduped) == 1
    assert deduped[0]["Priority"] == "High"
    assert deduped[0]["Count"] == 3
    assert deduped[0]["Source"] == "Commercial Knowledge / Deterministic Cost"


def test_normalize_recommendation_text_collapses_whitespace_and_case() -> None:
    normalized = app._normalize_recommendation_text("  Resolve   Missing COST  ")
    assert normalized == "resolve missing cost"

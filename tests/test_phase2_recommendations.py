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


def test_recommendation_destination_page_maps_aliases_and_fallback() -> None:
    assert app._recommendation_destination_page("Price Sheets") == "Price List Library"
    assert app._recommendation_destination_page("Assemblies") == "Knowledge"
    assert (
        app._recommendation_destination_page("Unknown Destination") == "Mission Control"
    )


def test_validate_assembly_component_reference_requires_reference_for_bound_types() -> (
    None
):
    valid, message = app._validate_assembly_component_reference("product", "")
    assert valid is False
    assert "required" in message.lower()

    valid_optional, _ = app._validate_assembly_component_reference("allowance", "")
    assert valid_optional is True


def test_recommendation_guidance_for_high_priority_estimate_signal() -> None:
    guidance = app._recommendation_guidance(
        {
            "Priority": "High",
            "Recommendation": "Resolve missing deterministic cost selections before estimate lock.",
            "Destination": "Estimate",
            "Source": "Estimate Engine D-03",
        }
    )

    assert (
        "deterministic estimate/assembly readiness diagnostics"
        in guidance["Why am I seeing this?"]
    )
    assert "block revision readiness" in guidance["Why does it matter?"]
    assert "Open Estimate" in guidance["What should I do?"]


def test_recommendation_guidance_falls_back_safely_for_unknown_source() -> None:
    guidance = app._recommendation_guidance(
        {
            "Priority": "Low",
            "Recommendation": "",
            "Destination": "Knowledge",
            "Source": "Unmapped Source",
        }
    )

    assert "deterministic workspace signals" in guidance["Why am I seeing this?"]
    assert "overall project hygiene" in guidance["Why does it matter?"]
    assert "Open Knowledge" in guidance["What should I do?"]


def test_persist_assembly_library_state_updates_engine_and_saves() -> None:
    class _StubEngine:
        def __init__(self) -> None:
            self.state: dict[str, object] = {}

    class _StubAssemblyService:
        @staticmethod
        def to_dict() -> dict[str, object]:
            return {"versions": [{"id": "av-1"}]}

    captured: list[tuple[object, object]] = []
    original_save = getattr(app, "_save_estimate_engine_service")
    setattr(
        app,
        "_save_estimate_engine_service",
        lambda st, engine: captured.append((st, engine)),
    )
    try:
        engine = _StubEngine()
        service = _StubAssemblyService()
        sentinel_state = object()

        app._persist_assembly_library_state(sentinel_state, engine, service)

        assert engine.state["assembly_state"] == {"versions": [{"id": "av-1"}]}
        assert captured == [(sentinel_state, engine)]
    finally:
        setattr(app, "_save_estimate_engine_service", original_save)

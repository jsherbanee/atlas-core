from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_settings_nav_tests",
    _MODULE_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


class _FakeStreamlit:
    def __init__(self, *, session_state: dict[str, object] | None = None) -> None:
        self.session_state = dict(session_state or {})


def test_settings_workspace_contract_has_expected_sections() -> None:
    contract = app._workspace_navigation_contract("Settings", "application")
    secondary_keys = [item["secondary_key"] for item in contract]
    assert secondary_keys == [
        "organization_settings",
        "personal_preferences",
        "integrations",
        "security",
        "billing",
        "advanced",
        "platform_management",
    ]

    org_section = next(
        item for item in contract if item["secondary_key"] == "organization_settings"
    )
    org_tertiary = [
        item["tertiary_key"]
        for item in org_section.get("supported_tertiary_actions", [])
    ]
    assert org_tertiary == [
        "overview",
        "organization_profile",
        "commercial_numbering",
        "taxes_surcharges",
        "terms_and_conditions",
        "document_templates",
        "roles_permissions",
        "audit",
    ]

    platform_section = next(
        item for item in contract if item["secondary_key"] == "platform_management"
    )
    platform_tertiary = [
        item["tertiary_key"]
        for item in platform_section.get("supported_tertiary_actions", [])
    ]
    assert platform_tertiary == [
        "tenant_manager",
        "alpha_health_check",
        "feedback",
        "alpha_tester_onboarding",
        "alpha_operations_dashboard",
        "alpha_release_stabilization",
        "error_log",
        "known_limitations",
        "operator_checklist",
    ]

    deferred_sections = {"integrations", "security", "billing", "advanced"}
    assert all(
        item["enabled"] is False
        for item in contract
        if item["secondary_key"] in deferred_sections
    )
    assert platform_section["enabled"] is True


def test_administration_routes_to_settings_primary() -> None:
    assert app._active_primary_workspace("Administration", None) == "Settings"


def test_sync_workspace_navigation_state_sets_settings_defaults() -> None:
    st = _FakeStreamlit(
        session_state={
            "atlas_active_page": "Administration",
            "atlas_context_selection": {"kind": "project", "data": {}},
        }
    )

    app._sync_workspace_navigation_state(st, record=None)

    assert st.session_state["atlas_active_primary_workspace"] == "Settings"
    assert st.session_state["atlas_active_workspace_mode"] == "application"
    assert st.session_state["atlas_active_secondary_section"] == "organization_settings"


def test_alpha_environment_marker_blocks_production_designation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATLAS_RELEASE_CHANNEL", "production")

    marker = app._alpha_environment_marker()

    assert marker["effective_channel"] == "controlled-alpha"
    assert marker["blocked_production_designation"] is True

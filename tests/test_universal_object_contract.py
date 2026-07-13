from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

from atlas_core.contracts.universal_object_contract import (
    UNIVERSAL_OBJECT_SCHEMA_VERSION,
    UniversalObjectActivity,
    UniversalObjectIdentity,
    UniversalObjectRelationship,
)
from atlas_core.domain import Project, ProjectStatus
from atlas_core.services.universal_object_registry import (
    UniversalObjectRegistry,
    build_default_universal_object_registry,
)
import pytest

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_universal_contract_tests", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


def test_universal_object_identity_is_deterministic() -> None:
    identity = UniversalObjectIdentity(
        object_id="EQ-1",
        object_type="equipment",
        tenant_id="local",
        owning_workspace="Projects",
        owning_project_id="maw-demo",
        canonical_display_name="QSC Core",
        source_authority="atlas",
    )

    assert identity.universal_object_id == "local:equipment:maw-demo:EQ-1"


def test_universal_object_identity_from_dict_supports_legacy_shape() -> None:
    identity = UniversalObjectIdentity.from_dict(
        {
            "object_id": "vendor-adi",
            "object_type": "vendor",
            "tenant_id": "local",
            "owning_workspace": "Knowledge",
            "canonical_display_name": "ADI",
        }
    )

    assert identity.schema_version == UNIVERSAL_OBJECT_SCHEMA_VERSION
    assert identity.universal_object_id == "local:vendor:application:vendor-adi"


def test_universal_relationship_rejects_cross_tenant_links() -> None:
    source = UniversalObjectIdentity(
        object_id="customer-acme",
        object_type="customer",
        tenant_id="tenant-a",
        owning_workspace="Knowledge",
        canonical_display_name="Acme",
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


def test_universal_activity_rejects_tenant_mismatch() -> None:
    identity = UniversalObjectIdentity(
        object_id="vendor-adi",
        object_type="vendor",
        tenant_id="tenant-a",
        owning_workspace="Knowledge",
        canonical_display_name="ADI",
        source_authority="atlas",
    )

    with pytest.raises(ValueError):
        UniversalObjectActivity(
            activity_id="activity-1",
            object_identity=identity,
            activity_type="updated",
            actor="system",
            timestamp="2026-07-13T00:00:00+00:00",
            tenant_id="tenant-b",
            summary="Updated vendor",
        )


def test_registry_rejects_duplicate_registration() -> None:
    registry = UniversalObjectRegistry()
    registry.register(
        "project",
        lambda source, *, tenant_id, owning_workspace, owning_project_id=None: source,
    )

    with pytest.raises(ValueError):
        registry.register(
            "project",
            lambda source, *, tenant_id, owning_workspace, owning_project_id=None: source,
        )


def test_registry_reports_registered_types_in_deterministic_order() -> None:
    registry = build_default_universal_object_registry()

    types = registry.registered_object_types()

    assert types == sorted(types)
    assert "project" in types
    assert "product" in types
    assert "drawing" in types


def test_project_adapter_preserves_existing_id() -> None:
    registry = build_default_universal_object_registry()
    project = Project(
        project_id="BID-2026-0001",
        name="MAW",
        client="MAW",
        status=ProjectStatus.INTAKE,
    )

    universal_object = registry.adapt(
        "project",
        project,
        tenant_id="local",
        owning_workspace="Projects",
    )

    assert universal_object.identity.object_id == "BID-2026-0001"
    assert universal_object.identity.object_type == "project"
    assert universal_object.presentation is not None
    assert "documents" in [
        view.lower() for view in universal_object.presentation.supported_views
    ]


@pytest.mark.parametrize(
    ("object_type", "payload", "expected_id"),
    [
        (
            "customer",
            {"customer": "Acme", "customer_id": "customer-acme"},
            "customer-acme",
        ),
        ("vendor", {"vendor": "ADI", "vendor_id": "vendor-adi"}, "vendor-adi"),
        (
            "manufacturer",
            {"manufacturer": "QSC", "manufacturer_id": "mfr-qsc"},
            "mfr-qsc",
        ),
        (
            "product",
            {
                "manufacturer": "QSC",
                "model": "Core 110f",
                "atlas_product_uuid": "prod-core-110f",
            },
            "prod-core-110f",
        ),
        (
            "service",
            {"service": "Programming", "service_id": "svc-programming"},
            "svc-programming",
        ),
        ("drawing", {"drawing_number": "AV-601", "title": "Plan"}, "AV-601"),
        ("specification", {"section": "27 41 16", "title": "AV Systems"}, "27 41 16"),
        (
            "equipment",
            {"equipment_id": "EQ-1", "manufacturer": "QSC", "model": "Core"},
            "EQ-1",
        ),
    ],
)
def test_representative_adapters_build_universal_identity(
    object_type: str,
    payload: dict[str, object],
    expected_id: str,
) -> None:
    registry = build_default_universal_object_registry()

    universal_object = registry.adapt(
        object_type,
        payload,
        tenant_id="local",
        owning_workspace=(
            "Knowledge"
            if object_type
            in {"customer", "vendor", "manufacturer", "product", "service"}
            else "Projects"
        ),
        owning_project_id=(
            "maw-demo"
            if object_type in {"drawing", "specification", "equipment"}
            else None
        ),
    )

    assert universal_object.identity.object_id == expected_id
    assert universal_object.identity.tenant_id == "local"
    assert universal_object.presentation is not None
    assert universal_object.actions


def test_registry_identity_resolution_and_presentation_helpers() -> None:
    registry = build_default_universal_object_registry()
    payload = {"vendor": "ADI", "vendor_id": "vendor-adi", "vendor_code": "ADI"}

    identity = registry.resolve_identity(
        "vendor",
        payload,
        tenant_id="local",
        owning_workspace="Knowledge",
    )
    presentation = registry.presentation_metadata(
        "vendor",
        payload,
        tenant_id="local",
        owning_workspace="Knowledge",
    )
    actions = registry.supported_actions(
        "vendor",
        payload,
        tenant_id="local",
        owning_workspace="Knowledge",
    )
    relationship_groups = registry.supported_relationship_groups(
        "vendor",
        payload,
        tenant_id="local",
        owning_workspace="Knowledge",
    )

    assert identity.universal_object_id == "local:vendor:application:vendor-adi"
    assert presentation is not None
    assert presentation.primary_label == "ADI"
    assert any(action.action_key == "open" for action in actions)
    assert "Related Products" in relationship_groups


def test_build_object_reference_exposes_universal_identity() -> None:
    reference = app._build_object_reference(
        kind="customer",
        data={"customer": "Acme", "customer_id": "customer-acme"},
        project_id="application",
        project_name="Knowledge",
        route="Knowledge",
    )

    assert (
        reference["universal_object_id"] == "local:customer:application:customer-acme"
    )
    assert reference["universal_object_identity"]["object_type"] == "customer"


def test_context_snapshot_persists_universal_identity_state() -> None:
    st = SimpleNamespace(
        session_state={
            "atlas_active_page": "Knowledge",
            "atlas_context_selection": {
                "kind": "vendor",
                "data": {"vendor": "ADI", "vendor_id": "vendor-adi"},
            },
            "atlas_file_search": "",
            "atlas_equipment_search": "",
            "atlas_search_type_filters": [],
            "atlas_relationship_search_enabled": False,
            "atlas_global_search_query": "ADI",
            "atlas_global_search_index": 0,
            "atlas_layout_mode": "Desktop",
            "atlas_navigation_collapsed": False,
            "atlas_notebook_entries": [],
            "atlas_review_flags": {},
            "atlas_recently_viewed_objects": [],
            "atlas_pinned_objects": [],
            "atlas_recent_search_queries": [],
            "atlas_recent_opened_results": [],
            "atlas_active_primary_workspace": "Knowledge",
            "atlas_active_workspace_mode": "application",
            "atlas_active_secondary_section": "vendors",
            "atlas_active_tertiary_action": "browse",
            "atlas_selected_entity_type": "vendor",
            "atlas_selected_entity_id": "ADI",
            "atlas_selected_project_object_type": "",
            "atlas_selected_project_object_id": "",
            "atlas_selected_project_object_identity": {},
            "atlas_selected_knowledge_entity_type": "vendor",
            "atlas_selected_knowledge_entity_id": "ADI",
            "atlas_selected_knowledge_entity_identity": {
                "universal_object_id": "local:vendor:application:vendor-adi",
                "object_type": "vendor",
            },
            "atlas_return_context": {},
            "atlas_navigation_history": [],
            "atlas_originating_workspace": "Projects",
            "atlas_originating_route": "Reports",
            "atlas_tenant_scope": "local",
        }
    )

    snapshot = app._workspace_state_snapshot(st)

    context_state = snapshot["workspace_context_state"]
    assert (
        context_state["selected_knowledge_entity_identity"]["universal_object_id"]
        == "local:vendor:application:vendor-adi"
    )


def test_return_context_carries_selected_universal_identity() -> None:
    st = SimpleNamespace(
        session_state={
            "atlas_active_primary_workspace": "Knowledge",
            "atlas_active_workspace_mode": "application",
            "atlas_active_page": "Knowledge",
            "atlas_active_secondary_section": "vendors",
            "atlas_active_tertiary_action": "browse",
            "atlas_active_workspace_id": "",
            "atlas_active_project_name": "",
            "atlas_context_selection": {
                "kind": "vendor",
                "data": {"vendor": "ADI", "vendor_id": "vendor-adi"},
            },
            "atlas_selected_project_object_type": "",
            "atlas_selected_project_object_id": "",
            "atlas_selected_project_object_identity": {},
            "atlas_selected_knowledge_entity_type": "vendor",
            "atlas_selected_knowledge_entity_id": "vendor-adi",
            "atlas_selected_knowledge_entity_identity": {
                "universal_object_id": "local:vendor:application:vendor-adi",
                "object_type": "vendor",
            },
            "atlas_tenant_scope": "local",
            "atlas_navigation_history": [],
        }
    )

    entry = app._record_return_context(st, source_label="Vendor List")

    assert (
        entry["source_object_identity"]["universal_object_id"]
        == "local:vendor:application:vendor-adi"
    )


def test_working_set_compatibility_preserves_legacy_entries() -> None:
    st = SimpleNamespace(
        session_state={
            "atlas_pinned_objects": [
                {
                    "object_id": "legacy-1",
                    "object_type": "Equipment",
                    "display_name": "Legacy",
                }
            ]
        }
    )
    new_reference = app._build_object_reference(
        kind="vendor",
        data={"vendor": "ADI", "vendor_id": "vendor-adi"},
        project_id="application",
        project_name="Knowledge",
        route="Knowledge",
    )

    app._toggle_pin_reference(st, new_reference, should_pin=True)

    assert len(st.session_state["atlas_pinned_objects"]) == 2
    assert any(
        item.get("object_id") == "legacy-1"
        for item in st.session_state["atlas_pinned_objects"]
    )
    assert any(
        item.get("universal_object_id") == "local:vendor:application:vendor-adi"
        for item in st.session_state["atlas_pinned_objects"]
    )

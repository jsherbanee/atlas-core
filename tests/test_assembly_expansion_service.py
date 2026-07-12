from decimal import Decimal

from atlas_core.domain.assembly_labor import (
    AccessoryRuleKind,
    AssemblyExpansionRequest,
    AssemblyLifecycleState,
    QuantityRuleType,
)
from atlas_core.services.assembly_expansion_service import AssemblyExpansionService


def _base_service() -> AssemblyExpansionService:
    service = AssemblyExpansionService()
    created = service.create_assembly(
        canonical_name="audio_dsp_package",
        display_name="Audio DSP Package",
        created_by="tester",
        assembly_id="assembly:audio:dsp",
    )
    assert created["version"]["lifecycle_state"] == AssemblyLifecycleState.DRAFT.value
    return service


def _material_component(component_id: str, quantity: float = 1.0) -> dict[str, object]:
    return {
        "component_id": component_id,
        "component_type": "product",
        "product_id": f"product::{component_id}",
        "quantity_rule": {
            "rule_type": QuantityRuleType.PER_PARENT.value,
            "value": quantity,
            "minimum_quantity": 0,
            "round_up_to": 1,
            "waste_factor": 0,
            "spare_factor": 0,
        },
        "accessory_rule": {"kind": AccessoryRuleKind.NONE.value},
    }


def test_lifecycle_validation_activation_and_supersede() -> None:
    service = _base_service()
    version_id = ""
    for row in service.state["versions"].values():
        version_id = str(row["assembly_version_id"])
    service.add_component(
        assembly_version_id=version_id,
        component=_material_component("main_dsp", 1),
    )
    validated = service.validate_assembly(assembly_version_id=version_id)
    assert validated["valid"] is True
    assert validated["lifecycle_state"] == AssemblyLifecycleState.VALIDATED.value

    activated = service.activate_assembly_version(assembly_version_id=version_id)
    assert activated["lifecycle_state"] == AssemblyLifecycleState.ACTIVE.value

    superseded = service.supersede_assembly_version(assembly_version_id=version_id)
    assert superseded["lifecycle_state"] == AssemblyLifecycleState.SUPERSEDED.value


def test_detect_cycles_on_nested_assembly() -> None:
    service = AssemblyExpansionService()
    root = service.create_assembly(
        canonical_name="root",
        display_name="Root",
        created_by="tester",
        assembly_id="assembly:root",
    )
    child = service.create_assembly(
        canonical_name="child",
        display_name="Child",
        created_by="tester",
        assembly_id="assembly:child",
    )
    root_version = root["version"]["assembly_version_id"]
    child_version = child["version"]["assembly_version_id"]

    service.add_component(
        assembly_version_id=root_version,
        component={
            "component_id": "root_to_child",
            "component_type": "nested_assembly",
            "nested_assembly_version_id": child_version,
            "quantity_rule": {"rule_type": "per_parent", "value": 1},
            "accessory_rule": {"kind": "none"},
        },
    )
    service.add_component(
        assembly_version_id=child_version,
        component={
            "component_id": "child_to_root",
            "component_type": "nested_assembly",
            "nested_assembly_version_id": root_version,
            "quantity_rule": {"rule_type": "per_parent", "value": 1},
            "accessory_rule": {"kind": "none"},
        },
    )

    cycle = service.detect_cycles(assembly_version_id=root_version)
    assert cycle["has_cycle"] is True

    validation = service.validate_assembly(assembly_version_id=root_version)
    assert validation["valid"] is False
    assert any(
        d["code"] == "circular_assembly_reference" for d in validation["diagnostics"]
    )


def test_accessory_required_and_optional_selection() -> None:
    service = _base_service()
    version_id = next(iter(service.state["versions"]))

    service.add_component(
        assembly_version_id=version_id,
        component=_material_component("required_mount", 1),
    )
    service.update_draft_component(
        assembly_version_id=version_id,
        component_id="required_mount",
        updates={"accessory_rule": {"kind": AccessoryRuleKind.REQUIRED.value}},
    )

    service.add_component(
        assembly_version_id=version_id,
        component={
            **_material_component("opt_cover", 1),
            "accessory_rule": {
                "kind": AccessoryRuleKind.OPTIONAL.value,
                "option_group": "cover",
            },
        },
    )

    required = service.list_required_accessories(assembly_version_id=version_id)
    optional = service.list_optional_accessories(assembly_version_id=version_id)
    assert len(required) == 1
    assert len(optional) == 1

    preview = service.preview_expansion(
        request=AssemblyExpansionRequest(
            estimate_id="estimate:1",
            revision_id="revision:1",
            assembly_version_id=version_id,
            parent_quantity=Decimal("1"),
            selected_optional_component_ids=[],
        )
    )
    assert len(preview["contributions"]) == 1

    preview_selected = service.preview_expansion(
        request=AssemblyExpansionRequest(
            estimate_id="estimate:1",
            revision_id="revision:1",
            assembly_version_id=version_id,
            parent_quantity=Decimal("1"),
            selected_optional_component_ids=["opt_cover"],
        )
    )
    assert len(preview_selected["contributions"]) == 2


def test_quantity_rule_computation_and_consolidation() -> None:
    service = _base_service()
    version_id = next(iter(service.state["versions"]))

    service.add_component(
        assembly_version_id=version_id,
        component={
            "component_id": "dsp",
            "component_type": "product",
            "product_id": "QSC::Core110f",
            "quantity_rule": {
                "rule_type": QuantityRuleType.PER_PARENT.value,
                "value": 2,
                "minimum_quantity": 1,
                "round_up_to": 1,
                "waste_factor": 0.1,
                "spare_factor": 0,
            },
            "accessory_rule": {"kind": AccessoryRuleKind.NONE.value},
        },
    )

    preview = service.preview_expansion(
        request={
            "estimate_id": "estimate:1",
            "revision_id": "revision:1",
            "assembly_version_id": version_id,
            "parent_quantity": 3,
        }
    )

    assert preview["diagnostics"] == []
    assert len(preview["contributions"]) == 1
    row = preview["contributions"][0]
    assert row["product_id"] == "QSC::Core110f"
    assert float(row["generated_quantity"]) == 7.0

    consolidated = preview["consolidated_materials"]
    assert len(consolidated) == 1
    assert consolidated[0]["product_id"] == "QSC::Core110f"
    assert float(consolidated[0]["generated_quantity"]) == 7.0


def test_labor_rollup_with_active_rate_set() -> None:
    service = _base_service()
    version_id = next(iter(service.state["versions"]))

    service.add_component(
        assembly_version_id=version_id,
        component={
            "component_id": "install_hours",
            "component_type": "labor_activity",
            "labor_activity_id": "labor:install",
            "quantity_rule": {
                "rule_type": QuantityRuleType.PER_PARENT.value,
                "value": 2,
                "minimum_quantity": 0,
                "round_up_to": 0.25,
                "waste_factor": 0,
                "spare_factor": 0,
            },
            "accessory_rule": {"kind": AccessoryRuleKind.NONE.value},
            "provenance_metadata": {"labor_category": "installation"},
        },
    )

    service.create_labor_rate_set(
        labor_rate_set_id="labor_rates:v1",
        version_label="v1",
        effective_date="2026-01-01",
        created_by="tester",
    )
    service.add_labor_rate_record(
        labor_rate_set_id="labor_rates:v1",
        record={
            "labor_category": "installation",
            "unit_basis": "hours",
            "straight_time_rate": 100,
            "burden_rate": 25,
        },
    )
    service.activate_labor_rate_set(labor_rate_set_id="labor_rates:v1")

    expanded = service.expand_assembly(
        request={
            "estimate_id": "estimate:1",
            "revision_id": "revision:1",
            "assembly_version_id": version_id,
            "parent_quantity": 3,
        },
        labor_rate_set_id="labor_rates:v1",
    )

    labor_rollup = expanded["labor_rollup"]
    assert labor_rollup["labor_rate_set_id"] == "labor_rates:v1"
    assert float(labor_rollup["total_hours"]) == 6.0
    assert float(labor_rollup["total_labor_cost"]) == 750.0


def test_active_version_is_immutable_and_prior_versions_remain_queryable() -> None:
    service = _base_service()
    initial_version_id = next(iter(service.state["versions"]))

    service.add_component(
        assembly_version_id=initial_version_id,
        component=_material_component("main_dsp", 1),
    )
    service.validate_assembly(assembly_version_id=initial_version_id)
    service.activate_assembly_version(assembly_version_id=initial_version_id)

    cloned = service.clone_assembly_version(
        source_assembly_version_id=initial_version_id,
        created_by="tester",
        version_label="v2",
        revision_reason="closeout update",
    )
    cloned_version_id = str(cloned["assembly_version_id"])
    service.validate_assembly(assembly_version_id=cloned_version_id)
    service.activate_assembly_version(assembly_version_id=cloned_version_id)

    try:
        service.add_component(
            assembly_version_id=initial_version_id,
            component=_material_component("new_component", 1),
        )
        assert False, "Expected active version immutability"
    except ValueError as exc:
        assert "immutable" in str(exc)

    # Historical versions must remain queryable after supersession.
    assert initial_version_id in service.state["versions"]
    assert service.state["versions"][initial_version_id]["lifecycle_state"] == (
        AssemblyLifecycleState.SUPERSEDED.value
    )

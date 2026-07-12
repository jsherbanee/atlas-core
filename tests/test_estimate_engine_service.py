from datetime import date

from atlas_core.services.assembly_expansion_service import AssemblyExpansionService
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
from atlas_core.services.estimate_engine_service import EstimateEngineService


def _commercial_state(unit_cost: float = 1000.0) -> dict[str, object]:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="VendorA",
        manufacturer="QSC",
        sheet_name="QSC Cost",
        description="Test",
        source_filename="qsc.csv",
        file_bytes=b"qsc",
        imported_by="tester",
        rows=[
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "QSC-110F",
                "unit_cost": unit_cost,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
                "confidence": 0.95,
            }
        ],
    )
    return service.to_dict()


def _line(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "product_id": "QSC::Core110f",
        "manufacturer": "QSC",
        "model": "Core110f",
        "description": "DSP",
        "requested_quantity": 2,
        "engineering_quantity": 2,
        "procurement_quantity": 2,
        "unit_of_measure": "ea",
        "section": "Audio",
        "system": "Main",
        "room": "Theater",
        "source_object_id": "EQ-1",
    }
    payload.update(overrides)
    return payload


def _seed_assembly(engine: EstimateEngineService) -> str:
    assembly = AssemblyExpansionService(
        state=dict(engine.state.get("assembly_state") or {})
    )
    created = assembly.create_assembly(
        canonical_name="dsp_with_labor",
        display_name="DSP with Labor",
        created_by="tester",
        assembly_id="assembly:dsp:labor",
    )
    version_id = str(created["version"]["assembly_version_id"])
    assembly.add_component(
        assembly_version_id=version_id,
        component={
            "component_id": "product:dsp",
            "component_type": "product",
            "product_id": "QSC::Core110f",
            "quantity_rule": {"rule_type": "per_parent", "value": 1},
            "accessory_rule": {"kind": "none"},
        },
    )
    assembly.add_component(
        assembly_version_id=version_id,
        component={
            "component_id": "labor:install",
            "component_type": "labor_activity",
            "labor_activity_id": "labor:install",
            "quantity_rule": {"rule_type": "per_parent", "value": 2},
            "accessory_rule": {"kind": "none"},
            "provenance_metadata": {"labor_category": "installation"},
        },
    )
    assembly.create_labor_rate_set(
        labor_rate_set_id="labor_rates:v1",
        version_label="v1",
        effective_date="2026-01-01",
        created_by="tester",
    )
    assembly.add_labor_rate_record(
        labor_rate_set_id="labor_rates:v1",
        record={
            "labor_category": "installation",
            "unit_basis": "hours",
            "straight_time_rate": 120,
            "burden_rate": 30,
        },
    )
    assembly.activate_labor_rate_set(labor_rate_set_id="labor_rates:v1")
    engine.state["assembly_state"] = assembly.to_dict()
    return version_id


def test_estimate_and_initial_revision_lifecycle_creation() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-1",
        name="Main Estimate",
        created_by="tester",
        estimate_id="estimate:project-1:main",
    )

    estimate = created["estimate"]
    revision = created["revision"]
    assert estimate["estimate_id"] == "estimate:project-1:main"
    assert revision["revision_number"] == 1
    assert revision["state"] == "draft"


def test_add_line_select_cost_validate_and_lock_revision() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-1",
        name="Main Estimate",
        created_by="tester",
        estimate_id="estimate:project-1:main",
    )
    revision_id = created["revision"]["revision_id"]

    line = engine.add_line_item(revision_id=revision_id, actor="tester", line=_line())
    selection = engine.select_line_cost(
        revision_id=revision_id,
        line_item_id=line["line_item_id"],
        commercial_state=_commercial_state(),
        actor="tester",
    )
    assert selection["snapshot"]["reference"]["price_record_id"]

    validation = engine.validate_revision(revision_id=revision_id)
    assert validation["ready"] is True
    locked = engine.lock_revision(revision_id=revision_id, actor="tester")
    assert locked["state"] == "locked"


def test_locked_revision_is_immutable() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-1",
        name="Main Estimate",
        created_by="tester",
        estimate_id="estimate:project-1:main",
    )
    revision_id = created["revision"]["revision_id"]
    line = engine.add_line_item(revision_id=revision_id, actor="tester", line=_line())
    engine.select_line_cost(
        revision_id=revision_id,
        line_item_id=line["line_item_id"],
        commercial_state=_commercial_state(),
        actor="tester",
    )
    engine.lock_revision(revision_id=revision_id, actor="tester")

    try:
        engine.update_draft_line_item(
            revision_id=revision_id,
            line_item_id=line["line_item_id"],
            actor="tester",
            updates={"description": "Updated"},
        )
        assert False, "Expected immutable revision failure"
    except ValueError as exc:
        assert "immutable" in str(exc)


def test_refresh_on_locked_revision_creates_new_draft() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-1",
        name="Main Estimate",
        created_by="tester",
        estimate_id="estimate:project-1:main",
    )
    revision_id = created["revision"]["revision_id"]
    line = engine.add_line_item(revision_id=revision_id, actor="tester", line=_line())
    engine.select_line_cost(
        revision_id=revision_id,
        line_item_id=line["line_item_id"],
        commercial_state=_commercial_state(1000.0),
        actor="tester",
    )
    engine.lock_revision(revision_id=revision_id, actor="tester")

    refresh = engine.refresh_line_cost(
        revision_id=revision_id,
        line_item_id=line["line_item_id"],
        commercial_state=_commercial_state(1200.0),
        actor="tester",
        accept=True,
    )
    assert refresh["working_revision_id"] != revision_id
    assert refresh["accepted"] is True


def test_replay_returns_frozen_revision_payload() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-1",
        name="Main Estimate",
        created_by="tester",
        estimate_id="estimate:project-1:main",
    )
    revision_id = created["revision"]["revision_id"]
    line = engine.add_line_item(revision_id=revision_id, actor="tester", line=_line())
    engine.select_line_cost(
        revision_id=revision_id,
        line_item_id=line["line_item_id"],
        commercial_state=_commercial_state(),
        actor="tester",
    )
    engine.lock_revision(revision_id=revision_id, actor="tester")

    replay = engine.replay_revision(revision_id=revision_id)
    assert replay["revision"]["state"] == "locked"
    assert len(replay["snapshots"]) == 1


def test_reselection_preview_compares_without_mutating_locked_revision() -> None:
    engine = EstimateEngineService(as_of=date(2026, 6, 1))
    created = engine.create_estimate(
        project_id="project-1",
        name="Main Estimate",
        created_by="tester",
        estimate_id="estimate:project-1:main",
    )
    revision_id = created["revision"]["revision_id"]
    line = engine.add_line_item(revision_id=revision_id, actor="tester", line=_line())
    engine.select_line_cost(
        revision_id=revision_id,
        line_item_id=line["line_item_id"],
        commercial_state=_commercial_state(1000.0),
        actor="tester",
    )
    engine.lock_revision(revision_id=revision_id, actor="tester")

    preview = engine.reselection_preview(
        revision_id=revision_id,
        commercial_state=_commercial_state(1100.0),
        as_of_date="2026-06-01",
    )
    assert preview["line_previews"]
    original = engine.replay_revision(revision_id=revision_id)
    assert original["revision"]["state"] == "locked"


def test_revision_comparison_detects_snapshot_changes() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-1",
        name="Main Estimate",
        created_by="tester",
        estimate_id="estimate:project-1:main",
    )
    baseline_id = created["revision"]["revision_id"]
    line = engine.add_line_item(revision_id=baseline_id, actor="tester", line=_line())
    engine.select_line_cost(
        revision_id=baseline_id,
        line_item_id=line["line_item_id"],
        commercial_state=_commercial_state(1000.0),
        actor="tester",
    )
    engine.lock_revision(revision_id=baseline_id, actor="tester")

    cloned = engine.clone_revision(source_revision_id=baseline_id, created_by="tester")
    clone_id = cloned["revision_id"]
    engine.refresh_line_cost(
        revision_id=clone_id,
        line_item_id=line["line_item_id"],
        commercial_state=_commercial_state(1300.0),
        actor="tester",
        accept=True,
    )

    comparison = engine.compare_revisions(
        baseline_revision_id=baseline_id,
        comparison_revision_id=clone_id,
    )
    assert comparison["changed_lines"]


def test_totals_are_decimal_safe_and_grouped() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-1",
        name="Main Estimate",
        created_by="tester",
        estimate_id="estimate:project-1:main",
    )
    revision_id = created["revision"]["revision_id"]
    line1 = engine.add_line_item(
        revision_id=revision_id,
        actor="tester",
        line=_line(line_item_id="line:1", requested_quantity=1),
    )
    line2 = engine.add_line_item(
        revision_id=revision_id,
        actor="tester",
        line=_line(line_item_id="line:2", requested_quantity=2, room="Lobby"),
    )

    state = _commercial_state(99.995)
    engine.select_line_cost(
        revision_id=revision_id,
        line_item_id=line1["line_item_id"],
        commercial_state=state,
        actor="tester",
    )
    engine.select_line_cost(
        revision_id=revision_id,
        line_item_id=line2["line_item_id"],
        commercial_state=state,
        actor="tester",
    )

    totals = engine.calculate_revision_totals(revision_id=revision_id)
    assert totals["acquisition_cost_total"] > 0
    assert "Audio" in totals["section_subtotals"]
    assert "Lobby" in totals["room_subtotals"]


def test_validation_and_readiness_block_missing_snapshot() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-1",
        name="Main Estimate",
        created_by="tester",
        estimate_id="estimate:project-1:main",
    )
    revision_id = created["revision"]["revision_id"]
    engine.add_line_item(revision_id=revision_id, actor="tester", line=_line())

    validation = engine.validate_revision(revision_id=revision_id)
    assert validation["ready"] is False
    assert any(item["code"] == "missing_snapshot" for item in validation["diagnostics"])


def test_mission_control_readiness_recommendations() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-1",
        name="Main Estimate",
        created_by="tester",
        estimate_id="estimate:project-1:main",
    )
    revision_id = created["revision"]["revision_id"]
    line = engine.add_line_item(revision_id=revision_id, actor="tester", line=_line())
    engine.select_line_cost(
        revision_id=revision_id,
        line_item_id=line["line_item_id"],
        commercial_state=_commercial_state(),
        actor="tester",
    )
    engine.validate_revision(revision_id=revision_id)

    recommendations = engine.mission_control_readiness(
        estimate_id="estimate:project-1:main"
    )
    assert recommendations["state"] in {"ready", "draft", "locked"}
    assert recommendations["recommendations"]


def test_add_assembly_to_revision_creates_parent_children_and_snapshots() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-assembly",
        name="Assembly Estimate",
        created_by="tester",
        estimate_id="estimate:project-assembly:main",
    )
    revision_id = created["revision"]["revision_id"]
    version_id = _seed_assembly(engine)

    inserted = engine.add_assembly_to_revision(
        revision_id=revision_id,
        assembly_version_id=version_id,
        parent_quantity=2,
        labor_rate_set_id="labor_rates:v1",
        commercial_state=_commercial_state(1500.0),
        actor="tester",
        parent_description="DSP Assembly",
    )
    assert inserted["accepted"] is True
    assert inserted["parent_line"]["line_role"] == "assembly_parent"

    revision = engine.state["revisions"][revision_id]
    line_roles = [str(item.get("line_role") or "") for item in revision["line_items"]]
    assert "assembly_parent" in line_roles
    assert "generated_product_child" in line_roles
    assert "generated_labor_child" in line_roles

    labor_children = [
        item
        for item in revision["line_items"]
        if str(item.get("line_role") or "") == "generated_labor_child"
    ]
    assert labor_children
    assert str(labor_children[0].get("labor_snapshot_id") or "")


def test_assembly_insertion_rolls_back_when_product_cost_missing() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-assembly-fail",
        name="Assembly Estimate",
        created_by="tester",
        estimate_id="estimate:project-assembly-fail:main",
    )
    revision_id = created["revision"]["revision_id"]
    version_id = _seed_assembly(engine)

    try:
        engine.add_assembly_to_revision(
            revision_id=revision_id,
            assembly_version_id=version_id,
            parent_quantity=1,
            labor_rate_set_id="labor_rates:v1",
            commercial_state={},
            actor="tester",
        )
        assert False, "Expected rollback when product cost selection fails"
    except ValueError as exc:
        assert "Missing required product cost selection" in str(exc)

    revision = engine.state["revisions"][revision_id]
    assert revision["line_items"] == []


def test_refresh_assembly_labor_rates_preview_and_apply() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-labor-refresh",
        name="Assembly Estimate",
        created_by="tester",
        estimate_id="estimate:project-labor-refresh:main",
    )
    revision_id = created["revision"]["revision_id"]
    version_id = _seed_assembly(engine)

    inserted = engine.add_assembly_to_revision(
        revision_id=revision_id,
        assembly_version_id=version_id,
        parent_quantity=1,
        labor_rate_set_id="labor_rates:v1",
        commercial_state=_commercial_state(),
        actor="tester",
    )
    expansion_run_id = inserted["expansion_run_id"]

    assembly = AssemblyExpansionService(
        state=dict(engine.state.get("assembly_state") or {})
    )
    assembly.create_labor_rate_set(
        labor_rate_set_id="labor_rates:v2",
        version_label="v2",
        effective_date="2026-02-01",
        created_by="tester",
    )
    assembly.add_labor_rate_record(
        labor_rate_set_id="labor_rates:v2",
        record={
            "labor_category": "installation",
            "unit_basis": "hours",
            "straight_time_rate": 200,
            "burden_rate": 50,
        },
    )
    assembly.activate_labor_rate_set(labor_rate_set_id="labor_rates:v2")
    engine.state["assembly_state"] = assembly.to_dict()

    preview = engine.refresh_assembly_labor_rates(
        revision_id=revision_id,
        expansion_run_id=expansion_run_id,
        labor_rate_set_id="labor_rates:v2",
        actor="tester",
    )
    assert preview["kind"] == "labor_rate_refresh"
    assert preview["updates"]

    applied = engine.apply_assembly_refresh(
        refresh_id=preview["refresh_id"],
        actor="tester",
        accept=True,
    )
    assert applied["accepted"] is True


def test_override_requires_reason_and_tracks_audit_metadata() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-override",
        name="Assembly Estimate",
        created_by="tester",
        estimate_id="estimate:project-override:main",
    )
    revision_id = created["revision"]["revision_id"]
    version_id = _seed_assembly(engine)
    inserted = engine.add_assembly_to_revision(
        revision_id=revision_id,
        assembly_version_id=version_id,
        parent_quantity=1,
        labor_rate_set_id="labor_rates:v1",
        commercial_state=_commercial_state(),
        actor="tester",
    )
    generated_product = next(
        item
        for item in inserted["created_lines"]
        if str(item.get("line_role") or "") == "generated_product_child"
    )
    line_id = generated_product["line_item_id"]

    try:
        engine.override_assembly_component(
            revision_id=revision_id,
            line_item_id=line_id,
            actor="tester",
            reason=" ",
            adjusted_quantity=3,
        )
        assert False, "Expected override to require reason"
    except ValueError as exc:
        assert "required" in str(exc)

    updated = engine.override_assembly_component(
        revision_id=revision_id,
        line_item_id=line_id,
        actor="tester",
        reason="Field condition",
        adjusted_quantity=3,
    )
    assert float(updated["requested_quantity"]) == 3.0
    record = engine.inspect_assembly_provenance(
        revision_id=revision_id,
        parent_line_item_id=inserted["parent_line"]["line_item_id"],
    )
    matching_line = next(
        item for item in record["lines"] if item.get("line_item_id") == line_id
    )
    assert matching_line["manual_adjustment_metadata"]


def test_add_assembly_to_locked_revision_clones_before_mutation() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-locked-assembly",
        name="Assembly Estimate",
        created_by="tester",
        estimate_id="estimate:project-locked-assembly:main",
    )
    locked_revision_id = created["revision"]["revision_id"]
    version_id = _seed_assembly(engine)

    engine.lock_revision(revision_id=locked_revision_id, actor="tester")
    inserted = engine.add_assembly_to_revision(
        revision_id=locked_revision_id,
        assembly_version_id=version_id,
        parent_quantity=1,
        labor_rate_set_id="labor_rates:v1",
        commercial_state=_commercial_state(),
        actor="tester",
    )

    working_revision_id = inserted["working_revision_id"]
    assert working_revision_id != locked_revision_id
    assert engine.state["revisions"][locked_revision_id]["state"] in {
        "locked",
        "superseded",
    }
    assert engine.state["revisions"][locked_revision_id]["line_items"] == []
    assert engine.state["revisions"][working_revision_id]["line_items"]


def test_apply_assembly_refresh_requires_explicit_acceptance() -> None:
    engine = EstimateEngineService()
    created = engine.create_estimate(
        project_id="project-refresh-reject",
        name="Assembly Estimate",
        created_by="tester",
        estimate_id="estimate:project-refresh-reject:main",
    )
    revision_id = created["revision"]["revision_id"]
    version_id = _seed_assembly(engine)

    inserted = engine.add_assembly_to_revision(
        revision_id=revision_id,
        assembly_version_id=version_id,
        parent_quantity=1,
        labor_rate_set_id="labor_rates:v1",
        commercial_state=_commercial_state(),
        actor="tester",
    )
    expansion_run_id = inserted["expansion_run_id"]
    labor_line = next(
        item
        for item in inserted["created_lines"]
        if str(item.get("line_role") or "") == "generated_labor_child"
    )
    prior_line_state = next(
        item
        for item in engine.state["revisions"][revision_id]["line_items"]
        if str(item.get("line_item_id") or "")
        == str(labor_line.get("line_item_id") or "")
    )
    prior_snapshot_id = str(prior_line_state.get("labor_snapshot_id") or "")

    assembly = AssemblyExpansionService(
        state=dict(engine.state.get("assembly_state") or {})
    )
    assembly.create_labor_rate_set(
        labor_rate_set_id="labor_rates:v2",
        version_label="v2",
        effective_date="2026-02-01",
        created_by="tester",
    )
    assembly.add_labor_rate_record(
        labor_rate_set_id="labor_rates:v2",
        record={
            "labor_category": "installation",
            "unit_basis": "hours",
            "straight_time_rate": 200,
            "burden_rate": 50,
        },
    )
    assembly.activate_labor_rate_set(labor_rate_set_id="labor_rates:v2")
    engine.state["assembly_state"] = assembly.to_dict()

    preview = engine.refresh_assembly_labor_rates(
        revision_id=revision_id,
        expansion_run_id=expansion_run_id,
        labor_rate_set_id="labor_rates:v2",
        actor="tester",
    )
    resolved = engine.apply_assembly_refresh(
        refresh_id=preview["refresh_id"],
        actor="tester",
        accept=False,
    )

    assert resolved["accepted"] is False
    post_revision = engine.state["revisions"][revision_id]
    post_labor_line = next(
        item
        for item in post_revision["line_items"]
        if str(item.get("line_item_id") or "")
        == str(labor_line.get("line_item_id") or "")
    )
    assert str(post_labor_line.get("labor_snapshot_id") or "") == prior_snapshot_id

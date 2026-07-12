from datetime import date

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

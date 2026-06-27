from atlas_core.domain import EquipmentCategory
from atlas_core.sample_data import build_maw_seed_data
from atlas_core.services import EstimateWorkflowService


def test_seed_data_contains_all_six_keys():
    seed = build_maw_seed_data()

    assert set(seed) == {
        "buildings",
        "rooms",
        "spaces",
        "scenes",
        "systems",
        "equipment",
    }


def test_seed_data_contains_at_least_four_rooms():
    seed = build_maw_seed_data()

    assert len(seed["rooms"]) >= 4


def test_seed_data_contains_speaker_equipment():
    seed = build_maw_seed_data()

    assert any(
        equipment.category is EquipmentCategory.SPEAKER
        for equipment in seed["equipment"]
    )


def test_seed_data_uses_preferred_projector_and_display_manufacturers():
    seed = build_maw_seed_data()
    equipment_by_id = {
        equipment.equipment_id: equipment
        for equipment in seed["equipment"]
    }

    assert equipment_by_id["maw-recital-projector"].manufacturer == "Epson"
    assert equipment_by_id["maw-recital-projector"].model == "PowerLite L735U"
    assert equipment_by_id["maw-classroom-display"].manufacturer == "Sony"
    assert equipment_by_id["maw-lobby-display"].manufacturer == "Sony"


def test_seed_data_creates_resolver_placeholders_in_estimate_workflow():
    seed = build_maw_seed_data()

    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        buildings=seed["buildings"],
        rooms=seed["rooms"],
        spaces=seed["spaces"],
        scenes=seed["scenes"],
        systems=seed["systems"],
        equipment=seed["equipment"],
    )

    assert result.placeholder_equipment_count >= 1
    assert any(row.equipment_category == "amplifier" for row in result.rows)


def test_seed_placeholder_rows_keep_source_context():
    seed = build_maw_seed_data()

    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        buildings=seed["buildings"],
        rooms=seed["rooms"],
        spaces=seed["spaces"],
        scenes=seed["scenes"],
        systems=seed["systems"],
        equipment=seed["equipment"],
    )
    placeholder_rows = [
        row for row in result.rows if row.status == "placeholder"
    ]

    assert placeholder_rows
    assert all(row.system_id for row in placeholder_rows)
    assert all(row.room_id for row in placeholder_rows)
    assert all(
        row.building_name == "MAW Music Education Center"
        for row in placeholder_rows
    )

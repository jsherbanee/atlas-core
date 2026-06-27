from atlas_core.domain import (
    Building,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    Room,
    SystemCategory,
)
from atlas_core.rules import ResolutionAction
from atlas_core.services import EstimateWorkflowService


def test_returns_rows_for_original_equipment():
    equipment = Equipment(
        equipment_id="eq-display",
        description="Display",
        category=EquipmentCategory.DISPLAY,
    )

    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        equipment=[equipment],
    )

    assert len(result.rows) == 1
    assert result.rows[0].equipment_id == "eq-display"
    assert result.rows[0].description == "Display"
    assert result.placeholder_equipment_count == 0


def test_creates_placeholder_equipment_for_speaker_without_amplifier():
    speaker = Equipment(
        equipment_id="eq-speaker",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
        system_id="sys-001",
    )

    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        equipment=[speaker],
    )

    assert result.placeholder_equipment_count == 1


def test_includes_placeholder_equipment_in_matrix_rows():
    speaker = Equipment(
        equipment_id="eq-speaker",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
        system_id="sys-001",
    )

    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        equipment=[speaker],
    )

    assert [row.equipment_id for row in result.rows] == [
        "eq-speaker",
        "placeholder-rule-001-eq-speaker",
    ]
    assert result.rows[1].equipment_category == "amplifier"
    assert result.rows[1].status == "placeholder"
    assert result.rows[1].review_required is True


def test_returns_resolver_resolutions():
    drapery = Equipment(
        equipment_id="eq-drapery",
        description="Motorized Drapery",
        category=EquipmentCategory.DRAPERY,
    )

    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        equipment=[drapery],
    )

    assert len(result.resolutions) == 1
    assert result.resolutions[0].rule_id == "RULE-004"
    assert result.resolutions[0].action is ResolutionAction.MARK_FOR_REVIEW
    assert result.rows[0].review_required is True
    assert result.rows[0].assumptions == (
        "Drapery scope requires review of track, hardware, infrastructure, "
        "support, and site conditions."
    )


def test_to_dict_serializes_rows_and_resolutions_cleanly():
    building = Building(
        building_id="bldg-001",
        name="Main Building",
        project_id="project-001",
    )
    room = Room(
        room_id="room-001",
        name="Classroom 101",
        building_id="bldg-001",
    )
    system = IntegratedSystem(
        system_id="sys-001",
        name="Classroom Audio",
        category=SystemCategory.AUDIO,
        room_id="room-001",
    )
    speaker = Equipment(
        equipment_id="eq-speaker",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
        system_id="sys-001",
    )

    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        buildings=[building],
        rooms=[room],
        systems=[system],
        equipment=[speaker],
    )
    data = result.to_dict()

    assert data["rows"][0]["equipment_id"] == "eq-speaker"
    assert data["rows"][0]["building_name"] == "Main Building"
    assert data["resolutions"][0]["action"] == "add_placeholder"
    assert data["resolutions"][0]["rule_id"] == "RULE-001"
    assert data["placeholder_equipment_count"] == 1

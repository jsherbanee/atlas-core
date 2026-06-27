from atlas_core.domain import (
    Building,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    Manufacturer,
    ManufacturerDiscipline,
    ManufacturerTier,
    Room,
    SystemCategory,
)
from atlas_core.registry import ManufacturerRegistry
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
    assert result.manufacturer_review_issues == []
    assert result.review_report == []


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
    assert data["manufacturer_review_issues"] == []
    assert data["review_report"][0]["source"] == "resolver"
    assert data["review_report"][0]["target_id"] == "eq-speaker"
    assert data["review_report"][0]["rule_id"] == "RULE-001"


def test_workflow_still_works_without_manufacturer_registry():
    equipment = Equipment(
        equipment_id="eq-display",
        description="Display",
        category=EquipmentCategory.DISPLAY,
        manufacturer="Unknown",
    )

    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        equipment=[equipment],
    )

    assert len(result.rows) == 1
    assert result.manufacturer_review_issues == []


def test_workflow_returns_manufacturer_review_issue_for_unregistered_manufacturer():
    equipment = Equipment(
        equipment_id="eq-display",
        description="Display",
        category=EquipmentCategory.DISPLAY,
        manufacturer="Unknown",
    )

    result = EstimateWorkflowService(
        manufacturer_registry=ManufacturerRegistry()
    ).build_equipment_matrix_with_resolutions(equipment=[equipment])

    assert len(result.manufacturer_review_issues) == 1
    assert result.manufacturer_review_issues[0].equipment_id == "eq-display"
    assert result.manufacturer_review_issues[0].manufacturer == "Unknown"
    assert result.manufacturer_review_issues[0].message == (
        "Manufacturer is not registered and requires estimator review."
    )


def test_workflow_returns_no_issue_for_registered_preferred_manufacturer():
    equipment = Equipment(
        equipment_id="eq-display",
        description="Display",
        category=EquipmentCategory.DISPLAY,
        manufacturer="QSC",
    )
    registry = ManufacturerRegistry(
        [
            Manufacturer(
                manufacturer_id="qsc",
                name="QSC",
                discipline=ManufacturerDiscipline.CONTROL,
                tier=ManufacturerTier.PREFERRED,
            )
        ]
    )

    result = EstimateWorkflowService(
        manufacturer_registry=registry
    ).build_equipment_matrix_with_resolutions(equipment=[equipment])

    assert result.manufacturer_review_issues == []


def test_workflow_reviews_placeholder_equipment_manufacturer():
    projector = Equipment(
        equipment_id="eq-projector",
        description="Projector",
        category=EquipmentCategory.PROJECTOR,
        manufacturer="Epson",
        room_id="room-001",
    )
    registry = ManufacturerRegistry(
        [
            Manufacturer(
                manufacturer_id="epson",
                name="Epson",
                discipline=ManufacturerDiscipline.PROJECTION,
                tier=ManufacturerTier.PREFERRED,
            )
        ]
    )

    result = EstimateWorkflowService(
        manufacturer_registry=registry
    ).build_equipment_matrix_with_resolutions(equipment=[projector])

    assert len(result.manufacturer_review_issues) == 1
    assert result.manufacturer_review_issues[0].equipment_id == (
        "placeholder-rule-003-eq-projector"
    )
    assert result.manufacturer_review_issues[0].manufacturer == "Chief"


def test_workflow_includes_review_report_items_for_resolver_resolutions():
    drapery = Equipment(
        equipment_id="eq-drapery",
        description="Motorized Drapery",
        category=EquipmentCategory.DRAPERY,
    )

    result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        equipment=[drapery],
    )

    assert len(result.review_report) == 1
    assert result.review_report[0].source == "resolver"
    assert result.review_report[0].target_id == "eq-drapery"
    assert result.review_report[0].rule_id == "RULE-004"


def test_workflow_includes_manufacturer_review_issues_in_review_report():
    equipment = Equipment(
        equipment_id="eq-display",
        description="Display",
        category=EquipmentCategory.DISPLAY,
        manufacturer="Unknown",
    )

    result = EstimateWorkflowService(
        manufacturer_registry=ManufacturerRegistry()
    ).build_equipment_matrix_with_resolutions(equipment=[equipment])

    assert len(result.review_report) == 1
    assert result.review_report[0].source == "manufacturer_registry"
    assert result.review_report[0].target_id == "eq-display"
    assert result.review_report[0].manufacturer == "Unknown"

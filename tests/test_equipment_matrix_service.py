from atlas_core.domain import (
    Building,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    Room,
    SystemCategory,
)
from atlas_core.services import EquipmentMatrixService


def test_creating_one_equipment_matrix_row_from_linked_records():
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
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
        manufacturer="QSC",
        model="AD-C6T",
        system_id="sys-001",
        labor_template="speaker-ceiling",
        drawing_reference="A701",
        specification_reference="27 41 16",
        confidence=0.84,
    )
    equipment.set_pricing(100.0, 150.0)

    rows = EquipmentMatrixService(
        buildings=[building],
        rooms=[room],
        systems=[system],
        equipment=[equipment],
    ).build_rows()

    assert rows == [
        {
            "project_building_id": "bldg-001",
            "building_name": "Main Building",
            "room_id": "room-001",
            "room_name": "Classroom 101",
            "space_id": "",
            "space_name": "",
            "scene_id": "",
            "scene_name": "",
            "system_id": "sys-001",
            "system_name": "Classroom Audio",
            "system_category": "audio",
            "equipment_id": "eq-001",
            "description": "Ceiling Speaker",
            "equipment_category": "speaker",
            "manufacturer": "QSC",
            "model": "AD-C6T",
            "quantity": 1,
            "status": "priced",
            "budget_cost": 100.0,
            "sell_price": 150.0,
            "labor_template": "speaker-ceiling",
            "drawing_reference": "A701",
            "specification_reference": "27 41 16",
            "confidence": 0.84,
            "review_required": False,
            "assumptions": "",
        }
    ]


def test_handling_missing_related_records_without_error():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
        system_id="missing-system",
    )

    rows = EquipmentMatrixService(equipment=[equipment]).build_rows()

    assert rows[0]["system_id"] == "missing-system"
    assert rows[0]["system_name"] == ""
    assert rows[0]["room_id"] == ""
    assert rows[0]["building_name"] == ""


def test_joining_assumptions():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
    )
    equipment.add_assumption("Existing cabling can be reused.")
    equipment.add_assumption("Verify ceiling type.")

    rows = EquipmentMatrixService(equipment=[equipment]).build_rows()

    assert rows[0]["assumptions"] == (
        "Existing cabling can be reused.; Verify ceiling type."
    )


def test_returning_empty_list_when_no_equipment_exists():
    assert EquipmentMatrixService().build_rows() == []

from typing import Any

from atlas_core.domain import DeviceSchedule, DeviceScheduleItem, EquipmentCategory
from atlas_core.services.device_schedule_equipment_service import (
    DeviceScheduleEquipmentService,
)


def make_item(**kwargs: Any) -> DeviceScheduleItem:
    base: dict[str, Any] = {
        "item_id": "sched-1-spk-1",
        "tag": "SPK-1",
        "description": "Ceiling loudspeaker",
    }
    base.update(kwargs)
    return DeviceScheduleItem(**base)


def test_converts_schedule_item_to_equipment():
    item = make_item()

    equipment = DeviceScheduleEquipmentService().equipment_from_item(item)

    assert equipment.equipment_id == "equipment-sched-1-spk-1"
    assert equipment.description == item.description


def test_carries_quantity():
    item = make_item(quantity=3)

    equipment = DeviceScheduleEquipmentService().equipment_from_item(item)

    assert equipment.quantity == 3


def test_carries_manufacturer_and_model():
    item = make_item(manufacturer="Acme", model="X100")

    equipment = DeviceScheduleEquipmentService().equipment_from_item(item)

    assert equipment.manufacturer == "Acme"
    assert equipment.model == "X100"


def test_carries_drawing_and_specification_references():
    item = make_item(drawing_reference="AV1.01", specification_reference="27 41 16")

    equipment = DeviceScheduleEquipmentService().equipment_from_item(item)

    assert equipment.drawing_reference == "AV1.01"
    assert equipment.specification_reference == "27 41 16"


def test_adds_schedule_assumption():
    item = make_item(tag="SPK-10")

    equipment = DeviceScheduleEquipmentService().equipment_from_item(item)

    assert equipment.assumptions == ["Created from device schedule item SPK-10."]


def test_carries_item_notes_as_assumptions():
    item = make_item(notes=["Install near stage", "Coordinate with architect"])

    equipment = DeviceScheduleEquipmentService().equipment_from_item(item)

    assert equipment.assumptions == [
        "Created from device schedule item SPK-1.",
        "Install near stage",
        "Coordinate with architect",
    ]


def test_infers_speaker_category():
    item = make_item(description="Main loudspeaker")

    equipment = DeviceScheduleEquipmentService().equipment_from_item(item)

    assert equipment.category is EquipmentCategory.SPEAKER


def test_infers_display_category():
    item = make_item(description="Lobby monitor")

    equipment = DeviceScheduleEquipmentService().equipment_from_item(item)

    assert equipment.category is EquipmentCategory.DISPLAY


def test_infers_projector_category():
    item = make_item(description="Laser projector")

    equipment = DeviceScheduleEquipmentService().equipment_from_item(item)

    assert equipment.category is EquipmentCategory.PROJECTOR


def test_infers_unknown_category():
    item = make_item(description="Custom widget")

    equipment = DeviceScheduleEquipmentService().equipment_from_item(item)

    assert equipment.category is EquipmentCategory.UNKNOWN


def test_converts_full_schedule_preserving_item_count():
    schedule = DeviceSchedule(
        schedule_id="sched-1",
        items=[
            make_item(item_id="sched-1-spk-1", tag="SPK-1", description="Speaker"),
            make_item(item_id="sched-1-dsp-1", tag="DSP-1", description="Processor"),
            make_item(item_id="sched-1-proj-1", tag="PROJ-1", description="Projector"),
        ],
    )

    equipment = DeviceScheduleEquipmentService().equipment_from_schedule(schedule)

    assert len(equipment) == 3

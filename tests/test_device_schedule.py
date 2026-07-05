import pytest

from atlas_core.domain import DeviceSchedule, DeviceScheduleItem


def test_creating_valid_device_schedule_item():
    item = DeviceScheduleItem(
        item_id="item-1",
        tag="TAG-1",
        description="Main loudspeaker",
        quantity=2,
        manufacturer="Acme",
        model="X100",
        room_name="Main Lobby",
        system_name="Audio",
        drawing_reference="AV1.01",
        specification_reference="27 41 16",
        notes=["Install near stage"],
        confidence=0.9,
    )

    assert item.item_id == "item-1"
    assert item.tag == "TAG-1"
    assert item.quantity == 2
    assert item.notes == ["Install near stage"]


def test_rejecting_blank_tag():
    with pytest.raises(ValueError, match="tag cannot be blank"):
        DeviceScheduleItem(item_id="item-1", tag=" ", description="desc")


def test_rejecting_invalid_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        DeviceScheduleItem(
            item_id="item-1", tag="TAG-1", description="desc", quantity=0
        )


def test_adding_item_to_schedule():
    schedule = DeviceSchedule(schedule_id="sched-1")
    item = DeviceScheduleItem(item_id="item-1", tag="TAG-1", description="desc")
    schedule.add_item(item)

    assert schedule.item_count() == 1


def test_item_count():
    schedule = DeviceSchedule(schedule_id="sched-1", items=[])
    assert schedule.item_count() == 0


def test_adding_notes():
    item = DeviceScheduleItem(item_id="item-1", tag="TAG-1", description="desc")
    item.add_note(" Check wiring ")
    assert item.notes == ["Check wiring"]

    schedule = DeviceSchedule(schedule_id="sched-1")
    schedule.add_note(" Review schedule ")
    assert schedule.notes == ["Review schedule"]


def test_to_dict_output():
    item = DeviceScheduleItem(item_id="item-1", tag="TAG-1", description="desc")
    schedule = DeviceSchedule(schedule_id="sched-1", items=[item], notes=["Note"])

    d = schedule.to_dict()
    assert d["schedule_id"] == "sched-1"
    assert d["items"] == [item.to_dict()]
    assert d["notes"] == ["Note"]

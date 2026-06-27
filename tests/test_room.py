import pytest

from atlas_core.domain import Room, RoomType


def test_creating_valid_room():
    room = Room(
        room_id=" room-001 ",
        name=" Classroom 101 ",
        building_id=" bldg-001 ",
    )

    assert room.room_id == "room-001"
    assert room.name == "Classroom 101"
    assert room.building_id == "bldg-001"
    assert room.room_type is RoomType.UNKNOWN
    assert room.confidence == 0.75


def test_accepting_string_room_type():
    room = Room(
        room_id="room-001",
        name="Classroom 101",
        building_id="bldg-001",
        room_type="classroom",
    )

    assert room.room_type is RoomType.CLASSROOM


def test_rejecting_blank_name():
    with pytest.raises(ValueError, match="name cannot be blank"):
        Room(
            room_id="room-001",
            name=" ",
            building_id="bldg-001",
        )


def test_rejecting_blank_building_id():
    with pytest.raises(ValueError, match="building_id cannot be blank"):
        Room(
            room_id="room-001",
            name="Classroom 101",
            building_id=" ",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        Room(
            room_id="room-001",
            name="Classroom 101",
            building_id="bldg-001",
            confidence=1.1,
        )


def test_adding_space_ids():
    room = Room(
        room_id="room-001",
        name="Classroom 101",
        building_id="bldg-001",
    )

    room.add_space(" space-001 ")
    room.add_space("space-002")

    assert room.space_ids == ["space-001", "space-002"]


def test_adding_system_ids():
    room = Room(
        room_id="room-001",
        name="Classroom 101",
        building_id="bldg-001",
    )

    room.add_system(" sys-001 ")
    room.add_system("sys-002")

    assert room.system_ids == ["sys-001", "sys-002"]


def test_adding_notes():
    room = Room(
        room_id="room-001",
        name="Classroom 101",
        building_id="bldg-001",
    )

    room.add_note(" Verify owner furniture layout. ")
    room.add_note("Coordinate ceiling access.")

    assert room.notes == [
        "Verify owner furniture layout.",
        "Coordinate ceiling access.",
    ]


def test_to_dict_output():
    room = Room(
        room_id="room-001",
        name="Classroom 101",
        building_id="bldg-001",
        room_number="101",
        room_type=RoomType.CLASSROOM,
        confidence=0.88,
    )
    room.add_space("space-001")
    room.add_system("sys-001")
    room.add_note("Verify owner furniture layout.")

    assert room.to_dict() == {
        "room_id": "room-001",
        "name": "Classroom 101",
        "building_id": "bldg-001",
        "room_number": "101",
        "room_type": "classroom",
        "space_ids": ["space-001"],
        "system_ids": ["sys-001"],
        "notes": ["Verify owner furniture layout."],
        "confidence": 0.88,
    }

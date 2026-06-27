import pytest

from atlas_core.domain import Space, SpaceType


def test_creating_valid_space():
    space = Space(
        space_id=" space-001 ",
        name=" Stage Left ",
        room_id=" room-001 ",
    )

    assert space.space_id == "space-001"
    assert space.name == "Stage Left"
    assert space.room_id == "room-001"
    assert space.space_type is SpaceType.UNKNOWN
    assert space.confidence == 0.75


def test_accepting_string_space_type():
    space = Space(
        space_id="space-001",
        name="Stage Left",
        room_id="room-001",
        space_type="stage",
    )

    assert space.space_type is SpaceType.STAGE


def test_rejecting_blank_name():
    with pytest.raises(ValueError, match="name cannot be blank"):
        Space(
            space_id="space-001",
            name=" ",
            room_id="room-001",
        )


def test_rejecting_blank_room_id():
    with pytest.raises(ValueError, match="room_id cannot be blank"):
        Space(
            space_id="space-001",
            name="Stage Left",
            room_id=" ",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        Space(
            space_id="space-001",
            name="Stage Left",
            room_id="room-001",
            confidence=1.1,
        )


def test_adding_scene_ids():
    space = Space(
        space_id="space-001",
        name="Stage Left",
        room_id="room-001",
    )

    space.add_scene(" scene-001 ")
    space.add_scene("scene-002")

    assert space.scene_ids == ["scene-001", "scene-002"]


def test_adding_equipment_ids():
    space = Space(
        space_id="space-001",
        name="Stage Left",
        room_id="room-001",
    )

    space.add_equipment(" eq-001 ")
    space.add_equipment("eq-002")

    assert space.equipment_ids == ["eq-001", "eq-002"]


def test_adding_notes():
    space = Space(
        space_id="space-001",
        name="Stage Left",
        room_id="room-001",
    )

    space.add_note(" Confirm rigging access. ")
    space.add_note("Coordinate with scenic drawings.")

    assert space.notes == [
        "Confirm rigging access.",
        "Coordinate with scenic drawings.",
    ]


def test_to_dict_output():
    space = Space(
        space_id="space-001",
        name="Stage Left",
        room_id="room-001",
        space_type=SpaceType.STAGE,
        confidence=0.89,
    )
    space.add_scene("scene-001")
    space.add_equipment("eq-001")
    space.add_note("Confirm rigging access.")

    assert space.to_dict() == {
        "space_id": "space-001",
        "name": "Stage Left",
        "room_id": "room-001",
        "space_type": "stage",
        "scene_ids": ["scene-001"],
        "equipment_ids": ["eq-001"],
        "notes": ["Confirm rigging access."],
        "confidence": 0.89,
    }

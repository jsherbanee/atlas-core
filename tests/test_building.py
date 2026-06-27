import pytest

from atlas_core.domain import Building, BuildingType


def test_creating_valid_building():
    building = Building(
        building_id=" bldg-001 ",
        name=" Main Building ",
        project_id=" project-001 ",
    )

    assert building.building_id == "bldg-001"
    assert building.name == "Main Building"
    assert building.project_id == "project-001"
    assert building.building_type is BuildingType.UNKNOWN
    assert building.confidence == 0.75


def test_accepting_string_building_type():
    building = Building(
        building_id="bldg-001",
        name="Main Building",
        project_id="project-001",
        building_type="education",
    )

    assert building.building_type is BuildingType.EDUCATION


def test_rejecting_blank_name():
    with pytest.raises(ValueError, match="name cannot be blank"):
        Building(
            building_id="bldg-001",
            name=" ",
            project_id="project-001",
        )


def test_rejecting_blank_project_id():
    with pytest.raises(ValueError, match="project_id cannot be blank"):
        Building(
            building_id="bldg-001",
            name="Main Building",
            project_id=" ",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        Building(
            building_id="bldg-001",
            name="Main Building",
            project_id="project-001",
            confidence=1.1,
        )


def test_adding_room_ids():
    building = Building(
        building_id="bldg-001",
        name="Main Building",
        project_id="project-001",
    )

    building.add_room(" room-001 ")
    building.add_room("room-002")

    assert building.room_ids == ["room-001", "room-002"]


def test_adding_notes():
    building = Building(
        building_id="bldg-001",
        name="Main Building",
        project_id="project-001",
    )

    building.add_note(" Coordinate after-hours access. ")
    building.add_note("Verify MDF location.")

    assert building.notes == [
        "Coordinate after-hours access.",
        "Verify MDF location.",
    ]


def test_to_dict_output():
    building = Building(
        building_id="bldg-001",
        name="Main Building",
        project_id="project-001",
        building_type=BuildingType.EDUCATION,
        address="123 Atlas Way",
        confidence=0.86,
    )
    building.add_room("room-001")
    building.add_note("Coordinate after-hours access.")

    assert building.to_dict() == {
        "building_id": "bldg-001",
        "name": "Main Building",
        "project_id": "project-001",
        "building_type": "education",
        "address": "123 Atlas Way",
        "room_ids": ["room-001"],
        "notes": ["Coordinate after-hours access."],
        "confidence": 0.86,
    }

import pytest

from atlas_core.domain import Scene, SceneType


def test_creating_valid_scene():
    scene = Scene(
        scene_id=" scene-001 ",
        name=" Lecture Mode ",
        space_id=" space-001 ",
    )

    assert scene.scene_id == "scene-001"
    assert scene.name == "Lecture Mode"
    assert scene.space_id == "space-001"
    assert scene.scene_type is SceneType.UNKNOWN
    assert scene.confidence == 0.75


def test_accepting_string_scene_type():
    scene = Scene(
        scene_id="scene-001",
        name="Lecture Mode",
        space_id="space-001",
        scene_type="lecture",
    )

    assert scene.scene_type is SceneType.LECTURE


def test_rejecting_blank_name():
    with pytest.raises(ValueError, match="name cannot be blank"):
        Scene(
            scene_id="scene-001",
            name=" ",
            space_id="space-001",
        )


def test_rejecting_blank_space_id():
    with pytest.raises(ValueError, match="space_id cannot be blank"):
        Scene(
            scene_id="scene-001",
            name="Lecture Mode",
            space_id=" ",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        Scene(
            scene_id="scene-001",
            name="Lecture Mode",
            space_id="space-001",
            confidence=1.1,
        )


def test_adding_system_ids():
    scene = Scene(
        scene_id="scene-001",
        name="Lecture Mode",
        space_id="space-001",
    )

    scene.add_system(" sys-001 ")
    scene.add_system("sys-002")

    assert scene.system_ids == ["sys-001", "sys-002"]


def test_adding_equipment_ids():
    scene = Scene(
        scene_id="scene-001",
        name="Lecture Mode",
        space_id="space-001",
    )

    scene.add_equipment(" eq-001 ")
    scene.add_equipment("eq-002")

    assert scene.equipment_ids == ["eq-001", "eq-002"]


def test_adding_control_notes():
    scene = Scene(
        scene_id="scene-001",
        name="Lecture Mode",
        space_id="space-001",
    )

    scene.add_control_note(" Recall lectern preset. ")
    scene.add_control_note("Mute house music.")

    assert scene.control_notes == [
        "Recall lectern preset.",
        "Mute house music.",
    ]


def test_adding_commissioning_notes():
    scene = Scene(
        scene_id="scene-001",
        name="Lecture Mode",
        space_id="space-001",
    )

    scene.add_commissioning_note(" Verify projector warmup timing. ")
    scene.add_commissioning_note("Confirm DSP preset levels.")

    assert scene.commissioning_notes == [
        "Verify projector warmup timing.",
        "Confirm DSP preset levels.",
    ]


def test_to_dict_output():
    scene = Scene(
        scene_id="scene-001",
        name="Lecture Mode",
        space_id="space-001",
        scene_type=SceneType.LECTURE,
        confidence=0.91,
    )
    scene.add_system("sys-001")
    scene.add_equipment("eq-001")
    scene.add_control_note("Recall lectern preset.")
    scene.add_commissioning_note("Verify projector warmup timing.")

    assert scene.to_dict() == {
        "scene_id": "scene-001",
        "name": "Lecture Mode",
        "space_id": "space-001",
        "scene_type": "lecture",
        "system_ids": ["sys-001"],
        "equipment_ids": ["eq-001"],
        "control_notes": ["Recall lectern preset."],
        "commissioning_notes": ["Verify projector warmup timing."],
        "confidence": 0.91,
    }

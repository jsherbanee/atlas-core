import pytest

from atlas_core.domain import IntegratedSystem, SystemCategory, SystemComplexity


def test_creating_valid_system():
    system = IntegratedSystem(
        system_id=" sys-001 ",
        name=" Conference Audio ",
        category=SystemCategory.AUDIO,
    )

    assert system.system_id == "sys-001"
    assert system.name == "Conference Audio"
    assert system.category is SystemCategory.AUDIO
    assert system.complexity is SystemComplexity.MEDIUM
    assert system.confidence == 0.75
    assert not system.review_required


def test_accepting_string_category_and_complexity():
    system = IntegratedSystem(
        system_id="sys-001",
        name="Lobby Video Wall",
        category="display",
        complexity="very_high",
    )

    assert system.category is SystemCategory.DISPLAY
    assert system.complexity is SystemComplexity.VERY_HIGH


def test_rejecting_blank_system_name():
    with pytest.raises(ValueError, match="name cannot be blank"):
        IntegratedSystem(system_id="sys-001", name=" ", category=SystemCategory.AUDIO)


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        IntegratedSystem(
            system_id="sys-001",
            name="Conference Audio",
            category=SystemCategory.AUDIO,
            confidence=1.1,
        )


def test_adding_manufacturers():
    system = IntegratedSystem(
        system_id="sys-001",
        name="Conference Audio",
        category=SystemCategory.AUDIO,
    )

    system.add_manufacturer(" Q-SYS ")
    system.add_manufacturer("Shure")

    assert system.manufacturers == ["Q-SYS", "Shure"]


def test_adding_equipment_ids():
    system = IntegratedSystem(
        system_id="sys-001",
        name="Conference Audio",
        category=SystemCategory.AUDIO,
    )

    system.add_equipment(" dsp-001 ")
    system.add_equipment("mic-001")

    assert system.equipment_ids == ["dsp-001", "mic-001"]


def test_adding_assumptions():
    system = IntegratedSystem(
        system_id="sys-001",
        name="Conference Audio",
        category=SystemCategory.AUDIO,
    )

    system.add_assumption(" Existing network supports Dante. ")
    system.add_assumption("Owner provides display mount.")

    assert system.assumptions == [
        "Existing network supports Dante.",
        "Owner provides display mount.",
    ]


def test_mark_for_review_without_reason():
    system = IntegratedSystem(
        system_id="sys-001",
        name="Conference Audio",
        category=SystemCategory.AUDIO,
    )

    system.mark_for_review()

    assert system.review_required
    assert system.assumptions == []


def test_mark_for_review_with_reason():
    system = IntegratedSystem(
        system_id="sys-001",
        name="Conference Audio",
        category=SystemCategory.AUDIO,
    )

    system.mark_for_review(" Verify ceiling speaker count. ")

    assert system.review_required
    assert system.assumptions == ["Verify ceiling speaker count."]


def test_to_dict_output():
    system = IntegratedSystem(
        system_id="sys-001",
        name="Conference Audio",
        category=SystemCategory.AUDIO,
        room_id="room-001",
        building_id="building-001",
        description="Audio reinforcement for conference room.",
        complexity=SystemComplexity.HIGH,
        confidence=0.82,
    )
    system.add_manufacturer("Q-SYS")
    system.add_equipment("dsp-001")
    system.add_assumption("Existing network supports Dante.")
    system.mark_for_review("Verify microphone quantity.")

    assert system.to_dict() == {
        "system_id": "sys-001",
        "name": "Conference Audio",
        "category": "audio",
        "room_id": "room-001",
        "building_id": "building-001",
        "description": "Audio reinforcement for conference room.",
        "complexity": "high",
        "manufacturers": ["Q-SYS"],
        "equipment_ids": ["dsp-001"],
        "assumptions": [
            "Existing network supports Dante.",
            "Verify microphone quantity.",
        ],
        "review_required": True,
        "confidence": 0.82,
    }

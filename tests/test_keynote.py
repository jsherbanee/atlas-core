import pytest

from atlas_core.domain import Keynote


def test_creating_valid_keynote():
    keynote = Keynote(
        keynote_id=" keynote-001 ",
        number=" 1 ",
        description=" Ceiling Speaker ",
        source_sheet_number=" AV1.01 ",
        equipment_category=" speaker ",
        system_category=" audio ",
        notes=[" Verify with reflected ceiling plan. "],
        confidence=0.9,
    )

    assert keynote.keynote_id == "keynote-001"
    assert keynote.number == "1"
    assert keynote.description == "Ceiling Speaker"
    assert keynote.source_sheet_number == "AV1.01"
    assert keynote.equipment_category == "speaker"
    assert keynote.system_category == "audio"
    assert keynote.notes == ["Verify with reflected ceiling plan."]
    assert keynote.confidence == 0.9


def test_rejecting_blank_number():
    with pytest.raises(ValueError, match="number cannot be blank"):
        Keynote(
            keynote_id="keynote-001",
            number=" ",
            description="Ceiling Speaker",
        )


def test_rejecting_blank_description():
    with pytest.raises(ValueError, match="description cannot be blank"):
        Keynote(
            keynote_id="keynote-001",
            number="1",
            description=" ",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        Keynote(
            keynote_id="keynote-001",
            number="1",
            description="Ceiling Speaker",
            confidence=1.1,
        )


def test_adding_notes():
    keynote = Keynote(
        keynote_id="keynote-001",
        number="1",
        description="Ceiling Speaker",
    )

    keynote.add_note(" Verify amplifier requirement. ")
    keynote.add_note("Coordinate with architect.")

    assert keynote.notes == [
        "Verify amplifier requirement.",
        "Coordinate with architect.",
    ]


def test_to_dict_output():
    keynote = Keynote(
        keynote_id="keynote-001",
        number="1",
        description="Ceiling Speaker",
        source_sheet_number="AV1.01",
        equipment_category="speaker",
        system_category="audio",
        notes=["Confirm mounting height."],
        confidence=0.85,
    )

    assert keynote.to_dict() == {
        "keynote_id": "keynote-001",
        "number": "1",
        "description": "Ceiling Speaker",
        "source_sheet_number": "AV1.01",
        "equipment_category": "speaker",
        "system_category": "audio",
        "notes": ["Confirm mounting height."],
        "confidence": 0.85,
    }

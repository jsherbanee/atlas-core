import pytest

from atlas_core.domain import DetailCallout


def test_creating_valid_detail_callout():
    callout = DetailCallout(
        callout_id=" callout-001 ",
        detail_number=" 2/A5.01 ",
        source_sheet_number=" AV1.01 ",
        target_sheet_number=" A5.01 ",
        description=" Detail reference for wall section ",
        system_category=" audio ",
        equipment_category=" speaker ",
        room_name=" Main Lobby ",
        notes=[" Verify mounting depth. "],
        confidence=0.9,
    )

    assert callout.callout_id == "callout-001"
    assert callout.detail_number == "2/A5.01"
    assert callout.source_sheet_number == "AV1.01"
    assert callout.target_sheet_number == "A5.01"
    assert callout.description == "Detail reference for wall section"
    assert callout.system_category == "audio"
    assert callout.equipment_category == "speaker"
    assert callout.room_name == "Main Lobby"
    assert callout.notes == ["Verify mounting depth."]
    assert callout.confidence == 0.9


def test_rejecting_blank_detail_number():
    with pytest.raises(ValueError, match="detail_number cannot be blank"):
        DetailCallout(
            callout_id="callout-001",
            detail_number=" ",
            source_sheet_number="AV1.01",
        )


def test_rejecting_blank_source_sheet_number():
    with pytest.raises(ValueError, match="source_sheet_number cannot be blank"):
        DetailCallout(
            callout_id="callout-001",
            detail_number="2/A5.01",
            source_sheet_number=" ",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        DetailCallout(
            callout_id="callout-001",
            detail_number="2/A5.01",
            source_sheet_number="AV1.01",
            confidence=1.2,
        )


def test_adding_notes():
    callout = DetailCallout(
        callout_id="callout-001",
        detail_number="2/A5.01",
        source_sheet_number="AV1.01",
    )

    callout.add_note(" Confirm dimension with architect. ")
    callout.add_note("Coordinate penetration clearance.")

    assert callout.notes == [
        "Confirm dimension with architect.",
        "Coordinate penetration clearance.",
    ]


def test_to_dict_output():
    callout = DetailCallout(
        callout_id="callout-001",
        detail_number="2/A5.01",
        source_sheet_number="AV1.01",
        target_sheet_number="A5.01",
        description="Wall section detail",
        system_category="audio",
        equipment_category="speaker",
        room_name="Main Lobby",
        notes=["Check structural backing."],
        confidence=0.85,
    )

    assert callout.to_dict() == {
        "callout_id": "callout-001",
        "detail_number": "2/A5.01",
        "source_sheet_number": "AV1.01",
        "target_sheet_number": "A5.01",
        "description": "Wall section detail",
        "system_category": "audio",
        "equipment_category": "speaker",
        "room_name": "Main Lobby",
        "notes": ["Check structural backing."],
        "confidence": 0.85,
    }

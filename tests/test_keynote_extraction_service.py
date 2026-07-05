from atlas_core.domain import DrawingSheet
from atlas_core.services.keynote_extraction_service import KeynoteExtractionService


def make_sheet(notes: list[str]) -> DrawingSheet:
    return DrawingSheet(
        sheet_id="av-101",
        sheet_number="AV 1.01",
        title="Audio Plan",
        notes=notes,
        confidence=0.9,
    )


def test_extracts_numbered_keynote_with_period() -> None:
    keynotes = KeynoteExtractionService().extract_from_sheet(
        make_sheet(["1. Ceiling loudspeaker"])
    )

    assert len(keynotes) == 1
    assert keynotes[0].number == "1"
    assert keynotes[0].description == "Ceiling loudspeaker"


def test_extracts_numbered_keynote_with_dash() -> None:
    keynotes = KeynoteExtractionService().extract_from_sheet(
        make_sheet(["2 - Projector location"])
    )

    assert len(keynotes) == 1
    assert keynotes[0].number == "2"
    assert keynotes[0].description == "Projector location"


def test_extracts_k_prefixed_keynote() -> None:
    keynotes = KeynoteExtractionService().extract_from_sheet(
        make_sheet(["K3: PTZ camera"])
    )

    assert len(keynotes) == 1
    assert keynotes[0].number == "K3"
    assert keynotes[0].description == "PTZ camera"
    assert keynotes[0].keynote_id == "av-1.01-keynote-k3"


def test_extracts_note_prefixed_keynote() -> None:
    keynotes = KeynoteExtractionService().extract_from_sheet(
        make_sheet(["NOTE 4: Equipment rack"])
    )

    assert len(keynotes) == 1
    assert keynotes[0].number == "4"
    assert keynotes[0].description == "Equipment rack"


def test_infers_speaker_category() -> None:
    keynotes = KeynoteExtractionService().extract_from_sheet(
        make_sheet(["1. Ceiling loudspeaker"])
    )

    assert keynotes[0].equipment_category == "speaker"


def test_infers_projector_category() -> None:
    keynotes = KeynoteExtractionService().extract_from_sheet(
        make_sheet(["2. Projector location"])
    )

    assert keynotes[0].equipment_category == "projector"


def test_infers_camera_category() -> None:
    keynotes = KeynoteExtractionService().extract_from_sheet(
        make_sheet(["K3: PTZ camera"])
    )

    assert keynotes[0].equipment_category == "camera"


def test_infers_system_category() -> None:
    keynotes = KeynoteExtractionService().extract_from_sheet(
        make_sheet(["5: Wireless microphone"])
    )

    assert keynotes[0].system_category == "audio"


def test_avoids_duplicates() -> None:
    keynotes = KeynoteExtractionService().extract_from_sheet(
        make_sheet(["1. Ceiling loudspeaker", "1 - Ceiling loudspeaker"])
    )

    assert len(keynotes) == 1
    assert keynotes[0].keynote_id == "av-1.01-keynote-1"


def test_returns_empty_list_when_no_keynotes_exist() -> None:
    keynotes = KeynoteExtractionService().extract_from_sheet(
        make_sheet(["General coordination note", "Provide spare conduit"])
    )

    assert keynotes == []

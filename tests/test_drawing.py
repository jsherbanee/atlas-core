import pytest

from atlas_core.domain import DrawingDiscipline, DrawingSheet


def test_creating_valid_drawing_sheet():
    sheet = DrawingSheet(
        sheet_id=" a101 ",
        sheet_number=" A1.01 ",
        title=" Floor Plan ",
        discipline=DrawingDiscipline.ARCHITECTURAL,
        revision=" 2 ",
        issue_date=" 2026-06-27 ",
        source_file=" drawings.pdf ",
        page_number=3,
        notes=[" Verify scale. "],
        confidence=0.9,
    )

    assert sheet.sheet_id == "a101"
    assert sheet.sheet_number == "A1.01"
    assert sheet.title == "Floor Plan"
    assert sheet.discipline is DrawingDiscipline.ARCHITECTURAL
    assert sheet.revision == "2"
    assert sheet.issue_date == "2026-06-27"
    assert sheet.source_file == "drawings.pdf"
    assert sheet.page_number == 3
    assert sheet.notes == ["Verify scale."]
    assert sheet.confidence == 0.9


def test_accepting_string_discipline():
    sheet = DrawingSheet(
        sheet_id="av101",
        sheet_number="AV1.01",
        title="AV Plan",
        discipline="audiovisual",
    )

    assert sheet.discipline is DrawingDiscipline.AUDIOVISUAL


def test_rejecting_blank_sheet_number():
    with pytest.raises(ValueError, match="sheet_number cannot be blank"):
        DrawingSheet(sheet_id="a101", sheet_number=" ", title="Floor Plan")


def test_rejecting_blank_title():
    with pytest.raises(ValueError, match="title cannot be blank"):
        DrawingSheet(sheet_id="a101", sheet_number="A1.01", title=" ")


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        DrawingSheet(
            sheet_id="a101",
            sheet_number="A1.01",
            title="Floor Plan",
            confidence=1.5,
        )


def test_rejecting_negative_page_number():
    with pytest.raises(ValueError, match="page_number cannot be negative"):
        DrawingSheet(
            sheet_id="a101",
            sheet_number="A1.01",
            title="Floor Plan",
            page_number=-1,
        )


def test_adding_notes():
    sheet = DrawingSheet(
        sheet_id="a101",
        sheet_number="A1.01",
        title="Floor Plan",
    )

    sheet.add_note(" Confirm room names. ")
    sheet.add_note("Coordinate with AV sheets.")

    assert sheet.notes == [
        "Confirm room names.",
        "Coordinate with AV sheets.",
    ]


def test_to_dict_output():
    sheet = DrawingSheet(
        sheet_id="av101",
        sheet_number="AV1.01",
        title="AV Plan",
        discipline=DrawingDiscipline.AUDIOVISUAL,
        revision="1",
        issue_date="2026-06-27",
        source_file="drawings.pdf",
        page_number=4,
        notes=["Coordinate speaker locations."],
        confidence=0.85,
    )

    assert sheet.to_dict() == {
        "sheet_id": "av101",
        "sheet_number": "AV1.01",
        "title": "AV Plan",
        "discipline": "audiovisual",
        "revision": "1",
        "issue_date": "2026-06-27",
        "source_file": "drawings.pdf",
        "page_number": 4,
        "notes": ["Coordinate speaker locations."],
        "confidence": 0.85,
    }

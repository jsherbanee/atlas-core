from atlas_core.domain import DrawingDiscipline, DrawingSheet
from atlas_core.services import DrawingMetadataService


def test_extracts_referenced_sheet_numbers() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-1",
        sheet_number="A101",
        title="Plan view referencing A102 and A103",
        notes=["See A102 detail"],
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.referenced_sheet_numbers == ["A102", "A103"]


def test_extracts_specification_sections() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-2",
        sheet_number="E101",
        title="Electrical plan with 26 24 16 and 27 41 16",
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.referenced_specification_sections == ["262416", "274116"]


def test_extracts_room_names() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-3",
        sheet_number="A102",
        title="Room 101 plan",
        notes=["Conference Room B"],
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.room_names == ["101", "B"]


def test_removes_duplicates() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-4",
        sheet_number="A103",
        title="Plan referencing A102 and A102 and room 101",
        notes=["Room 101", "See A102"],
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.referenced_sheet_numbers == ["A102"]
    assert metadata.room_names == ["101"]


def test_to_dict_output() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-5",
        sheet_number="A104",
        title="Room 201 plan",
        discipline=DrawingDiscipline.ELECTRICAL,
        revision="B",
        issue_date="2026-07-01",
        confidence=0.9,
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.to_dict() == {
        "sheet_number": "A104",
        "title": "Room 201 plan",
        "revision": "B",
        "issue_date": "2026-07-01",
        "discipline": "electrical",
        "referenced_sheet_numbers": [],
        "referenced_specification_sections": [],
        "room_names": ["201"],
        "confidence": 0.9,
    }

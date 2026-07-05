from atlas_core.domain import DrawingDiscipline, DrawingSheet
from atlas_core.services import DrawingMetadataService


def test_creates_metadata_from_drawing_sheet() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-1",
        sheet_number="AV-401",
        title="Main Lobby Plan",
        discipline=DrawingDiscipline.AUDIOVISUAL,
        revision="B",
        issue_date="2026-07-01",
        confidence=0.9,
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.sheet_number == "AV-401"
    assert metadata.title == "Main Lobby Plan"
    assert metadata.discipline == "audiovisual"
    assert metadata.confidence == 0.9


def test_extracts_referenced_sheet_numbers() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-2",
        sheet_number="AV-401",
        title="Plan references AV401 and A-701",
        notes=["See E-601 and TL-101"],
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.referenced_sheet_numbers == ["AV-401", "A-701", "E-601", "TL-101"]


def test_normalizes_referenced_sheet_numbers() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-3",
        sheet_number="AV-401",
        title="Plan references av401, a701, and sec-101",
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.referenced_sheet_numbers == ["AV-401", "A-701", "SEC-101"]


def test_extracts_specification_sections() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-4",
        sheet_number="AV-401",
        title="Plan with 27 41 16 and 26 05 00",
        notes=["Also references 11 61 33"],
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.referenced_specification_sections == [
        "27 41 16",
        "26 05 00",
        "11 61 33",
    ]


def test_extracts_room_names() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-5",
        sheet_number="AV-401",
        title="Recital Hall, Main Lobby",
        notes=["Control Booth", "Classroom 204"],
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.room_names == [
        "Recital Hall",
        "Main Lobby",
        "Control Booth",
        "Classroom 204",
    ]


def test_removes_duplicate_references() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-6",
        sheet_number="AV-401",
        title="References AV401 and AV401",
        notes=["See AV401 again"],
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.referenced_sheet_numbers == ["AV-401"]


def test_preserves_sheet_revision_and_issue_date() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-7",
        sheet_number="AV-401",
        title="Plan",
        revision="C",
        issue_date="2026-07-04",
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.revision == "C"
    assert metadata.issue_date == "2026-07-04"


def test_to_dict_output() -> None:
    sheet = DrawingSheet(
        sheet_id="sheet-8",
        sheet_number="AV-401",
        title="Main Lobby Plan",
        revision="A",
        issue_date="2026-07-01",
        notes=["Equipment Room"],
    )

    metadata = DrawingMetadataService().extract(sheet)

    assert metadata.to_dict() == {
        "sheet_number": "AV-401",
        "title": "Main Lobby Plan",
        "revision": "A",
        "issue_date": "2026-07-01",
        "discipline": "unknown",
        "referenced_sheet_numbers": [],
        "referenced_specification_sections": [],
        "room_names": ["Equipment Room"],
        "confidence": 0.75,
    }

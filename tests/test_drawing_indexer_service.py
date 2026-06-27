from atlas_core.domain import DrawingDiscipline
from atlas_core.services import DrawingIndexerService


def test_indexes_valid_raw_sheet():
    sheets = DrawingIndexerService().index_sheets(
        [
            {
                "sheet_number": " AV1.01 ",
                "title": " AV Floor Plan ",
                "revision": "1",
                "issue_date": "2026-06-27",
                "source_file": "drawings.pdf",
                "page_number": 4,
            }
        ]
    )

    assert len(sheets) == 1
    assert sheets[0].sheet_id == "av1.01"
    assert sheets[0].sheet_number == "AV1.01"
    assert sheets[0].title == "AV Floor Plan"
    assert sheets[0].discipline is DrawingDiscipline.AUDIOVISUAL
    assert sheets[0].revision == "1"
    assert sheets[0].issue_date == "2026-06-27"
    assert sheets[0].source_file == "drawings.pdf"
    assert sheets[0].page_number == 4


def test_skips_incomplete_records():
    sheets = DrawingIndexerService().index_sheets(
        [
            {"sheet_number": "A1.01"},
            {"title": "Floor Plan"},
            {"sheet_number": " ", "title": "Floor Plan"},
            {"sheet_number": "A1.01", "title": "Floor Plan"},
        ]
    )

    assert len(sheets) == 1
    assert sheets[0].sheet_number == "A1.01"


def test_infers_architectural_from_a_sheet():
    discipline = DrawingIndexerService().infer_discipline("A1.01")

    assert discipline is DrawingDiscipline.ARCHITECTURAL


def test_infers_electrical_from_e_sheet():
    discipline = DrawingIndexerService().infer_discipline("E2.01")

    assert discipline is DrawingDiscipline.ELECTRICAL


def test_infers_audiovisual_from_av_sheet():
    discipline = DrawingIndexerService().infer_discipline("AV3.01")

    assert discipline is DrawingDiscipline.AUDIOVISUAL


def test_infers_theatrical_from_title():
    discipline = DrawingIndexerService().infer_discipline(
        "X1.01",
        "Theatrical Rigging Plan",
    )

    assert discipline is DrawingDiscipline.THEATRICAL


def test_infers_lighting_from_tl_and_lx():
    service = DrawingIndexerService()

    assert service.infer_discipline("TL1.01") is DrawingDiscipline.LIGHTING
    assert service.infer_discipline("LX1.01") is DrawingDiscipline.LIGHTING


def test_sheet_id_normalization():
    sheets = DrawingIndexerService().index_sheets(
        [
            {
                "sheet_number": " AV 1.01 ",
                "title": "AV Plan",
            }
        ]
    )

    assert sheets[0].sheet_id == "av-1.01"

from atlas_core.services import DocumentClassifierService, DocumentType


def test_empty_raw_pages_returns_empty_list():
    assert DocumentClassifierService().classify([]) == []


def test_detects_drawing_pages():
    sheet_numbers = [
        "A101",
        "AV401",
        "E201",
        "T101",
        "TL101",
        "LX101",
        "FA101",
        "SEC101",
    ]

    for index, sheet_number in enumerate(sheet_numbers, start=1):
        sections = DocumentClassifierService().classify(
            [
                {
                    "page_number": index,
                    "text": f"{sheet_number} Drawing sheet",
                }
            ]
        )

        assert len(sections) == 1
        assert sections[0].document_type is DocumentType.DRAWING_SET
        assert sections[0].start_page == index
        assert sections[0].end_page == index


def test_detects_specification_pages():
    sections = DocumentClassifierService().classify(
        [
            {
                "page_number": 12,
                "text": "Division 27 Integrated Audio Systems Specification",
            }
        ]
    )

    assert sections[0].document_type is DocumentType.SPECIFICATION_BOOK


def test_detects_schedule_pages():
    sections = DocumentClassifierService().classify(
        [
            {
                "page_number": 8,
                "text": "Equipment Schedule and Device Schedule",
            }
        ]
    )

    assert sections[0].document_type is DocumentType.SCHEDULE


def test_detects_cover_sheet_pages():
    sections = DocumentClassifierService().classify(
        [
            {
                "page_number": 1,
                "text": "Table of Contents",
            }
        ]
    )

    assert sections[0].document_type is DocumentType.COVER_SHEET
    assert sections[0].title == "Cover Sheet"


def test_merges_consecutive_sections():
    sections = DocumentClassifierService().classify(
        [
            {"page_number": 1, "text": "A101 Floor Plan"},
            {"page_number": 2, "text": "AV401 Audio Plan"},
            {"page_number": 3, "text": "Division 27 Specification"},
            {"page_number": 4, "text": "Specification products"},
        ]
    )

    assert len(sections) == 2
    assert sections[0].document_type is DocumentType.DRAWING_SET
    assert sections[0].start_page == 1
    assert sections[0].end_page == 2
    assert sections[1].document_type is DocumentType.SPECIFICATION_BOOK
    assert sections[1].start_page == 3
    assert sections[1].end_page == 4


def test_nonconsecutive_same_types_do_not_merge():
    sections = DocumentClassifierService().classify(
        [
            {"page_number": 1, "text": "A101 Floor Plan"},
            {"page_number": 2, "text": "Division 27 Specification"},
            {"page_number": 3, "text": "AV401 Audio Plan"},
        ]
    )

    assert len(sections) == 3
    assert sections[0].document_type is DocumentType.DRAWING_SET
    assert sections[1].document_type is DocumentType.SPECIFICATION_BOOK
    assert sections[2].document_type is DocumentType.DRAWING_SET
    assert sections[0].start_page == 1
    assert sections[2].start_page == 3


def test_missing_page_number_uses_index():
    sections = DocumentClassifierService().classify(
        [
            {"page_number": 10, "text": "Equipment Schedule"},
            {"text": "AV401 Audio Plan"},
        ]
    )

    assert sections[1].start_page == 2
    assert sections[1].end_page == 2


def test_unknown_pages():
    sections = DocumentClassifierService().classify(
        [
            {
                "page_number": 1,
                "text": "General project notes without classifier signals.",
            }
        ]
    )

    assert sections[0].document_type is DocumentType.UNKNOWN
    assert sections[0].to_dict() == {
        "document_type": "unknown",
        "start_page": 1,
        "end_page": 1,
        "title": "Unknown",
        "confidence": 0.5,
    }

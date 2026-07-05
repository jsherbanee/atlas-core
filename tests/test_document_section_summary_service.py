from atlas_core.services.document_classifier_service import (
    DocumentSection,
    DocumentType,
)
from atlas_core.services.document_section_summary_service import (
    DocumentSectionSummary,
    DocumentSectionSummaryService,
)


def test_empty_sections_return_zero_summary() -> None:
    summary = DocumentSectionSummaryService().summarize([])

    assert summary == DocumentSectionSummary(
        total_sections=0,
        total_pages=0,
        drawing_pages=0,
        specification_pages=0,
        schedule_pages=0,
        cover_pages=0,
        unknown_pages=0,
    )


def test_counts_drawing_pages() -> None:
    summary = DocumentSectionSummaryService().summarize(
        [
            DocumentSection(
                document_type=DocumentType.DRAWING_SET,
                start_page=1,
                end_page=3,
                title="Drawings",
            )
        ]
    )

    assert summary.total_sections == 1
    assert summary.total_pages == 3
    assert summary.drawing_pages == 3


def test_counts_specification_pages() -> None:
    summary = DocumentSectionSummaryService().summarize(
        [
            DocumentSection(
                document_type=DocumentType.SPECIFICATION_BOOK,
                start_page=4,
                end_page=6,
                title="Specs",
            )
        ]
    )

    assert summary.total_pages == 3
    assert summary.specification_pages == 3


def test_counts_schedule_pages() -> None:
    summary = DocumentSectionSummaryService().summarize(
        [
            DocumentSection(
                document_type=DocumentType.SCHEDULE,
                start_page=7,
                end_page=8,
                title="Schedule",
            )
        ]
    )

    assert summary.total_pages == 2
    assert summary.schedule_pages == 2


def test_counts_cover_pages() -> None:
    summary = DocumentSectionSummaryService().summarize(
        [
            DocumentSection(
                document_type=DocumentType.COVER_SHEET,
                start_page=1,
                end_page=1,
                title="Cover",
            )
        ]
    )

    assert summary.total_pages == 1
    assert summary.cover_pages == 1


def test_counts_unknown_pages() -> None:
    summary = DocumentSectionSummaryService().summarize(
        [
            {
                "document_type": "not_real",
                "start_page": 10,
                "end_page": 12,
            }
        ]
    )

    assert summary.total_pages == 3
    assert summary.unknown_pages == 3


def test_accepts_dict_input() -> None:
    summary = DocumentSectionSummaryService().summarize(
        [
            {
                "document_type": "drawing_set",
                "start_page": 1,
                "end_page": 2,
            },
            {
                "document_type": "specification_book",
                "start_page": 3,
                "end_page": 5,
            },
        ]
    )

    assert summary.total_sections == 2
    assert summary.total_pages == 5
    assert summary.drawing_pages == 2
    assert summary.specification_pages == 3


def test_to_dict_output() -> None:
    summary = DocumentSectionSummary(
        total_sections=2,
        total_pages=5,
        drawing_pages=2,
        specification_pages=3,
        schedule_pages=0,
        cover_pages=0,
        unknown_pages=0,
    )

    assert summary.to_dict() == {
        "total_sections": 2,
        "total_pages": 5,
        "drawing_pages": 2,
        "specification_pages": 3,
        "schedule_pages": 0,
        "cover_pages": 0,
        "unknown_pages": 0,
    }

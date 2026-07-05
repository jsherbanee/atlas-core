from atlas_core.services.page_candidate_extraction_service import (
    PageCandidateExtractionService,
)


def test_extracts_av_sheet_candidate() -> None:
    candidates = PageCandidateExtractionService().extract_sheet_candidates(
        [
            {
                "page_number": 1,
                "text": "AV-101 Audio Visual Floor Plan",
            }
        ]
    )

    assert len(candidates) == 1
    assert candidates[0]["sheet_number"] == "AV-101"


def test_normalizes_av101_to_av_101_where_practical() -> None:
    candidates = PageCandidateExtractionService().extract_sheet_candidates(
        [
            {
                "page_number": 1,
                "text": "AV101 Audio Visual Floor Plan",
            }
        ]
    )

    assert candidates[0]["sheet_number"] == "AV-101"


def test_extracts_sheet_source_file_and_page_number() -> None:
    candidates = PageCandidateExtractionService().extract_sheet_candidates(
        [
            {
                "page_number": 4,
                "source_file": "drawings.pdf",
                "text": "E-601 Electrical Plan",
            }
        ]
    )

    assert candidates[0]["source_file"] == "drawings.pdf"
    assert candidates[0]["page_number"] == 4


def test_uses_fallback_sheet_title() -> None:
    candidates = PageCandidateExtractionService().extract_sheet_candidates(
        [
            {
                "page_number": 2,
                "text": "TL-101",
            }
        ]
    )

    assert candidates[0]["title"] == "Untitled Sheet"


def test_extracts_csi_specification_candidate() -> None:
    candidates = PageCandidateExtractionService().extract_specification_candidates(
        [
            {
                "page_number": 10,
                "text": "27 41 16 Integrated Audio-Video Systems",
            }
        ]
    )

    assert len(candidates) == 1
    assert candidates[0]["section_number"] == "27 41 16"


def test_extracts_spec_source_file_and_page_start_end() -> None:
    candidates = PageCandidateExtractionService().extract_specification_candidates(
        [
            {
                "page_number": 12,
                "source_file": "specs.pdf",
                "text": "26 05 00 Common Work Results for Electrical",
            }
        ]
    )

    assert candidates[0]["source_file"] == "specs.pdf"
    assert candidates[0]["page_start"] == 12
    assert candidates[0]["page_end"] == 12


def test_uses_fallback_specification_title() -> None:
    candidates = PageCandidateExtractionService().extract_specification_candidates(
        [
            {
                "page_number": 8,
                "text": "28 00 00",
            }
        ]
    )

    assert candidates[0]["title"] == "Untitled Specification Section"


def test_avoids_duplicate_sheet_candidates() -> None:
    candidates = PageCandidateExtractionService().extract_sheet_candidates(
        [
            {
                "page_number": 1,
                "text": "AV-101 Audio Plan AV-101 Audio Plan",
            }
        ]
    )

    assert len(candidates) == 1


def test_avoids_duplicate_spec_candidates() -> None:
    candidates = PageCandidateExtractionService().extract_specification_candidates(
        [
            {
                "page_number": 15,
                "text": "27 41 16 Integrated AV 27 41 16 Integrated AV",
            }
        ]
    )

    assert len(candidates) == 1


def test_empty_pages_return_empty_lists() -> None:
    service = PageCandidateExtractionService()

    assert service.extract_sheet_candidates([]) == []
    assert service.extract_specification_candidates([]) == []

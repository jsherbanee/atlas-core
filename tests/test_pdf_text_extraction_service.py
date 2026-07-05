from pathlib import Path

import pytest

from atlas_core.services import (
    ExtractedPdfPage,
    PdfTextExtractionService,
)


@pytest.fixture
def fixture_pdf_path() -> Path:
    return Path(__file__).parent / "fixtures" / "simple.pdf"


def test_rejects_missing_file(tmp_path: Path) -> None:
    service = PdfTextExtractionService()

    with pytest.raises(FileNotFoundError):
        service.extract_pages(tmp_path / "missing.pdf")


def test_rejects_non_pdf_file(tmp_path: Path) -> None:
    service = PdfTextExtractionService()
    non_pdf_path = tmp_path / "not-a-pdf.txt"
    non_pdf_path.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(ValueError):
        service.extract_pages(non_pdf_path)


def test_extracts_pages_from_simple_pdf_fixture(fixture_pdf_path: Path) -> None:
    pages = PdfTextExtractionService().extract_pages(fixture_pdf_path)

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "First page" in pages[0].text
    assert pages[0].source_file == "simple.pdf"
    assert pages[0].has_text is True


def test_preserves_page_order(fixture_pdf_path: Path) -> None:
    pages = PdfTextExtractionService().extract_pages(fixture_pdf_path)

    assert [page.page_number for page in pages] == [1, 2]


def test_marks_blank_pages_as_has_text_false(fixture_pdf_path: Path) -> None:
    pages = PdfTextExtractionService().extract_pages(fixture_pdf_path)

    assert pages[1].has_text is False
    assert pages[1].text == ""


def test_to_dict_output() -> None:
    page = ExtractedPdfPage(page_number=1, text="Sample", source_file="sample.pdf")

    assert page.to_dict() == {
        "page_number": 1,
        "text": "Sample",
        "source_file": "sample.pdf",
        "has_text": True,
    }

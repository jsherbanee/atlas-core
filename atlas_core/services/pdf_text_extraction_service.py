"""PDF text extraction service for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader


@dataclass(slots=True)
class ExtractedPdfPage:
    page_number: int
    text: str = ""
    source_file: str = ""
    has_text: bool = False

    def __post_init__(self) -> None:
        if self.page_number <= 0:
            raise ValueError("page_number must be greater than 0")

        if not isinstance(self.source_file, str) or not self.source_file.strip():
            raise ValueError("source_file cannot be blank")

        normalized_source = self.source_file.strip()
        self.source_file = normalized_source

        if self.text is None:
            self.text = ""
        elif not isinstance(self.text, str):
            self.text = str(self.text)

        self.has_text = bool(self.text.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "source_file": self.source_file,
            "has_text": self.has_text,
        }


class PdfTextExtractionService:
    def extract_pages(self, pdf_path: str | Path) -> list[ExtractedPdfPage]:
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        if not path.is_file():
            raise ValueError("pdf_path must point to a file")

        if path.suffix.lower() != ".pdf":
            raise ValueError("pdf_path must be a PDF")

        reader = PdfReader(str(path))
        pages: list[ExtractedPdfPage] = []

        for page_number, page in enumerate(reader.pages, start=1):
            extracted_text = page.extract_text() or ""
            pages.append(
                ExtractedPdfPage(
                    page_number=page_number,
                    text=extracted_text,
                    source_file=path.name,
                )
            )

        return pages

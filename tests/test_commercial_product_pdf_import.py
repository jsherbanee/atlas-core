from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pypdf import PdfWriter

from atlas_core.services.document_intake_service import DocumentIntakeService
from atlas_core.services.master_library import CommercialProductService


@pytest.fixture
def simple_pdf_bytes() -> bytes:
    return (Path(__file__).parent / "fixtures" / "simple.pdf").read_bytes()


def _foundation_pdf_service() -> tuple[CommercialProductService, dict[str, str]]:
    service = CommercialProductService()
    service.create_manufacturer(
        manufacturer_id="mfr-acme",
        canonical_name="ACME",
    )
    service.create_vendor(
        vendor_id="vendor-dist",
        canonical_name="Distributor One",
    )
    sheet = service.create_price_sheet(
        name="acme_price_sheet.pdf",
        vendor_id="vendor-dist",
        vendor="Distributor One",
        manufacturer_id="mfr-acme",
        manufacturer="ACME",
        purchasing_channel="distributor",
        currency="USD",
    )
    return service, sheet


def _patch_pdf_extraction(
    monkeypatch: pytest.MonkeyPatch,
    *,
    pages: list[dict[str, object]],
    warnings: list[str] | None = None,
    status: dict[str, object] | None = None,
) -> None:
    effective_status = status or {
        "status": "extracted",
        "extraction_mode": "embedded_text",
        "ocr_attempted": False,
        "total_pages": len(pages),
        "pages_with_embedded_text": len(pages),
        "pages_with_ocr_text": 0,
        "pages_without_embedded_text": 0,
        "requires_ocr": False,
        "warnings": list(warnings or []),
    }

    def _fake_extract(
        self: DocumentIntakeService,
        file_path: Path,
        group_name: str,
    ) -> tuple[list[dict[str, object]], list[str], dict[str, object]]:
        _ = (self, file_path, group_name)
        return pages, list(warnings or []), dict(effective_status)

    monkeypatch.setattr(DocumentIntakeService, "_extract_document_pages", _fake_extract)


def _table_page(page_number: int, *, ocr: bool = False) -> dict[str, object]:
    return {
        "page_number": page_number,
        "text": (
            "ACME PRICE LIST\n"
            "Part Number  Description  List Price  Net Price\n"
            f"PN-{page_number}  Speaker {page_number}  199.00  120.00\n"
            f"PN-{page_number + 10}  Amplifier {page_number}  299.00  180.00\n"
            "CONFIDENTIAL FOOTER"
        ),
        "has_text": True,
        "ocr_derived": ocr,
        "text_source": "ocr" if ocr else "embedded",
        "source_file": "acme_price_sheet.pdf",
    }


def test_pdf_inspection_text_native_pdf_reports_pages_and_text(
    simple_pdf_bytes: bytes,
) -> None:
    service, _ = _foundation_pdf_service()

    inspected = service.inspect_pdf_import_source(
        source_filename="simple.pdf",
        file_bytes=simple_pdf_bytes,
    )

    assert inspected["valid_pdf"] is True
    assert inspected["page_count"] >= 1
    assert len(list(inspected.get("pages") or [])) >= 1


def test_pdf_inspection_reports_ocr_required_and_failure(
    monkeypatch: pytest.MonkeyPatch,
    simple_pdf_bytes: bytes,
) -> None:
    service, _ = _foundation_pdf_service()
    _patch_pdf_extraction(
        monkeypatch,
        pages=[
            {
                "page_number": 1,
                "text": "",
                "has_text": False,
                "ocr_derived": False,
                "text_source": "none",
                "source_file": "acme_price_sheet.pdf",
            }
        ],
        warnings=[
            "acme_price_sheet.pdf: no embedded text found. OCR is required for extraction.",
            "acme_price_sheet.pdf: OCR attempted but no text was extracted from non-embedded pages.",
        ],
        status={
            "status": "failed",
            "extraction_mode": "ocr_failed",
            "ocr_attempted": True,
            "total_pages": 1,
            "pages_with_embedded_text": 0,
            "pages_with_ocr_text": 0,
            "pages_without_embedded_text": 1,
            "requires_ocr": True,
            "warnings": [],
        },
    )

    inspected = service.inspect_pdf_import_source(
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
    )

    codes = {item.get("code") for item in list(inspected.get("diagnostics") or [])}
    assert "no_extractable_text" in codes
    assert "ocr_failure" in codes


def test_pdf_inspection_reports_mixed_embedded_and_scanned_pages(
    monkeypatch: pytest.MonkeyPatch,
    simple_pdf_bytes: bytes,
) -> None:
    service, _ = _foundation_pdf_service()
    _patch_pdf_extraction(
        monkeypatch,
        pages=[_table_page(1, ocr=False), _table_page(2, ocr=True)],
        warnings=[],
        status={
            "status": "partial",
            "extraction_mode": "mixed_embedded_and_ocr",
            "ocr_attempted": True,
            "total_pages": 2,
            "pages_with_embedded_text": 1,
            "pages_with_ocr_text": 1,
            "pages_without_embedded_text": 0,
            "requires_ocr": False,
            "warnings": [],
        },
    )

    inspected = service.inspect_pdf_import_source(
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
    )

    assert any(
        item.get("code") == "ocr_required"
        for item in list(inspected.get("diagnostics") or [])
    )


def test_pdf_inspection_detects_repeated_headers_and_footers(
    monkeypatch: pytest.MonkeyPatch,
    simple_pdf_bytes: bytes,
) -> None:
    service, _ = _foundation_pdf_service()
    _patch_pdf_extraction(
        monkeypatch,
        pages=[_table_page(1), _table_page(2)],
    )

    inspected = service.inspect_pdf_import_source(
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
    )

    assert inspected["repeated_headers"]
    assert inspected["repeated_footers"]


def test_pdf_inspection_reports_rotated_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = _foundation_pdf_service()
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    page.rotate(90)
    pdf_path = Path(__file__).parent / "fixtures" / "rotated_synthetic.pdf"
    with pdf_path.open("wb") as file:
        writer.write(file)

    try:
        _patch_pdf_extraction(monkeypatch, pages=[_table_page(1)])
        inspected = service.inspect_pdf_import_source(
            source_filename="rotated_synthetic.pdf",
            file_bytes=pdf_path.read_bytes(),
        )
    finally:
        pdf_path.unlink(missing_ok=True)

    assert any(
        item.get("code") == "rotated_page"
        for item in list(inspected.get("diagnostics") or [])
    )


def test_pdf_inspection_reports_encrypted_pdf() -> None:
    service, _ = _foundation_pdf_service()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    pdf_path = Path(__file__).parent / "fixtures" / "encrypted_synthetic.pdf"
    with pdf_path.open("wb") as file:
        writer.write(file)
    try:
        inspected = service.inspect_pdf_import_source(
            source_filename="encrypted_synthetic.pdf",
            file_bytes=pdf_path.read_bytes(),
        )
    finally:
        pdf_path.unlink(missing_ok=True)

    assert any(
        item.get("code") == "encrypted_pdf"
        for item in list(inspected.get("diagnostics") or [])
    )


def test_pdf_inspection_reports_malformed_pdf() -> None:
    service, _ = _foundation_pdf_service()

    inspected = service.inspect_pdf_import_source(
        source_filename="malformed.pdf",
        file_bytes=b"not a valid pdf",
    )

    assert inspected["valid_pdf"] is False
    assert any(
        item.get("code") == "malformed_pdf"
        for item in list(inspected.get("diagnostics") or [])
    )


def test_pdf_create_draft_supports_page_range_and_candidate_selection(
    monkeypatch: pytest.MonkeyPatch,
    simple_pdf_bytes: bytes,
) -> None:
    service, sheet = _foundation_pdf_service()
    _patch_pdf_extraction(
        monkeypatch,
        pages=[_table_page(1), _table_page(2)],
    )
    inspected = service.inspect_pdf_import_source(
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
    )
    candidate = list(inspected.get("table_candidates") or [])[0]

    draft = service.create_pdf_import_draft(
        price_sheet_id=sheet["price_sheet_id"],
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
        version_label="pdf-v1",
        effective_date="2026-01-01",
        expiration_date="",
        currency="USD",
        selected_pages=[1],
        table_candidate_id=str(candidate.get("candidate_id")),
        header_row_index=0,
        column_mapping={
            "manufacturer_part_number": "Part Number",
            "description": "Description",
            "list_price": "List Price",
            "unit_cost": "Net Price",
        },
        imported_by="tester",
    )

    assert draft["record_count"] > 0
    assert all(
        int(row.get("source_page_number") or 0) == 1
        for row in list(draft.get("preview_rows") or [])
    )


def test_pdf_create_draft_supports_custom_header_and_corrections(
    monkeypatch: pytest.MonkeyPatch,
    simple_pdf_bytes: bytes,
) -> None:
    service, sheet = _foundation_pdf_service()
    _patch_pdf_extraction(
        monkeypatch,
        pages=[
            {
                "page_number": 1,
                "text": (
                    "ACME PRICE LIST\n"
                    "Inventory Export\n"
                    "Part Number  Description  List Price  Net Price\n"
                    "PN-1  Speaker  OneHundred  120.00\n"
                ),
                "has_text": True,
                "ocr_derived": False,
                "text_source": "embedded",
                "source_file": "acme_price_sheet.pdf",
            }
        ],
    )
    inspected = service.inspect_pdf_import_source(
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
    )
    candidate = list(inspected.get("table_candidates") or [])[0]

    draft = service.create_pdf_import_draft(
        price_sheet_id=sheet["price_sheet_id"],
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
        version_label="pdf-v2",
        effective_date="2026-01-01",
        expiration_date="",
        currency="USD",
        selected_pages=[1],
        table_candidate_id=str(candidate.get("candidate_id")),
        header_row_index=1,
        column_mapping={
            "manufacturer_part_number": "Part Number",
            "description": "Description",
            "list_price": "List Price",
            "unit_cost": "Net Price",
        },
        row_corrections={
            2: {
                "List Price": "199.00",
            }
        },
        imported_by="tester",
    )

    assert any(
        row.get("raw_extracted_values") for row in list(draft.get("preview_rows") or [])
    )


def test_pdf_finalize_blocks_on_extraction_or_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
    simple_pdf_bytes: bytes,
) -> None:
    service, sheet = _foundation_pdf_service()
    _patch_pdf_extraction(
        monkeypatch,
        pages=[
            {
                "page_number": 1,
                "text": (
                    "Part Number  Description  List Price  Net Price\n"
                    "PN-1  Speaker  bad-number  bad-number\n"
                ),
                "has_text": True,
                "ocr_derived": False,
                "text_source": "embedded",
                "source_file": "acme_price_sheet.pdf",
            }
        ],
    )
    inspected = service.inspect_pdf_import_source(
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
    )
    candidate = list(inspected.get("table_candidates") or [])[0]

    draft = service.create_pdf_import_draft(
        price_sheet_id=sheet["price_sheet_id"],
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
        version_label="pdf-v3",
        effective_date="2026-01-01",
        expiration_date="",
        currency="USD",
        selected_pages=[1],
        table_candidate_id=str(candidate.get("candidate_id")),
        header_row_index=0,
        column_mapping={
            "manufacturer_part_number": "Part Number",
            "description": "Description",
            "list_price": "List Price",
            "unit_cost": "Net Price",
        },
        imported_by="tester",
    )

    assert draft["status"] == "draft"
    with pytest.raises(ValueError, match="cannot be validated"):
        service.validate_price_sheet_draft(draft["draft_id"], acknowledge_warnings=True)


def test_pdf_finalized_records_keep_traceability_and_immutability(
    monkeypatch: pytest.MonkeyPatch,
    simple_pdf_bytes: bytes,
) -> None:
    service, sheet = _foundation_pdf_service()
    _patch_pdf_extraction(
        monkeypatch,
        pages=[_table_page(1)],
    )
    inspected = service.inspect_pdf_import_source(
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
    )
    candidate = list(inspected.get("table_candidates") or [])[0]
    draft = service.create_pdf_import_draft(
        price_sheet_id=sheet["price_sheet_id"],
        source_filename="acme_price_sheet.pdf",
        file_bytes=simple_pdf_bytes,
        version_label="pdf-v4",
        effective_date="2026-01-01",
        expiration_date="",
        currency="USD",
        selected_pages=[1],
        table_candidate_id=str(candidate.get("candidate_id")),
        header_row_index=0,
        column_mapping={
            "manufacturer_part_number": "Part Number",
            "description": "Description",
            "list_price": "List Price",
            "unit_cost": "Net Price",
        },
        imported_by="tester",
    )
    service.validate_price_sheet_draft(draft["draft_id"], acknowledge_warnings=True)
    finalized = service.finalize_price_sheet_draft(
        draft["draft_id"], imported_by="tester"
    )

    record = list(finalized.get("records") or [])[0]
    assert record.get("source_page_number") == 1
    assert record.get("extraction_method") in {"embedded", "ocr"}
    assert isinstance(record.get("raw_extracted_values"), dict)
    assert (
        finalized["version"].get("source_hash")
        == hashlib.sha1(simple_pdf_bytes).hexdigest()
    )

    with pytest.raises(ValueError, match="immutable"):
        service.update_price_record(
            record["price_record_id"],
            updates={"description_imported": "changed"},
        )

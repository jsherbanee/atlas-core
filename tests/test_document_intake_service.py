from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import zipfile

from atlas_core.services.pdf_text_extraction_service import (
    ExtractedPdfPage,
    PdfTextExtractionService,
)
from pypdf import PdfWriter

from atlas_core.services.document_intake_service import (
    DocumentIntakeService,
    LocalOcrEngine,
    UploadedIntakeFile,
)


def _write_blank_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as file:
        writer.write(file)


def _build_package(tmp_path: Path) -> Path:
    package = tmp_path / "example_project"
    drawings = package / "drawings"
    specifications = package / "specifications"
    schedules = package / "schedules"
    addenda = package / "addenda"

    drawings.mkdir(parents=True)
    specifications.mkdir(parents=True)
    schedules.mkdir(parents=True)
    addenda.mkdir(parents=True)

    (package / "metadata.json").write_text(
        json.dumps(
            {
                "project_id": "project-intake-001",
                "review_id": "review-intake-001",
                "project_name": "Example Intake Project",
                "name": "Example Intake Plan Review",
            }
        ),
        encoding="utf-8",
    )

    _write_blank_pdf(drawings / "AV-101 Audio Plan.pdf")
    _write_blank_pdf(specifications / "27 41 16 Integrated Audio Systems.pdf")
    _write_blank_pdf(addenda / "ADD-1 AV Addendum.pdf")

    with (schedules / "audio_schedule.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=["tag", "description"])
        writer.writeheader()
        writer.writerow({"tag": "SPK-1", "description": "Main ceiling speaker"})

    return package


def test_package_folder_discovery(tmp_path: Path) -> None:
    package = _build_package(tmp_path)
    discovery = DocumentIntakeService().discover_package(package)

    assert len(discovery.drawing_files) == 1
    assert len(discovery.specification_files) == 1
    assert len(discovery.schedule_files) == 1
    assert len(discovery.addenda_files) == 1
    assert discovery.metadata_path is not None


def test_metadata_and_pdf_page_extraction(tmp_path: Path) -> None:
    package = _build_package(tmp_path)
    snapshot = DocumentIntakeService().build_snapshot(package)

    assert snapshot.metadata["project_id"] == "project-intake-001"
    assert len(snapshot.raw_pages) == 3
    assert all(page["source_file"].endswith(".pdf") for page in snapshot.raw_pages)
    assert any("OCR is required" in warning for warning in snapshot.warnings)
    assert snapshot.import_summary["total_files"] >= 4
    assert snapshot.import_summary["total_pages"] == 3
    assert snapshot.import_summary["pages_without_embedded_text"] >= 3
    assert snapshot.import_summary["documents_requiring_ocr"] >= 1
    assert snapshot.import_summary["extraction_warning_count"] >= 1


def test_spec_and_sheet_detection_and_equipment_candidates(tmp_path: Path) -> None:
    package = _build_package(tmp_path)
    snapshot = DocumentIntakeService().build_snapshot(package)

    assert any(sheet["sheet_number"] == "AV-101" for sheet in snapshot.raw_sheets)
    assert any(
        section["section_number"] == "27 41 16" for section in snapshot.raw_sections
    )
    assert any(
        candidate["category_hint"] == "speaker"
        for candidate in snapshot.equipment_candidates
    )


def test_review_pipeline_from_snapshot_output(tmp_path: Path) -> None:
    package = _build_package(tmp_path)
    intake_service = DocumentIntakeService()

    snapshot = intake_service.build_snapshot(package)
    snapshot_path = intake_service.write_snapshot(snapshot, tmp_path / "outputs")
    loaded_snapshot = intake_service.load_snapshot(snapshot_path)
    result = intake_service.run_review_from_snapshot(loaded_snapshot)

    assert result.review.review_id == "review-intake-001"
    assert result.review.project_id == "project-intake-001"
    assert result.review.name == "Example Intake Plan Review"


def test_build_session_package_from_uploads_classifies_and_runs_intake(
    tmp_path: Path,
) -> None:
    service = DocumentIntakeService()
    uploads = [
        UploadedIntakeFile(name="AV-101 Audio Plan.txt", data=b"AV-101 Audio Plan"),
        UploadedIntakeFile(
            name="27_41_16_Integrated_Audio_Systems.docx",
            data=_docx_bytes("SECTION 27 41 16\nIntegrated Audio Systems"),
        ),
        UploadedIntakeFile(
            name="audio_schedule.csv",
            data=b"tag,description\nSPK-1,Main ceiling speaker\n",
        ),
        UploadedIntakeFile(name="cover.jpg", data=b"fake-image"),
        UploadedIntakeFile(
            name="metadata.json",
            data=json.dumps(
                {
                    "project_id": "upload-project-001",
                    "review_id": "upload-review-001",
                    "project_name": "Upload Project",
                }
            ).encode("utf-8"),
        ),
        UploadedIntakeFile(name="notes.exe", data=b"not-supported"),
    ]

    result = service.build_session_package_from_uploads(
        uploaded_files=uploads,
        uploads_root=tmp_path / "uploads",
        session_id="session-test",
    )

    assert result.package_path == tmp_path / "uploads" / "session-test"
    assert result.snapshot_path.exists()
    assert result.import_summary["drawing_count"] == 1
    assert result.import_summary["specification_count"] == 1
    assert result.import_summary["schedule_count"] == 1
    assert result.import_summary["image_count"] == 1
    assert result.import_summary["unsupported_file_count"] == 0
    assert any("OCR support is required" in warning for warning in result.warnings)


def test_zip_upload_is_unpacked_recursively(tmp_path: Path) -> None:
    service = DocumentIntakeService()
    zip_payload = _zip_bytes(
        {
            "nested/AV-102_Audio_Plan.txt": b"AV-102 AUDIO PLAN",
            "nested/audio_schedule.csv": b"tag,description\nDSP-1,Main DSP processor\n",
        }
    )
    uploads = [UploadedIntakeFile(name="project_package.zip", data=zip_payload)]

    result = service.build_session_package_from_uploads(
        uploaded_files=uploads,
        uploads_root=tmp_path / "uploads",
        session_id="zip-test",
    )

    assert result.import_summary["drawing_count"] == 1
    assert result.import_summary["schedule_count"] == 1
    assert result.snapshot.raw_pages


def test_inspect_uploaded_files_detects_duplicates_empty_and_unsupported() -> None:
    service = DocumentIntakeService()
    uploads = [
        UploadedIntakeFile(name="bid-sheet.pdf", data=b"pdf-content"),
        UploadedIntakeFile(name="bid-sheet.pdf", data=b"pdf-content-2"),
        UploadedIntakeFile(name="duplicate-hash.docx", data=b"same"),
        UploadedIntakeFile(name="duplicate-hash-2.docx", data=b"same"),
        UploadedIntakeFile(name="empty.pdf", data=b""),
        UploadedIntakeFile(name="unsupported.exe", data=b"x"),
        UploadedIntakeFile(name="photo.jpg", data=b"jpg-bytes"),
        UploadedIntakeFile(name="photo.jpeg", data=b"jpeg-bytes"),
        UploadedIntakeFile(name="schedule.xls", data=b"xls-bytes"),
        UploadedIntakeFile(name="schedule.xlsx", data=b"xlsx-bytes"),
        UploadedIntakeFile(name="legacy.doc", data=b"doc-bytes"),
        UploadedIntakeFile(name="modern.docx", data=_docx_bytes("DOCX TEXT")),
    ]

    inspected = service.inspect_uploaded_files(uploads)
    diagnostics = list(inspected.diagnostics)

    rejected = [item for item in diagnostics if not bool(item.get("accepted"))]
    accepted = [item for item in diagnostics if bool(item.get("accepted"))]

    assert any("duplicate filename" in ",".join(item["messages"]) for item in rejected)
    assert any(
        "duplicate source hash" in ",".join(item["messages"]) for item in rejected
    )
    assert any("empty file" in ",".join(item["messages"]) for item in rejected)
    assert any(
        "unsupported extension" in ",".join(item["messages"]) for item in rejected
    )
    assert any(item["name"].endswith(".jpg") for item in accepted)
    assert any(item["name"].endswith(".jpeg") for item in accepted)
    assert any(item["name"].endswith(".doc") for item in accepted)
    assert any(item["name"].endswith(".docx") for item in accepted)
    assert any(item["name"].endswith(".xls") for item in accepted)
    assert any(item["name"].endswith(".xlsx") for item in accepted)


def test_zip_upload_rejects_traversal_unsupported_and_system_artifacts(
    tmp_path: Path,
) -> None:
    service = DocumentIntakeService()
    zip_payload = _zip_bytes(
        {
            "nested/AV-300 Audio Plan.txt": b"AV-300",
            "nested/notes.exe": b"bad",
            "../escape.txt": b"escape",
            "__MACOSX/._ignored": b"ignored",
            ".DS_Store": b"ignored",
        }
    )

    inspected = service.inspect_uploaded_files(
        [UploadedIntakeFile(name="source.zip", data=zip_payload)]
    )

    accepted_names = [item.name for item in inspected.accepted_files]
    rejected = [item for item in inspected.diagnostics if not item.get("accepted")]

    assert any(name.endswith("AV-300 Audio Plan.txt") for name in accepted_names)
    assert any(name.endswith("notes.exe") for name in [d["name"] for d in rejected])
    assert any("unsafe archive path" in warning for warning in inspected.warnings)
    assert not any("__MACOSX" in name for name in accepted_names)
    assert not any(name.endswith(".DS_Store") for name in accepted_names)

    result = service.build_session_package_from_uploads(
        uploaded_files=[UploadedIntakeFile(name="source.zip", data=zip_payload)],
        uploads_root=tmp_path / "uploads",
        session_id="zip-safety",
    )
    assert result.import_summary["unsupported_file_count"] == 0
    assert result.import_summary["drawing_count"] >= 1


def test_zip_upload_handles_malformed_archive_deterministically() -> None:
    service = DocumentIntakeService()
    inspected = service.inspect_uploaded_files(
        [UploadedIntakeFile(name="broken.zip", data=b"not-a-real-zip")]
    )

    assert inspected.accepted_files == []
    assert any(
        "could not unpack ZIP archive" in warning for warning in inspected.warnings
    )


def test_zip_upload_entry_and_expansion_limits_are_enforced() -> None:
    service = DocumentIntakeService()
    service._MAX_ARCHIVE_ENTRY_COUNT = 2
    service._MAX_ARCHIVE_UNCOMPRESSED_BYTES = 10

    payload = _zip_bytes(
        {
            "a/one.pdf": b"12345",
            "a/two.pdf": b"67890",
            "a/three.pdf": b"overflow",
        }
    )
    inspected = service.inspect_uploaded_files(
        [UploadedIntakeFile(name="limited.zip", data=payload)]
    )

    assert len(inspected.accepted_files) <= 2
    assert any(
        "archive entry limit exceeded" in warning
        or "archive expansion size limit exceeded" in warning
        for warning in inspected.warnings
    )


def test_zip_nested_paths_preserved_as_source_metadata(tmp_path: Path) -> None:
    service = DocumentIntakeService()
    payload = _zip_bytes(
        {
            "nested/floor1/AV-401 Drawing.txt": b"AV-401",
        }
    )
    result = service.build_session_package_from_uploads(
        uploaded_files=[UploadedIntakeFile(name="bundle.zip", data=payload)],
        uploads_root=tmp_path / "uploads",
        session_id="zip-nested",
    )

    assert any(
        "bundle.zip/nested/floor1/AV-401 Drawing.txt" in str(page.get("source_path"))
        for page in result.snapshot.raw_pages
    )


def test_pdf_embedded_text_status_reports_extracted(tmp_path: Path) -> None:
    package = _build_package(tmp_path)

    class _TextExtractor(PdfTextExtractionService):
        def extract_pages(self, pdf_path: str | Path) -> list[ExtractedPdfPage]:
            return [
                ExtractedPdfPage(
                    page_number=1,
                    text="AV-101 AUDIO PLAN",
                    source_file=Path(pdf_path).name,
                )
            ]

    service = DocumentIntakeService(pdf_text_extraction_service=_TextExtractor())
    snapshot = service.build_snapshot(package)
    diagnostics = list(snapshot.import_summary.get("file_diagnostics") or [])

    drawing_diagnostics = [
        item for item in diagnostics if item.get("file_name") == "AV-101 Audio Plan.pdf"
    ]
    assert drawing_diagnostics
    assert drawing_diagnostics[0]["status"] == "extracted"
    assert snapshot.import_summary["pages_with_embedded_text"] >= 1


def test_pdf_mixed_text_status_reports_partial(tmp_path: Path) -> None:
    package = _build_package(tmp_path)

    class _MixedExtractor(PdfTextExtractionService):
        def extract_pages(self, pdf_path: str | Path) -> list[ExtractedPdfPage]:
            source = Path(pdf_path).name
            if source != "AV-101 Audio Plan.pdf":
                return [ExtractedPdfPage(page_number=1, text="", source_file=source)]

            return [
                ExtractedPdfPage(page_number=1, text="AV-101", source_file=source),
                ExtractedPdfPage(page_number=2, text="", source_file=source),
            ]

    service = DocumentIntakeService(pdf_text_extraction_service=_MixedExtractor())
    snapshot = service.build_snapshot(package)
    diagnostics = list(snapshot.import_summary.get("file_diagnostics") or [])
    drawing_diagnostics = [
        item for item in diagnostics if item.get("file_name") == "AV-101 Audio Plan.pdf"
    ]
    assert drawing_diagnostics
    assert drawing_diagnostics[0]["status"] == "partial"


def test_snapshot_serializes_file_diagnostics(tmp_path: Path) -> None:
    package = _build_package(tmp_path)
    service = DocumentIntakeService()
    snapshot = service.build_snapshot(package)
    snapshot_path = service.write_snapshot(snapshot, tmp_path / "outputs")
    loaded_snapshot = service.load_snapshot(snapshot_path)

    assert "file_diagnostics" in loaded_snapshot.import_summary
    assert isinstance(loaded_snapshot.import_summary["file_diagnostics"], list)


def test_image_only_intake_requires_ocr_without_fabricated_entities(
    tmp_path: Path,
) -> None:
    package = tmp_path / "image_only_project"
    (package / "drawings").mkdir(parents=True)
    (package / "specifications").mkdir(parents=True)
    (package / "schedules").mkdir(parents=True)
    (package / "addenda").mkdir(parents=True)
    (package / "images").mkdir(parents=True)
    (package / "images" / "scan-001.png").write_bytes(b"image-bytes")

    snapshot = DocumentIntakeService().build_snapshot(package)

    assert snapshot.raw_pages == []
    assert snapshot.raw_sheets == []
    assert snapshot.raw_sections == []
    assert snapshot.equipment_candidates == []
    assert snapshot.import_summary["documents_requiring_ocr"] >= 1
    assert any("OCR support is required" in warning for warning in snapshot.warnings)


def test_optional_local_ocr_marks_pdf_text_as_ocr_derived(tmp_path: Path) -> None:
    package = _build_package(tmp_path)

    class _NoEmbeddedExtractor(PdfTextExtractionService):
        def extract_pages(self, pdf_path: str | Path) -> list[ExtractedPdfPage]:
            return [
                ExtractedPdfPage(
                    page_number=1,
                    text="",
                    source_file=Path(pdf_path).name,
                )
            ]

    class _FakeLocalOcr(LocalOcrEngine):
        def is_available(self) -> bool:
            return True

        def ocr_pdf_pages(
            self,
            pdf_path: Path,
            page_numbers: list[int],
        ) -> tuple[dict[int, str], list[str]]:
            _ = pdf_path
            return {page_number: "OCR PAGE TEXT" for page_number in page_numbers}, []

        def ocr_image_file(self, image_path: Path) -> tuple[str, list[str]]:
            _ = image_path
            return "", []

    service = DocumentIntakeService(
        pdf_text_extraction_service=_NoEmbeddedExtractor(),
        local_ocr_engine=_FakeLocalOcr(),
        enable_local_ocr=True,
    )
    snapshot = service.build_snapshot(package)

    assert snapshot.import_summary["pages_with_ocr_text"] >= 1
    diagnostics = list(snapshot.import_summary.get("file_diagnostics") or [])
    drawing_diag = [
        item for item in diagnostics if item.get("file_name") == "AV-101 Audio Plan.pdf"
    ]
    assert drawing_diag
    assert drawing_diag[0]["extraction_mode"] in {
        "ocr_derived_text",
        "mixed_embedded_and_ocr",
    }


def test_optional_local_ocr_failure_is_reported_for_images(tmp_path: Path) -> None:
    package = tmp_path / "ocr_failure_project"
    (package / "drawings").mkdir(parents=True)
    (package / "specifications").mkdir(parents=True)
    (package / "schedules").mkdir(parents=True)
    (package / "addenda").mkdir(parents=True)
    (package / "images").mkdir(parents=True)
    (package / "images" / "sheet-scan.png").write_bytes(b"scan")

    class _FakeLocalOcr(LocalOcrEngine):
        def is_available(self) -> bool:
            return True

        def ocr_pdf_pages(
            self,
            pdf_path: Path,
            page_numbers: list[int],
        ) -> tuple[dict[int, str], list[str]]:
            _ = (pdf_path, page_numbers)
            return {}, []

        def ocr_image_file(self, image_path: Path) -> tuple[str, list[str]]:
            _ = image_path
            return "", []

    snapshot = DocumentIntakeService(
        local_ocr_engine=_FakeLocalOcr(),
        enable_local_ocr=True,
    ).build_snapshot(package)

    diagnostics = list(snapshot.import_summary.get("file_diagnostics") or [])
    image_diag = [
        item for item in diagnostics if item.get("file_name") == "sheet-scan.png"
    ]
    assert image_diag
    assert image_diag[0]["extraction_mode"] == "ocr_failed"
    assert image_diag[0]["status"] == "failed"


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)

    return buffer.getvalue()


def _docx_bytes(text: str) -> bytes:
    content_types = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>
  <Default Extension=\"xml\" ContentType=\"application/xml\"/>
  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>
</Types>
"""
    relationships = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"></Relationships>
"""
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>" + text + "</w:t></w:r></w:p></w:body></w:document>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document_xml)

    return buffer.getvalue()

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import zipfile

from pypdf import PdfWriter

from atlas_core.services.document_intake_service import (
    DocumentIntakeService,
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
    assert result.import_summary["unsupported_file_count"] == 1
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

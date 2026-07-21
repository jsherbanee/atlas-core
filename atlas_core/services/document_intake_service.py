"""Deterministic local package intake service for Phase 2 plan review."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import uuid
from typing import Any, Protocol
import zipfile
from xml.etree import ElementTree

from atlas_core.contracts import PlanReviewRequest
from atlas_core.contracts.upload_policy import GIB, bid_package_upload_policy
from atlas_core.domain.document_intake import (
    DocumentIntakeSnapshot,
    IntakeSourceReference,
)
from atlas_core.parsers.drawing_parser import extract_drawing_sheet_candidates
from atlas_core.parsers.schedule_parser import (
    detect_schedule_like_pages,
    extract_device_schedules_from_csv_files,
    extract_equipment_candidates,
)
from atlas_core.parsers.spec_parser import extract_specification_section_candidates
from atlas_core.services.pdf_text_extraction_service import PdfTextExtractionService
from atlas_core.services.plan_review_application_service import (
    PlanReviewApplicationService,
)


@dataclass
class PackageDiscoveryResult:
    package_path: Path
    metadata_path: Path | None
    drawing_files: list[Path]
    specification_files: list[Path]
    schedule_files: list[Path]
    addenda_files: list[Path]
    image_files: list[Path]
    unsupported_files: list[Path]


@dataclass
class UploadedIntakeFile:
    name: str
    data: bytes


@dataclass
class UploadSessionResult:
    session_id: str
    package_path: Path
    snapshot_path: Path
    snapshot: DocumentIntakeSnapshot
    import_summary: dict[str, Any]
    warnings: list[str]


@dataclass
class UploadInspectionResult:
    accepted_files: list[UploadedIntakeFile]
    diagnostics: list[dict[str, Any]]
    warnings: list[str]


class LocalOcrEngine(Protocol):
    def is_available(self) -> bool: ...

    def ocr_pdf_pages(
        self,
        pdf_path: Path,
        page_numbers: list[int],
    ) -> tuple[dict[int, str], list[str]]: ...

    def ocr_image_file(self, image_path: Path) -> tuple[str, list[str]]: ...


class NoOpLocalOcrEngine:
    def is_available(self) -> bool:
        return False

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


def _extraction_mode(
    *,
    status: str,
    pages_with_embedded_text: int,
    pages_with_ocr_text: int,
) -> str:
    if status == "failed":
        return "ocr_failed"

    if pages_with_ocr_text > 0 and pages_with_embedded_text > 0:
        return "mixed_embedded_and_ocr"

    if pages_with_ocr_text > 0:
        return "ocr_derived_text"

    if pages_with_embedded_text > 0:
        return "embedded_text"

    if status == "requires_ocr":
        return "requires_ocr"

    if status == "unsupported":
        return "unsupported"

    return "unknown"


class DocumentIntakeService:
    ENGINE_VERSION = "document-intake-service/1.0.0"

    _DRAWING_HINTS = ("draw", "sheet", "plan", "elevation", "detail", "av-")
    _SPEC_HINTS = ("spec", "section", "division", "27 ")
    _SCHEDULE_HINTS = ("schedule", "device", "equipment", "matrix")
    _ADDENDA_HINTS = ("addenda", "addendum", "add-")
    _IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}
    _SCHEDULE_EXTENSIONS = {".xlsx", ".xls", ".csv"}
    _DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".rtf"}
    _UPLOAD_POLICY = bid_package_upload_policy()
    _SUPPORTED_EXTENSIONS = _UPLOAD_POLICY.extensions_with_dot
    _MAX_UPLOAD_FILE_BYTES = _UPLOAD_POLICY.max_file_size_bytes
    _MAX_ARCHIVE_ENTRY_COUNT = 500
    _MAX_ARCHIVE_UNCOMPRESSED_BYTES = 2 * GIB
    _MAX_ARCHIVE_DEPTH = 3
    _SYSTEM_ARTIFACT_NAMES = {".ds_store"}
    _SYSTEM_ARTIFACT_PREFIXES = {"__macosx/"}

    def __init__(
        self,
        pdf_text_extraction_service: PdfTextExtractionService | None = None,
        local_ocr_engine: LocalOcrEngine | None = None,
        enable_local_ocr: bool = False,
    ) -> None:
        self.pdf_text_extraction_service = (
            pdf_text_extraction_service or PdfTextExtractionService()
        )
        self.local_ocr_engine = local_ocr_engine or NoOpLocalOcrEngine()
        self.enable_local_ocr = enable_local_ocr

    def discover_package(self, package_path: str | Path) -> PackageDiscoveryResult:
        root = Path(package_path)
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Package folder not found: {root}")

        metadata_path = root / "metadata.json"
        return PackageDiscoveryResult(
            package_path=root,
            metadata_path=metadata_path if metadata_path.exists() else None,
            drawing_files=self._sorted_files(root / "drawings"),
            specification_files=self._sorted_files(root / "specifications"),
            schedule_files=self._sorted_files(root / "schedules"),
            addenda_files=self._sorted_files(root / "addenda"),
            image_files=self._sorted_files(root / "images"),
            unsupported_files=self._sorted_files(root / "unsupported"),
        )

    def build_session_package_from_uploads(
        self,
        uploaded_files: list[UploadedIntakeFile],
        uploads_root: str | Path = "outputs/uploads",
        session_id: str | None = None,
    ) -> UploadSessionResult:
        if not uploaded_files:
            raise ValueError("No files were uploaded")

        inspection = self.inspect_uploaded_files(uploaded_files)
        normalized_files = [
            (item.name, item.data) for item in list(inspection.accepted_files)
        ]
        warnings = list(inspection.warnings)
        rejected_diagnostics = [
            item
            for item in list(inspection.diagnostics)
            if not bool(item.get("accepted", False))
        ]
        if not normalized_files:
            raise ValueError("No valid files were uploaded")
        active_session_id = session_id or f"session-{uuid.uuid4().hex[:12]}"
        session_root = Path(uploads_root) / active_session_id
        self._ensure_package_folders(session_root)

        drawing_count = 0
        specification_count = 0
        schedule_count = 0
        addenda_count = 0
        image_count = 0
        unsupported_file_count = 0

        metadata_written = False
        for upload_name, upload_data in normalized_files:
            target_group = self._classify_upload_path(upload_name)
            destination = self._write_classified_file(
                session_root,
                target_group,
                upload_name,
                upload_data,
            )

            if target_group == "drawings":
                drawing_count += 1
            elif target_group == "specifications":
                specification_count += 1
            elif target_group == "schedules":
                schedule_count += 1
            elif target_group == "addenda":
                addenda_count += 1
            elif target_group == "images":
                image_count += 1
            elif target_group == "unsupported":
                unsupported_file_count += 1

            if target_group == "metadata" and not metadata_written:
                if destination.suffix.lower() == ".json":
                    metadata_payload = self._normalize_metadata_file(destination)
                    if metadata_payload is not None:
                        with (session_root / "metadata.json").open(
                            "w", encoding="utf-8"
                        ) as file:
                            json.dump(metadata_payload, file, indent=2, sort_keys=True)

                        metadata_written = True

        summary = {
            "drawing_count": drawing_count,
            "specification_count": specification_count,
            "schedule_count": schedule_count,
            "addenda_count": addenda_count,
            "image_count": image_count,
            "unsupported_file_count": unsupported_file_count,
            "uploaded_file_count": len(normalized_files),
            "rejected_file_count": len(rejected_diagnostics),
            "rejected_file_diagnostics": rejected_diagnostics,
            "extraction_warnings": sorted(set(warnings)),
        }

        snapshot = self.build_snapshot(session_root)
        snapshot.import_summary = {
            **snapshot.import_summary,
            **summary,
            "package_location": str(session_root),
            "session_id": active_session_id,
        }
        snapshot.warnings = sorted(set([*snapshot.warnings, *warnings]))
        snapshot_path = self.write_snapshot(snapshot, session_root)
        return UploadSessionResult(
            session_id=active_session_id,
            package_path=session_root,
            snapshot_path=snapshot_path,
            snapshot=snapshot,
            import_summary=dict(snapshot.import_summary),
            warnings=list(snapshot.warnings),
        )

    def inspect_uploaded_files(
        self,
        uploaded_files: list[UploadedIntakeFile],
    ) -> UploadInspectionResult:
        normalized_files, warnings = self._flatten_uploads(uploaded_files)
        diagnostics: list[dict[str, Any]] = []
        accepted_files: list[UploadedIntakeFile] = []

        seen_names: set[str] = set()
        seen_hashes: set[str] = set()
        for name, data in normalized_files:
            suffix = Path(name).suffix.lower()
            source_hash = hashlib.sha1(data).hexdigest()
            duplicate_name = name.lower() in seen_names
            duplicate_hash = source_hash in seen_hashes
            file_size = len(data)
            unsupported = suffix not in self._SUPPORTED_EXTENSIONS or suffix == ".zip"
            policy_result = self._UPLOAD_POLICY.validate_file(
                name=name,
                size_bytes=file_size,
            )

            errors: list[str] = []
            for message in policy_result.messages:
                if message == "Queued for processing":
                    continue
                if message.startswith("Unsupported file type:"):
                    errors.append("unsupported extension")
                    continue
                if message == "File is empty.":
                    errors.append("empty file")
                    continue
                errors.append(message)
            if unsupported and "unsupported extension" not in errors:
                errors.append("unsupported extension")
            if duplicate_name:
                errors.append("duplicate filename")
            if duplicate_hash:
                errors.append("duplicate source hash")

            accepted = not errors
            if accepted:
                accepted_files.append(UploadedIntakeFile(name=name, data=data))

            diagnostics.append(
                {
                    "name": name,
                    "extension": suffix,
                    "size_bytes": file_size,
                    "source_hash": source_hash,
                    "source_type": (
                        "zip_entry" if "/" in name or "\\" in name else "file"
                    ),
                    "zip_source": (
                        Path(name).parts[0].lower().endswith(".zip")
                        if Path(name).parts
                        else False
                    ),
                    "duplicate_name": duplicate_name,
                    "duplicate_source_hash": duplicate_hash,
                    "accepted": accepted,
                    "severity": "error" if errors else "informational",
                    "messages": errors or ["accepted"],
                }
            )

            seen_names.add(name.lower())
            seen_hashes.add(source_hash)

        return UploadInspectionResult(
            accepted_files=accepted_files,
            diagnostics=diagnostics,
            warnings=warnings,
        )

    def build_snapshot(self, package_path: str | Path) -> DocumentIntakeSnapshot:
        discovery = self.discover_package(package_path)
        metadata = self._load_metadata(discovery)
        warnings: list[str] = []

        page_records: list[dict[str, Any]] = []
        source_references: list[dict[str, Any]] = []
        file_diagnostics: list[dict[str, Any]] = []
        schedule_rows_by_file: dict[str, int] = {}

        for group_name, files in (
            ("drawings", discovery.drawing_files),
            ("specifications", discovery.specification_files),
            ("schedules", discovery.schedule_files),
            ("addenda", discovery.addenda_files),
            ("images", discovery.image_files),
        ):
            for file_path in files:
                file_pages, file_warnings, diagnostic = self._extract_document_pages(
                    file_path,
                    group_name,
                )
                page_records.extend(file_pages)
                warnings.extend(file_warnings)
                file_diagnostics.append(
                    {
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                        "document_group": group_name,
                        **diagnostic,
                    }
                )

        raw_sheets = extract_drawing_sheet_candidates(
            [
                page
                for page in page_records
                if page.get("document_group") in {"drawings", "addenda"}
            ]
        )
        raw_sections = extract_specification_section_candidates(
            [
                page
                for page in page_records
                if page.get("document_group") in {"specifications", "addenda"}
            ]
        )

        csv_schedules, schedule_warnings = extract_device_schedules_from_csv_files(
            discovery.schedule_files
        )
        warnings.extend(schedule_warnings)
        for schedule in csv_schedules:
            source_file = str(schedule.get("source_file") or "")
            if source_file:
                schedule_rows_by_file[source_file] = len(
                    list(schedule.get("rows") or [])
                )

        pdf_schedules = detect_schedule_like_pages(
            [page for page in page_records if page.get("document_group") == "schedules"]
        )
        raw_device_schedules = self._dedupe_dicts([*csv_schedules, *pdf_schedules])

        for diagnostic in file_diagnostics:
            if diagnostic.get("document_group") != "schedules":
                continue
            if str(diagnostic.get("status") or "") == "unsupported":
                continue

            file_name = str(diagnostic.get("file_name") or "")
            row_count = schedule_rows_by_file.get(file_name)
            if row_count is not None:
                diagnostic["rows_extracted"] = row_count

        for warning in schedule_warnings:
            warning_lower = warning.lower()
            if (
                "unsupported" not in warning_lower
                and "could not be parsed" not in warning_lower
            ):
                continue

            file_name = (
                warning.split(" ", 2)[2].split(" ", 1)[0]
                if warning.startswith("Schedule file ")
                else ""
            )
            if not file_name:
                continue

            matched = False
            for diagnostic in file_diagnostics:
                if str(diagnostic.get("file_name") or "") != file_name:
                    continue
                diagnostic["status"] = "unsupported"
                diagnostic["warnings"] = sorted(
                    set(list(diagnostic.get("warnings") or []) + [warning])
                )
                matched = True
                break

            if not matched:
                file_diagnostics.append(
                    {
                        "file_name": file_name,
                        "file_path": str(
                            discovery.package_path / "schedules" / file_name
                        ),
                        "document_group": "schedules",
                        "status": "unsupported",
                        "extraction_mode": "unsupported",
                        "ocr_attempted": False,
                        "total_pages": None,
                        "pages_with_embedded_text": 0,
                        "pages_with_ocr_text": 0,
                        "pages_without_embedded_text": 0,
                        "requires_ocr": False,
                        "warnings": [warning],
                    }
                )

        equipment_candidates = self._equipment_candidates_with_schedule_context(
            page_records,
            raw_device_schedules,
        )
        self._attach_location_context(
            equipment_candidates=equipment_candidates,
            raw_sheets=raw_sheets,
            raw_sections=raw_sections,
        )

        for sheet in raw_sheets:
            source_references.append(
                IntakeSourceReference(
                    source_file=str(sheet.get("source_file") or ""),
                    page_number=self._int_or_none(sheet.get("page_number")),
                    sheet_number=str(sheet.get("sheet_number") or "") or None,
                    text_excerpt=str(sheet.get("source_excerpt") or "") or None,
                ).to_dict()
            )

        for section in raw_sections:
            source_references.append(
                IntakeSourceReference(
                    source_file=str(section.get("source_file") or ""),
                    page_number=self._int_or_none(section.get("page_number")),
                    section_number=str(section.get("section_number") or "") or None,
                    text_excerpt=str(section.get("source_excerpt") or "") or None,
                ).to_dict()
            )

        for candidate in equipment_candidates:
            source_ref = dict(candidate.get("source_ref") or {})
            source_references.append(
                IntakeSourceReference(
                    source_file=str(source_ref.get("source_file") or ""),
                    page_number=self._int_or_none(source_ref.get("page_number")),
                    text_excerpt=str(source_ref.get("text_excerpt") or "") or None,
                ).to_dict()
            )

        package_path_value = str(discovery.package_path.resolve())
        snapshot_id = f"intake-{hashlib.sha1(package_path_value.encode('utf-8')).hexdigest()[:12]}"

        for unsupported_file in discovery.unsupported_files:
            file_diagnostics.append(
                {
                    "file_name": unsupported_file.name,
                    "file_path": str(unsupported_file),
                    "document_group": "unsupported",
                    "status": "unsupported",
                    "extraction_mode": "unsupported",
                    "ocr_attempted": False,
                    "total_pages": None,
                    "pages_with_embedded_text": 0,
                    "pages_with_ocr_text": 0,
                    "pages_without_embedded_text": 0,
                    "requires_ocr": False,
                    "warnings": [f"{unsupported_file.name}: unsupported file format."],
                }
            )

        diagnostics_summary = self._build_extraction_diagnostics(
            file_diagnostics, warnings
        )

        return DocumentIntakeSnapshot(
            snapshot_id=snapshot_id,
            package_path=package_path_value,
            metadata=metadata,
            discovered_files={
                "drawings": [path.name for path in discovery.drawing_files],
                "specifications": [path.name for path in discovery.specification_files],
                "schedules": [path.name for path in discovery.schedule_files],
                "addenda": [path.name for path in discovery.addenda_files],
                "images": [path.name for path in discovery.image_files],
                "unsupported": [path.name for path in discovery.unsupported_files],
            },
            raw_pages=page_records,
            raw_sheets=raw_sheets,
            raw_sections=raw_sections,
            raw_device_schedules=raw_device_schedules,
            equipment_candidates=equipment_candidates,
            source_references=self._dedupe_dicts(source_references),
            warnings=sorted(set(warnings)),
            import_summary={
                "drawing_count": len(discovery.drawing_files),
                "specification_count": len(discovery.specification_files),
                "schedule_count": len(discovery.schedule_files),
                "addenda_count": len(discovery.addenda_files),
                "image_count": len(discovery.image_files),
                "unsupported_file_count": len(discovery.unsupported_files),
                **diagnostics_summary,
                "extraction_warnings": sorted(set(warnings)),
                "package_location": package_path_value,
            },
            created_by_engine_version=self.ENGINE_VERSION,
        )

    def write_snapshot(
        self,
        snapshot: DocumentIntakeSnapshot,
        output_dir: str | Path,
    ) -> Path:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = out_dir / "intake_snapshot.json"
        with snapshot_path.open("w", encoding="utf-8") as file:
            json.dump(snapshot.to_dict(), file, indent=2, sort_keys=True)

        return snapshot_path

    def load_snapshot(self, snapshot_path: str | Path) -> DocumentIntakeSnapshot:
        path = Path(snapshot_path)
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)

        return DocumentIntakeSnapshot.from_dict(payload)

    def build_plan_review_request(
        self,
        snapshot: DocumentIntakeSnapshot,
    ) -> PlanReviewRequest:
        metadata = snapshot.metadata
        package_name = Path(snapshot.package_path).name
        review_id = str(metadata.get("review_id") or f"{package_name}-review")
        project_id = str(metadata.get("project_id") or package_name)
        name = str(metadata.get("name") or metadata.get("project_name") or package_name)

        return PlanReviewRequest(
            review_id=review_id,
            project_id=project_id,
            name=name,
            raw_pages=list(snapshot.raw_pages),
            raw_sheets=list(snapshot.raw_sheets),
            raw_sections=list(snapshot.raw_sections),
            raw_device_schedules=list(snapshot.raw_device_schedules),
        )

    def run_review_from_snapshot(
        self,
        snapshot: DocumentIntakeSnapshot,
    ) -> Any:
        request = self.build_plan_review_request(snapshot)
        return PlanReviewApplicationService().run(request).result

    def _extract_pdf_pages(
        self,
        pdf_path: Path,
        group_name: str,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        try:
            pages = self.pdf_text_extraction_service.extract_pages(pdf_path)
        except Exception as exc:
            warnings.append(f"{pdf_path.name}: PDF extraction failed ({exc}).")
            return [], warnings
        page_records: list[dict[str, Any]] = []
        missing_text_pages = [page.page_number for page in pages if not page.has_text]
        if pages and not any(page.has_text for page in pages):
            warnings.append(
                f"{pdf_path.name}: no embedded text found. OCR is required for extraction."
            )

        ocr_page_text: dict[int, str] = {}
        if (
            self.enable_local_ocr
            and self.local_ocr_engine.is_available()
            and missing_text_pages
        ):
            extracted_text_map, ocr_warnings = self.local_ocr_engine.ocr_pdf_pages(
                pdf_path,
                missing_text_pages,
            )
            ocr_page_text = dict(extracted_text_map)
            warnings.extend(ocr_warnings)
            if not ocr_page_text:
                warnings.append(
                    f"{pdf_path.name}: OCR attempted but no text was extracted from non-embedded pages."
                )
            else:
                warnings.append(
                    f"{pdf_path.name}: OCR-derived text extracted for {len(ocr_page_text)} page(s); verify quality before downstream decisions."
                )

        for page in pages:
            record = page.to_dict()
            if not record.get("has_text") and page.page_number in ocr_page_text:
                ocr_text = str(ocr_page_text.get(page.page_number) or "").strip()
                if ocr_text:
                    record["text"] = ocr_text
                    record["has_text"] = True
                    record["ocr_derived"] = True
                    record["text_source"] = "ocr"
                else:
                    record["ocr_derived"] = False
                    record["text_source"] = "none"
            else:
                record["ocr_derived"] = False
                record["text_source"] = "embedded"

            record["document_group"] = group_name
            record["source_path"] = str(pdf_path)
            page_records.append(record)

        return page_records, warnings

    def _extract_document_pages(
        self,
        file_path: Path,
        group_name: str,
    ) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            pages, warnings = self._extract_pdf_pages(file_path, group_name)
            return pages, warnings, self._file_status_from_pages(pages, warnings)

        if suffix == ".docx":
            text = self._extract_docx_text(file_path)
            pages, warnings = self._single_page_record(file_path, group_name, text)
            return pages, warnings, self._file_status_from_pages(pages, warnings)

        if suffix in {".csv", ".xlsx", ".xls"}:
            return (
                [],
                [],
                {
                    "status": "extracted",
                    "extraction_mode": "embedded_text",
                    "ocr_attempted": False,
                    "total_pages": None,
                    "pages_with_embedded_text": 0,
                    "pages_with_ocr_text": 0,
                    "pages_without_embedded_text": 0,
                    "requires_ocr": False,
                    "warnings": [],
                },
            )

        if suffix in {".txt", ".rtf"}:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            pages, warnings = self._single_page_record(file_path, group_name, text)
            return pages, warnings, self._file_status_from_pages(pages, warnings)

        if suffix == ".doc":
            text = file_path.read_text(encoding="latin-1", errors="ignore")
            normalized = " ".join(text.split())
            if not normalized:
                warning = f"{file_path.name}: DOC extraction is unsupported; provide DOCX or PDF."
                return (
                    [],
                    [warning],
                    {
                        "status": "unsupported",
                        "extraction_mode": "unsupported",
                        "ocr_attempted": False,
                        "total_pages": 1,
                        "pages_with_embedded_text": 0,
                        "pages_with_ocr_text": 0,
                        "pages_without_embedded_text": 1,
                        "requires_ocr": False,
                        "warnings": [warning],
                    },
                )

            warning = f"{file_path.name}: DOC extraction is best-effort; provide DOCX or PDF for reliable parsing."
            pages, _ = self._single_page_record(file_path, group_name, text)
            status = self._file_status_from_pages(pages, [warning])
            return pages, [warning], status

        if suffix in self._IMAGE_EXTENSIONS:
            warning = f"{file_path.name}: This image contains no extractable embedded text. OCR support is required."
            if self.enable_local_ocr and self.local_ocr_engine.is_available():
                ocr_text, ocr_warnings = self.local_ocr_engine.ocr_image_file(file_path)
                warnings = [*ocr_warnings]
                if ocr_text.strip():
                    pages, page_warnings = self._single_page_record(
                        file_path,
                        group_name,
                        ocr_text,
                        text_source="ocr",
                    )
                    status = self._file_status_from_pages(
                        pages,
                        [*warnings, *page_warnings],
                    )
                    status["ocr_attempted"] = True
                    status["extraction_mode"] = "ocr_derived_text"
                    status["status"] = "extracted"
                    return pages, [*warnings, *page_warnings], status

                warnings.append(
                    f"{file_path.name}: OCR attempted but failed to extract usable text."
                )
                return (
                    [],
                    warnings,
                    {
                        "status": "failed",
                        "extraction_mode": "ocr_failed",
                        "ocr_attempted": True,
                        "total_pages": 1,
                        "pages_with_embedded_text": 0,
                        "pages_without_embedded_text": 1,
                        "requires_ocr": True,
                        "warnings": warnings,
                    },
                )

            return (
                [],
                [warning],
                {
                    "status": "requires_ocr",
                    "extraction_mode": "requires_ocr",
                    "ocr_attempted": False,
                    "total_pages": 1,
                    "pages_with_embedded_text": 0,
                    "pages_with_ocr_text": 0,
                    "pages_without_embedded_text": 1,
                    "requires_ocr": True,
                    "warnings": [warning],
                },
            )

        warning = f"{file_path.name}: unsupported document format for text extraction."
        return (
            [],
            [warning],
            {
                "status": "unsupported",
                "extraction_mode": "unsupported",
                "ocr_attempted": False,
                "total_pages": None,
                "pages_with_embedded_text": 0,
                "pages_with_ocr_text": 0,
                "pages_without_embedded_text": 0,
                "requires_ocr": False,
                "warnings": [warning],
            },
        )

    def _single_page_record(
        self,
        file_path: Path,
        group_name: str,
        text: str,
        text_source: str = "embedded",
    ) -> tuple[list[dict[str, Any]], list[str]]:
        record = {
            "page_number": 1,
            "text": text,
            "has_text": bool(text.strip()),
            "ocr_derived": text_source == "ocr",
            "text_source": text_source,
            "document_group": group_name,
            "source_path": str(file_path),
            "source_file": str(file_path),
        }
        warnings: list[str] = []
        if not text.strip():
            warnings.append(
                f"{file_path.name}: no extractable text found in file content."
            )

        return [record], warnings

    @staticmethod
    def _file_status_from_pages(
        pages: list[dict[str, Any]],
        warnings: list[str],
    ) -> dict[str, Any]:
        total_pages = len(pages)
        pages_with_text = sum(1 for page in pages if bool(page.get("has_text")))
        pages_without_text = max(total_pages - pages_with_text, 0)
        pages_with_ocr_text = sum(1 for page in pages if bool(page.get("ocr_derived")))
        pages_with_embedded_text = max(pages_with_text - pages_with_ocr_text, 0)

        if total_pages == 0:
            status = "failed"
        elif pages_with_text == total_pages:
            status = "extracted"
        elif pages_with_text == 0:
            status = "requires_ocr"
        else:
            status = "partial"

        return {
            "status": status,
            "extraction_mode": _extraction_mode(
                status=status,
                pages_with_embedded_text=pages_with_embedded_text,
                pages_with_ocr_text=pages_with_ocr_text,
            ),
            "ocr_attempted": pages_with_ocr_text > 0,
            "total_pages": total_pages,
            "pages_with_embedded_text": pages_with_embedded_text,
            "pages_with_ocr_text": pages_with_ocr_text,
            "pages_without_embedded_text": pages_without_text,
            "requires_ocr": status == "requires_ocr",
            "warnings": list(warnings),
        }

    @staticmethod
    def _build_extraction_diagnostics(
        file_diagnostics: list[dict[str, Any]],
        warnings: list[str],
    ) -> dict[str, Any]:
        total_pages = sum(
            int(item.get("total_pages") or 0)
            for item in file_diagnostics
            if item.get("total_pages") is not None
        )
        pages_with_embedded_text = sum(
            int(item.get("pages_with_embedded_text") or 0) for item in file_diagnostics
        )
        pages_with_ocr_text = sum(
            int(item.get("pages_with_ocr_text") or 0) for item in file_diagnostics
        )
        pages_without_embedded_text = sum(
            int(item.get("pages_without_embedded_text") or 0)
            for item in file_diagnostics
        )
        documents_requiring_ocr = sum(
            1 for item in file_diagnostics if bool(item.get("requires_ocr"))
        )

        return {
            "total_files": len(file_diagnostics),
            "total_pages": total_pages,
            "pages_with_embedded_text": pages_with_embedded_text,
            "pages_with_ocr_text": pages_with_ocr_text,
            "pages_without_embedded_text": pages_without_embedded_text,
            "documents_requiring_ocr": documents_requiring_ocr,
            "extraction_warning_count": len(sorted(set(warnings))),
            "file_diagnostics": file_diagnostics,
        }

    @staticmethod
    def _load_metadata(discovery: PackageDiscoveryResult) -> dict[str, Any]:
        if discovery.metadata_path is None:
            return {
                "name": discovery.package_path.name,
                "project_name": discovery.package_path.name,
            }

        with discovery.metadata_path.open(encoding="utf-8") as file:
            payload = json.load(file)

        if not isinstance(payload, dict):
            raise ValueError("metadata.json must contain an object")

        return payload

    @staticmethod
    def _sorted_files(folder_path: Path) -> list[Path]:
        if not folder_path.exists() or not folder_path.is_dir():
            return []

        return sorted(path for path in folder_path.rglob("*") if path.is_file())

    def _flatten_uploads(
        self,
        uploaded_files: list[UploadedIntakeFile],
    ) -> tuple[list[tuple[str, bytes]], list[str]]:
        flattened: list[tuple[str, bytes]] = []
        warnings: list[str] = []
        for uploaded_file in uploaded_files:
            flattened.extend(
                self._expand_upload_file(
                    uploaded_file.name,
                    uploaded_file.data,
                    warnings,
                )
            )

        return flattened, warnings

    def _expand_upload_file(
        self,
        name: str,
        data: bytes,
        warnings: list[str],
        depth: int = 0,
    ) -> list[tuple[str, bytes]]:
        if depth > self._MAX_ARCHIVE_DEPTH:
            warnings.append(f"{name}: nested archive depth limit reached; skipping.")
            return []

        suffix = Path(name).suffix.lower()
        if suffix != ".zip":
            return [(name, data)]

        expanded: list[tuple[str, bytes]] = []
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entry_count = 0
                total_uncompressed_size = 0
                seen_entries: set[str] = set()
                for info in archive.infolist():
                    if info.is_dir():
                        continue

                    entry_count += 1
                    if entry_count > self._MAX_ARCHIVE_ENTRY_COUNT:
                        warnings.append(
                            f"{name}: archive entry limit exceeded; remaining entries skipped."
                        )
                        break

                    entry_name = self._normalized_archive_entry(info.filename)
                    if entry_name is None:
                        warnings.append(
                            f"{name}: rejected unsafe archive path {info.filename}."
                        )
                        continue

                    if self._is_system_artifact(entry_name):
                        continue

                    if self._is_zip_symlink(info):
                        warnings.append(
                            f"{name}: symbolic link archive entry rejected ({entry_name})."
                        )
                        continue

                    if info.flag_bits & 0x1:
                        warnings.append(
                            f"{name}: encrypted archive entry rejected ({entry_name})."
                        )
                        continue

                    if entry_name in seen_entries:
                        warnings.append(
                            f"{name}: duplicate archive entry rejected ({entry_name})."
                        )
                        continue
                    seen_entries.add(entry_name)

                    total_uncompressed_size += int(info.file_size or 0)
                    if total_uncompressed_size > self._MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        warnings.append(
                            f"{name}: archive expansion size limit exceeded; remaining entries skipped."
                        )
                        break

                    inner_data = archive.read(info.filename)
                    logical_name = f"{name}/{entry_name}"
                    expanded.extend(
                        self._expand_upload_file(
                            logical_name,
                            inner_data,
                            warnings,
                            depth + 1,
                        )
                    )
        except zipfile.BadZipFile:
            warnings.append(f"{name}: could not unpack ZIP archive.")

        return expanded

    @classmethod
    def _normalized_archive_entry(cls, value: str) -> str | None:
        normalized = value.replace("\\", "/").strip()
        if not normalized or normalized.startswith("/"):
            return None

        parts: list[str] = []
        for part in normalized.split("/"):
            stripped = part.strip()
            if not stripped or stripped == ".":
                continue
            if stripped == "..":
                return None
            parts.append(stripped)

        if not parts:
            return None
        return "/".join(parts)

    @classmethod
    def _is_system_artifact(cls, normalized_entry: str) -> bool:
        lowered = normalized_entry.lower()
        if any(lowered.startswith(prefix) for prefix in cls._SYSTEM_ARTIFACT_PREFIXES):
            return True
        return Path(lowered).name in cls._SYSTEM_ARTIFACT_NAMES

    @staticmethod
    def _is_zip_symlink(info: zipfile.ZipInfo) -> bool:
        return ((info.external_attr >> 16) & 0o170000) == 0o120000

    def _ensure_package_folders(self, package_root: Path) -> None:
        for folder_name in (
            "drawings",
            "specifications",
            "schedules",
            "addenda",
            "images",
            "metadata",
            "unsupported",
        ):
            (package_root / folder_name).mkdir(parents=True, exist_ok=True)

    def _classify_upload_path(self, upload_name: str) -> str:
        file_name = Path(upload_name).name
        suffix = Path(file_name).suffix.lower()
        lowered = file_name.lower()

        if suffix in self._IMAGE_EXTENSIONS:
            return "images"

        if suffix in {".json"}:
            return "metadata"

        if suffix in self._SCHEDULE_EXTENSIONS:
            return "schedules"

        if suffix not in self._SUPPORTED_EXTENSIONS:
            return "unsupported"

        if any(token in lowered for token in self._ADDENDA_HINTS):
            return "addenda"

        if any(token in lowered for token in self._SCHEDULE_HINTS):
            return "schedules"

        if re.search(
            r"(?:^|[^0-9])\d{2}[_\-\s]?\d{2}[_\-\s]?\d{2}(?:[^0-9]|$)", lowered
        ):
            return "specifications"

        if any(token in lowered for token in self._SPEC_HINTS):
            return "specifications"

        if any(token in lowered for token in self._DRAWING_HINTS):
            return "drawings"

        if suffix in self._DOCUMENT_EXTENSIONS:
            return "drawings"

        return "unsupported"

    def _write_classified_file(
        self,
        package_root: Path,
        target_group: str,
        upload_name: str,
        upload_data: bytes,
    ) -> Path:
        normalized_name = upload_name.replace("\\", "/")
        relative_parts = [part for part in normalized_name.split("/") if part]
        if not relative_parts:
            relative_parts = [Path(upload_name).name]
        safe_parts: list[str] = []
        for part in relative_parts:
            stripped = part.strip()
            if not stripped or stripped in {".", ".."}:
                continue
            safe_parts.append(stripped)
        if not safe_parts:
            safe_parts = [Path(upload_name).name]

        destination = package_root / target_group
        for part in safe_parts[:-1]:
            destination = destination / part
        destination.mkdir(parents=True, exist_ok=True)
        destination = destination / safe_parts[-1]
        destination = self._resolve_duplicate_path(destination)
        destination.write_bytes(upload_data)
        return destination

    @staticmethod
    def _resolve_duplicate_path(path: Path) -> Path:
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1
        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate

            counter += 1

    @staticmethod
    def _normalize_metadata_file(path: Path) -> dict[str, Any] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        return payload

    @staticmethod
    def _extract_docx_text(path: Path) -> str:
        try:
            with zipfile.ZipFile(path) as archive:
                xml_bytes = archive.read("word/document.xml")
        except zipfile.BadZipFile, KeyError:
            return ""

        root = ElementTree.fromstring(xml_bytes)
        namespaces = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        }
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", namespaces):
            runs = [node.text or "" for node in paragraph.findall(".//w:t", namespaces)]
            text = "".join(runs).strip()
            if text:
                paragraphs.append(text)

        return "\n".join(paragraphs)

    @staticmethod
    def _dedupe_dicts(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        for value in values:
            marker = tuple(
                sorted((str(key), repr(item)) for key, item in value.items())
            )
            if marker in seen:
                continue

            seen.add(marker)
            result.append(value)

        return result

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if isinstance(value, int):
            return value

        return None

    @staticmethod
    def _equipment_candidates_with_schedule_context(
        page_records: list[dict[str, Any]],
        raw_device_schedules: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        candidates = extract_equipment_candidates(page_records)
        for schedule in raw_device_schedules:
            source_file = str(schedule.get("source_file") or "")
            for row in list(schedule.get("rows") or []):
                row_text = " ".join(str(value or "") for value in row.values()).strip()
                if not row_text:
                    continue

                row_candidates = extract_equipment_candidates(
                    [
                        {
                            "source_file": source_file,
                            "page_number": schedule.get("page_number"),
                            "text": row_text,
                        }
                    ]
                )
                for candidate in row_candidates:
                    candidate["source_ref"]["schedule_id"] = schedule.get("schedule_id")
                    candidates.append(candidate)

        return DocumentIntakeService._dedupe_dicts(candidates)

    @staticmethod
    def _attach_location_context(
        equipment_candidates: list[dict[str, Any]],
        raw_sheets: list[dict[str, Any]],
        raw_sections: list[dict[str, Any]],
    ) -> None:
        by_source_page: dict[tuple[str, int | None], dict[str, str]] = {}
        for sheet in raw_sheets:
            key = (str(sheet.get("source_file") or ""), sheet.get("page_number"))
            by_source_page.setdefault(key, {})["sheet_number"] = str(
                sheet.get("sheet_number") or ""
            )

        for section in raw_sections:
            key = (str(section.get("source_file") or ""), section.get("page_number"))
            by_source_page.setdefault(key, {})["section_number"] = str(
                section.get("section_number") or ""
            )

        for candidate in equipment_candidates:
            source_ref = dict(candidate.get("source_ref") or {})
            source_file = str(source_ref.get("source_file") or "")
            page_number = source_ref.get("page_number")
            location = by_source_page.get((source_file, page_number), {})
            if "sheet_number" in location:
                source_ref["sheet_number"] = location["sheet_number"]
            if "section_number" in location:
                source_ref["section_number"] = location["section_number"]
            source_ref["detected_location"] = candidate.get("category_hint")
            candidate["source_ref"] = source_ref

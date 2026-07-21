"""Shared upload policy contracts for bid-package intake."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

MIB = 1024 * 1024
GIB = 1024 * 1024 * 1024

BID_PACKAGE_UPLOAD_MAX_FILE_MIB = 200
BID_PACKAGE_UPLOAD_MAX_FILE_BYTES = BID_PACKAGE_UPLOAD_MAX_FILE_MIB * MIB
BID_PACKAGE_UPLOAD_MAX_BATCH_BYTES = GIB
BID_PACKAGE_UPLOAD_MAX_FILES = 50
BID_PACKAGE_UPLOAD_MAX_FILE_LABEL = "200 MiB"
BID_PACKAGE_UPLOAD_MAX_BATCH_LABEL = "1 GiB"
BID_PACKAGE_UPLOAD_ENV_VAR = "ATLAS_BID_PACKAGE_MAX_UPLOAD_MIB"

BID_PACKAGE_UPLOAD_EXTENSIONS: tuple[str, ...] = (
    "pdf",
    "docx",
    "doc",
    "xlsx",
    "xls",
    "csv",
    "jpg",
    "jpeg",
    "png",
    "tif",
    "tiff",
    "txt",
    "rtf",
    "zip",
)

BID_PACKAGE_UPLOAD_FORMATS_LABEL = (
    "PDF, DOCX, DOC, XLSX, XLS, CSV, JPG, JPEG, PNG, TIF, TIFF, TXT, RTF, ZIP"
)


@dataclass(frozen=True)
class UploadValidationResult:
    accepted: bool
    messages: tuple[str, ...]

    @property
    def message(self) -> str:
        return "; ".join(self.messages)


@dataclass(frozen=True)
class UploadBatchFile:
    name: str
    size_bytes: int
    identity_key: str = ""


@dataclass(frozen=True)
class UploadBatchFileResult:
    name: str
    size_bytes: int
    identity_key: str
    accepted: bool
    messages: tuple[str, ...]
    reason_codes: tuple[str, ...]
    batch_size_if_included_bytes: int | None = None

    @property
    def message(self) -> str:
        return "; ".join(self.messages)


@dataclass(frozen=True)
class UploadBatchValidationResult:
    files: tuple[UploadBatchFileResult, ...]
    selected_file_count: int
    selected_size_bytes: int
    accepted_file_count: int
    accepted_size_bytes: int
    max_batch_size_bytes: int
    max_files_per_batch: int

    @property
    def accepted_files(self) -> tuple[UploadBatchFileResult, ...]:
        return tuple(item for item in self.files if item.accepted)

    @property
    def rejected_files(self) -> tuple[UploadBatchFileResult, ...]:
        return tuple(item for item in self.files if not item.accepted)

    @property
    def accepted(self) -> bool:
        return not self.rejected_files

    @property
    def remaining_batch_capacity_bytes(self) -> int:
        return max(0, self.max_batch_size_bytes - self.accepted_size_bytes)

    @property
    def selected_summary_label(self) -> str:
        file_label = "file" if self.selected_file_count == 1 else "files"
        return (
            f"{self.selected_file_count} {file_label} selected · "
            f"{format_binary_size(self.selected_size_bytes)} of "
            f"{format_binary_size(self.max_batch_size_bytes)}"
        )

    @property
    def remaining_capacity_label(self) -> str:
        return (
            f"{format_binary_size(self.remaining_batch_capacity_bytes)} "
            "remaining in this batch"
        )


@dataclass(frozen=True)
class UploadPolicy:
    supported_extensions: tuple[str, ...]
    max_file_size_bytes: int
    max_batch_size_bytes: int
    max_files_per_batch: int
    max_file_size_label: str
    max_batch_size_label: str
    formats_label: str

    @property
    def streamlit_types(self) -> list[str]:
        return list(self.supported_extensions)

    @property
    def help_text(self) -> str:
        return (
            f"Up to {self.max_file_size_label} per file • "
            f"{self.max_batch_size_label} per batch • "
            f"{self.max_files_per_batch} files maximum • "
            f"{self.formats_label}"
        )

    @property
    def extensions_with_dot(self) -> set[str]:
        return {f".{extension}" for extension in self.supported_extensions}

    @property
    def user_facing_limits(self) -> dict[str, str]:
        return {
            "max_file_size": self.max_file_size_label,
            "max_batch_size": self.max_batch_size_label,
            "max_files_per_batch": str(self.max_files_per_batch),
            "formats": self.formats_label,
        }

    def validate_file(
        self,
        *,
        name: str,
        size_bytes: int,
        mime_type: str | None = None,
    ) -> UploadValidationResult:
        _ = mime_type
        messages: list[str] = []
        normalized_name = str(name or "").strip()
        suffix = Path(normalized_name).suffix.lower().lstrip(".")

        if not normalized_name:
            messages.append("Filename is required.")
        if suffix not in set(self.supported_extensions):
            messages.append(f"Unsupported file type: .{suffix or 'unknown'}")
        if size_bytes <= 0:
            messages.append("File is empty.")
        if size_bytes > self.max_file_size_bytes:
            messages.append(
                "File exceeds the per-file upload limit. "
                f"File is {format_binary_size(size_bytes)} "
                f"({size_bytes:,} bytes). "
                f"The maximum file size is {self.max_file_size_label} "
                f"({self.max_file_size_bytes:,} bytes)."
            )

        if messages:
            return UploadValidationResult(False, tuple(messages))
        return UploadValidationResult(True, ("Queued for processing",))

    def validate_batch(
        self,
        files: list[UploadBatchFile],
    ) -> UploadBatchValidationResult:
        accepted_size = 0
        accepted_count = 0
        results: list[UploadBatchFileResult] = []

        for file_item in files:
            file_result = self.validate_file(
                name=file_item.name,
                size_bytes=file_item.size_bytes,
            )
            messages = [
                message
                for message in file_result.messages
                if message != "Queued for processing"
            ]
            reason_codes: list[str] = []
            for message in messages:
                if message.startswith("Unsupported file type:"):
                    reason_codes.append("unsupported_type")
                elif message == "File is empty.":
                    reason_codes.append("empty_file")
                elif message.startswith("File exceeds the per-file"):
                    reason_codes.append("per_file_limit")
                elif message == "Filename is required.":
                    reason_codes.append("filename")

            projected_size = accepted_size + int(file_item.size_bytes)
            if file_result.accepted:
                if accepted_count >= self.max_files_per_batch:
                    messages.append(
                        "This file exceeds the batch file-count limit. "
                        f"The maximum files per batch is {self.max_files_per_batch}."
                    )
                    reason_codes.append("batch_file_count")
                elif projected_size > self.max_batch_size_bytes:
                    messages.append(
                        "This file would increase the batch to "
                        f"{format_binary_size(projected_size)}. "
                        "The maximum batch size is "
                        f"{self.max_batch_size_label}."
                    )
                    reason_codes.append("batch_size_limit")
                else:
                    accepted_count += 1
                    accepted_size = projected_size

            accepted = not messages
            results.append(
                UploadBatchFileResult(
                    name=file_item.name,
                    size_bytes=file_item.size_bytes,
                    identity_key=file_item.identity_key,
                    accepted=accepted,
                    messages=tuple(messages or ["Accepted"]),
                    reason_codes=tuple(reason_codes),
                    batch_size_if_included_bytes=(
                        projected_size if "batch_size_limit" in reason_codes else None
                    ),
                )
            )

        return UploadBatchValidationResult(
            files=tuple(results),
            selected_file_count=len(files),
            selected_size_bytes=sum(int(item.size_bytes) for item in files),
            accepted_file_count=accepted_count,
            accepted_size_bytes=accepted_size,
            max_batch_size_bytes=self.max_batch_size_bytes,
            max_files_per_batch=self.max_files_per_batch,
        )


def bid_package_upload_policy(
    environ: Mapping[str, str] | None = None,
) -> UploadPolicy:
    max_file_mib = BID_PACKAGE_UPLOAD_MAX_FILE_MIB
    if environ is not None:
        configured = str(environ.get(BID_PACKAGE_UPLOAD_ENV_VAR) or "").strip()
        if configured:
            parsed = _positive_int(configured)
            if parsed is not None:
                max_file_mib = parsed

    max_file_size_bytes = max_file_mib * MIB
    return UploadPolicy(
        supported_extensions=BID_PACKAGE_UPLOAD_EXTENSIONS,
        max_file_size_bytes=max_file_size_bytes,
        max_batch_size_bytes=BID_PACKAGE_UPLOAD_MAX_BATCH_BYTES,
        max_files_per_batch=BID_PACKAGE_UPLOAD_MAX_FILES,
        max_file_size_label=format_binary_size(max_file_size_bytes),
        max_batch_size_label=format_binary_size(BID_PACKAGE_UPLOAD_MAX_BATCH_BYTES),
        formats_label=BID_PACKAGE_UPLOAD_FORMATS_LABEL,
    )


def format_binary_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    if abs(size_bytes) >= GIB:
        return _format_unit(size_bytes / GIB, "GiB")
    if abs(size_bytes) >= MIB:
        return _format_unit(size_bytes / MIB, "MiB")
    if abs(size_bytes) >= 1024:
        return _format_unit(size_bytes / 1024, "KiB")
    return f"{size_bytes} B"


def _format_unit(value: float, unit: str) -> str:
    if value.is_integer():
        return f"{int(value)} {unit}"
    if value >= 10:
        return f"{value:.1f}".rstrip("0").rstrip(".") + f" {unit}"
    return f"{value:.2f}".rstrip("0").rstrip(".") + f" {unit}"


def _positive_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed

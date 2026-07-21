"""Shared upload policy contracts for bid-package intake."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

BID_PACKAGE_UPLOAD_MAX_MB = 200
BID_PACKAGE_UPLOAD_MAX_BYTES = BID_PACKAGE_UPLOAD_MAX_MB * 1_000_000
BID_PACKAGE_UPLOAD_MAX_LABEL = "200 MB per file"
BID_PACKAGE_UPLOAD_ENV_VAR = "ATLAS_BID_PACKAGE_MAX_UPLOAD_MB"

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
class UploadPolicy:
    supported_extensions: tuple[str, ...]
    max_file_size_bytes: int
    max_file_size_label: str
    formats_label: str

    @property
    def streamlit_types(self) -> list[str]:
        return list(self.supported_extensions)

    @property
    def help_text(self) -> str:
        return f"Up to {self.max_file_size_label} • {self.formats_label}"

    @property
    def extensions_with_dot(self) -> set[str]:
        return {f".{extension}" for extension in self.supported_extensions}

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
                "File exceeds the upload limit. "
                f"File is {_format_decimal_mb(size_bytes)} MB "
                f"({size_bytes:,} bytes). "
                f"The maximum supported size is {self.max_file_size_label} "
                f"({self.max_file_size_bytes:,} bytes)."
            )

        if messages:
            return UploadValidationResult(False, tuple(messages))
        return UploadValidationResult(True, ("Queued for processing",))


def bid_package_upload_policy(
    environ: Mapping[str, str] | None = None,
) -> UploadPolicy:
    max_mb = BID_PACKAGE_UPLOAD_MAX_MB
    if environ is not None:
        configured = str(environ.get(BID_PACKAGE_UPLOAD_ENV_VAR) or "").strip()
        if configured:
            parsed = _positive_decimal_mb(configured)
            if parsed is not None:
                max_mb = parsed

    return UploadPolicy(
        supported_extensions=BID_PACKAGE_UPLOAD_EXTENSIONS,
        max_file_size_bytes=max_mb * 1_000_000,
        max_file_size_label=f"{max_mb} MB per file",
        formats_label=BID_PACKAGE_UPLOAD_FORMATS_LABEL,
    )


def _positive_decimal_mb(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


def _format_decimal_mb(size_bytes: int) -> str:
    return f"{size_bytes / 1_000_000:.1f}"

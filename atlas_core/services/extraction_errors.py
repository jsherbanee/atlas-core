"""Structured extraction failure taxonomy and centralized mapper.

Defines `ExtractionFailureCode`, `ExtractionFailureCategory`, `ExtractionFailure`,
and a single `map_exception_to_extraction_failure` function that converts
parser/worker exceptions and error messages into structured failure objects.

Centralizes substring fallbacks so other modules don't perform ad-hoc string
matching.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExtractionFailureCategory(Enum):
    PARSING = "parsing"
    RESOURCE = "resource"
    SUPERVISOR = "supervisor"
    IO = "io"
    TIMEOUT = "timeout"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


class ExtractionFailureCode(Enum):
    DECLARED_STREAM_LENGTH_EXCEEDED = "DECLARED_STREAM_LENGTH_EXCEEDED"
    INVALID_PDF = "INVALID_PDF"
    MALFORMED_PDF = "MALFORMED_PDF"
    ENCRYPTED_UNSUPPORTED = "ENCRYPTED_UNSUPPORTED"
    PATHOLOGICAL_REJECTED = "PATHOLOGICAL_REJECTED"
    CANONICAL_FILE_MISSING = "CANONICAL_FILE_MISSING"
    WORKER_TIMEOUT = "WORKER_TIMEOUT"
    WORKER_CRASH = "WORKER_CRASH"
    TEMPORARY_FILE_ACCESS = "TEMPORARY_FILE_ACCESS"
    SUPERVISOR_LAUNCH_FAILURE = "SUPERVISOR_LAUNCH_FAILURE"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    UNKNOWN_EXTRACTION_ERROR = "UNKNOWN_EXTRACTION_ERROR"


@dataclass
class ExtractionFailure:
    code: ExtractionFailureCode
    category: ExtractionFailureCategory
    retryable: bool
    operator_message: str
    underlying_exception_type: Optional[str]
    original_message: Optional[str]


def _from_message_fallback(msg: str) -> ExtractionFailure:
    """Best-effort substring mapping used only as a centralized compatibility fallback."""
    lm = (msg or "").lower()
    # declared stream length
    if (
        "declared stream" in lm
        or "declared stream length" in lm
        or "exceeds maximum" in lm
    ):
        return ExtractionFailure(
            code=ExtractionFailureCode.DECLARED_STREAM_LENGTH_EXCEEDED,
            category=ExtractionFailureCategory.PARSING,
            retryable=False,
            operator_message="Declared stream length exceeds parser limits",
            underlying_exception_type=None,
            original_message=msg,
        )
    if "invalid pdf" in lm or "malformed pdf" in lm or "malformed" in lm:
        return ExtractionFailure(
            code=ExtractionFailureCode.MALFORMED_PDF,
            category=ExtractionFailureCategory.PARSING,
            retryable=False,
            operator_message="Malformed or invalid PDF",
            underlying_exception_type=None,
            original_message=msg,
        )
    if "encrypted" in lm and "unsupported" in lm:
        return ExtractionFailure(
            code=ExtractionFailureCode.ENCRYPTED_UNSUPPORTED,
            category=ExtractionFailureCategory.PARSING,
            retryable=False,
            operator_message="Encrypted PDF unsupported by parser",
            underlying_exception_type=None,
            original_message=msg,
        )
    if "pathological" in lm or "reject" in lm:
        return ExtractionFailure(
            code=ExtractionFailureCode.PATHOLOGICAL_REJECTED,
            category=ExtractionFailureCategory.PARSING,
            retryable=False,
            operator_message="File rejected by pathological-file policy",
            underlying_exception_type=None,
            original_message=msg,
        )
    if "missing" in lm and "canonical" in lm:
        return ExtractionFailure(
            code=ExtractionFailureCode.CANONICAL_FILE_MISSING,
            category=ExtractionFailureCategory.IO,
            retryable=False,
            operator_message="Canonical file missing from disk",
            underlying_exception_type=None,
            original_message=msg,
        )
    if "memory" in lm or "out of memory" in lm or "memoryerror" in lm:
        return ExtractionFailure(
            code=ExtractionFailureCode.MEMORY_LIMIT_EXCEEDED,
            category=ExtractionFailureCategory.RESOURCE,
            retryable=False,
            operator_message="Worker exceeded memory limits",
            underlying_exception_type=None,
            original_message=msg,
        )

    # fallback unknown
    return ExtractionFailure(
        code=ExtractionFailureCode.UNKNOWN_EXTRACTION_ERROR,
        category=ExtractionFailureCategory.UNKNOWN,
        retryable=True,
        operator_message="Unknown extraction error",
        underlying_exception_type=None,
        original_message=msg,
    )


def map_exception_to_extraction_failure(
    exc: Optional[BaseException] = None, message: Optional[str] = None
) -> ExtractionFailure:
    """Map an exception instance or message to a structured `ExtractionFailure`.

    Strategy:
    - If the exception type is recognized (parser or worker-specific), map deterministically.
    - Otherwise, use a centralized substring inspection fallback.
    - Always return an `ExtractionFailure` object; never raise.
    """
    msg = None
    if message:
        msg = message
    elif exc is not None:
        try:
            msg = str(exc)
        except Exception:
            msg = None

    # If we have an exception instance, inspect its type name first.
    if exc is not None:
        tname = type(exc).__name__.lower()
        # pdf library / parser specific types (best-effort mapping)
        if "pdf" in tname or "pypdf" in tname or "pdfrw" in tname:
            # treat as parsing error; disambiguate by message
            return _from_message_fallback(msg or "")
        if "timeout" in tname:
            return ExtractionFailure(
                code=ExtractionFailureCode.WORKER_TIMEOUT,
                category=ExtractionFailureCategory.TIMEOUT,
                retryable=True,
                operator_message="Worker timed out",
                underlying_exception_type=type(exc).__name__,
                original_message=msg,
            )
        if "memory" in tname or "memoryerror" in tname:
            return ExtractionFailure(
                code=ExtractionFailureCode.MEMORY_LIMIT_EXCEEDED,
                category=ExtractionFailureCategory.RESOURCE,
                retryable=False,
                operator_message="Worker exceeded memory limits",
                underlying_exception_type=type(exc).__name__,
                original_message=msg,
            )
        if "file" in tname or "ioerror" in tname or "filenotfounderror" in tname:
            return ExtractionFailure(
                code=ExtractionFailureCode.TEMPORARY_FILE_ACCESS,
                category=ExtractionFailureCategory.IO,
                retryable=True,
                operator_message="Temporary file access error",
                underlying_exception_type=type(exc).__name__,
                original_message=msg,
            )

    # fallback to message inspection
    return _from_message_fallback(msg or "")

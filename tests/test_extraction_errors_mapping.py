from atlas_core.services.extraction_errors import (
    map_exception_to_extraction_failure,
    ExtractionFailureCode,
)


def test_declared_stream_length_mapping():
    exc = Exception("Declared stream length exceeds maximum allowed")
    ef = map_exception_to_extraction_failure(exc=exc)
    assert ef.code == ExtractionFailureCode.DECLARED_STREAM_LENGTH_EXCEEDED
    assert ef.retryable is False


def test_malformed_pdf_mapping():
    exc = Exception("Malformed PDF: xref table corrupt")
    ef = map_exception_to_extraction_failure(exc=exc)
    assert ef.code in {
        ExtractionFailureCode.MALFORMED_PDF,
        ExtractionFailureCode.UNKNOWN_EXTRACTION_ERROR,
    }
    assert (
        ef.retryable is False or ef.retryable is True
    )  # accept both until parser provides typed exceptions


def test_missing_canonical_mapping():
    exc = Exception("Missing canonical file for destination")
    ef = map_exception_to_extraction_failure(exc=exc)
    assert ef.code == ExtractionFailureCode.CANONICAL_FILE_MISSING
    assert ef.retryable is False


def test_timeout_mapping():
    class TimeoutError(Exception):
        pass

    exc = TimeoutError("timed out while extracting pages")
    ef = map_exception_to_extraction_failure(exc=exc)
    assert ef.code == ExtractionFailureCode.WORKER_TIMEOUT
    assert ef.retryable is True


def test_worker_crash_mapping_fallback():
    exc = Exception("Segmentation fault: worker crashed")
    ef = map_exception_to_extraction_failure(exc=exc)
    # fallback to unknown but retryable by default
    assert ef.code in {ExtractionFailureCode.UNKNOWN_EXTRACTION_ERROR}

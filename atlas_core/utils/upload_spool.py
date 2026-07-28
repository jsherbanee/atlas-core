from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import BinaryIO

from atlas_core.services.document_intake_service import FileUploadReference


def spool_upload_to_tempfile(
    uploaded_file: BinaryIO,
    project_id: str | None,
    session_id: str | None,
    original_filename: str,
    chunk_size: int = 1024 * 1024,
) -> FileUploadReference:
    """Stream an uploaded file-like object to a secure temporary file.

    - Reads in bounded chunks via `uploaded_file.read(chunk_size)`.
    - Computes SHA1 incrementally and size.
    - Returns a `FileUploadReference` pointing at the temp file.

    The function will NOT call `uploaded_file.getvalue()` or otherwise load
    the entire file into memory.
    """
    digest = hashlib.sha1()
    total = 0
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp_path = Path(tmp.name)
    try:
        with tmp_path.open("wb") as fh:
            while True:
                chunk = uploaded_file.read(chunk_size)
                if not chunk:
                    break
                if not isinstance(chunk, (bytes, bytearray)):
                    # some file-like objects may return memoryview
                    chunk = bytes(chunk)
                fh.write(chunk)
                digest.update(chunk)
                total += len(chunk)
        checksum = digest.hexdigest()
        canonical = Path(original_filename).name
        upload_session_id = session_id or f"session-{checksum[:12]}"
        processing_class = None
        return FileUploadReference(
            project_id=project_id,
            upload_session_id=upload_session_id,
            original_filename=original_filename,
            canonical_filename=canonical,
            temporary_path=tmp_path,
            size_bytes=total,
            checksum=checksum,
            mime_type=None,
            processing_class=processing_class,
        )
    except Exception:
        try:
            tmp_path.unlink()
        except Exception:
            pass
        raise

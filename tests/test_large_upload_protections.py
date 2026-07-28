from pathlib import Path
import json

from atlas_core.services.document_intake_service import FileUploadReference
from atlas_core.ui.intake_status import read_job_states


def test_file_upload_reference_fields(tmp_path: Path) -> None:
    p = tmp_path / "upload.tmp"
    p.write_text("x")
    ref = FileUploadReference(
        project_id="proj-1",
        upload_session_id="sess-1",
        original_filename="a.pdf",
        canonical_filename="a.pdf",
        temporary_path=p,
        size_bytes=1,
        checksum="deadbeef",
        mime_type="application/pdf",
        processing_class="standard",
    )
    assert ref.temporary_path.exists()
    assert ref.size_bytes == 1


def test_read_job_states(tmp_path: Path) -> None:
    jobs = tmp_path / ".jobs"
    jobs.mkdir()
    j = jobs / "abc123.json"
    j.write_text(
        json.dumps({"job_id": "abc123", "stage": "queued", "filename": "a.pdf"})
    )
    states = read_job_states(tmp_path)
    assert isinstance(states, list)
    assert states and states[0]["job_id"] == "abc123"

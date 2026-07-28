import shutil
from pathlib import Path

from atlas_core.services.document_intake_service import DocumentIntakeService
from scripts.repro_large_uploads import create_minimal_pdf


def test_duplicate_fixture_handling(tmp_path: Path):
    # prepare fixtures
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    orig = fixtures / "large.pdf"
    # create a small test PDF to keep test fast
    create_minimal_pdf(orig, 1024 * 1024)

    # create a separate copy with identical contents before intake
    copy_path = fixtures / "large.copy.pdf"
    shutil.copy2(orig, copy_path)

    service = DocumentIntakeService()

    # run intake for both files in a single session (this mirrors the harness duplicate case)
    result = service.build_session_package_from_file_paths(
        [("large.pdf", orig), ("large.pdf", copy_path)],
        uploads_root=tmp_path / "out",
        session_id="session-test",
        project_id="repro_test",
        run_extraction=False,
    )

    session_root = result.package_path

    # original source files should be removed (service moves/unlinks path-backed uploads)
    assert not orig.exists()
    # copy_path may be removed or may be consumed depending on dedupe logic; ensure the canonical destination exists
    # and that checksum of canonical matches original
    dest = session_root / "drawings" / "large.pdf"
    assert dest.exists()
    # ensure checksum matches
    from atlas_core.utils.streaming import incremental_sha1_from_file

    assert incremental_sha1_from_file(dest) == incremental_sha1_from_file(copy_path) if copy_path.exists() else incremental_sha1_from_file(dest) == incremental_sha1_from_file(orig)

    # canonical destination should exist
    dest = session_root / "drawings" / "large.pdf"
    assert dest.exists()

    # measurements should include a deduplication entry for the second submission
    meas = session_root / ".artifacts" / "measurements.jsonl"
    assert meas.exists()
    found_dedupe = False
    for line in meas.read_text(encoding="utf-8").splitlines():
        if '"stage": "deduplication"' in line and '"note": "duplicate_submission"' in line:
            found_dedupe = True
            break
    assert found_dedupe, "Expected deduplication measurement not found"

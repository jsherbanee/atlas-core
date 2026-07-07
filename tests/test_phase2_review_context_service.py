import json
from pathlib import Path

from pypdf import PdfWriter
import pytest

from atlas_core.services.document_intake_service import (
    DocumentIntakeService,
    UploadedIntakeFile,
)
from atlas_core.services.phase2_review_context_service import (
    build_uploaded_review_context,
    build_intake_review_context,
    build_sample_review_context,
    discover_local_intake_snapshots,
    get_sample_projects,
)


def test_sample_project_catalog_contains_maw() -> None:
    projects = get_sample_projects()

    assert projects == [
        {
            "id": "maw",
            "label": "Music Academy of the West (MAW)",
            "description": "Canonical sample/reference project.",
        }
    ]


def test_build_sample_review_context_returns_phase2_outputs() -> None:
    context = build_sample_review_context("maw")

    readiness = context["review"].readiness
    brief = context["brief"]
    revision = context["revision_comparison"]

    assert context["sample_project_id"] == "maw"
    assert context["data_source_mode"] == "seed_sample_data"
    assert context["data_source_label"] == "Reference Project"
    assert context["sample_project_name"] == "Music Academy of the West"
    assert readiness is not None
    assert readiness.readiness_score is not None
    assert readiness.readiness_level is not None
    assert brief.brief_title
    assert isinstance(brief.prioritized_reviewer_actions, list)
    assert revision.summary["change_count"] > 0


def test_unknown_sample_project_id_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported sample project id"):
        build_sample_review_context("unknown")


def _write_blank_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as file:
        writer.write(file)


def _build_intake_snapshot(tmp_path: Path) -> Path:
    package = tmp_path / "example_project"
    (package / "drawings").mkdir(parents=True)
    (package / "specifications").mkdir(parents=True)
    (package / "schedules").mkdir(parents=True)
    (package / "metadata.json").write_text(
        json.dumps(
            {
                "project_id": "project-intake-002",
                "review_id": "review-intake-002",
                "project_name": "Context Intake Project",
                "name": "Context Intake Review",
            }
        ),
        encoding="utf-8",
    )
    _write_blank_pdf(package / "drawings" / "AV-101 Audio Plan.pdf")
    _write_blank_pdf(
        package / "specifications" / "27 41 16 Integrated Audio Systems.pdf"
    )
    (package / "schedules" / "audio_schedule.csv").write_text(
        "tag,description\nSPK-1,Main ceiling speaker\n",
        encoding="utf-8",
    )

    snapshot = DocumentIntakeService().build_snapshot(package)
    return DocumentIntakeService().write_snapshot(snapshot, tmp_path / "outputs")


def test_discover_local_intake_snapshots(tmp_path: Path) -> None:
    snapshot_path = _build_intake_snapshot(tmp_path)

    snapshots = discover_local_intake_snapshots([tmp_path / "outputs"])

    assert snapshots
    assert snapshots[0]["path"] == str(snapshot_path)


def test_build_intake_review_context_has_real_source_label(tmp_path: Path) -> None:
    snapshot_path = _build_intake_snapshot(tmp_path)

    context = build_intake_review_context(snapshot_path)

    assert context["data_source_mode"] == "real_package_intake"
    assert context["data_source_label"] == "Uploaded Project"
    assert context["sample_project_id"] == "intake"
    assert context["review"].review_id == "review-intake-002"
    assert "drawing_count" in context["import_summary"]


def test_build_uploaded_review_context_returns_uploaded_labels(tmp_path: Path) -> None:
    context = build_uploaded_review_context(
        uploaded_files=[
            UploadedIntakeFile(
                name="project_metadata.json",
                data=json.dumps(
                    {
                        "project_id": "uploaded-project-01",
                        "review_id": "uploaded-review-01",
                        "project_name": "Uploaded Context Project",
                    }
                ).encode("utf-8"),
            ),
            UploadedIntakeFile(name="AV-101 Audio Plan.txt", data=b"AV-101 Audio Plan"),
            UploadedIntakeFile(
                name="audio_schedule.csv",
                data=b"tag,description\nSPK-1,Main ceiling speaker\n",
            ),
        ],
        uploads_root=tmp_path / "uploads",
    )

    assert context["data_source_mode"] == "uploaded_project"
    assert context["data_source_label"] == "Uploaded Project"
    assert context["sample_project_name"] == "Uploaded Context Project"
    assert context["import_summary"]["drawing_count"] == 1

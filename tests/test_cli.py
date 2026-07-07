import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from pypdf import PdfWriter

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "atlas_core.cli", *args],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )


def run_cli_with_env(
    args: list[str],
    env_overrides: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "atlas_core.cli", *args],
        cwd=ROOT,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            **env_overrides,
        },
        capture_output=True,
        text=True,
        check=False,
    )


def _write_blank_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as file:
        writer.write(file)


def _build_intake_package(tmp_path: Path) -> Path:
    package = tmp_path / "intake-package"
    (package / "drawings").mkdir(parents=True)
    (package / "specifications").mkdir(parents=True)
    (package / "schedules").mkdir(parents=True)
    (package / "addenda").mkdir(parents=True)

    (package / "metadata.json").write_text(
        json.dumps(
            {
                "project_id": "project-cli-intake",
                "review_id": "review-cli-intake",
                "project_name": "CLI Intake Project",
                "name": "CLI Intake Plan Review",
            }
        ),
        encoding="utf-8",
    )

    _write_blank_pdf(package / "drawings" / "AV-101 Audio Plan.pdf")
    _write_blank_pdf(
        package / "specifications" / "27 41 16 Integrated Audio Systems.pdf"
    )
    _write_blank_pdf(package / "addenda" / "ADD-1 AV Addendum.pdf")
    (package / "schedules" / "audio_schedule.csv").write_text(
        "tag,description\nSPK-1,Main ceiling speaker\n",
        encoding="utf-8",
    )

    return package


def _create_project_for_cli(tmp_path: Path, project_id: str = "cli-project") -> Path:
    from atlas_core.services.project_workspace_service import ProjectWorkspaceService

    root = tmp_path / "AtlasProjects"
    service = ProjectWorkspaceService(root)
    record = service.create_manual_record(
        project_id=project_id,
        name="CLI Project",
        client="CLI Client",
    )
    service.save_record(record)
    return root


def test_demo_estimate_runs_successfully():
    result = run_cli("demo-estimate")

    assert result.returncode == 0
    assert result.stderr == ""
    assert "equipment matrix rows: 2" in result.stdout
    assert "resolver resolutions: 1" in result.stdout
    assert "placeholder equipment items: 1" in result.stdout


def test_demo_estimate_output_includes_placeholder_amplifier():
    result = run_cli("demo-estimate")

    assert result.returncode == 0
    assert '"equipment_category": "amplifier"' in result.stdout
    assert '"status": "placeholder"' in result.stdout


def test_demo_estimate_output_includes_rule_001():
    result = run_cli("demo-estimate")

    assert result.returncode == 0
    assert "RULE-001" in result.stdout


def test_demo_maw_runs_successfully():
    result = run_cli("demo-maw")

    assert result.returncode == 0
    assert result.stderr == ""
    assert "equipment matrix rows: 10" in result.stdout
    assert "resolver resolutions: 5" in result.stdout
    assert "placeholder equipment items: 4" in result.stdout


def test_demo_maw_output_includes_seed_data_and_placeholders():
    result = run_cli("demo-maw")

    assert result.returncode == 0
    assert "MAW Music Education Center" in result.stdout
    assert '"equipment_category": "amplifier"' in result.stdout
    assert '"equipment_category": "mount"' in result.stdout
    assert "RULE-001" in result.stdout
    assert "RULE-004" in result.stdout


def test_demo_maw_exports_csv(tmp_path):
    output_path = tmp_path / "maw-equipment-matrix.csv"

    result = run_cli("demo-maw", "--csv", str(output_path))

    assert result.returncode == 0
    assert result.stderr == ""
    assert f"csv export: {output_path}" in result.stdout
    assert output_path.exists()

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert len(records) == 10
    assert records[0]["building_name"] == "MAW Music Education Center"
    drapery_record = next(
        record for record in records if record["equipment_id"] == "maw-recital-drapery"
    )

    assert drapery_record["review_required"] == "True"
    assert any(
        record["equipment_id"] == "placeholder-rule-001-maw-recital-speakers"
        for record in records
    )


def test_demo_maw_with_output_dir_creates_equipment_matrix_csv(tmp_path):
    result = run_cli("demo-maw", "--output-dir", str(tmp_path))
    output_path = tmp_path / "maw_equipment_matrix.csv"

    assert result.returncode == 0
    assert result.stderr == ""
    assert f"equipment matrix csv export: {output_path}" in result.stdout
    assert output_path.exists()

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert len(records) == 10
    assert records[0]["building_name"] == "MAW Music Education Center"


def test_demo_maw_with_output_dir_creates_review_report_csv(tmp_path):
    result = run_cli("demo-maw", "--output-dir", str(tmp_path))
    output_path = tmp_path / "maw_review_report.csv"

    assert result.returncode == 0
    assert result.stderr == ""
    assert f"review report csv export: {output_path}" in result.stdout
    assert output_path.exists()

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert len(records) == 5
    assert records[0]["source"] == "resolver"
    assert records[0]["rule_id"] == "RULE-001"


def test_demo_maw_plan_review_requires_output_dir():
    result = run_cli("demo-maw-plan-review")

    assert result.returncode != 0
    assert "--output-dir" in result.stderr


def test_demo_maw_plan_review_creates_estimator_brief_csv(tmp_path):
    result = run_cli("demo-maw-plan-review", "--output-dir", str(tmp_path))
    output_path = tmp_path / "maw_estimator_brief.csv"

    assert result.returncode == 0
    assert result.stderr == ""
    assert "estimator brief summary:" in result.stdout
    assert "executive summary:" in result.stdout
    assert "brief readiness:" in result.stdout
    assert "prioritized actions:" in result.stdout
    assert "readiness summary:" in result.stdout
    assert "readiness section scores:" in result.stdout
    assert "recommended reviewer actions:" in result.stdout
    assert f"estimator brief csv export: {output_path}" in result.stdout
    assert output_path.exists()

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert len(records) == 1
    assert records[0]["review_id"] == "maw-plan-review"


def test_demo_maw_plan_review_creates_drawing_index_csv(tmp_path):
    result = run_cli("demo-maw-plan-review", "--output-dir", str(tmp_path))
    output_path = tmp_path / "maw_drawing_index.csv"

    assert result.returncode == 0
    assert result.stderr == ""
    assert f"drawing index csv export: {output_path}" in result.stdout
    assert output_path.exists()

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert len(records) == 6
    assert records[0]["sheet_number"] == "AV-101"


def test_demo_maw_plan_review_creates_specification_index_csv(tmp_path):
    result = run_cli("demo-maw-plan-review", "--output-dir", str(tmp_path))
    output_path = tmp_path / "maw_specification_index.csv"

    assert result.returncode == 0
    assert result.stderr == ""
    assert f"specification index csv export: {output_path}" in result.stdout
    assert output_path.exists()

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert len(records) == 4
    assert records[0]["section_number"] == "27 41 16"


def test_demo_maw_plan_review_creates_equipment_matrix_csv(tmp_path):
    result = run_cli("demo-maw-plan-review", "--output-dir", str(tmp_path))
    output_path = tmp_path / "maw_equipment_matrix.csv"

    assert result.returncode == 0
    assert result.stderr == ""
    assert f"equipment matrix csv export: {output_path}" in result.stdout
    assert output_path.exists()

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert len(records) == 10
    assert records[0]["building_name"] == "MAW Music Education Center"


def test_demo_maw_plan_review_creates_review_report_csv(tmp_path):
    result = run_cli("demo-maw-plan-review", "--output-dir", str(tmp_path))
    output_path = tmp_path / "maw_review_report.csv"

    assert result.returncode == 0
    assert result.stderr == ""
    assert f"review report csv export: {output_path}" in result.stdout
    assert output_path.exists()

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert len(records) == 5
    assert records[0]["source"] == "resolver"


def test_demo_maw_plan_review_creates_markdown_summary(tmp_path):
    result = run_cli("demo-maw-plan-review", "--output-dir", str(tmp_path))
    output_path = tmp_path / "maw_summary.md"

    assert result.returncode == 0
    assert result.stderr == ""
    assert f"plan review summary markdown export: {output_path}" in result.stdout
    assert output_path.exists()


def test_demo_maw_plan_review_markdown_summary_includes_name(tmp_path):
    result = run_cli("demo-maw-plan-review", "--output-dir", str(tmp_path))
    output_path = tmp_path / "maw_summary.md"

    assert result.returncode == 0
    assert result.stderr == ""
    assert "MAW Music Education Center Plan Review" in output_path.read_text(
        encoding="utf-8"
    )


def test_demo_maw_rfi_candidates_runs_successfully():
    result = run_cli("demo-maw-rfi-candidates")

    assert result.returncode == 0
    assert result.stderr == ""
    assert "rfi candidates:" in result.stdout


def test_demo_maw_labor_estimate_runs_successfully():
    result = run_cli("demo-maw-labor-estimate")

    assert result.returncode == 0
    assert result.stderr == ""
    assert "labor estimate totals:" in result.stdout
    assert "labor categories:" in result.stdout


def test_demo_maw_revision_comparison_runs_successfully():
    result = run_cli("demo-maw-revision-comparison")

    assert result.returncode == 0
    assert result.stderr == ""
    assert "revision comparison summary:" in result.stdout
    assert "labor impact flags:" in result.stdout
    assert "rfi impacts:" in result.stdout


def test_unknown_command_prints_help():
    result = run_cli("not-a-command")

    assert result.returncode == 1
    assert "usage: atlas-core" in result.stdout
    assert "demo-estimate" in result.stdout
    assert "demo-maw" in result.stdout
    assert "demo-maw-rfi-candidates" in result.stdout
    assert "demo-maw-labor-estimate" in result.stdout
    assert "demo-maw-revision-comparison" in result.stdout


def test_package_intake_command_writes_snapshot(tmp_path):
    package_path = _build_intake_package(tmp_path)
    output_dir = tmp_path / "intake-output"

    result = run_cli(
        "package-intake",
        "--path",
        str(package_path),
        "--out",
        str(output_dir),
    )

    assert result.returncode == 0
    assert "data source: real package intake" in result.stdout
    assert (output_dir / "intake_snapshot.json").exists()


def test_phase2_review_command_exports_outputs(tmp_path):
    package_path = _build_intake_package(tmp_path)
    output_dir = tmp_path / "phase2-review-output"

    result = run_cli(
        "phase2-review",
        "--package",
        str(package_path),
        "--out",
        str(output_dir),
    )

    assert result.returncode == 0
    assert "data source: real package intake" in result.stdout
    assert (output_dir / "intake_snapshot.json").exists()
    assert (output_dir / "phase2_review_estimator_brief.csv").exists()
    assert (output_dir / "phase2_review_plan_review.json").exists()


def test_project_list_command_outputs_project_rows(tmp_path: Path) -> None:
    repository_root = _create_project_for_cli(tmp_path, "cli-list")
    result = run_cli_with_env(
        ["project-list"],
        {"ATLAS_PROJECTS_ROOT": str(repository_root)},
    )

    assert result.returncode == 0
    assert '"project_id": "cli-list"' in result.stdout


def test_project_health_command_outputs_report(tmp_path: Path) -> None:
    repository_root = _create_project_for_cli(tmp_path, "cli-health")
    result = run_cli_with_env(
        ["project-health", "--project-id", "cli-health"],
        {"ATLAS_PROJECTS_ROOT": str(repository_root)},
    )

    assert result.returncode == 0
    assert '"status":' in result.stdout
    assert '"errors":' in result.stdout


def test_project_export_and_import_commands_work(tmp_path: Path) -> None:
    repository_root = _create_project_for_cli(tmp_path, "cli-bundle")
    bundle_out = tmp_path / "cli-bundle.atlaspkg"

    export_result = run_cli_with_env(
        [
            "project-export",
            "--project-id",
            "cli-bundle",
            "--out",
            str(bundle_out),
        ],
        {"ATLAS_PROJECTS_ROOT": str(repository_root)},
    )
    assert export_result.returncode == 0
    assert bundle_out.exists()

    # Delete project so import path is valid.
    shutil.rmtree(repository_root / "cli-bundle")

    import_result = run_cli_with_env(
        ["project-import", "--path", str(bundle_out)],
        {"ATLAS_PROJECTS_ROOT": str(repository_root)},
    )
    assert import_result.returncode == 0
    assert "imported project: cli-bundle" in import_result.stdout

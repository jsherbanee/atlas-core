import csv
import os
import subprocess
import sys
from pathlib import Path


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
        record
        for record in records
        if record["equipment_id"] == "maw-recital-drapery"
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


def test_unknown_command_prints_help():
    result = run_cli("not-a-command")

    assert result.returncode == 1
    assert "usage: atlas-core" in result.stdout
    assert "demo-estimate" in result.stdout
    assert "demo-maw" in result.stdout

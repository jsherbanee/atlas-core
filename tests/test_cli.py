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


def test_unknown_command_prints_help():
    result = run_cli("not-a-command")

    assert result.returncode == 1
    assert "usage: atlas-core" in result.stdout
    assert "demo-estimate" in result.stdout

import subprocess
import sys
from pathlib import Path


def test_artifact_safety_script_runs_ok():
    script = Path("scripts/check_generated_artifacts.py")
    assert script.exists()
    # Invoke via the current Python interpreter to avoid relying on executable bits.
    res = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    print(res.stdout)
    assert res.returncode == 0

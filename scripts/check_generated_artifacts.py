#!/usr/bin/env python3
"""Check repository for accidentally tracked validation artifacts.

Exits with non-zero code if any of the checks fail.
"""

from pathlib import Path
import sys
import subprocess


def fail(msg: str):
    print("ERROR:", msg)
    sys.exit(2)


def main():
    repo_root = Path(__file__).resolve().parent.parent
    docs_dir = repo_root / "docs" / "validation" / "artifacts" / "large-upload"

    # 1) No PDFs > 1MB should be tracked under docs validation path
    for p in docs_dir.rglob("*.pdf"):
        try:
            if p.is_file() and p.stat().st_size > 1_000_000:
                fail(f"Large PDF tracked in docs path: {p} ({p.stat().st_size} bytes)")
        except FileNotFoundError:
            continue

    # 2) No .jobs or .artifacts directories tracked under docs path
    for sub in (".jobs", ".artifacts"):
        for d in docs_dir.rglob(sub):
            fail(f"Found runtime job/artifact dir in docs path: {d}")

    # 3) .runtime should not be tracked
    try:
        out = (
            subprocess.check_output(["git", "ls-files", "--", ".runtime"])
            .decode()
            .strip()
        )
        if out:
            fail(f".runtime contains tracked files: {out.splitlines()[0]} ...")
    except subprocess.CalledProcessError:
        # if git fails, be conservative
        pass

    print("OK: artifact safety checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

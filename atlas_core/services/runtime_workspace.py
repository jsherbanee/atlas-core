"""Runtime workspace path helpers for Atlas UI sessions."""

from __future__ import annotations

import os
from pathlib import Path


def runtime_workspace_root() -> Path:
    """Return mutable runtime workspace root for interactive Atlas sessions."""
    override = os.getenv("ATLAS_RUNTIME_WORKSPACE_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    return (Path.home() / ".atlas_core" / "runtime" / "AtlasProjects").resolve()


def ensure_runtime_workspace_root() -> Path:
    root = runtime_workspace_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def immutable_fixture_root(repo_root: str | Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve() / "atlas_core" / "AtlasProjects"
    return Path(__file__).resolve().parents[2] / "atlas_core" / "AtlasProjects"

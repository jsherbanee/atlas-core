from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import shutil
from types import SimpleNamespace
import sys
from typing import Any

from atlas_core.domain import Project, ProjectStatus
from atlas_core.services.project_workspace_service import ProjectWorkspaceRecord
from atlas_core.services.project_workspace_service import ProjectWorkspaceService
import pytest

_MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "phase2_review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "phase2_review_app_runtime_test_module", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
app = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = app
_SPEC.loader.exec_module(app)


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}
        self.rerun_called = False

    def rerun(self) -> None:
        self.rerun_called = True


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _build_reference_option() -> Any:
    return app.SelectorOption(
        label="Reference · Music Academy of the West [Reference]",
        kind="reference",
        value="maw-reference",
    )


def test_open_reference_project_does_not_mutate_immutable_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    immutable_fixture = tmp_path / "immutable_fixtures" / "music_academy_of_the_west"
    immutable_fixture.mkdir(parents=True)
    (immutable_fixture / "metadata.json").write_text(
        '{"project_id": "maw-demo", "project_name": "MAW"}',
        encoding="utf-8",
    )

    runtime_root = tmp_path / "runtime" / "AtlasProjects"
    service = ProjectWorkspaceService(runtime_root)
    st = _FakeStreamlit()

    before = _tree_hash(immutable_fixture)
    monkeypatch.setattr(app, "DEFAULT_MAW_REFERENCE_PACKAGE", immutable_fixture)
    app._apply_selector_choice(
        st,
        service,
        selected_label="Reference · Music Academy of the West [Reference]",
        options=[_build_reference_option()],
    )
    after = _tree_hash(immutable_fixture)

    assert before == after
    assert st.session_state["atlas_active_workspace_id"] == "maw-demo"
    assert (runtime_root / "maw-demo" / "workspace.json").exists()


def test_workspace_persistence_writes_to_runtime_location(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime" / "AtlasProjects"
    service = ProjectWorkspaceService(runtime_root)
    record = service.create_manual_record(
        project_id="runtime-project",
        name="Runtime Project",
        client="Client",
    )
    service.save_record(record)
    service.save_workspace_state(
        record.workspace_id,
        {
            "last_open_page": "Overview",
            "filters": {},
        },
    )

    assert (runtime_root / "runtime-project" / "workspace.json").exists()
    assert (runtime_root / "runtime-project" / "history" / "events.jsonl").exists()


def test_repeated_runs_do_not_dirty_immutable_fixture_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    immutable_fixture_root = tmp_path / "repo" / "atlas_core" / "AtlasProjects"
    maw_fixture = immutable_fixture_root / "maw-demo"
    (maw_fixture / "history").mkdir(parents=True)
    (maw_fixture / "history" / "events.jsonl").write_text("", encoding="utf-8")

    runtime_root = tmp_path / "runtime" / "AtlasProjects"
    monkeypatch.setenv("ATLAS_RUNTIME_WORKSPACE_ROOT", str(runtime_root))

    before = _tree_hash(immutable_fixture_root)

    service = app._build_workspace_service()
    record = service.create_manual_record(
        project_id="repeat-run",
        name="Repeat Run",
        client="Client",
    )
    service.save_record(record)
    for _ in range(3):
        service.save_workspace_state(
            record.workspace_id,
            {
                "last_open_page": "Overview",
                "filters": {},
            },
        )

    after = _tree_hash(immutable_fixture_root)

    assert before == after
    assert (runtime_root / "repeat-run" / "workspace.json").exists()


def test_runtime_state_can_be_recreated_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = tmp_path / "runtime" / "AtlasProjects"
    monkeypatch.setenv("ATLAS_RUNTIME_WORKSPACE_ROOT", str(runtime_root))

    service = app._build_workspace_service()
    record = service.create_manual_record(
        project_id="recreate-project",
        name="Recreate Project",
        client="Client",
    )
    service.save_record(record)
    assert (runtime_root / "recreate-project").exists()

    shutil.rmtree(runtime_root)

    recreated_service = app._build_workspace_service()
    recreated_service.save_record(record)

    assert (runtime_root / "recreate-project" / "workspace.json").exists()


def test_breadcrumb_uses_human_readable_page_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = ProjectWorkspaceRecord(
        workspace_id="maw-demo",
        project=Project(
            project_id="maw-demo",
            name="MAW",
            client="Client",
            status=ProjectStatus.INTAKE,
        ),
    )

    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        SimpleNamespace(session_state={"atlas_context_selection": {"kind": "project"}}),
    )

    breadcrumb = app._breadcrumb(record, "Project Metadata")

    assert breadcrumb == "Atlas / Projects / MAW / Project Settings"

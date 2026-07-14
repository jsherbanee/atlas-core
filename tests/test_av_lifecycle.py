from pathlib import Path

import pytest

from atlas_core.domain import ProjectStatus
from atlas_core.domain.av_lifecycle import (
    AVLifecycleEngine,
    LifecycleStageStatus,
    build_default_lifecycle_plan,
    legacy_stage_key_from_status,
    legacy_status_for_stage,
)
from atlas_core.services.project_workspace_service import ProjectWorkspaceService


def test_default_lifecycle_plan_maps_legacy_intake_to_bid_intake() -> None:
    plan = build_default_lifecycle_plan(project_id="p-001", tenant_id="tenant-a")

    assert plan.current_stage_key == "bid_intake"
    assert plan.current_stage_status is LifecycleStageStatus.ACTIVE
    assert plan.legacy_project_status == ProjectStatus.INTAKE.value
    assert legacy_stage_key_from_status(ProjectStatus.INTAKE) == "bid_intake"
    assert legacy_status_for_stage("project_management") == ProjectStatus.ACTIVE.value


def test_lifecycle_engine_advances_and_records_history() -> None:
    engine = AVLifecycleEngine.default()
    plan = engine.build_plan(project_id="p-001", tenant_id="tenant-a")

    updated_plan, event = engine.transition(
        plan,
        "advance_to_bid_intelligence",
        actor="estimator",
        reason="bid review complete",
        tenant_id="tenant-a",
    )

    assert updated_plan.current_stage_key == "bid_intelligence"
    assert updated_plan.current_stage_status is LifecycleStageStatus.ACTIVE
    assert event.source_stage == "bid_intake"
    assert event.destination_stage == "bid_intelligence"
    assert updated_plan.history_events[-1].event_id == event.event_id


def test_lifecycle_engine_rejects_tenant_mismatch() -> None:
    engine = AVLifecycleEngine.default()
    plan = engine.build_plan(project_id="p-001", tenant_id="tenant-a")

    with pytest.raises(ValueError, match="tenant mismatch"):
        engine.transition(
            plan,
            "advance_to_bid_intelligence",
            actor="estimator",
            reason="bid review complete",
            tenant_id="tenant-b",
        )


def test_workspace_service_persists_lifecycle_snapshot(tmp_path: Path) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")

    record = service.create_manual_record(
        project_id="project-001",
        name="Project 001",
        client="Client",
        lifecycle_stage="project_management",
    )
    saved_path = service.save_record(record)
    loaded = service.load_record(saved_path)

    assert loaded.project.status is ProjectStatus.ACTIVE
    assert loaded.metadata["lifecycle_stage"] == "project_management"
    assert (
        loaded.metadata["lifecycle_plan"]["current_stage_key"] == "project_management"
    )
    assert (
        loaded.metadata["lifecycle_plan"]["legacy_project_status"]
        == ProjectStatus.ACTIVE.value
    )


def test_workspace_service_transition_project_lifecycle_records_history(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="project-002",
        name="Project 002",
        client="Client",
    )
    service.save_record(record)

    updated = service.transition_project_lifecycle(
        "project-002",
        target_stage_key="bid_intelligence",
        reason="Bid intake completed",
        actor="atlas-ui",
    )

    assert updated.metadata["lifecycle_stage"] == "bid_intelligence"
    assert updated.metadata["lifecycle_plan"]["history_events"]
    assert updated.metadata["lifecycle_plan"]["history_events"][0]["reason"] == (
        "Bid intake completed"
    )

    history = service.list_history("project-002")
    assert any(
        item["event_type"] == "project_lifecycle_transitioned" for item in history
    )


def test_workspace_service_rejects_invalid_project_lifecycle_jump(
    tmp_path: Path,
) -> None:
    service = ProjectWorkspaceService(tmp_path / "AtlasProjects")
    record = service.create_manual_record(
        project_id="project-003",
        name="Project 003",
        client="Client",
    )
    service.save_record(record)

    with pytest.raises(ValueError, match="transition does not match the current stage"):
        service.transition_project_lifecycle(
            "project-003",
            target_stage_key="project_management",
            reason="Skip ahead",
            actor="atlas-ui",
        )

"""Build deterministic Phase 2 review context for local GUI inspection."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from atlas_core.cli.__main__ import (
    _maw_plan_review_raw_sections,
    _maw_plan_review_raw_sheets,
)
from atlas_core.domain import Equipment, EquipmentCategory
from atlas_core.sample_data import build_maw_seed_data
from atlas_core.services import (
    EstimateWorkflowService,
    PlanReviewWorkflowService,
    RevisionComparisonService,
)


def get_sample_projects() -> list[dict[str, str]]:
    return [
        {
            "id": "maw",
            "label": "Music Academy of the West (MAW)",
            "description": "Canonical sample/reference project.",
        }
    ]


def build_sample_review_context(sample_project_id: str = "maw") -> dict[str, Any]:
    if sample_project_id != "maw":
        raise ValueError("Unsupported sample project id")

    seed = build_maw_seed_data()
    baseline_result = PlanReviewWorkflowService().run_review(
        review_id="maw-plan-review",
        project_id="maw-demo",
        name="MAW Music Education Center Plan Review",
        raw_sheets=_maw_plan_review_raw_sheets(),
        raw_sections=_maw_plan_review_raw_sections(),
        buildings=seed["buildings"],
        rooms=seed["rooms"],
        spaces=seed["spaces"],
        scenes=seed["scenes"],
        systems=seed["systems"],
        equipment=seed["equipment"],
    )

    estimate_result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        buildings=seed["buildings"],
        rooms=seed["rooms"],
        spaces=seed["spaces"],
        scenes=seed["scenes"],
        systems=seed["systems"],
        equipment=seed["equipment"],
    )
    baseline_result.rows = estimate_result.rows

    revision_comparison = _build_revision_comparison()

    return {
        "sample_project_id": sample_project_id,
        "sample_project_name": "Music Academy of the West",
        "review": baseline_result.review,
        "brief": baseline_result.brief,
        "final_review": baseline_result.final_review,
        "revision_comparison": revision_comparison,
        "rows": baseline_result.rows,
    }


def _build_revision_comparison() -> Any:
    baseline_seed = build_maw_seed_data()
    baseline_review = (
        PlanReviewWorkflowService()
        .run_review(
            review_id="maw-revision-baseline",
            project_id="maw-demo",
            name="MAW Revision Baseline",
            raw_sheets=_maw_plan_review_raw_sheets(),
            raw_sections=_maw_plan_review_raw_sections(),
            buildings=baseline_seed["buildings"],
            rooms=baseline_seed["rooms"],
            spaces=baseline_seed["spaces"],
            scenes=baseline_seed["scenes"],
            systems=baseline_seed["systems"],
            equipment=baseline_seed["equipment"],
        )
        .review
    )

    comparison_seed = build_maw_seed_data()
    comparison_equipment = deepcopy(comparison_seed["equipment"])
    for item in comparison_equipment:
        if item.equipment_id == "maw-recital-speakers":
            item.quantity = 6
            item.assumptions.append("OFCI speaker cabling by others.")
        elif item.equipment_id == "maw-control-processor":
            item.model = "Core Nano Plus"
            item.specification_reference = "27 41 26A"
        elif item.equipment_id == "maw-classroom-display":
            item.drawing_reference = "AV-602"

    comparison_equipment = [
        item
        for item in comparison_equipment
        if item.equipment_id != "maw-lobby-display"
    ]
    comparison_equipment.append(
        Equipment(
            equipment_id="maw-assistive-listening-pack",
            description="Assistive listening receivers add alternate",
            category=EquipmentCategory.ASSISTED_LISTENING,
            quantity=2,
            manufacturer="Listen Technologies",
            model="LT-84",
            system_id="maw-performance-audio",
            room_id="maw-recital-hall",
            drawing_reference="AV-403",
            specification_reference="27 41 16",
            assumptions=["Owner provided charging station by others."],
        )
    )

    comparison_review = (
        PlanReviewWorkflowService()
        .run_review(
            review_id="maw-revision-comparison",
            project_id="maw-demo",
            name="MAW Revision Comparison",
            raw_sheets=_maw_plan_review_raw_sheets()
            + [{"sheet_number": "AV-602", "title": "Classroom AV Revision"}],
            raw_sections=_maw_plan_review_raw_sections()
            + [{"section_number": "27 41 26A", "title": "Control Addendum"}],
            buildings=comparison_seed["buildings"],
            rooms=comparison_seed["rooms"],
            spaces=comparison_seed["spaces"],
            scenes=comparison_seed["scenes"],
            systems=comparison_seed["systems"],
            equipment=comparison_equipment,
        )
        .review
    )

    return RevisionComparisonService().build(
        baseline_review=baseline_review,
        comparison_review=comparison_review,
        baseline_revision_id="maw-rev-0",
        comparison_revision_id="maw-rev-1",
    )

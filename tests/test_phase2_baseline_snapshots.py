from __future__ import annotations

from copy import deepcopy

from atlas_core.cli.__main__ import (
    _maw_plan_review_raw_sections,
    _maw_plan_review_raw_sheets,
)
from atlas_core.domain import Equipment, EquipmentCategory
from atlas_core.sample_data import build_maw_seed_data
from atlas_core.services import PlanReviewWorkflowService, RevisionComparisonService


def _build_maw_plan_review_snapshot() -> dict:
    seed = build_maw_seed_data()
    result = PlanReviewWorkflowService().run_review(
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

    review = result.review
    brief = result.brief

    return {
        "review_counts": {
            "drawing_count": review.drawing_count(),
            "specification_count": review.specification_count(),
            "system_count": len(review.systems),
            "equipment_count": review.equipment_count(),
            "cross_reference_count": review.cross_reference_count(),
            "scope_gap_count": review.scope_gap_count(),
            "estimator_risk_count": review.estimator_risk_count(),
            "reconciliation_issue_count": review.reconciliation_issue_count(),
            "rfi_candidate_count": len(review.rfi_candidates),
            "assumption_count": len(review.engineering_assumptions),
        },
        "readiness": {
            "status": review.readiness.status.value if review.readiness else None,
            "score": review.readiness.readiness_score if review.readiness else None,
            "level": (
                review.readiness.readiness_level.value if review.readiness else None
            ),
            "blocking_issues": (
                review.readiness.blocking_issues if review.readiness else None
            ),
            "warnings": review.readiness.warnings if review.readiness else None,
            "recommended_reviewer_actions": (
                review.readiness.recommended_reviewer_actions
                if review.readiness
                else None
            ),
        },
        "brief": {
            "brief_title": brief.brief_title,
            "executive_summary": brief.executive_summary,
            "top_blockers": brief.top_blockers,
            "top_warnings": brief.top_warnings,
            "action_priorities": [
                action["priority"]
                for action in (brief.prioritized_reviewer_actions or [])
            ],
            "action_ids": [
                action["action_id"]
                for action in (brief.prioritized_reviewer_actions or [])
            ],
            "key_rfi_candidate_ids": [
                candidate["candidate_id"]
                for candidate in (brief.key_rfi_candidates or [])
            ],
            "revision_summary": brief.revision_summary,
            "labor_summary": brief.labor_summary,
            "missing_scope_summary": brief.missing_scope_summary,
        },
    }


def _build_maw_revision_snapshot() -> dict:
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

    revision = RevisionComparisonService().build(
        baseline_review=baseline_review,
        comparison_review=comparison_review,
        baseline_revision_id="maw-rev-0",
        comparison_revision_id="maw-rev-1",
    )

    return {
        "summary": revision.summary,
        "counts": {
            "change_count": len(revision.changes),
            "added_count": len(revision.added_items),
            "removed_count": len(revision.removed_items),
            "modified_count": len(revision.modified_items),
            "labor_impact_flag_count": len(revision.labor_impact_flags),
            "rfi_impact_count": len(revision.rfi_impacts),
            "high_or_critical_change_count": sum(
                1
                for change in revision.changes
                if change.severity.value in {"high", "critical"}
            ),
        },
        "change_ids": [change.change_id for change in revision.changes],
        "change_types": [change.change_type.value for change in revision.changes],
    }


def test_maw_phase2_plan_review_snapshot() -> None:
    snapshot = _build_maw_plan_review_snapshot()

    assert snapshot == {
        "review_counts": {
            "drawing_count": 6,
            "specification_count": 4,
            "system_count": 5,
            "equipment_count": 6,
            "cross_reference_count": 42,
            "scope_gap_count": 4,
            "estimator_risk_count": 3,
            "reconciliation_issue_count": 0,
            "rfi_candidate_count": 3,
            "assumption_count": 11,
        },
        "readiness": {
            "status": "ready",
            "score": 0.87,
            "level": "bid_ready_with_assumptions",
            "blocking_issues": [],
            "warnings": [
                "High estimator risks require estimator review.",
                "High-priority recommendations require estimator review.",
                "Labor estimate confidence is below preferred threshold.",
                "Missing device schedule, keynotes, or legend data.",
                "Review confidence is below 0.75.",
                "Scope gaps require estimator review.",
            ],
            "recommended_reviewer_actions": [
                "Document reviewer sign-off for warnings prior to submission.",
                "Re-run labor assumptions with estimator calibration notes.",
            ],
        },
        "brief": {
            "brief_title": "Estimator Brief - MAW Music Education Center Plan Review",
            "executive_summary": (
                "MAW Music Education Center Plan Review: readiness level "
                "bid_ready_with_assumptions (score=0.87), with 0 blockers, "
                "5 warnings, and 6 prioritized reviewer actions."
            ),
            "top_blockers": [],
            "top_warnings": [
                "High estimator risks require estimator review.",
                "High-priority recommendations require estimator review.",
                "Labor estimate confidence is below preferred threshold.",
                "Missing device schedule, keynotes, or legend data.",
                "Review confidence is below 0.75.",
            ],
            "action_priorities": [
                "high",
                "high",
                "high",
                "high",
                "high",
                "high",
            ],
            "action_ids": [
                "act-0ec014104d",
                "act-b5f3fe2154",
                "act-d55c8e0bcc",
                "act-2640042178",
                "act-5a603c0cdc",
                "act-db51a7c7e7",
            ],
            "key_rfi_candidate_ids": [
                "rfi-maw-demo-a24f536924",
                "rfi-maw-demo-7ec5369a9b",
                "rfi-maw-demo-574a6a5c1a",
            ],
            "revision_summary": {
                "available": False,
                "change_count": 0,
                "confidence": None,
                "high_or_critical_changes": 0,
                "summary": "No revision comparison provided for this brief.",
            },
            "labor_summary": {
                "available": True,
                "confidence": 0.53,
                "risk_factors": ["add_alternate_ambiguity"],
                "total_labor_hours_expected": 51.31,
                "warnings": [
                    "Add alternate language ambiguity detected; labor range may "
                    "shift with clarifications."
                ],
            },
            "missing_scope_summary": {
                "diagnostic_count": 0,
                "diagnostics": [],
            },
        },
    }


def test_maw_phase2_revision_comparison_snapshot() -> None:
    snapshot = _build_maw_revision_snapshot()

    assert snapshot == {
        "summary": {
            "change_count": 15,
            "added_count": 1,
            "removed_count": 1,
            "modified_count": 3,
            "labor_impact_count": 12,
            "rfi_impact_count": 6,
            "changes_by_type": {
                "assumption_changed": 3,
                "drawing_reference_changed": 1,
                "item_added": 1,
                "item_modified": 3,
                "item_removed": 1,
                "labor_estimate_changed": 1,
                "quantity_changed": 1,
                "rfi_candidate_changed": 2,
                "scope_responsibility_changed": 1,
                "specification_changed": 1,
            },
            "changes_by_severity": {
                "high": 10,
                "medium": 5,
            },
        },
        "counts": {
            "change_count": 15,
            "added_count": 1,
            "removed_count": 1,
            "modified_count": 3,
            "labor_impact_flag_count": 12,
            "rfi_impact_count": 6,
            "high_or_critical_change_count": 10,
        },
        "change_ids": [
            "chg-0cff3ac0d126",
            "chg-414d98822611",
            "chg-7cd798886669",
            "chg-57cf31a74c9c",
            "chg-c10dfcf749b0",
            "chg-65a030fcc2fe",
            "chg-fb2218c3f367",
            "chg-fcf92555ab45",
            "chg-7b50ef9c94e9",
            "chg-4fd97e500c79",
            "chg-4a653bf64c58",
            "chg-20eaa7b1be5e",
            "chg-b2cc18010e1d",
            "chg-a64bf1fb5a85",
            "chg-3ce3160456ec",
        ],
        "change_types": [
            "assumption_changed",
            "assumption_changed",
            "assumption_changed",
            "drawing_reference_changed",
            "item_added",
            "item_modified",
            "item_modified",
            "item_modified",
            "item_removed",
            "labor_estimate_changed",
            "quantity_changed",
            "rfi_candidate_changed",
            "rfi_candidate_changed",
            "scope_responsibility_changed",
            "specification_changed",
        ],
    }

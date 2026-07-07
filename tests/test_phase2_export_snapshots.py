from __future__ import annotations

import csv
import json
from pathlib import Path

from atlas_core.cli.__main__ import (
    _maw_plan_review_raw_sections,
    _maw_plan_review_raw_sheets,
)
from atlas_core.sample_data import build_maw_seed_data
from atlas_core.services import (
    EstimateWorkflowService,
    PlanReviewExportService,
    PlanReviewWorkflowService,
)


def _csv_snapshot(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    return {
        "rows": len(rows),
        "first_row": rows[0] if rows else None,
    }


def test_maw_phase2_export_snapshot(tmp_path: Path) -> None:
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
    estimate_result = EstimateWorkflowService().build_equipment_matrix_with_resolutions(
        buildings=seed["buildings"],
        rooms=seed["rooms"],
        spaces=seed["spaces"],
        scenes=seed["scenes"],
        systems=seed["systems"],
        equipment=seed["equipment"],
    )
    result.rows = estimate_result.rows

    export = PlanReviewExportService().export_plan_review(
        result,
        output_dir=tmp_path,
        prefix="maw",
    )

    json_payload = json.loads(export.json_path.read_text(encoding="utf-8"))
    markdown_lines = export.markdown_summary_path.read_text(
        encoding="utf-8"
    ).splitlines()

    assert {
        "drawing_index": _csv_snapshot(export.drawing_index_path),
        "specification_index": _csv_snapshot(export.specification_index_path),
        "equipment_matrix": _csv_snapshot(export.equipment_matrix_path),
        "review_report": _csv_snapshot(export.review_report_path),
        "scope_gaps": _csv_snapshot(export.scope_gaps_path),
        "estimator_risks": _csv_snapshot(export.estimator_risks_path),
        "recommendations": _csv_snapshot(export.recommendations_path),
        "json_summary": {
            "review_id": json_payload["review"]["review_id"],
            "name": json_payload["review"]["name"],
            "drawing_count": len(json_payload["review"]["drawing_sheets"]),
            "specification_count": len(
                json_payload["review"]["specification_sections"]
            ),
            "brief_title": json_payload["brief"]["brief_title"],
            "brief_action_count": len(
                json_payload["brief"]["prioritized_reviewer_actions"] or []
            ),
            "readiness_status": (
                json_payload["review"]["readiness"]["status"]
                if json_payload["review"]["readiness"]
                else None
            ),
        },
        "markdown_summary": {
            "line_count": len(markdown_lines),
            "first_12_lines": markdown_lines[:12],
        },
    } == {
        "drawing_index": {
            "rows": 6,
            "first_row": {
                "sheet_id": "av-101",
                "sheet_number": "AV-101",
                "title": "Lobby Digital Signage",
                "discipline": "audiovisual",
                "source_file": "",
                "page_number": "",
                "revision": "",
                "issue_date": "",
                "confidence": "0.75",
                "notes": "[]",
            },
        },
        "specification_index": {
            "rows": 4,
            "first_row": {
                "section_id": "27-41-16",
                "section_number": "27 41 16",
                "title": "Integrated Audio Systems",
                "discipline": "audiovisual",
                "source_file": "",
                "page_start": "",
                "page_end": "",
                "confidence": "0.75",
                "manufacturers": "[]",
                "notes": "[]",
            },
        },
        "equipment_matrix": {
            "rows": 10,
            "first_row": {
                "project_building_id": "maw-music-education-center",
                "building_name": "MAW Music Education Center",
                "room_id": "maw-recital-hall",
                "room_name": "Recital Hall",
                "space_id": "",
                "space_name": "",
                "scene_id": "",
                "scene_name": "",
                "system_id": "maw-performance-audio",
                "system_name": "Performance Audio",
                "system_category": "audio",
                "equipment_id": "maw-recital-speakers",
                "equipment_category": "speaker",
                "description": "Meyer Sound recital hall loudspeakers",
                "quantity": "4",
                "manufacturer": "Meyer Sound",
                "model": "ULTRA-X40",
                "labor_template": "",
                "assumptions": "",
                "budget_cost": "",
                "sell_price": "",
                "review_required": "False",
                "confidence": "0.92",
                "status": "detected",
                "drawing_reference": "AV-401",
                "specification_reference": "27 41 16",
            },
        },
        "review_report": {
            "rows": 5,
            "first_row": {
                "source": "resolver",
                "target_id": "maw-recital-speakers",
                "rule_id": "RULE-001",
                "message": "Passive speakers require an amplifier. No amplifier was detected in this system.",
                "severity": "review",
                "manufacturer": "",
            },
        },
        "scope_gaps": {
            "rows": 4,
            "first_row": {
                "gap_id": "speaker_missing_amplifier",
                "target_id": "maw-recital-speakers",
                "message": "Speaker equipment is present, but no amplifier was detected in the same system.",
                "severity": "high",
                "suggested_action": "Add amplifier channel capacity review and placeholder amplifier.",
                "confidence": "0.75",
            },
        },
        "estimator_risks": {
            "rows": 3,
            "first_row": {
                "risk_id": "scope_gaps_detected",
                "category": "scope",
                "message": "Scope gaps were detected and require estimator review.",
                "risk_level": "high",
                "confidence": "0.75",
            },
        },
        "recommendations": {
            "rows": 4,
            "first_row": {
                "recommendation_id": "scope-gap-speaker_missing_amplifier-maw-recital-speakers",
                "category": "scope_gap",
                "message": "Add amplifier channel capacity review and placeholder amplifier.",
                "priority": "high",
                "target_id": "maw-recital-speakers",
            },
        },
        "json_summary": {
            "review_id": "maw-plan-review",
            "name": "MAW Music Education Center Plan Review",
            "drawing_count": 6,
            "specification_count": 4,
            "brief_title": "Estimator Brief - MAW Music Education Center Plan Review",
            "brief_action_count": 6,
            "readiness_status": "ready",
        },
        "markdown_summary": {
            "line_count": 189,
            "first_12_lines": [
                "# MAW Music Education Center Plan Review",
                "",
                "## Final Estimator Review",
                "",
                "- Executive Summary: Bid package appears ready for pricing.",
                "- Readiness: ready - Plan review is bid-ready with explicit assumptions.",
                "- Completeness: partial (80%)",
                "- Confidence: 66%",
                "- Total Issues: 17",
                "- Total Recommendations: 4",
                "- Total Engineering Assumptions: 11",
                "- Next Actions:",
            ],
        },
    }

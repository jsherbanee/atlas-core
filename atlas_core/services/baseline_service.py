"""Estimate baseline service helpers for Atlas Core."""

from __future__ import annotations

from typing import TYPE_CHECKING

from atlas_core.services.estimate_workflow_service import EstimateWorkflowResult

if TYPE_CHECKING:
    from atlas_core.domain import EstimateBaseline


class BaselineService:
    def create_baseline_from_workflow(
        self,
        baseline_id: str,
        project_id: str,
        name: str,
        workflow_result: EstimateWorkflowResult,
        created_by: str | None = None,
        award: bool = False,
    ) -> EstimateBaseline:
        from atlas_core.domain import EstimateBaseline

        baseline = EstimateBaseline(
            baseline_id=baseline_id,
            project_id=project_id,
            name=name,
            rows=workflow_result.rows,
            created_by=created_by,
        )

        if award:
            baseline.award()

        baseline.add_note("Baseline created from estimate workflow.")

        if workflow_result.placeholder_equipment_count > 0:
            baseline.add_note(
                "Baseline includes placeholder equipment requiring review."
            )

        return baseline

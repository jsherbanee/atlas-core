"""JSON export helpers for Atlas Core services."""

import json
from pathlib import Path

from atlas_core.services.plan_review_workflow_service import PlanReviewWorkflowResult


class JsonExportService:
    def export_plan_review_result(
        self,
        result: PlanReviewWorkflowResult,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                result.to_dict(),
                file,
                indent=2,
                sort_keys=False,
            )

        return path

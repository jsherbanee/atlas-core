"""Markdown export helpers for Atlas Core services."""

from pathlib import Path

from atlas_core.services.plan_review_workflow_service import PlanReviewWorkflowResult


class MarkdownExportService:
    def export_plan_review_summary(
        self,
        result: PlanReviewWorkflowResult,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        content = self._plan_review_summary(result)
        path.write_text(content, encoding="utf-8")
        return path

    def _plan_review_summary(self, result: PlanReviewWorkflowResult) -> str:
        brief = result.brief
        lines = [
            f"# {brief.name}",
            "",
            f"Project ID: {brief.project_id}",
            f"Review ID: {brief.review_id}",
            f"Drawing count: {brief.drawing_count}",
            f"Specification count: {brief.specification_count}",
            f"System count: {brief.system_count}",
            f"Equipment count: {brief.equipment_count}",
            f"Issue count: {brief.issue_count}",
            f"Placeholder count: {brief.placeholder_count}",
            f"Review required count: {brief.review_required_count}",
            f"Confidence: {self._confidence_percentage(brief.confidence)}",
            "",
            "## Review Items",
            "",
        ]

        if not result.review.review_report:
            lines.append("No review items found.")
        else:
            for item in result.review.review_report:
                lines.append(
                    f"- [{item.source}] {item.target_id}: {item.message}"
                )

        return "\n".join(lines) + "\n"

    @staticmethod
    def _confidence_percentage(confidence: float) -> str:
        percentage = confidence * 100
        if percentage.is_integer():
            return f"{percentage:.0f}%"

        return f"{percentage:.1f}%"

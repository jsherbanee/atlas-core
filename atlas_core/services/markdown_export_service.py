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
        ]
        if hasattr(brief, "cross_reference_count"):
            lines.append(f"Cross reference count: {brief.cross_reference_count}")

        if hasattr(brief, "scope_gap_count"):
            lines.append(f"Scope gap count: {brief.scope_gap_count}")

        lines.extend(
            [
                f"Confidence: {self._confidence_percentage(brief.confidence)}",
                "",
                "## Review Items",
                "",
            ]
        )

        if not result.review.review_report:
            lines.append("No review items found.")
        else:
            for item in result.review.review_report:
                lines.append(f"- [{item.source}] {item.target_id}: {item.message}")

        lines.extend(["", "## Cross References", ""])

        if not result.review.cross_references:
            lines.append("No cross references found.")
        else:
            for reference in result.review.cross_references:
                lines.append(
                    f"- [{getattr(reference.reference_type, 'value', reference.reference_type)}] "
                    f"{reference.source_id} -> {reference.target_id}: {reference.message}"
                )

        lines.extend(["", "## Scope Gaps", ""])

        if not result.review.scope_gaps:
            lines.append("No scope gaps found.")
        else:
            for gap in result.review.scope_gaps:
                lines.append(
                    f"- [{getattr(gap.severity, 'value', gap.severity)}] {gap.target_id}: {gap.message}"
                )
                if gap.suggested_action:
                    lines.append(f"  Suggested action: {gap.suggested_action}")

        lines.extend(["", "## Scope Reconciliation", ""])

        if not getattr(result.review, "reconciliation_issues", None):
            lines.append("No scope reconciliation issues found.")
        else:
            for issue in result.review.reconciliation_issues:
                lines.append(
                    f"- [{getattr(issue.severity, 'value', issue.severity)}] {issue.message}"
                )
                if issue.target_id:
                    lines.append(f"  Target ID: {issue.target_id}")
                if issue.suggested_action:
                    lines.append(f"  Suggested action: {issue.suggested_action}")

        lines.extend(["", "## Bid Completeness", ""])

        bid_completeness = getattr(result.review, "bid_completeness", None)
        if bid_completeness is None:
            lines.append("No bid completeness assessment available.")
        else:
            lines.extend(
                [
                    f"- Status: {getattr(bid_completeness.status, 'value', bid_completeness.status)}",
                    f"- Score: {self._confidence_percentage(bid_completeness.score)}",
                    (
                        "- Drawing completeness: "
                        f"{self._confidence_percentage(bid_completeness.drawing_completeness)}"
                    ),
                    (
                        "- Specification completeness: "
                        f"{self._confidence_percentage(bid_completeness.specification_completeness)}"
                    ),
                    (
                        "- System completeness: "
                        f"{self._confidence_percentage(bid_completeness.system_completeness)}"
                    ),
                    (
                        "- Equipment completeness: "
                        f"{self._confidence_percentage(bid_completeness.equipment_completeness)}"
                    ),
                    (
                        "- Schedule completeness: "
                        f"{self._confidence_percentage(bid_completeness.schedule_completeness)}"
                    ),
                ]
            )

            lines.append("- Missing items:")
            if bid_completeness.missing_items:
                for missing_item in bid_completeness.missing_items:
                    lines.append(f"  - {missing_item}")
            else:
                lines.append("  - None")

        lines.extend(["", "## Estimator Risks", ""])

        if not result.review.estimator_risks:
            lines.append("No estimator risks found.")
        else:
            for risk in result.review.estimator_risks:
                lines.append(
                    f"- [{getattr(risk.risk_level, 'value', risk.risk_level)}] "
                    f"{risk.category}: {risk.message}"
                )

        lines.extend(["", "## Recommendations", ""])

        if not result.review.recommendations:
            lines.append("No recommendations found.")
        else:
            for recommendation in result.review.recommendations:
                lines.append(
                    f"- [{getattr(recommendation.priority, 'value', recommendation.priority)}] "
                    f"{recommendation.category}: {recommendation.message}"
                )

        # Drawing metadata
        lines.extend(["", "## Drawing Metadata", ""])

        if not getattr(result.review, "drawing_metadata", None):
            lines.append("No drawing metadata extracted.")
        else:
            for md in result.review.drawing_metadata:
                # md is expected to have sheet_number, title, referenced_sheet_numbers,
                # referenced_specification_sections, and room_names attributes.
                lines.append(f"- {md.sheet_number} - {md.title}")
                if getattr(md, "referenced_sheet_numbers", None):
                    lines.append(
                        "  Referenced sheets: " + ", ".join(md.referenced_sheet_numbers)
                    )
                if getattr(md, "referenced_specification_sections", None):
                    lines.append(
                        "  Referenced specifications: "
                        + ", ".join(md.referenced_specification_sections)
                    )
                if getattr(md, "room_names", None):
                    lines.append("  Rooms: " + ", ".join(md.room_names))

        lines.extend(["", "## Device Schedules", ""])

        if not getattr(result.review, "device_schedules", None):
            lines.append("No device schedules extracted.")
        else:
            for schedule in result.review.device_schedules:
                lines.append(
                    f"- {schedule.schedule_id}: {schedule.title} ({schedule.item_count()} items)"
                )

        lines.extend(["", "## Keynotes", ""])

        if not getattr(result.review, "keynotes", None):
            lines.append("No keynotes extracted.")
        else:
            for keynote in result.review.keynotes:
                lines.append(
                    f"- {keynote.source_sheet_number} keynote {keynote.number}: {keynote.description}"
                )

        lines.extend(["", "## Legends", ""])

        if not getattr(result.review, "legends", None):
            lines.append("No legends extracted.")
        else:
            for legend in result.review.legends:
                lines.append(
                    f"- {legend.source_sheet_number}: {legend.item_count()} items"
                )
                for legend_item in legend.items:
                    lines.append(f"  - {legend_item.symbol}: {legend_item.description}")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _confidence_percentage(confidence: float) -> str:
        percentage = confidence * 100
        if percentage.is_integer():
            return f"{percentage:.0f}%"

        return f"{percentage:.1f}%"

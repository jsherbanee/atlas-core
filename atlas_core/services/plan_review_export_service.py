"""Plan review export orchestration for Atlas Core services."""

from dataclasses import dataclass
from pathlib import Path

from atlas_core.services import (
    CsvExportService,
    EquipmentMatrixService,
    MarkdownExportService,
    PlanReviewWorkflowResult,
)
from atlas_core.services.json_export_service import JsonExportService


@dataclass
class PlanReviewExportResult:
    estimator_brief_path: Path
    final_estimator_review_path: Path
    json_path: Path
    drawing_index_path: Path
    specification_index_path: Path
    device_schedules_path: Path
    keynotes_path: Path
    legends_path: Path
    reconciliation_issues_path: Path
    equipment_matrix_path: Path
    review_report_path: Path
    scope_gaps_path: Path
    estimator_risks_path: Path
    recommendations_path: Path
    markdown_summary_path: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "estimator_brief_path": str(self.estimator_brief_path),
            "final_estimator_review_path": str(self.final_estimator_review_path),
            "json_path": str(self.json_path),
            "drawing_index_path": str(self.drawing_index_path),
            "specification_index_path": str(self.specification_index_path),
            "device_schedules_path": str(self.device_schedules_path),
            "keynotes_path": str(self.keynotes_path),
            "legends_path": str(self.legends_path),
            "reconciliation_issues_path": str(self.reconciliation_issues_path),
            "equipment_matrix_path": str(self.equipment_matrix_path),
            "review_report_path": str(self.review_report_path),
            "scope_gaps_path": str(self.scope_gaps_path),
            "estimator_risks_path": str(self.estimator_risks_path),
            "recommendations_path": str(self.recommendations_path),
            "markdown_summary_path": str(self.markdown_summary_path),
        }


class PlanReviewExportService:
    def __init__(
        self,
        csv_export_service: CsvExportService | None = None,
        json_export_service: JsonExportService | None = None,
        markdown_export_service: MarkdownExportService | None = None,
    ) -> None:
        self.csv_export_service = csv_export_service or CsvExportService()
        self.json_export_service = json_export_service or JsonExportService()
        self.markdown_export_service = (
            markdown_export_service or MarkdownExportService()
        )

    def export_plan_review(
        self,
        result: PlanReviewWorkflowResult,
        output_dir: str | Path,
        prefix: str = "plan_review",
    ) -> PlanReviewExportResult:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        estimator_brief_path = self.csv_export_service.export_estimator_brief(
            result.brief,
            output_path / f"{prefix}_estimator_brief.csv",
        )
        final_review = getattr(result, "final_review", None)
        if final_review is None:
            from atlas_core.services import FinalEstimatorReviewService

            final_review = FinalEstimatorReviewService().build(result.review)

        final_estimator_review_path = (
            self.csv_export_service.export_final_estimator_review(
                final_review,
                output_path / f"{prefix}_final_estimator_review.csv",
            )
        )
        json_path = self.json_export_service.export_plan_review_result(
            result,
            output_path / f"{prefix}_plan_review.json",
        )
        drawing_index_path = self.csv_export_service.export_drawing_index(
            result.review.drawing_sheets,
            output_path / f"{prefix}_drawing_index.csv",
        )
        specification_index_path = self.csv_export_service.export_specification_index(
            result.review.specification_sections,
            output_path / f"{prefix}_specification_index.csv",
        )
        device_schedules_path = self.csv_export_service.export_device_schedules(
            result.review.device_schedules,
            output_path / f"{prefix}_device_schedules.csv",
        )
        keynotes_path = self.csv_export_service.export_keynotes(
            result.review.keynotes,
            output_path / f"{prefix}_keynotes.csv",
        )
        legends_path = self.csv_export_service.export_legends(
            result.review.legends,
            output_path / f"{prefix}_legends.csv",
        )
        reconciliation_issues_path = (
            self.csv_export_service.export_reconciliation_issues(
                result.review.reconciliation_issues,
                output_path / f"{prefix}_reconciliation_issues.csv",
            )
        )
        equipment_matrix_path = self.csv_export_service.export_equipment_matrix(
            self._equipment_matrix_rows(result),
            output_path / f"{prefix}_equipment_matrix.csv",
        )
        review_report_path = self.csv_export_service.export_review_report(
            result.review.review_report,
            output_path / f"{prefix}_review_report.csv",
        )
        scope_gaps_path = self.csv_export_service.export_scope_gaps(
            result.review.scope_gaps,
            output_path / f"{prefix}_scope_gaps.csv",
        )
        estimator_risks_path = self.csv_export_service.export_estimator_risks(
            result.review.estimator_risks,
            output_path / f"{prefix}_estimator_risks.csv",
        )
        recommendations_path = self.csv_export_service.export_recommendations(
            result.review.recommendations,
            output_path / f"{prefix}_recommendations.csv",
        )
        markdown_summary_path = self.markdown_export_service.export_plan_review_summary(
            result,
            output_path / f"{prefix}_summary.md",
        )

        return PlanReviewExportResult(
            estimator_brief_path=estimator_brief_path,
            final_estimator_review_path=final_estimator_review_path,
            json_path=json_path,
            drawing_index_path=drawing_index_path,
            specification_index_path=specification_index_path,
            device_schedules_path=device_schedules_path,
            keynotes_path=keynotes_path,
            legends_path=legends_path,
            reconciliation_issues_path=reconciliation_issues_path,
            equipment_matrix_path=equipment_matrix_path,
            review_report_path=review_report_path,
            scope_gaps_path=scope_gaps_path,
            estimator_risks_path=estimator_risks_path,
            recommendations_path=recommendations_path,
            markdown_summary_path=markdown_summary_path,
        )

    @staticmethod
    def _equipment_matrix_rows(result: PlanReviewWorkflowResult) -> list:
        rows = getattr(result, "rows", None)
        if rows is not None:
            return list(rows)

        review = result.review
        return EquipmentMatrixService(
            buildings=getattr(review, "buildings", []),
            rooms=getattr(review, "rooms", []),
            spaces=getattr(review, "spaces", []),
            scenes=getattr(review, "scenes", []),
            systems=review.systems,
            equipment=review.equipment,
        ).build_rows()

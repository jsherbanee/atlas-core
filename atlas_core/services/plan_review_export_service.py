"""Plan review export orchestration for Atlas Core services."""

from dataclasses import dataclass
from pathlib import Path

from atlas_core.services import (
    CsvExportService,
    EquipmentMatrixService,
    MarkdownExportService,
    PlanReviewWorkflowResult,
)


@dataclass
class PlanReviewExportResult:
    estimator_brief_path: Path
    drawing_index_path: Path
    specification_index_path: Path
    equipment_matrix_path: Path
    review_report_path: Path
    scope_gaps_path: Path
    markdown_summary_path: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "estimator_brief_path": str(self.estimator_brief_path),
            "drawing_index_path": str(self.drawing_index_path),
            "specification_index_path": str(self.specification_index_path),
            "equipment_matrix_path": str(self.equipment_matrix_path),
            "review_report_path": str(self.review_report_path),
            "scope_gaps_path": str(self.scope_gaps_path),
            "markdown_summary_path": str(self.markdown_summary_path),
        }


class PlanReviewExportService:
    def __init__(
        self,
        csv_export_service: CsvExportService | None = None,
        markdown_export_service: MarkdownExportService | None = None,
    ) -> None:
        self.csv_export_service = csv_export_service or CsvExportService()
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
        drawing_index_path = self.csv_export_service.export_drawing_index(
            result.review.drawing_sheets,
            output_path / f"{prefix}_drawing_index.csv",
        )
        specification_index_path = (
            self.csv_export_service.export_specification_index(
                result.review.specification_sections,
                output_path / f"{prefix}_specification_index.csv",
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
        markdown_summary_path = (
            self.markdown_export_service.export_plan_review_summary(
                result,
                output_path / f"{prefix}_summary.md",
            )
        )

        return PlanReviewExportResult(
            estimator_brief_path=estimator_brief_path,
            drawing_index_path=drawing_index_path,
            specification_index_path=specification_index_path,
            equipment_matrix_path=equipment_matrix_path,
            review_report_path=review_report_path,
            scope_gaps_path=scope_gaps_path,
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

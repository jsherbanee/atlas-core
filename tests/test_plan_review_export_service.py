from atlas_core.domain import (
    BidPackageReview,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.services import (
    EstimatorBrief,
    PlanReviewExportService,
    PlanReviewWorkflowResult,
    ReviewReportItem,
)


def make_result() -> PlanReviewWorkflowResult:
    system = IntegratedSystem(
        system_id="sys-001",
        name="Audio System",
        category=SystemCategory.AUDIO,
    )
    equipment = Equipment(
        equipment_id="eq-001",
        description="Main loudspeaker",
        category=EquipmentCategory.SPEAKER,
        system_id=system.system_id,
    )

    return PlanReviewWorkflowResult(
        review=BidPackageReview(
            review_id="review-001",
            project_id="project-001",
            name="Plan Review",
            drawing_sheets=[
                DrawingSheet(
                    sheet_id="av-101",
                    sheet_number="AV-101",
                    title="Audio Plan",
                )
            ],
            specification_sections=[
                SpecificationSection(
                    section_id="27-41-16",
                    section_number="27 41 16",
                    title="Integrated Audio Systems",
                )
            ],
            systems=[system],
            equipment=[equipment],
            review_report=[
                ReviewReportItem(
                    source="resolver",
                    target_id=equipment.equipment_id,
                    message="Review item.",
                )
            ],
        ),
        brief=EstimatorBrief(
            review_id="review-001",
            project_id="project-001",
            name="Plan Review",
            drawing_count=1,
            specification_count=1,
            system_count=1,
            equipment_count=1,
            issue_count=1,
            placeholder_count=0,
            review_required_count=1,
            confidence=0.75,
        ),
    )


def test_exports_all_plan_review_files(tmp_path):
    result = PlanReviewExportService().export_plan_review(make_result(), tmp_path)

    assert result.estimator_brief_path.exists()
    assert result.drawing_index_path.exists()
    assert result.specification_index_path.exists()
    assert result.equipment_matrix_path.exists()
    assert result.review_report_path.exists()
    assert result.markdown_summary_path.exists()


def test_creates_output_directory(tmp_path):
    output_dir = tmp_path / "exports"

    PlanReviewExportService().export_plan_review(make_result(), output_dir)

    assert output_dir.exists()


def test_supports_custom_prefix(tmp_path):
    result = PlanReviewExportService().export_plan_review(
        make_result(),
        tmp_path,
        prefix="maw",
    )

    assert result.estimator_brief_path == tmp_path / "maw_estimator_brief.csv"
    assert result.drawing_index_path == tmp_path / "maw_drawing_index.csv"
    assert (
        result.specification_index_path
        == tmp_path / "maw_specification_index.csv"
    )
    assert result.equipment_matrix_path == tmp_path / "maw_equipment_matrix.csv"
    assert result.review_report_path == tmp_path / "maw_review_report.csv"
    assert result.markdown_summary_path == tmp_path / "maw_summary.md"


def test_to_dict_returns_string_paths(tmp_path):
    result = PlanReviewExportService().export_plan_review(make_result(), tmp_path)

    assert result.to_dict() == {
        "estimator_brief_path": str(result.estimator_brief_path),
        "drawing_index_path": str(result.drawing_index_path),
        "specification_index_path": str(result.specification_index_path),
        "equipment_matrix_path": str(result.equipment_matrix_path),
        "review_report_path": str(result.review_report_path),
        "markdown_summary_path": str(result.markdown_summary_path),
    }
    assert all(isinstance(value, str) for value in result.to_dict().values())

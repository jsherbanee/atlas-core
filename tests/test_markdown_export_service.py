from atlas_core.domain import BidPackageReview
from atlas_core.services import (
    CrossReference,
    EstimatorBrief,
    MarkdownExportService,
    PlanReviewWorkflowResult,
    ReviewReportItem,
)


def make_result(
    review_report: list[ReviewReportItem] | None = None,
    cross_references: list[CrossReference] | None = None,
) -> PlanReviewWorkflowResult:
    return PlanReviewWorkflowResult(
        review=BidPackageReview(
            review_id="review-001",
            project_id="project-001",
            name="Plan Review",
            review_report=list(review_report or []),
            cross_references=list(cross_references or []),
        ),
        brief=EstimatorBrief(
            review_id="review-001",
            project_id="project-001",
            name="Plan Review",
            drawing_count=2,
            specification_count=3,
            system_count=4,
            equipment_count=5,
            issue_count=6,
            placeholder_count=1,
            review_required_count=2,
            cross_reference_count=len(cross_references or []),
            scope_gap_count=0,
            confidence=0.75,
        ),
    )


def test_exports_markdown_file(tmp_path):
    output_path = tmp_path / "summary.md"

    written_path = MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    assert written_path == output_path
    assert output_path.exists()


def test_creates_parent_directory(tmp_path):
    output_path = tmp_path / "exports" / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    assert output_path.exists()


def test_includes_title(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    assert "# Plan Review" in output_path.read_text(encoding="utf-8")


def test_includes_brief_counts(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )
    content = output_path.read_text(encoding="utf-8")

    assert "Project ID: project-001" in content
    assert "Review ID: review-001" in content
    assert "Drawing count: 2" in content
    assert "Specification count: 3" in content
    assert "System count: 4" in content
    assert "Equipment count: 5" in content
    assert "Issue count: 6" in content
    assert "Placeholder count: 1" in content
    assert "Review required count: 2" in content
    assert "Cross reference count: 0" in content
    assert "Scope gap count: 0" in content
    assert "Confidence: 75%" in content


def test_includes_review_items(tmp_path):
    output_path = tmp_path / "summary.md"
    item = ReviewReportItem(
        source="resolver",
        target_id="eq-001",
        message="Missing amplifier.",
    )

    MarkdownExportService().export_plan_review_summary(
        make_result(review_report=[item]),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "## Review Items" in content
    assert "- [resolver] eq-001: Missing amplifier." in content


def test_handles_no_review_items(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "## Review Items" in content
    assert "No review items found." in content


def test_includes_cross_references_section(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "## Cross References" in content


def test_includes_cross_reference_items(tmp_path):
    output_path = tmp_path / "summary.md"
    item = CrossReference(
        reference_type="equipment_to_drawing",
        source_id="eq-001",
        target_id="av101",
        message="Equipment references drawing.",
    )

    MarkdownExportService().export_plan_review_summary(
        make_result(cross_references=[item]),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert (
        "- [equipment_to_drawing] eq-001 -> av101: "
        "Equipment references drawing."
    ) in content


def test_handles_no_cross_references(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "No cross references found." in content


def test_includes_cross_reference_count_when_present(tmp_path):
    output_path = tmp_path / "summary.md"
    item = CrossReference(
        reference_type="equipment_to_drawing",
        source_id="eq-001",
        target_id="av101",
        message="Equipment references drawing.",
    )

    MarkdownExportService().export_plan_review_summary(
        make_result(cross_references=[item]),
        output_path,
    )

    assert "Cross reference count: 1" in output_path.read_text(
        encoding="utf-8"
    )

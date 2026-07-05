import json

from atlas_core.domain import BidPackageReview
from atlas_core.services import (
    EstimatorBrief,
    FinalEstimatorReview,
    JsonExportService,
    PlanReviewWorkflowResult,
)


def make_result() -> PlanReviewWorkflowResult:
    review = BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )
    brief = EstimatorBrief(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        drawing_count=0,
        specification_count=0,
        system_count=0,
        equipment_count=0,
        issue_count=0,
        placeholder_count=0,
        review_required_count=0,
        cross_reference_count=0,
        reconciliation_issue_count=0,
        scope_gap_count=0,
        estimator_risk_count=0,
        keynote_count=0,
        legend_count=0,
        legend_item_count=0,
        room_count=0,
        confidence=0.75,
    )
    final_review = FinalEstimatorReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        executive_summary="Bid package review summary is available.",
        next_actions=["Proceed with pricing review."],
    )

    return PlanReviewWorkflowResult(
        review=review,
        brief=brief,
        final_review=final_review,
    )


def test_exports_json_file(tmp_path):
    output_path = tmp_path / "result.json"

    written_path = JsonExportService().export_plan_review_result(
        make_result(), output_path
    )

    assert written_path == output_path
    assert output_path.exists()


def test_creates_parent_directory(tmp_path):
    output_path = tmp_path / "exports" / "result.json"

    JsonExportService().export_plan_review_result(make_result(), output_path)

    assert output_path.exists()


def test_includes_review(tmp_path):
    output_path = tmp_path / "result.json"

    JsonExportService().export_plan_review_result(make_result(), output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "review" in payload


def test_includes_brief(tmp_path):
    output_path = tmp_path / "result.json"

    JsonExportService().export_plan_review_result(make_result(), output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "brief" in payload


def test_includes_final_review(tmp_path):
    output_path = tmp_path / "result.json"

    JsonExportService().export_plan_review_result(make_result(), output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "final_review" in payload
    assert payload["final_review"]["review_id"] == "review-001"


def test_output_is_valid_json(tmp_path):
    output_path = tmp_path / "result.json"

    JsonExportService().export_plan_review_result(make_result(), output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)

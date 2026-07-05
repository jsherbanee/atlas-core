from atlas_core.domain import (
    BidPackageReview,
    DeviceSchedule,
    DeviceScheduleItem,
    Keynote,
    Legend,
    LegendItem,
)
from atlas_core.services import (
    CrossReference,
    EstimatorBrief,
    EstimatorRisk,
    MarkdownExportService,
    PlanReviewWorkflowResult,
    ReviewReportItem,
    ScopeGap,
    CrossReferenceType,
)


def make_result(
    review_report: list[ReviewReportItem] | None = None,
    cross_references: list[CrossReference] | None = None,
    scope_gaps: list[ScopeGap] | None = None,
    estimator_risks: list[EstimatorRisk] | None = None,
) -> PlanReviewWorkflowResult:
    return PlanReviewWorkflowResult(
        review=BidPackageReview(
            review_id="review-001",
            project_id="project-001",
            name="Plan Review",
            review_report=list(review_report or []),
            cross_references=list(cross_references or []),
            scope_gaps=list(scope_gaps or []),
            estimator_risks=list(estimator_risks or []),
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
            scope_gap_count=len(scope_gaps or []),
            estimator_risk_count=len(estimator_risks or []),
            keynote_count=0,
            legend_count=0,
            legend_item_count=0,
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
        reference_type=CrossReferenceType.EQUIPMENT_TO_DRAWING,
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
        "- [equipment_to_drawing] eq-001 -> av101: " "Equipment references drawing."
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

    assert "Cross reference count: 1" in output_path.read_text(encoding="utf-8")


def test_includes_scope_gaps_section(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "## Scope Gaps" in content


def test_includes_scope_gap_items(tmp_path):
    output_path = tmp_path / "summary.md"
    gap = ScopeGap(
        gap_id="projector_missing_mount",
        target_id="projector-001",
        message="Projector is missing a mount.",
        severity="high",
        suggested_action="Add projector mount allowance.",
    )

    MarkdownExportService().export_plan_review_summary(
        make_result(scope_gaps=[gap]),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "- [high] projector-001: Projector is missing a mount." in content
    assert "  Suggested action: Add projector mount allowance." in content
    assert "Scope gap count: 1" in content


def test_handles_no_scope_gaps(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "No scope gaps found." in content


def test_includes_estimator_risks_section(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "## Estimator Risks" in content


def test_includes_estimator_risk_items(tmp_path):
    output_path = tmp_path / "summary.md"
    risk = EstimatorRisk(
        risk_id="scope_gaps_detected",
        message="Scope gaps were detected and require estimator review.",
        risk_level="high",
        category="scope",
    )

    MarkdownExportService().export_plan_review_summary(
        make_result(estimator_risks=[risk]),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert (
        "- [high] scope: Scope gaps were detected and require estimator review."
    ) in content


def test_handles_no_estimator_risks(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "No estimator risks found." in content


def test_includes_drawing_metadata_section(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "## Drawing Metadata" in content


def test_includes_drawing_metadata_items(tmp_path):
    output_path = tmp_path / "summary.md"

    # create a BidPackageReview with drawing metadata included
    md_item = {
        "sheet_number": "AV1.01",
        "title": "AV Plan",
        "referenced_sheet_numbers": ["A-701"],
        "referenced_specification_sections": ["27 41 16"],
        "room_names": ["Main Lobby"],
    }

    # construct PlanReviewWorkflowResult manually
    result = make_result()
    # attach drawing metadata dicts directly to review.drawing_metadata
    result.review.drawing_metadata = [
        # use the domain/data class to serialize in export implementation
        __import__(
            "atlas_core.services.drawing_metadata_service", fromlist=["DrawingMetadata"]
        ).DrawingMetadata(
            sheet_number=md_item["sheet_number"],
            title=md_item["title"],
            referenced_sheet_numbers=md_item["referenced_sheet_numbers"],
            referenced_specification_sections=md_item[
                "referenced_specification_sections"
            ],
            room_names=md_item["room_names"],
        )
    ]

    MarkdownExportService().export_plan_review_summary(result, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "AV1.01 - AV Plan" in content
    assert "Referenced sheets: A-701" in content
    assert "Referenced specifications: 27 41 16" in content
    assert "Rooms: Main Lobby" in content


def test_includes_device_schedules_section_with_empty_message(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "## Device Schedules" in content
    assert "No device schedules extracted." in content


def test_includes_device_schedules_items(tmp_path):
    output_path = tmp_path / "summary.md"
    result = make_result()
    result.review.device_schedules = [
        DeviceSchedule(
            schedule_id="sched-1",
            title="Audio Device Schedule",
            items=[
                DeviceScheduleItem(
                    item_id="sched-1-spk-1",
                    tag="SPK-1",
                    description="Main loudspeaker",
                )
            ],
        )
    ]

    MarkdownExportService().export_plan_review_summary(result, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "- sched-1: Audio Device Schedule (1 items)" in content


def test_includes_keynotes_section_with_empty_message(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "## Keynotes" in content
    assert "No keynotes extracted." in content


def test_includes_keynotes_items(tmp_path):
    output_path = tmp_path / "summary.md"
    result = make_result()
    result.review.keynotes = [
        Keynote(
            keynote_id="av1.01-keynote-k1",
            number="K1",
            description="Ceiling Speaker",
            source_sheet_number="AV1.01",
        )
    ]

    MarkdownExportService().export_plan_review_summary(result, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "- AV1.01 keynote K1: Ceiling Speaker" in content


def test_includes_legends_section_with_empty_message(tmp_path):
    output_path = tmp_path / "summary.md"

    MarkdownExportService().export_plan_review_summary(
        make_result(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "## Legends" in content
    assert "No legends extracted." in content


def test_includes_legend_items(tmp_path):
    output_path = tmp_path / "summary.md"
    result = make_result()
    result.review.legends = [
        Legend(
            legend_id="av1.01-legend",
            source_sheet_number="AV1.01",
            items=[
                LegendItem(
                    legend_item_id="av1.01-legend-spk",
                    symbol="SPK",
                    description="Ceiling Speaker",
                ),
                LegendItem(
                    legend_item_id="av1.01-legend-cam",
                    symbol="CAM",
                    description="PTZ Camera",
                ),
            ],
        )
    ]

    MarkdownExportService().export_plan_review_summary(result, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "- AV1.01: 2 items" in content
    assert "  - SPK: Ceiling Speaker" in content
    assert "  - CAM: PTZ Camera" in content

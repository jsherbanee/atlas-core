from atlas_core.domain import (
    BidPackageReview,
    DetailCallout,
    DeviceSchedule,
    DeviceScheduleItem,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    Keynote,
    Legend,
    LegendItem,
    Room,
    RoomType,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.services import (
    FinalEstimatorReview,
    EstimatorBrief,
    EstimatorRisk,
    PlanReviewExportService,
    PlanReviewWorkflowResult,
    ReconciliationIssue,
    ReviewReportItem,
    ScopeGap,
    RiskLevel,
    ScopeGapSeverity,
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
            rooms=[
                Room(
                    room_id="building-001-main-lobby",
                    name="Main Lobby",
                    building_id="building-001",
                    room_type=RoomType.LOBBY,
                )
            ],
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
            device_schedules=[
                DeviceSchedule(
                    schedule_id="sched-1",
                    source_sheet_number="AV-101",
                    items=[
                        DeviceScheduleItem(
                            item_id="sched-1-spk-1",
                            tag="SPK-1",
                            description="Main loudspeaker",
                        )
                    ],
                )
            ],
            keynotes=[
                Keynote(
                    keynote_id="kn-001",
                    number="1",
                    description="Provide ceiling speaker.",
                )
            ],
            legends=[
                Legend(
                    legend_id="legend-001",
                    title="AV Symbols",
                    items=[
                        LegendItem(
                            legend_item_id="li-001",
                            symbol="SPK",
                            description="Ceiling Speaker",
                        )
                    ],
                )
            ],
            detail_callouts=[
                DetailCallout(
                    callout_id="av-101-detail-5-av-701",
                    detail_number="5",
                    source_sheet_number="AV-101",
                    target_sheet_number="AV-701",
                    description="Detail 5/AV-701",
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
            reconciliation_issues=[
                ReconciliationIssue(
                    issue_id="keynote_missing_equipment_category:projector",
                    message=(
                        "Keynote references equipment category not found in "
                        "equipment matrix."
                    ),
                    target_id="kn-001",
                )
            ],
            scope_gaps=[
                ScopeGap(
                    gap_id="speaker_missing_amplifier",
                    target_id=equipment.equipment_id,
                    message="Speaker equipment is missing an amplifier.",
                    severity=ScopeGapSeverity.HIGH,
                )
            ],
            estimator_risks=[
                EstimatorRisk(
                    risk_id="scope_gaps_detected",
                    message="Scope gaps were detected.",
                    risk_level=RiskLevel.HIGH,
                    category="scope",
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
            room_count=1,
            detail_callout_count=0,
            issue_count=1,
            placeholder_count=0,
            review_required_count=1,
            cross_reference_count=0,
            reconciliation_issue_count=0,
            scope_gap_count=1,
            estimator_risk_count=1,
            keynote_count=0,
            legend_count=0,
            legend_item_count=0,
            confidence=0.75,
        ),
        final_review=FinalEstimatorReview(
            review_id="review-001",
            project_id="project-001",
            name="Plan Review",
            readiness_status="needs_review",
            readiness_message="Plan review needs estimator review before pricing.",
            completeness_status="partial",
            completeness_score=0.7,
            confidence=0.75,
            total_issues=3,
            total_recommendations=1,
            executive_summary="Bid package requires estimator review before pricing.",
            next_actions=["Review confidence before pricing."],
        ),
    )


def test_exports_all_plan_review_files(tmp_path):
    result = PlanReviewExportService().export_plan_review(make_result(), tmp_path)

    assert result.estimator_brief_path.exists()
    assert result.final_estimator_review_path.exists()
    assert result.json_path.exists()
    assert result.drawing_index_path.exists()
    assert result.specification_index_path.exists()
    assert result.device_schedules_path.exists()
    assert result.keynotes_path.exists()
    assert result.legends_path.exists()
    assert result.detail_callouts_path.exists()
    assert result.reconciliation_issues_path.exists()
    assert result.equipment_matrix_path.exists()
    assert result.review_report_path.exists()
    assert result.scope_gaps_path.exists()
    assert result.estimator_risks_path.exists()
    assert result.recommendations_path.exists()
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
    assert (
        result.final_estimator_review_path
        == tmp_path / "maw_final_estimator_review.csv"
    )
    assert result.json_path == tmp_path / "maw_plan_review.json"
    assert result.drawing_index_path == tmp_path / "maw_drawing_index.csv"
    assert result.specification_index_path == tmp_path / "maw_specification_index.csv"
    assert result.device_schedules_path == tmp_path / "maw_device_schedules.csv"
    assert result.keynotes_path == tmp_path / "maw_keynotes.csv"
    assert result.legends_path == tmp_path / "maw_legends.csv"
    assert result.detail_callouts_path == tmp_path / "maw_detail_callouts.csv"
    assert (
        result.reconciliation_issues_path == tmp_path / "maw_reconciliation_issues.csv"
    )
    assert result.equipment_matrix_path == tmp_path / "maw_equipment_matrix.csv"
    assert result.review_report_path == tmp_path / "maw_review_report.csv"
    assert result.scope_gaps_path == tmp_path / "maw_scope_gaps.csv"
    assert result.estimator_risks_path == tmp_path / "maw_estimator_risks.csv"
    assert result.recommendations_path == tmp_path / "maw_recommendations.csv"
    assert result.markdown_summary_path == tmp_path / "maw_summary.md"


def test_to_dict_returns_string_paths(tmp_path):
    result = PlanReviewExportService().export_plan_review(make_result(), tmp_path)

    assert result.to_dict() == {
        "estimator_brief_path": str(result.estimator_brief_path),
        "final_estimator_review_path": str(result.final_estimator_review_path),
        "json_path": str(result.json_path),
        "drawing_index_path": str(result.drawing_index_path),
        "specification_index_path": str(result.specification_index_path),
        "device_schedules_path": str(result.device_schedules_path),
        "keynotes_path": str(result.keynotes_path),
        "legends_path": str(result.legends_path),
        "detail_callouts_path": str(result.detail_callouts_path),
        "reconciliation_issues_path": str(result.reconciliation_issues_path),
        "equipment_matrix_path": str(result.equipment_matrix_path),
        "review_report_path": str(result.review_report_path),
        "scope_gaps_path": str(result.scope_gaps_path),
        "estimator_risks_path": str(result.estimator_risks_path),
        "recommendations_path": str(result.recommendations_path),
        "markdown_summary_path": str(result.markdown_summary_path),
    }
    assert all(isinstance(value, str) for value in result.to_dict().values())


def test_exports_scope_gaps_csv(tmp_path):
    result = PlanReviewExportService().export_plan_review(make_result(), tmp_path)

    assert result.scope_gaps_path.exists()
    assert result.scope_gaps_path.name == "plan_review_scope_gaps.csv"
    assert result.recommendations_path.exists()
    assert result.recommendations_path.name == "plan_review_recommendations.csv"


def test_exports_estimator_risks_csv(tmp_path):
    result = PlanReviewExportService().export_plan_review(make_result(), tmp_path)

    assert result.estimator_risks_path.exists()
    assert result.estimator_risks_path.name == "plan_review_estimator_risks.csv"


def test_exports_device_schedules_csv(tmp_path):
    result = PlanReviewExportService().export_plan_review(make_result(), tmp_path)

    assert result.device_schedules_path.exists()
    assert result.device_schedules_path.name == "plan_review_device_schedules.csv"


def test_exports_keynotes_and_legends_csv(tmp_path):
    result = PlanReviewExportService().export_plan_review(make_result(), tmp_path)

    assert result.keynotes_path.exists()
    assert result.keynotes_path.name == "plan_review_keynotes.csv"
    assert result.legends_path.exists()
    assert result.legends_path.name == "plan_review_legends.csv"


def test_exports_reconciliation_issues_csv(tmp_path):
    result = PlanReviewExportService().export_plan_review(make_result(), tmp_path)

    assert result.reconciliation_issues_path.exists()
    assert (
        result.reconciliation_issues_path.name
        == "plan_review_reconciliation_issues.csv"
    )

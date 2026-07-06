import csv

from atlas_core.domain import (
    DeviceSchedule,
    DeviceScheduleItem,
    DrawingSheet,
    Keynote,
    Legend,
    LegendItem,
    SpecificationSection,
)
from atlas_core.services import (
    CsvExportService,
    EquipmentMatrixRow,
    EstimatorBrief,
    EstimatorRisk,
    FinalEstimatorReview,
    ReconciliationIssue,
    ReconciliationSeverity,
    Recommendation,
    ReviewReportItem,
    ScopeGap,
)


def test_exports_csv_file(tmp_path):
    output_path = tmp_path / "matrix.csv"

    written_path = CsvExportService().export_equipment_matrix(
        [EquipmentMatrixRow(equipment_id="eq-001")],
        output_path,
    )

    assert written_path == output_path
    assert output_path.exists()


def test_creates_parent_directory(tmp_path):
    output_path = tmp_path / "exports" / "matrix.csv"

    CsvExportService().export_equipment_matrix([], output_path)

    assert output_path.exists()


def test_writes_headers(tmp_path):
    output_path = tmp_path / "matrix.csv"

    CsvExportService().export_equipment_matrix([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

    assert headers == list(EquipmentMatrixRow().to_dict().keys())


def test_writes_row_values(tmp_path):
    output_path = tmp_path / "matrix.csv"
    row = EquipmentMatrixRow(
        building_name="MAW Music Education Center",
        equipment_id="eq-001",
        description="Ceiling Speaker",
        equipment_category="speaker",
        quantity=4,
        review_required=False,
    )

    CsvExportService().export_equipment_matrix([row], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["building_name"] == "MAW Music Education Center"
    assert records[0]["equipment_id"] == "eq-001"
    assert records[0]["description"] == "Ceiling Speaker"
    assert records[0]["equipment_category"] == "speaker"
    assert records[0]["quantity"] == "4"
    assert records[0]["review_required"] == "False"


def test_handles_empty_rows(tmp_path):
    output_path = tmp_path / "matrix.csv"

    CsvExportService().export_equipment_matrix([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records == []


def test_exports_review_report_csv(tmp_path):
    output_path = tmp_path / "review" / "report.csv"

    written_path = CsvExportService().export_review_report(
        [ReviewReportItem(source="resolver", target_id="eq-001", message="Review.")],
        output_path,
    )

    assert written_path == output_path
    assert output_path.exists()


def test_writes_review_report_headers(tmp_path):
    output_path = tmp_path / "review_report.csv"

    CsvExportService().export_review_report([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

    assert headers == list(
        ReviewReportItem(
            source="",
            target_id="",
            message="",
        )
        .to_dict()
        .keys()
    )


def test_writes_review_report_values(tmp_path):
    output_path = tmp_path / "review_report.csv"
    item = ReviewReportItem(
        source="manufacturer_registry",
        target_id="eq-display",
        message="Manufacturer requires review.",
        severity="critical",
        rule_id="RULE-001",
        manufacturer="Legacy",
    )

    CsvExportService().export_review_report([item], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["source"] == "manufacturer_registry"
    assert records[0]["target_id"] == "eq-display"
    assert records[0]["message"] == "Manufacturer requires review."
    assert records[0]["severity"] == "critical"
    assert records[0]["rule_id"] == "RULE-001"
    assert records[0]["manufacturer"] == "Legacy"


def test_handles_empty_review_report(tmp_path):
    output_path = tmp_path / "review_report.csv"

    CsvExportService().export_review_report([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records == []


def test_exports_drawing_index_csv(tmp_path):
    output_path = tmp_path / "plan_review" / "drawings.csv"
    sheet = DrawingSheet(
        sheet_id="a-101",
        sheet_number="A-101",
        title="Floor Plan",
    )

    written_path = CsvExportService().export_drawing_index([sheet], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert written_path == output_path
    assert records[0]["sheet_number"] == "A-101"
    assert records[0]["title"] == "Floor Plan"


def test_exports_specification_index_csv(tmp_path):
    output_path = tmp_path / "plan_review" / "specifications.csv"
    section = SpecificationSection(
        section_id="27-4100",
        section_number="27 41 00",
        title="Audiovisual Systems",
    )

    written_path = CsvExportService().export_specification_index(
        [section],
        output_path,
    )

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert written_path == output_path
    assert records[0]["section_number"] == "27 41 00"
    assert records[0]["title"] == "Audiovisual Systems"


def test_exports_estimator_brief_csv(tmp_path):
    output_path = tmp_path / "plan_review" / "brief.csv"
    brief = EstimatorBrief(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        drawing_count=2,
        specification_count=1,
        system_count=3,
        equipment_count=4,
        detail_callout_count=0,
        issue_count=5,
        placeholder_count=1,
        review_required_count=2,
        cross_reference_count=3,
        reconciliation_issue_count=0,
        scope_gap_count=4,
        estimator_risk_count=5,
        keynote_count=0,
        legend_count=0,
        legend_item_count=0,
        room_count=0,
        confidence=0.75,
    )

    written_path = CsvExportService().export_estimator_brief(brief, output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert written_path == output_path
    assert records[0]["review_id"] == "review-001"
    assert records[0]["drawing_count"] == "2"
    assert records[0]["cross_reference_count"] == "3"
    assert records[0]["scope_gap_count"] == "4"
    assert records[0]["estimator_risk_count"] == "5"
    assert records[0]["confidence"] == "0.75"


def test_exports_final_estimator_review_csv(tmp_path):
    output_path = tmp_path / "plan_review" / "final_review.csv"
    final_review = FinalEstimatorReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        readiness_status="needs_review",
        readiness_message="Plan review needs estimator review before pricing.",
        completeness_status="partial",
        completeness_score=0.7,
        confidence=0.75,
        total_issues=6,
        total_recommendations=2,
        executive_summary="Bid package requires estimator review before pricing.",
        next_actions=["Review confidence before pricing."],
    )

    written_path = CsvExportService().export_final_estimator_review(
        final_review,
        output_path,
    )

    assert written_path == output_path
    assert output_path.exists()


def test_writes_final_review_headers(tmp_path):
    output_path = tmp_path / "final_review.csv"
    final_review = FinalEstimatorReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )

    CsvExportService().export_final_estimator_review(final_review, output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

    assert headers == list(final_review.to_dict().keys())


def test_writes_final_review_values(tmp_path):
    output_path = tmp_path / "final_review.csv"
    final_review = FinalEstimatorReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        readiness_status="not_ready",
        readiness_message="Plan review is not ready for pricing.",
        completeness_status="incomplete",
        completeness_score=0.3,
        confidence=0.6,
        total_issues=9,
        total_recommendations=3,
        executive_summary="Bid package is not ready for pricing.",
        next_actions=[
            "No drawing sheets are available.",
            "No specification sections are available.",
        ],
    )

    CsvExportService().export_final_estimator_review(final_review, output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["review_id"] == "review-001"
    assert records[0]["readiness_status"] == "not_ready"
    assert records[0]["completeness_status"] == "incomplete"
    assert records[0]["completeness_score"] == "0.3"
    assert records[0]["confidence"] == "0.6"
    assert records[0]["total_issues"] == "9"
    assert records[0]["total_recommendations"] == "3"
    assert records[0]["executive_summary"] == "Bid package is not ready for pricing."
    assert records[0]["next_actions"] == (
        "['No drawing sheets are available.', "
        "'No specification sections are available.']"
    )


def test_exports_keynotes_csv(tmp_path):
    output_path = tmp_path / "plan_review" / "keynotes.csv"

    written_path = CsvExportService().export_keynotes(
        [
            Keynote(
                keynote_id="kn-001",
                number="1",
                description="Provide ceiling speaker.",
            )
        ],
        output_path,
    )

    assert written_path == output_path
    assert output_path.exists()


def test_writes_keynote_headers(tmp_path):
    output_path = tmp_path / "keynotes.csv"

    CsvExportService().export_keynotes([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

    assert headers == list(
        Keynote(
            keynote_id="keynote",
            number="1",
            description="Keynote",
        )
        .to_dict()
        .keys()
    )


def test_writes_keynote_values(tmp_path):
    output_path = tmp_path / "keynotes.csv"
    keynote = Keynote(
        keynote_id="kn-001",
        number="K1",
        description="Provide amplifier.",
        source_sheet_number="AV1.01",
        equipment_category="electronics",
        system_category="audio",
        notes=["Coordinate with rack layout"],
        confidence=0.9,
    )

    CsvExportService().export_keynotes([keynote], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["keynote_id"] == "kn-001"
    assert records[0]["number"] == "K1"
    assert records[0]["description"] == "Provide amplifier."
    assert records[0]["source_sheet_number"] == "AV1.01"
    assert records[0]["equipment_category"] == "electronics"
    assert records[0]["system_category"] == "audio"
    assert records[0]["notes"] == "['Coordinate with rack layout']"
    assert records[0]["confidence"] == "0.9"


def test_handles_empty_keynotes(tmp_path):
    output_path = tmp_path / "keynotes.csv"

    CsvExportService().export_keynotes([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records == []


def test_exports_legends_csv(tmp_path):
    output_path = tmp_path / "plan_review" / "legends.csv"
    legend = Legend(
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

    written_path = CsvExportService().export_legends([legend], output_path)

    assert written_path == output_path
    assert output_path.exists()


def test_writes_legend_item_values(tmp_path):
    output_path = tmp_path / "legends.csv"
    legend = Legend(
        legend_id="legend-001",
        title="AV Symbols",
        items=[
            LegendItem(
                legend_item_id="li-001",
                symbol="DSP",
                description="Digital signal processor",
                equipment_category="electronics",
                system_category="audio",
                source_sheet_number="AV1.01",
                notes=["Coordinate with controls"],
                confidence=0.95,
            )
        ],
    )

    CsvExportService().export_legends([legend], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["legend_item_id"] == "li-001"
    assert records[0]["symbol"] == "DSP"
    assert records[0]["description"] == "Digital signal processor"
    assert records[0]["equipment_category"] == "electronics"
    assert records[0]["system_category"] == "audio"
    assert records[0]["source_sheet_number"] == "AV1.01"
    assert records[0]["notes"] == "['Coordinate with controls']"
    assert records[0]["confidence"] == "0.95"


def test_writes_legend_id_and_legend_title(tmp_path):
    output_path = tmp_path / "legends.csv"
    legend = Legend(
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

    CsvExportService().export_legends([legend], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["legend_id"] == "legend-001"
    assert records[0]["legend_title"] == "AV Symbols"


def test_handles_empty_legends(tmp_path):
    output_path = tmp_path / "legends.csv"

    CsvExportService().export_legends([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)
        rows = list(reader)

    assert headers == [
        "legend_id",
        "legend_title",
        *list(
            LegendItem(
                legend_item_id="legend-item",
                symbol="SYM",
                description="Legend item",
            )
            .to_dict()
            .keys()
        ),
    ]
    assert rows == []


def test_empty_drawing_index_writes_headers(tmp_path):
    output_path = tmp_path / "drawings.csv"

    CsvExportService().export_drawing_index([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

    assert headers == list(
        DrawingSheet(
            sheet_id="sheet",
            sheet_number="SHEET",
            title="Sheet",
        )
        .to_dict()
        .keys()
    )


def test_empty_specification_index_writes_headers(tmp_path):
    output_path = tmp_path / "specifications.csv"

    CsvExportService().export_specification_index([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

    assert headers == list(
        SpecificationSection(
            section_id="section",
            section_number="SECTION",
            title="Section",
        )
        .to_dict()
        .keys()
    )


def test_exports_scope_gaps_csv(tmp_path):
    output_path = tmp_path / "scope" / "gaps.csv"

    written_path = CsvExportService().export_scope_gaps(
        [ScopeGap(gap_id="gap-001", target_id="eq-001", message="Review mount.")],
        output_path,
    )

    assert written_path == output_path
    assert output_path.exists()


def test_writes_scope_gap_headers(tmp_path):
    output_path = tmp_path / "scope_gaps.csv"

    CsvExportService().export_scope_gaps([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

    assert headers == list(
        ScopeGap(
            gap_id="gap",
            target_id="target",
            message="Message.",
        )
        .to_dict()
        .keys()
    )


def test_writes_scope_gap_values(tmp_path):
    output_path = tmp_path / "scope_gaps.csv"
    gap = ScopeGap(
        gap_id="projector_missing_mount",
        target_id="projector-001",
        message=(
            "Projector is present, but no mount or mounting allowance was detected "
            "in the same room."
        ),
        severity="high",
        confidence=0.9,
        suggested_action="Add projector mount.",
    )

    CsvExportService().export_scope_gaps([gap], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["gap_id"] == "projector_missing_mount"
    assert records[0]["target_id"] == "projector-001"
    assert records[0]["message"] == (
        "Projector is present, but no mount or mounting allowance was detected "
        "in the same room."
    )
    assert records[0]["severity"] == "high"
    assert records[0]["confidence"] == "0.9"
    assert records[0]["suggested_action"] == "Add projector mount."


def test_handles_empty_scope_gaps(tmp_path):
    output_path = tmp_path / "scope_gaps.csv"

    CsvExportService().export_scope_gaps([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records == []


def test_exports_reconciliation_issues_csv(tmp_path):
    output_path = tmp_path / "reconciliation" / "issues.csv"

    written_path = CsvExportService().export_reconciliation_issues(
        [
            ReconciliationIssue(
                issue_id="device_schedule_item_missing_equipment:sched-1-dsp-1",
                message=(
                    "Device schedule item is not represented in equipment matrix."
                ),
            )
        ],
        output_path,
    )

    assert written_path == output_path
    assert output_path.exists()


def test_writes_reconciliation_issue_headers(tmp_path):
    output_path = tmp_path / "reconciliation_issues.csv"

    CsvExportService().export_reconciliation_issues([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

    assert headers == list(
        ReconciliationIssue(
            issue_id="issue",
            message="Message.",
        )
        .to_dict()
        .keys()
    )


def test_writes_reconciliation_issue_values(tmp_path):
    output_path = tmp_path / "reconciliation_issues.csv"
    issue = ReconciliationIssue(
        issue_id="device_schedule_item_missing_equipment:sched-1-dsp-1",
        message="Device schedule item is not represented in equipment matrix.",
        severity=ReconciliationSeverity.HIGH,
        target_id="sched-1-dsp-1",
        suggested_action="Add item to equipment matrix.",
        confidence=0.9,
    )

    CsvExportService().export_reconciliation_issues([issue], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert (
        records[0]["issue_id"] == "device_schedule_item_missing_equipment:sched-1-dsp-1"
    )
    assert (
        records[0]["message"]
        == "Device schedule item is not represented in equipment matrix."
    )
    assert records[0]["severity"] == "high"
    assert records[0]["source"] == "scope_reconciliation"
    assert records[0]["target_id"] == "sched-1-dsp-1"
    assert records[0]["suggested_action"] == "Add item to equipment matrix."
    assert records[0]["confidence"] == "0.9"


def test_handles_empty_reconciliation_issues(tmp_path):
    output_path = tmp_path / "reconciliation_issues.csv"

    CsvExportService().export_reconciliation_issues([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records == []


def test_exports_estimator_risks_csv(tmp_path):
    output_path = tmp_path / "risks" / "estimator_risks.csv"

    written_path = CsvExportService().export_estimator_risks(
        [
            EstimatorRisk(
                risk_id="scope_gaps_detected",
                message="Scope gaps were detected.",
            )
        ],
        output_path,
    )

    assert written_path == output_path
    assert output_path.exists()


def test_writes_estimator_risk_headers(tmp_path):
    output_path = tmp_path / "estimator_risks.csv"

    CsvExportService().export_estimator_risks([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

    assert headers == list(
        EstimatorRisk(
            risk_id="risk",
            message="Message.",
        )
        .to_dict()
        .keys()
    )


def test_writes_estimator_risk_values(tmp_path):
    output_path = tmp_path / "estimator_risks.csv"
    risk = EstimatorRisk(
        risk_id="scope_gaps_detected",
        message="Scope gaps were detected and require estimator review.",
        risk_level="high",
        category="scope",
        confidence=0.9,
    )

    CsvExportService().export_estimator_risks([risk], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["risk_id"] == "scope_gaps_detected"
    assert records[0]["message"] == (
        "Scope gaps were detected and require estimator review."
    )
    assert records[0]["risk_level"] == "high"
    assert records[0]["category"] == "scope"
    assert records[0]["confidence"] == "0.9"


def test_handles_empty_estimator_risks(tmp_path):
    output_path = tmp_path / "estimator_risks.csv"

    CsvExportService().export_estimator_risks([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records == []


def test_exports_recommendations_csv(tmp_path):
    output_path = tmp_path / "recommendations.csv"

    written_path = CsvExportService().export_recommendations(
        [
            Recommendation(
                recommendation_id="confirm-manufacturers",
                message="Confirm manufacturers before pricing.",
                priority="medium",
                category="manufacturer",
                target_id="eq-001",
            )
        ],
        output_path,
    )

    assert written_path == output_path
    assert output_path.exists()


def test_writes_recommendation_headers(tmp_path):
    output_path = tmp_path / "recommendations.csv"

    CsvExportService().export_recommendations([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

    assert headers == list(
        Recommendation(
            recommendation_id="recommendation_id",
            message="Message.",
        )
        .to_dict()
        .keys()
    )


def test_writes_recommendation_values(tmp_path):
    output_path = tmp_path / "recommendations.csv"
    recommendation = Recommendation(
        recommendation_id="confirm-manufacturers",
        message="Confirm manufacturers before pricing.",
        priority="medium",
        category="manufacturer",
        target_id="eq-001",
    )

    CsvExportService().export_recommendations([recommendation], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["recommendation_id"] == "confirm-manufacturers"
    assert records[0]["message"] == "Confirm manufacturers before pricing."
    assert records[0]["priority"] == "medium"
    assert records[0]["category"] == "manufacturer"
    assert records[0]["target_id"] == "eq-001"


def test_handles_empty_recommendations(tmp_path):
    output_path = tmp_path / "recommendations.csv"

    CsvExportService().export_recommendations([], output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records == []


def test_exports_single_device_schedule_csv(tmp_path):
    output_path = tmp_path / "device_schedule.csv"
    schedule = DeviceSchedule(
        schedule_id="sched-1",
        source_sheet_number="AV1.01",
        items=[
            DeviceScheduleItem(
                item_id="sched-1-spk-1",
                tag="SPK-1",
                description="Main loudspeaker",
            )
        ],
    )

    written_path = CsvExportService().export_device_schedule(schedule, output_path)

    assert written_path == output_path
    assert output_path.exists()


def test_exports_multiple_device_schedules_csv(tmp_path):
    output_path = tmp_path / "device_schedules.csv"
    schedules = [
        DeviceSchedule(
            schedule_id="sched-1",
            source_sheet_number="AV1.01",
            items=[
                DeviceScheduleItem(
                    item_id="sched-1-spk-1",
                    tag="SPK-1",
                    description="Main loudspeaker",
                )
            ],
        ),
        DeviceSchedule(
            schedule_id="sched-2",
            source_sheet_number="AV2.01",
            items=[
                DeviceScheduleItem(
                    item_id="sched-2-dsp-1",
                    tag="DSP-1",
                    description="Control processor",
                )
            ],
        ),
    ]

    CsvExportService().export_device_schedules(schedules, output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert len(records) == 2


def test_writes_schedule_id(tmp_path):
    output_path = tmp_path / "device_schedule.csv"
    schedule = DeviceSchedule(
        schedule_id="sched-1",
        items=[
            DeviceScheduleItem(
                item_id="sched-1-spk-1",
                tag="SPK-1",
                description="Main loudspeaker",
            )
        ],
    )

    CsvExportService().export_device_schedule(schedule, output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["schedule_id"] == "sched-1"


def test_writes_source_sheet_number(tmp_path):
    output_path = tmp_path / "device_schedule.csv"
    schedule = DeviceSchedule(
        schedule_id="sched-1",
        source_sheet_number="AV1.01",
        items=[
            DeviceScheduleItem(
                item_id="sched-1-spk-1",
                tag="SPK-1",
                description="Main loudspeaker",
            )
        ],
    )

    CsvExportService().export_device_schedule(schedule, output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["source_sheet_number"] == "AV1.01"


def test_writes_device_schedule_item_values(tmp_path):
    output_path = tmp_path / "device_schedule.csv"
    schedule = DeviceSchedule(
        schedule_id="sched-1",
        source_sheet_number="AV1.01",
        items=[
            DeviceScheduleItem(
                item_id="sched-1-spk-1",
                tag="SPK-1",
                description="Main loudspeaker",
                quantity=2,
                manufacturer="Acme",
                model="X100",
                drawing_reference="AV1.01",
                specification_reference="27 41 16",
            )
        ],
    )

    CsvExportService().export_device_schedule(schedule, output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert records[0]["item_id"] == "sched-1-spk-1"
    assert records[0]["tag"] == "SPK-1"
    assert records[0]["description"] == "Main loudspeaker"
    assert records[0]["quantity"] == "2"
    assert records[0]["manufacturer"] == "Acme"
    assert records[0]["model"] == "X100"
    assert records[0]["drawing_reference"] == "AV1.01"
    assert records[0]["specification_reference"] == "27 41 16"


def test_handles_empty_device_schedule(tmp_path):
    output_path = tmp_path / "device_schedule.csv"
    schedule = DeviceSchedule(schedule_id="sched-1", source_sheet_number="AV1.01")

    CsvExportService().export_device_schedule(schedule, output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)
        rows = list(reader)

    assert "schedule_id" in headers
    assert "source_sheet_number" in headers
    assert "item_id" in headers
    assert rows == []

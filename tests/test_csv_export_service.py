import csv

from atlas_core.domain import DrawingSheet, SpecificationSection
from atlas_core.services import (
    CsvExportService,
    EquipmentMatrixRow,
    EstimatorBrief,
    ReviewReportItem,
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
        ).to_dict().keys()
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
        issue_count=5,
        placeholder_count=1,
        review_required_count=2,
        cross_reference_count=3,
        confidence=0.75,
    )

    written_path = CsvExportService().export_estimator_brief(brief, output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    assert written_path == output_path
    assert records[0]["review_id"] == "review-001"
    assert records[0]["drawing_count"] == "2"
    assert records[0]["cross_reference_count"] == "3"
    assert records[0]["confidence"] == "0.75"


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
        ).to_dict().keys()
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
        ).to_dict().keys()
    )

import csv

from atlas_core.services import CsvExportService, EquipmentMatrixRow


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

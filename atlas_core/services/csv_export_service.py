"""CSV export helpers for Atlas Core services."""

import csv
from pathlib import Path

from atlas_core.services.equipment_matrix_service import EquipmentMatrixRow


class CsvExportService:
    def export_equipment_matrix(
        self,
        rows: list[EquipmentMatrixRow],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        headers = list(EquipmentMatrixRow().to_dict().keys())

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()

            for row in rows:
                writer.writerow(row.to_dict())

        return path

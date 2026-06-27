"""CSV export helpers for Atlas Core services."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from atlas_core.services.equipment_matrix_service import EquipmentMatrixRow
from atlas_core.services.review_report_service import ReviewReportItem

if TYPE_CHECKING:
    from atlas_core.domain import DrawingSheet, SpecificationSection
    from atlas_core.services.estimator_brief_service import EstimatorBrief


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

    def export_drawing_index(
        self,
        sheets: list[DrawingSheet],
        output_path: str | Path,
    ) -> Path:
        return self._write_csv(
            headers=self._drawing_index_headers(),
            rows=[sheet.to_dict() for sheet in sheets],
            output_path=output_path,
        )

    def export_specification_index(
        self,
        sections: list[SpecificationSection],
        output_path: str | Path,
    ) -> Path:
        return self._write_csv(
            headers=self._specification_index_headers(),
            rows=[section.to_dict() for section in sections],
            output_path=output_path,
        )

    def export_estimator_brief(
        self,
        brief: EstimatorBrief,
        output_path: str | Path,
    ) -> Path:
        brief_data = brief.to_dict()
        return self._write_csv(
            headers=list(brief_data.keys()),
            rows=[brief_data],
            output_path=output_path,
        )

    @staticmethod
    def _write_csv(
        headers: list[str],
        rows: list[dict],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        return path

    @staticmethod
    def _drawing_index_headers() -> list[str]:
        from atlas_core.domain import DrawingSheet

        return list(
            DrawingSheet(
                sheet_id="sheet",
                sheet_number="SHEET",
                title="Sheet",
            ).to_dict().keys()
        )

    @staticmethod
    def _specification_index_headers() -> list[str]:
        from atlas_core.domain import SpecificationSection

        return list(
            SpecificationSection(
                section_id="section",
                section_number="SECTION",
                title="Section",
            ).to_dict().keys()
        )

    def export_review_report(
        self,
        items: list[ReviewReportItem],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        headers = list(
            ReviewReportItem(
                source="",
                target_id="",
                message="",
            ).to_dict().keys()
        )

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()

            for item in items:
                writer.writerow(item.to_dict())

        return path

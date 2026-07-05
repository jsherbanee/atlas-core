"""CSV export helpers for Atlas Core services."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from atlas_core.services.equipment_matrix_service import EquipmentMatrixRow
from atlas_core.services.estimator_risk_service import EstimatorRisk
from atlas_core.services.recommendation_service import Recommendation
from atlas_core.services.review_report_service import ReviewReportItem
from atlas_core.services.scope_reconciliation_service import ReconciliationIssue
from atlas_core.services.scope_gap_service import ScopeGap
from atlas_core.services.final_estimator_review_service import FinalEstimatorReview

if TYPE_CHECKING:
    from atlas_core.domain import (
        DeviceSchedule,
        DeviceScheduleItem,
        DrawingSheet,
        Keynote,
        Legend,
        SpecificationSection,
    )
    from atlas_core.services.estimator_brief_service import EstimatorBrief


class CsvExportService:
    def export_device_schedule(
        self,
        schedule: DeviceSchedule,
        output_path: str | Path,
    ) -> Path:
        return self.export_device_schedules([schedule], output_path)

    def export_device_schedules(
        self,
        schedules: list[DeviceSchedule],
        output_path: str | Path,
    ) -> Path:
        rows: list[dict] = []
        for schedule in schedules:
            rows.extend(self._device_schedule_rows(schedule))

        return self._write_csv(
            headers=self._device_schedule_headers(),
            rows=rows,
            output_path=output_path,
        )

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

    def export_keynotes(
        self,
        keynotes: list[Keynote],
        output_path: str | Path,
    ) -> Path:
        return self._write_csv(
            headers=self._keynote_headers(),
            rows=[keynote.to_dict() for keynote in keynotes],
            output_path=output_path,
        )

    def export_legends(
        self,
        legends: list[Legend],
        output_path: str | Path,
    ) -> Path:
        rows: list[dict] = []
        for legend in legends:
            rows.extend(self._legend_rows(legend))

        return self._write_csv(
            headers=self._legend_headers(),
            rows=rows,
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

    def export_final_estimator_review(
        self,
        review: FinalEstimatorReview,
        output_path: str | Path,
    ) -> Path:
        review_data = review.to_dict()
        return self._write_csv(
            headers=list(review_data.keys()),
            rows=[review_data],
            output_path=output_path,
        )

    def export_recommendations(
        self,
        recommendations: list[Recommendation],
        output_path: str | Path,
    ) -> Path:
        return self._write_csv(
            headers=list(
                Recommendation(
                    recommendation_id="recommendation_id",
                    message="Message.",
                )
                .to_dict()
                .keys()
            ),
            rows=[recommendation.to_dict() for recommendation in recommendations],
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
            )
            .to_dict()
            .keys()
        )

    @staticmethod
    def _specification_index_headers() -> list[str]:
        from atlas_core.domain import SpecificationSection

        return list(
            SpecificationSection(
                section_id="section",
                section_number="SECTION",
                title="Section",
            )
            .to_dict()
            .keys()
        )

    @staticmethod
    def _keynote_headers() -> list[str]:
        from atlas_core.domain import Keynote

        return list(
            Keynote(
                keynote_id="keynote",
                number="1",
                description="Keynote",
            )
            .to_dict()
            .keys()
        )

    @staticmethod
    def _legend_headers() -> list[str]:
        from atlas_core.domain import LegendItem

        return [
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

    @staticmethod
    def _legend_rows(legend: Legend) -> list[dict]:
        rows: list[dict] = []
        for item in legend.items:
            rows.append(CsvExportService._legend_row(legend, item.to_dict()))

        return rows

    @staticmethod
    def _legend_row(legend: Legend, item: dict) -> dict:
        row = item.copy()
        row["legend_id"] = legend.legend_id
        row["legend_title"] = legend.title
        return row

    @staticmethod
    def _device_schedule_headers() -> list[str]:
        from atlas_core.domain import DeviceScheduleItem

        return [
            "schedule_id",
            "source_sheet_number",
            *list(
                DeviceScheduleItem(
                    item_id="item",
                    tag="TAG",
                    description="Item",
                )
                .to_dict()
                .keys()
            ),
        ]

    @staticmethod
    def _device_schedule_rows(schedule: DeviceSchedule) -> list[dict]:
        rows: list[dict] = []
        for item in schedule.items:
            rows.append(CsvExportService._device_schedule_row(item, schedule))

        return rows

    @staticmethod
    def _device_schedule_row(
        item: DeviceScheduleItem,
        schedule: DeviceSchedule,
    ) -> dict:
        row = item.to_dict()
        row["schedule_id"] = schedule.schedule_id
        row["source_sheet_number"] = schedule.source_sheet_number
        return row

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
            )
            .to_dict()
            .keys()
        )

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()

            for item in items:
                writer.writerow(item.to_dict())

        return path

    def export_scope_gaps(
        self,
        gaps: list[ScopeGap],
        output_path: str | Path,
    ) -> Path:
        return self._write_csv(
            headers=list(
                ScopeGap(
                    gap_id="gap",
                    target_id="target",
                    message="Message.",
                )
                .to_dict()
                .keys()
            ),
            rows=[gap.to_dict() for gap in gaps],
            output_path=output_path,
        )

    def export_reconciliation_issues(
        self,
        issues: list[ReconciliationIssue],
        output_path: str | Path,
    ) -> Path:
        return self._write_csv(
            headers=list(
                ReconciliationIssue(
                    issue_id="issue",
                    message="Message.",
                )
                .to_dict()
                .keys()
            ),
            rows=[issue.to_dict() for issue in issues],
            output_path=output_path,
        )

    def export_estimator_risks(
        self,
        risks: list[EstimatorRisk],
        output_path: str | Path,
    ) -> Path:
        return self._write_csv(
            headers=list(
                EstimatorRisk(
                    risk_id="risk",
                    message="Message.",
                )
                .to_dict()
                .keys()
            ),
            rows=[risk.to_dict() for risk in risks],
            output_path=output_path,
        )

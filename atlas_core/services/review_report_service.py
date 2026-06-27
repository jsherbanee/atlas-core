"""Review report aggregation helpers for Atlas Core services."""

from dataclasses import asdict, dataclass

from atlas_core.rules import Resolution
from atlas_core.services.manufacturer_review_service import (
    ManufacturerReviewIssue,
)


@dataclass
class ReviewReportItem:
    source: str
    target_id: str
    message: str
    severity: str = "review"
    rule_id: str | None = None
    manufacturer: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class ReviewReportService:
    def build_report(
        self,
        resolutions: list[Resolution],
        manufacturer_issues: list[ManufacturerReviewIssue] | None = None,
    ) -> list[ReviewReportItem]:
        report_items = [
            ReviewReportItem(
                source="resolver",
                target_id=resolution.target_id,
                message=resolution.message,
                rule_id=resolution.rule_id,
            )
            for resolution in resolutions
        ]

        report_items.extend(
            ReviewReportItem(
                source="manufacturer_registry",
                target_id=issue.equipment_id,
                message=issue.message,
                severity=issue.severity,
                manufacturer=issue.manufacturer,
            )
            for issue in manufacturer_issues or []
        )

        return report_items

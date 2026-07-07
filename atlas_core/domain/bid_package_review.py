"""Bid package review domain model for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from atlas_core.domain import (
    DeviceSchedule,
    DrawingSheet,
    Equipment,
    IntegratedSystem,
    Room,
    SpecificationSection,
)
from atlas_core.rules import Resolution
from atlas_core.utils.refactoring import serialize_item, serialize_items

if TYPE_CHECKING:
    from atlas_core.domain import (
        DetailCallout,
        EngineeringAssumption,
        Keynote,
        Legend,
        LaborEstimate,
        RFICandidate,
        RevisionComparison,
    )
    from atlas_core.services import ManufacturerReviewIssue, ReviewReportItem
    from atlas_core.services.bid_completeness_service import BidCompleteness
    from atlas_core.services.plan_review_readiness_service import PlanReviewReadiness
    from atlas_core.services.cross_reference_service import CrossReference
    from atlas_core.services.scope_reconciliation_service import ReconciliationIssue
    from atlas_core.services.estimator_risk_service import EstimatorRisk
    from atlas_core.services.recommendation_service import Recommendation
    from atlas_core.services.scope_gap_service import ScopeGap
    from atlas_core.services.drawing_metadata_service import DrawingMetadata


@dataclass
class BidPackageReview:
    review_id: str
    project_id: str
    name: str
    drawing_sheets: list[DrawingSheet] = field(default_factory=list)
    specification_sections: list[SpecificationSection] = field(default_factory=list)
    systems: list[IntegratedSystem] = field(default_factory=list)
    equipment: list[Equipment] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    detail_callouts: list[DetailCallout] = field(default_factory=list)
    drawing_metadata: list[DrawingMetadata] = field(default_factory=list)
    device_schedules: list[DeviceSchedule] = field(default_factory=list)
    keynotes: list[Keynote] = field(default_factory=list)
    legends: list[Legend] = field(default_factory=list)
    resolutions: list[Resolution] = field(default_factory=list)
    manufacturer_review_issues: list[ManufacturerReviewIssue] = field(
        default_factory=list
    )
    review_report: list[ReviewReportItem] = field(default_factory=list)
    cross_references: list[CrossReference] = field(default_factory=list)
    reconciliation_issues: list[ReconciliationIssue] = field(default_factory=list)
    scope_gaps: list[ScopeGap] = field(default_factory=list)
    estimator_risks: list[EstimatorRisk] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    engineering_assumptions: list[EngineeringAssumption] = field(default_factory=list)
    rfi_candidates: list[RFICandidate] = field(default_factory=list)
    labor_estimate: LaborEstimate | None = None
    revision_comparison: RevisionComparison | None = None
    bid_completeness: BidCompleteness | None = None
    readiness: PlanReviewReadiness | None = None
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.review_id = self._normalize_required_text("review_id", self.review_id)
        self.project_id = self._normalize_required_text("project_id", self.project_id)
        self.name = self._normalize_required_text("name", self.name)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def drawing_count(self) -> int:
        return len(self.drawing_sheets)

    def drawing_metadata_count(self) -> int:
        return len(self.drawing_metadata)

    def device_schedule_count(self) -> int:
        return len(self.device_schedules)

    def keynote_count(self) -> int:
        return len(self.keynotes)

    def legend_count(self) -> int:
        return len(self.legends)

    def legend_item_count(self) -> int:
        return sum(legend.item_count() for legend in self.legends)

    def specification_count(self) -> int:
        return len(self.specification_sections)

    def equipment_count(self) -> int:
        return len(self.equipment)

    def room_count(self) -> int:
        return len(self.rooms)

    def detail_callout_count(self) -> int:
        return len(self.detail_callouts)

    def cross_reference_count(self) -> int:
        return len(self.cross_references)

    def scope_gap_count(self) -> int:
        return len(self.scope_gaps)

    def reconciliation_issue_count(self) -> int:
        return len(self.reconciliation_issues)

    def estimator_risk_count(self) -> int:
        return len(self.estimator_risks)

    def recommendation_count(self) -> int:
        return len(self.recommendations)

    def rfi_candidate_count(self) -> int:
        return len(self.rfi_candidates)

    def issue_count(self) -> int:
        return (
            len(self.resolutions)
            + len(self.manufacturer_review_issues)
            + len(self.review_report)
            + len(self.reconciliation_issues)
            + len(self.scope_gaps)
            + len(self.estimator_risks)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "project_id": self.project_id,
            "name": self.name,
            "drawing_sheets": self._serialize_items(self.drawing_sheets),
            "specification_sections": self._serialize_items(
                self.specification_sections
            ),
            "systems": self._serialize_items(self.systems),
            "equipment": self._serialize_items(self.equipment),
            "rooms": self._serialize_items(self.rooms),
            "detail_callouts": self._serialize_items(self.detail_callouts),
            "resolutions": self._serialize_items(self.resolutions),
            "manufacturer_review_issues": self._serialize_items(
                self.manufacturer_review_issues
            ),
            "review_report": self._serialize_items(self.review_report),
            "cross_references": self._serialize_items(self.cross_references),
            "reconciliation_issues": self._serialize_items(self.reconciliation_issues),
            "scope_gaps": self._serialize_items(self.scope_gaps),
            "estimator_risks": self._serialize_items(self.estimator_risks),
            "recommendations": self._serialize_items(self.recommendations),
            "engineering_assumptions": self._serialize_items(
                self.engineering_assumptions
            ),
            "rfi_candidates": self._serialize_items(self.rfi_candidates),
            "labor_estimate": (
                self.labor_estimate.to_dict()
                if self.labor_estimate is not None
                else None
            ),
            "revision_comparison": (
                self.revision_comparison.to_dict()
                if self.revision_comparison is not None
                else None
            ),
            "bid_completeness": (
                self.bid_completeness.to_dict()
                if self.bid_completeness is not None
                else None
            ),
            "readiness": (
                self.readiness.to_dict() if self.readiness is not None else None
            ),
            "drawing_metadata": self._serialize_items(self.drawing_metadata),
            "device_schedules": self._serialize_items(self.device_schedules),
            "keynotes": self._serialize_items(self.keynotes),
            "legends": self._serialize_items(self.legends),
            "notes": list(self.notes),
            "confidence": self.confidence,
        }

    @classmethod
    def _serialize_items(cls, items: list[Any]) -> list[Any]:
        return serialize_items(items)

    @classmethod
    def _serialize_item(cls, item: Any) -> Any:
        return serialize_item(item)

    @classmethod
    def _normalize_note(cls, note: str) -> str:
        return cls._normalize_required_text("note", note)

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

"""Bid completeness assessment for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from atlas_core.domain import BidPackageReview


class CompletenessStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"


@dataclass
class BidCompleteness:
    status: CompletenessStatus
    score: float
    drawing_completeness: float
    specification_completeness: float
    system_completeness: float
    equipment_completeness: float
    schedule_completeness: float
    missing_items: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.status, CompletenessStatus):
            self.status = CompletenessStatus(str(self.status).strip().lower())

        self.score = self._validate_score("score", self.score)
        self.drawing_completeness = self._validate_score(
            "drawing_completeness", self.drawing_completeness
        )
        self.specification_completeness = self._validate_score(
            "specification_completeness", self.specification_completeness
        )
        self.system_completeness = self._validate_score(
            "system_completeness", self.system_completeness
        )
        self.equipment_completeness = self._validate_score(
            "equipment_completeness", self.equipment_completeness
        )
        self.schedule_completeness = self._validate_score(
            "schedule_completeness", self.schedule_completeness
        )

        self.missing_items = [
            self._normalize_required_text("missing_item", item)
            for item in self.missing_items
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "score": self.score,
            "drawing_completeness": self.drawing_completeness,
            "specification_completeness": self.specification_completeness,
            "system_completeness": self.system_completeness,
            "equipment_completeness": self.equipment_completeness,
            "schedule_completeness": self.schedule_completeness,
            "missing_items": list(self.missing_items),
        }

    @staticmethod
    def _validate_score(field_name: str, value: float) -> float:
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"{field_name} must be between 0 and 1")

        return float(value)

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


class BidCompletenessService:
    def assess(self, review: BidPackageReview) -> BidCompleteness:
        drawing_completeness = 1.0 if review.drawing_sheets else 0.0
        specification_completeness = 1.0 if review.specification_sections else 0.0
        system_completeness = 1.0 if review.systems else 0.0
        equipment_completeness = 1.0 if review.equipment else 0.0
        schedule_completeness = self._schedule_completeness(review)

        score = round(
            (
                drawing_completeness
                + specification_completeness
                + system_completeness
                + equipment_completeness
                + schedule_completeness
            )
            / 5,
            2,
        )

        status = self._status(score)

        return BidCompleteness(
            status=status,
            score=score,
            drawing_completeness=drawing_completeness,
            specification_completeness=specification_completeness,
            system_completeness=system_completeness,
            equipment_completeness=equipment_completeness,
            schedule_completeness=schedule_completeness,
            missing_items=self._missing_items(
                drawing_completeness,
                specification_completeness,
                system_completeness,
                equipment_completeness,
                schedule_completeness,
            ),
        )

    @staticmethod
    def _schedule_completeness(review: BidPackageReview) -> float:
        if review.device_schedules:
            return 1.0

        if review.keynotes or review.legends:
            return 0.5

        return 0.0

    @staticmethod
    def _status(score: float) -> CompletenessStatus:
        if score >= 0.9:
            return CompletenessStatus.COMPLETE
        if score >= 0.5:
            return CompletenessStatus.PARTIAL
        return CompletenessStatus.INCOMPLETE

    @staticmethod
    def _missing_items(
        drawing_completeness: float,
        specification_completeness: float,
        system_completeness: float,
        equipment_completeness: float,
        schedule_completeness: float,
    ) -> list[str]:
        missing: list[str] = []

        if drawing_completeness < 1.0:
            missing.append("Missing drawing index.")
        if specification_completeness < 1.0:
            missing.append("Missing specification index.")
        if system_completeness < 1.0:
            missing.append("Missing system detection.")
        if equipment_completeness < 1.0:
            missing.append("Missing equipment detection.")
        if schedule_completeness < 1.0:
            missing.append("Missing device schedule, keynotes, or legend data.")

        return missing

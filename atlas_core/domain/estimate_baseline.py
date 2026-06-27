"""Estimate baseline domain model for Atlas Core."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from atlas_core.services.equipment_matrix_service import EquipmentMatrixRow


class EstimateBaselineStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    AWARDED = "awarded"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


@dataclass
class EstimateBaseline:
    baseline_id: str
    project_id: str
    name: str
    rows: list[EquipmentMatrixRow] = field(default_factory=list)
    status: EstimateBaselineStatus = EstimateBaselineStatus.DRAFT
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.baseline_id = self._normalize_required_text(
            "baseline_id",
            self.baseline_id,
        )
        self.project_id = self._normalize_required_text(
            "project_id",
            self.project_id,
        )
        self.name = self._normalize_required_text("name", self.name)

        if not isinstance(self.status, EstimateBaselineStatus):
            self.status = EstimateBaselineStatus(self.status)

        if not isinstance(self.version, int) or self.version <= 0:
            raise ValueError("version must be greater than 0")

        self.created_by = self._normalize_optional_text(self.created_by)
        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def submit(self) -> None:
        self.status = EstimateBaselineStatus.SUBMITTED

    def award(self) -> None:
        self.status = EstimateBaselineStatus.AWARDED

    def supersede(self) -> None:
        self.status = EstimateBaselineStatus.SUPERSEDED

    def archive(self) -> None:
        self.status = EstimateBaselineStatus.ARCHIVED

    def total_budget_cost(self) -> float:
        return sum((self._number(row.budget_cost) for row in self.rows), 0.0)

    def total_sell_price(self) -> float:
        return sum((self._number(row.sell_price) for row in self.rows), 0.0)

    def gross_margin(self) -> float | None:
        total_sell_price = self.total_sell_price()
        if total_sell_price == 0:
            return None

        return (total_sell_price - self.total_budget_cost()) / total_sell_price

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "project_id": self.project_id,
            "name": self.name,
            "rows": [row.to_dict() for row in self.rows],
            "status": self.status.value,
            "version": self.version,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "notes": list(self.notes),
        }

    @classmethod
    def _normalize_required_text(cls, field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

    @classmethod
    def _normalize_note(cls, note: str) -> str:
        return cls._normalize_required_text("note", note)

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _number(value: Any) -> float:
        if value in (None, ""):
            return 0.0

        return float(value)

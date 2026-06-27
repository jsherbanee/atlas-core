"""Purchase order domain model for Atlas Core."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class PurchaseOrderLine:
    line_id: str
    description: str
    equipment_id: str | None = None
    quantity: float = 1
    unit_cost: float = 0
    received_quantity: float = 0
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.line_id = self._normalize_required_text("line_id", self.line_id)
        self.description = self._normalize_required_text(
            "description",
            self.description,
        )
        self.equipment_id = self._normalize_optional_text(self.equipment_id)

        if self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")

        if self.unit_cost < 0:
            raise ValueError("unit_cost cannot be negative")

        self._validate_received_quantity(self.received_quantity)
        self.notes = [self._normalize_note(note) for note in self.notes]

    def receive(self, quantity: float) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be greater than 0")

        self._validate_received_quantity(self.received_quantity + quantity)
        self.received_quantity += quantity

    def remaining_quantity(self) -> float:
        return self.quantity - self.received_quantity

    def extended_cost(self) -> float:
        return self.quantity * self.unit_cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_id": self.line_id,
            "equipment_id": self.equipment_id,
            "description": self.description,
            "quantity": self.quantity,
            "unit_cost": self.unit_cost,
            "received_quantity": self.received_quantity,
            "notes": list(self.notes),
        }

    def _validate_received_quantity(self, received_quantity: float) -> None:
        if received_quantity < 0:
            raise ValueError("received_quantity cannot be negative")

        if received_quantity > self.quantity:
            raise ValueError("received_quantity cannot exceed quantity")

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
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


@dataclass
class PurchaseOrder:
    purchase_order_id: str
    project_id: str
    vendor_id: str
    vendor_name: str
    baseline_id: str | None = None
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    lines: list[PurchaseOrderLine] = field(default_factory=list)
    issued_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.purchase_order_id = self._normalize_required_text(
            "purchase_order_id",
            self.purchase_order_id,
        )
        self.project_id = self._normalize_required_text(
            "project_id",
            self.project_id,
        )
        self.vendor_id = self._normalize_required_text("vendor_id", self.vendor_id)
        self.vendor_name = self._normalize_required_text(
            "vendor_name",
            self.vendor_name,
        )
        self.baseline_id = self._normalize_optional_text(self.baseline_id)

        if not isinstance(self.status, PurchaseOrderStatus):
            self.status = PurchaseOrderStatus(self.status)

        self.lines = [self._normalize_line(line) for line in self.lines]
        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_line(self, line: PurchaseOrderLine) -> None:
        self.lines.append(self._normalize_line(line))

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def issue(self) -> None:
        self.status = PurchaseOrderStatus.ISSUED
        self.issued_at = datetime.utcnow().isoformat()

    def cancel(self) -> None:
        self.status = PurchaseOrderStatus.CANCELLED

    def close(self) -> None:
        self.status = PurchaseOrderStatus.CLOSED

    def receive_line(self, line_id: str, quantity: float) -> None:
        line = self._line_by_id(line_id)
        if line is None:
            raise ValueError("line_id was not found")

        line.receive(quantity)
        self._update_receiving_status()

    def total_cost(self) -> float:
        return sum((line.extended_cost() for line in self.lines), 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "purchase_order_id": self.purchase_order_id,
            "project_id": self.project_id,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "baseline_id": self.baseline_id,
            "status": self.status.value,
            "lines": [line.to_dict() for line in self.lines],
            "issued_at": self.issued_at,
            "created_at": self.created_at,
            "notes": list(self.notes),
        }

    def _line_by_id(self, line_id: str) -> PurchaseOrderLine | None:
        normalized_line_id = self._normalize_required_text("line_id", line_id)
        for line in self.lines:
            if line.line_id == normalized_line_id:
                return line

        return None

    def _update_receiving_status(self) -> None:
        if not self.lines:
            return

        if all(line.remaining_quantity() == 0 for line in self.lines):
            self.status = PurchaseOrderStatus.RECEIVED
            return

        if any(line.received_quantity > 0 for line in self.lines):
            self.status = PurchaseOrderStatus.PARTIALLY_RECEIVED

    @classmethod
    def _normalize_line(
        cls,
        line: PurchaseOrderLine | dict[str, Any],
    ) -> PurchaseOrderLine:
        if isinstance(line, PurchaseOrderLine):
            return line

        return PurchaseOrderLine(**line)

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
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()

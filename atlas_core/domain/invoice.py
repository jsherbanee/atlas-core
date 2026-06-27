"""Invoice domain model for Atlas Core."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    RECEIVED = "received"
    APPROVED = "approved"
    DISPUTED = "disputed"
    PAID = "paid"
    VOID = "void"


@dataclass
class InvoiceLine:
    line_id: str
    description: str
    purchase_order_line_id: str | None = None
    equipment_id: str | None = None
    quantity: float = 1
    unit_cost: float = 0
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.line_id = self._normalize_required_text("line_id", self.line_id)
        self.description = self._normalize_required_text(
            "description",
            self.description,
        )
        self.purchase_order_line_id = self._normalize_optional_text(
            self.purchase_order_line_id
        )
        self.equipment_id = self._normalize_optional_text(self.equipment_id)

        if self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")

        if self.unit_cost < 0:
            raise ValueError("unit_cost cannot be negative")

        self.notes = [self._normalize_note(note) for note in self.notes]

    def extended_cost(self) -> float:
        return self.quantity * self.unit_cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_id": self.line_id,
            "purchase_order_line_id": self.purchase_order_line_id,
            "equipment_id": self.equipment_id,
            "description": self.description,
            "quantity": self.quantity,
            "unit_cost": self.unit_cost,
            "notes": list(self.notes),
        }

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
class Invoice:
    invoice_id: str
    project_id: str
    vendor_id: str
    vendor_name: str
    purchase_order_id: str | None = None
    status: InvoiceStatus = InvoiceStatus.DRAFT
    lines: list[InvoiceLine] = field(default_factory=list)
    received_at: str | None = None
    approved_at: str | None = None
    paid_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.invoice_id = self._normalize_required_text(
            "invoice_id",
            self.invoice_id,
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
        self.purchase_order_id = self._normalize_optional_text(
            self.purchase_order_id
        )

        if not isinstance(self.status, InvoiceStatus):
            self.status = InvoiceStatus(self.status)

        self.lines = [self._normalize_line(line) for line in self.lines]
        self.notes = [self._normalize_note(note) for note in self.notes]

    def add_line(self, line: InvoiceLine) -> None:
        self.lines.append(self._normalize_line(line))

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_note(note))

    def receive(self) -> None:
        self.status = InvoiceStatus.RECEIVED
        self.received_at = datetime.utcnow().isoformat()

    def approve(self) -> None:
        self.status = InvoiceStatus.APPROVED
        self.approved_at = datetime.utcnow().isoformat()

    def dispute(self, note: str | None = None) -> None:
        self.status = InvoiceStatus.DISPUTED
        if note is not None:
            self.add_note(note)

    def pay(self) -> None:
        self.status = InvoiceStatus.PAID
        self.paid_at = datetime.utcnow().isoformat()

    def void(self) -> None:
        self.status = InvoiceStatus.VOID

    def total_cost(self) -> float:
        return sum((line.extended_cost() for line in self.lines), 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "project_id": self.project_id,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "purchase_order_id": self.purchase_order_id,
            "status": self.status.value,
            "lines": [line.to_dict() for line in self.lines],
            "received_at": self.received_at,
            "approved_at": self.approved_at,
            "paid_at": self.paid_at,
            "created_at": self.created_at,
            "notes": list(self.notes),
        }

    @classmethod
    def _normalize_line(
        cls,
        line: InvoiceLine | dict[str, Any],
    ) -> InvoiceLine:
        if isinstance(line, InvoiceLine):
            return line

        return InvoiceLine(**line)

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

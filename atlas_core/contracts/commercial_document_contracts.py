"""Contracts for commercial document foundation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from atlas_core.domain.commercial_document import CommercialDocumentType


def _required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value.strip()


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


@dataclass
class CommercialDocumentCreateRequest:
    tenant_id: str
    organization_id: str
    document_type: CommercialDocumentType
    project_id: str | None = None
    project_code: str | None = None
    customer_id: str | None = None
    vendor_id: str | None = None

    def __post_init__(self) -> None:
        self.tenant_id = _required_text("tenant_id", self.tenant_id)
        self.organization_id = _required_text("organization_id", self.organization_id)
        if not isinstance(self.document_type, CommercialDocumentType):
            self.document_type = CommercialDocumentType(self.document_type)
        self.project_id = _optional_text(self.project_id)
        self.project_code = _optional_text(self.project_code)
        self.customer_id = _optional_text(self.customer_id)
        self.vendor_id = _optional_text(self.vendor_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "document_type": self.document_type.value,
            "project_id": self.project_id,
            "project_code": self.project_code,
            "customer_id": self.customer_id,
            "vendor_id": self.vendor_id,
        }


@dataclass
class CommercialDocumentLineRequest:
    description: str
    quantity: Decimal
    unit_price: Decimal
    sequence: int | None = None
    unit_of_measure: str | None = None
    discount: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    project_code: str | None = None
    product_or_service_reference: str | None = None
    source_document_id: str | None = None
    source_line_id: str | None = None
    related_document_id: str | None = None
    related_line_id: str | None = None

    def __post_init__(self) -> None:
        self.description = _required_text("description", self.description)
        if self.sequence is not None:
            self.sequence = int(self.sequence)
            if self.sequence <= 0:
                raise ValueError("sequence must be greater than 0")
        self.unit_of_measure = _optional_text(self.unit_of_measure)
        self.project_code = _optional_text(self.project_code)
        self.product_or_service_reference = _optional_text(
            self.product_or_service_reference
        )
        self.source_document_id = _optional_text(self.source_document_id)
        self.source_line_id = _optional_text(self.source_line_id)
        self.related_document_id = _optional_text(self.related_document_id)
        self.related_line_id = _optional_text(self.related_line_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "sequence": self.sequence,
            "unit_of_measure": self.unit_of_measure,
            "discount": str(self.discount),
            "tax_rate": str(self.tax_rate),
            "unit_cost": str(self.unit_cost),
            "project_code": self.project_code,
            "product_or_service_reference": self.product_or_service_reference,
            "source_document_id": self.source_document_id,
            "source_line_id": self.source_line_id,
            "related_document_id": self.related_document_id,
            "related_line_id": self.related_line_id,
        }


@dataclass
class CommercialDocumentResponse:
    payload: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "payload": dict(self.payload),
            "warnings": list(self.warnings),
        }

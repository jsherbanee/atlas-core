"""Contracts for the Commercial MVP API boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field as dataclass_field, is_dataclass
from decimal import Decimal
from typing import Any, cast

from atlas_core.contracts.commercial_spine_contracts import (
    EstimateLineItem,
    ProjectJobLink,
    VendorBillLineItem,
)


def _required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value.strip()


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _serialize_value(value: Any) -> Any:
    if is_dataclass(value):
        return {
            key: _serialize_value(item)
            for key, item in asdict(cast(Any, value)).items()
        }
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    return value


@dataclass
class CommercialMvpTenantContext:
    tenant_id: str
    organization_id: str | None = None

    def __post_init__(self) -> None:
        self.tenant_id = _required_text("tenant_id", self.tenant_id)
        self.organization_id = _optional_text(self.organization_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
        }


@dataclass
class CommercialMvpApiRequest:
    context: CommercialMvpTenantContext | dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.context, CommercialMvpTenantContext):
            self.context = CommercialMvpTenantContext(**self.context)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> CommercialMvpApiRequest:
        return cls(**dict(payload))

    def to_dict(self) -> dict[str, Any]:
        return _serialize_value(asdict(self))


@dataclass
class CreateCustomerAccountRequest(CommercialMvpApiRequest):
    customer_id: str = ""
    name: str = ""
    account_number: str | None = None
    legal_name: str | None = None
    billing_email: str | None = None
    active: bool = True
    notes: list[str] = dataclass_field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.customer_id = _required_text("customer_id", self.customer_id)
        self.name = _required_text("name", self.name)
        self.account_number = _optional_text(self.account_number)
        self.legal_name = _optional_text(self.legal_name)
        self.billing_email = _optional_text(self.billing_email)
        self.notes = [_required_text("note", note) for note in list(self.notes or [])]


@dataclass
class CreateOpportunityRequest(CommercialMvpApiRequest):
    customer_id: str = ""
    opportunity_id: str = ""
    name: str = ""
    estimated_value: Decimal | None = None
    close_date: str | None = None
    notes: list[str] = dataclass_field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.customer_id = _required_text("customer_id", self.customer_id)
        self.opportunity_id = _required_text("opportunity_id", self.opportunity_id)
        self.name = _required_text("name", self.name)
        self.close_date = _optional_text(self.close_date)
        self.notes = [_required_text("note", note) for note in list(self.notes or [])]


@dataclass
class CreateEstimateRequest(CommercialMvpApiRequest):
    customer_id: str = ""
    estimate_id: str = ""
    opportunity_id: str | None = None
    proposal_id: str | None = None
    project_job_link: ProjectJobLink | dict[str, Any] | None = None
    line_items: list[EstimateLineItem | dict[str, Any]] = dataclass_field(
        default_factory=list
    )
    notes: list[str] = dataclass_field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.customer_id = _required_text("customer_id", self.customer_id)
        self.estimate_id = _required_text("estimate_id", self.estimate_id)
        self.opportunity_id = _optional_text(self.opportunity_id)
        self.proposal_id = _optional_text(self.proposal_id)
        self.project_job_link = self._normalize_project_job_link(self.project_job_link)
        self.line_items = [
            item if isinstance(item, EstimateLineItem) else EstimateLineItem(**item)
            for item in list(self.line_items or [])
        ]
        self.notes = [_required_text("note", note) for note in list(self.notes or [])]

    @staticmethod
    def _normalize_project_job_link(
        value: ProjectJobLink | dict[str, Any] | None,
    ) -> ProjectJobLink | None:
        if value is None:
            return None
        if isinstance(value, ProjectJobLink):
            return value
        return ProjectJobLink(**value)


@dataclass
class AddEstimateLineItemRequest(CommercialMvpApiRequest):
    estimate_id: str = ""
    line_item: EstimateLineItem | dict[str, Any] = dataclass_field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.estimate_id = _required_text("estimate_id", self.estimate_id)
        if not isinstance(self.line_item, EstimateLineItem):
            self.line_item = EstimateLineItem(**self.line_item)


@dataclass
class UpdateEstimateLineItemRequest(CommercialMvpApiRequest):
    estimate_id: str = ""
    line_item_id: str = ""
    description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    catalog_item_id: str | None = None
    notes: list[str] | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.estimate_id = _required_text("estimate_id", self.estimate_id)
        self.line_item_id = _required_text("line_item_id", self.line_item_id)
        self.description = _optional_text(self.description)
        self.catalog_item_id = _optional_text(self.catalog_item_id)
        if self.notes is not None:
            self.notes = [
                _required_text("note", note) for note in list(self.notes or [])
            ]


@dataclass
class RemoveEstimateLineItemRequest(CommercialMvpApiRequest):
    estimate_id: str = ""
    line_item_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.estimate_id = _required_text("estimate_id", self.estimate_id)
        self.line_item_id = _required_text("line_item_id", self.line_item_id)


@dataclass
class CreateProposalForEstimateRequest(CommercialMvpApiRequest):
    estimate_id: str = ""
    proposal_id: str | None = None
    notes: list[str] = dataclass_field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.estimate_id = _required_text("estimate_id", self.estimate_id)
        self.proposal_id = _optional_text(self.proposal_id)
        self.notes = [_required_text("note", note) for note in list(self.notes or [])]


@dataclass
class MarkProposalReadyRequest(CommercialMvpApiRequest):
    proposal_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.proposal_id = _required_text("proposal_id", self.proposal_id)


@dataclass
class SendProposalRequest(CommercialMvpApiRequest):
    proposal_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.proposal_id = _required_text("proposal_id", self.proposal_id)


@dataclass
class AcceptProposalRequest(CommercialMvpApiRequest):
    proposal_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.proposal_id = _required_text("proposal_id", self.proposal_id)


@dataclass
class RejectProposalRequest(CommercialMvpApiRequest):
    proposal_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.proposal_id = _required_text("proposal_id", self.proposal_id)


@dataclass
class ConvertAcceptedEstimateToSalesOrderRequest(CommercialMvpApiRequest):
    estimate_id: str = ""
    sales_order_id: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.estimate_id = _required_text("estimate_id", self.estimate_id)
        self.sales_order_id = _optional_text(self.sales_order_id)


@dataclass
class CheckInventoryAvailabilityRequest(CommercialMvpApiRequest):
    sales_order_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.sales_order_id = _required_text("sales_order_id", self.sales_order_id)


@dataclass
class ReserveInventoryRequest(CommercialMvpApiRequest):
    sales_order_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.sales_order_id = _required_text("sales_order_id", self.sales_order_id)


@dataclass
class GenerateCustomerInvoiceFromSalesOrderRequest(CommercialMvpApiRequest):
    sales_order_id: str = ""
    customer_invoice_id: str | None = None
    due_at: str | None = None
    notes: list[str] = dataclass_field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.sales_order_id = _required_text("sales_order_id", self.sales_order_id)
        self.customer_invoice_id = _optional_text(self.customer_invoice_id)
        self.due_at = _optional_text(self.due_at)
        self.notes = [_required_text("note", note) for note in list(self.notes or [])]


@dataclass
class CreateVendorBillRequest(CommercialMvpApiRequest):
    vendor_bill_id: str = ""
    vendor_id: str = ""
    vendor_name: str = ""
    purchase_order_id: str | None = None
    procurement_need_id: str | None = None
    project_job_link: ProjectJobLink | dict[str, Any] | None = None
    line_items: list[VendorBillLineItem | dict[str, Any]] = dataclass_field(
        default_factory=list
    )
    entered_at: str | None = None
    due_at: str | None = None
    notes: list[str] = dataclass_field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.vendor_bill_id = _required_text("vendor_bill_id", self.vendor_bill_id)
        self.vendor_id = _required_text("vendor_id", self.vendor_id)
        self.vendor_name = _required_text("vendor_name", self.vendor_name)
        self.purchase_order_id = _optional_text(self.purchase_order_id)
        self.procurement_need_id = _optional_text(self.procurement_need_id)
        self.project_job_link = self._normalize_project_job_link(self.project_job_link)
        self.entered_at = _optional_text(self.entered_at)
        self.due_at = _optional_text(self.due_at)
        self.line_items = [
            item if isinstance(item, VendorBillLineItem) else VendorBillLineItem(**item)
            for item in list(self.line_items or [])
        ]
        self.notes = [_required_text("note", note) for note in list(self.notes or [])]

    @staticmethod
    def _normalize_project_job_link(
        value: ProjectJobLink | dict[str, Any] | None,
    ) -> ProjectJobLink | None:
        if value is None:
            return None
        if isinstance(value, ProjectJobLink):
            return value
        return ProjectJobLink(**value)


@dataclass
class MarkCustomerInvoiceSyncPendingRequest(CommercialMvpApiRequest):
    customer_invoice_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.customer_invoice_id = _required_text(
            "customer_invoice_id", self.customer_invoice_id
        )


@dataclass
class MarkVendorBillSyncPendingRequest(CommercialMvpApiRequest):
    vendor_bill_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.vendor_bill_id = _required_text("vendor_bill_id", self.vendor_bill_id)


@dataclass
class GetCommercialReportingSnapshotRequest(CommercialMvpApiRequest):
    def __post_init__(self) -> None:
        super().__post_init__()


@dataclass
class CommercialMvpApiError:
    code: str
    message: str
    field: str | None = None
    details: dict[str, Any] = dataclass_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize_value(asdict(self))


@dataclass
class CommercialMvpApiResponse:
    operation: str
    tenant_id: str | None
    organization_id: str | None
    payload: dict[str, Any] | None = None
    error: CommercialMvpApiError | None = None
    warnings: list[str] = dataclass_field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        return _serialize_value(
            {
                "operation": self.operation,
                "status": "ok" if self.ok else "error",
                "tenant_id": self.tenant_id,
                "organization_id": self.organization_id,
                "payload": self.payload,
                "error": self.error,
                "warnings": list(self.warnings),
            }
        )


__all__ = [
    "AcceptProposalRequest",
    "AddEstimateLineItemRequest",
    "CheckInventoryAvailabilityRequest",
    "CommercialMvpApiError",
    "CommercialMvpApiRequest",
    "CommercialMvpApiResponse",
    "CommercialMvpTenantContext",
    "ConvertAcceptedEstimateToSalesOrderRequest",
    "CreateCustomerAccountRequest",
    "CreateEstimateRequest",
    "CreateOpportunityRequest",
    "CreateProposalForEstimateRequest",
    "CreateVendorBillRequest",
    "GenerateCustomerInvoiceFromSalesOrderRequest",
    "GetCommercialReportingSnapshotRequest",
    "MarkProposalReadyRequest",
    "MarkCustomerInvoiceSyncPendingRequest",
    "MarkVendorBillSyncPendingRequest",
    "RejectProposalRequest",
    "RemoveEstimateLineItemRequest",
    "ReserveInventoryRequest",
    "SendProposalRequest",
    "UpdateEstimateLineItemRequest",
]

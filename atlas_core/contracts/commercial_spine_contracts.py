"""Commercial operating-spine contracts for Atlas Core.

These models stay intentionally lightweight. They capture the workflow shape
and system-of-record boundaries for future commercial features without
implementing the full estimating, inventory, or accounting logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, TypeVar


def _required_text(field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    return normalized or None


def _optional_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _decimal(field_name: str, value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid decimal value") from exc


def _decimal_non_negative(field_name: str, value: Any) -> Decimal:
    parsed = _decimal(field_name, value)
    if parsed < Decimal("0"):
        raise ValueError(f"{field_name} cannot be negative")
    return parsed


def _serialize_value(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


EnumT = TypeVar("EnumT", bound=Enum)


def _normalize_enum(value: Any, enum_cls: type[EnumT]) -> EnumT:
    if isinstance(value, enum_cls):
        return value
    return enum_cls(value)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class OpportunityStatus(str, Enum):
    OPEN = "open"
    QUALIFIED = "qualified"
    WON = "won"
    LOST = "lost"
    ON_HOLD = "on_hold"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    SENT = "sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SalesOrderStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    FULFILLED = "fulfilled"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ChangeOrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    VOIDED = "voided"


class ChangeOrderDirection(str, Enum):
    ADDITIVE = "additive"
    DEDUCTIVE = "deductive"


class InventoryReservationStatus(str, Enum):
    REQUESTED = "requested"
    RESERVED = "reserved"
    RELEASED = "released"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class ProcurementNeedStatus(str, Enum):
    IDENTIFIED = "identified"
    REQUESTED = "requested"
    QUOTED = "quoted"
    ORDERED = "ordered"
    RECEIVED = "received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class CustomerInvoiceStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    ISSUED = "issued"
    VOIDED = "voided"


class VendorBillStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    ENTERED = "entered"
    VOIDED = "voided"


class QuickBooksSyncDirection(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class QuickBooksSyncStatus(str, Enum):
    NOT_READY = "not_ready"
    NOT_SYNCED = "not_synced"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SYNCED = "synced"
    FAILED = "failed"
    SKIPPED = "skipped"


class QuickBooksSyncOperation(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    VOID = "void"


@dataclass
class QuickBooksSyncTask:
    tenant_id: str
    organization_id: str | None
    entity_type: str
    entity_id: str
    operation: QuickBooksSyncOperation
    idempotency_key: str
    status: QuickBooksSyncStatus
    retry_eligible: bool = False
    external_id: str | None = None
    sync_reference_id: str | None = None


@dataclass
class CommercialRecordBase:
    tenant_id: str
    organization_id: str | None = None

    def __post_init__(self) -> None:
        self.tenant_id = _required_text("tenant_id", self.tenant_id)
        self.organization_id = _optional_text(self.organization_id)

    def _scope_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
        }


@dataclass
class CustomerAccount(CommercialRecordBase):
    customer_id: str = ""
    name: str = ""
    account_number: str | None = None
    legal_name: str | None = None
    billing_email: str | None = None
    active: bool = True
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.customer_id = _required_text("customer_id", self.customer_id)
        self.name = _required_text("name", self.name)
        self.account_number = _optional_text(self.account_number)
        self.legal_name = _optional_text(self.legal_name)
        self.billing_email = _optional_text(self.billing_email)
        self.active = _optional_bool(self.active, default=True)
        self.notes = [_required_text("note", note) for note in list(self.notes)]

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "customer_id": self.customer_id,
                "name": self.name,
                "account_number": self.account_number,
                "legal_name": self.legal_name,
                "billing_email": self.billing_email,
                "active": self.active,
                "notes": list(self.notes),
            }
        )
        return payload


@dataclass
class Opportunity(CommercialRecordBase):
    opportunity_id: str = ""
    customer_id: str = ""
    name: str = ""
    status: OpportunityStatus = OpportunityStatus.OPEN
    estimated_value: Decimal | None = None
    close_date: str | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.opportunity_id = _required_text("opportunity_id", self.opportunity_id)
        self.customer_id = _required_text("customer_id", self.customer_id)
        self.name = _required_text("name", self.name)
        self.status = _normalize_enum(self.status, OpportunityStatus)
        self.estimated_value = (
            None
            if self.estimated_value is None
            else _decimal_non_negative("estimated_value", self.estimated_value)
        )
        self.close_date = _optional_text(self.close_date)
        self.notes = [_required_text("note", note) for note in list(self.notes)]

    def mark_won(self) -> None:
        self.status = OpportunityStatus.WON

    def mark_lost(self) -> None:
        self.status = OpportunityStatus.LOST

    def mark_on_hold(self) -> None:
        self.status = OpportunityStatus.ON_HOLD

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "opportunity_id": self.opportunity_id,
                "customer_id": self.customer_id,
                "name": self.name,
                "status": self.status.value,
                "estimated_value": _serialize_value(self.estimated_value),
                "close_date": self.close_date,
                "notes": list(self.notes),
            }
        )
        return payload


@dataclass
class ProjectJobLink:
    project_id: str
    job_id: str | None = None
    project_name: str | None = None
    job_number: str | None = None

    def __post_init__(self) -> None:
        self.project_id = _required_text("project_id", self.project_id)
        self.job_id = _optional_text(self.job_id)
        self.project_name = _optional_text(self.project_name)
        self.job_number = _optional_text(self.job_number)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "job_id": self.job_id,
            "project_name": self.project_name,
            "job_number": self.job_number,
        }


@dataclass
class VendorManufacturerReference:
    vendor_id: str
    vendor_name: str
    manufacturer_id: str | None = None
    manufacturer_name: str | None = None
    vendor_part_number: str | None = None

    def __post_init__(self) -> None:
        self.vendor_id = _required_text("vendor_id", self.vendor_id)
        self.vendor_name = _required_text("vendor_name", self.vendor_name)
        self.manufacturer_id = _optional_text(self.manufacturer_id)
        self.manufacturer_name = _optional_text(self.manufacturer_name)
        self.vendor_part_number = _optional_text(self.vendor_part_number)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "manufacturer_id": self.manufacturer_id,
            "manufacturer_name": self.manufacturer_name,
            "vendor_part_number": self.vendor_part_number,
        }


@dataclass
class CatalogItem(CommercialRecordBase):
    catalog_item_id: str = ""
    sku: str = ""
    description: str = ""
    unit_of_measure: str = "ea"
    list_price: Decimal = Decimal("0")
    active: bool = True
    vendor_manufacturer_reference: VendorManufacturerReference | None = None
    external_reference: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.catalog_item_id = _required_text("catalog_item_id", self.catalog_item_id)
        self.sku = _required_text("sku", self.sku)
        self.description = _required_text("description", self.description)
        self.unit_of_measure = _required_text("unit_of_measure", self.unit_of_measure)
        self.list_price = _decimal_non_negative("list_price", self.list_price)
        self.active = _optional_bool(self.active, default=True)
        if self.vendor_manufacturer_reference is not None and not isinstance(
            self.vendor_manufacturer_reference, VendorManufacturerReference
        ):
            self.vendor_manufacturer_reference = VendorManufacturerReference(
                **self.vendor_manufacturer_reference
            )
        self.external_reference = _optional_text(self.external_reference)

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "catalog_item_id": self.catalog_item_id,
                "sku": self.sku,
                "description": self.description,
                "unit_of_measure": self.unit_of_measure,
                "list_price": str(self.list_price),
                "active": self.active,
                "vendor_manufacturer_reference": _serialize_value(
                    self.vendor_manufacturer_reference
                ),
                "external_reference": self.external_reference,
            }
        )
        return payload


@dataclass
class CommercialLineItemBase:
    line_item_id: str
    description: str
    quantity: Decimal
    unit_price: Decimal = Decimal("0")
    catalog_item_id: str | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.line_item_id = _required_text("line_item_id", self.line_item_id)
        self.description = _required_text("description", self.description)
        self.quantity = _decimal_non_negative("quantity", self.quantity)
        self.unit_price = _decimal_non_negative("unit_price", self.unit_price)
        self.catalog_item_id = _optional_text(self.catalog_item_id)
        self.notes = [_required_text("note", note) for note in list(self.notes)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_item_id": self.line_item_id,
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "catalog_item_id": self.catalog_item_id,
            "notes": list(self.notes),
        }


@dataclass
class EstimateLineItem(CommercialLineItemBase):
    estimate_id: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.estimate_id = _optional_text(self.estimate_id)

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["estimate_id"] = self.estimate_id
        return payload


@dataclass
class SalesOrderLineItem(CommercialLineItemBase):
    estimate_line_item_id: str | None = None
    change_order_id: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.estimate_line_item_id = _optional_text(self.estimate_line_item_id)
        self.change_order_id = _optional_text(self.change_order_id)

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "estimate_line_item_id": self.estimate_line_item_id,
                "change_order_id": self.change_order_id,
            }
        )
        return payload


@dataclass
class Estimate(CommercialRecordBase):
    estimate_id: str = ""
    customer_id: str = ""
    opportunity_id: str | None = None
    proposal_id: str | None = None
    project_job_link: ProjectJobLink | None = None
    line_items: list[EstimateLineItem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.estimate_id = _required_text("estimate_id", self.estimate_id)
        self.customer_id = _required_text("customer_id", self.customer_id)
        self.opportunity_id = _optional_text(self.opportunity_id)
        self.proposal_id = _optional_text(self.proposal_id)
        if self.project_job_link is not None and not isinstance(
            self.project_job_link, ProjectJobLink
        ):
            self.project_job_link = ProjectJobLink(**self.project_job_link)
        self.line_items = [
            item if isinstance(item, EstimateLineItem) else EstimateLineItem(**item)
            for item in list(self.line_items)
        ]
        self.notes = [_required_text("note", note) for note in list(self.notes)]

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "estimate_id": self.estimate_id,
                "customer_id": self.customer_id,
                "opportunity_id": self.opportunity_id,
                "proposal_id": self.proposal_id,
                "project_job_link": _serialize_value(self.project_job_link),
                "line_items": [item.to_dict() for item in self.line_items],
                "notes": list(self.notes),
            }
        )
        return payload


@dataclass
class Proposal(CommercialRecordBase):
    proposal_id: str = ""
    estimate_id: str = ""
    customer_id: str = ""
    status: ProposalStatus = ProposalStatus.DRAFT
    sent_at: str | None = None
    responded_at: str | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.proposal_id = _required_text("proposal_id", self.proposal_id)
        self.estimate_id = _required_text("estimate_id", self.estimate_id)
        self.customer_id = _required_text("customer_id", self.customer_id)
        self.status = _normalize_enum(self.status, ProposalStatus)
        self.sent_at = _optional_text(self.sent_at)
        self.responded_at = _optional_text(self.responded_at)
        self.notes = [_required_text("note", note) for note in list(self.notes)]

    def mark_ready(self) -> None:
        if self.status not in {ProposalStatus.DRAFT, ProposalStatus.CANCELLED}:
            raise ValueError(
                "proposal can only be marked ready from draft or cancelled"
            )
        self.status = ProposalStatus.READY

    def send(self) -> None:
        if self.status not in {ProposalStatus.DRAFT, ProposalStatus.READY}:
            raise ValueError("proposal can only be sent from draft or ready")
        self.status = ProposalStatus.SENT
        self.sent_at = _utc_now()

    def accept(self) -> None:
        if self.status != ProposalStatus.SENT:
            raise ValueError("proposal can only be accepted after it is sent")
        self.status = ProposalStatus.ACCEPTED
        self.responded_at = _utc_now()

    def decline(self) -> None:
        if self.status != ProposalStatus.SENT:
            raise ValueError("proposal can only be declined after it is sent")
        self.status = ProposalStatus.DECLINED
        self.responded_at = _utc_now()

    def expire(self) -> None:
        if self.status != ProposalStatus.SENT:
            raise ValueError("proposal can only expire after it is sent")
        self.status = ProposalStatus.EXPIRED
        self.responded_at = _utc_now()

    def cancel(self) -> None:
        self.status = ProposalStatus.CANCELLED

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "proposal_id": self.proposal_id,
                "estimate_id": self.estimate_id,
                "customer_id": self.customer_id,
                "status": self.status.value,
                "sent_at": self.sent_at,
                "responded_at": self.responded_at,
                "notes": list(self.notes),
            }
        )
        return payload


@dataclass
class SalesOrder(CommercialRecordBase):
    sales_order_id: str = ""
    customer_id: str = ""
    estimate_id: str | None = None
    proposal_id: str | None = None
    project_job_link: ProjectJobLink | None = None
    status: SalesOrderStatus = SalesOrderStatus.DRAFT
    line_items: list[SalesOrderLineItem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.sales_order_id = _required_text("sales_order_id", self.sales_order_id)
        self.customer_id = _required_text("customer_id", self.customer_id)
        self.estimate_id = _optional_text(self.estimate_id)
        self.proposal_id = _optional_text(self.proposal_id)
        if self.project_job_link is not None and not isinstance(
            self.project_job_link, ProjectJobLink
        ):
            self.project_job_link = ProjectJobLink(**self.project_job_link)
        self.status = _normalize_enum(self.status, SalesOrderStatus)
        self.line_items = [
            item if isinstance(item, SalesOrderLineItem) else SalesOrderLineItem(**item)
            for item in list(self.line_items)
        ]
        self.notes = [_required_text("note", note) for note in list(self.notes)]

    def open(self) -> None:
        if self.status != SalesOrderStatus.DRAFT:
            raise ValueError("sales order can only be opened from draft")
        self.status = SalesOrderStatus.OPEN

    def mark_partially_fulfilled(self) -> None:
        if self.status not in {
            SalesOrderStatus.OPEN,
            SalesOrderStatus.PARTIALLY_FULFILLED,
        }:
            raise ValueError("sales order can only be partially fulfilled when open")
        self.status = SalesOrderStatus.PARTIALLY_FULFILLED

    def fulfill(self) -> None:
        if self.status not in {
            SalesOrderStatus.OPEN,
            SalesOrderStatus.PARTIALLY_FULFILLED,
        }:
            raise ValueError("sales order can only be fulfilled when open")
        self.status = SalesOrderStatus.FULFILLED

    def close(self) -> None:
        if self.status not in {
            SalesOrderStatus.FULFILLED,
            SalesOrderStatus.PARTIALLY_FULFILLED,
            SalesOrderStatus.OPEN,
        }:
            raise ValueError("sales order can only be closed once it is active")
        self.status = SalesOrderStatus.CLOSED

    def cancel(self) -> None:
        self.status = SalesOrderStatus.CANCELLED

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "sales_order_id": self.sales_order_id,
                "customer_id": self.customer_id,
                "estimate_id": self.estimate_id,
                "proposal_id": self.proposal_id,
                "project_job_link": _serialize_value(self.project_job_link),
                "status": self.status.value,
                "line_items": [item.to_dict() for item in self.line_items],
                "notes": list(self.notes),
            }
        )
        return payload


@dataclass
class ChangeOrder(CommercialRecordBase):
    change_order_id: str = ""
    sales_order_id: str = ""
    project_job_link: ProjectJobLink | None = None
    status: ChangeOrderStatus = ChangeOrderStatus.DRAFT
    direction: ChangeOrderDirection = ChangeOrderDirection.ADDITIVE
    change_order_number: str | None = None
    line_items: list[SalesOrderLineItem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.change_order_id = _required_text("change_order_id", self.change_order_id)
        self.sales_order_id = _required_text("sales_order_id", self.sales_order_id)
        if self.project_job_link is not None and not isinstance(
            self.project_job_link, ProjectJobLink
        ):
            self.project_job_link = ProjectJobLink(**self.project_job_link)
        self.status = _normalize_enum(self.status, ChangeOrderStatus)
        self.direction = _normalize_enum(self.direction, ChangeOrderDirection)
        self.change_order_number = _optional_text(self.change_order_number)
        self.line_items = [
            item if isinstance(item, SalesOrderLineItem) else SalesOrderLineItem(**item)
            for item in list(self.line_items)
        ]
        self.notes = [_required_text("note", note) for note in list(self.notes)]

    def submit(self) -> None:
        if self.status != ChangeOrderStatus.DRAFT:
            raise ValueError("change order can only be submitted from draft")
        self.status = ChangeOrderStatus.SUBMITTED

    def approve(self) -> None:
        if self.status != ChangeOrderStatus.SUBMITTED:
            raise ValueError("change order can only be approved after submission")
        self.status = ChangeOrderStatus.APPROVED

    def reject(self) -> None:
        if self.status != ChangeOrderStatus.SUBMITTED:
            raise ValueError("change order can only be rejected after submission")
        self.status = ChangeOrderStatus.REJECTED

    def apply(self) -> None:
        if self.status != ChangeOrderStatus.APPROVED:
            raise ValueError("change order can only be applied after approval")
        self.status = ChangeOrderStatus.APPLIED

    def void(self) -> None:
        self.status = ChangeOrderStatus.VOIDED

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "change_order_id": self.change_order_id,
                "sales_order_id": self.sales_order_id,
                "project_job_link": _serialize_value(self.project_job_link),
                "status": self.status.value,
                "direction": self.direction.value,
                "change_order_number": self.change_order_number,
                "line_items": [item.to_dict() for item in self.line_items],
                "notes": list(self.notes),
            }
        )
        return payload


@dataclass
class InventoryLocation(CommercialRecordBase):
    location_id: str = ""
    name: str = ""
    code: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()
        self.location_id = _required_text("location_id", self.location_id)
        self.name = _required_text("name", self.name)
        self.code = _optional_text(self.code)
        self.active = _optional_bool(self.active, default=True)

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "location_id": self.location_id,
                "name": self.name,
                "code": self.code,
                "active": self.active,
            }
        )
        return payload


@dataclass
class InventoryPosition(CommercialRecordBase):
    position_id: str = ""
    catalog_item_id: str = ""
    location_id: str = ""
    quantity_on_hand: Decimal = Decimal("0")
    quantity_reserved: Decimal = Decimal("0")
    quantity_available: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        super().__post_init__()
        self.position_id = _required_text("position_id", self.position_id)
        self.catalog_item_id = _required_text("catalog_item_id", self.catalog_item_id)
        self.location_id = _required_text("location_id", self.location_id)
        self.quantity_on_hand = _decimal_non_negative(
            "quantity_on_hand", self.quantity_on_hand
        )
        self.quantity_reserved = _decimal_non_negative(
            "quantity_reserved", self.quantity_reserved
        )
        self.quantity_available = _decimal_non_negative(
            "quantity_available", self.quantity_available
        )
        if self.quantity_reserved > self.quantity_on_hand:
            raise ValueError("quantity_reserved cannot exceed quantity_on_hand")
        if self.quantity_available > self.quantity_on_hand:
            raise ValueError("quantity_available cannot exceed quantity_on_hand")

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "position_id": self.position_id,
                "catalog_item_id": self.catalog_item_id,
                "location_id": self.location_id,
                "quantity_on_hand": str(self.quantity_on_hand),
                "quantity_reserved": str(self.quantity_reserved),
                "quantity_available": str(self.quantity_available),
            }
        )
        return payload


@dataclass
class InventoryReservation(CommercialRecordBase):
    reservation_id: str = ""
    catalog_item_id: str = ""
    location_id: str = ""
    quantity: Decimal = Decimal("0")
    status: InventoryReservationStatus = InventoryReservationStatus.REQUESTED
    sales_order_line_item_id: str | None = None
    change_order_id: str | None = None
    project_job_link: ProjectJobLink | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.reservation_id = _required_text("reservation_id", self.reservation_id)
        self.catalog_item_id = _required_text("catalog_item_id", self.catalog_item_id)
        self.location_id = _required_text("location_id", self.location_id)
        self.quantity = _decimal_non_negative("quantity", self.quantity)
        self.status = _normalize_enum(self.status, InventoryReservationStatus)
        self.sales_order_line_item_id = _optional_text(self.sales_order_line_item_id)
        self.change_order_id = _optional_text(self.change_order_id)
        if self.project_job_link is not None and not isinstance(
            self.project_job_link, ProjectJobLink
        ):
            self.project_job_link = ProjectJobLink(**self.project_job_link)

    def reserve(self) -> None:
        if self.status not in {
            InventoryReservationStatus.REQUESTED,
            InventoryReservationStatus.RELEASED,
        }:
            raise ValueError(
                "inventory reservation can only be reserved from a request"
            )
        self.status = InventoryReservationStatus.RESERVED

    def release(self) -> None:
        if self.status not in {
            InventoryReservationStatus.REQUESTED,
            InventoryReservationStatus.RESERVED,
        }:
            raise ValueError("inventory reservation can only be released when active")
        self.status = InventoryReservationStatus.RELEASED

    def fulfill(self) -> None:
        if self.status != InventoryReservationStatus.RESERVED:
            raise ValueError(
                "inventory reservation can only be fulfilled when reserved"
            )
        self.status = InventoryReservationStatus.FULFILLED

    def cancel(self) -> None:
        self.status = InventoryReservationStatus.CANCELLED

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "reservation_id": self.reservation_id,
                "catalog_item_id": self.catalog_item_id,
                "location_id": self.location_id,
                "quantity": str(self.quantity),
                "status": self.status.value,
                "sales_order_line_item_id": self.sales_order_line_item_id,
                "change_order_id": self.change_order_id,
                "project_job_link": _serialize_value(self.project_job_link),
            }
        )
        return payload


@dataclass
class ProcurementNeed(CommercialRecordBase):
    procurement_need_id: str = ""
    catalog_item_id: str = ""
    quantity_required: Decimal = Decimal("0")
    status: ProcurementNeedStatus = ProcurementNeedStatus.IDENTIFIED
    sales_order_id: str | None = None
    change_order_id: str | None = None
    vendor_id: str | None = None
    project_job_link: ProjectJobLink | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.procurement_need_id = _required_text(
            "procurement_need_id", self.procurement_need_id
        )
        self.catalog_item_id = _required_text("catalog_item_id", self.catalog_item_id)
        self.quantity_required = _decimal_non_negative(
            "quantity_required", self.quantity_required
        )
        self.status = _normalize_enum(self.status, ProcurementNeedStatus)
        self.sales_order_id = _optional_text(self.sales_order_id)
        self.change_order_id = _optional_text(self.change_order_id)
        self.vendor_id = _optional_text(self.vendor_id)
        if self.project_job_link is not None and not isinstance(
            self.project_job_link, ProjectJobLink
        ):
            self.project_job_link = ProjectJobLink(**self.project_job_link)

    def request(self) -> None:
        if self.status != ProcurementNeedStatus.IDENTIFIED:
            raise ValueError("procurement need can only be requested once identified")
        self.status = ProcurementNeedStatus.REQUESTED

    def quote(self) -> None:
        if self.status != ProcurementNeedStatus.REQUESTED:
            raise ValueError("procurement need can only be quoted after request")
        self.status = ProcurementNeedStatus.QUOTED

    def order(self) -> None:
        if self.status not in {
            ProcurementNeedStatus.REQUESTED,
            ProcurementNeedStatus.QUOTED,
        }:
            raise ValueError("procurement need can only be ordered after request")
        self.status = ProcurementNeedStatus.ORDERED

    def receive(self) -> None:
        if self.status != ProcurementNeedStatus.ORDERED:
            raise ValueError("procurement need can only be received after ordering")
        self.status = ProcurementNeedStatus.RECEIVED

    def close(self) -> None:
        if self.status not in {
            ProcurementNeedStatus.RECEIVED,
            ProcurementNeedStatus.ORDERED,
        }:
            raise ValueError("procurement need can only close when progressed")
        self.status = ProcurementNeedStatus.CLOSED

    def cancel(self) -> None:
        self.status = ProcurementNeedStatus.CANCELLED

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "procurement_need_id": self.procurement_need_id,
                "catalog_item_id": self.catalog_item_id,
                "quantity_required": str(self.quantity_required),
                "status": self.status.value,
                "sales_order_id": self.sales_order_id,
                "change_order_id": self.change_order_id,
                "vendor_id": self.vendor_id,
                "project_job_link": _serialize_value(self.project_job_link),
            }
        )
        return payload


@dataclass
class CustomerInvoiceLineItem(CommercialLineItemBase):
    sales_order_line_item_id: str | None = None
    change_order_id: str | None = None
    revenue_account_code: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.sales_order_line_item_id = _optional_text(self.sales_order_line_item_id)
        self.change_order_id = _optional_text(self.change_order_id)
        self.revenue_account_code = _optional_text(self.revenue_account_code)

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "sales_order_line_item_id": self.sales_order_line_item_id,
                "change_order_id": self.change_order_id,
                "revenue_account_code": self.revenue_account_code,
            }
        )
        return payload


@dataclass
class VendorBillLineItem(CommercialLineItemBase):
    purchase_order_line_item_id: str | None = None
    procurement_need_id: str | None = None
    expense_account_code: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.purchase_order_line_item_id = _optional_text(
            self.purchase_order_line_item_id
        )
        self.procurement_need_id = _optional_text(self.procurement_need_id)
        self.expense_account_code = _optional_text(self.expense_account_code)

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "purchase_order_line_item_id": self.purchase_order_line_item_id,
                "procurement_need_id": self.procurement_need_id,
                "expense_account_code": self.expense_account_code,
            }
        )
        return payload


@dataclass
class QuickBooksSyncReference(CommercialRecordBase):
    sync_reference_id: str = ""
    entity_type: str = ""
    entity_id: str = ""
    operation: QuickBooksSyncOperation = QuickBooksSyncOperation.CREATE
    idempotency_key: str | None = None
    external_id: str | None = None
    direction: QuickBooksSyncDirection = QuickBooksSyncDirection.OUTBOUND
    status: QuickBooksSyncStatus = QuickBooksSyncStatus.NOT_SYNCED
    retry_eligible: bool = False
    attempt_count: int = 0
    last_attempted_at: str | None = None
    last_synced_at: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.sync_reference_id = _required_text(
            "sync_reference_id", self.sync_reference_id
        )
        self.entity_type = _required_text("entity_type", self.entity_type)
        self.entity_id = _required_text("entity_id", self.entity_id)
        self.operation = _normalize_enum(self.operation, QuickBooksSyncOperation)
        self.idempotency_key = _optional_text(self.idempotency_key)
        self.external_id = _optional_text(self.external_id)
        self.direction = _normalize_enum(self.direction, QuickBooksSyncDirection)
        self.status = _normalize_enum(self.status, QuickBooksSyncStatus)
        self.retry_eligible = _optional_bool(self.retry_eligible, default=False)
        self.attempt_count = int(self.attempt_count)
        if self.attempt_count < 0:
            raise ValueError("attempt_count cannot be negative")
        self.last_attempted_at = _optional_text(self.last_attempted_at)
        self.last_synced_at = _optional_text(self.last_synced_at)
        self.last_error_code = _optional_text(self.last_error_code)
        self.last_error_message = _optional_text(self.last_error_message)
        self.notes = [_required_text("note", note) for note in list(self.notes)]

    def mark_not_ready(self, reason: str | None = None) -> None:
        self.status = QuickBooksSyncStatus.NOT_READY
        self.retry_eligible = False
        self.last_error_code = None
        self.last_error_message = _optional_text(reason)

    def mark_pending(
        self,
        *,
        idempotency_key: str | None = None,
        operation: QuickBooksSyncOperation | str | None = None,
        retry_eligible: bool = True,
    ) -> None:
        if idempotency_key is not None:
            self.idempotency_key = _required_text("idempotency_key", idempotency_key)
        if operation is not None:
            self.operation = _normalize_enum(operation, QuickBooksSyncOperation)
        self.status = QuickBooksSyncStatus.PENDING
        self.retry_eligible = _optional_bool(retry_eligible, default=True)
        self.attempt_count += 1
        self.last_attempted_at = _utc_now()
        self.last_error_code = None
        self.last_error_message = None

    def mark_in_progress(
        self,
        *,
        idempotency_key: str | None = None,
        operation: QuickBooksSyncOperation | str | None = None,
    ) -> None:
        if idempotency_key is not None:
            self.idempotency_key = _required_text("idempotency_key", idempotency_key)
        if operation is not None:
            self.operation = _normalize_enum(operation, QuickBooksSyncOperation)
        self.status = QuickBooksSyncStatus.IN_PROGRESS
        self.last_attempted_at = _utc_now()

    def mark_synced(
        self,
        external_id: str | None = None,
        *,
        idempotency_key: str | None = None,
        operation: QuickBooksSyncOperation | str | None = None,
    ) -> None:
        if idempotency_key is not None:
            self.idempotency_key = _required_text("idempotency_key", idempotency_key)
        if operation is not None:
            self.operation = _normalize_enum(operation, QuickBooksSyncOperation)
        if external_id is not None:
            self.external_id = _required_text("external_id", external_id)
        self.status = QuickBooksSyncStatus.SYNCED
        self.retry_eligible = False
        self.last_attempted_at = _utc_now()
        self.last_synced_at = _utc_now()
        self.last_error_code = None
        self.last_error_message = None

    def mark_failed(
        self,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
        retry_eligible: bool = True,
        idempotency_key: str | None = None,
        operation: QuickBooksSyncOperation | str | None = None,
    ) -> None:
        if idempotency_key is not None:
            self.idempotency_key = _required_text("idempotency_key", idempotency_key)
        if operation is not None:
            self.operation = _normalize_enum(operation, QuickBooksSyncOperation)
        self.status = QuickBooksSyncStatus.FAILED
        self.retry_eligible = _optional_bool(retry_eligible, default=True)
        self.last_attempted_at = _utc_now()
        self.last_error_code = _optional_text(error_code)
        self.last_error_message = _optional_text(error_message)

    def mark_skipped(
        self,
        *,
        reason: str | None = None,
        retry_eligible: bool = False,
        idempotency_key: str | None = None,
        operation: QuickBooksSyncOperation | str | None = None,
    ) -> None:
        if idempotency_key is not None:
            self.idempotency_key = _required_text("idempotency_key", idempotency_key)
        if operation is not None:
            self.operation = _normalize_enum(operation, QuickBooksSyncOperation)
        self.status = QuickBooksSyncStatus.SKIPPED
        self.retry_eligible = _optional_bool(retry_eligible, default=False)
        self.last_attempted_at = _utc_now()
        self.last_error_code = None
        self.last_error_message = _optional_text(reason)

    def can_retry(self) -> bool:
        return self.retry_eligible and self.status in {
            QuickBooksSyncStatus.FAILED,
            QuickBooksSyncStatus.SKIPPED,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "sync_reference_id": self.sync_reference_id,
                "entity_type": self.entity_type,
                "entity_id": self.entity_id,
                "operation": self.operation.value,
                "idempotency_key": self.idempotency_key,
                "external_id": self.external_id,
                "direction": self.direction.value,
                "status": self.status.value,
                "retry_eligible": self.retry_eligible,
                "attempt_count": self.attempt_count,
                "last_attempted_at": self.last_attempted_at,
                "last_synced_at": self.last_synced_at,
                "last_error_code": self.last_error_code,
                "last_error_message": self.last_error_message,
                "notes": list(self.notes),
            }
        )
        return payload


@dataclass
class CustomerInvoice(CommercialRecordBase):
    customer_invoice_id: str = ""
    customer_id: str = ""
    customer_name: str = ""
    estimate_id: str | None = None
    sales_order_id: str | None = None
    change_order_id: str | None = None
    project_job_link: ProjectJobLink | None = None
    status: CustomerInvoiceStatus = CustomerInvoiceStatus.DRAFT
    line_items: list[CustomerInvoiceLineItem] = field(default_factory=list)
    issued_at: str | None = None
    due_at: str | None = None
    quickbooks_sync_reference: QuickBooksSyncReference | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.customer_invoice_id = _required_text(
            "customer_invoice_id", self.customer_invoice_id
        )
        self.customer_id = _required_text("customer_id", self.customer_id)
        self.customer_name = _required_text("customer_name", self.customer_name)
        self.estimate_id = _optional_text(self.estimate_id)
        self.sales_order_id = _optional_text(self.sales_order_id)
        self.change_order_id = _optional_text(self.change_order_id)
        if self.project_job_link is not None and not isinstance(
            self.project_job_link, ProjectJobLink
        ):
            self.project_job_link = ProjectJobLink(**self.project_job_link)
        self.status = _normalize_enum(self.status, CustomerInvoiceStatus)
        self.line_items = [
            (
                item
                if isinstance(item, CustomerInvoiceLineItem)
                else CustomerInvoiceLineItem(**item)
            )
            for item in list(self.line_items)
        ]
        self.issued_at = _optional_text(self.issued_at)
        self.due_at = _optional_text(self.due_at)
        if self.quickbooks_sync_reference is not None and not isinstance(
            self.quickbooks_sync_reference, QuickBooksSyncReference
        ):
            self.quickbooks_sync_reference = QuickBooksSyncReference(
                **self.quickbooks_sync_reference
            )
        self.notes = [_required_text("note", note) for note in list(self.notes)]

    def issue(self) -> None:
        if self.status not in {
            CustomerInvoiceStatus.DRAFT,
            CustomerInvoiceStatus.READY,
        }:
            raise ValueError("customer invoice can only be issued from draft or ready")
        self.status = CustomerInvoiceStatus.ISSUED
        self.issued_at = _utc_now()

    def void(self) -> None:
        self.status = CustomerInvoiceStatus.VOIDED

    def mark_sync_pending(self) -> None:
        self._ensure_quickbooks_sync_reference().mark_pending()

    def mark_sync_synced(self, external_id: str | None = None) -> None:
        self._ensure_quickbooks_sync_reference().mark_synced(external_id)

    def mark_sync_failed(
        self,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self._ensure_quickbooks_sync_reference().mark_failed(
            error_code=error_code,
            error_message=error_message,
        )

    def _ensure_quickbooks_sync_reference(self) -> QuickBooksSyncReference:
        if self.quickbooks_sync_reference is None:
            self.quickbooks_sync_reference = QuickBooksSyncReference(
                tenant_id=self.tenant_id,
                organization_id=self.organization_id,
                sync_reference_id=f"customer-invoice-sync:{self.customer_invoice_id}",
                entity_type="customer_invoice",
                entity_id=self.customer_invoice_id,
            )
        return self.quickbooks_sync_reference

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "customer_invoice_id": self.customer_invoice_id,
                "customer_id": self.customer_id,
                "customer_name": self.customer_name,
                "estimate_id": self.estimate_id,
                "sales_order_id": self.sales_order_id,
                "change_order_id": self.change_order_id,
                "project_job_link": _serialize_value(self.project_job_link),
                "status": self.status.value,
                "line_items": [item.to_dict() for item in self.line_items],
                "issued_at": self.issued_at,
                "due_at": self.due_at,
                "quickbooks_sync_reference": _serialize_value(
                    self.quickbooks_sync_reference
                ),
                "notes": list(self.notes),
            }
        )
        return payload


@dataclass
class VendorBill(CommercialRecordBase):
    vendor_bill_id: str = ""
    vendor_id: str = ""
    vendor_name: str = ""
    purchase_order_id: str | None = None
    procurement_need_id: str | None = None
    project_job_link: ProjectJobLink | None = None
    status: VendorBillStatus = VendorBillStatus.DRAFT
    line_items: list[VendorBillLineItem] = field(default_factory=list)
    entered_at: str | None = None
    due_at: str | None = None
    quickbooks_sync_reference: QuickBooksSyncReference | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.vendor_bill_id = _required_text("vendor_bill_id", self.vendor_bill_id)
        self.vendor_id = _required_text("vendor_id", self.vendor_id)
        self.vendor_name = _required_text("vendor_name", self.vendor_name)
        self.purchase_order_id = _optional_text(self.purchase_order_id)
        self.procurement_need_id = _optional_text(self.procurement_need_id)
        if self.project_job_link is not None and not isinstance(
            self.project_job_link, ProjectJobLink
        ):
            self.project_job_link = ProjectJobLink(**self.project_job_link)
        self.status = _normalize_enum(self.status, VendorBillStatus)
        self.line_items = [
            item if isinstance(item, VendorBillLineItem) else VendorBillLineItem(**item)
            for item in list(self.line_items)
        ]
        self.entered_at = _optional_text(self.entered_at)
        self.due_at = _optional_text(self.due_at)
        if self.quickbooks_sync_reference is not None and not isinstance(
            self.quickbooks_sync_reference, QuickBooksSyncReference
        ):
            self.quickbooks_sync_reference = QuickBooksSyncReference(
                **self.quickbooks_sync_reference
            )
        self.notes = [_required_text("note", note) for note in list(self.notes)]

    def issue(self) -> None:
        if self.status not in {VendorBillStatus.DRAFT, VendorBillStatus.READY}:
            raise ValueError("vendor bill can only be entered from draft or ready")
        self.status = VendorBillStatus.ENTERED
        self.entered_at = _utc_now()

    def void(self) -> None:
        self.status = VendorBillStatus.VOIDED

    def mark_sync_pending(self) -> None:
        self._ensure_quickbooks_sync_reference().mark_pending()

    def mark_sync_synced(self, external_id: str | None = None) -> None:
        self._ensure_quickbooks_sync_reference().mark_synced(external_id)

    def mark_sync_failed(
        self,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self._ensure_quickbooks_sync_reference().mark_failed(
            error_code=error_code,
            error_message=error_message,
        )

    def _ensure_quickbooks_sync_reference(self) -> QuickBooksSyncReference:
        if self.quickbooks_sync_reference is None:
            self.quickbooks_sync_reference = QuickBooksSyncReference(
                tenant_id=self.tenant_id,
                organization_id=self.organization_id,
                sync_reference_id=f"vendor-bill-sync:{self.vendor_bill_id}",
                entity_type="vendor_bill",
                entity_id=self.vendor_bill_id,
            )
        return self.quickbooks_sync_reference

    def to_dict(self) -> dict[str, Any]:
        payload = self._scope_dict()
        payload.update(
            {
                "vendor_bill_id": self.vendor_bill_id,
                "vendor_id": self.vendor_id,
                "vendor_name": self.vendor_name,
                "purchase_order_id": self.purchase_order_id,
                "procurement_need_id": self.procurement_need_id,
                "project_job_link": _serialize_value(self.project_job_link),
                "status": self.status.value,
                "line_items": [item.to_dict() for item in self.line_items],
                "entered_at": self.entered_at,
                "due_at": self.due_at,
                "quickbooks_sync_reference": _serialize_value(
                    self.quickbooks_sync_reference
                ),
                "notes": list(self.notes),
            }
        )
        return payload


__all__ = [
    "CustomerAccount",
    "Opportunity",
    "OpportunityStatus",
    "ProjectJobLink",
    "VendorManufacturerReference",
    "CatalogItem",
    "CommercialLineItemBase",
    "EstimateLineItem",
    "SalesOrderLineItem",
    "Estimate",
    "Proposal",
    "ProposalStatus",
    "SalesOrder",
    "SalesOrderStatus",
    "ChangeOrder",
    "ChangeOrderStatus",
    "ChangeOrderDirection",
    "InventoryLocation",
    "InventoryPosition",
    "InventoryReservation",
    "InventoryReservationStatus",
    "ProcurementNeed",
    "ProcurementNeedStatus",
    "CustomerInvoiceLineItem",
    "VendorBillLineItem",
    "CustomerInvoiceStatus",
    "VendorBillStatus",
    "CustomerInvoice",
    "VendorBill",
    "QuickBooksSyncOperation",
    "QuickBooksSyncReference",
    "QuickBooksSyncTask",
    "QuickBooksSyncDirection",
    "QuickBooksSyncStatus",
]

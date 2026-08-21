"""Tenant-scoped commercial reporting read models for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Protocol

from atlas_core.contracts.commercial_spine_contracts import (
    CustomerInvoice,
    Estimate,
    QuickBooksSyncStatus,
    SalesOrder,
    VendorBill,
)

if TYPE_CHECKING:
    from atlas_core.repository.contracts import RepositoryBundle


ZERO = Decimal("0")
UNCONVERTED_STAGE = "unconverted"
PROPOSAL_LINKED_STAGE = "proposal_linked"
SALES_ORDER_LINKED_STAGE = "sales_order_linked"
INVOICED_STAGE = "invoiced"
BACKLOG_STATUSES = {"draft", "open", "partially_fulfilled"}


class PricedLineItem(Protocol):
    quantity: Decimal
    unit_price: Decimal


@dataclass
class CommercialCountSummary:
    total_count: int = 0
    counts_by_status: dict[str, int] = field(default_factory=dict)


@dataclass
class CommercialMonetaryStatusSummary:
    total_count: int = 0
    counts_by_status: dict[str, int] = field(default_factory=dict)
    totals_by_status: dict[str, Decimal] = field(default_factory=dict)
    total_amount: Decimal = ZERO
    backlog_count: int = 0
    backlog_amount: Decimal = ZERO


@dataclass
class CommercialQuantityStatusSummary:
    total_count: int = 0
    counts_by_status: dict[str, int] = field(default_factory=dict)
    quantities_by_status: dict[str, Decimal] = field(default_factory=dict)
    total_quantity: Decimal = ZERO


CommercialProcurementNeedSummary = CommercialQuantityStatusSummary


@dataclass
class CommercialEstimatePipelineSummary:
    total_estimates: int = 0
    counts_by_stage: dict[str, int] = field(default_factory=dict)
    totals_by_stage: dict[str, Decimal] = field(default_factory=dict)
    total_estimate_value: Decimal = ZERO


@dataclass
class CommercialInventoryAvailabilityRow:
    catalog_item_id: str
    location_id: str
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal


@dataclass
class CommercialInventoryAvailabilitySummary:
    total_positions: int = 0
    total_on_hand: Decimal = ZERO
    total_reserved: Decimal = ZERO
    total_available: Decimal = ZERO
    rows: list[CommercialInventoryAvailabilityRow] = field(default_factory=list)


@dataclass
class CommercialQuickBooksSyncSummary:
    total_references: int = 0
    counts_by_status: dict[str, int] = field(default_factory=dict)
    counts_by_entity_type: dict[str, int] = field(default_factory=dict)
    counts_by_entity_type_and_status: dict[str, dict[str, int]] = field(
        default_factory=dict
    )


@dataclass
class CommercialReportingSnapshot:
    estimate_pipeline: CommercialEstimatePipelineSummary
    proposal_statuses: CommercialCountSummary
    sales_order_backlog: CommercialMonetaryStatusSummary
    invoice_statuses: CommercialMonetaryStatusSummary
    vendor_bill_statuses: CommercialMonetaryStatusSummary
    inventory_availability: CommercialInventoryAvailabilitySummary
    procurement_needs: CommercialProcurementNeedSummary
    quickbooks_sync: CommercialQuickBooksSyncSummary


class CommercialReportingService:
    """Tenant-scoped commercial reporting read models."""

    def __init__(self, repositories: "RepositoryBundle") -> None:
        if repositories.commercial_repository is None:
            raise ValueError("commercial repository is required for reporting")
        self.repositories = repositories
        self.commercial_repository = repositories.commercial_repository
        if repositories.tenant_id is None:
            raise ValueError("tenant_id is required for reporting")
        self.tenant_id = repositories.tenant_id

    def estimate_pipeline_summary(
        self,
        *,
        organization_id: str | None = None,
    ) -> CommercialEstimatePipelineSummary:
        estimates = self._filter_records(
            self.commercial_repository.list_estimates(),
            organization_id=organization_id,
        )
        proposals_by_estimate_id = {
            proposal.estimate_id: proposal
            for proposal in self._filter_records(
                self.commercial_repository.list_proposals(),
                organization_id=organization_id,
            )
        }
        sales_orders = self._filter_records(
            self.commercial_repository.list_sales_orders(),
            organization_id=organization_id,
        )
        sales_orders_by_estimate_id = {
            sales_order.estimate_id: sales_order
            for sales_order in sales_orders
            if sales_order.estimate_id is not None
        }
        invoiced_estimate_ids = self._estimate_ids_with_invoices(
            organization_id=organization_id,
        )

        counts_by_stage: dict[str, int] = {}
        totals_by_stage: dict[str, Decimal] = {}
        total_estimate_value = ZERO
        for estimate in estimates:
            stage = self._estimate_stage(
                estimate,
                proposals_by_estimate_id=proposals_by_estimate_id,
                sales_orders_by_estimate_id=sales_orders_by_estimate_id,
                invoiced_estimate_ids=invoiced_estimate_ids,
            )
            amount = self._calculate_line_items_total(estimate.line_items)
            counts_by_stage[stage] = counts_by_stage.get(stage, 0) + 1
            totals_by_stage[stage] = totals_by_stage.get(stage, ZERO) + amount
            total_estimate_value += amount

        return CommercialEstimatePipelineSummary(
            total_estimates=len(estimates),
            counts_by_stage=self._sorted_int_dict(counts_by_stage),
            totals_by_stage=self._sorted_decimal_dict(totals_by_stage),
            total_estimate_value=total_estimate_value,
        )

    def proposal_status_summary(
        self,
        *,
        organization_id: str | None = None,
    ) -> CommercialCountSummary:
        proposals = self._filter_records(
            self.commercial_repository.list_proposals(),
            organization_id=organization_id,
        )
        return CommercialCountSummary(
            total_count=len(proposals),
            counts_by_status=self._count_by_status(proposals),
        )

    def sales_order_backlog_summary(
        self,
        *,
        organization_id: str | None = None,
    ) -> CommercialMonetaryStatusSummary:
        sales_orders = self._filter_records(
            self.commercial_repository.list_sales_orders(),
            organization_id=organization_id,
        )
        return self._monetary_status_summary(
            sales_orders,
            backlog_statuses=BACKLOG_STATUSES,
        )

    def invoice_status_summary(
        self,
        *,
        organization_id: str | None = None,
    ) -> CommercialMonetaryStatusSummary:
        invoices = self._filter_records(
            self.commercial_repository.list_customer_invoices(),
            organization_id=organization_id,
        )
        return self._monetary_status_summary(invoices)

    def vendor_bill_status_summary(
        self,
        *,
        organization_id: str | None = None,
    ) -> CommercialMonetaryStatusSummary:
        vendor_bills = self._filter_records(
            self.commercial_repository.list_vendor_bills(),
            organization_id=organization_id,
        )
        return self._monetary_status_summary(vendor_bills)

    def inventory_availability_summary(
        self,
        *,
        organization_id: str | None = None,
    ) -> CommercialInventoryAvailabilitySummary:
        positions = self._filter_records(
            self.commercial_repository.list_inventory_positions(),
            organization_id=organization_id,
        )
        rows = [
            CommercialInventoryAvailabilityRow(
                catalog_item_id=position.catalog_item_id,
                location_id=position.location_id,
                quantity_on_hand=position.quantity_on_hand,
                quantity_reserved=position.quantity_reserved,
                quantity_available=position.quantity_available,
            )
            for position in sorted(
                positions,
                key=lambda item: (
                    item.catalog_item_id,
                    item.location_id,
                    item.position_id,
                ),
            )
        ]
        total_on_hand = sum((row.quantity_on_hand for row in rows), ZERO)
        total_reserved = sum((row.quantity_reserved for row in rows), ZERO)
        total_available = sum((row.quantity_available for row in rows), ZERO)
        return CommercialInventoryAvailabilitySummary(
            total_positions=len(rows),
            total_on_hand=total_on_hand,
            total_reserved=total_reserved,
            total_available=total_available,
            rows=rows,
        )

    def procurement_need_summary(
        self,
        *,
        organization_id: str | None = None,
    ) -> CommercialProcurementNeedSummary:
        procurement_needs = self._filter_records(
            self.commercial_repository.list_procurement_needs(),
            organization_id=organization_id,
        )
        counts_by_status: dict[str, int] = {}
        quantities_by_status: dict[str, Decimal] = {}
        total_quantity = ZERO
        for procurement_need in procurement_needs:
            status = self._status_label(procurement_need.status)
            counts_by_status[status] = counts_by_status.get(status, 0) + 1
            quantities_by_status[status] = quantities_by_status.get(status, ZERO) + (
                procurement_need.quantity_required
            )
            total_quantity += procurement_need.quantity_required
        return CommercialProcurementNeedSummary(
            total_count=len(procurement_needs),
            counts_by_status=self._sorted_int_dict(counts_by_status),
            quantities_by_status=self._sorted_decimal_dict(quantities_by_status),
            total_quantity=total_quantity,
        )

    def quickbooks_sync_summary(
        self,
        *,
        organization_id: str | None = None,
    ) -> CommercialQuickBooksSyncSummary:
        counts_by_status: dict[str, int] = {}
        counts_by_entity_type: dict[str, int] = {}
        counts_by_entity_type_and_status: dict[str, dict[str, int]] = {}

        for entity_type, record in self._iter_sync_records(
            organization_id=organization_id,
        ):
            sync_status = self._sync_status_for_record(record)
            counts_by_status[sync_status] = counts_by_status.get(sync_status, 0) + 1
            counts_by_entity_type[entity_type] = (
                counts_by_entity_type.get(entity_type, 0) + 1
            )
            entity_counts = counts_by_entity_type_and_status.setdefault(entity_type, {})
            entity_counts[sync_status] = entity_counts.get(sync_status, 0) + 1

        return CommercialQuickBooksSyncSummary(
            total_references=sum(counts_by_entity_type.values()),
            counts_by_status=self._sorted_int_dict(counts_by_status),
            counts_by_entity_type=self._sorted_int_dict(counts_by_entity_type),
            counts_by_entity_type_and_status={
                entity_type: self._sorted_int_dict(status_counts)
                for entity_type, status_counts in sorted(
                    counts_by_entity_type_and_status.items()
                )
            },
        )

    def build_commercial_reporting_snapshot(
        self,
        *,
        organization_id: str | None = None,
    ) -> CommercialReportingSnapshot:
        return CommercialReportingSnapshot(
            estimate_pipeline=self.estimate_pipeline_summary(
                organization_id=organization_id
            ),
            proposal_statuses=self.proposal_status_summary(
                organization_id=organization_id
            ),
            sales_order_backlog=self.sales_order_backlog_summary(
                organization_id=organization_id
            ),
            invoice_statuses=self.invoice_status_summary(
                organization_id=organization_id
            ),
            vendor_bill_statuses=self.vendor_bill_status_summary(
                organization_id=organization_id
            ),
            inventory_availability=self.inventory_availability_summary(
                organization_id=organization_id
            ),
            procurement_needs=self.procurement_need_summary(
                organization_id=organization_id
            ),
            quickbooks_sync=self.quickbooks_sync_summary(
                organization_id=organization_id
            ),
        )

    def _estimate_stage(
        self,
        estimate: Estimate,
        *,
        proposals_by_estimate_id: dict[str, Any],
        sales_orders_by_estimate_id: dict[str, SalesOrder],
        invoiced_estimate_ids: set[str],
    ) -> str:
        if estimate.estimate_id in invoiced_estimate_ids:
            return INVOICED_STAGE
        if estimate.estimate_id in sales_orders_by_estimate_id:
            return SALES_ORDER_LINKED_STAGE
        if (
            estimate.proposal_id is not None
            or estimate.estimate_id in proposals_by_estimate_id
        ):
            return PROPOSAL_LINKED_STAGE
        return UNCONVERTED_STAGE

    def _estimate_ids_with_invoices(
        self,
        *,
        organization_id: str | None,
    ) -> set[str]:
        sales_orders_by_id = {
            sales_order.sales_order_id: sales_order
            for sales_order in self._filter_records(
                self.commercial_repository.list_sales_orders(),
                organization_id=organization_id,
            )
        }
        estimate_ids: set[str] = set()
        for invoice in self._filter_records(
            self.commercial_repository.list_customer_invoices(),
            organization_id=organization_id,
        ):
            estimate_id = invoice.estimate_id
            if estimate_id is None and invoice.sales_order_id is not None:
                sales_order = sales_orders_by_id.get(invoice.sales_order_id)
                if sales_order is not None:
                    estimate_id = sales_order.estimate_id
            if estimate_id is not None:
                estimate_ids.add(estimate_id)
        return estimate_ids

    def _monetary_status_summary(
        self,
        records: list[Any],
        *,
        backlog_statuses: set[str] | None = None,
    ) -> CommercialMonetaryStatusSummary:
        counts_by_status: dict[str, int] = {}
        totals_by_status: dict[str, Decimal] = {}
        total_amount = ZERO
        backlog_count = 0
        backlog_amount = ZERO
        for record in records:
            status = self._status_label(record.status)
            amount = self._calculate_line_items_total(record.line_items)
            counts_by_status[status] = counts_by_status.get(status, 0) + 1
            totals_by_status[status] = totals_by_status.get(status, ZERO) + amount
            total_amount += amount
            if backlog_statuses is not None and status in backlog_statuses:
                backlog_count += 1
                backlog_amount += amount
        return CommercialMonetaryStatusSummary(
            total_count=len(records),
            counts_by_status=self._sorted_int_dict(counts_by_status),
            totals_by_status=self._sorted_decimal_dict(totals_by_status),
            total_amount=total_amount,
            backlog_count=backlog_count,
            backlog_amount=backlog_amount,
        )

    def _iter_sync_records(
        self,
        *,
        organization_id: str | None,
    ) -> list[tuple[str, CustomerInvoice | VendorBill]]:
        records: list[tuple[str, CustomerInvoice | VendorBill]] = []
        for invoice in self._filter_records(
            self.commercial_repository.list_customer_invoices(),
            organization_id=organization_id,
        ):
            records.append(("customer_invoice", invoice))
        for vendor_bill in self._filter_records(
            self.commercial_repository.list_vendor_bills(),
            organization_id=organization_id,
        ):
            records.append(("vendor_bill", vendor_bill))
        return records

    def _sync_status_for_record(self, record: CustomerInvoice | VendorBill) -> str:
        sync_reference = record.quickbooks_sync_reference
        if sync_reference is None:
            return QuickBooksSyncStatus.NOT_SYNCED.value
        return sync_reference.status.value

    def _calculate_line_items_total(
        self,
        line_items: list[PricedLineItem],
    ) -> Decimal:
        total = ZERO
        for line_item in line_items:
            total += line_item.quantity * line_item.unit_price
        return total

    def _status_label(self, value: Any) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    def _count_by_status(self, records: list[Any]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in records:
            status = self._status_label(record.status)
            counts[status] = counts.get(status, 0) + 1
        return self._sorted_int_dict(counts)

    def _filter_records(
        self,
        records: list[Any],
        *,
        organization_id: str | None,
    ) -> list[Any]:
        filtered: list[Any] = []
        for record in records:
            if record.tenant_id != self.tenant_id:
                continue
            if (
                organization_id is not None
                and record.organization_id != organization_id
            ):
                continue
            filtered.append(record)
        return filtered

    def _sorted_int_dict(self, values: dict[str, int]) -> dict[str, int]:
        return dict(sorted(values.items()))

    def _sorted_decimal_dict(self, values: dict[str, Decimal]) -> dict[str, Decimal]:
        return dict(sorted(values.items()))


__all__ = [
    "CommercialCountSummary",
    "CommercialEstimatePipelineSummary",
    "CommercialInventoryAvailabilityRow",
    "CommercialInventoryAvailabilitySummary",
    "CommercialMonetaryStatusSummary",
    "CommercialProcurementNeedSummary",
    "CommercialQuantityStatusSummary",
    "CommercialQuickBooksSyncSummary",
    "CommercialReportingService",
    "CommercialReportingSnapshot",
]

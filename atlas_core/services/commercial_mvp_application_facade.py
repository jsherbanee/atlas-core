"""Tenant-scoped commercial MVP application facade for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from atlas_core.contracts.commercial_spine_contracts import (
    CustomerAccount,
    CustomerInvoice,
    Estimate,
    InventoryReservation,
    Opportunity,
    Proposal,
    SalesOrder,
    SalesOrderLineItem,
    VendorBill,
)
from atlas_core.services.commercial_customer_opportunity_estimate_service import (
    CommercialCustomerOpportunityEstimateService,
)
from atlas_core.services.commercial_invoice_vendor_bill_service import (
    CommercialInvoiceVendorBillService,
)
from atlas_core.services.commercial_proposal_sales_order_service import (
    CommercialProposalSalesOrderWorkflowService,
)
from atlas_core.services.commercial_quickbooks_sync_service import (
    CommercialQuickBooksSyncService,
)
from atlas_core.services.commercial_reporting_service import (
    CommercialReportingService,
    CommercialReportingSnapshot,
)
from atlas_core.services.inventory_service import InventoryService

if TYPE_CHECKING:
    from atlas_core.repository.contracts import RepositoryBundle


@dataclass(frozen=True)
class CommercialSalesOrderInventoryAvailability:
    sales_order_id: str
    sales_order_line_item_id: str
    catalog_item_id: str | None
    requested_quantity: Decimal
    available_quantity: Decimal
    selected_location_id: str | None
    selected_position_id: str | None
    can_reserve: bool


class CommercialMvpApplicationFacade:
    """Tenant-scoped application facade for future commercial UI/API layers."""

    def __init__(self, repositories: "RepositoryBundle") -> None:
        if repositories.tenant_id is None or repositories.tenant_root is None:
            raise ValueError("tenant-scoped repository bundle is required")
        self.repositories = repositories
        self.tenant_id = repositories.tenant_id
        self.tenant_root = repositories.tenant_root
        self.customer_opportunity_estimate_service = (
            CommercialCustomerOpportunityEstimateService(repositories)
        )
        self.proposal_sales_order_service = CommercialProposalSalesOrderWorkflowService(
            repositories
        )
        self.inventory_service = InventoryService(repositories)
        self.invoice_vendor_bill_service = CommercialInvoiceVendorBillService(
            repositories
        )
        self.reporting_service = CommercialReportingService(repositories)
        self.quickbooks_sync_service = CommercialQuickBooksSyncService(repositories)

    def create_customer_account(self, **kwargs: Any) -> CustomerAccount:
        return self.customer_opportunity_estimate_service.create_customer_account(
            **kwargs
        )

    def create_opportunity(self, **kwargs: Any) -> Opportunity:
        return self.customer_opportunity_estimate_service.create_opportunity(**kwargs)

    def list_customer_accounts(self, **kwargs: Any) -> list[CustomerAccount]:
        return self.customer_opportunity_estimate_service.list_customer_accounts(
            **kwargs
        )

    def list_opportunities(self, **kwargs: Any) -> list[Opportunity]:
        return self.customer_opportunity_estimate_service.list_opportunities(**kwargs)

    def create_estimate(self, **kwargs: Any) -> Estimate:
        return self.customer_opportunity_estimate_service.create_estimate(**kwargs)

    def list_estimates(self, **kwargs: Any) -> list[Estimate]:
        return self.customer_opportunity_estimate_service.list_estimates(**kwargs)

    def update_estimate(self, *args: Any, **kwargs: Any) -> Estimate:
        return self.customer_opportunity_estimate_service.update_estimate(
            *args, **kwargs
        )

    def add_estimate_line_item(self, *args: Any, **kwargs: Any) -> Estimate:
        return self.customer_opportunity_estimate_service.add_estimate_line_item(
            *args, **kwargs
        )

    def update_estimate_line_item(self, *args: Any, **kwargs: Any) -> Estimate:
        return self.customer_opportunity_estimate_service.update_estimate_line_item(
            *args, **kwargs
        )

    def remove_estimate_line_item(self, *args: Any, **kwargs: Any) -> Estimate:
        return self.customer_opportunity_estimate_service.remove_estimate_line_item(
            *args, **kwargs
        )

    def create_proposal_for_estimate(self, *args: Any, **kwargs: Any) -> Proposal:
        return self.proposal_sales_order_service.create_proposal_for_estimate(
            *args, **kwargs
        )

    def list_proposals(self, **kwargs: Any) -> list[Proposal]:
        return self.proposal_sales_order_service.list_proposals(**kwargs)

    def mark_proposal_ready(self, *args: Any, **kwargs: Any) -> Proposal:
        return self.proposal_sales_order_service.mark_proposal_ready(*args, **kwargs)

    def send_proposal(self, *args: Any, **kwargs: Any) -> Proposal:
        return self.proposal_sales_order_service.send_proposal(*args, **kwargs)

    def accept_proposal(self, *args: Any, **kwargs: Any) -> Proposal:
        return self.proposal_sales_order_service.accept_proposal(*args, **kwargs)

    def reject_proposal(self, *args: Any, **kwargs: Any) -> Proposal:
        return self.proposal_sales_order_service.reject_proposal(*args, **kwargs)

    def convert_accepted_estimate_to_sales_order(
        self, *args: Any, **kwargs: Any
    ) -> SalesOrder:
        return (
            self.proposal_sales_order_service.convert_accepted_estimate_to_sales_order(
                *args, **kwargs
            )
        )

    def list_sales_orders(self, **kwargs: Any) -> list[SalesOrder]:
        return self.proposal_sales_order_service.list_sales_orders(**kwargs)

    def check_inventory_availability_for_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
    ) -> list[CommercialSalesOrderInventoryAvailability]:
        sales_order = self._require_sales_order(
            sales_order_id,
            organization_id=organization_id,
        )
        return [
            self._build_sales_order_inventory_availability(
                sales_order,
                line_item,
                organization_id=organization_id or sales_order.organization_id,
            )
            for line_item in sales_order.line_items
        ]

    def reserve_inventory_for_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
    ) -> list[InventoryReservation]:
        sales_order = self._require_sales_order(
            sales_order_id,
            organization_id=organization_id,
        )
        target_organization_id = organization_id or sales_order.organization_id
        if target_organization_id is None:
            raise ValueError("sales order is not associated with an organization")
        reservations: list[InventoryReservation] = []
        availability_rows = self.check_inventory_availability_for_sales_order(
            sales_order_id,
            organization_id=organization_id,
        )

        for line_item, availability in zip(sales_order.line_items, availability_rows):
            if not availability.can_reserve:
                continue
            if line_item.catalog_item_id is None:
                continue
            if availability.selected_location_id is None:
                continue
            reservation_id = self._sales_order_reservation_id(
                sales_order.sales_order_id,
                line_item.line_item_id,
            )
            existing = self.inventory_service.get_inventory_reservation(
                reservation_id,
                organization_id=target_organization_id,
            )
            if existing is not None:
                reservations.append(existing)
                continue
            reservations.append(
                self.inventory_service.create_inventory_reservation(
                    organization_id=target_organization_id,
                    reservation_id=reservation_id,
                    catalog_item_id=line_item.catalog_item_id,
                    location_id=availability.selected_location_id,
                    quantity=line_item.quantity,
                    sales_order_line_item_id=line_item.line_item_id,
                    project_job_link=sales_order.project_job_link,
                )
            )

        return reservations

    def generate_customer_invoice_from_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
        customer_invoice_id: str | None = None,
        due_at: str | None = None,
        notes: list[str] | None = None,
    ) -> CustomerInvoice:
        return (
            self.invoice_vendor_bill_service.create_customer_invoice_from_sales_order(
                sales_order_id,
                organization_id=organization_id,
                customer_invoice_id=customer_invoice_id,
                due_at=due_at,
                notes=notes,
            )
        )

    def list_customer_invoices(self, **kwargs: Any) -> list[CustomerInvoice]:
        return self.invoice_vendor_bill_service.list_customer_invoices(**kwargs)

    def create_vendor_bill(self, **kwargs: Any) -> VendorBill:
        return self.invoice_vendor_bill_service.create_vendor_bill(**kwargs)

    def list_vendor_bills(self, **kwargs: Any) -> list[VendorBill]:
        return self.invoice_vendor_bill_service.list_vendor_bills(**kwargs)

    def mark_customer_invoice_sync_pending(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
    ) -> CustomerInvoice:
        return self.invoice_vendor_bill_service.mark_customer_invoice_sync_pending(
            customer_invoice_id,
            organization_id=organization_id,
        )

    def mark_vendor_bill_sync_pending(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
    ) -> VendorBill:
        return self.invoice_vendor_bill_service.mark_vendor_bill_sync_pending(
            vendor_bill_id,
            organization_id=organization_id,
        )

    def get_commercial_reporting_snapshot(
        self,
        *,
        organization_id: str | None = None,
    ) -> CommercialReportingSnapshot:
        return self.reporting_service.build_commercial_reporting_snapshot(
            organization_id=organization_id,
        )

    def _require_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None,
    ) -> SalesOrder:
        sales_order = self.proposal_sales_order_service.get_sales_order(
            sales_order_id,
            organization_id=organization_id,
        )
        if sales_order is None:
            raise ValueError("sales order was not found")
        return sales_order

    def _build_sales_order_inventory_availability(
        self,
        sales_order: SalesOrder,
        line_item: SalesOrderLineItem,
        *,
        organization_id: str | None,
    ) -> CommercialSalesOrderInventoryAvailability:
        position = self._select_inventory_position(
            line_item.catalog_item_id,
            organization_id=organization_id,
        )
        available_quantity = (
            position.quantity_available if position is not None else Decimal("0")
        )
        return CommercialSalesOrderInventoryAvailability(
            sales_order_id=sales_order.sales_order_id,
            sales_order_line_item_id=line_item.line_item_id,
            catalog_item_id=line_item.catalog_item_id,
            requested_quantity=line_item.quantity,
            available_quantity=available_quantity,
            selected_location_id=position.location_id if position is not None else None,
            selected_position_id=position.position_id if position is not None else None,
            can_reserve=position is not None
            and available_quantity >= line_item.quantity,
        )

    def _select_inventory_position(
        self,
        catalog_item_id: str | None,
        *,
        organization_id: str | None,
    ) -> Any:
        if catalog_item_id is None:
            return None
        positions = [
            position
            for position in self.inventory_service.list_inventory_positions(
                organization_id=organization_id,
            )
            if position.catalog_item_id == catalog_item_id
        ]
        if not positions:
            return None
        positions.sort(
            key=lambda position: (
                -position.quantity_available,
                position.location_id,
                position.position_id,
            )
        )
        return positions[0]

    @staticmethod
    def _sales_order_reservation_id(
        sales_order_id: str,
        line_item_id: str,
    ) -> str:
        return f"res-{sales_order_id}-{line_item_id}"


__all__ = [
    "CommercialMvpApplicationFacade",
    "CommercialSalesOrderInventoryAvailability",
]

"""Tenant-scoped customer invoice and vendor bill service for Atlas Core."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from atlas_core.contracts.commercial_spine_contracts import (
    CustomerInvoice,
    CustomerInvoiceLineItem,
    CustomerInvoiceStatus,
    ProcurementNeed,
    ProjectJobLink,
    QuickBooksSyncReference,
    SalesOrder,
    VendorBill,
    VendorBillLineItem,
    VendorBillStatus,
)
from atlas_core.services.commercial_proposal_sales_order_service import (
    CommercialProposalSalesOrderWorkflowService,
)

if TYPE_CHECKING:
    from atlas_core.repository.contracts import RepositoryBundle


_UNSET = object()


class CommercialInvoiceVendorBillService(CommercialProposalSalesOrderWorkflowService):
    """Tenant-scoped customer invoice and vendor bill workflow."""

    def __init__(self, repositories: "RepositoryBundle") -> None:
        super().__init__(repositories)

    def create_customer_invoice(
        self,
        *,
        organization_id: str,
        customer_invoice_id: str,
        customer_id: str,
        customer_name: str | None = None,
        estimate_id: str | None = None,
        sales_order_id: str | None = None,
        change_order_id: str | None = None,
        project_job_link: ProjectJobLink | dict[str, Any] | None = None,
        line_items: Sequence[CustomerInvoiceLineItem | dict[str, Any]] | None = None,
        status: CustomerInvoiceStatus = CustomerInvoiceStatus.DRAFT,
        issued_at: str | None = None,
        due_at: str | None = None,
        quickbooks_sync_reference: (
            QuickBooksSyncReference | dict[str, Any] | None
        ) = None,
        notes: list[str] | None = None,
    ) -> CustomerInvoice:
        customer = self._require_customer_account(
            customer_id,
            organization_id=organization_id,
        )
        if customer_name is None:
            customer_name = customer.name
        if sales_order_id is not None:
            sales_order = self._require_sales_order(
                sales_order_id,
                organization_id=organization_id,
            )
            if sales_order.customer_id != customer.customer_id:
                raise ValueError("sales order does not belong to the selected customer")
            self._ensure_no_existing_invoice_for_sales_order(
                sales_order.sales_order_id,
                organization_id=organization_id,
            )
        if estimate_id is not None:
            estimate = self._require_estimate(
                estimate_id,
                organization_id=organization_id,
            )
            if estimate.customer_id != customer.customer_id:
                raise ValueError("estimate does not belong to the selected customer")
        if (
            self.get_customer_invoice(
                customer_invoice_id, organization_id=organization_id
            )
            is not None
        ):
            raise ValueError("customer invoice already exists")
        record = CustomerInvoice(
            tenant_id=self.tenant_id,
            organization_id=organization_id,
            customer_invoice_id=customer_invoice_id,
            customer_id=customer.customer_id,
            customer_name=customer_name,
            estimate_id=estimate_id,
            sales_order_id=sales_order_id,
            change_order_id=change_order_id,
            project_job_link=self._normalize_project_job_link(project_job_link),
            status=status,
            line_items=[
                self._normalize_customer_invoice_line_item(item)
                for item in list(line_items or [])
            ],
            issued_at=issued_at,
            due_at=due_at,
            quickbooks_sync_reference=self._normalize_quickbooks_sync_reference(
                quickbooks_sync_reference
            ),
            notes=list(notes or []),
        )
        self.commercial_repository.save_customer_invoice(record)
        return record

    def create_customer_invoice_from_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None = None,
        customer_invoice_id: str | None = None,
        due_at: str | None = None,
        notes: list[str] | None = None,
    ) -> CustomerInvoice:
        sales_order = self._require_sales_order(
            sales_order_id,
            organization_id=organization_id,
        )
        if sales_order.organization_id is None:
            raise ValueError("sales order is not associated with an organization")
        customer = self._require_customer_account(
            sales_order.customer_id,
            organization_id=sales_order.organization_id,
        )
        customer_invoice_id = customer_invoice_id or f"ci-{sales_order.sales_order_id}"
        self._ensure_no_existing_invoice_for_sales_order(
            sales_order.sales_order_id,
            organization_id=sales_order.organization_id,
        )
        line_items = [
            CustomerInvoiceLineItem(
                line_item_id=line_item.line_item_id,
                description=line_item.description,
                quantity=line_item.quantity,
                unit_price=line_item.unit_price,
                catalog_item_id=line_item.catalog_item_id,
                notes=list(line_item.notes),
                sales_order_line_item_id=line_item.line_item_id,
                change_order_id=line_item.change_order_id,
            )
            for line_item in sales_order.line_items
        ]
        return self.create_customer_invoice(
            organization_id=sales_order.organization_id,
            customer_invoice_id=customer_invoice_id,
            customer_id=customer.customer_id,
            customer_name=customer.name,
            estimate_id=sales_order.estimate_id,
            sales_order_id=sales_order.sales_order_id,
            project_job_link=sales_order.project_job_link,
            line_items=line_items,
            status=CustomerInvoiceStatus.DRAFT,
            due_at=due_at,
            notes=list(sales_order.notes if notes is None else notes),
        )

    def update_customer_invoice(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
        customer_id: Any = _UNSET,
        customer_name: Any = _UNSET,
        estimate_id: Any = _UNSET,
        sales_order_id: Any = _UNSET,
        change_order_id: Any = _UNSET,
        project_job_link: Any = _UNSET,
        line_items: Any = _UNSET,
        status: Any = _UNSET,
        issued_at: Any = _UNSET,
        due_at: Any = _UNSET,
        quickbooks_sync_reference: Any = _UNSET,
        notes: Any = _UNSET,
    ) -> CustomerInvoice:
        invoice = self.get_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        if invoice is None:
            raise ValueError("customer invoice was not found")
        payload = invoice.to_dict()
        if customer_id is not _UNSET:
            payload["customer_id"] = customer_id
        if customer_name is not _UNSET:
            payload["customer_name"] = customer_name
        if estimate_id is not _UNSET:
            payload["estimate_id"] = estimate_id
        if sales_order_id is not _UNSET:
            payload["sales_order_id"] = sales_order_id
        if change_order_id is not _UNSET:
            payload["change_order_id"] = change_order_id
        if project_job_link is not _UNSET:
            payload["project_job_link"] = self._normalize_project_job_link(
                project_job_link
            )
        if line_items is not _UNSET:
            payload["line_items"] = [
                self._normalize_customer_invoice_line_item(item).to_dict()
                for item in list(line_items or [])
            ]
        if status is not _UNSET:
            payload["status"] = status.value if hasattr(status, "value") else status
        if issued_at is not _UNSET:
            payload["issued_at"] = issued_at
        if due_at is not _UNSET:
            payload["due_at"] = due_at
        if quickbooks_sync_reference is not _UNSET:
            payload["quickbooks_sync_reference"] = (
                self._normalize_quickbooks_sync_reference(quickbooks_sync_reference)
            )
        if notes is not _UNSET:
            payload["notes"] = list(notes or [])
        updated = CustomerInvoice(**payload)
        self.commercial_repository.save_customer_invoice(updated)
        return updated

    def mark_customer_invoice_ready(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        if invoice.status != CustomerInvoiceStatus.DRAFT:
            raise ValueError("customer invoice can only be marked ready from draft")
        invoice.status = CustomerInvoiceStatus.READY
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def issue_customer_invoice(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        invoice.issue()
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def void_customer_invoice(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        invoice.void()
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def mark_customer_invoice_sync_pending(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        invoice.mark_sync_pending()
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def mark_customer_invoice_sync_synced(
        self,
        customer_invoice_id: str,
        external_id: str | None = None,
        *,
        organization_id: str | None = None,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        invoice.mark_sync_synced(external_id)
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def mark_customer_invoice_sync_failed(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        invoice.mark_sync_failed(error_code=error_code, error_message=error_message)
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def get_customer_invoice(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
    ) -> CustomerInvoice | None:
        record = self.commercial_repository.load_customer_invoice(customer_invoice_id)
        if record is None:
            return None
        if record.tenant_id != self.tenant_id:
            return None
        if organization_id is not None and record.organization_id != organization_id:
            return None
        return record

    def list_customer_invoices(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[CustomerInvoice]:
        invoices = self.commercial_repository.list_customer_invoices()
        return self._filter_organization(invoices, organization_id)

    def calculate_customer_invoice_subtotal(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
    ) -> Decimal:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        return self._calculate_line_items_total(invoice.line_items)

    def calculate_customer_invoice_total(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
    ) -> Decimal:
        return self.calculate_customer_invoice_subtotal(
            customer_invoice_id,
            organization_id=organization_id,
        )

    def create_vendor_bill(
        self,
        *,
        organization_id: str,
        vendor_bill_id: str,
        vendor_id: str,
        vendor_name: str,
        purchase_order_id: str | None = None,
        procurement_need_id: str | None = None,
        project_job_link: ProjectJobLink | dict[str, Any] | None = None,
        line_items: Sequence[VendorBillLineItem | dict[str, Any]] | None = None,
        status: VendorBillStatus = VendorBillStatus.DRAFT,
        entered_at: str | None = None,
        due_at: str | None = None,
        quickbooks_sync_reference: (
            QuickBooksSyncReference | dict[str, Any] | None
        ) = None,
        notes: list[str] | None = None,
    ) -> VendorBill:
        if (
            self.get_vendor_bill(vendor_bill_id, organization_id=organization_id)
            is not None
        ):
            raise ValueError("vendor bill already exists")
        if procurement_need_id is not None:
            procurement_need = self._require_procurement_need(
                procurement_need_id,
                organization_id=organization_id,
            )
            if (
                procurement_need.vendor_id is not None
                and procurement_need.vendor_id != vendor_id
            ):
                raise ValueError(
                    "procurement need does not belong to the selected vendor"
                )
        record = VendorBill(
            tenant_id=self.tenant_id,
            organization_id=organization_id,
            vendor_bill_id=vendor_bill_id,
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            purchase_order_id=purchase_order_id,
            procurement_need_id=procurement_need_id,
            project_job_link=self._normalize_project_job_link(project_job_link),
            status=status,
            line_items=[
                self._normalize_vendor_bill_line_item(item)
                for item in list(line_items or [])
            ],
            entered_at=entered_at,
            due_at=due_at,
            quickbooks_sync_reference=self._normalize_quickbooks_sync_reference(
                quickbooks_sync_reference
            ),
            notes=list(notes or []),
        )
        self.commercial_repository.save_vendor_bill(record)
        return record

    def update_vendor_bill(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
        vendor_id: Any = _UNSET,
        vendor_name: Any = _UNSET,
        purchase_order_id: Any = _UNSET,
        procurement_need_id: Any = _UNSET,
        project_job_link: Any = _UNSET,
        line_items: Any = _UNSET,
        status: Any = _UNSET,
        entered_at: Any = _UNSET,
        due_at: Any = _UNSET,
        quickbooks_sync_reference: Any = _UNSET,
        notes: Any = _UNSET,
    ) -> VendorBill:
        bill = self.get_vendor_bill(vendor_bill_id, organization_id=organization_id)
        if bill is None:
            raise ValueError("vendor bill was not found")
        payload = bill.to_dict()
        if vendor_id is not _UNSET:
            payload["vendor_id"] = vendor_id
        if vendor_name is not _UNSET:
            payload["vendor_name"] = vendor_name
        if purchase_order_id is not _UNSET:
            payload["purchase_order_id"] = purchase_order_id
        if procurement_need_id is not _UNSET:
            payload["procurement_need_id"] = procurement_need_id
        if project_job_link is not _UNSET:
            payload["project_job_link"] = self._normalize_project_job_link(
                project_job_link
            )
        if line_items is not _UNSET:
            payload["line_items"] = [
                self._normalize_vendor_bill_line_item(item).to_dict()
                for item in list(line_items or [])
            ]
        if status is not _UNSET:
            payload["status"] = status.value if hasattr(status, "value") else status
        if entered_at is not _UNSET:
            payload["entered_at"] = entered_at
        if due_at is not _UNSET:
            payload["due_at"] = due_at
        if quickbooks_sync_reference is not _UNSET:
            payload["quickbooks_sync_reference"] = (
                self._normalize_quickbooks_sync_reference(quickbooks_sync_reference)
            )
        if notes is not _UNSET:
            payload["notes"] = list(notes or [])
        updated = VendorBill(**payload)
        self.commercial_repository.save_vendor_bill(updated)
        return updated

    def mark_vendor_bill_ready(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        if bill.status != VendorBillStatus.DRAFT:
            raise ValueError("vendor bill can only be marked ready from draft")
        bill.status = VendorBillStatus.READY
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def issue_vendor_bill(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        bill.issue()
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def void_vendor_bill(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        bill.void()
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def mark_vendor_bill_sync_pending(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        bill.mark_sync_pending()
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def mark_vendor_bill_sync_synced(
        self,
        vendor_bill_id: str,
        external_id: str | None = None,
        *,
        organization_id: str | None = None,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        bill.mark_sync_synced(external_id)
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def mark_vendor_bill_sync_failed(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        bill.mark_sync_failed(error_code=error_code, error_message=error_message)
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def get_vendor_bill(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
    ) -> VendorBill | None:
        record = self.commercial_repository.load_vendor_bill(vendor_bill_id)
        if record is None:
            return None
        if record.tenant_id != self.tenant_id:
            return None
        if organization_id is not None and record.organization_id != organization_id:
            return None
        return record

    def list_vendor_bills(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[VendorBill]:
        bills = self.commercial_repository.list_vendor_bills()
        return self._filter_organization(bills, organization_id)

    def calculate_vendor_bill_subtotal(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
    ) -> Decimal:
        bill = self._require_vendor_bill(
            vendor_bill_id,
            organization_id=organization_id,
        )
        return self._calculate_line_items_total(bill.line_items)

    def calculate_vendor_bill_total(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
    ) -> Decimal:
        return self.calculate_vendor_bill_subtotal(
            vendor_bill_id,
            organization_id=organization_id,
        )

    def _require_customer_invoice(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None,
    ) -> CustomerInvoice:
        invoice = self.get_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        if invoice is None:
            raise ValueError("customer invoice was not found")
        return invoice

    def _require_vendor_bill(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None,
    ) -> VendorBill:
        bill = self.get_vendor_bill(vendor_bill_id, organization_id=organization_id)
        if bill is None:
            raise ValueError("vendor bill was not found")
        return bill

    def _require_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str | None,
    ) -> SalesOrder:
        sales_order = self.get_sales_order(
            sales_order_id, organization_id=organization_id
        )
        if sales_order is None:
            raise ValueError("sales order was not found")
        return sales_order

    def _require_procurement_need(
        self,
        procurement_need_id: str,
        *,
        organization_id: str,
    ) -> ProcurementNeed:
        procurement_need = self.commercial_repository.load_procurement_need(
            procurement_need_id
        )
        if procurement_need is None:
            raise ValueError("procurement need was not found")
        if procurement_need.tenant_id != self.tenant_id:
            raise ValueError("procurement need was not found")
        if procurement_need.organization_id != organization_id:
            raise ValueError("procurement need was not found")
        return procurement_need

    def _ensure_no_existing_invoice_for_sales_order(
        self,
        sales_order_id: str,
        *,
        organization_id: str,
    ) -> None:
        for invoice in self.list_customer_invoices(organization_id=organization_id):
            if invoice.sales_order_id == sales_order_id:
                raise ValueError("sales order has already been invoiced")

    @staticmethod
    def _normalize_customer_invoice_line_item(
        value: CustomerInvoiceLineItem | dict[str, Any],
    ) -> CustomerInvoiceLineItem:
        if isinstance(value, CustomerInvoiceLineItem):
            return value
        return CustomerInvoiceLineItem(**value)

    @staticmethod
    def _normalize_vendor_bill_line_item(
        value: VendorBillLineItem | dict[str, Any],
    ) -> VendorBillLineItem:
        if isinstance(value, VendorBillLineItem):
            return value
        return VendorBillLineItem(**value)

    @staticmethod
    def _normalize_quickbooks_sync_reference(
        value: QuickBooksSyncReference | dict[str, Any] | None,
    ) -> QuickBooksSyncReference | None:
        if value is None:
            return None
        if isinstance(value, QuickBooksSyncReference):
            return value
        return QuickBooksSyncReference(**value)

    def _calculate_line_items_total(
        self,
        line_items: Sequence[CustomerInvoiceLineItem | VendorBillLineItem],
    ) -> Decimal:
        total = Decimal("0")
        for line_item in line_items:
            total += line_item.quantity * line_item.unit_price
        return total


__all__ = ["CommercialInvoiceVendorBillService"]

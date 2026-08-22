"""Tenant-scoped QuickBooks sync architecture for Atlas commercial records."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from atlas_core.contracts.commercial_spine_contracts import (
    CustomerInvoice,
    CustomerInvoiceStatus,
    QuickBooksSyncOperation,
    QuickBooksSyncReference,
    QuickBooksSyncStatus,
    QuickBooksSyncTask,
    VendorBill,
    VendorBillStatus,
)
from atlas_core.services.commercial_invoice_vendor_bill_service import (
    CommercialInvoiceVendorBillService,
)

if TYPE_CHECKING:
    from atlas_core.repository.contracts import RepositoryBundle


class CommercialQuickBooksSyncService(CommercialInvoiceVendorBillService):
    """Tenant-scoped QuickBooks sync coordinator for invoices and vendor bills."""

    def __init__(self, repositories: "RepositoryBundle") -> None:
        super().__init__(repositories)

    def build_customer_invoice_sync_task(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
    ) -> QuickBooksSyncTask | None:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        return self._build_customer_invoice_sync_task(invoice)

    def build_vendor_bill_sync_task(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
    ) -> QuickBooksSyncTask | None:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        return self._build_vendor_bill_sync_task(bill)

    def list_syncable_customer_invoices(
        self,
        *,
        organization_id: str | None = None,
        include_retry: bool = True,
    ) -> list[QuickBooksSyncTask]:
        tasks = []
        for invoice in self.list_customer_invoices(organization_id=organization_id):
            task = self._build_customer_invoice_sync_task(invoice)
            if task is None:
                continue
            if not self._is_syncable(
                task, invoice.quickbooks_sync_reference, include_retry
            ):
                continue
            tasks.append(task)
        return sorted(tasks, key=lambda task: (task.entity_id, task.operation.value))

    def list_syncable_vendor_bills(
        self,
        *,
        organization_id: str | None = None,
        include_retry: bool = True,
    ) -> list[QuickBooksSyncTask]:
        tasks = []
        for bill in self.list_vendor_bills(organization_id=organization_id):
            task = self._build_vendor_bill_sync_task(bill)
            if task is None:
                continue
            if not self._is_syncable(
                task, bill.quickbooks_sync_reference, include_retry
            ):
                continue
            tasks.append(task)
        return sorted(tasks, key=lambda task: (task.entity_id, task.operation.value))

    def mark_customer_invoice_sync_not_ready(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
        reason: str | None = None,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        reference = self._ensure_sync_reference(
            invoice,
            operation=QuickBooksSyncOperation.CREATE,
            idempotency_key=self.build_customer_invoice_sync_key(invoice),
        )
        reference.mark_not_ready(reason)
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
        task = self._require_customer_invoice_sync_candidate(invoice)
        reference = self._ensure_sync_reference(
            invoice,
            operation=task.operation,
            idempotency_key=task.idempotency_key,
        )
        reference.mark_pending(
            idempotency_key=task.idempotency_key,
            operation=task.operation,
            retry_eligible=True,
        )
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def mark_customer_invoice_sync_in_progress(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        task = self._require_customer_invoice_sync_task(invoice)
        if task.status not in {
            QuickBooksSyncStatus.NOT_SYNCED,
            QuickBooksSyncStatus.PENDING,
            QuickBooksSyncStatus.FAILED,
            QuickBooksSyncStatus.SKIPPED,
            QuickBooksSyncStatus.IN_PROGRESS,
        }:
            raise ValueError("customer invoice is not syncable")
        reference = self._ensure_sync_reference(
            invoice,
            operation=task.operation,
            idempotency_key=task.idempotency_key,
        )
        reference.mark_in_progress(
            idempotency_key=task.idempotency_key,
            operation=task.operation,
        )
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def record_customer_invoice_sync_success(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
        external_id: str | None = None,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        task = self._require_customer_invoice_sync_task(invoice)
        reference = self._ensure_sync_reference(
            invoice,
            operation=task.operation,
            idempotency_key=task.idempotency_key,
        )
        reference.mark_synced(
            external_id,
            idempotency_key=task.idempotency_key,
            operation=task.operation,
        )
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def record_customer_invoice_sync_failure(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        retry_eligible: bool = True,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        task = self._require_customer_invoice_sync_task(invoice)
        reference = self._ensure_sync_reference(
            invoice,
            operation=task.operation,
            idempotency_key=task.idempotency_key,
        )
        reference.mark_failed(
            error_code=error_code,
            error_message=error_message,
            retry_eligible=retry_eligible,
            idempotency_key=task.idempotency_key,
            operation=task.operation,
        )
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def mark_customer_invoice_sync_skipped(
        self,
        customer_invoice_id: str,
        *,
        organization_id: str | None = None,
        reason: str | None = None,
    ) -> CustomerInvoice:
        invoice = self._require_customer_invoice(
            customer_invoice_id,
            organization_id=organization_id,
        )
        task = self._require_customer_invoice_sync_task(invoice)
        reference = self._ensure_sync_reference(
            invoice,
            operation=task.operation,
            idempotency_key=task.idempotency_key,
        )
        reference.mark_skipped(
            reason=reason,
            idempotency_key=task.idempotency_key,
            operation=task.operation,
        )
        self.commercial_repository.save_customer_invoice(invoice)
        return invoice

    def mark_vendor_bill_sync_not_ready(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
        reason: str | None = None,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        reference = self._ensure_sync_reference(
            bill,
            operation=QuickBooksSyncOperation.CREATE,
            idempotency_key=self.build_vendor_bill_sync_key(bill),
        )
        reference.mark_not_ready(reason)
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
        task = self._require_vendor_bill_sync_candidate(bill)
        reference = self._ensure_sync_reference(
            bill,
            operation=task.operation,
            idempotency_key=task.idempotency_key,
        )
        reference.mark_pending(
            idempotency_key=task.idempotency_key,
            operation=task.operation,
            retry_eligible=True,
        )
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def mark_vendor_bill_sync_in_progress(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        task = self._require_vendor_bill_sync_task(bill)
        if task.status not in {
            QuickBooksSyncStatus.NOT_SYNCED,
            QuickBooksSyncStatus.PENDING,
            QuickBooksSyncStatus.FAILED,
            QuickBooksSyncStatus.SKIPPED,
            QuickBooksSyncStatus.IN_PROGRESS,
        }:
            raise ValueError("vendor bill is not syncable")
        reference = self._ensure_sync_reference(
            bill,
            operation=task.operation,
            idempotency_key=task.idempotency_key,
        )
        reference.mark_in_progress(
            idempotency_key=task.idempotency_key,
            operation=task.operation,
        )
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def record_vendor_bill_sync_success(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
        external_id: str | None = None,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        task = self._require_vendor_bill_sync_task(bill)
        reference = self._ensure_sync_reference(
            bill,
            operation=task.operation,
            idempotency_key=task.idempotency_key,
        )
        reference.mark_synced(
            external_id,
            idempotency_key=task.idempotency_key,
            operation=task.operation,
        )
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def record_vendor_bill_sync_failure(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        retry_eligible: bool = True,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        task = self._require_vendor_bill_sync_task(bill)
        reference = self._ensure_sync_reference(
            bill,
            operation=task.operation,
            idempotency_key=task.idempotency_key,
        )
        reference.mark_failed(
            error_code=error_code,
            error_message=error_message,
            retry_eligible=retry_eligible,
            idempotency_key=task.idempotency_key,
            operation=task.operation,
        )
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def mark_vendor_bill_sync_skipped(
        self,
        vendor_bill_id: str,
        *,
        organization_id: str | None = None,
        reason: str | None = None,
    ) -> VendorBill:
        bill = self._require_vendor_bill(
            vendor_bill_id, organization_id=organization_id
        )
        task = self._require_vendor_bill_sync_task(bill)
        reference = self._ensure_sync_reference(
            bill,
            operation=task.operation,
            idempotency_key=task.idempotency_key,
        )
        reference.mark_skipped(
            reason=reason,
            idempotency_key=task.idempotency_key,
            operation=task.operation,
        )
        self.commercial_repository.save_vendor_bill(bill)
        return bill

    def build_customer_invoice_sync_key(self, invoice: CustomerInvoice) -> str:
        operation = self._customer_invoice_operation(invoice)
        if operation is None:
            operation = QuickBooksSyncOperation.CREATE
        return self._build_sync_key(invoice, operation)

    def build_vendor_bill_sync_key(self, bill: VendorBill) -> str:
        operation = self._vendor_bill_operation(bill)
        if operation is None:
            operation = QuickBooksSyncOperation.CREATE
        return self._build_sync_key(bill, operation)

    def _build_customer_invoice_sync_task(
        self,
        invoice: CustomerInvoice,
    ) -> QuickBooksSyncTask | None:
        operation = self._customer_invoice_operation(invoice)
        if operation is None:
            if invoice.quickbooks_sync_reference is not None:
                return QuickBooksSyncTask(
                    tenant_id=invoice.tenant_id,
                    organization_id=invoice.organization_id,
                    entity_type="customer_invoice",
                    entity_id=invoice.customer_invoice_id,
                    operation=QuickBooksSyncOperation.CREATE,
                    idempotency_key=self._build_sync_key(
                        invoice,
                        QuickBooksSyncOperation.CREATE,
                    ),
                    status=QuickBooksSyncStatus.NOT_READY,
                    retry_eligible=False,
                    external_id=invoice.quickbooks_sync_reference.external_id,
                    sync_reference_id=invoice.quickbooks_sync_reference.sync_reference_id,
                )
            return None
        idempotency_key = self._build_sync_key(invoice, operation)
        reference = invoice.quickbooks_sync_reference
        status = (
            reference.status
            if reference is not None
            else QuickBooksSyncStatus.NOT_SYNCED
        )
        retry_eligible = reference.can_retry() if reference is not None else True
        external_id = reference.external_id if reference is not None else None
        sync_reference_id = (
            reference.sync_reference_id if reference is not None else None
        )
        return QuickBooksSyncTask(
            tenant_id=invoice.tenant_id,
            organization_id=invoice.organization_id,
            entity_type="customer_invoice",
            entity_id=invoice.customer_invoice_id,
            operation=operation,
            idempotency_key=idempotency_key,
            status=status,
            retry_eligible=retry_eligible,
            external_id=external_id,
            sync_reference_id=sync_reference_id,
        )

    def _build_vendor_bill_sync_task(
        self,
        bill: VendorBill,
    ) -> QuickBooksSyncTask | None:
        operation = self._vendor_bill_operation(bill)
        if operation is None:
            if bill.quickbooks_sync_reference is not None:
                return QuickBooksSyncTask(
                    tenant_id=bill.tenant_id,
                    organization_id=bill.organization_id,
                    entity_type="vendor_bill",
                    entity_id=bill.vendor_bill_id,
                    operation=QuickBooksSyncOperation.CREATE,
                    idempotency_key=self._build_sync_key(
                        bill,
                        QuickBooksSyncOperation.CREATE,
                    ),
                    status=QuickBooksSyncStatus.NOT_READY,
                    retry_eligible=False,
                    external_id=bill.quickbooks_sync_reference.external_id,
                    sync_reference_id=bill.quickbooks_sync_reference.sync_reference_id,
                )
            return None
        idempotency_key = self._build_sync_key(bill, operation)
        reference = bill.quickbooks_sync_reference
        status = (
            reference.status
            if reference is not None
            else QuickBooksSyncStatus.NOT_SYNCED
        )
        retry_eligible = reference.can_retry() if reference is not None else True
        external_id = reference.external_id if reference is not None else None
        sync_reference_id = (
            reference.sync_reference_id if reference is not None else None
        )
        return QuickBooksSyncTask(
            tenant_id=bill.tenant_id,
            organization_id=bill.organization_id,
            entity_type="vendor_bill",
            entity_id=bill.vendor_bill_id,
            operation=operation,
            idempotency_key=idempotency_key,
            status=status,
            retry_eligible=retry_eligible,
            external_id=external_id,
            sync_reference_id=sync_reference_id,
        )

    def _require_customer_invoice_sync_task(
        self,
        invoice: CustomerInvoice,
    ) -> QuickBooksSyncTask:
        task = self._build_customer_invoice_sync_task(invoice)
        if task is None:
            raise ValueError("customer invoice is not syncable")
        return task

    def _require_customer_invoice_sync_candidate(
        self,
        invoice: CustomerInvoice,
    ) -> QuickBooksSyncTask:
        task = self._require_customer_invoice_sync_task(invoice)
        if not self._is_syncable(task, invoice.quickbooks_sync_reference, True):
            raise ValueError("customer invoice is not syncable")
        return task

    def _require_vendor_bill_sync_task(self, bill: VendorBill) -> QuickBooksSyncTask:
        task = self._build_vendor_bill_sync_task(bill)
        if task is None:
            raise ValueError("vendor bill is not syncable")
        return task

    def _require_vendor_bill_sync_candidate(
        self,
        bill: VendorBill,
    ) -> QuickBooksSyncTask:
        task = self._require_vendor_bill_sync_task(bill)
        if not self._is_syncable(task, bill.quickbooks_sync_reference, True):
            raise ValueError("vendor bill is not syncable")
        return task

    def _customer_invoice_operation(
        self,
        invoice: CustomerInvoice,
    ) -> QuickBooksSyncOperation | None:
        if invoice.status == CustomerInvoiceStatus.VOIDED:
            if self._sync_reference_has_external_id(invoice.quickbooks_sync_reference):
                return QuickBooksSyncOperation.VOID
            return None
        if invoice.status != CustomerInvoiceStatus.ISSUED:
            return None
        if self._sync_reference_has_external_id(invoice.quickbooks_sync_reference):
            return QuickBooksSyncOperation.UPDATE
        return QuickBooksSyncOperation.CREATE

    def _vendor_bill_operation(
        self,
        bill: VendorBill,
    ) -> QuickBooksSyncOperation | None:
        if bill.status == VendorBillStatus.VOIDED:
            if self._sync_reference_has_external_id(bill.quickbooks_sync_reference):
                return QuickBooksSyncOperation.VOID
            return None
        if bill.status != VendorBillStatus.ENTERED:
            return None
        if self._sync_reference_has_external_id(bill.quickbooks_sync_reference):
            return QuickBooksSyncOperation.UPDATE
        return QuickBooksSyncOperation.CREATE

    def _sync_reference_has_external_id(
        self,
        reference: QuickBooksSyncReference | None,
    ) -> bool:
        return reference is not None and reference.external_id is not None

    def _ensure_sync_reference(
        self,
        record: CustomerInvoice | VendorBill,
        *,
        operation: QuickBooksSyncOperation,
        idempotency_key: str,
    ) -> QuickBooksSyncReference:
        reference = record.quickbooks_sync_reference
        if reference is None:
            reference = QuickBooksSyncReference(
                tenant_id=record.tenant_id,
                organization_id=record.organization_id,
                sync_reference_id=self._sync_reference_id(record),
                entity_type=self._sync_entity_type(record),
                entity_id=self._sync_entity_id(record),
                operation=operation,
                idempotency_key=idempotency_key,
            )
            record.quickbooks_sync_reference = reference
            return reference
        reference.operation = operation
        reference.idempotency_key = idempotency_key
        return reference

    def _sync_reference_id(self, record: CustomerInvoice | VendorBill) -> str:
        if isinstance(record, CustomerInvoice):
            return f"customer-invoice-sync:{record.customer_invoice_id}"
        return f"vendor-bill-sync:{record.vendor_bill_id}"

    def _sync_entity_type(self, record: CustomerInvoice | VendorBill) -> str:
        return (
            "customer_invoice" if isinstance(record, CustomerInvoice) else "vendor_bill"
        )

    def _sync_entity_id(self, record: CustomerInvoice | VendorBill) -> str:
        if isinstance(record, CustomerInvoice):
            return record.customer_invoice_id
        return record.vendor_bill_id

    def _build_sync_key(
        self,
        record: CustomerInvoice | VendorBill,
        operation: QuickBooksSyncOperation,
    ) -> str:
        payload = dict(record.to_dict())
        payload.pop("quickbooks_sync_reference", None)
        normalized = json.dumps(
            {
                "entity_type": self._sync_entity_type(record),
                "entity_id": self._sync_entity_id(record),
                "operation": operation.value,
                "payload": payload,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _is_syncable(
        self,
        task: QuickBooksSyncTask,
        reference: QuickBooksSyncReference | None,
        include_retry: bool,
    ) -> bool:
        if task.status == QuickBooksSyncStatus.NOT_READY:
            return False
        if reference is None:
            return task.status in {
                QuickBooksSyncStatus.NOT_SYNCED,
                QuickBooksSyncStatus.FAILED,
                QuickBooksSyncStatus.SKIPPED,
            }
        if reference.idempotency_key != task.idempotency_key:
            return True
        if reference.status in {
            QuickBooksSyncStatus.SYNCED,
            QuickBooksSyncStatus.PENDING,
            QuickBooksSyncStatus.IN_PROGRESS,
        }:
            return False
        if reference.status in {
            QuickBooksSyncStatus.FAILED,
            QuickBooksSyncStatus.SKIPPED,
        }:
            return include_retry and reference.can_retry()
        return True


__all__ = ["CommercialQuickBooksSyncService"]

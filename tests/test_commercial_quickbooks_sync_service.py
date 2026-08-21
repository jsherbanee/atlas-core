from __future__ import annotations

from decimal import Decimal

from atlas_core.contracts import (
    CustomerInvoiceStatus,
    EstimateLineItem,
    QuickBooksSyncOperation,
    QuickBooksSyncStatus,
)
from atlas_core.repository.local import build_local_tenant_repository_bundle
from atlas_core.services.commercial_quickbooks_sync_service import (
    CommercialQuickBooksSyncService,
)
from atlas_core.services.commercial_reporting_service import CommercialReportingService


def _service(tenant_id: str, root: str) -> CommercialQuickBooksSyncService:
    return CommercialQuickBooksSyncService(
        build_local_tenant_repository_bundle(tenant_id, root)
    )


def _reporting_service(tenant_id: str, root: str) -> CommercialReportingService:
    return CommercialReportingService(
        build_local_tenant_repository_bundle(tenant_id, root)
    )


def _seed_customer_workflow(
    service: CommercialQuickBooksSyncService,
    *,
    customer_name: str,
) -> tuple[str, str]:
    service.create_customer_account(
        organization_id="org-1",
        customer_id="customer-1",
        name=customer_name,
    )
    service.create_opportunity(
        organization_id="org-1",
        opportunity_id="opp-1",
        customer_id="customer-1",
        name="Conference room refresh",
        estimated_value=Decimal("12500.00"),
    )
    service.create_estimate(
        organization_id="org-1",
        estimate_id="est-1",
        customer_id="customer-1",
        opportunity_id="opp-1",
        line_items=[
            EstimateLineItem(
                line_item_id="est-line-1",
                description="Core display package",
                quantity=Decimal("2"),
                unit_price=Decimal("4500.00"),
                catalog_item_id="cat-1",
            )
        ],
    )
    proposal = service.create_proposal_for_estimate("est-1")
    service.send_proposal(proposal.proposal_id)
    service.accept_proposal(proposal.proposal_id)
    sales_order = service.convert_accepted_estimate_to_sales_order("est-1")
    invoice = service.create_customer_invoice_from_sales_order(
        sales_order.sales_order_id
    )
    service.issue_customer_invoice(invoice.customer_invoice_id)

    manual_invoice = service.create_customer_invoice(
        organization_id="org-1",
        customer_invoice_id="ci-manual-1",
        customer_id="customer-1",
        customer_name=customer_name,
        status=CustomerInvoiceStatus.ISSUED,
        line_items=[
            {
                "line_item_id": "ci-manual-line-1",
                "description": "Additional room control",
                "quantity": Decimal("1"),
                "unit_price": Decimal("2500.00"),
                "catalog_item_id": "cat-2",
            }
        ],
    )

    return invoice.customer_invoice_id, manual_invoice.customer_invoice_id


def _seed_vendor_bills(service: CommercialQuickBooksSyncService) -> tuple[str, str]:
    first_bill = service.create_vendor_bill(
        organization_id="org-1",
        vendor_bill_id="vb-1",
        vendor_id="vendor-1",
        vendor_name="Vendor One",
        line_items=[
            {
                "line_item_id": "vb-line-1",
                "description": "Display processor",
                "quantity": Decimal("1"),
                "unit_price": Decimal("5200.00"),
                "catalog_item_id": "cat-1",
            }
        ],
    )
    second_bill = service.create_vendor_bill(
        organization_id="org-1",
        vendor_bill_id="vb-2",
        vendor_id="vendor-2",
        vendor_name="Vendor Two",
        line_items=[
            {
                "line_item_id": "vb-line-2",
                "description": "Room controller",
                "quantity": Decimal("1"),
                "unit_price": Decimal("1800.00"),
                "catalog_item_id": "cat-2",
            }
        ],
    )
    service.mark_vendor_bill_ready(first_bill.vendor_bill_id)
    service.issue_vendor_bill(first_bill.vendor_bill_id)
    service.mark_vendor_bill_ready(second_bill.vendor_bill_id)
    service.issue_vendor_bill(second_bill.vendor_bill_id)
    return first_bill.vendor_bill_id, second_bill.vendor_bill_id


def test_quickbooks_sync_selection_idempotency_and_lifecycle(tmp_path) -> None:
    root = str(tmp_path / "Atlas")
    service = _service("tenant-a", root)

    synced_invoice_id, manual_invoice_id = _seed_customer_workflow(
        service,
        customer_name="Acme Integrators",
    )
    first_bill_id, second_bill_id = _seed_vendor_bills(service)

    invoice_tasks = service.list_syncable_customer_invoices(organization_id="org-1")
    bill_tasks = service.list_syncable_vendor_bills(organization_id="org-1")

    assert [task.entity_id for task in invoice_tasks] == [
        manual_invoice_id,
        synced_invoice_id,
    ]
    assert [task.entity_id for task in bill_tasks] == [first_bill_id, second_bill_id]
    assert invoice_tasks == service.list_syncable_customer_invoices(
        organization_id="org-1"
    )
    assert bill_tasks == service.list_syncable_vendor_bills(organization_id="org-1")

    invoice_task = service.build_customer_invoice_sync_task(synced_invoice_id)
    assert invoice_task is not None
    assert invoice_task.operation == QuickBooksSyncOperation.CREATE
    synced_invoice = service.get_customer_invoice(synced_invoice_id)
    assert synced_invoice is not None
    assert invoice_task.idempotency_key == service.build_customer_invoice_sync_key(
        synced_invoice
    )

    service.mark_customer_invoice_sync_pending(synced_invoice_id)
    invoice_after_pending = service.get_customer_invoice(synced_invoice_id)
    assert invoice_after_pending is not None
    assert invoice_after_pending.quickbooks_sync_reference is not None
    assert (
        invoice_after_pending.quickbooks_sync_reference.status
        == QuickBooksSyncStatus.PENDING
    )
    assert invoice_after_pending.quickbooks_sync_reference.attempt_count == 1

    service.mark_customer_invoice_sync_in_progress(synced_invoice_id)
    invoice_after_in_progress = service.get_customer_invoice(synced_invoice_id)
    assert invoice_after_in_progress is not None
    assert invoice_after_in_progress.quickbooks_sync_reference is not None
    assert (
        invoice_after_in_progress.quickbooks_sync_reference.status
        == QuickBooksSyncStatus.IN_PROGRESS
    )

    service.record_customer_invoice_sync_success(
        synced_invoice_id,
        external_id="qb-inv-1",
    )
    synced_invoice = service.get_customer_invoice(synced_invoice_id)
    assert synced_invoice is not None
    assert synced_invoice.quickbooks_sync_reference is not None
    assert (
        synced_invoice.quickbooks_sync_reference.status == QuickBooksSyncStatus.SYNCED
    )
    assert synced_invoice.quickbooks_sync_reference.external_id == "qb-inv-1"
    assert (
        synced_invoice.quickbooks_sync_reference.operation
        == QuickBooksSyncOperation.CREATE
    )
    assert synced_invoice.quickbooks_sync_reference.retry_eligible is False

    service.mark_customer_invoice_sync_not_ready(
        manual_invoice_id,
        reason="Waiting on customer approval",
    )
    manual_invoice = service.get_customer_invoice(manual_invoice_id)
    assert manual_invoice is not None
    assert manual_invoice.quickbooks_sync_reference is not None
    assert (
        manual_invoice.quickbooks_sync_reference.status
        == QuickBooksSyncStatus.NOT_READY
    )
    assert manual_invoice.quickbooks_sync_reference.can_retry() is False

    service.mark_vendor_bill_sync_pending(first_bill_id)
    service.mark_vendor_bill_sync_in_progress(first_bill_id)
    service.record_vendor_bill_sync_failure(
        first_bill_id,
        error_code="QB-500",
        error_message="Temporary outage",
        retry_eligible=True,
    )
    failed_bill = service.get_vendor_bill(first_bill_id)
    assert failed_bill is not None
    assert failed_bill.quickbooks_sync_reference is not None
    assert failed_bill.quickbooks_sync_reference.status == QuickBooksSyncStatus.FAILED
    assert failed_bill.quickbooks_sync_reference.last_error_code == "QB-500"
    assert failed_bill.quickbooks_sync_reference.can_retry() is True

    service.mark_vendor_bill_sync_pending(second_bill_id)
    service.mark_vendor_bill_sync_in_progress(second_bill_id)
    service.mark_vendor_bill_sync_skipped(second_bill_id, reason="Not required")
    skipped_bill = service.get_vendor_bill(second_bill_id)
    assert skipped_bill is not None
    assert skipped_bill.quickbooks_sync_reference is not None
    assert skipped_bill.quickbooks_sync_reference.status == QuickBooksSyncStatus.SKIPPED
    assert skipped_bill.quickbooks_sync_reference.can_retry() is False

    service.update_customer_invoice(synced_invoice_id, notes=["Revised after sync"])
    updated_task = service.build_customer_invoice_sync_task(synced_invoice_id)
    assert updated_task is not None
    assert updated_task.operation == QuickBooksSyncOperation.UPDATE
    assert updated_task.idempotency_key != invoice_task.idempotency_key

    retryable_bill_tasks = service.list_syncable_vendor_bills(organization_id="org-1")
    non_retryable_bill_tasks = service.list_syncable_vendor_bills(
        organization_id="org-1",
        include_retry=False,
    )
    assert [task.entity_id for task in retryable_bill_tasks] == [first_bill_id]
    assert non_retryable_bill_tasks == []

    assert service.list_syncable_customer_invoices(organization_id="org-1") == [
        updated_task,
    ]

    reporting = _reporting_service("tenant-a", root)
    sync_summary = reporting.quickbooks_sync_summary(organization_id="org-1")
    assert sync_summary.counts_by_status == {
        "failed": 1,
        "not_ready": 1,
        "skipped": 1,
        "synced": 1,
    }
    assert sync_summary.counts_by_entity_type == {
        "customer_invoice": 2,
        "vendor_bill": 2,
    }


def test_quickbooks_sync_is_tenant_scoped(tmp_path) -> None:
    root = str(tmp_path / "Atlas")
    service_a = _service("tenant-a", root)
    service_b = _service("tenant-b", root)

    invoice_a_1, invoice_a_2 = _seed_customer_workflow(
        service_a,
        customer_name="Tenant A Integrators",
    )
    _seed_vendor_bills(service_a)
    invoice_b_1, invoice_b_2 = _seed_customer_workflow(
        service_b,
        customer_name="Tenant B Integrators",
    )
    _seed_vendor_bills(service_b)

    task_a = service_a.build_customer_invoice_sync_task(invoice_a_1)
    task_b = service_b.build_customer_invoice_sync_task(invoice_b_1)
    assert task_a is not None
    assert task_b is not None
    assert task_a.idempotency_key != task_b.idempotency_key

    service_a.record_customer_invoice_sync_success(invoice_a_1, external_id="qb-a-1")
    service_a.mark_customer_invoice_sync_not_ready(invoice_a_2, reason="Blocked")
    service_b.mark_customer_invoice_sync_not_ready(invoice_b_2, reason="Blocked")

    invoice_a = service_a.get_customer_invoice(invoice_a_1)
    invoice_b = service_b.get_customer_invoice(invoice_a_1)
    assert invoice_a is not None
    assert invoice_a.quickbooks_sync_reference is not None
    assert invoice_a.quickbooks_sync_reference.external_id == "qb-a-1"
    assert invoice_b is not None
    assert invoice_b.quickbooks_sync_reference is None

    reporting_a = _reporting_service("tenant-a", root)
    reporting_b = _reporting_service("tenant-b", root)
    assert reporting_a.quickbooks_sync_summary(
        organization_id="org-1"
    ).counts_by_status == {
        "not_ready": 1,
        "not_synced": 2,
        "synced": 1,
    }
    assert reporting_b.quickbooks_sync_summary(
        organization_id="org-1"
    ).counts_by_status == {
        "not_ready": 1,
        "not_synced": 3,
    }

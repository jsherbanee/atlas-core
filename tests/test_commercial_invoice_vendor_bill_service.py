from __future__ import annotations

from decimal import Decimal

import pytest

from atlas_core.contracts import (
    CustomerInvoiceStatus,
    EstimateLineItem,
    ProcurementNeed,
    ProjectJobLink,
    QuickBooksSyncReference,
    VendorBillStatus,
)
from atlas_core.repository.local import build_local_tenant_repository_bundle
from atlas_core.services.commercial_invoice_vendor_bill_service import (
    CommercialInvoiceVendorBillService,
)


def _service(tenant_id: str, root: str) -> CommercialInvoiceVendorBillService:
    return CommercialInvoiceVendorBillService(
        build_local_tenant_repository_bundle(tenant_id, root)
    )


def _seed_sales_order(service: CommercialInvoiceVendorBillService) -> str:
    service.create_customer_account(
        organization_id="org-1",
        customer_id="customer-1",
        name="Acme Integrators",
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
    return sales_order.sales_order_id


def test_customer_invoice_generation_sync_and_totals(tmp_path) -> None:
    service = _service("tenant-a", str(tmp_path / "Atlas"))
    sales_order_id = _seed_sales_order(service)

    invoice = service.create_customer_invoice_from_sales_order(sales_order_id)
    loaded_invoice = service.get_customer_invoice(invoice.customer_invoice_id)

    assert invoice.customer_id == "customer-1"
    assert invoice.customer_name == "Acme Integrators"
    assert invoice.sales_order_id == sales_order_id
    assert invoice.line_items[0].sales_order_line_item_id == "est-line-1"
    assert invoice.line_items[0].quantity == Decimal("2")
    assert invoice.line_items[0].unit_price == Decimal("4500.00")
    assert service.calculate_customer_invoice_subtotal(
        invoice.customer_invoice_id
    ) == Decimal("9000.00")
    assert service.calculate_customer_invoice_total(
        invoice.customer_invoice_id
    ) == Decimal("9000.00")
    assert loaded_invoice is not None
    assert loaded_invoice.sales_order_id == sales_order_id

    ready_invoice = service.mark_customer_invoice_ready(invoice.customer_invoice_id)
    issued_invoice = service.issue_customer_invoice(invoice.customer_invoice_id)
    sync_pending_invoice = service.mark_customer_invoice_sync_pending(
        invoice.customer_invoice_id
    )
    sync_failed_invoice = service.mark_customer_invoice_sync_failed(
        invoice.customer_invoice_id,
        error_code="QB-422",
        error_message="Duplicate",
    )
    sync_synced_invoice = service.mark_customer_invoice_sync_synced(
        invoice.customer_invoice_id,
        external_id="qb-inv-1",
    )

    assert ready_invoice.status == CustomerInvoiceStatus.READY
    assert issued_invoice.status == CustomerInvoiceStatus.ISSUED
    assert sync_pending_invoice.quickbooks_sync_reference is not None
    assert sync_pending_invoice.quickbooks_sync_reference.status.value == "pending"
    assert sync_failed_invoice.quickbooks_sync_reference is not None
    assert sync_failed_invoice.quickbooks_sync_reference.last_error_code == "QB-422"
    assert sync_synced_invoice.quickbooks_sync_reference is not None
    assert sync_synced_invoice.quickbooks_sync_reference.external_id == "qb-inv-1"

    with pytest.raises(ValueError, match="sales order has already been invoiced"):
        service.create_customer_invoice_from_sales_order(sales_order_id)

    manual_invoice = service.create_customer_invoice(
        organization_id="org-1",
        customer_invoice_id="ci-manual-1",
        customer_id="customer-1",
        customer_name="Acme Integrators",
        line_items=[],
        status=CustomerInvoiceStatus.DRAFT,
        quickbooks_sync_reference=QuickBooksSyncReference(
            tenant_id="tenant-a",
            organization_id="org-1",
            sync_reference_id="ci-sync-1",
            entity_type="customer_invoice",
            entity_id="ci-manual-1",
        ),
    )
    voided_invoice = service.void_customer_invoice(manual_invoice.customer_invoice_id)

    assert voided_invoice.status == CustomerInvoiceStatus.VOIDED
    assert len(service.list_customer_invoices()) == 2


def test_vendor_bill_lifecycle_totals_and_sync_references(tmp_path) -> None:
    service = _service("tenant-a", str(tmp_path / "Atlas"))
    service.commercial_repository.save_procurement_need(
        ProcurementNeed(
            tenant_id="tenant-a",
            organization_id="org-1",
            procurement_need_id="need-1",
            catalog_item_id="cat-1",
            quantity_required=Decimal("3"),
            vendor_id="vendor-1",
            sales_order_id="so-1",
            project_job_link=ProjectJobLink(project_id="project-1", job_id="job-1"),
        )
    )

    vendor_bill = service.create_vendor_bill(
        organization_id="org-1",
        vendor_bill_id="vb-1",
        vendor_id="vendor-1",
        vendor_name="AV Supply",
        procurement_need_id="need-1",
        project_job_link=ProjectJobLink(project_id="project-1", job_id="job-1"),
        line_items=[
            {
                "line_item_id": "vb-line-1",
                "description": "Display processor",
                "quantity": Decimal("1"),
                "unit_price": Decimal("5200.00"),
                "catalog_item_id": "cat-1",
                "purchase_order_line_item_id": "po-line-1",
            }
        ],
        quickbooks_sync_reference={
            "tenant_id": "tenant-a",
            "organization_id": "org-1",
            "sync_reference_id": "vb-sync-1",
            "entity_type": "vendor_bill",
            "entity_id": "vb-1",
        },
    )
    updated_bill = service.update_vendor_bill(
        vendor_bill.vendor_bill_id,
        notes=["Verified against procurement need"],
    )

    assert vendor_bill.vendor_id == "vendor-1"
    assert vendor_bill.line_items[0].purchase_order_line_item_id == "po-line-1"
    assert service.calculate_vendor_bill_subtotal(
        vendor_bill.vendor_bill_id
    ) == Decimal("5200.00")
    assert service.calculate_vendor_bill_total(vendor_bill.vendor_bill_id) == Decimal(
        "5200.00"
    )
    assert updated_bill.notes == ["Verified against procurement need"]

    ready_bill = service.mark_vendor_bill_ready(vendor_bill.vendor_bill_id)
    entered_bill = service.issue_vendor_bill(vendor_bill.vendor_bill_id)
    pending_bill = service.mark_vendor_bill_sync_pending(vendor_bill.vendor_bill_id)
    failed_bill = service.mark_vendor_bill_sync_failed(
        vendor_bill.vendor_bill_id,
        error_code="QB-500",
        error_message="Ledger unavailable",
    )
    synced_bill = service.mark_vendor_bill_sync_synced(
        vendor_bill.vendor_bill_id,
        external_id="qb-bill-1",
    )

    assert ready_bill.status == VendorBillStatus.READY
    assert entered_bill.status == VendorBillStatus.ENTERED
    assert pending_bill.quickbooks_sync_reference is not None
    assert pending_bill.quickbooks_sync_reference.status.value == "pending"
    assert failed_bill.quickbooks_sync_reference is not None
    assert failed_bill.quickbooks_sync_reference.last_error_code == "QB-500"
    assert synced_bill.quickbooks_sync_reference is not None
    assert synced_bill.quickbooks_sync_reference.external_id == "qb-bill-1"

    assert service.get_vendor_bill(vendor_bill.vendor_bill_id) is not None
    assert [bill.vendor_bill_id for bill in service.list_vendor_bills()] == ["vb-1"]


def test_financial_services_preserve_tenant_isolation_and_reject_cross_tenant_links(
    tmp_path,
) -> None:
    service_a = _service("tenant-a", str(tmp_path / "Atlas"))
    service_b = _service("tenant-b", str(tmp_path / "Atlas"))

    sales_order_id = _seed_sales_order(service_a)
    service_a.commercial_repository.save_procurement_need(
        ProcurementNeed(
            tenant_id="tenant-a",
            organization_id="org-1",
            procurement_need_id="need-1",
            catalog_item_id="cat-1",
            quantity_required=Decimal("1"),
            vendor_id="vendor-a",
        )
    )

    invoice_a = service_a.create_customer_invoice_from_sales_order(sales_order_id)
    bill_a = service_a.create_vendor_bill(
        organization_id="org-1",
        vendor_bill_id="vb-a",
        vendor_id="vendor-a",
        vendor_name="Tenant A Supply",
        procurement_need_id="need-1",
        line_items=[],
    )

    assert service_b.get_customer_invoice(invoice_a.customer_invoice_id) is None
    assert service_b.get_vendor_bill(bill_a.vendor_bill_id) is None
    assert [
        invoice.customer_invoice_id for invoice in service_a.list_customer_invoices()
    ] == [invoice_a.customer_invoice_id]
    assert [bill.vendor_bill_id for bill in service_a.list_vendor_bills()] == [
        bill_a.vendor_bill_id
    ]

    with pytest.raises(ValueError, match="sales order was not found"):
        service_b.create_customer_invoice_from_sales_order(sales_order_id)

    with pytest.raises(ValueError, match="procurement need was not found"):
        service_b.create_vendor_bill(
            organization_id="org-1",
            vendor_bill_id="vb-b",
            vendor_id="vendor-a",
            vendor_name="Tenant B Supply",
            procurement_need_id="need-1",
            line_items=[],
        )

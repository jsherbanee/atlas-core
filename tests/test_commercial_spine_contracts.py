from __future__ import annotations

from decimal import Decimal

import pytest

from atlas_core.contracts import (
    CatalogItem,
    ChangeOrder,
    ChangeOrderDirection,
    CustomerAccount,
    CustomerInvoice,
    CustomerInvoiceLineItem,
    CustomerInvoiceStatus,
    Estimate,
    EstimateLineItem,
    InventoryLocation,
    InventoryPosition,
    InventoryReservation,
    InventoryReservationStatus,
    Opportunity,
    Proposal,
    ProposalStatus,
    ProcurementNeed,
    ProcurementNeedStatus,
    ProjectJobLink,
    QuickBooksSyncOperation,
    QuickBooksSyncDirection,
    QuickBooksSyncReference,
    QuickBooksSyncStatus,
    SalesOrder,
    SalesOrderLineItem,
    SalesOrderStatus,
    VendorBill,
    VendorBillLineItem,
    VendorBillStatus,
    VendorManufacturerReference,
)


def test_customer_opportunity_and_estimate_serialize_with_tenant_scope() -> None:
    customer = CustomerAccount(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-1",
        name="Acme Integrators",
        billing_email="ops@acme.example",
    )
    opportunity = Opportunity(
        tenant_id="tenant-1",
        organization_id="org-1",
        opportunity_id="opp-1",
        customer_id="customer-1",
        name="Conference room refresh",
        estimated_value=Decimal("12500.00"),
    )
    estimate = Estimate(
        tenant_id="tenant-1",
        organization_id="org-1",
        estimate_id="est-1",
        customer_id="customer-1",
        opportunity_id="opp-1",
        proposal_id="prop-1",
        project_job_link=ProjectJobLink(project_id="project-1", job_id="job-1"),
        line_items=[
            EstimateLineItem(
                line_item_id="line-1",
                description="Core display package",
                quantity=Decimal("2"),
                unit_price=Decimal("4500.00"),
                catalog_item_id="cat-1",
            )
        ],
    )

    assert customer.to_dict()["tenant_id"] == "tenant-1"
    assert opportunity.to_dict()["estimated_value"] == "12500.00"
    payload = estimate.to_dict()
    assert payload["project_job_link"] == {
        "project_id": "project-1",
        "job_id": "job-1",
        "project_name": None,
        "job_number": None,
    }
    assert payload["line_items"][0]["quantity"] == "2"
    assert payload["line_items"][0]["unit_price"] == "4500.00"


def test_proposal_and_sales_order_status_transitions() -> None:
    proposal = Proposal(
        tenant_id="tenant-1",
        organization_id="org-1",
        proposal_id="prop-1",
        estimate_id="est-1",
        customer_id="customer-1",
    )
    proposal.mark_ready()
    proposal.send()
    proposal.accept()

    sales_order = SalesOrder(
        tenant_id="tenant-1",
        organization_id="org-1",
        sales_order_id="so-1",
        customer_id="customer-1",
        estimate_id="est-1",
        proposal_id="prop-1",
        project_job_link=ProjectJobLink(project_id="project-1", job_id="job-1"),
        line_items=[
            SalesOrderLineItem(
                line_item_id="so-line-1",
                description="Core display package",
                quantity=Decimal("2"),
                unit_price=Decimal("4500.00"),
                catalog_item_id="cat-1",
                estimate_line_item_id="line-1",
            )
        ],
    )
    sales_order.open()
    sales_order.mark_partially_fulfilled()
    sales_order.fulfill()
    sales_order.close()

    assert proposal.status == ProposalStatus.ACCEPTED
    assert sales_order.status == SalesOrderStatus.CLOSED
    assert sales_order.to_dict()["line_items"][0]["estimate_line_item_id"] == "line-1"


def test_change_order_inventory_and_procurement_transitions() -> None:
    change_order = ChangeOrder(
        tenant_id="tenant-1",
        organization_id="org-1",
        change_order_id="co-1",
        sales_order_id="so-1",
        project_job_link=ProjectJobLink(project_id="project-1", job_id="job-1"),
        direction=ChangeOrderDirection.DEDUCTIVE,
    )
    change_order.submit()
    change_order.approve()
    change_order.apply()

    reservation = InventoryReservation(
        tenant_id="tenant-1",
        organization_id="org-1",
        reservation_id="res-1",
        catalog_item_id="cat-1",
        location_id="loc-1",
        quantity=Decimal("3"),
        sales_order_line_item_id="so-line-1",
    )
    reservation.reserve()
    reservation.fulfill()

    procurement_need = ProcurementNeed(
        tenant_id="tenant-1",
        organization_id="org-1",
        procurement_need_id="need-1",
        catalog_item_id="cat-1",
        quantity_required=Decimal("3"),
        sales_order_id="so-1",
        vendor_id="vendor-1",
    )
    procurement_need.request()
    procurement_need.quote()
    procurement_need.order()
    procurement_need.receive()
    procurement_need.close()

    assert change_order.status.value == "applied"
    assert reservation.status == InventoryReservationStatus.FULFILLED
    assert procurement_need.status == ProcurementNeedStatus.CLOSED


def test_reference_and_sync_models_serialize() -> None:
    reference = VendorManufacturerReference(
        vendor_id="vendor-1",
        vendor_name="Acme Supply",
        manufacturer_id="mfg-1",
        manufacturer_name="Atlas Displays",
        vendor_part_number="PN-100",
    )
    catalog_item = CatalogItem(
        tenant_id="tenant-1",
        organization_id="org-1",
        catalog_item_id="cat-1",
        sku="SKU-1",
        description="Display",
        list_price=Decimal("1200.00"),
        vendor_manufacturer_reference=reference,
    )
    location = InventoryLocation(
        tenant_id="tenant-1",
        organization_id="org-1",
        location_id="loc-1",
        name="Main warehouse",
        code="WH1",
    )
    position = InventoryPosition(
        tenant_id="tenant-1",
        organization_id="org-1",
        position_id="pos-1",
        catalog_item_id="cat-1",
        location_id="loc-1",
        quantity_on_hand=Decimal("10"),
        quantity_reserved=Decimal("2"),
        quantity_available=Decimal("8"),
    )
    sync_reference = QuickBooksSyncReference(
        tenant_id="tenant-1",
        organization_id="org-1",
        sync_reference_id="sync-1",
        entity_type="sales_order",
        entity_id="so-1",
        operation=QuickBooksSyncOperation.CREATE,
        idempotency_key="sync-key-1",
        direction=QuickBooksSyncDirection.OUTBOUND,
    )
    sync_reference.mark_pending()
    sync_reference.mark_synced("qb-100")

    assert (
        catalog_item.to_dict()["vendor_manufacturer_reference"]["vendor_name"]
        == "Acme Supply"
    )
    assert location.to_dict()["code"] == "WH1"
    assert position.to_dict()["quantity_available"] == "8"
    assert sync_reference.status == QuickBooksSyncStatus.SYNCED
    assert sync_reference.to_dict()["external_id"] == "qb-100"
    assert sync_reference.to_dict()["operation"] == "create"
    assert sync_reference.to_dict()["idempotency_key"] == "sync-key-1"
    assert sync_reference.to_dict()["attempt_count"] == 1
    assert sync_reference.retry_eligible is False


def test_customer_invoice_and_vendor_bill_sync_payloads() -> None:
    customer_invoice = CustomerInvoice(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_invoice_id="ci-1",
        customer_id="customer-1",
        customer_name="Acme Integrators",
        estimate_id="est-1",
        sales_order_id="so-1",
        project_job_link=ProjectJobLink(project_id="project-1", job_id="job-1"),
        line_items=[
            CustomerInvoiceLineItem(
                line_item_id="ci-line-1",
                description="Installed display package",
                quantity=Decimal("1"),
                unit_price=Decimal("8500.00"),
                catalog_item_id="cat-1",
                sales_order_line_item_id="so-line-1",
            )
        ],
    )
    vendor_bill = VendorBill(
        tenant_id="tenant-1",
        organization_id="org-1",
        vendor_bill_id="vb-1",
        vendor_id="vendor-1",
        vendor_name="Acme Supply",
        purchase_order_id="po-1",
        project_job_link=ProjectJobLink(project_id="project-1", job_id="job-1"),
        line_items=[
            VendorBillLineItem(
                line_item_id="vb-line-1",
                description="Purchased display package",
                quantity=Decimal("1"),
                unit_price=Decimal("5200.00"),
                catalog_item_id="cat-1",
                purchase_order_line_item_id="po-line-1",
            )
        ],
    )

    customer_invoice.issue()
    customer_invoice.mark_sync_pending()
    customer_invoice.mark_sync_failed(error_code="QB-422", error_message="Duplicate")
    customer_invoice.mark_sync_synced("qb-inv-1")

    vendor_bill.issue()
    vendor_bill.mark_sync_pending()
    vendor_bill.mark_sync_synced("qb-bill-1")

    invoice_payload = customer_invoice.to_dict()
    bill_payload = vendor_bill.to_dict()

    assert customer_invoice.status == CustomerInvoiceStatus.ISSUED
    assert invoice_payload["quickbooks_sync_reference"]["external_id"] == "qb-inv-1"
    assert invoice_payload["quickbooks_sync_reference"]["last_error_code"] is None
    assert invoice_payload["quickbooks_sync_reference"]["operation"] == "create"
    assert invoice_payload["quickbooks_sync_reference"]["attempt_count"] == 1
    assert invoice_payload["quickbooks_sync_reference"]["retry_eligible"] is False
    assert bill_payload["quickbooks_sync_reference"]["status"] == "synced"
    assert vendor_bill.status == VendorBillStatus.ENTERED
    assert bill_payload["line_items"][0]["purchase_order_line_item_id"] == "po-line-1"


def test_model_invariants_reject_blank_and_negative_values() -> None:
    with pytest.raises(ValueError, match="customer_id cannot be blank"):
        CustomerAccount(tenant_id="tenant-1", customer_id=" ", name="Acme")

    with pytest.raises(ValueError, match="quantity cannot be negative"):
        EstimateLineItem(
            line_item_id="line-1",
            description="Bad quantity",
            quantity=Decimal("-1"),
        )

    with pytest.raises(
        ValueError, match="quantity_available cannot exceed quantity_on_hand"
    ):
        InventoryPosition(
            tenant_id="tenant-1",
            organization_id="org-1",
            position_id="pos-1",
            catalog_item_id="cat-1",
            location_id="loc-1",
            quantity_on_hand=Decimal("1"),
            quantity_reserved=Decimal("0"),
            quantity_available=Decimal("2"),
        )

    with pytest.raises(ValueError, match="customer invoice can only be issued"):
        CustomerInvoice(
            tenant_id="tenant-1",
            organization_id="org-1",
            customer_invoice_id="ci-2",
            customer_id="customer-1",
            customer_name="Acme",
            status=CustomerInvoiceStatus.ISSUED,
        ).issue()

from __future__ import annotations

from decimal import Decimal
from typing import Any

from atlas_core.contracts import EstimateLineItem
from atlas_core.contracts.commercial_api_contracts import (
    AcceptProposalRequest,
    AddEstimateLineItemRequest,
    CheckInventoryAvailabilityRequest,
    CommercialMvpTenantContext,
    ConvertAcceptedEstimateToSalesOrderRequest,
    CreateCustomerAccountRequest,
    CreateEstimateRequest,
    CreateOpportunityRequest,
    CreateProposalForEstimateRequest,
    CreateVendorBillRequest,
    GenerateCustomerInvoiceFromSalesOrderRequest,
    GetCommercialReportingSnapshotRequest,
    MarkCustomerInvoiceSyncPendingRequest,
    MarkProposalReadyRequest,
    MarkVendorBillSyncPendingRequest,
    RemoveEstimateLineItemRequest,
    ReserveInventoryRequest,
    SendProposalRequest,
)
from atlas_core.repository.local import build_local_tenant_repository_bundle
from atlas_core.services.commercial_mvp_api_boundary import CommercialMvpApiBoundary
from atlas_core.services.commercial_mvp_application_facade import (
    CommercialMvpApplicationFacade,
)
from atlas_core.services.commercial_reporting_service import CommercialReportingService
from atlas_core.services.inventory_service import InventoryService


def _bundle(tenant_id: str, root: str):
    return build_local_tenant_repository_bundle(tenant_id, root)


def _facade(tenant_id: str, root: str) -> CommercialMvpApplicationFacade:
    return CommercialMvpApplicationFacade(_bundle(tenant_id, root))


def _boundary(tenant_id: str, root: str) -> CommercialMvpApiBoundary:
    return CommercialMvpApiBoundary(_facade(tenant_id, root))


def _seed_inventory(service: InventoryService, *, catalog_item_id: str) -> None:
    service.create_catalog_item(
        organization_id="org-1",
        catalog_item_id=catalog_item_id,
        sku=f"SKU-{catalog_item_id}",
        description=f"{catalog_item_id} display",
    )
    service.create_inventory_location(
        organization_id="org-1",
        location_id=f"loc-{catalog_item_id}",
        name=f"Warehouse {catalog_item_id}",
    )
    service.create_inventory_position(
        organization_id="org-1",
        position_id=f"pos-{catalog_item_id}",
        catalog_item_id=catalog_item_id,
        location_id=f"loc-{catalog_item_id}",
        quantity_on_hand=Decimal("10"),
    )


def _payload(response: object) -> dict[str, Any]:
    payload = getattr(response, "payload")
    assert payload is not None
    return payload


def test_commercial_mvp_checkpoint_covers_the_full_current_workflow(tmp_path) -> None:
    root = str(tmp_path / "Atlas")
    tenant_context = CommercialMvpTenantContext(
        tenant_id="tenant-a",
        organization_id="org-1",
    )
    boundary = _boundary("tenant-a", root)
    facade = _facade("tenant-a", root)
    inventory = InventoryService(_bundle("tenant-a", root))
    _seed_inventory(inventory, catalog_item_id="cat-2")

    customer = boundary.create_customer_account(
        CreateCustomerAccountRequest(
            context=tenant_context,
            customer_id="customer-1",
            name="Acme Integrators",
            account_number="A-1",
        )
    )
    opportunity = boundary.create_opportunity(
        CreateOpportunityRequest(
            context=tenant_context,
            customer_id="customer-1",
            opportunity_id="opp-1",
            name="Conference room refresh",
            estimated_value=Decimal("12500.00"),
        )
    )
    estimate = boundary.create_estimate(
        CreateEstimateRequest(
            context=tenant_context,
            customer_id="customer-1",
            estimate_id="est-1",
            opportunity_id="opp-1",
            line_items=[
                EstimateLineItem(
                    line_item_id="line-1",
                    description="Display package",
                    quantity=Decimal("1"),
                    unit_price=Decimal("4500.00"),
                    catalog_item_id="cat-1",
                )
            ],
        )
    )
    estimate = boundary.add_estimate_line_item(
        AddEstimateLineItemRequest(
            context=tenant_context,
            estimate_id="est-1",
            line_item=EstimateLineItem(
                line_item_id="line-2",
                description="Mounting hardware",
                quantity=Decimal("5"),
                unit_price=Decimal("125.00"),
                catalog_item_id="cat-2",
            ),
        )
    )
    estimate = boundary.remove_estimate_line_item(
        RemoveEstimateLineItemRequest(
            context=tenant_context,
            estimate_id="est-1",
            line_item_id="line-1",
        )
    )
    proposal = boundary.create_proposal_for_estimate(
        CreateProposalForEstimateRequest(
            context=tenant_context,
            estimate_id="est-1",
        )
    )
    proposal = boundary.mark_proposal_ready(
        MarkProposalReadyRequest(
            context=tenant_context,
            proposal_id=_payload(proposal)["proposal"]["proposal_id"],
        )
    )
    proposal = boundary.send_proposal(
        SendProposalRequest(
            context=tenant_context,
            proposal_id=_payload(proposal)["proposal"]["proposal_id"],
        )
    )
    proposal = boundary.accept_proposal(
        AcceptProposalRequest(
            context=tenant_context,
            proposal_id=_payload(proposal)["proposal"]["proposal_id"],
        )
    )
    sales_order = boundary.convert_accepted_estimate_to_sales_order(
        ConvertAcceptedEstimateToSalesOrderRequest(
            context=tenant_context,
            estimate_id="est-1",
        )
    )
    sales_order_payload = _payload(sales_order)["sales_order"]
    availability = boundary.check_inventory_availability(
        CheckInventoryAvailabilityRequest(
            context=tenant_context,
            sales_order_id=sales_order_payload["sales_order_id"],
        )
    )
    reservations = boundary.reserve_inventory(
        ReserveInventoryRequest(
            context=tenant_context,
            sales_order_id=sales_order_payload["sales_order_id"],
        )
    )
    invoice = boundary.generate_customer_invoice_from_sales_order(
        GenerateCustomerInvoiceFromSalesOrderRequest(
            context=tenant_context,
            sales_order_id=sales_order_payload["sales_order_id"],
        )
    )
    duplicate_invoice = boundary.generate_customer_invoice_from_sales_order(
        GenerateCustomerInvoiceFromSalesOrderRequest(
            context=tenant_context,
            sales_order_id=sales_order_payload["sales_order_id"],
        )
    )
    vendor_bill = boundary.create_vendor_bill(
        CreateVendorBillRequest(
            context=tenant_context,
            vendor_bill_id="vb-1",
            vendor_id="vendor-1",
            vendor_name="AV Partner",
            line_items=[
                {
                    "line_item_id": "vb-line-1",
                    "description": "Mounting hardware",
                    "quantity": "5",
                    "unit_price": "125.00",
                }
            ],
        )
    )
    invoice_synced = boundary.mark_customer_invoice_sync_pending(
        MarkCustomerInvoiceSyncPendingRequest(
            context=tenant_context,
            customer_invoice_id=_payload(invoice)["customer_invoice"][
                "customer_invoice_id"
            ],
        )
    )
    vendor_bill_synced = boundary.mark_vendor_bill_sync_pending(
        MarkVendorBillSyncPendingRequest(
            context=tenant_context,
            vendor_bill_id=_payload(vendor_bill)["vendor_bill"]["vendor_bill_id"],
        )
    )
    snapshot = boundary.get_commercial_reporting_snapshot(
        GetCommercialReportingSnapshotRequest(context=tenant_context)
    )

    assert customer.ok
    assert opportunity.ok
    assert estimate.ok
    assert proposal.ok
    assert sales_order.ok
    assert availability.ok
    assert reservations.ok
    assert invoice.ok
    assert not duplicate_invoice.ok
    assert vendor_bill.ok
    assert invoice_synced.ok
    assert vendor_bill_synced.ok
    assert snapshot.ok

    assert _payload(customer)["customer_account"]["customer_id"] == "customer-1"
    assert _payload(opportunity)["opportunity"]["customer_id"] == "customer-1"

    proposal_payload = _payload(proposal)["proposal"]
    assert proposal_payload["status"] == "accepted"
    assert proposal_payload["estimate_id"] == "est-1"

    estimate_record = facade.customer_opportunity_estimate_service.get_estimate("est-1")
    assert estimate_record is not None
    assert estimate_record.proposal_id == proposal_payload["proposal_id"]
    assert len(estimate_record.line_items) == 1
    assert estimate_record.line_items[0].line_item_id == "line-2"
    assert estimate_record.line_items[0].quantity == Decimal("5")
    assert estimate_record.line_items[0].unit_price == Decimal("125.00")

    assert sales_order_payload["status"] == "draft"
    assert sales_order_payload["proposal_id"] == proposal_payload["proposal_id"]
    assert sales_order_payload["estimate_id"] == "est-1"
    assert len(sales_order_payload["line_items"]) == 1
    assert sales_order_payload["line_items"][0]["line_item_id"] == "line-2"

    availability_payload = _payload(availability)["availability"]
    assert availability_payload[0]["can_reserve"] is True
    assert availability_payload[0]["selected_location_id"] == "loc-cat-2"
    assert availability_payload[0]["selected_position_id"] == "pos-cat-2"

    reservations_payload = _payload(reservations)["reservations"]
    assert reservations_payload[0]["sales_order_line_item_id"] == "line-2"
    assert reservations_payload[0]["quantity"] == Decimal("5")

    invoice_payload = _payload(invoice)["customer_invoice"]
    assert invoice_payload["sales_order_id"] == sales_order_payload["sales_order_id"]
    assert invoice_payload["status"] == "draft"
    assert len(invoice_payload["line_items"]) == 1
    assert invoice_payload["line_items"][0]["sales_order_line_item_id"] == "line-2"

    assert duplicate_invoice.error is not None
    assert duplicate_invoice.error.code == "validation_error"
    assert "already been invoiced" in duplicate_invoice.error.message

    vendor_bill_payload = _payload(vendor_bill)["vendor_bill"]
    assert vendor_bill_payload["vendor_bill_id"] == "vb-1"
    assert vendor_bill_payload["status"] == "draft"
    assert len(vendor_bill_payload["line_items"]) == 1

    invoice_sync_payload = _payload(invoice_synced)["customer_invoice"]
    vendor_bill_sync_payload = _payload(vendor_bill_synced)["vendor_bill"]
    assert invoice_sync_payload["quickbooks_sync_reference"]["status"] == "pending"
    assert vendor_bill_sync_payload["quickbooks_sync_reference"]["status"] == "pending"

    snapshot_payload = _payload(snapshot)["snapshot"]
    assert snapshot_payload["estimate_pipeline"]["total_estimates"] == 1
    assert snapshot_payload["proposal_statuses"]["total_count"] == 1
    assert snapshot_payload["sales_order_backlog"]["total_count"] == 1
    assert snapshot_payload["invoice_statuses"]["total_count"] == 1
    assert snapshot_payload["vendor_bill_statuses"]["total_count"] == 1
    assert snapshot_payload["quickbooks_sync"]["total_references"] == 2

    assert (
        facade.customer_opportunity_estimate_service.get_estimate("est-1") is not None
    )
    assert (
        facade.proposal_sales_order_service.get_sales_order(
            sales_order_payload["sales_order_id"]
        )
        is not None
    )
    assert (
        facade.invoice_vendor_bill_service.get_customer_invoice(
            invoice_payload["customer_invoice_id"]
        )
        is not None
    )
    assert (
        facade.invoice_vendor_bill_service.get_vendor_bill(
            vendor_bill_payload["vendor_bill_id"]
        )
        is not None
    )
    assert (
        facade.get_commercial_reporting_snapshot(
            organization_id="org-1"
        ).quickbooks_sync.total_references
        == 2
    )

    assert (
        CommercialReportingService(_bundle("tenant-a", root))
        .build_commercial_reporting_snapshot(organization_id="org-1")
        .quickbooks_sync.total_references
        == 2
    )


def test_commercial_mvp_checkpoint_preserves_tenant_isolation(tmp_path) -> None:
    root = str(tmp_path / "Atlas")
    tenant_a_facade = _facade("tenant-a", root)
    tenant_b_facade = _facade("tenant-b", root)
    tenant_a_inventory = InventoryService(_bundle("tenant-a", root))
    tenant_b_inventory = InventoryService(_bundle("tenant-b", root))
    _seed_inventory(tenant_a_inventory, catalog_item_id="cat-2")
    _seed_inventory(tenant_b_inventory, catalog_item_id="cat-2")

    tenant_context_a = CommercialMvpTenantContext(
        tenant_id="tenant-a",
        organization_id="org-1",
    )
    tenant_context_b = CommercialMvpTenantContext(
        tenant_id="tenant-b",
        organization_id="org-1",
    )
    tenant_a_boundary = _boundary("tenant-a", root)
    tenant_b_boundary = _boundary("tenant-b", root)

    tenant_a_boundary.create_customer_account(
        CreateCustomerAccountRequest(
            context=tenant_context_a,
            customer_id="customer-1",
            name="Tenant A Customer",
        )
    )
    tenant_b_boundary.create_customer_account(
        CreateCustomerAccountRequest(
            context=tenant_context_b,
            customer_id="customer-1",
            name="Tenant B Customer",
        )
    )

    tenant_a_boundary.create_opportunity(
        CreateOpportunityRequest(
            context=tenant_context_a,
            customer_id="customer-1",
            opportunity_id="opp-1",
            name="Tenant A Opportunity",
        )
    )
    tenant_b_boundary.create_opportunity(
        CreateOpportunityRequest(
            context=tenant_context_b,
            customer_id="customer-1",
            opportunity_id="opp-1",
            name="Tenant B Opportunity",
        )
    )

    tenant_a_snapshot = tenant_a_boundary.get_commercial_reporting_snapshot(
        GetCommercialReportingSnapshotRequest(context=tenant_context_a)
    )
    tenant_b_snapshot = tenant_b_boundary.get_commercial_reporting_snapshot(
        GetCommercialReportingSnapshotRequest(context=tenant_context_b)
    )

    assert tenant_a_snapshot.ok
    assert tenant_b_snapshot.ok
    assert (
        _payload(tenant_a_snapshot)["snapshot"]["estimate_pipeline"]["total_estimates"]
        == 0
    )
    assert (
        _payload(tenant_b_snapshot)["snapshot"]["estimate_pipeline"]["total_estimates"]
        == 0
    )
    tenant_a_customer = (
        tenant_a_facade.customer_opportunity_estimate_service.get_customer_account(
            "customer-1"
        )
    )
    tenant_b_customer = (
        tenant_b_facade.customer_opportunity_estimate_service.get_customer_account(
            "customer-1"
        )
    )
    assert tenant_a_customer is not None
    assert tenant_b_customer is not None
    assert tenant_a_customer.name == "Tenant A Customer"
    assert tenant_b_customer.name == "Tenant B Customer"

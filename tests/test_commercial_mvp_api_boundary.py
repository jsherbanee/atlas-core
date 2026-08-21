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
    RejectProposalRequest,
    RemoveEstimateLineItemRequest,
    ReserveInventoryRequest,
    SendProposalRequest,
    UpdateEstimateLineItemRequest,
)
from atlas_core.repository.local import build_local_tenant_repository_bundle
from atlas_core.services.commercial_customer_opportunity_estimate_service import (
    CommercialCustomerOpportunityEstimateService,
)
from atlas_core.services.commercial_mvp_api_boundary import CommercialMvpApiBoundary
from atlas_core.services.commercial_mvp_application_facade import (
    CommercialMvpApplicationFacade,
)
from atlas_core.services.commercial_proposal_sales_order_service import (
    CommercialProposalSalesOrderWorkflowService,
)
from atlas_core.services.commercial_reporting_service import (
    CommercialReportingService,
)
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


def _payload(response: Any) -> dict[str, Any]:
    assert response.payload is not None
    return response.payload


def test_api_boundary_maps_commercial_workflow_and_returns_serializable_payloads(
    tmp_path,
) -> None:
    root = str(tmp_path / "Atlas")
    boundary = _boundary("tenant-a", root)
    facade = _facade("tenant-a", root)
    inventory = InventoryService(_bundle("tenant-a", root))
    _seed_inventory(inventory, catalog_item_id="cat-2")
    direct_reporting_service = CommercialReportingService(_bundle("tenant-a", root))

    tenant_context = CommercialMvpTenantContext(
        tenant_id="tenant-a",
        organization_id="org-1",
    )

    customer = boundary.create_customer_account(
        CreateCustomerAccountRequest(
            context=tenant_context,
            customer_id="customer-1",
            name="Acme Integrators",
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
                quantity=Decimal("4"),
                unit_price=Decimal("125.00"),
                catalog_item_id="cat-2",
            ),
        )
    )
    estimate = boundary.update_estimate_line_item(
        UpdateEstimateLineItemRequest(
            context=tenant_context,
            estimate_id="est-1",
            line_item_id="line-2",
            quantity=Decimal("5"),
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
    proposal_payload = _payload(proposal)
    proposal = boundary.mark_proposal_ready(
        MarkProposalReadyRequest(
            context=tenant_context,
            proposal_id=proposal_payload["proposal"]["proposal_id"],
        )
    )
    proposal_payload = _payload(proposal)
    proposal = boundary.send_proposal(
        SendProposalRequest(
            context=tenant_context,
            proposal_id=proposal_payload["proposal"]["proposal_id"],
        )
    )
    proposal_payload = _payload(proposal)
    proposal = boundary.accept_proposal(
        AcceptProposalRequest(
            context=tenant_context,
            proposal_id=proposal_payload["proposal"]["proposal_id"],
        )
    )
    sales_order = boundary.convert_accepted_estimate_to_sales_order(
        ConvertAcceptedEstimateToSalesOrderRequest(
            context=tenant_context,
            estimate_id="est-1",
        )
    )
    sales_order_payload = _payload(sales_order)
    availability = boundary.check_inventory_availability(
        CheckInventoryAvailabilityRequest(
            context=tenant_context,
            sales_order_id=sales_order_payload["sales_order"]["sales_order_id"],
        )
    )
    reservations = boundary.reserve_inventory(
        ReserveInventoryRequest(
            context=tenant_context,
            sales_order_id=sales_order_payload["sales_order"]["sales_order_id"],
        )
    )
    invoice = boundary.generate_customer_invoice_from_sales_order(
        GenerateCustomerInvoiceFromSalesOrderRequest(
            context=tenant_context,
            sales_order_id=sales_order_payload["sales_order"]["sales_order_id"],
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
                    "expense_account_code": "5000",
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

    assert (
        customer.ok
        and _payload(customer)["customer_account"]["name"] == "Acme Integrators"
    )
    assert (
        opportunity.ok
        and _payload(opportunity)["opportunity"]["customer_id"] == "customer-1"
    )
    assert (
        estimate.ok
        and _payload(estimate)["estimate"]["line_items"][0]["line_item_id"] == "line-2"
    )
    assert proposal.ok and _payload(proposal)["proposal"]["status"] == "accepted"
    assert (
        sales_order.ok
        and _payload(sales_order)["sales_order"]["proposal_id"]
        == _payload(proposal)["proposal"]["proposal_id"]
    )
    assert (
        availability.ok
        and _payload(availability)["availability"][0]["can_reserve"] is True
    )
    assert reservations.ok
    assert (
        _payload(reservations)["reservations"][0]["sales_order_line_item_id"]
        == "line-2"
    )
    assert (
        invoice.ok
        and _payload(invoice)["customer_invoice"]["sales_order_id"]
        == _payload(sales_order)["sales_order"]["sales_order_id"]
    )
    assert (
        vendor_bill.ok
        and _payload(vendor_bill)["vendor_bill"]["vendor_bill_id"] == "vb-1"
    )
    assert (
        invoice_synced.ok
        and _payload(invoice_synced)["customer_invoice"]["quickbooks_sync_reference"][
            "status"
        ]
        == "pending"
    )
    assert (
        vendor_bill_synced.ok
        and _payload(vendor_bill_synced)["vendor_bill"]["quickbooks_sync_reference"][
            "status"
        ]
        == "pending"
    )
    assert (
        snapshot.ok
        and _payload(snapshot)["snapshot"]["quickbooks_sync"]["total_references"] == 2
    )

    direct_facade_snapshot = facade.get_commercial_reporting_snapshot(
        organization_id="org-1"
    )
    direct_customer_service = CommercialCustomerOpportunityEstimateService(
        _bundle("tenant-a", root)
    )
    direct_workflow_service = CommercialProposalSalesOrderWorkflowService(
        _bundle("tenant-a", root)
    )

    assert direct_customer_service.get_estimate("est-1") is not None
    assert (
        direct_workflow_service.get_sales_order(
            _payload(sales_order)["sales_order"]["sales_order_id"]
        )
        is not None
    )
    assert direct_facade_snapshot.quickbooks_sync.total_references == 2
    assert (
        direct_reporting_service.build_commercial_reporting_snapshot(
            organization_id="org-1"
        ).quickbooks_sync.total_references
        == 2
    )


def test_api_boundary_returns_deterministic_validation_and_tenant_errors(
    tmp_path,
) -> None:
    root = str(tmp_path / "Atlas")
    boundary = _boundary("tenant-a", root)

    missing_context = boundary.create_customer_account(
        {
            "customer_id": "customer-1",
            "name": "Broken",
        }
    )
    tenant_mismatch = boundary.create_customer_account(
        CreateCustomerAccountRequest(
            context=CommercialMvpTenantContext(
                tenant_id="tenant-b",
                organization_id="org-1",
            ),
            customer_id="customer-2",
            name="Wrong Tenant",
        )
    )

    assert not missing_context.ok
    assert missing_context.error is not None
    assert missing_context.error.code == "validation_error"
    assert not tenant_mismatch.ok
    assert tenant_mismatch.error is not None
    assert tenant_mismatch.error.code == "tenant_mismatch"
    assert tenant_mismatch.error.field == "tenant_id"


def test_api_boundary_returns_empty_snapshot_and_isolates_tenants(tmp_path) -> None:
    root = str(tmp_path / "Atlas")
    boundary_a = _boundary("tenant-a", root)
    boundary_b = _boundary("tenant-b", root)

    empty_snapshot = boundary_a.get_commercial_reporting_snapshot(
        GetCommercialReportingSnapshotRequest(
            context=CommercialMvpTenantContext(
                tenant_id="tenant-a",
                organization_id="org-1",
            )
        )
    )
    isolated_customer = boundary_a.create_customer_account(
        CreateCustomerAccountRequest(
            context=CommercialMvpTenantContext(
                tenant_id="tenant-b",
                organization_id="org-1",
            ),
            customer_id="customer-1",
            name="Tenant B Customer",
        )
    )
    boundary_b_customer = boundary_b.create_customer_account(
        CreateCustomerAccountRequest(
            context=CommercialMvpTenantContext(
                tenant_id="tenant-b",
                organization_id="org-1",
            ),
            customer_id="customer-1",
            name="Tenant B Customer",
        )
    )
    boundary_b.create_opportunity(
        CreateOpportunityRequest(
            context=CommercialMvpTenantContext(
                tenant_id="tenant-b",
                organization_id="org-1",
            ),
            customer_id="customer-1",
            opportunity_id="opp-1",
            name="Tenant B Opportunity",
        )
    )
    boundary_b.create_estimate(
        CreateEstimateRequest(
            context=CommercialMvpTenantContext(
                tenant_id="tenant-b",
                organization_id="org-1",
            ),
            customer_id="customer-1",
            estimate_id="est-1",
            opportunity_id="opp-1",
        )
    )
    proposal_b = boundary_b.create_proposal_for_estimate(
        CreateProposalForEstimateRequest(
            context=CommercialMvpTenantContext(
                tenant_id="tenant-b",
                organization_id="org-1",
            ),
            estimate_id="est-1",
        )
    )
    proposal_b_payload = _payload(proposal_b)
    boundary_b.mark_proposal_ready(
        MarkProposalReadyRequest(
            context=CommercialMvpTenantContext(
                tenant_id="tenant-b",
                organization_id="org-1",
            ),
            proposal_id=proposal_b_payload["proposal"]["proposal_id"],
        )
    )
    boundary_b.send_proposal(
        SendProposalRequest(
            context=CommercialMvpTenantContext(
                tenant_id="tenant-b",
                organization_id="org-1",
            ),
            proposal_id=proposal_b_payload["proposal"]["proposal_id"],
        )
    )
    rejected_proposal = boundary_b.reject_proposal(
        RejectProposalRequest(
            context=CommercialMvpTenantContext(
                tenant_id="tenant-b",
                organization_id="org-1",
            ),
            proposal_id=proposal_b_payload["proposal"]["proposal_id"],
        )
    )

    assert empty_snapshot.ok
    empty_snapshot_payload = _payload(empty_snapshot)
    assert (
        empty_snapshot_payload["snapshot"]["estimate_pipeline"]["total_estimates"] == 0
    )
    assert empty_snapshot_payload["snapshot"]["proposal_statuses"]["total_count"] == 0
    assert (
        empty_snapshot_payload["snapshot"]["quickbooks_sync"]["total_references"] == 0
    )
    assert rejected_proposal.ok
    assert _payload(rejected_proposal)["proposal"]["status"] == "declined"
    assert not isolated_customer.ok
    assert isolated_customer.error is not None
    assert isolated_customer.error.code == "tenant_mismatch"
    assert boundary_b_customer.ok

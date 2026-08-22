from __future__ import annotations

from decimal import Decimal

from atlas_core.contracts import EstimateLineItem
from atlas_core.repository.local import build_local_tenant_repository_bundle
from atlas_core.services.commercial_customer_opportunity_estimate_service import (
    CommercialCustomerOpportunityEstimateService,
)
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


def _seed_inventory(
    service: InventoryService, *, sku: str, catalog_item_id: str
) -> None:
    service.create_catalog_item(
        organization_id="org-1",
        catalog_item_id=catalog_item_id,
        sku=sku,
        description=f"{sku} display",
    )
    service.create_inventory_location(
        organization_id="org-1",
        location_id=f"loc-{sku}",
        name=f"Warehouse {sku}",
    )
    service.create_inventory_position(
        organization_id="org-1",
        position_id=f"pos-{sku}",
        catalog_item_id=catalog_item_id,
        location_id=f"loc-{sku}",
        quantity_on_hand=Decimal("10"),
    )


def _seed_facade_workflow(
    facade: CommercialMvpApplicationFacade,
    *,
    customer_name: str = "Acme Integrators",
    opportunity_name: str = "Conference room refresh",
) -> str:
    facade.create_customer_account(
        organization_id="org-1",
        customer_id="customer-1",
        name=customer_name,
    )
    facade.create_opportunity(
        organization_id="org-1",
        opportunity_id="opp-1",
        customer_id="customer-1",
        name=opportunity_name,
        estimated_value=Decimal("12500.00"),
    )
    facade.create_estimate(
        organization_id="org-1",
        estimate_id="est-1",
        customer_id="customer-1",
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
        notes=["Initial discovery complete"],
    )
    facade.add_estimate_line_item(
        "est-1",
        EstimateLineItem(
            line_item_id="line-2",
            description="Mounting hardware",
            quantity=Decimal("4"),
            unit_price=Decimal("125.00"),
            catalog_item_id="cat-2",
        ),
    )
    facade.update_estimate_line_item(
        "est-1",
        "line-2",
        quantity=Decimal("5"),
    )
    facade.remove_estimate_line_item("est-1", "line-1")
    proposal = facade.create_proposal_for_estimate("est-1")
    facade.mark_proposal_ready(proposal.proposal_id)
    facade.send_proposal(proposal.proposal_id)
    facade.accept_proposal(proposal.proposal_id)
    sales_order = facade.convert_accepted_estimate_to_sales_order("est-1")
    return sales_order.sales_order_id


def test_facade_orchestrates_commercial_mvp_workflow(tmp_path) -> None:
    root = str(tmp_path / "Atlas")
    facade = _facade("tenant-a", root)
    inventory = InventoryService(_bundle("tenant-a", root))
    _seed_inventory(inventory, sku="SKU-1", catalog_item_id="cat-2")

    sales_order_id = _seed_facade_workflow(facade)

    availability = facade.check_inventory_availability_for_sales_order(sales_order_id)
    reservations = facade.reserve_inventory_for_sales_order(sales_order_id)
    invoice = facade.generate_customer_invoice_from_sales_order(sales_order_id)
    vendor_bill = facade.create_vendor_bill(
        organization_id="org-1",
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
    invoice_synced = facade.mark_customer_invoice_sync_pending(
        invoice.customer_invoice_id
    )
    vendor_bill_synced = facade.mark_vendor_bill_sync_pending(
        vendor_bill.vendor_bill_id
    )
    snapshot = facade.get_commercial_reporting_snapshot(organization_id="org-1")

    customer_service = CommercialCustomerOpportunityEstimateService(
        _bundle("tenant-a", root)
    )
    workflow_service = CommercialProposalSalesOrderWorkflowService(
        _bundle("tenant-a", root)
    )
    reporting_service = CommercialReportingService(_bundle("tenant-a", root))

    assert customer_service.get_estimate("est-1") is not None
    assert workflow_service.get_sales_order(sales_order_id) is not None
    assert (
        reporting_service.build_commercial_reporting_snapshot(
            organization_id="org-1"
        ).invoice_statuses.total_count
        == 1
    )
    assert availability[0].can_reserve is True
    assert availability[0].catalog_item_id == "cat-2"
    assert availability[0].selected_location_id == "loc-SKU-1"
    assert reservations[0].sales_order_line_item_id == "line-2"
    assert reservations[0].quantity == Decimal("5")
    assert invoice.sales_order_id == sales_order_id
    assert vendor_bill.vendor_bill_id == "vb-1"
    assert invoice_synced.quickbooks_sync_reference is not None
    assert vendor_bill_synced.quickbooks_sync_reference is not None
    assert snapshot.quickbooks_sync.counts_by_status["pending"] == 2
    assert snapshot.invoice_statuses.total_count == 1
    assert snapshot.vendor_bill_statuses.total_count == 1


def test_facade_preserves_tenant_isolation(tmp_path) -> None:
    root = str(tmp_path / "Atlas")
    facade_a = _facade("tenant-a", root)
    facade_b = _facade("tenant-b", root)
    inventory_a = InventoryService(_bundle("tenant-a", root))
    inventory_b = InventoryService(_bundle("tenant-b", root))
    _seed_inventory(inventory_a, sku="SKU-A", catalog_item_id="cat-2")
    _seed_inventory(inventory_b, sku="SKU-B", catalog_item_id="cat-2")

    sales_order_a = _seed_facade_workflow(
        facade_a,
        customer_name="Tenant A Customer",
        opportunity_name="Tenant A Opportunity",
    )
    sales_order_b = _seed_facade_workflow(
        facade_b,
        customer_name="Tenant B Customer",
        opportunity_name="Tenant B Opportunity",
    )

    reservation_a = facade_a.reserve_inventory_for_sales_order(sales_order_a)
    reservation_b = facade_b.reserve_inventory_for_sales_order(sales_order_b)

    snapshot_a = facade_a.get_commercial_reporting_snapshot(organization_id="org-1")
    snapshot_b = facade_b.get_commercial_reporting_snapshot(organization_id="org-1")

    assert reservation_a[0].reservation_id == "res-so-est-1-line-2"
    assert reservation_b[0].reservation_id == "res-so-est-1-line-2"
    customer_a = facade_a.customer_opportunity_estimate_service.get_customer_account(
        "customer-1"
    )
    customer_b = facade_b.customer_opportunity_estimate_service.get_customer_account(
        "customer-1"
    )
    assert customer_a is not None
    assert customer_b is not None
    assert customer_a.name == "Tenant A Customer"
    assert customer_b.name == "Tenant B Customer"
    assert snapshot_a.quickbooks_sync.total_references == 0
    assert snapshot_b.quickbooks_sync.total_references == 0
    assert inventory_a.get_available_quantity("cat-2", "loc-SKU-A") == Decimal("5")
    assert inventory_b.get_available_quantity("cat-2", "loc-SKU-B") == Decimal("5")

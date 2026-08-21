from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from atlas_core.contracts import (
    CatalogItem,
    ChangeOrder,
    CustomerAccount,
    CustomerInvoice,
    CustomerInvoiceLineItem,
    Estimate,
    EstimateLineItem,
    InventoryLocation,
    InventoryPosition,
    InventoryReservation,
    Opportunity,
    ProcurementNeed,
    Proposal,
    QuickBooksSyncOperation,
    QuickBooksSyncReference,
    SalesOrder,
    SalesOrderLineItem,
    VendorBill,
    VendorBillLineItem,
)
from atlas_core.repository.local import build_local_tenant_repository_bundle
from atlas_core.repository.project_manager import AtlasProjectManager


def _customer_account() -> CustomerAccount:
    return CustomerAccount(
        tenant_id="tenant-a",
        organization_id="org-1",
        customer_id="customer-1",
        name="Acme Integrators",
        billing_email="ops@acme.example",
    )


def _opportunity() -> Opportunity:
    return Opportunity(
        tenant_id="tenant-a",
        organization_id="org-1",
        opportunity_id="opp-1",
        customer_id="customer-1",
        name="Conference room refresh",
        estimated_value=Decimal("12500.00"),
    )


def _estimate() -> Estimate:
    return Estimate(
        tenant_id="tenant-a",
        organization_id="org-1",
        estimate_id="est-1",
        customer_id="customer-1",
        opportunity_id="opp-1",
        proposal_id="prop-1",
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


def _proposal() -> Proposal:
    proposal = Proposal(
        tenant_id="tenant-a",
        organization_id="org-1",
        proposal_id="prop-1",
        estimate_id="est-1",
        customer_id="customer-1",
    )
    proposal.mark_ready()
    proposal.send()
    return proposal


def _sales_order() -> SalesOrder:
    return SalesOrder(
        tenant_id="tenant-a",
        organization_id="org-1",
        sales_order_id="so-1",
        customer_id="customer-1",
        estimate_id="est-1",
        proposal_id="prop-1",
        line_items=[
            SalesOrderLineItem(
                line_item_id="so-line-1",
                description="Core display package",
                quantity=Decimal("2"),
                unit_price=Decimal("4500.00"),
                catalog_item_id="cat-1",
                estimate_line_item_id="est-line-1",
            )
        ],
    )


def _change_order() -> ChangeOrder:
    return ChangeOrder(
        tenant_id="tenant-a",
        organization_id="org-1",
        change_order_id="co-1",
        sales_order_id="so-1",
        line_items=[
            SalesOrderLineItem(
                line_item_id="co-line-1",
                description="Add cable pathway",
                quantity=Decimal("1"),
                unit_price=Decimal("250.00"),
                catalog_item_id="cat-2",
                change_order_id="co-1",
            )
        ],
    )


def _catalog_item() -> CatalogItem:
    return CatalogItem(
        tenant_id="tenant-a",
        organization_id="org-1",
        catalog_item_id="cat-1",
        sku="SKU-1",
        description="Display",
        list_price=Decimal("1200.00"),
    )


def _inventory_location() -> InventoryLocation:
    return InventoryLocation(
        tenant_id="tenant-a",
        organization_id="org-1",
        location_id="loc-1",
        name="Main warehouse",
        code="WH1",
    )


def _inventory_position() -> InventoryPosition:
    return InventoryPosition(
        tenant_id="tenant-a",
        organization_id="org-1",
        position_id="pos-1",
        catalog_item_id="cat-1",
        location_id="loc-1",
        quantity_on_hand=Decimal("10"),
        quantity_reserved=Decimal("2"),
        quantity_available=Decimal("8"),
    )


def _inventory_reservation() -> InventoryReservation:
    return InventoryReservation(
        tenant_id="tenant-a",
        organization_id="org-1",
        reservation_id="res-1",
        catalog_item_id="cat-1",
        location_id="loc-1",
        quantity=Decimal("3"),
        sales_order_line_item_id="so-line-1",
    )


def _procurement_need() -> ProcurementNeed:
    return ProcurementNeed(
        tenant_id="tenant-a",
        organization_id="org-1",
        procurement_need_id="need-1",
        catalog_item_id="cat-1",
        quantity_required=Decimal("3"),
        sales_order_id="so-1",
        vendor_id="vendor-1",
    )


def _customer_invoice() -> CustomerInvoice:
    return CustomerInvoice(
        tenant_id="tenant-a",
        organization_id="org-1",
        customer_invoice_id="ci-1",
        customer_id="customer-1",
        customer_name="Acme Integrators",
        estimate_id="est-1",
        sales_order_id="so-1",
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
        quickbooks_sync_reference=QuickBooksSyncReference(
            tenant_id="tenant-a",
            organization_id="org-1",
            sync_reference_id="ci-sync-1",
            entity_type="customer_invoice",
            entity_id="ci-1",
        ),
    )


def _vendor_bill() -> VendorBill:
    return VendorBill(
        tenant_id="tenant-a",
        organization_id="org-1",
        vendor_bill_id="vb-1",
        vendor_id="vendor-1",
        vendor_name="Acme Supply",
        purchase_order_id="po-1",
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
        quickbooks_sync_reference=QuickBooksSyncReference(
            tenant_id="tenant-a",
            organization_id="org-1",
            sync_reference_id="vb-sync-1",
            entity_type="vendor_bill",
            entity_id="vb-1",
        ),
    )


def test_commercial_records_save_load_list_and_update(tmp_path: Path) -> None:
    bundle = build_local_tenant_repository_bundle("tenant-a", tmp_path / "Atlas")
    manager = AtlasProjectManager(repositories=bundle)
    repo = manager.commercial_repository
    assert repo is not None

    repo.save_customer_account(_customer_account())
    repo.save_opportunity(_opportunity())
    repo.save_proposal(_proposal())
    repo.save_estimate(_estimate())
    repo.save_sales_order(_sales_order())
    repo.save_change_order(_change_order())
    repo.save_catalog_item(_catalog_item())
    repo.save_inventory_location(_inventory_location())
    repo.save_inventory_position(_inventory_position())
    repo.save_inventory_reservation(_inventory_reservation())
    repo.save_procurement_need(_procurement_need())
    repo.save_customer_invoice(_customer_invoice())
    repo.save_vendor_bill(_vendor_bill())

    customer = repo.load_customer_account("customer-1")
    opportunity = repo.load_opportunity("opp-1")
    proposal = repo.load_proposal("prop-1")
    estimate = repo.load_estimate("est-1")
    sales_order = repo.load_sales_order("so-1")
    change_order = repo.load_change_order("co-1")
    catalog_item = repo.load_catalog_item("cat-1")
    inventory_location = repo.load_inventory_location("loc-1")
    inventory_position = repo.load_inventory_position("pos-1")
    inventory_reservation = repo.load_inventory_reservation("res-1")
    procurement_need = repo.load_procurement_need("need-1")
    customer_invoice = repo.load_customer_invoice("ci-1")
    vendor_bill = repo.load_vendor_bill("vb-1")

    assert customer is not None and customer.billing_email == "ops@acme.example"
    assert (
        opportunity is not None
        and opportunity.to_dict()["estimated_value"] == "12500.00"
    )
    assert proposal is not None and proposal.status.value == "sent"
    assert estimate is not None and estimate.line_items[0].line_item_id == "est-line-1"
    assert (
        sales_order is not None
        and sales_order.line_items[0].estimate_line_item_id == "est-line-1"
    )
    assert (
        change_order is not None
        and change_order.line_items[0].change_order_id == "co-1"
    )
    assert catalog_item is not None and catalog_item.sku == "SKU-1"
    assert inventory_location is not None and inventory_location.code == "WH1"
    assert (
        inventory_position is not None
        and inventory_position.quantity_available == Decimal("8")
    )
    assert (
        inventory_reservation is not None
        and inventory_reservation.quantity == Decimal("3")
    )
    assert procurement_need is not None and procurement_need.vendor_id == "vendor-1"
    assert (
        customer_invoice is not None
        and customer_invoice.line_items[0].sales_order_line_item_id == "so-line-1"
    )
    assert customer_invoice.quickbooks_sync_reference is not None
    assert customer_invoice.quickbooks_sync_reference.sync_reference_id == "ci-sync-1"
    assert (
        vendor_bill is not None
        and vendor_bill.line_items[0].purchase_order_line_item_id == "po-line-1"
    )
    assert vendor_bill.quickbooks_sync_reference is not None
    assert vendor_bill.quickbooks_sync_reference.sync_reference_id == "vb-sync-1"

    updated_customer = _customer_account()
    updated_customer.billing_email = "billing@acme.example"
    repo.save_customer_account(updated_customer)
    loaded_updated_customer = repo.load_customer_account("customer-1")
    assert loaded_updated_customer is not None
    assert loaded_updated_customer.billing_email == "billing@acme.example"
    assert len(repo.list_customer_accounts()) == 1
    assert len(repo.list_opportunities()) == 1
    assert len(repo.list_proposals()) == 1
    assert len(repo.list_estimates()) == 1
    assert len(repo.list_sales_orders()) == 1
    assert len(repo.list_change_orders()) == 1
    assert len(repo.list_catalog_items()) == 1
    assert len(repo.list_inventory_locations()) == 1
    assert len(repo.list_inventory_positions()) == 1
    assert len(repo.list_inventory_reservations()) == 1
    assert len(repo.list_procurement_needs()) == 1
    assert len(repo.list_customer_invoices()) == 1
    assert len(repo.list_vendor_bills()) == 1


def test_tenant_bundles_cannot_see_each_others_commercial_records(
    tmp_path: Path,
) -> None:
    tenant_a = AtlasProjectManager(
        repositories=build_local_tenant_repository_bundle(
            "tenant-a", tmp_path / "Atlas"
        )
    )
    tenant_b = AtlasProjectManager(
        repositories=build_local_tenant_repository_bundle(
            "tenant-b", tmp_path / "Atlas"
        )
    )

    assert tenant_a.commercial_repository is not None
    assert tenant_b.commercial_repository is not None
    tenant_a.commercial_repository.save_customer_account(_customer_account())
    tenant_b.commercial_repository.save_customer_account(
        CustomerAccount(
            tenant_id="tenant-b",
            organization_id="org-1",
            customer_id="customer-2",
            name="Beta Integrators",
        )
    )

    assert (
        tenant_a.commercial_repository.load_customer_account("customer-1") is not None
    )
    assert tenant_a.commercial_repository.load_customer_account("customer-2") is None
    assert tenant_b.commercial_repository.load_customer_account("customer-1") is None
    assert (
        tenant_b.commercial_repository.load_customer_account("customer-2") is not None
    )


def test_quickbooks_sync_reference_persists_and_updates(tmp_path: Path) -> None:
    repo = AtlasProjectManager(
        repositories=build_local_tenant_repository_bundle(
            "tenant-a", tmp_path / "Atlas"
        )
    ).commercial_repository
    assert repo is not None

    reference = QuickBooksSyncReference(
        tenant_id="tenant-a",
        organization_id="org-1",
        sync_reference_id="sync-1",
        entity_type="customer_invoice",
        entity_id="ci-1",
        operation=QuickBooksSyncOperation.UPDATE,
        idempotency_key="sync-key-1",
    )
    reference.mark_pending()
    reference.mark_failed(error_code="QB-422", error_message="Duplicate")
    repo.save_quickbooks_sync_reference(reference)

    loaded = repo.load_quickbooks_sync_reference("sync-1")
    assert loaded is not None
    assert loaded.status.value == "failed"
    assert loaded.last_error_code == "QB-422"
    assert loaded.last_error_message == "Duplicate"
    assert loaded.operation == QuickBooksSyncOperation.UPDATE
    assert loaded.idempotency_key == "sync-key-1"
    assert loaded.retry_eligible is True
    assert loaded.attempt_count == 1

    reference.mark_synced("qb-sync-1")
    repo.save_quickbooks_sync_reference(reference)
    loaded_reference = repo.load_quickbooks_sync_reference("sync-1")
    assert loaded_reference is not None
    assert loaded_reference.external_id == "qb-sync-1"
    assert loaded_reference.status.value == "synced"
    assert loaded_reference.retry_eligible is False

from __future__ import annotations

from decimal import Decimal

import pytest

from atlas_core.contracts import EstimateLineItem, VendorManufacturerReference
from atlas_core.repository.local import build_local_tenant_repository_bundle
from atlas_core.services.commercial_proposal_sales_order_service import (
    CommercialProposalSalesOrderWorkflowService,
)
from atlas_core.services.inventory_service import InventoryService


def _inventory_service(tenant_id: str, root: str) -> InventoryService:
    return InventoryService(build_local_tenant_repository_bundle(tenant_id, root))


def _workflow_service(
    tenant_id: str,
    root: str,
) -> CommercialProposalSalesOrderWorkflowService:
    return CommercialProposalSalesOrderWorkflowService(
        build_local_tenant_repository_bundle(tenant_id, root)
    )


def _seed_sales_order(
    service: CommercialProposalSalesOrderWorkflowService,
) -> str:
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
    return sales_order.line_items[0].line_item_id


def test_catalog_location_position_and_availability_workflow(tmp_path) -> None:
    service = _inventory_service("tenant-a", str(tmp_path / "Atlas"))

    catalog_item = service.create_catalog_item(
        organization_id="org-1",
        catalog_item_id="cat-1",
        sku="SKU-1",
        description="Display processor",
        unit_of_measure="ea",
        list_price=Decimal("1200.00"),
        vendor_manufacturer_reference=VendorManufacturerReference(
            vendor_id="vendor-1",
            manufacturer_name="QSC",
            vendor_name="AV Partner",
            vendor_part_number="AV-123",
        ),
    )
    updated_catalog_item = service.update_catalog_item(
        "cat-1",
        description="Updated display processor",
        active=False,
        external_reference="ext-1",
    )

    location = service.create_inventory_location(
        organization_id="org-1",
        location_id="loc-1",
        name="Main warehouse",
        code="WH1",
    )
    updated_location = service.update_inventory_location(
        "loc-1",
        name="Primary warehouse",
        active=False,
    )

    position = service.create_inventory_position(
        organization_id="org-1",
        position_id="pos-1",
        catalog_item_id="cat-1",
        location_id="loc-1",
        quantity_on_hand=Decimal("10"),
        quantity_reserved=Decimal("2"),
    )
    updated_position = service.update_inventory_position(
        "pos-1",
        quantity_on_hand=Decimal("12"),
        quantity_reserved=Decimal("3"),
    )

    loaded_catalog_item = service.get_catalog_item("cat-1")
    assert loaded_catalog_item is not None
    loaded_location = service.get_inventory_location("loc-1")
    loaded_position = service.get_inventory_position("pos-1")

    assert catalog_item.vendor_manufacturer_reference is not None
    assert updated_catalog_item.description == "Updated display processor"
    assert updated_catalog_item.active is False
    assert location.code == "WH1"
    assert updated_location.active is False
    assert position.quantity_available == Decimal("8")
    assert updated_position.quantity_available == Decimal("9")
    assert service.get_available_quantity("cat-1", "loc-1") == Decimal("9")
    assert loaded_catalog_item.external_reference == "ext-1"
    assert loaded_location is not None
    assert loaded_location.name == "Primary warehouse"
    assert loaded_position is not None
    assert loaded_position.quantity_reserved == Decimal("3")
    assert [item.catalog_item_id for item in service.list_catalog_items()] == ["cat-1"]
    assert [item.location_id for item in service.list_inventory_locations()] == [
        "loc-1"
    ]
    assert [item.position_id for item in service.list_inventory_positions()] == [
        "pos-1"
    ]


def test_reservations_reduce_restore_and_allocate_deterministically(tmp_path) -> None:
    service = _inventory_service("tenant-a", str(tmp_path / "Atlas"))
    sales_order_line_item_id = _seed_sales_order(
        _workflow_service("tenant-a", str(tmp_path / "Atlas"))
    )

    service.create_catalog_item(
        organization_id="org-1",
        catalog_item_id="cat-1",
        sku="SKU-1",
        description="Display processor",
    )
    service.create_inventory_location(
        organization_id="org-1",
        location_id="loc-1",
        name="Main warehouse",
    )
    service.create_inventory_position(
        organization_id="org-1",
        position_id="pos-1",
        catalog_item_id="cat-1",
        location_id="loc-1",
        quantity_on_hand=Decimal("10"),
    )

    reservation = service.create_inventory_reservation(
        organization_id="org-1",
        reservation_id="res-1",
        catalog_item_id="cat-1",
        location_id="loc-1",
        quantity=Decimal("4"),
        sales_order_line_item_id=sales_order_line_item_id,
    )
    assert reservation.status.value == "reserved"
    assert service.get_available_quantity("cat-1", "loc-1") == Decimal("6")

    with pytest.raises(ValueError, match="reservation exceeds available quantity"):
        service.create_inventory_reservation(
            organization_id="org-1",
            reservation_id="res-2",
            catalog_item_id="cat-1",
            location_id="loc-1",
            quantity=Decimal("7"),
        )

    cancelled = service.cancel_inventory_reservation("res-1")
    assert cancelled.status.value == "cancelled"
    assert service.get_available_quantity("cat-1", "loc-1") == Decimal("10")

    reservation_two = service.create_inventory_reservation(
        organization_id="org-1",
        reservation_id="res-2",
        catalog_item_id="cat-1",
        location_id="loc-1",
        quantity=Decimal("5"),
        sales_order_line_item_id=sales_order_line_item_id,
    )
    allocated = service.allocate_inventory_reservation("res-2")
    assert reservation_two.status.value == "reserved"
    assert allocated.status.value == "fulfilled"
    assert service.get_available_quantity("cat-1", "loc-1") == Decimal("10")

    with pytest.raises(
        ValueError, match="inventory reservation can only be fulfilled when reserved"
    ):
        service.allocate_inventory_reservation("res-2")


def test_inventory_rejects_invalid_references_and_preserves_tenant_scope(
    tmp_path,
) -> None:
    service_a = _inventory_service("tenant-a", str(tmp_path / "Atlas"))
    service_b = _inventory_service("tenant-b", str(tmp_path / "Atlas"))

    service_a.create_catalog_item(
        organization_id="org-1",
        catalog_item_id="cat-1",
        sku="SKU-1",
        description="Display processor",
    )
    service_a.create_inventory_location(
        organization_id="org-1",
        location_id="loc-1",
        name="Main warehouse",
    )
    service_a.create_inventory_position(
        organization_id="org-1",
        position_id="pos-1",
        catalog_item_id="cat-1",
        location_id="loc-1",
        quantity_on_hand=Decimal("2"),
    )

    service_b.create_catalog_item(
        organization_id="org-1",
        catalog_item_id="cat-1",
        sku="SKU-2",
        description="Tenant B display",
    )

    catalog_item_a = service_a.get_catalog_item("cat-1")
    catalog_item_b = service_b.get_catalog_item("cat-1")
    assert catalog_item_a is not None
    assert catalog_item_b is not None
    assert catalog_item_a.sku == "SKU-1"
    assert catalog_item_b.sku == "SKU-2"
    assert service_a.get_catalog_item("missing") is None
    assert service_b.get_inventory_location("loc-1") is None
    assert [item.sku for item in service_a.list_catalog_items()] == ["SKU-1"]
    assert [item.sku for item in service_b.list_catalog_items()] == ["SKU-2"]

    with pytest.raises(ValueError, match="reservation exceeds available quantity"):
        service_a.create_inventory_reservation(
            organization_id="org-1",
            reservation_id="res-1",
            catalog_item_id="cat-1",
            location_id="loc-1",
            quantity=Decimal("3"),
        )

    with pytest.raises(ValueError, match="sales order line item was not found"):
        service_a.create_inventory_reservation(
            organization_id="org-1",
            reservation_id="res-2",
            catalog_item_id="cat-1",
            location_id="loc-1",
            quantity=Decimal("1"),
            sales_order_line_item_id="missing-line",
        )

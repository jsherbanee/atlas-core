"""Tenant-scoped inventory service for catalog, availability, and reservations."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from atlas_core.contracts.commercial_spine_contracts import (
    CatalogItem,
    ChangeOrder,
    InventoryLocation,
    InventoryPosition,
    InventoryReservation,
    InventoryReservationStatus,
    ProjectJobLink,
    SalesOrder,
    VendorManufacturerReference,
)

if TYPE_CHECKING:
    from atlas_core.repository.contracts import RepositoryBundle


_UNSET = object()


class InventoryService:
    """Tenant-scoped inventory state, availability, and reservation behavior."""

    def __init__(self, repositories: "RepositoryBundle") -> None:
        if repositories.commercial_repository is None:
            raise ValueError("commercial repository is required for inventory service")
        self.repositories = repositories
        self.commercial_repository = repositories.commercial_repository
        if repositories.tenant_id is None:
            raise ValueError("tenant_id is required for inventory service")
        self.tenant_id = repositories.tenant_id

    def create_catalog_item(
        self,
        *,
        organization_id: str,
        catalog_item_id: str,
        sku: str,
        description: str,
        unit_of_measure: str = "ea",
        list_price: Decimal = Decimal("0"),
        active: bool = True,
        vendor_manufacturer_reference: (
            VendorManufacturerReference | dict[str, Any] | None
        ) = None,
        external_reference: str | None = None,
    ) -> CatalogItem:
        if (
            self.get_catalog_item(catalog_item_id, organization_id=organization_id)
            is not None
        ):
            raise ValueError("catalog item already exists")
        record = CatalogItem(
            tenant_id=self.tenant_id,
            organization_id=organization_id,
            catalog_item_id=catalog_item_id,
            sku=sku,
            description=description,
            unit_of_measure=unit_of_measure,
            list_price=list_price,
            active=active,
            vendor_manufacturer_reference=self._normalize_vendor_manufacturer_reference(
                vendor_manufacturer_reference
            ),
            external_reference=external_reference,
        )
        self.commercial_repository.save_catalog_item(record)
        return record

    def update_catalog_item(
        self,
        catalog_item_id: str,
        *,
        organization_id: str | None = None,
        sku: Any = _UNSET,
        description: Any = _UNSET,
        unit_of_measure: Any = _UNSET,
        list_price: Any = _UNSET,
        active: Any = _UNSET,
        vendor_manufacturer_reference: Any = _UNSET,
        external_reference: Any = _UNSET,
    ) -> CatalogItem:
        record = self.get_catalog_item(catalog_item_id, organization_id=organization_id)
        if record is None:
            raise ValueError("catalog item was not found")
        payload = record.to_dict()
        if sku is not _UNSET:
            payload["sku"] = sku
        if description is not _UNSET:
            payload["description"] = description
        if unit_of_measure is not _UNSET:
            payload["unit_of_measure"] = unit_of_measure
        if list_price is not _UNSET:
            payload["list_price"] = str(list_price)
        if active is not _UNSET:
            payload["active"] = active
        if vendor_manufacturer_reference is not _UNSET:
            payload["vendor_manufacturer_reference"] = (
                self._normalize_vendor_manufacturer_reference(
                    vendor_manufacturer_reference
                )
            )
        if external_reference is not _UNSET:
            payload["external_reference"] = external_reference
        updated = CatalogItem(**payload)
        self.commercial_repository.save_catalog_item(updated)
        return updated

    def get_catalog_item(
        self,
        catalog_item_id: str,
        *,
        organization_id: str | None = None,
    ) -> CatalogItem | None:
        record = self.commercial_repository.load_catalog_item(catalog_item_id)
        if record is None:
            return None
        if record.tenant_id != self.tenant_id:
            return None
        if organization_id is not None and record.organization_id != organization_id:
            return None
        return record

    def list_catalog_items(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[CatalogItem]:
        items = self.commercial_repository.list_catalog_items()
        return self._filter_organization(items, organization_id)

    def create_inventory_location(
        self,
        *,
        organization_id: str,
        location_id: str,
        name: str,
        code: str | None = None,
        active: bool = True,
    ) -> InventoryLocation:
        if (
            self.get_inventory_location(location_id, organization_id=organization_id)
            is not None
        ):
            raise ValueError("inventory location already exists")
        record = InventoryLocation(
            tenant_id=self.tenant_id,
            organization_id=organization_id,
            location_id=location_id,
            name=name,
            code=code,
            active=active,
        )
        self.commercial_repository.save_inventory_location(record)
        return record

    def update_inventory_location(
        self,
        location_id: str,
        *,
        organization_id: str | None = None,
        name: Any = _UNSET,
        code: Any = _UNSET,
        active: Any = _UNSET,
    ) -> InventoryLocation:
        record = self.get_inventory_location(
            location_id, organization_id=organization_id
        )
        if record is None:
            raise ValueError("inventory location was not found")
        payload = record.to_dict()
        if name is not _UNSET:
            payload["name"] = name
        if code is not _UNSET:
            payload["code"] = code
        if active is not _UNSET:
            payload["active"] = active
        updated = InventoryLocation(**payload)
        self.commercial_repository.save_inventory_location(updated)
        return updated

    def get_inventory_location(
        self,
        location_id: str,
        *,
        organization_id: str | None = None,
    ) -> InventoryLocation | None:
        record = self.commercial_repository.load_inventory_location(location_id)
        if record is None:
            return None
        if record.tenant_id != self.tenant_id:
            return None
        if organization_id is not None and record.organization_id != organization_id:
            return None
        return record

    def list_inventory_locations(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[InventoryLocation]:
        locations = self.commercial_repository.list_inventory_locations()
        return self._filter_organization(locations, organization_id)

    def create_inventory_position(
        self,
        *,
        organization_id: str,
        position_id: str,
        catalog_item_id: str,
        location_id: str,
        quantity_on_hand: Decimal,
        quantity_reserved: Decimal = Decimal("0"),
        quantity_available: Decimal | None = None,
    ) -> InventoryPosition:
        self._require_catalog_item(catalog_item_id, organization_id=organization_id)
        self._require_inventory_location(location_id, organization_id=organization_id)
        if (
            self.get_inventory_position(position_id, organization_id=organization_id)
            is not None
        ):
            raise ValueError("inventory position already exists")
        reserved = quantity_reserved
        available = (
            quantity_available
            if quantity_available is not None
            else quantity_on_hand - reserved
        )
        record = InventoryPosition(
            tenant_id=self.tenant_id,
            organization_id=organization_id,
            position_id=position_id,
            catalog_item_id=catalog_item_id,
            location_id=location_id,
            quantity_on_hand=quantity_on_hand,
            quantity_reserved=reserved,
            quantity_available=available,
        )
        self._validate_position(record)
        self.commercial_repository.save_inventory_position(record)
        return record

    def update_inventory_position(
        self,
        position_id: str,
        *,
        organization_id: str | None = None,
        catalog_item_id: Any = _UNSET,
        location_id: Any = _UNSET,
        quantity_on_hand: Any = _UNSET,
        quantity_reserved: Any = _UNSET,
        quantity_available: Any = _UNSET,
    ) -> InventoryPosition:
        record = self.get_inventory_position(
            position_id, organization_id=organization_id
        )
        if record is None:
            raise ValueError("inventory position was not found")
        payload = record.to_dict()
        if catalog_item_id is not _UNSET:
            payload["catalog_item_id"] = catalog_item_id
        if location_id is not _UNSET:
            payload["location_id"] = location_id
        if quantity_on_hand is not _UNSET:
            payload["quantity_on_hand"] = str(quantity_on_hand)
        if quantity_reserved is not _UNSET:
            payload["quantity_reserved"] = str(quantity_reserved)
        if quantity_available is not _UNSET:
            payload["quantity_available"] = str(quantity_available)
        else:
            payload["quantity_available"] = str(
                Decimal(str(payload["quantity_on_hand"]))
                - Decimal(str(payload["quantity_reserved"]))
            )
        updated = InventoryPosition(**payload)
        self._validate_position(updated)
        self.commercial_repository.save_inventory_position(updated)
        return updated

    def get_inventory_position(
        self,
        position_id: str,
        *,
        organization_id: str | None = None,
    ) -> InventoryPosition | None:
        record = self.commercial_repository.load_inventory_position(position_id)
        if record is None:
            return None
        if record.tenant_id != self.tenant_id:
            return None
        if organization_id is not None and record.organization_id != organization_id:
            return None
        return record

    def list_inventory_positions(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[InventoryPosition]:
        positions = self.commercial_repository.list_inventory_positions()
        return self._filter_organization(positions, organization_id)

    def get_available_quantity(
        self,
        catalog_item_id: str,
        location_id: str,
        *,
        organization_id: str | None = None,
    ) -> Decimal:
        position = self._require_inventory_position(
            catalog_item_id,
            location_id,
            organization_id=organization_id,
        )
        self._refresh_position_availability(position)
        return position.quantity_available

    def create_inventory_reservation(
        self,
        *,
        organization_id: str,
        reservation_id: str,
        catalog_item_id: str,
        location_id: str,
        quantity: Decimal,
        sales_order_line_item_id: str | None = None,
        change_order_id: str | None = None,
        project_job_link: ProjectJobLink | dict[str, Any] | None = None,
    ) -> InventoryReservation:
        if (
            self.get_inventory_reservation(
                reservation_id, organization_id=organization_id
            )
            is not None
        ):
            raise ValueError("inventory reservation already exists")
        position = self._require_inventory_position(
            catalog_item_id,
            location_id,
            organization_id=organization_id,
        )
        available = self._refresh_position_availability(position)
        if quantity > available:
            raise ValueError("reservation exceeds available quantity")
        self._validate_reservation_demand_references(
            sales_order_line_item_id=sales_order_line_item_id,
            change_order_id=change_order_id,
        )
        record = InventoryReservation(
            tenant_id=self.tenant_id,
            organization_id=organization_id,
            reservation_id=reservation_id,
            catalog_item_id=catalog_item_id,
            location_id=location_id,
            quantity=quantity,
            sales_order_line_item_id=sales_order_line_item_id,
            change_order_id=change_order_id,
            project_job_link=self._normalize_project_job_link(project_job_link),
        )
        record.reserve()
        self.commercial_repository.save_inventory_reservation(record)
        position.quantity_reserved += quantity
        position.quantity_available = (
            position.quantity_on_hand - position.quantity_reserved
        )
        self._validate_position(position)
        self.commercial_repository.save_inventory_position(position)
        return record

    def update_inventory_reservation(
        self,
        reservation_id: str,
        *,
        organization_id: str | None = None,
        quantity: Any = _UNSET,
        sales_order_line_item_id: Any = _UNSET,
        change_order_id: Any = _UNSET,
        project_job_link: Any = _UNSET,
    ) -> InventoryReservation:
        record = self.get_inventory_reservation(
            reservation_id,
            organization_id=organization_id,
        )
        if record is None:
            raise ValueError("inventory reservation was not found")
        payload = record.to_dict()
        if quantity is not _UNSET:
            if record.status == InventoryReservationStatus.RESERVED:
                position = self._require_inventory_position(
                    record.catalog_item_id,
                    record.location_id,
                    organization_id=record.organization_id,
                )
                available = self._refresh_position_availability(position)
                allowed_quantity = available + record.quantity
                if Decimal(str(quantity)) > allowed_quantity:
                    raise ValueError("reservation exceeds available quantity")
            payload["quantity"] = str(quantity)
        if sales_order_line_item_id is not _UNSET:
            payload["sales_order_line_item_id"] = sales_order_line_item_id
        if change_order_id is not _UNSET:
            payload["change_order_id"] = change_order_id
        if project_job_link is not _UNSET:
            payload["project_job_link"] = self._normalize_project_job_link(
                project_job_link
            )
        self._validate_reservation_demand_references(
            sales_order_line_item_id=payload.get("sales_order_line_item_id"),
            change_order_id=payload.get("change_order_id"),
        )
        updated = InventoryReservation(**payload)
        self.commercial_repository.save_inventory_reservation(updated)
        self._recalculate_inventory_position(
            updated.catalog_item_id, updated.location_id
        )
        return updated

    def cancel_inventory_reservation(
        self,
        reservation_id: str,
        *,
        organization_id: str | None = None,
    ) -> InventoryReservation:
        return self._transition_inventory_reservation(
            reservation_id,
            organization_id=organization_id,
            transition="cancel",
        )

    def allocate_inventory_reservation(
        self,
        reservation_id: str,
        *,
        organization_id: str | None = None,
    ) -> InventoryReservation:
        return self._transition_inventory_reservation(
            reservation_id,
            organization_id=organization_id,
            transition="fulfill",
        )

    def get_inventory_reservation(
        self,
        reservation_id: str,
        *,
        organization_id: str | None = None,
    ) -> InventoryReservation | None:
        record = self.commercial_repository.load_inventory_reservation(reservation_id)
        if record is None:
            return None
        if record.tenant_id != self.tenant_id:
            return None
        if organization_id is not None and record.organization_id != organization_id:
            return None
        return record

    def list_inventory_reservations(
        self,
        *,
        organization_id: str | None = None,
    ) -> list[InventoryReservation]:
        reservations = self.commercial_repository.list_inventory_reservations()
        return self._filter_organization(reservations, organization_id)

    def _require_catalog_item(
        self,
        catalog_item_id: str,
        *,
        organization_id: str,
    ) -> CatalogItem:
        record = self.get_catalog_item(catalog_item_id, organization_id=organization_id)
        if record is None:
            raise ValueError("catalog item was not found")
        return record

    def _require_inventory_location(
        self,
        location_id: str,
        *,
        organization_id: str,
    ) -> InventoryLocation:
        record = self.get_inventory_location(
            location_id, organization_id=organization_id
        )
        if record is None:
            raise ValueError("inventory location was not found")
        return record

    def _require_inventory_position(
        self,
        catalog_item_id: str,
        location_id: str,
        *,
        organization_id: str | None,
    ) -> InventoryPosition:
        matches = [
            record
            for record in self.list_inventory_positions(organization_id=organization_id)
            if record.catalog_item_id == catalog_item_id
            and record.location_id == location_id
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            matches.sort(key=lambda record: record.position_id)
            return matches[0]
        raise ValueError("inventory position was not found")

    def _refresh_position_availability(self, position: InventoryPosition) -> Decimal:
        self._validate_position(position)
        return position.quantity_available

    def _transition_inventory_reservation(
        self,
        reservation_id: str,
        *,
        organization_id: str | None,
        transition: str,
    ) -> InventoryReservation:
        record = self.get_inventory_reservation(
            reservation_id,
            organization_id=organization_id,
        )
        if record is None:
            raise ValueError("inventory reservation was not found")
        position = self._require_inventory_position(
            record.catalog_item_id,
            record.location_id,
            organization_id=record.organization_id,
        )
        before_status = record.status
        if transition == "cancel":
            record.cancel()
            if before_status == InventoryReservationStatus.RESERVED:
                position.quantity_reserved -= record.quantity
        elif transition == "fulfill":
            record.fulfill()
            if before_status == InventoryReservationStatus.RESERVED:
                position.quantity_reserved -= record.quantity
        else:
            raise ValueError("unknown inventory reservation transition")
        position.quantity_available = (
            position.quantity_on_hand - position.quantity_reserved
        )
        self._validate_position(position)
        self.commercial_repository.save_inventory_reservation(record)
        self.commercial_repository.save_inventory_position(position)
        return record

    def _validate_reservation_demand_references(
        self,
        *,
        sales_order_line_item_id: str | None,
        change_order_id: str | None,
    ) -> None:
        if sales_order_line_item_id is not None:
            self._require_sales_order_line_item(sales_order_line_item_id)
        if change_order_id is not None:
            self._require_change_order(change_order_id)

    def _require_sales_order_line_item(
        self, sales_order_line_item_id: str
    ) -> SalesOrder:
        for sales_order in self.commercial_repository.list_sales_orders():
            if sales_order.tenant_id != self.tenant_id:
                continue
            for line_item in sales_order.line_items:
                if line_item.line_item_id == sales_order_line_item_id:
                    return sales_order
        raise ValueError("sales order line item was not found")

    def _require_change_order(self, change_order_id: str) -> ChangeOrder:
        for change_order in self.commercial_repository.list_change_orders():
            if change_order.tenant_id != self.tenant_id:
                continue
            if change_order.change_order_id == change_order_id:
                return change_order
        raise ValueError("change order was not found")

    def _recalculate_inventory_position(
        self, catalog_item_id: str, location_id: str
    ) -> None:
        position = self._require_inventory_position(
            catalog_item_id,
            location_id,
            organization_id=None,
        )
        self._refresh_position_availability(position)

    @staticmethod
    def _normalize_project_job_link(
        value: ProjectJobLink | dict[str, Any] | None,
    ) -> ProjectJobLink | None:
        if value is None:
            return None
        if isinstance(value, ProjectJobLink):
            return value
        return ProjectJobLink(**value)

    @staticmethod
    def _normalize_vendor_manufacturer_reference(
        value: VendorManufacturerReference | dict[str, Any] | None,
    ) -> VendorManufacturerReference | None:
        if value is None:
            return None
        if isinstance(value, VendorManufacturerReference):
            return value
        return VendorManufacturerReference(**value)

    @staticmethod
    def _filter_organization(
        records: list[Any], organization_id: str | None
    ) -> list[Any]:
        if organization_id is None:
            return [
                record
                for record in records
                if getattr(record, "tenant_id", None) is not None
            ]
        return [
            record
            for record in records
            if getattr(record, "organization_id", None) == organization_id
        ]

    @staticmethod
    def _validate_position(record: InventoryPosition) -> None:
        if record.quantity_reserved > record.quantity_on_hand:
            raise ValueError("quantity_reserved cannot exceed quantity_on_hand")
        if record.quantity_available > record.quantity_on_hand:
            raise ValueError("quantity_available cannot exceed quantity_on_hand")
        if (
            record.quantity_available
            != record.quantity_on_hand - record.quantity_reserved
        ):
            raise ValueError(
                "quantity_available must equal quantity_on_hand minus quantity_reserved"
            )


__all__ = ["InventoryService"]

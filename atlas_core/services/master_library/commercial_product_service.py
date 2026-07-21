"""Commercial product foundation service for Atlas Core."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
import hashlib
import io
import json
import re
import tempfile
import uuid
from typing import Any
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile
from pypdf import PdfReader

from atlas_core.domain.commercial_product import (
    CanonicalProduct,
    PriceListVersionRecord,
    ProductCommercialMetadata,
    ProductEngineeringMetadata,
    ProductFutureHooks,
    ImportDiagnosticSeverity,
    ProductLifecycleStatus,
    ProductPriceHistoryRecord,
    PriceSheetVersionStatus,
    VendorOfferingRecord,
)
from atlas_core.services.document_intake_service import DocumentIntakeService

ALLOWED_PURCHASING_CHANNELS = {
    "direct_from_manufacturer",
    "distributor",
    "dealer_reseller",
    "other",
}
ALLOWED_IMPORT_STATUSES = {"draft", "imported", "finalized", "failed"}
ALLOWED_PRICE_RECORD_RESOLUTION = {
    "unresolved",
    "resolved_product",
    "resolved_vendor_offering",
}
ALLOWED_CURRENCIES = {"USD", "CAD", "EUR", "GBP", "AUD", "JPY"}
SUPPORTED_KNOWLEDGE_ENTITY_TYPES = {
    "customer",
    "service",
    "manufacturer",
    "vendor",
    "product",
    "organization",
    "contact",
    "location",
    "project",
}


class CommercialProductService:
    def __init__(
        self,
        state: dict[str, Any] | None = None,
        *,
        as_of: date | None = None,
    ) -> None:
        self._as_of = as_of or datetime.now(UTC).date()
        self.state = self._normalized_state(state or self.empty_state())

    @staticmethod
    def empty_state() -> dict[str, Any]:
        return {
            "manufacturers": {},
            "vendors": {},
            "products": {},
            "vendor_offerings": {},
            "price_sheets": {},
            "price_list_versions": {},
            "price_records": {},
            "price_sheet_drafts": {},
            "mapping_profiles": {},
            "product_price_history": {},
            "import_index": {},
            "project_only_products": {},
            "knowledge_entities": {},
            "knowledge_relationships": {},
            "knowledge_audit_log": [],
        }

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.state, sort_keys=True))

    # Manufacturer management
    def create_manufacturer(
        self,
        *,
        manufacturer_id: str,
        canonical_name: str,
        display_name: str | None = None,
        manufacturer_code: str | None = None,
        website: str | None = None,
        aliases: list[str] | None = None,
        notes: str = "",
        active: bool = True,
    ) -> dict[str, Any]:
        normalized_name = self.normalize_name(canonical_name)
        duplicates = self.detect_duplicate_manufacturers(
            canonical_name=canonical_name,
            normalized_name=normalized_name,
        )
        if duplicates:
            raise ValueError(
                "Duplicate manufacturer canonical/normalized name detected"
            )

        created = self._now_iso()
        record = {
            "manufacturer_id": self._safe(manufacturer_id),
            "canonical_name": self._safe(canonical_name),
            "display_name": self._safe(display_name, self._safe(canonical_name)),
            "normalized_name": normalized_name,
            "manufacturer_code": self._safe(manufacturer_code),
            "website": self._safe(website),
            "aliases": [
                self._safe(item) for item in list(aliases or []) if self._safe(item)
            ],
            "active": bool(active),
            "notes": self._safe(notes),
            "created_at": created,
            "updated_at": created,
        }
        if not record["manufacturer_id"]:
            raise ValueError("manufacturer_id cannot be blank")
        self.state.setdefault("manufacturers", {})[record["manufacturer_id"]] = record
        manufacturer_aliases_raw = record.get("aliases")
        manufacturer_aliases = (
            list(manufacturer_aliases_raw)
            if isinstance(manufacturer_aliases_raw, list)
            else []
        )
        self._upsert_knowledge_entity(
            entity_id=f"manufacturer:{record['manufacturer_id']}",
            entity_type="manufacturer",
            canonical_name=self._safe(record.get("canonical_name"), ""),
            display_name=self._safe(record.get("display_name"), ""),
            aliases=manufacturer_aliases,
            notes=self._safe(record.get("notes"), ""),
            active=bool(record.get("active", True)),
            attributes={
                "manufacturer_id": record["manufacturer_id"],
                "manufacturer_code": record.get("manufacturer_code"),
                "website": record.get("website"),
            },
            fail_on_duplicate=False,
        )
        return dict(record)

    def get_manufacturer(self, manufacturer_id: str) -> dict[str, Any] | None:
        return (
            dict(
                self.state.get("manufacturers", {}).get(self._safe(manufacturer_id), {})
            )
            or None
        )

    def list_manufacturers(
        self, *, include_inactive: bool = True
    ) -> list[dict[str, Any]]:
        rows = list(self.state.get("manufacturers", {}).values())
        if not include_inactive:
            rows = [item for item in rows if bool(item.get("active", True))]
        rows.sort(key=lambda item: self._safe(item.get("canonical_name"), "").lower())
        return [dict(item) for item in rows]

    def search_manufacturers(self, query: str) -> list[dict[str, Any]]:
        q = self.normalize_name(query)
        if not q:
            return self.list_manufacturers()
        return [
            item
            for item in self.list_manufacturers()
            if q in self.normalize_name(item.get("canonical_name", ""))
            or q in self.normalize_name(item.get("display_name", ""))
            or any(
                q in self.normalize_name(alias)
                for alias in list(item.get("aliases") or [])
            )
        ]

    def update_manufacturer(
        self, manufacturer_id: str, *, updates: dict[str, Any]
    ) -> dict[str, Any]:
        current = self.get_manufacturer(manufacturer_id)
        if current is None:
            raise ValueError("Manufacturer not found")
        candidate_name = self._safe(
            updates.get("canonical_name"), current["canonical_name"]
        )
        candidate_norm = self.normalize_name(candidate_name)
        duplicates = [
            item
            for item in self.detect_duplicate_manufacturers(
                canonical_name=candidate_name,
                normalized_name=candidate_norm,
            )
            if self._safe(item.get("manufacturer_id"), "")
            != self._safe(manufacturer_id)
        ]
        if duplicates:
            raise ValueError(
                "Duplicate manufacturer canonical/normalized name detected"
            )

        current["canonical_name"] = candidate_name
        current["display_name"] = self._safe(
            updates.get("display_name"),
            self._safe(current.get("display_name"), candidate_name),
        )
        current["normalized_name"] = candidate_norm
        current["manufacturer_code"] = self._safe(
            updates.get("manufacturer_code"),
            self._safe(current.get("manufacturer_code"), ""),
        )
        current["website"] = self._safe(
            updates.get("website"), self._safe(current.get("website"), "")
        )
        if "aliases" in updates:
            current["aliases"] = [
                self._safe(item)
                for item in list(updates.get("aliases") or [])
                if self._safe(item)
            ]
        current["notes"] = self._safe(
            updates.get("notes"), self._safe(current.get("notes"), "")
        )
        current["updated_at"] = self._now_iso()
        self.state.setdefault("manufacturers", {})[
            self._safe(manufacturer_id)
        ] = current
        self._upsert_knowledge_entity(
            entity_id=f"manufacturer:{self._safe(manufacturer_id)}",
            entity_type="manufacturer",
            canonical_name=current["canonical_name"],
            display_name=current["display_name"],
            aliases=list(current.get("aliases") or []),
            notes=current["notes"],
            active=bool(current.get("active", True)),
            attributes={
                "manufacturer_id": self._safe(manufacturer_id),
                "manufacturer_code": current.get("manufacturer_code"),
                "website": current.get("website"),
            },
            fail_on_duplicate=False,
        )
        return dict(current)

    def set_manufacturer_active(
        self, manufacturer_id: str, active: bool
    ) -> dict[str, Any]:
        return self._set_manufacturer_active(manufacturer_id, active)

    def _set_manufacturer_active(
        self, manufacturer_id: str, active: bool
    ) -> dict[str, Any]:
        current = self.get_manufacturer(manufacturer_id)
        if current is None:
            raise ValueError("Manufacturer not found")
        current["active"] = bool(active)
        current["updated_at"] = self._now_iso()
        self.state.setdefault("manufacturers", {})[
            self._safe(manufacturer_id)
        ] = current
        self._set_knowledge_entity_active(
            entity_id=f"manufacturer:{self._safe(manufacturer_id)}",
            active=bool(active),
        )
        return dict(current)

    def detect_duplicate_manufacturers(
        self,
        *,
        canonical_name: str,
        normalized_name: str | None = None,
    ) -> list[dict[str, Any]]:
        target_norm = normalized_name or self.normalize_name(canonical_name)
        return [
            dict(item)
            for item in self.state.get("manufacturers", {}).values()
            if self.normalize_name(item.get("canonical_name", "")) == target_norm
            or self.normalize_name(item.get("normalized_name", "")) == target_norm
        ]

    # Vendor management
    def create_vendor(
        self,
        *,
        vendor_id: str,
        canonical_name: str,
        display_name: str | None = None,
        vendor_code: str | None = None,
        website: str | None = None,
        aliases: list[str] | None = None,
        notes: str = "",
        active: bool = True,
    ) -> dict[str, Any]:
        normalized_name = self.normalize_name(canonical_name)
        duplicates = self.detect_duplicate_vendors(
            canonical_name=canonical_name,
            normalized_name=normalized_name,
        )
        if duplicates:
            raise ValueError("Duplicate vendor canonical/normalized name detected")

        created = self._now_iso()
        record = {
            "vendor_id": self._safe(vendor_id),
            "canonical_name": self._safe(canonical_name),
            "display_name": self._safe(display_name, self._safe(canonical_name)),
            "normalized_name": normalized_name,
            "vendor_code": self._safe(vendor_code),
            "website": self._safe(website),
            "aliases": [
                self._safe(item) for item in list(aliases or []) if self._safe(item)
            ],
            "active": bool(active),
            "notes": self._safe(notes),
            "created_at": created,
            "updated_at": created,
        }
        if not record["vendor_id"]:
            raise ValueError("vendor_id cannot be blank")
        self.state.setdefault("vendors", {})[record["vendor_id"]] = record
        vendor_aliases_raw = record.get("aliases")
        vendor_aliases = (
            list(vendor_aliases_raw) if isinstance(vendor_aliases_raw, list) else []
        )
        self._upsert_knowledge_entity(
            entity_id=f"vendor:{record['vendor_id']}",
            entity_type="vendor",
            canonical_name=self._safe(record.get("canonical_name"), ""),
            display_name=self._safe(record.get("display_name"), ""),
            aliases=vendor_aliases,
            notes=self._safe(record.get("notes"), ""),
            active=bool(record.get("active", True)),
            attributes={
                "vendor_id": record["vendor_id"],
                "vendor_code": record.get("vendor_code"),
                "website": record.get("website"),
            },
            fail_on_duplicate=False,
        )
        return dict(record)

    def get_vendor(self, vendor_id: str) -> dict[str, Any] | None:
        return (
            dict(self.state.get("vendors", {}).get(self._safe(vendor_id), {})) or None
        )

    def list_vendors(self, *, include_inactive: bool = True) -> list[dict[str, Any]]:
        rows = list(self.state.get("vendors", {}).values())
        if not include_inactive:
            rows = [item for item in rows if bool(item.get("active", True))]
        rows.sort(key=lambda item: self._safe(item.get("canonical_name"), "").lower())
        return [dict(item) for item in rows]

    def search_vendors(self, query: str) -> list[dict[str, Any]]:
        q = self.normalize_name(query)
        if not q:
            return self.list_vendors()
        return [
            item
            for item in self.list_vendors()
            if q in self.normalize_name(item.get("canonical_name", ""))
            or q in self.normalize_name(item.get("display_name", ""))
            or any(
                q in self.normalize_name(alias)
                for alias in list(item.get("aliases") or [])
            )
        ]

    def update_vendor(
        self, vendor_id: str, *, updates: dict[str, Any]
    ) -> dict[str, Any]:
        current = self.get_vendor(vendor_id)
        if current is None:
            raise ValueError("Vendor not found")
        candidate_name = self._safe(
            updates.get("canonical_name"), current["canonical_name"]
        )
        candidate_norm = self.normalize_name(candidate_name)
        duplicates = [
            item
            for item in self.detect_duplicate_vendors(
                canonical_name=candidate_name,
                normalized_name=candidate_norm,
            )
            if self._safe(item.get("vendor_id"), "") != self._safe(vendor_id)
        ]
        if duplicates:
            raise ValueError("Duplicate vendor canonical/normalized name detected")

        current["canonical_name"] = candidate_name
        current["display_name"] = self._safe(
            updates.get("display_name"),
            self._safe(current.get("display_name"), candidate_name),
        )
        current["normalized_name"] = candidate_norm
        current["vendor_code"] = self._safe(
            updates.get("vendor_code"),
            self._safe(current.get("vendor_code"), ""),
        )
        current["website"] = self._safe(
            updates.get("website"), self._safe(current.get("website"), "")
        )
        if "aliases" in updates:
            current["aliases"] = [
                self._safe(item)
                for item in list(updates.get("aliases") or [])
                if self._safe(item)
            ]
        current["notes"] = self._safe(
            updates.get("notes"), self._safe(current.get("notes"), "")
        )
        current["updated_at"] = self._now_iso()
        self.state.setdefault("vendors", {})[self._safe(vendor_id)] = current
        self._upsert_knowledge_entity(
            entity_id=f"vendor:{self._safe(vendor_id)}",
            entity_type="vendor",
            canonical_name=current["canonical_name"],
            display_name=current["display_name"],
            aliases=list(current.get("aliases") or []),
            notes=current["notes"],
            active=bool(current.get("active", True)),
            attributes={
                "vendor_id": self._safe(vendor_id),
                "vendor_code": current.get("vendor_code"),
                "website": current.get("website"),
            },
            fail_on_duplicate=False,
        )
        return dict(current)

    def set_vendor_active(self, vendor_id: str, active: bool) -> dict[str, Any]:
        current = self.get_vendor(vendor_id)
        if current is None:
            raise ValueError("Vendor not found")
        current["active"] = bool(active)
        current["updated_at"] = self._now_iso()
        self.state.setdefault("vendors", {})[self._safe(vendor_id)] = current
        self._set_knowledge_entity_active(
            entity_id=f"vendor:{self._safe(vendor_id)}",
            active=bool(active),
        )
        return dict(current)

    def detect_duplicate_vendors(
        self,
        *,
        canonical_name: str,
        normalized_name: str | None = None,
    ) -> list[dict[str, Any]]:
        target_norm = normalized_name or self.normalize_name(canonical_name)
        return [
            dict(item)
            for item in self.state.get("vendors", {}).values()
            if self.normalize_name(item.get("canonical_name", "")) == target_norm
            or self.normalize_name(item.get("normalized_name", "")) == target_norm
        ]

    # Product management
    def create_product(
        self,
        *,
        manufacturer_id: str,
        manufacturer: str,
        manufacturer_part_number: str,
        product_name: str,
        product_description: str,
        category: str,
        lifecycle_status: str = ProductLifecycleStatus.PENDING_VERIFICATION.value,
        active: bool = True,
        replacement_product_uuid: str | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        if not self.get_manufacturer(manufacturer_id):
            raise ValueError("Products require a valid manufacturer reference")
        normalized_part = self.normalize_part_number(manufacturer_part_number)
        manufacturer_key = self._safe(manufacturer)
        duplicate = self.find_product_by_identity(
            manufacturer=manufacturer_key,
            normalized_part_number=normalized_part,
        )
        if duplicate is not None:
            raise ValueError(
                "Duplicate product identity for manufacturer + normalized part number"
            )

        product_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"product::{manufacturer_key.upper()}::{normalized_part}",
            )
        )
        record = CanonicalProduct(
            atlas_product_uuid=product_id,
            manufacturer=manufacturer_key,
            manufacturer_sku=self._safe(manufacturer_part_number),
            canonical_sku=self._safe(manufacturer_part_number),
            description=self._safe(product_description),
            product_family="General",
            category=self._safe(category, "other"),
            discipline="general",
            lifecycle_status=self._lifecycle(lifecycle_status),
            active=bool(active),
            replacement_product_uuid=self._safe(replacement_product_uuid) or None,
        ).to_dict()
        record["manufacturer_id"] = self._safe(manufacturer_id)
        record["manufacturer_part_number"] = self._safe(manufacturer_part_number)
        record["normalized_manufacturer_part_number"] = normalized_part
        record["product_name"] = self._safe(product_name)
        record["product_description"] = self._safe(product_description)
        record["discontinued"] = bool(
            self._safe(record.get("lifecycle_status"), "")
            in {
                ProductLifecycleStatus.DISCONTINUED.value,
                ProductLifecycleStatus.END_OF_LIFE.value,
                ProductLifecycleStatus.OBSOLETE.value,
            }
        )
        record["notes"] = self._safe(notes)
        product_key = self._product_key(
            manufacturer=manufacturer_key,
            canonical_sku=self._safe(record.get("canonical_sku"), ""),
            manufacturer_sku=self._safe(record.get("manufacturer_sku"), ""),
        )
        self.state.setdefault("products", {})[product_key] = record
        self._upsert_knowledge_entity(
            entity_id=f"product:{record['atlas_product_uuid']}",
            entity_type="product",
            canonical_name=self._safe(record.get("canonical_sku"), "Unknown Product"),
            display_name=self._safe(
                record.get("product_name"),
                self._safe(record.get("canonical_sku"), "Unknown Product"),
            ),
            aliases=[
                self._safe(record.get("manufacturer_part_number"), ""),
                self._safe(record.get("manufacturer_sku"), ""),
            ],
            notes=self._safe(record.get("notes"), ""),
            active=bool(record.get("active", True)),
            attributes={
                "atlas_product_uuid": record.get("atlas_product_uuid"),
                "manufacturer_id": record.get("manufacturer_id"),
                "manufacturer": record.get("manufacturer"),
                "manufacturer_part_number": record.get("manufacturer_part_number"),
                "normalized_manufacturer_part_number": record.get(
                    "normalized_manufacturer_part_number"
                ),
                "category": record.get("category"),
                "lifecycle_status": record.get("lifecycle_status"),
            },
            fail_on_duplicate=False,
        )
        return dict(record)

    # Knowledge entity framework
    def create_customer(
        self,
        *,
        customer_id: str,
        canonical_name: str,
        display_name: str | None = None,
        aliases: list[str] | None = None,
        notes: str = "",
        active: bool = True,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._safe(customer_id):
            raise ValueError("customer_id cannot be blank")
        return self._upsert_knowledge_entity(
            entity_id=f"customer:{self._safe(customer_id)}",
            entity_type="customer",
            canonical_name=canonical_name,
            display_name=display_name,
            aliases=list(aliases or []),
            notes=notes,
            active=active,
            attributes={
                "customer_id": self._safe(customer_id),
                **dict(attributes or {}),
            },
            fail_on_duplicate=True,
        )

    def create_service_entity(
        self,
        *,
        service_id: str,
        canonical_name: str,
        display_name: str | None = None,
        aliases: list[str] | None = None,
        notes: str = "",
        active: bool = True,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._safe(service_id):
            raise ValueError("service_id cannot be blank")
        return self._upsert_knowledge_entity(
            entity_id=f"service:{self._safe(service_id)}",
            entity_type="service",
            canonical_name=canonical_name,
            display_name=display_name,
            aliases=list(aliases or []),
            notes=notes,
            active=active,
            attributes={"service_id": self._safe(service_id), **dict(attributes or {})},
            fail_on_duplicate=True,
        )

    def create_contact(
        self,
        *,
        contact_id: str,
        canonical_name: str,
        display_name: str | None = None,
        aliases: list[str] | None = None,
        email: str | None = None,
        phone: str | None = None,
        title: str | None = None,
        organization: str | None = None,
        external_identifier: str | None = None,
        notes: str = "",
        active: bool = True,
        attributes: dict[str, Any] | None = None,
        relationships: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self._safe(contact_id):
            raise ValueError("contact_id cannot be blank")
        record = self._upsert_knowledge_entity(
            entity_id=f"contact:{self._safe(contact_id)}",
            entity_type="contact",
            canonical_name=canonical_name,
            display_name=display_name,
            aliases=list(aliases or []),
            notes=notes,
            active=active,
            attributes={
                "contact_id": self._safe(contact_id),
                "email": self._safe(email),
                "phone": self._safe(phone),
                "title": self._safe(title),
                "organization": self._safe(organization),
                "external_identifier": self._safe(external_identifier),
                **dict(attributes or {}),
            },
            fail_on_duplicate=True,
        )
        self._upsert_relationship_specs(relationships or [])
        return record

    def create_location(
        self,
        *,
        location_id: str,
        canonical_name: str,
        display_name: str | None = None,
        aliases: list[str] | None = None,
        address_line1: str | None = None,
        address_line2: str | None = None,
        city: str | None = None,
        state: str | None = None,
        postal_code: str | None = None,
        country: str | None = None,
        external_identifier: str | None = None,
        notes: str = "",
        active: bool = True,
        attributes: dict[str, Any] | None = None,
        relationships: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self._safe(location_id):
            raise ValueError("location_id cannot be blank")
        record = self._upsert_knowledge_entity(
            entity_id=f"location:{self._safe(location_id)}",
            entity_type="location",
            canonical_name=canonical_name,
            display_name=display_name,
            aliases=list(aliases or []),
            notes=notes,
            active=active,
            attributes={
                "location_id": self._safe(location_id),
                "address_line1": self._safe(address_line1),
                "address_line2": self._safe(address_line2),
                "city": self._safe(city),
                "state": self._safe(state),
                "postal_code": self._safe(postal_code),
                "country": self._safe(country),
                "external_identifier": self._safe(external_identifier),
                **dict(attributes or {}),
            },
            fail_on_duplicate=True,
        )
        self._upsert_relationship_specs(relationships or [])
        return record

    def create_project_entity(
        self,
        *,
        project_id: str,
        canonical_name: str,
        display_name: str | None = None,
        aliases: list[str] | None = None,
        customer: str | None = None,
        location: str | None = None,
        client_project_number: str | None = None,
        internal_project_number: str | None = None,
        status: str | None = None,
        external_identifier: str | None = None,
        notes: str = "",
        active: bool = True,
        attributes: dict[str, Any] | None = None,
        relationships: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self._safe(project_id):
            raise ValueError("project_id cannot be blank")
        record = self._upsert_knowledge_entity(
            entity_id=f"project:{self._safe(project_id)}",
            entity_type="project",
            canonical_name=canonical_name,
            display_name=display_name,
            aliases=list(aliases or []),
            notes=notes,
            active=active,
            attributes={
                "project_id": self._safe(project_id),
                "customer": self._safe(customer),
                "location": self._safe(location),
                "client_project_number": self._safe(client_project_number),
                "internal_project_number": self._safe(internal_project_number),
                "status": self._safe(status),
                "external_identifier": self._safe(external_identifier),
                **dict(attributes or {}),
            },
            fail_on_duplicate=False,
        )
        self._upsert_relationship_specs(relationships or [])
        return record

    def get_knowledge_entity(self, entity_id: str) -> dict[str, Any] | None:
        normalized_id = self._safe(entity_id)
        return (
            dict(self.state.get("knowledge_entities", {}).get(normalized_id, {}))
            or None
        )

    def upsert_organization_entity(
        self,
        *,
        organization_id: str,
        canonical_name: str,
        display_name: str | None = None,
        roles: list[str] | None = None,
        aliases: list[str] | None = None,
        notes: str = "",
        attributes: dict[str, Any] | None = None,
        active: bool = True,
    ) -> dict[str, Any]:
        if not self._safe(organization_id):
            raise ValueError("organization_id cannot be blank")
        return self._upsert_knowledge_entity(
            entity_id=f"organization:{self._safe(organization_id)}",
            entity_type="organization",
            canonical_name=canonical_name,
            display_name=display_name,
            aliases=list(aliases or []),
            notes=notes,
            active=active,
            attributes={
                "organization_id": self._safe(organization_id),
                "roles": sorted(
                    {self._safe(item) for item in list(roles or []) if self._safe(item)}
                ),
                **dict(attributes or {}),
            },
            fail_on_duplicate=False,
        )

    def update_knowledge_entity(
        self,
        *,
        entity_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        current = self.get_knowledge_entity(entity_id)
        if current is None:
            raise ValueError("Knowledge entity not found")

        canonical_name = self._safe(
            updates.get("canonical_name"),
            self._safe(current.get("canonical_name"), ""),
        )
        display_name = self._safe(
            updates.get("display_name"),
            self._safe(current.get("display_name"), canonical_name),
        )
        aliases = (
            [
                self._safe(item)
                for item in list(updates.get("aliases") or [])
                if self._safe(item)
            ]
            if "aliases" in updates
            else list(current.get("aliases") or [])
        )
        notes = self._safe(
            updates.get("notes"),
            self._safe(current.get("notes"), ""),
        )
        active = bool(updates.get("active", current.get("active", True)))
        attributes = dict(current.get("attributes") or {})
        if "attributes" in updates:
            attributes.update(dict(updates.get("attributes") or {}))

        return self._upsert_knowledge_entity(
            entity_id=self._safe(current.get("entity_id"), ""),
            entity_type=self._safe(current.get("entity_type"), ""),
            canonical_name=canonical_name,
            display_name=display_name,
            aliases=aliases,
            notes=notes,
            active=active,
            attributes=attributes,
            fail_on_duplicate=True,
        )

    def set_knowledge_entity_active(self, *, entity_id: str, active: bool) -> None:
        if self.get_knowledge_entity(entity_id) is None:
            raise ValueError("Knowledge entity not found")
        self._set_knowledge_entity_active(entity_id=entity_id, active=active)

    def link_role_entity_to_organization(
        self,
        *,
        entity_id: str,
        organization_id: str,
        role: str,
    ) -> dict[str, Any]:
        current = self.get_knowledge_entity(entity_id)
        if current is None:
            raise ValueError("Knowledge entity not found")
        attributes = dict(current.get("attributes") or {})
        attributes["organization_id"] = self._safe(organization_id)
        attributes["organization_role"] = self._safe(role).lower()
        updated = self.update_knowledge_entity(
            entity_id=entity_id,
            updates={"attributes": attributes},
        )
        self._append_knowledge_audit(
            event_type="knowledge_role_linked_to_organization",
            entity_id=entity_id,
            payload={
                "organization_id": self._safe(organization_id),
                "role": self._safe(role).lower(),
            },
        )
        return updated

    def mark_role_entity_merged(
        self,
        *,
        entity_id: str,
        organization_id: str,
        actor: str,
        reason: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        current = self.get_knowledge_entity(entity_id)
        if current is None:
            raise ValueError("Knowledge entity not found")
        attributes = dict(current.get("attributes") or {})
        attributes.update(
            {
                "merge_status": "redirected",
                "merged_into_organization_id": self._safe(organization_id),
                "merge_actor": self._safe(actor),
                "merge_reason": self._safe(reason),
                "merge_correlation_id": self._safe(correlation_id),
                "merged_at": self._now_iso(),
                "read_only": True,
            }
        )
        aliases = {
            self._safe(item)
            for item in list(current.get("aliases") or [])
            if self._safe(item)
        }
        aliases.update(
            {
                self._safe(current.get("canonical_name"), ""),
                self._safe(current.get("display_name"), ""),
                entity_id,
            }
        )
        updated = self.update_knowledge_entity(
            entity_id=entity_id,
            updates={
                "aliases": sorted({item for item in aliases if item}),
                "attributes": attributes,
                "active": False,
            },
        )
        self._append_knowledge_audit(
            event_type="knowledge_role_merged_redirected",
            entity_id=entity_id,
            payload={
                "organization_id": self._safe(organization_id),
                "actor": self._safe(actor),
                "reason": self._safe(reason),
                "correlation_id": self._safe(correlation_id),
            },
        )
        return updated

    def reassign_knowledge_relationships(
        self,
        *,
        source_entity_ids: list[str],
        target_entity_id: str,
    ) -> dict[str, int]:
        sources = {self._safe(item) for item in source_entity_ids if self._safe(item)}
        target = self._safe(target_entity_id)
        if not target:
            raise ValueError("target_entity_id is required")
        if target not in self.state.get("knowledge_entities", {}):
            raise ValueError("target relationship entity must exist")
        if not sources:
            return {"relationships_reassigned": 0}
        original = list(self.state.get("knowledge_relationships", {}).values())
        rewritten: dict[str, dict[str, Any]] = {}
        reassigned = 0
        for item in original:
            row = dict(item)
            changed = False
            if self._safe(row.get("source_entity_id"), "") in sources:
                row["source_entity_id"] = target
                changed = True
            if self._safe(row.get("target_entity_id"), "") in sources:
                row["target_entity_id"] = target
                changed = True
            if row.get("source_entity_id") == row.get("target_entity_id"):
                reassigned += 1 if changed else 0
                continue
            if changed:
                reassigned += 1
                row["relationship_id"] = self._knowledge_relationship_id(
                    source_entity_id=self._safe(row.get("source_entity_id"), ""),
                    target_entity_id=self._safe(row.get("target_entity_id"), ""),
                    relationship_type=self._safe(row.get("relationship_type"), ""),
                )
                row["updated_at"] = self._now_iso()
            rewritten[self._safe(row.get("relationship_id"), "")] = row
        self.state["knowledge_relationships"] = rewritten
        if reassigned:
            self._append_knowledge_audit(
                event_type="knowledge_relationships_reassigned",
                entity_id=target,
                payload={
                    "source_entity_ids": sorted(sources),
                    "target_entity_id": target,
                    "relationships_reassigned": reassigned,
                },
            )
        return {"relationships_reassigned": reassigned}

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        return self.get_knowledge_entity(f"customer:{self._safe(customer_id)}")

    def list_customers(self, *, include_inactive: bool = True) -> list[dict[str, Any]]:
        return self.list_knowledge_entities(
            entity_type="customer",
            include_inactive=include_inactive,
        )

    def search_customers(
        self,
        query: str,
        *,
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        return self.search_knowledge_entities(
            query,
            entity_type="customer",
            include_inactive=include_inactive,
        )

    def update_customer(
        self,
        customer_id: str,
        *,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        return self.update_knowledge_entity(
            entity_id=f"customer:{self._safe(customer_id)}",
            updates=updates,
        )

    def set_customer_active(self, customer_id: str, active: bool) -> None:
        self.set_knowledge_entity_active(
            entity_id=f"customer:{self._safe(customer_id)}",
            active=active,
        )

    def get_service_entity(self, service_id: str) -> dict[str, Any] | None:
        return self.get_knowledge_entity(f"service:{self._safe(service_id)}")

    def list_service_entities(
        self,
        *,
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        return self.list_knowledge_entities(
            entity_type="service",
            include_inactive=include_inactive,
        )

    def search_service_entities(
        self,
        query: str,
        *,
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        return self.search_knowledge_entities(
            query,
            entity_type="service",
            include_inactive=include_inactive,
        )

    def update_service_entity(
        self,
        service_id: str,
        *,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        return self.update_knowledge_entity(
            entity_id=f"service:{self._safe(service_id)}",
            updates=updates,
        )

    def set_service_entity_active(self, service_id: str, active: bool) -> None:
        self.set_knowledge_entity_active(
            entity_id=f"service:{self._safe(service_id)}",
            active=active,
        )

    def get_contact(self, contact_id: str) -> dict[str, Any] | None:
        return self.get_knowledge_entity(f"contact:{self._safe(contact_id)}")

    def list_contacts(self, *, include_inactive: bool = True) -> list[dict[str, Any]]:
        return self.list_knowledge_entities(
            entity_type="contact",
            include_inactive=include_inactive,
        )

    def search_contacts(
        self,
        query: str,
        *,
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        return self.search_knowledge_entities(
            query,
            entity_type="contact",
            include_inactive=include_inactive,
        )

    def update_contact(
        self,
        contact_id: str,
        *,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        return self.update_knowledge_entity(
            entity_id=f"contact:{self._safe(contact_id)}",
            updates=updates,
        )

    def set_contact_active(self, contact_id: str, active: bool) -> None:
        self.set_knowledge_entity_active(
            entity_id=f"contact:{self._safe(contact_id)}",
            active=active,
        )

    def get_location(self, location_id: str) -> dict[str, Any] | None:
        return self.get_knowledge_entity(f"location:{self._safe(location_id)}")

    def list_locations(self, *, include_inactive: bool = True) -> list[dict[str, Any]]:
        return self.list_knowledge_entities(
            entity_type="location",
            include_inactive=include_inactive,
        )

    def search_locations(
        self,
        query: str,
        *,
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        return self.search_knowledge_entities(
            query,
            entity_type="location",
            include_inactive=include_inactive,
        )

    def update_location(
        self,
        location_id: str,
        *,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        return self.update_knowledge_entity(
            entity_id=f"location:{self._safe(location_id)}",
            updates=updates,
        )

    def set_location_active(self, location_id: str, active: bool) -> None:
        self.set_knowledge_entity_active(
            entity_id=f"location:{self._safe(location_id)}",
            active=active,
        )

    def get_project_entity(self, project_id: str) -> dict[str, Any] | None:
        return self.get_knowledge_entity(f"project:{self._safe(project_id)}")

    def list_project_entities(
        self,
        *,
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        return self.list_knowledge_entities(
            entity_type="project",
            include_inactive=include_inactive,
        )

    def search_project_entities(
        self,
        query: str,
        *,
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        return self.search_knowledge_entities(
            query,
            entity_type="project",
            include_inactive=include_inactive,
        )

    def update_project_entity(
        self,
        project_id: str,
        *,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        return self.update_knowledge_entity(
            entity_id=f"project:{self._safe(project_id)}",
            updates=updates,
        )

    def set_project_entity_active(self, project_id: str, active: bool) -> None:
        self.set_knowledge_entity_active(
            entity_id=f"project:{self._safe(project_id)}",
            active=active,
        )

    def _knowledge_entity_matches_query(self, item: dict[str, Any], query: str) -> bool:
        return self._knowledge_entity_search_rank(item, query)[0] < 9

    def _knowledge_entity_search_rank(
        self,
        item: dict[str, Any],
        query: str,
    ) -> tuple[int, str, str]:
        normalized_query = self.normalize_name(query)
        entity_type = self._safe(item.get("entity_type"), "").lower()
        search_terms = self._knowledge_entity_search_terms(item)

        if not normalized_query:
            return (9, entity_type, self._safe(item.get("entity_id"), ""))

        normalized_terms = {
            self.normalize_name(term) for term in search_terms if self._safe(term)
        }
        if normalized_query in normalized_terms:
            return (0, entity_type, self._safe(item.get("entity_id"), ""))

        if any(
            self.normalize_name(term).startswith(normalized_query)
            for term in search_terms
        ):
            return (1, entity_type, self._safe(item.get("entity_id"), ""))

        if any(normalized_query in self.normalize_name(term) for term in search_terms):
            return (2, entity_type, self._safe(item.get("entity_id"), ""))

        return (9, entity_type, self._safe(item.get("entity_id"), ""))

    def _knowledge_entity_search_terms(self, item: dict[str, Any]) -> list[str]:
        entity_type = self._safe(item.get("entity_type"), "").lower()
        attributes = dict(item.get("attributes") or {})
        terms = [
            self._safe(item.get("entity_id"), ""),
            self._safe(item.get("canonical_name"), ""),
            self._safe(item.get("display_name"), ""),
            self._safe(item.get("normalized_name"), ""),
            " ".join(list(item.get("aliases") or [])),
        ]
        if entity_type == "contact":
            terms.extend(
                [
                    self._safe(attributes.get("contact_id"), ""),
                    self._safe(attributes.get("email"), ""),
                    self._safe(attributes.get("phone"), ""),
                    self._safe(attributes.get("title"), ""),
                    self._safe(attributes.get("organization"), ""),
                    self._safe(attributes.get("external_identifier"), ""),
                ]
            )
        elif entity_type == "location":
            terms.extend(
                [
                    self._safe(attributes.get("location_id"), ""),
                    self._safe(attributes.get("address_line1"), ""),
                    self._safe(attributes.get("address_line2"), ""),
                    self._safe(attributes.get("city"), ""),
                    self._safe(attributes.get("state"), ""),
                    self._safe(attributes.get("postal_code"), ""),
                    self._safe(attributes.get("country"), ""),
                    self._safe(attributes.get("external_identifier"), ""),
                ]
            )
        elif entity_type == "project":
            terms.extend(
                [
                    self._safe(attributes.get("project_id"), ""),
                    self._safe(attributes.get("customer"), ""),
                    self._safe(attributes.get("location"), ""),
                    self._safe(attributes.get("client_project_number"), ""),
                    self._safe(attributes.get("internal_project_number"), ""),
                    self._safe(attributes.get("status"), ""),
                    self._safe(attributes.get("external_identifier"), ""),
                ]
            )
        else:
            terms.extend(
                [
                    self._safe(attributes.get("manufacturer_id"), ""),
                    self._safe(attributes.get("manufacturer_code"), ""),
                    self._safe(attributes.get("vendor_id"), ""),
                    self._safe(attributes.get("vendor_code"), ""),
                    self._safe(attributes.get("atlas_product_uuid"), ""),
                    self._safe(attributes.get("manufacturer_part_number"), ""),
                    self._safe(
                        attributes.get("normalized_manufacturer_part_number"), ""
                    ),
                    self._safe(attributes.get("category"), ""),
                    self._safe(attributes.get("lifecycle_status"), ""),
                    self._safe(attributes.get("website"), ""),
                    self._safe(attributes.get("service_id"), ""),
                ]
            )
        return [term for term in terms if self._safe(term)]

    def knowledge_entity_summary(self) -> dict[str, Any]:
        rows = self.list_knowledge_entities(include_inactive=True)
        relationships = self.list_knowledge_relationships()
        by_type: dict[str, dict[str, int]] = {}
        for item in rows:
            entity_type = self._safe(item.get("entity_type"), "unknown")
            bucket = by_type.setdefault(
                entity_type,
                {"total": 0, "active": 0, "inactive": 0},
            )
            bucket["total"] += 1
            if bool(item.get("active", True)):
                bucket["active"] += 1
            else:
                bucket["inactive"] += 1

        return {
            "total_entities": len(rows),
            "active_entities": sum(
                1 for item in rows if bool(item.get("active", True))
            ),
            "inactive_entities": sum(
                1 for item in rows if not bool(item.get("active", True))
            ),
            "total_relationships": len(relationships),
            "by_type": dict(sorted(by_type.items())),
        }

    def list_knowledge_audit_events(
        self,
        *,
        entity_id: str = "",
        event_type: str = "",
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        entity_filter = self._safe(entity_id)
        event_filter = self._safe(event_type)
        rows = list(self.state.get("knowledge_audit_log") or [])
        if entity_filter:
            rows = [
                item
                for item in rows
                if self._safe(dict(item).get("entity_id"), "") == entity_filter
            ]
        if event_filter:
            rows = [
                item
                for item in rows
                if self._safe(dict(item).get("event_type"), "") == event_filter
            ]
        rows.sort(key=lambda item: self._safe(dict(item).get("timestamp"), ""))
        return [dict(item) for item in rows[-max(1, int(limit)) :]]

    def knowledge_entity_csv_template(self, *, entity_type: str) -> str:
        normalized_type = self._safe(entity_type).lower()
        if normalized_type == "customer":
            fieldnames = [
                "customer_id",
                "canonical_name",
                "display_name",
                "aliases",
                "notes",
                "active",
            ]
            sample = {
                "customer_id": "cust-001",
                "canonical_name": "Example Customer",
                "display_name": "Example Customer",
                "aliases": "Example Cust;EC",
                "notes": "",
                "active": "true",
            }
        elif normalized_type == "service":
            fieldnames = [
                "service_id",
                "canonical_name",
                "display_name",
                "aliases",
                "notes",
                "active",
            ]
            sample = {
                "service_id": "svc-001",
                "canonical_name": "Example Service",
                "display_name": "Example Service",
                "aliases": "Ops;Support",
                "notes": "",
                "active": "true",
            }
        elif normalized_type == "contact":
            fieldnames = [
                "contact_id",
                "canonical_name",
                "display_name",
                "email",
                "phone",
                "title",
                "organization",
                "external_identifier",
                "aliases",
                "notes",
                "active",
            ]
            sample = {
                "contact_id": "contact-001",
                "canonical_name": "Example Contact",
                "display_name": "Example Contact",
                "email": "contact@example.com",
                "phone": "555-0100",
                "title": "Project Manager",
                "organization": "Example Organization",
                "external_identifier": "EXT-CONTACT-001",
                "aliases": "EC",
                "notes": "",
                "active": "true",
            }
        elif normalized_type == "location":
            fieldnames = [
                "location_id",
                "canonical_name",
                "display_name",
                "address_line1",
                "address_line2",
                "city",
                "state",
                "postal_code",
                "country",
                "external_identifier",
                "aliases",
                "notes",
                "active",
            ]
            sample = {
                "location_id": "loc-001",
                "canonical_name": "Example Location",
                "display_name": "Example Location",
                "address_line1": "100 Main St",
                "address_line2": "Suite 200",
                "city": "Los Angeles",
                "state": "CA",
                "postal_code": "90001",
                "country": "US",
                "external_identifier": "EXT-LOC-001",
                "aliases": "HQ",
                "notes": "",
                "active": "true",
            }
        elif normalized_type == "project":
            fieldnames = [
                "project_id",
                "canonical_name",
                "display_name",
                "customer",
                "location",
                "client_project_number",
                "internal_project_number",
                "status",
                "external_identifier",
                "aliases",
                "notes",
                "active",
            ]
            sample = {
                "project_id": "project-001",
                "canonical_name": "Example Project",
                "display_name": "Example Project",
                "customer": "Example Customer",
                "location": "Example Location",
                "client_project_number": "C-1001",
                "internal_project_number": "I-1001",
                "status": "active",
                "external_identifier": "EXT-PROJ-001",
                "aliases": "EP",
                "notes": "",
                "active": "true",
            }
        elif normalized_type == "manufacturer":
            fieldnames = [
                "manufacturer_id",
                "canonical_name",
                "display_name",
                "manufacturer_code",
                "website",
                "aliases",
                "notes",
                "active",
            ]
            sample = {
                "manufacturer_id": "mfr-001",
                "canonical_name": "Example Manufacturer",
                "display_name": "Example Manufacturer",
                "manufacturer_code": "EXM",
                "website": "https://example.com",
                "aliases": "EXMFG",
                "notes": "",
                "active": "true",
            }
        elif normalized_type == "vendor":
            fieldnames = [
                "vendor_id",
                "canonical_name",
                "display_name",
                "vendor_code",
                "website",
                "aliases",
                "notes",
                "active",
            ]
            sample = {
                "vendor_id": "vendor-001",
                "canonical_name": "Example Vendor",
                "display_name": "Example Vendor",
                "vendor_code": "EXV",
                "website": "https://example.com",
                "aliases": "EXVEND",
                "notes": "",
                "active": "true",
            }
        elif normalized_type == "product":
            fieldnames = [
                "manufacturer_id",
                "manufacturer_part_number",
                "product_name",
                "product_description",
                "category",
                "lifecycle_status",
                "active",
                "notes",
            ]
            sample = {
                "manufacturer_id": "mfr-001",
                "manufacturer_part_number": "EX-100",
                "product_name": "Example Product",
                "product_description": "Example description",
                "category": "other",
                "lifecycle_status": "pending_verification",
                "active": "true",
                "notes": "",
            }
        else:
            raise ValueError("Unsupported knowledge entity type")

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(sample)
        return buffer.getvalue()

    def preview_knowledge_entity_import_csv(
        self,
        *,
        entity_type: str,
        file_bytes: bytes,
    ) -> dict[str, Any]:
        normalized_type = self._safe(entity_type).lower()
        if normalized_type not in {
            "customer",
            "service",
            "contact",
            "location",
            "project",
            "manufacturer",
            "vendor",
            "product",
        }:
            raise ValueError("Unsupported knowledge entity type")

        text = file_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = [dict(item) for item in list(reader)]

        diagnostics: list[dict[str, Any]] = []
        preview_rows: list[dict[str, Any]] = []
        seen_keys: dict[str, int] = {}

        for index, row in enumerate(rows, start=1):
            parsed = self._normalize_knowledge_import_row(
                entity_type=normalized_type,
                row=row,
            )
            key = self._knowledge_import_row_key(
                entity_type=normalized_type,
                normalized_row=parsed,
            )
            seen_keys[key] = seen_keys.get(key, 0) + 1
            preview: dict[str, Any] = {
                "row_number": index,
                "status": "accepted",
                "operation": "upsert",
                "errors": [],
                "warnings": [],
                "normalized_row": parsed,
                "raw_row": dict(row),
            }
            validation_errors = self._validate_knowledge_import_row(
                entity_type=normalized_type,
                normalized_row=parsed,
            )
            if validation_errors:
                preview["status"] = "rejected"
                preview["errors"] = list(validation_errors)
                for message in validation_errors:
                    diagnostics.append(
                        {
                            "severity": "error",
                            "row_number": index,
                            "code": "invalid_row",
                            "message": message,
                        }
                    )
            preview_rows.append(preview)

        for preview in preview_rows:
            row_number = int(preview.get("row_number") or 0)
            normalized_preview_row = dict(preview.get("normalized_row") or {})
            key = self._knowledge_import_row_key(
                entity_type=normalized_type,
                normalized_row=normalized_preview_row,
            )
            if seen_keys.get(key, 0) > 1:
                preview["status"] = "rejected"
                message = "Duplicate row identity detected in import file"
                preview.setdefault("errors", []).append(message)
                diagnostics.append(
                    {
                        "severity": "error",
                        "row_number": row_number,
                        "code": "duplicate_row_identity",
                        "message": message,
                    }
                )

        accepted_count = sum(
            1
            for item in preview_rows
            if self._safe(item.get("status"), "") == "accepted"
        )
        rejected_count = len(preview_rows) - accepted_count
        return {
            "entity_type": normalized_type,
            "record_count": len(preview_rows),
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "preview_rows": preview_rows,
            "diagnostics": diagnostics,
        }

    def import_knowledge_entities_from_csv(
        self,
        *,
        entity_type: str,
        file_bytes: bytes,
        allow_partial_success: bool = True,
    ) -> dict[str, Any]:
        preview = self.preview_knowledge_entity_import_csv(
            entity_type=entity_type,
            file_bytes=file_bytes,
        )
        rejected_rows = [
            dict(item)
            for item in list(preview.get("preview_rows") or [])
            if self._safe(item.get("status"), "") == "rejected"
        ]
        accepted_rows = [
            dict(item)
            for item in list(preview.get("preview_rows") or [])
            if self._safe(item.get("status"), "") == "accepted"
        ]
        if rejected_rows and not allow_partial_success:
            raise ValueError(
                "Import contains rejected rows; partial success not allowed"
            )

        imported = 0
        for item in accepted_rows:
            normalized_type = self._safe(preview.get("entity_type"), "")
            normalized_row = dict(item.get("normalized_row") or {})
            if normalized_type == "customer":
                customer_id = self._safe(normalized_row.get("customer_id"), "")
                existing = self.get_customer(customer_id)
                if existing:
                    self.update_customer(customer_id, updates=normalized_row)
                else:
                    self.create_customer(
                        customer_id=customer_id,
                        canonical_name=self._safe(
                            normalized_row.get("canonical_name"), ""
                        ),
                        display_name=self._safe(normalized_row.get("display_name"), ""),
                        aliases=list(normalized_row.get("aliases") or []),
                        notes=self._safe(normalized_row.get("notes"), ""),
                        active=bool(normalized_row.get("active", True)),
                    )
                imported += 1
                continue

            if normalized_type == "service":
                service_id = self._safe(normalized_row.get("service_id"), "")
                existing = self.get_service_entity(service_id)
                if existing:
                    self.update_service_entity(service_id, updates=normalized_row)
                else:
                    self.create_service_entity(
                        service_id=service_id,
                        canonical_name=self._safe(
                            normalized_row.get("canonical_name"), ""
                        ),
                        display_name=self._safe(normalized_row.get("display_name"), ""),
                        aliases=list(normalized_row.get("aliases") or []),
                        notes=self._safe(normalized_row.get("notes"), ""),
                        active=bool(normalized_row.get("active", True)),
                    )
                imported += 1
                continue

            if normalized_type == "contact":
                contact_id = self._safe(normalized_row.get("contact_id"), "")
                if self.get_contact(contact_id):
                    self.update_contact(contact_id, updates=normalized_row)
                else:
                    self.create_contact(
                        contact_id=contact_id,
                        canonical_name=self._safe(
                            normalized_row.get("canonical_name"), ""
                        ),
                        display_name=self._safe(normalized_row.get("display_name"), ""),
                        email=self._safe(normalized_row.get("email"), ""),
                        phone=self._safe(normalized_row.get("phone"), ""),
                        title=self._safe(normalized_row.get("title"), ""),
                        organization=self._safe(normalized_row.get("organization"), ""),
                        external_identifier=self._safe(
                            normalized_row.get("external_identifier"),
                            "",
                        ),
                        aliases=list(normalized_row.get("aliases") or []),
                        notes=self._safe(normalized_row.get("notes"), ""),
                        active=bool(normalized_row.get("active", True)),
                    )
                imported += 1
                continue

            if normalized_type == "location":
                location_id = self._safe(normalized_row.get("location_id"), "")
                if self.get_location(location_id):
                    self.update_location(location_id, updates=normalized_row)
                else:
                    self.create_location(
                        location_id=location_id,
                        canonical_name=self._safe(
                            normalized_row.get("canonical_name"), ""
                        ),
                        display_name=self._safe(normalized_row.get("display_name"), ""),
                        address_line1=self._safe(
                            normalized_row.get("address_line1"), ""
                        ),
                        address_line2=self._safe(
                            normalized_row.get("address_line2"), ""
                        ),
                        city=self._safe(normalized_row.get("city"), ""),
                        state=self._safe(normalized_row.get("state"), ""),
                        postal_code=self._safe(normalized_row.get("postal_code"), ""),
                        country=self._safe(normalized_row.get("country"), ""),
                        external_identifier=self._safe(
                            normalized_row.get("external_identifier"),
                            "",
                        ),
                        aliases=list(normalized_row.get("aliases") or []),
                        notes=self._safe(normalized_row.get("notes"), ""),
                        active=bool(normalized_row.get("active", True)),
                    )
                imported += 1
                continue

            if normalized_type == "project":
                project_id = self._safe(normalized_row.get("project_id"), "")
                if self.get_project_entity(project_id):
                    self.update_project_entity(project_id, updates=normalized_row)
                else:
                    self.create_project_entity(
                        project_id=project_id,
                        canonical_name=self._safe(
                            normalized_row.get("canonical_name"), ""
                        ),
                        display_name=self._safe(normalized_row.get("display_name"), ""),
                        customer=self._safe(normalized_row.get("customer"), ""),
                        location=self._safe(normalized_row.get("location"), ""),
                        client_project_number=self._safe(
                            normalized_row.get("client_project_number"),
                            "",
                        ),
                        internal_project_number=self._safe(
                            normalized_row.get("internal_project_number"),
                            "",
                        ),
                        status=self._safe(normalized_row.get("status"), ""),
                        external_identifier=self._safe(
                            normalized_row.get("external_identifier"),
                            "",
                        ),
                        aliases=list(normalized_row.get("aliases") or []),
                        notes=self._safe(normalized_row.get("notes"), ""),
                        active=bool(normalized_row.get("active", True)),
                    )
                imported += 1
                continue

            if normalized_type == "manufacturer":
                manufacturer_id = self._safe(normalized_row.get("manufacturer_id"), "")
                if self.get_manufacturer(manufacturer_id):
                    self.update_manufacturer(manufacturer_id, updates=normalized_row)
                else:
                    self.create_manufacturer(
                        manufacturer_id=manufacturer_id,
                        canonical_name=self._safe(
                            normalized_row.get("canonical_name"), ""
                        ),
                        display_name=self._safe(normalized_row.get("display_name"), ""),
                        manufacturer_code=self._safe(
                            normalized_row.get("manufacturer_code"), ""
                        ),
                        website=self._safe(normalized_row.get("website"), ""),
                        aliases=list(normalized_row.get("aliases") or []),
                        notes=self._safe(normalized_row.get("notes"), ""),
                        active=bool(normalized_row.get("active", True)),
                    )
                imported += 1
                continue

            if normalized_type == "vendor":
                vendor_id = self._safe(normalized_row.get("vendor_id"), "")
                if self.get_vendor(vendor_id):
                    self.update_vendor(vendor_id, updates=normalized_row)
                else:
                    self.create_vendor(
                        vendor_id=vendor_id,
                        canonical_name=self._safe(
                            normalized_row.get("canonical_name"), ""
                        ),
                        display_name=self._safe(normalized_row.get("display_name"), ""),
                        vendor_code=self._safe(normalized_row.get("vendor_code"), ""),
                        website=self._safe(normalized_row.get("website"), ""),
                        aliases=list(normalized_row.get("aliases") or []),
                        notes=self._safe(normalized_row.get("notes"), ""),
                        active=bool(normalized_row.get("active", True)),
                    )
                imported += 1
                continue

            manufacturer_id = self._safe(normalized_row.get("manufacturer_id"), "")
            manufacturer_record = self.get_manufacturer(manufacturer_id)
            if not manufacturer_record:
                continue
            manufacturer_name = self._safe(
                dict(manufacturer_record).get("canonical_name"),
                "",
            )
            existing_product = self.find_product_by_identity(
                manufacturer=manufacturer_name,
                normalized_part_number=self.normalize_part_number(
                    normalized_row.get("manufacturer_part_number", "")
                ),
            )
            if existing_product:
                self.update_product(
                    self._safe(existing_product.get("atlas_product_uuid"), ""),
                    updates={
                        "product_name": self._safe(
                            normalized_row.get("product_name"), ""
                        ),
                        "product_description": self._safe(
                            normalized_row.get("product_description"),
                            "",
                        ),
                        "category": self._safe(normalized_row.get("category"), "other"),
                        "lifecycle_status": self._safe(
                            normalized_row.get("lifecycle_status"),
                            ProductLifecycleStatus.PENDING_VERIFICATION.value,
                        ),
                        "active": bool(normalized_row.get("active", True)),
                        "notes": self._safe(normalized_row.get("notes"), ""),
                    },
                )
            else:
                self.create_product(
                    manufacturer_id=manufacturer_id,
                    manufacturer=manufacturer_name,
                    manufacturer_part_number=self._safe(
                        normalized_row.get("manufacturer_part_number"),
                        "",
                    ),
                    product_name=self._safe(normalized_row.get("product_name"), ""),
                    product_description=self._safe(
                        normalized_row.get("product_description"),
                        "",
                    ),
                    category=self._safe(normalized_row.get("category"), "other"),
                    lifecycle_status=self._safe(
                        normalized_row.get("lifecycle_status"),
                        ProductLifecycleStatus.PENDING_VERIFICATION.value,
                    ),
                    active=bool(normalized_row.get("active", True)),
                    notes=self._safe(normalized_row.get("notes"), ""),
                )
            imported += 1

        rejected_csv = self.export_rejected_knowledge_import_rows_csv(
            preview_rows=rejected_rows
        )
        self._append_knowledge_audit(
            event_type="knowledge_csv_imported",
            payload={
                "entity_type": self._safe(preview.get("entity_type"), ""),
                "imported_rows": imported,
                "rejected_rows": len(rejected_rows),
                "allow_partial_success": bool(allow_partial_success),
            },
        )
        return {
            "entity_type": self._safe(preview.get("entity_type"), ""),
            "record_count": int(preview.get("record_count", 0) or 0),
            "imported_rows": imported,
            "rejected_rows": len(rejected_rows),
            "diagnostics": list(preview.get("diagnostics") or []),
            "preview_rows": list(preview.get("preview_rows") or []),
            "rejected_rows_csv": rejected_csv,
        }

    def export_rejected_knowledge_import_rows_csv(
        self,
        *,
        preview_rows: list[dict[str, Any]],
    ) -> str:
        rows = [
            {
                "row_number": int(item.get("row_number") or 0),
                "status": self._safe(item.get("status"), ""),
                "errors": " | ".join(list(item.get("errors") or [])),
                "warnings": " | ".join(list(item.get("warnings") or [])),
                "raw_row": json.dumps(
                    {
                        self._safe(key): self._safe(value)
                        for key, value in dict(item.get("raw_row") or {}).items()
                        if self._safe(key)
                    },
                    sort_keys=True,
                ),
            }
            for item in list(preview_rows or [])
            if self._safe(item.get("status"), "") == "rejected"
        ]
        headers = ["row_number", "status", "errors", "warnings", "raw_row"]
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buffer.getvalue()

    def export_knowledge_entities_csv(
        self,
        *,
        entity_type: str = "",
        include_inactive: bool = True,
        query: str = "",
    ) -> str:
        rows = self.list_knowledge_entities(
            entity_type=entity_type,
            include_inactive=include_inactive,
        )
        q = self.normalize_name(query)
        if q:
            rows = [
                item
                for item in rows
                if q in self.normalize_name(item.get("canonical_name", ""))
                or q in self.normalize_name(item.get("display_name", ""))
                or any(
                    q in self.normalize_name(alias)
                    for alias in list(item.get("aliases") or [])
                )
            ]
        export_rows = [
            {
                "entity_id": self._safe(item.get("entity_id"), ""),
                "entity_type": self._safe(item.get("entity_type"), ""),
                "canonical_name": self._safe(item.get("canonical_name"), ""),
                "display_name": self._safe(item.get("display_name"), ""),
                "aliases": ";".join(list(item.get("aliases") or [])),
                "active": bool(item.get("active", True)),
                "notes": self._safe(item.get("notes"), ""),
                "attributes": json.dumps(
                    dict(item.get("attributes") or {}), sort_keys=True
                ),
                "created_at": self._safe(item.get("created_at"), ""),
                "updated_at": self._safe(item.get("updated_at"), ""),
            }
            for item in rows
        ]
        headers = [
            "entity_id",
            "entity_type",
            "canonical_name",
            "display_name",
            "aliases",
            "active",
            "notes",
            "attributes",
            "created_at",
            "updated_at",
        ]
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=headers)
        writer.writeheader()
        for row in export_rows:
            writer.writerow(row)
        return buffer.getvalue()

    def export_knowledge_entities_json(
        self,
        *,
        entity_type: str = "",
        include_inactive: bool = True,
        query: str = "",
    ) -> str:
        rows = self.list_knowledge_entities(
            entity_type=entity_type,
            include_inactive=include_inactive,
        )
        q = self.normalize_name(query)
        if q:
            rows = [
                item
                for item in rows
                if q in self.normalize_name(item.get("canonical_name", ""))
                or q in self.normalize_name(item.get("display_name", ""))
                or any(
                    q in self.normalize_name(alias)
                    for alias in list(item.get("aliases") or [])
                )
            ]
        payload = {
            "entities": [dict(item) for item in rows],
            "entity_type": self._safe(entity_type).lower(),
            "include_inactive": bool(include_inactive),
            "query": self._safe(query),
            "exported_at": self._now_iso(),
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    def list_knowledge_entities(
        self,
        *,
        entity_type: str = "",
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        requested_type = self._safe(entity_type).lower()
        rows = list(self.state.get("knowledge_entities", {}).values())
        if requested_type:
            rows = [
                item
                for item in rows
                if self._safe(item.get("entity_type"), "").lower() == requested_type
            ]
        if not include_inactive:
            rows = [item for item in rows if bool(item.get("active", True))]
        rows.sort(
            key=lambda item: (
                self._safe(item.get("entity_type"), "").lower(),
                self._safe(item.get("canonical_name"), "").lower(),
            )
        )
        return [dict(item) for item in rows]

    def search_knowledge_entities(
        self,
        query: str,
        *,
        entity_type: str = "",
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        q = self.normalize_name(query)
        rows = self.list_knowledge_entities(
            entity_type=entity_type,
            include_inactive=include_inactive,
        )
        if not q:
            return rows
        matched = [
            item for item in rows if self._knowledge_entity_matches_query(item, q)
        ]
        matched.sort(key=lambda item: self._knowledge_entity_search_rank(item, q))
        return matched

    def detect_duplicate_knowledge_entities(
        self,
        *,
        entity_type: str,
        canonical_name: str,
        normalized_name: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized_type = self._safe(entity_type).lower()
        if not normalized_type:
            return []
        target_norm = normalized_name or self.normalize_name(canonical_name)
        rows = self.list_knowledge_entities(entity_type=normalized_type)
        return [
            dict(item)
            for item in rows
            if self.normalize_name(item.get("canonical_name", "")) == target_norm
            or self.normalize_name(item.get("normalized_name", "")) == target_norm
        ]

    def create_knowledge_relationship(
        self,
        *,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        confidence: float = 1.0,
        evidence_refs: list[str] | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        source_id = self._safe(source_entity_id)
        target_id = self._safe(target_entity_id)
        rel_type = self._safe(relationship_type).lower()
        if not source_id or not target_id:
            raise ValueError("source_entity_id and target_entity_id are required")
        if source_id == target_id:
            raise ValueError("Knowledge relationships must connect distinct entities")
        if not rel_type:
            raise ValueError("relationship_type cannot be blank")

        entity_map = self.state.setdefault("knowledge_entities", {})
        if source_id not in entity_map or target_id not in entity_map:
            raise ValueError("Both relationship entities must exist")

        try:
            confidence_value = max(0.0, min(1.0, float(confidence)))
        except Exception:
            confidence_value = 1.0

        relationship_id = self._knowledge_relationship_id(
            source_entity_id=source_id,
            target_entity_id=target_id,
            relationship_type=rel_type,
        )
        now_text = self._now_iso()
        existing = dict(
            self.state.get("knowledge_relationships", {}).get(relationship_id) or {}
        )
        record = {
            "relationship_id": relationship_id,
            "source_entity_id": source_id,
            "target_entity_id": target_id,
            "relationship_type": rel_type,
            "confidence": confidence_value,
            "evidence_refs": [
                self._safe(item)
                for item in list(evidence_refs or [])
                if self._safe(item)
            ],
            "notes": self._safe(notes),
            "created_at": self._safe(existing.get("created_at"), now_text),
            "updated_at": now_text,
        }
        self.state.setdefault("knowledge_relationships", {})[relationship_id] = record
        self._append_knowledge_audit(
            event_type="knowledge_relationship_upserted",
            entity_id=relationship_id,
            payload={
                "source_entity_id": source_id,
                "target_entity_id": target_id,
                "relationship_type": rel_type,
            },
        )
        return dict(record)

    def list_knowledge_relationships(
        self,
        *,
        source_entity_id: str = "",
        target_entity_id: str = "",
        relationship_type: str = "",
    ) -> list[dict[str, Any]]:
        source_filter = self._safe(source_entity_id)
        target_filter = self._safe(target_entity_id)
        type_filter = self._safe(relationship_type).lower()
        rows = list(self.state.get("knowledge_relationships", {}).values())
        if source_filter:
            rows = [
                item
                for item in rows
                if self._safe(item.get("source_entity_id"), "") == source_filter
            ]
        if target_filter:
            rows = [
                item
                for item in rows
                if self._safe(item.get("target_entity_id"), "") == target_filter
            ]
        if type_filter:
            rows = [
                item
                for item in rows
                if self._safe(item.get("relationship_type"), "").lower() == type_filter
            ]
        rows.sort(
            key=lambda item: (
                self._safe(item.get("relationship_type"), ""),
                self._safe(item.get("source_entity_id"), ""),
                self._safe(item.get("target_entity_id"), ""),
            )
        )
        return [dict(item) for item in rows]

    def _upsert_relationship_specs(self, relationships: list[dict[str, Any]]) -> None:
        for item in list(relationships or []):
            if not isinstance(item, dict):
                continue
            source_entity_id = self._safe(item.get("source_entity_id"), "")
            target_entity_id = self._safe(item.get("target_entity_id"), "")
            relationship_type = self._safe(item.get("relationship_type"), "")
            if not source_entity_id or not target_entity_id or not relationship_type:
                continue
            self.create_knowledge_relationship(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=relationship_type,
                confidence=float(item.get("confidence", 1.0) or 1.0),
                evidence_refs=[
                    self._safe(reference)
                    for reference in list(item.get("evidence_refs") or [])
                    if self._safe(reference)
                ],
                notes=self._safe(item.get("notes"), ""),
            )

    def export_knowledge_entity_bundle(self) -> dict[str, Any]:
        return {
            "entities": self.list_knowledge_entities(include_inactive=True),
            "relationships": self.list_knowledge_relationships(),
            "audit_log": [
                dict(item) for item in list(self.state.get("knowledge_audit_log") or [])
            ],
            "exported_at": self._now_iso(),
        }

    def import_knowledge_entity_bundle(
        self,
        *,
        bundle: dict[str, Any],
    ) -> dict[str, Any]:
        entities = list(dict(bundle or {}).get("entities") or [])
        relationships = list(dict(bundle or {}).get("relationships") or [])
        upserted_entities = 0
        upserted_relationships = 0

        for item in entities:
            if not isinstance(item, dict):
                continue
            entity_id = self._safe(item.get("entity_id"), "")
            entity_type = self._safe(item.get("entity_type"), "").lower()
            canonical_name = self._safe(item.get("canonical_name"), "")
            if not entity_id or not entity_type or not canonical_name:
                continue
            self._upsert_knowledge_entity(
                entity_id=entity_id,
                entity_type=entity_type,
                canonical_name=canonical_name,
                display_name=self._safe(item.get("display_name"), canonical_name),
                aliases=[
                    self._safe(alias)
                    for alias in list(item.get("aliases") or [])
                    if self._safe(alias)
                ],
                notes=self._safe(item.get("notes"), ""),
                active=bool(item.get("active", True)),
                attributes=dict(item.get("attributes") or {}),
                fail_on_duplicate=False,
            )
            upserted_entities += 1

        for item in relationships:
            if not isinstance(item, dict):
                continue
            source_entity_id = self._safe(item.get("source_entity_id"), "")
            target_entity_id = self._safe(item.get("target_entity_id"), "")
            relationship_type = self._safe(item.get("relationship_type"), "")
            if not source_entity_id or not target_entity_id or not relationship_type:
                continue
            self.create_knowledge_relationship(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=relationship_type,
                confidence=float(item.get("confidence", 1.0) or 1.0),
                evidence_refs=[
                    self._safe(reference)
                    for reference in list(item.get("evidence_refs") or [])
                    if self._safe(reference)
                ],
                notes=self._safe(item.get("notes"), ""),
            )
            upserted_relationships += 1

        self._append_knowledge_audit(
            event_type="knowledge_bundle_imported",
            payload={
                "upserted_entities": upserted_entities,
                "upserted_relationships": upserted_relationships,
            },
        )
        return {
            "upserted_entities": upserted_entities,
            "upserted_relationships": upserted_relationships,
        }

    def update_product(
        self,
        atlas_product_uuid: str,
        *,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        product = self.get_product(atlas_product_uuid)
        if product is None:
            raise ValueError("Product not found")

        if "manufacturer_part_number" in updates:
            normalized_part = self.normalize_part_number(
                updates.get("manufacturer_part_number")
            )
            duplicate = self.find_product_by_identity(
                manufacturer=self._safe(product.get("manufacturer"), ""),
                normalized_part_number=normalized_part,
            )
            if duplicate and self._safe(
                duplicate.get("atlas_product_uuid"), ""
            ) != self._safe(atlas_product_uuid):
                raise ValueError(
                    "Duplicate product identity for manufacturer + normalized part number"
                )
            product["manufacturer_part_number"] = self._safe(
                updates.get("manufacturer_part_number"),
                product.get("manufacturer_part_number", ""),
            )
            product["manufacturer_sku"] = product["manufacturer_part_number"]
            product["normalized_manufacturer_part_number"] = normalized_part

        for key in [
            "product_name",
            "product_description",
            "category",
            "notes",
            "lifecycle_status",
        ]:
            if key in updates:
                product[key] = self._safe(
                    updates.get(key), self._safe(product.get(key), "")
                )
        if "active" in updates:
            product["active"] = bool(updates.get("active"))
        if "replacement_product_uuid" in updates:
            replacement = self._safe(updates.get("replacement_product_uuid"), "")
            if replacement:
                if replacement == self._safe(atlas_product_uuid):
                    raise ValueError("Product replacement cannot reference itself")
                if self._replacement_cycle_exists(atlas_product_uuid, replacement):
                    raise ValueError("Product replacement cycle detected")
            product["replacement_product_uuid"] = replacement or None

        product["updated_at"] = self._now_iso()
        self._persist_product(product)
        return dict(product)

    def get_product(self, atlas_product_uuid: str) -> dict[str, Any] | None:
        target = self._safe(atlas_product_uuid)
        for item in self.state.get("products", {}).values():
            if self._safe(item.get("atlas_product_uuid"), "") == target:
                return dict(item)
        return None

    def list_products(self, *, include_inactive: bool = True) -> list[dict[str, Any]]:
        rows = list(self.state.get("products", {}).values())
        if not include_inactive:
            rows = [item for item in rows if bool(item.get("active", True))]
        rows.sort(
            key=lambda item: (
                self._safe(item.get("manufacturer"), "").lower(),
                self._safe(item.get("manufacturer_sku"), "").lower(),
            )
        )
        return [dict(item) for item in rows]

    def search_products(
        self,
        *,
        manufacturer: str | None = None,
        part_number: str | None = None,
        text: str | None = None,
        lifecycle_status: str | None = None,
        active: bool | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.list_products(include_inactive=True)
        part_norm = self.normalize_part_number(part_number or "")
        text_norm = self.normalize_name(text or "")
        result: list[dict[str, Any]] = []
        for item in rows:
            if manufacturer and self._safe(item.get("manufacturer"), "") != self._safe(
                manufacturer
            ):
                continue
            if (
                part_norm
                and self.normalize_part_number(
                    item.get(
                        "manufacturer_part_number", item.get("manufacturer_sku", "")
                    )
                )
                != part_norm
            ):
                continue
            if lifecycle_status and self._safe(
                item.get("lifecycle_status"), ""
            ) != self._safe(lifecycle_status):
                continue
            if active is not None and bool(item.get("active", True)) != bool(active):
                continue
            if text_norm:
                searchable = self.normalize_name(
                    " ".join(
                        [
                            self._safe(item.get("product_name"), ""),
                            self._safe(item.get("product_description"), ""),
                            self._safe(item.get("manufacturer_part_number"), ""),
                            self._safe(item.get("manufacturer_sku"), ""),
                        ]
                    )
                )
                if text_norm not in searchable:
                    continue
            result.append(dict(item))
        return result

    def mark_product_discontinued(self, atlas_product_uuid: str) -> dict[str, Any]:
        return self._set_product_lifecycle(
            atlas_product_uuid,
            lifecycle_status=ProductLifecycleStatus.DISCONTINUED.value,
            active=False,
        )

    def reactivate_product(self, atlas_product_uuid: str) -> dict[str, Any]:
        return self._set_product_lifecycle(
            atlas_product_uuid,
            lifecycle_status=ProductLifecycleStatus.ACTIVE.value,
            active=True,
        )

    def assign_replacement_product(
        self,
        *,
        atlas_product_uuid: str,
        replacement_product_uuid: str,
    ) -> dict[str, Any]:
        if self._safe(atlas_product_uuid) == self._safe(replacement_product_uuid):
            raise ValueError("Product replacement cannot reference itself")
        if self._replacement_cycle_exists(atlas_product_uuid, replacement_product_uuid):
            raise ValueError("Product replacement cycle detected")
        product = self.get_product(atlas_product_uuid)
        if product is None:
            raise ValueError("Product not found")
        product["replacement_product_uuid"] = self._safe(replacement_product_uuid)
        product["lifecycle_status"] = ProductLifecycleStatus.REPLACEMENT_AVAILABLE.value
        product["updated_at"] = self._now_iso()
        self._persist_product(product)
        return dict(product)

    # Vendor offering management
    def create_vendor_offering(
        self,
        *,
        vendor_id: str,
        vendor: str,
        atlas_product_uuid: str,
        vendor_sku: str,
        purchasing_channel: str,
        direct_from_manufacturer: bool,
        authorization_status: str,
        minimum_order_quantity: int | None,
        order_multiple: int | None,
        unit_of_measure: str,
        pack_quantity: int | None,
        lead_time_notes: str,
        active: bool = True,
        notes: str = "",
    ) -> dict[str, Any]:
        self._validate_purchasing_channel(purchasing_channel)
        if self.get_product(atlas_product_uuid) is None:
            raise ValueError("Vendor offering requires a valid product reference")
        if self.get_vendor(vendor_id) is None and not self.search_vendors(vendor):
            raise ValueError("Vendor offering requires a valid vendor reference")

        duplicate = self.find_vendor_offering(
            vendor_id=vendor_id, atlas_product_uuid=atlas_product_uuid
        )
        if duplicate is not None:
            raise ValueError("Duplicate vendor/product offering detected")

        if minimum_order_quantity is not None and minimum_order_quantity < 0:
            raise ValueError("minimum_order_quantity must be non-negative")
        if pack_quantity is not None and pack_quantity < 0:
            raise ValueError("pack_quantity must be non-negative")
        if order_multiple is not None and order_multiple <= 0:
            raise ValueError("order_multiple must be positive")

        now = self._now_iso()
        offering_id = self._vendor_offering_id(
            atlas_product_uuid,
            self._safe(vendor),
            self.normalize_vendor_sku(vendor_sku),
        )
        record = {
            "vendor_offering_id": offering_id,
            "vendor_id": self._safe(vendor_id),
            "atlas_product_uuid": self._safe(atlas_product_uuid),
            "vendor": self._safe(vendor),
            "vendor_sku": self._safe(vendor_sku),
            "normalized_vendor_sku": self.normalize_vendor_sku(vendor_sku),
            "purchasing_channel": self._safe(purchasing_channel),
            "direct_from_manufacturer": bool(direct_from_manufacturer),
            "authorization_status": self._safe(authorization_status, "unknown"),
            "minimum_order_quantity": minimum_order_quantity,
            "order_multiple": order_multiple,
            "unit_of_measure": self._safe(unit_of_measure, "ea"),
            "pack_quantity": pack_quantity,
            "lead_time_notes": self._safe(lead_time_notes),
            "active": bool(active),
            "notes": self._safe(notes),
            "created_at": now,
            "updated_at": now,
            "price_version": "",
            "pricing_available": False,
        }
        self.state.setdefault("vendor_offerings", {})[offering_id] = record
        return dict(record)

    def update_vendor_offering(
        self,
        vendor_offering_id: str,
        *,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        current = dict(
            self.state.get("vendor_offerings", {}).get(
                self._safe(vendor_offering_id), {}
            )
        )
        if not current:
            raise ValueError("Vendor offering not found")
        if "purchasing_channel" in updates:
            self._validate_purchasing_channel(updates.get("purchasing_channel"))
            current["purchasing_channel"] = self._safe(
                updates.get("purchasing_channel"),
                self._safe(current.get("purchasing_channel"), "other"),
            )
        for key in [
            "authorization_status",
            "unit_of_measure",
            "lead_time_notes",
            "notes",
        ]:
            if key in updates:
                current[key] = self._safe(
                    updates.get(key), self._safe(current.get(key), "")
                )

        for key in ["minimum_order_quantity", "pack_quantity"]:
            candidate = updates.get(key)
            parsed_value = self._int_or_none(candidate)
            if key in updates and candidate is not None and parsed_value is None:
                raise ValueError(f"{key} must be an integer")
            if key in updates and parsed_value is not None and parsed_value < 0:
                raise ValueError(f"{key} must be non-negative")
            if key in updates:
                current[key] = parsed_value

        if "order_multiple" in updates:
            value = updates.get("order_multiple")
            parsed_order_multiple = self._int_or_none(value)
            if value is not None and parsed_order_multiple is None:
                raise ValueError("order_multiple must be an integer")
            if parsed_order_multiple is not None and parsed_order_multiple <= 0:
                raise ValueError("order_multiple must be positive")
            current["order_multiple"] = parsed_order_multiple

        if "active" in updates:
            current["active"] = bool(updates.get("active"))
        if "direct_from_manufacturer" in updates:
            current["direct_from_manufacturer"] = bool(
                updates.get("direct_from_manufacturer")
            )

        current["updated_at"] = self._now_iso()
        self.state.setdefault("vendor_offerings", {})[
            self._safe(vendor_offering_id)
        ] = current
        return dict(current)

    def list_vendor_offerings_by_vendor(self, vendor_id: str) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in self.state.get("vendor_offerings", {}).values()
            if self._safe(item.get("vendor_id"), "") == self._safe(vendor_id)
        ]

    def list_vendor_offerings_by_product(
        self, atlas_product_uuid: str
    ) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in self.state.get("vendor_offerings", {}).values()
            if self._safe(item.get("atlas_product_uuid"), "")
            == self._safe(atlas_product_uuid)
        ]

    def search_vendor_offerings_by_vendor_sku(
        self, vendor_sku: str
    ) -> list[dict[str, Any]]:
        target = self.normalize_vendor_sku(vendor_sku)
        return [
            dict(item)
            for item in self.state.get("vendor_offerings", {}).values()
            if self.normalize_vendor_sku(item.get("vendor_sku", "")) == target
        ]

    def search_vendor_offerings_by_manufacturer_part_number(
        self, manufacturer_part_number: str
    ) -> list[dict[str, Any]]:
        part_norm = self.normalize_part_number(manufacturer_part_number)
        product_ids = {
            self._safe(item.get("atlas_product_uuid"), "")
            for item in self.state.get("products", {}).values()
            if self.normalize_part_number(
                item.get("manufacturer_part_number", item.get("manufacturer_sku", ""))
            )
            == part_norm
        }
        return [
            dict(item)
            for item in self.state.get("vendor_offerings", {}).values()
            if self._safe(item.get("atlas_product_uuid"), "") in product_ids
        ]

    def set_vendor_offering_active(
        self, vendor_offering_id: str, active: bool
    ) -> dict[str, Any]:
        return self.update_vendor_offering(
            vendor_offering_id,
            updates={"active": bool(active)},
        )

    def find_vendor_offering(
        self,
        *,
        vendor_id: str,
        atlas_product_uuid: str,
    ) -> dict[str, Any] | None:
        for item in self.state.get("vendor_offerings", {}).values():
            if self._safe(item.get("vendor_id"), "") == self._safe(
                vendor_id
            ) and self._safe(item.get("atlas_product_uuid"), "") == self._safe(
                atlas_product_uuid
            ):
                return dict(item)
        return None

    # Price sheet foundation
    def create_price_sheet(
        self,
        *,
        name: str,
        vendor_id: str,
        vendor: str,
        manufacturer_id: str | None,
        manufacturer: str | None,
        purchasing_channel: str,
        currency: str,
        active: bool = True,
        notes: str = "",
    ) -> dict[str, Any]:
        self._validate_purchasing_channel(purchasing_channel)
        self._validate_currency(currency)
        sheet_id = self._sheet_id(
            self._safe(vendor, self._safe(vendor_id)),
            self._safe(manufacturer, self._safe(manufacturer_id)),
            self._safe(name),
        )
        now = self._now_iso()
        record = {
            "price_sheet_id": sheet_id,
            "name": self._safe(name),
            "vendor_id": self._safe(vendor_id),
            "vendor": self._safe(vendor),
            "manufacturer_id": self._safe(manufacturer_id),
            "manufacturer": self._safe(manufacturer),
            "purchasing_channel": self._safe(purchasing_channel),
            "currency": self._safe(currency),
            "active": bool(active),
            "notes": self._safe(notes),
            "created_at": now,
            "updated_at": now,
            "active_version": "",
        }
        self.state.setdefault("price_sheets", {})[sheet_id] = record
        return dict(record)

    def get_price_sheet(self, price_sheet_id: str) -> dict[str, Any] | None:
        return (
            dict(self.state.get("price_sheets", {}).get(self._safe(price_sheet_id), {}))
            or None
        )

    def list_price_sheets(
        self,
        *,
        vendor_id: str | None = None,
        manufacturer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = list(self.state.get("price_sheets", {}).values())
        if vendor_id:
            rows = [
                item
                for item in rows
                if self._safe(item.get("vendor_id"), "") == self._safe(vendor_id)
            ]
        if manufacturer_id:
            rows = [
                item
                for item in rows
                if self._safe(item.get("manufacturer_id"), "")
                == self._safe(manufacturer_id)
            ]
        rows.sort(key=lambda item: self._safe(item.get("name"), "").lower())
        return [dict(item) for item in rows]

    def parse_import_source(
        self,
        *,
        source_filename: str,
        file_bytes: bytes,
        worksheet: str | None = None,
        header_row_index: int = 0,
    ) -> dict[str, Any]:
        extension = self._file_extension(source_filename)
        if extension == ".csv":
            parsed = self._parse_csv_rows(file_bytes)
        elif extension in {".xlsx", ".xls"}:
            parsed = self._parse_xlsx_rows(
                file_bytes=file_bytes,
                worksheet=worksheet,
                header_row_index=header_row_index,
            )
        else:
            raise ValueError("Unsupported source format; only CSV and XLSX are allowed")

        return {
            "source_filename": self._safe(source_filename),
            "extension": extension,
            "rows": list(parsed.get("rows") or []),
            "headers": list(parsed.get("headers") or []),
            "worksheets": list(parsed.get("worksheets") or []),
            "selected_worksheet": self._safe(parsed.get("selected_worksheet"), ""),
            "header_row_index": int(parsed.get("header_row_index", header_row_index)),
            "diagnostics": list(parsed.get("diagnostics") or []),
        }

    def inspect_pdf_import_source(
        self,
        *,
        source_filename: str,
        file_bytes: bytes,
    ) -> dict[str, Any]:
        diagnostics: list[dict[str, Any]] = []
        if self._file_extension(source_filename) != ".pdf":
            raise ValueError("PDF inspection requires a .pdf source file")

        source_hash = hashlib.sha1(file_bytes).hexdigest()
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
        except Exception:
            return {
                "source_filename": self._safe(source_filename),
                "source_hash": source_hash,
                "valid_pdf": False,
                "page_count": 0,
                "pages": [],
                "table_candidates": [],
                "repeated_headers": [],
                "repeated_footers": [],
                "diagnostics": [
                    {
                        "severity": ImportDiagnosticSeverity.ERROR.value,
                        "code": "malformed_pdf",
                        "message": "Malformed PDF could not be parsed.",
                        "row_number": None,
                    }
                ],
            }

        if getattr(reader, "is_encrypted", False):
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.ERROR.value,
                    "code": "encrypted_pdf",
                    "message": "Encrypted PDF is unsupported for import.",
                    "row_number": None,
                }
            )
            return {
                "source_filename": self._safe(source_filename),
                "source_hash": source_hash,
                "valid_pdf": True,
                "page_count": 0,
                "pages": [],
                "table_candidates": [],
                "repeated_headers": [],
                "repeated_footers": [],
                "inspection_status": {
                    "status": "unsupported",
                    "extraction_mode": "unsupported",
                },
                "diagnostics": diagnostics,
            }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)
        try:
            intake = DocumentIntakeService(enable_local_ocr=True)
            pages, intake_warnings, status = intake._extract_document_pages(
                tmp_path,
                "schedules",
            )
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

        page_records: list[dict[str, Any]] = []
        first_line_counts: dict[str, int] = {}
        last_line_counts: dict[str, int] = {}
        for page in pages:
            page_number = int(page.get("page_number") or 0)
            text = self._safe(page.get("text"), "")
            text_lines = [line.strip() for line in text.splitlines() if line.strip()]
            first_line = text_lines[0] if text_lines else ""
            last_line = text_lines[-1] if text_lines else ""
            if first_line:
                first_line_counts[first_line] = first_line_counts.get(first_line, 0) + 1
            if last_line:
                last_line_counts[last_line] = last_line_counts.get(last_line, 0) + 1
            rotation = 0
            try:
                if 1 <= page_number <= len(reader.pages):
                    rotation = int(reader.pages[page_number - 1].get("/Rotate", 0) or 0)
            except Exception:
                rotation = 0
            if rotation:
                diagnostics.append(
                    {
                        "severity": ImportDiagnosticSeverity.WARNING.value,
                        "code": "rotated_page",
                        "message": f"Page {page_number} has rotation={rotation}.",
                        "row_number": page_number,
                    }
                )
            if self._safe(page.get("text_source"), "") == "ocr":
                diagnostics.append(
                    {
                        "severity": ImportDiagnosticSeverity.WARNING.value,
                        "code": "ocr_required",
                        "message": f"Page {page_number} required OCR extraction.",
                        "row_number": page_number,
                    }
                )
                diagnostics.append(
                    {
                        "severity": ImportDiagnosticSeverity.WARNING.value,
                        "code": "low_ocr_reliability",
                        "message": f"Page {page_number} OCR reliability may be low; verify before finalization.",
                        "row_number": page_number,
                    }
                )
            page_records.append(
                {
                    "page_number": page_number,
                    "text_source": self._safe(page.get("text_source"), "none"),
                    "ocr_derived": bool(page.get("ocr_derived", False)),
                    "has_text": bool(page.get("has_text", False)),
                    "rotation": rotation,
                    "line_count": len(text_lines),
                    "preview": " ".join(text_lines[:3])[:240],
                    "text_lines": text_lines,
                }
            )

        for warning in intake_warnings:
            lower = self._safe(warning).lower()
            code = "unsupported_document_structure"
            severity = ImportDiagnosticSeverity.WARNING.value
            if "no embedded text" in lower:
                code = "no_extractable_text"
                severity = ImportDiagnosticSeverity.WARNING.value
            if "ocr attempted but no text" in lower:
                code = "ocr_failure"
                severity = ImportDiagnosticSeverity.ERROR.value
            diagnostics.append(
                {
                    "severity": severity,
                    "code": code,
                    "message": self._safe(warning),
                    "row_number": None,
                }
            )

        repeated_headers = [
            text for text, count in first_line_counts.items() if count >= 2
        ]
        repeated_footers = [
            text for text, count in last_line_counts.items() if count >= 2
        ]
        for header in repeated_headers:
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.INFORMATIONAL.value,
                    "code": "repeated_page_headers",
                    "message": f"Repeated page header detected: {header}",
                    "row_number": None,
                }
            )
        for footer in repeated_footers:
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.INFORMATIONAL.value,
                    "code": "repeated_page_footers",
                    "message": f"Repeated page footer detected: {footer}",
                    "row_number": None,
                }
            )

        table_candidates = self._detect_pdf_table_candidates(
            pages=page_records,
            repeated_headers=repeated_headers,
            repeated_footers=repeated_footers,
        )
        if not table_candidates:
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.ERROR.value,
                    "code": "no_table_candidate_found",
                    "message": "No table candidate found in selected PDF.",
                    "row_number": None,
                }
            )
        if len(table_candidates) > 1:
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.WARNING.value,
                    "code": "multiple_table_candidates_found",
                    "message": "Multiple table candidates detected; user selection required.",
                    "row_number": None,
                }
            )

        return {
            "source_filename": self._safe(source_filename),
            "source_hash": source_hash,
            "valid_pdf": True,
            "page_count": len(reader.pages),
            "pages": page_records,
            "table_candidates": table_candidates,
            "repeated_headers": repeated_headers,
            "repeated_footers": repeated_footers,
            "inspection_status": dict(status),
            "diagnostics": diagnostics,
        }

    def create_pdf_import_draft(
        self,
        *,
        price_sheet_id: str,
        source_filename: str,
        file_bytes: bytes,
        version_label: str,
        effective_date: str,
        expiration_date: str,
        currency: str,
        selected_pages: list[int],
        table_candidate_id: str,
        header_row_index: int,
        column_mapping: dict[str, str],
        row_corrections: dict[int, dict[str, Any]] | None = None,
        imported_by: str = "atlas",
    ) -> dict[str, Any]:
        sheet = self.get_price_sheet(price_sheet_id)
        if sheet is None:
            raise ValueError("Price sheet not found")

        inspected = self.inspect_pdf_import_source(
            source_filename=source_filename,
            file_bytes=file_bytes,
        )
        candidates = list(inspected.get("table_candidates") or [])
        selected_candidate = next(
            (
                item
                for item in candidates
                if self._safe(item.get("candidate_id"), "")
                == self._safe(table_candidate_id)
            ),
            None,
        )
        if selected_candidate is None:
            raise ValueError("Selected table candidate was not found")

        selected_page_set = {int(value) for value in selected_pages if int(value) > 0}
        if not selected_page_set:
            raise ValueError("At least one page must be selected")

        raw_rows = [
            dict(row)
            for row in list(selected_candidate.get("rows") or [])
            if int(row.get("page_number") or 0) in selected_page_set
        ]
        if not raw_rows:
            raise ValueError("No rows found for selected pages and table candidate")

        header_index = max(0, int(header_row_index))
        if header_index >= len(raw_rows):
            header_index = 0
        header_source = list(raw_rows[header_index].get("cells") or [])
        headers = [
            self._safe(value) or f"column_{idx + 1}"
            for idx, value in enumerate(header_source)
        ]

        mapping = self._normalized_mapping(column_mapping, headers)

        transformed_rows: list[dict[str, Any]] = []
        transformation_diagnostics: list[dict[str, Any]] = []
        header_like_count = sum(
            1
            for row in raw_rows[:5]
            if all(
                not bool(re.search(r"\d", self._safe(cell)))
                for cell in list(row.get("cells") or [])
                if self._safe(cell)
            )
        )
        if header_like_count > 1:
            transformation_diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.WARNING.value,
                    "code": "ambiguous_header_row",
                    "message": "Multiple potential header rows detected; confirm header row selection.",
                    "row_number": None,
                }
            )

        selected_pages_sorted = sorted(selected_page_set)
        if len(selected_pages_sorted) > 1:
            for current, nxt in zip(selected_pages_sorted, selected_pages_sorted[1:]):
                if nxt - current > 1:
                    transformation_diagnostics.append(
                        {
                            "severity": ImportDiagnosticSeverity.INFORMATIONAL.value,
                            "code": "uncertain_row_segmentation",
                            "message": "Non-contiguous selected pages may affect row segmentation certainty.",
                            "row_number": None,
                        }
                    )
                    break

        for idx, row in enumerate(raw_rows):
            if idx == header_index:
                continue
            cells = list(row.get("cells") or [])
            row_map: dict[str, Any] = {
                headers[col_idx]: self._safe(
                    cells[col_idx] if col_idx < len(cells) else ""
                )
                for col_idx in range(len(headers))
            }
            row_map["source_page_number"] = int(row.get("page_number") or 0)
            row_map["source_region_reference"] = self._safe(row.get("region_id"), "")
            row_map["source_row_reference"] = self._safe(row.get("row_reference"), "")
            row_map["extraction_method"] = self._safe(
                row.get("extraction_method"), "embedded"
            )
            row_map["ocr_status"] = self._safe(row.get("ocr_status"), "not_required")
            row_map["raw_extracted_values"] = dict(row_map)
            sequence_number = int(row.get("sequence_number") or 0)
            if row_corrections and sequence_number in row_corrections:
                for key, value in dict(row_corrections[sequence_number] or {}).items():
                    row_map[self._safe(key)] = self._safe(value)
            transformed_rows.append(row_map)

            if len(cells) != len(headers):
                transformation_diagnostics.append(
                    {
                        "severity": ImportDiagnosticSeverity.WARNING.value,
                        "code": "inconsistent_column_count",
                        "message": f"Row {row.get('sequence_number')} has inconsistent column count.",
                        "row_number": int(row.get("sequence_number") or 0),
                    }
                )
                if len(cells) < len(headers):
                    transformation_diagnostics.append(
                        {
                            "severity": ImportDiagnosticSeverity.WARNING.value,
                            "code": "merged_cells",
                            "message": f"Row {row.get('sequence_number')} may contain merged cells.",
                            "row_number": int(row.get("sequence_number") or 0),
                        }
                    )

        page_row_counts: dict[int, int] = {}
        for row in transformed_rows:
            page_number = int(row.get("source_page_number") or 0)
            page_row_counts[page_number] = page_row_counts.get(page_number, 0) + 1
        if len(page_row_counts) > 1:
            transformation_diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.INFORMATIONAL.value,
                    "code": "rows_split_across_pages",
                    "message": "Rows span multiple pages; review split-page row boundaries.",
                    "row_number": None,
                }
            )

        duplicate_row_key_counts: dict[str, int] = {}
        for row in transformed_rows:
            key = "|".join(
                [
                    self.normalize_part_number(
                        self._safe(
                            row.get(mapping.get("manufacturer_part_number", ""), "")
                        )
                    ),
                    self.normalize_vendor_sku(
                        self._safe(row.get(mapping.get("vendor_sku", ""), ""))
                    ),
                    self._safe(str(row.get("source_page_number") or "")),
                ]
            )
            duplicate_row_key_counts[key] = duplicate_row_key_counts.get(key, 0) + 1
        if any(count > 1 for count in duplicate_row_key_counts.values()):
            transformation_diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.WARNING.value,
                    "code": "conflicting_duplicate_rows",
                    "message": "Potential duplicate/conflicting rows detected in extracted table data.",
                    "row_number": None,
                }
            )

        for row in transformed_rows:
            description_value = self._safe(row.get(mapping.get("description", ""), ""))
            if description_value and len(description_value) > 140:
                transformation_diagnostics.append(
                    {
                        "severity": ImportDiagnosticSeverity.INFORMATIONAL.value,
                        "code": "wrapped_descriptions",
                        "message": "Long description may indicate wrapped text from PDF extraction.",
                        "row_number": (
                            int(row.get("source_row_reference", "0").split(":row")[-1])
                            if ":row" in self._safe(row.get("source_row_reference"), "")
                            else None
                        ),
                    }
                )

        validation = self._validate_import_preview_rows(
            raw_rows=transformed_rows,
            mapping=mapping,
            sheet=sheet,
            currency=currency,
            effective_date=effective_date,
            expiration_date=expiration_date,
        )

        preview_rows = []
        for preview in list(validation.get("preview_rows") or []):
            source_page_number = int(
                preview.get("raw_values", {}).get("source_page_number") or 0
            )
            source_region_reference = self._safe(
                preview.get("raw_values", {}).get("source_region_reference"), ""
            )
            source_row_reference = self._safe(
                preview.get("raw_values", {}).get("source_row_reference"), ""
            )
            extraction_method = self._safe(
                preview.get("raw_values", {}).get("extraction_method"), "embedded"
            )
            ocr_status = self._safe(
                preview.get("raw_values", {}).get("ocr_status"), "not_required"
            )
            updated = dict(preview)
            updated["source_page_number"] = source_page_number
            updated["source_region_reference"] = source_region_reference
            updated["source_row_reference"] = source_row_reference
            updated["extraction_method"] = extraction_method
            updated["ocr_status"] = ocr_status
            updated["raw_extracted_values"] = dict(preview.get("raw_values") or {})
            preview_rows.append(updated)

        file_hash = hashlib.sha1(file_bytes).hexdigest()
        diagnostics = list(inspected.get("diagnostics") or []) + list(
            transformation_diagnostics
        )
        diagnostics.extend(list(validation.get("diagnostics") or []))
        duplicate_versions = self.find_versions_by_source_hash(file_hash)
        if duplicate_versions:
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.WARNING.value,
                    "code": "duplicate_source_hash",
                    "message": "Source file hash already exists in version history.",
                    "row_number": None,
                }
            )

        draft_id = self._draft_id(
            price_sheet_id=price_sheet_id,
            source_filename=source_filename,
            source_hash=file_hash,
            version_label=version_label,
        )
        has_errors = any(
            item.get("severity") == ImportDiagnosticSeverity.ERROR.value
            for item in diagnostics
        )
        draft_status = (
            PriceSheetVersionStatus.DRAFT.value
            if has_errors
            else PriceSheetVersionStatus.VALIDATED.value
        )

        draft = {
            "draft_id": draft_id,
            "price_sheet_id": self._safe(price_sheet_id),
            "version_label": self._safe(version_label),
            "effective_date": self._safe(effective_date),
            "expiration_date": self._safe(expiration_date),
            "source_filename": self._safe(source_filename),
            "source_hash": file_hash,
            "currency": self._safe(currency),
            "worksheet": "pdf",
            "header_row_index": int(header_index),
            "column_mapping": dict(mapping),
            "preview_rows": preview_rows,
            "diagnostics": diagnostics,
            "status": draft_status,
            "record_count": len(preview_rows),
            "unresolved_count": int(validation.get("unresolved_count", 0) or 0),
            "error_count": int(validation.get("error_count", 0) or 0)
            + sum(
                1
                for item in diagnostics
                if item.get("severity") == ImportDiagnosticSeverity.ERROR.value
            ),
            "warning_count": int(validation.get("warning_count", 0) or 0)
            + sum(
                1
                for item in diagnostics
                if item.get("severity") == ImportDiagnosticSeverity.WARNING.value
            ),
            "acknowledged_warnings": False,
            "imported_by": self._safe(imported_by, "atlas"),
            "source_metadata": (
                f"pdf_pages={','.join(str(v) for v in sorted(selected_page_set))};"
                f"table_candidate={self._safe(table_candidate_id)};header_row={header_index}"
            ),
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
            "pdf_inspection": {
                "page_count": int(inspected.get("page_count") or 0),
                "selected_pages": sorted(selected_page_set),
                "table_candidate_id": self._safe(table_candidate_id),
                "repeated_headers": list(inspected.get("repeated_headers") or []),
                "repeated_footers": list(inspected.get("repeated_footers") or []),
            },
        }
        self.state.setdefault("price_sheet_drafts", {})[draft_id] = draft
        return dict(draft)

    def suggest_column_mapping(self, headers: list[str]) -> dict[str, str]:
        synonyms: dict[str, set[str]] = {
            "manufacturer": {"manufacturer", "mfr", "brand"},
            "manufacturer_part_number": {
                "manufacturer part number",
                "manufacturer_pn",
                "mfr pn",
                "mfr part",
                "part number",
                "part_no",
                "mpn",
                "model",
            },
            "vendor_sku": {"vendor sku", "sku", "item code", "vendor_part", "vpn"},
            "description": {
                "description",
                "item description",
                "product description",
                "desc",
            },
            "unit_cost": {"unit cost", "cost", "net cost", "dealer cost", "price"},
            "list_price": {"list price", "msrp", "retail", "map"},
            "currency": {"currency", "curr"},
            "unit_of_measure": {"uom", "unit", "unit of measure"},
            "pack_quantity": {"pack qty", "pack quantity", "case qty", "qty per pack"},
            "minimum_order_quantity": {
                "moq",
                "minimum order quantity",
                "min qty",
                "min order",
            },
            "effective_date_override": {"effective date", "effective", "start date"},
            "source_category": {"category", "manufacturer category", "source category"},
            "notes": {"notes", "comments", "remark", "remarks"},
        }
        header_lookup = {
            self.normalize_name(item).replace("-", " "): self._safe(item)
            for item in headers
            if self._safe(item)
        }
        mapping: dict[str, str] = {}
        for target, options in synonyms.items():
            for option in options:
                normalized = self.normalize_name(option).replace("-", " ")
                if normalized in header_lookup:
                    mapping[target] = header_lookup[normalized]
                    break
        return mapping

    def save_mapping_profile(
        self,
        *,
        profile_name: str,
        mapping: dict[str, str],
        vendor_id: str = "",
        price_sheet_id: str = "",
    ) -> dict[str, Any]:
        name = self._safe(profile_name)
        if not name:
            raise ValueError("profile_name cannot be blank")
        profile_id = self._mapping_profile_id(name, vendor_id, price_sheet_id)
        profile = {
            "profile_id": profile_id,
            "profile_name": name,
            "vendor_id": self._safe(vendor_id),
            "price_sheet_id": self._safe(price_sheet_id),
            "mapping": {
                self._safe(key): self._safe(value)
                for key, value in dict(mapping or {}).items()
                if self._safe(key) and self._safe(value)
            },
            "updated_at": self._now_iso(),
        }
        self.state.setdefault("mapping_profiles", {})[profile_id] = profile
        return dict(profile)

    def list_mapping_profiles(
        self,
        *,
        vendor_id: str | None = None,
        price_sheet_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = list(self.state.get("mapping_profiles", {}).values())
        if vendor_id:
            rows = [
                item
                for item in rows
                if self._safe(item.get("vendor_id"), "") == self._safe(vendor_id)
            ]
        if price_sheet_id:
            rows = [
                item
                for item in rows
                if self._safe(item.get("price_sheet_id"), "")
                == self._safe(price_sheet_id)
            ]
        rows.sort(key=lambda item: self._safe(item.get("profile_name"), "").lower())
        return [dict(item) for item in rows]

    def create_import_draft(
        self,
        *,
        price_sheet_id: str,
        source_filename: str,
        file_bytes: bytes,
        version_label: str,
        effective_date: str,
        expiration_date: str,
        currency: str,
        worksheet: str | None,
        header_row_index: int,
        column_mapping: dict[str, str],
        mapping_profile_name: str = "",
        vendor_id: str = "",
        imported_by: str = "atlas",
    ) -> dict[str, Any]:
        sheet = self.get_price_sheet(price_sheet_id)
        if sheet is None:
            raise ValueError("Price sheet not found")
        self._validate_currency(currency)
        self._validate_effective_expiration(effective_date, expiration_date)

        parsed = self.parse_import_source(
            source_filename=source_filename,
            file_bytes=file_bytes,
            worksheet=worksheet,
            header_row_index=header_row_index,
        )
        mapping = self._normalized_mapping(
            column_mapping, list(parsed.get("headers") or [])
        )
        validation = self._validate_import_preview_rows(
            raw_rows=list(parsed.get("rows") or []),
            mapping=mapping,
            sheet=sheet,
            currency=currency,
            effective_date=effective_date,
            expiration_date=expiration_date,
        )

        file_hash = hashlib.sha1(file_bytes).hexdigest()
        duplicate_hash_versions = self.find_versions_by_source_hash(file_hash)
        hash_warning = {
            "severity": ImportDiagnosticSeverity.WARNING.value,
            "code": "duplicate_source_hash",
            "message": "Source file hash already exists in version history.",
            "row_number": None,
        }
        diagnostics = list(validation.get("diagnostics") or [])
        if duplicate_hash_versions:
            diagnostics.append(hash_warning)

        draft_id = self._draft_id(
            price_sheet_id=price_sheet_id,
            source_filename=source_filename,
            source_hash=file_hash,
            version_label=version_label,
        )
        status = PriceSheetVersionStatus.DRAFT.value
        if not any(
            item.get("severity") == ImportDiagnosticSeverity.ERROR.value
            for item in diagnostics
        ):
            status = PriceSheetVersionStatus.VALIDATED.value

        draft = {
            "draft_id": draft_id,
            "price_sheet_id": self._safe(price_sheet_id),
            "version_label": self._safe(version_label),
            "effective_date": self._safe(effective_date),
            "expiration_date": self._safe(expiration_date),
            "source_filename": self._safe(source_filename),
            "source_hash": file_hash,
            "currency": self._safe(currency),
            "worksheet": self._safe(worksheet),
            "header_row_index": int(header_row_index),
            "column_mapping": dict(mapping),
            "preview_rows": list(validation.get("preview_rows") or []),
            "diagnostics": diagnostics,
            "status": status,
            "record_count": len(list(validation.get("preview_rows") or [])),
            "unresolved_count": int(validation.get("unresolved_count", 0) or 0),
            "error_count": int(validation.get("error_count", 0) or 0),
            "warning_count": int(validation.get("warning_count", 0) or 0),
            "acknowledged_warnings": False,
            "imported_by": self._safe(imported_by, "atlas"),
            "source_metadata": f"worksheet={self._safe(worksheet, 'sheet1')};header_row={int(header_row_index)}",
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
        }
        self.state.setdefault("price_sheet_drafts", {})[draft_id] = draft
        if self._safe(mapping_profile_name):
            self.save_mapping_profile(
                profile_name=mapping_profile_name,
                mapping=mapping,
                vendor_id=vendor_id or self._safe(sheet.get("vendor_id"), ""),
                price_sheet_id=price_sheet_id,
            )
        return dict(draft)

    def create_manual_draft_version(
        self,
        *,
        price_sheet_id: str,
        version_label: str,
        effective_date: str,
        expiration_date: str = "",
        currency: str = "USD",
        imported_by: str = "atlas",
    ) -> dict[str, Any]:
        sheet = self.get_price_sheet(price_sheet_id)
        if sheet is None:
            raise ValueError("Price sheet not found")
        self._validate_currency(currency)
        self._validate_effective_expiration(effective_date, expiration_date)
        draft_id = self._draft_id(
            price_sheet_id=price_sheet_id,
            source_filename="manual-entry",
            source_hash=f"manual-{self._now_iso()}",
            version_label=version_label,
        )
        draft = {
            "draft_id": draft_id,
            "price_sheet_id": self._safe(price_sheet_id),
            "version_label": self._safe(version_label),
            "effective_date": self._safe(effective_date),
            "expiration_date": self._safe(expiration_date),
            "source_filename": "manual-entry",
            "source_hash": hashlib.sha1(
                f"manual:{draft_id}".encode("utf-8")
            ).hexdigest(),
            "currency": self._safe(currency),
            "worksheet": "",
            "header_row_index": 0,
            "column_mapping": {},
            "preview_rows": [],
            "diagnostics": [],
            "status": PriceSheetVersionStatus.DRAFT.value,
            "record_count": 0,
            "unresolved_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "acknowledged_warnings": False,
            "imported_by": self._safe(imported_by, "atlas"),
            "source_metadata": "manual_entry=true",
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
        }
        self.state.setdefault("price_sheet_drafts", {})[draft_id] = draft
        return dict(draft)

    def add_manual_price_record_to_draft(
        self,
        draft_id: str,
        *,
        manufacturer_part_number_imported: str,
        vendor_sku_imported: str,
        description_imported: str,
        unit_cost: float | None,
        list_price: float | None,
        unit_of_measure: str = "ea",
        pack_quantity: int | None = None,
        minimum_order_quantity: int | None = None,
        effective_date_override: str = "",
        source_category: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        draft = self.get_price_sheet_draft(draft_id)
        if draft is None:
            raise ValueError("Draft not found")
        if (
            self._safe(draft.get("status"), "")
            == PriceSheetVersionStatus.FINALIZED.value
        ):
            raise ValueError("Finalized drafts are immutable")

        row_number = len(list(draft.get("preview_rows") or [])) + 1
        row = {
            "source_row_number": row_number,
            "manufacturer": self._safe(
                dict(
                    self.get_price_sheet(self._safe(draft.get("price_sheet_id"), ""))
                    or {}
                ).get("manufacturer"),
                "",
            ),
            "manufacturer_part_number_imported": self._safe(
                manufacturer_part_number_imported
            ),
            "vendor_sku_imported": self._safe(vendor_sku_imported),
            "description_imported": self._safe(description_imported),
            "unit_cost": self._float_or_none(unit_cost),
            "list_price": self._float_or_none(list_price),
            "currency": self._safe(draft.get("currency"), "USD"),
            "unit_of_measure": self._safe(unit_of_measure, "ea"),
            "pack_quantity": self._int_or_none(pack_quantity),
            "minimum_order_quantity": self._int_or_none(minimum_order_quantity),
            "effective_date_override": self._safe(effective_date_override),
            "source_category": self._safe(source_category),
            "notes": self._safe(notes),
            "atlas_product_uuid": "",
            "vendor_offering_id": "",
            "resolution_status": "unresolved",
            "diagnostic_messages": [],
            "validation_status": "valid",
            "raw_values": {
                "manufacturer_part_number": self._safe(
                    manufacturer_part_number_imported
                ),
                "vendor_sku": self._safe(vendor_sku_imported),
                "description": self._safe(description_imported),
            },
            "normalized_values": {
                "manufacturer_part_number": self.normalize_part_number(
                    manufacturer_part_number_imported
                ),
                "vendor_sku": self.normalize_vendor_sku(vendor_sku_imported),
            },
        }
        rows = list(draft.get("preview_rows") or [])
        rows.append(row)
        draft["preview_rows"] = rows
        draft["record_count"] = len(rows)
        draft["updated_at"] = self._now_iso()
        self.state.setdefault("price_sheet_drafts", {})[self._safe(draft_id)] = draft
        return dict(row)

    def get_price_sheet_draft(self, draft_id: str) -> dict[str, Any] | None:
        return (
            dict(self.state.get("price_sheet_drafts", {}).get(self._safe(draft_id), {}))
            or None
        )

    def update_price_sheet_draft_preview_rows(
        self,
        draft_id: str,
        *,
        preview_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        draft = self.get_price_sheet_draft(draft_id)
        if draft is None:
            raise ValueError("Draft not found")
        if (
            self._safe(draft.get("status"), "")
            == PriceSheetVersionStatus.FINALIZED.value
        ):
            raise ValueError("Finalized drafts are immutable")

        rows = [dict(row) for row in list(preview_rows or [])]
        for idx, row in enumerate(rows, start=1):
            row.setdefault("source_row_number", idx)
            row.setdefault("diagnostic_messages", [])
            row.setdefault("validation_status", "valid")
            if not self._safe(
                row.get("manufacturer_part_number_imported"), ""
            ) and not self._safe(row.get("vendor_sku_imported"), ""):
                row["validation_status"] = "invalid"
                row["diagnostic_messages"] = list(
                    row.get("diagnostic_messages") or []
                ) + [
                    "Missing product identity (manufacturer part number or vendor SKU)."
                ]
            if (
                self._float_or_none(row.get("unit_cost")) is None
                and self._float_or_none(row.get("list_price")) is None
            ):
                row["validation_status"] = "invalid"
                row["diagnostic_messages"] = list(
                    row.get("diagnostic_messages") or []
                ) + ["Missing both unit_cost and list_price."]

        diagnostics: list[dict[str, Any]] = []
        error_count = 0
        warning_count = 0
        unresolved_count = 0
        for row in rows:
            row_number = int(row.get("source_row_number") or 0)
            if self._safe(row.get("resolution_status"), "unresolved") == "unresolved":
                unresolved_count += 1
            for message in list(row.get("diagnostic_messages") or []):
                severity = ImportDiagnosticSeverity.WARNING.value
                if self._safe(row.get("validation_status"), "valid") == "invalid":
                    severity = ImportDiagnosticSeverity.ERROR.value
                diagnostics.append(
                    {
                        "severity": severity,
                        "code": "draft_row_correction_diagnostic",
                        "message": self._safe(message),
                        "row_number": row_number,
                    }
                )
                if severity == ImportDiagnosticSeverity.ERROR.value:
                    error_count += 1
                else:
                    warning_count += 1

        draft["preview_rows"] = rows
        draft["record_count"] = len(rows)
        draft["diagnostics"] = diagnostics
        draft["error_count"] = error_count
        draft["warning_count"] = warning_count
        draft["unresolved_count"] = unresolved_count
        draft["status"] = (
            PriceSheetVersionStatus.DRAFT.value
            if error_count > 0
            else PriceSheetVersionStatus.VALIDATED.value
        )
        draft["updated_at"] = self._now_iso()
        self.state.setdefault("price_sheet_drafts", {})[self._safe(draft_id)] = draft
        return dict(draft)

    def list_price_sheet_drafts(self, price_sheet_id: str = "") -> list[dict[str, Any]]:
        rows = list(self.state.get("price_sheet_drafts", {}).values())
        if self._safe(price_sheet_id):
            rows = [
                item
                for item in rows
                if self._safe(item.get("price_sheet_id"), "")
                == self._safe(price_sheet_id)
            ]
        rows.sort(key=lambda item: self._safe(item.get("created_at"), ""), reverse=True)
        return [dict(item) for item in rows]

    def validate_price_sheet_draft(
        self,
        draft_id: str,
        *,
        acknowledge_warnings: bool = False,
    ) -> dict[str, Any]:
        draft = self.get_price_sheet_draft(draft_id)
        if draft is None:
            raise ValueError("Draft not found")
        diagnostics = list(draft.get("diagnostics") or [])
        has_errors = any(
            item.get("severity") == ImportDiagnosticSeverity.ERROR.value
            for item in diagnostics
        )
        has_warnings = any(
            item.get("severity") == ImportDiagnosticSeverity.WARNING.value
            for item in diagnostics
        )
        if has_errors:
            draft["status"] = PriceSheetVersionStatus.DRAFT.value
            draft["error_count"] = sum(
                1
                for item in diagnostics
                if item.get("severity") == ImportDiagnosticSeverity.ERROR.value
            )
            draft["updated_at"] = self._now_iso()
            self.state.setdefault("price_sheet_drafts", {})[
                self._safe(draft_id)
            ] = draft
            raise ValueError("Draft contains errors and cannot be validated")
        if has_warnings and not acknowledge_warnings:
            raise ValueError(
                "Draft contains warnings; acknowledge warnings before validation"
            )
        draft["status"] = PriceSheetVersionStatus.VALIDATED.value
        draft["acknowledged_warnings"] = bool(acknowledge_warnings)
        draft["updated_at"] = self._now_iso()
        self.state.setdefault("price_sheet_drafts", {})[self._safe(draft_id)] = draft
        return dict(draft)

    def finalize_price_sheet_draft(
        self,
        draft_id: str,
        *,
        imported_by: str,
        block_duplicate_hash: bool = False,
    ) -> dict[str, Any]:
        draft = self.get_price_sheet_draft(draft_id)
        if draft is None:
            raise ValueError("Draft not found")
        if (
            self._safe(draft.get("status"), "")
            == PriceSheetVersionStatus.FINALIZED.value
        ):
            raise ValueError("Draft already finalized")
        if (
            self._safe(draft.get("status"), "")
            != PriceSheetVersionStatus.VALIDATED.value
        ):
            draft = self.validate_price_sheet_draft(
                draft_id,
                acknowledge_warnings=bool(draft.get("acknowledged_warnings", False)),
            )

        source_hash = self._safe(draft.get("source_hash"), "")
        duplicates = self.find_versions_by_source_hash(source_hash)
        if duplicates and block_duplicate_hash:
            raise ValueError(
                "Duplicate source hash detected for finalized version history"
            )

        sheet = self.get_price_sheet(self._safe(draft.get("price_sheet_id"), ""))
        if sheet is None:
            raise ValueError("Price sheet not found")

        version = self.create_price_sheet_version(
            price_sheet_id=self._safe(draft.get("price_sheet_id"), ""),
            version_label=self._safe(draft.get("version_label"), ""),
            effective_date=self._safe(draft.get("effective_date"), ""),
            expiration_date=self._safe(draft.get("expiration_date"), ""),
            source_filename=self._safe(draft.get("source_filename"), "manual-entry"),
            source_metadata=self._safe(draft.get("source_metadata"), ""),
            source_hash=source_hash,
            import_status=PriceSheetVersionStatus.FINALIZED.value,
            record_count=len(list(draft.get("preview_rows") or [])),
            imported_by=self._safe(
                imported_by, self._safe(draft.get("imported_by"), "atlas")
            ),
        )

        finalized_records: list[dict[str, Any]] = []
        for row in list(draft.get("preview_rows") or []):
            finalized_records.append(
                self.create_price_record(
                    price_sheet_version_id=self._safe(version.get("version_id"), ""),
                    vendor_offering_id=self._safe(row.get("vendor_offering_id"), ""),
                    atlas_product_uuid=self._safe(row.get("atlas_product_uuid"), ""),
                    manufacturer_part_number_imported=self._safe(
                        row.get("manufacturer_part_number_imported"), ""
                    ),
                    vendor_sku_imported=self._safe(row.get("vendor_sku_imported"), ""),
                    description_imported=self._safe(
                        row.get("description_imported"), ""
                    ),
                    unit_cost=self._float_or_none(row.get("unit_cost")),
                    list_price=self._float_or_none(row.get("list_price")),
                    currency=self._safe(
                        row.get("currency"), self._safe(draft.get("currency"), "USD")
                    ),
                    unit_of_measure=self._safe(row.get("unit_of_measure"), "ea"),
                    pack_quantity=self._int_or_none(row.get("pack_quantity")),
                    minimum_order_quantity=self._int_or_none(
                        row.get("minimum_order_quantity")
                    ),
                    effective_date_override=self._safe(
                        row.get("effective_date_override"), ""
                    ),
                    resolution_status=self._safe(
                        row.get("resolution_status"), "unresolved"
                    ),
                    source_row_reference=self._safe(row.get("source_row_number"), "0"),
                    source_page_number=self._int_or_none(row.get("source_page_number")),
                    source_region_reference=self._safe(
                        row.get("source_region_reference"), ""
                    ),
                    extraction_method=self._safe(row.get("extraction_method"), ""),
                    ocr_status=self._safe(row.get("ocr_status"), ""),
                    raw_extracted_values=dict(row.get("raw_extracted_values") or {}),
                    finalized=True,
                )
            )

        draft["status"] = PriceSheetVersionStatus.FINALIZED.value
        draft["finalized_version_id"] = self._safe(version.get("version_id"), "")
        draft["updated_at"] = self._now_iso()
        self.state.setdefault("price_sheet_drafts", {})[self._safe(draft_id)] = draft
        return {
            "version": dict(version),
            "records": finalized_records,
            "duplicate_source_hash_versions": duplicates,
        }

    def find_versions_by_source_hash(self, source_hash: str) -> list[dict[str, Any]]:
        target = self._safe(source_hash)
        if not target:
            return []
        return [
            dict(item)
            for item in self.state.get("price_list_versions", {}).values()
            if self._safe(item.get("source_hash"), "") == target
        ]

    def unresolved_price_records(
        self,
        *,
        vendor_id: str | None = None,
        manufacturer_id: str | None = None,
        price_sheet_id: str | None = None,
        version_id: str | None = None,
        severity: str | None = None,
        missing_product: bool | None = None,
        missing_vendor_offering: bool | None = None,
        duplicate_source_identity: bool | None = None,
    ) -> list[dict[str, Any]]:
        version_map = self.state.get("price_list_versions", {})
        sheet_map = self.state.get("price_sheets", {})
        unresolved: list[dict[str, Any]] = []
        for record in self.state.get("price_records", {}).values():
            if (
                self._safe(record.get("resolution_status"), "unresolved")
                != "unresolved"
            ):
                continue
            version = dict(
                version_map.get(self._safe(record.get("price_sheet_version_id"), ""))
                or {}
            )
            sheet = dict(
                sheet_map.get(self._safe(version.get("price_sheet_id"), "")) or {}
            )
            if vendor_id and self._safe(sheet.get("vendor_id"), "") != self._safe(
                vendor_id
            ):
                continue
            if manufacturer_id and self._safe(
                sheet.get("manufacturer_id"), ""
            ) != self._safe(manufacturer_id):
                continue
            if price_sheet_id and self._safe(
                version.get("price_sheet_id"), ""
            ) != self._safe(price_sheet_id):
                continue
            if version_id and self._safe(
                record.get("price_sheet_version_id"), ""
            ) != self._safe(version_id):
                continue
            enriched = {
                **dict(record),
                "vendor_id": self._safe(sheet.get("vendor_id"), ""),
                "manufacturer_id": self._safe(sheet.get("manufacturer_id"), ""),
                "price_sheet_id": self._safe(version.get("price_sheet_id"), ""),
                "version_label": self._safe(version.get("version_label"), ""),
                "source_filename": self._safe(version.get("source_filename"), ""),
                "diagnostic_severity": ImportDiagnosticSeverity.INFORMATIONAL.value,
                "duplicate_source_identity": False,
            }
            if missing_product is True and self._safe(
                record.get("atlas_product_uuid"), ""
            ):
                continue
            if missing_vendor_offering is True and self._safe(
                record.get("vendor_offering_id"), ""
            ):
                continue
            unresolved.append(enriched)

        duplicate_keys: dict[str, int] = {}
        for record in unresolved:
            key = "|".join(
                [
                    self._safe(record.get("price_sheet_version_id"), ""),
                    self.normalize_part_number(
                        record.get("manufacturer_part_number_imported", "")
                    ),
                    self.normalize_vendor_sku(record.get("vendor_sku_imported", "")),
                ]
            )
            duplicate_keys[key] = duplicate_keys.get(key, 0) + 1

        rows: list[dict[str, Any]] = []
        for record in unresolved:
            key = "|".join(
                [
                    self._safe(record.get("price_sheet_version_id"), ""),
                    self.normalize_part_number(
                        record.get("manufacturer_part_number_imported", "")
                    ),
                    self.normalize_vendor_sku(record.get("vendor_sku_imported", "")),
                ]
            )
            is_duplicate = duplicate_keys.get(key, 0) > 1
            candidate = dict(record)
            candidate["duplicate_source_identity"] = is_duplicate
            if is_duplicate:
                candidate["diagnostic_severity"] = (
                    ImportDiagnosticSeverity.WARNING.value
                )
            if duplicate_source_identity is True and not is_duplicate:
                continue
            if severity and self._safe(
                candidate.get("diagnostic_severity"), ""
            ) != self._safe(severity):
                continue
            rows.append(candidate)
        return rows

    def commercial_completeness_summary(self) -> dict[str, Any]:
        products = self.list_products(include_inactive=True)
        offerings = list(self.state.get("vendor_offerings", {}).values())
        sheets = list(self.state.get("price_sheets", {}).values())
        versions = list(self.state.get("price_list_versions", {}).values())
        records = list(self.state.get("price_records", {}).values())

        product_without_offerings = 0
        product_without_finalized_records = 0
        product_without_current_effective = 0
        for product in products:
            product_offerings = self.list_vendor_offerings_by_product(
                self._safe(product.get("atlas_product_uuid"), "")
            )
            if not product_offerings:
                product_without_offerings += 1
            product_records = [
                item
                for item in records
                if self._safe(item.get("atlas_product_uuid"), "")
                == self._safe(product.get("atlas_product_uuid"), "")
                and bool(item.get("finalized", False))
            ]
            if not product_records:
                product_without_finalized_records += 1
            if not any(self._is_record_current(item) for item in product_records):
                product_without_current_effective += 1

        offering_without_pricing = sum(
            1
            for item in offerings
            if not any(
                self._safe(record.get("vendor_offering_id"), "")
                == self._safe(item.get("vendor_offering_id"), "")
                and bool(record.get("finalized", False))
                for record in records
            )
        )
        stale_or_expired_offerings = sum(
            1
            for item in offerings
            if self._offering_pricing_freshness(item)
            in {"stale", "expired", "future_only", "missing"}
        )
        vendors_with_unresolved_records = len(
            {
                self._safe(row.get("vendor_id"), "")
                for row in self.unresolved_price_records()
                if self._safe(row.get("vendor_id"), "")
            }
        )
        sheets_without_finalized = sum(
            1
            for sheet in sheets
            if not any(
                self._safe(version.get("price_sheet_id"), "")
                == self._safe(sheet.get("price_sheet_id"), "")
                and bool(version.get("finalized", False))
                for version in versions
            )
        )
        sheets_with_pending_draft = sum(
            1
            for sheet in sheets
            if any(
                self._safe(draft.get("price_sheet_id"), "")
                == self._safe(sheet.get("price_sheet_id"), "")
                and self._safe(draft.get("status"), "")
                in {
                    PriceSheetVersionStatus.DRAFT.value,
                    PriceSheetVersionStatus.VALIDATED.value,
                }
                for draft in self.state.get("price_sheet_drafts", {}).values()
            )
        )

        return {
            "products_total": len(products),
            "products_without_offerings": product_without_offerings,
            "products_without_finalized_price_records": product_without_finalized_records,
            "products_without_current_effective_price": product_without_current_effective,
            "vendor_offerings_total": len(offerings),
            "offerings_without_pricing": offering_without_pricing,
            "offerings_stale_or_expired": stale_or_expired_offerings,
            "vendors_with_unresolved_records": vendors_with_unresolved_records,
            "price_sheets_total": len(sheets),
            "price_sheets_without_finalized_versions": sheets_without_finalized,
            "price_sheets_with_pending_drafts": sheets_with_pending_draft,
            "unresolved_price_records": len(self.unresolved_price_records()),
        }

    def create_price_sheet_version(
        self,
        *,
        price_sheet_id: str,
        version_label: str,
        effective_date: str,
        expiration_date: str,
        source_filename: str,
        source_metadata: str,
        source_hash: str,
        import_status: str,
        record_count: int,
        imported_by: str,
    ) -> dict[str, Any]:
        sheet = self.get_price_sheet(price_sheet_id)
        if sheet is None:
            raise ValueError("Price sheet not found")
        self._validate_import_status(import_status)
        self._validate_effective_expiration(effective_date, expiration_date)

        version_id = self._version_id(
            manufacturer=self._safe(sheet.get("manufacturer"), ""),
            vendor=self._safe(sheet.get("vendor"), ""),
            source_file=self._safe(source_filename),
            file_bytes=self._safe(source_hash).encode("utf-8"),
        )
        now = self._now_iso()
        record = {
            "version_id": version_id,
            "price_sheet_id": self._safe(price_sheet_id),
            "version_label": self._safe(version_label),
            "effective_date": self._safe(effective_date),
            "expiration_date": self._safe(expiration_date),
            "import_timestamp": now,
            "source_filename": self._safe(source_filename),
            "source_metadata": self._safe(source_metadata),
            "source_hash": self._safe(source_hash),
            "import_status": self._safe(import_status),
            "record_count": int(record_count),
            "imported_by": self._safe(imported_by, "atlas"),
            "finalized": self._safe(import_status) in {"imported", "finalized"},
            "created_at": now,
            "updated_at": now,
        }
        self.state.setdefault("price_list_versions", {})[version_id] = record
        sheet["active_version"] = version_id
        sheet["updated_at"] = now
        self.state.setdefault("price_sheets", {})[self._safe(price_sheet_id)] = sheet
        return dict(record)

    def get_price_sheet_version(self, version_id: str) -> dict[str, Any] | None:
        return (
            dict(
                self.state.get("price_list_versions", {}).get(
                    self._safe(version_id), {}
                )
            )
            or None
        )

    def list_price_sheet_versions(self, price_sheet_id: str) -> list[dict[str, Any]]:
        rows = [
            dict(item)
            for item in self.state.get("price_list_versions", {}).values()
            if self._safe(item.get("price_sheet_id"), "") == self._safe(price_sheet_id)
        ]
        rows.sort(
            key=lambda item: self._safe(item.get("import_timestamp"), ""), reverse=True
        )
        return rows

    def update_price_sheet_version(
        self,
        version_id: str,
        *,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        current = self.get_price_sheet_version(version_id)
        if current is None:
            raise ValueError("Price sheet version not found")
        if bool(current.get("finalized", False)):
            raise ValueError("Finalized price sheet versions are immutable")
        for key in [
            "version_label",
            "import_status",
            "record_count",
            "source_metadata",
        ]:
            if key in updates:
                if key == "import_status":
                    self._validate_import_status(updates.get(key))
                if key == "record_count":
                    parsed_record_count = self._int_or_none(updates.get(key))
                    if updates.get(key) is not None and parsed_record_count is None:
                        raise ValueError("record_count must be an integer")
                    if parsed_record_count is not None and parsed_record_count < 0:
                        raise ValueError("record_count must be non-negative")
                    current[key] = parsed_record_count
                    continue
                current[key] = updates.get(key)
        current["updated_at"] = self._now_iso()
        self.state.setdefault("price_list_versions", {})[
            self._safe(version_id)
        ] = current
        return dict(current)

    def create_price_record(
        self,
        *,
        price_sheet_version_id: str,
        vendor_offering_id: str | None,
        atlas_product_uuid: str | None,
        manufacturer_part_number_imported: str,
        vendor_sku_imported: str,
        description_imported: str,
        unit_cost: float | None,
        list_price: float | None,
        currency: str,
        unit_of_measure: str,
        pack_quantity: int | None,
        minimum_order_quantity: int | None,
        effective_date_override: str,
        resolution_status: str,
        source_row_reference: str,
        source_page_number: int | None = None,
        source_region_reference: str = "",
        extraction_method: str = "",
        ocr_status: str = "",
        raw_extracted_values: dict[str, Any] | None = None,
        finalized: bool = True,
    ) -> dict[str, Any]:
        if self.get_price_sheet_version(price_sheet_version_id) is None:
            raise ValueError("Price sheet version not found")
        self._validate_currency(currency)
        self._validate_price_record_resolution_status(resolution_status)
        if pack_quantity is not None and int(pack_quantity) < 0:
            raise ValueError("pack_quantity must be non-negative")
        if minimum_order_quantity is not None and int(minimum_order_quantity) < 0:
            raise ValueError("minimum_order_quantity must be non-negative")

        record_id = hashlib.sha1(
            f"{price_sheet_version_id}|{vendor_sku_imported}|{source_row_reference}".encode(
                "utf-8"
            )
        ).hexdigest()[:20]
        now = self._now_iso()
        record = {
            "price_record_id": f"price-record:{record_id}",
            "price_sheet_version_id": self._safe(price_sheet_version_id),
            "vendor_offering_id": self._safe(vendor_offering_id),
            "atlas_product_uuid": self._safe(atlas_product_uuid),
            "manufacturer_part_number_imported": self._safe(
                manufacturer_part_number_imported
            ),
            "vendor_sku_imported": self._safe(vendor_sku_imported),
            "description_imported": self._safe(description_imported),
            "unit_cost": self._float_or_none(unit_cost),
            "list_price": self._float_or_none(list_price),
            "currency": self._safe(currency),
            "unit_of_measure": self._safe(unit_of_measure, "ea"),
            "pack_quantity": pack_quantity,
            "minimum_order_quantity": minimum_order_quantity,
            "effective_date_override": self._safe(effective_date_override),
            "resolution_status": self._safe(resolution_status),
            "source_row_reference": self._safe(source_row_reference),
            "source_page_number": source_page_number,
            "source_region_reference": self._safe(source_region_reference),
            "extraction_method": self._safe(extraction_method),
            "ocr_status": self._safe(ocr_status),
            "raw_extracted_values": dict(raw_extracted_values or {}),
            "created_at": now,
            "finalized": bool(finalized),
        }
        self.state.setdefault("price_records", {})[record["price_record_id"]] = record
        return dict(record)

    def update_price_record(
        self, price_record_id: str, *, updates: dict[str, Any]
    ) -> dict[str, Any]:
        current = dict(
            self.state.get("price_records", {}).get(self._safe(price_record_id), {})
        )
        if not current:
            raise ValueError("Price record not found")
        if bool(current.get("finalized", True)):
            raise ValueError("Finalized price records are immutable")
        for key in [
            "description_imported",
            "resolution_status",
            "source_row_reference",
        ]:
            if key in updates:
                if key == "resolution_status":
                    self._validate_price_record_resolution_status(updates.get(key))
                current[key] = updates.get(key)
        self.state.setdefault("price_records", {})[
            self._safe(price_record_id)
        ] = current
        return dict(current)

    def import_price_list_version(
        self,
        *,
        manufacturer: str,
        vendor: str,
        source_file: str,
        file_bytes: bytes,
        import_user: str,
        rows: list[dict[str, Any]],
        effective_date: str = "",
        version_notes: str = "",
    ) -> dict[str, Any]:
        manufacturer_text = self._safe(manufacturer, "Unknown Manufacturer")
        vendor_text = self._safe(vendor, "Unknown Vendor")
        normalized_rows = [
            self._normalized_row(
                row,
                manufacturer=manufacturer_text,
                vendor=vendor_text,
            )
            for row in list(rows or [])
        ]

        row_map = {
            self._product_key(
                manufacturer=self._safe(item.get("manufacturer"), manufacturer_text),
                canonical_sku=self._safe(item.get("canonical_sku"), ""),
                manufacturer_sku=self._safe(item.get("manufacturer_sku"), ""),
            ): item
            for item in normalized_rows
            if self._safe(item.get("canonical_sku"), "")
        }

        import_key = self._import_key(manufacturer_text, vendor_text)
        previous_product_ids = set(
            self.state.get("import_index", {})
            .get(import_key, {})
            .get("product_keys", [])
        )
        current_product_ids = set(row_map.keys())

        products_added = sorted(current_product_ids - previous_product_ids)
        products_removed = sorted(previous_product_ids - current_product_ids)
        overlap = sorted(current_product_ids & previous_product_ids)

        updated_count = 0
        for product_key in overlap:
            product_uuid = (
                self.state.get("products", {})
                .get(product_key, {})
                .get("atlas_product_uuid")
            )
            if not product_uuid:
                continue
            existing = dict(self.state.get("products", {}).get(product_key) or {})
            existing_cost = self._float_or_none(
                dict(existing.get("commercial") or {}).get("preferred_cost")
            )
            new_cost = self._float_or_none(row_map[product_key].get("preferred_cost"))
            if existing_cost != new_cost:
                updated_count += 1

        version_id = self._version_id(
            manufacturer=manufacturer_text,
            vendor=vendor_text,
            source_file=source_file,
            file_bytes=file_bytes,
        )
        sheet_id = self._sheet_id(vendor_text, manufacturer_text, source_file)
        if not self.get_price_sheet(sheet_id):
            self.state.setdefault("price_sheets", {})[sheet_id] = {
                "price_sheet_id": sheet_id,
                "name": source_file,
                "vendor_id": self._safe(vendor_text).lower().replace(" ", "-"),
                "vendor": vendor_text,
                "manufacturer_id": self._safe(manufacturer_text)
                .lower()
                .replace(" ", "-"),
                "manufacturer": manufacturer_text,
                "purchasing_channel": "other",
                "currency": "USD",
                "active": True,
                "notes": "",
                "created_at": self._now_iso(),
                "updated_at": self._now_iso(),
                "active_version": "",
            }

        now_text = self._now_iso()
        self.state.setdefault("price_list_versions", {})[version_id] = {
            "version_id": version_id,
            "price_sheet_id": sheet_id,
            "import_timestamp": now_text,
            "finalized": True,
        }
        for product_key, row in row_map.items():
            self._upsert_product_from_row(
                product_key=product_key,
                row=row,
                version_id=version_id,
                import_date=now_text,
            )

            offering = self.find_vendor_offering(
                vendor_id=self._safe(vendor_text).lower().replace(" ", "-"),
                atlas_product_uuid=self._safe(
                    self.state.get("products", {})
                    .get(product_key, {})
                    .get("atlas_product_uuid"),
                    "",
                ),
            )
            self.create_price_record(
                price_sheet_version_id=version_id,
                vendor_offering_id=self._safe(
                    dict(offering or {}).get("vendor_offering_id"),
                    "",
                ),
                atlas_product_uuid=self._safe(
                    self.state.get("products", {})
                    .get(product_key, {})
                    .get("atlas_product_uuid"),
                    "",
                ),
                manufacturer_part_number_imported=self._safe(
                    row.get("manufacturer_sku"),
                    self._safe(row.get("canonical_sku"), ""),
                ),
                vendor_sku_imported=self._safe(
                    row.get("vendor_sku"),
                    self._safe(row.get("canonical_sku"), ""),
                ),
                description_imported=self._safe(row.get("description"), ""),
                unit_cost=self._float_or_none(row.get("preferred_cost")),
                list_price=self._float_or_none(row.get("msrp")),
                currency=self._safe(row.get("currency"), "USD"),
                unit_of_measure=self._safe(row.get("unit_of_measure"), "ea"),
                pack_quantity=self._int_or_none(row.get("package_quantity")),
                minimum_order_quantity=self._int_or_none(
                    row.get("minimum_order_quantity")
                ),
                effective_date_override=self._safe(
                    row.get("effective_date"),
                    now_text[:10],
                ),
                resolution_status=(
                    "resolved_vendor_offering"
                    if offering is not None
                    else "resolved_product"
                ),
                source_row_reference=self._safe(
                    row.get("source_row"),
                    product_key,
                ),
                finalized=True,
            )

        self.state.setdefault("import_index", {})[import_key] = {
            "version_id": version_id,
            "product_keys": sorted(current_product_ids),
            "import_date": now_text,
        }

        version = PriceListVersionRecord(
            version_id=version_id,
            manufacturer=manufacturer_text,
            vendor=vendor_text,
            import_date=now_text,
            effective_date=self._safe(effective_date, now_text[:10]),
            source_file=self._safe(source_file, "upload"),
            import_user=self._safe(import_user, "atlas"),
            product_count=len(current_product_ids),
            products_added=len(products_added),
            products_updated=updated_count,
            products_removed=len(products_removed),
            version_notes=self._safe(version_notes),
            file_checksum=hashlib.sha1(file_bytes).hexdigest(),
        ).to_dict()
        version["price_sheet_id"] = sheet_id
        version["version_label"] = (
            f"v{len(self.list_price_sheet_versions(sheet_id)) + 1}"
        )
        version["import_status"] = "finalized"
        version["record_count"] = len(current_product_ids)
        version["source_metadata"] = f"file={source_file}"
        version["source_hash"] = version["file_checksum"]
        version["finalized"] = True

        self.state.setdefault("price_list_versions", {})[version_id] = version
        sheet = dict(self.state.get("price_sheets", {}).get(sheet_id) or {})
        sheet["active_version"] = version_id
        sheet["updated_at"] = now_text
        self.state.setdefault("price_sheets", {})[sheet_id] = sheet
        return {
            "version": dict(version),
            "products_added": products_added,
            "products_removed": products_removed,
        }

    def add_project_only_product(
        self,
        *,
        project_id: str,
        manufacturer: str,
        model: str,
        description: str,
        vendor: str,
        vendor_type: str,
        cost: float,
        source: str,
    ) -> dict[str, Any]:
        project_key = self._safe(project_id)
        product_uuid = str(
            uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"project-only::{project_key}::{manufacturer}::{model}",
            )
        )
        entry = {
            "atlas_product_uuid": product_uuid,
            "manufacturer": self._safe(manufacturer, "Unknown"),
            "manufacturer_sku": self._safe(model, "Unknown"),
            "canonical_sku": self._safe(model, "Unknown"),
            "alternate_skus": [],
            "description": self._safe(description, ""),
            "product_family": "Project Specific",
            "category": "other",
            "discipline": "general",
            "lifecycle_status": ProductLifecycleStatus.PENDING_VERIFICATION.value,
            "active": True,
            "product_image": "",
            "datasheet": "",
            "commercial": ProductCommercialMetadata(
                preferred_cost=float(cost),
                preferred_vendor=self._safe(vendor, "Unknown Vendor"),
                currency="USD",
            ).to_dict(),
            "engineering": {},
            "future_hooks": {},
            "replacement_product_uuid": None,
            "compatible_products": [],
            "related_accessories": [],
            "project_references": [project_key],
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
            "project_only": True,
            "source": self._safe(source, "manual"),
            "vendor_type": self._safe(vendor_type, "other"),
        }

        project_bucket = self.state.setdefault("project_only_products", {}).setdefault(
            project_key, {}
        )
        project_bucket[product_uuid] = entry
        return dict(entry)

    def promote_project_only_product(
        self,
        *,
        project_id: str,
        atlas_product_uuid: str,
        vendor: str,
        vendor_type: str,
        import_user: str,
    ) -> dict[str, Any]:
        project_bucket = dict(
            self.state.get("project_only_products", {}).get(self._safe(project_id), {})
        )
        product = dict(project_bucket.get(self._safe(atlas_product_uuid), {}))
        if not product:
            raise ValueError("Project-only product not found")

        row = {
            "manufacturer": product.get("manufacturer"),
            "manufacturer_sku": product.get("manufacturer_sku"),
            "canonical_sku": product.get("canonical_sku"),
            "alternate_skus": list(product.get("alternate_skus") or []),
            "description": product.get("description"),
            "product_family": product.get("product_family"),
            "category": product.get("category"),
            "discipline": product.get("discipline"),
            "lifecycle_status": product.get("lifecycle_status"),
            "preferred_cost": dict(product.get("commercial") or {}).get(
                "preferred_cost"
            ),
            "preferred_vendor": self._safe(vendor),
            "vendor": self._safe(vendor),
            "vendor_type": self._safe(vendor_type),
            "vendor_sku": product.get("canonical_sku"),
            "availability": "in_stock",
            "lead_time": dict(product.get("commercial") or {}).get("lead_time"),
            "comments": "Promoted from project-only quick add",
        }

        import_result = self.import_price_list_version(
            manufacturer=self._safe(product.get("manufacturer"), "Unknown"),
            vendor=self._safe(vendor, "Unknown Vendor"),
            source_file="project_only_promotion",
            file_bytes=json.dumps(row, sort_keys=True).encode("utf-8"),
            import_user=self._safe(import_user, "atlas"),
            rows=[row],
            version_notes="Project-only product promotion",
        )
        return {
            "promoted_product_uuid": atlas_product_uuid,
            "import_result": import_result,
        }

    def product_rows(
        self, *, include_project_only: bool = True
    ) -> list[dict[str, Any]]:
        rows = list(self.state.get("products", {}).values())
        if include_project_only:
            for project_rows in self.state.get("project_only_products", {}).values():
                rows.extend(list(project_rows.values()))

        rows.sort(
            key=lambda item: (
                self._safe(item.get("manufacturer"), "").lower(),
                self._safe(item.get("canonical_sku"), "").lower(),
            )
        )

        enriched: list[dict[str, Any]] = []
        canonical_fields = set(CanonicalProduct.__dataclass_fields__)
        for row in rows:
            source_row = dict(row)
            product = CanonicalProduct(
                **{
                    key: value
                    for key, value in source_row.items()
                    if key in canonical_fields
                }
            )
            enriched.append(
                {
                    **product.to_dict(),
                    "manufacturer_id": self._safe(
                        source_row.get("manufacturer_id"), ""
                    ),
                    "manufacturer_part_number": self._safe(
                        source_row.get("manufacturer_part_number"),
                        product.manufacturer_sku,
                    ),
                    "product_name": self._safe(
                        source_row.get("product_name"), product.canonical_sku
                    ),
                    "product_description": self._safe(
                        source_row.get("product_description"), product.description
                    ),
                    "discontinued": bool(source_row.get("discontinued", False)),
                    "notes": self._safe(source_row.get("notes"), ""),
                    "commercial_health": self._commercial_health(product),
                    "product_intelligence": self._product_intelligence(product),
                    "confidence": self._confidence(product),
                    "import_history": self._import_history_for_product(
                        product.atlas_product_uuid
                    ),
                    "price_history": self._price_history_for_product(
                        product.atlas_product_uuid
                    ),
                }
            )
        return enriched

    def dashboard_summary(self) -> dict[str, Any]:
        rows = self.product_rows(include_project_only=True)
        knowledge_summary = self.knowledge_entity_summary()
        active_products = sum(1 for item in rows if bool(item.get("active", True)))
        missing_pricing = sum(
            1
            for item in rows
            if bool(dict(item.get("commercial_health") or {}).get("missing_pricing"))
        )
        stale_pricing = sum(
            1
            for item in rows
            if dict(item.get("commercial_health") or {}).get("pricing_freshness")
            == "stale"
        )
        missing_preferred_vendor = sum(
            1
            for item in rows
            if not bool(
                dict(item.get("commercial_health") or {}).get("preferred_vendor_exists")
            )
        )
        recent_price_changes = sum(
            1
            for item in rows
            if list(item.get("price_history") or [])
            and abs(
                float(
                    (list(item.get("price_history") or [])[-1] or {}).get(
                        "dollar_difference"
                    )
                    or 0.0
                )
            )
            > 0
        )
        new_products = sum(
            1
            for item in rows
            if self._safe(item.get("lifecycle_status"), "")
            == ProductLifecycleStatus.NEW.value
        )
        end_of_life = sum(
            1
            for item in rows
            if self._safe(item.get("lifecycle_status"), "")
            in {
                ProductLifecycleStatus.END_OF_LIFE.value,
                ProductLifecycleStatus.OBSOLETE.value,
                ProductLifecycleStatus.DISCONTINUED.value,
            }
        )
        replacement_candidates = sum(
            1 for item in rows if self._safe(item.get("replacement_product_uuid"), "")
        )
        average_confidence = (
            round(
                sum(
                    float(
                        dict(item.get("confidence") or {}).get("overall_confidence", 0)
                    )
                    for item in rows
                )
                / len(rows),
                4,
            )
            if rows
            else 0.0
        )

        return {
            "active_products": active_products,
            "missing_pricing": missing_pricing,
            "stale_pricing": stale_pricing,
            "missing_preferred_vendor": missing_preferred_vendor,
            "recent_price_changes": recent_price_changes,
            "new_products": new_products,
            "end_of_life_products": end_of_life,
            "replacement_candidates": replacement_candidates,
            "average_confidence": average_confidence,
            "knowledge_entities": int(knowledge_summary.get("total_entities", 0)),
            "knowledge_relationships": int(
                knowledge_summary.get("total_relationships", 0)
            ),
            "knowledge_entity_summary": knowledge_summary,
        }

    def _upsert_product_from_row(
        self,
        *,
        product_key: str,
        row: dict[str, Any],
        version_id: str,
        import_date: str,
    ) -> None:
        products = self.state.setdefault("products", {})
        current = dict(products.get(product_key) or {})
        product_uuid = self._safe(current.get("atlas_product_uuid"), "") or str(
            uuid.uuid5(uuid.NAMESPACE_DNS, product_key)
        )

        alternate_skus = sorted(
            {
                self._safe(item)
                for item in list(current.get("alternate_skus") or [])
                + list(row.get("alternate_skus") or [])
                if self._safe(item)
            }
        )

        commercial_payload = {
            **dict(current.get("commercial") or {}),
            **dict(row.get("commercial") or {}),
            "preferred_vendor": self._safe(
                row.get("preferred_vendor"),
                self._safe(
                    dict(current.get("commercial") or {}).get("preferred_vendor"), ""
                ),
            ),
            "currency": self._safe(
                row.get("currency"),
                self._safe(
                    dict(current.get("commercial") or {}).get("currency"), "USD"
                ),
            ),
            "lead_time": self._safe(
                row.get("lead_time"),
                self._safe(dict(current.get("commercial") or {}).get("lead_time"), ""),
            ),
            "minimum_order_quantity": self._int_or_none(
                row.get("minimum_order_quantity")
                if row.get("minimum_order_quantity") is not None
                else dict(current.get("commercial") or {}).get("minimum_order_quantity")
            ),
            "package_quantity": self._int_or_none(
                row.get("package_quantity")
                if row.get("package_quantity") is not None
                else dict(current.get("commercial") or {}).get("package_quantity")
            ),
        }

        product = CanonicalProduct(
            atlas_product_uuid=product_uuid,
            manufacturer=self._safe(row.get("manufacturer"), "Unknown"),
            manufacturer_sku=self._safe(row.get("manufacturer_sku"), "UNKNOWN"),
            canonical_sku=self._safe(
                row.get("canonical_sku"),
                self._safe(row.get("manufacturer_sku"), "UNKNOWN"),
            ),
            alternate_skus=alternate_skus,
            description=self._safe(
                row.get("description"),
                self._safe(current.get("description"), ""),
            ),
            product_family=self._safe(
                row.get("product_family"),
                self._safe(current.get("product_family"), "General"),
            ),
            category=self._safe(
                row.get("category"),
                self._safe(current.get("category"), "other"),
            ),
            discipline=self._safe(
                row.get("discipline"),
                self._safe(current.get("discipline"), "general"),
            ),
            lifecycle_status=self._lifecycle(
                row.get("lifecycle_status")
                or current.get("lifecycle_status")
                or ProductLifecycleStatus.PENDING_VERIFICATION.value
            ),
            active=bool(row.get("active", current.get("active", True))),
            product_image=self._safe(
                row.get("product_image"),
                self._safe(current.get("product_image"), ""),
            ),
            datasheet=self._safe(
                row.get("datasheet"),
                self._safe(current.get("datasheet"), ""),
            ),
            commercial=ProductCommercialMetadata(**commercial_payload),
            engineering=ProductEngineeringMetadata(
                **dict(current.get("engineering") or {})
            ),
            future_hooks=ProductFutureHooks(**dict(current.get("future_hooks") or {})),
            replacement_product_uuid=self._safe(
                row.get("replacement_product_uuid"),
                self._safe(current.get("replacement_product_uuid"), ""),
            )
            or None,
            compatible_products=sorted(
                {
                    self._safe(item)
                    for item in list(current.get("compatible_products") or [])
                    + list(row.get("compatible_products") or [])
                    if self._safe(item)
                }
            ),
            related_accessories=sorted(
                {
                    self._safe(item)
                    for item in list(current.get("related_accessories") or [])
                    + list(row.get("related_accessories") or [])
                    if self._safe(item)
                }
            ),
            project_references=sorted(
                {
                    self._safe(item)
                    for item in list(current.get("project_references") or [])
                    + list(row.get("project_references") or [])
                    if self._safe(item)
                }
            ),
            created_at=self._safe(current.get("created_at"), import_date),
            updated_at=import_date,
        )
        products[product_key] = product.to_dict()

        self._upsert_vendor_offering(
            product_uuid=product_uuid,
            row=row,
            version_id=version_id,
            import_date=import_date,
        )
        self._append_price_history(
            product_uuid=product_uuid,
            vendor=self._safe(row.get("vendor"), ""),
            version_id=version_id,
            effective_date=self._safe(row.get("effective_date"), import_date[:10]),
            new_cost=self._float_or_none(row.get("preferred_cost")),
        )

    def _upsert_vendor_offering(
        self,
        *,
        product_uuid: str,
        row: dict[str, Any],
        version_id: str,
        import_date: str,
    ) -> None:
        offerings = self.state.setdefault("vendor_offerings", {})
        vendor = self._safe(row.get("vendor"), "Unknown Vendor")
        vendor_sku = self._safe(
            row.get("vendor_sku"),
            self._safe(row.get("canonical_sku"), "UNKNOWN"),
        )
        offering_id = self._vendor_offering_id(product_uuid, vendor, vendor_sku)
        record = VendorOfferingRecord(
            vendor_offering_id=offering_id,
            atlas_product_uuid=product_uuid,
            vendor=vendor,
            vendor_sku=vendor_sku,
            vendor_type=self._safe(row.get("vendor_type"), "other"),
            vendor_cost=self._float_or_none(row.get("preferred_cost")),
            availability=self._safe(row.get("availability"), "unknown"),
            lead_time=self._safe(row.get("lead_time"), ""),
            price_version=version_id,
            preferred_vendor=bool(row.get("preferred_vendor", False)),
            contract_pricing=bool(row.get("contract_pricing", False)),
            freight_notes=self._safe(row.get("freight_notes"), ""),
            date_verified=self._safe(row.get("date_verified"), import_date),
            comments=self._safe(row.get("comments"), ""),
        )
        payload = record.to_dict()
        payload["vendor_id"] = self._safe(vendor).lower().replace(" ", "-")
        payload["normalized_vendor_sku"] = self.normalize_vendor_sku(vendor_sku)
        payload["purchasing_channel"] = self._safe(
            row.get("purchasing_channel"), "other"
        )
        payload["direct_from_manufacturer"] = bool(
            row.get("direct_from_manufacturer", False)
        )
        payload["authorization_status"] = self._safe(
            row.get("authorization_status"), "unknown"
        )
        payload["minimum_order_quantity"] = self._int_or_none(
            row.get("minimum_order_quantity")
        )
        payload["order_multiple"] = self._int_or_none(row.get("order_multiple"))
        payload["unit_of_measure"] = self._safe(row.get("unit_of_measure"), "ea")
        payload["pack_quantity"] = self._int_or_none(row.get("package_quantity"))
        payload["lead_time_notes"] = self._safe(row.get("lead_time"), "")
        payload["pricing_available"] = (
            self._float_or_none(row.get("preferred_cost")) is not None
        )
        payload["active"] = bool(row.get("active", True))
        payload["created_at"] = self._safe(payload.get("created_at"), import_date)
        payload["updated_at"] = import_date
        offerings[offering_id] = payload

    def _append_price_history(
        self,
        *,
        product_uuid: str,
        vendor: str,
        version_id: str,
        effective_date: str,
        new_cost: float | None,
    ) -> None:
        history_map = self.state.setdefault("product_price_history", {})
        rows = list(history_map.get(product_uuid) or [])
        previous_cost = None
        if rows:
            previous_cost = self._float_or_none(rows[-1].get("new_cost"))

        dollar_diff = None
        pct_change = None
        if previous_cost is not None and new_cost is not None:
            dollar_diff = round(new_cost - previous_cost, 4)
            if previous_cost != 0:
                pct_change = round((dollar_diff / previous_cost) * 100, 4)

        record = ProductPriceHistoryRecord(
            atlas_product_uuid=product_uuid,
            effective_date=effective_date,
            previous_cost=previous_cost,
            new_cost=new_cost,
            dollar_difference=dollar_diff,
            percentage_change=pct_change,
            vendor=vendor,
            source_version=version_id,
        ).to_dict()
        rows.append(record)
        history_map[product_uuid] = rows

    def _commercial_health(self, product: CanonicalProduct) -> dict[str, Any]:
        offerings = [
            item
            for item in self.state.get("vendor_offerings", {}).values()
            if self._safe(item.get("atlas_product_uuid"), "")
            == product.atlas_product_uuid
        ]
        latest_verified = ""
        days_since_verification = None
        if offerings:
            latest_verified = max(
                [self._safe(item.get("date_verified"), "") for item in offerings],
                default="",
            )
            latest_date = self._date_from_text(latest_verified)
            if latest_date is not None:
                days_since_verification = max((self._as_of - latest_date).days, 0)

        freshness = "fresh"
        if days_since_verification is None:
            freshness = "missing"
        elif days_since_verification > 365:
            freshness = "stale"
        elif days_since_verification > 180:
            freshness = "review_recommended"

        has_cost = any(
            self._float_or_none(item.get("vendor_cost")) is not None
            for item in offerings
        )
        preferred_vendor_exists = bool(
            product.commercial.preferred_vendor
            and any(
                self._safe(item.get("vendor"), "").lower()
                == product.commercial.preferred_vendor.lower()
                for item in offerings
            )
        )

        return {
            "pricing_freshness": freshness,
            "days_since_verification": days_since_verification,
            "missing_pricing": not has_cost,
            "preferred_vendor_exists": preferred_vendor_exists,
            "has_cost": has_cost,
            "estimate_ready": bool(
                has_cost
                and preferred_vendor_exists
                and product.active
                and product.lifecycle_status
                in {
                    ProductLifecycleStatus.ACTIVE,
                    ProductLifecycleStatus.NEW,
                    ProductLifecycleStatus.PENDING_VERIFICATION,
                }
            ),
        }

    def _product_intelligence(self, product: CanonicalProduct) -> dict[str, Any]:
        offerings = [
            item
            for item in self.state.get("vendor_offerings", {}).values()
            if self._safe(item.get("atlas_product_uuid"), "")
            == product.atlas_product_uuid
        ]
        costs: list[float] = []
        for item in offerings:
            cost_value = self._float_or_none(item.get("vendor_cost"))
            if cost_value is not None:
                costs.append(cost_value)
        margins: list[float] = []

        history = self._price_history_for_product(product.atlas_product_uuid)
        trend = "flat"
        if len(history) >= 2:
            first = self._float_or_none(history[0].get("new_cost"))
            last = self._float_or_none(history[-1].get("new_cost"))
            if first is not None and last is not None:
                if last > first:
                    trend = "up"
                elif last < first:
                    trend = "down"

        return {
            "lowest_cost": min(costs) if costs else None,
            "highest_cost": max(costs) if costs else None,
            "average_cost": round(sum(costs) / len(costs), 4) if costs else None,
            "vendor_count": len(offerings),
            "margin_range": (
                {
                    "minimum": min(margins),
                    "maximum": max(margins),
                }
                if margins
                else None
            ),
            "cost_trend": trend,
            "replacement_product": product.replacement_product_uuid,
            "compatible_products": list(product.compatible_products),
            "related_accessories": list(product.related_accessories),
        }

    def _confidence(self, product: CanonicalProduct) -> dict[str, Any]:
        health = self._commercial_health(product)

        engineering_conf = 1.0
        if not product.engineering.connectors:
            engineering_conf -= 0.1
        if not product.engineering.warranty:
            engineering_conf -= 0.08
        if not product.engineering.power:
            engineering_conf -= 0.08
        engineering_conf = max(0.0, min(1.0, round(engineering_conf, 4)))

        commercial_conf = 1.0
        if health["missing_pricing"]:
            commercial_conf -= 0.35
        if not health["preferred_vendor_exists"]:
            commercial_conf -= 0.2
        if health["pricing_freshness"] == "review_recommended":
            commercial_conf -= 0.15
        if health["pricing_freshness"] == "stale":
            commercial_conf -= 0.35
        commercial_conf = max(0.0, min(1.0, round(commercial_conf, 4)))

        lifecycle_conf = 1.0
        if product.lifecycle_status is ProductLifecycleStatus.PENDING_VERIFICATION:
            lifecycle_conf -= 0.3
        if product.lifecycle_status in {
            ProductLifecycleStatus.DISCONTINUED,
            ProductLifecycleStatus.END_OF_LIFE,
            ProductLifecycleStatus.OBSOLETE,
        }:
            lifecycle_conf -= 0.5
        lifecycle_conf = max(0.0, min(1.0, round(lifecycle_conf, 4)))

        overall = round((engineering_conf + commercial_conf + lifecycle_conf) / 3, 4)

        return {
            "engineering_confidence": engineering_conf,
            "commercial_confidence": commercial_conf,
            "lifecycle_confidence": lifecycle_conf,
            "overall_confidence": overall,
        }

    def _price_history_for_product(self, product_uuid: str) -> list[dict[str, Any]]:
        return list(self.state.get("product_price_history", {}).get(product_uuid) or [])

    def _import_history_for_product(self, product_uuid: str) -> list[dict[str, Any]]:
        offerings = [
            item
            for item in self.state.get("vendor_offerings", {}).values()
            if self._safe(item.get("atlas_product_uuid"), "") == product_uuid
        ]
        version_ids = sorted(
            {self._safe(item.get("price_version"), "") for item in offerings}
        )
        return [
            dict(self.state.get("price_list_versions", {}).get(version_id) or {})
            for version_id in version_ids
            if version_id
        ]

    @staticmethod
    def normalize_name(value: Any) -> str:
        text = " ".join(str(value or "").strip().upper().split())
        return text

    @staticmethod
    def normalize_part_number(value: Any) -> str:
        text = str(value or "").strip().upper()
        text = " ".join(text.split())
        # Conservative normalization: trim, uppercase, collapse repeats, and normalize safe separators.
        text = text.replace("_", "-")
        while "--" in text:
            text = text.replace("--", "-")
        return text

    @staticmethod
    def normalize_vendor_sku(value: Any) -> str:
        return CommercialProductService.normalize_part_number(value)

    def find_product_by_identity(
        self,
        *,
        manufacturer: str,
        normalized_part_number: str,
    ) -> dict[str, Any] | None:
        for item in self.state.get("products", {}).values():
            if self._safe(item.get("manufacturer"), "").upper() == self._safe(
                manufacturer, ""
            ).upper() and self.normalize_part_number(
                item.get(
                    "normalized_manufacturer_part_number",
                    item.get(
                        "manufacturer_part_number", item.get("manufacturer_sku", "")
                    ),
                )
            ) == self.normalize_part_number(
                normalized_part_number
            ):
                return dict(item)
        return None

    def _set_product_lifecycle(
        self,
        atlas_product_uuid: str,
        *,
        lifecycle_status: str,
        active: bool,
    ) -> dict[str, Any]:
        product = self.get_product(atlas_product_uuid)
        if product is None:
            raise ValueError("Product not found")
        product["lifecycle_status"] = self._safe(lifecycle_status)
        product["discontinued"] = self._safe(lifecycle_status) in {
            ProductLifecycleStatus.DISCONTINUED.value,
            ProductLifecycleStatus.END_OF_LIFE.value,
            ProductLifecycleStatus.OBSOLETE.value,
        }
        product["active"] = bool(active)
        product["updated_at"] = self._now_iso()
        self._persist_product(product)
        return dict(product)

    def _persist_product(self, product: dict[str, Any]) -> None:
        product_key = self._product_key(
            manufacturer=self._safe(product.get("manufacturer"), ""),
            canonical_sku=self._safe(product.get("canonical_sku"), ""),
            manufacturer_sku=self._safe(product.get("manufacturer_sku"), ""),
        )
        self.state.setdefault("products", {})[product_key] = dict(product)
        self._upsert_knowledge_entity(
            entity_id=f"product:{self._safe(product.get('atlas_product_uuid'), '')}",
            entity_type="product",
            canonical_name=self._safe(product.get("canonical_sku"), "Unknown Product"),
            display_name=self._safe(
                product.get("product_name"),
                self._safe(product.get("canonical_sku"), "Unknown Product"),
            ),
            aliases=[
                self._safe(product.get("manufacturer_part_number"), ""),
                self._safe(product.get("manufacturer_sku"), ""),
            ],
            notes=self._safe(product.get("notes"), ""),
            active=bool(product.get("active", True)),
            attributes={
                "atlas_product_uuid": product.get("atlas_product_uuid"),
                "manufacturer_id": product.get("manufacturer_id"),
                "manufacturer": product.get("manufacturer"),
                "manufacturer_part_number": product.get("manufacturer_part_number"),
                "normalized_manufacturer_part_number": product.get(
                    "normalized_manufacturer_part_number"
                ),
                "category": product.get("category"),
                "lifecycle_status": product.get("lifecycle_status"),
                "replacement_product_uuid": product.get("replacement_product_uuid"),
            },
            fail_on_duplicate=False,
        )

    def _replacement_cycle_exists(self, product_id: str, replacement_id: str) -> bool:
        next_id = self._safe(replacement_id)
        visited: set[str] = set()
        while next_id:
            if next_id in visited:
                return True
            visited.add(next_id)
            if next_id == self._safe(product_id):
                return True
            node = self.get_product(next_id)
            if node is None:
                return False
            next_id = self._safe(node.get("replacement_product_uuid"), "")
        return False

    @staticmethod
    def _validate_purchasing_channel(value: Any) -> None:
        channel = str(value or "").strip()
        if channel not in ALLOWED_PURCHASING_CHANNELS:
            raise ValueError("Invalid purchasing channel")

    @staticmethod
    def _validate_import_status(value: Any) -> None:
        status = str(value or "").strip()
        if status not in ALLOWED_IMPORT_STATUSES:
            raise ValueError("Invalid import_status")

    @staticmethod
    def _validate_price_record_resolution_status(value: Any) -> None:
        status = str(value or "").strip()
        if status not in ALLOWED_PRICE_RECORD_RESOLUTION:
            raise ValueError("Invalid resolution_status")

    @staticmethod
    def _validate_currency(value: Any) -> None:
        code = str(value or "").strip().upper()
        if code not in ALLOWED_CURRENCIES:
            raise ValueError("Invalid currency code")

    @staticmethod
    def _validate_effective_expiration(
        effective_date: str, expiration_date: str
    ) -> None:
        if not effective_date or not expiration_date:
            return
        try:
            eff = datetime.fromisoformat(str(effective_date).replace("Z", "+00:00"))
            exp = datetime.fromisoformat(str(expiration_date).replace("Z", "+00:00"))
        except ValueError:
            return
        if exp < eff:
            raise ValueError("expiration_date cannot precede effective_date")

    @staticmethod
    def _default_purchasing_channel(vendor_type: str) -> str:
        value = str(vendor_type or "").strip().lower()
        if value in {"manufacturer_direct", "direct", "oem_direct"}:
            return "direct_from_manufacturer"
        if value in {
            "authorized_distributor",
            "regional_distributor",
            "distributor",
            "buying_group",
        }:
            return "distributor"
        if value in {"dealer", "dealer_reseller", "reseller", "integrator"}:
            return "dealer_reseller"
        return "other"

    def _normalized_state(self, state: dict[str, Any]) -> dict[str, Any]:
        normalized = self.empty_state()
        for key in normalized:
            candidate = state.get(key)
            if isinstance(candidate, dict):
                normalized[key] = dict(candidate)
            if key == "knowledge_audit_log" and isinstance(candidate, list):
                normalized[key] = list(candidate)
        return normalized

    def _upsert_knowledge_entity(
        self,
        *,
        entity_id: str,
        entity_type: str,
        canonical_name: str,
        display_name: str | None = None,
        aliases: list[str] | None = None,
        notes: str = "",
        active: bool = True,
        attributes: dict[str, Any] | None = None,
        fail_on_duplicate: bool,
    ) -> dict[str, Any]:
        normalized_id = self._safe(entity_id)
        normalized_type = self._safe(entity_type).lower()
        canonical = self._safe(canonical_name)
        if not normalized_id:
            raise ValueError("entity_id cannot be blank")
        if not normalized_type:
            raise ValueError("entity_type cannot be blank")
        if not canonical:
            raise ValueError("canonical_name cannot be blank")

        normalized_name = self.normalize_name(canonical)
        duplicates = [
            item
            for item in self.detect_duplicate_knowledge_entities(
                entity_type=normalized_type,
                canonical_name=canonical,
                normalized_name=normalized_name,
            )
            if self._safe(item.get("entity_id"), "") != normalized_id
        ]
        if duplicates and fail_on_duplicate:
            raise ValueError(
                "Duplicate knowledge entity canonical/normalized name detected"
            )

        now_text = self._now_iso()
        current = dict(
            self.state.get("knowledge_entities", {}).get(normalized_id) or {}
        )
        record = {
            "entity_id": normalized_id,
            "entity_type": normalized_type,
            "canonical_name": canonical,
            "display_name": self._safe(display_name, canonical),
            "normalized_name": normalized_name,
            "aliases": [
                self._safe(item) for item in list(aliases or []) if self._safe(item)
            ],
            "active": bool(active),
            "notes": self._safe(notes),
            "attributes": dict(attributes or {}),
            "created_at": self._safe(current.get("created_at"), now_text),
            "updated_at": now_text,
        }
        self.state.setdefault("knowledge_entities", {})[normalized_id] = record
        self._append_knowledge_audit(
            event_type="knowledge_entity_upserted",
            entity_id=normalized_id,
            payload={
                "entity_type": normalized_type,
                "canonical_name": canonical,
            },
        )
        return dict(record)

    def _set_knowledge_entity_active(self, *, entity_id: str, active: bool) -> None:
        normalized_id = self._safe(entity_id)
        record = dict(self.state.get("knowledge_entities", {}).get(normalized_id) or {})
        if not record:
            return
        record["active"] = bool(active)
        record["updated_at"] = self._now_iso()
        self.state.setdefault("knowledge_entities", {})[normalized_id] = record
        self._append_knowledge_audit(
            event_type="knowledge_entity_activation_changed",
            entity_id=normalized_id,
            payload={"active": bool(active)},
        )

    def _knowledge_relationship_id(
        self,
        *,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
    ) -> str:
        token = "|".join(
            [
                self._safe(source_entity_id),
                self._safe(target_entity_id),
                self._safe(relationship_type).lower(),
            ]
        )
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:16]
        return f"rel:{digest}"

    def _append_knowledge_audit(
        self,
        *,
        event_type: str,
        entity_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        now_text = self._now_iso()
        token = "|".join(
            [
                now_text,
                self._safe(event_type),
                self._safe(entity_id),
                json.dumps(dict(payload or {}), sort_keys=True),
            ]
        )
        event_id = f"audit:{hashlib.sha1(token.encode('utf-8')).hexdigest()[:16]}"
        entry = {
            "event_id": event_id,
            "event_type": self._safe(event_type),
            "entity_id": self._safe(entity_id),
            "timestamp": now_text,
            "payload": dict(payload or {}),
        }
        rows = list(self.state.get("knowledge_audit_log") or [])
        rows.append(entry)
        self.state["knowledge_audit_log"] = rows[-1000:]

    def _normalize_knowledge_import_row(
        self,
        *,
        entity_type: str,
        row: dict[str, Any],
    ) -> dict[str, Any]:
        aliases = [
            self._safe(item)
            for item in re.split(r"[;,|]", self._safe(row.get("aliases"), ""))
            if self._safe(item)
        ]
        active_text = self._safe(row.get("active"), "true").strip().lower()
        active = active_text not in {"false", "0", "no", "n", "off"}
        if entity_type == "customer":
            return {
                "customer_id": self._safe(row.get("customer_id"), ""),
                "canonical_name": self._safe(row.get("canonical_name"), ""),
                "display_name": self._safe(row.get("display_name"), ""),
                "aliases": aliases,
                "notes": self._safe(row.get("notes"), ""),
                "active": active,
            }
        if entity_type == "service":
            return {
                "service_id": self._safe(row.get("service_id"), ""),
                "canonical_name": self._safe(row.get("canonical_name"), ""),
                "display_name": self._safe(row.get("display_name"), ""),
                "aliases": aliases,
                "notes": self._safe(row.get("notes"), ""),
                "active": active,
            }
        if entity_type == "contact":
            return {
                "contact_id": self._safe(row.get("contact_id"), ""),
                "canonical_name": self._safe(row.get("canonical_name"), ""),
                "display_name": self._safe(row.get("display_name"), ""),
                "email": self._safe(row.get("email"), ""),
                "phone": self._safe(row.get("phone"), ""),
                "title": self._safe(row.get("title"), ""),
                "organization": self._safe(row.get("organization"), ""),
                "external_identifier": self._safe(
                    row.get("external_identifier"),
                    "",
                ),
                "aliases": aliases,
                "notes": self._safe(row.get("notes"), ""),
                "active": active,
            }
        if entity_type == "location":
            return {
                "location_id": self._safe(row.get("location_id"), ""),
                "canonical_name": self._safe(row.get("canonical_name"), ""),
                "display_name": self._safe(row.get("display_name"), ""),
                "address_line1": self._safe(row.get("address_line1"), ""),
                "address_line2": self._safe(row.get("address_line2"), ""),
                "city": self._safe(row.get("city"), ""),
                "state": self._safe(row.get("state"), ""),
                "postal_code": self._safe(row.get("postal_code"), ""),
                "country": self._safe(row.get("country"), ""),
                "external_identifier": self._safe(
                    row.get("external_identifier"),
                    "",
                ),
                "aliases": aliases,
                "notes": self._safe(row.get("notes"), ""),
                "active": active,
            }
        if entity_type == "project":
            return {
                "project_id": self._safe(row.get("project_id"), ""),
                "canonical_name": self._safe(row.get("canonical_name"), ""),
                "display_name": self._safe(row.get("display_name"), ""),
                "customer": self._safe(row.get("customer"), ""),
                "location": self._safe(row.get("location"), ""),
                "client_project_number": self._safe(
                    row.get("client_project_number"),
                    "",
                ),
                "internal_project_number": self._safe(
                    row.get("internal_project_number"),
                    "",
                ),
                "status": self._safe(row.get("status"), ""),
                "external_identifier": self._safe(
                    row.get("external_identifier"),
                    "",
                ),
                "aliases": aliases,
                "notes": self._safe(row.get("notes"), ""),
                "active": active,
            }
        if entity_type == "manufacturer":
            return {
                "manufacturer_id": self._safe(row.get("manufacturer_id"), ""),
                "canonical_name": self._safe(row.get("canonical_name"), ""),
                "display_name": self._safe(row.get("display_name"), ""),
                "manufacturer_code": self._safe(row.get("manufacturer_code"), ""),
                "website": self._safe(row.get("website"), ""),
                "aliases": aliases,
                "notes": self._safe(row.get("notes"), ""),
                "active": active,
            }
        if entity_type == "vendor":
            return {
                "vendor_id": self._safe(row.get("vendor_id"), ""),
                "canonical_name": self._safe(row.get("canonical_name"), ""),
                "display_name": self._safe(row.get("display_name"), ""),
                "vendor_code": self._safe(row.get("vendor_code"), ""),
                "website": self._safe(row.get("website"), ""),
                "aliases": aliases,
                "notes": self._safe(row.get("notes"), ""),
                "active": active,
            }
        return {
            "manufacturer_id": self._safe(row.get("manufacturer_id"), ""),
            "manufacturer_part_number": self._safe(
                row.get("manufacturer_part_number"),
                "",
            ),
            "product_name": self._safe(row.get("product_name"), ""),
            "product_description": self._safe(row.get("product_description"), ""),
            "category": self._safe(row.get("category"), "other"),
            "lifecycle_status": self._safe(
                row.get("lifecycle_status"),
                ProductLifecycleStatus.PENDING_VERIFICATION.value,
            ),
            "notes": self._safe(row.get("notes"), ""),
            "active": active,
        }

    def _knowledge_import_row_key(
        self,
        *,
        entity_type: str,
        normalized_row: dict[str, Any],
    ) -> str:
        if entity_type == "customer":
            return self._safe(normalized_row.get("customer_id"), "")
        if entity_type == "service":
            return self._safe(normalized_row.get("service_id"), "")
        if entity_type == "contact":
            return self._safe(normalized_row.get("contact_id"), "")
        if entity_type == "location":
            return self._safe(normalized_row.get("location_id"), "")
        if entity_type == "project":
            return self._safe(normalized_row.get("project_id"), "")
        if entity_type == "manufacturer":
            return self._safe(normalized_row.get("manufacturer_id"), "")
        if entity_type == "vendor":
            return self._safe(normalized_row.get("vendor_id"), "")
        return "|".join(
            [
                self._safe(normalized_row.get("manufacturer_id"), ""),
                self.normalize_part_number(
                    self._safe(normalized_row.get("manufacturer_part_number"), "")
                ),
            ]
        )

    def _validate_knowledge_import_row(
        self,
        *,
        entity_type: str,
        normalized_row: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []
        if entity_type == "customer":
            if not self._safe(normalized_row.get("customer_id"), ""):
                errors.append("customer_id is required")
            if not self._safe(normalized_row.get("canonical_name"), ""):
                errors.append("canonical_name is required")
            return errors
        if entity_type == "service":
            if not self._safe(normalized_row.get("service_id"), ""):
                errors.append("service_id is required")
            if not self._safe(normalized_row.get("canonical_name"), ""):
                errors.append("canonical_name is required")
            return errors
        if entity_type == "contact":
            if not self._safe(normalized_row.get("contact_id"), ""):
                errors.append("contact_id is required")
            if not self._safe(normalized_row.get("canonical_name"), ""):
                errors.append("canonical_name is required")
            return errors
        if entity_type == "location":
            if not self._safe(normalized_row.get("location_id"), ""):
                errors.append("location_id is required")
            if not self._safe(normalized_row.get("canonical_name"), ""):
                errors.append("canonical_name is required")
            return errors
        if entity_type == "project":
            if not self._safe(normalized_row.get("project_id"), ""):
                errors.append("project_id is required")
            if not self._safe(normalized_row.get("canonical_name"), ""):
                errors.append("canonical_name is required")
            return errors
        if entity_type == "manufacturer":
            if not self._safe(normalized_row.get("manufacturer_id"), ""):
                errors.append("manufacturer_id is required")
            if not self._safe(normalized_row.get("canonical_name"), ""):
                errors.append("canonical_name is required")
            return errors
        if entity_type == "vendor":
            if not self._safe(normalized_row.get("vendor_id"), ""):
                errors.append("vendor_id is required")
            if not self._safe(normalized_row.get("canonical_name"), ""):
                errors.append("canonical_name is required")
            return errors

        manufacturer_id = self._safe(normalized_row.get("manufacturer_id"), "")
        if not manufacturer_id:
            errors.append("manufacturer_id is required")
        if not self.get_manufacturer(manufacturer_id):
            errors.append("manufacturer_id does not exist")
        if not self._safe(normalized_row.get("manufacturer_part_number"), ""):
            errors.append("manufacturer_part_number is required")
        if not self._safe(normalized_row.get("product_name"), ""):
            errors.append("product_name is required")
        return errors

    @staticmethod
    def _file_extension(filename: str) -> str:
        name = str(filename or "").strip().lower()
        if "." not in name:
            return ""
        return "." + name.rsplit(".", 1)[1]

    def _draft_id(
        self,
        *,
        price_sheet_id: str,
        source_filename: str,
        source_hash: str,
        version_label: str,
    ) -> str:
        token = "|".join(
            [
                self._safe(price_sheet_id),
                self._safe(source_filename),
                self._safe(source_hash),
                self._safe(version_label),
                self._now_iso(),
            ]
        )
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:16]
        return f"psd-{digest}"

    def _mapping_profile_id(
        self, profile_name: str, vendor_id: str, price_sheet_id: str
    ) -> str:
        token = "|".join(
            [
                self.normalize_name(profile_name),
                self._safe(vendor_id),
                self._safe(price_sheet_id),
            ]
        )
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:12]
        return f"cmp-{digest}"

    def _parse_csv_rows(self, file_bytes: bytes) -> dict[str, Any]:
        text = file_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        headers = [
            self._safe(item)
            for item in list(reader.fieldnames or [])
            if self._safe(item)
        ]
        rows: list[dict[str, Any]] = []
        for row in reader:
            cleaned = {
                self._safe(key): self._safe(value)
                for key, value in dict(row).items()
                if self._safe(key)
            }
            rows.append(cleaned)
        diagnostics: list[dict[str, Any]] = []
        if not headers:
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.ERROR.value,
                    "code": "missing_headers",
                    "message": "Could not detect CSV headers.",
                    "row_number": None,
                }
            )
        return {
            "rows": rows,
            "headers": headers,
            "worksheets": ["sheet1"],
            "selected_worksheet": "sheet1",
            "header_row_index": 0,
            "diagnostics": diagnostics,
        }

    def _parse_xlsx_rows(
        self,
        *,
        file_bytes: bytes,
        worksheet: str | None,
        header_row_index: int,
    ) -> dict[str, Any]:
        try:
            archive = zipfile.ZipFile(io.BytesIO(file_bytes), "r")
        except zipfile.BadZipFile as exc:
            raise ValueError("Invalid XLSX content") from exc

        workbook_xml = archive.read("xl/workbook.xml")
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        workbook_root = ET.fromstring(workbook_xml)
        sheet_nodes = workbook_root.findall("x:sheets/x:sheet", namespace)
        sheets: list[dict[str, str]] = []
        for node in sheet_nodes:
            name = self._safe(node.attrib.get("name"), "")
            rid = self._safe(
                node.attrib.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                ),
                "",
            )
            if name and rid:
                sheets.append({"name": name, "rid": rid})

        rels_xml = archive.read("xl/_rels/workbook.xml.rels")
        rels_root = ET.fromstring(rels_xml)
        rel_namespace = {
            "r": "http://schemas.openxmlformats.org/package/2006/relationships"
        }
        rel_map = {
            self._safe(node.attrib.get("Id"), ""): self._safe(
                node.attrib.get("Target"), ""
            )
            for node in rels_root.findall("r:Relationship", rel_namespace)
        }

        sheet_names = [item.get("name", "") for item in sheets]
        selected_name = self._safe(worksheet)
        if selected_name and selected_name not in sheet_names:
            raise ValueError("Selected worksheet was not found")
        if not selected_name:
            selected_name = sheet_names[0] if sheet_names else ""
        selected = next(
            (item for item in sheets if item.get("name") == selected_name), None
        )
        if selected is None:
            raise ValueError("Workbook does not contain any worksheets")

        target = self._safe(rel_map.get(self._safe(selected.get("rid"), ""), ""), "")
        if target.startswith("/"):
            sheet_path = target.lstrip("/")
        else:
            sheet_path = f"xl/{target}" if not target.startswith("xl/") else target
        sheet_xml = archive.read(sheet_path)

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for node in shared_root.findall(
                ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
            ):
                shared_strings.append(self._safe(node.text, ""))

        rows = self._extract_xlsx_sheet_rows(
            sheet_xml=sheet_xml,
            shared_strings=shared_strings,
            header_row_index=header_row_index,
        )
        return {
            "rows": list(rows.get("rows") or []),
            "headers": list(rows.get("headers") or []),
            "worksheets": sheet_names,
            "selected_worksheet": selected_name,
            "header_row_index": int(header_row_index),
            "diagnostics": list(rows.get("diagnostics") or []),
        }

    def _extract_xlsx_sheet_rows(
        self,
        *,
        sheet_xml: bytes,
        shared_strings: list[str],
        header_row_index: int,
    ) -> dict[str, Any]:
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        root = ET.fromstring(sheet_xml)
        row_nodes = root.findall("x:sheetData/x:row", namespace)
        grid: list[list[str]] = []
        max_columns = 0
        for row_node in row_nodes:
            row_cells: dict[int, str] = {}
            for cell in row_node.findall("x:c", namespace):
                ref = self._safe(cell.attrib.get("r"), "")
                column_index = self._excel_col_to_index(ref)
                value = self._read_xlsx_cell_value(cell, shared_strings, namespace)
                row_cells[column_index] = value
                if column_index + 1 > max_columns:
                    max_columns = column_index + 1
            row_data = [""] * max_columns
            for index, value in row_cells.items():
                if index >= len(row_data):
                    row_data.extend([""] * ((index + 1) - len(row_data)))
                row_data[index] = value
            grid.append(row_data)

        diagnostics: list[dict[str, Any]] = []
        if not grid:
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.ERROR.value,
                    "code": "empty_sheet",
                    "message": "Worksheet is empty.",
                    "row_number": None,
                }
            )
            return {"headers": [], "rows": [], "diagnostics": diagnostics}

        safe_header_index = max(0, int(header_row_index))
        if safe_header_index >= len(grid):
            safe_header_index = 0
        header_row = grid[safe_header_index]
        headers = [self._safe(item) for item in header_row]
        if not any(headers):
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.ERROR.value,
                    "code": "missing_headers",
                    "message": "Header row is blank.",
                    "row_number": safe_header_index + 1,
                }
            )

        rows: list[dict[str, Any]] = []
        for row_idx in range(safe_header_index + 1, len(grid)):
            row_data = grid[row_idx]
            if not any(self._safe(value) for value in row_data):
                continue
            row_obj: dict[str, Any] = {}
            for col_idx, header in enumerate(headers):
                key = self._safe(header) or f"column_{col_idx + 1}"
                row_obj[key] = self._safe(
                    row_data[col_idx] if col_idx < len(row_data) else ""
                )
            rows.append(row_obj)
        return {
            "headers": [
                item or f"column_{idx + 1}" for idx, item in enumerate(headers)
            ],
            "rows": rows,
            "diagnostics": diagnostics,
        }

    def _read_xlsx_cell_value(
        self,
        cell: ET.Element,
        shared_strings: list[str],
        namespace: dict[str, str],
    ) -> str:
        cell_type = self._safe(cell.attrib.get("t"), "")
        value_node = cell.find("x:v", namespace)
        inline_node = cell.find("x:is/x:t", namespace)
        if inline_node is not None and inline_node.text is not None:
            return self._safe(inline_node.text)
        if value_node is None or value_node.text is None:
            return ""
        raw = self._safe(value_node.text)
        if cell_type == "s":
            index = self._int_or_none(raw)
            if index is None or index < 0 or index >= len(shared_strings):
                return ""
            return self._safe(shared_strings[index])
        return raw

    def _excel_col_to_index(self, cell_ref: str) -> int:
        letters = "".join(ch for ch in self._safe(cell_ref) if ch.isalpha()).upper()
        if not letters:
            return 0
        index = 0
        for ch in letters:
            index = (index * 26) + (ord(ch) - ord("A") + 1)
        return max(0, index - 1)

    def _normalized_mapping(
        self, mapping: dict[str, str], headers: list[str]
    ) -> dict[str, str]:
        header_map = {
            self._safe(item): self._safe(item) for item in headers if self._safe(item)
        }
        normalized: dict[str, str] = {}
        for key, value in dict(mapping or {}).items():
            target = self._safe(key)
            source = self._safe(value)
            if not target or not source:
                continue
            if source not in header_map:
                source_norm = self.normalize_name(source)
                match = next(
                    (
                        header
                        for header in header_map
                        if self.normalize_name(header) == source_norm
                    ),
                    "",
                )
                if not match:
                    continue
                normalized[target] = match
            else:
                normalized[target] = source
        return normalized

    def _extract_mapped(
        self, row: dict[str, Any], mapping: dict[str, str], target_field: str
    ) -> str:
        source_column = self._safe(mapping.get(target_field), "")
        if not source_column:
            return ""
        return self._safe(row.get(source_column), "")

    def _validate_import_preview_rows(
        self,
        *,
        raw_rows: list[dict[str, Any]],
        mapping: dict[str, str],
        sheet: dict[str, Any],
        currency: str,
        effective_date: str,
        expiration_date: str,
    ) -> dict[str, Any]:
        diagnostics: list[dict[str, Any]] = []
        preview_rows: list[dict[str, Any]] = []
        error_count = 0
        warning_count = 0
        unresolved_count = 0

        if "manufacturer_part_number" not in mapping and "vendor_sku" not in mapping:
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.ERROR.value,
                    "code": "missing_identity_mapping",
                    "message": "Mapping must include manufacturer_part_number or vendor_sku.",
                    "row_number": None,
                }
            )
            error_count += 1

        manufacturer_name = self._safe(sheet.get("manufacturer"), "")
        vendor_id = self._safe(sheet.get("vendor_id"), "")

        for index, raw in enumerate(raw_rows, start=1):
            row_errors: list[str] = []
            row_warnings: list[str] = []

            part_number = self._extract_mapped(raw, mapping, "manufacturer_part_number")
            vendor_sku = self._extract_mapped(raw, mapping, "vendor_sku")
            description = self._extract_mapped(raw, mapping, "description")
            unit_cost = self._float_or_none(
                self._extract_mapped(raw, mapping, "unit_cost")
            )
            list_price = self._float_or_none(
                self._extract_mapped(raw, mapping, "list_price")
            )
            raw_unit_cost = self._extract_mapped(raw, mapping, "unit_cost")
            raw_list_price = self._extract_mapped(raw, mapping, "list_price")
            row_currency = self._extract_mapped(raw, mapping, "currency") or currency
            uom = self._extract_mapped(raw, mapping, "unit_of_measure") or "ea"
            pack_qty = self._int_or_none(
                self._extract_mapped(raw, mapping, "pack_quantity")
            )
            moq = self._int_or_none(
                self._extract_mapped(raw, mapping, "minimum_order_quantity")
            )
            effective_override = self._extract_mapped(
                raw, mapping, "effective_date_override"
            )
            source_category = self._extract_mapped(raw, mapping, "source_category")
            notes = self._extract_mapped(raw, mapping, "notes")

            if not self.normalize_part_number(
                part_number
            ) and not self.normalize_vendor_sku(vendor_sku):
                row_errors.append(
                    "Missing product identity (manufacturer part number or vendor SKU)."
                )
            if unit_cost is None and list_price is None:
                row_errors.append("Missing both unit_cost and list_price.")
            if self._safe(raw_unit_cost) and unit_cost is None:
                row_errors.append("Malformed numeric value in unit_cost.")
            if self._safe(raw_list_price) and list_price is None:
                row_errors.append("Malformed numeric value in list_price.")
            if unit_cost is not None and unit_cost < 0:
                row_errors.append("unit_cost cannot be negative.")
            if list_price is not None and list_price < 0:
                row_errors.append("list_price cannot be negative.")
            if (
                unit_cost is not None
                and list_price is not None
                and unit_cost > list_price
            ):
                row_warnings.append("unit_cost exceeds list_price.")
            if pack_qty is not None and pack_qty <= 0:
                row_errors.append("pack_quantity must be positive when provided.")
            if moq is not None and moq <= 0:
                row_errors.append(
                    "minimum_order_quantity must be positive when provided."
                )

            effective_override_value = self._safe(effective_override)
            if effective_override_value:
                try:
                    datetime.fromisoformat(effective_override_value)
                except ValueError:
                    row_errors.append(
                        "effective_date_override must be ISO format YYYY-MM-DD."
                    )

            offering: dict[str, Any] | None = None
            normalized_vendor_sku = self.normalize_vendor_sku(vendor_sku)
            if normalized_vendor_sku and vendor_id:
                offering = next(
                    (
                        item
                        for item in self.list_vendor_offerings_by_vendor(vendor_id)
                        if self.normalize_vendor_sku(item.get("vendor_sku", ""))
                        == normalized_vendor_sku
                    ),
                    None,
                )
            if offering is None and part_number:
                candidates = self.search_vendor_offerings_by_manufacturer_part_number(
                    part_number
                )
                if vendor_id:
                    candidates = [
                        item
                        for item in candidates
                        if self._safe(item.get("vendor_id"), "")
                        == self._safe(vendor_id)
                    ]
                offering = candidates[0] if candidates else None

            atlas_product_uuid = self._safe(
                (offering or {}).get("atlas_product_uuid"), ""
            )
            vendor_offering_id = self._safe(
                (offering or {}).get("vendor_offering_id"), ""
            )
            resolution_status = "resolved" if offering else "unresolved"
            if not offering:
                unresolved_count += 1
                row_warnings.append(
                    "No existing vendor offering match; record remains unresolved."
                )

            validation_status = "valid"
            if row_errors:
                validation_status = "invalid"
                error_count += len(row_errors)
            if row_warnings:
                warning_count += len(row_warnings)

            diagnostics_messages = row_errors + row_warnings
            for message in row_errors:
                diagnostics.append(
                    {
                        "severity": ImportDiagnosticSeverity.ERROR.value,
                        "code": "row_validation_error",
                        "message": message,
                        "row_number": index,
                    }
                )
            for message in row_warnings:
                diagnostics.append(
                    {
                        "severity": ImportDiagnosticSeverity.WARNING.value,
                        "code": "row_validation_warning",
                        "message": message,
                        "row_number": index,
                    }
                )

            preview_rows.append(
                {
                    "source_row_number": index,
                    "manufacturer": manufacturer_name,
                    "manufacturer_part_number_imported": self._safe(part_number),
                    "vendor_sku_imported": self._safe(vendor_sku),
                    "description_imported": self._safe(description),
                    "unit_cost": unit_cost,
                    "list_price": list_price,
                    "currency": self._safe(row_currency, currency),
                    "unit_of_measure": self._safe(uom, "ea"),
                    "pack_quantity": pack_qty,
                    "minimum_order_quantity": moq,
                    "effective_date_override": effective_override_value,
                    "source_category": self._safe(source_category),
                    "notes": self._safe(notes),
                    "atlas_product_uuid": atlas_product_uuid,
                    "vendor_offering_id": vendor_offering_id,
                    "resolution_status": resolution_status,
                    "diagnostic_messages": diagnostics_messages,
                    "validation_status": validation_status,
                    "raw_values": dict(raw),
                    "normalized_values": {
                        "manufacturer_part_number": self.normalize_part_number(
                            part_number
                        ),
                        "vendor_sku": self.normalize_vendor_sku(vendor_sku),
                    },
                }
            )

        try:
            self._validate_currency(currency)
            self._validate_effective_expiration(effective_date, expiration_date)
        except ValueError as exc:
            diagnostics.append(
                {
                    "severity": ImportDiagnosticSeverity.ERROR.value,
                    "code": "version_metadata_invalid",
                    "message": self._safe(str(exc), "Version metadata invalid."),
                    "row_number": None,
                }
            )
            error_count += 1

        return {
            "preview_rows": preview_rows,
            "diagnostics": diagnostics,
            "error_count": error_count,
            "warning_count": warning_count,
            "unresolved_count": unresolved_count,
        }

    def _detect_pdf_table_candidates(
        self,
        *,
        pages: list[dict[str, Any]],
        repeated_headers: list[str],
        repeated_footers: list[str],
    ) -> list[dict[str, Any]]:
        repeated_header_set = {
            self._safe(item) for item in repeated_headers if self._safe(item)
        }
        repeated_footer_set = {
            self._safe(item) for item in repeated_footers if self._safe(item)
        }
        raw_candidates: list[dict[str, Any]] = []
        for page in pages:
            page_number = int(page.get("page_number") or 0)
            method = self._safe(page.get("text_source"), "embedded")
            ocr_status = (
                "used" if bool(page.get("ocr_derived", False)) else "not_required"
            )
            lines = [
                self._safe(line)
                for line in list(page.get("text_lines") or [])
                if self._safe(line)
            ]
            lines = [
                line
                for line in lines
                if line not in repeated_header_set and line not in repeated_footer_set
            ]
            segments = self._pdf_table_segments(lines)
            for segment_idx, segment in enumerate(segments, start=1):
                rows: list[dict[str, Any]] = []
                for local_idx, line in enumerate(segment, start=1):
                    rows.append(
                        {
                            "sequence_number": local_idx,
                            "page_number": page_number,
                            "region_id": f"pdf-page-{page_number}-seg-{segment_idx}",
                            "row_reference": f"p{page_number}:seg{segment_idx}:row{local_idx}",
                            "cells": self._pdf_split_line_to_cells(line),
                            "raw_line": line,
                            "extraction_method": method,
                            "ocr_status": ocr_status,
                        }
                    )
                if rows:
                    raw_candidates.append(
                        {
                            "candidate_id": f"pdf-candidate-page-{page_number}-{segment_idx}",
                            "page_numbers": [page_number],
                            "rows": rows,
                            "header_signature": "|".join(
                                [
                                    self.normalize_name(item)
                                    for item in rows[0].get("cells") or []
                                ]
                            ),
                        }
                    )

        grouped: dict[str, list[dict[str, Any]]] = {}
        for candidate in raw_candidates:
            signature = self._safe(candidate.get("header_signature"), "")
            if not signature:
                signature = self._safe(candidate.get("candidate_id"), "")
            grouped.setdefault(signature, []).append(candidate)

        merged_candidates: list[dict[str, Any]] = []
        for signature, members in grouped.items():
            pages_covered = sorted(
                {
                    int(page_no)
                    for member in members
                    for page_no in list(member.get("page_numbers") or [])
                }
            )
            all_rows: list[dict[str, Any]] = []
            for member in sorted(
                members, key=lambda item: int((item.get("page_numbers") or [0])[0])
            ):
                all_rows.extend(list(member.get("rows") or []))
            merged_candidates.append(
                {
                    "candidate_id": f"pdf-table-{hashlib.sha1(signature.encode('utf-8')).hexdigest()[:12]}",
                    "page_numbers": pages_covered,
                    "row_count": len(all_rows),
                    "column_count": max(
                        (len(row.get("cells") or []) for row in all_rows), default=0
                    ),
                    "header_signature": signature,
                    "rows": all_rows,
                }
            )

        merged_candidates.sort(
            key=lambda item: (
                len(list(item.get("page_numbers") or [])) * -1,
                -int(item.get("row_count") or 0),
            )
        )
        return merged_candidates

    def _pdf_table_segments(self, lines: list[str]) -> list[list[str]]:
        segments: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            if self._is_probable_table_line(line):
                current.append(line)
                continue
            if current:
                if len(current) >= 2:
                    segments.append(list(current))
                current = []
        if current and len(current) >= 2:
            segments.append(current)
        return segments

    def _is_probable_table_line(self, line: str) -> bool:
        text = self._safe(line)
        if not text:
            return False
        if "|" in text or "\t" in text or "," in text:
            return len(self._pdf_split_line_to_cells(text)) >= 3
        if len(re.findall(r"\s{2,}", text)) >= 2:
            return len(self._pdf_split_line_to_cells(text)) >= 3
        token_count = len([token for token in text.split(" ") if token.strip()])
        has_price_like = bool(re.search(r"\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?", text))
        return token_count >= 4 and has_price_like

    def _pdf_split_line_to_cells(self, line: str) -> list[str]:
        text = self._safe(line)
        for delimiter in ["|", "\t", ","]:
            if delimiter in text:
                parts = [self._safe(item) for item in text.split(delimiter)]
                return [item for item in parts if item]
        parts = [self._safe(item) for item in re.split(r"\s{2,}", text)]
        return [item for item in parts if item]

    def _is_record_current(self, record: dict[str, Any]) -> bool:
        version = self.state.get("price_list_versions", {}).get(
            self._safe(record.get("price_sheet_version_id"), ""),
            {},
        )
        if not version:
            return False
        today = date.today()
        effective = self._safe(version.get("effective_date"), "")
        expiration = self._safe(version.get("expiration_date"), "")
        try:
            effective_date = (
                datetime.fromisoformat(effective).date() if effective else None
            )
            expiration_date = (
                datetime.fromisoformat(expiration).date() if expiration else None
            )
        except ValueError:
            return False
        if effective_date and effective_date > today:
            return False
        if expiration_date and expiration_date < today:
            return False
        return True

    def _offering_pricing_freshness(self, offering: dict[str, Any]) -> str:
        relevant = [
            record
            for record in self.state.get("price_records", {}).values()
            if self._safe(record.get("vendor_offering_id"), "")
            == self._safe(offering.get("vendor_offering_id"), "")
            and bool(record.get("finalized", False))
        ]
        if not relevant:
            return "missing"
        today = date.today()
        latest_effective = None
        all_future = True
        all_expired = True
        for record in relevant:
            version = self.state.get("price_list_versions", {}).get(
                self._safe(record.get("price_sheet_version_id"), ""),
                {},
            )
            effective = self._safe(version.get("effective_date"), "")
            expiration = self._safe(version.get("expiration_date"), "")
            try:
                effective_date = (
                    datetime.fromisoformat(effective).date() if effective else None
                )
                expiration_date = (
                    datetime.fromisoformat(expiration).date() if expiration else None
                )
            except ValueError:
                continue
            if effective_date and (
                latest_effective is None or effective_date > latest_effective
            ):
                latest_effective = effective_date
            if not effective_date or effective_date <= today:
                all_future = False
            if not expiration_date or expiration_date >= today:
                all_expired = False
        if all_future:
            return "future_only"
        if all_expired:
            return "expired"
        if latest_effective and (today - latest_effective).days > 365:
            return "stale"
        return "current"

    def _normalized_row(
        self,
        row: dict[str, Any],
        *,
        manufacturer: str,
        vendor: str,
    ) -> dict[str, Any]:
        manufacturer_sku = self._safe(
            row.get("manufacturer_sku"),
            self._safe(row.get("model"), "UNKNOWN"),
        )
        canonical_sku = self._safe(row.get("canonical_sku"), manufacturer_sku)
        alternate_skus = [
            self._safe(item)
            for item in list(row.get("alternate_skus") or [])
            if self._safe(item)
        ]
        preferred_cost = self._float_or_none(
            row.get("preferred_cost")
            if row.get("preferred_cost") is not None
            else row.get("unit_cost")
        )

        commercial = ProductCommercialMetadata(
            preferred_vendor=self._safe(
                row.get("preferred_vendor"), self._safe(row.get("vendor"), vendor)
            ),
            preferred_purchase_method=self._safe(row.get("preferred_purchase_method")),
            currency=self._safe(row.get("currency"), "USD"),
            lead_time=self._safe(row.get("lead_time"), ""),
            minimum_order_quantity=self._int_or_none(row.get("minimum_order_quantity")),
            package_quantity=self._int_or_none(row.get("package_quantity")),
        )

        return {
            "manufacturer": self._safe(row.get("manufacturer"), manufacturer),
            "manufacturer_sku": manufacturer_sku,
            "canonical_sku": canonical_sku,
            "alternate_skus": alternate_skus,
            "description": self._safe(row.get("description"), ""),
            "product_family": self._safe(row.get("product_family"), "General"),
            "category": self._safe(row.get("category"), "other"),
            "discipline": self._safe(row.get("discipline"), "general"),
            "lifecycle_status": self._safe(
                row.get("lifecycle_status"),
                ProductLifecycleStatus.PENDING_VERIFICATION.value,
            ),
            "active": bool(row.get("active", True)),
            "product_image": self._safe(row.get("product_image"), ""),
            "datasheet": self._safe(row.get("datasheet"), ""),
            "commercial": commercial.to_dict(),
            "preferred_cost": preferred_cost,
            "preferred_vendor": self._safe(
                row.get("preferred_vendor"), self._safe(row.get("vendor"), vendor)
            ),
            "vendor": self._safe(row.get("vendor"), vendor),
            "vendor_sku": self._safe(row.get("vendor_sku"), canonical_sku),
            "vendor_type": self._safe(row.get("vendor_type"), "other"),
            "purchasing_channel": self._safe(
                row.get("purchasing_channel"),
                self._default_purchasing_channel(
                    self._safe(row.get("vendor_type"), "other")
                ),
            ),
            "direct_from_manufacturer": bool(
                row.get("direct_from_manufacturer", False)
            ),
            "authorization_status": self._safe(
                row.get("authorization_status"),
                "unknown",
            ),
            "availability": self._safe(row.get("availability_status"), "unknown"),
            "lead_time": self._safe(row.get("lead_time"), ""),
            "contract_pricing": bool(row.get("contract_pricing", False)),
            "freight_notes": self._safe(row.get("freight_notes"), ""),
            "date_verified": self._safe(row.get("date_verified"), self._now_iso()),
            "comments": self._safe(row.get("comments"), ""),
            "effective_date": self._safe(
                row.get("effective_date"), self._now_iso()[:10]
            ),
            "replacement_product_uuid": self._safe(
                row.get("replacement_product_uuid"), ""
            )
            or None,
            "compatible_products": [
                self._safe(item)
                for item in list(row.get("compatible_products") or [])
                if self._safe(item)
            ],
            "related_accessories": [
                self._safe(item)
                for item in list(row.get("related_accessories") or [])
                if self._safe(item)
            ],
            "project_references": [
                self._safe(item)
                for item in list(row.get("project_references") or [])
                if self._safe(item)
            ],
        }

    @staticmethod
    def _product_key(
        manufacturer: str, canonical_sku: str, manufacturer_sku: str
    ) -> str:
        sku = canonical_sku or manufacturer_sku
        return f"{manufacturer.upper()}::{sku.upper()}"

    @staticmethod
    def _import_key(manufacturer: str, vendor: str) -> str:
        return f"{manufacturer.upper()}::{vendor.upper()}"

    @staticmethod
    def _vendor_offering_id(product_uuid: str, vendor: str, vendor_sku: str) -> str:
        digest = hashlib.sha1(
            f"{product_uuid}|{vendor}|{vendor_sku}".encode("utf-8")
        ).hexdigest()[:16]
        return f"vendor-offering:{digest}"

    @staticmethod
    def _sheet_id(vendor: str, manufacturer: str, name: str) -> str:
        digest = hashlib.sha1(
            f"{vendor}|{manufacturer}|{name}".encode("utf-8")
        ).hexdigest()[:16]
        return f"price-sheet:{digest}"

    @staticmethod
    def _version_id(
        *,
        manufacturer: str,
        vendor: str,
        source_file: str,
        file_bytes: bytes,
    ) -> str:
        digest = hashlib.sha1(
            f"{manufacturer}|{vendor}|{source_file}|{hashlib.sha1(file_bytes).hexdigest()}".encode(
                "utf-8"
            )
        ).hexdigest()[:16]
        return f"price-version:{digest}"

    @staticmethod
    def _safe(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return round(float(value), 4)
        text = str(value).strip().replace("$", "").replace(",", "")
        if not text:
            return None
        try:
            return round(float(text), 4)
        except ValueError:
            return None

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        text = str(value).strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    @staticmethod
    def _lifecycle(value: Any) -> ProductLifecycleStatus:
        try:
            return ProductLifecycleStatus(str(value).strip())
        except ValueError:
            return ProductLifecycleStatus.PENDING_VERIFICATION

    @staticmethod
    def _date_from_text(value: str) -> date | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            for pattern in ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"]:
                try:
                    return datetime.strptime(value, pattern).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()

"""Commercial product foundation domain models for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class ProductLifecycleStatus(str, Enum):
    ACTIVE = "active"
    NEW = "new"
    PENDING_VERIFICATION = "pending_verification"
    DISCONTINUED = "discontinued"
    END_OF_LIFE = "end_of_life"
    OBSOLETE = "obsolete"
    REPLACEMENT_AVAILABLE = "replacement_available"


class ImportDiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFORMATIONAL = "informational"


class PriceSheetVersionStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    FINALIZED = "finalized"
    FAILED = "failed"


@dataclass
class ProductCommercialMetadata:
    msrp: float | None = None
    map_price: float | None = None
    preferred_cost: float | None = None
    suggested_sell_price: float | None = None
    minimum_sell_price: float | None = None
    maximum_sell_price: float | None = None
    target_margin: float | None = None
    minimum_margin: float | None = None
    historical_average_margin: float | None = None
    preferred_vendor: str = ""
    preferred_purchase_method: str = ""
    currency: str = "USD"
    lead_time: str = ""
    minimum_order_quantity: int | None = None
    package_quantity: int | None = None

    def __post_init__(self) -> None:
        for field_name in [
            "msrp",
            "map_price",
            "preferred_cost",
            "suggested_sell_price",
            "minimum_sell_price",
            "maximum_sell_price",
            "target_margin",
            "minimum_margin",
            "historical_average_margin",
        ]:
            value = getattr(self, field_name)
            if value is not None:
                setattr(self, field_name, _non_negative_float(field_name, value))

        self.preferred_vendor = _safe(self.preferred_vendor)
        self.preferred_purchase_method = _safe(self.preferred_purchase_method)
        self.currency = _safe(self.currency, "USD")
        self.lead_time = _safe(self.lead_time)

        if self.minimum_order_quantity is not None:
            self.minimum_order_quantity = _non_negative_int(
                "minimum_order_quantity", self.minimum_order_quantity
            )
        if self.package_quantity is not None:
            self.package_quantity = _non_negative_int(
                "package_quantity", self.package_quantity
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "msrp": self.msrp,
            "map_price": self.map_price,
            "preferred_cost": self.preferred_cost,
            "suggested_sell_price": self.suggested_sell_price,
            "minimum_sell_price": self.minimum_sell_price,
            "maximum_sell_price": self.maximum_sell_price,
            "target_margin": self.target_margin,
            "minimum_margin": self.minimum_margin,
            "historical_average_margin": self.historical_average_margin,
            "preferred_vendor": self.preferred_vendor,
            "preferred_purchase_method": self.preferred_purchase_method,
            "currency": self.currency,
            "lead_time": self.lead_time,
            "minimum_order_quantity": self.minimum_order_quantity,
            "package_quantity": self.package_quantity,
        }


@dataclass
class ProductEngineeringMetadata:
    dimensions: str = ""
    weight: str = ""
    rack_units: str = ""
    power: str = ""
    network: str = ""
    poe: str = ""
    connectors: list[str] = field(default_factory=list)
    mounting: str = ""
    environmental_rating: str = ""
    certifications: list[str] = field(default_factory=list)
    warranty: str = ""
    firmware: str = ""

    def __post_init__(self) -> None:
        self.dimensions = _safe(self.dimensions)
        self.weight = _safe(self.weight)
        self.rack_units = _safe(self.rack_units)
        self.power = _safe(self.power)
        self.network = _safe(self.network)
        self.poe = _safe(self.poe)
        self.connectors = [_safe(item) for item in list(self.connectors) if _safe(item)]
        self.mounting = _safe(self.mounting)
        self.environmental_rating = _safe(self.environmental_rating)
        self.certifications = [
            _safe(item) for item in list(self.certifications) if _safe(item)
        ]
        self.warranty = _safe(self.warranty)
        self.firmware = _safe(self.firmware)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": self.dimensions,
            "weight": self.weight,
            "rack_units": self.rack_units,
            "power": self.power,
            "network": self.network,
            "poe": self.poe,
            "connectors": list(self.connectors),
            "mounting": self.mounting,
            "environmental_rating": self.environmental_rating,
            "certifications": list(self.certifications),
            "warranty": self.warranty,
            "firmware": self.firmware,
        }


@dataclass
class ProductFutureHooks:
    inventory_enabled: bool = False
    procurement_enabled: bool = False
    receiving_enabled: bool = False
    warehouse_enabled: bool = False
    serial_numbers_enabled: bool = False
    warranty_enabled: bool = False
    installed_assets_enabled: bool = False
    service_history_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "inventory_enabled": self.inventory_enabled,
            "procurement_enabled": self.procurement_enabled,
            "receiving_enabled": self.receiving_enabled,
            "warehouse_enabled": self.warehouse_enabled,
            "serial_numbers_enabled": self.serial_numbers_enabled,
            "warranty_enabled": self.warranty_enabled,
            "installed_assets_enabled": self.installed_assets_enabled,
            "service_history_enabled": self.service_history_enabled,
        }


@dataclass
class CanonicalProduct:
    atlas_product_uuid: str
    manufacturer: str
    manufacturer_sku: str
    canonical_sku: str
    alternate_skus: list[str] = field(default_factory=list)
    description: str = ""
    product_family: str = "General"
    category: str = "other"
    discipline: str = "general"
    lifecycle_status: ProductLifecycleStatus = (
        ProductLifecycleStatus.PENDING_VERIFICATION
    )
    active: bool = True
    product_image: str = ""
    datasheet: str = ""
    commercial: ProductCommercialMetadata = field(
        default_factory=ProductCommercialMetadata
    )
    engineering: ProductEngineeringMetadata = field(
        default_factory=ProductEngineeringMetadata
    )
    future_hooks: ProductFutureHooks = field(default_factory=ProductFutureHooks)
    replacement_product_uuid: str | None = None
    compatible_products: list[str] = field(default_factory=list)
    related_accessories: list[str] = field(default_factory=list)
    project_references: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        self.atlas_product_uuid = _required(
            "atlas_product_uuid", self.atlas_product_uuid
        )
        self.manufacturer = _required("manufacturer", self.manufacturer)
        self.manufacturer_sku = _required("manufacturer_sku", self.manufacturer_sku)
        self.canonical_sku = _required("canonical_sku", self.canonical_sku)
        self.alternate_skus = [
            _safe(item) for item in list(self.alternate_skus) if _safe(item)
        ]
        self.description = _safe(self.description)
        self.product_family = _safe(self.product_family, "General")
        self.category = _safe(self.category, "other")
        self.discipline = _safe(self.discipline, "general")
        if not isinstance(self.lifecycle_status, ProductLifecycleStatus):
            self.lifecycle_status = ProductLifecycleStatus(self.lifecycle_status)
        self.product_image = _safe(self.product_image)
        self.datasheet = _safe(self.datasheet)
        if not isinstance(self.commercial, ProductCommercialMetadata):
            self.commercial = ProductCommercialMetadata(**self.commercial)
        if not isinstance(self.engineering, ProductEngineeringMetadata):
            self.engineering = ProductEngineeringMetadata(**self.engineering)
        if not isinstance(self.future_hooks, ProductFutureHooks):
            self.future_hooks = ProductFutureHooks(**self.future_hooks)
        self.replacement_product_uuid = _safe(self.replacement_product_uuid) or None
        self.compatible_products = [
            _safe(item) for item in list(self.compatible_products) if _safe(item)
        ]
        self.related_accessories = [
            _safe(item) for item in list(self.related_accessories) if _safe(item)
        ]
        self.project_references = [
            _safe(item) for item in list(self.project_references) if _safe(item)
        ]
        self.created_at = _required("created_at", self.created_at)
        self.updated_at = _required("updated_at", self.updated_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "atlas_product_uuid": self.atlas_product_uuid,
            "manufacturer": self.manufacturer,
            "manufacturer_sku": self.manufacturer_sku,
            "canonical_sku": self.canonical_sku,
            "alternate_skus": list(self.alternate_skus),
            "description": self.description,
            "product_family": self.product_family,
            "category": self.category,
            "discipline": self.discipline,
            "lifecycle_status": self.lifecycle_status.value,
            "active": self.active,
            "product_image": self.product_image,
            "datasheet": self.datasheet,
            "commercial": self.commercial.to_dict(),
            "engineering": self.engineering.to_dict(),
            "future_hooks": self.future_hooks.to_dict(),
            "replacement_product_uuid": self.replacement_product_uuid,
            "compatible_products": list(self.compatible_products),
            "related_accessories": list(self.related_accessories),
            "project_references": list(self.project_references),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class VendorOfferingRecord:
    vendor_offering_id: str
    atlas_product_uuid: str
    vendor: str
    vendor_sku: str
    vendor_type: str
    vendor_cost: float | None
    availability: str
    lead_time: str
    price_version: str
    preferred_vendor: bool
    contract_pricing: bool
    freight_notes: str
    date_verified: str
    comments: str

    def __post_init__(self) -> None:
        self.vendor_offering_id = _required(
            "vendor_offering_id", self.vendor_offering_id
        )
        self.atlas_product_uuid = _required(
            "atlas_product_uuid", self.atlas_product_uuid
        )
        self.vendor = _required("vendor", self.vendor)
        self.vendor_sku = _required("vendor_sku", self.vendor_sku)
        self.vendor_type = _safe(self.vendor_type, "other")
        self.vendor_cost = (
            None
            if self.vendor_cost is None
            else _non_negative_float("vendor_cost", self.vendor_cost)
        )
        self.availability = _safe(self.availability)
        self.lead_time = _safe(self.lead_time)
        self.price_version = _safe(self.price_version)
        self.freight_notes = _safe(self.freight_notes)
        self.date_verified = _safe(self.date_verified)
        self.comments = _safe(self.comments)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_offering_id": self.vendor_offering_id,
            "atlas_product_uuid": self.atlas_product_uuid,
            "vendor": self.vendor,
            "vendor_sku": self.vendor_sku,
            "vendor_type": self.vendor_type,
            "vendor_cost": self.vendor_cost,
            "availability": self.availability,
            "lead_time": self.lead_time,
            "price_version": self.price_version,
            "preferred_vendor": self.preferred_vendor,
            "contract_pricing": self.contract_pricing,
            "freight_notes": self.freight_notes,
            "date_verified": self.date_verified,
            "comments": self.comments,
        }


@dataclass
class PriceListVersionRecord:
    version_id: str
    manufacturer: str
    vendor: str
    import_date: str
    effective_date: str
    source_file: str
    import_user: str
    product_count: int
    products_added: int
    products_updated: int
    products_removed: int
    version_notes: str
    file_checksum: str

    def __post_init__(self) -> None:
        self.version_id = _required("version_id", self.version_id)
        self.manufacturer = _required("manufacturer", self.manufacturer)
        self.vendor = _required("vendor", self.vendor)
        self.import_date = _required("import_date", self.import_date)
        self.effective_date = _safe(self.effective_date)
        self.source_file = _required("source_file", self.source_file)
        self.import_user = _required("import_user", self.import_user)
        self.product_count = _non_negative_int("product_count", self.product_count)
        self.products_added = _non_negative_int("products_added", self.products_added)
        self.products_updated = _non_negative_int(
            "products_updated", self.products_updated
        )
        self.products_removed = _non_negative_int(
            "products_removed", self.products_removed
        )
        self.version_notes = _safe(self.version_notes)
        self.file_checksum = _required("file_checksum", self.file_checksum)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "manufacturer": self.manufacturer,
            "vendor": self.vendor,
            "import_date": self.import_date,
            "effective_date": self.effective_date,
            "source_file": self.source_file,
            "import_user": self.import_user,
            "product_count": self.product_count,
            "products_added": self.products_added,
            "products_updated": self.products_updated,
            "products_removed": self.products_removed,
            "version_notes": self.version_notes,
            "file_checksum": self.file_checksum,
        }


@dataclass
class ProductPriceHistoryRecord:
    atlas_product_uuid: str
    effective_date: str
    previous_cost: float | None
    new_cost: float | None
    dollar_difference: float | None
    percentage_change: float | None
    vendor: str
    source_version: str

    def __post_init__(self) -> None:
        self.atlas_product_uuid = _required(
            "atlas_product_uuid", self.atlas_product_uuid
        )
        self.effective_date = _safe(self.effective_date)
        self.previous_cost = (
            None
            if self.previous_cost is None
            else _non_negative_float("previous_cost", self.previous_cost)
        )
        self.new_cost = (
            None
            if self.new_cost is None
            else _non_negative_float("new_cost", self.new_cost)
        )
        self.dollar_difference = (
            None
            if self.dollar_difference is None
            else round(float(self.dollar_difference), 4)
        )
        self.percentage_change = (
            None
            if self.percentage_change is None
            else round(float(self.percentage_change), 4)
        )
        self.vendor = _safe(self.vendor)
        self.source_version = _safe(self.source_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "atlas_product_uuid": self.atlas_product_uuid,
            "effective_date": self.effective_date,
            "previous_cost": self.previous_cost,
            "new_cost": self.new_cost,
            "dollar_difference": self.dollar_difference,
            "percentage_change": self.percentage_change,
            "vendor": self.vendor,
            "source_version": self.source_version,
        }


def _safe(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _required(field_name: str, value: Any) -> str:
    text = _safe(value)
    if not text:
        raise ValueError(f"{field_name} cannot be blank")
    return text


def _non_negative_float(field_name: str, value: Any) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 4)
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return normalized


def _non_negative_int(field_name: str, value: Any) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value

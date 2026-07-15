"""Commercial knowledge domain models with immutable price versioning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class CommercialProductLifecycleStatus(str, Enum):
    ACTIVE = "active"
    MISSING_FROM_LATEST_PRICE_SHEET = "missing_from_latest_price_sheet"
    SUSPECTED_DISCONTINUED = "suspected_discontinued"
    CONFIRMED_DISCONTINUED = "confirmed_discontinued"
    REPLACEMENT_AVAILABLE = "replacement_available"
    OBSOLETE = "obsolete"
    UNKNOWN = "unknown"


class KnowledgeFreshnessStatus(str, Enum):
    FRESH = "fresh"
    REVIEW_RECOMMENDED = "review_recommended"
    STALE = "stale"
    MISSING = "missing"


class CatalogItemType(str, Enum):
    PRODUCT = "product"
    SERVICE = "service"
    FEE = "fee"
    ASSEMBLY = "assembly"


class PricingPolicyType(str, Enum):
    MSRP = "msrp"
    MAP = "map"
    COST_PLUS_PERCENT = "cost_plus_percent"
    MARGIN_PERCENT = "margin_percent"
    MULTIPLIER = "multiplier"
    MANUAL = "manual"


@dataclass
class VendorOffering:
    vendor_offering_id: str
    vendor: str
    vendor_type: str
    product: str
    manufacturer: str
    vendor_sku: str
    latest_version: str | None = None
    historical_versions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.vendor_offering_id = _required(
            "vendor_offering_id", self.vendor_offering_id
        )
        self.vendor = _required("vendor", self.vendor)
        self.vendor_type = _safe(self.vendor_type, "other")
        self.product = _required("product", self.product)
        self.manufacturer = _required("manufacturer", self.manufacturer)
        self.vendor_sku = _required("vendor_sku", self.vendor_sku)
        self.historical_versions = [
            _required("historical_version", item)
            for item in list(self.historical_versions)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_offering_id": self.vendor_offering_id,
            "vendor": self.vendor,
            "vendor_type": self.vendor_type,
            "product": self.product,
            "manufacturer": self.manufacturer,
            "vendor_sku": self.vendor_sku,
            "latest_version": self.latest_version,
            "historical_versions": list(self.historical_versions),
        }


@dataclass
class PriceSheet:
    price_sheet_id: str
    vendor: str
    manufacturer: str
    sheet_name: str
    description: str
    active_version: str | None = None
    created_date: str = field(default_factory=_now_iso)
    last_import_date: str | None = None
    status: str = "active"
    notes: str = ""

    def __post_init__(self) -> None:
        self.price_sheet_id = _required("price_sheet_id", self.price_sheet_id)
        self.vendor = _required("vendor", self.vendor)
        self.manufacturer = _required("manufacturer", self.manufacturer)
        self.sheet_name = _required("sheet_name", self.sheet_name)
        self.description = _safe(self.description)
        self.status = _required("status", self.status)
        self.notes = _safe(self.notes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "price_sheet_id": self.price_sheet_id,
            "vendor": self.vendor,
            "manufacturer": self.manufacturer,
            "sheet_name": self.sheet_name,
            "description": self.description,
            "active_version": self.active_version,
            "created_date": self.created_date,
            "last_import_date": self.last_import_date,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass
class PriceSheetVersion:
    version_id: str
    price_sheet_id: str
    version_name: str
    import_date: str
    effective_date: str
    expiration_date: str
    source_filename: str
    file_hash: str
    imported_by: str
    row_count: int
    added_products: int
    removed_products: int
    updated_products: int
    unchanged_products: int
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.version_id = _required("version_id", self.version_id)
        self.price_sheet_id = _required("price_sheet_id", self.price_sheet_id)
        self.version_name = _required("version_name", self.version_name)
        self.import_date = _required("import_date", self.import_date)
        self.effective_date = _safe(self.effective_date)
        self.expiration_date = _safe(self.expiration_date)
        self.source_filename = _required("source_filename", self.source_filename)
        self.file_hash = _required("file_hash", self.file_hash)
        self.imported_by = _required("imported_by", self.imported_by)
        self.row_count = _non_negative_int("row_count", self.row_count)
        self.added_products = _non_negative_int("added_products", self.added_products)
        self.removed_products = _non_negative_int(
            "removed_products", self.removed_products
        )
        self.updated_products = _non_negative_int(
            "updated_products", self.updated_products
        )
        self.unchanged_products = _non_negative_int(
            "unchanged_products", self.unchanged_products
        )
        self.warnings = [_safe(item) for item in list(self.warnings) if _safe(item)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "price_sheet_id": self.price_sheet_id,
            "version_name": self.version_name,
            "import_date": self.import_date,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "source_filename": self.source_filename,
            "file_hash": self.file_hash,
            "imported_by": self.imported_by,
            "row_count": self.row_count,
            "added_products": self.added_products,
            "removed_products": self.removed_products,
            "updated_products": self.updated_products,
            "unchanged_products": self.unchanged_products,
            "warnings": list(self.warnings),
        }


@dataclass
class PriceRecord:
    price_record_id: str
    version_id: str
    vendor: str
    vendor_type: str
    product: str
    vendor_sku: str
    cost: float | None
    list_price: float | None
    currency: str
    lead_time: str
    availability: str
    effective_date: str
    expiration_date: str
    confidence: float
    source_row: int
    unit_of_measure: str = "ea"
    pack_quantity: int | None = None
    minimum_order_quantity: int | None = None
    purchase_multiple: int | None = None
    active: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        self.price_record_id = _required("price_record_id", self.price_record_id)
        self.version_id = _required("version_id", self.version_id)
        self.vendor = _required("vendor", self.vendor)
        self.vendor_type = _safe(self.vendor_type, "other")
        self.product = _required("product", self.product)
        self.vendor_sku = _required("vendor_sku", self.vendor_sku)
        self.currency = _required("currency", self.currency)
        self.lead_time = _safe(self.lead_time)
        self.availability = _safe(self.availability)
        self.effective_date = _safe(self.effective_date)
        self.expiration_date = _safe(self.expiration_date)
        self.confidence = _rate("confidence", self.confidence)
        self.source_row = _non_negative_int("source_row", self.source_row)
        self.unit_of_measure = _safe(self.unit_of_measure, "ea")
        if self.pack_quantity is not None:
            self.pack_quantity = _non_negative_int("pack_quantity", self.pack_quantity)
        if self.minimum_order_quantity is not None:
            self.minimum_order_quantity = _non_negative_int(
                "minimum_order_quantity", self.minimum_order_quantity
            )
        if self.purchase_multiple is not None:
            self.purchase_multiple = _non_negative_int(
                "purchase_multiple", self.purchase_multiple
            )
        self.active = bool(self.active)
        self.notes = _safe(self.notes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "price_record_id": self.price_record_id,
            "version_id": self.version_id,
            "vendor": self.vendor,
            "vendor_type": self.vendor_type,
            "product": self.product,
            "vendor_sku": self.vendor_sku,
            "cost": self.cost,
            "list_price": self.list_price,
            "currency": self.currency,
            "lead_time": self.lead_time,
            "availability": self.availability,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "confidence": self.confidence,
            "source_row": self.source_row,
            "unit_of_measure": self.unit_of_measure,
            "pack_quantity": self.pack_quantity,
            "minimum_order_quantity": self.minimum_order_quantity,
            "purchase_multiple": self.purchase_multiple,
            "active": self.active,
            "notes": self.notes,
        }


@dataclass
class CatalogItem:
    catalog_item_id: str
    item_type: CatalogItemType
    code: str
    name: str
    description: str = ""
    long_description: str = ""
    manufacturer: str | None = None
    vendor: str | None = None
    uom: str = "ea"
    category: str = ""
    family: str = ""
    status: str = "active"
    tax_category: str = "standard"
    cost_references: list[dict[str, Any]] = field(default_factory=list)
    cost: float | None = None
    msrp: float | None = None
    map_price: float | None = None
    default_sales_price: float | None = None
    manual_unit_price: float | None = None
    taxable: bool = True
    default_tax_nexus: str | None = None
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = "manual"
    provenance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    archived: bool = False
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        self.catalog_item_id = _required("catalog_item_id", self.catalog_item_id)
        if not isinstance(self.item_type, CatalogItemType):
            self.item_type = CatalogItemType(_required("item_type", self.item_type))
        self.code = _required("code", self.code)
        self.name = _required("name", self.name)
        self.description = _safe(self.description)
        self.long_description = _safe(self.long_description)
        self.manufacturer = _safe(self.manufacturer) or None
        self.vendor = _safe(self.vendor) or None
        self.uom = _safe(self.uom, "ea")
        self.category = _safe(self.category)
        self.family = _safe(self.family)
        self.status = _safe(self.status, "active")
        self.tax_category = _safe(self.tax_category, "standard")
        self.cost_references = [
            dict(item)
            for item in list(self.cost_references or [])
            if isinstance(item, dict)
        ]
        self.cost = _non_negative_float_or_none("cost", self.cost)
        self.msrp = _non_negative_float_or_none("msrp", self.msrp)
        self.map_price = _non_negative_float_or_none("map_price", self.map_price)
        self.default_sales_price = _non_negative_float_or_none(
            "default_sales_price", self.default_sales_price
        )
        self.manual_unit_price = _non_negative_float_or_none(
            "manual_unit_price", self.manual_unit_price
        )
        self.taxable = bool(self.taxable)
        self.default_tax_nexus = _safe(self.default_tax_nexus) or None
        self.notes = _safe(self.notes)
        self.tags = [_safe(item) for item in list(self.tags or []) if _safe(item)]
        self.source = _safe(self.source, "manual")
        self.provenance = dict(self.provenance or {})
        self.metadata = dict(self.metadata or {})
        self.archived = bool(self.archived)
        self.created_at = _required("created_at", self.created_at)
        self.updated_at = _required("updated_at", self.updated_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_item_id": self.catalog_item_id,
            "item_type": self.item_type.value,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "long_description": self.long_description,
            "manufacturer": self.manufacturer,
            "vendor": self.vendor,
            "uom": self.uom,
            "category": self.category,
            "family": self.family,
            "status": self.status,
            "tax_category": self.tax_category,
            "cost_references": list(self.cost_references),
            "cost": self.cost,
            "msrp": self.msrp,
            "map_price": self.map_price,
            "default_sales_price": self.default_sales_price,
            "manual_unit_price": self.manual_unit_price,
            "taxable": self.taxable,
            "default_tax_nexus": self.default_tax_nexus,
            "notes": self.notes,
            "tags": list(self.tags),
            "source": self.source,
            "provenance": dict(self.provenance),
            "metadata": dict(self.metadata),
            "archived": self.archived,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AssemblyComponent:
    component_id: str
    component_item_id: str
    quantity: float
    required: bool = True
    sequence: int = 1
    notes: str = ""

    def __post_init__(self) -> None:
        self.component_id = _required("component_id", self.component_id)
        self.component_item_id = _required("component_item_id", self.component_item_id)
        self.quantity = _non_negative_float("quantity", self.quantity)
        self.required = bool(self.required)
        self.sequence = _non_negative_int("sequence", self.sequence)
        if self.sequence == 0:
            raise ValueError("sequence must be greater than zero")
        self.notes = _safe(self.notes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_item_id": self.component_item_id,
            "quantity": self.quantity,
            "required": self.required,
            "sequence": self.sequence,
            "notes": self.notes,
        }


@dataclass
class AssemblyVersion:
    assembly_version_id: str
    assembly_item_id: str
    version_number: int
    status: str = "active"
    expanded_description: str = ""
    component_count: int = 0
    total_cost: float = 0.0
    total_sales_price: float = 0.0
    components: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    archived: bool = False

    def __post_init__(self) -> None:
        self.assembly_version_id = _required(
            "assembly_version_id", self.assembly_version_id
        )
        self.assembly_item_id = _required("assembly_item_id", self.assembly_item_id)
        self.version_number = _non_negative_int("version_number", self.version_number)
        if self.version_number == 0:
            raise ValueError("version_number must be greater than zero")
        self.status = _safe(self.status, "active")
        self.expanded_description = _safe(self.expanded_description)
        self.component_count = _non_negative_int(
            "component_count", self.component_count
        )
        self.total_cost = _non_negative_float("total_cost", self.total_cost)
        self.total_sales_price = _non_negative_float(
            "total_sales_price", self.total_sales_price
        )
        normalized_components: list[dict[str, Any]] = []
        for component in list(self.components or []):
            if isinstance(component, dict):
                normalized_components.append(AssemblyComponent(**component).to_dict())
        self.components = normalized_components
        self.created_at = _required("created_at", self.created_at)
        self.updated_at = _required("updated_at", self.updated_at)
        self.archived = bool(self.archived)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assembly_version_id": self.assembly_version_id,
            "assembly_item_id": self.assembly_item_id,
            "version_number": self.version_number,
            "status": self.status,
            "expanded_description": self.expanded_description,
            "component_count": self.component_count,
            "total_cost": self.total_cost,
            "total_sales_price": self.total_sales_price,
            "components": [dict(item) for item in self.components],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "archived": self.archived,
        }


@dataclass
class TaxNexusRule:
    tax_rule_id: str
    nexus: str
    title: str
    rate: float
    priority: int = 100
    compound: bool = False
    taxable_item_types: list[CatalogItemType | str] = field(default_factory=list)
    exemption_flags: list[str] = field(default_factory=list)
    effective_date: str | None = None
    expiration_date: str | None = None
    archived: bool = False

    def __post_init__(self) -> None:
        self.tax_rule_id = _required("tax_rule_id", self.tax_rule_id)
        self.nexus = _required("nexus", self.nexus)
        self.title = _required("title", self.title)
        self.rate = _non_negative_float("rate", self.rate)
        self.priority = _non_negative_int("priority", self.priority)
        self.compound = bool(self.compound)
        self.taxable_item_types = [
            CatalogItemType(_required("taxable_item_type", item)).value
            for item in list(self.taxable_item_types or [])
        ]
        if not self.taxable_item_types:
            self.taxable_item_types = [item.value for item in CatalogItemType]
        self.exemption_flags = [
            _required("exemption_flag", item).lower()
            for item in list(self.exemption_flags or [])
        ]
        self.effective_date = _safe(self.effective_date) or None
        self.expiration_date = _safe(self.expiration_date) or None
        self.archived = bool(self.archived)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tax_rule_id": self.tax_rule_id,
            "nexus": self.nexus,
            "title": self.title,
            "rate": self.rate,
            "priority": self.priority,
            "compound": self.compound,
            "taxable_item_types": list(self.taxable_item_types),
            "exemption_flags": list(self.exemption_flags),
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "archived": self.archived,
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


def _rate(field_name: str, value: Any) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 4)
    if not 0 <= normalized <= 1:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return normalized


def _non_negative_int(field_name: str, value: Any) -> int:
    if not isinstance(value, int):
        if isinstance(value, float) and float(value).is_integer():
            value = int(value)
        else:
            raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _non_negative_float(field_name: str, value: Any) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 4)
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return normalized


def _non_negative_float_or_none(field_name: str, value: Any) -> float | None:
    if value is None:
        return None
    return _non_negative_float(field_name, value)

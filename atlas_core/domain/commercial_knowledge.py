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


@dataclass
class VendorOffering:
    vendor_offering_id: str
    vendor: str
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
    notes: str = ""

    def __post_init__(self) -> None:
        self.price_record_id = _required("price_record_id", self.price_record_id)
        self.version_id = _required("version_id", self.version_id)
        self.vendor = _required("vendor", self.vendor)
        self.product = _required("product", self.product)
        self.vendor_sku = _required("vendor_sku", self.vendor_sku)
        self.currency = _required("currency", self.currency)
        self.lead_time = _safe(self.lead_time)
        self.availability = _safe(self.availability)
        self.effective_date = _safe(self.effective_date)
        self.expiration_date = _safe(self.expiration_date)
        self.confidence = _rate("confidence", self.confidence)
        self.source_row = _non_negative_int("source_row", self.source_row)
        self.notes = _safe(self.notes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "price_record_id": self.price_record_id,
            "version_id": self.version_id,
            "vendor": self.vendor,
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
            "notes": self.notes,
        }


def _safe(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


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

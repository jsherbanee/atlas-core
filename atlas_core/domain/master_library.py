"""Master Library domain model for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from atlas_core.utils.refactoring import enum_value, normalize_required_text


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ProductStatus(str, Enum):
    """Lifecycle status for a canonical master-library product."""

    ACTIVE = "active"
    LEGACY = "legacy"
    DISCONTINUED = "discontinued"
    UNKNOWN = "unknown"
    PLANNED = "planned"


class ProductCategory(str, Enum):
    """Engineering category for master-library product cataloging."""

    LOUDSPEAKER = "loudspeaker"
    AMPLIFIER = "amplifier"
    DSP = "dsp"
    MICROPHONE = "microphone"
    CAMERA = "camera"
    PROJECTOR = "projector"
    DISPLAY = "display"
    LED = "led"
    RACK = "rack"
    CONTROL_PROCESSOR = "control_processor"
    TOUCH_PANEL = "touch_panel"
    NETWORK_SWITCH = "network_switch"
    AV_OVER_IP = "av_over_ip"
    CABLE = "cable"
    CONNECTOR = "connector"
    ACCESSORY = "accessory"
    MOUNT = "mount"
    FURNITURE = "furniture"
    OTHER = "other"


@dataclass
class EngineeringAttributes:
    """Engineering-focused product metadata preserved for traceability."""

    attributes: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        normalized: dict[str, str] = {}
        for key, value in dict(self.attributes).items():
            normalized_key = normalize_required_text(
                "engineering_attribute_key",
                str(key),
            )
            normalized_value = normalize_required_text(
                "engineering_attribute_value",
                str(value),
            )
            normalized[normalized_key] = normalized_value
        self.attributes = normalized

        self.tags = [
            normalize_required_text("engineering_attribute_tag", str(item))
            for item in list(self.tags)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {"attributes": dict(self.attributes), "tags": list(self.tags)}


@dataclass
class ProductRelationship:
    """Relationship between canonical products (replacement, sibling, accessory, etc.)."""

    relationship_type: str
    target_product_id: str
    confidence: float = 0.8
    evidence_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.relationship_type = normalize_required_text(
            "relationship_type",
            self.relationship_type,
        )
        self.target_product_id = normalize_required_text(
            "target_product_id",
            self.target_product_id,
        )
        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("relationship confidence must be between 0 and 1")
        self.evidence_refs = [
            normalize_required_text("evidence_ref", str(item))
            for item in list(self.evidence_refs)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_type": self.relationship_type,
            "target_product_id": self.target_product_id,
            "confidence": float(self.confidence),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass
class ProductAlias:
    """Alias reference preserved for deterministic product resolution traceability."""

    alias: str
    normalized_alias: str
    source: str = "manual"

    def __post_init__(self) -> None:
        self.alias = normalize_required_text("alias", self.alias)
        self.normalized_alias = normalize_required_text(
            "normalized_alias",
            self.normalized_alias,
        )
        self.source = normalize_required_text("source", self.source)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "normalized_alias": self.normalized_alias,
            "source": self.source,
        }


@dataclass
class ManufacturerReference:
    """Canonical manufacturer identity and known deterministic aliases."""

    manufacturer_id: str
    name: str
    normalized_name: str
    aliases: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.manufacturer_id = normalize_required_text(
            "manufacturer_id",
            self.manufacturer_id,
        )
        self.name = normalize_required_text("name", self.name)
        self.normalized_name = normalize_required_text(
            "normalized_name",
            self.normalized_name,
        )
        self.aliases = [
            normalize_required_text("manufacturer_alias", str(item))
            for item in list(self.aliases)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "manufacturer_id": self.manufacturer_id,
            "name": self.name,
            "normalized_name": self.normalized_name,
            "aliases": list(self.aliases),
        }


@dataclass
class ProductFamily:
    """Product family grouping within the master library."""

    family_id: str
    name: str
    category: ProductCategory = ProductCategory.OTHER

    def __post_init__(self) -> None:
        self.family_id = normalize_required_text("family_id", self.family_id)
        self.name = normalize_required_text("name", self.name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "name": self.name,
            "category": enum_value(self.category),
        }


@dataclass
class MasterProduct:
    """Canonical product record used as the engineering source of truth."""

    product_id: str
    manufacturer: str
    model: str
    normalized_model: str
    description: str
    category: ProductCategory = ProductCategory.OTHER
    family: str = "General"
    status: ProductStatus = ProductStatus.UNKNOWN
    aliases: list[ProductAlias] = field(default_factory=list)
    engineering_attributes: EngineeringAttributes = field(
        default_factory=EngineeringAttributes
    )
    related_products: list[ProductRelationship] = field(default_factory=list)
    confidence: float = 0.75
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        self.product_id = normalize_required_text("product_id", self.product_id)
        self.manufacturer = normalize_required_text("manufacturer", self.manufacturer)
        self.model = normalize_required_text("model", self.model)
        self.normalized_model = normalize_required_text(
            "normalized_model",
            self.normalized_model,
        )
        self.description = normalize_required_text("description", self.description)
        self.family = normalize_required_text("family", self.family)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.aliases = list(self.aliases)
        self.related_products = list(self.related_products)
        self.created_at = normalize_required_text("created_at", self.created_at)
        self.updated_at = normalize_required_text("updated_at", self.updated_at)

    def touch(self) -> None:
        self.updated_at = _now_iso()

    def add_alias(self, alias: ProductAlias) -> None:
        if alias.normalized_alias in {
            item.normalized_alias for item in list(self.aliases)
        }:
            return
        self.aliases.append(alias)
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "normalized_model": self.normalized_model,
            "description": self.description,
            "category": enum_value(self.category),
            "family": self.family,
            "status": enum_value(self.status),
            "aliases": [item.to_dict() for item in self.aliases],
            "engineering_attributes": self.engineering_attributes.to_dict(),
            "related_products": [item.to_dict() for item in self.related_products],
            "confidence": float(self.confidence),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

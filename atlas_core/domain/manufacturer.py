"""Manufacturer domain model for Atlas Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from atlas_core.domain.vendor_relationship import VendorRelationship


class ManufacturerTier(str, Enum):
    """Preference tier for an Atlas manufacturer."""

    PREFERRED = "preferred"
    PROJECT_DRIVEN = "project_driven"
    APPROVED = "approved"
    REVIEW_REQUIRED = "review_required"
    AVOID = "avoid"


class ManufacturerDiscipline(str, Enum):
    """Primary discipline for an Atlas manufacturer."""

    AUDIO = "audio"
    MICROPHONES = "microphones"
    CONTROL = "control"
    PROJECTION = "projection"
    DISPLAYS = "displays"
    VIDEO = "video"
    ASSISTED_LISTENING = "assisted_listening"
    INTERCOM = "intercom"
    LIGHTING = "lighting"
    SCREENS = "screens"
    INFRASTRUCTURE = "infrastructure"
    NETWORKING = "networking"
    UNKNOWN = "unknown"


@dataclass
class Manufacturer:
    manufacturer_id: str
    name: str
    discipline: ManufacturerDiscipline
    tier: ManufacturerTier = ManufacturerTier.APPROVED
    product_families: list[str] = field(default_factory=list)
    preferred_vendor: str | None = None
    vendor_relationships: list[VendorRelationship] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    active: bool = True
    confidence: float = 0.75

    def __post_init__(self) -> None:
        self.manufacturer_id = self._normalize_required_text(
            "manufacturer_id", self.manufacturer_id
        )
        self.name = self._normalize_required_text("name", self.name)

        if not isinstance(self.discipline, ManufacturerDiscipline):
            self.discipline = ManufacturerDiscipline(self.discipline)

        if not isinstance(self.tier, ManufacturerTier):
            self.tier = ManufacturerTier(self.tier)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

        self.product_families = [
            self._normalize_required_text("product_family", product_family)
            for product_family in self.product_families
        ]
        self.vendor_relationships = [
            self._validate_vendor_relationship(relationship)
            for relationship in self.vendor_relationships
        ]
        self.notes = [
            self._normalize_required_text("note", note)
            for note in self.notes
        ]

    def add_product_family(self, product_family: str) -> None:
        self.product_families.append(
            self._normalize_required_text("product_family", product_family)
        )

    def add_note(self, note: str) -> None:
        self.notes.append(self._normalize_required_text("note", note))

    def add_vendor_relationship(
        self, relationship: VendorRelationship
    ) -> None:
        self.vendor_relationships.append(
            self._validate_vendor_relationship(relationship)
        )

    def primary_vendor_relationship(self) -> VendorRelationship | None:
        active_relationships = [
            relationship
            for relationship in self.vendor_relationships
            if relationship.active
        ]
        if not active_relationships:
            return None

        return min(
            active_relationships,
            key=lambda relationship: relationship.priority,
        )

    def mark_review_required(self, reason: str | None = None) -> None:
        self.tier = ManufacturerTier.REVIEW_REQUIRED

        if reason is not None:
            self.add_note(reason)

    def mark_avoid(self, reason: str | None = None) -> None:
        self.tier = ManufacturerTier.AVOID

        if reason is not None:
            self.add_note(reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manufacturer_id": self.manufacturer_id,
            "name": self.name,
            "discipline": self.discipline.value,
            "tier": self.tier.value,
            "product_families": list(self.product_families),
            "preferred_vendor": self.preferred_vendor,
            "vendor_relationships": [
                relationship.to_dict()
                for relationship in self.vendor_relationships
            ],
            "notes": list(self.notes),
            "active": self.active,
            "confidence": self.confidence,
        }

    @staticmethod
    def _validate_required_text(field_name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

    @classmethod
    def _normalize_required_text(cls, field_name: str, value: str) -> str:
        cls._validate_required_text(field_name, value)
        return value.strip()

    @staticmethod
    def _validate_vendor_relationship(
        relationship: VendorRelationship,
    ) -> VendorRelationship:
        if not isinstance(relationship, VendorRelationship):
            raise ValueError("vendor_relationships must be VendorRelationship objects")

        return relationship

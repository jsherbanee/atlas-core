"""Manufacturer registry helpers for Atlas Core."""

from enum import Enum

from atlas_core.domain import (
    Manufacturer,
    ManufacturerDiscipline,
    ManufacturerTier,
)


class PurchasingPath(str, Enum):
    """Purchasing path for a registered manufacturer."""

    DIRECT = "direct"
    DISTRIBUTOR = "distributor"
    BOTH = "both"
    UNKNOWN = "unknown"


class ManufacturerRegistry:
    def __init__(self, manufacturers: list[Manufacturer] | None = None) -> None:
        self._manufacturers_by_id: dict[str, Manufacturer] = {}
        self._manufacturer_ids_by_name: dict[str, str] = {}

        for manufacturer in manufacturers or []:
            self.add(manufacturer)

    def add(self, manufacturer: Manufacturer) -> None:
        existing = self._manufacturers_by_id.get(manufacturer.manufacturer_id)
        if existing is not None:
            self._manufacturer_ids_by_name.pop(
                self._normalize_name(existing.name),
                None,
            )

        self._manufacturers_by_id[manufacturer.manufacturer_id] = manufacturer
        self._manufacturer_ids_by_name[
            self._normalize_name(manufacturer.name)
        ] = manufacturer.manufacturer_id

    def get_by_id(self, manufacturer_id: str) -> Manufacturer | None:
        if not isinstance(manufacturer_id, str):
            return None

        return self._manufacturers_by_id.get(manufacturer_id.strip())

    def get_by_name(self, name: str) -> Manufacturer | None:
        manufacturer_id = self._manufacturer_ids_by_name.get(
            self._normalize_name(name)
        )
        if manufacturer_id is None:
            return None

        return self._manufacturers_by_id.get(manufacturer_id)

    def preferred_by_discipline(
        self, discipline: ManufacturerDiscipline | str
    ) -> list[Manufacturer]:
        normalized_discipline = self._discipline(discipline)
        if normalized_discipline is None:
            return []

        return [
            manufacturer
            for manufacturer in self._manufacturers_by_id.values()
            if manufacturer.discipline is normalized_discipline
            and manufacturer.tier is ManufacturerTier.PREFERRED
        ]

    def approved_by_discipline(
        self, discipline: ManufacturerDiscipline | str
    ) -> list[Manufacturer]:
        normalized_discipline = self._discipline(discipline)
        if normalized_discipline is None:
            return []

        approved_tiers = {
            ManufacturerTier.PREFERRED,
            ManufacturerTier.APPROVED,
            ManufacturerTier.PROJECT_DRIVEN,
        }
        return [
            manufacturer
            for manufacturer in self._manufacturers_by_id.values()
            if manufacturer.discipline is normalized_discipline
            and manufacturer.tier in approved_tiers
        ]

    def requires_review(self, name: str) -> bool:
        manufacturer = self.get_by_name(name)
        if manufacturer is None:
            return True

        return (
            manufacturer.tier
            in {ManufacturerTier.REVIEW_REQUIRED, ManufacturerTier.AVOID}
            or not manufacturer.active
        )

    def purchasing_path(self, name: str) -> PurchasingPath:
        manufacturer = self.get_by_name(name)
        if manufacturer is None:
            return PurchasingPath.UNKNOWN

        preferred_vendor = self._preferred_vendor(manufacturer)
        if preferred_vendor is None:
            return PurchasingPath.UNKNOWN

        normalized_vendor = preferred_vendor.casefold()
        if normalized_vendor == "direct":
            return PurchasingPath.DIRECT

        if "direct" in normalized_vendor and "distributor" in normalized_vendor:
            return PurchasingPath.BOTH

        return PurchasingPath.DISTRIBUTOR

    def preferred_vendor_for(self, name: str) -> str | None:
        manufacturer = self.get_by_name(name)
        if manufacturer is None:
            return None

        return manufacturer.preferred_vendor

    def to_list(self) -> list[dict]:
        return [
            manufacturer.to_dict()
            for manufacturer in self._manufacturers_by_id.values()
        ]

    @staticmethod
    def _normalize_name(name: str) -> str:
        if not isinstance(name, str):
            return ""

        return name.strip().casefold()

    @staticmethod
    def _discipline(
        discipline: ManufacturerDiscipline | str,
    ) -> ManufacturerDiscipline | None:
        if isinstance(discipline, ManufacturerDiscipline):
            return discipline

        try:
            return ManufacturerDiscipline(discipline)
        except ValueError:
            return None

    @staticmethod
    def _preferred_vendor(manufacturer: Manufacturer) -> str | None:
        preferred_vendor = manufacturer.preferred_vendor
        if preferred_vendor is None or not preferred_vendor.strip():
            return None

        return preferred_vendor.strip()

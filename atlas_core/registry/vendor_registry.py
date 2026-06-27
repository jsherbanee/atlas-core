"""Vendor registry helpers for Atlas Core."""

from atlas_core.domain import Vendor, VendorStatus, VendorType


class VendorRegistry:
    def __init__(self, vendors: list[Vendor] | None = None) -> None:
        self._vendors_by_id: dict[str, Vendor] = {}
        self._vendor_ids_by_name: dict[str, str] = {}

        for vendor in vendors or []:
            self.add(vendor)

    def add(self, vendor: Vendor) -> None:
        existing = self._vendors_by_id.get(vendor.vendor_id)
        if existing is not None:
            self._vendor_ids_by_name.pop(
                self._normalize_name(existing.name),
                None,
            )

        self._vendors_by_id[vendor.vendor_id] = vendor
        self._vendor_ids_by_name[
            self._normalize_name(vendor.name)
        ] = vendor.vendor_id

    def get_by_id(self, vendor_id: str) -> Vendor | None:
        if not isinstance(vendor_id, str):
            return None

        return self._vendors_by_id.get(vendor_id.strip())

    def get_by_name(self, name: str) -> Vendor | None:
        vendor_id = self._vendor_ids_by_name.get(self._normalize_name(name))
        if vendor_id is None:
            return None

        return self._vendors_by_id.get(vendor_id)

    def active_vendors(self) -> list[Vendor]:
        return [
            vendor
            for vendor in self._vendors_by_id.values()
            if vendor.active and vendor.status is VendorStatus.ACTIVE
        ]

    def by_type(self, vendor_type: VendorType | str) -> list[Vendor]:
        normalized_vendor_type = self._vendor_type(vendor_type)
        if normalized_vendor_type is None:
            return []

        return [
            vendor
            for vendor in self._vendors_by_id.values()
            if vendor.vendor_type is normalized_vendor_type
        ]

    def requires_review(self, name: str) -> bool:
        vendor = self.get_by_name(name)
        if vendor is None:
            return True

        return vendor.requires_review()

    def to_list(self) -> list[dict]:
        return [vendor.to_dict() for vendor in self._vendors_by_id.values()]

    @staticmethod
    def _normalize_name(name: str) -> str:
        if not isinstance(name, str):
            return ""

        return name.strip().casefold()

    @staticmethod
    def _vendor_type(vendor_type: VendorType | str) -> VendorType | None:
        if isinstance(vendor_type, VendorType):
            return vendor_type

        try:
            return VendorType(vendor_type)
        except ValueError:
            return None

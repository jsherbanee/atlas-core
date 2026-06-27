"""Vendor sample seed data for Atlas Core."""

from atlas_core.domain import Vendor, VendorStatus, VendorType
from atlas_core.registry import VendorRegistry


def build_vendor_seed_data() -> list[Vendor]:
    return [
        Vendor(
            vendor_id="direct",
            name="DIRECT",
            vendor_type=VendorType.MANUFACTURER_DIRECT,
            notes=[
                "Used when AKJOHNSTON buys directly from the manufacturer."
            ],
        ),
        Vendor(
            vendor_id="midwich",
            name="Midwich",
            vendor_type=VendorType.DISTRIBUTOR,
        ),
        Vendor(
            vendor_id="exertis-almo",
            name="Exertis Almo",
            vendor_type=VendorType.DISTRIBUTOR,
        ),
        Vendor(
            vendor_id="adi",
            name="ADI",
            vendor_type=VendorType.DISTRIBUTOR,
        ),
        Vendor(
            vendor_id="wesco-anixter",
            name="Wesco / Anixter",
            vendor_type=VendorType.DISTRIBUTOR,
        ),
        Vendor(
            vendor_id="snap-one",
            name="Snap One",
            vendor_type=VendorType.DISTRIBUTOR,
        ),
        Vendor(
            vendor_id="local-subcontractor",
            name="Local subcontractor",
            vendor_type=VendorType.SUBCONTRACTOR,
            status=VendorStatus.REVIEW_REQUIRED,
            notes=[
                "Placeholder subcontractor record for project-specific field support."
            ],
        ),
    ]


def build_vendor_registry() -> VendorRegistry:
    return VendorRegistry(build_vendor_seed_data())

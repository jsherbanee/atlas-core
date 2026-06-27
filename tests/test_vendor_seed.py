from atlas_core.domain import Vendor, VendorStatus
from atlas_core.registry import VendorRegistry
from atlas_core.sample_data import build_vendor_registry, build_vendor_seed_data


def test_build_vendor_seed_data_returns_vendors():
    vendors = build_vendor_seed_data()

    assert vendors
    assert all(isinstance(vendor, Vendor) for vendor in vendors)


def test_build_vendor_registry_returns_vendor_registry():
    registry = build_vendor_registry()

    assert isinstance(registry, VendorRegistry)


def test_direct_exists():
    registry = build_vendor_registry()

    assert registry.get_by_name("DIRECT") is not None


def test_midwich_exists():
    registry = build_vendor_registry()

    assert registry.get_by_name("Midwich") is not None


def test_local_subcontractor_requires_review():
    registry = build_vendor_registry()
    vendor = registry.get_by_name("Local subcontractor")

    assert vendor is not None
    assert vendor.status is VendorStatus.REVIEW_REQUIRED
    assert registry.requires_review("Local subcontractor") is True

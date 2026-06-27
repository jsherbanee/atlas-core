from atlas_core.domain import Manufacturer
from atlas_core.registry import ManufacturerRegistry, PurchasingPath
from atlas_core.sample_data import (
    build_manufacturer_registry,
    build_manufacturer_seed_data,
)


def test_build_manufacturer_seed_data_returns_manufacturers():
    manufacturers = build_manufacturer_seed_data()

    assert manufacturers
    assert all(
        isinstance(manufacturer, Manufacturer)
        for manufacturer in manufacturers
    )


def test_build_manufacturer_registry_returns_manufacturer_registry():
    registry = build_manufacturer_registry()

    assert isinstance(registry, ManufacturerRegistry)


def test_qsc_exists():
    registry = build_manufacturer_registry()

    assert registry.get_by_name("QSC") is not None


def test_shure_purchasing_path_is_direct():
    registry = build_manufacturer_registry()

    assert registry.purchasing_path("Shure") is PurchasingPath.DIRECT


def test_epson_purchasing_path_is_distributor():
    registry = build_manufacturer_registry()

    assert registry.purchasing_path("Epson") is PurchasingPath.DISTRIBUTOR


def test_meyer_sound_preferred_vendor_is_direct():
    registry = build_manufacturer_registry()

    assert registry.preferred_vendor_for("Meyer Sound") == "DIRECT"


def test_qsc_preferred_vendor_is_midwich():
    registry = build_manufacturer_registry()

    assert registry.preferred_vendor_for("QSC") == "Midwich"

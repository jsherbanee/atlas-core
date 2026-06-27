from atlas_core.domain import Vendor, VendorStatus, VendorType
from atlas_core.registry import VendorRegistry


def make_vendor(
    vendor_id: str = "starin",
    name: str = "Starin",
    vendor_type: VendorType = VendorType.DISTRIBUTOR,
    status: VendorStatus = VendorStatus.ACTIVE,
    active: bool = True,
) -> Vendor:
    return Vendor(
        vendor_id=vendor_id,
        name=name,
        vendor_type=vendor_type,
        status=status,
        active=active,
    )


def test_add_and_get_by_id():
    vendor = make_vendor()
    registry = VendorRegistry()

    registry.add(vendor)

    assert registry.get_by_id("starin") is vendor


def test_get_by_name_case_insensitive():
    vendor = make_vendor(name="Starin")
    registry = VendorRegistry([vendor])

    assert registry.get_by_name("starin") is vendor
    assert registry.get_by_name(" STARIN ") is vendor


def test_replacing_duplicate_vendor_id():
    original = make_vendor(name="Starin")
    replacement = make_vendor(name="Starin AV")
    registry = VendorRegistry([original])

    registry.add(replacement)

    assert registry.get_by_id("starin") is replacement
    assert registry.get_by_name("Starin AV") is replacement
    assert registry.get_by_name("Starin") is None


def test_active_vendors_returns_active_status_and_active_flag():
    active_vendor = make_vendor()
    inactive_status_vendor = make_vendor(
        vendor_id="old",
        name="Old Vendor",
        status=VendorStatus.INACTIVE,
    )
    inactive_flag_vendor = make_vendor(
        vendor_id="disabled",
        name="Disabled Vendor",
        active=False,
    )
    registry = VendorRegistry(
        [active_vendor, inactive_status_vendor, inactive_flag_vendor]
    )

    assert registry.active_vendors() == [active_vendor]


def test_by_type_returns_matching_vendor_type():
    distributor = make_vendor()
    dealer = make_vendor(
        vendor_id="dealer",
        name="Dealer",
        vendor_type=VendorType.DEALER,
    )
    registry = VendorRegistry([distributor, dealer])

    assert registry.by_type("distributor") == [distributor]
    assert registry.by_type(VendorType.DEALER) == [dealer]


def test_by_type_returns_empty_list_for_invalid_type():
    registry = VendorRegistry([make_vendor()])

    assert registry.by_type("invalid") == []


def test_requires_review_for_missing_vendor():
    assert VendorRegistry().requires_review("Missing") is True


def test_requires_review_uses_vendor_requires_review():
    vendor = make_vendor(status=VendorStatus.REVIEW_REQUIRED)
    registry = VendorRegistry([vendor])

    assert registry.requires_review("Starin") is True


def test_requires_review_returns_false_for_active_vendor():
    vendor = make_vendor()
    registry = VendorRegistry([vendor])

    assert registry.requires_review("Starin") is False


def test_to_list_returns_vendor_dicts():
    vendor = make_vendor()
    registry = VendorRegistry([vendor])

    assert registry.to_list() == [vendor.to_dict()]

import pytest

from atlas_core.domain import Vendor, VendorStatus, VendorType


def test_creating_valid_vendor():
    vendor = Vendor(
        vendor_id=" starin ",
        name=" Starin ",
        vendor_type=VendorType.DISTRIBUTOR,
        status=VendorStatus.ACTIVE,
        account_number="12345",
        contact_name="Jane Smith",
        contact_email="jane@example.com",
        phone="555-0100",
        notes=[" Preferred for Q-SYS accessories. "],
    )

    assert vendor.vendor_id == "starin"
    assert vendor.name == "Starin"
    assert vendor.vendor_type is VendorType.DISTRIBUTOR
    assert vendor.status is VendorStatus.ACTIVE
    assert vendor.account_number == "12345"
    assert vendor.contact_name == "Jane Smith"
    assert vendor.contact_email == "jane@example.com"
    assert vendor.phone == "555-0100"
    assert vendor.notes == ["Preferred for Q-SYS accessories."]
    assert vendor.active is True


def test_accepting_string_vendor_type_and_status():
    vendor = Vendor(
        vendor_id="starin",
        name="Starin",
        vendor_type="dealer",
        status="review_required",
    )

    assert vendor.vendor_type is VendorType.DEALER
    assert vendor.status is VendorStatus.REVIEW_REQUIRED


def test_rejecting_blank_vendor_id():
    with pytest.raises(ValueError, match="vendor_id cannot be blank"):
        Vendor(vendor_id=" ", name="Starin")


def test_rejecting_blank_name():
    with pytest.raises(ValueError, match="name cannot be blank"):
        Vendor(vendor_id="starin", name=" ")


def test_rejecting_blank_notes():
    with pytest.raises(ValueError, match="note cannot be blank"):
        Vendor(vendor_id="starin", name="Starin", notes=[" "])


def test_adding_notes():
    vendor = Vendor(vendor_id="starin", name="Starin")

    vendor.add_note(" Confirm freight terms. ")
    vendor.add_note("Use for quick-ship accessories.")

    assert vendor.notes == [
        "Confirm freight terms.",
        "Use for quick-ship accessories.",
    ]


@pytest.mark.parametrize(
    "status",
    [
        VendorStatus.REVIEW_REQUIRED,
        VendorStatus.AVOID,
        VendorStatus.INACTIVE,
    ],
)
def test_requires_review_for_review_statuses(status: VendorStatus):
    vendor = Vendor(vendor_id="starin", name="Starin", status=status)

    assert vendor.requires_review() is True


def test_requires_review_for_inactive_vendor():
    vendor = Vendor(vendor_id="starin", name="Starin", active=False)

    assert vendor.requires_review() is True


def test_does_not_require_review_for_active_vendor():
    vendor = Vendor(vendor_id="starin", name="Starin")

    assert vendor.requires_review() is False


def test_to_dict_output():
    vendor = Vendor(
        vendor_id="starin",
        name="Starin",
        vendor_type=VendorType.DISTRIBUTOR,
        status=VendorStatus.REVIEW_REQUIRED,
        account_number="12345",
        contact_name="Jane Smith",
        contact_email="jane@example.com",
        phone="555-0100",
        notes=["Confirm freight terms."],
        active=False,
    )

    assert vendor.to_dict() == {
        "vendor_id": "starin",
        "name": "Starin",
        "vendor_type": "distributor",
        "status": "review_required",
        "account_number": "12345",
        "contact_name": "Jane Smith",
        "contact_email": "jane@example.com",
        "phone": "555-0100",
        "notes": ["Confirm freight terms."],
        "active": False,
    }

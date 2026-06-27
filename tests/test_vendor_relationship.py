import pytest

from atlas_core.domain import VendorRelationship, VendorRelationshipType


def test_creating_valid_relationship():
    relationship = VendorRelationship(
        vendor_name=" Starin ",
        relationship_type=VendorRelationshipType.DISTRIBUTOR,
        priority=2,
        account_number="12345",
        typical_lead_time_days=14,
        notes=[" Preferred distributor. "],
        active=True,
    )

    assert relationship.vendor_name == "Starin"
    assert relationship.relationship_type is VendorRelationshipType.DISTRIBUTOR
    assert relationship.priority == 2
    assert relationship.account_number == "12345"
    assert relationship.typical_lead_time_days == 14
    assert relationship.notes == ["Preferred distributor."]
    assert relationship.active is True


def test_accepting_string_relationship_type():
    relationship = VendorRelationship(
        vendor_name="Starin",
        relationship_type="dealer",
    )

    assert relationship.relationship_type is VendorRelationshipType.DEALER


def test_rejecting_blank_vendor_name():
    with pytest.raises(ValueError, match="vendor_name cannot be blank"):
        VendorRelationship(vendor_name=" ")


def test_rejecting_invalid_priority():
    with pytest.raises(ValueError, match="priority must be greater than 0"):
        VendorRelationship(vendor_name="Starin", priority=0)


def test_rejecting_negative_lead_time():
    with pytest.raises(
        ValueError,
        match="typical_lead_time_days cannot be negative",
    ):
        VendorRelationship(
            vendor_name="Starin",
            typical_lead_time_days=-1,
        )


def test_adding_notes():
    relationship = VendorRelationship(vendor_name="Starin")

    relationship.add_note(" Confirm account pricing. ")
    relationship.add_note("Coordinate freight.")

    assert relationship.notes == [
        "Confirm account pricing.",
        "Coordinate freight.",
    ]


def test_to_dict_output():
    relationship = VendorRelationship(
        vendor_name="Starin",
        relationship_type=VendorRelationshipType.DISTRIBUTOR,
        priority=2,
        account_number="12345",
        typical_lead_time_days=14,
        notes=["Confirm account pricing."],
        active=False,
    )

    assert relationship.to_dict() == {
        "vendor_name": "Starin",
        "relationship_type": "distributor",
        "priority": 2,
        "account_number": "12345",
        "typical_lead_time_days": 14,
        "notes": ["Confirm account pricing."],
        "active": False,
    }

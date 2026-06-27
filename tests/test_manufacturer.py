import pytest

from atlas_core.domain import (
    Manufacturer,
    ManufacturerDiscipline,
    ManufacturerTier,
    VendorRelationship,
    VendorRelationshipType,
)


def test_creating_valid_manufacturer():
    manufacturer = Manufacturer(
        manufacturer_id=" qsc ",
        name=" Q-SYS ",
        discipline=ManufacturerDiscipline.AUDIO,
    )

    assert manufacturer.manufacturer_id == "qsc"
    assert manufacturer.name == "Q-SYS"
    assert manufacturer.discipline is ManufacturerDiscipline.AUDIO
    assert manufacturer.tier is ManufacturerTier.APPROVED
    assert manufacturer.active
    assert manufacturer.confidence == 0.75


def test_accepting_string_discipline_and_tier():
    manufacturer = Manufacturer(
        manufacturer_id="sony",
        name="Sony",
        discipline="displays",
        tier="preferred",
    )

    assert manufacturer.discipline is ManufacturerDiscipline.DISPLAYS
    assert manufacturer.tier is ManufacturerTier.PREFERRED


def test_rejecting_blank_name():
    with pytest.raises(ValueError, match="name cannot be blank"):
        Manufacturer(
            manufacturer_id="qsc",
            name=" ",
            discipline=ManufacturerDiscipline.AUDIO,
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        Manufacturer(
            manufacturer_id="qsc",
            name="Q-SYS",
            discipline=ManufacturerDiscipline.AUDIO,
            confidence=1.1,
        )


def test_adding_product_families():
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
    )

    manufacturer.add_product_family(" QIO ")
    manufacturer.add_product_family("Core")

    assert manufacturer.product_families == ["QIO", "Core"]


def test_adding_notes():
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
    )

    manufacturer.add_note(" Preferred for divisible rooms. ")
    manufacturer.add_note("Confirm current lead times.")

    assert manufacturer.notes == [
        "Preferred for divisible rooms.",
        "Confirm current lead times.",
    ]


def test_mark_review_required_without_reason():
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
    )

    manufacturer.mark_review_required()

    assert manufacturer.tier is ManufacturerTier.REVIEW_REQUIRED
    assert manufacturer.notes == []


def test_mark_review_required_with_reason():
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
    )

    manufacturer.mark_review_required(" Confirm compatibility with owner standard. ")

    assert manufacturer.tier is ManufacturerTier.REVIEW_REQUIRED
    assert manufacturer.notes == ["Confirm compatibility with owner standard."]


def test_mark_avoid_without_reason():
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
    )

    manufacturer.mark_avoid()

    assert manufacturer.tier is ManufacturerTier.AVOID
    assert manufacturer.notes == []


def test_mark_avoid_with_reason():
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
    )

    manufacturer.mark_avoid(" Not approved by client. ")

    assert manufacturer.tier is ManufacturerTier.AVOID
    assert manufacturer.notes == ["Not approved by client."]


def test_to_dict_output():
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
        tier=ManufacturerTier.PREFERRED,
        preferred_vendor="Acme AV Supply",
        active=True,
        confidence=0.9,
    )
    manufacturer.add_product_family("Core")
    manufacturer.add_note("Preferred for conference rooms.")

    assert manufacturer.to_dict() == {
        "manufacturer_id": "qsc",
        "name": "Q-SYS",
        "discipline": "audio",
        "tier": "preferred",
        "product_families": ["Core"],
        "preferred_vendor": "Acme AV Supply",
        "vendor_relationships": [],
        "notes": ["Preferred for conference rooms."],
        "active": True,
        "confidence": 0.9,
    }


def test_adding_vendor_relationship():
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
    )
    relationship = VendorRelationship(
        vendor_name="Starin",
        relationship_type=VendorRelationshipType.DISTRIBUTOR,
    )

    manufacturer.add_vendor_relationship(relationship)

    assert manufacturer.vendor_relationships == [relationship]


def test_primary_vendor_relationship_uses_lowest_priority():
    direct = VendorRelationship(
        vendor_name="QSC Direct",
        relationship_type=VendorRelationshipType.DIRECT,
        priority=2,
    )
    distributor = VendorRelationship(
        vendor_name="Starin",
        relationship_type=VendorRelationshipType.DISTRIBUTOR,
        priority=1,
    )
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
        vendor_relationships=[direct, distributor],
    )

    assert manufacturer.primary_vendor_relationship() is distributor


def test_primary_vendor_relationship_ignores_inactive_relationships():
    inactive = VendorRelationship(
        vendor_name="QSC Direct",
        relationship_type=VendorRelationshipType.DIRECT,
        priority=1,
        active=False,
    )
    active = VendorRelationship(
        vendor_name="Starin",
        relationship_type=VendorRelationshipType.DISTRIBUTOR,
        priority=2,
    )
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
        vendor_relationships=[inactive, active],
    )

    assert manufacturer.primary_vendor_relationship() is active


def test_primary_vendor_relationship_returns_none_without_active_relationships():
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
        vendor_relationships=[
            VendorRelationship(vendor_name="QSC Direct", active=False)
        ],
    )

    assert manufacturer.primary_vendor_relationship() is None


def test_to_dict_includes_vendor_relationships():
    relationship = VendorRelationship(
        vendor_name="Starin",
        relationship_type=VendorRelationshipType.DISTRIBUTOR,
        priority=2,
    )
    manufacturer = Manufacturer(
        manufacturer_id="qsc",
        name="Q-SYS",
        discipline=ManufacturerDiscipline.AUDIO,
        vendor_relationships=[relationship],
    )

    assert manufacturer.to_dict()["vendor_relationships"] == [
        relationship.to_dict()
    ]

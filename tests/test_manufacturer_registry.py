from atlas_core.domain import (
    Manufacturer,
    ManufacturerDiscipline,
    ManufacturerTier,
    VendorRelationship,
    VendorRelationshipType,
)
from atlas_core.registry import ManufacturerRegistry, PurchasingPath


def make_manufacturer(
    manufacturer_id: str = "qsc",
    name: str = "Q-SYS",
    discipline: ManufacturerDiscipline = ManufacturerDiscipline.AUDIO,
    tier: ManufacturerTier = ManufacturerTier.APPROVED,
    preferred_vendor: str | None = None,
    vendor_relationships: list[VendorRelationship] | None = None,
    active: bool = True,
) -> Manufacturer:
    return Manufacturer(
        manufacturer_id=manufacturer_id,
        name=name,
        discipline=discipline,
        tier=tier,
        preferred_vendor=preferred_vendor,
        vendor_relationships=vendor_relationships or [],
        active=active,
    )


def test_add_and_get_by_id():
    manufacturer = make_manufacturer()
    registry = ManufacturerRegistry()

    registry.add(manufacturer)

    assert registry.get_by_id("qsc") is manufacturer


def test_get_by_name_case_insensitive():
    manufacturer = make_manufacturer(name="Q-SYS")
    registry = ManufacturerRegistry([manufacturer])

    assert registry.get_by_name("q-sys") is manufacturer
    assert registry.get_by_name(" Q-SYS ") is manufacturer


def test_replacing_duplicate_manufacturer_id():
    original = make_manufacturer(name="Q-SYS")
    replacement = make_manufacturer(name="QSC")
    registry = ManufacturerRegistry([original])

    registry.add(replacement)

    assert registry.get_by_id("qsc") is replacement
    assert registry.get_by_name("QSC") is replacement
    assert registry.get_by_name("Q-SYS") is None


def test_preferred_by_discipline():
    preferred_audio = make_manufacturer(tier=ManufacturerTier.PREFERRED)
    approved_audio = make_manufacturer(
        manufacturer_id="biamp",
        name="Biamp",
        tier=ManufacturerTier.APPROVED,
    )
    preferred_display = make_manufacturer(
        manufacturer_id="sony",
        name="Sony",
        discipline=ManufacturerDiscipline.DISPLAYS,
        tier=ManufacturerTier.PREFERRED,
    )
    registry = ManufacturerRegistry(
        [preferred_audio, approved_audio, preferred_display]
    )

    assert registry.preferred_by_discipline("audio") == [preferred_audio]


def test_approved_by_discipline():
    preferred_audio = make_manufacturer(tier=ManufacturerTier.PREFERRED)
    approved_audio = make_manufacturer(
        manufacturer_id="biamp",
        name="Biamp",
        tier=ManufacturerTier.APPROVED,
    )
    project_driven_audio = make_manufacturer(
        manufacturer_id="meyer",
        name="Meyer Sound",
        tier=ManufacturerTier.PROJECT_DRIVEN,
    )
    review_audio = make_manufacturer(
        manufacturer_id="legacy",
        name="Legacy Audio",
        tier=ManufacturerTier.REVIEW_REQUIRED,
    )
    registry = ManufacturerRegistry(
        [
            preferred_audio,
            approved_audio,
            project_driven_audio,
            review_audio,
        ]
    )

    assert registry.approved_by_discipline(ManufacturerDiscipline.AUDIO) == [
        preferred_audio,
        approved_audio,
        project_driven_audio,
    ]


def test_requires_review_for_missing_manufacturer():
    assert ManufacturerRegistry().requires_review("Unknown") is True


def test_requires_review_for_review_required_tier():
    manufacturer = make_manufacturer(tier=ManufacturerTier.REVIEW_REQUIRED)
    registry = ManufacturerRegistry([manufacturer])

    assert registry.requires_review("Q-SYS") is True


def test_requires_review_for_avoid_tier():
    manufacturer = make_manufacturer(tier=ManufacturerTier.AVOID)
    registry = ManufacturerRegistry([manufacturer])

    assert registry.requires_review("Q-SYS") is True


def test_requires_review_for_inactive_manufacturer():
    manufacturer = make_manufacturer(active=False)
    registry = ManufacturerRegistry([manufacturer])

    assert registry.requires_review("Q-SYS") is True


def test_purchasing_path_returns_direct_when_preferred_vendor_is_direct():
    manufacturer = make_manufacturer(preferred_vendor="DIRECT")
    registry = ManufacturerRegistry([manufacturer])

    assert registry.purchasing_path("Q-SYS") is PurchasingPath.DIRECT


def test_purchasing_path_uses_direct_vendor_relationship():
    manufacturer = make_manufacturer(
        preferred_vendor="Acme AV Supply",
        vendor_relationships=[
            VendorRelationship(
                vendor_name="QSC Direct",
                relationship_type=VendorRelationshipType.DIRECT,
            )
        ],
    )
    registry = ManufacturerRegistry([manufacturer])

    assert registry.purchasing_path("Q-SYS") is PurchasingPath.DIRECT


def test_purchasing_path_returns_distributor_when_vendor_is_distributor_name():
    manufacturer = make_manufacturer(preferred_vendor="Acme AV Supply")
    registry = ManufacturerRegistry([manufacturer])

    assert registry.purchasing_path("Q-SYS") is PurchasingPath.DISTRIBUTOR


def test_purchasing_path_uses_distributor_vendor_relationship():
    manufacturer = make_manufacturer(
        preferred_vendor="DIRECT",
        vendor_relationships=[
            VendorRelationship(
                vendor_name="Starin",
                relationship_type=VendorRelationshipType.DISTRIBUTOR,
            )
        ],
    )
    registry = ManufacturerRegistry([manufacturer])

    assert registry.purchasing_path("Q-SYS") is PurchasingPath.DISTRIBUTOR


def test_purchasing_path_returns_both_when_vendor_supports_direct_and_distributor():
    manufacturer = make_manufacturer(preferred_vendor="Direct and Distributor")
    registry = ManufacturerRegistry([manufacturer])

    assert registry.purchasing_path("Q-SYS") is PurchasingPath.BOTH


def test_purchasing_path_returns_unknown_when_preferred_vendor_is_missing():
    manufacturer = make_manufacturer()
    registry = ManufacturerRegistry([manufacturer])

    assert registry.purchasing_path("Q-SYS") is PurchasingPath.UNKNOWN
    assert registry.purchasing_path("Unknown") is PurchasingPath.UNKNOWN


def test_preferred_vendor_for_returns_vendor_name():
    manufacturer = make_manufacturer(preferred_vendor="Acme AV Supply")
    registry = ManufacturerRegistry([manufacturer])

    assert registry.preferred_vendor_for("Q-SYS") == "Acme AV Supply"
    assert registry.preferred_vendor_for("Unknown") is None


def test_preferred_vendor_for_uses_primary_vendor_relationship():
    manufacturer = make_manufacturer(
        preferred_vendor="Legacy Vendor",
        vendor_relationships=[
            VendorRelationship(
                vendor_name="Secondary Vendor",
                relationship_type=VendorRelationshipType.DISTRIBUTOR,
                priority=2,
            ),
            VendorRelationship(
                vendor_name="Primary Vendor",
                relationship_type=VendorRelationshipType.DEALER,
                priority=1,
            ),
        ],
    )
    registry = ManufacturerRegistry([manufacturer])

    assert registry.preferred_vendor_for("Q-SYS") == "Primary Vendor"


def test_preferred_vendor_for_falls_back_to_preferred_vendor():
    manufacturer = make_manufacturer(preferred_vendor="Acme AV Supply")
    registry = ManufacturerRegistry([manufacturer])

    assert registry.preferred_vendor_for("Q-SYS") == "Acme AV Supply"


def test_inactive_vendor_relationships_are_ignored():
    manufacturer = make_manufacturer(
        preferred_vendor="Acme AV Supply",
        vendor_relationships=[
            VendorRelationship(
                vendor_name="QSC Direct",
                relationship_type=VendorRelationshipType.DIRECT,
                active=False,
            )
        ],
    )
    registry = ManufacturerRegistry([manufacturer])

    assert registry.purchasing_path("Q-SYS") is PurchasingPath.DISTRIBUTOR
    assert registry.preferred_vendor_for("Q-SYS") == "Acme AV Supply"


def test_invalid_discipline_returns_empty_list():
    registry = ManufacturerRegistry([make_manufacturer()])

    assert registry.preferred_by_discipline("invalid") == []
    assert registry.approved_by_discipline("invalid") == []

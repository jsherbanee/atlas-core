"""Manufacturer sample seed data for Atlas Core."""

from atlas_core.domain import (
    Manufacturer,
    ManufacturerDiscipline,
    ManufacturerTier,
    VendorRelationship,
    VendorRelationshipType,
)
from atlas_core.registry import ManufacturerRegistry


def build_manufacturer_seed_data() -> list[Manufacturer]:
    return [
        Manufacturer(
            manufacturer_id="qsc",
            name="QSC",
            discipline=ManufacturerDiscipline.CONTROL,
            tier=ManufacturerTier.PREFERRED,
            vendor_relationships=[
                _relationship("Midwich", VendorRelationshipType.DISTRIBUTOR, 1),
                _relationship("Exertis Almo", VendorRelationshipType.DISTRIBUTOR, 2),
            ],
            product_families=["Q-SYS", "QIO", "CX-Q"],
        ),
        Manufacturer(
            manufacturer_id="shure",
            name="Shure",
            discipline=ManufacturerDiscipline.MICROPHONES,
            tier=ManufacturerTier.PREFERRED,
            vendor_relationships=[
                _relationship("DIRECT", VendorRelationshipType.DIRECT, 1),
                _relationship("Midwich", VendorRelationshipType.DISTRIBUTOR, 2),
            ],
            product_families=["Axient Digital", "ULX-D", "Microflex"],
        ),
        Manufacturer(
            manufacturer_id="meyer-sound",
            name="Meyer Sound",
            discipline=ManufacturerDiscipline.AUDIO,
            tier=ManufacturerTier.PREFERRED,
            vendor_relationships=[
                _relationship("DIRECT", VendorRelationshipType.DIRECT, 1),
            ],
            product_families=["ULTRA-X", "Leopard", "Lina"],
        ),
        Manufacturer(
            manufacturer_id="l-acoustics",
            name="L-Acoustics",
            discipline=ManufacturerDiscipline.AUDIO,
            tier=ManufacturerTier.PREFERRED,
            vendor_relationships=[
                _relationship("DIRECT", VendorRelationshipType.DIRECT, 1),
            ],
            product_families=[
                "A Series",
                "X Series",
                "LA Amplified Controllers",
            ],
        ),
        Manufacturer(
            manufacturer_id="epson",
            name="Epson",
            discipline=ManufacturerDiscipline.PROJECTION,
            tier=ManufacturerTier.PREFERRED,
            vendor_relationships=[
                _relationship("Midwich", VendorRelationshipType.DISTRIBUTOR, 1),
                _relationship("Exertis Almo", VendorRelationshipType.DISTRIBUTOR, 2),
            ],
            product_families=["PowerLite", "Pro L", "EB-PU"],
        ),
        Manufacturer(
            manufacturer_id="sony",
            name="Sony",
            discipline=ManufacturerDiscipline.DISPLAYS,
            tier=ManufacturerTier.APPROVED,
            vendor_relationships=[
                _relationship("Midwich", VendorRelationshipType.DISTRIBUTOR, 1),
                _relationship("Exertis Almo", VendorRelationshipType.DISTRIBUTOR, 2),
            ],
            product_families=["BRAVIA Professional Displays"],
        ),
        Manufacturer(
            manufacturer_id="chief",
            name="Chief",
            discipline=ManufacturerDiscipline.INFRASTRUCTURE,
            tier=ManufacturerTier.PREFERRED,
            vendor_relationships=[
                _relationship("Midwich", VendorRelationshipType.DISTRIBUTOR, 1),
                _relationship("ADI", VendorRelationshipType.DISTRIBUTOR, 2),
            ],
            product_families=["Fusion", "Tempo", "RPA"],
        ),
        Manufacturer(
            manufacturer_id="middle-atlantic",
            name="Middle Atlantic",
            discipline=ManufacturerDiscipline.INFRASTRUCTURE,
            tier=ManufacturerTier.PREFERRED,
            vendor_relationships=[
                _relationship("Midwich", VendorRelationshipType.DISTRIBUTOR, 1),
                _relationship("ADI", VendorRelationshipType.DISTRIBUTOR, 2),
            ],
            product_families=["BGR", "DWR", "SR"],
        ),
        Manufacturer(
            manufacturer_id="etc",
            name="ETC",
            discipline=ManufacturerDiscipline.LIGHTING,
            tier=ManufacturerTier.PREFERRED,
            vendor_relationships=[
                _relationship("DIRECT", VendorRelationshipType.DIRECT, 1),
            ],
            product_families=["Eos", "Source Four", "ColorSource"],
        ),
        Manufacturer(
            manufacturer_id="blackmagic",
            name="Blackmagic",
            discipline=ManufacturerDiscipline.VIDEO,
            tier=ManufacturerTier.APPROVED,
            vendor_relationships=[
                _relationship("Midwich", VendorRelationshipType.DISTRIBUTOR, 1),
                _relationship("Exertis Almo", VendorRelationshipType.DISTRIBUTOR, 2),
            ],
            product_families=["ATEM", "DeckLink", "HyperDeck"],
        ),
        Manufacturer(
            manufacturer_id="brightsign",
            name="BrightSign",
            discipline=ManufacturerDiscipline.VIDEO,
            tier=ManufacturerTier.APPROVED,
            vendor_relationships=[
                _relationship("Midwich", VendorRelationshipType.DISTRIBUTOR, 1),
            ],
            product_families=["XT", "XD", "LS"],
        ),
    ]


def build_manufacturer_registry() -> ManufacturerRegistry:
    return ManufacturerRegistry(build_manufacturer_seed_data())


def _relationship(
    vendor_name: str,
    relationship_type: VendorRelationshipType,
    priority: int,
) -> VendorRelationship:
    return VendorRelationship(
        vendor_name=vendor_name,
        relationship_type=relationship_type,
        priority=priority,
    )

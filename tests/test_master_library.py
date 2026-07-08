import pytest

from atlas_core.domain import (
    EngineeringAttributes,
    MasterProduct,
    ProductAlias,
    ProductCategory,
    ProductRelationship,
    ProductStatus,
)


def test_master_product_serializes_aliases() -> None:
    product = MasterProduct(
        product_id="prd-1",
        manufacturer="QSC",
        model="Core 110f",
        normalized_model="CORE110F",
        description="Network DSP",
        category=ProductCategory.DSP,
        family="Q-SYS Core",
        status=ProductStatus.ACTIVE,
        aliases=[
            ProductAlias(alias="QSYS CORE 110F", normalized_alias="QSYSCORE110F"),
            ProductAlias(alias="Core-110f", normalized_alias="CORE110F"),
        ],
        engineering_attributes=EngineeringAttributes(
            attributes={"io_channels": "8x8", "protocol": "Q-LAN"},
            tags=["audio", "dsp"],
        ),
        related_products=[
            ProductRelationship(
                relationship_type="replacement_for",
                target_product_id="prd-legacy-core",
                confidence=0.9,
            )
        ],
        confidence=0.88,
        created_at="2026-07-07T00:00:00+00:00",
        updated_at="2026-07-07T00:00:00+00:00",
    )

    assert product.category is ProductCategory.DSP
    assert product.status is ProductStatus.ACTIVE
    assert len(product.aliases) == 2

    payload = product.to_dict()
    assert payload["category"] == "dsp"
    assert payload["status"] == "active"
    assert payload["aliases"][0]["alias"] in {"Core-110f", "QSYS CORE 110F"}
    assert payload["engineering_attributes"]["attributes"]["protocol"] == "Q-LAN"


def test_master_product_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        MasterProduct(
            product_id="prd-1",
            manufacturer="QSC",
            model="Core 110f",
            normalized_model="CORE110F",
            description="Network DSP",
            confidence=1.2,
            created_at="2026-07-07T00:00:00+00:00",
            updated_at="2026-07-07T00:00:00+00:00",
        )

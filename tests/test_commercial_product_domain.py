import pytest

from atlas_core.domain.commercial_product import (
    CanonicalProduct,
    ProductCommercialMetadata,
    ProductLifecycleStatus,
)


def test_canonical_product_serializes_with_required_lifecycle_states() -> None:
    product = CanonicalProduct(
        atlas_product_uuid="e4ce8f89-43e4-5cde-a748-0f2d1222585d",
        manufacturer="QSC",
        manufacturer_sku="Core 110f",
        canonical_sku="CORE-110F",
        lifecycle_status=ProductLifecycleStatus.PENDING_VERIFICATION,
    )
    payload = product.to_dict()

    assert payload["lifecycle_status"] == "pending_verification"
    assert payload["manufacturer"] == "QSC"


def test_commercial_metadata_rejects_negative_numbers() -> None:
    with pytest.raises(ValueError, match="must be non-negative"):
        ProductCommercialMetadata(preferred_cost=-1)

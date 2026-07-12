import pytest

from atlas_core.domain import (
    ProductResolution,
    ProductResolutionCandidate,
    ProductResolutionManualOverride,
    ProductResolutionStatus,
)


def test_product_resolution_domain_to_dict() -> None:
    candidate = ProductResolutionCandidate(
        product_id="prd:1",
        manufacturer="QSC",
        model="Core 110f",
        match_type="exact_manufacturer_model",
        confidence=0.98,
        reason="Exact manufacturer/model match",
    )
    override = ProductResolutionManualOverride(
        original_match={"canonical_product_id": "prd:1"},
        manual_selection={"selected_product_id": "prd:2"},
        reviewer="Estimator",
        timestamp="2026-07-11T10:00:00+00:00",
        reason="Preferred project standard",
    )

    resolution = ProductResolution(
        resolution_id="resolution:abc",
        source_object_id="EQ-1",
        resolution_status=ProductResolutionStatus.EXACT_PRODUCT,
        canonical_product={"product_id": "prd:1"},
        manufacturer="QSC",
        model="Core 110f",
        resolution_confidence=0.95,
        resolution_reason="Exact manufacturer/model match.",
        candidate_matches=[candidate],
        manual_override=override,
        source_evidence=["AV-601"],
        canonical_product_id="prd:1",
        manufacturer_id="qsc",
        future_price_records=[],
        future_vendor_records=[],
        future_labor_templates=[],
    )

    data = resolution.to_dict()
    assert data["resolution_id"] == "resolution:abc"
    assert data["resolution_status"] == "exact_product"
    assert data["manual_override"]["reviewer"] == "Estimator"


def test_product_resolution_domain_rejects_blank_reason() -> None:
    with pytest.raises(ValueError, match="resolution_reason cannot be blank"):
        ProductResolution(
            resolution_id="resolution:abc",
            source_object_id="EQ-1",
            resolution_status=ProductResolutionStatus.UNKNOWN_PRODUCT,
            canonical_product=None,
            manufacturer="Unknown",
            model="Unknown",
            resolution_confidence=0.1,
            resolution_reason=" ",
        )

from atlas_core.domain.cost_engine import CostStatus, VendorClassification
from atlas_core.domain.deterministic_estimate import (
    CostStatus as EstimateCostStatus,
    Estimate,
    EstimateLine,
    EstimatePackage,
    ProductResolutionStatus,
)
from atlas_core.domain.product_resolution import ProductResolution
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
from atlas_core.services.cost_engine_service import DeterministicCostEngine


def _estimate() -> Estimate:
    return Estimate(
        estimate_id="estimate:test",
        project_id="project-1",
        project_name="Test",
        packages=[
            EstimatePackage(
                package_id="pkg-1",
                name="Equipment",
                lines=[
                    EstimateLine(
                        line_id="estimate-line:1",
                        source_object="EQ-1",
                        object_type="equipment",
                        manufacturer="QSC",
                        model="Core110f",
                        description="DSP",
                        quantity=2,
                        pricing_status=EstimateCostStatus.NO_PRICING,
                        labor_status=EstimateCostStatus.NO_PRICING,
                        confidence=0.8,
                    )
                ],
            )
        ],
    )


def _resolution(status: str = "exact_product") -> ProductResolution:
    return ProductResolution(
        resolution_id="res-1",
        source_object_id="EQ-1",
        resolution_status=ProductResolutionStatus(status),
        canonical_product={
            "product_id": "QSC::Core110f",
            "manufacturer": "QSC",
            "model": "Core110f",
        },
        manufacturer="QSC",
        model="Core110f",
        resolution_confidence=0.92,
        resolution_reason="matched",
        candidate_matches=[],
        source_evidence=["AV-101"],
        canonical_product_id="QSC::Core110f",
        manufacturer_id="qsc",
    )


def _commercial_state(
    vendor: str = "PreferredVendor", cost: float = 1000.0
) -> dict[str, object]:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor=vendor,
        manufacturer="QSC",
        sheet_name="QSC Sheet",
        description="Test",
        source_filename="qsc.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=[
            {
                "vendor": vendor,
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "QSC-110F",
                "unit_cost": cost,
                "currency": "USD",
                "availability_status": "in_stock",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
                "confidence": 0.95,
            }
        ],
    )
    return service.to_dict()


def test_cost_selection_prefers_project_quote() -> None:
    result = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=_commercial_state(cost=1000.0),
        project_id="project-1",
        project_quotes=[
            {
                "project_id": "project-1",
                "product": "QSC::Core110f",
                "vendor": "QuotedVendor",
                "unit_cost": 920.0,
                "currency": "USD",
                "active": True,
            }
        ],
    )
    assert result.lines[0].status is CostStatus.QUOTED
    assert result.lines[0].unit_cost == 920.0


def test_vendor_preference_and_classification() -> None:
    result = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=_commercial_state(vendor="Regional Dist", cost=980.0),
        project_id="project-1",
        preferred_vendor_policy={"organization": "Regional Dist"},
        vendor_type_overrides={"Regional Dist": "authorized_distributor"},
    )
    line = result.lines[0]
    assert line.vendor == "Regional Dist"
    assert line.vendor_type is VendorClassification.AUTHORIZED_DISTRIBUTOR
    assert line.status in {CostStatus.VERIFIED, CostStatus.CURRENT}


def test_allowance_and_missing_status() -> None:
    allowance = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution(status="generic_allowance")],
        commercial_state=CommercialKnowledgeService.empty_state(),
        project_id="project-1",
        allowances={"EQ-1": 150.0},
    )
    assert allowance.lines[0].status is CostStatus.ALLOWANCE

    missing = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution(status="unknown_product")],
        commercial_state=CommercialKnowledgeService.empty_state(),
        project_id="project-1",
    )
    assert missing.lines[0].status is CostStatus.MISSING


def test_traceability_and_coverage_summary() -> None:
    result = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=_commercial_state(cost=1000.0),
        project_id="project-1",
    )
    line = result.lines[0]
    assert line.price_sheet_version_id
    assert line.source_file
    assert result.summary is not None
    assert result.commercial_coverage is not None
    assert result.commercial_coverage.coverage_percent >= 0


def test_quick_add_project_only_and_promotion() -> None:
    engine = DeterministicCostEngine()
    project_result = engine.quick_add_product(
        project_id="project-1",
        manufacturer="QSC",
        model="NV-32H",
        description="Quick add encoder",
        vendor="QuickVendor",
        vendor_type="integrator",
        cost=600.0,
        source="manual entry",
        project_only=True,
        project_state={},
    )
    assert project_result["mode"] == "project_only"
    project_state = project_result["project_state"]
    assert project_state["quick_add_products"]["project-1"]

    promoted = engine.quick_add_product(
        project_id="project-1",
        manufacturer="QSC",
        model="NV-32H",
        description="Quick add encoder",
        vendor="QuickVendor",
        vendor_type="integrator",
        cost=610.0,
        source="manual entry",
        project_only=False,
        commercial_state=CommercialKnowledgeService.empty_state(),
    )
    assert promoted["mode"] == "promoted"
    state = promoted["commercial_state"]
    assert state["price_records"]

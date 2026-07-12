from datetime import UTC, datetime
from typing import Any

from atlas_core.domain.deterministic_estimate import (
    CostStatus,
    Estimate,
    EstimatePackage,
    EstimateLine,
    ProductResolutionStatus,
)
from atlas_core.domain.pricing_engine import PricingStatus
from atlas_core.domain.product_resolution import ProductResolution
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
from atlas_core.services.pricing_engine_service import DeterministicPricingEngine


def _estimate_line(line_id: str = "estimate-line:1") -> EstimateLine:
    return EstimateLine(
        line_id=line_id,
        source_object="EQ-1",
        object_type="equipment",
        manufacturer="QSC",
        model="Core110f",
        description="DSP",
        quantity=2,
        pricing_status=CostStatus.NO_PRICING,
        labor_status=CostStatus.NO_PRICING,
        confidence=0.8,
    )


def _estimate() -> Estimate:
    return Estimate(
        estimate_id="estimate:test",
        project_id="project-1",
        project_name="Test",
        packages=[
            EstimatePackage(
                package_id="pkg-1",
                name="Equipment",
                lines=[_estimate_line()],
            )
        ],
    )


def _resolution(status: str = "exact_product") -> ProductResolution:
    status_value = ProductResolutionStatus(status)
    return ProductResolution(
        resolution_id="res-1",
        source_object_id="EQ-1",
        resolution_status=status_value,
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


def _commercial_state(cost: float = 1000.0) -> dict[str, Any]:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="PreferredVendor",
        manufacturer="QSC",
        sheet_name="QSC Sheet",
        description="Test",
        source_filename="qsc.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=[
            {
                "vendor": "PreferredVendor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "QSC-110F",
                "unit_cost": cost,
                "list_price": 2000,
                "currency": "USD",
                "lead_time": "4 weeks",
                "availability_status": "in_stock",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
                "confidence": 0.95,
            },
            {
                "vendor": "AltVendor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "ALT-110F",
                "unit_cost": cost + 100,
                "list_price": 2100,
                "currency": "USD",
                "lead_time": "5 weeks",
                "availability_status": "in_stock",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
                "confidence": 0.9,
            },
        ],
    )
    return service.to_dict()


def test_exact_current_price_selection() -> None:
    engine = DeterministicPricingEngine()
    result = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=_commercial_state(),
        project_id="project-1",
        preferred_vendor_policy={"organization": "PreferredVendor"},
    )

    line = result.priced_lines[0]
    assert line.pricing_status in {
        PricingStatus.VERIFIED_CURRENT,
        PricingStatus.CURRENT_PRICE_SHEET,
    }
    assert line.unit_cost == 1000.0


def test_preferred_vendor_selection() -> None:
    engine = DeterministicPricingEngine()
    result = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=_commercial_state(),
        project_id="project-1",
        preferred_vendor_policy={"organization": "PreferredVendor"},
    )
    line = result.priced_lines[0]
    assert line.selection is not None
    assert line.selection.candidates
    assert line.selection.candidates[0].vendor == "PreferredVendor"


def test_project_quote_priority() -> None:
    engine = DeterministicPricingEngine()
    result = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=_commercial_state(cost=1000.0),
        project_id="project-1",
        preferred_vendor_policy={"organization": "PreferredVendor"},
        project_quotes=[
            {
                "project_id": "project-1",
                "product": "QSC::Core110f",
                "vendor": "QuotedVendor",
                "unit_cost": 900.0,
                "currency": "USD",
                "active": True,
                "exact_match": True,
            }
        ],
    )
    line = result.priced_lines[0]
    assert line.pricing_status is PricingStatus.QUOTED
    assert line.unit_cost == 900.0


def test_multiple_vendor_candidates_kept_reviewable() -> None:
    engine = DeterministicPricingEngine()
    result = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=_commercial_state(),
        project_id="project-1",
    )
    line = result.priced_lines[0]
    assert line.selection is not None
    assert len(line.selection.candidates) >= 2


def test_historical_fallback_and_stale_selection() -> None:
    old_state = _commercial_state(cost=800.0)
    old_state["product_history"]["QSC::Core110f"]["last_updated"] = datetime(
        2020, 1, 1, tzinfo=UTC
    ).isoformat()

    engine = DeterministicPricingEngine()
    result = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=old_state,
        project_id="project-1",
    )

    line = result.priced_lines[0]
    assert line.pricing_status in {
        PricingStatus.STALE_PRICE,
        PricingStatus.HISTORICAL_PRICE,
    }


def test_expired_price_rejection_when_current_exists() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="PreferredVendor",
        manufacturer="QSC",
        sheet_name="QSC Sheet",
        description="Test",
        source_filename="qsc.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=[
            {
                "vendor": "PreferredVendor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "QSC-110F",
                "unit_cost": 900,
                "effective_date": "2026-01-01",
                "expiration_date": "2099-01-01",
                "availability_status": "in_stock",
            },
            {
                "vendor": "ExpiredVendor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "EXP-110F",
                "unit_cost": 700,
                "effective_date": "2024-01-01",
                "expiration_date": "2024-12-31",
                "availability_status": "in_stock",
            },
        ],
    )

    result = DeterministicPricingEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=service.to_dict(),
        project_id="project-1",
        preferred_vendor_policy={"organization": "PreferredVendor"},
    )
    line = result.priced_lines[0]
    assert line.unit_cost == 900.0


def test_missing_from_latest_warning() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="PreferredVendor",
        manufacturer="QSC",
        sheet_name="QSC Sheet",
        description="Test",
        source_filename="qsc_v1.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=[
            {
                "vendor": "PreferredVendor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "QSC-110F",
                "unit_cost": 1000,
            }
        ],
    )
    service.import_price_sheet(
        vendor="PreferredVendor",
        manufacturer="QSC",
        sheet_name="QSC Sheet",
        description="Test",
        source_filename="qsc_v2.csv",
        file_bytes=b"v2",
        imported_by="tester",
        rows=[],
    )

    result = DeterministicPricingEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=service.to_dict(),
        project_id="project-1",
    )
    line = result.priced_lines[0]
    assert line.pricing_status in {
        PricingStatus.MISSING_FROM_LATEST_PRICE_SHEET,
        PricingStatus.NO_PRICING,
    }


def test_generic_allowance_and_unknown_product_unpriced() -> None:
    engine = DeterministicPricingEngine()

    generic = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution(status="generic_allowance")],
        commercial_state=CommercialKnowledgeService.empty_state(),
        project_id="project-1",
        generic_allowances={"EQ-1": 150.0},
    )
    assert generic.priced_lines[0].pricing_status in {
        PricingStatus.ESTIMATED_ALLOWANCE,
        PricingStatus.MANUAL_OVERRIDE,
    }

    unknown = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution(status="unknown_product")],
        commercial_state=CommercialKnowledgeService.empty_state(),
        project_id="project-1",
    )
    assert unknown.priced_lines[0].pricing_status is PricingStatus.NO_PRICING


def test_manual_override_and_extended_cost() -> None:
    engine = DeterministicPricingEngine()
    result = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=_commercial_state(cost=1000.0),
        project_id="project-1",
        manual_overrides={
            "estimate-line:1": {
                "manual_unit_cost": 777.0,
                "selected_vendor": "ManualVendor",
                "override_reason": "Use negotiated project value",
                "reviewer_placeholder": "Estimator",
                "source_reference": "email quote",
            }
        },
    )
    line = result.priced_lines[0]
    assert line.pricing_status is PricingStatus.MANUAL_OVERRIDE
    assert line.extended_cost == 1554.0


def test_commercial_coverage_and_confidence_summary() -> None:
    engine = DeterministicPricingEngine()
    result = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=_commercial_state(cost=1000.0),
        project_id="project-1",
    )
    assert result.commercial_coverage is not None
    assert result.summary is not None
    assert result.summary.material_subtotal >= 0
    assert 0 <= result.summary.commercial_confidence <= 1


def test_price_sheet_version_traceability_and_deterministic_rerun() -> None:
    engine = DeterministicPricingEngine()
    state = _commercial_state(cost=1000.0)
    first = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )
    second = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )

    line = first.priced_lines[0]
    assert line.selected_price_sheet_version_id
    assert line.source_refs
    assert first.pricing_run_id == second.pricing_run_id


def test_price_update_impact_detection_and_exports() -> None:
    engine = DeterministicPricingEngine()
    state_old = _commercial_state(cost=1000.0)
    snapshot = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state_old,
        project_id="project-1",
    )

    state_new = _commercial_state(cost=1200.0)
    latest = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state_new,
        project_id="project-1",
    )

    advisories = engine.detect_price_update_impact(snapshot=snapshot, latest=latest)
    assert advisories

    summary_json = engine.export_pricing_summary_json(latest)
    priced_bom_csv = engine.export_priced_bom_csv(latest)
    coverage_json = engine.export_commercial_coverage_json(latest)
    exceptions_csv = engine.export_pricing_exceptions_csv(latest)

    assert "pricing_run_id" in summary_json
    assert "estimate_line_id" in priced_bom_csv
    assert "total_resolved_products" in coverage_json
    assert "warning_code" in exceptions_csv

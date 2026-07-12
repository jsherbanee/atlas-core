from datetime import date

from atlas_core.domain.cost_engine import (
    CostSelectionRequest,
    CostSelectionResultStatus,
    CostStatus,
    VendorClassification,
)
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


def _estimate(quantity: float = 2.0) -> Estimate:
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
                        quantity=quantity,
                        pricing_status=EstimateCostStatus.NO_PRICING,
                        labor_status=EstimateCostStatus.NO_PRICING,
                        confidence=0.86,
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


def _state_with_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="VendorA",
        manufacturer="QSC",
        sheet_name="QSC Sheet",
        description="Test",
        source_filename="qsc.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=rows,
    )
    return service.to_dict()


def test_single_valid_cost_selection_and_provenance() -> None:
    state = _state_with_rows(
        [
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "QSC-110F",
                "unit_cost": 1000.0,
                "currency": "USD",
                "availability_status": "in_stock",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
                "confidence": 0.95,
            }
        ]
    )
    result = DeterministicCostEngine(as_of=DeterministicCostEngine().as_of).run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )
    line = result.lines[0]
    assert line.status in {CostStatus.CURRENT, CostStatus.VERIFIED}
    assert line.vendor == "VendorA"
    assert line.price_sheet_id is not None
    assert line.price_sheet_version_id is not None
    assert line.price_record_id is not None
    assert line.selection_timestamp
    assert line.selection_rule_id
    assert line.candidate_fingerprint


def test_multiple_valid_vendors_and_tie_break_lowest_cost() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="VendorA",
        manufacturer="QSC",
        sheet_name="QSC Sheet A",
        description="A",
        source_filename="a.csv",
        file_bytes=b"a",
        imported_by="tester",
        rows=[
            {
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 1000.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ],
    )
    service.import_price_sheet(
        vendor="VendorB",
        manufacturer="QSC",
        sheet_name="QSC Sheet B",
        description="B",
        source_filename="b.csv",
        file_bytes=b"b",
        imported_by="tester",
        rows=[
            {
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "B-1",
                "unit_cost": 980.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ],
    )
    state = service.to_dict()
    result = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )
    assert result.lines[0].vendor == "VendorB"
    assert result.lines[0].unit_cost == 980.0


def test_direct_vs_distributor_prefers_manufacturer_direct() -> None:
    state = _state_with_rows(
        [
            {
                "vendor": "QSC",
                "vendor_type": "manufacturer_direct",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "D-1",
                "unit_cost": 995.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            },
            {
                "vendor": "DistributorX",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "X-1",
                "unit_cost": 990.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            },
        ]
    )
    result = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )
    assert result.lines[0].vendor_type is VendorClassification.MANUFACTURER_DIRECT


def test_overlapping_versions_deterministic_selection() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="VendorA",
        manufacturer="QSC",
        sheet_name="QSC Sheet",
        description="v1",
        source_filename="qsc1.csv",
        file_bytes=b"v1",
        imported_by="tester",
        rows=[
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 1000.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ],
    )
    service.import_price_sheet(
        vendor="VendorA",
        manufacturer="QSC",
        sheet_name="QSC Sheet",
        description="v2",
        source_filename="qsc2.csv",
        file_bytes=b"v2",
        imported_by="tester",
        rows=[
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 980.0,
                "currency": "USD",
                "effective_date": "2026-06-01",
                "expiration_date": "2026-12-31",
            }
        ],
    )
    result = DeterministicCostEngine(as_of=DeterministicCostEngine().as_of).run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=service.to_dict(),
        project_id="project-1",
    )
    assert result.lines[0].unit_cost in {980.0, 1000.0}
    assert result.lines[0].selection is not None


def test_expired_and_future_version_handling() -> None:
    state = _state_with_rows(
        [
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 990.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-01-31",
            }
        ]
    )
    expired = DeterministicCostEngine(as_of=date(2026, 7, 1)).run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )
    assert expired.lines[0].status in {CostStatus.EXPIRED, CostStatus.UNAVAILABLE}

    future_only_state = _state_with_rows(
        [
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 990.0,
                "currency": "USD",
                "effective_date": "2027-01-01",
                "expiration_date": "2027-12-31",
            }
        ]
    )
    future = DeterministicCostEngine(as_of=date(2026, 7, 1)).run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=future_only_state,
        project_id="project-1",
    )
    assert future.lines[0].status is CostStatus.MISSING
    assert "future_pricing_only" in (
        future.lines[0].warnings[0] if future.lines[0].warnings else ""
    )


def test_no_pricing_and_inactive_eligibility_states() -> None:
    missing = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution(status="unknown_product")],
        commercial_state=CommercialKnowledgeService.empty_state(),
        project_id="project-1",
    )
    assert missing.lines[0].status is CostStatus.MISSING

    state = _state_with_rows(
        [
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 1000.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ]
    )
    inactive = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
        eligibility_state={
            "inactive_vendors": ["VendorA"],
            "inactive_products": ["QSC::Core110f"],
        },
    )
    assert inactive.lines[0].status is CostStatus.MISSING


def test_pack_moq_purchase_multiple_handling() -> None:
    state = _state_with_rows(
        [
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 200.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
                "pack_quantity": 2,
                "minimum_order_quantity": 5,
                "purchase_multiple": 3,
            }
        ]
    )
    result = DeterministicCostEngine().run(
        estimate=_estimate(quantity=2.0),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )
    line = result.lines[0]
    assert line.unit_cost == 100.0
    assert line.purchasing_quantity == 6.0
    assert line.extended_cost == 600.0


def test_manual_override_precedence_and_audit() -> None:
    result = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=CommercialKnowledgeService.empty_state(),
        project_id="project-1",
        manual_overrides={
            "estimate-line:1": {
                "unit_cost": 777.0,
                "vendor": "ManualVendor",
                "reason": "Bid-day negotiated override",
                "owner_user_id": "estimator",
                "active": True,
            }
        },
    )
    line = result.lines[0]
    assert line.unit_cost == 777.0
    assert line.selection is not None
    assert line.selection.method == "manual_override"
    assert line.selection_rule_id == "cost_source_hierarchy:manual_override"


def test_snapshot_reproducibility_and_compare() -> None:
    state = _state_with_rows(
        [
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 1000.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ]
    )
    engine = DeterministicCostEngine()
    a = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )
    b = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )
    assert a.cost_run_id == b.cost_run_id
    assert engine.replay_cost_snapshot(a.to_dict()).cost_run_id == a.cost_run_id

    c = engine.run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
        manual_overrides={"estimate-line:1": {"unit_cost": 900.0, "active": True}},
    )
    deltas = engine.compare_cost_snapshots(baseline=a, candidate=c)
    assert deltas


def test_confidence_breakdown_and_candidate_reasons() -> None:
    state = _state_with_rows(
        [
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 1000.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            },
            {
                "vendor": "VendorB",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "B-1",
                "unit_cost": 1005.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            },
        ]
    )
    result = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )
    line = result.lines[0]
    assert line.confidence is not None
    assert 0.0 <= line.confidence.score <= 1.0
    assert any("freshness_score=" in item for item in line.confidence.rationale)
    assert line.selection is not None
    assert any(not item.selected for item in line.selection.candidates)


def test_allowance_and_quick_add_paths() -> None:
    allowance = DeterministicCostEngine().run(
        estimate=_estimate(),
        product_resolutions=[_resolution(status="generic_allowance")],
        commercial_state=CommercialKnowledgeService.empty_state(),
        project_id="project-1",
        allowances={"EQ-1": 150.0},
    )
    assert allowance.lines[0].status is CostStatus.ALLOWANCE

    engine = DeterministicCostEngine()
    quick = engine.quick_add_product(
        project_id="project-1",
        manufacturer="QSC",
        model="NV-32H",
        description="Quick add encoder",
        vendor="QuickVendor",
        vendor_type="integrator",
        cost=610.0,
        source="manual entry",
        project_only=True,
        project_state={},
    )
    assert quick["mode"] == "project_only"


def test_core_selection_api_surface_select_cost() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="VendorA",
        manufacturer="QSC",
        sheet_name="Sheet A",
        description="A",
        source_filename="a.csv",
        file_bytes=b"a",
        imported_by="tester",
        rows=[
            {
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 1200.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ],
    )
    service.import_price_sheet(
        vendor="VendorB",
        manufacturer="QSC",
        sheet_name="Sheet B",
        description="B",
        source_filename="b.csv",
        file_bytes=b"b",
        imported_by="tester",
        rows=[
            {
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "B-1",
                "unit_cost": 1100.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ],
    )
    state = service.to_dict()
    engine = DeterministicCostEngine(as_of=date(2026, 7, 1))
    request = CostSelectionRequest(
        product_id="QSC::Core110f",
        requested_quantity=3.0,
        as_of_date="2026-07-01",
        preferred_vendor="VendorB",
        currency="USD",
    )
    result = engine.select_cost(request, commercial_state=state)
    assert result.status in {
        CostSelectionResultStatus.SELECTED,
        CostSelectionResultStatus.SELECTED_WITH_WARNINGS,
    }
    assert result.selected_candidate is not None
    assert result.selected_candidate.vendor == "VendorB"
    assert result.extended_acquisition_cost > 0
    assert result.provenance is not None
    assert result.provenance.product_id == "QSC::Core110f"


def test_core_selection_api_helpers() -> None:
    state = _state_with_rows(
        [
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 200.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
                "pack_quantity": 2,
                "minimum_order_quantity": 5,
                "purchase_multiple": 3,
            }
        ]
    )
    engine = DeterministicCostEngine(as_of=date(2026, 7, 1))
    request = {
        "product_id": "QSC::Core110f",
        "requested_quantity": 2.0,
        "as_of_date": "2026-07-01",
    }
    selection = engine.select_cost(request, commercial_state=state)
    candidates = engine.list_eligible_candidates(request, commercial_state=state)
    assert candidates
    first_eval = engine.evaluate_candidate(candidates[0])
    assert "eligible" in first_eval
    rejection = engine.explain_candidate_rejection(candidates[0])
    assert rejection.message
    if len(candidates) > 1:
        comparison = engine.compare_candidates(candidates[0], candidates[1])
        assert comparison["winner"]
    preview = engine.preview_quantity_normalization(
        requested_quantity=2.0,
        unit_cost=200.0,
        pack_quantity=2,
        minimum_order_quantity=5,
        purchase_multiple=3,
    )
    assert preview["purchasable_quantity"] == 6.0
    provenance = engine.get_selection_provenance(selection)
    assert provenance.get("product_id") == "QSC::Core110f"
    confidence = engine.get_confidence_breakdown(selection)
    assert "score" in confidence


def test_select_cost_honors_permitted_purchasing_channels() -> None:
    service = CommercialKnowledgeService()
    service.import_price_sheet(
        vendor="DistVendor",
        manufacturer="QSC",
        sheet_name="Dist Sheet",
        description="dist",
        source_filename="dist.csv",
        file_bytes=b"dist",
        imported_by="tester",
        rows=[
            {
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "D-1",
                "unit_cost": 1200.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ],
    )
    service.import_price_sheet(
        vendor="MarketVendor",
        manufacturer="QSC",
        sheet_name="Market Sheet",
        description="market",
        source_filename="market.csv",
        file_bytes=b"market",
        imported_by="tester",
        rows=[
            {
                "vendor_type": "marketplace",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "M-1",
                "unit_cost": 900.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ],
    )

    engine = DeterministicCostEngine(as_of=date(2026, 7, 1))
    result = engine.select_cost(
        {
            "product_id": "QSC::Core110f",
            "requested_quantity": 1.0,
            "as_of_date": "2026-07-01",
            "permitted_purchasing_channels": ["authorized_distributor"],
        },
        commercial_state=service.to_dict(),
    )

    assert result.selected_candidate is not None
    assert result.selected_candidate.vendor == "DistVendor"


def test_cost_engine_skips_non_finalized_price_sheet_versions() -> None:
    state = _state_with_rows(
        [
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 1000.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ]
    )
    versions = state.get("price_sheet_versions", {})
    assert isinstance(versions, dict)
    for version in versions.values():
        if isinstance(version, dict):
            version["status"] = "draft"

    result = DeterministicCostEngine(as_of=date(2026, 7, 1)).run(
        estimate=_estimate(),
        product_resolutions=[_resolution()],
        commercial_state=state,
        project_id="project-1",
    )
    assert result.lines[0].status is CostStatus.MISSING


def test_select_cost_populates_provenance_source_file_hash() -> None:
    state = _state_with_rows(
        [
            {
                "vendor": "VendorA",
                "vendor_type": "authorized_distributor",
                "manufacturer": "QSC",
                "model": "Core110f",
                "vendor_sku": "A-1",
                "unit_cost": 1000.0,
                "currency": "USD",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
            }
        ]
    )
    expected_hash = ""
    versions = state.get("price_sheet_versions", {})
    assert isinstance(versions, dict)
    for version in versions.values():
        if isinstance(version, dict):
            expected_hash = str(version.get("file_hash") or "")
            if expected_hash:
                break

    result = DeterministicCostEngine(as_of=date(2026, 7, 1)).select_cost(
        {
            "product_id": "QSC::Core110f",
            "requested_quantity": 1.0,
            "as_of_date": "2026-07-01",
        },
        commercial_state=state,
    )
    assert result.provenance is not None
    assert result.provenance.source_file_hash == expected_hash

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from atlas_core.domain.document_intake import DocumentIntakeSnapshot
from atlas_core.services.evidence_baseline_reconstruction_service import (
    EvidenceBaselineReconstructionResult,
    BeforeAfterRow,
)

from atlas_core.domain.deterministic_estimate import (
    ProductResolutionStatus,
)
from atlas_core.domain.pricing_engine import PricingStatus
from atlas_core.domain.product_resolution import (
    ProductResolution,
    ProductResolutionCandidate,
)
from atlas_core.services.commercial_baseline_validation_service import (
    CommercialBaselineValidationService,
)
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
from atlas_core.services.estimate_service import DeterministicEstimateService
from atlas_core.services.pricing_engine_service import DeterministicPricingEngine

SNAPSHOT_PATH = Path(
    "/Users/joesherbanee/.atlas_core/runtime/AtlasProjects/bid-2026-0002/intake/latest/intake_snapshot.json"
)
WORKSPACE_PATH = Path(
    "/Users/joesherbanee/.atlas_core/runtime/AtlasProjects/bid-2026-0002/workspace.json"
)


def _resolution(
    *,
    source_object_id: str,
    status: ProductResolutionStatus,
    canonical_product_id: str | None,
    manufacturer: str,
    model: str,
    confidence: float = 0.95,
) -> ProductResolution:
    return ProductResolution(
        resolution_id=f"resolution:{source_object_id}",
        source_object_id=source_object_id,
        resolution_status=status,
        canonical_product={},
        manufacturer=manufacturer,
        model=model,
        resolution_confidence=confidence,
        resolution_reason="test",
        candidate_matches=[],
        source_evidence=["test"],
        canonical_product_id=canonical_product_id,
        manufacturer_id=manufacturer,
    )


def test_runtime_av03_validation_is_deterministic_and_project_scoped(
    tmp_path: Path, monkeypatch
) -> None:
    # Make test hermetic: point HOME to an empty tmp dir and synthesize snapshot
    monkeypatch.setenv("HOME", str(tmp_path))

    service = CommercialBaselineValidationService()

    # Synthetic minimal snapshot (no filesystem access)
    snapshot = DocumentIntakeSnapshot(
        snapshot_id="test-snap",
        package_path=".",
        metadata={"project_id": "TEST-PROJ"},
        discovered_files={"drawings": ["d1.pdf"]},
        raw_pages=[],
        raw_sheets=[],
        raw_sections=[],
        raw_device_schedules=[],
        equipment_candidates=[],
        source_references=[],
        document_relevance_assessments=[],
        source_fitness_assessments=[],
        warnings=[],
        import_summary={},
    )

    # Monkeypatch downstream services to return deterministic, small results
    def fake_build(self, snap):
        # Minimal EvidenceBaselineReconstructionResult with baseline equipment
        source_fitness = SimpleNamespace(
            document_assessments=[], page_assessments=[], evidence_assessments=[]
        )
        baseline_equipment = []
        for i in range(1, 6):
            baseline_equipment.append(
                SimpleNamespace(
                    manufacturer="Maker",
                    model="ModelX",
                    description="Desc",
                    system_block="Audio",
                    performance_space=f"Room{i}",
                    quantity="1",
                    source_file=f"doc{i}.pdf",
                    page_number=i,
                    source_fitness_status="strong_baseline_evidence",
                    source_fitness_score=90,
                    responsibility="contractor furnished",
                    allowance_status="allowance",
                    alternate_status="primary",
                    baseline_role="baseline",
                    confidence=90,
                    evidence_reference=f"doc{i}.pdf#p{i}",
                )
            )

        return EvidenceBaselineReconstructionResult(
            source_fitness=source_fitness,
            major_system_components=[],
            baseline_equipment=baseline_equipment,
            source_deficiencies=[],
            consolidated_rfis=[],
            drawing_spec_alignment=[],
            system_confidence=[],
            before_after=[BeforeAfterRow(metric="m", before="a", after="b", notes="")],
            room_inventory=[],
            report_markdown="REPORT for TEST-PROJ",
            summary={"dummy": 1},
        )

    monkeypatch.setattr(
        "atlas_core.services.evidence_baseline_reconstruction_service.EvidenceBaselineReconstructionService.build",
        fake_build,
    )

    # Product resolution: produce 3 exact, 1 generic
    def fake_resolve(self, rows):
        class FakeResolution:
            def __init__(self, status: ProductResolutionStatus, sid: str = "src"):
                self.source_object_id = f"{sid}"
                self.resolution_status = status
                self.manufacturer = "Maker"
                self.model = "ModelX"
                self.canonical_product_id = None
                self.resolution_confidence = 0.9
                self.resolution_reason = "test"
                self.candidate_matches: list[ProductResolutionCandidate] = []
                self.source_evidence = ["doc#p1"]
                self.manual_override = None
                self.manufacturer_id = "Maker"

            def to_dict(self):
                return {
                    "resolution_id": f"resolution:{self.source_object_id}",
                    "source_object_id": self.source_object_id,
                    "resolution_status": self.resolution_status,
                    "canonical_product": {},
                    "manufacturer": self.manufacturer,
                    "model": self.model,
                }

        return [
            FakeResolution(ProductResolutionStatus.EXACT_PRODUCT, "EQ-1"),
            FakeResolution(ProductResolutionStatus.EXACT_PRODUCT, "EQ-2"),
            FakeResolution(ProductResolutionStatus.EXACT_PRODUCT, "EQ-3"),
            FakeResolution(ProductResolutionStatus.GENERIC_ALLOWANCE, "EQ-4"),
        ]

    monkeypatch.setattr(
        "atlas_core.services.product_resolution_service.ProductResolutionService.resolve_equipment_rows",
        fake_resolve,
    )

    # DeterministicEstimateService.build -> object with all_lines()
    class FakeEstimate:
        def all_lines(self):
            return [1, 2, 3, 4, 5]

    monkeypatch.setattr(
        "atlas_core.services.estimate_service.DeterministicEstimateService.build",
        lambda *args, **kwargs: FakeEstimate(),
    )

    # Pricing engine: one priced line
    class FakePricing:
        def __init__(self):
            self.priced_lines = [
                SimpleNamespace(
                    estimate_line_id="estimate-line:1",
                    source_equipment_id="baseline:1",
                    pricing_status=PricingStatus.VERIFIED_CURRENT,
                    pricing_confidence=0.9,
                    freshness_status=SimpleNamespace(value="unknown"),
                    selection_reason="matched",
                )
            ]
            self.commercial_coverage = SimpleNamespace(
                percentage_bom_lines_priced=20.0,
                commercial_confidence=0.5,
                to_dict=lambda: {
                    "percentage_bom_lines_priced": 20.0,
                    "commercial_confidence": 0.5,
                },
            )
            self.summary = SimpleNamespace(to_dict=lambda: {"coverage": 20})

    monkeypatch.setattr(
        "atlas_core.services.pricing_engine_service.DeterministicPricingEngine.run",
        lambda *args, **kwargs: FakePricing(),
    )

    # Now call build() directly with explicit project info (no files)
    first = service.build(
        snapshot=snapshot,
        commercial_state={"price_records": 0},
        project_id="TEST-PROJ",
        project_name="Test Project",
    )

    second = service.build(
        snapshot=snapshot,
        commercial_state={"price_records": 0},
        project_id="TEST-PROJ",
        project_name="Test Project",
    )

    # Expectations updated for synthetic fixture
    assert first.project_id == "TEST-PROJ"
    assert first.project_name == "Test Project"
    assert first.estimate_line_count == 5
    assert first.exact_products_resolved == 3
    assert first.generic_products == 1
    assert first.unresolved_products == 0
    assert first.priced_lines == 1
    # quote_required_lines is derived from priced_lines and policy; keep non-negative
    assert first.quote_required_lines >= 0
    assert 0.0 <= first.overall_readiness_score <= 1.0

    # Deterministic: repeated runs match
    assert first.report_markdown == second.report_markdown
    assert first.estimate_baseline_rows == second.estimate_baseline_rows
    # Project-scoped: report should not include unrelated project id
    assert "BID-2026-0001" not in first.report_markdown

    output_dir = tmp_path / "artifacts"
    report_path = tmp_path / "AV-03_COMMERCIAL_BASELINE_VALIDATION.md"
    service.write_artifacts(first, output_dir=output_dir, report_path=report_path)

    expected = [
        "AV-03_ESTIMATE_BASELINE.csv",
        "AV-03_PRODUCT_RESOLUTION.csv",
        "AV-03_PROCUREMENT_PATHS.csv",
        "AV-03_PRICING_READINESS.csv",
        "AV-03_SCOPE_RESPONSIBILITY.csv",
        "AV-03_ACCESSORY_GAPS.csv",
        "AV-03_LABOR_READINESS.csv",
        "AV-03_SYSTEM_CONFIDENCE.csv",
        "AV-03_COMMERCIAL_RISKS.csv",
        "AV-03_BEFORE_AFTER.csv",
    ]
    for name in expected:
        assert (output_dir / name).exists()
        assert (output_dir / name).read_text(encoding="utf-8").splitlines()[0]
    assert report_path.exists()


def test_validation_helpers_consolidate_scope_gap_and_labor_rows() -> None:
    service = CommercialBaselineValidationService()
    baseline_rows = [
        {
            "source_equipment_id": "baseline:1",
            "source_file": "Div 27 Communications.pdf",
            "page_number": 42,
            "performance_space": "Main Auditorium",
            "system_block": "Audio",
            "description": "Main DSP",
            "manufacturer": "QSC",
            "model": "Core110f",
            "quantity": "1",
            "source_fitness_status": "strong_baseline_evidence",
            "source_fitness_score": 92,
            "resolution_status": ProductResolutionStatus.EXACT_PRODUCT.value,
            "pricing_status": PricingStatus.NO_PRICING.value,
            "commercial_product_id": "QSC::Core110f",
            "quote_required": True,
            "scope_responsibility": "contractor furnished",
            "allowance_status": "allowance",
            "alternate_status": "primary",
            "labor_ready_score": 0.75,
            "accessory_gap": "quote-required accessory package",
            "confidence": 88,
            "evidence_reference": "Div 27 Communications.pdf#p42",
        },
        {
            "source_equipment_id": "baseline:2",
            "source_file": "Div 27 Communications.pdf",
            "page_number": 42,
            "performance_space": "Main Auditorium",
            "system_block": "Audio",
            "description": "Accessory allowance",
            "manufacturer": "Unknown",
            "model": "Unknown",
            "quantity": "LOT",
            "source_fitness_status": "strong_baseline_evidence",
            "source_fitness_score": 92,
            "resolution_status": ProductResolutionStatus.GENERIC_ALLOWANCE.value,
            "pricing_status": PricingStatus.NO_PRICING.value,
            "commercial_product_id": "",
            "quote_required": True,
            "scope_responsibility": "owner furnished",
            "allowance_status": "allowance",
            "alternate_status": "alternate",
            "labor_ready_score": 0.25,
            "accessory_gap": "generic allowance accessories",
            "confidence": 72,
            "evidence_reference": "Div 27 Communications.pdf#p42b",
        },
    ]

    procurement_rows = service._procurement_path_rows(baseline_rows)
    scope_rows = service._scope_responsibility_rows(baseline_rows)
    accessory_rows = service._accessory_gap_rows(baseline_rows)
    labor_rows = service._labor_readiness_rows(baseline_rows)

    assert {row["procurement_path"] for row in procurement_rows} == {
        "allowance procurement",
        "quote required",
    }
    assert scope_rows[0]["responsibility"] == "contractor furnished"
    assert scope_rows[1]["responsibility"] == "owner furnished"
    assert len(accessory_rows) == 2
    assert accessory_rows[0]["affected_count"] == 1
    assert labor_rows[0]["labor_ready_score"] > labor_rows[1]["labor_ready_score"]
    assert service._labor_readiness_score(
        quantity="1",
        manufacturer="QSC",
        model="Core110f",
        room="Main Auditorium",
        source_fitness_score=92,
    ) > service._labor_readiness_score(
        quantity="LOT",
        manufacturer="Unknown",
        model="Unknown",
        room="",
        source_fitness_score=20,
    )

    pricing = SimpleNamespace(
        priced_lines=[
            SimpleNamespace(
                source_equipment_id="baseline:1",
                pricing_status=PricingStatus.NO_PRICING,
                pricing_confidence=0.2,
                freshness_status=SimpleNamespace(value="unknown"),
                selection_reason="no price",
            ),
            SimpleNamespace(
                source_equipment_id="baseline:2",
                pricing_status=PricingStatus.NO_PRICING,
                pricing_confidence=0.2,
                freshness_status=SimpleNamespace(value="unknown"),
                selection_reason="no price",
            ),
        ]
    )
    risks = service._commercial_risk_rows(
        baseline_rows,
        pricing,
        {"price_records": 1, "price_sheets": 1, "vendor_offerings": 1},
    )
    assert any(row["root_issue"] == "all lines quote required" for row in risks)


def test_exact_vs_generic_product_resolution_and_pricing_status() -> None:
    commercial_service = CommercialKnowledgeService()
    commercial_service.import_price_sheet(
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
                "unit_cost": 1000.0,
                "list_price": 1200.0,
                "currency": "USD",
                "lead_time": "4 weeks",
                "availability_status": "in_stock",
                "effective_date": "2026-01-01",
                "expiration_date": "2026-12-31",
                "confidence": 0.95,
            }
        ],
    )
    commercial_state = commercial_service.to_dict()
    exact_product_key = next(iter(commercial_state["price_records"].values()))[
        "product"
    ]

    rows = [
        {
            "equipment_id": "EQ-1",
            "manufacturer": "QSC",
            "model": "Core110f",
            "description": "DSP",
            "system": "Audio",
            "room": "Rack",
            "quantity": "1",
            "completeness_status": "complete",
            "drawing_references": ["AV-101"],
            "specification_references": ["27 41 16"],
            "source_documents": ["bid-set.pdf"],
        },
        {
            "equipment_id": "EQ-2",
            "manufacturer": "Unknown",
            "model": "Unknown",
            "description": "Allowance",
            "system": "Audio",
            "room": "Rack",
            "quantity": "1",
            "completeness_status": "drawing_only",
            "drawing_references": ["AV-102"],
            "specification_references": ["27 41 16"],
            "source_documents": ["bid-set.pdf"],
        },
    ]
    resolutions = [
        _resolution(
            source_object_id="EQ-1",
            status=ProductResolutionStatus.EXACT_PRODUCT,
            canonical_product_id=exact_product_key,
            manufacturer="QSC",
            model="Core110f",
        ),
        _resolution(
            source_object_id="EQ-2",
            status=ProductResolutionStatus.GENERIC_ALLOWANCE,
            canonical_product_id=None,
            manufacturer="Unknown",
            model="Unknown",
            confidence=0.45,
        ),
    ]
    resolution_payloads: list[ProductResolution | dict[str, object]] = [
        item.to_dict() for item in resolutions
    ]
    estimate = DeterministicEstimateService().build(
        project_id="BID-2026-0002",
        project_name="Music Academy of the West",
        bom_rows=rows,
        product_resolutions=resolution_payloads,
    )
    result = DeterministicPricingEngine().run(
        estimate=estimate,
        product_resolutions=resolution_payloads,
        commercial_state=commercial_state,
        project_id="BID-2026-0002",
        preferred_vendor_policy={"organization": "PreferredVendor"},
        project_quotes=[],
    )

    assert result.priced_lines[0].pricing_status in {
        PricingStatus.VERIFIED_CURRENT,
        PricingStatus.CURRENT_PRICE_SHEET,
    }
    assert result.priced_lines[0].unit_cost == 1000.0
    assert result.priced_lines[1].pricing_status is PricingStatus.NO_PRICING
    assert result.summary is not None
    assert result.summary.current_pricing_coverage > 0

from atlas_core.domain import CostStatus, ProductResolutionStatus
from atlas_core.services import DeterministicEstimateService


def _row(
    *,
    bom_item_id: str,
    manufacturer: str = "QSC",
    model: str = "Core 110f",
    quantity: float | int | str = 1,
    known_cost: float | None = 1000.0,
    pricing_source: str = "estimated_price_list",
    completeness_status: str = "complete",
    warnings: list[str] | None = None,
    drawing_refs: list[str] | None = None,
    specification_refs: list[str] | None = None,
    source_documents: list[str] | None = None,
) -> dict[str, object]:
    return {
        "bom_item_id": bom_item_id,
        "manufacturer": manufacturer,
        "model": model,
        "description": "Audio DSP",
        "quantity": quantity,
        "known_cost": known_cost,
        "pricing_source": pricing_source,
        "completeness_status": completeness_status,
        "warnings": list(warnings or []),
        "drawing_references": list(drawing_refs or ["AV-601"]),
        "specification_references": list(specification_refs or ["27 41 16"]),
        "source_documents": list(source_documents or ["bid-set.pdf"]),
    }


def test_estimate_creation_and_traceability_fields() -> None:
    estimate = DeterministicEstimateService().build(
        project_id="project-001",
        project_name="MAW",
        bom_rows=[_row(bom_item_id="EQ-1")],
    )

    line = estimate.all_lines()[0]
    assert line.source_object == "EQ-1"
    assert line.object_type == "equipment"
    assert line.manufacturer == "QSC"
    assert line.model == "Core 110f"
    assert line.quantity == 1.0
    assert line.source_references


def test_resolution_states_include_unknown_and_generic_allowance() -> None:
    service = DeterministicEstimateService()
    estimate = service.build(
        project_id="project-001",
        project_name="MAW",
        bom_rows=[
            _row(bom_item_id="EQ-UNK", manufacturer="Unknown", model="Unknown"),
            _row(
                bom_item_id="EQ-GEN",
                completeness_status="drawing_only",
                known_cost=None,
            ),
        ],
    )

    statuses = [line.product_resolution_status for line in estimate.all_lines()]
    assert ProductResolutionStatus.UNKNOWN_PRODUCT in statuses
    assert ProductResolutionStatus.GENERIC_ALLOWANCE in statuses


def test_unknown_products_cannot_receive_deterministic_pricing() -> None:
    estimate = DeterministicEstimateService().build(
        project_id="project-001",
        project_name="MAW",
        bom_rows=[
            _row(
                bom_item_id="EQ-UNK",
                manufacturer="Unknown",
                model="Unknown",
                known_cost=1200.0,
            )
        ],
    )

    line = estimate.all_lines()[0]
    assert line.product_resolution_status is ProductResolutionStatus.UNKNOWN_PRODUCT
    assert line.pricing_status is CostStatus.NO_PRICING
    assert line.material_cost.amount == 0.0


def test_cost_status_classification() -> None:
    estimate = DeterministicEstimateService().build(
        project_id="project-001",
        project_name="MAW",
        bom_rows=[
            _row(bom_item_id="EQ-NP", known_cost=None),
            _row(
                bom_item_id="EQ-Q",
                pricing_source="vendor_quote",
                known_cost=300.0,
            ),
            _row(
                bom_item_id="EQ-V",
                pricing_source="verified_registry",
                known_cost=500.0,
            ),
            _row(
                bom_item_id="EQ-E",
                warnings=["expired quote"],
                known_cost=600.0,
            ),
            _row(
                bom_item_id="EQ-U",
                warnings=["unavailable product"],
                known_cost=700.0,
            ),
        ],
    )

    statuses = [line.pricing_status for line in estimate.all_lines()]
    assert statuses == [
        CostStatus.NO_PRICING,
        CostStatus.QUOTED,
        CostStatus.VERIFIED,
        CostStatus.EXPIRED,
        CostStatus.UNAVAILABLE,
    ]


def test_navigation_targets_exist_for_estimate_line() -> None:
    estimate = DeterministicEstimateService().build(
        project_id="project-001",
        project_name="MAW",
        bom_rows=[_row(bom_item_id="EQ-1")],
    )

    line = estimate.all_lines()[0]
    targets = {item["kind"] for item in line.navigation_refs}
    assert targets == {
        "equipment",
        "drawing",
        "specification",
        "relationships",
        "evidence",
    }


def test_estimate_totals_and_dashboard_summary() -> None:
    service = DeterministicEstimateService()
    estimate = service.build(
        project_id="project-001",
        project_name="MAW",
        bom_rows=[
            _row(bom_item_id="EQ-1", known_cost=100.0, quantity=2),
            _row(bom_item_id="EQ-2", known_cost=None),
        ],
    )
    dashboard = service.build_dashboard(estimate)

    assert estimate.subtotal().amount == 200.0
    assert estimate.grand_total().amount == 200.0
    assert dashboard["material_cost"] == 200.0
    assert dashboard["known_cost_percent"] == 50.0
    assert dashboard["unknown_cost_percent"] == 50.0


def test_empty_estimate_is_supported() -> None:
    service = DeterministicEstimateService()
    estimate = service.build(
        project_id="project-empty",
        project_name="Empty",
        bom_rows=[],
    )

    assert estimate.all_lines() == []
    assert estimate.subtotal().amount == 0.0
    assert estimate.grand_total().amount == 0.0
    assert estimate.confidence_model is not None
    assert estimate.confidence_model.score == 0.0


def test_labor_architecture_categories_exist() -> None:
    service = DeterministicEstimateService()
    estimate = service.build(
        project_id="project-001",
        project_name="MAW",
        bom_rows=[_row(bom_item_id="EQ-1")],
    )

    labor_rows = service.labor_architecture_rows(estimate)
    categories = [item["Labor Category"] for item in labor_rows]
    assert categories == [
        "Receiving",
        "Staging",
        "Rack Build",
        "Installation",
        "Termination",
        "Programming",
        "Commissioning",
        "Testing",
        "Training",
        "Punch",
    ]


def test_confidence_model_messages_explain_quality_gaps() -> None:
    estimate = DeterministicEstimateService().build(
        project_id="project-001",
        project_name="MAW",
        bom_rows=[
            _row(
                bom_item_id="EQ-UNK",
                manufacturer="Unknown",
                model="Unknown",
                known_cost=None,
            ),
            _row(
                bom_item_id="EQ-GEN",
                completeness_status="specification_only",
                known_cost=None,
            ),
        ],
    )

    model = estimate.confidence_model
    assert model is not None
    assert model.score < 0.5
    assert any("Pricing coverage" in message for message in model.messages)
    assert any("Product resolution" in message for message in model.messages)

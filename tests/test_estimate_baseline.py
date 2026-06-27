import pytest

from atlas_core.domain import EstimateBaseline, EstimateBaselineStatus
from atlas_core.services import EquipmentMatrixRow


def make_row(
    budget_cost: float | str | None = 100.0,
    sell_price: float | str | None = 150.0,
) -> EquipmentMatrixRow:
    return EquipmentMatrixRow(
        equipment_id="eq-001",
        description="Display",
        budget_cost=budget_cost,
        sell_price=sell_price,
    )


def test_creating_valid_baseline():
    baseline = EstimateBaseline(
        baseline_id=" baseline-001 ",
        project_id=" project-001 ",
        name=" Submitted Estimate ",
        rows=[make_row()],
        created_by=" Estimator ",
    )

    assert baseline.baseline_id == "baseline-001"
    assert baseline.project_id == "project-001"
    assert baseline.name == "Submitted Estimate"
    assert baseline.rows == [make_row()]
    assert baseline.status is EstimateBaselineStatus.DRAFT
    assert baseline.version == 1
    assert isinstance(baseline.created_at, str)
    assert baseline.created_by == "Estimator"
    assert baseline.notes == []


def test_rejecting_blank_name():
    with pytest.raises(ValueError, match="name cannot be blank"):
        EstimateBaseline(
            baseline_id="baseline-001",
            project_id="project-001",
            name=" ",
        )


def test_accepting_string_status():
    baseline = EstimateBaseline(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        status="submitted",
    )

    assert baseline.status is EstimateBaselineStatus.SUBMITTED


def test_rejecting_invalid_version():
    with pytest.raises(ValueError, match="version must be greater than 0"):
        EstimateBaseline(
            baseline_id="baseline-001",
            project_id="project-001",
            name="Submitted Estimate",
            version=0,
        )


def test_adding_notes():
    baseline = EstimateBaseline(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        notes=[" Confirm alternates. "],
    )

    baseline.add_note(" Owner approved scope. ")

    assert baseline.notes == [
        "Confirm alternates.",
        "Owner approved scope.",
    ]


def test_rejecting_blank_notes():
    baseline = EstimateBaseline(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
    )

    with pytest.raises(ValueError, match="note cannot be blank"):
        baseline.add_note(" ")


def test_lifecycle_status_methods():
    baseline = EstimateBaseline(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
    )

    baseline.submit()
    assert baseline.status is EstimateBaselineStatus.SUBMITTED

    baseline.award()
    assert baseline.status is EstimateBaselineStatus.AWARDED

    baseline.supersede()
    assert baseline.status is EstimateBaselineStatus.SUPERSEDED

    baseline.archive()
    assert baseline.status is EstimateBaselineStatus.ARCHIVED


def test_total_budget_cost():
    baseline = EstimateBaseline(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        rows=[
            make_row(budget_cost=100.0),
            make_row(budget_cost=50.5),
            make_row(budget_cost=None),
        ],
    )

    assert baseline.total_budget_cost() == 150.5


def test_total_sell_price():
    baseline = EstimateBaseline(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        rows=[
            make_row(sell_price=200.0),
            make_row(sell_price="75.25"),
            make_row(sell_price=None),
        ],
    )

    assert baseline.total_sell_price() == 275.25


def test_gross_margin():
    baseline = EstimateBaseline(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        rows=[
            make_row(budget_cost=100.0, sell_price=200.0),
            make_row(budget_cost=50.0, sell_price=100.0),
        ],
    )

    assert baseline.gross_margin() == 0.5


def test_gross_margin_returns_none_when_sell_price_is_zero():
    baseline = EstimateBaseline(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        rows=[make_row(budget_cost=100.0, sell_price=0.0)],
    )

    assert baseline.gross_margin() is None


def test_to_dict_output():
    row = make_row(budget_cost=100.0, sell_price=150.0)
    baseline = EstimateBaseline(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        rows=[row],
        status=EstimateBaselineStatus.SUBMITTED,
        version=2,
        created_at="2026-06-27T12:00:00",
        created_by="Estimator",
        notes=["Confirm alternates."],
    )

    assert baseline.to_dict() == {
        "baseline_id": "baseline-001",
        "project_id": "project-001",
        "name": "Submitted Estimate",
        "rows": [row.to_dict()],
        "status": "submitted",
        "version": 2,
        "created_at": "2026-06-27T12:00:00",
        "created_by": "Estimator",
        "notes": ["Confirm alternates."],
    }

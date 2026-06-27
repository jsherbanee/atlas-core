from atlas_core.domain import EstimateBaselineStatus
from atlas_core.services import (
    BaselineService,
    EquipmentMatrixRow,
    EstimateWorkflowResult,
)


def make_workflow_result(
    placeholder_equipment_count: int = 0,
) -> EstimateWorkflowResult:
    return EstimateWorkflowResult(
        rows=[
            EquipmentMatrixRow(
                equipment_id="eq-001",
                description="Display",
                budget_cost=100.0,
                sell_price=150.0,
            )
        ],
        resolutions=[],
        placeholder_equipment_count=placeholder_equipment_count,
    )


def test_creates_baseline_from_workflow_result():
    baseline = BaselineService().create_baseline_from_workflow(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        workflow_result=make_workflow_result(),
    )

    assert baseline.baseline_id == "baseline-001"
    assert baseline.project_id == "project-001"
    assert baseline.name == "Submitted Estimate"
    assert baseline.status is EstimateBaselineStatus.DRAFT


def test_carries_rows():
    workflow_result = make_workflow_result()

    baseline = BaselineService().create_baseline_from_workflow(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        workflow_result=workflow_result,
    )

    assert baseline.rows == workflow_result.rows


def test_sets_created_by():
    baseline = BaselineService().create_baseline_from_workflow(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        workflow_result=make_workflow_result(),
        created_by="Estimator",
    )

    assert baseline.created_by == "Estimator"


def test_award_true_sets_status_to_awarded():
    baseline = BaselineService().create_baseline_from_workflow(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Awarded Estimate",
        workflow_result=make_workflow_result(),
        award=True,
    )

    assert baseline.status is EstimateBaselineStatus.AWARDED


def test_adds_baseline_created_note():
    baseline = BaselineService().create_baseline_from_workflow(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        workflow_result=make_workflow_result(),
    )

    assert baseline.notes == ["Baseline created from estimate workflow."]


def test_adds_placeholder_note_when_placeholders_exist():
    baseline = BaselineService().create_baseline_from_workflow(
        baseline_id="baseline-001",
        project_id="project-001",
        name="Submitted Estimate",
        workflow_result=make_workflow_result(placeholder_equipment_count=1),
    )

    assert baseline.notes == [
        "Baseline created from estimate workflow.",
        "Baseline includes placeholder equipment requiring review.",
    ]

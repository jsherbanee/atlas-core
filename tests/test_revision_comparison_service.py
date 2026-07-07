from atlas_core.domain import (
    AssumptionSeverity,
    BidPackageReview,
    EngineeringAssumption,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    LaborEstimate,
    LaborEstimateCategory,
    RFICandidate,
    RFICandidateCategory,
    RFICandidateSeverity,
    RevisionChangeRecord,
    RevisionChangeSeverity,
    RevisionChangeType,
    SystemCategory,
)
from atlas_core.services.revision_comparison_engine import RevisionComparisonEngine
from atlas_core.services.revision_comparison_service import RevisionComparisonService


def make_review(
    review_id: str,
    equipment: list[Equipment] | None = None,
    assumptions: list[EngineeringAssumption] | None = None,
    rfi_candidates: list[RFICandidate] | None = None,
    labor_estimate: LaborEstimate | None = None,
) -> BidPackageReview:
    return BidPackageReview(
        review_id=review_id,
        project_id="project-001",
        name=f"Review {review_id}",
        systems=[
            IntegratedSystem(
                system_id="sys-001",
                name="Performance Audio",
                category=SystemCategory.AUDIO,
            )
        ],
        equipment=list(equipment or []),
        engineering_assumptions=list(assumptions or []),
        rfi_candidates=list(rfi_candidates or []),
        labor_estimate=labor_estimate,
    )


def test_detects_item_added() -> None:
    baseline = make_review(review_id="baseline")
    comparison = make_review(
        review_id="comparison",
        equipment=[
            Equipment(
                equipment_id="eq-001",
                description="Speaker",
                category=EquipmentCategory.SPEAKER,
                quantity=2,
            )
        ],
    )

    result = RevisionComparisonService().build(baseline, comparison)

    assert "eq-001" in result.added_items
    assert any(
        change.change_type is RevisionChangeType.ITEM_ADDED for change in result.changes
    )


def test_detects_item_removed() -> None:
    baseline = make_review(
        review_id="baseline",
        equipment=[
            Equipment(
                equipment_id="eq-001",
                description="Speaker",
                category=EquipmentCategory.SPEAKER,
            )
        ],
    )
    comparison = make_review(review_id="comparison")

    result = RevisionComparisonService().build(baseline, comparison)

    assert "eq-001" in result.removed_items
    assert any(
        change.change_type is RevisionChangeType.ITEM_REMOVED
        for change in result.changes
    )


def test_detects_quantity_changed() -> None:
    baseline = make_review(
        review_id="baseline",
        equipment=[
            Equipment(
                equipment_id="eq-qty",
                description="Display",
                category=EquipmentCategory.DISPLAY,
                quantity=1,
            )
        ],
    )
    comparison = make_review(
        review_id="comparison",
        equipment=[
            Equipment(
                equipment_id="eq-qty",
                description="Display",
                category=EquipmentCategory.DISPLAY,
                quantity=3,
            )
        ],
    )

    result = RevisionComparisonService().build(baseline, comparison)

    assert result.quantity_changes
    assert any(
        change.change_type is RevisionChangeType.QUANTITY_CHANGED
        for change in result.changes
    )


def test_detects_description_model_spec_modifications() -> None:
    baseline = make_review(
        review_id="baseline",
        equipment=[
            Equipment(
                equipment_id="eq-mod",
                description="Control processor",
                category=EquipmentCategory.CONTROL_PROCESSOR,
                manufacturer="QSC",
                model="Core Nano",
                specification_reference="27 41 26",
            )
        ],
    )
    comparison = make_review(
        review_id="comparison",
        equipment=[
            Equipment(
                equipment_id="eq-mod",
                description="Control processor rev A",
                category=EquipmentCategory.CONTROL_PROCESSOR,
                manufacturer="QSC",
                model="Core Nano Plus",
                specification_reference="27 41 26A",
            )
        ],
    )

    result = RevisionComparisonService().build(baseline, comparison)

    assert "eq-mod" in result.modified_items
    assert any(
        change.change_type is RevisionChangeType.ITEM_MODIFIED
        for change in result.changes
    )
    assert any(
        change.change_type is RevisionChangeType.SPECIFICATION_CHANGED
        for change in result.changes
    )


def test_detects_scope_responsibility_changed() -> None:
    baseline = make_review(
        review_id="baseline",
        equipment=[
            Equipment(
                equipment_id="eq-scope",
                description="Display system",
                category=EquipmentCategory.DISPLAY,
            )
        ],
    )
    comparison = make_review(
        review_id="comparison",
        equipment=[
            Equipment(
                equipment_id="eq-scope",
                description="Display system",
                category=EquipmentCategory.DISPLAY,
                assumptions=["OFE mount by others"],
            )
        ],
    )

    result = RevisionComparisonService().build(baseline, comparison)

    assert result.scope_changes
    assert any(
        change.change_type is RevisionChangeType.SCOPE_RESPONSIBILITY_CHANGED
        for change in result.changes
    )


def test_flags_labor_impact_for_quantity_change() -> None:
    baseline = make_review(
        review_id="baseline",
        equipment=[
            Equipment(
                equipment_id="eq-labor",
                description="Speaker",
                category=EquipmentCategory.SPEAKER,
                quantity=1,
            )
        ],
    )
    comparison = make_review(
        review_id="comparison",
        equipment=[
            Equipment(
                equipment_id="eq-labor",
                description="Speaker",
                category=EquipmentCategory.SPEAKER,
                quantity=2,
            )
        ],
    )

    result = RevisionComparisonService().build(baseline, comparison)

    assert result.labor_impact_flags


def test_flags_rfi_impact_for_scope_change() -> None:
    baseline = make_review(
        review_id="baseline",
        equipment=[
            Equipment(
                equipment_id="eq-rfi",
                description="Projector",
                category=EquipmentCategory.PROJECTOR,
            )
        ],
    )
    comparison = make_review(
        review_id="comparison",
        equipment=[
            Equipment(
                equipment_id="eq-rfi",
                description="Projector by others",
                category=EquipmentCategory.PROJECTOR,
            )
        ],
    )

    result = RevisionComparisonService().build(baseline, comparison)

    assert result.rfi_impacts


def test_duplicate_suppression_prefers_higher_severity() -> None:
    engine = RevisionComparisonEngine()
    duplicate_low = RevisionChangeRecord(
        change_id="chg-1",
        change_type=RevisionChangeType.QUANTITY_CHANGED,
        title="Equipment quantity changed: eq-001",
        description="Quantity changed.",
        severity=RevisionChangeSeverity.MEDIUM,
        confidence=0.7,
        affected_items=["eq-001"],
        detected_condition="equipment_quantity_changed",
        estimating_impact="Affects estimate.",
        recommended_action="Recheck quantities.",
    )
    duplicate_high = RevisionChangeRecord(
        change_id="chg-2",
        change_type=RevisionChangeType.QUANTITY_CHANGED,
        title="Equipment quantity changed: eq-001",
        description="Quantity changed.",
        severity=RevisionChangeSeverity.HIGH,
        confidence=0.8,
        affected_items=["eq-001"],
        detected_condition="equipment_quantity_changed",
        estimating_impact="Affects estimate.",
        recommended_action="Recheck quantities.",
    )

    deduped = engine._suppress_duplicates([duplicate_low, duplicate_high])

    assert len(deduped) == 1
    assert deduped[0].severity is RevisionChangeSeverity.HIGH


def test_serialization_output_contains_expected_fields() -> None:
    baseline = make_review(
        review_id="baseline",
        equipment=[
            Equipment(
                equipment_id="eq-ser",
                description="Display",
                category=EquipmentCategory.DISPLAY,
                quantity=1,
            )
        ],
        assumptions=[
            EngineeringAssumption(
                assumption_id="assume-001",
                category="scope",
                description="Baseline assumption",
                severity=AssumptionSeverity.REVIEW,
                related_equipment="eq-ser",
            )
        ],
        rfi_candidates=[
            RFICandidate(
                candidate_id="rfi-base-001",
                project_id="project-001",
                title="Baseline ambiguity",
                description="Need clarification",
                category=RFICandidateCategory.SCOPE_AMBIGUITY,
                severity=RFICandidateSeverity.MEDIUM,
                confidence=0.85,
                detected_condition="scope_responsibility_ambiguity",
                recommended_action="Clarify scope ownership.",
            )
        ],
        labor_estimate=LaborEstimate(
            project_id="project-001",
            total_labor_hours_low=10,
            total_labor_hours_expected=12,
            total_labor_hours_high=14,
            labor_categories=[
                LaborEstimateCategory(
                    category_id="field_installation:general",
                    category_name="field_installation",
                    system_area="general",
                    quantity_basis="quantity_sum=1",
                    hours_low=4,
                    hours_expected=5,
                    hours_high=6,
                    confidence=0.8,
                    calculation_method="test",
                )
            ],
        ),
    )
    comparison = make_review(
        review_id="comparison",
        equipment=[
            Equipment(
                equipment_id="eq-ser",
                description="Display revised",
                category=EquipmentCategory.DISPLAY,
                quantity=2,
            )
        ],
        labor_estimate=LaborEstimate(
            project_id="project-001",
            total_labor_hours_low=12,
            total_labor_hours_expected=15,
            total_labor_hours_high=18,
        ),
    )

    result = RevisionComparisonService().build(
        baseline,
        comparison,
        baseline_revision_id="rev-a",
        comparison_revision_id="rev-b",
    )
    payload = result.to_dict()

    assert payload["project_id"] == "project-001"
    assert payload["baseline_revision_id"] == "rev-a"
    assert payload["comparison_revision_id"] == "rev-b"
    assert "summary" in payload
    assert "changes" in payload
    assert "labor_impact_flags" in payload
    assert "rfi_impacts" in payload
    assert "created_by_engine_version" in payload

from atlas_core.domain import (
    BidPackageReview,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    LaborEstimate,
    LaborEstimateCategory,
    RFICandidate,
    RFICandidateCategory,
    RFICandidateSeverity,
    SystemCategory,
)
from atlas_core.services.labor_service import LaborService


def make_review(
    equipment: list[Equipment] | None = None,
    systems: list[IntegratedSystem] | None = None,
    rfi_candidates: list[RFICandidate] | None = None,
) -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Labor Review",
        equipment=list(equipment or []),
        systems=list(systems or []),
        rfi_candidates=list(rfi_candidates or []),
        confidence=0.85,
    )


def test_builds_basic_labor_estimate_from_resolved_equipment() -> None:
    review = make_review(
        systems=[
            IntegratedSystem(
                system_id="sys-audio",
                name="Performance Audio",
                category=SystemCategory.AUDIO,
            )
        ],
        equipment=[
            Equipment(
                equipment_id="eq-speaker-1",
                description="Main speaker",
                category=EquipmentCategory.SPEAKER,
                quantity=2,
                system_id="sys-audio",
                manufacturer="JBL",
                model="CBT 70J",
            )
        ],
    )

    estimate = LaborService().build(review)

    assert estimate.project_id == "project-001"
    assert estimate.total_labor_hours_expected > 0
    assert any(
        category.category_name == "field_installation"
        for category in estimate.labor_categories
    )


def test_category_level_rollup_groups_by_category_and_system_area() -> None:
    review = make_review(
        systems=[
            IntegratedSystem(
                system_id="sys-audio",
                name="Performance Audio",
                category=SystemCategory.AUDIO,
            )
        ],
        equipment=[
            Equipment(
                equipment_id="eq-speaker-1",
                description="Main speaker",
                category=EquipmentCategory.SPEAKER,
                quantity=1,
                system_id="sys-audio",
            ),
            Equipment(
                equipment_id="eq-speaker-2",
                description="Delay speaker",
                category=EquipmentCategory.SPEAKER,
                quantity=1,
                system_id="sys-audio",
            ),
        ],
    )

    estimate = LaborService().build(review)
    matching = [
        category
        for category in estimate.labor_categories
        if category.category_name == "field_installation"
        and category.system_area == "Performance Audio"
    ]

    assert len(matching) == 1
    assert matching[0].hours_expected > 0


def test_ranges_are_low_expected_high() -> None:
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display-1",
                description="Lobby display",
                category=EquipmentCategory.DISPLAY,
                quantity=3,
            )
        ]
    )

    estimate = LaborService().build(review)

    assert estimate.total_labor_hours_low <= estimate.total_labor_hours_expected
    assert estimate.total_labor_hours_expected <= estimate.total_labor_hours_high
    assert all(
        category.hours_low <= category.hours_expected <= category.hours_high
        for category in estimate.labor_categories
    )


def test_confidence_reduces_when_rfi_candidates_exist() -> None:
    review_without_rfi = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-control",
                description="Control processor",
                category=EquipmentCategory.CONTROL_PROCESSOR,
            )
        ]
    )
    review_with_rfi = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-control",
                description="Control processor",
                category=EquipmentCategory.CONTROL_PROCESSOR,
            )
        ],
        rfi_candidates=[
            RFICandidate(
                candidate_id="rfi-project-001-abcd1234",
                project_id="project-001",
                title="Scope responsibility language is ambiguous",
                description="Detected OFCI and by others language.",
                category=RFICandidateCategory.RESPONSIBILITY_GAP,
                severity=RFICandidateSeverity.HIGH,
                confidence=0.9,
                detected_condition="scope_responsibility_ambiguity",
                recommended_action="Issue scope matrix RFI candidate.",
            )
        ],
    )

    base_confidence = LaborService().build(review_without_rfi).confidence
    reduced_confidence = LaborService().build(review_with_rfi).confidence

    assert reduced_confidence < base_confidence


def test_risk_factors_and_warnings_include_quantity_conflict_or_scope_ambiguity() -> (
    None
):
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display-1",
                description="Display",
                category=EquipmentCategory.DISPLAY,
                quantity=2,
            )
        ],
        rfi_candidates=[
            RFICandidate(
                candidate_id="rfi-project-001-qty001",
                project_id="project-001",
                title="Quantity conflict identified",
                description="Schedule quantity differs from drawing quantity.",
                category=RFICandidateCategory.QUANTITY_CONFLICT,
                severity=RFICandidateSeverity.HIGH,
                confidence=0.92,
                detected_condition="quantity_conflict",
                recommended_action="Resolve source mismatch.",
            ),
            RFICandidate(
                candidate_id="rfi-project-001-scope001",
                project_id="project-001",
                title="Scope responsibility language is ambiguous",
                description="Detected OFE and by others references.",
                category=RFICandidateCategory.RESPONSIBILITY_GAP,
                severity=RFICandidateSeverity.MEDIUM,
                confidence=0.88,
                detected_condition="scope_responsibility_ambiguity",
                recommended_action="Clarify responsibility matrix.",
            ),
        ],
    )

    estimate = LaborService().build(review)

    assert any(
        "Quantity conflicts detected" in warning for warning in estimate.warnings
    )
    assert any(
        "Scope responsibility ambiguity detected" in warning
        for warning in estimate.warnings
    )
    assert any(
        "quantity_conflict" in category.risk_factors
        for category in estimate.labor_categories
    )
    assert any(
        "scope_responsibility_ambiguity" in category.risk_factors
        for category in estimate.labor_categories
    )


def test_preserves_existing_human_entered_labor_estimate() -> None:
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-speaker-1",
                description="Main speaker",
                category=EquipmentCategory.SPEAKER,
            )
        ]
    )
    manual_estimate = LaborEstimate(
        project_id="project-001",
        total_labor_hours_low=10.0,
        total_labor_hours_expected=12.0,
        total_labor_hours_high=15.0,
        labor_categories=[
            LaborEstimateCategory(
                category_id="field_installation:general",
                category_name="field_installation",
                system_area="general",
                quantity_basis="quantity_sum=1",
                hours_low=4.0,
                hours_expected=5.0,
                hours_high=6.0,
                confidence=0.8,
                calculation_method="manual_entry",
            )
        ],
        assumptions=["Manual estimator override."],
        exclusions=["None"],
        confidence=0.8,
    )
    review.labor_estimate = manual_estimate

    estimate = LaborService().build(review)

    assert estimate is manual_estimate

from atlas_core.domain import (
    AssumptionSeverity,
    BidPackageReview,
    DetailCallout,
    EngineeringAssumption,
    Equipment,
    EquipmentCategory,
)
from atlas_core.services.rfi_candidate_service import RFICandidateService
from atlas_core.services.scope_gap_service import ScopeGap


def make_review(
    scope_gaps: list[ScopeGap] | None = None,
    equipment: list[Equipment] | None = None,
    detail_callouts: list[DetailCallout] | None = None,
    engineering_assumptions: list[EngineeringAssumption] | None = None,
) -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        scope_gaps=list(scope_gaps or []),
        equipment=list(equipment or []),
        detail_callouts=list(detail_callouts or []),
        engineering_assumptions=list(engineering_assumptions or []),
    )


def test_high_scope_gap_creates_rfi():
    review = make_review(
        scope_gaps=[
            ScopeGap(
                gap_id="projector_missing_mount",
                target_id="eq-projector",
                message="Projector missing mount",
                severity="high",
            )
        ]
    )

    candidates = RFICandidateService().build(review)

    assert any(candidate.category == "scope_gap" for candidate in candidates)
    assert any(candidate.priority.value == "high" for candidate in candidates)


def test_projector_without_mount_detail_creates_rfi():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
                specification_reference="27 41 16",
            )
        ]
    )

    candidates = RFICandidateService().build(review)

    projector_rfi = next(
        candidate
        for candidate in candidates
        if candidate.rfi_id == "rfi_projector_mounting_eq-projector"
    )
    assert projector_rfi.priority.value == "high"
    assert projector_rfi.category == "mounting"


def test_display_without_mount_detail_creates_rfi():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display",
                description="Main display",
                category=EquipmentCategory.DISPLAY,
                specification_reference="27 41 16",
            )
        ]
    )

    candidates = RFICandidateService().build(review)

    display_rfi = next(
        candidate
        for candidate in candidates
        if candidate.rfi_id == "rfi_display_mounting_eq-display"
    )
    assert display_rfi.priority.value == "medium"
    assert display_rfi.category == "mounting"


def test_drapery_creates_rfi():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-drapery",
                description="Stage drapery",
                category=EquipmentCategory.DRAPERY,
                specification_reference="11 61 00",
            )
        ]
    )

    candidates = RFICandidateService().build(review)

    drapery_rfi = next(
        candidate
        for candidate in candidates
        if candidate.rfi_id == "rfi_drapery_equipment_eq-drapery"
    )
    assert drapery_rfi.priority.value == "high"
    assert drapery_rfi.category == "drapery"


def test_equipment_without_specification_reference_creates_low_priority_rfi():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display",
                description="Main display",
                category=EquipmentCategory.DISPLAY,
            )
        ]
    )

    candidates = RFICandidateService().build(review)

    spec_rfi = next(
        candidate
        for candidate in candidates
        if candidate.rfi_id == "rfi_specification_reference_eq-display"
    )
    assert spec_rfi.priority.value == "low"
    assert spec_rfi.category == "specification"


def test_risk_engineering_assumption_creates_high_priority_rfi():
    review = make_review(
        engineering_assumptions=[
            EngineeringAssumption(
                assumption_id="assumption-001",
                category="mounting",
                description="Structural support should be verified.",
                severity=AssumptionSeverity.RISK,
                related_equipment="eq-projector",
            )
        ]
    )

    candidates = RFICandidateService().build(review)

    assumption_rfi = next(
        candidate
        for candidate in candidates
        if candidate.rfi_id == "rfi_assumption_assumption-001"
    )
    assert assumption_rfi.priority.value == "high"
    assert assumption_rfi.category == "assumption"
    assert assumption_rfi.question == "Structural support should be verified."


def test_duplicates_are_avoided():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
                specification_reference="27 41 16",
            ),
            Equipment(
                equipment_id="eq-projector",
                description="Duplicate projector",
                category=EquipmentCategory.PROJECTOR,
                specification_reference="27 41 16",
            ),
        ],
        detail_callouts=[],
    )

    candidates = RFICandidateService().build(review)

    assert [candidate.rfi_id for candidate in candidates].count(
        "rfi_projector_mounting_eq-projector"
    ) == 1


def test_clean_review_returns_empty_list():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
                specification_reference="27 41 16",
            ),
            Equipment(
                equipment_id="eq-display",
                description="Main display",
                category=EquipmentCategory.DISPLAY,
                specification_reference="27 41 16",
            ),
        ],
        detail_callouts=[
            DetailCallout(
                callout_id="callout-001",
                detail_number="1",
                source_sheet_number="AV-101",
                equipment_category="mount",
                description="Mounting detail",
            )
        ],
        scope_gaps=[],
        engineering_assumptions=[
            EngineeringAssumption(
                assumption_id="assumption-001",
                category="general",
                description="General review note.",
                severity=AssumptionSeverity.REVIEW,
            )
        ],
    )

    candidates = RFICandidateService().build(review)

    assert candidates == []

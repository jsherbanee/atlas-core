from typing import Any

from atlas_core.domain import (
    BidPackageReview,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    LaborEstimate,
    RFICandidate,
    RFICandidateCategory,
    RFICandidateSeverity,
    RevisionChangeRecord,
    RevisionChangeSeverity,
    RevisionChangeType,
    RevisionComparison,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.services import (
    PlanReviewReadiness,
    PlanReviewReadinessService,
    ReadinessEvidenceRef,
    ReadinessLevel,
    ReadinessStatus,
)


def make_system() -> IntegratedSystem:
    return IntegratedSystem(
        system_id="sys-001",
        name="Performance Audio",
        category=SystemCategory.AUDIO,
    )


def make_equipment(**overrides: Any) -> Equipment:
    values: dict[str, Any] = {
        "equipment_id": "eq-001",
        "description": "Main speaker",
        "category": EquipmentCategory.SPEAKER,
        "quantity": 2,
        "manufacturer": "JBL",
        "model": "CBT 70J",
        "system_id": "sys-001",
        "drawing_reference": "AV-401",
        "specification_reference": "27 41 16",
    }
    values.update(overrides)
    return Equipment(**values)


def make_drawing_sheet() -> DrawingSheet:
    return DrawingSheet(
        sheet_id="av-401",
        sheet_number="AV-401",
        title="Audio Plan",
    )


def make_specification_section() -> SpecificationSection:
    return SpecificationSection(
        section_id="27-41-16",
        section_number="27 41 16",
        title="Integrated AV Systems",
    )


def make_review(**overrides: Any) -> BidPackageReview:
    values: dict[str, Any] = {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Bid Package Review",
        "drawing_sheets": [],
        "specification_sections": [],
        "systems": [make_system()],
        "equipment": [make_equipment()],
        "confidence": 0.9,
        "labor_estimate": LaborEstimate(
            project_id="project-001",
            total_labor_hours_low=10,
            total_labor_hours_expected=12,
            total_labor_hours_high=14,
            confidence=0.86,
        ),
    }
    values.update(overrides)
    return BidPackageReview(**values)


def assess(review: BidPackageReview) -> PlanReviewReadiness:
    return PlanReviewReadinessService().assess(review)


def test_fully_ready_package_returns_bid_ready() -> None:
    review = make_review(
        drawing_sheets=[make_drawing_sheet()],
        specification_sections=[make_specification_section()],
    )

    readiness = assess(review)

    assert readiness.status is ReadinessStatus.READY
    assert readiness.readiness_level in {
        ReadinessLevel.BID_READY,
        ReadinessLevel.BID_READY_WITH_ASSUMPTIONS,
    }
    assert readiness.project_id == "project-001"
    assert readiness.readiness_score > 0.7
    assert "equipment_completeness" in readiness.section_scores
    assert "revision_stability" in readiness.section_scores


def test_missing_equipment_model_data_reduces_equipment_score() -> None:
    review = make_review(
        drawing_sheets=[make_drawing_sheet()],
        specification_sections=[make_specification_section()],
        equipment=[make_equipment(model=None, manufacturer=None)],
    )

    readiness = assess(review)

    assert readiness.section_scores["equipment_completeness"] < 0.8
    assert any(
        "Missing model" in diagnostic
        for diagnostic in readiness.missing_scope_diagnostics
    )


def test_quantity_conflict_reduces_quantity_confidence() -> None:
    review = make_review(
        drawing_sheets=[make_drawing_sheet()],
        specification_sections=[make_specification_section()],
        rfi_candidates=[
            RFICandidate(
                candidate_id="rfi-001",
                project_id="project-001",
                title="Quantity mismatch",
                description="Schedule differs from drawing",
                category=RFICandidateCategory.QUANTITY_CONFLICT,
                severity=RFICandidateSeverity.HIGH,
                confidence=0.9,
                detected_condition="quantity_conflict",
                recommended_action="Reconcile quantities",
            )
        ],
    )

    readiness = assess(review)

    assert readiness.section_scores["quantity_confidence"] < 0.9


def test_scope_responsibility_ambiguity_creates_warning_or_blocker() -> None:
    review = make_review(
        drawing_sheets=[make_drawing_sheet()],
        specification_sections=[make_specification_section()],
        equipment=[
            make_equipment(
                assumptions=["OFCI cabling by others"],
                description="Speaker package by others",
            )
        ],
        rfi_candidates=[
            RFICandidate(
                candidate_id="rfi-002",
                project_id="project-001",
                title="Scope ambiguity",
                description="Responsibility unclear",
                category=RFICandidateCategory.RESPONSIBILITY_GAP,
                severity=RFICandidateSeverity.HIGH,
                confidence=0.9,
                detected_condition="scope_responsibility_ambiguity",
                recommended_action="Clarify ownership",
            )
        ],
    )

    readiness = assess(review)

    assert readiness.section_scores["scope_responsibility_clarity"] < 0.8
    assert readiness.warnings or readiness.blocking_issues


def test_critical_rfi_candidate_creates_blocker() -> None:
    review = make_review(
        drawing_sheets=[make_drawing_sheet()],
        specification_sections=[make_specification_section()],
        rfi_candidates=[
            RFICandidate(
                candidate_id="rfi-003",
                project_id="project-001",
                title="Critical product conflict",
                description="Discontinued device",
                category=RFICandidateCategory.PRODUCT_CONFLICT,
                severity=RFICandidateSeverity.CRITICAL,
                confidence=0.95,
                detected_condition="product_unavailable_reference",
                recommended_action="Resolve substitution",
            )
        ],
    )

    readiness = assess(review)

    assert readiness.status is ReadinessStatus.NOT_READY
    assert (
        "Critical RFI candidate risk requires clarification."
        in readiness.blocking_issues
    )


def test_low_labor_confidence_reduces_score() -> None:
    review = make_review(
        drawing_sheets=[make_drawing_sheet()],
        specification_sections=[make_specification_section()],
        labor_estimate=LaborEstimate(
            project_id="project-001",
            total_labor_hours_low=10,
            total_labor_hours_expected=12,
            total_labor_hours_high=14,
            confidence=0.45,
        ),
    )

    readiness = assess(review)

    assert readiness.section_scores["labor_estimate_confidence"] == 0.45
    assert (
        "Labor estimate confidence is below preferred threshold." in readiness.warnings
    )


def test_revision_comparison_instability_reduces_score() -> None:
    unstable_revision = RevisionComparison(
        project_id="project-001",
        baseline_revision_id="rev-a",
        comparison_revision_id="rev-b",
        summary={"change_count": 1},
        changes=[
            RevisionChangeRecord(
                change_id="chg-001",
                change_type=RevisionChangeType.SPECIFICATION_CHANGED,
                title="Spec changed",
                description="Major spec shift",
                severity=RevisionChangeSeverity.HIGH,
                confidence=0.9,
                affected_items=["eq-001"],
                detected_condition="specification_reference_changed",
                estimating_impact="Major",
                recommended_action="Review",
            )
        ],
        confidence=0.55,
    )
    review = make_review(
        drawing_sheets=[make_drawing_sheet()],
        specification_sections=[make_specification_section()],
        revision_comparison=unstable_revision,
    )

    readiness = assess(review)

    assert readiness.section_scores["revision_stability"] < 0.7
    assert (
        "Revision instability suggests additional estimator review."
        in readiness.warnings
    )


def test_serialization_output() -> None:
    readiness = PlanReviewReadiness(
        status=ReadinessStatus.NEEDS_REVIEW,
        message="Plan review needs estimator review before pricing.",
        blockers=["Major blocker"],
        warnings=["Warning"],
        project_id="project-001",
        readiness_score=0.66,
        readiness_level=ReadinessLevel.NEEDS_REVIEW,
        section_scores={
            "equipment_completeness": 0.7,
            "quantity_confidence": 0.6,
            "scope_responsibility_clarity": 0.6,
            "drawing_spec_alignment": 0.7,
            "assumptions_quality": 0.8,
            "rfi_candidate_risk": 0.5,
            "labor_estimate_confidence": 0.7,
            "revision_stability": 1.0,
        },
        blocking_issues=["Major blocker"],
        missing_scope_diagnostics=["Missing model"],
        evidence_refs=[
            ReadinessEvidenceRef(
                source_type="equipment",
                source_id="eq-001",
                field="model",
                excerpt="model is missing",
            )
        ],
        recommendation_summary="1 blocker and 1 warning.",
        recommended_reviewer_actions=["Resolve blocker"],
        confidence=0.7,
    )

    payload = readiness.to_dict()

    assert payload["project_id"] == "project-001"
    assert payload["readiness_score"] == 0.66
    assert payload["readiness_level"] == "needs_review"
    assert "section_scores" in payload
    assert "blocking_issues" in payload
    assert "warnings" in payload
    assert "missing_scope_diagnostics" in payload
    assert "evidence_refs" in payload
    assert "recommendation_summary" in payload
    assert "recommended_reviewer_actions" in payload
    assert payload["created_by_engine_version"]

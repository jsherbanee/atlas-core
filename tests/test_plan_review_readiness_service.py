from typing import Any

from atlas_core.domain import (
    BidPackageReview,
    DrawingDiscipline,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    SpecificationDiscipline,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.services import (
    EstimatorRisk,
    PlanReviewReadiness,
    PlanReviewReadinessService,
    ReadinessStatus,
    Recommendation,
    ScopeGap,
)


def make_drawing_sheet() -> DrawingSheet:
    return DrawingSheet(
        sheet_id="av101",
        sheet_number="AV1.01",
        title="AV Plan",
        discipline=DrawingDiscipline.AUDIOVISUAL,
    )


def make_specification_section() -> SpecificationSection:
    return SpecificationSection(
        section_id="27-41-16",
        section_number="27 41 16",
        title="Integrated Audio-Video Systems",
        discipline=SpecificationDiscipline.AUDIOVISUAL,
    )


def make_system() -> IntegratedSystem:
    return IntegratedSystem(
        system_id="sys-001",
        name="Performance Audio",
        category=SystemCategory.AUDIO,
    )


def make_equipment() -> Equipment:
    return Equipment(
        equipment_id="eq-001",
        description="Display",
        category=EquipmentCategory.DISPLAY,
    )


def make_review(**overrides: Any) -> BidPackageReview:
    values: dict[str, Any] = {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Bid Package Review",
        "drawing_sheets": [make_drawing_sheet()],
        "specification_sections": [make_specification_section()],
        "systems": [make_system()],
        "equipment": [make_equipment()],
        "confidence": 0.9,
    }
    values.update(overrides)
    return BidPackageReview(**values)


def assess(review: BidPackageReview) -> PlanReviewReadiness:
    return PlanReviewReadinessService().assess(review)


def test_ready_review_returns_ready():
    readiness = assess(make_review())

    assert readiness.status is ReadinessStatus.READY
    assert readiness.message == "Plan review is ready for pricing."
    assert readiness.blockers == []
    assert readiness.warnings == []


def test_missing_drawings_returns_not_ready():
    readiness = assess(make_review(drawing_sheets=[]))

    assert readiness.status is ReadinessStatus.NOT_READY
    assert "No drawing sheets are available." in readiness.blockers


def test_missing_specs_returns_not_ready():
    readiness = assess(make_review(specification_sections=[]))

    assert readiness.status is ReadinessStatus.NOT_READY
    assert "No specification sections are available." in readiness.blockers


def test_missing_systems_returns_not_ready():
    readiness = assess(make_review(systems=[]))

    assert readiness.status is ReadinessStatus.NOT_READY
    assert "No systems were detected." in readiness.blockers


def test_missing_equipment_returns_not_ready():
    readiness = assess(make_review(equipment=[]))

    assert readiness.status is ReadinessStatus.NOT_READY
    assert "No equipment was detected." in readiness.blockers


def test_scope_gaps_return_needs_review():
    readiness = assess(
        make_review(
            scope_gaps=[
                ScopeGap(
                    gap_id="speaker_missing_amplifier",
                    target_id="eq-001",
                    message="Speaker is missing amplifier.",
                )
            ]
        )
    )

    assert readiness.status is ReadinessStatus.NEEDS_REVIEW
    assert "Scope gaps require estimator review." in readiness.warnings


def test_high_estimator_risks_return_needs_review():
    readiness = assess(
        make_review(
            estimator_risks=[
                EstimatorRisk(
                    risk_id="scope_risk",
                    message="Scope risk requires review.",
                    risk_level="high",
                )
            ]
        )
    )

    assert readiness.status is ReadinessStatus.NEEDS_REVIEW
    assert "High estimator risks require estimator review." in readiness.warnings


def test_high_recommendations_return_needs_review():
    readiness = assess(
        make_review(
            recommendations=[
                Recommendation(
                    recommendation_id="review-low-confidence",
                    message="Review low confidence.",
                    priority="high",
                )
            ]
        )
    )

    assert readiness.status is ReadinessStatus.NEEDS_REVIEW
    assert (
        "High-priority recommendations require estimator review." in readiness.warnings
    )


def test_low_confidence_returns_needs_review():
    readiness = assess(make_review(confidence=0.7))

    assert readiness.status is ReadinessStatus.NEEDS_REVIEW
    assert "Review confidence is below 0.75." in readiness.warnings


def test_to_dict_output():
    readiness = PlanReviewReadiness(
        status="needs_review",
        message=" Plan review needs estimator review before pricing. ",
        blockers=[" Confirm drawing index. "],
        warnings=[" Review confidence. "],
    )

    assert readiness.to_dict() == {
        "status": "needs_review",
        "message": "Plan review needs estimator review before pricing.",
        "blockers": ["Confirm drawing index."],
        "warnings": ["Review confidence."],
    }

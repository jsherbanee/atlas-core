from typing import Any

from atlas_core.domain import (
    BidPackageReview,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.rules import Resolution, ResolutionAction
from atlas_core.services.confidence_scoring_service import ConfidenceScoringService
from atlas_core.services import (
    EstimatorRisk,
    ManufacturerReviewIssue,
    ScopeGap,
)


def make_review(**overrides: Any) -> BidPackageReview:
    values: dict[str, Any] = {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Plan Review",
        "drawing_sheets": [
            DrawingSheet(
                sheet_id="av-101",
                sheet_number="AV-101",
                title="Audio Plan",
            )
        ],
        "specification_sections": [
            SpecificationSection(
                section_id="27-41-16",
                section_number="27 41 16",
                title="Integrated Audio Systems",
            )
        ],
        "systems": [
            IntegratedSystem(
                system_id="sys-001",
                name="Audio System",
                category=SystemCategory.AUDIO,
            )
        ],
        "equipment": [
            Equipment(
                equipment_id="eq-001",
                description="Main loudspeaker",
                category=EquipmentCategory.SPEAKER,
            )
        ],
    }
    values.update(overrides)
    return BidPackageReview(**values)


def make_scope_gap(index: int = 1) -> ScopeGap:
    return ScopeGap(
        gap_id=f"gap-{index}",
        target_id=f"eq-{index}",
        message="Scope gap requires review.",
    )


def make_estimator_risk(index: int = 1) -> EstimatorRisk:
    return EstimatorRisk(
        risk_id=f"risk-{index}",
        message="Estimator risk requires review.",
    )


def make_manufacturer_issue(index: int = 1) -> ManufacturerReviewIssue:
    return ManufacturerReviewIssue(
        equipment_id=f"eq-{index}",
        manufacturer="Unknown",
        message="Manufacturer requires review.",
    )


def make_resolution(index: int = 1) -> Resolution:
    return Resolution(
        rule_id=f"RULE-{index:03}",
        action=ResolutionAction.MARK_FOR_REVIEW,
        target_id=f"eq-{index}",
        message="Resolver issue requires review.",
    )


def test_perfect_review_returns_1_0():
    assert ConfidenceScoringService().score_review(make_review()) == 1.0


def test_scope_gaps_reduce_confidence():
    review = make_review(scope_gaps=[make_scope_gap()])

    assert ConfidenceScoringService().score_review(review) == 0.95


def test_estimator_risks_reduce_confidence():
    review = make_review(estimator_risks=[make_estimator_risk()])

    assert ConfidenceScoringService().score_review(review) == 0.97


def test_manufacturer_issues_reduce_confidence():
    review = make_review(manufacturer_review_issues=[make_manufacturer_issue()])

    assert ConfidenceScoringService().score_review(review) == 0.98


def test_resolver_resolutions_reduce_confidence():
    review = make_review(resolutions=[make_resolution()])

    assert ConfidenceScoringService().score_review(review) == 0.99


def test_missing_drawings_specs_systems_equipment_reduce_confidence():
    review = make_review(
        drawing_sheets=[],
        specification_sections=[],
        systems=[],
        equipment=[],
    )

    assert ConfidenceScoringService().score_review(review) == 0.8


def test_score_does_not_go_below_0_25():
    review = make_review(
        drawing_sheets=[],
        specification_sections=[],
        systems=[],
        equipment=[],
        scope_gaps=[make_scope_gap(index) for index in range(10)],
        estimator_risks=[make_estimator_risk(index) for index in range(10)],
        manufacturer_review_issues=[
            make_manufacturer_issue(index) for index in range(10)
        ],
        resolutions=[make_resolution(index) for index in range(20)],
    )

    assert ConfidenceScoringService().score_review(review) == 0.25


def test_score_rounds_to_2_decimals():
    review = make_review(
        scope_gaps=[make_scope_gap()],
        estimator_risks=[make_estimator_risk()],
        manufacturer_review_issues=[make_manufacturer_issue()],
        resolutions=[make_resolution()],
    )

    assert ConfidenceScoringService().score_review(review) == 0.89

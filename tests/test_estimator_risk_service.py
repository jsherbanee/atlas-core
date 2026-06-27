from atlas_core.domain import BidPackageReview, Equipment, EquipmentCategory
from atlas_core.services import (
    EstimatorRisk,
    EstimatorRiskService,
    ManufacturerReviewIssue,
    ReviewReportItem,
    RiskLevel,
    ScopeGap,
)


def make_review(**overrides) -> BidPackageReview:
    values = {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Plan Review",
    }
    values.update(overrides)
    return BidPackageReview(**values)


def test_scope_gaps_create_high_risk():
    review = make_review(
        scope_gaps=[
            ScopeGap(
                gap_id="projector_missing_mount",
                target_id="eq-001",
                message="Projector is missing a mount.",
            )
        ]
    )

    risks = EstimatorRiskService().assess(review)

    assert risks[0].risk_id == "scope_gaps_detected"
    assert risks[0].risk_level is RiskLevel.HIGH
    assert risks[0].category == "scope"
    assert (
        risks[0].message
        == "Scope gaps were detected and require estimator review."
    )


def test_manufacturer_issues_create_medium_risk():
    review = make_review(
        manufacturer_review_issues=[
            ManufacturerReviewIssue(
                equipment_id="eq-001",
                manufacturer="Legacy",
                message="Manufacturer requires review.",
            )
        ]
    )

    risks = EstimatorRiskService().assess(review)

    assert risks[0].risk_id == "manufacturer_review_required"
    assert risks[0].risk_level is RiskLevel.MEDIUM
    assert risks[0].category == "manufacturer"
    assert risks[0].message == "One or more manufacturers require review."


def test_drapery_creates_high_risk():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-drapery",
                description="Traveler curtain",
                category=EquipmentCategory.DRAPERY,
            )
        ]
    )

    risks = EstimatorRiskService().assess(review)

    assert risks[0].risk_id == "drapery_scope_review"
    assert risks[0].risk_level is RiskLevel.HIGH
    assert risks[0].category == "drapery"
    assert risks[0].message == (
        "Drapery scope requires review of track, hardware, structure, "
        "fire rating, and site conditions."
    )


def test_low_confidence_creates_medium_risk():
    review = make_review(confidence=0.6)

    risks = EstimatorRiskService().assess(review)

    assert risks[0].risk_id == "low_review_confidence"
    assert risks[0].risk_level is RiskLevel.MEDIUM
    assert risks[0].category == "confidence"
    assert risks[0].message == "Overall review confidence is below threshold."


def test_review_report_creates_medium_risk():
    review = make_review(
        review_report=[
            ReviewReportItem(
                source="resolver",
                target_id="eq-001",
                message="Review missing allowance.",
            )
        ]
    )

    risks = EstimatorRiskService().assess(review)

    assert risks[0].risk_id == "review_report_action_items"
    assert risks[0].risk_level is RiskLevel.MEDIUM
    assert risks[0].category == "review"
    assert risks[0].message == "Review report contains estimator action items."


def test_no_duplicate_risks():
    review = make_review(
        scope_gaps=[
            ScopeGap(
                gap_id="projector_missing_mount",
                target_id="eq-001",
                message="Projector is missing a mount.",
            ),
            ScopeGap(
                gap_id="display_missing_mount",
                target_id="eq-002",
                message="Display is missing a mount.",
            ),
        ]
    )

    risks = EstimatorRiskService().assess(review)

    assert [risk.risk_id for risk in risks] == ["scope_gaps_detected"]


def test_to_dict_output():
    risk = EstimatorRisk(
        risk_id="scope_gaps_detected",
        message="Scope gaps were detected.",
        risk_level="high",
        category="scope",
        confidence=0.9,
    )

    assert risk.to_dict() == {
        "risk_id": "scope_gaps_detected",
        "message": "Scope gaps were detected.",
        "risk_level": "high",
        "category": "scope",
        "confidence": 0.9,
    }

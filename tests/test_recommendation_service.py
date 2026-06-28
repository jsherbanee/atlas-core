from atlas_core.domain import BidPackageReview, DrawingSheet, SpecificationSection
from atlas_core.services import (
    EstimatorRisk,
    ManufacturerReviewIssue,
    Recommendation,
    RecommendationPriority,
    RecommendationService,
    ScopeGap,
)


def make_review(**overrides) -> BidPackageReview:
    values = {
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
        "confidence": 0.9,
    }
    values.update(overrides)
    return BidPackageReview(**values)


def recommendation_ids(recommendations):
    return [recommendation.recommendation_id for recommendation in recommendations]


def test_high_severity_scope_gap_creates_high_priority_recommendation():
    review = make_review(
        scope_gaps=[
            ScopeGap(
                gap_id="projector_missing_mount",
                target_id="eq-projector",
                message="Projector is missing a mount.",
                severity="high",
                suggested_action="Add projector mount allowance.",
            )
        ]
    )

    recommendations = RecommendationService().build_recommendations(review)

    assert recommendations[0].recommendation_id == (
        "scope-gap-projector_missing_mount-eq-projector"
    )
    assert recommendations[0].message == "Add projector mount allowance."
    assert recommendations[0].priority is RecommendationPriority.HIGH
    assert recommendations[0].category == "scope_gap"
    assert recommendations[0].target_id == "eq-projector"


def test_estimator_risks_create_recommendation():
    review = make_review(
        estimator_risks=[
            EstimatorRisk(
                risk_id="scope_gaps_detected",
                message="Scope gaps were detected.",
            )
        ]
    )

    recommendations = RecommendationService().build_recommendations(review)

    assert "review-estimator-risks" in recommendation_ids(recommendations)
    assert recommendations[0].message == (
        "Review estimator risks before pricing or submitting bid."
    )


def test_manufacturer_issues_create_recommendation():
    review = make_review(
        manufacturer_review_issues=[
            ManufacturerReviewIssue(
                equipment_id="eq-001",
                manufacturer="Unknown",
                message="Manufacturer requires review.",
            )
        ]
    )

    recommendations = RecommendationService().build_recommendations(review)

    assert "confirm-manufacturers" in recommendation_ids(recommendations)
    assert recommendations[0].category == "manufacturer"


def test_low_confidence_creates_recommendation():
    review = make_review(confidence=0.7)

    recommendations = RecommendationService().build_recommendations(review)

    assert "review-low-confidence" in recommendation_ids(recommendations)
    assert recommendations[0].priority is RecommendationPriority.HIGH
    assert recommendations[0].category == "confidence"


def test_missing_drawings_creates_recommendation():
    review = make_review(drawing_sheets=[])

    recommendations = RecommendationService().build_recommendations(review)

    assert "missing-drawing-index" in recommendation_ids(recommendations)
    assert recommendations[0].message == (
        "No drawing index is available. Upload or extract drawing sheets before "
        "pricing."
    )


def test_missing_specs_creates_recommendation():
    review = make_review(specification_sections=[])

    recommendations = RecommendationService().build_recommendations(review)

    assert "missing-specification-index" in recommendation_ids(recommendations)
    assert recommendations[0].message == (
        "No specification index is available. Upload or extract specifications "
        "before pricing."
    )


def test_clean_review_returns_empty_list():
    assert RecommendationService().build_recommendations(make_review()) == []


def test_to_dict_output():
    recommendation = Recommendation(
        recommendation_id="review-low-confidence",
        message="Review confidence.",
        priority="high",
        category="confidence",
        target_id="review-001",
    )

    assert recommendation.to_dict() == {
        "recommendation_id": "review-low-confidence",
        "message": "Review confidence.",
        "priority": "high",
        "category": "confidence",
        "target_id": "review-001",
    }

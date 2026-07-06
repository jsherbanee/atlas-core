from atlas_core.domain import (
    AssumptionSeverity,
    BidPackageReview,
    Equipment,
    EquipmentCategory,
)
from atlas_core.services import (
    BidCompleteness,
    CompletenessStatus,
    FinalEstimatorReview,
    FinalEstimatorReviewService,
    PlanReviewReadiness,
    ReadinessStatus,
    Recommendation,
    ScopeGap,
)


def make_review(
    readiness: PlanReviewReadiness | None = None,
    bid_completeness: BidCompleteness | None = None,
    recommendations: list[Recommendation] | None = None,
    scope_gaps: list[ScopeGap] | None = None,
    equipment: list[Equipment] | None = None,
) -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        equipment=list(
            equipment
            or [
                Equipment(
                    equipment_id="eq-001",
                    description="Display",
                    category=EquipmentCategory.DISPLAY,
                )
            ]
        ),
        readiness=readiness,
        bid_completeness=bid_completeness,
        recommendations=list(recommendations or []),
        scope_gaps=list(scope_gaps or []),
        confidence=0.82,
    )


def build(review: BidPackageReview) -> FinalEstimatorReview:
    return FinalEstimatorReviewService().build(review)


def test_builds_final_review():
    review = make_review(
        readiness=PlanReviewReadiness(
            status=ReadinessStatus.NEEDS_REVIEW,
            message="Plan review needs estimator review before pricing.",
        ),
        bid_completeness=BidCompleteness(
            status=CompletenessStatus.PARTIAL,
            score=0.7,
            drawing_completeness=1.0,
            specification_completeness=1.0,
            system_completeness=0.0,
            equipment_completeness=1.0,
            schedule_completeness=0.5,
            missing_items=["Missing system detection."],
        ),
    )

    final_review = build(review)

    assert final_review.review_id == "review-001"
    assert final_review.project_id == "project-001"
    assert final_review.name == "Bid Package Review"
    assert final_review.readiness_status == "needs_review"
    assert final_review.readiness_message == (
        "Plan review needs estimator review before pricing."
    )
    assert final_review.completeness_status == "partial"
    assert final_review.completeness_score == 0.7
    assert final_review.confidence == 0.82
    assert final_review.total_issues == review.issue_count()
    assert final_review.total_recommendations == review.recommendation_count()
    assert final_review.total_assumptions == len(final_review.engineering_assumptions)


def test_ready_summary():
    final_review = build(
        make_review(
            readiness=PlanReviewReadiness(
                status=ReadinessStatus.READY,
                message="Plan review is ready for pricing.",
            )
        )
    )

    assert final_review.executive_summary == "Bid package appears ready for pricing."


def test_needs_review_summary():
    final_review = build(
        make_review(
            readiness=PlanReviewReadiness(
                status=ReadinessStatus.NEEDS_REVIEW,
                message="Plan review needs estimator review before pricing.",
            )
        )
    )

    assert final_review.executive_summary == (
        "Bid package requires estimator review before pricing."
    )


def test_not_ready_summary():
    final_review = build(
        make_review(
            readiness=PlanReviewReadiness(
                status=ReadinessStatus.NOT_READY,
                message="Plan review is not ready for pricing.",
            )
        )
    )

    assert final_review.executive_summary == "Bid package is not ready for pricing."


def test_includes_blockers_as_next_actions():
    final_review = build(
        make_review(
            readiness=PlanReviewReadiness(
                status=ReadinessStatus.NOT_READY,
                message="Plan review is not ready for pricing.",
                blockers=["No drawing sheets are available."],
            )
        )
    )

    assert "No drawing sheets are available." in final_review.next_actions


def test_includes_warnings_as_next_actions():
    final_review = build(
        make_review(
            readiness=PlanReviewReadiness(
                status=ReadinessStatus.NEEDS_REVIEW,
                message="Plan review needs estimator review before pricing.",
                warnings=["Review confidence is below 0.75."],
            )
        )
    )

    assert "Review confidence is below 0.75." in final_review.next_actions


def test_includes_recommendations_as_next_actions():
    final_review = build(
        make_review(
            recommendations=[
                Recommendation(
                    recommendation_id="review-low-confidence",
                    message="Review confidence before pricing.",
                    priority="high",
                )
            ]
        )
    )

    assert "Review confidence before pricing." in final_review.next_actions


def test_includes_high_severity_scope_gap_suggested_actions():
    final_review = build(
        make_review(
            scope_gaps=[
                ScopeGap(
                    gap_id="speaker_missing_amplifier",
                    target_id="eq-001",
                    message="Speaker equipment is present, but no amplifier exists.",
                    severity="high",
                    suggested_action="Add amplifier channel capacity review.",
                )
            ]
        )
    )

    assert "Add amplifier channel capacity review." in final_review.next_actions


def test_avoids_duplicate_next_actions():
    action = "Review confidence before pricing."
    final_review = build(
        make_review(
            readiness=PlanReviewReadiness(
                status=ReadinessStatus.NEEDS_REVIEW,
                message="Plan review needs estimator review before pricing.",
                warnings=[action],
            ),
            recommendations=[
                Recommendation(
                    recommendation_id="review-low-confidence",
                    message=action,
                    priority="high",
                )
            ],
        )
    )

    assert final_review.next_actions.count(action) == 1


def test_includes_engineering_assumptions_in_output_and_actions():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            )
        ]
    )

    final_review = build(review)

    assert final_review.total_assumptions > 0
    assert final_review.engineering_assumptions

    projector_assumption = next(
        assumption
        for assumption in final_review.engineering_assumptions
        if assumption.assumption_id == "projector_mounting_detail_missing"
    )
    assert projector_assumption.severity is AssumptionSeverity.REVIEW
    assert projector_assumption.description in final_review.next_actions


def test_to_dict_output():
    final_review = FinalEstimatorReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        readiness_status="needs_review",
        readiness_message="Plan review needs estimator review before pricing.",
        completeness_status="partial",
        completeness_score=0.7,
        confidence=0.82,
        total_issues=3,
        total_recommendations=2,
        total_assumptions=1,
        executive_summary="Bid package requires estimator review before pricing.",
        next_actions=["Review confidence before pricing."],
        engineering_assumptions=[],
    )

    assert final_review.to_dict() == {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Bid Package Review",
        "readiness_status": "needs_review",
        "readiness_message": "Plan review needs estimator review before pricing.",
        "completeness_status": "partial",
        "completeness_score": 0.7,
        "confidence": 0.82,
        "total_issues": 3,
        "total_recommendations": 2,
        "total_assumptions": 1,
        "executive_summary": "Bid package requires estimator review before pricing.",
        "next_actions": ["Review confidence before pricing."],
        "engineering_assumptions": [],
    }

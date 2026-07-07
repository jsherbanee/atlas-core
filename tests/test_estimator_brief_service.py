from atlas_core.domain import (
    AssumptionSeverity,
    BidPackageReview,
    EngineeringAssumption,
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
    SystemCategory,
)
from atlas_core.services import (
    EstimatorBrief,
    EstimatorBriefService,
    PlanReviewReadiness,
    ReadinessEvidenceRef,
    ReadinessLevel,
    ReadinessStatus,
)


def make_review() -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        drawing_sheets=[],
        specification_sections=[],
        systems=[
            IntegratedSystem(
                system_id="sys-001",
                name="Performance Audio",
                category=SystemCategory.AUDIO,
            )
        ],
        equipment=[
            Equipment(
                equipment_id="eq-001",
                description="Main speaker",
                category=EquipmentCategory.SPEAKER,
                quantity=2,
                manufacturer="JBL",
                model="CBT 70J",
                drawing_reference="AV-401",
                specification_reference="27 41 16",
            )
        ],
        engineering_assumptions=[
            EngineeringAssumption(
                assumption_id="assume-001",
                category="coordination",
                description="Confirm conduit pathway.",
                severity=AssumptionSeverity.RISK,
            )
        ],
        rfi_candidates=[
            RFICandidate(
                candidate_id="rfi-001",
                project_id="project-001",
                title="Scope ambiguity",
                description="By others language detected.",
                category=RFICandidateCategory.RESPONSIBILITY_GAP,
                severity=RFICandidateSeverity.HIGH,
                confidence=0.9,
                detected_condition="scope_responsibility_ambiguity",
                recommended_action="Clarify ownership.",
            )
        ],
        labor_estimate=LaborEstimate(
            project_id="project-001",
            total_labor_hours_low=10,
            total_labor_hours_expected=12,
            total_labor_hours_high=14,
            confidence=0.62,
            warnings=["Scope ambiguity may increase labor hours."],
        ),
        revision_comparison=RevisionComparison(
            project_id="project-001",
            baseline_revision_id="rev-a",
            comparison_revision_id="rev-b",
            summary={"change_count": 1},
            changes=[
                RevisionChangeRecord(
                    change_id="chg-001",
                    change_type=RevisionChangeType.SPECIFICATION_CHANGED,
                    title="Spec changed",
                    description="Control spec update",
                    severity=RevisionChangeSeverity.HIGH,
                    confidence=0.9,
                    affected_items=["eq-001"],
                    detected_condition="specification_reference_changed",
                    estimating_impact="Scope impact",
                    recommended_action="Review update",
                )
            ],
            confidence=0.58,
        ),
        readiness=PlanReviewReadiness(
            status=ReadinessStatus.NEEDS_REVIEW,
            message="Plan review needs estimator review before pricing.",
            project_id="project-001",
            readiness_score=0.66,
            readiness_level=ReadinessLevel.NEEDS_REVIEW,
            section_scores={
                "equipment_completeness": 0.8,
                "quantity_confidence": 0.7,
                "scope_responsibility_clarity": 0.55,
                "drawing_spec_alignment": 0.72,
                "assumptions_quality": 0.68,
                "rfi_candidate_risk": 0.58,
                "labor_estimate_confidence": 0.62,
                "revision_stability": 0.54,
            },
            blocking_issues=["Critical ambiguity unresolved."],
            warnings=["Labor estimate confidence is below preferred threshold."],
            missing_scope_diagnostics=["Missing specification reference for eq-002."],
            evidence_refs=[
                ReadinessEvidenceRef(
                    source_type="equipment",
                    source_id="eq-002",
                    field="specification_reference",
                    excerpt="missing",
                )
            ],
            recommendation_summary="1 blocker and 1 warning.",
            recommended_reviewer_actions=["Resolve ambiguity."],
            confidence=0.7,
        ),
        confidence=0.79,
    )


def test_brief_generation_from_clean_ready_package() -> None:
    review = make_review()
    review.readiness = PlanReviewReadiness(
        status=ReadinessStatus.READY,
        message="Plan review is ready for pricing.",
        project_id="project-001",
        readiness_score=0.91,
        readiness_level=ReadinessLevel.BID_READY,
        section_scores={
            "equipment_completeness": 1.0,
            "quantity_confidence": 1.0,
            "scope_responsibility_clarity": 0.95,
            "drawing_spec_alignment": 1.0,
            "assumptions_quality": 0.9,
            "rfi_candidate_risk": 0.9,
            "labor_estimate_confidence": 0.8,
            "revision_stability": 0.9,
        },
        recommendation_summary="No blockers.",
        confidence=0.9,
    )
    review.rfi_candidates = []
    review.revision_comparison = None

    brief = EstimatorBriefService().build_brief(review)

    assert brief.project_id == "project-001"
    assert brief.brief_title == "Estimator Brief - Bid Package Review"
    assert brief.readiness_summary is not None
    assert brief.readiness_summary["readiness_level"] == "bid_ready"
    assert brief.top_blockers == []


def test_brief_generation_with_blockers() -> None:
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.top_blockers is not None
    assert "Critical ambiguity unresolved." in brief.top_blockers
    assert brief.prioritized_reviewer_actions is not None
    assert len(brief.prioritized_reviewer_actions) > 0


def test_rfi_candidate_inclusion() -> None:
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.key_rfi_candidates is not None
    assert brief.key_rfi_candidates[0]["candidate_id"] == "rfi-001"


def test_labor_summary_inclusion() -> None:
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.labor_summary is not None
    assert brief.labor_summary["available"] is True
    assert brief.labor_summary["confidence"] == 0.62


def test_revision_summary_inclusion() -> None:
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.revision_summary is not None
    assert brief.revision_summary["available"] is True
    assert brief.revision_summary["high_or_critical_changes"] == 1


def test_action_prioritization() -> None:
    brief = EstimatorBriefService().build_brief(make_review())

    actions = brief.prioritized_reviewer_actions or []
    assert len(actions) > 1
    priorities = [action["priority"] for action in actions]
    assert priorities == sorted(
        priorities,
        key=lambda value: {"critical": 4, "high": 3, "medium": 2, "low": 1}[value],
        reverse=True,
    )


def test_evidence_refs_inclusion() -> None:
    brief = EstimatorBriefService().build_brief(make_review())

    assert brief.evidence_refs is not None
    assert any(ref["source_type"] == "equipment" for ref in brief.evidence_refs)


def test_serialization() -> None:
    brief = EstimatorBriefService().build_brief(make_review())
    payload = brief.to_dict()

    assert payload["project_id"] == "project-001"
    assert "brief_title" in payload
    assert "executive_summary" in payload
    assert "readiness_summary" in payload
    assert "top_blockers" in payload
    assert "top_warnings" in payload
    assert "key_rfi_candidates" in payload
    assert "labor_summary" in payload
    assert "revision_summary" in payload
    assert "assumption_summary" in payload
    assert "missing_scope_summary" in payload
    assert "prioritized_reviewer_actions" in payload
    assert "evidence_refs" in payload
    assert "confidence" in payload
    assert "created_by_engine_version" in payload


def test_to_dict_output_for_dataclass_instantiation() -> None:
    brief = EstimatorBrief(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        drawing_count=1,
        specification_count=1,
        system_count=1,
        equipment_count=1,
        room_count=0,
        detail_callout_count=0,
        issue_count=0,
        placeholder_count=0,
        review_required_count=0,
        cross_reference_count=0,
        reconciliation_issue_count=0,
        scope_gap_count=0,
        estimator_risk_count=0,
        keynote_count=0,
        legend_count=0,
        legend_item_count=0,
        confidence=0.9,
        brief_title="Estimator Brief - Bid Package Review",
        executive_summary="Summary",
        readiness_summary={"readiness_level": "bid_ready"},
        top_blockers=[],
        top_warnings=[],
        key_rfi_candidates=[],
        labor_summary={"available": False},
        revision_summary={"available": False},
        assumption_summary={"total_count": 0},
        missing_scope_summary={"diagnostic_count": 0},
        prioritized_reviewer_actions=[],
        evidence_refs=[],
    )

    payload = brief.to_dict()

    assert payload["brief_title"] == "Estimator Brief - Bid Package Review"
    assert payload["readiness_summary"]["readiness_level"] == "bid_ready"

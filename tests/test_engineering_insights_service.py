from atlas_core.domain import (
    AssumptionSeverity,
    BidPackageReview,
    DrawingSheet,
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
    Room,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.services import (
    EngineeringInsightsService,
    EstimatorBriefService,
    PlanReviewReadiness,
    ReadinessLevel,
    ReadinessStatus,
)


def _make_review() -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Engineering Intelligence Test",
        drawing_sheets=[
            DrawingSheet(
                sheet_id="sheet-101", sheet_number="AV-101", title="Audio Plan"
            ),
            DrawingSheet(
                sheet_id="sheet-401", sheet_number="AV-401", title="Rack Plan"
            ),
        ],
        specification_sections=[
            SpecificationSection(
                section_id="spec-271416",
                section_number="27 41 16",
                title="Integrated Audio Systems",
            ),
            SpecificationSection(
                section_id="spec-274123",
                section_number="27 41 23",
                title="Video Display Systems",
            ),
        ],
        systems=[
            IntegratedSystem(
                system_id="sys-audio",
                name="Audio",
                category=SystemCategory.AUDIO,
            ),
            IntegratedSystem(
                system_id="sys-video",
                name="Video",
                category=SystemCategory.VIDEO,
            ),
        ],
        equipment=[
            Equipment(
                equipment_id="eq-001",
                description="Main speaker",
                category=EquipmentCategory.SPEAKER,
                quantity=2,
                manufacturer="JBL",
                model="CBT 70J",
                system_id="sys-audio",
                room_id="rm-101",
                drawing_reference="AV-101,AV-401",
                specification_reference="",
            ),
            Equipment(
                equipment_id="eq-002",
                description="Projector",
                category=EquipmentCategory.PROJECTOR,
                quantity=1,
                manufacturer="",
                model="",
                system_id="sys-video",
                room_id="",
                drawing_reference="AV-401",
                specification_reference="27 41 23",
                assumptions=["OFCI mount by others"],
            ),
        ],
        rooms=[
            Room(room_id="rm-101", name="Main Hall", building_id="bldg-1"),
            Room(room_id="rm-102", name="Lobby", building_id="bldg-1"),
        ],
        engineering_assumptions=[
            EngineeringAssumption(
                assumption_id="asm-001",
                category="coordination",
                description="Confirm UL-listed pathway standard",
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
                confidence=0.88,
                detected_condition="scope_responsibility_ambiguity",
                recommended_action="Clarify ownership.",
                related_items=["eq-002"],
            )
        ],
        labor_estimate=LaborEstimate(
            project_id="project-001",
            total_labor_hours_low=20,
            total_labor_hours_expected=24,
            total_labor_hours_high=30,
            confidence=0.62,
            warnings=["Schedule lead-time uncertainty"],
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
            confidence=0.6,
        ),
        readiness=PlanReviewReadiness(
            status=ReadinessStatus.NEEDS_REVIEW,
            message="Requires estimator review",
            project_id="project-001",
            readiness_score=0.65,
            readiness_level=ReadinessLevel.NEEDS_REVIEW,
            section_scores={"equipment_completeness": 0.75},
            blocking_issues=["Missing ownership confirmation."],
            warnings=["Schedule milestone mismatch"],
            missing_scope_diagnostics=["Missing specification reference for eq-001."],
            confidence=0.72,
        ),
        notes=["Check applicable code and owner standards."],
        confidence=0.74,
    )


def _knowledge_graph() -> dict[str, list[dict[str, str]]]:
    return {
        "nodes": [
            {
                "id": "project:project-001",
                "type": "Project",
                "label": "Engineering Intelligence Test",
            },
            {"id": "drawing:AV-101", "type": "Drawing", "label": "AV-101"},
            {"id": "drawing:AV-401", "type": "Drawing", "label": "AV-401"},
            {"id": "spec:27 41 16", "type": "Specification", "label": "27 41 16"},
            {"id": "equipment:eq-001", "type": "Equipment", "label": "eq-001"},
            {"id": "equipment:eq-002", "type": "Equipment", "label": "eq-002"},
            {"id": "system:sys-audio", "type": "System", "label": "sys-audio"},
            {"id": "system:sys-video", "type": "System", "label": "sys-video"},
            {"id": "evidence:AV-101:1", "type": "Evidence", "label": "AV-101 p.1"},
        ],
        "edges": [
            {
                "source": "drawing:AV-101",
                "target": "equipment:eq-001",
                "relationship": "Drawing to Equipment",
                "confidence": "0.8",
                "source_evidence": "AV-101",
            },
            {
                "source": "equipment:eq-001",
                "target": "system:sys-audio",
                "relationship": "Equipment to System",
                "confidence": "0.8",
                "source_evidence": "AV-101",
            },
            {
                "source": "drawing:AV-101",
                "target": "evidence:AV-101:1",
                "relationship": "Drawing to Evidence",
                "confidence": "0.7",
                "source_evidence": "AV-101",
            },
        ],
    }


def test_engineering_insights_builds_deterministic_output() -> None:
    review = _make_review()
    brief = EstimatorBriefService().build_brief(review)

    result = EngineeringInsightsService().build(
        review=review,
        knowledge_graph=_knowledge_graph(),
        estimator_brief=brief,
    )

    assert result.insights
    assert result.project_health.score >= 0
    assert result.project_health.score <= 100
    assert result.system_health
    assert result.recommendations


def test_engineering_insights_contains_expected_categories() -> None:
    review = _make_review()
    brief = EstimatorBriefService().build_brief(review)
    result = EngineeringInsightsService().build(
        review=review,
        knowledge_graph=_knowledge_graph(),
        estimator_brief=brief,
    )

    categories = {item.category for item in result.insights}
    assert "Missing Information" in categories
    assert "Labor Risk" in categories
    assert "Revision Impact" in categories
    assert "General Recommendation" in categories


def test_system_health_fields_are_populated() -> None:
    review = _make_review()
    result = EngineeringInsightsService().build(
        review=review,
        knowledge_graph=_knowledge_graph(),
        estimator_brief=None,
    )

    for item in result.system_health:
        assert item.health_score >= 0
        assert item.health_score <= 100
        assert 0 <= item.equipment_completeness <= 1
        assert 0 <= item.specification_coverage <= 1
        assert 0 <= item.drawing_coverage <= 1


def test_recommendations_include_traceability() -> None:
    review = _make_review()
    brief = EstimatorBriefService().build_brief(review)
    result = EngineeringInsightsService().build(
        review=review,
        knowledge_graph=_knowledge_graph(),
        estimator_brief=brief,
    )

    assert result.recommendations
    assert all(item.recommended_action for item in result.recommendations)
    assert any(item.evidence_refs for item in result.recommendations)

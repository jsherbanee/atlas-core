import pytest

from atlas_core.domain import (
    RFICandidate,
    RFICandidateCategory,
    RFICandidateSeverity,
    RFICandidateSourceRef,
    RFICandidateStatus,
)


def test_creating_valid_rfi_candidate():
    candidate = RFICandidate(
        candidate_id=" rfi-project-001-abc123 ",
        project_id=" project-001 ",
        title=" Missing model number for eq-projector ",
        description=" Projector has manufacturer but model is missing. ",
        category=RFICandidateCategory.MISSING_INFORMATION,
        severity=RFICandidateSeverity.HIGH,
        confidence=0.9,
        source_refs=[
            RFICandidateSourceRef(
                source_type=" equipment ",
                source_id=" eq-projector ",
                field=" model ",
                excerpt=" manufacturer=Epson ",
            )
        ],
        related_items=[" eq-projector "],
        detected_condition=" missing_model_number ",
        recommended_action=" Confirm model number before pricing. ",
        status=RFICandidateStatus.CANDIDATE,
        created_by_engine_version=" rfi-candidate-engine/1.0.0 ",
    )

    assert candidate.candidate_id == "rfi-project-001-abc123"
    assert candidate.project_id == "project-001"
    assert candidate.title == "Missing model number for eq-projector"
    assert candidate.description == "Projector has manufacturer but model is missing."
    assert candidate.category is RFICandidateCategory.MISSING_INFORMATION
    assert candidate.severity is RFICandidateSeverity.HIGH
    assert candidate.confidence == 0.9
    assert candidate.source_refs[0].source_type == "equipment"
    assert candidate.source_refs[0].source_id == "eq-projector"
    assert candidate.source_refs[0].field == "model"
    assert candidate.source_refs[0].excerpt == "manufacturer=Epson"
    assert candidate.related_items == ["eq-projector"]
    assert candidate.detected_condition == "missing_model_number"
    assert candidate.recommended_action == "Confirm model number before pricing."
    assert candidate.status is RFICandidateStatus.CANDIDATE
    assert candidate.created_by_engine_version == "rfi-candidate-engine/1.0.0"


def test_accepting_string_enum_values():
    candidate = RFICandidate(
        candidate_id="rfi-001",
        project_id="project-001",
        title="Missing manufacturer",
        description="Manufacturer missing for display.",
        category="missing_information",
        severity="medium",
        confidence=0.8,
        detected_condition="missing_manufacturer",
        recommended_action="Confirm manufacturer.",
        status="candidate",
    )

    assert candidate.category is RFICandidateCategory.MISSING_INFORMATION
    assert candidate.severity is RFICandidateSeverity.MEDIUM
    assert candidate.status is RFICandidateStatus.CANDIDATE


def test_rejecting_blank_title():
    with pytest.raises(ValueError, match="title cannot be blank"):
        RFICandidate(
            candidate_id="rfi-001",
            project_id="project-001",
            title=" ",
            description="Description",
            category="missing_information",
            severity="high",
            confidence=0.8,
            detected_condition="missing_information",
            recommended_action="Action",
        )


def test_rejecting_blank_detected_condition():
    with pytest.raises(ValueError, match="detected_condition cannot be blank"):
        RFICandidate(
            candidate_id="rfi-001",
            project_id="project-001",
            title="Confirm lens",
            description="Description",
            category="missing_information",
            severity="high",
            confidence=0.8,
            detected_condition=" ",
            recommended_action="Action",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        RFICandidate(
            candidate_id="rfi-001",
            project_id="project-001",
            title="Confirm lens",
            description="Description",
            category="missing_information",
            severity="high",
            confidence=1.2,
            detected_condition="missing_information",
            recommended_action="Action",
        )


def test_to_dict_output():
    candidate = RFICandidate(
        candidate_id="rfi-001",
        project_id="project-001",
        title="Missing model number for eq-projector",
        description="Projector has manufacturer but model is missing.",
        category=RFICandidateCategory.MISSING_INFORMATION,
        severity=RFICandidateSeverity.HIGH,
        confidence=0.9,
        source_refs=[
            RFICandidateSourceRef(
                source_type="equipment",
                source_id="eq-projector",
                field="model",
                source_label="Main projector",
                excerpt="manufacturer=Epson",
            )
        ],
        related_items=["eq-projector"],
        detected_condition="missing_model_number",
        recommended_action="Confirm model number before pricing.",
        status=RFICandidateStatus.CANDIDATE,
        created_by_engine_version="rfi-candidate-engine/1.0.0",
    )

    assert candidate.to_dict() == {
        "candidate_id": "rfi-001",
        "project_id": "project-001",
        "title": "Missing model number for eq-projector",
        "description": "Projector has manufacturer but model is missing.",
        "category": "missing_information",
        "severity": "high",
        "confidence": 0.9,
        "source_refs": [
            {
                "source_type": "equipment",
                "source_id": "eq-projector",
                "field": "model",
                "source_label": "Main projector",
                "excerpt": "manufacturer=Epson",
            }
        ],
        "related_items": ["eq-projector"],
        "detected_condition": "missing_model_number",
        "recommended_action": "Confirm model number before pricing.",
        "status": "candidate",
        "created_by_engine_version": "rfi-candidate-engine/1.0.0",
    }

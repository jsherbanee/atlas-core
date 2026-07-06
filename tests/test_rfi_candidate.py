import pytest

from atlas_core.domain import RFICandidate, RFIPriority


def test_creating_valid_rfi_candidate():
    candidate = RFICandidate(
        rfi_id=" rfi-001 ",
        title=" Confirm projector throw distance ",
        question=" Please confirm final projector throw distance and lens type. ",
        priority=RFIPriority.HIGH,
        category=" coordination ",
        related_sheet=" AV-201 ",
        related_specification=" 27 41 16 ",
        related_equipment=" eq-projector ",
        source=" atlas ",
        confidence=0.9,
    )

    assert candidate.rfi_id == "rfi-001"
    assert candidate.title == "Confirm projector throw distance"
    assert (
        candidate.question
        == "Please confirm final projector throw distance and lens type."
    )
    assert candidate.priority is RFIPriority.HIGH
    assert candidate.category == "coordination"
    assert candidate.related_sheet == "AV-201"
    assert candidate.related_specification == "27 41 16"
    assert candidate.related_equipment == "eq-projector"
    assert candidate.source == "atlas"
    assert candidate.confidence == 0.9


def test_accepting_string_priority():
    candidate = RFICandidate(
        rfi_id="rfi-001",
        title="Confirm lens",
        question="Please confirm lens type.",
        priority="medium",
    )

    assert candidate.priority is RFIPriority.MEDIUM


def test_rejecting_blank_title():
    with pytest.raises(ValueError, match="title cannot be blank"):
        RFICandidate(
            rfi_id="rfi-001",
            title=" ",
            question="Please confirm lens type.",
        )


def test_rejecting_blank_question():
    with pytest.raises(ValueError, match="question cannot be blank"):
        RFICandidate(
            rfi_id="rfi-001",
            title="Confirm lens",
            question=" ",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        RFICandidate(
            rfi_id="rfi-001",
            title="Confirm lens",
            question="Please confirm lens type.",
            confidence=1.2,
        )


def test_to_dict_output():
    candidate = RFICandidate(
        rfi_id="rfi-001",
        title="Confirm projector throw distance",
        question="Please confirm final projector throw distance and lens type.",
        priority=RFIPriority.HIGH,
        category="coordination",
        related_sheet="AV-201",
        related_specification="27 41 16",
        related_equipment="eq-projector",
        source="atlas",
        confidence=0.9,
    )

    assert candidate.to_dict() == {
        "rfi_id": "rfi-001",
        "title": "Confirm projector throw distance",
        "question": "Please confirm final projector throw distance and lens type.",
        "priority": "high",
        "category": "coordination",
        "related_sheet": "AV-201",
        "related_specification": "27 41 16",
        "related_equipment": "eq-projector",
        "source": "atlas",
        "confidence": 0.9,
    }

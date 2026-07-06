import pytest

from atlas_core.domain import AssumptionSeverity, EngineeringAssumption


def test_creating_valid_engineering_assumption():
    assumption = EngineeringAssumption(
        assumption_id=" assumption-001 ",
        category=" mounting ",
        description=" Coordinate mounting heights in field. ",
        severity=AssumptionSeverity.RISK,
        source=" atlas ",
        related_sheet=" AV-101 ",
        related_specification=" 27 41 16 ",
        related_equipment=" eq-001 ",
        confidence=0.9,
    )

    assert assumption.assumption_id == "assumption-001"
    assert assumption.category == "mounting"
    assert assumption.description == "Coordinate mounting heights in field."
    assert assumption.severity is AssumptionSeverity.RISK
    assert assumption.source == "atlas"
    assert assumption.related_sheet == "AV-101"
    assert assumption.related_specification == "27 41 16"
    assert assumption.related_equipment == "eq-001"
    assert assumption.confidence == 0.9


def test_rejecting_blank_assumption_id():
    with pytest.raises(ValueError, match="assumption_id cannot be blank"):
        EngineeringAssumption(
            assumption_id=" ",
            category="mounting",
            description="Coordinate mounting heights in field.",
        )


def test_accepting_string_severity():
    assumption = EngineeringAssumption(
        assumption_id="assumption-001",
        category="mounting",
        description="Coordinate mounting heights in field.",
        severity="review",
    )

    assert assumption.severity is AssumptionSeverity.REVIEW


def test_rejecting_blank_category():
    with pytest.raises(ValueError, match="category cannot be blank"):
        EngineeringAssumption(
            assumption_id="assumption-001",
            category=" ",
            description="Coordinate mounting heights in field.",
        )


def test_rejecting_blank_description():
    with pytest.raises(ValueError, match="description cannot be blank"):
        EngineeringAssumption(
            assumption_id="assumption-001",
            category="mounting",
            description=" ",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        EngineeringAssumption(
            assumption_id="assumption-001",
            category="mounting",
            description="Coordinate mounting heights in field.",
            confidence=1.1,
        )


def test_to_dict_output():
    assumption = EngineeringAssumption(
        assumption_id="assumption-001",
        category="mounting",
        description="Coordinate mounting heights in field.",
        severity=AssumptionSeverity.REVIEW,
        source="atlas",
        related_sheet="AV-101",
        related_specification="27 41 16",
        related_equipment="eq-001",
        confidence=0.85,
    )

    assert assumption.to_dict() == {
        "assumption_id": "assumption-001",
        "category": "mounting",
        "description": "Coordinate mounting heights in field.",
        "severity": "review",
        "source": "atlas",
        "related_sheet": "AV-101",
        "related_specification": "27 41 16",
        "related_equipment": "eq-001",
        "confidence": 0.85,
    }

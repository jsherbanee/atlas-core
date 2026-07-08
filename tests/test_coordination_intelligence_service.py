from atlas_core.domain import BidPackageReview
from atlas_core.services.coordination_intelligence import (
    CoordinationCategory,
    CoordinationIntelligenceEngine,
)


def _review_fixture() -> BidPackageReview:
    return BidPackageReview(
        review_id="review-coordination",
        project_id="project-coordination",
        name="Coordination Intelligence Test",
        confidence=0.87,
    )


def test_coordination_engine_generates_conflict_gap_and_agreement_findings() -> None:
    review = _review_fixture()

    drawings = [
        {
            "drawing_number": "AV-101",
            "referenced_specifications": ["27 41 16", "27 05 00"],
        }
    ]
    specifications = [
        {
            "section": "27 41 16",
            "referenced_drawings": ["AV-101", "AV-999"],
            "requirement_candidates": [{"requirement_type": "testing_requirements"}],
        }
    ]
    equipment = [
        {
            "equipment_id": "EQ-AMP-001",
            "drawing_references": ["AV-101"],
            "specification_references": [],
            "system": "Audio",
        },
        {
            "equipment_id": "EQ-DSP-002",
            "drawing_references": ["AV-101"],
            "specification_references": ["27 41 16"],
            "system": "Audio",
        },
    ]
    systems = [{"system": "Audio"}]

    result = CoordinationIntelligenceEngine().build(
        review=review,
        drawings=drawings,
        specifications=specifications,
        equipment=equipment,
        systems=systems,
        rfis=[],
        assumptions=[],
        evidence=[{"source_file": "AV-101.pdf", "page": 1}],
    )

    assert result.findings
    assert result.summary.total_findings == len(result.findings)
    assert result.summary.gap_count > 0
    assert result.summary.agreement_count > 0

    categories = {item.category for item in result.findings}
    assert CoordinationCategory.DRAWING_SPECIFICATION_ALIGNMENT in categories
    assert CoordinationCategory.EQUIPMENT_SPECIFICATION_ALIGNMENT in categories


def test_coordination_engine_adds_evidence_traceability_gap_without_evidence() -> None:
    review = _review_fixture()

    result = CoordinationIntelligenceEngine().build(
        review=review,
        drawings=[
            {
                "drawing_number": "AV-102",
                "referenced_specifications": ["27 41 16"],
            }
        ],
        specifications=[
            {
                "section": "27 41 16",
                "referenced_drawings": ["AV-102"],
                "requirement_candidates": [],
            }
        ],
        equipment=[],
        systems=[],
        rfis=[],
        assumptions=[],
        evidence=[],
    )

    finding_ids = {item.finding_id for item in result.findings}
    assert "coord-evidence-gap:global" in finding_ids
    assert result.summary.total_findings == len(result.findings)

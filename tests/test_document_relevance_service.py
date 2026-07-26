from __future__ import annotations

import pytest

from atlas_core.services.document_relevance_service import DocumentRelevanceService


def _page(source_file: str, text: str, page_number: int = 1) -> dict[str, object]:
    return {
        "source_file": source_file,
        "page_number": page_number,
        "text": text,
    }


@pytest.mark.parametrize(
    ("text", "expected_primary"),
    [
        ("audiovisual", "audiovisual"),
        ("touchpanel", "av control systems"),
        ("gateway", "integrated control systems"),
        ("dmx", "theatrical lighting"),
        ("dimming", "theatrical lighting control"),
        ("show control", "show control"),
        ("performance-system", "performance-system controls"),
    ],
)
def test_primary_disciplines_receive_equal_weight(
    text: str,
    expected_primary: str,
) -> None:
    service = DocumentRelevanceService()
    assessment = service.assess_document(
        source_file="example.pdf",
        group_name="drawings",
        page_records=[_page("example.pdf", text)],
    )

    assert assessment.primary_discipline == expected_primary
    assert assessment.authority_level == "governing"
    assert assessment.overall_relevance_score == 72
    assert assessment.project_membership_status == "governing"
    assert expected_primary in assessment.governing_for[0]
    assert assessment.page_assessments[0].page_number == 1
    assert assessment.page_assessments[0].detected_sheet_number is None
    assert assessment.page_assessments[0].detected_discipline == expected_primary
    assert assessment.page_assessments[0].workflow_scores.intake > 0


def test_architectural_lighting_is_visible_but_lower_scope() -> None:
    service = DocumentRelevanceService()
    assessment = service.assess_document(
        source_file="architectural-lighting.pdf",
        group_name="drawings",
        page_records=[
            _page(
                "architectural-lighting.pdf",
                "room lighting occupancy controls lighting panel schedule facade lighting",
            )
        ],
    )

    assert assessment.primary_discipline is None
    assert "architectural lighting" in assessment.secondary_disciplines
    assert "Possible Architectural Lighting Scope" in assessment.review_flags
    assert assessment.authority_level == "coordination"
    assert assessment.project_membership_status == "possible_scope"
    assert "architectural lighting coordination" in assessment.coordination_for
    assert "architectural lighting estimating" in assessment.non_governing_for
    assert (
        assessment.page_assessments[0].detected_discipline == "architectural lighting"
    )
    assert assessment.page_assessments[0].workflow_scores.intake == 58


def test_report_scope_remains_explainable_without_auto_rejection() -> None:
    service = DocumentRelevanceService()
    assessment = service.assess_document(
        source_file="acoustics-narrative.pdf",
        group_name="reports",
        page_records=[
            _page(
                "acoustics-narrative.pdf",
                "Acoustics narrative and design narrative for coordination review.",
            )
        ],
    )

    assert assessment.primary_discipline is None
    assert assessment.authority_level == "coordination"
    assert assessment.project_membership_status == "related"
    assert assessment.review_flags == ["Review For Scope Relevance"]
    assert "acoustics coordination" in assessment.coordination_for
    assert "AV equipment estimating" in assessment.non_governing_for
    assert assessment.page_assessments[0].page_number == 1
    assert assessment.page_assessments[0].detected_discipline is None
    assert assessment.page_assessments[0].workflow_scores.engineering >= 70

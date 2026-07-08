from atlas_core.domain import BidPackageReview, DrawingDiscipline, DrawingSheet
from atlas_core.services.drawing_intelligence import (
    DrawingAnalyzer,
    DrawingIntelligenceEngine,
)


def _review_fixture() -> BidPackageReview:
    return BidPackageReview(
        review_id="review-drawing-intel",
        project_id="project-drawing-intel",
        name="Drawing Intelligence Test",
        drawing_sheets=[
            DrawingSheet(
                sheet_id="sheet-av-101",
                sheet_number="AV-101",
                title="AV Floor Plan",
                discipline=DrawingDiscipline.AUDIOVISUAL,
                notes=[
                    "See AV-201 for continuation.",
                    "DETAIL 3 at display wall.",
                    "VIEW 2 shows projector alignment.",
                    "KEYNOTE 12 applies to cable pathway.",
                    'SCALE: 1/8" = 1\'-0"',
                ],
                confidence=0.9,
            ),
            DrawingSheet(
                sheet_id="sheet-av-201",
                sheet_number="AV-201",
                title="AV Equipment Plan",
                discipline=DrawingDiscipline.AUDIOVISUAL,
                notes=["See AV-101 and DETAIL 1."],
                confidence=0.87,
            ),
        ],
        confidence=0.88,
    )


def test_drawing_analyzer_extracts_deterministic_metadata_and_references() -> None:
    review = _review_fixture()
    analyzer = DrawingAnalyzer()

    metadata = analyzer.analyze_sheet(
        review.drawing_sheets[0],
        {"AV-101", "AV-201"},
    )

    assert metadata.discipline.value == "av"
    assert metadata.sheet_category.value == "floor_plan"
    assert metadata.scale == '1/8" = 1\'-0"'
    assert "AV-201" in [
        ref.target_id
        for ref in metadata.references
        if ref.reference_type.value == "sheet"
    ]
    assert "3" in metadata.detail_references
    assert "2" in metadata.view_references
    assert "KEYNOTE 12" in metadata.keynotes


def test_drawing_intelligence_engine_builds_index_hierarchy_and_relationships() -> None:
    review = _review_fixture()
    result = DrawingIntelligenceEngine().build(review)

    assert result.metadata
    assert "AV-101" in result.drawing_index.by_sheet_number
    assert "av" in result.hierarchy.disciplines
    assert result.confidence > 0.0

    relationships = [
        (item.source_id, item.target_id, item.relationship_type)
        for item in result.relationships
    ]
    assert ("AV-101", "AV-201", "references_sheet") in relationships

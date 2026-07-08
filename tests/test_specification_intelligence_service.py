from atlas_core.domain import (
    BidPackageReview,
    SpecificationDiscipline,
    SpecificationSection,
)
from atlas_core.services.specification_intelligence import (
    SpecificationAnalyzer,
    SpecificationIntelligenceEngine,
)


def _review_fixture() -> BidPackageReview:
    return BidPackageReview(
        review_id="review-spec-intel",
        project_id="project-spec-intel",
        name="Specification Intelligence Test",
        specification_sections=[
            SpecificationSection(
                section_id="spec-27-41-16",
                section_number="27 41 16",
                title="Integrated Audio-Video Systems",
                discipline=SpecificationDiscipline.AUDIOVISUAL,
                manufacturers=["QSC", "Shure"],
                notes=[
                    "PART 1 - GENERAL",
                    "1.1 SUMMARY",
                    "PART 2 - PRODUCTS",
                    "2.2 ACCEPTABLE MANUFACTURERS",
                    "PART 3 - EXECUTION",
                    "3.1 INSTALLATION",
                    "Warranty: Provide 2 year system warranty.",
                    "Submittals are required before procurement.",
                    "Testing and commissioning required.",
                    "Drawings AV-101 and AV-201 govern layout.",
                    "See schedule AV schedule A.",
                    "Comply with NFPA 70 and ANSI/TIA-568.",
                    "Addendum ADD-02 modifies conduit responsibility.",
                ],
                confidence=0.9,
            ),
            SpecificationSection(
                section_id="spec-26-05-00",
                section_number="26 05 00",
                title="Common Work Results for Electrical",
                discipline=SpecificationDiscipline.ELECTRICAL,
                notes=["Coordination with 27 41 16 is required."],
                confidence=0.84,
            ),
        ],
        confidence=0.86,
    )


def test_specification_analyzer_extracts_metadata_parts_and_requirements() -> None:
    review = _review_fixture()
    analyzer = SpecificationAnalyzer()

    section = analyzer.analyze_section(
        review.specification_sections[0],
        {"27 41 16", "26 05 00"},
    )

    assert section.division == "Division 27 Communications"
    assert section.discipline.value == "av_systems"
    assert [item.part_number for item in section.parts] == [
        "Part 1",
        "Part 2",
        "Part 3",
    ]
    assert any(item.heading == "SUMMARY" for item in section.articles)
    assert any(
        item["requirement_type"] == "warranty_requirements"
        for item in section.requirement_candidates
    )
    assert "NFPA 70" in section.metadata.referenced_standards
    assert "AV-101" in section.metadata.referenced_drawings
    assert "ADD-02" in section.metadata.addendum_references


def test_specification_intelligence_engine_builds_index_and_relationships() -> None:
    review = _review_fixture()

    result = SpecificationIntelligenceEngine().build(review)

    assert result.sections
    assert "27 41 16" in result.specification_index.by_section
    assert "Division 27 Communications" in result.specification_index.by_division
    assert result.confidence > 0.0

    relationship_keys = {
        (item.source_id, item.target_id, item.relationship_type)
        for item in result.relationships
    }
    assert (
        "27 41 16",
        "27 41 16:Part 1",
        "has_part",
    ) in relationship_keys
    assert (
        "27 41 16",
        "drawing:AV-101",
        "references_drawing",
    ) in relationship_keys

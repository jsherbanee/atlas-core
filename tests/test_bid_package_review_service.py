from atlas_core.domain import Equipment, EquipmentCategory
from atlas_core.services import BidPackageReviewService, CrossReferenceType


def build_review(**kwargs):
    return BidPackageReviewService().build_review(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        **kwargs,
    )


def test_builds_review_from_raw_sheets_and_raw_sections():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ],
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ],
    )

    assert review.review_id == "review-001"
    assert review.project_id == "project-001"
    assert review.name == "Bid Package Review"
    assert review.drawing_count() == 1
    assert review.specification_count() == 1


def test_includes_indexed_drawing_sheets():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ],
    )

    assert review.drawing_sheets[0].sheet_id == "av1.01"
    assert review.drawing_sheets[0].title == "AV Plan"


def test_includes_indexed_specification_sections():
    review = build_review(
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ],
    )

    assert review.specification_sections[0].section_id == "27-41-16"
    assert review.specification_sections[0].title == (
        "Integrated Audio-Video Systems"
    )


def test_includes_equipment():
    equipment = [
        Equipment(
            equipment_id="eq-display",
            description="Display",
            category=EquipmentCategory.DISPLAY,
        )
    ]

    review = build_review(equipment=equipment)

    assert review.equipment == equipment
    assert review.equipment_count() == 1


def test_includes_resolver_resolutions():
    equipment = [
        Equipment(
            equipment_id="eq-drapery",
            description="Motorized Drapery",
            category=EquipmentCategory.DRAPERY,
        )
    ]

    review = build_review(equipment=equipment)

    assert len(review.resolutions) == 1
    assert review.resolutions[0].rule_id == "RULE-004"


def test_includes_review_report():
    equipment = [
        Equipment(
            equipment_id="eq-drapery",
            description="Motorized Drapery",
            category=EquipmentCategory.DRAPERY,
        )
    ]

    review = build_review(equipment=equipment)

    assert len(review.review_report) == 1
    assert review.review_report[0].source == "resolver"
    assert review.review_report[0].target_id == "eq-drapery"


def test_includes_cross_references_when_equipment_references_drawing_and_spec():
    equipment = [
        Equipment(
            equipment_id="eq-speaker",
            description="Main loudspeaker",
            category=EquipmentCategory.SPEAKER,
            drawing_reference="AV1.01",
            specification_reference="27 41 16",
        )
    ]

    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ],
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ],
        equipment=equipment,
    )

    assert any(
        reference.reference_type is CrossReferenceType.EQUIPMENT_TO_DRAWING
        and reference.source_id == "eq-speaker"
        and reference.target_id == "av1.01"
        for reference in review.cross_references
    )
    assert any(
        reference.reference_type is CrossReferenceType.EQUIPMENT_TO_SPEC
        and reference.source_id == "eq-speaker"
        and reference.target_id == "27-41-16"
        for reference in review.cross_references
    )


def test_includes_scope_gaps_for_missing_projector_mount():
    equipment = [
        Equipment(
            equipment_id="eq-projector",
            description="Projector",
            category=EquipmentCategory.PROJECTOR,
            room_id="room-001",
        )
    ]

    review = build_review(equipment=equipment)

    assert len(review.scope_gaps) == 1
    assert review.scope_gaps[0].gap_id == "projector_missing_mount"
    assert review.scope_gaps[0].target_id == "eq-projector"


def test_works_with_empty_inputs():
    review = build_review()

    assert review.drawing_sheets == []
    assert review.specification_sections == []
    assert review.systems == []
    assert review.equipment == []
    assert review.resolutions == []
    assert review.manufacturer_review_issues == []
    assert review.review_report == []
    assert review.cross_references == []
    assert review.scope_gaps == []

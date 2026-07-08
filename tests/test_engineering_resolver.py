from atlas_core.domain import (
    BidPackageReview,
    DrawingDiscipline,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    Room,
    RoomType,
    SpecificationDiscipline,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.services.resolver import EngineeringResolver, ResolverContext


def _build_review() -> BidPackageReview:
    return BidPackageReview(
        review_id="review-1",
        project_id="project-1",
        name="Resolver Review",
        drawing_sheets=[
            DrawingSheet(
                sheet_id="sheet-1",
                sheet_number="A1.01",
                title="Plan",
                discipline=DrawingDiscipline.AUDIOVISUAL,
            )
        ],
        specification_sections=[
            SpecificationSection(
                section_id="spec-1",
                section_number="27 41 00",
                title="AV Systems",
                discipline=SpecificationDiscipline.AUDIOVISUAL,
            )
        ],
        systems=[
            IntegratedSystem(
                system_id="sys-1",
                name="Main AV",
                category=SystemCategory.AUDIO,
                room_id="room-1",
                building_id="building-1",
            )
        ],
        equipment=[
            Equipment(
                equipment_id="eq-1",
                description="Main speaker",
                category=EquipmentCategory.SPEAKER,
                manufacturer="Acme Audio",
                model="A-100",
                system_id="sys-1",
                room_id="room-1",
                building_id="building-1",
                drawing_reference="A1.01",
                specification_reference="27 41 00",
            )
        ],
        rooms=[
            Room(
                room_id="room-1",
                name="Room 101",
                building_id="building-1",
                room_type=RoomType.CONFERENCE,
            )
        ],
    )


def test_resolver_normalizes_objects_and_links_evidence() -> None:
    result = EngineeringResolver().resolve(ResolverContext(review=_build_review()))

    assert result.summary["resolved_count"] == 6
    assert result.summary["conflict_count"] == 0
    assert result.summary["manual_review_count"] == 0
    assert result.confidence > 0.7

    equipment = next(
        item for item in result.resolved_objects if item.object_type == "equipment"
    )
    assert equipment.canonical_values["manufacturer"] == "Acme Audio"
    assert equipment.canonical_values["drawing_references"] == ["A1.01"]
    assert equipment.canonical_values["specification_references"] == ["27 41 00"]
    assert equipment.manual_review_required is False


def test_resolver_reports_missing_system_as_conflict() -> None:
    review = _build_review()
    review.equipment[0].system_id = "sys-missing"

    result = EngineeringResolver().resolve(ResolverContext(review=review))

    assert result.summary["conflict_count"] == 1
    equipment = next(
        item for item in result.resolved_objects if item.object_type == "equipment"
    )
    assert equipment.manual_review_required is True
    assert equipment.conflict_ids

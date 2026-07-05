from typing import Any

from atlas_core.domain import (
    BidPackageReview,
    DeviceSchedule,
    DrawingDiscipline,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    Keynote,
    SpecificationDiscipline,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.services import (
    BidCompleteness,
    BidCompletenessService,
    CompletenessStatus,
)


def make_drawing_sheet() -> DrawingSheet:
    return DrawingSheet(
        sheet_id="av101",
        sheet_number="AV1.01",
        title="AV Plan",
        discipline=DrawingDiscipline.AUDIOVISUAL,
    )


def make_specification_section() -> SpecificationSection:
    return SpecificationSection(
        section_id="27-41-16",
        section_number="27 41 16",
        title="Integrated Audio-Video Systems",
        discipline=SpecificationDiscipline.AUDIOVISUAL,
    )


def make_system() -> IntegratedSystem:
    return IntegratedSystem(
        system_id="sys-001",
        name="Performance Audio",
        category=SystemCategory.AUDIO,
    )


def make_equipment() -> Equipment:
    return Equipment(
        equipment_id="eq-001",
        description="Display",
        category=EquipmentCategory.DISPLAY,
    )


def make_schedule() -> DeviceSchedule:
    return DeviceSchedule(schedule_id="sched-001")


def make_keynote() -> Keynote:
    return Keynote(
        keynote_id="keynote-001",
        number="1",
        description="Ceiling Speaker",
    )


def make_review(**overrides: Any) -> BidPackageReview:
    values: dict[str, Any] = {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Bid Package Review",
        "drawing_sheets": [make_drawing_sheet()],
        "specification_sections": [make_specification_section()],
        "systems": [make_system()],
        "equipment": [make_equipment()],
        "device_schedules": [make_schedule()],
    }
    values.update(overrides)
    return BidPackageReview(**values)


def assess(review: BidPackageReview) -> BidCompleteness:
    return BidCompletenessService().assess(review)


def test_complete_review_returns_complete():
    completeness = assess(make_review())

    assert completeness.status is CompletenessStatus.COMPLETE
    assert completeness.score == 1.0


def test_missing_drawings_lowers_score():
    completeness = assess(make_review(drawing_sheets=[]))

    assert completeness.drawing_completeness == 0.0
    assert completeness.score == 0.8


def test_missing_specs_lowers_score():
    completeness = assess(make_review(specification_sections=[]))

    assert completeness.specification_completeness == 0.0
    assert completeness.score == 0.8


def test_missing_systems_lowers_score():
    completeness = assess(make_review(systems=[]))

    assert completeness.system_completeness == 0.0
    assert completeness.score == 0.8


def test_missing_equipment_lowers_score():
    completeness = assess(make_review(equipment=[]))

    assert completeness.equipment_completeness == 0.0
    assert completeness.score == 0.8


def test_keynotes_without_schedules_gives_partial_schedule_completeness():
    completeness = assess(make_review(device_schedules=[], keynotes=[make_keynote()]))

    assert completeness.schedule_completeness == 0.5
    assert completeness.score == 0.9


def test_missing_all_returns_incomplete():
    completeness = assess(
        make_review(
            drawing_sheets=[],
            specification_sections=[],
            systems=[],
            equipment=[],
            device_schedules=[],
            keynotes=[],
            legends=[],
        )
    )

    assert completeness.status is CompletenessStatus.INCOMPLETE
    assert completeness.score == 0.0


def test_missing_items_output():
    completeness = assess(
        make_review(
            drawing_sheets=[],
            specification_sections=[],
            systems=[],
            equipment=[],
            device_schedules=[],
            keynotes=[],
            legends=[],
        )
    )

    assert completeness.missing_items == [
        "Missing drawing index.",
        "Missing specification index.",
        "Missing system detection.",
        "Missing equipment detection.",
        "Missing device schedule, keynotes, or legend data.",
    ]


def test_to_dict_output():
    completeness = BidCompleteness(
        status="partial",
        score=0.85,
        drawing_completeness=1,
        specification_completeness=1,
        system_completeness=1,
        equipment_completeness=1,
        schedule_completeness=0.25,
        missing_items=[" Missing drawing index. "],
    )

    assert completeness.to_dict() == {
        "status": "partial",
        "score": 0.85,
        "drawing_completeness": 1.0,
        "specification_completeness": 1.0,
        "system_completeness": 1.0,
        "equipment_completeness": 1.0,
        "schedule_completeness": 0.25,
        "missing_items": ["Missing drawing index."],
    }

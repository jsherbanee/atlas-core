from atlas_core.domain import (
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    SpecificationSection,
    SystemCategory,
)
from atlas_core.services import (
    CrossReference,
    CrossReferenceService,
    CrossReferenceType,
)


def make_drawing() -> DrawingSheet:
    return DrawingSheet(
        sheet_id="drawing-av-401",
        sheet_number="AV-401",
        title="Recital Hall Audio Plan",
    )


def make_specification() -> SpecificationSection:
    return SpecificationSection(
        section_id="spec-27-41-16",
        section_number="27 41 16",
        title="Integrated Audio Systems",
        discipline="audiovisual",
    )


def make_equipment() -> Equipment:
    return Equipment(
        equipment_id="eq-speaker",
        description="Main loudspeaker",
        category=EquipmentCategory.SPEAKER,
        drawing_reference="av 401",
        specification_reference="27-41-16",
    )


def test_equipment_links_to_drawing_by_drawing_reference():
    references = CrossReferenceService().build_references(
        drawings=[make_drawing()],
        equipment=[make_equipment()],
    )

    assert any(
        reference.reference_type is CrossReferenceType.EQUIPMENT_TO_DRAWING
        and reference.source_id == "eq-speaker"
        and reference.target_id == "drawing-av-401"
        for reference in references
    )


def test_equipment_links_to_specification_by_specification_reference():
    references = CrossReferenceService().build_references(
        specifications=[make_specification()],
        equipment=[make_equipment()],
    )

    assert any(
        reference.reference_type is CrossReferenceType.EQUIPMENT_TO_SPEC
        and reference.source_id == "eq-speaker"
        and reference.target_id == "spec-27-41-16"
        for reference in references
    )


def test_system_audio_links_to_audiovisual_specification():
    system = IntegratedSystem(
        system_id="system-audio",
        name="Performance Audio",
        category=SystemCategory.AUDIO,
    )

    references = CrossReferenceService().build_references(
        specifications=[make_specification()],
        systems=[system],
    )

    assert any(
        reference.reference_type is CrossReferenceType.SYSTEM_TO_SPEC
        and reference.source_id == "system-audio"
        and reference.target_id == "spec-27-41-16"
        for reference in references
    )


def test_av_drawing_links_to_av_specification():
    references = CrossReferenceService().build_references(
        drawings=[make_drawing()],
        specifications=[make_specification()],
    )

    assert any(
        reference.reference_type is CrossReferenceType.DRAWING_TO_SPEC
        and reference.source_id == "drawing-av-401"
        and reference.target_id == "spec-27-41-16"
        for reference in references
    )


def test_duplicate_references_are_avoided():
    equipment = make_equipment()

    references = CrossReferenceService().build_references(
        drawings=[make_drawing()],
        equipment=[equipment, equipment],
    )
    matching_references = [
        reference
        for reference in references
        if reference.reference_type is CrossReferenceType.EQUIPMENT_TO_DRAWING
        and reference.source_id == "eq-speaker"
        and reference.target_id == "drawing-av-401"
    ]

    assert len(matching_references) == 1


def test_empty_inputs_return_empty_list():
    assert CrossReferenceService().build_references() == []


def test_to_dict_output():
    reference = CrossReference(
        reference_type="equipment_to_drawing",
        source_id="eq-speaker",
        target_id="drawing-av-401",
        message="Equipment references drawing.",
        confidence=0.9,
    )

    assert reference.to_dict() == {
        "reference_type": "equipment_to_drawing",
        "source_id": "eq-speaker",
        "target_id": "drawing-av-401",
        "message": "Equipment references drawing.",
        "confidence": 0.9,
    }

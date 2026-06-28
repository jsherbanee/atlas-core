from atlas_core.domain import (
    DrawingSheet,
    SpecificationSection,
    SystemCategory,
    SystemComplexity,
)
from atlas_core.services import SystemDetectionService


def make_drawing(title: str, sheet_number: str = "AV-101") -> DrawingSheet:
    return DrawingSheet(
        sheet_id=sheet_number.casefold(),
        sheet_number=sheet_number,
        title=title,
    )


def make_specification(
    title: str,
    section_number: str = "27 41 16",
) -> SpecificationSection:
    return SpecificationSection(
        section_id=section_number.replace(" ", "-").casefold(),
        section_number=section_number,
        title=title,
    )


def system_ids(systems):
    return [system.system_id for system in systems]


def test_detects_audio_from_spec_title():
    systems = SystemDetectionService().detect_systems(
        specifications=[make_specification("Integrated Audio Systems")]
    )

    assert systems[0].system_id == "detected-audio"
    assert systems[0].name == "Audio System"
    assert systems[0].category is SystemCategory.AUDIO
    assert systems[0].complexity is SystemComplexity.MEDIUM


def test_detects_projection_from_drawing_title():
    systems = SystemDetectionService().detect_systems(
        drawings=[make_drawing("Recital Hall Projection Plan")]
    )

    assert "detected-projection" in system_ids(systems)


def test_detects_display_from_digital_signage_title():
    systems = SystemDetectionService().detect_systems(
        drawings=[make_drawing("Lobby Digital Signage")]
    )

    assert "detected-display" in system_ids(systems)


def test_detects_control_from_av_control_title():
    systems = SystemDetectionService().detect_systems(
        drawings=[make_drawing("AV Control Details")]
    )

    assert "detected-control" in system_ids(systems)


def test_detects_lighting_from_theatrical_lighting_title():
    systems = SystemDetectionService().detect_systems(
        drawings=[make_drawing("Theatrical Lighting Plan", sheet_number="TL-101")]
    )

    assert systems[0].system_id == "detected-lighting"
    assert systems[0].category is SystemCategory.LIGHTING
    assert systems[0].complexity is SystemComplexity.HIGH


def test_detects_drapery_from_curtain_title():
    systems = SystemDetectionService().detect_systems(
        specifications=[
            make_specification(
                "Stage Curtains and Drapery",
                section_number="11 61 33",
            )
        ]
    )

    assert "detected-drapery" in system_ids(systems)


def test_detects_intercom():
    systems = SystemDetectionService().detect_systems(
        drawings=[make_drawing("Backstage Intercom Riser")]
    )

    assert "detected-intercom" in system_ids(systems)


def test_detects_assisted_listening():
    systems = SystemDetectionService().detect_systems(
        specifications=[make_specification("Assisted Listening System")]
    )

    assert "detected-assisted-listening" in system_ids(systems)


def test_avoids_duplicates():
    systems = SystemDetectionService().detect_systems(
        drawings=[make_drawing("Audio Plan")],
        specifications=[make_specification("Integrated Audio Systems")],
    )

    assert system_ids(systems).count("detected-audio") == 1


def test_passes_room_id_and_building_id_into_detected_systems():
    systems = SystemDetectionService().detect_systems(
        drawings=[make_drawing("Audio Plan")],
        room_id="room-001",
        building_id="building-001",
    )

    assert systems[0].room_id == "room-001"
    assert systems[0].building_id == "building-001"


def test_empty_inputs_return_empty_list():
    assert SystemDetectionService().detect_systems() == []

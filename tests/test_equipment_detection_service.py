from atlas_core.domain import (
    DrawingSheet,
    EquipmentCategory,
    SpecificationSection,
)
from atlas_core.services import EquipmentDetectionService


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


def equipment_ids(equipment):
    return [item.equipment_id for item in equipment]


def test_detects_speaker_from_loudspeaker_title():
    equipment = EquipmentDetectionService().detect_equipment(
        drawings=[make_drawing("Main Loudspeaker Plan")]
    )

    assert equipment[0].equipment_id == "detected-speaker"
    assert equipment[0].description == "Detected loudspeaker allowance"
    assert equipment[0].category is EquipmentCategory.SPEAKER
    assert equipment[0].status.value == "detected"
    assert equipment[0].confidence == 0.65
    assert equipment[0].drawing_reference == "AV-101"


def test_detects_amplifier():
    equipment = EquipmentDetectionService().detect_equipment(
        specifications=[make_specification("Amplifier Schedule")]
    )

    assert "detected-amplifier" in equipment_ids(equipment)
    assert equipment[0].specification_reference == "27 41 16"


def test_detects_projector():
    equipment = EquipmentDetectionService().detect_equipment(
        drawings=[make_drawing("Projection Plan")]
    )

    assert "detected-projector" in equipment_ids(equipment)


def test_detects_display_from_digital_signage():
    equipment = EquipmentDetectionService().detect_equipment(
        drawings=[make_drawing("Lobby Digital Signage")]
    )

    assert "detected-display" in equipment_ids(equipment)


def test_detects_control_processor_from_q_sys():
    equipment = EquipmentDetectionService().detect_equipment(
        specifications=[make_specification("Q-SYS Control System")]
    )

    assert "detected-control-processor" in equipment_ids(equipment)


def test_detects_microphone():
    equipment = EquipmentDetectionService().detect_equipment(
        drawings=[make_drawing("Wireless Mic Locations")]
    )

    assert "detected-microphone" in equipment_ids(equipment)


def test_detects_camera_from_ptz():
    equipment = EquipmentDetectionService().detect_equipment(
        drawings=[make_drawing("PTZ Camera Locations")]
    )

    assert "detected-camera" in equipment_ids(equipment)


def test_detects_lighting_fixture():
    equipment = EquipmentDetectionService().detect_equipment(
        drawings=[make_drawing("Lighting Fixture Schedule", sheet_number="TL-101")]
    )

    assert "detected-lighting-fixture" in equipment_ids(equipment)


def test_detects_lighting_console():
    equipment = EquipmentDetectionService().detect_equipment(
        specifications=[
            make_specification(
                "Lighting Console",
                section_number="11 61 00",
            )
        ]
    )

    assert "detected-lighting-console" in equipment_ids(equipment)


def test_detects_intercom():
    equipment = EquipmentDetectionService().detect_equipment(
        drawings=[make_drawing("Backstage Intercom Stations")]
    )

    assert "detected-intercom" in equipment_ids(equipment)


def test_detects_assisted_listening():
    equipment = EquipmentDetectionService().detect_equipment(
        specifications=[make_specification("Assisted Listening System")]
    )

    assert "detected-assisted-listening" in equipment_ids(equipment)


def test_detects_rack():
    equipment = EquipmentDetectionService().detect_equipment(
        drawings=[make_drawing("Equipment Rack Elevation")]
    )

    assert "detected-rack" in equipment_ids(equipment)


def test_detects_drapery():
    equipment = EquipmentDetectionService().detect_equipment(
        specifications=[
            make_specification(
                "Stage Curtains and Drapery",
                section_number="11 61 33",
            )
        ]
    )

    assert "detected-drapery" in equipment_ids(equipment)


def test_avoids_duplicates():
    equipment = EquipmentDetectionService().detect_equipment(
        drawings=[make_drawing("Digital Signage Plan")],
        specifications=[make_specification("Display Systems")],
    )

    assert equipment_ids(equipment).count("detected-display") == 1


def test_passes_room_id_building_id_and_system_id_into_detected_equipment():
    equipment = EquipmentDetectionService().detect_equipment(
        drawings=[make_drawing("Main Loudspeaker Plan")],
        room_id="room-001",
        building_id="building-001",
        system_id="system-001",
    )

    assert equipment[0].room_id == "room-001"
    assert equipment[0].building_id == "building-001"
    assert equipment[0].system_id == "system-001"


def test_empty_inputs_return_empty_list():
    assert EquipmentDetectionService().detect_equipment() == []

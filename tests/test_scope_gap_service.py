from atlas_core.domain import Equipment, EquipmentCategory
from atlas_core.services import (
    CrossReference,
    ScopeGap,
    ScopeGapService,
    ScopeGapSeverity,
)


def make_equipment(
    equipment_id: str,
    category: EquipmentCategory,
    room_id: str | None = None,
    system_id: str | None = None,
) -> Equipment:
    return Equipment(
        equipment_id=equipment_id,
        description=equipment_id,
        category=category,
        room_id=room_id,
        system_id=system_id,
    )


def test_projector_without_mount_creates_high_severity_gap():
    projector = make_equipment(
        "projector-001",
        EquipmentCategory.PROJECTOR,
        room_id="room-001",
    )

    gaps = ScopeGapService().detect_gaps(equipment=[projector])

    assert len(gaps) == 1
    assert gaps[0].gap_id == "projector_missing_mount"
    assert gaps[0].target_id == "projector-001"
    assert gaps[0].severity is ScopeGapSeverity.HIGH


def test_display_without_mount_creates_medium_severity_gap():
    display = make_equipment(
        "display-001",
        EquipmentCategory.DISPLAY,
        room_id="room-001",
    )

    gaps = ScopeGapService().detect_gaps(equipment=[display])

    assert len(gaps) == 1
    assert gaps[0].gap_id == "display_missing_mount"
    assert gaps[0].severity is ScopeGapSeverity.MEDIUM


def test_speaker_without_amplifier_creates_high_severity_gap():
    speaker = make_equipment(
        "speaker-001",
        EquipmentCategory.SPEAKER,
        system_id="system-001",
    )

    gaps = ScopeGapService().detect_gaps(equipment=[speaker])

    assert len(gaps) == 1
    assert gaps[0].gap_id == "speaker_missing_amplifier"
    assert gaps[0].severity is ScopeGapSeverity.HIGH


def test_no_speaker_gap_when_amplifier_exists_in_same_system():
    speaker = make_equipment(
        "speaker-001",
        EquipmentCategory.SPEAKER,
        system_id="system-001",
    )
    amplifier = make_equipment(
        "amplifier-001",
        EquipmentCategory.AMPLIFIER,
        system_id="system-001",
    )

    gaps = ScopeGapService().detect_gaps(equipment=[speaker, amplifier])

    assert gaps == []


def test_drapery_without_cross_reference_creates_high_severity_gap():
    drapery = make_equipment(
        "drapery-001",
        EquipmentCategory.DRAPERY,
        room_id="room-001",
    )

    gaps = ScopeGapService().detect_gaps(equipment=[drapery])

    assert len(gaps) == 1
    assert gaps[0].gap_id == "drapery_missing_cross_reference"
    assert gaps[0].severity is ScopeGapSeverity.HIGH


def test_empty_inputs_return_empty_list():
    assert ScopeGapService().detect_gaps() == []


def test_duplicate_gaps_are_avoided():
    speaker = make_equipment(
        "speaker-001",
        EquipmentCategory.SPEAKER,
        system_id="system-001",
    )

    gaps = ScopeGapService().detect_gaps(equipment=[speaker, speaker])

    assert len(gaps) == 1
    assert gaps[0].gap_id == "speaker_missing_amplifier"


def test_to_dict_output():
    gap = ScopeGap(
        gap_id="speaker_missing_amplifier",
        target_id="speaker-001",
        message="Speaker equipment is present.",
        severity="high",
        confidence=0.9,
        suggested_action="Add amplifier.",
    )

    assert gap.to_dict() == {
        "gap_id": "speaker_missing_amplifier",
        "target_id": "speaker-001",
        "message": "Speaker equipment is present.",
        "severity": "high",
        "confidence": 0.9,
        "suggested_action": "Add amplifier.",
    }


def test_drapery_with_cross_reference_does_not_create_gap():
    drapery = make_equipment(
        "drapery-001",
        EquipmentCategory.DRAPERY,
        room_id="room-001",
    )
    cross_reference = CrossReference(
        reference_type="equipment_to_drawing",
        source_id="drapery-001",
        target_id="a701",
        message="Drapery references drawing.",
    )

    gaps = ScopeGapService().detect_gaps(
        equipment=[drapery],
        cross_references=[cross_reference],
    )

    assert gaps == []

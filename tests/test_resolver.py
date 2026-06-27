from atlas_core.domain import Equipment, EquipmentCategory
from atlas_core.rules import ResolutionAction, Resolver


def test_speaker_without_amplifier_creates_amplifier_placeholder_resolution():
    speaker = Equipment(
        equipment_id="eq-speaker",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
        system_id="sys-001",
    )

    resolutions = Resolver().resolve([speaker])

    assert len(resolutions) == 1
    assert resolutions[0].rule_id == "RULE-001"
    assert resolutions[0].action is ResolutionAction.ADD_PLACEHOLDER
    assert resolutions[0].target_id == "eq-speaker"
    assert resolutions[0].suggested_category == "amplifier"


def test_speaker_with_amplifier_in_same_system_does_not_create_placeholder():
    speaker = Equipment(
        equipment_id="eq-speaker",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
        system_id="sys-001",
    )
    amplifier = Equipment(
        equipment_id="eq-amplifier",
        description="Amplifier",
        category=EquipmentCategory.AMPLIFIER,
        system_id="sys-001",
    )

    assert Resolver().resolve([speaker, amplifier]) == []


def test_speaker_without_system_id_does_not_create_placeholder():
    speaker = Equipment(
        equipment_id="eq-speaker",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
    )

    assert Resolver().resolve([speaker]) == []


def test_display_without_mount_in_same_room_creates_chief_mount_placeholder():
    display = Equipment(
        equipment_id="eq-display",
        description="Display",
        category=EquipmentCategory.DISPLAY,
        room_id="room-001",
    )

    resolutions = Resolver().resolve([display])

    assert len(resolutions) == 1
    assert resolutions[0].rule_id == "RULE-002"
    assert resolutions[0].action is ResolutionAction.ADD_PLACEHOLDER
    assert resolutions[0].suggested_category == "mount"
    assert resolutions[0].suggested_manufacturer == "Chief"


def test_display_without_room_id_does_not_create_placeholder():
    display = Equipment(
        equipment_id="eq-display",
        description="Display",
        category=EquipmentCategory.DISPLAY,
    )

    assert Resolver().resolve([display]) == []


def test_projector_without_mount_in_same_room_creates_chief_mount_placeholder():
    projector = Equipment(
        equipment_id="eq-projector",
        description="Projector",
        category=EquipmentCategory.PROJECTOR,
        room_id="room-001",
    )

    resolutions = Resolver().resolve([projector])

    assert len(resolutions) == 1
    assert resolutions[0].rule_id == "RULE-003"
    assert resolutions[0].action is ResolutionAction.ADD_PLACEHOLDER
    assert resolutions[0].suggested_category == "mount"
    assert resolutions[0].suggested_manufacturer == "Chief"


def test_projector_without_room_id_does_not_create_placeholder():
    projector = Equipment(
        equipment_id="eq-projector",
        description="Projector",
        category=EquipmentCategory.PROJECTOR,
    )

    assert Resolver().resolve([projector]) == []


def test_drapery_creates_review_resolution():
    drapery = Equipment(
        equipment_id="eq-drapery",
        description="Motorized Drapery",
        category=EquipmentCategory.DRAPERY,
    )

    resolutions = Resolver().resolve([drapery])

    assert len(resolutions) == 1
    assert resolutions[0].rule_id == "RULE-004"
    assert resolutions[0].action is ResolutionAction.MARK_FOR_REVIEW


def test_low_confidence_equipment_creates_review_resolution():
    equipment = Equipment(
        equipment_id="eq-low-confidence",
        description="Unknown Device",
        category=EquipmentCategory.UNKNOWN,
        confidence=0.5,
    )

    resolutions = Resolver().resolve([equipment])

    assert len(resolutions) == 1
    assert resolutions[0].rule_id == "RULE-005"
    assert resolutions[0].action is ResolutionAction.MARK_FOR_REVIEW


def test_duplicate_resolutions_are_not_emitted():
    display = Equipment(
        equipment_id="eq-display",
        description="Display",
        category=EquipmentCategory.DISPLAY,
        room_id="room-001",
    )

    resolutions = Resolver().resolve([display, display])

    assert len(resolutions) == 1
    assert resolutions[0].rule_id == "RULE-002"
    assert resolutions[0].target_id == "eq-display"

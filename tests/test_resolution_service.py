from atlas_core.domain import EquipmentCategory, EquipmentStatus
from atlas_core.rules import Resolution, ResolutionAction
from atlas_core.services import ResolutionService


def test_creating_placeholder_equipment_from_add_placeholder_resolution():
    resolution = Resolution(
        rule_id="RULE-001",
        action=ResolutionAction.ADD_PLACEHOLDER,
        target_id="eq-speaker",
        message="Passive speakers require an amplifier.",
        confidence=0.82,
        suggested_category="amplifier",
        suggested_manufacturer="QSC",
        suggested_model="CX-Q",
        source_system_id="sys-001",
        source_room_id="room-001",
        source_building_id="building-001",
    )

    equipment = ResolutionService().create_placeholder_equipment([resolution])

    assert len(equipment) == 1
    assert equipment[0].equipment_id == "placeholder-rule-001-eq-speaker"
    assert equipment[0].description == "Passive speakers require an amplifier."
    assert equipment[0].category is EquipmentCategory.AMPLIFIER
    assert equipment[0].manufacturer == "QSC"
    assert equipment[0].model == "CX-Q"
    assert equipment[0].system_id == "sys-001"
    assert equipment[0].room_id == "room-001"
    assert equipment[0].building_id == "building-001"
    assert equipment[0].status is EquipmentStatus.PLACEHOLDER
    assert equipment[0].quantity == 1
    assert equipment[0].confidence == 0.82
    assert equipment[0].assumptions == ["Passive speakers require an amplifier."]
    assert equipment[0].review_required is True


def test_ignoring_mark_for_review_resolutions():
    resolution = Resolution(
        rule_id="RULE-005",
        action=ResolutionAction.MARK_FOR_REVIEW,
        target_id="eq-low-confidence",
        message="Equipment confidence is below threshold.",
    )

    assert ResolutionService().create_placeholder_equipment([resolution]) == []


def test_using_suggested_description_when_present():
    resolution = Resolution(
        rule_id="RULE-002",
        action=ResolutionAction.ADD_PLACEHOLDER,
        target_id="eq-display",
        message="Display requires a mount.",
        suggested_category="mount",
        suggested_description="Display mounting allowance",
    )

    equipment = ResolutionService().create_placeholder_equipment([resolution])

    assert equipment[0].description == "Display mounting allowance"


def test_falling_back_to_unknown_category_when_invalid():
    resolution = Resolution(
        rule_id="RULE-999",
        action=ResolutionAction.ADD_PLACEHOLDER,
        target_id="eq-invalid",
        message="Invalid placeholder category.",
        suggested_category="not-a-category",
    )

    equipment = ResolutionService().create_placeholder_equipment([resolution])

    assert equipment[0].category is EquipmentCategory.UNKNOWN


def test_avoiding_duplicate_placeholder_equipment():
    resolution = Resolution(
        rule_id="RULE-002",
        action=ResolutionAction.ADD_PLACEHOLDER,
        target_id="eq-display",
        message="Display requires a mount.",
        suggested_category="mount",
    )

    equipment = ResolutionService().create_placeholder_equipment(
        [resolution, resolution]
    )

    assert len(equipment) == 1
    assert equipment[0].equipment_id == "placeholder-rule-002-eq-display"

import pytest

from atlas_core.domain import Equipment, EquipmentCategory, EquipmentStatus


def test_creating_valid_equipment():
    equipment = Equipment(
        equipment_id=" eq-001 ",
        description=" Ceiling Speaker ",
        category=EquipmentCategory.SPEAKER,
    )

    assert equipment.equipment_id == "eq-001"
    assert equipment.description == "Ceiling Speaker"
    assert equipment.category is EquipmentCategory.SPEAKER
    assert equipment.quantity == 1
    assert equipment.status is EquipmentStatus.DETECTED
    assert equipment.confidence == 0.75
    assert not equipment.review_required


def test_accepting_string_category_and_status():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category="speaker",
        status="approved",
    )

    assert equipment.category is EquipmentCategory.SPEAKER
    assert equipment.status is EquipmentStatus.APPROVED


def test_rejecting_blank_description():
    with pytest.raises(ValueError, match="description cannot be blank"):
        Equipment(
            equipment_id="eq-001",
            description=" ",
            category=EquipmentCategory.SPEAKER,
        )


def test_rejecting_invalid_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        Equipment(
            equipment_id="eq-001",
            description="Ceiling Speaker",
            category=EquipmentCategory.SPEAKER,
            quantity=0,
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        Equipment(
            equipment_id="eq-001",
            description="Ceiling Speaker",
            category=EquipmentCategory.SPEAKER,
            confidence=1.1,
        )


def test_rejecting_negative_pricing():
    with pytest.raises(ValueError, match="budget_cost cannot be negative"):
        Equipment(
            equipment_id="eq-001",
            description="Ceiling Speaker",
            category=EquipmentCategory.SPEAKER,
            budget_cost=-1,
        )

    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
    )

    with pytest.raises(ValueError, match="sell_price cannot be negative"):
        equipment.set_pricing(100, -1)


def test_setting_pricing():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
    )

    equipment.set_pricing(100.0, 150.0)

    assert equipment.budget_cost == 100.0
    assert equipment.sell_price == 150.0
    assert equipment.status is EquipmentStatus.PRICED


def test_setting_pricing_defaults_sell_price_to_budget_cost():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
    )

    equipment.set_pricing(100.0)

    assert equipment.budget_cost == 100.0
    assert equipment.sell_price == 100.0
    assert equipment.status is EquipmentStatus.PRICED


def test_adding_assumptions():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
    )

    equipment.add_assumption(" Existing cabling can be reused. ")
    equipment.add_assumption("Verify ceiling type.")

    assert equipment.assumptions == [
        "Existing cabling can be reused.",
        "Verify ceiling type.",
    ]


def test_mark_placeholder_without_reason():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
    )

    equipment.mark_placeholder()

    assert equipment.status is EquipmentStatus.PLACEHOLDER
    assert equipment.assumptions == []


def test_mark_placeholder_with_reason():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
    )

    equipment.mark_placeholder(" Confirm final model. ")

    assert equipment.status is EquipmentStatus.PLACEHOLDER
    assert equipment.assumptions == ["Confirm final model."]


def test_mark_for_review_without_reason():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
    )

    equipment.mark_for_review()

    assert equipment.review_required
    assert equipment.assumptions == []


def test_mark_for_review_with_reason():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
    )

    equipment.mark_for_review(" Verify quantity against reflected ceiling plan. ")

    assert equipment.review_required
    assert equipment.assumptions == [
        "Verify quantity against reflected ceiling plan.",
    ]


def test_to_dict_output():
    equipment = Equipment(
        equipment_id="eq-001",
        description="Ceiling Speaker",
        category=EquipmentCategory.SPEAKER,
        quantity=4,
        manufacturer="QSC",
        model="AD-C6T",
        system_id="sys-001",
        room_id="room-001",
        building_id="building-001",
        labor_template="speaker-ceiling",
        drawing_reference="A701",
        specification_reference="27 41 16",
        confidence=0.84,
    )
    equipment.set_pricing(100.0, 150.0)
    equipment.add_assumption("Existing cabling can be reused.")
    equipment.mark_for_review("Verify ceiling type.")

    assert equipment.to_dict() == {
        "equipment_id": "eq-001",
        "description": "Ceiling Speaker",
        "category": "speaker",
        "quantity": 4,
        "manufacturer": "QSC",
        "model": "AD-C6T",
        "system_id": "sys-001",
        "room_id": "room-001",
        "building_id": "building-001",
        "status": "priced",
        "budget_cost": 100.0,
        "sell_price": 150.0,
        "labor_template": "speaker-ceiling",
        "drawing_reference": "A701",
        "specification_reference": "27 41 16",
        "confidence": 0.84,
        "assumptions": [
            "Existing cabling can be reused.",
            "Verify ceiling type.",
        ],
        "review_required": True,
    }

from atlas_core.domain import BidPackageReview, Equipment, EquipmentCategory
from atlas_core.rules import (
    DMXDistributionRule,
    EmergencyLightingCoordinationRule,
    EngineeringRuleRegistry,
    HouseLightingInterfaceRule,
    LightingConsoleNetworkRule,
    LightingFixtureSafetyCableRule,
    LightingPowerRule,
    register_lighting_rules,
)


def make_review(equipment: list[Equipment] | None = None) -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        equipment=list(equipment or []),
    )


def test_lighting_fixture_safety_cable_rule_triggers_without_safety_reference():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-fixture",
                description="Pendant fixture",
                category=EquipmentCategory.LIGHTING_FIXTURE,
            )
        ]
    )

    assumptions = LightingFixtureSafetyCableRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "lighting_fixture_safety_missing_eq-fixture"
    assert assumptions[0].category == "safety"


def test_lighting_console_network_rule_triggers_without_network_reference():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-console",
                description="Lighting console",
                category=EquipmentCategory.LIGHTING_CONSOLE,
            )
        ]
    )

    assumptions = LightingConsoleNetworkRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "lighting_console_network_missing_eq-console"
    assert assumptions[0].category == "control"


def test_lighting_power_rule_triggers_without_power_reference():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-fixture",
                description="Pendant fixture",
                category=EquipmentCategory.LIGHTING_FIXTURE,
            )
        ]
    )

    assumptions = LightingPowerRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "lighting_power_missing_eq-fixture"
    assert assumptions[0].category == "power"


def test_dmx_distribution_rule_triggers_when_distribution_not_identified():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-fixture",
                description="Stage fixture",
                category=EquipmentCategory.LIGHTING_FIXTURE,
            )
        ]
    )

    assumptions = DMXDistributionRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "lighting_distribution_missing_eq-fixture"
    assert assumptions[0].category == "control"


def test_house_lighting_interface_rule_triggers_without_integration_reference():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-console",
                description="Lighting console",
                category=EquipmentCategory.LIGHTING_CONSOLE,
            )
        ]
    )

    assumptions = HouseLightingInterfaceRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "lighting_house_interface_missing_eq-console"
    assert assumptions[0].category == "integration"


def test_emergency_lighting_coordination_rule_triggers_without_life_safety_reference():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-fixture",
                description="House lighting fixture",
                category=EquipmentCategory.LIGHTING_FIXTURE,
            )
        ]
    )

    assumptions = EmergencyLightingCoordinationRule().generate(review)

    assert len(assumptions) == 1
    assert (
        assumptions[0].assumption_id
        == "lighting_emergency_coordination_missing_eq-fixture"
    )
    assert assumptions[0].category == "life_safety"


def test_register_lighting_rules_registers_all_rules():
    registry = EngineeringRuleRegistry()

    register_lighting_rules(registry)

    assert [rule.rule_id for rule in registry.rules()] == [
        "lighting_fixture_safety_cable",
        "lighting_console_network",
        "lighting_power",
        "lighting_dmx_distribution",
        "lighting_house_interface",
        "lighting_emergency_coordination",
    ]


def test_prevents_duplicate_assumptions_with_same_assumption_id():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-fixture",
                description="Pendant fixture",
                category=EquipmentCategory.LIGHTING_FIXTURE,
            ),
            Equipment(
                equipment_id="eq-fixture",
                description="Pendant fixture duplicate",
                category=EquipmentCategory.LIGHTING_FIXTURE,
            ),
        ]
    )

    assumptions = LightingFixtureSafetyCableRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "lighting_fixture_safety_missing_eq-fixture"


def test_lighting_rules_do_not_match_when_inputs_are_complete():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-fixture",
                description="Pendant fixture with safety cable and clamp",
                category=EquipmentCategory.LIGHTING_FIXTURE,
                assumptions=[
                    "Rigging and mounting by vendor",
                    "Power circuit by dimmer distribution",
                    "Emergency egress and UL924 coordination",
                ],
            ),
            Equipment(
                equipment_id="eq-console",
                description="Lighting console",
                category=EquipmentCategory.LIGHTING_CONSOLE,
                assumptions=[
                    "Control via DMX and sACN over network",
                    "House lighting integration via relay/dimmer",
                ],
            ),
            Equipment(
                equipment_id="eq-node",
                description="Art-Net gateway node distribution",
                category=EquipmentCategory.ACCESSORY,
            ),
        ]
    )

    assert LightingFixtureSafetyCableRule().matches(review) is False
    assert LightingConsoleNetworkRule().matches(review) is False
    assert LightingPowerRule().matches(review) is False
    assert DMXDistributionRule().matches(review) is False
    assert HouseLightingInterfaceRule().matches(review) is False
    assert EmergencyLightingCoordinationRule().matches(review) is False

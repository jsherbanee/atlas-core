from atlas_core.domain import (
    BidPackageReview,
    DetailCallout,
    Equipment,
    EquipmentCategory,
)
from atlas_core.rules import (
    BackingRule,
    CablePathwayRule,
    ConduitRule,
    EngineeringRuleRegistry,
    GroundingRule,
    RackCoolingRule,
    RackElevationRule,
    RackPowerRule,
    UPSRule,
    register_infrastructure_rules,
)


def make_review(
    equipment: list[Equipment] | None = None,
    detail_callouts: list[DetailCallout] | None = None,
) -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        equipment=list(equipment or []),
        detail_callouts=list(detail_callouts or []),
    )


def test_conduit_rule_generates_assumption_when_conduit_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-cable",
                description="Category cable run",
                category=EquipmentCategory.CABLE,
            )
        ]
    )

    assumptions = ConduitRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "infrastructure_conduit_missing_eq-cable"


def test_backing_rule_generates_assumption_when_backing_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display",
                description="Wall display",
                category=EquipmentCategory.DISPLAY,
            )
        ]
    )

    assumptions = BackingRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "infrastructure_backing_missing_eq-display"


def test_rack_cooling_rule_generates_assumption_when_cooling_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-rack",
                description="Main rack",
                category=EquipmentCategory.RACK,
            )
        ]
    )

    assumptions = RackCoolingRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "infrastructure_rack_cooling_missing_eq-rack"


def test_rack_power_rule_generates_assumption_when_power_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-rack",
                description="Main rack",
                category=EquipmentCategory.RACK,
            )
        ]
    )

    assumptions = RackPowerRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "infrastructure_rack_power_missing_eq-rack"


def test_rack_elevation_rule_generates_assumption_when_elevation_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-rack",
                description="Main rack",
                category=EquipmentCategory.RACK,
            )
        ]
    )

    assumptions = RackElevationRule().generate(review)

    assert len(assumptions) == 1
    assert (
        assumptions[0].assumption_id == "infrastructure_rack_elevation_missing_eq-rack"
    )


def test_ups_rule_generates_assumption_when_ups_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-rack",
                description="Main rack",
                category=EquipmentCategory.RACK,
            )
        ]
    )

    assumptions = UPSRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "infrastructure_ups_missing_eq-rack"


def test_grounding_rule_generates_assumption_when_grounding_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-rack",
                description="Main rack",
                category=EquipmentCategory.RACK,
            )
        ]
    )

    assumptions = GroundingRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "infrastructure_grounding_missing_eq-rack"


def test_cable_pathway_rule_generates_assumption_when_pathway_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-cable",
                description="Category cable run",
                category=EquipmentCategory.CABLE,
            )
        ]
    )

    assumptions = CablePathwayRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "infrastructure_pathway_missing_eq-cable"


def test_register_infrastructure_rules_registers_all_rules():
    registry = EngineeringRuleRegistry()

    register_infrastructure_rules(registry)

    assert [rule.rule_id for rule in registry.rules()] == [
        "infrastructure_conduit",
        "infrastructure_backing",
        "infrastructure_rack_cooling",
        "infrastructure_rack_power",
        "infrastructure_rack_elevation",
        "infrastructure_ups",
        "infrastructure_grounding",
        "infrastructure_cable_pathway",
    ]


def test_infrastructure_rules_do_not_match_when_inputs_are_complete():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display",
                description="Wall display",
                category=EquipmentCategory.DISPLAY,
            ),
            Equipment(
                equipment_id="eq-rack",
                description="Main rack with cooling and power",
                category=EquipmentCategory.RACK,
                assumptions=[
                    "Cooling and ventilation by mechanical",
                    "Power by dedicated 120V circuit",
                    "Ground bonding by EC",
                ],
            ),
            Equipment(
                equipment_id="eq-cable",
                description="Cable in conduit and tray pathway",
                category=EquipmentCategory.CABLE,
                assumptions=["Conduit and cable tray pathway by EC"],
            ),
            Equipment(
                equipment_id="eq-ups",
                description="UPS battery backup",
                category=EquipmentCategory.ACCESSORY,
            ),
        ],
        detail_callouts=[
            DetailCallout(
                callout_id="callout-001",
                detail_number="1",
                source_sheet_number="AV-101",
                equipment_category="rack elevation",
                description="Rack elevation with backing and support",
            )
        ],
    )

    assert ConduitRule().matches(review) is False
    assert BackingRule().matches(review) is False
    assert RackCoolingRule().matches(review) is False
    assert RackPowerRule().matches(review) is False
    assert RackElevationRule().matches(review) is False
    assert UPSRule().matches(review) is False
    assert GroundingRule().matches(review) is False
    assert CablePathwayRule().matches(review) is False

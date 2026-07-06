from atlas_core.domain import (
    BidPackageReview,
    DetailCallout,
    Equipment,
    EquipmentCategory,
)
from atlas_core.rules import (
    EngineeringRuleRegistry,
    ProjectionCoolingRule,
    ProjectionPowerRule,
    ProjectionStructureRule,
    ProjectorLensRule,
    ProjectorMountRule,
    register_projection_rules,
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


def test_projector_mount_rule_generates_assumption_without_mount_detail():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            )
        ]
    )

    rule = ProjectorMountRule()

    assert rule.matches(review) is True
    assumptions = rule.generate(review)
    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "projection_mount_missing_eq-projector"


def test_projector_lens_rule_generates_assumption_when_lens_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            )
        ]
    )

    assumptions = ProjectorLensRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "projection_lens_missing_eq-projector"


def test_projection_power_rule_generates_assumption_when_power_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            )
        ]
    )

    assumptions = ProjectionPowerRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "projection_power_missing_eq-projector"


def test_projection_structure_rule_generates_assumption_when_structure_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            )
        ]
    )

    assumptions = ProjectionStructureRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "projection_structure_missing_eq-projector"


def test_projection_cooling_rule_generates_assumption_when_cooling_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            )
        ]
    )

    assumptions = ProjectionCoolingRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "projection_cooling_missing_eq-projector"


def test_register_projection_rules_registers_all_rules():
    registry = EngineeringRuleRegistry()

    register_projection_rules(registry)

    assert [rule.rule_id for rule in registry.rules()] == [
        "projection_projector_mount",
        "projection_projector_lens",
        "projection_power",
        "projection_structure",
        "projection_cooling",
    ]


def test_projector_rules_do_not_match_when_projection_inputs_are_complete():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector with lens and throw",
                category=EquipmentCategory.PROJECTOR,
                assumptions=[
                    "Power by dedicated 120V circuit",
                    "Cooling and ventilation by mechanical",
                ],
            )
        ],
        detail_callouts=[
            DetailCallout(
                callout_id="callout-001",
                detail_number="5",
                source_sheet_number="AV-101",
                equipment_category="mount",
                description="Structural support and blocking requirements",
            )
        ],
    )

    assert ProjectorMountRule().matches(review) is False
    assert ProjectorLensRule().matches(review) is False
    assert ProjectionPowerRule().matches(review) is False
    assert ProjectionStructureRule().matches(review) is False
    assert ProjectionCoolingRule().matches(review) is False

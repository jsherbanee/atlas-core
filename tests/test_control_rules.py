from atlas_core.domain import BidPackageReview, Equipment, EquipmentCategory
from atlas_core.rules import (
    ControlProgrammingRule,
    EngineeringRuleRegistry,
    register_control_rules,
)


def make_review(equipment: list[Equipment] | None = None) -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        equipment=list(equipment or []),
    )


def test_control_programming_rule_triggers_for_control_processor_without_programming():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-control",
                description="Main control processor",
                category=EquipmentCategory.CONTROL_PROCESSOR,
            )
        ]
    )

    assumptions = ControlProgrammingRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "audio_programming_missing_eq-control"
    assert assumptions[0].category == "programming"


def test_control_programming_rule_does_not_trigger_with_programming_reference():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-control",
                description="Main control processor",
                category=EquipmentCategory.CONTROL_PROCESSOR,
                assumptions=["Programming by integrator"],
            )
        ]
    )

    assert ControlProgrammingRule().matches(review) is False


def test_register_control_rules_registers_all_rules():
    registry = EngineeringRuleRegistry()

    register_control_rules(registry)

    assert [rule.rule_id for rule in registry.rules()] == ["control_programming"]

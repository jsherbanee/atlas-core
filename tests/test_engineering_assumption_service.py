from typing import Any

from atlas_core.domain import (
    BidPackageReview,
    DetailCallout,
    Equipment,
    EquipmentCategory,
)
from atlas_core.rules import (
    EngineeringRuleEngine,
    EngineeringRuleRegistry,
    register_default_engineering_rules,
)
from atlas_core.services import EngineeringAssumptionService


def make_review(**overrides: Any) -> BidPackageReview:
    values: dict[str, Any] = {
        "review_id": "review-001",
        "project_id": "project-001",
        "name": "Plan Review",
    }
    values.update(overrides)
    return BidPackageReview(**values)


def assumption_ids(assumptions: list) -> list[str]:
    return [assumption.assumption_id for assumption in assumptions]


def build_default_engine() -> EngineeringRuleEngine:
    registry = EngineeringRuleRegistry()
    register_default_engineering_rules(registry)
    return EngineeringRuleEngine(registry)


def test_build_matches_engine_evaluation_for_same_review():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            ),
            Equipment(
                equipment_id="eq-ptz",
                description="PTZ camera",
                category=EquipmentCategory.CAMERA,
            ),
        ]
    )

    engine = build_default_engine()
    service = EngineeringAssumptionService(engineering_rule_engine=engine)

    assert assumption_ids(service.build(review)) == assumption_ids(
        engine.evaluate(review)
    )


def test_generates_assumptions_through_registered_rule_modules():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            ),
            Equipment(
                equipment_id="eq-display",
                description="Main display",
                category=EquipmentCategory.DISPLAY,
            ),
            Equipment(
                equipment_id="eq-control",
                description="Main control processor",
                category=EquipmentCategory.CONTROL_PROCESSOR,
            ),
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)
    ids = set(assumption_ids(assumptions))

    assert "projection_mount_missing_eq-projector" in ids
    assert "video_display_mount_missing_eq-display" in ids
    assert "audio_programming_missing_eq-control" in ids


def test_missing_review_fields_do_not_crash():
    class MinimalReview:
        pass

    assumptions = EngineeringAssumptionService().build(MinimalReview())

    assert assumptions == []


def test_returns_empty_for_clean_review():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Projector with lens and throw and power and cooling",
                category=EquipmentCategory.PROJECTOR,
                assumptions=[
                    "Lens package confirmed",
                    "120V power confirmed",
                    "Cooling ventilation complete",
                    "Structure and support verified",
                ],
            ),
            Equipment(
                equipment_id="eq-mount",
                description="Projector mount",
                category=EquipmentCategory.MOUNT,
            ),
            Equipment(
                equipment_id="eq-control",
                description="Main control processor",
                category=EquipmentCategory.CONTROL_PROCESSOR,
                assumptions=["Programming by integrator"],
            ),
        ],
        detail_callouts=[
            DetailCallout(
                callout_id="callout-001",
                detail_number="1",
                source_sheet_number="AV-101",
                equipment_category="mount",
                description="Mounting and structural support detail",
            )
        ],
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert assumptions == []

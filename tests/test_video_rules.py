from atlas_core.domain import (
    BidPackageReview,
    DetailCallout,
    Equipment,
    EquipmentCategory,
)
from atlas_core.rules import (
    CameraPowerRule,
    DisplayMountRule,
    EngineeringRuleRegistry,
    PTZConnectivityRule,
    ProjectionScreenSupportRule,
    VideoWallStructureRule,
    register_video_rules,
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


def test_display_mount_rule_triggers_without_mounting_detail():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display",
                description="Main display",
                category=EquipmentCategory.DISPLAY,
            )
        ]
    )

    assumptions = DisplayMountRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "video_display_mount_missing_eq-display"
    assert assumptions[0].description == "Display mounting solution should be verified."


def test_ptz_connectivity_rule_triggers_without_usb_ip_control_reference():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-ptz",
                description="PTZ camera",
                category=EquipmentCategory.CAMERA,
            )
        ]
    )

    assumptions = PTZConnectivityRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "video_ptz_connectivity_missing_eq-ptz"
    assert assumptions[0].description == "PTZ camera connectivity should be verified."


def test_camera_power_rule_triggers_when_power_reference_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-cam",
                description="Fixed camera",
                category=EquipmentCategory.CAMERA,
            )
        ]
    )

    assumptions = CameraPowerRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "video_camera_power_missing_eq-cam"
    assert (
        assumptions[0].description == "Camera power requirements should be confirmed."
    )


def test_video_wall_structure_rule_triggers_without_structure_detail():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-vw-1",
                description="Video wall panel",
                category=EquipmentCategory.DISPLAY,
            )
        ]
    )

    assumptions = VideoWallStructureRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "video_wall_structure_missing_eq-vw-1"
    assert (
        assumptions[0].description
        == "Video wall structural support should be reviewed."
    )


def test_projection_screen_support_rule_triggers_without_mounting_detail():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-screen",
                description="Projection screen",
                category=EquipmentCategory.PROJECTION_SCREEN,
            )
        ]
    )

    assumptions = ProjectionScreenSupportRule().generate(review)

    assert len(assumptions) == 1
    assert (
        assumptions[0].assumption_id
        == "video_projection_screen_support_missing_eq-screen"
    )
    assert (
        assumptions[0].description
        == "Projection screen support and mounting should be confirmed."
    )


def test_register_video_rules_registers_all_rules():
    registry = EngineeringRuleRegistry()

    register_video_rules(registry)

    assert [rule.rule_id for rule in registry.rules()] == [
        "video_display_mount",
        "video_ptz_connectivity",
        "video_camera_power",
        "video_wall_structure",
        "video_projection_screen_support",
    ]


def test_prevents_duplicate_assumptions_with_same_assumption_id():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display",
                description="Display A",
                category=EquipmentCategory.DISPLAY,
            ),
            Equipment(
                equipment_id="eq-display",
                description="Display B",
                category=EquipmentCategory.DISPLAY,
            ),
        ]
    )

    assumptions = DisplayMountRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "video_display_mount_missing_eq-display"


def test_video_rules_do_not_match_when_inputs_are_complete():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display",
                description="Main display",
                category=EquipmentCategory.DISPLAY,
            ),
            Equipment(
                equipment_id="eq-ptz",
                description="PTZ camera",
                category=EquipmentCategory.CAMERA,
                assumptions=["IP control, USB bridge, and power by PoE"],
            ),
            Equipment(
                equipment_id="eq-cam",
                description="Fixed camera with power",
                category=EquipmentCategory.CAMERA,
                assumptions=["Power by PoE"],
            ),
            Equipment(
                equipment_id="eq-vw-1",
                description="Video wall panel",
                category=EquipmentCategory.DISPLAY,
            ),
            Equipment(
                equipment_id="eq-screen",
                description="Projection screen",
                category=EquipmentCategory.PROJECTION_SCREEN,
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

    assert DisplayMountRule().matches(review) is False
    assert PTZConnectivityRule().matches(review) is False
    assert CameraPowerRule().matches(review) is False
    assert VideoWallStructureRule().matches(review) is False
    assert ProjectionScreenSupportRule().matches(review) is False

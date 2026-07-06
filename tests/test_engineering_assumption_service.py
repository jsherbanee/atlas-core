from typing import Any

from atlas_core.domain import (
    AssumptionSeverity,
    BidPackageReview,
    DetailCallout,
    Equipment,
    EquipmentCategory,
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


def assumption_ids(assumptions):
    return [assumption.assumption_id for assumption in assumptions]


def test_projector_without_mount_detail_creates_review_assumption():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            )
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert "projector_mounting_detail_missing_eq-projector" in assumption_ids(
        assumptions
    )
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "projector_mounting_detail_missing_eq-projector"
    )
    assert assumption.severity is AssumptionSeverity.REVIEW
    assert assumption.description == (
        "No projector mounting hardware or mounting detail has been identified."
    )


def test_display_without_mount_detail_creates_review_assumption():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display",
                description="Main display",
                category=EquipmentCategory.DISPLAY,
            )
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert "display_mounting_detail_missing_eq-display" in assumption_ids(assumptions)
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "display_mounting_detail_missing_eq-display"
    )
    assert assumption.severity is AssumptionSeverity.REVIEW
    assert assumption.description == "Display mounting solution should be confirmed."


def test_rack_equipment_without_rack_detail_creates_risk_assumption():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-rack",
                description="Equipment rack",
                category=EquipmentCategory.RACK,
            )
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert "rack_detail_missing_eq-rack" in assumption_ids(assumptions)
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "rack_detail_missing_eq-rack"
    )
    assert assumption.severity is AssumptionSeverity.RISK
    assert assumption.description == "Equipment rack details should be confirmed."


def test_control_processor_creates_programming_assumption():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-control",
                description="Main control processor",
                category=EquipmentCategory.CONTROL_PROCESSOR,
            )
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert "programming_scope_unverified_eq-control" in assumption_ids(assumptions)
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "programming_scope_unverified_eq-control"
    )
    assert assumption.severity is AssumptionSeverity.REVIEW
    assert (
        assumption.description == "DSP or control programming scope should be verified."
    )


def test_wireless_microphones_without_antenna_creates_risk_assumption():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-mic",
                description="Wireless microphone handheld",
                category=EquipmentCategory.MICROPHONE,
            )
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert "wireless_microphone_antenna_unverified_eq-mic" in assumption_ids(
        assumptions
    )
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "wireless_microphone_antenna_unverified_eq-mic"
    )
    assert assumption.severity is AssumptionSeverity.RISK
    assert assumption.description == (
        "Wireless microphone antenna distribution should be reviewed."
    )


def test_ptz_cameras_without_connectivity_path_creates_review_assumption():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-ptz",
                description="PTZ camera",
                category=EquipmentCategory.CAMERA,
            )
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert "ptz_connectivity_unverified_eq-ptz" in assumption_ids(assumptions)
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "ptz_connectivity_unverified_eq-ptz"
    )
    assert assumption.severity is AssumptionSeverity.REVIEW
    assert assumption.description == "PTZ camera connectivity should be verified."


def test_equipment_without_specification_reference_creates_informational_assumption():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display",
                description="Main display",
                category=EquipmentCategory.DISPLAY,
            )
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert "equipment_specification_reference_missing_eq-display" in assumption_ids(
        assumptions
    )
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "equipment_specification_reference_missing_eq-display"
    )
    assert assumption.severity is AssumptionSeverity.INFORMATIONAL
    assert (
        assumption.description
        == "Equipment should be validated against specifications."
    )
    assert assumption.related_equipment == "eq-display"


def test_avoids_duplicates():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            ),
            Equipment(
                equipment_id="eq-projector",
                description="Main projector duplicate",
                category=EquipmentCategory.PROJECTOR,
            ),
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert (
        assumption_ids(assumptions).count(
            "projector_mounting_detail_missing_eq-projector"
        )
        == 1
    )


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
                description="Projector with mount detail",
                category=EquipmentCategory.PROJECTOR,
                specification_reference="27 41 16",
                assumptions=["Review completed"],
            ),
            Equipment(
                equipment_id="eq-mount",
                description="Projector mount",
                category=EquipmentCategory.MOUNT,
                specification_reference="27 41 16",
                assumptions=["Power coordination complete"],
            ),
            Equipment(
                equipment_id="eq-rack",
                description="Main AV rack",
                category=EquipmentCategory.RACK,
                specification_reference="27 41 16",
                assumptions=["Review completed"],
            ),
            Equipment(
                equipment_id="eq-dsp",
                description="DSP processor",
                category=EquipmentCategory.DSP,
                specification_reference="27 41 16",
                assumptions=["Programming by owner"],
            ),
            Equipment(
                equipment_id="eq-mic",
                description="Wireless microphone handheld",
                category=EquipmentCategory.MICROPHONE,
                specification_reference="27 41 16",
                assumptions=["Audio review completed"],
            ),
            Equipment(
                equipment_id="eq-antenna",
                description="Antenna distribution system",
                category=EquipmentCategory.ACCESSORY,
                specification_reference="27 41 16",
                assumptions=["Audio review completed"],
            ),
            Equipment(
                equipment_id="eq-ptz",
                description="PTZ camera",
                category=EquipmentCategory.CAMERA,
                specification_reference="27 41 16",
                assumptions=["Control and network path confirmed"],
            ),
        ],
        detail_callouts=[
            DetailCallout(
                callout_id="av-101-detail-5-av-701",
                detail_number="5",
                source_sheet_number="AV-101",
                target_sheet_number="AV-701",
                equipment_category="mount",
            ),
            DetailCallout(
                callout_id="av-101-detail-1-av-801",
                detail_number="1",
                source_sheet_number="AV-101",
                target_sheet_number="AV-801",
                equipment_category="rack",
            ),
        ],
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert assumptions == []

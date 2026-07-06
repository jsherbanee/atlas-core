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

    assert "projector_mounting_detail_missing" in assumption_ids(assumptions)
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "projector_mounting_detail_missing"
    )
    assert assumption.severity is AssumptionSeverity.REVIEW
    assert assumption.description == "No projector mounting hardware has been identified."


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

    assert "display_mounting_detail_missing" in assumption_ids(assumptions)
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "display_mounting_detail_missing"
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

    assert "rack_detail_missing" in assumption_ids(assumptions)
    assumption = next(item for item in assumptions if item.assumption_id == "rack_detail_missing")
    assert assumption.severity is AssumptionSeverity.RISK
    assert assumption.description == "Equipment rack details should be confirmed."


def test_dsp_without_programming_notes_creates_review_assumption():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-dsp",
                description="Q-SYS DSP",
                category=EquipmentCategory.DSP,
            )
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert "dsp_programming_scope_unverified" in assumption_ids(assumptions)
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "dsp_programming_scope_unverified"
    )
    assert assumption.severity is AssumptionSeverity.REVIEW
    assert assumption.description == "DSP programming scope should be verified."


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

    assert "wireless_microphone_antenna_unverified" in assumption_ids(assumptions)
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "wireless_microphone_antenna_unverified"
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

    assert "ptz_connectivity_unverified" in assumption_ids(assumptions)
    assumption = next(
        item for item in assumptions if item.assumption_id == "ptz_connectivity_unverified"
    )
    assert assumption.severity is AssumptionSeverity.REVIEW
    assert assumption.description == "PTZ camera connectivity should be verified."


def test_equipment_without_power_reference_creates_review_assumption():
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

    assert "equipment_power_reference_missing" in assumption_ids(assumptions)
    assumption = next(
        item for item in assumptions if item.assumption_id == "equipment_power_reference_missing"
    )
    assert assumption.severity is AssumptionSeverity.REVIEW
    assert assumption.description == "Power requirements should be confirmed."


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

    assert "equipment_specification_reference_missing" in assumption_ids(assumptions)
    assumption = next(
        item
        for item in assumptions
        if item.assumption_id == "equipment_specification_reference_missing"
    )
    assert assumption.severity is AssumptionSeverity.INFORMATIONAL
    assert assumption.description == "Equipment should be validated against specifications."


def test_avoids_duplicates():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector-1",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
            ),
            Equipment(
                equipment_id="eq-projector-2",
                description="Backup projector",
                category=EquipmentCategory.PROJECTOR,
            ),
        ]
    )

    assumptions = EngineeringAssumptionService().build(review)

    assert assumption_ids(assumptions).count("projector_mounting_detail_missing") == 1


def test_returns_empty_for_clean_review():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Projector with power and mount detail",
                category=EquipmentCategory.PROJECTOR,
                specification_reference="27 41 16",
                assumptions=["Power provided from AV rack"],
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
                assumptions=["Power from dedicated 120V circuit"],
            ),
            Equipment(
                equipment_id="eq-dsp",
                description="DSP processor",
                category=EquipmentCategory.DSP,
                specification_reference="27 41 16",
                assumptions=["Programming by owner with power by PoE"],
            ),
            Equipment(
                equipment_id="eq-mic",
                description="Wireless microphone handheld",
                category=EquipmentCategory.MICROPHONE,
                specification_reference="27 41 16",
                assumptions=["Power by battery"],
            ),
            Equipment(
                equipment_id="eq-antenna",
                description="Antenna distribution system",
                category=EquipmentCategory.ACCESSORY,
                specification_reference="27 41 16",
                assumptions=["Power from rack"],
            ),
            Equipment(
                equipment_id="eq-ptz",
                description="PTZ camera with network path",
                category=EquipmentCategory.CAMERA,
                specification_reference="27 41 16",
                assumptions=["Network via CAT6 and PoE"],
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

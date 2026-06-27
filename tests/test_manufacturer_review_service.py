from atlas_core.domain import (
    Equipment,
    EquipmentCategory,
    Manufacturer,
    ManufacturerDiscipline,
    ManufacturerTier,
)
from atlas_core.registry import ManufacturerRegistry
from atlas_core.services import (
    ManufacturerReviewIssue,
    ManufacturerReviewService,
)


def make_equipment(
    equipment_id: str = "eq-001",
    manufacturer: str | None = "QSC",
) -> Equipment:
    return Equipment(
        equipment_id=equipment_id,
        description="Display",
        category=EquipmentCategory.DISPLAY,
        manufacturer=manufacturer,
    )


def make_manufacturer(
    name: str = "QSC",
    tier: ManufacturerTier = ManufacturerTier.PREFERRED,
    active: bool = True,
) -> Manufacturer:
    return Manufacturer(
        manufacturer_id=name.lower().replace(" ", "-"),
        name=name,
        discipline=ManufacturerDiscipline.CONTROL,
        tier=tier,
        active=active,
    )


def review(
    equipment: list[Equipment],
    manufacturers: list[Manufacturer],
) -> list[ManufacturerReviewIssue]:
    return ManufacturerReviewService(
        ManufacturerRegistry(manufacturers)
    ).review_equipment(equipment)


def test_no_issue_for_preferred_registered_manufacturer():
    issues = review(
        [make_equipment(manufacturer="QSC")],
        [make_manufacturer(name="QSC")],
    )

    assert issues == []


def test_issue_for_missing_manufacturer():
    issues = review(
        [make_equipment(manufacturer="Unknown")],
        [make_manufacturer(name="QSC")],
    )

    assert issues == [
        ManufacturerReviewIssue(
            equipment_id="eq-001",
            manufacturer="Unknown",
            message="Manufacturer is not registered and requires estimator review.",
        )
    ]
    assert issues[0].to_dict()["severity"] == "review"


def test_issue_for_review_required_manufacturer():
    issues = review(
        [make_equipment(manufacturer="Legacy")],
        [
            make_manufacturer(
                name="Legacy",
                tier=ManufacturerTier.REVIEW_REQUIRED,
            )
        ],
    )

    assert len(issues) == 1
    assert issues[0].message == (
        "Manufacturer is registered but requires estimator review."
    )


def test_issue_for_avoid_manufacturer():
    issues = review(
        [make_equipment(manufacturer="Legacy")],
        [make_manufacturer(name="Legacy", tier=ManufacturerTier.AVOID)],
    )

    assert len(issues) == 1
    assert issues[0].manufacturer == "Legacy"


def test_issue_for_inactive_manufacturer():
    issues = review(
        [make_equipment(manufacturer="Legacy")],
        [make_manufacturer(name="Legacy", active=False)],
    )

    assert len(issues) == 1
    assert issues[0].manufacturer == "Legacy"


def test_ignores_equipment_with_no_manufacturer():
    issues = review(
        [
            make_equipment(manufacturer=None),
            make_equipment(equipment_id="eq-002", manufacturer=" "),
        ],
        [make_manufacturer(name="QSC")],
    )

    assert issues == []


def test_avoids_duplicate_issues():
    issues = review(
        [
            make_equipment(equipment_id="eq-001", manufacturer="Unknown"),
            make_equipment(equipment_id="eq-001", manufacturer=" unknown "),
        ],
        [],
    )

    assert len(issues) == 1
    assert issues[0].equipment_id == "eq-001"
    assert issues[0].manufacturer == "Unknown"

from atlas_core.rules import Resolution, ResolutionAction
from atlas_core.services import (
    ManufacturerReviewIssue,
    ReviewReportItem,
    ReviewReportService,
)


def make_resolution(
    rule_id: str = "RULE-001",
    target_id: str = "eq-speaker",
    message: str = "Passive speakers require an amplifier.",
) -> Resolution:
    return Resolution(
        rule_id=rule_id,
        action=ResolutionAction.ADD_PLACEHOLDER,
        target_id=target_id,
        message=message,
    )


def make_manufacturer_issue(
    equipment_id: str = "eq-display",
    manufacturer: str = "Unknown",
    message: str = "Manufacturer is not registered and requires estimator review.",
) -> ManufacturerReviewIssue:
    return ManufacturerReviewIssue(
        equipment_id=equipment_id,
        manufacturer=manufacturer,
        message=message,
    )


def test_empty_report():
    report = ReviewReportService().build_report([])

    assert report == []


def test_resolution_converted_to_review_item():
    report = ReviewReportService().build_report([make_resolution()])

    assert report == [
        ReviewReportItem(
            source="resolver",
            target_id="eq-speaker",
            message="Passive speakers require an amplifier.",
            severity="review",
            rule_id="RULE-001",
        )
    ]


def test_manufacturer_issue_converted_to_review_item():
    report = ReviewReportService().build_report(
        [],
        [make_manufacturer_issue()],
    )

    assert report == [
        ReviewReportItem(
            source="manufacturer_registry",
            target_id="eq-display",
            message=(
                "Manufacturer is not registered and requires estimator review."
            ),
            severity="review",
            manufacturer="Unknown",
        )
    ]


def test_preserves_order():
    report = ReviewReportService().build_report(
        [
            make_resolution(rule_id="RULE-001", target_id="eq-speaker"),
            make_resolution(rule_id="RULE-002", target_id="eq-display"),
        ],
        [
            make_manufacturer_issue(
                equipment_id="eq-review",
                manufacturer="Legacy",
            )
        ],
    )

    assert [item.source for item in report] == [
        "resolver",
        "resolver",
        "manufacturer_registry",
    ]
    assert [item.target_id for item in report] == [
        "eq-speaker",
        "eq-display",
        "eq-review",
    ]


def test_to_dict_output():
    item = ReviewReportItem(
        source="manufacturer_registry",
        target_id="eq-display",
        message="Manufacturer requires review.",
        severity="critical",
        rule_id="RULE-001",
        manufacturer="Legacy",
    )

    assert item.to_dict() == {
        "source": "manufacturer_registry",
        "target_id": "eq-display",
        "message": "Manufacturer requires review.",
        "severity": "critical",
        "rule_id": "RULE-001",
        "manufacturer": "Legacy",
    }

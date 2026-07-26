from atlas_core.domain import (
    DeviceSchedule,
    DeviceScheduleItem,
    Equipment,
    EquipmentCategory,
    Keynote,
    Legend,
    LegendItem,
)
from atlas_core.services import (
    ReconciliationIssue,
    ReconciliationSeverity,
    ScopeReconciliationService,
)


def make_equipment(
    equipment_id: str,
    category: EquipmentCategory = EquipmentCategory.SPEAKER,
    manufacturer: str | None = None,
    model: str | None = None,
    drawing_reference: str | None = "A-101",
    specification_reference: str | None = "27 41 16",
) -> Equipment:
    return Equipment(
        equipment_id=equipment_id,
        description=equipment_id,
        category=category,
        manufacturer=manufacturer,
        model=model,
        drawing_reference=drawing_reference,
        specification_reference=specification_reference,
    )


def test_keynote_category_missing_from_equipment_creates_issue():
    keynotes = [
        Keynote(
            keynote_id="kn-001",
            number="1",
            description="Use projector.",
            equipment_category="projector",
        )
    ]

    issues = ScopeReconciliationService().reconcile(
        equipment=[make_equipment("eq-001", category=EquipmentCategory.SPEAKER)],
        keynotes=keynotes,
    )

    assert len(issues) == 1
    assert issues[0].issue_id == "keynote_missing_equipment_category:projector"
    assert issues[0].severity is ReconciliationSeverity.MEDIUM
    assert (
        issues[0].message
        == "Keynote references equipment category not found in equipment matrix."
    )


def test_legend_category_missing_from_equipment_creates_issue():
    legends = [
        Legend(
            legend_id="legend-001",
            title="AV Symbols",
            items=[
                LegendItem(
                    legend_item_id="li-001",
                    symbol="DSP",
                    description="Processor",
                    equipment_category="dsp",
                )
            ],
        )
    ]

    issues = ScopeReconciliationService().reconcile(
        equipment=[make_equipment("eq-001", category=EquipmentCategory.SPEAKER)],
        legends=legends,
    )

    assert len(issues) == 1
    assert issues[0].issue_id == "legend_missing_equipment_category:dsp"
    assert issues[0].severity is ReconciliationSeverity.MEDIUM
    assert (
        issues[0].message
        == "Legend references equipment category not found in equipment matrix."
    )


def test_device_schedule_item_missing_from_equipment_creates_high_severity_issue():
    schedules = [
        DeviceSchedule(
            schedule_id="sched-001",
            items=[
                DeviceScheduleItem(
                    item_id="sched-001-item-1",
                    tag="SPK-1",
                    description="Speaker",
                    manufacturer="Acme",
                    model="X100",
                )
            ],
        )
    ]

    issues = ScopeReconciliationService().reconcile(
        equipment=[
            make_equipment(
                "eq-001",
                category=EquipmentCategory.SPEAKER,
                manufacturer="Other",
                model="Model",
            )
        ],
        device_schedules=schedules,
    )

    assert len(issues) == 1
    assert (
        issues[0].issue_id == "device_schedule_item_missing_equipment:sched-001-item-1"
    )
    assert issues[0].severity is ReconciliationSeverity.HIGH
    assert (
        issues[0].message
        == "Device schedule item is not represented in equipment matrix."
    )


def test_equipment_without_drawing_or_spec_reference_creates_low_severity_issue():
    issues = ScopeReconciliationService().reconcile(
        equipment=[
            make_equipment(
                "eq-001",
                category=EquipmentCategory.SPEAKER,
                drawing_reference=None,
                specification_reference=None,
            )
        ]
    )

    assert len(issues) == 1
    assert issues[0].issue_id == (
        "equipment_missing_drawing_or_specification_reference:"
        "speaker:no-room:no-system"
    )
    assert issues[0].severity is ReconciliationSeverity.LOW
    assert "1 item(s)" in issues[0].message


def test_equipment_reference_gaps_are_grouped():
    issues = ScopeReconciliationService().reconcile(
        equipment=[
            make_equipment(
                "eq-001",
                category=EquipmentCategory.SPEAKER,
                drawing_reference=None,
                specification_reference=None,
            ),
            make_equipment(
                "eq-002",
                category=EquipmentCategory.SPEAKER,
                drawing_reference=None,
                specification_reference=None,
            ),
        ]
    )

    assert len(issues) == 1
    assert "2 item(s)" in issues[0].message


def test_no_issue_when_categories_match():
    issues = ScopeReconciliationService().reconcile(
        equipment=[make_equipment("eq-001", category=EquipmentCategory.PROJECTOR)],
        keynotes=[
            Keynote(
                keynote_id="kn-001",
                number="1",
                description="Use projector.",
                equipment_category="PROJECTOR",
            )
        ],
        legends=[
            Legend(
                legend_id="legend-001",
                items=[
                    LegendItem(
                        legend_item_id="li-001",
                        symbol="PJ",
                        description="Projector",
                        equipment_category="projector",
                    )
                ],
            )
        ],
    )

    assert issues == []


def test_duplicate_issues_are_avoided():
    issues = ScopeReconciliationService().reconcile(
        equipment=[],
        keynotes=[
            Keynote(
                keynote_id="kn-001",
                number="1",
                description="Use projector.",
                equipment_category="projector",
            ),
            Keynote(
                keynote_id="kn-002",
                number="2",
                description="Use projector.",
                equipment_category="PROJECTOR",
            ),
        ],
    )

    assert len(issues) == 1
    assert issues[0].issue_id == "keynote_missing_equipment_category:projector"


def test_empty_inputs_return_empty_list():
    assert ScopeReconciliationService().reconcile() == []


def test_to_dict_output():
    issue = ReconciliationIssue(
        issue_id="device_schedule_item_missing_equipment:sched-1",
        message="Device schedule item is not represented in equipment matrix.",
        severity="high",
        target_id="sched-1",
        suggested_action="Add item to equipment matrix.",
        confidence=0.9,
    )

    assert issue.to_dict() == {
        "issue_id": "device_schedule_item_missing_equipment:sched-1",
        "message": "Device schedule item is not represented in equipment matrix.",
        "severity": "high",
        "source": "scope_reconciliation",
        "target_id": "sched-1",
        "suggested_action": "Add item to equipment matrix.",
        "confidence": 0.9,
    }

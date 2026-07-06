from atlas_core.domain import (
    BidPackageReview,
    DetailCallout,
    DrawingDiscipline,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    Keynote,
    Legend,
    LegendItem,
)
from atlas_core.rules import (
    CoordinationRule,
    EngineeringRuleRegistry,
    HealthcareSiteRule,
    LoadInRule,
    MobilizationRule,
    PrevailingWageRule,
    SafetyCertificationRule,
    SiteStorageRule,
    TrashAndCleaningRule,
    TravelDistanceRule,
    register_construction_rules,
)


def make_review(
    notes: list[str] | None = None,
    equipment: list[Equipment] | None = None,
    detail_callouts: list[DetailCallout] | None = None,
    keynotes: list[Keynote] | None = None,
    legends: list[Legend] | None = None,
    drawing_sheets: list[DrawingSheet] | None = None,
) -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Construction Review",
        notes=list(notes or []),
        equipment=list(equipment or []),
        detail_callouts=list(detail_callouts or []),
        keynotes=list(keynotes or []),
        legends=list(legends or []),
        drawing_sheets=list(drawing_sheets or []),
    )


def test_travel_distance_rule_triggers_from_review_notes():
    review = make_review(notes=["Remote site travel with hotel and per diem required"])

    assumptions = TravelDistanceRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "construction_travel_distance_review"
    assert assumptions[0].category == "travel"


def test_mobilization_rule_triggers_from_equipment_assumptions():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-001",
                description="Control rack",
                category=EquipmentCategory.RACK,
                assumptions=["Phased work and remobilization may be required"],
            )
        ]
    )

    assumptions = MobilizationRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "construction_mobilization_review"
    assert assumptions[0].category == "mobilization"


def test_load_in_rule_triggers_from_detail_callout_notes():
    review = make_review(
        detail_callouts=[
            DetailCallout(
                callout_id="callout-001",
                detail_number="1",
                source_sheet_number="A1.01",
                notes=["Freight elevator access restrictions and crane access"],
            )
        ]
    )

    assumptions = LoadInRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "construction_load_in_risk"
    assert assumptions[0].category == "load_in"


def test_site_storage_rule_triggers_from_keynote():
    review = make_review(
        keynotes=[
            Keynote(
                keynote_id="keynote-001",
                number="K1",
                description="Limited storage onsite with daily delivery",
            )
        ]
    )

    assumptions = SiteStorageRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "construction_site_storage_review"
    assert assumptions[0].category == "site_storage"


def test_trash_and_cleaning_rule_triggers_from_legend_item_notes():
    review = make_review(
        legends=[
            Legend(
                legend_id="legend-001",
                items=[
                    LegendItem(
                        legend_item_id="item-001",
                        symbol="TR",
                        description="Temporary requirements",
                        notes=["Daily cleanup and dumpster by installer"],
                    )
                ],
            )
        ]
    )

    assumptions = TrashAndCleaningRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "construction_cleanup_review"
    assert assumptions[0].category == "cleanup"


def test_healthcare_site_rule_triggers_from_drawing_sheet_notes():
    review = make_review(
        drawing_sheets=[
            DrawingSheet(
                sheet_id="sheet-001",
                sheet_number="AV-101",
                title="AV Floor Plan",
                discipline=DrawingDiscipline.AUDIOVISUAL,
                notes=["Hospital floor requires ICRA dust control and containment"],
            )
        ]
    )

    assumptions = HealthcareSiteRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "construction_healthcare_site_risk"
    assert assumptions[0].category == "healthcare"


def test_prevailing_wage_rule_triggers_from_review_notes():
    review = make_review(notes=["Project is public works with certified payroll"])

    assumptions = PrevailingWageRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "construction_prevailing_wage_risk"
    assert assumptions[0].category == "labor_compliance"


def test_safety_certification_rule_triggers_from_review_notes():
    review = make_review(notes=["OSHA orientation and fall protection are required"])

    assumptions = SafetyCertificationRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "construction_safety_certification_review"
    assert assumptions[0].category == "safety"


def test_coordination_rule_triggers_from_review_notes():
    review = make_review(
        notes=["Conduit by others and power by others; coordinate with GC and EC"]
    )

    assumptions = CoordinationRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "construction_coordination_review"
    assert assumptions[0].category == "coordination"


def test_register_construction_rules_registers_all_rules():
    registry = EngineeringRuleRegistry()

    register_construction_rules(registry)

    assert [rule.rule_id for rule in registry.rules()] == [
        "construction_travel_distance",
        "construction_mobilization",
        "construction_load_in",
        "construction_site_storage",
        "construction_cleanup",
        "construction_healthcare_site",
        "construction_prevailing_wage",
        "construction_safety_certification",
        "construction_coordination",
    ]


def test_construction_rules_do_not_match_when_notes_do_not_include_tokens():
    review = make_review(
        notes=["Standard daytime install with normal access and no special conditions"],
        equipment=[
            Equipment(
                equipment_id="eq-001",
                description="Display",
                category=EquipmentCategory.DISPLAY,
                assumptions=["Install per drawings"],
            )
        ],
    )

    assert TravelDistanceRule().matches(review) is False
    assert MobilizationRule().matches(review) is False
    assert LoadInRule().matches(review) is False
    assert SiteStorageRule().matches(review) is False
    assert TrashAndCleaningRule().matches(review) is False
    assert HealthcareSiteRule().matches(review) is False
    assert PrevailingWageRule().matches(review) is False
    assert SafetyCertificationRule().matches(review) is False
    assert CoordinationRule().matches(review) is False


def test_rule_emits_single_assumption_when_multiple_tokens_present():
    review = make_review(
        notes=[
            "Travel distance and flight required",
            "Hotel and per diem required",
            "Mileage reimbursement applies",
        ]
    )

    assumptions = TravelDistanceRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "construction_travel_distance_review"

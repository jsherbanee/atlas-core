from atlas_core.domain import (
    BidPackageReview,
    DeviceSchedule,
    DeviceScheduleItem,
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    RFICandidateCategory,
    SpecificationSection,
)
from atlas_core.services.rfi_candidate_service import RFICandidateService
from atlas_core.services.scope_reconciliation_service import (
    ReconciliationIssue,
    ReconciliationSeverity,
)


def make_review(
    equipment: list[Equipment] | None = None,
    drawings: list[DrawingSheet] | None = None,
    specs: list[SpecificationSection] | None = None,
    schedules: list[DeviceSchedule] | None = None,
    reconciliation_issues: list[ReconciliationIssue] | None = None,
) -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        equipment=list(equipment or []),
        drawing_sheets=list(drawings or []),
        specification_sections=list(specs or []),
        device_schedules=list(schedules or []),
        reconciliation_issues=list(reconciliation_issues or []),
    )


def test_missing_model_number_creates_candidate():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
                manufacturer="Epson",
            )
        ]
    )

    candidates = RFICandidateService().build(review)

    assert any(
        candidate.detected_condition == "missing_model_number"
        for candidate in candidates
    )
    assert any(
        candidate.category is RFICandidateCategory.MISSING_INFORMATION
        for candidate in candidates
    )


def test_ofe_ofci_cfci_by_others_ambiguity_creates_candidate():
    review = make_review(
        drawings=[
            DrawingSheet(
                sheet_id="av-101",
                sheet_number="AV-101",
                title="AV Plan",
                notes=["Display by others; OFE mount and OFCI cabling."],
            )
        ]
    )

    candidates = RFICandidateService().build(review)

    ambiguity_candidate = next(
        candidate
        for candidate in candidates
        if candidate.detected_condition == "scope_responsibility_ambiguity"
    )
    assert ambiguity_candidate.category is RFICandidateCategory.RESPONSIBILITY_GAP
    assert ambiguity_candidate.source_refs


def test_quantity_mismatch_creates_candidate():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-speaker",
                description="Ceiling speaker",
                category=EquipmentCategory.SPEAKER,
                manufacturer="JBL",
                model="CBT 70J",
                quantity=4,
            )
        ],
        schedules=[
            DeviceSchedule(
                schedule_id="sched-001",
                items=[
                    DeviceScheduleItem(
                        item_id="sched-item-1",
                        tag="SPK-1",
                        description="Ceiling speaker",
                        manufacturer="JBL",
                        model="CBT 70J",
                        quantity=6,
                    )
                ],
            )
        ],
        reconciliation_issues=[
            ReconciliationIssue(
                issue_id="qty-mismatch-1",
                message="Quantity mismatch between drawing and schedule.",
                severity=ReconciliationSeverity.HIGH,
                target_id="eq-speaker",
            )
        ],
    )

    candidates = RFICandidateService().build(review)

    assert any(
        candidate.detected_condition == "quantity_conflict" for candidate in candidates
    )


def test_drawing_spec_mismatch_creates_candidate():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-display",
                description="Main display",
                category=EquipmentCategory.DISPLAY,
                drawing_reference="AV-201",
            )
        ]
    )

    candidates = RFICandidateService().build(review)

    mismatch_candidate = next(
        candidate
        for candidate in candidates
        if candidate.detected_condition == "drawing_spec_cross_reference_gap"
    )
    assert mismatch_candidate.category is RFICandidateCategory.DRAWING_SPEC_MISMATCH


def test_add_alternate_ambiguity_creates_candidate():
    review = make_review(
        specs=[
            SpecificationSection(
                section_id="27-41-16",
                section_number="27 41 16",
                title="Integrated AV Systems",
                notes=["Add alternate: provide additional displays."],
            )
        ]
    )

    candidates = RFICandidateService().build(review)

    assert any(
        candidate.detected_condition == "add_alternate_ambiguity"
        for candidate in candidates
    )


def test_duplicate_or_near_duplicate_candidates_are_suppressed():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector-a",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
                manufacturer="Panasonic",
            ),
            Equipment(
                equipment_id="eq-projector-b",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
                manufacturer="Panasonic",
            ),
        ]
    )

    candidates = RFICandidateService().build(review)

    missing_model_candidates = [
        candidate
        for candidate in candidates
        if candidate.detected_condition == "missing_model_number"
    ]
    assert len(missing_model_candidates) == 1


def test_clean_review_returns_empty_list():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-projector",
                description="Main projector",
                category=EquipmentCategory.PROJECTOR,
                manufacturer="Epson",
                model="EB-PQ2220B",
                specification_reference="27 41 16",
                drawing_reference="AV-201",
            ),
            Equipment(
                equipment_id="eq-display",
                description="Main display",
                category=EquipmentCategory.DISPLAY,
                manufacturer="Samsung",
                model="QM75C",
                specification_reference="27 41 16",
                drawing_reference="AV-202",
            ),
        ],
        drawings=[
            DrawingSheet(
                sheet_id="av-101",
                sheet_number="AV-101",
                title="AV Plan",
                notes=["Mounting and power responsibilities by AV contractor."],
            )
        ],
        specs=[
            SpecificationSection(
                section_id="27-41-16",
                section_number="27 41 16",
                title="Integrated AV Systems",
                notes=["Basis of design and quantity are defined in this section."],
            )
        ],
    )

    candidates = RFICandidateService().build(review)

    assert candidates == []

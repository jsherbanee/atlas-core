from atlas_core.domain import (
    Building,
    Equipment,
    EquipmentCategory,
    IntegratedSystem,
    SystemCategory,
    Room,
    RoomType,
)
from atlas_core.services import (
    BidPackageReviewService,
    CompletenessStatus,
    ConfidenceScoringService,
    CrossReferenceType,
)


def build_review(**kwargs):
    return BidPackageReviewService().build_review(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        **kwargs,
    )


def make_room() -> Room:
    return Room(
        room_id="building-001-main-lobby",
        name="Main Lobby",
        building_id="building-001",
        room_type=RoomType.LOBBY,
    )


def make_building() -> Building:
    return Building(
        building_id="building-001",
        name="Main Building",
        project_id="project-001",
    )


class LowConfidenceScoringService:
    def score_review(self, review):
        return 0.6


class EmptyScheduleEquipmentService:
    def equipment_from_schedule(self, schedule):
        return []


def test_builds_review_from_raw_sheets_and_raw_sections():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ],
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ],
    )

    assert review.review_id == "review-001"
    assert review.project_id == "project-001"
    assert review.name == "Bid Package Review"
    assert review.drawing_count() == 1
    assert review.specification_count() == 1


def test_includes_indexed_drawing_sheets():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ],
    )

    assert review.drawing_sheets[0].sheet_id == "av1.01"
    assert review.drawing_sheets[0].title == "AV Plan"


def test_includes_indexed_specification_sections():
    review = build_review(
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ],
    )

    assert review.specification_sections[0].section_id == "27-41-16"
    assert review.specification_sections[0].title == ("Integrated Audio-Video Systems")


def test_includes_equipment():
    equipment = [
        Equipment(
            equipment_id="eq-display",
            description="Display",
            category=EquipmentCategory.DISPLAY,
        )
    ]

    review = build_review(equipment=equipment)

    assert review.equipment == equipment
    assert review.equipment_count() == 1


def test_detects_equipment_when_no_equipment_is_supplied():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "Main Loudspeaker Plan",
            }
        ],
    )

    assert len(review.equipment) == 1
    assert review.equipment[0].equipment_id == "detected-speaker"
    assert review.equipment[0].category is EquipmentCategory.SPEAKER


def test_does_not_replace_supplied_equipment():
    supplied_equipment = Equipment(
        equipment_id="eq-custom",
        description="Custom display",
        category=EquipmentCategory.DISPLAY,
    )

    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "Main Loudspeaker Plan",
            }
        ],
        equipment=[supplied_equipment],
    )

    assert review.equipment == [supplied_equipment]


def test_detected_equipment_flows_into_review_equipment():
    review = build_review(
        raw_sections=[
            {
                "section_number": "27 41 26",
                "title": "Q-SYS Control System",
            }
        ],
    )

    assert any(
        item.equipment_id == "detected-control-processor"
        and item.category is EquipmentCategory.CONTROL_PROCESSOR
        for item in review.equipment
    )


def test_detected_equipment_creates_resolver_and_scope_gap_issues():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "Main Loudspeaker Plan",
            }
        ],
    )

    assert any(
        resolution.rule_id == "RULE-001" and resolution.target_id == "detected-speaker"
        for resolution in review.resolutions
    )
    assert any(
        gap.gap_id == "speaker_missing_amplifier"
        and gap.target_id == "detected-speaker"
        for gap in review.scope_gaps
    )


def test_includes_resolver_resolutions():
    equipment = [
        Equipment(
            equipment_id="eq-drapery",
            description="Motorized Drapery",
            category=EquipmentCategory.DRAPERY,
        )
    ]

    review = build_review(equipment=equipment)

    assert len(review.resolutions) == 1
    assert review.resolutions[0].rule_id == "RULE-004"


def test_includes_review_report():
    equipment = [
        Equipment(
            equipment_id="eq-drapery",
            description="Motorized Drapery",
            category=EquipmentCategory.DRAPERY,
        )
    ]

    review = build_review(equipment=equipment)

    assert len(review.review_report) == 1
    assert review.review_report[0].source == "resolver"
    assert review.review_report[0].target_id == "eq-drapery"


def test_includes_cross_references_when_equipment_references_drawing_and_spec():
    equipment = [
        Equipment(
            equipment_id="eq-speaker",
            description="Main loudspeaker",
            category=EquipmentCategory.SPEAKER,
            drawing_reference="AV1.01",
            specification_reference="27 41 16",
        )
    ]

    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ],
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ],
        equipment=equipment,
    )

    assert any(
        reference.reference_type is CrossReferenceType.EQUIPMENT_TO_DRAWING
        and reference.source_id == "eq-speaker"
        and reference.target_id == "av1.01"
        for reference in review.cross_references
    )
    assert any(
        reference.reference_type is CrossReferenceType.EQUIPMENT_TO_SPEC
        and reference.source_id == "eq-speaker"
        and reference.target_id == "27-41-16"
        for reference in review.cross_references
    )


def test_detects_systems_when_no_systems_are_supplied():
    review = build_review(
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio Systems",
            }
        ],
    )

    assert len(review.systems) == 1
    assert review.systems[0].system_id == "detected-audio"
    assert review.systems[0].category is SystemCategory.AUDIO


def test_does_not_replace_supplied_systems():
    supplied_system = IntegratedSystem(
        system_id="sys-custom",
        name="Custom System",
        category=SystemCategory.CONTROL,
    )

    review = build_review(
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio Systems",
            }
        ],
        systems=[supplied_system],
    )

    assert review.systems == [supplied_system]


def test_detects_rooms_when_no_rooms_are_supplied():
    review = build_review(
        buildings=[make_building()],
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "Main Lobby AV Plan",
            }
        ],
    )

    assert len(review.rooms) == 1
    assert review.rooms[0].name == "Main Lobby"
    assert review.rooms[0].building_id == "building-001"


def test_does_not_replace_supplied_rooms():
    supplied_room = make_room()

    review = build_review(
        buildings=[make_building()],
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "Main Lobby AV Plan",
            }
        ],
        rooms=[supplied_room],
    )

    assert review.rooms == [supplied_room]


def test_does_not_detect_rooms_without_building_context():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "Main Lobby AV Plan",
            }
        ],
    )

    assert review.rooms == []


def test_includes_scope_gaps_for_missing_projector_mount():
    equipment = [
        Equipment(
            equipment_id="eq-projector",
            description="Projector",
            category=EquipmentCategory.PROJECTOR,
            room_id="room-001",
        )
    ]

    review = build_review(equipment=equipment)

    assert len(review.scope_gaps) == 1
    assert review.scope_gaps[0].gap_id == "projector_missing_mount"
    assert review.scope_gaps[0].target_id == "eq-projector"


def test_includes_estimator_risks_when_scope_gaps_exist():
    equipment = [
        Equipment(
            equipment_id="eq-projector",
            description="Projector",
            category=EquipmentCategory.PROJECTOR,
            room_id="room-001",
        )
    ]

    review = build_review(equipment=equipment)

    assert any(
        risk.risk_id == "scope_gaps_detected" and risk.category == "scope"
        for risk in review.estimator_risks
    )


def test_scores_review_confidence_after_content_is_populated():
    equipment = [
        Equipment(
            equipment_id="eq-projector",
            description="Projector",
            category=EquipmentCategory.PROJECTOR,
            room_id="room-001",
        )
    ]

    review = build_review(equipment=equipment)

    assert review.confidence == ConfidenceScoringService().score_review(review)


def test_includes_recommendations_when_confidence_is_low():
    review = BidPackageReviewService(
        confidence_scoring_service=LowConfidenceScoringService()
    ).build_review(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
    )

    assert review.confidence == 0.6
    assert any(
        recommendation.recommendation_id == "review-low-confidence"
        and recommendation.category == "confidence"
        for recommendation in review.recommendations
    )


def test_includes_recommendations_when_scope_gaps_exist():
    equipment = [
        Equipment(
            equipment_id="eq-projector",
            description="Projector",
            category=EquipmentCategory.PROJECTOR,
            room_id="room-001",
        )
    ]

    review = build_review(equipment=equipment)

    assert any(
        recommendation.recommendation_id
        == "scope-gap-projector_missing_mount-eq-projector"
        and recommendation.category == "scope_gap"
        and recommendation.target_id == "eq-projector"
        for recommendation in review.recommendations
    )


def test_includes_bid_completeness():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ],
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ],
    )

    assert review.bid_completeness is not None


def test_includes_readiness():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ],
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ],
    )

    assert review.readiness is not None
    assert review.readiness.message


def test_bid_completeness_is_incomplete_when_drawings_and_specs_are_missing():
    review = build_review(
        raw_sheets=[],
        raw_sections=[],
        systems=[],
        equipment=[],
        raw_device_schedules=[],
    )

    assert review.bid_completeness is not None
    assert review.bid_completeness.status is CompletenessStatus.INCOMPLETE


def test_bid_completeness_is_complete_when_core_data_exists():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ],
        raw_sections=[
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
            }
        ],
        systems=[
            IntegratedSystem(
                system_id="sys-001",
                name="Audio System",
                category=SystemCategory.AUDIO,
            )
        ],
        equipment=[
            Equipment(
                equipment_id="eq-001",
                description="Display",
                category=EquipmentCategory.DISPLAY,
            )
        ],
        raw_device_schedules=[
            {
                "schedule_id": "sched-1",
                "title": "Device Schedule",
                "rows": [],
            }
        ],
    )

    assert review.bid_completeness is not None
    assert review.bid_completeness.status is CompletenessStatus.COMPLETE


def test_works_with_empty_inputs():
    review = build_review()

    assert review.drawing_sheets == []
    assert review.specification_sections == []
    assert review.systems == []
    assert review.equipment == []
    assert review.resolutions == []
    assert review.manufacturer_review_issues == []
    assert review.review_report == []
    assert review.cross_references == []
    assert review.scope_gaps == []
    assert review.estimator_risks == []


def test_includes_drawing_metadata_for_indexed_drawing_sheets():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
            }
        ],
    )

    assert len(review.drawing_metadata) == 1
    assert review.drawing_metadata[0].sheet_number == "AV1.01"
    assert review.drawing_metadata[0].title == "AV Plan"


def test_extracts_device_schedules_from_raw_device_schedules():
    review = build_review(
        raw_device_schedules=[
            {
                "schedule_id": "sched-1",
                "source_sheet_number": "AV1.01",
                "title": "Audio Device Schedule",
                "rows": [{"tag": "SPK-1", "description": "Main loudspeaker"}],
            }
        ]
    )

    assert len(review.device_schedules) == 1
    assert review.device_schedules[0].schedule_id == "sched-1"
    assert review.device_schedules[0].title == "Audio Device Schedule"


def test_includes_device_schedules_in_review():
    review = build_review(
        raw_device_schedules=[
            {
                "schedule_id": "sched-1",
                "rows": [{"tag": "DSP-1", "description": "Control processor"}],
            }
        ]
    )

    assert review.device_schedule_count() == 1


def test_converts_device_schedule_rows_to_equipment():
    review = build_review(
        raw_device_schedules=[
            {
                "schedule_id": "sched-1",
                "rows": [{"tag": "DSP-1", "description": "Q-SYS control processor"}],
            }
        ]
    )

    assert any(
        item.equipment_id == "equipment-sched-1-dsp-1" for item in review.equipment
    )


def test_schedule_derived_equipment_flows_into_review_equipment():
    supplied_equipment = Equipment(
        equipment_id="eq-custom",
        description="Custom display",
        category=EquipmentCategory.DISPLAY,
    )

    review = build_review(
        equipment=[supplied_equipment],
        raw_device_schedules=[
            {
                "schedule_id": "sched-1",
                "rows": [{"tag": "SPK-1", "description": "Main loudspeaker"}],
            }
        ],
    )

    assert any(item.equipment_id == "eq-custom" for item in review.equipment)
    assert any(
        item.equipment_id == "equipment-sched-1-spk-1" for item in review.equipment
    )


def test_schedule_derived_speaker_without_amplifier_creates_resolver_scope_gap_issue():
    review = build_review(
        raw_device_schedules=[
            {
                "schedule_id": "sched-1",
                "rows": [{"tag": "SPK-1", "description": "Main loudspeaker"}],
            }
        ]
    )

    assert any(
        resolution.rule_id == "RULE-001"
        and resolution.target_id == "equipment-sched-1-spk-1"
        for resolution in review.resolutions
    )
    assert any(
        gap.gap_id == "speaker_missing_amplifier"
        and gap.target_id == "equipment-sched-1-spk-1"
        for gap in review.scope_gaps
    )


def test_extracts_keynotes_from_drawing_notes():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
                "notes": ["K1: Ceiling Speaker"],
            }
        ]
    )

    assert review.keynote_count() == 1
    assert review.keynotes[0].number == "K1"
    assert review.keynotes[0].description == "Ceiling Speaker"


def test_extracts_legends_from_drawing_notes():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
                "notes": ["SPK - Ceiling Speaker"],
            }
        ]
    )

    assert review.legend_count() == 1
    assert review.legends[0].item_count() == 1
    assert review.legends[0].items[0].symbol == "SPK"


def test_includes_keynotes_in_review():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
                "notes": ["1 - Projector"],
            }
        ]
    )

    assert len(review.keynotes) == 1
    assert review.keynotes[0].keynote_id == "av1.01-keynote-1"


def test_extracts_detail_callouts_from_drawing_notes():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
                "notes": ["Detail 5/AV-701"],
            }
        ]
    )

    assert review.detail_callout_count() == 1
    assert review.detail_callouts[0].detail_number == "5"
    assert review.detail_callouts[0].target_sheet_number == "AV-701"


def test_includes_detail_callouts_in_review():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "Rack Detail 1/AV-801",
            }
        ]
    )

    assert len(review.detail_callouts) == 1
    assert review.detail_callouts[0].callout_id == "av1.01-detail-1-av-801"


def test_includes_legends_in_review():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
                "notes": ["△ Wireless Microphone"],
            }
        ]
    )

    assert len(review.legends) == 1
    assert review.legends[0].legend_id == "av1.01-legend"


def test_includes_reconciliation_issues_when_keynote_references_missing_equipment():
    review = build_review(
        raw_sheets=[
            {
                "sheet_number": "AV1.01",
                "title": "AV Plan",
                "notes": ["1: Projector"],
            }
        ],
        equipment=[
            Equipment(
                equipment_id="eq-speaker",
                description="Speaker",
                category=EquipmentCategory.SPEAKER,
            )
        ],
    )

    assert any(
        issue.issue_id == "keynote_missing_equipment_category:projector"
        and issue.target_id == "av1.01-keynote-1"
        for issue in review.reconciliation_issues
    )


def test_includes_reconciliation_issues_when_device_schedule_item_is_not_represented_in_equipment_matrix():
    review = BidPackageReviewService(
        device_schedule_equipment_service=EmptyScheduleEquipmentService()
    ).build_review(
        review_id="review-001",
        project_id="project-001",
        name="Bid Package Review",
        raw_device_schedules=[
            {
                "schedule_id": "sched-1",
                "rows": [
                    {
                        "tag": "DSP-1",
                        "description": "Control processor",
                        "manufacturer": "Acme",
                        "model": "X100",
                    }
                ],
            }
        ],
    )

    assert any(
        issue.issue_id == "device_schedule_item_missing_equipment:sched-1-dsp-1"
        and issue.target_id == "sched-1-dsp-1"
        for issue in review.reconciliation_issues
    )

from atlas_core.domain import BidPackageReview, Equipment, EquipmentCategory
from atlas_core.rules import (
    DSPProgrammingRule,
    EngineeringRuleRegistry,
    HearingAssistanceRule,
    MicrophonePowerRule,
    PagingRule,
    SpeakerAmplifierRule,
    WirelessAntennaRule,
    register_audio_rules,
)


def make_review(equipment: list[Equipment] | None = None) -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
        equipment=list(equipment or []),
    )


def test_speaker_amplifier_rule_generates_assumption_when_amplifier_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-speaker",
                description="Ceiling speaker",
                category=EquipmentCategory.SPEAKER,
                system_id="sys-1",
            )
        ]
    )

    assumptions = SpeakerAmplifierRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "audio_amplifier_missing_eq-speaker"


def test_dsp_programming_rule_generates_assumption_when_programming_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-dsp",
                description="Main DSP",
                category=EquipmentCategory.DSP,
            )
        ]
    )

    assumptions = DSPProgrammingRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "audio_programming_missing_eq-dsp"


def test_wireless_antenna_rule_generates_assumption_when_antenna_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-mic",
                description="Wireless handheld microphone",
                category=EquipmentCategory.MICROPHONE,
            )
        ]
    )

    assumptions = WirelessAntennaRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "audio_wireless_antenna_missing_eq-mic"


def test_paging_rule_generates_assumption_when_paging_scope_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-intercom",
                description="Intercom master station",
                category=EquipmentCategory.INTERCOM,
            )
        ]
    )

    assumptions = PagingRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "audio_paging_missing_eq-intercom"


def test_hearing_assistance_rule_generates_assumption_when_system_needs_coverage():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-speaker",
                description="Ceiling speaker",
                category=EquipmentCategory.SPEAKER,
            )
        ]
    )

    assumptions = HearingAssistanceRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "audio_hearing_assistance_missing"


def test_microphone_power_rule_generates_assumption_when_power_missing():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-mic",
                description="Gooseneck microphone",
                category=EquipmentCategory.MICROPHONE,
            )
        ]
    )

    assumptions = MicrophonePowerRule().generate(review)

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == "audio_microphone_power_missing_eq-mic"


def test_register_audio_rules_registers_all_rules():
    registry = EngineeringRuleRegistry()

    register_audio_rules(registry)

    assert [rule.rule_id for rule in registry.rules()] == [
        "audio_speaker_amplifier",
        "audio_dsp_programming",
        "audio_wireless_antenna",
        "audio_paging",
        "audio_hearing_assistance",
        "audio_microphone_power",
    ]


def test_audio_rules_do_not_match_when_inputs_are_complete():
    review = make_review(
        equipment=[
            Equipment(
                equipment_id="eq-speaker",
                description="Ceiling speaker",
                category=EquipmentCategory.SPEAKER,
                system_id="sys-1",
            ),
            Equipment(
                equipment_id="eq-amp",
                description="Power amplifier",
                category=EquipmentCategory.AMPLIFIER,
                system_id="sys-1",
            ),
            Equipment(
                equipment_id="eq-dsp",
                description="DSP processor",
                category=EquipmentCategory.DSP,
                assumptions=["Programming by controls contractor"],
            ),
            Equipment(
                equipment_id="eq-mic-1",
                description="Wireless handheld microphone",
                category=EquipmentCategory.MICROPHONE,
                assumptions=["Power by battery"],
            ),
            Equipment(
                equipment_id="eq-antenna",
                description="Antenna distribution",
                category=EquipmentCategory.ACCESSORY,
            ),
            Equipment(
                equipment_id="eq-intercom",
                description="Intercom paging station",
                category=EquipmentCategory.INTERCOM,
                assumptions=["Paging zones confirmed"],
            ),
            Equipment(
                equipment_id="eq-assisted",
                description="Assistive listening receiver",
                category=EquipmentCategory.ASSISTED_LISTENING,
            ),
        ]
    )

    assert SpeakerAmplifierRule().matches(review) is False
    assert DSPProgrammingRule().matches(review) is False
    assert WirelessAntennaRule().matches(review) is False
    assert PagingRule().matches(review) is False
    assert HearingAssistanceRule().matches(review) is False
    assert MicrophonePowerRule().matches(review) is False

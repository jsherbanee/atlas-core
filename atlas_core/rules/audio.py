"""Audio-focused engineering rules for Atlas Core."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atlas_core.domain.engineering_assumption import (
    AssumptionSeverity,
    EngineeringAssumption,
)
from atlas_core.domain.equipment import EquipmentCategory
from atlas_core.rules.engineering_rule import EngineeringRule
from atlas_core.rules.engineering_rule_registry import EngineeringRuleRegistry
from atlas_core.utils.refactoring import enum_value

if TYPE_CHECKING:
    from atlas_core.domain.bid_package_review import BidPackageReview


class SpeakerAmplifierRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="audio_speaker_amplifier",
            category="audio",
            description="Speaker systems should include matching amplifier capacity.",
            priority=10,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []
        speakers = self._items_by_category(review, EquipmentCategory.SPEAKER)
        amplifiers = self._items_by_category(review, EquipmentCategory.AMPLIFIER)

        for speaker in speakers:
            speaker_system_id = str(getattr(speaker, "system_id", "") or "")
            has_amplifier = any(
                (
                    str(getattr(amplifier, "system_id", "") or "") == speaker_system_id
                    if speaker_system_id
                    else True
                )
                for amplifier in amplifiers
            )
            if has_amplifier:
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"audio_amplifier_missing_{speaker.equipment_id}",
                    category="audio",
                    description="Speaker amplifier capacity should be verified.",
                    severity=AssumptionSeverity.RISK,
                    related_equipment=speaker.equipment_id,
                )
            )

        return assumptions

    @staticmethod
    def _items_by_category(
        review: BidPackageReview,
        category: EquipmentCategory,
    ) -> list[Any]:
        equipment = list(getattr(review, "equipment", []) or [])
        target_value = enum_value(category)
        return [
            item
            for item in equipment
            if enum_value(getattr(item, "category", None)) == target_value
        ]


class DSPProgrammingRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="audio_dsp_programming",
            category="programming",
            description="DSP and control processors should include programming scope.",
            priority=20,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []
        equipment = list(getattr(review, "equipment", []) or [])

        for item in equipment:
            category = enum_value(getattr(item, "category", None))
            if category not in {
                enum_value(EquipmentCategory.DSP),
                enum_value(EquipmentCategory.CONTROL_PROCESSOR),
            }:
                continue

            if self._has_programming_reference(item):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"audio_programming_missing_{item.equipment_id}",
                    category="programming",
                    description="DSP programming scope should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=item.equipment_id,
                )
            )

        return assumptions

    @staticmethod
    def _has_programming_reference(item: Any) -> bool:
        text = " ".join(
            [
                str(getattr(item, "description", "") or ""),
                " ".join(str(note) for note in getattr(item, "assumptions", []) or []),
            ]
        ).casefold()
        return any(token in text for token in ("program", "configuration", "tuning"))


class WirelessAntennaRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="audio_wireless_antenna",
            category="wireless",
            description=(
                "Wireless microphones should include antenna distribution equipment."
            ),
            priority=30,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []
        equipment = list(getattr(review, "equipment", []) or [])

        has_antenna_equipment = any(self._mentions_antenna(item) for item in equipment)

        for item in equipment:
            if enum_value(getattr(item, "category", None)) != enum_value(
                EquipmentCategory.MICROPHONE
            ):
                continue

            text = self._equipment_text(item)
            if "wireless" not in text or has_antenna_equipment:
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=(
                        "audio_wireless_antenna_missing_" f"{item.equipment_id}"
                    ),
                    category="wireless",
                    description=(
                        "Wireless microphone antenna distribution should be verified."
                    ),
                    severity=AssumptionSeverity.RISK,
                    related_equipment=item.equipment_id,
                )
            )

        return assumptions

    @classmethod
    def _mentions_antenna(cls, item: Any) -> bool:
        return "antenna" in cls._equipment_text(item)

    @staticmethod
    def _equipment_text(item: Any) -> str:
        return " ".join(
            [
                str(getattr(item, "description", "") or ""),
                str(getattr(item, "model", "") or ""),
                " ".join(str(note) for note in getattr(item, "assumptions", []) or []),
            ]
        ).casefold()


class PagingRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="audio_paging",
            category="paging",
            description="Paging systems should identify source, routing, and zones.",
            priority=40,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []
        intercoms = self._items_by_category(review, EquipmentCategory.INTERCOM)

        for item in intercoms:
            if "paging" in self._equipment_text(item):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"audio_paging_missing_{item.equipment_id}",
                    category="paging",
                    description="Paging scope and zoning should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=item.equipment_id,
                )
            )

        return assumptions

    @staticmethod
    def _items_by_category(
        review: BidPackageReview,
        category: EquipmentCategory,
    ) -> list[Any]:
        equipment = list(getattr(review, "equipment", []) or [])
        target_value = enum_value(category)
        return [
            item
            for item in equipment
            if enum_value(getattr(item, "category", None)) == target_value
        ]

    @staticmethod
    def _equipment_text(item: Any) -> str:
        return " ".join(
            [
                str(getattr(item, "description", "") or ""),
                " ".join(str(note) for note in getattr(item, "assumptions", []) or []),
            ]
        ).casefold()


class HearingAssistanceRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="audio_hearing_assistance",
            category="compliance",
            description=(
                "Hearing assistance coverage should be reviewed for audio systems."
            ),
            priority=50,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        equipment = list(getattr(review, "equipment", []) or [])

        has_audio_system = any(
            enum_value(getattr(item, "category", None))
            in {
                enum_value(EquipmentCategory.SPEAKER),
                enum_value(EquipmentCategory.MICROPHONE),
                enum_value(EquipmentCategory.INTERCOM),
            }
            for item in equipment
        )
        if not has_audio_system:
            return []

        has_hearing_assistance = any(
            enum_value(getattr(item, "category", None))
            == enum_value(EquipmentCategory.ASSISTED_LISTENING)
            for item in equipment
        )
        if has_hearing_assistance:
            return []

        first_audio_equipment = next(
            item
            for item in equipment
            if enum_value(getattr(item, "category", None))
            in {
                enum_value(EquipmentCategory.SPEAKER),
                enum_value(EquipmentCategory.MICROPHONE),
                enum_value(EquipmentCategory.INTERCOM),
            }
        )

        return [
            EngineeringAssumption(
                assumption_id="audio_hearing_assistance_missing",
                category="compliance",
                description="Assistive listening requirements should be verified.",
                severity=AssumptionSeverity.REVIEW,
                related_equipment=getattr(first_audio_equipment, "equipment_id", None),
            )
        ]


class MicrophonePowerRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="audio_microphone_power",
            category="power",
            description="Microphones should identify power source and requirements.",
            priority=60,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []
        microphones = self._items_by_category(review, EquipmentCategory.MICROPHONE)

        for item in microphones:
            if self._has_power_reference(item):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"audio_microphone_power_missing_{item.equipment_id}",
                    category="power",
                    description="Microphone power source should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=item.equipment_id,
                )
            )

        return assumptions

    @staticmethod
    def _items_by_category(
        review: BidPackageReview,
        category: EquipmentCategory,
    ) -> list[Any]:
        equipment = list(getattr(review, "equipment", []) or [])
        target_value = enum_value(category)
        return [
            item
            for item in equipment
            if enum_value(getattr(item, "category", None)) == target_value
        ]

    @staticmethod
    def _has_power_reference(item: Any) -> bool:
        text = " ".join(
            [
                str(getattr(item, "description", "") or ""),
                " ".join(str(note) for note in getattr(item, "assumptions", []) or []),
            ]
        ).casefold()
        return any(
            token in text for token in ("power", "battery", "phantom", "48v", "poe")
        )


def register_audio_rules(registry: EngineeringRuleRegistry) -> None:
    registry.register(SpeakerAmplifierRule())
    registry.register(DSPProgrammingRule())
    registry.register(WirelessAntennaRule())
    registry.register(PagingRule())
    registry.register(HearingAssistanceRule())
    registry.register(MicrophonePowerRule())

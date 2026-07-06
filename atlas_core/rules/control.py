"""Control-focused engineering rules for Atlas Core."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atlas_core.domain.equipment import EquipmentCategory
from atlas_core.rules import EngineeringRule
from atlas_core.rules.engineering_rule_registry import EngineeringRuleRegistry
from atlas_core.utils.refactoring import enum_value

if TYPE_CHECKING:
    from atlas_core.domain import EngineeringAssumption
    from atlas_core.domain.bid_package_review import BidPackageReview


class ControlProgrammingRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="control_programming",
            category="programming",
            description="Control processors should include programming scope.",
            priority=10,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        assumptions: list[EngineeringAssumption] = []

        for item in self._control_processors(review):
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
    def _control_processors(review: BidPackageReview) -> list[Any]:
        equipment = list(getattr(review, "equipment", []) or [])
        return [
            item
            for item in equipment
            if enum_value(getattr(item, "category", None))
            == enum_value(EquipmentCategory.CONTROL_PROCESSOR)
        ]

    @staticmethod
    def _has_programming_reference(item: Any) -> bool:
        text = " ".join(
            [
                str(getattr(item, "description", "") or ""),
                " ".join(str(note) for note in getattr(item, "assumptions", []) or []),
            ]
        ).casefold()
        return any(token in text for token in ("program", "configuration", "tuning"))


def register_control_rules(registry: EngineeringRuleRegistry) -> None:
    registry.register(ControlProgrammingRule())

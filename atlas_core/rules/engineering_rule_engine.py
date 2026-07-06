"""Engineering rule evaluation engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from atlas_core.rules.engineering_rule_registry import EngineeringRuleRegistry

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview, EngineeringAssumption


class EngineeringRuleEngine:
    def __init__(self, registry: EngineeringRuleRegistry | None = None) -> None:
        self.registry = registry or EngineeringRuleRegistry()

    def evaluate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []

        for rule in self.registry.rules():
            if not rule.matches(review):
                continue

            assumptions.extend(rule.generate(review))

        deduped = self._dedupe_assumptions(assumptions)
        return sorted(deduped, key=lambda assumption: assumption.assumption_id)

    @staticmethod
    def _dedupe_assumptions(
        assumptions: list[EngineeringAssumption],
    ) -> list[EngineeringAssumption]:
        deduped: list[EngineeringAssumption] = []
        emitted: set[str] = set()

        for assumption in assumptions:
            if assumption.assumption_id in emitted:
                continue

            emitted.add(assumption.assumption_id)
            deduped.append(assumption)

        return deduped

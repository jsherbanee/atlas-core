"""Registry for engineering rules."""

from __future__ import annotations

from atlas_core.rules.engineering_rule import EngineeringRule


class EngineeringRuleRegistry:
    def __init__(self) -> None:
        self._rules_by_id: dict[str, EngineeringRule] = {}

    def register(self, rule: EngineeringRule) -> None:
        if rule.rule_id in self._rules_by_id:
            raise ValueError(f"rule_id already registered: {rule.rule_id}")

        self._rules_by_id[rule.rule_id] = rule

    def rules(self) -> list[EngineeringRule]:
        return list(self._rules_by_id.values())

    def get(self, rule_id: str) -> EngineeringRule | None:
        return self._rules_by_id.get(rule_id)

    def clear(self) -> None:
        self._rules_by_id.clear()

import pytest

from atlas_core.rules import EngineeringRule, EngineeringRuleRegistry


class AlwaysRule(EngineeringRule):
    def matches(self, review) -> bool:
        return True

    def generate(self, review):
        return []


def make_rule(rule_id: str) -> EngineeringRule:
    return AlwaysRule(
        rule_id=rule_id,
        category="test",
        description=f"Rule {rule_id}",
    )


def test_registers_and_lists_rules_in_order():
    registry = EngineeringRuleRegistry()
    rule_1 = make_rule("rule-001")
    rule_2 = make_rule("rule-002")

    registry.register(rule_1)
    registry.register(rule_2)

    assert registry.rules() == [rule_1, rule_2]


def test_get_returns_rule_by_id():
    registry = EngineeringRuleRegistry()
    rule = make_rule("rule-001")

    registry.register(rule)

    assert registry.get("rule-001") is rule
    assert registry.get("missing") is None


def test_clear_removes_all_registered_rules():
    registry = EngineeringRuleRegistry()
    registry.register(make_rule("rule-001"))

    registry.clear()

    assert registry.rules() == []


def test_rejects_duplicate_rule_ids():
    registry = EngineeringRuleRegistry()
    registry.register(make_rule("rule-001"))

    with pytest.raises(ValueError, match="rule_id already registered: rule-001"):
        registry.register(make_rule("rule-001"))

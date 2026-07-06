from atlas_core.domain import (
    AssumptionSeverity,
    BidPackageReview,
    EngineeringAssumption,
)
from atlas_core.rules import (
    EngineeringRule,
    EngineeringRuleEngine,
    EngineeringRuleRegistry,
)


class MatchRule(EngineeringRule):
    def __init__(self, assumptions: list[EngineeringAssumption], **kwargs):
        super().__init__(**kwargs)
        self._assumptions = assumptions

    def matches(self, review: BidPackageReview) -> bool:
        return True

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        return list(self._assumptions)


class NoMatchRule(EngineeringRule):
    def matches(self, review: BidPackageReview) -> bool:
        return False

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        return [
            EngineeringAssumption(
                assumption_id="should-not-be-generated",
                category="test",
                description="Should not be emitted.",
                severity=AssumptionSeverity.REVIEW,
            )
        ]


def make_review() -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )


def test_returns_empty_when_no_rules_registered():
    engine = EngineeringRuleEngine()

    assumptions = engine.evaluate(make_review())

    assert assumptions == []


def test_evaluates_matching_rules_and_collects_generated_assumptions():
    registry = EngineeringRuleRegistry()
    registry.register(
        MatchRule(
            rule_id="rule-001",
            category="mounting",
            description="Projector mount rule",
            assumptions=[
                EngineeringAssumption(
                    assumption_id="b-assumption",
                    category="mounting",
                    description="Projector mount detail missing.",
                    severity=AssumptionSeverity.REVIEW,
                )
            ],
        )
    )
    registry.register(
        NoMatchRule(
            rule_id="rule-002",
            category="wireless",
            description="Wireless rule",
        )
    )
    registry.register(
        MatchRule(
            rule_id="rule-003",
            category="specification",
            description="Specification rule",
            assumptions=[
                EngineeringAssumption(
                    assumption_id="a-assumption",
                    category="specification",
                    description="Specification reference missing.",
                    severity=AssumptionSeverity.INFORMATIONAL,
                )
            ],
        )
    )

    assumptions = EngineeringRuleEngine(registry).evaluate(make_review())

    assert [assumption.assumption_id for assumption in assumptions] == [
        "a-assumption",
        "b-assumption",
    ]


def test_dedupes_assumptions_by_assumption_id():
    duplicate_id = "duplicate-assumption"
    shared_assumption = EngineeringAssumption(
        assumption_id=duplicate_id,
        category="mounting",
        description="Duplicate assumption.",
        severity=AssumptionSeverity.REVIEW,
    )

    registry = EngineeringRuleRegistry()
    registry.register(
        MatchRule(
            rule_id="rule-001",
            category="mounting",
            description="Rule one",
            assumptions=[shared_assumption],
        )
    )
    registry.register(
        MatchRule(
            rule_id="rule-002",
            category="mounting",
            description="Rule two",
            assumptions=[
                EngineeringAssumption(
                    assumption_id=duplicate_id,
                    category="mounting",
                    description="Duplicate assumption from rule two.",
                    severity=AssumptionSeverity.REVIEW,
                )
            ],
        )
    )

    assumptions = EngineeringRuleEngine(registry).evaluate(make_review())

    assert len(assumptions) == 1
    assert assumptions[0].assumption_id == duplicate_id

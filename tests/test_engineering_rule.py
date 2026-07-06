import pytest

from atlas_core.domain import BidPackageReview
from atlas_core.rules import EngineeringRule


class StubRule(EngineeringRule):
    pass


def make_review() -> BidPackageReview:
    return BidPackageReview(
        review_id="review-001",
        project_id="project-001",
        name="Plan Review",
    )


def test_matches_raises_not_implemented_error():
    rule = StubRule(
        rule_id="rule-001",
        category="mounting",
        description="Rule description",
    )

    with pytest.raises(NotImplementedError):
        rule.matches(make_review())


def test_generate_raises_not_implemented_error():
    rule = StubRule(
        rule_id="rule-001",
        category="mounting",
        description="Rule description",
    )

    with pytest.raises(NotImplementedError):
        rule.generate(make_review())

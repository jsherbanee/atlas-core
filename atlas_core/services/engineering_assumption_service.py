"""Compatibility wrapper for engineering assumption generation."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from atlas_core.rules import (
    EngineeringRuleEngine,
    EngineeringRuleRegistry,
    register_default_engineering_rules,
)

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview, EngineeringAssumption


class EngineeringAssumptionService:
    def __init__(
        self,
        engineering_rule_engine: EngineeringRuleEngine | None = None,
        engineering_rule_registry: EngineeringRuleRegistry | None = None,
    ) -> None:
        warnings.warn(
            (
                "EngineeringAssumptionService is deprecated; use "
                "EngineeringRuleEngine with EngineeringRuleRegistry instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )

        if engineering_rule_engine is not None:
            self.engineering_rule_engine = engineering_rule_engine
        else:
            registry = engineering_rule_registry or EngineeringRuleRegistry()
            if engineering_rule_registry is None:
                register_default_engineering_rules(registry)
            self.engineering_rule_engine = EngineeringRuleEngine(registry)

    def build(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        return self.engineering_rule_engine.evaluate(review)

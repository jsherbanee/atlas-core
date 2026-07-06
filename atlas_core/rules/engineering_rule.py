"""Engineering rule abstractions for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview, EngineeringAssumption


@dataclass
class EngineeringRule:
    rule_id: str
    category: str
    description: str
    priority: int = 100

    def matches(self, review: BidPackageReview) -> bool:
        raise NotImplementedError("EngineeringRule.matches must be implemented")

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        raise NotImplementedError("EngineeringRule.generate must be implemented")

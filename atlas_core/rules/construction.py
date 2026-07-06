"""Construction-focused engineering rules for Atlas Core."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from atlas_core.rules import EngineeringRule
from atlas_core.rules.engineering_rule_registry import EngineeringRuleRegistry

if TYPE_CHECKING:
    from atlas_core.domain import EngineeringAssumption
    from atlas_core.domain.bid_package_review import BidPackageReview


class _ConstructionRuleBase(EngineeringRule):
    @staticmethod
    def _equipment(review: BidPackageReview) -> list[Any]:
        return list(getattr(review, "equipment", []) or [])

    @staticmethod
    def _detail_callouts(review: BidPackageReview) -> list[Any]:
        return list(getattr(review, "detail_callouts", []) or [])

    @staticmethod
    def _keynotes(review: BidPackageReview) -> list[Any]:
        return list(getattr(review, "keynotes", []) or [])

    @staticmethod
    def _drawing_sheets(review: BidPackageReview) -> list[Any]:
        return list(getattr(review, "drawing_sheets", []) or [])

    @staticmethod
    def _legends(review: BidPackageReview) -> list[Any]:
        return list(getattr(review, "legends", []) or [])

    @classmethod
    def _review_text(cls, review: BidPackageReview) -> str:
        parts: list[str] = [
            " ".join(str(note) for note in getattr(review, "notes", []) or []),
        ]

        parts.extend(
            " ".join(
                [
                    str(getattr(item, "description", "") or ""),
                    str(getattr(item, "model", "") or ""),
                    " ".join(
                        str(note) for note in getattr(item, "assumptions", []) or []
                    ),
                ]
            )
            for item in cls._equipment(review)
        )

        parts.extend(
            " ".join(
                [
                    str(getattr(callout, "equipment_category", "") or ""),
                    str(getattr(callout, "system_category", "") or ""),
                    str(getattr(callout, "description", "") or ""),
                    " ".join(str(note) for note in getattr(callout, "notes", []) or []),
                ]
            )
            for callout in cls._detail_callouts(review)
        )

        parts.extend(
            " ".join(
                [
                    str(getattr(keynote, "description", "") or ""),
                    str(getattr(keynote, "equipment_category", "") or ""),
                    str(getattr(keynote, "system_category", "") or ""),
                    " ".join(str(note) for note in getattr(keynote, "notes", []) or []),
                ]
            )
            for keynote in cls._keynotes(review)
        )

        parts.extend(
            " ".join(
                [
                    str(getattr(sheet, "title", "") or ""),
                    str(getattr(sheet, "discipline", "") or ""),
                    " ".join(str(note) for note in getattr(sheet, "notes", []) or []),
                ]
            )
            for sheet in cls._drawing_sheets(review)
        )

        for legend in cls._legends(review):
            parts.append(str(getattr(legend, "title", "") or ""))
            parts.extend(
                " ".join(
                    [
                        str(getattr(item, "description", "") or ""),
                        str(getattr(item, "equipment_category", "") or ""),
                        str(getattr(item, "system_category", "") or ""),
                        " ".join(
                            str(note) for note in getattr(item, "notes", []) or []
                        ),
                    ]
                )
                for item in getattr(legend, "items", []) or []
            )

        return " ".join(parts).casefold()

    @staticmethod
    def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
        for token in tokens:
            normalized = token.casefold()
            if " " in normalized:
                if normalized in text:
                    return True
                continue

            if normalized.isalnum() and len(normalized) <= 3:
                if re.search(rf"\b{re.escape(normalized)}\b", text):
                    return True
                continue

            if normalized in text:
                return True

        return False

    @staticmethod
    def _dedupe_assumptions(assumptions: list[Any]) -> list[Any]:
        deduped: list[Any] = []
        emitted: set[str] = set()

        for assumption in assumptions:
            if assumption.assumption_id in emitted:
                continue
            emitted.add(assumption.assumption_id)
            deduped.append(assumption)

        return deduped


class TravelDistanceRule(_ConstructionRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="construction_travel_distance",
            category="travel",
            description=(
                "Travel distance, lodging, mileage, and per diem requirements should "
                "be reviewed."
            ),
            priority=10,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        text = self._review_text(review)
        if not self._contains_any(
            text,
            (
                "travel",
                "distance",
                "remote site",
                "out of area",
                "overnight",
                "hotel",
                "flight",
                "mileage",
                "per diem",
            ),
        ):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id="construction_travel_distance_review",
                category="travel",
                description=(
                    "Travel distance, lodging, mileage, and per diem requirements "
                    "should be reviewed."
                ),
                severity=AssumptionSeverity.REVIEW,
            )
        ]
        return self._dedupe_assumptions(assumptions)


class MobilizationRule(_ConstructionRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="construction_mobilization",
            category="mobilization",
            description=(
                "Mobilization count, work windows, and trip charges should be "
                "reviewed."
            ),
            priority=20,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        text = self._review_text(review)
        if not self._contains_any(
            text,
            (
                "mobilization",
                "phased work",
                "multiple trips",
                "remobilization",
                "night work",
                "weekend work",
                "after hours",
            ),
        ):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id="construction_mobilization_review",
                category="mobilization",
                description=(
                    "Mobilization count, work windows, and trip charges should be "
                    "reviewed."
                ),
                severity=AssumptionSeverity.REVIEW,
            )
        ]
        return self._dedupe_assumptions(assumptions)


class LoadInRule(_ConstructionRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="construction_load_in",
            category="load_in",
            description=(
                "Load-in conditions, staging access, freight elevator access, and "
                "material handling requirements should be reviewed."
            ),
            priority=30,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        text = self._review_text(review)
        if not self._contains_any(
            text,
            (
                "loading dock",
                "freight elevator",
                "stair carry",
                "long push",
                "high rise",
                "campus",
                "crane",
                "lift",
                "laydown",
                "staging",
                "access restrictions",
            ),
        ):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id="construction_load_in_risk",
                category="load_in",
                description=(
                    "Load-in conditions, staging access, freight elevator access, and "
                    "material handling requirements should be reviewed."
                ),
                severity=AssumptionSeverity.RISK,
            )
        ]
        return self._dedupe_assumptions(assumptions)


class SiteStorageRule(_ConstructionRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="construction_site_storage",
            category="site_storage",
            description="Onsite material storage and delivery sequencing should be confirmed.",
            priority=40,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        text = self._review_text(review)
        if not self._contains_any(
            text,
            (
                "no storage",
                "limited storage",
                "secure storage",
                "daily delivery",
                "just-in-time delivery",
                "material storage",
                "laydown",
            ),
        ):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id="construction_site_storage_review",
                category="site_storage",
                description="Onsite material storage and delivery sequencing should be confirmed.",
                severity=AssumptionSeverity.REVIEW,
            )
        ]
        return self._dedupe_assumptions(assumptions)


class TrashAndCleaningRule(_ConstructionRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="construction_cleanup",
            category="cleanup",
            description=(
                "Trash removal, daily cleanup, debris handling, and dumpster "
                "responsibility should be confirmed."
            ),
            priority=50,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        text = self._review_text(review)
        if not self._contains_any(
            text,
            (
                "trash",
                "debris",
                "cleanup",
                "broom clean",
                "daily clean",
                "cleaning policy",
                "dumpster",
                "haul off",
                "waste",
            ),
        ):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id="construction_cleanup_review",
                category="cleanup",
                description=(
                    "Trash removal, daily cleanup, debris handling, and dumpster "
                    "responsibility should be confirmed."
                ),
                severity=AssumptionSeverity.REVIEW,
            )
        ]
        return self._dedupe_assumptions(assumptions)


class HealthcareSiteRule(_ConstructionRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="construction_healthcare_site",
            category="healthcare",
            description=(
                "Healthcare site protocols, infection control, dust containment, "
                "access restrictions, and safety requirements should be reviewed."
            ),
            priority=60,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        text = self._review_text(review)
        if not self._contains_any(
            text,
            (
                "healthcare",
                "hospital",
                "clinic",
                "icra",
                "infection control",
                "dust control",
                "containment",
                "patient",
                "oshpd",
                "hcai",
            ),
        ):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id="construction_healthcare_site_risk",
                category="healthcare",
                description=(
                    "Healthcare site protocols, infection control, dust containment, "
                    "access restrictions, and safety requirements should be reviewed."
                ),
                severity=AssumptionSeverity.RISK,
            )
        ]
        return self._dedupe_assumptions(assumptions)


class PrevailingWageRule(_ConstructionRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="construction_prevailing_wage",
            category="labor_compliance",
            description=(
                "Prevailing wage, certified payroll, apprenticeship, and labor "
                "compliance requirements should be reviewed."
            ),
            priority=70,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        text = self._review_text(review)
        if not self._contains_any(
            text,
            (
                "prevailing wage",
                "certified payroll",
                "dir",
                "apprenticeship",
                "public works",
                "pla",
                "union",
                "labor compliance",
                "wage determination",
            ),
        ):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id="construction_prevailing_wage_risk",
                category="labor_compliance",
                description=(
                    "Prevailing wage, certified payroll, apprenticeship, and labor "
                    "compliance requirements should be reviewed."
                ),
                severity=AssumptionSeverity.RISK,
            )
        ]
        return self._dedupe_assumptions(assumptions)


class SafetyCertificationRule(_ConstructionRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="construction_safety_certification",
            category="safety",
            description=(
                "Site safety certifications, lift requirements, fall protection, "
                "and safety orientation requirements should be confirmed."
            ),
            priority=80,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        text = self._review_text(review)
        if not self._contains_any(
            text,
            (
                "osha",
                "lift certification",
                "fall protection",
                "harness",
                "hot work",
                "confined space",
                "rigging certification",
                "jha",
                "safety orientation",
            ),
        ):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id="construction_safety_certification_review",
                category="safety",
                description=(
                    "Site safety certifications, lift requirements, fall protection, "
                    "and safety orientation requirements should be confirmed."
                ),
                severity=AssumptionSeverity.REVIEW,
            )
        ]
        return self._dedupe_assumptions(assumptions)


class CoordinationRule(_ConstructionRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="construction_coordination",
            category="coordination",
            description=(
                "Scope coordination with GC, EC, owner, network team, and other "
                "trades should be confirmed."
            ),
            priority=90,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        text = self._review_text(review)
        if not self._contains_any(
            text,
            (
                "coordinate",
                "by others",
                "gc",
                "ec",
                "owner furnished",
                "ofe",
                "nic",
                "conduit by others",
                "backing by others",
                "power by others",
                "network by others",
                "scope by others",
            ),
        ):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id="construction_coordination_review",
                category="coordination",
                description=(
                    "Scope coordination with GC, EC, owner, network team, and other "
                    "trades should be confirmed."
                ),
                severity=AssumptionSeverity.REVIEW,
            )
        ]
        return self._dedupe_assumptions(assumptions)


def register_construction_rules(registry: EngineeringRuleRegistry) -> None:
    registry.register(TravelDistanceRule())
    registry.register(MobilizationRule())
    registry.register(LoadInRule())
    registry.register(SiteStorageRule())
    registry.register(TrashAndCleaningRule())
    registry.register(HealthcareSiteRule())
    registry.register(PrevailingWageRule())
    registry.register(SafetyCertificationRule())
    registry.register(CoordinationRule())

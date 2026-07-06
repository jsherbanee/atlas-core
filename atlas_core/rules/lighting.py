"""Lighting-focused engineering rules for Atlas Core."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atlas_core.domain.equipment import EquipmentCategory
from atlas_core.rules import EngineeringRule
from atlas_core.rules.engineering_rule_registry import EngineeringRuleRegistry
from atlas_core.utils.refactoring import enum_value

if TYPE_CHECKING:
    from atlas_core.domain import EngineeringAssumption
    from atlas_core.domain.bid_package_review import BidPackageReview


class _LightingRuleBase(EngineeringRule):
    @staticmethod
    def _equipment(review: BidPackageReview) -> list[Any]:
        return list(getattr(review, "equipment", []) or [])

    @classmethod
    def _lighting_fixtures(cls, review: BidPackageReview) -> list[Any]:
        return [
            item
            for item in cls._equipment(review)
            if enum_value(getattr(item, "category", None))
            == enum_value(EquipmentCategory.LIGHTING_FIXTURE)
        ]

    @classmethod
    def _lighting_consoles(cls, review: BidPackageReview) -> list[Any]:
        return [
            item
            for item in cls._equipment(review)
            if enum_value(getattr(item, "category", None))
            == enum_value(EquipmentCategory.LIGHTING_CONSOLE)
        ]

    @staticmethod
    def _equipment_text(item: Any) -> str:
        return " ".join(
            [
                str(getattr(item, "description", "") or ""),
                str(getattr(item, "model", "") or ""),
                " ".join(str(note) for note in getattr(item, "assumptions", []) or []),
            ]
        ).casefold()

    @classmethod
    def _review_text(cls, review: BidPackageReview) -> str:
        return " ".join(cls._equipment_text(item) for item in cls._equipment(review))

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


class LightingFixtureSafetyCableRule(_LightingRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="lighting_fixture_safety_cable",
            category="safety",
            description=(
                "Lighting fixtures should include safety cable, clamp, rigging, "
                "or mounting references."
            ),
            priority=10,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        assumptions: list[EngineeringAssumption] = []
        reference_tokens = ("safety cable", "rigging", "clamp", "mount")

        for fixture in self._lighting_fixtures(review):
            text = self._equipment_text(fixture)
            if any(token in text for token in reference_tokens):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=(
                        "lighting_fixture_safety_missing_" f"{fixture.equipment_id}"
                    ),
                    category="safety",
                    description=(
                        "Lighting fixture safety cable, clamp, and overhead mounting "
                        "requirements should be verified."
                    ),
                    severity=AssumptionSeverity.RISK,
                    related_equipment=fixture.equipment_id,
                )
            )

        return self._dedupe_assumptions(assumptions)


class LightingConsoleNetworkRule(_LightingRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="lighting_console_network",
            category="control",
            description=(
                "Lighting console systems should include DMX/sACN/Art-Net and "
                "control path references."
            ),
            priority=20,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        assumptions: list[EngineeringAssumption] = []
        reference_tokens = ("network", "dmx", "sacn", "art-net", "control")

        for console in self._lighting_consoles(review):
            text = self._equipment_text(console)
            if any(token in text for token in reference_tokens):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=(
                        "lighting_console_network_missing_" f"{console.equipment_id}"
                    ),
                    category="control",
                    description=(
                        "Lighting console control network and DMX/sACN distribution "
                        "should be confirmed."
                    ),
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=console.equipment_id,
                )
            )

        return self._dedupe_assumptions(assumptions)


class LightingPowerRule(_LightingRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="lighting_power",
            category="power",
            description=(
                "Lighting fixture systems should include power and circuiting "
                "references."
            ),
            priority=30,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        assumptions: list[EngineeringAssumption] = []
        reference_tokens = ("power", "circuit", "dimmer", "relay", "distribution")

        for fixture in self._lighting_fixtures(review):
            text = self._equipment_text(fixture)
            if any(token in text for token in reference_tokens):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"lighting_power_missing_{fixture.equipment_id}",
                    category="power",
                    description=(
                        "Lighting fixture power and circuiting requirements should "
                        "be confirmed."
                    ),
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=fixture.equipment_id,
                )
            )

        return self._dedupe_assumptions(assumptions)


class DMXDistributionRule(_LightingRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="lighting_dmx_distribution",
            category="control",
            description=(
                "Lighting systems should identify DMX/sACN/Art-Net distribution "
                "components."
            ),
            priority=40,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        fixtures = self._lighting_fixtures(review)
        if not fixtures:
            return []

        review_text = self._review_text(review)
        has_distribution = any(
            token in review_text
            for token in ("dmx", "sacn", "art-net", "gateway", "node", "distribution")
        )
        if has_distribution:
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id=f"lighting_distribution_missing_{fixture.equipment_id}",
                category="control",
                description=(
                    "Lighting control distribution should be reviewed for DMX, "
                    "sACN, Art-Net, gateways, nodes, and network infrastructure."
                ),
                severity=AssumptionSeverity.REVIEW,
                related_equipment=fixture.equipment_id,
            )
            for fixture in fixtures
        ]

        return self._dedupe_assumptions(assumptions)


class HouseLightingInterfaceRule(_LightingRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="lighting_house_interface",
            category="integration",
            description=(
                "Lighting control systems should define house and architectural "
                "lighting integration."
            ),
            priority=50,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        consoles = self._lighting_consoles(review)
        if not consoles:
            return []

        review_text = self._review_text(review)
        has_interface_reference = any(
            token in review_text
            for token in (
                "house lighting",
                "architectural lighting",
                "relay",
                "dimmer",
                "integration",
            )
        )
        if has_interface_reference:
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id=(
                    "lighting_house_interface_missing_" f"{console.equipment_id}"
                ),
                category="integration",
                description=(
                    "House lighting and architectural lighting integration should "
                    "be confirmed."
                ),
                severity=AssumptionSeverity.REVIEW,
                related_equipment=console.equipment_id,
            )
            for console in consoles
        ]

        return self._dedupe_assumptions(assumptions)


class EmergencyLightingCoordinationRule(_LightingRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="lighting_emergency_coordination",
            category="life_safety",
            description=(
                "Lighting systems should coordinate emergency and life-safety "
                "requirements."
            ),
            priority=60,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        lighting_equipment = self._lighting_fixtures(review) + self._lighting_consoles(
            review
        )
        if not lighting_equipment:
            return []

        review_text = self._review_text(review)
        has_emergency_reference = any(
            token in review_text
            for token in ("emergency", "egress", "ul924", "life-safety")
        )
        if has_emergency_reference:
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id=(
                    "lighting_emergency_coordination_missing_" f"{item.equipment_id}"
                ),
                category="life_safety",
                description=(
                    "Emergency lighting and life-safety coordination should be "
                    "reviewed."
                ),
                severity=AssumptionSeverity.RISK,
                related_equipment=item.equipment_id,
            )
            for item in lighting_equipment
        ]

        return self._dedupe_assumptions(assumptions)


def register_lighting_rules(registry: EngineeringRuleRegistry) -> None:
    registry.register(LightingFixtureSafetyCableRule())
    registry.register(LightingConsoleNetworkRule())
    registry.register(LightingPowerRule())
    registry.register(DMXDistributionRule())
    registry.register(HouseLightingInterfaceRule())
    registry.register(EmergencyLightingCoordinationRule())

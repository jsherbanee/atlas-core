"""Infrastructure-focused engineering rules for Atlas Core."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atlas_core.domain.engineering_assumption import (
    AssumptionSeverity,
    EngineeringAssumption,
)
from atlas_core.domain.equipment import EquipmentCategory
from atlas_core.rules.engineering_rule import EngineeringRule
from atlas_core.rules.engineering_rule_registry import EngineeringRuleRegistry
from atlas_core.utils.refactoring import enum_value

if TYPE_CHECKING:
    from atlas_core.domain.bid_package_review import BidPackageReview


class _InfrastructureRuleBase(EngineeringRule):
    @staticmethod
    def _equipment(review: BidPackageReview) -> list[Any]:
        return list(getattr(review, "equipment", []) or [])

    @staticmethod
    def _detail_callouts(review: BidPackageReview) -> list[Any]:
        return list(getattr(review, "detail_callouts", []) or [])

    @classmethod
    def _by_category(
        cls,
        review: BidPackageReview,
        category: EquipmentCategory,
    ) -> list[Any]:
        target = enum_value(category)
        return [
            item
            for item in cls._equipment(review)
            if enum_value(getattr(item, "category", None)) == target
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
        return " ".join(
            [
                " ".join(cls._equipment_text(item) for item in cls._equipment(review)),
                " ".join(
                    " ".join(
                        [
                            str(getattr(callout, "equipment_category", "") or ""),
                            str(getattr(callout, "description", "") or ""),
                            " ".join(
                                str(note)
                                for note in getattr(callout, "notes", []) or []
                            ),
                        ]
                    )
                    for callout in cls._detail_callouts(review)
                ),
            ]
        ).casefold()


class ConduitRule(_InfrastructureRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="infrastructure_conduit",
            category="pathway",
            description="Cable infrastructure should include conduit routing assumptions.",
            priority=10,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []
        conduit_tokens = ("conduit", "emt", "raceway")

        for cable in self._by_category(review, EquipmentCategory.CABLE):
            if any(token in self._equipment_text(cable) for token in conduit_tokens):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"infrastructure_conduit_missing_{cable.equipment_id}",
                    category="pathway",
                    description="Cable conduit routing should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=cable.equipment_id,
                )
            )

        return assumptions


class BackingRule(_InfrastructureRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="infrastructure_backing",
            category="structure",
            description="Wall and ceiling backing requirements should be identified.",
            priority=20,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []
        has_backing_reference = any(
            token in self._review_text(review)
            for token in ("backing", "blocking", "support")
        )

        if has_backing_reference:
            return assumptions

        target_categories = {
            enum_value(EquipmentCategory.DISPLAY),
            enum_value(EquipmentCategory.PROJECTOR),
            enum_value(EquipmentCategory.SPEAKER),
        }

        for item in self._equipment(review):
            if enum_value(getattr(item, "category", None)) not in target_categories:
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"infrastructure_backing_missing_{item.equipment_id}",
                    category="structure",
                    description="Backing and blocking requirements should be verified.",
                    severity=AssumptionSeverity.RISK,
                    related_equipment=item.equipment_id,
                )
            )

        return assumptions


class RackCoolingRule(_InfrastructureRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="infrastructure_rack_cooling",
            category="rack",
            description="Rack cooling and ventilation should be identified.",
            priority=30,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []

        for rack in self._by_category(review, EquipmentCategory.RACK):
            text = self._equipment_text(rack)
            if "cool" in text or "vent" in text:
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"infrastructure_rack_cooling_missing_{rack.equipment_id}",
                    category="rack",
                    description="Rack cooling and ventilation should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=rack.equipment_id,
                )
            )

        return assumptions


class RackPowerRule(_InfrastructureRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="infrastructure_rack_power",
            category="power",
            description="Rack power requirements and circuiting should be identified.",
            priority=40,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []

        for rack in self._by_category(review, EquipmentCategory.RACK):
            text = self._equipment_text(rack)
            if any(token in text for token in ("power", "120v", "208v", "poe")):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"infrastructure_rack_power_missing_{rack.equipment_id}",
                    category="power",
                    description="Rack power requirements should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=rack.equipment_id,
                )
            )

        return assumptions


class RackElevationRule(_InfrastructureRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="infrastructure_rack_elevation",
            category="rack",
            description="Rack elevations should be documented for coordination.",
            priority=50,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        has_elevation_detail = any(
            "rack"
            in " ".join(
                [
                    str(getattr(callout, "equipment_category", "") or ""),
                    str(getattr(callout, "description", "") or ""),
                ]
            ).casefold()
            and "elevation"
            in " ".join(
                [
                    str(getattr(callout, "equipment_category", "") or ""),
                    str(getattr(callout, "description", "") or ""),
                ]
            ).casefold()
            for callout in self._detail_callouts(review)
        )

        if has_elevation_detail:
            return []

        return [
            EngineeringAssumption(
                assumption_id=f"infrastructure_rack_elevation_missing_{rack.equipment_id}",
                category="rack",
                description="Rack elevation details should be verified.",
                severity=AssumptionSeverity.REVIEW,
                related_equipment=rack.equipment_id,
            )
            for rack in self._by_category(review, EquipmentCategory.RACK)
        ]


class UPSRule(_InfrastructureRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="infrastructure_ups",
            category="power",
            description="Critical AV systems should identify UPS backup strategy.",
            priority=60,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        racks = self._by_category(review, EquipmentCategory.RACK)
        if not racks:
            return []

        has_ups = any(
            "ups" in self._equipment_text(item) for item in self._equipment(review)
        )
        if has_ups:
            return []

        return [
            EngineeringAssumption(
                assumption_id=f"infrastructure_ups_missing_{rack.equipment_id}",
                category="power",
                description="UPS backup requirements should be verified.",
                severity=AssumptionSeverity.REVIEW,
                related_equipment=rack.equipment_id,
            )
            for rack in racks
        ]


class GroundingRule(_InfrastructureRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="infrastructure_grounding",
            category="power",
            description="Rack and infrastructure grounding should be coordinated.",
            priority=70,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []

        for rack in self._by_category(review, EquipmentCategory.RACK):
            text = self._equipment_text(rack)
            if any(token in text for token in ("ground", "bonding", "bond")):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"infrastructure_grounding_missing_{rack.equipment_id}",
                    category="power",
                    description="Grounding and bonding requirements should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=rack.equipment_id,
                )
            )

        return assumptions


class CablePathwayRule(_InfrastructureRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="infrastructure_cable_pathway",
            category="pathway",
            description="Cable pathway routing should be identified and coordinated.",
            priority=80,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []
        pathway_tokens = ("pathway", "tray", "ladder rack", "raceway")

        for cable in self._by_category(review, EquipmentCategory.CABLE):
            text = self._equipment_text(cable)
            if any(token in text for token in pathway_tokens):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"infrastructure_pathway_missing_{cable.equipment_id}",
                    category="pathway",
                    description="Cable pathway routing should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=cable.equipment_id,
                )
            )

        return assumptions


def register_infrastructure_rules(registry: EngineeringRuleRegistry) -> None:
    registry.register(ConduitRule())
    registry.register(BackingRule())
    registry.register(RackCoolingRule())
    registry.register(RackPowerRule())
    registry.register(RackElevationRule())
    registry.register(UPSRule())
    registry.register(GroundingRule())
    registry.register(CablePathwayRule())

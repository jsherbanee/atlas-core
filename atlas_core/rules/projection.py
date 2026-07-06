"""Projection-focused engineering rules for Atlas Core."""

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


class ProjectorMountRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="projection_projector_mount",
            category="mounting",
            description=(
                "Projectors should include mounting hardware or explicit mount "
                "detail references."
            ),
            priority=10,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self._projectors(review)) and not self._has_mount_detail(review)

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        return [
            EngineeringAssumption(
                assumption_id=f"projection_mount_missing_{item.equipment_id}",
                category="mounting",
                description="Projector mounting solution should be verified.",
                severity=AssumptionSeverity.REVIEW,
                related_equipment=item.equipment_id,
            )
            for item in self._projectors(review)
        ]

    @staticmethod
    def _projectors(review: BidPackageReview) -> list[Any]:
        equipment = list(getattr(review, "equipment", []) or [])
        return [
            item
            for item in equipment
            if enum_value(getattr(item, "category", None))
            == enum_value(EquipmentCategory.PROJECTOR)
        ]

    @staticmethod
    def _has_mount_detail(review: BidPackageReview) -> bool:
        detail_callouts = list(getattr(review, "detail_callouts", []) or [])
        for callout in detail_callouts:
            value = " ".join(
                [
                    str(getattr(callout, "equipment_category", "") or ""),
                    str(getattr(callout, "description", "") or ""),
                ]
            ).casefold()
            if "mount" in value:
                return True

        return False


class ProjectorLensRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="projection_projector_lens",
            category="optics",
            description=(
                "Projectors should identify lens type and throw requirements for "
                "coordination."
            ),
            priority=20,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return any(not self._has_lens_info(item) for item in self._projectors(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []

        for item in self._projectors(review):
            if self._has_lens_info(item):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"projection_lens_missing_{item.equipment_id}",
                    category="optics",
                    description="Projector lens type and throw distance should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=item.equipment_id,
                )
            )

        return assumptions

    @classmethod
    def _projectors(cls, review: BidPackageReview) -> list[Any]:
        return ProjectorMountRule._projectors(review)

    @staticmethod
    def _has_lens_info(item: Any) -> bool:
        text = " ".join(
            [
                str(getattr(item, "description", "") or ""),
                str(getattr(item, "model", "") or ""),
                " ".join(str(note) for note in getattr(item, "assumptions", []) or []),
            ]
        ).casefold()
        return "lens" in text or "throw" in text


class ProjectionPowerRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="projection_power",
            category="power",
            description="Projection equipment should include defined power requirements.",
            priority=30,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return any(not self._has_power_info(item) for item in self._projectors(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []

        for item in self._projectors(review):
            if self._has_power_info(item):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"projection_power_missing_{item.equipment_id}",
                    category="power",
                    description="Projector power requirements should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=item.equipment_id,
                )
            )

        return assumptions

    @classmethod
    def _projectors(cls, review: BidPackageReview) -> list[Any]:
        return ProjectorMountRule._projectors(review)

    @staticmethod
    def _has_power_info(item: Any) -> bool:
        text = " ".join(
            [
                str(getattr(item, "description", "") or ""),
                " ".join(str(note) for note in getattr(item, "assumptions", []) or []),
            ]
        ).casefold()
        return any(token in text for token in ("power", "120v", "208v", "277v"))


class ProjectionStructureRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="projection_structure",
            category="structure",
            description="Projection mounting should identify structural support requirements.",
            priority=40,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self._projectors(review)) and not self._has_structure_reference(
            review
        )

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        return [
            EngineeringAssumption(
                assumption_id=f"projection_structure_missing_{item.equipment_id}",
                category="structure",
                description="Projector structural support and backing should be verified.",
                severity=AssumptionSeverity.RISK,
                related_equipment=item.equipment_id,
            )
            for item in self._projectors(review)
        ]

    @classmethod
    def _projectors(cls, review: BidPackageReview) -> list[Any]:
        return ProjectorMountRule._projectors(review)

    @staticmethod
    def _has_structure_reference(review: BidPackageReview) -> bool:
        detail_callouts = list(getattr(review, "detail_callouts", []) or [])
        for callout in detail_callouts:
            text = " ".join(
                [
                    str(getattr(callout, "description", "") or ""),
                    " ".join(str(note) for note in getattr(callout, "notes", []) or []),
                ]
            ).casefold()
            if any(token in text for token in ("structure", "support", "blocking")):
                return True

        return False


class ProjectionCoolingRule(EngineeringRule):
    def __init__(self) -> None:
        super().__init__(
            rule_id="projection_cooling",
            category="cooling",
            description="Projection equipment should include ventilation and cooling assumptions.",
            priority=50,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return any(
            not self._has_cooling_info(item)
            for item in ProjectorMountRule._projectors(review)
        )

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []

        for item in ProjectorMountRule._projectors(review):
            if self._has_cooling_info(item):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"projection_cooling_missing_{item.equipment_id}",
                    category="cooling",
                    description="Projector cooling and ventilation should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=item.equipment_id,
                )
            )

        return assumptions

    @staticmethod
    def _has_cooling_info(item: Any) -> bool:
        text = " ".join(
            [
                str(getattr(item, "description", "") or ""),
                " ".join(str(note) for note in getattr(item, "assumptions", []) or []),
            ]
        ).casefold()
        return any(token in text for token in ("cool", "cooling", "ventilation"))


def register_projection_rules(registry: EngineeringRuleRegistry) -> None:
    registry.register(ProjectorMountRule())
    registry.register(ProjectorLensRule())
    registry.register(ProjectionPowerRule())
    registry.register(ProjectionStructureRule())
    registry.register(ProjectionCoolingRule())

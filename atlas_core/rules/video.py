"""Video-focused engineering rules for Atlas Core."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from atlas_core.domain.equipment import EquipmentCategory
from atlas_core.rules import EngineeringRule
from atlas_core.rules.engineering_rule_registry import EngineeringRuleRegistry
from atlas_core.utils.refactoring import enum_value

if TYPE_CHECKING:
    from atlas_core.domain import EngineeringAssumption
    from atlas_core.domain.bid_package_review import BidPackageReview


class _VideoRuleBase(EngineeringRule):
    @staticmethod
    def _equipment(review: BidPackageReview) -> list[Any]:
        return list(getattr(review, "equipment", []) or [])

    @staticmethod
    def _detail_callouts(review: BidPackageReview) -> list[Any]:
        return list(getattr(review, "detail_callouts", []) or [])

    @classmethod
    def _equipment_by_category(
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
    def _has_detail_token(
        cls, review: BidPackageReview, tokens: tuple[str, ...]
    ) -> bool:
        for callout in cls._detail_callouts(review):
            text = " ".join(
                [
                    str(getattr(callout, "equipment_category", "") or ""),
                    str(getattr(callout, "description", "") or ""),
                    " ".join(str(note) for note in getattr(callout, "notes", []) or []),
                ]
            ).casefold()
            if any(token in text for token in tokens):
                return True

        return False

    @staticmethod
    def _dedupe_assumptions(
        assumptions: list[Any],
    ) -> list[Any]:
        deduped: list[Any] = []
        emitted: set[str] = set()

        for assumption in assumptions:
            if assumption.assumption_id in emitted:
                continue
            emitted.add(assumption.assumption_id)
            deduped.append(assumption)

        return deduped


class DisplayMountRule(_VideoRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="video_display_mount",
            category="mounting",
            description="Displays should include mounting-related detail references.",
            priority=10,
        )

    def matches(self, review: BidPackageReview) -> bool:
        displays = self._equipment_by_category(review, EquipmentCategory.DISPLAY)
        return bool(displays) and not self._has_mounting_detail(review)

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        if not self.matches(review):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id=f"video_display_mount_missing_{item.equipment_id}",
                category="mounting",
                description="Display mounting solution should be verified.",
                severity=AssumptionSeverity.REVIEW,
                related_equipment=item.equipment_id,
            )
            for item in self._equipment_by_category(review, EquipmentCategory.DISPLAY)
        ]
        return self._dedupe_assumptions(assumptions)

    @classmethod
    def _has_mounting_detail(cls, review: BidPackageReview) -> bool:
        return cls._has_detail_token(review, ("mount", "mounting", "bracket"))


class PTZConnectivityRule(_VideoRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="video_ptz_connectivity",
            category="connectivity",
            description="PTZ cameras should identify USB, IP, or control connectivity.",
            priority=20,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        assumptions: list[EngineeringAssumption] = []

        for camera in self._equipment_by_category(review, EquipmentCategory.CAMERA):
            text = self._equipment_text(camera)
            if "ptz" not in text:
                continue

            if self._has_connectivity_reference(text):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=(
                        f"video_ptz_connectivity_missing_{camera.equipment_id}"
                    ),
                    category="connectivity",
                    description="PTZ camera connectivity should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=camera.equipment_id,
                )
            )

        return self._dedupe_assumptions(assumptions)

    @staticmethod
    def _has_connectivity_reference(text: str) -> bool:
        return any(
            [
                "usb" in text,
                "control" in text,
                bool(re.search(r"\bip\b", text)),
            ]
        )


class CameraPowerRule(_VideoRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="video_camera_power",
            category="power",
            description="Camera equipment should include power references.",
            priority=30,
        )

    def matches(self, review: BidPackageReview) -> bool:
        return bool(self.generate(review))

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        assumptions: list[EngineeringAssumption] = []

        for camera in self._equipment_by_category(review, EquipmentCategory.CAMERA):
            text = self._equipment_text(camera)
            if any(token in text for token in ("power", "poe", "120v", "208v")):
                continue

            assumptions.append(
                EngineeringAssumption(
                    assumption_id=f"video_camera_power_missing_{camera.equipment_id}",
                    category="power",
                    description="Camera power requirements should be confirmed.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=camera.equipment_id,
                )
            )

        return self._dedupe_assumptions(assumptions)


class VideoWallStructureRule(_VideoRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="video_wall_structure",
            category="structure",
            description="Video wall systems should include structural support detail.",
            priority=40,
        )

    def matches(self, review: BidPackageReview) -> bool:
        video_wall_items = self._video_wall_equipment(review)
        return bool(video_wall_items) and not self._has_structure_detail(review)

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        if not self.matches(review):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id=f"video_wall_structure_missing_{item.equipment_id}",
                category="structure",
                description="Video wall structural support should be reviewed.",
                severity=AssumptionSeverity.RISK,
                related_equipment=item.equipment_id,
            )
            for item in self._video_wall_equipment(review)
        ]

        return self._dedupe_assumptions(assumptions)

    @classmethod
    def _video_wall_equipment(cls, review: BidPackageReview) -> list[Any]:
        return [
            item
            for item in cls._equipment(review)
            if "video wall" in cls._equipment_text(item)
        ]

    @classmethod
    def _has_structure_detail(cls, review: BidPackageReview) -> bool:
        return cls._has_detail_token(review, ("structure", "support", "blocking"))


class ProjectionScreenSupportRule(_VideoRuleBase):
    def __init__(self) -> None:
        super().__init__(
            rule_id="video_projection_screen_support",
            category="mounting",
            description="Projection screens should include mounting and support details.",
            priority=50,
        )

    def matches(self, review: BidPackageReview) -> bool:
        screens = self._equipment_by_category(
            review, EquipmentCategory.PROJECTION_SCREEN
        )
        return bool(screens) and not self._has_mounting_detail(review)

    def generate(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import AssumptionSeverity, EngineeringAssumption

        if not self.matches(review):
            return []

        assumptions = [
            EngineeringAssumption(
                assumption_id=(
                    f"video_projection_screen_support_missing_{item.equipment_id}"
                ),
                category="mounting",
                description="Projection screen support and mounting should be confirmed.",
                severity=AssumptionSeverity.REVIEW,
                related_equipment=item.equipment_id,
            )
            for item in self._equipment_by_category(
                review, EquipmentCategory.PROJECTION_SCREEN
            )
        ]

        return self._dedupe_assumptions(assumptions)

    @classmethod
    def _has_mounting_detail(cls, review: BidPackageReview) -> bool:
        return cls._has_detail_token(review, ("mount", "mounting", "support"))


def register_video_rules(registry: EngineeringRuleRegistry) -> None:
    registry.register(DisplayMountRule())
    registry.register(PTZConnectivityRule())
    registry.register(CameraPowerRule())
    registry.register(VideoWallStructureRule())
    registry.register(ProjectionScreenSupportRule())

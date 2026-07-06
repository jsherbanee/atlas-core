"""Engineering assumption builders for Atlas Core services."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from atlas_core.utils.refactoring import enum_value

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview, EngineeringAssumption


class EngineeringAssumptionService:
    _MOUNT_KEYWORDS = ("mount", "mounting", "ceiling mount", "wall mount")
    _RACK_KEYWORDS = ("rack", "equipment rack")
    _PROGRAMMING_KEYWORDS = ("program", "programming", "configuration")
    _ANTENNA_KEYWORDS = ("antenna", "antennae", "antenna distribution")
    _PTZ_CONNECTIVITY_KEYWORDS = ("network", "usb", "control")

    def build(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        from atlas_core.domain import (
            AssumptionSeverity,
            EngineeringAssumption,
            EquipmentCategory,
        )

        assumptions: list[EngineeringAssumption] = []
        emitted: set[str] = set()

        equipment = list(getattr(review, "equipment", []) or [])
        detail_callouts = list(getattr(review, "detail_callouts", []) or [])

        has_mount_detail = any(
            self._detail_mentions(callout, self._MOUNT_KEYWORDS)
            for callout in detail_callouts
        )
        has_rack_detail = any(
            self._detail_mentions(callout, self._RACK_KEYWORDS)
            for callout in detail_callouts
        )

        for item in equipment:
            category = self._value(getattr(item, "category", None))

            if (
                category == enum_value(EquipmentCategory.PROJECTOR)
                and not has_mount_detail
            ):
                self._add_assumption(
                    assumptions,
                    emitted,
                    EngineeringAssumption(
                        assumption_id=(
                            f"projector_mounting_detail_missing_{item.equipment_id}"
                        ),
                        category="mounting",
                        description=(
                            "No projector mounting hardware or mounting detail has "
                            "been identified."
                        ),
                        severity=AssumptionSeverity.REVIEW,
                        related_equipment=item.equipment_id,
                    ),
                )

            if (
                category == enum_value(EquipmentCategory.DISPLAY)
                and not has_mount_detail
            ):
                self._add_assumption(
                    assumptions,
                    emitted,
                    EngineeringAssumption(
                        assumption_id=(
                            f"display_mounting_detail_missing_{item.equipment_id}"
                        ),
                        category="mounting",
                        description="Display mounting solution should be confirmed.",
                        severity=AssumptionSeverity.REVIEW,
                        related_equipment=item.equipment_id,
                    ),
                )

            if category == enum_value(EquipmentCategory.RACK) and not has_rack_detail:
                self._add_assumption(
                    assumptions,
                    emitted,
                    EngineeringAssumption(
                        assumption_id=f"rack_detail_missing_{item.equipment_id}",
                        category="rack",
                        description="Equipment rack details should be confirmed.",
                        severity=AssumptionSeverity.RISK,
                        related_equipment=item.equipment_id,
                    ),
                )

            if category in {
                enum_value(EquipmentCategory.DSP),
                enum_value(EquipmentCategory.CONTROL_PROCESSOR),
            } and not self._equipment_mentions(item, self._PROGRAMMING_KEYWORDS):
                self._add_assumption(
                    assumptions,
                    emitted,
                    EngineeringAssumption(
                        assumption_id=f"programming_scope_unverified_{item.equipment_id}",
                        category="programming",
                        description="DSP or control programming scope should be verified.",
                        severity=AssumptionSeverity.REVIEW,
                        related_equipment=item.equipment_id,
                    ),
                )

            if (
                category == enum_value(EquipmentCategory.MICROPHONE)
                and "wireless" in self._equipment_text(item)
                and not self._has_antenna_equipment(equipment)
            ):
                self._add_assumption(
                    assumptions,
                    emitted,
                    EngineeringAssumption(
                        assumption_id=(
                            "wireless_microphone_antenna_unverified_"
                            f"{item.equipment_id}"
                        ),
                        category="wireless",
                        description=(
                            "Wireless microphone antenna distribution should be "
                            "reviewed."
                        ),
                        severity=AssumptionSeverity.RISK,
                        related_equipment=item.equipment_id,
                    ),
                )

            if (
                category == enum_value(EquipmentCategory.CAMERA)
                and "ptz" in self._equipment_text(item)
                and not self._equipment_mentions(item, self._PTZ_CONNECTIVITY_KEYWORDS)
            ):
                self._add_assumption(
                    assumptions,
                    emitted,
                    EngineeringAssumption(
                        assumption_id=f"ptz_connectivity_unverified_{item.equipment_id}",
                        category="connectivity",
                        description="PTZ camera connectivity should be verified.",
                        severity=AssumptionSeverity.REVIEW,
                        related_equipment=item.equipment_id,
                    ),
                )

            if not self._has_specification_reference(item):
                self._add_assumption(
                    assumptions,
                    emitted,
                    EngineeringAssumption(
                        assumption_id=(
                            "equipment_specification_reference_missing_"
                            f"{item.equipment_id}"
                        ),
                        category="specification",
                        description=(
                            "Equipment should be validated against specifications."
                        ),
                        severity=AssumptionSeverity.INFORMATIONAL,
                        related_equipment=item.equipment_id,
                    ),
                )

        return assumptions

    @staticmethod
    def _add_assumption(
        assumptions: list[EngineeringAssumption],
        emitted: set[str],
        assumption: EngineeringAssumption,
    ) -> None:
        if assumption.assumption_id in emitted:
            return

        emitted.add(assumption.assumption_id)
        assumptions.append(assumption)

    @classmethod
    def _equipment_text(cls, item: Any) -> str:
        return " ".join(
            [
                str(getattr(item, "description", "") or ""),
                str(getattr(item, "model", "") or ""),
                " ".join(str(note) for note in getattr(item, "assumptions", []) or []),
            ]
        ).casefold()

    @classmethod
    def _detail_mentions(cls, callout: Any, keywords: tuple[str, ...]) -> bool:
        value = " ".join(
            [
                str(getattr(callout, "equipment_category", "") or ""),
                str(getattr(callout, "description", "") or ""),
                " ".join(str(note) for note in getattr(callout, "notes", []) or []),
            ]
        ).casefold()
        return any(keyword in value for keyword in keywords)

    @classmethod
    def _equipment_mentions(cls, item: Any, keywords: tuple[str, ...]) -> bool:
        value = cls._equipment_text(item)
        return any(keyword in value for keyword in keywords)

    @classmethod
    def _has_antenna_equipment(cls, equipment: list[Any]) -> bool:
        for item in equipment:
            if cls._equipment_mentions(item, cls._ANTENNA_KEYWORDS):
                return True

        return False

    @staticmethod
    def _has_specification_reference(item: Any) -> bool:
        specification_reference = getattr(item, "specification_reference", None)
        return isinstance(specification_reference, str) and bool(
            specification_reference.strip()
        )

    @staticmethod
    def _value(value: Any) -> Any:
        return enum_value(value)

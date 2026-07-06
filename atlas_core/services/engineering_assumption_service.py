"""Engineering assumption builders for Atlas Core services."""

from __future__ import annotations

from typing import Any

from typing import TYPE_CHECKING

from atlas_core.domain.engineering_assumption import (
    AssumptionSeverity,
    EngineeringAssumption,
)
from atlas_core.utils.refactoring import enum_value

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview


class EngineeringAssumptionService:
    def build(self, review: BidPackageReview) -> list[EngineeringAssumption]:
        assumptions: list[EngineeringAssumption] = []
        emitted: set[str] = set()

        equipment = list(review.equipment)
        detail_callouts = list(getattr(review, "detail_callouts", []))

        has_mount_detail = any(
            self._value(getattr(callout, "equipment_category", None)) == "mount"
            for callout in detail_callouts
        )
        has_rack_detail = any(
            self._value(getattr(callout, "equipment_category", None)) == "rack"
            for callout in detail_callouts
        )

        projectors = [
            item for item in equipment if self._value(item.category) == "projector"
        ]
        if projectors and not has_mount_detail:
            self._add_assumption(
                assumptions,
                emitted,
                EngineeringAssumption(
                    assumption_id="projector_mounting_detail_missing",
                    category="mounting",
                    description="No projector mounting hardware has been identified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=projectors[0].equipment_id,
                ),
            )

        displays = [item for item in equipment if self._value(item.category) == "display"]
        if displays and not has_mount_detail:
            self._add_assumption(
                assumptions,
                emitted,
                EngineeringAssumption(
                    assumption_id="display_mounting_detail_missing",
                    category="mounting",
                    description="Display mounting solution should be confirmed.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=displays[0].equipment_id,
                ),
            )

        racks = [item for item in equipment if self._value(item.category) == "rack"]
        if racks and not has_rack_detail:
            self._add_assumption(
                assumptions,
                emitted,
                EngineeringAssumption(
                    assumption_id="rack_detail_missing",
                    category="rack",
                    description="Equipment rack details should be confirmed.",
                    severity=AssumptionSeverity.RISK,
                    related_equipment=racks[0].equipment_id,
                ),
            )

        dsp_items = [item for item in equipment if self._value(item.category) == "dsp"]
        if dsp_items and not any(self._has_programming_notes(item) for item in dsp_items):
            self._add_assumption(
                assumptions,
                emitted,
                EngineeringAssumption(
                    assumption_id="dsp_programming_scope_unverified",
                    category="programming",
                    description="DSP programming scope should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=dsp_items[0].equipment_id,
                ),
            )

        wireless_microphones = [
            item
            for item in equipment
            if self._value(item.category) == "microphone"
            and "wireless" in self._equipment_text(item)
        ]
        if wireless_microphones and not any(
            self._is_antenna_equipment(item) for item in equipment
        ):
            self._add_assumption(
                assumptions,
                emitted,
                EngineeringAssumption(
                    assumption_id="wireless_microphone_antenna_unverified",
                    category="wireless",
                    description=(
                        "Wireless microphone antenna distribution should be "
                        "reviewed."
                    ),
                    severity=AssumptionSeverity.RISK,
                    related_equipment=wireless_microphones[0].equipment_id,
                ),
            )

        ptz_cameras = [
            item
            for item in equipment
            if self._value(item.category) == "camera"
            and "ptz" in self._equipment_text(item)
        ]
        if ptz_cameras and not self._has_usb_network_path(ptz_cameras, equipment):
            self._add_assumption(
                assumptions,
                emitted,
                EngineeringAssumption(
                    assumption_id="ptz_connectivity_unverified",
                    category="connectivity",
                    description="PTZ camera connectivity should be verified.",
                    severity=AssumptionSeverity.REVIEW,
                    related_equipment=ptz_cameras[0].equipment_id,
                ),
            )

        if equipment and any(not self._has_power_reference(item) for item in equipment):
            self._add_assumption(
                assumptions,
                emitted,
                EngineeringAssumption(
                    assumption_id="equipment_power_reference_missing",
                    category="power",
                    description="Power requirements should be confirmed.",
                    severity=AssumptionSeverity.REVIEW,
                ),
            )

        if equipment and any(
            not isinstance(item.specification_reference, str)
            or not item.specification_reference.strip()
            for item in equipment
        ):
            self._add_assumption(
                assumptions,
                emitted,
                EngineeringAssumption(
                    assumption_id="equipment_specification_reference_missing",
                    category="specification",
                    description="Equipment should be validated against specifications.",
                    severity=AssumptionSeverity.INFORMATIONAL,
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
    def _has_programming_notes(cls, item: Any) -> bool:
        return "program" in cls._equipment_text(item)

    @classmethod
    def _is_antenna_equipment(cls, item: Any) -> bool:
        return "antenna" in cls._equipment_text(item)

    @classmethod
    def _has_usb_network_path(cls, ptz_items: list[Any], equipment: list[Any]) -> bool:
        connectivity_tokens = ("usb", "network", "ethernet", "cat6", "cat 6")

        for item in ptz_items:
            if any(token in cls._equipment_text(item) for token in connectivity_tokens):
                return True

        for item in equipment:
            if cls._value(getattr(item, "category", None)) == "network":
                return True
            if any(token in cls._equipment_text(item) for token in connectivity_tokens):
                return True

        return False

    @classmethod
    def _has_power_reference(cls, item: Any) -> bool:
        power_tokens = ("power", "120v", "208v", "277v", "poe")
        return any(token in cls._equipment_text(item) for token in power_tokens)

    @staticmethod
    def _value(value: Any) -> Any:
        return enum_value(value)

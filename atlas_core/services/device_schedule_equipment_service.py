"""Convert device schedule domain objects into equipment domain objects."""

from __future__ import annotations

from atlas_core.domain.device_schedule import DeviceSchedule, DeviceScheduleItem
from atlas_core.domain.equipment import Equipment, EquipmentCategory


class DeviceScheduleEquipmentService:
    def equipment_from_schedule(self, schedule: DeviceSchedule) -> list[Equipment]:
        return [self.equipment_from_item(item) for item in schedule.items]

    def equipment_from_item(self, item: DeviceScheduleItem) -> Equipment:
        assumptions = [f"Created from device schedule item {item.tag}."]
        assumptions.extend(item.notes)

        return Equipment(
            equipment_id=f"equipment-{item.item_id}",
            description=item.description,
            category=self._infer_category(item),
            quantity=item.quantity,
            manufacturer=item.manufacturer,
            model=item.model,
            room_id=None,
            system_id=None,
            drawing_reference=item.drawing_reference,
            specification_reference=item.specification_reference,
            confidence=item.confidence,
            assumptions=assumptions,
        )

    @staticmethod
    def _infer_category(item: DeviceScheduleItem) -> EquipmentCategory:
        haystack = " ".join(
            part
            for part in [item.tag, item.description, item.manufacturer, item.model]
            if part
        ).lower()

        if "assisted listening" in haystack:
            return EquipmentCategory.ASSISTED_LISTENING
        if (
            "control processor" in haystack
            or "q-sys" in haystack
            or "qsys" in haystack
            or "crestron" in haystack
        ):
            return EquipmentCategory.CONTROL_PROCESSOR
        if "lighting fixture" in haystack:
            return EquipmentCategory.LIGHTING_FIXTURE
        if "lighting console" in haystack:
            return EquipmentCategory.LIGHTING_CONSOLE
        if "loudspeaker" in haystack or "speaker" in haystack:
            return EquipmentCategory.SPEAKER
        if "amplifier" in haystack or " amp " in f" {haystack} ":
            return EquipmentCategory.AMPLIFIER
        if "projector" in haystack:
            return EquipmentCategory.PROJECTOR
        if "display" in haystack or "monitor" in haystack or "signage" in haystack:
            return EquipmentCategory.DISPLAY
        if "microphone" in haystack or " mic " in f" {haystack} ":
            return EquipmentCategory.MICROPHONE
        if "camera" in haystack or "ptz" in haystack:
            return EquipmentCategory.CAMERA
        if "rack" in haystack:
            return EquipmentCategory.RACK
        if "drapery" in haystack or "curtain" in haystack or "traveler" in haystack:
            return EquipmentCategory.DRAPERY
        if "intercom" in haystack:
            return EquipmentCategory.INTERCOM

        return EquipmentCategory.UNKNOWN

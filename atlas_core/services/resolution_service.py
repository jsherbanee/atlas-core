"""Apply resolver outputs to Atlas domain objects."""

from typing import Any

from atlas_core.domain import Equipment, EquipmentCategory, EquipmentStatus
from atlas_core.rules import Resolution, ResolutionAction


class ResolutionService:
    def apply_review_resolutions(
        self,
        equipment: list[Any],
        resolutions: list[Resolution],
    ) -> None:
        equipment_by_id = {}
        for item in equipment:
            equipment_id = self._equipment_id(item)
            if equipment_id != "":
                equipment_by_id[equipment_id] = item

        for resolution in resolutions:
            if resolution.action is not ResolutionAction.MARK_FOR_REVIEW:
                continue

            item = equipment_by_id.get(resolution.target_id)
            if item is None:
                continue

            if hasattr(item, "mark_for_review"):
                self._mark_for_review(item, resolution.message)
            elif hasattr(item, "review_required"):
                item.review_required = True

    def create_placeholder_equipment(
        self, resolutions: list[Resolution]
    ) -> list[Equipment]:
        placeholder_equipment: list[Equipment] = []
        emitted_equipment_ids: set[str] = set()

        for resolution in resolutions:
            if resolution.action is not ResolutionAction.ADD_PLACEHOLDER:
                continue

            equipment_id = (
                f"placeholder-{resolution.rule_id.lower()}-{resolution.target_id}"
            )
            if equipment_id in emitted_equipment_ids:
                continue

            emitted_equipment_ids.add(equipment_id)
            placeholder_equipment.append(
                Equipment(
                    equipment_id=equipment_id,
                    description=self._description(resolution),
                    category=self._equipment_category(
                        resolution.suggested_category
                    ),
                    manufacturer=resolution.suggested_manufacturer,
                    model=resolution.suggested_model,
                    system_id=resolution.source_system_id,
                    room_id=resolution.source_room_id,
                    building_id=resolution.source_building_id,
                    status=EquipmentStatus.PLACEHOLDER,
                    confidence=resolution.confidence,
                    assumptions=[resolution.message],
                    review_required=True,
                )
            )

        return placeholder_equipment

    @staticmethod
    def _description(resolution: Resolution) -> str:
        if (
            resolution.suggested_description
            and resolution.suggested_description.strip()
        ):
            return resolution.suggested_description.strip()

        return resolution.message

    @staticmethod
    def _equipment_category(
        suggested_category: str | None,
    ) -> EquipmentCategory:
        if suggested_category is None or not suggested_category.strip():
            return EquipmentCategory.UNKNOWN

        try:
            return EquipmentCategory(suggested_category)
        except ValueError:
            return EquipmentCategory.UNKNOWN

    @staticmethod
    def _equipment_id(item: Any) -> str:
        if item is None:
            return ""

        if hasattr(item, "to_dict"):
            value = item.to_dict().get("equipment_id")
        else:
            value = getattr(item, "equipment_id", "")

        if not isinstance(value, str):
            return ""

        return value.strip()

    @staticmethod
    def _mark_for_review(item: Any, message: str) -> None:
        assumptions = getattr(item, "assumptions", None)
        if isinstance(assumptions, list) and message in assumptions:
            if hasattr(item, "review_required"):
                item.review_required = True
            return

        item.mark_for_review(message)

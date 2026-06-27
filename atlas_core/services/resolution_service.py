"""Apply resolver outputs to Atlas domain objects."""

from atlas_core.domain import Equipment, EquipmentCategory, EquipmentStatus
from atlas_core.rules import Resolution, ResolutionAction


class ResolutionService:
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

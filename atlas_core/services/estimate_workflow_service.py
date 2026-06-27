"""Estimate workflow orchestration for Atlas Core."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from atlas_core.rules import Resolution, Resolver
from atlas_core.services import (
    EquipmentMatrixRow,
    EquipmentMatrixService,
    ResolutionService,
)


@dataclass
class EstimateWorkflowResult:
    rows: list[EquipmentMatrixRow]
    resolutions: list[Resolution]
    placeholder_equipment_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": [row.to_dict() for row in self.rows],
            "resolutions": [
                self._resolution_to_dict(resolution)
                for resolution in self.resolutions
            ],
            "placeholder_equipment_count": self.placeholder_equipment_count,
        }

    @staticmethod
    def _resolution_to_dict(resolution: Resolution) -> dict[str, Any]:
        data = dict(resolution.__dict__)
        action = data.get("action")

        if isinstance(action, Enum):
            data["action"] = action.value

        return data


class EstimateWorkflowService:
    def __init__(
        self,
        resolver: Resolver | None = None,
        resolution_service: ResolutionService | None = None,
    ) -> None:
        self.resolver = resolver or Resolver()
        self.resolution_service = resolution_service or ResolutionService()

    def build_equipment_matrix_with_resolutions(
        self,
        buildings: list[Any] | None = None,
        rooms: list[Any] | None = None,
        spaces: list[Any] | None = None,
        scenes: list[Any] | None = None,
        systems: list[Any] | None = None,
        equipment: list[Any] | None = None,
    ) -> EstimateWorkflowResult:
        building_items = list(buildings or [])
        room_items = list(rooms or [])
        space_items = list(spaces or [])
        scene_items = list(scenes or [])
        system_items = list(systems or [])
        equipment_items = list(equipment or [])

        resolutions = self.resolver.resolve(
            equipment_items,
            systems=system_items,
        )
        self.resolution_service.apply_review_resolutions(
            equipment_items,
            resolutions,
        )
        placeholder_equipment = (
            self.resolution_service.create_placeholder_equipment(resolutions)
        )
        rows = EquipmentMatrixService(
            buildings=building_items,
            rooms=room_items,
            spaces=space_items,
            scenes=scene_items,
            systems=system_items,
            equipment=equipment_items + placeholder_equipment,
        ).build_rows()

        return EstimateWorkflowResult(
            rows=rows,
            resolutions=resolutions,
            placeholder_equipment_count=len(placeholder_equipment),
        )

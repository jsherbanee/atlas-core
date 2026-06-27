"""Build equipment matrix rows from Atlas domain objects."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


MatrixNumber = int | float | str
MatrixBool = bool | str


@dataclass
class EquipmentMatrixRow:
    project_building_id: str = ""
    building_name: str = ""
    room_id: str = ""
    room_name: str = ""
    space_id: str = ""
    space_name: str = ""
    scene_id: str = ""
    scene_name: str = ""
    system_id: str = ""
    system_name: str = ""
    system_category: str = ""
    equipment_id: str = ""
    description: str = ""
    equipment_category: str = ""
    manufacturer: str = ""
    model: str = ""
    quantity: MatrixNumber = ""
    status: str = ""
    budget_cost: MatrixNumber = ""
    sell_price: MatrixNumber = ""
    labor_template: str = ""
    drawing_reference: str = ""
    specification_reference: str = ""
    confidence: MatrixNumber = ""
    review_required: MatrixBool = ""
    assumptions: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EquipmentMatrixService:
    def __init__(
        self,
        buildings: list[Any] | None = None,
        rooms: list[Any] | None = None,
        spaces: list[Any] | None = None,
        scenes: list[Any] | None = None,
        systems: list[Any] | None = None,
        equipment: list[Any] | None = None,
    ) -> None:
        self.buildings = list(buildings or [])
        self.rooms = list(rooms or [])
        self.spaces = list(spaces or [])
        self.scenes = list(scenes or [])
        self.systems = list(systems or [])
        self.equipment = list(equipment or [])

        self._buildings_by_id = self._index_by(self.buildings, "building_id")
        self._rooms_by_id = self._index_by(self.rooms, "room_id")
        self._spaces_by_id = self._index_by(self.spaces, "space_id")
        self._scenes_by_id = self._index_by(self.scenes, "scene_id")
        self._systems_by_id = self._index_by(self.systems, "system_id")

    def build_rows(self) -> list[EquipmentMatrixRow]:
        return [self._build_equipment_row(item) for item in self.equipment]

    def _build_equipment_row(self, equipment: Any) -> EquipmentMatrixRow:
        equipment_system_id = self._value(equipment, "system_id")
        system = self._systems_by_id.get(equipment_system_id)

        equipment_room_id = self._value(equipment, "room_id")
        system_room_id = self._value(system, "room_id")
        room_id = system_room_id or equipment_room_id
        room = self._rooms_by_id.get(room_id)

        room_building_id = self._value(room, "building_id")
        system_building_id = self._value(system, "building_id")
        equipment_building_id = self._value(equipment, "building_id")
        building_id = (
            room_building_id or system_building_id or equipment_building_id
        )
        building = self._buildings_by_id.get(building_id)

        equipment_space_id = getattr(equipment, "space_id", None)
        space = self._spaces_by_id.get(equipment_space_id)

        equipment_scene_id = getattr(equipment, "scene_id", None)
        scene = self._scenes_by_id.get(equipment_scene_id)

        return EquipmentMatrixRow(
            project_building_id=self._value(building, "building_id", building_id),
            building_name=self._value(building, "name"),
            room_id=self._value(room, "room_id", room_id),
            room_name=self._value(room, "name"),
            space_id=self._value(space, "space_id", equipment_space_id or ""),
            space_name=self._value(space, "name"),
            scene_id=self._value(scene, "scene_id", equipment_scene_id or ""),
            scene_name=self._value(scene, "name"),
            system_id=self._value(system, "system_id", equipment_system_id),
            system_name=self._value(system, "name"),
            system_category=self._value(system, "category"),
            equipment_id=self._value(equipment, "equipment_id"),
            description=self._value(equipment, "description"),
            equipment_category=self._value(equipment, "category"),
            manufacturer=self._value(equipment, "manufacturer"),
            model=self._value(equipment, "model"),
            quantity=self._value(equipment, "quantity"),
            status=self._value(equipment, "status"),
            budget_cost=self._value(equipment, "budget_cost"),
            sell_price=self._value(equipment, "sell_price"),
            labor_template=self._value(equipment, "labor_template"),
            drawing_reference=self._value(equipment, "drawing_reference"),
            specification_reference=self._value(
                equipment, "specification_reference"
            ),
            confidence=self._value(equipment, "confidence"),
            review_required=self._value(equipment, "review_required"),
            assumptions=self._join_values(self._value(equipment, "assumptions")),
        )

    @classmethod
    def _index_by(cls, items: list[Any], field_name: str) -> dict[str, Any]:
        indexed = {}

        for item in items:
            value = cls._value(item, field_name)
            if value != "":
                indexed[str(value)] = item

        return indexed

    @staticmethod
    def _as_dict(item: Any) -> dict[str, Any]:
        if item is None or not hasattr(item, "to_dict"):
            return {}

        return item.to_dict()

    @classmethod
    def _value(cls, item: Any, field_name: str, default: Any = "") -> Any:
        if item is None:
            return default

        data = cls._as_dict(item)
        value = data.get(field_name, getattr(item, field_name, default))

        if value is None:
            return default

        if isinstance(value, Enum):
            return value.value

        return value

    @staticmethod
    def _join_values(value: Any) -> str:
        if value in ("", None):
            return ""

        if isinstance(value, str):
            return value

        return "; ".join(str(item) for item in value if item not in ("", None))

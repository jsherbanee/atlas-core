"""Manufacturer review helpers for Atlas Core services."""

from dataclasses import asdict, dataclass

from atlas_core.domain import Equipment
from atlas_core.registry import ManufacturerRegistry


@dataclass
class ManufacturerReviewIssue:
    equipment_id: str
    manufacturer: str
    message: str
    severity: str = "review"

    def to_dict(self) -> dict:
        return asdict(self)


class ManufacturerReviewService:
    def __init__(self, manufacturer_registry: ManufacturerRegistry) -> None:
        self.manufacturer_registry = manufacturer_registry

    def review_equipment(
        self,
        equipment: list[Equipment],
    ) -> list[ManufacturerReviewIssue]:
        issues: list[ManufacturerReviewIssue] = []
        emitted: set[tuple[str, str]] = set()

        for item in equipment:
            manufacturer = self._manufacturer(item)
            if manufacturer is None:
                continue

            equipment_id = item.equipment_id
            key = (equipment_id, manufacturer.casefold())
            if key in emitted:
                continue

            if not self.manufacturer_registry.requires_review(manufacturer):
                continue

            emitted.add(key)
            issues.append(
                ManufacturerReviewIssue(
                    equipment_id=equipment_id,
                    manufacturer=manufacturer,
                    message=self._message(manufacturer),
                )
            )

        return issues

    def _message(self, manufacturer: str) -> str:
        if self.manufacturer_registry.get_by_name(manufacturer) is None:
            return "Manufacturer is not registered and requires estimator review."

        return "Manufacturer is registered but requires estimator review."

    @staticmethod
    def _manufacturer(equipment: Equipment) -> str | None:
        manufacturer = equipment.manufacturer
        if manufacturer is None or not manufacturer.strip():
            return None

        return manufacturer.strip()

"""Cross-reference helpers for Atlas Core bid package review."""

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from atlas_core.domain import (
    DrawingSheet,
    Equipment,
    IntegratedSystem,
    SpecificationSection,
)


class CrossReferenceType(str, Enum):
    DRAWING_TO_SPEC = "drawing_to_spec"
    EQUIPMENT_TO_DRAWING = "equipment_to_drawing"
    EQUIPMENT_TO_SPEC = "equipment_to_spec"
    SYSTEM_TO_DRAWING = "system_to_drawing"
    SYSTEM_TO_SPEC = "system_to_spec"
    UNKNOWN = "unknown"


@dataclass
class CrossReference:
    reference_type: CrossReferenceType
    source_id: str
    target_id: str
    message: str
    confidence: float = 0.75

    def __post_init__(self) -> None:
        if not isinstance(self.reference_type, CrossReferenceType):
            self.reference_type = CrossReferenceType(self.reference_type)

        self.source_id = self._normalize_required_text("source_id", self.source_id)
        self.target_id = self._normalize_required_text("target_id", self.target_id)
        self.message = self._normalize_required_text("message", self.message)

        if (
            not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reference_type"] = self.reference_type.value
        return data

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


class CrossReferenceService:
    def build_references(
        self,
        drawings: list[DrawingSheet] | None = None,
        specifications: list[SpecificationSection] | None = None,
        systems: list[IntegratedSystem] | None = None,
        equipment: list[Equipment] | None = None,
    ) -> list[CrossReference]:
        drawing_items = list(drawings or [])
        specification_items = list(specifications or [])
        system_items = list(systems or [])
        equipment_items = list(equipment or [])

        drawing_by_number = {
            self._match_key(drawing.sheet_number): drawing
            for drawing in drawing_items
        }
        specification_by_number = {
            self._match_key(specification.section_number): specification
            for specification in specification_items
        }
        audiovisual_specs = [
            specification
            for specification in specification_items
            if self._is_audiovisual_specification(specification)
        ]

        references: list[CrossReference] = []
        emitted: set[tuple[CrossReferenceType, str, str]] = set()

        for item in equipment_items:
            self._add_equipment_references(
                item,
                drawing_by_number,
                specification_by_number,
                references,
                emitted,
            )

        for system in system_items:
            for specification in self._matching_system_specifications(
                system,
                specification_items,
                audiovisual_specs,
            ):
                self._add_reference(
                    references,
                    emitted,
                    CrossReference(
                        reference_type=CrossReferenceType.SYSTEM_TO_SPEC,
                        source_id=system.system_id,
                        target_id=specification.section_id,
                        message=(
                            f"System {system.system_id} aligns with "
                            f"specification {specification.section_number}."
                        ),
                    ),
                )

        for drawing in drawing_items:
            if not self._drawing_suggests_av(drawing):
                continue

            for specification in audiovisual_specs:
                self._add_reference(
                    references,
                    emitted,
                    CrossReference(
                        reference_type=CrossReferenceType.DRAWING_TO_SPEC,
                        source_id=drawing.sheet_id,
                        target_id=specification.section_id,
                        message=(
                            f"Drawing {drawing.sheet_number} aligns with "
                            f"specification {specification.section_number}."
                        ),
                    ),
                )

        return references

    def _add_equipment_references(
        self,
        equipment: Equipment,
        drawing_by_number: dict[str, DrawingSheet],
        specification_by_number: dict[str, SpecificationSection],
        references: list[CrossReference],
        emitted: set[tuple[CrossReferenceType, str, str]],
    ) -> None:
        drawing = drawing_by_number.get(self._match_key(equipment.drawing_reference))
        if drawing is not None:
            self._add_reference(
                references,
                emitted,
                CrossReference(
                    reference_type=CrossReferenceType.EQUIPMENT_TO_DRAWING,
                    source_id=equipment.equipment_id,
                    target_id=drawing.sheet_id,
                    message=(
                        f"Equipment {equipment.equipment_id} references "
                        f"drawing {drawing.sheet_number}."
                    ),
                    confidence=0.9,
                ),
            )

        specification = specification_by_number.get(
            self._match_key(equipment.specification_reference)
        )
        if specification is not None:
            self._add_reference(
                references,
                emitted,
                CrossReference(
                    reference_type=CrossReferenceType.EQUIPMENT_TO_SPEC,
                    source_id=equipment.equipment_id,
                    target_id=specification.section_id,
                    message=(
                        f"Equipment {equipment.equipment_id} references "
                        f"specification {specification.section_number}."
                    ),
                    confidence=0.9,
                ),
            )

    def _matching_system_specifications(
        self,
        system: IntegratedSystem,
        specifications: list[SpecificationSection],
        audiovisual_specs: list[SpecificationSection],
    ) -> list[SpecificationSection]:
        category = self._value(system.category)
        if category in {"audio", "video", "control", "projection", "display"}:
            return audiovisual_specs

        return [
            specification
            for specification in specifications
            if self._value(specification.discipline) == category
        ]

    @classmethod
    def _add_reference(
        cls,
        references: list[CrossReference],
        emitted: set[tuple[CrossReferenceType, str, str]],
        reference: CrossReference,
    ) -> None:
        key = (
            reference.reference_type,
            reference.source_id,
            reference.target_id,
        )
        if key in emitted:
            return

        emitted.add(key)
        references.append(reference)

    @classmethod
    def _is_audiovisual_specification(
        cls,
        specification: SpecificationSection,
    ) -> bool:
        discipline = cls._value(specification.discipline)
        normalized_title = specification.title.casefold()
        return (
            discipline == "audiovisual"
            or cls._match_key(specification.section_number).startswith("2741")
            or "audiovisual" in normalized_title
            or "audio visual" in normalized_title
            or "audio-video" in normalized_title
        )

    @classmethod
    def _drawing_suggests_av(cls, drawing: DrawingSheet) -> bool:
        normalized_sheet_number = cls._match_key(drawing.sheet_number)
        normalized_title = drawing.title.casefold()
        return (
            normalized_sheet_number.startswith("av")
            or "audiovisual" in normalized_title
            or "audio visual" in normalized_title
            or re.search(r"\bav\b", normalized_title) is not None
        )

    @staticmethod
    def _match_key(value: Any) -> str:
        if not isinstance(value, str):
            return ""

        return "".join(
            character
            for character in value.casefold()
            if character.isalnum()
        )

    @staticmethod
    def _value(value: Any) -> Any:
        return getattr(value, "value", value)

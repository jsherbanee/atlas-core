"""Equipment detection helpers for Atlas Core plan review."""

import re
from dataclasses import dataclass

from atlas_core.domain import (
    DrawingSheet,
    Equipment,
    EquipmentCategory,
    SpecificationSection,
)


@dataclass(frozen=True)
class _SourceText:
    text: str
    drawing_reference: str | None = None
    specification_reference: str | None = None


class EquipmentDetectionService:
    def detect_equipment(
        self,
        drawings: list[DrawingSheet] | None = None,
        specifications: list[SpecificationSection] | None = None,
        room_id: str | None = None,
        building_id: str | None = None,
        system_id: str | None = None,
    ) -> list[Equipment]:
        sources = self._source_texts(drawings or [], specifications or [])
        equipment: list[Equipment] = []
        emitted: set[str] = set()

        for definition in self._definitions():
            source = self._first_matching_source(definition["matches"], sources)
            if source is None:
                continue

            self._add_equipment(
                equipment=equipment,
                emitted=emitted,
                equipment_id=definition["equipment_id"],
                description=definition["description"],
                category=definition["category"],
                source=source,
                room_id=room_id,
                building_id=building_id,
                system_id=system_id,
            )

        return equipment

    @classmethod
    def _source_texts(
        cls,
        drawings: list[DrawingSheet],
        specifications: list[SpecificationSection],
    ) -> list[_SourceText]:
        sources: list[_SourceText] = []

        for drawing in drawings:
            sources.append(
                _SourceText(
                    text=cls._normalize_text(drawing.sheet_number, drawing.title),
                    drawing_reference=drawing.sheet_number,
                )
            )

        for specification in specifications:
            sources.append(
                _SourceText(
                    text=cls._normalize_text(
                        specification.section_number,
                        specification.title,
                    ),
                    specification_reference=specification.section_number,
                )
            )

        return sources

    @staticmethod
    def _normalize_text(*parts: str | None) -> str:
        return " ".join(part or "" for part in parts).casefold()

    @staticmethod
    def _first_matching_source(
        matches,
        sources: list[_SourceText],
    ) -> _SourceText | None:
        for source in sources:
            if matches(source.text):
                return source

        return None

    @classmethod
    def _definitions(cls) -> list[dict]:
        return [
            {
                "equipment_id": "detected-speaker",
                "description": "Detected loudspeaker allowance",
                "category": EquipmentCategory.SPEAKER,
                "matches": cls._matches_speaker,
            },
            {
                "equipment_id": "detected-amplifier",
                "description": "Detected amplifier allowance",
                "category": EquipmentCategory.AMPLIFIER,
                "matches": cls._matches_amplifier,
            },
            {
                "equipment_id": "detected-projector",
                "description": "Detected projector allowance",
                "category": EquipmentCategory.PROJECTOR,
                "matches": cls._matches_projector,
            },
            {
                "equipment_id": "detected-display",
                "description": "Detected display allowance",
                "category": EquipmentCategory.DISPLAY,
                "matches": cls._matches_display,
            },
            {
                "equipment_id": "detected-control-processor",
                "description": "Detected control processor allowance",
                "category": EquipmentCategory.CONTROL_PROCESSOR,
                "matches": cls._matches_control_processor,
            },
            {
                "equipment_id": "detected-microphone",
                "description": "Detected microphone allowance",
                "category": EquipmentCategory.MICROPHONE,
                "matches": cls._matches_microphone,
            },
            {
                "equipment_id": "detected-camera",
                "description": "Detected camera allowance",
                "category": EquipmentCategory.CAMERA,
                "matches": cls._matches_camera,
            },
            {
                "equipment_id": "detected-lighting-fixture",
                "description": "Detected lighting fixture allowance",
                "category": EquipmentCategory.LIGHTING_FIXTURE,
                "matches": cls._matches_lighting_fixture,
            },
            {
                "equipment_id": "detected-lighting-console",
                "description": "Detected lighting console allowance",
                "category": EquipmentCategory.LIGHTING_CONSOLE,
                "matches": cls._matches_lighting_console,
            },
            {
                "equipment_id": "detected-intercom",
                "description": "Detected intercom allowance",
                "category": EquipmentCategory.INTERCOM,
                "matches": cls._matches_intercom,
            },
            {
                "equipment_id": "detected-assisted-listening",
                "description": "Detected assisted listening allowance",
                "category": EquipmentCategory.ASSISTED_LISTENING,
                "matches": cls._matches_assisted_listening,
            },
            {
                "equipment_id": "detected-rack",
                "description": "Detected equipment rack allowance",
                "category": EquipmentCategory.RACK,
                "matches": cls._matches_rack,
            },
            {
                "equipment_id": "detected-drapery",
                "description": "Detected drapery allowance",
                "category": EquipmentCategory.DRAPERY,
                "matches": cls._matches_drapery,
            },
        ]

    @staticmethod
    def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _has_word(text: str, word: str) -> bool:
        return re.search(rf"\b{re.escape(word)}\b", text) is not None

    @classmethod
    def _matches_speaker(cls, text: str) -> bool:
        return cls._has_any(text, ("speaker", "loudspeaker"))

    @classmethod
    def _matches_amplifier(cls, text: str) -> bool:
        return cls._has_any(text, ("amplifier", "amplified controller"))

    @classmethod
    def _matches_projector(cls, text: str) -> bool:
        return cls._has_any(text, ("projector", "projection"))

    @classmethod
    def _matches_display(cls, text: str) -> bool:
        return cls._has_any(
            text,
            (
                "display",
                "monitor",
                "digital signage",
            ),
        )

    @classmethod
    def _matches_control_processor(cls, text: str) -> bool:
        return cls._has_any(
            text,
            (
                "control processor",
                "q-sys",
                "qsys",
                "crestron",
                "control system",
            ),
        )

    @classmethod
    def _matches_microphone(cls, text: str) -> bool:
        return cls._has_any(
            text,
            ("microphone", "wireless microphone"),
        ) or cls._has_word(text, "mic")

    @classmethod
    def _matches_camera(cls, text: str) -> bool:
        return cls._has_any(text, ("camera", "ptz"))

    @classmethod
    def _matches_lighting_fixture(cls, text: str) -> bool:
        return "lighting fixture" in text

    @classmethod
    def _matches_lighting_console(cls, text: str) -> bool:
        return "lighting console" in text

    @classmethod
    def _matches_intercom(cls, text: str) -> bool:
        return "intercom" in text

    @classmethod
    def _matches_assisted_listening(cls, text: str) -> bool:
        return cls._has_any(
            text,
            (
                "assisted listening",
                "assistive listening",
            ),
        )

    @classmethod
    def _matches_rack(cls, text: str) -> bool:
        return cls._has_word(text, "rack")

    @classmethod
    def _matches_drapery(cls, text: str) -> bool:
        return cls._has_any(text, ("drapery", "curtain", "traveler"))

    @staticmethod
    def _add_equipment(
        *,
        equipment: list[Equipment],
        emitted: set[str],
        equipment_id: str,
        description: str,
        category: EquipmentCategory,
        source: _SourceText,
        room_id: str | None,
        building_id: str | None,
        system_id: str | None,
    ) -> None:
        if equipment_id in emitted:
            return

        emitted.add(equipment_id)
        equipment.append(
            Equipment(
                equipment_id=equipment_id,
                description=description,
                category=category,
                system_id=system_id,
                room_id=room_id,
                building_id=building_id,
                status="detected",
                drawing_reference=source.drawing_reference,
                specification_reference=source.specification_reference,
                confidence=0.65,
            )
        )

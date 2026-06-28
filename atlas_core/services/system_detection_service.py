"""System detection helpers for Atlas Core plan review."""

from dataclasses import dataclass

from atlas_core.domain import (
    DrawingSheet,
    IntegratedSystem,
    SpecificationSection,
    SystemCategory,
    SystemComplexity,
)


@dataclass(frozen=True)
class _SourceText:
    text: str
    assumption: str


class SystemDetectionService:
    def detect_systems(
        self,
        drawings: list[DrawingSheet] | None = None,
        specifications: list[SpecificationSection] | None = None,
        room_id: str | None = None,
        building_id: str | None = None,
    ) -> list[IntegratedSystem]:
        sources = self._source_texts(drawings or [], specifications or [])
        systems: list[IntegratedSystem] = []
        emitted: set[str] = set()

        for definition in self._definitions():
            source = self._first_matching_source(definition["matches"], sources)
            if source is None:
                continue

            self._add_system(
                systems=systems,
                emitted=emitted,
                system_id=definition["system_id"],
                name=definition["name"],
                category=definition["category"],
                complexity=definition["complexity"],
                source=source,
                room_id=room_id,
                building_id=building_id,
            )

        return systems

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
                    assumption=(
                        f"Detected from drawing {drawing.sheet_number}: "
                        f"{drawing.title}"
                    ),
                )
            )

        for specification in specifications:
            sources.append(
                _SourceText(
                    text=cls._normalize_text(
                        specification.section_number,
                        specification.title,
                    ),
                    assumption=(
                        "Detected from specification "
                        f"{specification.section_number}: {specification.title}"
                    ),
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
                "system_id": "detected-audio",
                "name": "Audio System",
                "category": SystemCategory.AUDIO,
                "complexity": SystemComplexity.MEDIUM,
                "matches": cls._matches_audio,
            },
            {
                "system_id": "detected-projection",
                "name": "Projection System",
                "category": SystemCategory.PROJECTION,
                "complexity": SystemComplexity.MEDIUM,
                "matches": cls._matches_projection,
            },
            {
                "system_id": "detected-display",
                "name": "Display System",
                "category": SystemCategory.DISPLAY,
                "complexity": SystemComplexity.MEDIUM,
                "matches": cls._matches_display,
            },
            {
                "system_id": "detected-control",
                "name": "Control System",
                "category": SystemCategory.CONTROL,
                "complexity": SystemComplexity.MEDIUM,
                "matches": cls._matches_control,
            },
            {
                "system_id": "detected-lighting",
                "name": "Theatrical Lighting System",
                "category": SystemCategory.LIGHTING,
                "complexity": SystemComplexity.HIGH,
                "matches": cls._matches_lighting,
            },
            {
                "system_id": "detected-drapery",
                "name": "Drapery System",
                "category": SystemCategory.DRAPERY,
                "complexity": SystemComplexity.HIGH,
                "matches": cls._matches_drapery,
            },
            {
                "system_id": "detected-intercom",
                "name": "Intercom System",
                "category": SystemCategory.INTERCOM,
                "complexity": SystemComplexity.MEDIUM,
                "matches": cls._matches_intercom,
            },
            {
                "system_id": "detected-assisted-listening",
                "name": "Assisted Listening System",
                "category": SystemCategory.ASSISTED_LISTENING,
                "complexity": SystemComplexity.MEDIUM,
                "matches": cls._matches_assisted_listening,
            },
        ]

    @staticmethod
    def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    @classmethod
    def _matches_audio(cls, text: str) -> bool:
        return cls._has_any(
            text,
            (
                "audio",
                "sound",
                "speaker",
                "loudspeaker",
                "microphone",
            ),
        )

    @classmethod
    def _matches_projection(cls, text: str) -> bool:
        return cls._has_any(
            text,
            (
                "projection",
                "projector",
                "projection screen",
            ),
        )

    @classmethod
    def _matches_display(cls, text: str) -> bool:
        return cls._has_any(
            text,
            (
                "display",
                "digital signage",
                "signage",
                "video wall",
            ),
        )

    @classmethod
    def _matches_control(cls, text: str) -> bool:
        return cls._has_any(
            text,
            (
                "control",
                "control system",
                "av control",
            ),
        )

    @classmethod
    def _matches_lighting(cls, text: str) -> bool:
        return cls._has_any(
            text,
            (
                "theatrical",
                "lighting",
                "lx-",
                "tl-",
            ),
        )

    @classmethod
    def _matches_drapery(cls, text: str) -> bool:
        return cls._has_any(
            text,
            (
                "drapery",
                "curtain",
                "traveler",
            ),
        )

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
                "hearing assistance",
            ),
        )

    @staticmethod
    def _add_system(
        *,
        systems: list[IntegratedSystem],
        emitted: set[str],
        system_id: str,
        name: str,
        category: SystemCategory,
        complexity: SystemComplexity,
        source: _SourceText,
        room_id: str | None,
        building_id: str | None,
    ) -> None:
        if system_id in emitted:
            return

        emitted.add(system_id)
        systems.append(
            IntegratedSystem(
                system_id=system_id,
                name=name,
                category=category,
                complexity=complexity,
                room_id=room_id,
                building_id=building_id,
                assumptions=[source.assumption],
            )
        )

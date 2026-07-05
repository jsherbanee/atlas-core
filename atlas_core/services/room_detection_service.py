"""Room detection helpers for Atlas Core services."""

from __future__ import annotations

import re

from atlas_core.domain.device_schedule import DeviceSchedule
from atlas_core.domain.drawing import DrawingSheet
from atlas_core.domain.equipment import Equipment
from atlas_core.domain.keynote import Keynote
from atlas_core.domain.legend import Legend
from atlas_core.domain.room import Room, RoomType
from atlas_core.domain.specification import SpecificationSection
from atlas_core.services.drawing_metadata_service import DrawingMetadata


class RoomDetectionService:
    _ROOM_PATTERN = re.compile(
        r"\b(?:[A-Za-z0-9][A-Za-z0-9'&/-]*\s+){0,4}"
        r"(?:Control Room|Equipment Room|Conference Room|Green Room|Rack Room|"
        r"Classroom|Studio|Stage|Theater|Theatre|Lobby|Booth|Hall)(?:\s+\d+)?\b",
        re.IGNORECASE,
    )
    _GENERIC_ROOM_PATTERN = re.compile(
        r"\b(?:[A-Za-z0-9][A-Za-z0-9'&/-]*\s+){0,4}Room(?:\s+\d+)?\b",
        re.IGNORECASE,
    )

    def detect_rooms(
        self,
        building_id: str,
        drawing_metadata: list[DrawingMetadata] | None = None,
        drawings: list[DrawingSheet] | None = None,
        specifications: list[SpecificationSection] | None = None,
        device_schedules: list[DeviceSchedule] | None = None,
        keynotes: list[Keynote] | None = None,
        legends: list[Legend] | None = None,
        equipment: list[Equipment] | None = None,
    ) -> list[Room]:
        normalized_building_id = self._normalize_building_id(building_id)
        drawing_metadata = drawing_metadata or []
        drawings = drawings or []
        specifications = specifications or []
        device_schedules = device_schedules or []
        keynotes = keynotes or []
        legends = legends or []
        equipment = equipment or []

        rooms: list[Room] = []
        seen_names: set[str] = set()

        for metadata in drawing_metadata:
            for room_name in getattr(metadata, "room_names", []):
                self._add_room_candidate(
                    rooms,
                    seen_names,
                    normalized_building_id,
                    room_name,
                )

        for drawing in drawings:
            self._extract_from_text(
                rooms,
                seen_names,
                normalized_building_id,
                " ".join([drawing.title, *drawing.notes]),
            )

        for specification in specifications:
            self._extract_from_text(
                rooms,
                seen_names,
                normalized_building_id,
                " ".join([specification.title, *specification.notes]),
            )

        for schedule in device_schedules:
            for item in getattr(schedule, "items", []):
                room_name = getattr(item, "room_name", None)
                if room_name:
                    self._add_room_candidate(
                        rooms,
                        seen_names,
                        normalized_building_id,
                        room_name,
                    )

        for keynote in keynotes:
            self._extract_from_text(
                rooms,
                seen_names,
                normalized_building_id,
                keynote.description,
            )

        for legend in legends:
            for item in getattr(legend, "items", []):
                self._extract_from_text(
                    rooms,
                    seen_names,
                    normalized_building_id,
                    item.description,
                )

        for item in equipment:
            self._extract_from_text(
                rooms,
                seen_names,
                normalized_building_id,
                item.description,
            )
            room_id = getattr(item, "room_id", None)
            if room_id and self._looks_human_readable(room_id):
                self._extract_from_text(
                    rooms,
                    seen_names,
                    normalized_building_id,
                    room_id,
                )

        return sorted(rooms, key=lambda room: room.name.casefold())

    def _extract_from_text(
        self,
        rooms: list[Room],
        seen_names: set[str],
        building_id: str,
        text: str,
    ) -> None:
        if not isinstance(text, str) or not text.strip():
            return

        room_spans: list[tuple[int, int]] = []
        for pattern in (self._ROOM_PATTERN, self._GENERIC_ROOM_PATTERN):
            for match in pattern.finditer(text):
                if pattern is self._GENERIC_ROOM_PATTERN and self._overlaps(
                    match.span(),
                    room_spans,
                ):
                    continue

                room_spans.append(match.span())
                self._add_room_candidate(
                    rooms,
                    seen_names,
                    building_id,
                    match.group(0),
                )

    def _add_room_candidate(
        self,
        rooms: list[Room],
        seen_names: set[str],
        building_id: str,
        room_name: str,
    ) -> None:
        normalized_name = self._normalize_room_name(room_name)
        if not normalized_name:
            return

        key = normalized_name.casefold()
        if key in seen_names:
            return

        seen_names.add(key)
        rooms.append(
            Room(
                room_id=self._room_id(building_id, normalized_name),
                name=normalized_name,
                building_id=building_id,
                room_type=self._room_type(normalized_name),
                confidence=0.75,
            )
        )

    @staticmethod
    def _overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
        start, end = span
        for existing_start, existing_end in spans:
            if start < existing_end and end > existing_start:
                return True

        return False

    @staticmethod
    def _normalize_building_id(value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("building_id cannot be blank")

        return value.strip()

    @staticmethod
    def _looks_human_readable(value: str) -> bool:
        if not isinstance(value, str):
            return False

        cleaned = value.strip()
        if not cleaned:
            return False

        if not re.search(r"[A-Za-z]", cleaned):
            return False

        return bool(re.search(r"\s|[-_]", cleaned))

    @staticmethod
    def _room_id(building_id: str, room_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", room_name.casefold()).strip("-")
        return f"{building_id}-{slug}" if slug else building_id

    @staticmethod
    def _room_type(room_name: str) -> RoomType:
        normalized = room_name.casefold()

        if "conference room" in normalized:
            return RoomType.CONFERENCE

        if "control room" in normalized:
            return RoomType.CONTROL_ROOM

        if "equipment room" in normalized or "rack room" in normalized:
            return RoomType.EQUIPMENT_ROOM

        if "green room" in normalized:
            return RoomType.SUPPORT

        if "classroom" in normalized:
            return RoomType.CLASSROOM

        if "lobby" in normalized:
            return RoomType.LOBBY

        if "studio" in normalized:
            return RoomType.STUDIO

        if any(term in normalized for term in ("theater", "theatre", "hall", "stage")):
            return RoomType.PERFORMANCE

        if "booth" in normalized:
            return RoomType.CONTROL_ROOM

        return RoomType.UNKNOWN

    @staticmethod
    def _normalize_room_name(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            return ""

        cleaned = re.sub(r"[,:;\-/]+$", "", cleaned).strip()
        words = cleaned.split()
        if len(words) > 4:
            words = words[-4:]

        stopwords = {
            "a",
            "an",
            "and",
            "at",
            "by",
            "for",
            "from",
            "in",
            "into",
            "of",
            "on",
            "or",
            "the",
            "to",
            "with",
        }

        while len(words) > 1 and words[0].casefold() in stopwords:
            words = words[1:]

        return " ".join(words).title()

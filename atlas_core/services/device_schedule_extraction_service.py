"""Device schedule extraction service for Atlas Core."""

from __future__ import annotations

import re

from atlas_core.domain import DeviceSchedule, DeviceScheduleItem


class DeviceScheduleExtractionService:
    def extract_from_rows(
        self,
        schedule_id: str,
        rows: list[dict],
        source_sheet_number: str | None = None,
        title: str = "Device Schedule",
    ) -> DeviceSchedule:
        schedule = DeviceSchedule(
            schedule_id=schedule_id,
            source_sheet_number=source_sheet_number,
            title=title,
        )

        for row in rows:
            tag = self._get_text(row, "tag")
            description = self._get_text(row, "description")
            if not tag or not description:
                continue

            drawing_reference = self._get_text(row, "drawing_reference")
            if not drawing_reference and source_sheet_number:
                drawing_reference = source_sheet_number

            item = DeviceScheduleItem(
                item_id=self._make_item_id(schedule.schedule_id, tag),
                tag=tag,
                description=description,
                quantity=self._parse_quantity(row),
                manufacturer=self._get_text(row, "manufacturer") or None,
                model=self._get_text(row, "model") or None,
                room_name=self._get_text(row, "room_name", "room") or None,
                system_name=self._get_text(row, "system_name", "system") or None,
                drawing_reference=drawing_reference,
                specification_reference=self._get_text(row, "specification_reference")
                or None,
            )

            notes = row.get("notes")
            if isinstance(notes, str):
                item.add_note(notes)
            elif isinstance(notes, list):
                for note in notes:
                    if isinstance(note, str):
                        item.add_note(note)

            schedule.add_item(item)

        return schedule

    @staticmethod
    def _get_text(row: dict, *keys: str) -> str:
        for key in keys:
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _parse_quantity(row: dict) -> float:
        value = row.get("qty", row.get("quantity", 1))
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return 1
            try:
                parsed = float(candidate)
                return parsed if parsed > 0 else 1
            except ValueError:
                return 1
        return 1

    @staticmethod
    def _make_item_id(schedule_id: str, tag: str) -> str:
        normalized_tag = re.sub(r"\s+", "-", tag.strip().lower())
        return f"{schedule_id.strip().lower()}-{normalized_tag}"

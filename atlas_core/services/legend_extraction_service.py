"""Extract legend items from drawing sheet notes."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas_core.domain import DrawingSheet, Legend


class LegendExtractionService:
    _SYMBOL_PATTERN = re.compile(r"^\s*(?P<symbol>[▲■○◇△])\s*(?P<description>.+?)\s*$")
    _TEXT_CODE_PATTERN = re.compile(
        r"^\s*(?P<symbol>[A-Za-z][A-Za-z0-9]*)\s*(?:-|:)\s*(?P<description>.+?)\s*$"
    )

    def extract_from_sheet(self, sheet: DrawingSheet) -> Legend | None:
        from atlas_core.domain import Legend, LegendItem

        legend_id = self._legend_id(sheet.sheet_number)
        legend = Legend(
            legend_id=legend_id,
            source_sheet_number=sheet.sheet_number,
            confidence=sheet.confidence,
        )
        seen_ids: set[str] = set()

        for note in sheet.notes:
            parsed = self._parse_legend_note(note)
            if parsed is None:
                continue

            symbol, description = parsed
            item_id = self._legend_item_id(sheet.sheet_number, symbol)
            if item_id in seen_ids:
                continue

            seen_ids.add(item_id)
            equipment_category, system_category = self._infer_categories(description)
            legend.add_item(
                LegendItem(
                    legend_item_id=item_id,
                    symbol=symbol,
                    description=description,
                    equipment_category=equipment_category,
                    system_category=system_category,
                    source_sheet_number=sheet.sheet_number,
                    confidence=sheet.confidence,
                )
            )

        return legend if legend.items else None

    @classmethod
    def _parse_legend_note(cls, note: str) -> tuple[str, str] | None:
        for pattern in (cls._SYMBOL_PATTERN, cls._TEXT_CODE_PATTERN):
            match = pattern.match(note)
            if match:
                return match.group("symbol").strip(), match.group("description").strip()
        return None

    @staticmethod
    def _legend_id(sheet_number: str) -> str:
        return LegendExtractionService._normalize_identifier(f"{sheet_number}-legend")

    @staticmethod
    def _legend_item_id(sheet_number: str, symbol: str) -> str:
        return LegendExtractionService._normalize_identifier(
            f"{sheet_number}-legend-{symbol}"
        )

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        return re.sub(r"\s+", "-", value.strip().lower())

    @staticmethod
    def _infer_categories(description: str) -> tuple[str | None, str | None]:
        lowered = description.lower()

        if "assisted listening" in lowered:
            return "assisted_listening", "assisted_listening"
        if "speaker" in lowered or "loudspeaker" in lowered:
            return "speaker", "audio"
        if "projector" in lowered:
            return "projector", "projection"
        if any(token in lowered for token in ("display", "monitor", "signage")):
            return "display", "display"
        if "microphone" in lowered or "mic" in lowered:
            return "microphone", "audio"
        if "camera" in lowered or "ptz" in lowered:
            return "camera", "video"
        if "rack" in lowered:
            return "rack", "infrastructure"
        if any(token in lowered for token in ("drapery", "curtain", "traveler")):
            return "drapery", "drapery"
        if "intercom" in lowered:
            return "intercom", "intercom"

        return None, None

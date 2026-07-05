"""Extract keynotes from drawing sheet notes."""

from __future__ import annotations

import re

from atlas_core.domain.drawing import DrawingSheet
from atlas_core.domain.keynote import Keynote


class KeynoteExtractionService:
    _KEYNOTE_PATTERN = re.compile(
        r"^\s*(?:NOTE\s+)?(?P<number>K?\d+)\s*(?:\.|-|:)\s*(?P<description>.+?)\s*$",
        flags=re.IGNORECASE,
    )

    def extract_from_sheet(self, sheet: DrawingSheet) -> list[Keynote]:
        keynotes: list[Keynote] = []
        seen_ids: set[str] = set()

        for note in sheet.notes:
            match = self._KEYNOTE_PATTERN.match(note)
            if not match:
                continue

            number = match.group("number").strip()
            description = match.group("description").strip()
            keynote_id = self._keynote_id(sheet.sheet_number, number)

            if keynote_id in seen_ids:
                continue

            seen_ids.add(keynote_id)
            keynotes.append(
                Keynote(
                    keynote_id=keynote_id,
                    number=number,
                    description=description,
                    source_sheet_number=sheet.sheet_number,
                    equipment_category=self._infer_equipment_category(description),
                    system_category=self._infer_system_category(description),
                    confidence=sheet.confidence,
                )
            )

        return keynotes

    @staticmethod
    def _keynote_id(sheet_number: str, number: str) -> str:
        raw = f"{sheet_number}-keynote-{number}".strip().lower()
        return re.sub(r"\s+", "-", raw)

    @staticmethod
    def _infer_equipment_category(description: str) -> str | None:
        text = description.lower()

        if "assisted listening" in text:
            return "assisted_listening"
        if "loudspeaker" in text or "speaker" in text:
            return "speaker"
        if "projector" in text:
            return "projector"
        if "display" in text or "monitor" in text or "signage" in text:
            return "display"
        if "microphone" in text or re.search(r"\bmic\b", text):
            return "microphone"
        if "camera" in text or "ptz" in text:
            return "camera"
        if "rack" in text:
            return "rack"
        if "drapery" in text or "curtain" in text or "traveler" in text:
            return "drapery"
        if "intercom" in text:
            return "intercom"

        return None

    @staticmethod
    def _infer_system_category(description: str) -> str | None:
        text = description.lower()

        if "assisted listening" in text:
            return "assisted_listening"
        if "projector" in text:
            return "projection"
        if "display" in text or "signage" in text:
            return "display"
        if "camera" in text or "ptz" in text:
            return "video"
        if "drapery" in text or "curtain" in text or "traveler" in text:
            return "drapery"
        if "intercom" in text:
            return "intercom"
        if (
            "loudspeaker" in text
            or "speaker" in text
            or "microphone" in text
            or re.search(r"\bmic\b", text)
        ):
            return "audio"

        return None

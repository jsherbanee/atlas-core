"""Extract detail callouts from drawing sheet title and notes."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas_core.domain import DetailCallout, DrawingSheet


class DetailCalloutExtractionService:
    _CALLOUT_PATTERN = re.compile(
        r"\b(?:see|ref:?|detail|mounting\s+detail|rack\s+detail)?\s*"
        r"(?P<detail_number>\d+)\s*/\s*"
        r"(?P<target_sheet>[A-Za-z]{1,5}\s*-?\s*\d{2,4}(?:\.\d{1,2})?)\b",
        flags=re.IGNORECASE,
    )

    def extract_from_sheet(self, sheet: DrawingSheet) -> list[DetailCallout]:
        from atlas_core.domain import DetailCallout

        callouts: list[DetailCallout] = []
        seen_ids: set[str] = set()

        for line in [sheet.title, *sheet.notes]:
            for match in self._CALLOUT_PATTERN.finditer(line):
                detail_number = match.group("detail_number").strip()
                target_sheet_number = self._normalize_target_sheet_number(
                    match.group("target_sheet")
                )
                callout_id = self._callout_id(
                    source_sheet_number=sheet.sheet_number,
                    detail_number=detail_number,
                    target_sheet_number=target_sheet_number,
                )

                if callout_id in seen_ids:
                    continue

                seen_ids.add(callout_id)
                description = line.strip() or match.group(0).strip()
                equipment_category, system_category = self._infer_categories(
                    description
                )

                callouts.append(
                    DetailCallout(
                        callout_id=callout_id,
                        detail_number=detail_number,
                        source_sheet_number=sheet.sheet_number,
                        target_sheet_number=target_sheet_number,
                        description=description,
                        equipment_category=equipment_category,
                        system_category=system_category,
                        confidence=sheet.confidence,
                    )
                )

        return callouts

    @staticmethod
    def _normalize_target_sheet_number(value: str) -> str:
        normalized = re.sub(r"\s+", "", value.strip().upper())
        normalized = re.sub(r"^([A-Z]+)(\d)", r"\1-\2", normalized)
        normalized = re.sub(r"-+", "-", normalized)
        return normalized

    @staticmethod
    def _callout_id(
        source_sheet_number: str,
        detail_number: str,
        target_sheet_number: str,
    ) -> str:
        raw = f"{source_sheet_number}-detail-{detail_number}-{target_sheet_number}".strip().lower()
        raw = re.sub(r"[\s/]+", "-", raw)
        raw = re.sub(r"[^a-z0-9.-]+", "-", raw)
        return re.sub(r"-+", "-", raw).strip("-")

    @staticmethod
    def _infer_categories(description: str) -> tuple[str | None, str | None]:
        text = description.casefold()
        equipment_category: str | None = None
        system_category: str | None = None

        if "projector" in text or "projection" in text:
            equipment_category = "projector"
            system_category = "projection"
        elif any(token in text for token in ("display", "monitor", "signage")):
            equipment_category = "display"
            system_category = "display"
        elif "speaker" in text or "loudspeaker" in text:
            equipment_category = "speaker"
            system_category = "audio"
        elif "rack" in text:
            equipment_category = "rack"
            system_category = "infrastructure"
        elif "mount" in text or "mounting" in text:
            equipment_category = "mount"
            system_category = "infrastructure"
        elif any(token in text for token in ("drapery", "curtain", "traveler")):
            equipment_category = "drapery"
            system_category = "drapery"

        if system_category is None and any(
            token in text
            for token in ("conduit", "backing", "power", "structure", "structural")
        ):
            system_category = "infrastructure"

        return equipment_category, system_category

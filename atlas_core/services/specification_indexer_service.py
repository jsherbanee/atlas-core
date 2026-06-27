"""Specification section indexing helpers for Atlas Core services."""

from typing import Any

from atlas_core.domain import SpecificationDiscipline, SpecificationSection


class SpecificationIndexerService:
    def index_sections(self, raw_sections: list[dict]) -> list[SpecificationSection]:
        sections: list[SpecificationSection] = []

        for raw_section in raw_sections:
            section_number = self._text(raw_section.get("section_number"))
            title = self._text(raw_section.get("title"))
            if section_number is None or title is None:
                continue

            discipline = raw_section.get("discipline")
            if discipline is None:
                discipline = self.infer_discipline(section_number, title)

            sections.append(
                SpecificationSection(
                    section_id=self._section_id(section_number),
                    section_number=section_number,
                    title=title,
                    discipline=discipline,
                    source_file=raw_section.get("source_file"),
                    page_start=raw_section.get("page_start"),
                    page_end=raw_section.get("page_end"),
                    manufacturers=raw_section.get("manufacturers", []),
                )
            )

        return sections

    def infer_discipline(
        self,
        section_number: str,
        title: str = "",
    ) -> SpecificationDiscipline:
        normalized_section_number = " ".join(section_number.strip().split())
        normalized_title = title.strip().casefold()

        if normalized_section_number.startswith("27 41") or any(
            phrase in normalized_title
            for phrase in ("audiovisual", "audio visual", "audio-video")
        ):
            return SpecificationDiscipline.AUDIOVISUAL

        if normalized_section_number.startswith("27") or "communications" in normalized_title:
            return SpecificationDiscipline.COMMUNICATIONS

        if normalized_section_number.startswith("11 61") or "theatrical" in normalized_title:
            return SpecificationDiscipline.THEATRICAL

        if any(
            phrase in normalized_title
            for phrase in ("drapery", "curtain", "traveler")
        ):
            return SpecificationDiscipline.DRAPERY

        if "rigging" in normalized_title:
            return SpecificationDiscipline.RIGGING

        if "acoustics" in normalized_title:
            return SpecificationDiscipline.ACOUSTICS

        if normalized_section_number.startswith("26") or "electrical" in normalized_title:
            return SpecificationDiscipline.ELECTRICAL

        if "lighting" in normalized_title:
            return SpecificationDiscipline.LIGHTING

        if normalized_section_number.startswith("28") or "security" in normalized_title:
            return SpecificationDiscipline.SECURITY

        return SpecificationDiscipline.UNKNOWN

    @staticmethod
    def _section_id(section_number: str) -> str:
        return "-".join(section_number.strip().casefold().split())

    @staticmethod
    def _text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        normalized = value.strip()
        return normalized or None

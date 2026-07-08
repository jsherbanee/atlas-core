"""Deterministic drawing analyzer for Atlas Drawing Intelligence."""

from __future__ import annotations

import re

from atlas_core.domain.drawing import DrawingDiscipline as DomainDrawingDiscipline
from atlas_core.domain.drawing import DrawingSheet

from atlas_core.services.drawing_intelligence.models import (
    DrawingDiscipline,
    DrawingMetadata,
    DrawingReference,
    DrawingReferenceType,
    DrawingSheetCategory,
    aggregate_confidence,
)

_SHEET_REF_PATTERN = re.compile(r"\b[A-Z]{1,4}[\-\s]?\d{2,4}[A-Z]?\b")
_SCALE_PATTERN = re.compile(r"\bSCALE\s*[:=]\s*([^;\n]+)", flags=re.IGNORECASE)
_DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_KEYNOTE_PATTERN = re.compile(r"\b(?:KEYNOTE\s*\d+|K\d{1,3})\b", flags=re.IGNORECASE)
_DETAIL_PATTERN = re.compile(r"\b(?:DETAIL|DET\.)\s*[:#-]?\s*([A-Z]?\d+(?:\.\d+)?)")
_VIEW_PATTERN = re.compile(r"\b(?:VIEW|VIEWS)\s*[:#-]?\s*([A-Z]?\d+(?:\.\d+)?)")
_SECTION_PATTERN = re.compile(r"\bSECTION\s*[:#-]?\s*([A-Z]?\d+(?:\.\d+)?)")
_CALLOUT_PATTERN = re.compile(r"\bCALLOUT\s*[:#-]?\s*([A-Z]?\d+(?:\.\d+)?)")


class DrawingAnalyzer:
    """Analyze drawing sheets into deterministic metadata and references."""

    _discipline_keywords: dict[DrawingDiscipline, tuple[str, ...]] = {
        DrawingDiscipline.ARCHITECTURAL: (
            "architectural",
            "ceiling",
            "elevation",
            "section",
        ),
        DrawingDiscipline.AV: ("av", "audio", "video", "signal flow", "rack"),
        DrawingDiscipline.ELECTRICAL: ("electrical", "single line", "power"),
        DrawingDiscipline.MECHANICAL: ("mechanical", "hvac"),
        DrawingDiscipline.STRUCTURAL: ("structural", "steel", "foundation"),
        DrawingDiscipline.TECHNOLOGY: (
            "technology",
            "it",
            "network",
            "diagram",
        ),
        DrawingDiscipline.LOW_VOLTAGE: ("low voltage", "lv"),
        DrawingDiscipline.FIRE_ALARM: ("fire alarm",),
        DrawingDiscipline.TELECOM: ("telecom", "telecommunications"),
        DrawingDiscipline.CIVIL: ("civil", "grading", "utility"),
        DrawingDiscipline.LANDSCAPE: ("landscape", "planting", "irrigation"),
    }

    _sheet_category_keywords: dict[DrawingSheetCategory, tuple[str, ...]] = {
        DrawingSheetCategory.COVER_SHEET: ("cover", "title sheet"),
        DrawingSheetCategory.GENERAL_NOTES: ("general notes",),
        DrawingSheetCategory.LEGEND: ("legend",),
        DrawingSheetCategory.SYMBOLS: ("symbols",),
        DrawingSheetCategory.SITE_PLAN: ("site plan",),
        DrawingSheetCategory.FLOOR_PLAN: ("floor plan",),
        DrawingSheetCategory.REFLECTED_CEILING_PLAN: ("reflected ceiling",),
        DrawingSheetCategory.EQUIPMENT_PLAN: ("equipment plan",),
        DrawingSheetCategory.RACK_ELEVATION: ("rack elevation",),
        DrawingSheetCategory.SINGLE_LINE_DIAGRAM: ("single line",),
        DrawingSheetCategory.BLOCK_DIAGRAM: ("block diagram",),
        DrawingSheetCategory.SIGNAL_FLOW: ("signal flow",),
        DrawingSheetCategory.TYPICAL_DETAIL: ("typical detail",),
        DrawingSheetCategory.MOUNTING_DETAIL: ("mounting detail",),
        DrawingSheetCategory.SECTION: ("section",),
        DrawingSheetCategory.ELEVATION: ("elevation",),
        DrawingSheetCategory.SCHEDULE: ("schedule",),
        DrawingSheetCategory.INDEX: ("index",),
    }

    _domain_to_intelligence = {
        DomainDrawingDiscipline.ARCHITECTURAL: DrawingDiscipline.ARCHITECTURAL,
        DomainDrawingDiscipline.ELECTRICAL: DrawingDiscipline.ELECTRICAL,
        DomainDrawingDiscipline.AUDIOVISUAL: DrawingDiscipline.AV,
        DomainDrawingDiscipline.THEATRICAL: DrawingDiscipline.TECHNOLOGY,
        DomainDrawingDiscipline.LIGHTING: DrawingDiscipline.ELECTRICAL,
        DomainDrawingDiscipline.STRUCTURAL: DrawingDiscipline.STRUCTURAL,
        DomainDrawingDiscipline.MECHANICAL: DrawingDiscipline.MECHANICAL,
        DomainDrawingDiscipline.TELECOM: DrawingDiscipline.TELECOM,
        DomainDrawingDiscipline.FIRE_ALARM: DrawingDiscipline.FIRE_ALARM,
        DomainDrawingDiscipline.UNKNOWN: DrawingDiscipline.UNKNOWN,
    }

    def analyze_sheet(
        self,
        sheet: DrawingSheet,
        known_sheet_numbers: set[str],
    ) -> DrawingMetadata:
        note_text = "\n".join(item for item in list(sheet.notes or []) if item)
        sheet_text = f"{sheet.sheet_number} {sheet.title} {note_text}".strip()

        discipline = self._detect_discipline(sheet)
        sheet_category = self._classify_sheet(sheet_text)
        sheet_sequence = self._extract_sheet_sequence(sheet.sheet_number)
        scale = self._extract_scale(sheet_text)
        issue_date = sheet.issue_date or self._extract_issue_date(sheet_text)

        references: list[DrawingReference] = []
        references.extend(
            self._extract_sheet_references(
                source_sheet=sheet.sheet_number,
                source_text=sheet_text,
                known_sheet_numbers=known_sheet_numbers,
            )
        )
        references.extend(
            self._extract_structured_references(
                source_sheet=sheet.sheet_number,
                source_text=sheet_text,
            )
        )

        detail_references = [
            item.target_id
            for item in references
            if item.reference_type == DrawingReferenceType.DETAIL
        ]
        view_references = [
            item.target_id
            for item in references
            if item.reference_type == DrawingReferenceType.VIEW
        ]

        general_notes = self._extract_general_notes(sheet.notes)
        keynotes = self._extract_keynotes(sheet_text)

        confidence = aggregate_confidence(
            [
                sheet.confidence,
                0.9 if discipline != DrawingDiscipline.UNKNOWN else 0.6,
                0.88 if sheet_category != DrawingSheetCategory.OTHER else 0.62,
                0.86 if sheet_sequence is not None else 0.7,
                0.84 if references else 0.74,
            ],
            default=sheet.confidence,
        )

        return DrawingMetadata(
            sheet_number=sheet.sheet_number,
            title=sheet.title,
            revision=sheet.revision,
            issue_date=issue_date,
            scale=scale,
            discipline=discipline,
            sheet_category=sheet_category,
            sheet_sequence=sheet_sequence,
            references=self._dedupe_references(references),
            general_notes=general_notes,
            detail_references=self._dedupe_text(detail_references),
            view_references=self._dedupe_text(view_references),
            keynotes=self._dedupe_text(keynotes),
            confidence=confidence,
            source_trace={
                "sheet_id": sheet.sheet_id,
                "sheet_number": sheet.sheet_number,
                "title": sheet.title,
                "source_file": sheet.source_file,
                "page_number": sheet.page_number,
                "source_notes": list(sheet.notes),
            },
        )

    def _detect_discipline(self, sheet: DrawingSheet) -> DrawingDiscipline:
        mapped = self._domain_to_intelligence.get(sheet.discipline)
        if mapped is not None and mapped != DrawingDiscipline.UNKNOWN:
            return mapped

        text = f"{sheet.sheet_number} {sheet.title}".lower()
        for discipline, keywords in self._discipline_keywords.items():
            if any(keyword in text for keyword in keywords):
                return discipline

        sheet_number = sheet.sheet_number.strip().upper()
        if sheet_number.startswith("A"):
            return DrawingDiscipline.ARCHITECTURAL
        if sheet_number.startswith("AV"):
            return DrawingDiscipline.AV
        if sheet_number.startswith("E"):
            return DrawingDiscipline.ELECTRICAL
        if sheet_number.startswith("M"):
            return DrawingDiscipline.MECHANICAL
        if sheet_number.startswith("S"):
            return DrawingDiscipline.STRUCTURAL
        if sheet_number.startswith("C"):
            return DrawingDiscipline.CIVIL
        if sheet_number.startswith("L"):
            return DrawingDiscipline.LANDSCAPE

        return DrawingDiscipline.UNKNOWN

    def _classify_sheet(self, sheet_text: str) -> DrawingSheetCategory:
        text = sheet_text.lower()
        for category, keywords in self._sheet_category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category
        return DrawingSheetCategory.OTHER

    @staticmethod
    def _extract_sheet_sequence(sheet_number: str) -> int | None:
        match = re.search(r"(\d{2,4})", sheet_number)
        if not match:
            return None
        return int(match.group(1))

    @staticmethod
    def _extract_scale(sheet_text: str) -> str | None:
        match = _SCALE_PATTERN.search(sheet_text)
        if not match:
            return None
        candidate = match.group(1).strip().rstrip(".")
        return candidate or None

    @staticmethod
    def _extract_issue_date(sheet_text: str) -> str | None:
        match = _DATE_PATTERN.search(sheet_text)
        if not match:
            return None
        return match.group(0)

    def _extract_sheet_references(
        self,
        source_sheet: str,
        source_text: str,
        known_sheet_numbers: set[str],
    ) -> list[DrawingReference]:
        values = _SHEET_REF_PATTERN.findall(source_text.upper())
        references: list[DrawingReference] = []
        for value in values:
            normalized = self._normalize_sheet_reference(value)
            if not normalized or normalized == source_sheet.upper():
                continue

            # Keep deterministic references only when they point to known sheets.
            if known_sheet_numbers and normalized not in known_sheet_numbers:
                continue

            references.append(
                DrawingReference(
                    source_sheet=source_sheet,
                    target_id=normalized,
                    reference_type=DrawingReferenceType.SHEET,
                    confidence=0.85,
                    source_text=value,
                )
            )
        return references

    def _extract_structured_references(
        self,
        source_sheet: str,
        source_text: str,
    ) -> list[DrawingReference]:
        references: list[DrawingReference] = []
        references.extend(
            self._pattern_references(
                source_sheet,
                source_text,
                _DETAIL_PATTERN,
                DrawingReferenceType.DETAIL,
                0.82,
            )
        )
        references.extend(
            self._pattern_references(
                source_sheet,
                source_text,
                _VIEW_PATTERN,
                DrawingReferenceType.VIEW,
                0.82,
            )
        )
        references.extend(
            self._pattern_references(
                source_sheet,
                source_text,
                _SECTION_PATTERN,
                DrawingReferenceType.SECTION,
                0.8,
            )
        )
        references.extend(
            self._pattern_references(
                source_sheet,
                source_text,
                _CALLOUT_PATTERN,
                DrawingReferenceType.CALLOUT,
                0.78,
            )
        )
        if "schedule" in source_text.lower():
            references.append(
                DrawingReference(
                    source_sheet=source_sheet,
                    target_id="SCHEDULE",
                    reference_type=DrawingReferenceType.SCHEDULE,
                    confidence=0.78,
                    source_text="schedule",
                )
            )
        if "index" in source_text.lower():
            references.append(
                DrawingReference(
                    source_sheet=source_sheet,
                    target_id="INDEX",
                    reference_type=DrawingReferenceType.INDEX,
                    confidence=0.78,
                    source_text="index",
                )
            )
        return references

    def _pattern_references(
        self,
        source_sheet: str,
        source_text: str,
        pattern: re.Pattern[str],
        reference_type: DrawingReferenceType,
        confidence: float,
    ) -> list[DrawingReference]:
        results: list[DrawingReference] = []
        for match in pattern.finditer(source_text):
            target = (match.group(1) or "").strip()
            if not target:
                continue
            results.append(
                DrawingReference(
                    source_sheet=source_sheet,
                    target_id=target,
                    reference_type=reference_type,
                    confidence=confidence,
                    source_text=match.group(0),
                )
            )
        return results

    @staticmethod
    def _extract_general_notes(notes: list[str]) -> list[str]:
        values: list[str] = []
        for note in list(notes or []):
            text = str(note).strip()
            lowered = text.lower()
            if lowered.startswith("note") or "general note" in lowered:
                values.append(text)
        return values

    @staticmethod
    def _extract_keynotes(sheet_text: str) -> list[str]:
        return [match.group(0) for match in _KEYNOTE_PATTERN.finditer(sheet_text)]

    @staticmethod
    def _normalize_sheet_reference(value: str) -> str:
        token = re.sub(r"\s+", "", value.upper())
        token = token.replace("--", "-")
        if "-" in token:
            return token

        match = re.match(r"([A-Z]{1,4})(\d{2,4}[A-Z]?)", token)
        if not match:
            return token
        return f"{match.group(1)}-{match.group(2)}"

    @staticmethod
    def _dedupe_references(values: list[DrawingReference]) -> list[DrawingReference]:
        seen: set[tuple[str, str, str]] = set()
        result: list[DrawingReference] = []
        for item in values:
            key = (
                item.source_sheet,
                item.target_id,
                item.reference_type.value,
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    @staticmethod
    def _dedupe_text(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            cleaned = str(value).strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            result.append(cleaned)
        return result

"""Deterministic analyzer for Atlas specification intelligence."""

from __future__ import annotations

import re
from typing import Any

from atlas_core.domain.specification import SpecificationSection as DomainSpecSection

from atlas_core.services.specification_intelligence.models import (
    SpecificationArticle,
    SpecificationDiscipline,
    SpecificationMetadata,
    SpecificationPart,
    SpecificationReference,
    SpecificationReferenceType,
    SpecificationSection,
    aggregate_confidence,
)

_DRAWING_REF_PATTERN = re.compile(r"\b[A-Z]{1,4}[\-\s]?\d{2,4}[A-Z]?\b")
_SECTION_REF_PATTERN = re.compile(r"\b\d{2}\s+\d{2}\s+\d{2}\b")
_DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_REVISION_PATTERN = re.compile(
    r"\b(?:REV(?:ISION)?\s*[:#-]?\s*([A-Z0-9.\-]+))\b", flags=re.IGNORECASE
)
_ADDENDUM_PATTERN = re.compile(
    r"\bADD(?:ENDUM)?\s*[:#-]?\s*([A-Z0-9.\-]+)\b", flags=re.IGNORECASE
)
_PART_PATTERN = re.compile(
    r"\bPART\s*([123])\s*[-:–]?\s*([A-Z][A-Z0-9\s/,&()\-]+)",
    flags=re.IGNORECASE,
)
_ARTICLE_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+(.+?)\s*$")
_STANDARD_PATTERN = re.compile(
    r"\b(?:ANSI|ASTM|IEEE|NFPA|UL|NEMA|TIA|EIA|SMPTE|ISO|NEC)\s*[A-Z0-9.\-]*\b"
)
_PRODUCT_PATTERN = re.compile(r"\b[A-Z]{2,}[\- ][A-Z0-9]{2,}\b")
_SCHEDULE_PATTERN = re.compile(
    r"\b([A-Z]{0,3}\s*schedule(?:\s*[A-Z0-9\-]+)?)\b", flags=re.IGNORECASE
)
_EQUIPMENT_PATTERN = re.compile(r"\b(?:EQ|DEVICE|DEV)\s*[-#:]?\s*([A-Z0-9.\-]+)\b")


class SpecificationAnalyzer:
    """Analyze spec sections into deterministic structured section intelligence."""

    _division_names = {
        "01": "Division 01 General Requirements",
        "26": "Division 26 Electrical",
        "27": "Division 27 Communications",
        "28": "Division 28 Electronic Safety and Security",
    }

    _system_terms = {
        "audio": "audio",
        "video": "video",
        "control": "control",
        "network": "network",
        "telecom": "telecom",
        "security": "security",
        "theatrical": "theatrical",
        "lighting": "lighting",
        "rigging": "rigging",
        "acoustics": "acoustics",
    }

    _requirement_map: dict[str, tuple[str, ...]] = {
        "warranty_requirements": ("warranty",),
        "submittal_requirements": ("submittal", "submit"),
        "training_requirements": ("training",),
        "testing_requirements": ("testing", "test and inspect"),
        "commissioning_requirements": ("commissioning", "commission"),
        "closeout_requirements": ("closeout", "close-out"),
        "mockup_requirements": ("mockup", "mock-up"),
        "quality_assurance_requirements": ("quality assurance", "qa"),
        "manufacturer_qualifications": (
            "manufacturer qualifications",
            "qualified manufacturer",
        ),
        "installer_qualifications": ("installer qualifications", "qualified installer"),
        "coordination_requirements": ("coordination", "coordinate"),
        "power_responsibility": ("power by", "power responsibility"),
        "network_responsibility": ("network by", "network responsibility"),
        "conduit_responsibility": ("conduit by", "conduit responsibility"),
        "owner_furnished_responsibility": (
            "owner furnished",
            "ofci",
            "owner-provided",
        ),
        "contractor_furnished_responsibility": (
            "contractor furnished",
            "by contractor",
            "integrator furnished",
        ),
    }

    def analyze_section(
        self,
        section: DomainSpecSection,
        known_sections: set[str],
    ) -> SpecificationSection:
        lines = self._section_lines(section)
        joined_text = "\n".join(lines)

        division = self._division_label(section.section_number)
        discipline = self._classify_discipline(section.section_number, section.title)
        revision = self._extract_revision(lines)
        issue_date = self._extract_issue_date(lines)

        parts = self._extract_parts(lines)
        articles = self._extract_articles(lines)

        refs = self._extract_references(
            section=section,
            lines=lines,
            text=joined_text,
            known_sections=known_sections,
        )
        requirements = self._extract_requirement_candidates(lines)

        status = "needs_review" if requirements else "indexed"

        metadata = SpecificationMetadata(
            section_number=section.section_number,
            title=section.title,
            division=division,
            discipline=discipline,
            revision=revision,
            issue_date=issue_date,
            addendum_references=self._reference_targets(
                refs, SpecificationReferenceType.ADDENDUM
            ),
            referenced_standards=self._reference_targets(
                refs, SpecificationReferenceType.STANDARD
            ),
            referenced_manufacturers=self._reference_targets(
                refs, SpecificationReferenceType.MANUFACTURER
            ),
            referenced_products=self._reference_targets(
                refs, SpecificationReferenceType.PRODUCT
            ),
            referenced_systems=self._reference_targets(
                refs, SpecificationReferenceType.SYSTEM
            ),
            referenced_drawings=self._reference_targets(
                refs, SpecificationReferenceType.DRAWING
            ),
            related_schedules=self._reference_targets(
                refs, SpecificationReferenceType.SCHEDULE
            ),
            confidence=aggregate_confidence(
                [
                    section.confidence,
                    0.9 if discipline != SpecificationDiscipline.OTHER else 0.72,
                    0.88 if division != "Division Unknown" else 0.7,
                    0.84 if refs else 0.72,
                    0.86 if parts else 0.74,
                    0.86 if articles else 0.74,
                    0.87 if requirements else 0.76,
                ],
                default=section.confidence,
            ),
            source_trace={
                "section_id": section.section_id,
                "section_number": section.section_number,
                "title": section.title,
                "source_file": section.source_file,
                "page_start": section.page_start,
                "page_end": section.page_end,
                "source_notes": list(section.notes),
                "source_manufacturers": list(section.manufacturers),
            },
        )

        return SpecificationSection(
            section_number=section.section_number,
            title=section.title,
            division=division,
            discipline=discipline,
            status=status,
            revision=revision,
            issue_date=issue_date,
            metadata=metadata,
            parts=parts,
            articles=articles,
            references=refs,
            requirement_candidates=requirements,
            confidence=metadata.confidence,
        )

    def _section_lines(self, section: DomainSpecSection) -> list[str]:
        lines = [
            section.section_number.strip(),
            section.title.strip(),
        ]
        lines.extend(
            [
                str(item).strip()
                for item in list(section.notes or [])
                if str(item).strip()
            ]
        )
        lines.extend(
            [item.strip() for item in list(section.manufacturers or []) if item]
        )
        return lines

    def _division_label(self, section_number: str) -> str:
        div = self._division_code(section_number)
        if div is None:
            return "Division Unknown"
        return self._division_names.get(div, f"Division {div}")

    def _classify_discipline(
        self,
        section_number: str,
        title: str,
    ) -> SpecificationDiscipline:
        lower_title = title.lower()
        division = self._division_code(section_number)

        if division == "01":
            return SpecificationDiscipline.DIVISION_01_GENERAL_REQUIREMENTS
        if division == "26":
            return SpecificationDiscipline.DIVISION_26_ELECTRICAL
        if division == "27":
            if any(term in lower_title for term in ("audio", "video", "av")):
                return SpecificationDiscipline.AV_SYSTEMS
            return SpecificationDiscipline.DIVISION_27_COMMUNICATIONS
        if division == "28":
            return SpecificationDiscipline.DIVISION_28_ELECTRONIC_SAFETY_SECURITY

        if "audio" in lower_title and "video" in lower_title:
            return SpecificationDiscipline.AV_SYSTEMS
        if "audio" in lower_title:
            return SpecificationDiscipline.AUDIO_SYSTEMS
        if "video" in lower_title or "display" in lower_title:
            return SpecificationDiscipline.VIDEO_SYSTEMS
        if "control" in lower_title:
            return SpecificationDiscipline.CONTROL_SYSTEMS
        if "network" in lower_title or "communications" in lower_title:
            return SpecificationDiscipline.NETWORK_SYSTEMS
        if "telecom" in lower_title:
            return SpecificationDiscipline.TELECOM
        if "security" in lower_title:
            return SpecificationDiscipline.SECURITY
        if "theatr" in lower_title:
            return SpecificationDiscipline.THEATRICAL_SYSTEMS
        if "lighting" in lower_title:
            return SpecificationDiscipline.LIGHTING_SYSTEMS
        if "rigging" in lower_title:
            return SpecificationDiscipline.RIGGING
        if "acoustic" in lower_title:
            return SpecificationDiscipline.ACOUSTICS

        return SpecificationDiscipline.OTHER

    def _extract_parts(self, lines: list[str]) -> list[SpecificationPart]:
        parts: list[SpecificationPart] = []
        seen: set[str] = set()
        for line in lines:
            match = _PART_PATTERN.search(line)
            if match is None:
                continue
            part_number = f"Part {match.group(1)}"
            title = " ".join(match.group(2).split()).title()
            key = f"{part_number}:{title}".lower()
            if key in seen:
                continue
            seen.add(key)
            parts.append(SpecificationPart(part_number=part_number, title=title))
        return parts

    def _extract_articles(self, lines: list[str]) -> list[SpecificationArticle]:
        articles: list[SpecificationArticle] = []
        seen: set[str] = set()
        for line in lines:
            match = _ARTICLE_PATTERN.match(line)
            if match is None:
                continue
            identifier = match.group(1)
            heading = " ".join(match.group(2).split())
            key = f"{identifier}:{heading}".lower()
            if key in seen:
                continue
            seen.add(key)
            articles.append(
                SpecificationArticle(
                    identifier=identifier,
                    heading=heading,
                    source_text=line,
                )
            )
        return articles

    def _extract_references(
        self,
        section: DomainSpecSection,
        lines: list[str],
        text: str,
        known_sections: set[str],
    ) -> list[SpecificationReference]:
        refs: list[SpecificationReference] = []
        refs.extend(
            self._section_references(section.section_number, text, known_sections)
        )
        refs.extend(self._drawing_references(section.section_number, text))
        refs.extend(self._standard_references(section.section_number, text))
        refs.extend(self._schedule_references(section.section_number, text))
        refs.extend(self._addendum_references(section.section_number, text))
        refs.extend(self._product_references(section.section_number, text))
        refs.extend(self._equipment_references(section.section_number, text))
        refs.extend(self._system_references(section.section_number, lines))
        refs.extend(
            self._manufacturer_references(section.section_number, section.manufacturers)
        )
        return self._dedupe_references(refs)

    def _section_references(
        self,
        source: str,
        text: str,
        known_sections: set[str],
    ) -> list[SpecificationReference]:
        refs: list[SpecificationReference] = []
        for match in _SECTION_REF_PATTERN.findall(text):
            normalized = " ".join(match.split())
            if normalized == source:
                continue
            if known_sections and normalized not in known_sections:
                continue
            refs.append(
                SpecificationReference(
                    source_section=source,
                    target_id=normalized,
                    reference_type=SpecificationReferenceType.SECTION,
                    confidence=0.86,
                    source_text=match,
                )
            )
        return refs

    def _drawing_references(
        self, source: str, text: str
    ) -> list[SpecificationReference]:
        refs: list[SpecificationReference] = []
        for match in _DRAWING_REF_PATTERN.findall(text.upper()):
            normalized = self._normalize_drawing_ref(match)
            if not normalized:
                continue
            refs.append(
                SpecificationReference(
                    source_section=source,
                    target_id=normalized,
                    reference_type=SpecificationReferenceType.DRAWING,
                    confidence=0.84,
                    source_text=match,
                )
            )
        return refs

    def _standard_references(
        self, source: str, text: str
    ) -> list[SpecificationReference]:
        return [
            SpecificationReference(
                source_section=source,
                target_id=match.group(0),
                reference_type=SpecificationReferenceType.STANDARD,
                confidence=0.88,
                source_text=match.group(0),
            )
            for match in _STANDARD_PATTERN.finditer(text.upper())
        ]

    def _manufacturer_references(
        self,
        source: str,
        manufacturers: list[str],
    ) -> list[SpecificationReference]:
        refs: list[SpecificationReference] = []
        for manufacturer in list(manufacturers or []):
            value = str(manufacturer).strip()
            if not value:
                continue
            refs.append(
                SpecificationReference(
                    source_section=source,
                    target_id=value,
                    reference_type=SpecificationReferenceType.MANUFACTURER,
                    confidence=0.9,
                    source_text=value,
                )
            )
        return refs

    def _product_references(
        self, source: str, text: str
    ) -> list[SpecificationReference]:
        refs: list[SpecificationReference] = []
        for match in _PRODUCT_PATTERN.finditer(text.upper()):
            token = " ".join(match.group(0).split())
            if len(token) < 5:
                continue
            refs.append(
                SpecificationReference(
                    source_section=source,
                    target_id=token,
                    reference_type=SpecificationReferenceType.PRODUCT,
                    confidence=0.76,
                    source_text=match.group(0),
                )
            )
        return refs

    def _system_references(
        self, source: str, lines: list[str]
    ) -> list[SpecificationReference]:
        refs: list[SpecificationReference] = []
        joined = "\n".join(lines).lower()
        for term, target in self._system_terms.items():
            if term not in joined:
                continue
            refs.append(
                SpecificationReference(
                    source_section=source,
                    target_id=target,
                    reference_type=SpecificationReferenceType.SYSTEM,
                    confidence=0.82,
                    source_text=term,
                )
            )
        return refs

    def _schedule_references(
        self, source: str, text: str
    ) -> list[SpecificationReference]:
        refs: list[SpecificationReference] = []
        for match in _SCHEDULE_PATTERN.finditer(text):
            refs.append(
                SpecificationReference(
                    source_section=source,
                    target_id=" ".join(match.group(1).split()),
                    reference_type=SpecificationReferenceType.SCHEDULE,
                    confidence=0.8,
                    source_text=match.group(0),
                )
            )
        return refs

    def _addendum_references(
        self, source: str, text: str
    ) -> list[SpecificationReference]:
        refs: list[SpecificationReference] = []
        for match in _ADDENDUM_PATTERN.finditer(text.upper()):
            refs.append(
                SpecificationReference(
                    source_section=source,
                    target_id=match.group(1),
                    reference_type=SpecificationReferenceType.ADDENDUM,
                    confidence=0.9,
                    source_text=match.group(0),
                )
            )
        return refs

    def _equipment_references(
        self, source: str, text: str
    ) -> list[SpecificationReference]:
        refs: list[SpecificationReference] = []
        for match in _EQUIPMENT_PATTERN.finditer(text.upper()):
            refs.append(
                SpecificationReference(
                    source_section=source,
                    target_id=match.group(1),
                    reference_type=SpecificationReferenceType.EQUIPMENT,
                    confidence=0.78,
                    source_text=match.group(0),
                )
            )
        return refs

    def _extract_requirement_candidates(self, lines: list[str]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for line in lines:
            lowered = line.lower()
            for requirement_type, keywords in self._requirement_map.items():
                if not any(keyword in lowered for keyword in keywords):
                    continue
                key = (requirement_type, lowered)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    {
                        "requirement_type": requirement_type,
                        "text": line,
                        "confidence": 0.82,
                        "source": "section_notes",
                    }
                )
        return candidates

    @staticmethod
    def _extract_revision(lines: list[str]) -> str | None:
        for line in lines:
            match = _REVISION_PATTERN.search(line)
            if match is None:
                continue
            value = str(match.group(1) or "").strip()
            if value:
                return value
        return None

    @staticmethod
    def _extract_issue_date(lines: list[str]) -> str | None:
        for line in lines:
            match = _DATE_PATTERN.search(line)
            if match is not None:
                return match.group(0)
        return None

    @staticmethod
    def _reference_targets(
        refs: list[SpecificationReference],
        reference_type: SpecificationReferenceType,
    ) -> list[str]:
        values = [
            item.target_id for item in refs if item.reference_type == reference_type
        ]
        return SpecificationAnalyzer._dedupe_text(values)

    @staticmethod
    def _division_code(section_number: str) -> str | None:
        match = re.match(r"\s*(\d{2})", section_number)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _normalize_drawing_ref(value: str) -> str:
        token = re.sub(r"\s+", "", value.upper())
        if "-" in token:
            return token
        match = re.match(r"([A-Z]{1,4})(\d{2,4}[A-Z]?)", token)
        if match is None:
            return token
        return f"{match.group(1)}-{match.group(2)}"

    @staticmethod
    def _dedupe_references(
        refs: list[SpecificationReference],
    ) -> list[SpecificationReference]:
        seen: set[tuple[str, str, str]] = set()
        result: list[SpecificationReference] = []
        for item in refs:
            key = (
                item.source_section,
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
        for item in values:
            value = str(item).strip()
            if not value:
                continue
            lowered = value.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            result.append(value)
        return result

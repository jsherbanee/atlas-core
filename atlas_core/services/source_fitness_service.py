"""Explainable source-fitness assessment for Atlas intake."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import re
from typing import Any, Iterable

from atlas_core.domain.document_intake import DocumentIntakeSnapshot
from atlas_core.domain.document_relevance import DocumentRelevanceAssessment
from atlas_core.domain.source_fitness import (
    SourceFitnessAssessment,
    SourceFitnessResult,
)

_MAW_COMPONENT_HINTS = (
    "appendix a",
    "base equipment schedule",
    "specified equipment",
    "device type make model qty",
    "owner furnish",
    "add alternate",
)

_DRAWING_COORDINATION_HINTS = (
    "signal flow",
    "rack",
    "topology",
    "network",
    "cable",
    "cross reference",
    "legend",
    "keynote",
    "detail",
    "sheet",
    "diagram",
)

_REPORT_HINTS = (
    "acoustics",
    "design narrative",
    "coordination",
)

_NOISE_HINTS = (
    "11 61 11",
    "wiring and electrical service shall be performed",
    "construction shall reflect",
    "1. control system is a unified control architecture",
    "3. drawings shall show all information necessary",
)

_KNOWN_MANUFACTURERS = (
    "blackmagic",
    "bluestream",
    "bittree",
    "clear-com",
    "chief",
    "dpa",
    "epson",
    "genelec",
    "grace design",
    "jbl",
    "k-array",
    "listen tech",
    "middle atlantic",
    "netgear",
    "panasonic",
    "ptz optics",
    "qsc",
    "redco",
    "rf venue",
    "ross",
    "sennheiser",
    "shure",
    "skaarhoj",
    "turtle av",
    "visionary solutions",
    "yamaha",
    "apple",
    "asus",
    "audix",
    "avid",
    "dell",
    "google",
    "logitech",
)


@dataclass(slots=True)
class _FitnessSignals:
    score: int
    status: str
    baseline_role: str
    authority_level: str
    reasons: list[str]
    evidence_refs: list[str]
    review_flags: list[str]
    source_deficiencies: list[str]
    atlas_failures: list[str]


class SourceFitnessService:
    """Assess how useful each document, page, and evidence item is for baseline work."""

    ENGINE_VERSION = "source-fitness-service/1.0.0"

    def assess_snapshot(self, snapshot: DocumentIntakeSnapshot) -> SourceFitnessResult:
        document_relevance_by_file = {
            assessment.source_file: assessment
            for assessment in list(snapshot.document_relevance_assessments or [])
            if isinstance(assessment, DocumentRelevanceAssessment)
        }

        page_records_by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in list(snapshot.raw_pages or []):
            if not isinstance(record, dict):
                continue
            source_file = str(record.get("source_file") or "").strip()
            if source_file:
                page_records_by_file[source_file].append(record)

        evidence_records: list[tuple[str, str, dict[str, Any]]] = []
        for section in list(snapshot.raw_sections or []):
            if not isinstance(section, dict):
                continue
            source_file = str(section.get("source_file") or "").strip()
            if not source_file:
                continue
            evidence_records.append(("specification_section", source_file, section))

        for schedule in list(snapshot.raw_device_schedules or []):
            if not isinstance(schedule, dict):
                continue
            source_file = str(schedule.get("source_file") or "").strip()
            if not source_file:
                continue
            rows = list(schedule.get("rows") or [])
            for index, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    continue
                evidence_records.append(
                    (
                        "device_schedule_row",
                        source_file,
                        {
                            **row,
                            "page_number": schedule.get("page_number"),
                            "schedule_id": schedule.get("schedule_id"),
                            "row_index": index,
                            "title": schedule.get("title"),
                        },
                    )
                )

        for candidate in list(snapshot.equipment_candidates or []):
            if not isinstance(candidate, dict):
                continue
            source_ref = dict(candidate.get("source_ref") or {})
            source_file = str(source_ref.get("source_file") or "").strip()
            if not source_file:
                continue
            evidence_records.append(
                (
                    "equipment_candidate",
                    source_file,
                    {**candidate, "source_ref": source_ref},
                )
            )

        discovered_files = dict(snapshot.discovered_files or {})
        candidate_files = set(page_records_by_file)
        for files in discovered_files.values():
            candidate_files.update(str(item) for item in files if str(item).strip())
        for _, source_file, _ in evidence_records:
            candidate_files.add(source_file)

        document_assessments: list[SourceFitnessAssessment] = []
        page_assessments: list[SourceFitnessAssessment] = []
        evidence_assessments: list[SourceFitnessAssessment] = []

        for source_file in sorted(candidate_files):
            group_name = self._file_group(source_file, discovered_files)
            pages = sorted(
                page_records_by_file.get(source_file, []),
                key=lambda item: int(item.get("page_number") or 0),
            )
            relevance = document_relevance_by_file.get(source_file)

            page_assessment_rows = [
                self._assess_page(
                    source_file=source_file,
                    group_name=group_name,
                    record=page,
                    document_relevance=relevance,
                )
                for page in pages
            ]
            page_assessments.extend(page_assessment_rows)

            document_assessment = self._assess_document(
                source_file=source_file,
                group_name=group_name,
                page_assessments=page_assessment_rows,
                relevance=relevance,
            )
            document_assessments.append(document_assessment)

        for evidence_type, source_file, record in evidence_records:
            evidence_assessments.append(
                self._assess_evidence(
                    evidence_type=evidence_type,
                    source_file=source_file,
                    record=record,
                    group_name=self._file_group(source_file, discovered_files),
                    document_relevance=document_relevance_by_file.get(source_file),
                )
            )

        summary = {
            "document_count": len(document_assessments),
            "page_count": len(page_assessments),
            "evidence_count": len(evidence_assessments),
            "governing_documents": sum(
                1
                for item in document_assessments
                if item.authority_level == "governing"
            ),
            "coordination_documents": sum(
                1
                for item in document_assessments
                if item.authority_level == "coordination"
            ),
            "strong_baseline_pages": sum(
                1
                for item in page_assessments
                if item.fitness_status == "strong_baseline_evidence"
            ),
            "noise_pages": sum(
                1
                for item in page_assessments
                if item.fitness_status == "likely_extraction_noise"
            ),
            "strong_baseline_evidence": sum(
                1
                for item in evidence_assessments
                if item.fitness_status == "strong_baseline_evidence"
            ),
            "noise_evidence": sum(
                1
                for item in evidence_assessments
                if item.fitness_status == "likely_extraction_noise"
            ),
        }

        return SourceFitnessResult(
            document_assessments=document_assessments,
            page_assessments=page_assessments,
            evidence_assessments=evidence_assessments,
            summary=summary,
            created_by_engine_version=self.ENGINE_VERSION,
        )

    def _assess_document(
        self,
        *,
        source_file: str,
        group_name: str,
        page_assessments: list[SourceFitnessAssessment],
        relevance: DocumentRelevanceAssessment | None,
    ) -> SourceFitnessAssessment:
        if not page_assessments:
            signals = _FitnessSignals(
                score=self._base_score(group_name),
                status="not_useful",
                baseline_role="contextual",
                authority_level="contextual",
                reasons=[
                    "No extracted pages or structured evidence were available for this file."
                ],
                evidence_refs=[self._page_ref(source_file, None)],
                review_flags=["Missing Extracted Content"],
                source_deficiencies=["missing_project_info"],
                atlas_failures=[],
            )
            return self._to_assessment(
                record_type="document",
                source_file=source_file,
                group_name=group_name,
                signals=signals,
                relevance=relevance,
            )

        score = max(item.fitness_score for item in page_assessments)
        page_statuses = Counter(item.fitness_status for item in page_assessments)
        page_roles = Counter(item.baseline_role for item in page_assessments)
        review_flags: list[str] = []
        reasons: list[str] = []
        evidence_refs: list[str] = []
        source_deficiencies: list[str] = []
        atlas_failures: list[str] = []

        if page_statuses.get("strong_baseline_evidence"):
            review_flags.append("Contains major system component evidence")
            reasons.append("At least one page contains a major system component list.")
        if page_statuses.get("governing_but_incomplete"):
            reasons.append(
                "The file contributes governing evidence but the drawings are incomplete."
            )
        if page_statuses.get("likely_extraction_noise"):
            reasons.append("Most extracted evidence looks like OCR or parser noise.")
            source_deficiencies.append("source_document_deficiency")
            atlas_failures.append("atlas_extraction_failure")

        if relevance is not None:
            reasons.append(
                f"Current relevance engine ranks the file as {relevance.project_membership_status}."
            )
            if relevance.primary_discipline:
                evidence_refs.extend(relevance.governing_for)

        evidence_refs.extend(
            self._unique_ref(item.evidence_references[0:2] for item in page_assessments)
        )

        if group_name == "specifications" and page_statuses.get(
            "strong_baseline_evidence"
        ):
            status = "strong_baseline_evidence"
            role = "governing"
            authority = "governing"
            score = max(score, 92)
        elif group_name == "schedules" and page_statuses.get("likely_extraction_noise"):
            status = "likely_extraction_noise"
            role = "noise"
            authority = "contextual"
            score = min(score, 32)
        elif group_name == "drawings" and page_statuses.get("governing_but_incomplete"):
            status = "governing_but_incomplete"
            role = "coordination"
            authority = "coordination"
            score = max(score, 66)
        elif group_name == "reports":
            status = "supplemental_evidence"
            role = "supplemental"
            authority = "coordination"
            score = min(max(score, 40), 68)
        elif page_statuses.get("strong_baseline_evidence"):
            status = "governing_usable"
            role = "governing"
            authority = "governing"
            score = max(score, 84)
        else:
            status = "ambiguous"
            role = "contextual"
            authority = "coordination" if score >= 45 else "contextual"

        baseline_role = role
        if page_roles.get("noise") and role != "governing":
            review_flags.append("Likely Extraction Noise")

        return self._to_assessment(
            record_type="document",
            source_file=source_file,
            group_name=group_name,
            signals=_FitnessSignals(
                score=min(100, score),
                status=status,
                baseline_role=baseline_role,
                authority_level=authority,
                reasons=self._unique(reasons),
                evidence_refs=self._unique(
                    [ref for ref in evidence_refs if isinstance(ref, str)]
                ),
                review_flags=self._unique(review_flags),
                source_deficiencies=self._unique(source_deficiencies),
                atlas_failures=self._unique(atlas_failures),
            ),
            relevance=relevance,
        )

    def _assess_page(
        self,
        *,
        source_file: str,
        group_name: str,
        record: dict[str, Any],
        document_relevance: DocumentRelevanceAssessment | None,
    ) -> SourceFitnessAssessment:
        text = self._page_text(record)
        page_number = self._int_or_none(record.get("page_number"))
        sheet_number = self._text(record.get("sheet_number"))
        detected_discipline = self._page_discipline(
            source_file=source_file,
            page_number=page_number,
            relevance=document_relevance,
        )
        signals = self._score_page_text(
            text=text,
            source_file=source_file,
            group_name=group_name,
            page_number=page_number,
            sheet_number=sheet_number,
        )
        return self._to_assessment(
            record_type="page",
            source_file=source_file,
            group_name=group_name,
            signals=signals,
            page_number=page_number,
            detected_sheet_number=sheet_number,
            detected_discipline=detected_discipline,
            source_excerpt=text[:240] or None,
            relevance=document_relevance,
        )

    def _assess_evidence(
        self,
        *,
        evidence_type: str,
        source_file: str,
        record: dict[str, Any],
        group_name: str,
        document_relevance: DocumentRelevanceAssessment | None,
    ) -> SourceFitnessAssessment:
        text = self._evidence_text(evidence_type, record)
        page_number = self._int_or_none(record.get("page_number"))
        sheet_number = self._text(
            record.get("section_number") or record.get("sheet_number")
        )
        signals = self._score_evidence_text(
            evidence_type=evidence_type,
            text=text,
            source_file=source_file,
            group_name=group_name,
            page_number=page_number,
        )
        return self._to_assessment(
            record_type="evidence",
            source_file=source_file,
            group_name=group_name,
            signals=signals,
            page_number=page_number,
            evidence_id=self._evidence_id(evidence_type, source_file, record),
            evidence_type=evidence_type,
            detected_sheet_number=sheet_number,
            source_excerpt=text[:240] or None,
            relevance=document_relevance,
        )

    def _score_page_text(
        self,
        *,
        text: str,
        source_file: str,
        group_name: str,
        page_number: int | None,
        sheet_number: str | None,
    ) -> _FitnessSignals:
        normalized = self._normalize_text(text)
        score = self._base_score(group_name)
        reasons: list[str] = []
        evidence_refs = [self._page_ref(source_file, page_number)]
        review_flags: list[str] = []
        source_deficiencies: list[str] = []
        atlas_failures: list[str] = []

        if self._has_any(normalized, _MAW_COMPONENT_HINTS):
            score += 30
            reasons.append("The page contains appendix/component-list language.")
            review_flags.append("Major System Component Page")

        if "description device type make model qty" in normalized:
            score += 18
            reasons.append("The page includes a structured make/model/quantity table.")

        quantity_hits = len(re.findall(r"\b(?:LOT|\d+(?:\.\d+)?)\b", normalized))
        manufacturer_hits = sum(
            1 for manufacturer in _KNOWN_MANUFACTURERS if manufacturer in normalized
        )
        if quantity_hits >= 4 and manufacturer_hits >= 2:
            score += 14
            reasons.append("The page contains multiple manufacturer/model rows.")

        if self._has_any(normalized, _DRAWING_COORDINATION_HINTS):
            score += 8
            reasons.append(
                "The page supports drawing coordination and topology review."
            )

        if self._has_any(normalized, _REPORT_HINTS) and group_name == "reports":
            score += 10
            reasons.append("The page contributes supplemental coordination evidence.")

        if self._has_any(normalized, _NOISE_HINTS):
            score -= 22
            reasons.append("The page looks like extraction noise or OCR residue.")
            review_flags.append("Likely Extraction Noise")
            source_deficiencies.append("source_document_deficiency")
            atlas_failures.append("atlas_extraction_failure")

        if sheet_number:
            score += 4
            reasons.append("Sheet or section identifiers are preserved on the page.")

        if group_name == "drawings" and not self._has_any(
            normalized, ("signal flow", "rack", "network topology", "cable schedule")
        ):
            reasons.append(
                "The drawing page does not expose signal-flow or topology detail."
            )
            source_deficiencies.append("source_document_deficiency")

        if group_name == "reports" and not self._has_any(normalized, _REPORT_HINTS):
            source_deficiencies.append("missing_project_info")

        if group_name == "schedules" and quantity_hits < 2:
            review_flags.append("Sparse Schedule Evidence")

        if self._has_any(normalized, ("owner furnish", "add alternate")):
            review_flags.append("Responsibility or alternate language present")

        if score >= 86 and group_name in {"specifications", "schedules"}:
            status = "strong_baseline_evidence"
            role = "governing"
            authority = "governing"
        elif group_name == "drawings" and score >= 58:
            status = "governing_but_incomplete"
            role = "coordination"
            authority = "coordination"
        elif group_name == "reports" and score >= 40:
            status = "supplemental_evidence"
            role = "supplemental"
            authority = "coordination"
        elif self._has_any(normalized, _NOISE_HINTS) or score <= 28:
            status = "likely_extraction_noise"
            role = "noise"
            authority = "contextual"
        elif score >= 65:
            status = "governing_usable"
            role = "governing"
            authority = "governing"
        elif score >= 45:
            status = "coordination_evidence"
            role = "coordination"
            authority = "coordination"
        else:
            status = "not_useful"
            role = "contextual"
            authority = "contextual"

        return _FitnessSignals(
            score=min(100, score),
            status=status,
            baseline_role=role,
            authority_level=authority,
            reasons=self._unique(reasons),
            evidence_refs=self._unique(evidence_refs),
            review_flags=self._unique(review_flags),
            source_deficiencies=self._unique(source_deficiencies),
            atlas_failures=self._unique(atlas_failures),
        )

    def _score_evidence_text(
        self,
        *,
        evidence_type: str,
        text: str,
        source_file: str,
        group_name: str,
        page_number: int | None,
    ) -> _FitnessSignals:
        normalized = self._normalize_text(text)
        score = 42 if evidence_type == "device_schedule_row" else 50
        reasons: list[str] = []
        evidence_refs = [self._page_ref(source_file, page_number)]
        review_flags: list[str] = []
        source_deficiencies: list[str] = []
        atlas_failures: list[str] = []

        if evidence_type == "equipment_candidate":
            score += 24
            reasons.append("The evidence item already resolves an equipment candidate.")
        if evidence_type == "specification_section":
            score += 12
            reasons.append("The evidence item is tied to a specification section.")

        if self._has_any(normalized, _MAW_COMPONENT_HINTS):
            score += 18
            reasons.append(
                "The evidence item comes from the major system component list."
            )

        if self._has_any(normalized, _DRAWING_COORDINATION_HINTS):
            score += 8
            reasons.append(
                "The evidence item supports drawing/specification coordination."
            )

        if self._has_any(normalized, _NOISE_HINTS) or (
            evidence_type == "device_schedule_row"
            and self._looks_like_noise(normalized)
        ):
            score -= 26
            reasons.append("The evidence item looks like repeated prose or OCR noise.")
            review_flags.append("Likely Extraction Noise")
            source_deficiencies.append("source_document_deficiency")
            atlas_failures.append("atlas_extraction_failure")

        if "add alternate" in normalized:
            review_flags.append("Alternate Scope")
        if "owner furnish" in normalized:
            review_flags.append("Owner Furnished Scope")
        if "by contractor" in normalized or "by av contractor" in normalized:
            review_flags.append("Contractor Responsibility")

        if score >= 82:
            status = "strong_baseline_evidence"
            role = "governing"
            authority = "governing"
        elif score >= 64:
            status = "governing_usable"
            role = "governing"
            authority = "governing"
        elif score >= 48:
            status = "coordination_evidence"
            role = "coordination"
            authority = "coordination"
        elif score >= 34:
            status = "supplemental_evidence"
            role = "supplemental"
            authority = "coordination"
        elif score >= 20:
            status = "ambiguous"
            role = "contextual"
            authority = "contextual"
        else:
            status = "likely_extraction_noise"
            role = "noise"
            authority = "contextual"

        if group_name == "schedules" and status != "strong_baseline_evidence":
            review_flags.append("Schedule Row Review Required")

        return _FitnessSignals(
            score=max(0, min(100, score)),
            status=status,
            baseline_role=role,
            authority_level=authority,
            reasons=self._unique(reasons),
            evidence_refs=self._unique(evidence_refs),
            review_flags=self._unique(review_flags),
            source_deficiencies=self._unique(source_deficiencies),
            atlas_failures=self._unique(atlas_failures),
        )

    def _to_assessment(
        self,
        *,
        record_type: str,
        source_file: str,
        group_name: str,
        signals: _FitnessSignals,
        relevance: DocumentRelevanceAssessment | None,
        page_number: int | None = None,
        evidence_id: str | None = None,
        evidence_type: str | None = None,
        detected_sheet_number: str | None = None,
        detected_discipline: str | None = None,
        source_excerpt: str | None = None,
    ) -> SourceFitnessAssessment:
        governing_for: list[str] = []
        coordination_for: list[str] = []
        non_governing_for: list[str] = []

        if relevance is not None:
            governing_for.extend(list(relevance.governing_for or []))
            coordination_for.extend(list(relevance.coordination_for or []))
            non_governing_for.extend(list(relevance.non_governing_for or []))

        if signals.authority_level == "governing" and not governing_for:
            governing_for.append("baseline engineering scope")
        elif signals.authority_level == "coordination" and not coordination_for:
            coordination_for.append("engineering coordination")
        elif signals.authority_level == "contextual" and not non_governing_for:
            non_governing_for.append("baseline exclusion review")

        return SourceFitnessAssessment(
            record_type=record_type,
            source_file=source_file,
            source_group=group_name,
            page_number=page_number,
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            detected_sheet_number=detected_sheet_number,
            detected_discipline=detected_discipline,
            source_excerpt=source_excerpt,
            fitness_status=signals.status,
            baseline_role=signals.baseline_role,
            fitness_score=signals.score,
            authority_level=signals.authority_level,
            governing_for=governing_for,
            coordination_for=coordination_for,
            non_governing_for=non_governing_for,
            reasons=signals.reasons,
            evidence_references=signals.evidence_refs,
            review_flags=signals.review_flags,
            source_deficiencies=signals.source_deficiencies,
            atlas_failures=signals.atlas_failures,
        )

    @staticmethod
    def _page_discipline(
        *,
        source_file: str,
        page_number: int | None,
        relevance: DocumentRelevanceAssessment | None,
    ) -> str | None:
        if relevance is None:
            return None

        if relevance.primary_discipline:
            return relevance.primary_discipline

        if (
            relevance.page_assessments
            and page_number is not None
            and 0 < page_number <= len(relevance.page_assessments)
        ):
            page_assessment = relevance.page_assessments[page_number - 1]
            return page_assessment.detected_discipline

        return None

    @staticmethod
    def _page_text(record: dict[str, Any]) -> str:
        text = record.get("text")
        if isinstance(text, str):
            return text.strip()
        return ""

    def _evidence_text(self, evidence_type: str, record: dict[str, Any]) -> str:
        if evidence_type == "specification_section":
            parts = [
                self._text(record.get("section_number")),
                self._text(record.get("title")),
                self._text(record.get("source_excerpt")),
            ]
            return " ".join(part for part in parts if part)

        if evidence_type == "equipment_candidate":
            parts = [
                self._text(record.get("description")),
                self._text(record.get("tag")),
                self._text((record.get("source_ref") or {}).get("text_excerpt")),
            ]
            return " ".join(part for part in parts if part)

        if evidence_type == "device_schedule_row":
            parts = [
                self._text(record.get("tag")),
                self._text(record.get("description")),
                self._text(record.get("manufacturer")),
                self._text(record.get("model")),
                self._text(record.get("qty") or record.get("quantity")),
            ]
            return " ".join(part for part in parts if part)

        return " ".join(
            part
            for part in (
                self._text(record.get("source_excerpt")),
                self._text(record.get("text_excerpt")),
                self._text(record.get("description")),
            )
            if part
        )

    def _file_group(
        self,
        source_file: str,
        discovered_files: dict[str, list[str]],
    ) -> str:
        for group_name, files in discovered_files.items():
            if source_file in files:
                return group_name

        lowered = source_file.casefold()
        if "report" in lowered or "narrative" in lowered:
            return "reports"
        if "equipment" in lowered:
            return "schedules"
        if "draw" in lowered or "av" in lowered:
            return "drawings"
        if "spec" in lowered:
            return "specifications"
        return "other"

    @staticmethod
    def _base_score(group_name: str) -> int:
        return {
            "specifications": 68,
            "schedules": 54,
            "drawings": 58,
            "reports": 36,
            "addenda": 72,
            "images": 20,
            "other": 24,
            "unsupported": 12,
        }.get(group_name, 24)

    @staticmethod
    def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
        return any(pattern in text for pattern in patterns)

    @staticmethod
    def _looks_like_noise(text: str) -> bool:
        if not text:
            return True
        tokens = text.split()
        alpha_tokens = sum(
            1 for token in tokens if any(char.isalpha() for char in token)
        )
        numeric_tokens = sum(
            1 for token in tokens if any(char.isdigit() for char in token)
        )
        if len(tokens) <= 4 and numeric_tokens >= 1:
            return True
        if alpha_tokens and numeric_tokens and alpha_tokens < numeric_tokens:
            return True
        if " " not in text and len(text) < 10:
            return True
        return False

    @staticmethod
    def _page_ref(source_file: str, page_number: int | None) -> str:
        if page_number is None:
            return source_file
        return f"{source_file}#p{page_number}"

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.split()).casefold()

    @staticmethod
    def _evidence_id(
        evidence_type: str, source_file: str, record: dict[str, Any]
    ) -> str:
        if evidence_type == "equipment_candidate":
            candidate_id = str(record.get("candidate_id") or "candidate")
            return f"{source_file}::{candidate_id}"
        if evidence_type == "specification_section":
            section_number = str(record.get("section_number") or "section")
            page_number = record.get("page_number")
            suffix = f"p{page_number}" if page_number is not None else "page"
            return f"{source_file}::{section_number}:{suffix}"
        if evidence_type == "device_schedule_row":
            schedule_id = str(record.get("schedule_id") or "schedule")
            row_index = record.get("row_index") or 0
            return f"{source_file}::{schedule_id}:{row_index}"
        return f"{source_file}::evidence"

    @staticmethod
    def _text(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(
            dict.fromkeys(item.strip() for item in values if item and item.strip())
        )

    @staticmethod
    def _unique_ref(values: Iterable[list[str]]) -> list[str]:
        flattened: list[str] = []
        for value in values:
            flattened.extend(value)
        return list(
            dict.fromkeys(item.strip() for item in flattened if item and item.strip())
        )

"""Explainable document relevance assessment for Atlas intake."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import re
from typing import Any

from atlas_core.domain.document_intake import DocumentIntakeSnapshot
from atlas_core.domain.document_relevance import (
    DocumentRelevanceAssessment,
    PageRelevanceAssessment,
    RelevanceWorkflowScores,
)

_PRIMARY_DISCIPLINE_PATTERNS: dict[str, tuple[str, ...]] = {
    "audiovisual": (
        "audio visual",
        "audiovisual",
        "av systems",
        "av system",
        "av panel",
        "audio/video",
        "a/v",
    ),
    "av control systems": (
        "av control",
        "av controller",
        "control processor",
        "touchpanel",
        "control booth",
        "control room",
        "control system",
    ),
    "integrated control systems": (
        "integrated control",
        "integrated systems",
        "control network",
        "system integration",
        "gateway",
    ),
    "theatrical lighting": (
        "theatrical lighting",
        "theatre lighting",
        "stage lighting",
        "lighting instruments",
        "lighting positions",
        "lighting fixtures",
        "lighting console",
        "lighting system",
        "dmx",
        "sacn",
        "art-net",
        "company switch",
    ),
    "theatrical lighting control": (
        "lighting control",
        "lighting-control",
        "dimming",
        "lighting processor",
        "lighting network",
        "relay",
        "scene control",
        "house light integration",
    ),
    "show control": (
        "show control",
        "cue stack",
        "cue",
        "scene control",
        "show system",
        "show playback",
    ),
    "performance-system controls": (
        "performance system",
        "performance-system",
        "stage management",
        "control booth",
        "control room",
        "house light integration",
        "performance control",
    ),
}

_ARCHITECTURAL_LIGHTING_PATTERNS: tuple[str, ...] = (
    "architectural lighting",
    "decorative lighting",
    "general illumination",
    "daylighting",
    "daylight harvesting",
    "occupancy sensor",
    "occupancy controls",
    "room lighting",
    "room scenes",
    "lighting panel",
    "lighting-panel",
    "lighting control panel",
    "wall station",
    "normal lighting",
    "emergency lighting",
    "facade lighting",
    "landscape lighting",
)

_REPORT_SCOPE_PATTERNS: tuple[str, ...] = (
    "acoustics",
    "sound isolation",
    "room acoustics",
    "noise/vibration",
    "noise control",
    "design narrative",
)

_GROUP_BASE_SCORES = {
    "drawings": 60,
    "specifications": 68,
    "schedules": 66,
    "addenda": 72,
    "reports": 48,
    "images": 28,
    "other": 22,
    "unsupported": 15,
}

_WORKFLOW_BASE = {
    "governing": RelevanceWorkflowScores(
        intake=92,
        estimating=96,
        engineering=95,
        procurement=92,
        construction=84,
        commissioning=78,
        service=72,
    ),
    "coordination": RelevanceWorkflowScores(
        intake=72,
        estimating=52,
        engineering=74,
        procurement=48,
        construction=58,
        commissioning=50,
        service=45,
    ),
    "possible_scope": RelevanceWorkflowScores(
        intake=64,
        estimating=46,
        engineering=62,
        procurement=42,
        construction=50,
        commissioning=44,
        service=40,
    ),
    "contextual": RelevanceWorkflowScores(
        intake=34,
        estimating=18,
        engineering=30,
        procurement=16,
        construction=18,
        commissioning=16,
        service=14,
    ),
    "incidental": RelevanceWorkflowScores(
        intake=16,
        estimating=8,
        engineering=12,
        procurement=8,
        construction=8,
        commissioning=8,
        service=8,
    ),
}

_PAGE_REF_PATTERN = re.compile(r"^(?P<source>.+?)(?:#p(?P<page>\d+))?$")


@dataclass(slots=True)
class _PageSignals:
    primary_hits: Counter[str]
    architectural_hits: list[str]
    report_hits: list[str]
    reasons: list[str]
    evidence: list[str]
    score: int
    review_flags: list[str]


class DocumentRelevanceService:
    """Build explainable document relevance assessments for intake."""

    def assess_snapshot(
        self,
        snapshot: DocumentIntakeSnapshot,
    ) -> list[DocumentRelevanceAssessment]:
        discovered_files = dict(snapshot.discovered_files or {})
        return self.assess_documents(
            page_records=list(snapshot.raw_pages or []),
            discovered_files=discovered_files,
            file_groups=self._file_groups_from_discovered_files(discovered_files),
        )

    def assess_documents(
        self,
        *,
        page_records: list[dict[str, Any]],
        discovered_files: dict[str, list[str]] | None = None,
        file_groups: dict[str, str] | None = None,
    ) -> list[DocumentRelevanceAssessment]:
        grouped_pages: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in page_records:
            if not isinstance(record, dict):
                continue
            source_file = str(record.get("source_file") or "").strip()
            if not source_file:
                continue
            grouped_pages[source_file].append(record)

        discovered_files = dict(discovered_files or {})
        file_groups = dict(file_groups or {})

        candidate_files = set(grouped_pages)
        for files in discovered_files.values():
            candidate_files.update(str(name) for name in files if str(name).strip())

        assessments: list[DocumentRelevanceAssessment] = []
        for source_file in sorted(candidate_files):
            pages = sorted(
                grouped_pages.get(source_file, []),
                key=lambda item: int(item.get("page_number") or 0),
            )
            group_name = file_groups.get(source_file) or self._infer_group(
                source_file,
                discovered_files,
            )
            page_assessments = [
                self._assess_page(
                    source_file=source_file, record=page, group_name=group_name
                )
                for page in pages
            ]
            assessment = self._assess_document(
                source_file=source_file,
                group_name=group_name,
                page_assessments=page_assessments,
            )
            assessments.append(assessment)

        return assessments

    def assess_document(
        self,
        *,
        source_file: str,
        group_name: str,
        page_records: list[dict[str, Any]],
    ) -> DocumentRelevanceAssessment:
        page_assessments = [
            self._assess_page(
                source_file=source_file, record=record, group_name=group_name
            )
            for record in sorted(
                page_records,
                key=lambda item: int(item.get("page_number") or 0),
            )
        ]
        return self._assess_document(
            source_file=source_file,
            group_name=group_name,
            page_assessments=page_assessments,
        )

    def _assess_document(
        self,
        *,
        source_file: str,
        group_name: str,
        page_assessments: list[PageRelevanceAssessment],
    ) -> DocumentRelevanceAssessment:
        page_count = len(page_assessments)
        if not page_assessments:
            synthetic = self._assess_page(
                source_file=source_file,
                record={"source_file": source_file, "page_number": None, "text": ""},
                group_name=group_name,
            )
            page_assessments = [synthetic]
            page_count = 0

        aggregate_primary_hits: Counter[str] = Counter()
        aggregate_arch_hits: list[str] = []
        aggregate_report_hits: list[str] = []
        aggregate_reasons: list[str] = []
        aggregate_evidence: list[str] = []
        review_flags: list[str] = []

        for page in page_assessments:
            aggregate_primary_hits.update(
                self._count_discipline_hits(page.relevance_reasons)
            )
            aggregate_arch_hits.extend(
                self._extract_reason_markers(
                    page.relevance_reasons, "architectural lighting"
                )
            )
            aggregate_report_hits.extend(
                self._extract_reason_markers(page.relevance_reasons, "report scope")
            )
            aggregate_reasons.extend(page.relevance_reasons)
            aggregate_evidence.extend(page.evidence_references)
            review_flags.extend(page.review_flags)

        primary_discipline, secondary_disciplines = self._select_disciplines(
            aggregate_primary_hits,
            aggregate_arch_hits,
        )
        overall_score = self._aggregate_page_score(page_assessments, group_name)
        authority_level = self._resolve_authority_level(
            group_name=group_name,
            primary_discipline=primary_discipline,
            review_flags=review_flags,
            overall_score=overall_score,
        )
        membership_status = self._membership_status(
            authority_level=authority_level,
            primary_discipline=primary_discipline,
            review_flags=review_flags,
            overall_score=overall_score,
        )
        workflow_scores = self._workflow_scores(
            authority_level=authority_level,
            group_name=group_name,
            overall_score=overall_score,
            primary_discipline=primary_discipline,
            review_flags=review_flags,
        )

        governing_for, coordination_for, non_governing_for = self._scope_lists(
            primary_discipline=primary_discipline,
            secondary_disciplines=secondary_disciplines,
            review_flags=review_flags,
            authority_level=authority_level,
            group_name=group_name,
        )

        return DocumentRelevanceAssessment(
            source_file=source_file,
            document_group=group_name,
            page_count=page_count,
            project_membership_score=overall_score,
            project_membership_status=membership_status,
            primary_discipline=primary_discipline,
            secondary_disciplines=secondary_disciplines,
            overall_relevance_score=overall_score,
            workflow_scores=workflow_scores,
            authority_level=authority_level,
            governing_for=governing_for,
            coordination_for=coordination_for,
            non_governing_for=non_governing_for,
            relevance_reasons=self._unique(aggregate_reasons),
            evidence_references=self._unique(aggregate_evidence),
            review_flags=self._unique(review_flags),
            page_assessments=page_assessments,
        )

    def _assess_page(
        self,
        *,
        source_file: str,
        record: dict[str, Any],
        group_name: str,
    ) -> PageRelevanceAssessment:
        text = self._page_text(record)
        signals = self._score_text(
            text=text, source_file=source_file, group_name=group_name
        )
        primary_discipline, secondary_disciplines = self._select_disciplines(
            signals.primary_hits,
            signals.architectural_hits,
        )
        detected_discipline = primary_discipline or (
            "architectural lighting"
            if "architectural lighting" in secondary_disciplines
            else None
        )
        authority_level = self._resolve_authority_level(
            group_name=group_name,
            primary_discipline=primary_discipline,
            review_flags=signals.review_flags,
            overall_score=signals.score,
        )
        membership_status = self._membership_status(
            authority_level=authority_level,
            primary_discipline=primary_discipline,
            review_flags=signals.review_flags,
            overall_score=signals.score,
        )
        workflow_scores = self._workflow_scores(
            authority_level=authority_level,
            group_name=group_name,
            overall_score=signals.score,
            primary_discipline=primary_discipline,
            review_flags=signals.review_flags,
        )
        return PageRelevanceAssessment(
            source_file=source_file,
            page_number=self._int_or_none(record.get("page_number")),
            detected_sheet_number=self._detected_sheet_number(record),
            detected_discipline=detected_discipline,
            project_membership_score=signals.score,
            project_membership_status=membership_status,
            primary_discipline=primary_discipline,
            secondary_disciplines=secondary_disciplines,
            overall_relevance_score=signals.score,
            workflow_scores=workflow_scores,
            authority_level=authority_level,
            governing_for=self._governing_scope_labels(
                primary_discipline, secondary_disciplines
            ),
            coordination_for=self._coordination_scope_labels(
                group_name=group_name,
                review_flags=signals.review_flags,
                primary_discipline=primary_discipline,
            ),
            non_governing_for=self._non_governing_scope_labels(
                group_name=group_name,
                review_flags=signals.review_flags,
                primary_discipline=primary_discipline,
            ),
            relevance_reasons=signals.reasons,
            evidence_references=signals.evidence,
            review_flags=signals.review_flags,
        )

    def _score_text(
        self,
        *,
        text: str,
        source_file: str,
        group_name: str,
    ) -> _PageSignals:
        normalized = self._normalize_text(text)
        primary_hits: Counter[str] = Counter()
        reasons: list[str] = []
        evidence: list[str] = [self._page_ref(source_file, None)]
        score = _GROUP_BASE_SCORES.get(group_name, 24)
        review_flags: list[str] = []

        for discipline, patterns in _PRIMARY_DISCIPLINE_PATTERNS.items():
            hits = [pattern for pattern in patterns if pattern in normalized]
            if not hits:
                continue
            primary_hits[discipline] += len(hits)
            score += min(18, 10 + len(hits) * 2)
            reasons.append(
                f"Matched {discipline} evidence: {', '.join(self._format_terms(hits))}."
            )
            evidence.extend(hits[:3])

        arch_hits = [
            pattern
            for pattern in _ARCHITECTURAL_LIGHTING_PATTERNS
            if pattern in normalized
        ]
        if arch_hits:
            score += min(12, 6 + len(arch_hits))
            reasons.append(
                "Matched architectural lighting evidence: "
                f"{', '.join(self._format_terms(arch_hits[:5]))}."
            )
            evidence.extend(arch_hits[:3])
            review_flags.append("Possible Architectural Lighting Scope")

        report_hits = [
            pattern for pattern in _REPORT_SCOPE_PATTERNS if pattern in normalized
        ]
        if report_hits:
            score += min(10, 5 + len(report_hits))
            reasons.append(
                "Matched report/coordination evidence: "
                f"{', '.join(self._format_terms(report_hits[:4]))}."
            )
            evidence.extend(report_hits[:2])

        if "sheet title" in normalized or "sheet number" in normalized:
            score += 4
            reasons.append("Sheet metadata indicates a governed drawing page.")

        if any(
            token in normalized
            for token in ("division 11", "section 27", "audio visual systems")
        ):
            score += 8
            reasons.append("Text references a governed AV or specification section.")

        if any(token in normalized for token in ("control booth", "control room")):
            score += 6
            reasons.append("Control-space evidence indicates coordination priority.")

        if arch_hits and primary_hits:
            review_flags.append("Shared Lighting Scope")

        if not primary_hits and not arch_hits and group_name == "reports":
            review_flags.append("Review For Scope Relevance")

        score = min(100, score)
        if not primary_hits and not arch_hits and group_name in {"other", "images"}:
            score = min(score, 35)

        return _PageSignals(
            primary_hits=primary_hits,
            architectural_hits=arch_hits,
            report_hits=report_hits,
            reasons=self._unique(reasons)
            or [f"Detected {group_name} document context."],
            evidence=self._unique(evidence),
            score=score,
            review_flags=self._unique(review_flags),
        )

    def _aggregate_page_score(
        self,
        page_assessments: list[PageRelevanceAssessment],
        group_name: str,
    ) -> int:
        if not page_assessments:
            return _GROUP_BASE_SCORES.get(group_name, 24)

        top_scores = sorted(
            (page.overall_relevance_score for page in page_assessments),
            reverse=True,
        )
        best = top_scores[0]
        bonus = min(12, 3 * max(0, sum(1 for score in top_scores if score >= 60) - 1))
        return min(100, best + bonus)

    def _workflow_scores(
        self,
        *,
        authority_level: str,
        group_name: str,
        overall_score: int,
        primary_discipline: str | None,
        review_flags: list[str],
    ) -> RelevanceWorkflowScores:
        base = _WORKFLOW_BASE.get(authority_level, _WORKFLOW_BASE["contextual"])
        if authority_level == "governing" and group_name == "schedules":
            return RelevanceWorkflowScores(
                intake=min(100, base.intake + 1),
                estimating=min(100, base.estimating + 2),
                engineering=min(100, base.engineering + 1),
                procurement=min(100, base.procurement + 3),
                construction=min(100, base.construction + 2),
                commissioning=min(100, base.commissioning + 1),
                service=min(100, base.service),
            )

        if primary_discipline in {"theatrical lighting", "theatrical lighting control"}:
            return RelevanceWorkflowScores(
                intake=max(base.intake, 88),
                estimating=max(base.estimating, 92),
                engineering=max(base.engineering, 90),
                procurement=max(base.procurement, 90),
                construction=max(base.construction, 84),
                commissioning=max(base.commissioning, 78),
                service=max(base.service, 72),
            )

        if "Possible Architectural Lighting Scope" in review_flags:
            return RelevanceWorkflowScores(
                intake=58,
                estimating=36,
                engineering=62,
                procurement=44,
                construction=55,
                commissioning=48,
                service=42,
            )

        if group_name == "reports":
            return RelevanceWorkflowScores(
                intake=46,
                estimating=24,
                engineering=max(70, min(88, overall_score + 18)),
                procurement=18,
                construction=24,
                commissioning=36,
                service=28,
            )

        if group_name == "other":
            return RelevanceWorkflowScores(
                intake=30,
                estimating=14,
                engineering=24,
                procurement=12,
                construction=14,
                commissioning=12,
                service=12,
            )

        return base

    def _select_disciplines(
        self,
        primary_hits: Counter[str],
        architectural_hits: list[str],
    ) -> tuple[str | None, list[str]]:
        candidates = [
            (discipline, hits) for discipline, hits in primary_hits.items() if hits > 0
        ]
        if not candidates:
            secondary_disciplines = (
                ["architectural lighting"] if architectural_hits else []
            )
            return None, secondary_disciplines

        primary_discipline = sorted(
            candidates,
            key=lambda item: (-item[1], item[0]),
        )[
            0
        ][0]
        secondary_disciplines = sorted(
            discipline
            for discipline, _ in candidates
            if discipline != primary_discipline
        )

        if architectural_hits:
            secondary_disciplines.append("architectural lighting")

        return primary_discipline, self._unique(secondary_disciplines)

    def _resolve_authority_level(
        self,
        *,
        group_name: str,
        primary_discipline: str | None,
        review_flags: list[str],
        overall_score: int,
    ) -> str:
        if primary_discipline is not None:
            return "governing"
        if "Possible Architectural Lighting Scope" in review_flags:
            return "coordination"
        if group_name == "reports":
            return "coordination"
        if group_name == "schedules":
            return "governing" if overall_score >= 60 else "coordination"
        if group_name == "drawings" and overall_score >= 55:
            return "coordination"
        if overall_score >= 70:
            return "governing"
        if overall_score >= 45:
            return "coordination"
        return "contextual"

    def _membership_status(
        self,
        *,
        authority_level: str,
        primary_discipline: str | None,
        review_flags: list[str],
        overall_score: int,
    ) -> str:
        if "Possible Architectural Lighting Scope" in review_flags:
            return "possible_scope"
        if primary_discipline is not None and authority_level == "governing":
            return "governing"
        if authority_level == "governing" and overall_score >= 80:
            return "governing"
        if authority_level == "governing":
            return "likely_scope"
        if authority_level == "coordination" and overall_score >= 50:
            return "related"
        if overall_score >= 30:
            return "related"
        return "incidental"

    def _scope_lists(
        self,
        *,
        primary_discipline: str | None,
        secondary_disciplines: list[str],
        review_flags: list[str],
        authority_level: str,
        group_name: str,
    ) -> tuple[list[str], list[str], list[str]]:
        governing_for: list[str] = []
        coordination_for: list[str] = []
        non_governing_for: list[str] = []

        if primary_discipline:
            governing_for.append(f"{primary_discipline} scope")
            for discipline in secondary_disciplines:
                if discipline == "architectural lighting":
                    coordination_for.append("architectural lighting coordination")
                else:
                    coordination_for.append(f"{discipline} coordination")
        elif group_name == "schedules":
            governing_for.extend(
                [
                    "equipment estimating",
                    "equipment procurement",
                    "scope coordination",
                ]
            )
        elif group_name == "reports":
            coordination_for.extend(["acoustics coordination", "design review"])
            non_governing_for.extend(["AV equipment estimating"])
        elif group_name == "drawings":
            coordination_for.extend(["drawing coordination"])
        else:
            non_governing_for.append("AV equipment estimating")

        if "Possible Architectural Lighting Scope" in review_flags:
            coordination_for.append("architectural lighting coordination")
            non_governing_for.append("architectural lighting estimating")

        if authority_level == "coordination" and not coordination_for:
            coordination_for.append("coordination review")

        return (
            self._unique(governing_for),
            self._unique(coordination_for),
            self._unique(non_governing_for),
        )

    def _governing_scope_labels(
        self,
        primary_discipline: str | None,
        secondary_disciplines: list[str],
    ) -> list[str]:
        labels = []
        if primary_discipline:
            labels.append(f"{primary_discipline} scope")
        labels.extend(
            f"{discipline} scope"
            for discipline in secondary_disciplines
            if discipline != "architectural lighting"
        )
        return self._unique(labels)

    def _coordination_scope_labels(
        self,
        *,
        group_name: str,
        review_flags: list[str],
        primary_discipline: str | None,
    ) -> list[str]:
        labels: list[str] = []
        if group_name == "reports":
            labels.extend(["acoustics coordination", "design review"])
        if group_name == "drawings" and primary_discipline is None:
            labels.append("drawing coordination")
        if "Possible Architectural Lighting Scope" in review_flags:
            labels.append("architectural lighting coordination")
        return self._unique(labels)

    def _non_governing_scope_labels(
        self,
        *,
        group_name: str,
        review_flags: list[str],
        primary_discipline: str | None,
    ) -> list[str]:
        labels: list[str] = []
        if group_name == "reports":
            labels.append("AV equipment estimating")
        if "Possible Architectural Lighting Scope" in review_flags:
            labels.append("architectural lighting estimating")
        if primary_discipline is None and group_name == "other":
            labels.append("incidental cross-trade information")
        return self._unique(labels)

    def _page_text(self, record: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in (
            "text",
            "source_excerpt",
            "title",
            "sheet_number",
            "section_number",
        ):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        source_file = str(record.get("source_file") or "")
        if source_file:
            parts.append(source_file)
        return " ".join(parts)

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip().lower()

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    @staticmethod
    def _page_ref(source_file: str, page_number: int | None) -> str:
        if page_number is None:
            return source_file
        return f"{source_file}#p{page_number}"

    @staticmethod
    def _detected_sheet_number(record: dict[str, Any]) -> str | None:
        for key in ("sheet_number", "section_number"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _format_terms(terms: list[str]) -> list[str]:
        return [term.replace("-", " ") for term in terms]

    @staticmethod
    def _count_discipline_hits(reasons: list[str]) -> Counter[str]:
        counter: Counter[str] = Counter()
        allowed_labels = set(_PRIMARY_DISCIPLINE_PATTERNS)
        for reason in reasons:
            match = re.match(r"Matched (?P<label>.+?) evidence:", reason)
            if match and match.group("label") in allowed_labels:
                counter[match.group("label")] += 1
        return counter

    @staticmethod
    def _extract_reason_markers(reasons: list[str], marker: str) -> list[str]:
        return [reason for reason in reasons if marker.lower() in reason.lower()]

    @staticmethod
    def _infer_group(source_file: str, discovered_files: dict[str, list[str]]) -> str:
        name = source_file.lower()
        if source_file in discovered_files.get("drawings", []):
            return "drawings"
        if source_file in discovered_files.get("specifications", []):
            return "specifications"
        if source_file in discovered_files.get("schedules", []):
            return "schedules"
        if source_file in discovered_files.get("addenda", []):
            return "addenda"
        if source_file in discovered_files.get("images", []):
            return "images"
        if "report" in name or "narrative" in name:
            return "reports"
        if "schedule" in name:
            return "schedules"
        if "spec" in name or "section" in name:
            return "specifications"
        if "draw" in name or "sheet" in name or "plan" in name or "t0-" in name:
            return "drawings"
        return "other"

    @staticmethod
    def _file_groups_from_discovered_files(
        discovered_files: dict[str, list[str]],
    ) -> dict[str, str]:
        groups: dict[str, str] = {}
        for group_name, files in discovered_files.items():
            for file_name in files:
                groups[str(file_name)] = group_name
        return groups

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(
            dict.fromkeys(
                item.strip()
                for item in values
                if isinstance(item, str) and item.strip()
            )
        )

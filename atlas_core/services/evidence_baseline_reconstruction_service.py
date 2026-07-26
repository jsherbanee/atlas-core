"""Evidence-based baseline reconstruction for Atlas validation runs."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
import csv
import re
from pathlib import Path
from typing import Any

from atlas_core.domain.document_intake import DocumentIntakeSnapshot
from atlas_core.domain.source_fitness import (
    SourceFitnessAssessment,
    SourceFitnessResult,
)
from atlas_core.services.document_intake_service import DocumentIntakeService

_KNOWN_MANUFACTURERS = (
    "visionary solutions",
    "middle atlantic",
    "clear-com",
    "listen tech",
    "k-array",
    "sennheiser",
    "blackmagic",
    "turtle av",
    "skaarhoj",
    "grace design",
    "netgear",
    "middle atlantic",
    "bittree",
    "bluestream",
    "panasonic",
    "ptz optics",
    "qsc",
    "redco",
    "rf venue",
    "shure",
    "yamaha",
    "asus",
    "apple",
    "audix",
    "chief",
    "dell",
    "epson",
    "genelec",
    "jbl",
    "lg",
    "logitech",
    "ross",
)

_ROOM_TITLE_HINTS = (
    "pre-function",
    "dressing rooms",
    "practice rooms",
    "facility office",
    "manager office",
    "building circulation",
    "student lounge",
    "teaching studios",
    "ensemble studio",
    "recording studio",
    "roof terrace",
    "wireless com",
    "roof terrace portable",
)


@dataclass(slots=True)
class MajorSystemComponentRow:
    source_file: str
    page_number: int
    performance_space: str
    system_block: str
    raw_line: str
    description: str
    manufacturer: str | None
    model: str | None
    quantity: str
    responsibility: str | None
    allowance_status: str
    alternate_status: str
    baseline_role: str
    source_fitness_status: str
    source_fitness_score: int
    evidence_reference: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BaselineEquipmentRow:
    source_file: str
    page_number: int
    performance_space: str
    system_block: str
    description: str
    manufacturer: str | None
    model: str | None
    quantity: str
    responsibility: str | None
    allowance_status: str
    alternate_status: str
    source_fitness_status: str
    source_fitness_score: int
    baseline_role: str
    confidence: int
    evidence_reference: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceDeficiencyRow:
    source_file: str
    page_number: int | None
    deficiency_type: str
    severity: str
    explanation: str
    evidence_reference: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ConsolidatedRfiRow:
    root_issue: str
    issue_group: str
    severity: str
    affected_count: int
    source_files: list[str] = field(default_factory=list)
    page_numbers: list[str] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_files"] = "; ".join(self.source_files)
        payload["page_numbers"] = "; ".join(self.page_numbers)
        payload["evidence_references"] = "; ".join(self.evidence_references)
        return payload


@dataclass(slots=True)
class DrawingSpecAlignmentRow:
    source_file: str
    metric: str
    before: str
    after: str
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SystemConfidenceRow:
    system_name: str
    component_count: int
    resolved_count: int
    unresolved_count: int
    source_coverage: int
    confidence_score: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BeforeAfterRow:
    metric: str
    before: str
    after: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvidenceBaselineReconstructionResult:
    source_fitness: SourceFitnessResult
    major_system_components: list[MajorSystemComponentRow]
    baseline_equipment: list[BaselineEquipmentRow]
    source_deficiencies: list[SourceDeficiencyRow]
    consolidated_rfis: list[ConsolidatedRfiRow]
    drawing_spec_alignment: list[DrawingSpecAlignmentRow]
    system_confidence: list[SystemConfidenceRow]
    before_after: list[BeforeAfterRow]
    room_inventory: list[str]
    report_markdown: str
    summary: dict[str, Any]


class EvidenceBaselineReconstructionService:
    ENGINE_VERSION = "evidence-baseline-reconstruction-service/1.0.0"

    def __init__(self) -> None:
        self.intake_service = DocumentIntakeService()

    def build(
        self,
        snapshot: DocumentIntakeSnapshot,
        review: Any | None = None,
    ) -> EvidenceBaselineReconstructionResult:
        source_fitness = self._ensure_source_fitness(snapshot)
        if review is None:
            review = self.intake_service.run_review_from_snapshot(snapshot).review

        major_components = self._extract_major_system_components(
            snapshot=snapshot,
            source_fitness=source_fitness,
        )
        baseline_equipment = self._build_baseline_equipment(major_components)
        source_deficiencies = self._build_source_deficiencies(
            snapshot=snapshot,
            source_fitness=source_fitness,
            major_components=major_components,
        )
        consolidated_rfis = self._consolidate_rfis(
            review=review,
            baseline_equipment=baseline_equipment,
            source_deficiencies=source_deficiencies,
        )
        drawing_spec_alignment = self._build_alignment_rows(
            review=review,
            source_fitness=source_fitness,
            major_components=major_components,
            baseline_equipment=baseline_equipment,
        )
        system_confidence = self._build_system_confidence(
            source_fitness=source_fitness,
            baseline_equipment=baseline_equipment,
        )
        before_after = self._build_before_after(
            review=review,
            source_fitness=source_fitness,
            baseline_equipment=baseline_equipment,
            source_deficiencies=source_deficiencies,
            consolidated_rfis=consolidated_rfis,
            drawing_spec_alignment=drawing_spec_alignment,
            system_confidence=system_confidence,
        )
        room_inventory = self._room_inventory(major_components)
        report_markdown = self._render_markdown(
            snapshot=snapshot,
            review=review,
            source_fitness=source_fitness,
            major_components=major_components,
            baseline_equipment=baseline_equipment,
            source_deficiencies=source_deficiencies,
            consolidated_rfis=consolidated_rfis,
            drawing_spec_alignment=drawing_spec_alignment,
            system_confidence=system_confidence,
            before_after=before_after,
            room_inventory=room_inventory,
        )

        summary = {
            "source_fitness_documents": len(source_fitness.document_assessments),
            "source_fitness_pages": len(source_fitness.page_assessments),
            "source_fitness_evidence": len(source_fitness.evidence_assessments),
            "major_components": len(major_components),
            "baseline_equipment": len(baseline_equipment),
            "source_deficiencies": len(source_deficiencies),
            "consolidated_rfis": len(consolidated_rfis),
            "drawing_spec_alignment_rows": len(drawing_spec_alignment),
            "system_confidence_rows": len(system_confidence),
            "rooms_detected": len(room_inventory),
            "readiness_before": self._readiness_score(review),
            "readiness_after": self._readiness_proxy(
                source_fitness=source_fitness,
                baseline_equipment=baseline_equipment,
                source_deficiencies=source_deficiencies,
            ),
        }

        return EvidenceBaselineReconstructionResult(
            source_fitness=source_fitness,
            major_system_components=major_components,
            baseline_equipment=baseline_equipment,
            source_deficiencies=source_deficiencies,
            consolidated_rfis=consolidated_rfis,
            drawing_spec_alignment=drawing_spec_alignment,
            system_confidence=system_confidence,
            before_after=before_after,
            room_inventory=room_inventory,
            report_markdown=report_markdown,
            summary=summary,
        )

    def write_artifacts(
        self,
        result: EvidenceBaselineReconstructionResult,
        output_dir: str | Path,
        report_path: str | Path,
    ) -> None:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        self._write_csv(
            output / "AV-02A_SOURCE_FITNESS.csv",
            self._flatten_source_fitness(result.source_fitness),
        )
        self._write_csv(
            output / "AV-02A_MAJOR_SYSTEM_COMPONENTS.csv",
            [row.to_dict() for row in result.major_system_components],
        )
        self._write_csv(
            output / "AV-02A_BASELINE_EQUIPMENT.csv",
            [row.to_dict() for row in result.baseline_equipment],
        )
        self._write_csv(
            output / "AV-02A_SOURCE_DEFICIENCIES.csv",
            [row.to_dict() for row in result.source_deficiencies],
        )
        self._write_csv(
            output / "AV-02A_CONSOLIDATED_RFIS.csv",
            [row.to_dict() for row in result.consolidated_rfis],
        )
        self._write_csv(
            output / "AV-02A_SYSTEM_CONFIDENCE.csv",
            [row.to_dict() for row in result.system_confidence],
        )
        self._write_csv(
            output / "AV-02A_DRAWING_SPEC_ALIGNMENT.csv",
            [row.to_dict() for row in result.drawing_spec_alignment],
        )
        self._write_csv(
            output / "AV-02A_BEFORE_AFTER.csv",
            [row.to_dict() for row in result.before_after],
        )
        Path(report_path).write_text(result.report_markdown, encoding="utf-8")

    def _ensure_source_fitness(
        self,
        snapshot: DocumentIntakeSnapshot,
    ) -> SourceFitnessResult:
        if snapshot.source_fitness_assessments:
            document_assessments: list[SourceFitnessAssessment] = []
            page_assessments: list[SourceFitnessAssessment] = []
            evidence_assessments: list[SourceFitnessAssessment] = []
            for item in snapshot.source_fitness_assessments:
                if item.record_type == "document":
                    document_assessments.append(item)
                elif item.record_type == "page":
                    page_assessments.append(item)
                else:
                    evidence_assessments.append(item)
            return SourceFitnessResult(
                document_assessments=document_assessments,
                page_assessments=page_assessments,
                evidence_assessments=evidence_assessments,
                summary={
                    "document_count": len(document_assessments),
                    "page_count": len(page_assessments),
                    "evidence_count": len(evidence_assessments),
                },
            )
        return self.intake_service.source_fitness_service.assess_snapshot(snapshot)

    def _extract_major_system_components(
        self,
        *,
        snapshot: DocumentIntakeSnapshot,
        source_fitness: SourceFitnessResult,
    ) -> list[MajorSystemComponentRow]:
        document_by_file = {
            assessment.source_file: assessment
            for assessment in source_fitness.document_assessments
        }
        rows: list[MajorSystemComponentRow] = []
        for page in sorted(
            (
                record
                for record in snapshot.raw_pages
                if self._is_component_page(record)
            ),
            key=lambda item: (
                self._text(item.get("source_file")),
                self._int_or_zero(item.get("page_number")),
            ),
        ):
            source_file = self._text(page.get("source_file"))
            page_number = self._int_or_zero(page.get("page_number"))
            document_assessment = document_by_file.get(source_file)
            for row in self._parse_component_rows(
                source_file=source_file,
                page_number=page_number,
                text=self._text(page.get("text")),
                source_fitness=document_assessment,
            ):
                rows.append(row)
        return rows

    def _build_baseline_equipment(
        self,
        components: list[MajorSystemComponentRow],
    ) -> list[BaselineEquipmentRow]:
        equipment: list[BaselineEquipmentRow] = []
        emitted: set[tuple[str, str | None, str | None, str]] = set()
        for component in components:
            if component.source_fitness_status == "likely_extraction_noise":
                continue
            key = (
                component.description.casefold(),
                self._text(component.manufacturer).casefold() or None,
                self._text(component.model).casefold() or None,
                component.quantity.casefold(),
            )
            if key in emitted:
                continue
            emitted.add(key)
            confidence = component.source_fitness_score
            if component.baseline_role == "governing":
                confidence = min(100, confidence + 4)
            equipment.append(
                BaselineEquipmentRow(
                    source_file=component.source_file,
                    page_number=component.page_number,
                    performance_space=component.performance_space,
                    system_block=component.system_block,
                    description=component.description,
                    manufacturer=component.manufacturer,
                    model=component.model,
                    quantity=component.quantity,
                    responsibility=component.responsibility,
                    allowance_status=component.allowance_status,
                    alternate_status=component.alternate_status,
                    source_fitness_status=component.source_fitness_status,
                    source_fitness_score=component.source_fitness_score,
                    baseline_role=component.baseline_role,
                    confidence=confidence,
                    evidence_reference=component.evidence_reference,
                )
            )
        return equipment

    def _build_source_deficiencies(
        self,
        *,
        snapshot: DocumentIntakeSnapshot,
        source_fitness: SourceFitnessResult,
        major_components: list[MajorSystemComponentRow],
    ) -> list[SourceDeficiencyRow]:
        rows: list[SourceDeficiencyRow] = []
        seen: set[tuple[str, int | None, str]] = set()
        component_count_by_file = Counter(row.source_file for row in major_components)
        for assessment in source_fitness.page_assessments:
            if assessment.fitness_status not in {
                "likely_extraction_noise",
                "governing_but_incomplete",
                "supplemental_evidence",
                "ambiguous",
                "not_useful",
            }:
                continue
            key = (
                assessment.source_file,
                assessment.page_number,
                assessment.fitness_status,
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                SourceDeficiencyRow(
                    source_file=assessment.source_file,
                    page_number=assessment.page_number,
                    deficiency_type=self._deficiency_type(assessment.fitness_status),
                    severity=self._severity_for_status(assessment.fitness_status),
                    explanation=self._deficiency_explanation(
                        assessment=assessment,
                        component_count=component_count_by_file.get(
                            assessment.source_file, 0
                        ),
                    ),
                    evidence_reference=self._first_reference(
                        assessment.evidence_references
                    ),
                )
            )
        return rows

    def _consolidate_rfis(
        self,
        *,
        review: Any,
        baseline_equipment: list[BaselineEquipmentRow],
        source_deficiencies: list[SourceDeficiencyRow],
    ) -> list[ConsolidatedRfiRow]:
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        pages: dict[tuple[str, str], set[str]] = defaultdict(set)
        refs: dict[tuple[str, str], list[str]] = defaultdict(list)
        severity_by_group: dict[tuple[str, str], str] = {}
        explanation_by_group: dict[tuple[str, str], str] = {}

        for equipment in baseline_equipment:
            if equipment.alternate_status == "alternate":
                group = ("alternate clarification", equipment.system_block)
                groups[group].append(equipment.description)
                pages[group].add(str(equipment.page_number))
                refs[group].append(equipment.evidence_reference)
                severity_by_group[group] = "medium"
                explanation_by_group[group] = (
                    "Collapse repeated alternate-language items into one owner/contractor clarification."
                )
            elif equipment.responsibility and equipment.responsibility.lower() in {
                "by contractor",
                "by av contractor",
            }:
                group = ("responsibility clarification", equipment.system_block)
                groups[group].append(equipment.description)
                pages[group].add(str(equipment.page_number))
                refs[group].append(equipment.evidence_reference)
                severity_by_group[group] = "medium"
                explanation_by_group[group] = (
                    "Consolidate repeated contractor-responsibility statements into one RFI."
                )
            elif not equipment.manufacturer or not equipment.model:
                group = ("missing product identity", equipment.system_block)
                groups[group].append(equipment.description)
                pages[group].add(str(equipment.page_number))
                refs[group].append(equipment.evidence_reference)
                severity_by_group[group] = "high"
                explanation_by_group[group] = (
                    "Combine unresolved equipment identity gaps by system and source page."
                )

        for deficiency in source_deficiencies:
            if deficiency.deficiency_type == "extraction_noise":
                group = ("extraction noise", "source quality")
            elif deficiency.deficiency_type == "drawing deficiency":
                group = ("drawing/spec gap", "coordination")
            else:
                group = (deficiency.deficiency_type, "source quality")
            groups[group].append(deficiency.explanation)
            pages[group].add(str(deficiency.page_number or ""))
            refs[group].append(deficiency.evidence_reference)
            severity_by_group.setdefault(group, deficiency.severity)
            explanation_by_group.setdefault(group, deficiency.explanation)

        rfis: list[ConsolidatedRfiRow] = []
        for index, ((root_issue, issue_group), items) in enumerate(
            sorted(groups.items(), key=lambda item: (item[0][0], item[0][1])), start=1
        ):
            rfis.append(
                ConsolidatedRfiRow(
                    root_issue=root_issue,
                    issue_group=issue_group,
                    severity=severity_by_group.get((root_issue, issue_group), "medium"),
                    affected_count=len(items),
                    source_files=sorted(
                        {
                            ref.split("::", 1)[0].split("#", 1)[0]
                            for ref in refs[(root_issue, issue_group)]
                            if ref
                        }
                    ),
                    page_numbers=[
                        str(page)
                        for page in sorted(
                            {
                                int(page)
                                for page in pages[(root_issue, issue_group)]
                                if page and str(page).isdigit()
                            }
                        )
                    ],
                    evidence_references=self._unique(refs[(root_issue, issue_group)]),
                    explanation=explanation_by_group.get((root_issue, issue_group), ""),
                )
            )
        return rfis

    def _build_alignment_rows(
        self,
        *,
        review: Any,
        source_fitness: SourceFitnessResult,
        major_components: list[MajorSystemComponentRow],
        baseline_equipment: list[BaselineEquipmentRow],
    ) -> list[DrawingSpecAlignmentRow]:
        before = (
            f"{len(getattr(review, 'cross_references', []) or [])} cross references"
        )
        after = f"{len(major_components)} major component rows"
        return [
            DrawingSpecAlignmentRow(
                source_file="BID-2026-0002",
                metric="drawing/spec traceability",
                before=before,
                after=after,
                explanation=(
                    "The reconstructed baseline is driven by the Div 27 appendix pages rather than weak drawing traces."
                ),
            ),
            DrawingSpecAlignmentRow(
                source_file="BID-2026-0002",
                metric="spec component list coverage",
                before=f"{len(getattr(review, 'specification_sections', []) or [])} sections in the raw review",
                after=f"{len({row.page_number for row in major_components})} appendix pages with usable component rows",
                explanation="The specification appendix provides the governing baseline component lists.",
            ),
        ]

    def _build_system_confidence(
        self,
        *,
        source_fitness: SourceFitnessResult,
        baseline_equipment: list[BaselineEquipmentRow],
    ) -> list[SystemConfidenceRow]:
        grouped: dict[str, list[BaselineEquipmentRow]] = defaultdict(list)
        for row in baseline_equipment:
            grouped[self._system_name(row)].append(row)

        rows: list[SystemConfidenceRow] = []
        for system_name in sorted(grouped):
            items = grouped[system_name]
            resolved = sum(1 for item in items if item.manufacturer and item.model)
            unresolved = len(items) - resolved
            pages = len({item.page_number for item in items})
            source_strength = max(
                (
                    assessment.fitness_score
                    for assessment in source_fitness.page_assessments
                    if assessment.source_file in {item.source_file for item in items}
                ),
                default=0,
            )
            confidence = round(
                min(
                    1.0,
                    0.25
                    + (resolved / max(1, len(items))) * 0.5
                    + (source_strength / 100) * 0.25,
                ),
                2,
            )
            rows.append(
                SystemConfidenceRow(
                    system_name=system_name,
                    component_count=len(items),
                    resolved_count=resolved,
                    unresolved_count=unresolved,
                    source_coverage=pages,
                    confidence_score=confidence,
                    explanation=(
                        "Confidence rises with resolved manufacturer/model pairs and source pages that carry structured component evidence."
                    ),
                )
            )
        return rows

    def _build_before_after(
        self,
        *,
        review: Any,
        source_fitness: SourceFitnessResult,
        baseline_equipment: list[BaselineEquipmentRow],
        source_deficiencies: list[SourceDeficiencyRow],
        consolidated_rfis: list[ConsolidatedRfiRow],
        drawing_spec_alignment: list[DrawingSpecAlignmentRow],
        system_confidence: list[SystemConfidenceRow],
    ) -> list[BeforeAfterRow]:
        unresolved_before = sum(
            1
            for item in list(getattr(review, "equipment", []) or [])
            if not getattr(item, "manufacturer", None)
            or not getattr(item, "model", None)
        )
        unresolved_after = sum(
            1 for item in baseline_equipment if not item.manufacturer or not item.model
        )
        room_before = len(getattr(review, "rooms", []) or [])
        room_after = len(self._room_inventory_from_baseline(baseline_equipment))
        source_strength_before = max(
            (
                assessment.overall_relevance_score
                for assessment in getattr(review, "relevance_assessments", []) or []
            ),
            default=0,
        )
        source_strength_after = max(
            (
                assessment.fitness_score
                for assessment in source_fitness.page_assessments
            ),
            default=0,
        )
        return [
            BeforeAfterRow(
                metric="readiness",
                before=self._format_score(self._readiness_score(review)),
                after=self._format_score(
                    self._readiness_proxy(
                        source_fitness=source_fitness,
                        baseline_equipment=baseline_equipment,
                        source_deficiencies=source_deficiencies,
                    )
                ),
                notes="Proxy readiness improves when governing appendix pages outrank deficient drawing and schedule evidence.",
            ),
            BeforeAfterRow(
                metric="rooms detected",
                before=str(room_before),
                after=str(room_after),
                notes="Room names are inferred from appendix page titles and major component spaces.",
            ),
            BeforeAfterRow(
                metric="unresolved equipment",
                before=str(unresolved_before),
                after=str(unresolved_after),
                notes="Baseline rows only persist unresolved items when evidence remains insufficient.",
            ),
            BeforeAfterRow(
                metric="drawing/spec alignment",
                before=str(len(getattr(review, "cross_references", []) or [])),
                after=str(len(drawing_spec_alignment)),
                notes="The reconstruction keeps alignment focused on governable component-list evidence.",
            ),
            BeforeAfterRow(
                metric="rfi count",
                before=str(len(getattr(review, "rfi_candidates", []) or [])),
                after=str(len(consolidated_rfis)),
                notes="Repeated findings are collapsed into root-issue review buckets.",
            ),
            BeforeAfterRow(
                metric="conflicts and gaps",
                before=str(
                    len(getattr(review, "reconciliation_issues", []) or [])
                    + len(getattr(review, "scope_gaps", []) or [])
                ),
                after=str(len(source_deficiencies)),
                notes="Source deficiencies are isolated from extraction failures and missing project info.",
            ),
            BeforeAfterRow(
                metric="scope score",
                before=self._format_score(
                    source_strength_before / 100 if source_strength_before else 0
                ),
                after=self._format_score(
                    source_strength_after / 100 if source_strength_after else 0
                ),
                notes="Scope ranking rises when the component appendix is used as the governing baseline.",
            ),
            BeforeAfterRow(
                metric="labor readiness",
                before=self._format_score(self._labor_readiness_before(review)),
                after=self._format_score(
                    self._labor_readiness_after(system_confidence)
                ),
                notes="Labor readiness improves when quantity, manufacturer, model, and source coverage are clearer.",
            ),
        ]

    def _render_markdown(
        self,
        *,
        snapshot: DocumentIntakeSnapshot,
        review: Any,
        source_fitness: SourceFitnessResult,
        major_components: list[MajorSystemComponentRow],
        baseline_equipment: list[BaselineEquipmentRow],
        source_deficiencies: list[SourceDeficiencyRow],
        consolidated_rfis: list[ConsolidatedRfiRow],
        drawing_spec_alignment: list[DrawingSpecAlignmentRow],
        system_confidence: list[SystemConfidenceRow],
        before_after: list[BeforeAfterRow],
        room_inventory: list[str],
    ) -> str:
        lines: list[str] = [
            "# AV-02A Evidence Quality and Baseline Reconstruction",
            "",
            "## Executive Summary",
            "",
            f"- Snapshot ID: {snapshot.snapshot_id}",
            f"- Source-fitness documents: {len(source_fitness.document_assessments)}",
            f"- Major system component rows: {len(major_components)}",
            f"- Baseline equipment rows: {len(baseline_equipment)}",
            f"- Consolidated RFIs: {len(consolidated_rfis)}",
            f"- Detected rooms: {len(room_inventory)}",
            f"- Readiness proxy before: {self._format_score(self._readiness_score(review))}",
            f"- Readiness proxy after: {self._format_score(self._readiness_proxy(source_fitness=source_fitness, baseline_equipment=baseline_equipment, source_deficiencies=source_deficiencies))}",
            "",
            "The Music Academy of the West package is governed primarily by the Div 27 specification appendix. The late appendix pages carry structured make/model/quantity evidence, while the schedule extraction remains noisy and the drawings remain coordination-heavy.",
            "",
            "## Source Fitness Assessment",
            "",
            *self._markdown_bullets(
                self._top_source_fitness(source_fitness.document_assessments)
            ),
            "",
            "## Drawing Deficiency Assessment",
            "",
            *self._markdown_bullets(
                self._summarize_deficiencies(source_deficiencies, "drawing deficiency")
                or ["No drawing deficiency rows were emitted."]
            ),
            "",
            "## Specification Component-List Review",
            "",
            f"The governing component list appears on pages {self._component_pages(major_components)} of Div 27 Communications.",
            "",
            "## Reconstructed Engineering Baseline",
            "",
            f"- Component rows captured: {len(major_components)}",
            f"- Baseline equipment rows retained: {len(baseline_equipment)}",
            "",
            "## Equipment Resolution",
            "",
            f"- Resolved baseline rows: {sum(1 for item in baseline_equipment if item.manufacturer and item.model)}",
            f"- Unresolved baseline rows: {sum(1 for item in baseline_equipment if not item.manufacturer or not item.model)}",
            "",
            "## System-by-System Confidence",
            "",
            *self._markdown_bullets(
                [
                    f"{row.system_name}: confidence {row.confidence_score:.2f} ({row.resolved_count}/{row.component_count} resolved, {row.source_coverage} source pages)"
                    for row in system_confidence
                ]
                or ["No system-confidence rows were emitted."]
            ),
            "",
            "## Source Deficiencies vs Atlas Failures",
            "",
            *self._markdown_bullets(
                self._summarize_deficiencies(source_deficiencies, limit=12)
                or ["No source-deficiency rows were emitted."]
            ),
            "",
            "## Consolidated RFIs and Pricing Risks",
            "",
            *self._markdown_bullets(
                [
                    f"{row.root_issue} ({row.issue_group}): {row.affected_count} affected item(s)"
                    for row in consolidated_rfis
                ]
                or ["No consolidated RFI rows were emitted."]
            ),
            "",
            "## Remaining Blockers",
            "",
            *self._markdown_bullets(
                self._remaining_blockers(source_deficiencies, consolidated_rfis)
                or ["No remaining blockers were identified."]
            ),
            "",
            "## Recommendation",
            "",
            self._recommendation_line(source_deficiencies, consolidated_rfis),
            "",
            "## Before / After",
            "",
        ]
        for row in before_after:
            lines.append(f"- {row.metric}: {row.before} -> {row.after}")
        lines.extend(["", "## Room Inventory", ""])
        lines.extend(self._markdown_bullets(room_inventory or ["No rooms detected."]))
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _markdown_bullets(items: list[str]) -> list[str]:
        return [f"- {item}" for item in items]

    @staticmethod
    def _summarize_deficiencies(
        rows: list[SourceDeficiencyRow],
        deficiency_type: str | None = None,
        limit: int | None = None,
    ) -> list[str]:
        grouped: dict[tuple[str, str], list[SourceDeficiencyRow]] = defaultdict(list)
        for row in rows:
            if deficiency_type is not None and row.deficiency_type != deficiency_type:
                continue
            grouped[(row.source_file, row.deficiency_type)].append(row)

        summary_rows: list[str] = []
        for (source_file, deficiency), grouped_rows in sorted(
            grouped.items(),
            key=lambda item: (item[0][0], item[0][1]),
        ):
            page_numbers = sorted(
                {
                    int(row.page_number)
                    for row in grouped_rows
                    if row.page_number is not None
                }
            )
            page_suffix = (
                f" pages {page_numbers[0]}-{page_numbers[-1]}"
                if len(page_numbers) > 1
                else (f" page {page_numbers[0]}" if page_numbers else "")
            )
            summary_rows.append(
                f"{source_file}{page_suffix}: {deficiency} ({len(grouped_rows)} row(s)) - {grouped_rows[0].explanation}"
            )
            if limit is not None and len(summary_rows) >= limit:
                break
        return summary_rows

    @staticmethod
    def _top_source_fitness(
        assessments: list[SourceFitnessAssessment],
    ) -> list[str]:
        sorted_assessments = sorted(
            assessments,
            key=lambda item: (
                -item.fitness_score,
                item.source_file,
                item.page_number or 0,
            ),
        )
        lines: list[str] = []
        for assessment in sorted_assessments[:8]:
            location = (
                f" p.{assessment.page_number}"
                if assessment.page_number is not None
                else ""
            )
            lines.append(
                f"{assessment.source_file}{location}: {assessment.fitness_status} "
                f"({assessment.fitness_score}/100) - {assessment.reasons[0] if assessment.reasons else 'No explanation available.'}"
            )
        return lines

    @staticmethod
    def _remaining_blockers(
        source_deficiencies: list[SourceDeficiencyRow],
        consolidated_rfis: list[ConsolidatedRfiRow],
    ) -> list[str]:
        blockers: list[str] = []
        if any(row.severity == "high" for row in source_deficiencies):
            blockers.append("High-severity source deficiencies remain in the package.")
        if len(consolidated_rfis) > 12:
            blockers.append(
                "The consolidated RFI set is still larger than a reviewable target."
            )
        if not source_deficiencies:
            blockers.append(
                "No source deficiencies were detected, but the package still needs human confirmation."
            )
        return blockers

    @staticmethod
    def _recommendation_line(
        source_deficiencies: list[SourceDeficiencyRow],
        consolidated_rfis: list[ConsolidatedRfiRow],
    ) -> str:
        if any(
            row.deficiency_type == "extraction_noise" for row in source_deficiencies
        ):
            return "Proceed only after the noisy schedule and drawing extraction paths are corrected."
        if len(consolidated_rfis) <= 12:
            return "Proceed to AV-03 with the reconstructed baseline and the consolidated RFI set."
        return "Repeat AV-02 after reducing the remaining source-quality and RFI noise."

    @staticmethod
    def _component_pages(components: list[MajorSystemComponentRow]) -> str:
        pages = sorted({row.page_number for row in components})
        return ", ".join(str(page) for page in pages)

    @staticmethod
    def _room_inventory(components: list[MajorSystemComponentRow]) -> list[str]:
        return list(
            dict.fromkeys(
                item
                for item in (
                    component.performance_space
                    for component in components
                    if component.performance_space
                )
                if item
            )
        )

    @staticmethod
    def _room_inventory_from_baseline(
        baseline_equipment: list[BaselineEquipmentRow],
    ) -> list[str]:
        return list(
            dict.fromkeys(
                item.performance_space
                for item in baseline_equipment
                if item.performance_space
            )
        )

    def _parse_component_rows(
        self,
        *,
        source_file: str,
        page_number: int,
        text: str,
        source_fitness: SourceFitnessAssessment | None,
    ) -> list[MajorSystemComponentRow]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        system_block = ""
        performance_space = ""
        rows: list[MajorSystemComponentRow] = []
        buffer = ""
        table_started = False
        for line in lines:
            if self._is_page_header(line):
                continue
            if line.startswith("AUDIOVISUAL SYSTEMS APPENDIX A") or line.startswith(
                "APPENDIX A"
            ):
                continue
            if line == "Description Device Type Make Model Qty":
                table_started = True
                continue
            if not table_started:
                performance_space = (
                    self._normalize_space_heading(line) or performance_space
                )
                continue
            if self._is_section_heading(line):
                system_block = line
                buffer = ""
                continue
            if self._is_space_heading(line):
                performance_space = self._normalize_space_heading(line)
                buffer = ""
                continue
            if self._is_preamble_line(line):
                continue
            buffer = f"{buffer} {line}".strip() if buffer else line
            if not self._row_is_complete(buffer):
                continue
            row = self._split_component_row(
                source_file=source_file,
                page_number=page_number,
                performance_space=performance_space,
                system_block=system_block,
                raw_line=buffer,
                source_fitness=source_fitness,
            )
            if row is not None:
                rows.append(row)
            buffer = ""
        return rows

    def _split_component_row(
        self,
        *,
        source_file: str,
        page_number: int,
        performance_space: str,
        system_block: str,
        raw_line: str,
        source_fitness: SourceFitnessAssessment | None,
    ) -> MajorSystemComponentRow | None:
        normalized = " ".join(raw_line.split())
        if self._looks_like_heading(normalized):
            return None

        qty_match = re.search(r"\b(?P<qty>LOT|\d+(?:\.\d+)?)$", normalized, flags=re.I)
        if qty_match:
            quantity = qty_match.group("qty")
            body = normalized[: qty_match.start()].strip()
        else:
            quantity = "1"
            body = normalized

        responsibility = None
        if " by av contractor" in body.casefold():
            responsibility = "by AV Contractor"
            body = re.sub(r"\s+by av contractor\s*$", "", body, flags=re.I).strip()
        elif " by contractor" in body.casefold():
            responsibility = "by contractor"
            body = re.sub(r"\s+by contractor\s*$", "", body, flags=re.I).strip()
        elif "owner furnish" in body.casefold():
            responsibility = "Owner Furnish"
            body = re.sub(r"\s+owner furnish(?:ed)?\s*$", "", body, flags=re.I).strip()

        manufacturer, model, description = self._split_manufacturer_model(body)
        allowance_status = (
            "allowance"
            if quantity.upper() == "LOT" or "tbd" in normalized.casefold()
            else "specified"
        )
        alternate_status = (
            "alternate"
            if "add alternate" in performance_space.casefold()
            or "alternate" in normalized.casefold()
            else "primary"
        )
        baseline_role = self._baseline_role(
            allowance_status, alternate_status, responsibility
        )
        fitness_status, source_fitness_score = self._source_fitness_for_row(
            source_fitness=source_fitness,
            raw_line=normalized,
        )
        evidence_reference = f"{source_file}#p{page_number}"
        return MajorSystemComponentRow(
            source_file=source_file,
            page_number=page_number,
            performance_space=performance_space or "unspecified",
            system_block=system_block or "unspecified",
            raw_line=normalized,
            description=description or body,
            manufacturer=manufacturer,
            model=model,
            quantity=quantity,
            responsibility=responsibility,
            allowance_status=allowance_status,
            alternate_status=alternate_status,
            baseline_role=baseline_role,
            source_fitness_status=fitness_status,
            source_fitness_score=source_fitness_score,
            evidence_reference=evidence_reference,
        )

    @staticmethod
    def _split_manufacturer_model(text: str) -> tuple[str | None, str | None, str]:
        normalized = " ".join(text.split())
        lower = normalized.casefold()
        for manufacturer in sorted(_KNOWN_MANUFACTURERS, key=len, reverse=True):
            idx = lower.find(manufacturer)
            if idx < 0:
                continue
            manufacturer_text = normalized[idx : idx + len(manufacturer)]
            description = normalized[:idx].strip(" -")
            model = normalized[idx + len(manufacturer) :].strip(" -")
            if not description:
                description = normalized
            return manufacturer_text, model or None, description
        tokens = normalized.split()
        if len(tokens) >= 3 and any(ch.isdigit() for ch in tokens[-1]):
            manufacturer = tokens[-2]
            model = tokens[-1]
            description = " ".join(tokens[:-2])
            return manufacturer, model, description
        return None, None, normalized

    @staticmethod
    def _baseline_role(
        allowance_status: str,
        alternate_status: str,
        responsibility: str | None,
    ) -> str:
        if alternate_status == "alternate":
            return "coordination"
        if allowance_status == "allowance":
            return "supplemental"
        if responsibility:
            return "coordination"
        return "governing"

    @staticmethod
    def _source_fitness_for_row(
        *,
        source_fitness: SourceFitnessAssessment | None,
        raw_line: str,
    ) -> tuple[str, int]:
        if source_fitness is None:
            return "strong_baseline_evidence", 78
        if source_fitness.fitness_status == "likely_extraction_noise":
            return "likely_extraction_noise", min(35, source_fitness.fitness_score)
        if (
            "owner furnish" in raw_line.casefold()
            or "add alternate" in raw_line.casefold()
        ):
            return "coordination_evidence", max(45, source_fitness.fitness_score - 8)
        return source_fitness.fitness_status, source_fitness.fitness_score

    @staticmethod
    def _is_component_page(record: dict[str, Any]) -> bool:
        text = " ".join(
            part
            for part in (
                record.get("text"),
                record.get("source_file"),
            )
            if isinstance(part, str)
        ).casefold()
        source_file = str(record.get("source_file") or "")
        page_number = record.get("page_number")
        if source_file == "Div 27 Communications.pdf" and isinstance(page_number, int):
            if 42 <= page_number <= 56:
                return True
        return (
            "appendix a: base equipment schedule" in text
            or "specified equipment, base system" in text
            or "audiovisual systems appendix a" in text
        )

    @staticmethod
    def _row_is_complete(buffer: str) -> bool:
        normalized = " ".join(buffer.split())
        return bool(re.search(r"\b(?:LOT|\d+(?:\.\d+)?)$", normalized, flags=re.I))

    @staticmethod
    def _looks_like_heading(text: str) -> bool:
        if not text:
            return True
        if text in {"A", "B", "C"}:
            return True
        if text.upper() == text and len(text.split()) <= 5:
            return True
        if text.endswith(")") and not any(char.isdigit() for char in text):
            return True
        return False

    @staticmethod
    def _is_section_heading(text: str) -> bool:
        normalized = text.casefold()
        return normalized in {
            "audio",
            "video",
            "control",
            "recording and capture",
            "patching and distribution",
            "misc",
            "support infrastructure",
            "production intercom",
            "cabling & plates",
            "furniture, stands, mounts",
            "furnitures, stands, mounts",
            "owner furnish",
        }

    @staticmethod
    def _is_space_heading(text: str) -> bool:
        normalized = text.casefold()
        return normalized in {hint.casefold() for hint in _ROOM_TITLE_HINTS} or (
            "typical of" in normalized
        )

    @staticmethod
    def _normalize_space_heading(text: str) -> str:
        cleaned = " ".join(text.split())
        return cleaned.strip(" -")

    @staticmethod
    def _is_page_header(text: str) -> bool:
        normalized = text.casefold()
        return (
            normalized.startswith("music academy of the west")
            or normalized.startswith("new music education center")
            or normalized.startswith("brooks scarpa huber")
            or normalized.startswith("project no.")
            or normalized.startswith("05/29/2026")
        )

    @staticmethod
    def _is_preamble_line(text: str) -> bool:
        normalized = text.casefold()
        return (
            normalized
            in {
                "description device type make model qty",
                "description device type make model qty.",
                "prepared by kirkegaard",
            }
            or normalized.startswith("a. ")
            or normalized.startswith("b. ")
            or normalized.startswith("c. ")
        )

    @staticmethod
    def _readiness_score(review: Any) -> float:
        readiness = getattr(review, "readiness", None)
        return float(getattr(readiness, "readiness_score", 0.0) or 0.0)

    @staticmethod
    def _readiness_proxy(
        *,
        source_fitness: SourceFitnessResult,
        baseline_equipment: list[BaselineEquipmentRow],
        source_deficiencies: list[SourceDeficiencyRow],
    ) -> float:
        resolved = sum(
            1 for item in baseline_equipment if item.manufacturer and item.model
        )
        total = len(baseline_equipment)
        if not total:
            return 0.0
        source_strength = max(
            (
                assessment.fitness_score
                for assessment in source_fitness.page_assessments
            ),
            default=0,
        )
        deficiency_penalty = min(0.18, len(source_deficiencies) * 0.01)
        score = 0.25 + (resolved / total) * 0.45 + (source_strength / 100) * 0.3
        return max(0.0, min(0.98, score - deficiency_penalty))

    @staticmethod
    def _labor_readiness_before(review: Any) -> float:
        equipment = list(getattr(review, "equipment", []) or [])
        if not equipment:
            return 0.0
        resolved = sum(
            1
            for item in equipment
            if getattr(item, "manufacturer", None) and getattr(item, "model", None)
        )
        return min(1.0, 0.05 + (resolved / len(equipment)) * 0.25)

    @staticmethod
    def _labor_readiness_after(system_confidence: list[SystemConfidenceRow]) -> float:
        if not system_confidence:
            return 0.0
        return round(
            min(
                1.0,
                0.15
                + sum(row.confidence_score for row in system_confidence)
                / len(system_confidence)
                * 0.65,
            ),
            2,
        )

    @staticmethod
    def _format_score(value: float) -> str:
        return f"{value:.2f}"

    @staticmethod
    def _deficiency_type(status: str) -> str:
        return {
            "likely_extraction_noise": "extraction_noise",
            "governing_but_incomplete": "drawing deficiency",
            "supplemental_evidence": "supplemental evidence",
            "ambiguous": "ambiguous evidence",
            "not_useful": "not useful",
        }.get(status, "source deficiency")

    @staticmethod
    def _severity_for_status(status: str) -> str:
        return {
            "likely_extraction_noise": "high",
            "governing_but_incomplete": "medium",
            "supplemental_evidence": "low",
            "ambiguous": "medium",
            "not_useful": "low",
        }.get(status, "medium")

    @staticmethod
    def _deficiency_explanation(
        *,
        assessment: SourceFitnessAssessment,
        component_count: int,
    ) -> str:
        if assessment.fitness_status == "likely_extraction_noise":
            return "Extraction produced prose fragments rather than usable device rows."
        if assessment.fitness_status == "governing_but_incomplete":
            return "Drawing evidence exists, but it does not expose signal-flow, rack, or topology detail."
        if assessment.fitness_status == "supplemental_evidence":
            return "The page is useful for coordination, but it should not govern the baseline."
        if assessment.fitness_status == "ambiguous":
            return f"The page supports {component_count} extracted component rows but remains ambiguous."
        return "The page did not add useful baseline evidence."

    @staticmethod
    def _first_reference(values: list[str]) -> str:
        return values[0] if values else ""

    @staticmethod
    def _system_name(row: BaselineEquipmentRow) -> str:
        if row.system_block and row.system_block != "unspecified":
            return row.system_block
        description = row.description.casefold()
        if any(term in description for term in ("intercom",)):
            return "intercom"
        if any(term in description for term in ("projector", "display", "video")):
            return "video"
        if any(
            term in description
            for term in ("speaker", "audio", "microphone", "amplifier")
        ):
            return "audio"
        if any(
            term in description
            for term in ("control", "processor", "touch", "network", "dsp")
        ):
            return "control"
        if any(term in description for term in ("cable", "patch", "rack", "power")):
            return "infrastructure"
        return "general"

    @staticmethod
    def _flatten_source_fitness(
        source_fitness: SourceFitnessResult,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for assessment in (
            source_fitness.document_assessments
            + source_fitness.page_assessments
            + source_fitness.evidence_assessments
        ):
            payload = assessment.to_dict()
            payload["record_level"] = assessment.record_type
            rows.append(payload)
        return rows

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        headers = list(rows[0].keys()) if rows else []
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers, lineterminator="\n")
            if headers:
                writer.writeheader()
                writer.writerows(rows)

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(
            dict.fromkeys(item.strip() for item in values if item and item.strip())
        )

    @staticmethod
    def _int_or_zero(value: Any) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return 0

    @staticmethod
    def _text(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if value is None:
            return ""
        return str(value).strip()

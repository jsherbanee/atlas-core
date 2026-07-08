"""Deterministic Atlas coordination intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_core.domain.bid_package_review import BidPackageReview

from atlas_core.services.coordination_intelligence.models import (
    CoordinationCategory,
    CoordinationConfidence,
    CoordinationEvidence,
    CoordinationFinding,
    CoordinationIntelligenceResult,
    CoordinationIssue,
    CoordinationSeverity,
    CoordinationSummary,
    aggregate_confidence,
)


@dataclass
class CoordinationIntelligenceEngine:
    """Build deterministic coordination findings across drawings/specs/equipment/systems."""

    engine_version: str = "coordination-intelligence/1.0.0"

    def build(
        self,
        review: BidPackageReview,
        drawings: list[dict[str, Any]] | None = None,
        specifications: list[dict[str, Any]] | None = None,
        equipment: list[dict[str, Any]] | None = None,
        systems: list[dict[str, Any]] | None = None,
        rfis: list[dict[str, Any]] | None = None,
        assumptions: list[dict[str, Any]] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> CoordinationIntelligenceResult:
        drawings = list(drawings or [])
        specifications = list(specifications or [])
        equipment = list(equipment or [])
        systems = list(systems or [])
        rfis = list(rfis or [])
        assumptions = list(assumptions or [])
        evidence = list(evidence or [])

        findings: list[CoordinationFinding] = []

        drawing_ids = {
            self._safe_text(item.get("drawing_number"), "").strip()
            for item in drawings
            if self._safe_text(item.get("drawing_number"), "").strip()
        }
        spec_ids = {
            self._safe_text(item.get("section"), "").strip()
            for item in specifications
            if self._safe_text(item.get("section"), "").strip()
        }
        equipment_ids = {
            self._safe_text(item.get("equipment_id"), "").strip()
            for item in equipment
            if self._safe_text(item.get("equipment_id"), "").strip()
        }
        system_ids = {
            self._safe_text(item.get("system"), "").strip()
            for item in systems
            if self._safe_text(item.get("system"), "").strip()
        }

        for drawing in drawings:
            drawing_id = self._safe_text(drawing.get("drawing_number"), "")
            if not drawing_id:
                continue
            drawing_specs = {
                self._safe_text(item, "").strip()
                for item in list(drawing.get("referenced_specifications") or [])
                if self._safe_text(item, "").strip()
            }
            missing_specs = sorted(
                item for item in drawing_specs if item not in spec_ids
            )
            if missing_specs:
                findings.append(
                    self._finding(
                        finding_id=f"coord-drawing-missing-spec:{drawing_id}",
                        category=CoordinationCategory.DRAWING_SPECIFICATION_ALIGNMENT,
                        severity=CoordinationSeverity.HIGH,
                        confidence=CoordinationConfidence.HIGH,
                        title=f"Drawing {drawing_id} references missing specification sections",
                        description=(
                            f"Drawing {drawing_id} references specification sections that are not available "
                            "in the indexed package."
                        ),
                        recommended_action="Verify section references and add missing specification files to intake.",
                        related_objects=[f"drawing:{drawing_id}"]
                        + [f"spec:{item}" for item in missing_specs[:5]],
                        evidence=[
                            CoordinationEvidence(
                                source_ref=f"drawing:{drawing_id}",
                                object_id=f"spec:{item}",
                                confidence=0.9,
                                excerpt="drawing to spec cross-reference",
                            )
                            for item in missing_specs[:3]
                        ],
                    )
                )

            if drawing_specs and not missing_specs:
                findings.append(
                    self._finding(
                        finding_id=f"coord-drawing-spec-agreement:{drawing_id}",
                        category=CoordinationCategory.DRAWING_SPECIFICATION_ALIGNMENT,
                        severity=CoordinationSeverity.LOW,
                        confidence=CoordinationConfidence.HIGH,
                        title=f"Drawing {drawing_id} aligns with indexed specification references",
                        description=(
                            f"Drawing {drawing_id} references sections that are present in the current "
                            "specification index."
                        ),
                        recommended_action="Maintain current drawing/spec linkage during revision updates.",
                        related_objects=[f"drawing:{drawing_id}"]
                        + [f"spec:{item}" for item in sorted(drawing_specs)[:4]],
                    )
                )

        for spec in specifications:
            section = self._safe_text(spec.get("section"), "")
            if not section:
                continue

            referenced_drawings = {
                self._safe_text(item, "").strip()
                for item in list(spec.get("referenced_drawings") or [])
                if self._safe_text(item, "").strip()
            }
            missing_drawings = sorted(
                item for item in referenced_drawings if item not in drawing_ids
            )
            if missing_drawings:
                findings.append(
                    self._finding(
                        finding_id=f"coord-spec-missing-drawing:{section}",
                        category=CoordinationCategory.DRAWING_SPECIFICATION_ALIGNMENT,
                        severity=CoordinationSeverity.HIGH,
                        confidence=CoordinationConfidence.MEDIUM,
                        title=f"Specification {section} references missing drawing sheets",
                        description=(
                            f"Specification {section} includes drawing references that are not found "
                            "in the drawing index."
                        ),
                        recommended_action="Confirm sheet references and update drawing package coverage.",
                        related_objects=[f"spec:{section}"]
                        + [f"drawing:{item}" for item in missing_drawings[:5]],
                    )
                )

            requirement_candidates = list(spec.get("requirement_candidates") or [])
            if requirement_candidates and not referenced_drawings:
                findings.append(
                    self._finding(
                        finding_id=f"coord-requirement-no-drawing:{section}",
                        category=CoordinationCategory.REQUIREMENT_CANDIDATE_COVERAGE,
                        severity=CoordinationSeverity.MEDIUM,
                        confidence=CoordinationConfidence.MEDIUM,
                        title=f"Specification {section} has requirement candidates without drawing linkage",
                        description=(
                            f"Section {section} includes deterministic requirement candidates but no linked "
                            "drawing references."
                        ),
                        recommended_action="Map requirement candidates to drawing sheets or create review RFIs.",
                        related_objects=[f"spec:{section}"],
                    )
                )

        for item in equipment:
            equipment_id = self._safe_text(item.get("equipment_id"), "")
            if not equipment_id:
                continue

            drawing_refs = {
                self._safe_text(ref, "").strip()
                for ref in list(item.get("drawing_references") or [])
                if self._safe_text(ref, "").strip()
            }
            spec_refs = {
                self._safe_text(ref, "").strip()
                for ref in list(item.get("specification_references") or [])
                if self._safe_text(ref, "").strip()
            }
            system_id = self._safe_text(item.get("system"), "").strip()

            if drawing_refs and not spec_refs:
                findings.append(
                    self._finding(
                        finding_id=f"coord-equipment-drawing-no-spec:{equipment_id}",
                        category=CoordinationCategory.EQUIPMENT_SPECIFICATION_ALIGNMENT,
                        severity=CoordinationSeverity.HIGH,
                        confidence=CoordinationConfidence.HIGH,
                        title=f"Equipment {equipment_id} appears on drawings without specification linkage",
                        description=(
                            f"Equipment {equipment_id} has drawing references but no specification references."
                        ),
                        recommended_action="Add or confirm governing specification section for this equipment.",
                        related_objects=[f"equipment:{equipment_id}"]
                        + [f"drawing:{ref}" for ref in sorted(drawing_refs)[:4]],
                    )
                )

            missing_spec_refs = sorted(
                item for item in spec_refs if item not in spec_ids
            )
            if missing_spec_refs:
                findings.append(
                    self._finding(
                        finding_id=f"coord-equipment-missing-spec:{equipment_id}",
                        category=CoordinationCategory.EQUIPMENT_SPECIFICATION_ALIGNMENT,
                        severity=CoordinationSeverity.HIGH,
                        confidence=CoordinationConfidence.HIGH,
                        title=f"Equipment {equipment_id} references unavailable specification sections",
                        description=(
                            f"Equipment {equipment_id} links to sections that are not present in current specs."
                        ),
                        recommended_action="Confirm specification references and import missing sections.",
                        related_objects=[f"equipment:{equipment_id}"]
                        + [f"spec:{ref}" for ref in missing_spec_refs[:4]],
                    )
                )

            if system_id and system_ids and system_id not in system_ids:
                findings.append(
                    self._finding(
                        finding_id=f"coord-equipment-missing-system:{equipment_id}",
                        category=CoordinationCategory.SYSTEM_COORDINATION,
                        severity=CoordinationSeverity.MEDIUM,
                        confidence=CoordinationConfidence.MEDIUM,
                        title=f"Equipment {equipment_id} references a system not present in system objects",
                        description=(
                            f"Equipment {equipment_id} references system {system_id}, but no matching "
                            "system object exists in the workspace."
                        ),
                        recommended_action="Create or reconcile the missing system object.",
                        related_objects=[
                            f"equipment:{equipment_id}",
                            f"system:{system_id}",
                        ],
                    )
                )

            if drawing_refs and spec_refs and not missing_spec_refs:
                findings.append(
                    self._finding(
                        finding_id=f"coord-equipment-alignment:{equipment_id}",
                        category=CoordinationCategory.EQUIPMENT_SPECIFICATION_ALIGNMENT,
                        severity=CoordinationSeverity.LOW,
                        confidence=CoordinationConfidence.HIGH,
                        title=f"Equipment {equipment_id} has coordinated drawing and spec references",
                        description=(
                            f"Equipment {equipment_id} is linked to both drawing and specification objects."
                        ),
                        recommended_action="Preserve current object linkage during package revisions.",
                        related_objects=[f"equipment:{equipment_id}"],
                    )
                )

        for rfi in rfis:
            rfi_id = self._safe_text(
                rfi.get("rfi_id"), self._safe_text(rfi.get("title"), "rfi")
            )
            if not rfi_id:
                continue
            rfi_blob = str(rfi)
            linked_objects: list[str] = []
            for drawing_id in sorted(drawing_ids):
                if drawing_id and drawing_id in rfi_blob:
                    linked_objects.append(f"drawing:{drawing_id}")
            for section in sorted(spec_ids):
                if section and section in rfi_blob:
                    linked_objects.append(f"spec:{section}")
            for equipment_id in sorted(equipment_ids):
                if equipment_id and equipment_id in rfi_blob:
                    linked_objects.append(f"equipment:{equipment_id}")

            if linked_objects:
                findings.append(
                    self._finding(
                        finding_id=f"coord-rfi-signal:{rfi_id}",
                        category=CoordinationCategory.RFI_CANDIDATE_SIGNAL,
                        severity=CoordinationSeverity.MEDIUM,
                        confidence=CoordinationConfidence.MEDIUM,
                        title=f"RFI {rfi_id} signals cross-object coordination risk",
                        description=(
                            f"RFI candidate {rfi_id} references objects across drawing/spec/equipment sets."
                        ),
                        recommended_action="Review linked objects and confirm final estimator assumptions.",
                        related_objects=[f"rfi:{rfi_id}"] + linked_objects[:6],
                    )
                )

        for assumption in assumptions:
            assumption_id = self._safe_text(
                assumption.get("assumption_id"),
                self._safe_text(assumption.get("title"), "assumption"),
            )
            assumption_blob = str(assumption)
            linked = (
                any(token in assumption_blob for token in drawing_ids)
                or any(token in assumption_blob for token in spec_ids)
                or any(token in assumption_blob for token in equipment_ids)
            )
            if not linked:
                findings.append(
                    self._finding(
                        finding_id=f"coord-assumption-unlinked:{assumption_id}",
                        category=CoordinationCategory.ASSUMPTION_TRACEABILITY,
                        severity=CoordinationSeverity.MEDIUM,
                        confidence=CoordinationConfidence.MEDIUM,
                        title=f"Engineering assumption {assumption_id} lacks object traceability",
                        description=(
                            f"Assumption {assumption_id} is not linked to a drawing/spec/equipment object."
                        ),
                        recommended_action="Attach assumption to explicit drawing/spec/equipment evidence.",
                        related_objects=[f"assumption:{assumption_id}"],
                    )
                )

        if not evidence and findings:
            findings.append(
                self._finding(
                    finding_id="coord-evidence-gap:global",
                    category=CoordinationCategory.EVIDENCE_TRACEABILITY,
                    severity=CoordinationSeverity.HIGH,
                    confidence=CoordinationConfidence.MEDIUM,
                    title="Coordination findings are present with limited evidence references",
                    description=(
                        "Coordination findings were generated but no evidence rows were available "
                        "for traceability linking."
                    ),
                    recommended_action="Load source evidence pages or snapshots for estimator traceability.",
                    related_objects=[
                        item
                        for finding in findings[:5]
                        for item in finding.related_objects[:2]
                    ],
                )
            )

        issues = self._build_issues(findings)
        summary = self._build_summary(findings)

        result_confidence = aggregate_confidence(
            [
                review.confidence,
                *[self._confidence_score(item.confidence) for item in findings],
            ],
            default=review.confidence,
        )

        return CoordinationIntelligenceResult(
            findings=findings,
            issues=issues,
            summary=summary,
            confidence=result_confidence,
        )

    def _build_issues(
        self,
        findings: list[CoordinationFinding],
    ) -> list[CoordinationIssue]:
        grouped: dict[
            tuple[CoordinationCategory, CoordinationSeverity], list[CoordinationFinding]
        ] = {}
        for finding in findings:
            key = (finding.category, finding.severity)
            grouped.setdefault(key, []).append(finding)

        issues: list[CoordinationIssue] = []
        for index, ((category, severity), items) in enumerate(grouped.items(), start=1):
            related_objects = sorted(
                {
                    related
                    for finding in items
                    for related in list(finding.related_objects or [])
                }
            )
            issues.append(
                CoordinationIssue(
                    issue_id=f"issue-{category.value}-{index}",
                    category=category,
                    severity=severity,
                    finding_ids=[item.finding_id for item in items],
                    related_objects=related_objects[:16],
                )
            )
        return issues

    def _build_summary(
        self, findings: list[CoordinationFinding]
    ) -> CoordinationSummary:
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_confidence: dict[str, int] = {}
        conflict_count = 0
        gap_count = 0
        agreement_count = 0

        for finding in findings:
            category = finding.category.value
            severity = finding.severity.value
            confidence = finding.confidence.value
            by_category[category] = by_category.get(category, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_confidence[confidence] = by_confidence.get(confidence, 0) + 1

            blob = f"{finding.title} {finding.description}".lower()
            if "missing" in blob or "not present" in blob or "without" in blob:
                gap_count += 1
            elif "align" in blob or "coordinated" in blob:
                agreement_count += 1
            else:
                conflict_count += 1

        top_actions = []
        for item in sorted(
            findings,
            key=lambda finding: (
                self._severity_rank(finding.severity),
                self._confidence_score(finding.confidence),
            ),
            reverse=True,
        )[:6]:
            top_actions.append(item.recommended_action)

        return CoordinationSummary(
            total_findings=len(findings),
            conflict_count=conflict_count,
            gap_count=gap_count,
            agreement_count=agreement_count,
            by_category=by_category,
            by_severity=by_severity,
            by_confidence=by_confidence,
            top_actions=top_actions,
        )

    def _finding(
        self,
        finding_id: str,
        category: CoordinationCategory,
        severity: CoordinationSeverity,
        confidence: CoordinationConfidence,
        title: str,
        description: str,
        recommended_action: str,
        related_objects: list[str],
        evidence: list[CoordinationEvidence] | None = None,
    ) -> CoordinationFinding:
        return CoordinationFinding(
            finding_id=finding_id,
            category=category,
            severity=severity,
            confidence=confidence,
            title=title,
            description=description,
            recommended_action=recommended_action,
            related_objects=sorted({item for item in related_objects if item}),
            evidence=list(evidence or []),
        )

    @staticmethod
    def _severity_rank(severity: CoordinationSeverity) -> int:
        ranks = {
            CoordinationSeverity.CRITICAL: 4,
            CoordinationSeverity.HIGH: 3,
            CoordinationSeverity.MEDIUM: 2,
            CoordinationSeverity.LOW: 1,
        }
        return ranks.get(severity, 0)

    @staticmethod
    def _confidence_score(confidence: CoordinationConfidence) -> float:
        mapping = {
            CoordinationConfidence.HIGH: 0.9,
            CoordinationConfidence.MEDIUM: 0.7,
            CoordinationConfidence.LOW: 0.5,
        }
        return mapping.get(confidence, 0.5)

    @staticmethod
    def _safe_text(value: Any, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text or fallback

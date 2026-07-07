"""Deterministic engineering intelligence and decision support helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from atlas_core.domain import BidPackageReview
from atlas_core.services.estimator_brief_service import EstimatorBrief


class InsightPriority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class EngineeringInsight:
    insight_id: str
    category: str
    severity: str
    confidence: float
    title: str
    description: str
    recommended_action: str
    supporting_objects: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    created_by_engine_version: str = "engineering-insights-service/1.0.0"
    priority: str = InsightPriority.MEDIUM.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectHealthCategory:
    category: str
    weight: float
    score: float
    rationale: str

    def weighted_score(self) -> float:
        return self.weight * self.score

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["weighted_score"] = round(self.weighted_score(), 2)
        return data


@dataclass
class ProjectHealthModel:
    score: int
    categories: list[ProjectHealthCategory]
    rationale: list[str]
    created_by_engine_version: str = "engineering-insights-service/1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "categories": [item.to_dict() for item in self.categories],
            "rationale": list(self.rationale),
            "created_by_engine_version": self.created_by_engine_version,
        }


@dataclass
class SystemHealth:
    system_id: str
    system_name: str
    health_score: int
    confidence: float
    equipment_completeness: float
    specification_coverage: float
    drawing_coverage: float
    outstanding_rfis: int
    outstanding_assumptions: int
    labor_confidence: float
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EngineeringIntelligenceResult:
    insights: list[EngineeringInsight]
    project_health: ProjectHealthModel
    system_health: list[SystemHealth]
    recommendations: list[EngineeringInsight]
    created_by_engine_version: str = "engineering-insights-service/1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "insights": [item.to_dict() for item in self.insights],
            "project_health": self.project_health.to_dict(),
            "system_health": [item.to_dict() for item in self.system_health],
            "recommendations": [item.to_dict() for item in self.recommendations],
            "created_by_engine_version": self.created_by_engine_version,
        }


class EngineeringInsightsService:
    ENGINE_VERSION = "engineering-insights-service/1.0.0"

    def build(
        self,
        review: BidPackageReview,
        knowledge_graph: dict[str, Any],
        estimator_brief: EstimatorBrief | None = None,
    ) -> EngineeringIntelligenceResult:
        readiness = getattr(review, "readiness", None)
        labor = getattr(review, "labor_estimate", None)
        revision = getattr(review, "revision_comparison", None)

        insights: list[EngineeringInsight] = []
        graph_nodes = list(knowledge_graph.get("nodes", []))
        graph_edges = list(knowledge_graph.get("edges", []))

        blockers = list(getattr(readiness, "blocking_issues", []) or [])
        missing_scope = list(getattr(readiness, "missing_scope_diagnostics", []) or [])
        readiness_warnings = list(getattr(readiness, "warnings", []) or [])

        if blockers:
            insights.append(
                self._insight(
                    insight_id="missing-information-blockers",
                    category="Missing Information",
                    severity="critical",
                    confidence=0.9,
                    title="Critical missing information blocks estimate confidence",
                    description=f"Readiness has {len(blockers)} blocking issues requiring engineering clarification.",
                    recommended_action="Resolve blockers and verify updated references before final estimate.",
                    supporting_objects=[
                        f"blocker:{index}" for index, _ in enumerate(blockers, start=1)
                    ],
                    evidence_refs=blockers[:5],
                )
            )

        if missing_scope:
            insights.append(
                self._insight(
                    insight_id="scope-conflict-missing-scope",
                    category="Scope Conflict",
                    severity="high",
                    confidence=0.82,
                    title="Scope diagnostics indicate unresolved conflicts",
                    description=f"Detected {len(missing_scope)} missing-scope diagnostics in deterministic readiness outputs.",
                    recommended_action="Review scope diagnostics and align drawing/spec/system ownership.",
                    supporting_objects=list(missing_scope)[:6],
                    evidence_refs=list(missing_scope)[:6],
                )
            )

        spec_conflicts = self._specification_conflicts(review)
        if spec_conflicts:
            insights.append(
                self._insight(
                    insight_id="specification-conflict-unmatched-products",
                    category="Specification Conflict",
                    severity="high",
                    confidence=0.8,
                    title="Specification references are not fully represented by equipment",
                    description=(
                        "Some specification sections are not linked to detected equipment, which may indicate unresolved product scope."
                    ),
                    recommended_action="Verify product coverage for referenced specification sections.",
                    supporting_objects=spec_conflicts,
                    evidence_refs=spec_conflicts,
                )
            )

        drawing_conflicts = self._drawing_conflicts(review)
        if drawing_conflicts:
            insights.append(
                self._insight(
                    insight_id="drawing-conflict-unlinked-drawings",
                    category="Drawing Conflict",
                    severity="medium",
                    confidence=0.76,
                    title="Drawings have weak traceability to specification references",
                    description="Some drawings are referenced without linked specification detail paths.",
                    recommended_action="Map affected drawings to explicit specification sections before estimate finalization.",
                    supporting_objects=drawing_conflicts,
                    evidence_refs=drawing_conflicts,
                )
            )

        if labor is not None and getattr(labor, "confidence", 1.0) < 0.75:
            labor_conf = float(getattr(labor, "confidence", 0.0) or 0.0)
            insights.append(
                self._insight(
                    insight_id="labor-risk-low-confidence",
                    category="Labor Risk",
                    severity="high",
                    confidence=0.85,
                    title="Labor estimate confidence is below preferred engineering threshold",
                    description=f"Labor estimate confidence is {labor_conf:.2f}, indicating unstable quantity assumptions.",
                    recommended_action="Review labor categories with highest risk factors before pricing.",
                    supporting_objects=[
                        str(getattr(item, "category_name", "labor-category"))
                        for item in list(getattr(labor, "labor_categories", []) or [])
                    ][:8],
                    evidence_refs=list(getattr(labor, "warnings", []) or [])[:8],
                )
            )

        if revision is not None:
            high_changes = [
                item
                for item in list(getattr(revision, "changes", []) or [])
                if self._value(getattr(item, "severity", "")) in {"high", "critical"}
            ]
            if high_changes:
                insights.append(
                    self._insight(
                        insight_id="revision-impact-high-change-count",
                        category="Revision Impact",
                        severity="high",
                        confidence=0.83,
                        title="Revision comparison has high-impact changes",
                        description=(
                            f"Detected {len(high_changes)} high/critical revision changes affecting engineering scope."
                        ),
                        recommended_action="Review changed sheets/specs and confirm quantity/system impacts.",
                        supporting_objects=[
                            self._safe_text(getattr(item, "change_id", None), "change")
                            for item in high_changes[:8]
                        ],
                        evidence_refs=[
                            self._safe_text(
                                getattr(item, "title", None), "revision-change"
                            )
                            for item in high_changes[:8]
                        ],
                    )
                )

        coordination_issues = self._coordination_issues(review)
        if coordination_issues:
            insights.append(
                self._insight(
                    insight_id="coordination-issue-cross-object",
                    category="Coordination Issue",
                    severity="medium",
                    confidence=0.79,
                    title="Cross-object coordination issues detected",
                    description="Equipment/system/room references show coordination gaps requiring engineering alignment.",
                    recommended_action="Resolve room and system assignment gaps before lock-in.",
                    supporting_objects=coordination_issues,
                    evidence_refs=coordination_issues,
                )
            )

        assumptions = list(getattr(review, "engineering_assumptions", []) or [])
        if assumptions:
            insights.append(
                self._insight(
                    insight_id="engineering-assumption-review",
                    category="Engineering Assumption",
                    severity="medium",
                    confidence=0.77,
                    title="Engineering assumptions require deterministic confirmation",
                    description=f"{len(assumptions)} engineering assumptions were captured and should be validated.",
                    recommended_action="Validate assumption ownership and document approval path.",
                    supporting_objects=[
                        self._safe_text(
                            getattr(item, "assumption_id", None), "assumption"
                        )
                        for item in assumptions[:10]
                    ],
                    evidence_refs=[
                        self._safe_text(
                            getattr(item, "description", None), "assumption"
                        )
                        for item in assumptions[:10]
                    ],
                )
            )

        reminders = self._code_standard_reminders(review)
        if reminders:
            insights.append(
                self._insight(
                    insight_id="code-standards-reminder",
                    category="Code / Standards Reminder",
                    severity="low",
                    confidence=0.66,
                    title="Standards and owner criteria reminders generated",
                    description="Deterministic package cues indicate standards-related review reminders.",
                    recommended_action="Confirm owner/standard notes in specifications and addenda during final review.",
                    supporting_objects=reminders,
                    evidence_refs=reminders,
                )
            )

        procurement_advisory = self._procurement_advisory(review)
        if procurement_advisory:
            insights.append(
                self._insight(
                    insight_id="procurement-risk-advisory",
                    category="Procurement Risk",
                    severity="low",
                    confidence=0.62,
                    title="Procurement risk advisory",
                    description="Manufacturer/model completeness indicates advisory procurement uncertainty.",
                    recommended_action="Confirm lead-time-sensitive items and OFCI responsibilities.",
                    supporting_objects=procurement_advisory,
                    evidence_refs=procurement_advisory,
                )
            )

        schedule_advisory = self._schedule_advisory(readiness_warnings)
        if schedule_advisory:
            insights.append(
                self._insight(
                    insight_id="schedule-risk-advisory",
                    category="Schedule Risk",
                    severity="low",
                    confidence=0.6,
                    title="Schedule risk advisory",
                    description="Readiness evidence includes schedule-sensitive warning indicators.",
                    recommended_action="Review schedule-related assumptions and critical path dependencies.",
                    supporting_objects=schedule_advisory,
                    evidence_refs=schedule_advisory,
                )
            )

        cross_object = self._cross_object_risks(review, graph_nodes, graph_edges)
        insights.extend(cross_object)

        if estimator_brief is not None and estimator_brief.prioritized_reviewer_actions:
            insights.append(
                self._insight(
                    insight_id="general-recommendation-brief-actions",
                    category="General Recommendation",
                    severity="medium",
                    confidence=0.81,
                    title="Highest-confidence reviewer actions are available",
                    description="Estimator Brief produced prioritized deterministic reviewer actions.",
                    recommended_action="Execute highest-priority reviewer actions before pricing freeze.",
                    supporting_objects=[
                        self._safe_text(item.get("action_id"), "action")
                        for item in list(
                            estimator_brief.prioritized_reviewer_actions or []
                        )[:8]
                    ],
                    evidence_refs=[
                        self._safe_text(item.get("title"), "action")
                        for item in list(
                            estimator_brief.prioritized_reviewer_actions or []
                        )[:8]
                    ],
                )
            )

        prioritized = self._prioritize_insights(
            insights=insights,
            review=review,
            knowledge_graph=knowledge_graph,
            blockers=blockers,
        )

        project_health = self._project_health(
            review=review, knowledge_graph=knowledge_graph
        )
        system_health = self._system_health(
            review=review, knowledge_graph=knowledge_graph
        )
        recommendations = self._recommendations(prioritized)

        return EngineeringIntelligenceResult(
            insights=prioritized,
            project_health=project_health,
            system_health=system_health,
            recommendations=recommendations,
            created_by_engine_version=self.ENGINE_VERSION,
        )

    def _cross_object_risks(
        self,
        review: BidPackageReview,
        graph_nodes: list[dict[str, Any]],
        graph_edges: list[dict[str, Any]],
    ) -> list[EngineeringInsight]:
        insights: list[EngineeringInsight] = []

        heavily_referenced_no_spec: list[str] = []
        for equipment in list(getattr(review, "equipment", []) or []):
            drawing_refs = self._split_refs(
                getattr(equipment, "drawing_reference", None)
            )
            spec_ref = self._safe_text(
                getattr(equipment, "specification_reference", None), ""
            )
            if len(drawing_refs) >= 2 and not spec_ref:
                heavily_referenced_no_spec.append(
                    self._safe_text(
                        getattr(equipment, "equipment_id", None), "equipment"
                    )
                )

        if heavily_referenced_no_spec:
            insights.append(
                self._insight(
                    insight_id="cross-object-equipment-no-spec",
                    category="Coordination Issue",
                    severity="high",
                    confidence=0.84,
                    title="Equipment is referenced by multiple drawings but has no specification",
                    description=(
                        "Deterministic cross-object check found equipment with broad drawing references and missing specification linkage."
                    ),
                    recommended_action="Add or confirm specification references for affected equipment.",
                    supporting_objects=heavily_referenced_no_spec,
                    evidence_refs=heavily_referenced_no_spec,
                )
            )

        specs_without_drawing: list[str] = []
        for specification in list(getattr(review, "specification_sections", []) or []):
            section = self._safe_text(
                getattr(specification, "section_number", None), "specification"
            )
            matched = any(
                self._safe_text(getattr(equipment, "specification_reference", None), "")
                == section
                and bool(
                    self._safe_text(getattr(equipment, "drawing_reference", None), "")
                )
                for equipment in list(getattr(review, "equipment", []) or [])
            )
            if not matched:
                specs_without_drawing.append(section)

        if specs_without_drawing:
            insights.append(
                self._insight(
                    insight_id="cross-object-spec-without-drawing-products",
                    category="Specification Conflict",
                    severity="medium",
                    confidence=0.78,
                    title="Specifications reference products not found on drawings",
                    description="Specification sections exist without drawing-linked equipment references.",
                    recommended_action="Validate product placement and drawing coverage for affected sections.",
                    supporting_objects=specs_without_drawing[:10],
                    evidence_refs=specs_without_drawing[:10],
                )
            )

        systems_without_equipment: list[str] = []
        for system in list(getattr(review, "systems", []) or []):
            system_id = self._safe_text(getattr(system, "system_id", None), "system")
            has_equipment = any(
                self._safe_text(getattr(item, "system_id", None), "") == system_id
                for item in list(getattr(review, "equipment", []) or [])
            )
            if not has_equipment:
                systems_without_equipment.append(system_id)

        if systems_without_equipment:
            insights.append(
                self._insight(
                    insight_id="cross-object-incomplete-systems",
                    category="Missing Information",
                    severity="high",
                    confidence=0.82,
                    title="Systems with incomplete equipment detected",
                    description="One or more systems have no detected equipment assignments.",
                    recommended_action="Confirm system equipment schedules and update extraction references.",
                    supporting_objects=systems_without_equipment,
                    evidence_refs=systems_without_equipment,
                )
            )

        rooms_without_devices: list[str] = []
        for room in list(getattr(review, "rooms", []) or []):
            room_id = self._safe_text(getattr(room, "room_id", None), "room")
            has_devices = any(
                self._safe_text(getattr(item, "room_id", None), "") == room_id
                for item in list(getattr(review, "equipment", []) or [])
            )
            if not has_devices:
                rooms_without_devices.append(room_id)

        if rooms_without_devices:
            insights.append(
                self._insight(
                    insight_id="cross-object-rooms-without-devices",
                    category="Missing Information",
                    severity="medium",
                    confidence=0.74,
                    title="Rooms with missing devices identified",
                    description="Room objects exist without linked equipment devices.",
                    recommended_action="Review room device schedules and verify room-to-equipment mappings.",
                    supporting_objects=rooms_without_devices[:10],
                    evidence_refs=rooms_without_devices[:10],
                )
            )

        drawings_without_specs: list[str] = []
        for drawing in list(getattr(review, "drawing_sheets", []) or []):
            drawing_id = self._safe_text(
                getattr(drawing, "sheet_number", None), "drawing"
            )
            linked_specs = {
                self._safe_text(getattr(item, "specification_reference", None), "")
                for item in list(getattr(review, "equipment", []) or [])
                if drawing_id
                in self._split_refs(getattr(item, "drawing_reference", None))
            }
            linked_specs.discard("")
            if not linked_specs:
                drawings_without_specs.append(drawing_id)

        if drawings_without_specs:
            insights.append(
                self._insight(
                    insight_id="cross-object-drawings-without-specifications",
                    category="Drawing Conflict",
                    severity="medium",
                    confidence=0.73,
                    title="Drawings without referenced specifications",
                    description="Some drawings do not link to specification references through detected equipment.",
                    recommended_action="Confirm specification references for affected drawings.",
                    supporting_objects=drawings_without_specs[:12],
                    evidence_refs=drawings_without_specs[:12],
                )
            )

        evidence_nodes = {
            str(node.get("id"))
            for node in graph_nodes
            if self._safe_text(node.get("type"), "") == "Evidence"
        }
        referenced_evidence = {
            str(edge.get("target"))
            for edge in graph_edges
            if "Evidence" in self._safe_text(edge.get("relationship"), "")
        }
        evidence_gaps = sorted(evidence_nodes - referenced_evidence)
        if evidence_gaps:
            insights.append(
                self._insight(
                    insight_id="cross-object-evidence-gaps",
                    category="Missing Information",
                    severity="medium",
                    confidence=0.7,
                    title="Evidence gaps detected",
                    description="Evidence nodes exist without deterministic object relationships.",
                    recommended_action="Back-link evidence to drawings/specifications/assumptions where applicable.",
                    supporting_objects=evidence_gaps[:10],
                    evidence_refs=evidence_gaps[:10],
                )
            )

        return insights

    def _project_health(
        self,
        review: BidPackageReview,
        knowledge_graph: dict[str, Any],
    ) -> ProjectHealthModel:
        readiness = getattr(review, "readiness", None)
        labor = getattr(review, "labor_estimate", None)
        revision = getattr(review, "revision_comparison", None)

        blockers = len(list(getattr(readiness, "blocking_issues", []) or []))
        warnings = len(list(getattr(readiness, "warnings", []) or []))
        missing_scope = len(
            list(getattr(readiness, "missing_scope_diagnostics", []) or [])
        )

        drawing_count = max(review.drawing_count(), 1)
        spec_count = max(review.specification_count(), 1)
        equipment_count = max(review.equipment_count(), 1)

        graph_edges = len(list(knowledge_graph.get("edges", [])))
        graph_nodes = max(len(list(knowledge_graph.get("nodes", []))), 1)
        resolver_summary = dict(knowledge_graph.get("resolver_summary") or {})
        resolver_confidence = float(
            resolver_summary.get("confidence", review.confidence) or review.confidence
        )
        resolver_conflicts = int(resolver_summary.get("conflict_count", 0) or 0)
        resolver_manual_reviews = int(
            resolver_summary.get("manual_review_count", 0) or 0
        )

        completeness_score = max(
            0.0,
            min(
                1.0,
                (
                    (review.drawing_count() / drawing_count)
                    + (review.specification_count() / spec_count)
                    + (review.equipment_count() / equipment_count)
                )
                / 3,
            ),
        )

        consistency_penalty = min(0.6, (missing_scope * 0.08) + (warnings * 0.03))
        consistency_score = max(0.0, 1.0 - consistency_penalty)

        coordination_score = max(
            0.0,
            min(1.0, graph_edges / max(graph_nodes * 2, 1)),
        )

        confidence_score = float(getattr(review, "confidence", 0.0) or 0.0)
        if labor is not None:
            confidence_score = (
                confidence_score + float(getattr(labor, "confidence", 0.0) or 0.0)
            ) / 2
        confidence_score = (confidence_score + resolver_confidence) / 2
        confidence_score = max(
            0.0, min(1.0, confidence_score - (resolver_conflicts * 0.02))
        )

        revision_stability = 1.0
        if revision is not None:
            high_changes = sum(
                1
                for item in list(getattr(revision, "changes", []) or [])
                if self._value(getattr(item, "severity", "")) in {"high", "critical"}
            )
            revision_stability = max(0.0, 1.0 - min(0.7, high_changes * 0.12))

        blockers_penalty = min(0.35, blockers * 0.09)

        categories = [
            ProjectHealthCategory(
                category="Engineering Completeness",
                weight=0.30,
                score=max(0.0, completeness_score - blockers_penalty),
                rationale="Balances available drawings, specifications, and equipment against active blockers.",
            ),
            ProjectHealthCategory(
                category="Package Consistency",
                weight=0.25,
                score=consistency_score,
                rationale="Penalizes missing-scope diagnostics and readiness warnings.",
            ),
            ProjectHealthCategory(
                category="Cross-Object Coordination",
                weight=0.20,
                score=coordination_score,
                rationale="Uses deterministic relationship density across the project knowledge graph.",
            ),
            ProjectHealthCategory(
                category="Estimating Confidence",
                weight=0.15,
                score=max(0.0, min(1.0, confidence_score)),
                rationale="Combines review, labor, and resolver confidence when available.",
            ),
            ProjectHealthCategory(
                category="Revision Stability",
                weight=0.10,
                score=revision_stability,
                rationale="Reduces score when high/critical revision changes are present.",
            ),
        ]

        weighted = sum(item.weighted_score() for item in categories)
        score = max(0, min(100, int(round(weighted * 100))))
        rationale = [
            f"{item.category}: {item.score:.2f} x {item.weight:.2f}"
            for item in categories
        ]
        rationale.append(f"Blockers considered: {blockers}")
        rationale.append(f"Missing scope diagnostics considered: {missing_scope}")
        rationale.append(f"Resolver conflicts considered: {resolver_conflicts}")
        rationale.append(f"Resolver manual reviews considered: {resolver_manual_reviews}")

        return ProjectHealthModel(
            score=score, categories=categories, rationale=rationale
        )

    def _system_health(
        self,
        review: BidPackageReview,
        knowledge_graph: dict[str, Any],
    ) -> list[SystemHealth]:
        systems = list(getattr(review, "systems", []) or [])
        equipment = list(getattr(review, "equipment", []) or [])
        assumptions = list(getattr(review, "engineering_assumptions", []) or [])
        rfis = list(getattr(review, "rfi_candidates", []) or [])
        labor = getattr(review, "labor_estimate", None)

        edge_pairs = [
            (
                self._safe_text(edge.get("source"), ""),
                self._safe_text(edge.get("target"), ""),
                self._safe_text(edge.get("relationship"), ""),
            )
            for edge in list(knowledge_graph.get("edges", []))
        ]

        results: list[SystemHealth] = []
        for system in systems:
            system_id = self._safe_text(getattr(system, "system_id", None), "system")
            system_name = self._safe_text(getattr(system, "name", None), system_id)
            system_equipment = [
                item
                for item in equipment
                if self._safe_text(getattr(item, "system_id", None), "") == system_id
            ]

            equipment_total = max(len(system_equipment), 1)
            with_manufacturer = sum(
                1
                for item in system_equipment
                if bool(self._safe_text(getattr(item, "manufacturer", None), ""))
            )
            with_spec = sum(
                1
                for item in system_equipment
                if bool(
                    self._safe_text(getattr(item, "specification_reference", None), "")
                )
            )
            with_drawing = sum(
                1
                for item in system_equipment
                if bool(self._safe_text(getattr(item, "drawing_reference", None), ""))
            )

            equipment_completeness = with_manufacturer / equipment_total
            specification_coverage = with_spec / equipment_total
            drawing_coverage = with_drawing / equipment_total

            outstanding_rfis = sum(
                1
                for item in rfis
                if any(
                    equipment_id in list(getattr(item, "related_items", []) or [])
                    for equipment_id in [
                        self._safe_text(getattr(eq, "equipment_id", None), "")
                        for eq in system_equipment
                    ]
                )
            )

            outstanding_assumptions = sum(
                1
                for assumption in assumptions
                if any(
                    self._safe_text(getattr(eq, "equipment_id", None), "")
                    in self._safe_text(getattr(assumption, "description", None), "")
                    for eq in system_equipment
                )
            )

            relationship_count = sum(
                1
                for source, target, _ in edge_pairs
                if source.endswith(system_id) or target.endswith(system_id)
            )

            labor_confidence = float(
                getattr(labor, "confidence", review.confidence) or 0.0
            )
            base_score = (
                equipment_completeness * 0.30
                + specification_coverage * 0.20
                + drawing_coverage * 0.20
                + labor_confidence * 0.15
                + min(1.0, relationship_count / 8) * 0.15
            )
            deductions = min(
                0.45, outstanding_rfis * 0.08 + outstanding_assumptions * 0.05
            )
            health_score = max(0, min(100, int(round((base_score - deductions) * 100))))

            warnings: list[str] = []
            if equipment_completeness < 0.7:
                warnings.append("Manufacturer/model completeness is below threshold.")
            if specification_coverage < 0.7:
                warnings.append("Specification coverage is incomplete.")
            if drawing_coverage < 0.7:
                warnings.append("Drawing coverage is incomplete.")
            if outstanding_rfis > 0:
                warnings.append(f"Outstanding RFIs: {outstanding_rfis}")
            if outstanding_assumptions > 0:
                warnings.append(f"Outstanding assumptions: {outstanding_assumptions}")

            results.append(
                SystemHealth(
                    system_id=system_id,
                    system_name=system_name,
                    health_score=health_score,
                    confidence=float(getattr(review, "confidence", 0.0) or 0.0),
                    equipment_completeness=round(equipment_completeness, 2),
                    specification_coverage=round(specification_coverage, 2),
                    drawing_coverage=round(drawing_coverage, 2),
                    outstanding_rfis=outstanding_rfis,
                    outstanding_assumptions=outstanding_assumptions,
                    labor_confidence=round(labor_confidence, 2),
                    warnings=warnings,
                )
            )

        results.sort(key=lambda item: item.health_score)
        return results

    def _recommendations(
        self,
        insights: list[EngineeringInsight],
    ) -> list[EngineeringInsight]:
        recommendations: list[EngineeringInsight] = []
        for insight in insights:
            if not insight.recommended_action:
                continue
            recommendation = EngineeringInsight(
                insight_id=f"recommendation-{insight.insight_id}",
                category="General Recommendation",
                severity=insight.severity,
                confidence=insight.confidence,
                title=insight.title,
                description=(
                    "Deterministic recommendation generated from engineering insight: "
                    f"{insight.description}"
                ),
                recommended_action=insight.recommended_action,
                supporting_objects=list(insight.supporting_objects),
                evidence_refs=list(insight.evidence_refs),
                created_by_engine_version=self.ENGINE_VERSION,
                priority=insight.priority,
            )
            recommendations.append(recommendation)

        seen: set[str] = set()
        deduped: list[EngineeringInsight] = []
        for item in recommendations:
            key = f"{item.title}|{item.recommended_action}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        return deduped[:12]

    def _prioritize_insights(
        self,
        insights: list[EngineeringInsight],
        review: BidPackageReview,
        knowledge_graph: dict[str, Any],
        blockers: list[str],
    ) -> list[EngineeringInsight]:
        edge_count = len(list(knowledge_graph.get("edges", [])))

        severity_weight = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }

        prioritized: list[EngineeringInsight] = []
        for insight in insights:
            sev = severity_weight.get(insight.severity.lower(), 1)
            confidence_score = max(0.0, min(1.0, insight.confidence))
            relationship_factor = min(1.0, edge_count / 100)
            system_factor = min(
                1.0,
                len(
                    [
                        item
                        for item in insight.supporting_objects
                        if "sys" in item.lower() or "system" in item.lower()
                    ]
                )
                / 5,
            )
            drawing_factor = min(
                1.0,
                len(
                    [
                        item
                        for item in insight.supporting_objects
                        if "av-" in item.lower() or "drawing" in item.lower()
                    ]
                )
                / 6,
            )
            blocker_factor = min(1.0, len(blockers) / 6)

            rank_value = (
                sev * 0.40
                + confidence_score * 0.20
                + relationship_factor * 0.12
                + system_factor * 0.10
                + drawing_factor * 0.08
                + blocker_factor * 0.10
            )

            if rank_value >= 2.8:
                insight.priority = InsightPriority.CRITICAL.value
            elif rank_value >= 2.1:
                insight.priority = InsightPriority.HIGH.value
            elif rank_value >= 1.5:
                insight.priority = InsightPriority.MEDIUM.value
            else:
                insight.priority = InsightPriority.LOW.value

            prioritized.append(insight)

        priority_order = {
            InsightPriority.CRITICAL.value: 4,
            InsightPriority.HIGH.value: 3,
            InsightPriority.MEDIUM.value: 2,
            InsightPriority.LOW.value: 1,
        }

        prioritized.sort(
            key=lambda item: (
                priority_order.get(item.priority, 0),
                severity_weight.get(item.severity.lower(), 0),
                item.confidence,
                len(item.supporting_objects),
            ),
            reverse=True,
        )
        return prioritized

    def _specification_conflicts(self, review: BidPackageReview) -> list[str]:
        equipment_spec_refs = {
            self._safe_text(getattr(item, "specification_reference", None), "")
            for item in list(getattr(review, "equipment", []) or [])
        }
        equipment_spec_refs.discard("")

        unmatched: list[str] = []
        for spec in list(getattr(review, "specification_sections", []) or []):
            section = self._safe_text(getattr(spec, "section_number", None), "")
            if section and section not in equipment_spec_refs:
                unmatched.append(section)

        return unmatched[:12]

    def _drawing_conflicts(self, review: BidPackageReview) -> list[str]:
        drawing_refs = {
            ref
            for item in list(getattr(review, "equipment", []) or [])
            for ref in self._split_refs(getattr(item, "drawing_reference", None))
        }
        conflicts: list[str] = []
        for drawing in list(getattr(review, "drawing_sheets", []) or []):
            sheet = self._safe_text(getattr(drawing, "sheet_number", None), "")
            if sheet and sheet not in drawing_refs:
                conflicts.append(sheet)

        return conflicts[:12]

    def _coordination_issues(self, review: BidPackageReview) -> list[str]:
        coordination: list[str] = []
        for equipment in list(getattr(review, "equipment", []) or []):
            equipment_id = self._safe_text(getattr(equipment, "equipment_id", None), "")
            room_id = self._safe_text(getattr(equipment, "room_id", None), "")
            system_id = self._safe_text(getattr(equipment, "system_id", None), "")
            if not room_id or not system_id:
                coordination.append(equipment_id or "equipment")
        return coordination[:12]

    def _code_standard_reminders(self, review: BidPackageReview) -> list[str]:
        reminders: list[str] = []
        notes = list(getattr(review, "notes", []) or [])
        for note in notes:
            text = self._safe_text(note, "").lower()
            if "code" in text or "standard" in text or "nfpa" in text:
                reminders.append(note)

        for assumption in list(getattr(review, "engineering_assumptions", []) or []):
            description = self._safe_text(getattr(assumption, "description", None), "")
            if any(
                token in description.lower()
                for token in ["standard", "code", "ul", "nfpa"]
            ):
                reminders.append(description)

        return reminders[:12]

    def _procurement_advisory(self, review: BidPackageReview) -> list[str]:
        advisories: list[str] = []
        for equipment in list(getattr(review, "equipment", []) or []):
            manufacturer = self._safe_text(getattr(equipment, "manufacturer", None), "")
            model = self._safe_text(getattr(equipment, "model", None), "")
            assumptions = list(getattr(equipment, "assumptions", []) or [])
            if not manufacturer or not model:
                advisories.append(
                    self._safe_text(
                        getattr(equipment, "equipment_id", None), "equipment"
                    )
                )
            if any("ofci" in self._safe_text(item, "").lower() for item in assumptions):
                advisories.append(
                    f"{self._safe_text(getattr(equipment, 'equipment_id', None), 'equipment')}: OFCI"
                )

        return advisories[:10]

    def _schedule_advisory(self, readiness_warnings: list[str]) -> list[str]:
        indicators = [
            item
            for item in readiness_warnings
            if any(
                token in self._safe_text(item, "").lower()
                for token in ["schedule", "lead", "timeline", "phase"]
            )
        ]
        return indicators[:10]

    def _insight(
        self,
        insight_id: str,
        category: str,
        severity: str,
        confidence: float,
        title: str,
        description: str,
        recommended_action: str,
        supporting_objects: list[str],
        evidence_refs: list[str],
    ) -> EngineeringInsight:
        return EngineeringInsight(
            insight_id=insight_id,
            category=category,
            severity=severity,
            confidence=max(0.0, min(1.0, float(confidence))),
            title=title,
            description=description,
            recommended_action=recommended_action,
            supporting_objects=[
                self._safe_text(item, "object") for item in supporting_objects
            ],
            evidence_refs=[self._safe_text(item, "evidence") for item in evidence_refs],
            created_by_engine_version=self.ENGINE_VERSION,
        )

    @staticmethod
    def _split_refs(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).replace("|", ",").replace(";", ",")
        return [item.strip() for item in text.split(",") if item.strip()]

    @staticmethod
    def _safe_text(value: Any, default: str) -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _value(value: Any) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

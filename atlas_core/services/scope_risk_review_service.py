"""Focused scope and risk findings for estimator and sales/design review."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ScopeRiskFinding:
    finding_id: str
    category: str
    severity: str
    confidence: float
    title: str
    concise_explanation: str
    affected_bom_items: list[str]
    affected_systems: list[str]
    affected_rooms: list[str]
    source_references: list[str]
    estimating_impact: str
    recommended_action: str
    likely_owner: str
    candidate_rfi_text: str
    section: str
    impact_score: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ScopeRiskReviewService:
    def build_findings(
        self,
        bom_rows: list[dict[str, Any]] | None,
        resolver_rows: list[dict[str, Any]] | None = None,
        coordination_findings: list[dict[str, Any]] | None = None,
        risk_rows: list[dict[str, Any]] | None = None,
        rfi_rows: list[dict[str, Any]] | None = None,
    ) -> list[ScopeRiskFinding]:
        bom = list(bom_rows or [])
        resolver = list(resolver_rows or [])
        coordination = list(coordination_findings or [])
        risks = list(risk_rows or [])
        rfis = list(rfi_rows or [])

        findings: list[ScopeRiskFinding] = []
        emitted_ids: set[str] = set()

        self._emit_missing_scope_findings(findings, emitted_ids, bom)
        self._emit_responsibility_gap_findings(findings, emitted_ids, bom)
        self._emit_quantity_conflict_findings(findings, emitted_ids, bom, resolver)
        self._emit_engineering_gap_findings(
            findings,
            emitted_ids,
            bom,
            coordination,
            risks,
        )
        self._emit_commercial_risk_findings(findings, emitted_ids, bom, risks)
        self._emit_mismatch_findings(findings, emitted_ids, bom)

        findings.sort(
            key=lambda item: (
                -item.impact_score,
                -item.confidence,
                item.category,
                item.finding_id,
            )
        )
        self._augment_candidate_rfi_from_pool(findings, rfis)
        return findings

    @staticmethod
    def sectioned_rows(
        findings: list[ScopeRiskFinding],
    ) -> dict[str, list[dict[str, Any]]]:
        ordered_sections = [
            "Critical Issues",
            "Missing Scope",
            "Responsibility Gaps",
            "Quantity Conflicts",
            "Engineering Gaps",
            "Commercial Risks",
            "Recommended RFIs",
        ]
        grouped: dict[str, list[dict[str, Any]]] = {
            section: [] for section in ordered_sections
        }
        for finding in findings:
            grouped.setdefault(finding.section, [])
            grouped[finding.section].append(finding.to_dict())

        grouped["Recommended RFIs"] = [
            {
                "finding_id": item.finding_id,
                "category": item.category,
                "severity": item.severity,
                "title": item.title,
                "candidate_rfi_text": item.candidate_rfi_text,
                "likely_owner": item.likely_owner,
                "estimating_impact": item.estimating_impact,
                "impact_score": item.impact_score,
            }
            for item in findings
            if item.candidate_rfi_text
        ]
        return grouped

    @classmethod
    def _emit_missing_scope_findings(
        cls,
        findings: list[ScopeRiskFinding],
        emitted_ids: set[str],
        bom_rows: list[dict[str, Any]],
    ) -> None:
        missing_mapping = {
            "missing_equipment": (
                [
                    item
                    for item in bom_rows
                    if cls._normalized_text(item.get("description"), "") == "n/a"
                    or cls._normalized_text(item.get("description"), "") == ""
                ],
                "Equipment scope appears underdeveloped in extracted BOM lines.",
                "Confirm missing equipment scope with consultant narratives and reflected ceiling plans.",
                "Estimator",
                "Missing equipment scope may create material and labor omissions.",
            ),
            "missing_manufacturer": (
                [
                    item
                    for item in bom_rows
                    if cls._normalized_text(item.get("manufacturer"), "").lower()
                    in {"", "unknown", "n/a"}
                ],
                "Manufacturer is missing for one or more BOM lines.",
                "Obtain approved manufacturer basis-of-design or acceptable alternates.",
                "Design Engineer",
                "Pricing and lead-time certainty are reduced without manufacturer data.",
            ),
            "missing_model": (
                [
                    item
                    for item in bom_rows
                    if cls._normalized_text(item.get("model"), "").lower()
                    in {"", "unknown", "n/a"}
                ],
                "Model information is incomplete on one or more BOM lines.",
                "Request model-level basis of design and required performance constraints.",
                "Design Engineer",
                "Undefined models can cause substitutions, performance risk, and repricing.",
            ),
            "missing_quantity": (
                [
                    item
                    for item in bom_rows
                    if cls._normalized_text(item.get("quantity"), "").lower()
                    in {"", "unknown", "n/a"}
                ],
                "Quantity is missing on one or more BOM lines.",
                "Issue quantity clarification before final estimate submission.",
                "Estimator",
                "Missing quantities directly impact estimate completeness and bid risk.",
            ),
            "missing_accessories": (
                [
                    item
                    for item in bom_rows
                    if cls._contains_any(
                        item.get("description"),
                        ["display", "projector", "speaker", "microphone"],
                    )
                    and not cls._contains_any(
                        item.get("description"),
                        ["kit", "accessory", "cable", "connector", "mount"],
                    )
                ],
                "Accessory scope is not explicit for primary AV devices.",
                "Confirm required accessories, trims, adapters, and interface kits.",
                "Sales Engineer",
                "Accessory omissions frequently drive unplanned change orders.",
            ),
            "missing_mounting_hardware": (
                [
                    item
                    for item in bom_rows
                    if cls._contains_any(
                        item.get("description"), ["display", "projector"]
                    )
                    and not cls._contains_any(
                        item.get("description"),
                        ["mount", "bracket", "plate", "suspension"],
                    )
                ],
                "Mounting hardware is not explicitly scoped for mounted devices.",
                "Clarify mount type, tilt requirement, and install hardware responsibility.",
                "Design Engineer",
                "Missing mount scope affects labor, structure coordination, and safety margins.",
            ),
            "missing_rack_infrastructure": (
                [
                    item
                    for item in bom_rows
                    if cls._contains_any(
                        item.get("system"), ["audio", "control", "network"]
                    )
                ],
                "Rack infrastructure requirements are not explicitly represented.",
                "Define rack count, RU allocation, thermal strategy, and power distribution.",
                "Sales Engineer",
                "Rack under-scoping creates significant cost and schedule exposure.",
            ),
            "missing_cabling": (
                [
                    item
                    for item in bom_rows
                    if cls._contains_any(
                        item.get("system"),
                        ["audio", "video", "network", "control"],
                    )
                ],
                "Cabling scope is not clearly quantified.",
                "Define cable types, pathways, terminations, and test requirements.",
                "Estimator",
                "Unclear cabling scope can materially understate labor and material costs.",
            ),
            "missing_connectors": (
                [
                    item
                    for item in bom_rows
                    if cls._contains_any(
                        item.get("system"),
                        ["audio", "video", "network", "control"],
                    )
                ],
                "Connector and termination hardware is not explicitly stated.",
                "Clarify connector families, quantities, and installation standards.",
                "Estimator",
                "Connector assumptions can add substantial hidden field labor.",
            ),
            "missing_power_requirements": (
                [
                    item
                    for item in bom_rows
                    if cls._contains_any(
                        item.get("description"),
                        ["amplifier", "display", "projector", "rack", "switch"],
                    )
                ],
                "Power requirements are not explicitly captured for powered devices.",
                "Request voltage, circuiting, receptacle type, and branch responsibility.",
                "Design Engineer",
                "Power ambiguity can create major coordination delays and retrofit costs.",
            ),
            "missing_network_requirements": (
                [
                    item
                    for item in bom_rows
                    if cls._contains_any(
                        item.get("description"),
                        ["dsp", "processor", "network", "switch", "controller"],
                    )
                ],
                "Network requirements are not fully defined for connected systems.",
                "Clarify VLAN, ports, addressing, QoS, and managed switch requirements.",
                "Sales Engineer",
                "Network scope gaps often produce commissioning delays and scope disputes.",
            ),
            "missing_backing_or_structural_support": (
                [
                    item
                    for item in bom_rows
                    if cls._contains_any(
                        item.get("description"), ["display", "projector", "speaker"]
                    )
                ],
                "Backing or structural support requirements are undefined.",
                "Confirm structural support requirements and responsible trade.",
                "GC/Structural",
                "Structural scope uncertainty can force costly late-stage field changes.",
            ),
        }

        for category, (
            affected,
            explanation,
            action,
            owner,
            impact,
        ) in missing_mapping.items():
            if not affected:
                continue
            severity = (
                "high"
                if category
                in {"missing_quantity", "missing_manufacturer", "missing_model"}
                else "medium"
            )
            cls._add_finding(
                findings,
                emitted_ids,
                category=category,
                section="Missing Scope",
                severity=severity,
                confidence=0.78,
                title=category.replace("_", " ").title(),
                explanation=explanation,
                affected_rows=affected,
                estimating_impact=impact,
                recommended_action=action,
                likely_owner=owner,
                candidate_rfi=(
                    "Internal draft RFI: Please confirm "
                    + category.replace("_", " ")
                    + " requirements and basis-of-design assumptions for bidding."
                ),
            )

    @classmethod
    def _emit_responsibility_gap_findings(
        cls,
        findings: list[ScopeRiskFinding],
        emitted_ids: set[str],
        bom_rows: list[dict[str, Any]],
    ) -> None:
        unknown_resp = [
            item
            for item in bom_rows
            if cls._normalized_text(item.get("responsibility"), "unknown").lower()
            in {"unknown", "tbd", "n/a", ""}
        ]
        if unknown_resp:
            cls._add_finding(
                findings,
                emitted_ids,
                category="unclear_ofe_ofci_cfci_nic_responsibility",
                section="Responsibility Gaps",
                severity="high",
                confidence=0.82,
                title="Unclear OFE/OFCI/CFCI/NIC Responsibility",
                explanation="Ownership classification is unclear for one or more BOM lines.",
                affected_rows=unknown_resp,
                estimating_impact="Ambiguous ownership drives pricing exclusions and change-order risk.",
                recommended_action="Request a responsibility matrix by package and system.",
                likely_owner="Estimator",
                candidate_rfi="Internal draft RFI: Please identify OFE/OFCI/CFCI/NIC responsibility for listed systems and devices.",
            )

        if bom_rows:
            cls._add_finding(
                findings,
                emitted_ids,
                category="missing_conduit_pathway_responsibility",
                section="Responsibility Gaps",
                severity="high",
                confidence=0.74,
                title="Conduit and Pathway Responsibility Not Defined",
                explanation="Pathway responsibility is not explicitly identified in the extracted scope.",
                affected_rows=bom_rows,
                estimating_impact="Conduit ambiguity can materially shift labor and subcontract costs.",
                recommended_action="Clarify which trade furnishes and installs conduit, cable tray, and sleeves.",
                likely_owner="GC/EC",
                candidate_rfi="Internal draft RFI: Please confirm conduit/pathway furnishing and installation responsibility by trade.",
            )

    @classmethod
    def _emit_quantity_conflict_findings(
        cls,
        findings: list[ScopeRiskFinding],
        emitted_ids: set[str],
        bom_rows: list[dict[str, Any]],
        resolver_rows: list[dict[str, Any]],
    ) -> None:
        conflicting_rows = [
            item
            for item in bom_rows
            if cls._normalized_text(item.get("completeness_status"), "")
            == "conflicting_quantity"
        ]
        if conflicting_rows:
            cls._add_finding(
                findings,
                emitted_ids,
                category="quantity_conflict",
                section="Quantity Conflicts",
                severity="critical",
                confidence=0.9,
                title="Quantity Conflict Across Source Documents",
                explanation="Conflicting quantities were detected and intentionally remain unresolved.",
                affected_rows=conflicting_rows,
                estimating_impact="Conflicting quantities can materially change material and labor totals.",
                recommended_action="Resolve quantity variances before final pricing and proposal exclusions.",
                likely_owner="Estimator",
                candidate_rfi="Internal draft RFI: Please confirm final quantity for listed items where drawing/spec/schedule counts differ.",
            )

        mismatch_rows = [
            item
            for item in resolver_rows
            if cls._contains_any(item.get("field"), ["quantity"])
        ]
        if mismatch_rows and not conflicting_rows:
            pseudo_rows = [
                {"bom_item_id": cls._normalized_text(item.get("target_id"), "unknown")}
                for item in mismatch_rows
            ]
            cls._add_finding(
                findings,
                emitted_ids,
                category="schedule_drawing_mismatch",
                section="Quantity Conflicts",
                severity="high",
                confidence=0.8,
                title="Schedule and Drawing Mismatch",
                explanation="Resolver detected quantity mismatches across schedule and drawing references.",
                affected_rows=pseudo_rows,
                estimating_impact="Mismatched counts reduce estimate reliability and can delay bid submission.",
                recommended_action="Reconcile schedule and drawing quantities with design team confirmation.",
                likely_owner="Design Engineer",
                candidate_rfi="Internal draft RFI: Please reconcile schedule and drawing quantity discrepancies for referenced systems.",
            )

    @classmethod
    def _emit_engineering_gap_findings(
        cls,
        findings: list[ScopeRiskFinding],
        emitted_ids: set[str],
        bom_rows: list[dict[str, Any]],
        coordination_findings: list[dict[str, Any]],
        risk_rows: list[dict[str, Any]],
    ) -> None:
        unresolved_rows = [
            item
            for item in bom_rows
            if cls._normalized_text(item.get("completeness_status"), "")
            in {"unresolved", "drawing_only", "specification_only", "schedule_only"}
        ]
        if unresolved_rows:
            cls._add_finding(
                findings,
                emitted_ids,
                category="undeveloped_system_design",
                section="Engineering Gaps",
                severity="high",
                confidence=0.76,
                title="Undeveloped System Design",
                explanation="BOM evidence indicates partially defined systems requiring engineering decisions.",
                affected_rows=unresolved_rows,
                estimating_impact="Undeveloped systems drive contingency and can compromise bid competitiveness.",
                recommended_action="Develop a basis-of-design narrative with assumptions and explicit exclusions.",
                likely_owner="Sales Engineer",
                candidate_rfi="Internal draft RFI: Please provide missing performance criteria and final basis-of-design details for unresolved systems.",
            )

        if coordination_findings:
            pseudo_rows = [
                {
                    "bom_item_id": cls._normalized_text(
                        item.get("finding_id"), "finding"
                    ),
                    "system": cls._normalized_text(item.get("category"), "Unknown"),
                    "room_or_area": "Unknown",
                    "source_documents": [],
                    "source_pages": [],
                }
                for item in coordination_findings
            ]
            cls._add_finding(
                findings,
                emitted_ids,
                category="drawing_specification_mismatch",
                section="Engineering Gaps",
                severity="high",
                confidence=0.73,
                title="Drawing and Specification Mismatch",
                explanation="Coordination analysis indicates mismatches between drawing and specification intent.",
                affected_rows=pseudo_rows,
                estimating_impact="Mismatch risk can cause procurement errors and redesign cost.",
                recommended_action="Resolve drawing/spec discrepancies and publish revised coordination notes.",
                likely_owner="Design Engineer",
                candidate_rfi="Internal draft RFI: Please resolve identified drawing/specification mismatches and issue final governing references.",
            )

        textual_gap_categories = [
            (
                "undefined_programming_scope",
                "Programming scope is not clearly defined.",
                "Define control logic, UI scope, and integration responsibilities.",
            ),
            (
                "undefined_commissioning_scope",
                "Commissioning scope is undefined or incomplete.",
                "Clarify commissioning process, duration, and required deliverables.",
            ),
            (
                "undefined_training_scope",
                "Training scope is undefined.",
                "Identify training sessions, audience, and handoff documentation.",
            ),
            (
                "undefined_closeout_scope",
                "Closeout scope is undefined.",
                "Specify closeout package requirements and acceptance criteria.",
            ),
            (
                "undefined_warranty_scope",
                "Warranty scope is undefined.",
                "Confirm warranty term, labor coverage, and response expectations.",
            ),
        ]

        if risk_rows or bom_rows:
            subset = bom_rows[:8] if bom_rows else [{"bom_item_id": "project"}]
            for category, explanation, action in textual_gap_categories:
                cls._add_finding(
                    findings,
                    emitted_ids,
                    category=category,
                    section="Engineering Gaps",
                    severity="medium",
                    confidence=0.66,
                    title=category.replace("_", " ").title(),
                    explanation=explanation,
                    affected_rows=subset,
                    estimating_impact="Undefined post-install scope can materially alter labor and indirect costs.",
                    recommended_action=action,
                    likely_owner="Sales Engineer",
                    candidate_rfi="Internal draft RFI: Please provide explicit scope boundaries and deliverables for this workstream.",
                )

    @classmethod
    def _emit_commercial_risk_findings(
        cls,
        findings: list[ScopeRiskFinding],
        emitted_ids: set[str],
        bom_rows: list[dict[str, Any]],
        risk_rows: list[dict[str, Any]],
    ) -> None:
        text_blob = " ".join(str(item) for item in risk_rows).lower()
        commercial_cases = [
            (
                "add_alternate_ambiguity",
                "Add-alternate scope language appears ambiguous.",
                "Separate base bid and alternate assumptions with explicit pricing boundaries.",
                "Estimator",
            ),
            (
                "allowance_ambiguity",
                "Allowance scope language appears ambiguous.",
                "Clarify allowance inclusions, exclusions, and unit-rate treatment.",
                "Estimator",
            ),
            (
                "discontinued_product_reference",
                "Potential discontinued or obsolete product references were detected.",
                "Validate availability and approved substitutes before bid issue.",
                "Sales Engineer",
            ),
        ]

        for category, explanation, action, owner in commercial_cases:
            trigger = True
            if category == "add_alternate_ambiguity":
                trigger = "alternate" in text_blob or "add-alt" in text_blob
            elif category == "allowance_ambiguity":
                trigger = "allowance" in text_blob
            elif category == "discontinued_product_reference":
                trigger = "discontinued" in text_blob or "obsolete" in text_blob

            if not trigger and not bom_rows:
                continue

            cls._add_finding(
                findings,
                emitted_ids,
                category=category,
                section="Commercial Risks",
                severity="high" if category != "allowance_ambiguity" else "medium",
                confidence=0.7,
                title=category.replace("_", " ").title(),
                explanation=explanation,
                affected_rows=(
                    bom_rows[:10] if bom_rows else [{"bom_item_id": "project"}]
                ),
                estimating_impact="Commercial ambiguity reduces bid defensibility and margin confidence.",
                recommended_action=action,
                likely_owner=owner,
                candidate_rfi="Internal draft RFI: Please clarify commercial language and governing assumptions for this package.",
            )

    @classmethod
    def _emit_mismatch_findings(
        cls,
        findings: list[ScopeRiskFinding],
        emitted_ids: set[str],
        bom_rows: list[dict[str, Any]],
    ) -> None:
        drawing_only = [
            item
            for item in bom_rows
            if cls._normalized_text(item.get("completeness_status"), "")
            == "drawing_only"
        ]
        if drawing_only:
            cls._add_finding(
                findings,
                emitted_ids,
                category="drawing_specification_mismatch",
                section="Engineering Gaps",
                severity="high",
                confidence=0.79,
                title="Drawing-only Items Missing Specification Coverage",
                explanation="Some BOM lines are drawing-only without matching specification references.",
                affected_rows=drawing_only,
                estimating_impact="Specification gaps increase substitution and compliance risk.",
                recommended_action="Confirm whether specification coverage is missing or pending addendum.",
                likely_owner="Design Engineer",
                candidate_rfi="Internal draft RFI: Please confirm governing specification sections for drawing-only BOM items.",
            )

        spec_only = [
            item
            for item in bom_rows
            if cls._normalized_text(item.get("completeness_status"), "")
            == "specification_only"
        ]
        if spec_only:
            cls._add_finding(
                findings,
                emitted_ids,
                category="schedule_drawing_mismatch",
                section="Engineering Gaps",
                severity="medium",
                confidence=0.72,
                title="Specification-only Items Missing Drawing Coverage",
                explanation="Some BOM lines are specification-only without matching drawing references.",
                affected_rows=spec_only,
                estimating_impact="Missing drawing references can cause installation uncertainty and labor variance.",
                recommended_action="Verify drawing coverage and identify required detail references.",
                likely_owner="Sales Engineer",
                candidate_rfi="Internal draft RFI: Please identify drawing references for listed specification-only BOM lines.",
            )

    @classmethod
    def _augment_candidate_rfi_from_pool(
        cls,
        findings: list[ScopeRiskFinding],
        rfi_rows: list[dict[str, Any]],
    ) -> None:
        if not rfi_rows:
            return
        pool = [
            cls._normalized_text(item.get("title") or item.get("rfi_id"), "")
            for item in rfi_rows
            if cls._normalized_text(item.get("title") or item.get("rfi_id"), "")
        ]
        if not pool:
            return
        for index, finding in enumerate(findings):
            if finding.candidate_rfi_text:
                continue
            finding.candidate_rfi_text = (
                "Internal draft RFI: " + pool[index % len(pool)]
            )

    @classmethod
    def _add_finding(
        cls,
        findings: list[ScopeRiskFinding],
        emitted_ids: set[str],
        *,
        category: str,
        section: str,
        severity: str,
        confidence: float,
        title: str,
        explanation: str,
        affected_rows: list[dict[str, Any]],
        estimating_impact: str,
        recommended_action: str,
        likely_owner: str,
        candidate_rfi: str,
    ) -> None:
        finding_id = f"scope-risk:{category}"
        if finding_id in emitted_ids:
            return

        bom_items = sorted(
            {
                cls._normalized_text(row.get("bom_item_id"), "")
                for row in affected_rows
                if cls._normalized_text(row.get("bom_item_id"), "")
            }
        )
        systems = sorted(
            {
                cls._normalized_text(row.get("system"), "Unknown")
                for row in affected_rows
                if cls._normalized_text(row.get("system"), "")
            }
        )
        rooms = sorted(
            {
                cls._normalized_text(
                    row.get("room_or_area") or row.get("room"),
                    "Unknown",
                )
                for row in affected_rows
                if cls._normalized_text(row.get("room_or_area") or row.get("room"), "")
            }
        )

        references: set[str] = set()
        for row in affected_rows:
            for source_file in list(row.get("source_documents") or []):
                references.add(cls._normalized_text(source_file, ""))
            for page in list(row.get("source_pages") or []):
                if cls._normalized_text(page, ""):
                    references.add(f"p.{cls._normalized_text(page, '')}")
            for item in list(row.get("drawing_references") or []):
                references.add(cls._normalized_text(item, ""))
            for item in list(row.get("specification_references") or []):
                references.add(cls._normalized_text(item, ""))

        impact_score = {
            "critical": 3,
            "high": 2,
            "medium": 1,
            "low": 0,
        }.get(severity.lower(), 1)

        findings.append(
            ScopeRiskFinding(
                finding_id=finding_id,
                category=category,
                severity=severity,
                confidence=max(0.0, min(confidence, 1.0)),
                title=title,
                concise_explanation=explanation,
                affected_bom_items=bom_items,
                affected_systems=systems,
                affected_rooms=rooms,
                source_references=sorted(item for item in references if item),
                estimating_impact=estimating_impact,
                recommended_action=recommended_action,
                likely_owner=likely_owner,
                candidate_rfi_text=candidate_rfi,
                section=section,
                impact_score=impact_score,
            )
        )
        emitted_ids.add(finding_id)

    @staticmethod
    def _contains_any(value: Any, needles: list[str]) -> bool:
        hay = str(value or "").lower()
        return any(needle.lower() in hay for needle in needles if needle)

    @staticmethod
    def _normalized_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

"""Internal sales/design engineer review synthesis for project analysis outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


@dataclass
class SalesDesignEngineerReview:
    project_summary: dict[str, Any]
    inferred_customer_and_stakeholder_information: list[str]
    project_type: str
    major_systems: list[str]
    bom_summary: dict[str, Any]
    missing_bom_detail: list[str]
    undeveloped_scope: list[str]
    major_risk_areas: list[str]
    responsibility_gaps: list[str]
    quantity_conflicts: list[str]
    drawing_specification_coordination_issues: list[str]
    product_lifecycle_warnings: list[str]
    preliminary_cost_coverage: dict[str, Any]
    labor_confidence: str
    recommended_rfis: list[str]
    recommended_next_actions: list[str]
    overall_confidence: float
    limitations: list[str]
    traceability_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SalesDesignReviewService:
    def build_review(
        self,
        *,
        summary: dict[str, Any],
        bom_rows: list[dict[str, Any]],
        scope_findings: list[dict[str, Any]],
    ) -> SalesDesignEngineerReview:
        major_systems = self._major_systems(bom_rows)
        bom_summary = self._bom_summary(bom_rows)
        missing_bom_detail = self._missing_bom_detail(bom_rows)
        undeveloped_scope = self._findings_by_section(scope_findings, "Missing Scope")
        major_risk_areas = self._risk_areas(scope_findings)
        responsibility_gaps = self._findings_by_section(
            scope_findings,
            "Responsibility Gaps",
        )
        quantity_conflicts = self._findings_by_category(
            scope_findings,
            "quantity_conflict",
        )
        drawing_spec_coordination = [
            *self._findings_by_category(
                scope_findings,
                "drawing_specification_mismatch",
            ),
            *self._findings_by_category(
                scope_findings,
                "schedule_drawing_mismatch",
            ),
        ]
        lifecycle_warnings = self._product_lifecycle_warnings(bom_rows)
        cost_coverage = self._cost_coverage(bom_rows)
        labor_confidence = self._labor_confidence(summary)
        recommended_rfis = self._recommended_rfis(scope_findings)
        recommended_next_actions = self._recommended_next_actions(
            summary, scope_findings
        )
        limitations = self._limitations(summary, bom_rows, scope_findings)
        overall_confidence = self._overall_confidence(summary, bom_rows, scope_findings)

        inferred_stakeholders = [
            item
            for item in [
                self._text(summary.get("customer"), ""),
                self._text(summary.get("project_name"), ""),
                self._text(summary.get("project_type"), ""),
            ]
            if item
        ]

        traceability = [
            "Conclusions are derived from canonical BOM, scope/risk findings, resolver conflicts, and source references.",
            "Unsupported engineering decisions are intentionally excluded and listed under limitations.",
        ]

        return SalesDesignEngineerReview(
            project_summary={
                "project_name": summary.get("project_name"),
                "analysis_status": summary.get("analysis_status"),
                "document_count": summary.get("document_count"),
                "recommended_next_action": summary.get("recommended_next_action"),
            },
            inferred_customer_and_stakeholder_information=inferred_stakeholders,
            project_type=self._text(summary.get("project_type"), "Unspecified"),
            major_systems=major_systems,
            bom_summary=bom_summary,
            missing_bom_detail=missing_bom_detail,
            undeveloped_scope=undeveloped_scope,
            major_risk_areas=major_risk_areas,
            responsibility_gaps=responsibility_gaps,
            quantity_conflicts=quantity_conflicts,
            drawing_specification_coordination_issues=drawing_spec_coordination,
            product_lifecycle_warnings=lifecycle_warnings,
            preliminary_cost_coverage=cost_coverage,
            labor_confidence=labor_confidence,
            recommended_rfis=recommended_rfis,
            recommended_next_actions=recommended_next_actions,
            overall_confidence=overall_confidence,
            limitations=limitations,
            traceability_notes=traceability,
        )

    def to_markdown(self, review: SalesDesignEngineerReview) -> str:
        data = review.to_dict()
        lines = [
            f"# Internal Sales / Design Engineer Review - {self._text(data['project_summary'].get('project_name'), 'Project')}",
            "",
            "## 1. What Atlas Found",
            f"- Project Type: {data['project_type']}",
            f"- Major Systems: {', '.join(data['major_systems']) or 'None'}",
            f"- BOM Summary: {json.dumps(data['bom_summary'], sort_keys=True)}",
            f"- Overall Confidence: {int(float(data['overall_confidence']) * 100)}%",
            "",
            "## 2. What Appears Complete",
            f"- Complete BOM lines: {data['bom_summary'].get('complete_lines', 0)}",
            f"- Preliminary cost coverage: {data['preliminary_cost_coverage'].get('known_cost_coverage_ratio', '0%')}",
            f"- Labor confidence: {data['labor_confidence']}",
            "",
            "## 3. What Is Missing",
            *[
                f"- {item}"
                for item in (
                    data["missing_bom_detail"]
                    or ["No major missing BOM detail detected."]
                )
            ],
            "",
            "## 4. What Is Risky",
            *[
                f"- {item}"
                for item in (
                    data["major_risk_areas"] or ["No major high-risk areas detected."]
                )
            ],
            "",
            "## 5. What Needs Clarification",
            *[
                f"- {item}"
                for item in (
                    data["responsibility_gaps"]
                    or ["No major responsibility gaps detected."]
                )
            ],
            *[f"- Quantity conflict: {item}" for item in data["quantity_conflicts"]],
            *[
                f"- Coordination: {item}"
                for item in data["drawing_specification_coordination_issues"]
            ],
            "",
            "## 6. What Should Happen Next",
            *[
                f"- {item}"
                for item in (
                    data["recommended_next_actions"] or ["No next actions generated."]
                )
            ],
            "",
            "## Recommended RFIs",
            *[
                f"- {item}"
                for item in (data["recommended_rfis"] or ["No RFIs generated."])
            ],
            "",
            "## Limitations",
            *[f"- {item}" for item in data["limitations"]],
            "",
            "## Appendix: Traceability",
            *[f"- {item}" for item in data["traceability_notes"]],
        ]
        return "\n".join(lines)

    def to_json(self, review: SalesDesignEngineerReview) -> str:
        return json.dumps(review.to_dict(), indent=2, sort_keys=True)

    def to_html(self, review: SalesDesignEngineerReview) -> str:
        data = review.to_dict()

        def _items(items: list[str]) -> str:
            if not items:
                return "<li>None</li>"
            return "".join([f"<li>{self._escape(item)}</li>" for item in items])

        return (
            "<html><head><meta charset='utf-8'><title>Sales Design Review</title>"
            "<style>body{font-family:Arial,sans-serif;line-height:1.4;padding:20px}"
            "h2{margin-top:24px} .muted{color:#666;font-size:12px}</style></head><body>"
            f"<h1>Internal Sales / Design Engineer Review - {self._escape(self._text(data['project_summary'].get('project_name'), 'Project'))}</h1>"
            "<h2>1. What Atlas Found</h2>"
            f"<p>Project type: {self._escape(data['project_type'])}<br/>"
            f"Major systems: {self._escape(', '.join(data['major_systems']) or 'None')}<br/>"
            f"Overall confidence: {int(float(data['overall_confidence']) * 100)}%</p>"
            "<h2>2. What Appears Complete</h2>"
            f"<p>Complete BOM lines: {data['bom_summary'].get('complete_lines', 0)}<br/>"
            f"Cost coverage: {self._escape(self._text(data['preliminary_cost_coverage'].get('known_cost_coverage_ratio'), '0%'))}<br/>"
            f"Labor confidence: {self._escape(data['labor_confidence'])}</p>"
            "<h2>3. What Is Missing</h2><ul>"
            + _items(data["missing_bom_detail"])
            + "</ul><h2>4. What Is Risky</h2><ul>"
            + _items(data["major_risk_areas"])
            + "</ul><h2>5. What Needs Clarification</h2><ul>"
            + _items(data["responsibility_gaps"] + data["quantity_conflicts"])
            + "</ul><h2>6. What Should Happen Next</h2><ul>"
            + _items(data["recommended_next_actions"])
            + "</ul><h2>Recommended RFIs</h2><ul>"
            + _items(data["recommended_rfis"])
            + "</ul><h2>Limitations</h2><ul>"
            + _items(data["limitations"])
            + "</ul><p class='muted'>Internal draft only. Unsupported conclusions are labeled in limitations.</p></body></html>"
        )

    def _major_systems(self, bom_rows: list[dict[str, Any]]) -> list[str]:
        counts: dict[str, int] = {}
        for row in bom_rows:
            system = self._text(row.get("system"), "Unknown")
            counts[system] = counts.get(system, 0) + 1
        return [
            item[0]
            for item in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
        ]

    def _bom_summary(self, bom_rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(bom_rows)
        complete = sum(
            1
            for row in bom_rows
            if self._text(row.get("completeness_status"), "") == "complete"
        )
        conflicts = sum(
            1
            for row in bom_rows
            if self._text(row.get("completeness_status"), "") == "conflicting_quantity"
        )
        return {
            "total_lines": total,
            "complete_lines": complete,
            "incomplete_lines": max(total - complete - conflicts, 0),
            "conflicting_lines": conflicts,
        }

    def _missing_bom_detail(self, bom_rows: list[dict[str, Any]]) -> list[str]:
        issues = []
        states = [self._text(row.get("completeness_status"), "") for row in bom_rows]
        for state in [
            "missing_manufacturer",
            "missing_model",
            "missing_quantity",
            "generic_description",
            "unresolved",
        ]:
            count = sum(1 for item in states if item == state)
            if count:
                issues.append(f"{state.replace('_', ' ').title()}: {count} line(s)")
        return issues

    def _risk_areas(self, findings: list[dict[str, Any]]) -> list[str]:
        rows = [
            item
            for item in findings
            if self._text(item.get("severity"), "").lower() in {"critical", "high"}
        ]
        return [
            f"{self._text(item.get('title'), 'Risk')}: {self._text(item.get('estimating_impact'), 'Impact not stated')}"
            for item in rows[:10]
        ]

    def _findings_by_section(
        self,
        findings: list[dict[str, Any]],
        section: str,
    ) -> list[str]:
        return [
            self._text(item.get("title"), "Finding")
            for item in findings
            if self._text(item.get("section"), "") == section
        ]

    def _findings_by_category(
        self,
        findings: list[dict[str, Any]],
        category: str,
    ) -> list[str]:
        return [
            self._text(item.get("title"), "Finding")
            for item in findings
            if self._text(item.get("category"), "") == category
        ]

    def _product_lifecycle_warnings(self, bom_rows: list[dict[str, Any]]) -> list[str]:
        warnings: list[str] = []
        for row in bom_rows:
            text = self._text(row.get("pricing_warning"), "")
            if not text:
                continue
            if "expired" in text.lower() or "discontinued" in text.lower():
                warnings.append(f"{self._text(row.get('bom_item_id'), 'item')}: {text}")
        return warnings

    def _cost_coverage(self, bom_rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(bom_rows)
        known_cost_rows = sum(
            1 for row in bom_rows if row.get("known_cost") is not None
        )
        list_price_rows = sum(
            1 for row in bom_rows if row.get("list_price") is not None
        )
        ratio = "0%"
        if total > 0:
            ratio = f"{int((known_cost_rows / total) * 100)}%"
        return {
            "lines_with_known_cost": known_cost_rows,
            "lines_with_list_price": list_price_rows,
            "known_cost_coverage_ratio": ratio,
        }

    def _labor_confidence(self, summary: dict[str, Any]) -> str:
        high_risk = int(summary.get("high_risk_issue_count", 0) or 0)
        if high_risk >= 8:
            return "Low"
        if high_risk >= 3:
            return "Medium"
        return "High"

    def _recommended_rfis(self, findings: list[dict[str, Any]]) -> list[str]:
        rfis = [
            self._text(item.get("candidate_rfi_text"), "")
            for item in findings
            if self._text(item.get("candidate_rfi_text"), "")
        ]
        return rfis[:12]

    def _recommended_next_actions(
        self,
        summary: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> list[str]:
        actions: list[str] = []
        actions.extend(
            [
                self._text(item.get("recommended_action"), "")
                for item in findings
                if self._text(item.get("recommended_action"), "")
            ]
        )
        summary_action = self._text(summary.get("recommended_next_action"), "")
        if summary_action:
            actions.append(summary_action)

        ordered: list[str] = []
        seen: set[str] = set()
        for item in actions:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered[:12]

    def _limitations(
        self,
        summary: dict[str, Any],
        bom_rows: list[dict[str, Any]],
        findings: list[dict[str, Any]],
    ) -> list[str]:
        limitations = [
            "Unsupported conclusion label: Atlas does not finalize engineering design decisions without explicit source evidence.",
            "Unsupported conclusion label: Atlas does not replace consultant intent, stamped drawings, or owner-issued clarifications.",
        ]
        if not bom_rows:
            limitations.append(
                "Unsupported conclusion label: BOM evidence is limited; pricing and scope confidence are preliminary."
            )
        if not findings:
            limitations.append(
                "Unsupported conclusion label: Scope/risk findings are limited; additional intake documents may be required."
            )
        if int(summary.get("document_count", 0) or 0) == 0:
            limitations.append(
                "Unsupported conclusion label: No source documents were available for analysis."
            )
        return limitations

    def _overall_confidence(
        self,
        summary: dict[str, Any],
        bom_rows: list[dict[str, Any]],
        findings: list[dict[str, Any]],
    ) -> float:
        if not bom_rows:
            return 0.35

        complete_ratio = sum(
            1
            for row in bom_rows
            if self._text(row.get("completeness_status"), "") == "complete"
        ) / max(len(bom_rows), 1)

        high_risk = sum(
            1
            for row in findings
            if self._text(row.get("severity"), "").lower() in {"critical", "high"}
        )
        risk_penalty = min(0.4, high_risk * 0.03)

        base = 0.55 + (complete_ratio * 0.35) - risk_penalty
        if int(summary.get("documents_requiring_ocr", 0) or 0) > 0:
            base -= 0.08
        return round(max(0.0, min(base, 1.0)), 2)

    def _text(self, value: Any, default: str) -> str:
        if value is None:
            return default
        normalized = str(value).strip()
        return normalized if normalized else default

    def _escape(self, value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

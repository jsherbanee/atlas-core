"""Estimator brief helpers for Atlas Core services."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlas_core.domain import BidPackageReview


@dataclass
class EstimatorBriefEvidenceRef:
    source_type: str
    source_id: str
    field: str | None = None
    excerpt: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "field": self.field,
            "excerpt": self.excerpt,
        }


@dataclass
class EstimatorReviewerAction:
    action_id: str
    priority: str
    title: str
    description: str
    reason: str
    related_risks: list[str]
    source_refs: list[EstimatorBriefEvidenceRef]
    suggested_owner_role: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "reason": self.reason,
            "related_risks": list(self.related_risks),
            "source_refs": [source_ref.to_dict() for source_ref in self.source_refs],
            "suggested_owner_role": self.suggested_owner_role,
        }


@dataclass
class EstimatorBrief:
    review_id: str
    project_id: str
    name: str
    drawing_count: int
    specification_count: int
    system_count: int
    equipment_count: int
    room_count: int
    detail_callout_count: int
    issue_count: int
    placeholder_count: int
    review_required_count: int
    cross_reference_count: int
    reconciliation_issue_count: int
    scope_gap_count: int
    estimator_risk_count: int
    keynote_count: int
    legend_count: int
    legend_item_count: int
    confidence: float
    engineering_assumption_count: int = 0
    bid_completeness_score: float | None = None
    bid_completeness_status: str | None = None
    readiness_status: str | None = None
    readiness_message: str | None = None
    recommendation_count: int = 0
    brief_title: str = ""
    executive_summary: str = ""
    readiness_summary: dict[str, Any] | None = None
    top_blockers: list[str] | None = None
    top_warnings: list[str] | None = None
    key_rfi_candidates: list[dict[str, Any]] | None = None
    labor_summary: dict[str, Any] | None = None
    revision_summary: dict[str, Any] | None = None
    assumption_summary: dict[str, Any] | None = None
    missing_scope_summary: dict[str, Any] | None = None
    prioritized_reviewer_actions: list[dict[str, Any]] | None = None
    evidence_refs: list[dict[str, Any]] | None = None
    created_by_engine_version: str = "estimator-brief-service/2.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EstimatorBriefService:
    ENGINE_VERSION = "estimator-brief-service/2.0.0"

    _PRIORITY_RANK = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }

    def build_brief(self, review: BidPackageReview) -> EstimatorBrief:
        readiness = getattr(review, "readiness", None)
        readiness_summary = self._readiness_summary(review)
        top_blockers = list(getattr(readiness, "blocking_issues", []) or [])[:5]
        top_warnings = list(getattr(readiness, "warnings", []) or [])[:5]
        key_rfi_candidates = self._key_rfi_candidates(review)
        labor_summary = self._labor_summary(review)
        revision_summary = self._revision_summary(review)
        assumption_summary = self._assumption_summary(review)
        missing_scope_summary = self._missing_scope_summary(review)
        actions = self._prioritized_reviewer_actions(review)
        evidence_refs = self._collect_evidence_refs(
            review=review,
            actions=actions,
            key_rfi_candidates=key_rfi_candidates,
            missing_scope_summary=missing_scope_summary,
        )

        executive_summary = self._executive_summary(
            review=review,
            readiness_summary=readiness_summary,
            top_blockers=top_blockers,
            top_warnings=top_warnings,
            actions=actions,
        )

        return EstimatorBrief(
            review_id=review.review_id,
            project_id=review.project_id,
            name=review.name,
            drawing_count=review.drawing_count(),
            specification_count=review.specification_count(),
            system_count=len(review.systems),
            equipment_count=review.equipment_count(),
            room_count=review.room_count(),
            detail_callout_count=review.detail_callout_count(),
            issue_count=review.issue_count(),
            placeholder_count=self._placeholder_count(review),
            review_required_count=self._review_required_count(review),
            cross_reference_count=review.cross_reference_count(),
            reconciliation_issue_count=review.reconciliation_issue_count(),
            scope_gap_count=review.scope_gap_count(),
            estimator_risk_count=review.estimator_risk_count(),
            engineering_assumption_count=len(
                list(getattr(review, "engineering_assumptions", []) or [])
            ),
            keynote_count=review.keynote_count(),
            legend_count=review.legend_count(),
            legend_item_count=review.legend_item_count(),
            recommendation_count=review.recommendation_count(),
            confidence=review.confidence,
            bid_completeness_score=self._bid_completeness_score(review),
            bid_completeness_status=self._bid_completeness_status(review),
            readiness_status=self._readiness_status(review),
            readiness_message=self._readiness_message(review),
            brief_title=f"Estimator Brief - {review.name}",
            executive_summary=executive_summary,
            readiness_summary=readiness_summary,
            top_blockers=top_blockers,
            top_warnings=top_warnings,
            key_rfi_candidates=key_rfi_candidates,
            labor_summary=labor_summary,
            revision_summary=revision_summary,
            assumption_summary=assumption_summary,
            missing_scope_summary=missing_scope_summary,
            prioritized_reviewer_actions=[action.to_dict() for action in actions],
            evidence_refs=[evidence_ref.to_dict() for evidence_ref in evidence_refs],
            created_by_engine_version=self.ENGINE_VERSION,
        )

    def _readiness_summary(self, review: BidPackageReview) -> dict[str, Any]:
        readiness = getattr(review, "readiness", None)
        if readiness is None:
            return {
                "status": self._readiness_status(review),
                "message": self._readiness_message(review),
                "readiness_score": None,
                "readiness_level": None,
                "section_scores": {},
            }

        return {
            "status": self._value(getattr(readiness, "status", None)),
            "message": self._readiness_message(review),
            "readiness_score": getattr(readiness, "readiness_score", None),
            "readiness_level": self._value(getattr(readiness, "readiness_level", None)),
            "section_scores": dict(getattr(readiness, "section_scores", {}) or {}),
        }

    def _key_rfi_candidates(self, review: BidPackageReview) -> list[dict[str, Any]]:
        def sort_key(candidate: Any) -> tuple[int, float, str]:
            severity = self._value(getattr(candidate, "severity", None))
            severity_rank = {
                "critical": 4,
                "high": 3,
                "medium": 2,
                "low": 1,
            }.get(str(severity), 0)
            confidence = float(getattr(candidate, "confidence", 0.0) or 0.0)
            candidate_id = str(getattr(candidate, "candidate_id", ""))
            return (severity_rank, confidence, candidate_id)

        ranked = sorted(review.rfi_candidates, key=sort_key, reverse=True)
        result: list[dict[str, Any]] = []
        for candidate in ranked[:5]:
            result.append(
                {
                    "candidate_id": getattr(candidate, "candidate_id", None),
                    "title": getattr(candidate, "title", None),
                    "severity": self._value(getattr(candidate, "severity", None)),
                    "confidence": getattr(candidate, "confidence", None),
                    "detected_condition": getattr(
                        candidate, "detected_condition", None
                    ),
                    "recommended_action": getattr(
                        candidate, "recommended_action", None
                    ),
                }
            )

        return result

    def _labor_summary(self, review: BidPackageReview) -> dict[str, Any]:
        labor = getattr(review, "labor_estimate", None)
        if labor is None:
            return {
                "available": False,
                "confidence": None,
                "risk_factors": [],
                "warnings": ["Labor estimate is unavailable."],
            }

        risk_factors = sorted(
            {
                risk
                for category in getattr(labor, "labor_categories", [])
                for risk in getattr(category, "risk_factors", [])
            }
        )
        return {
            "available": True,
            "confidence": getattr(labor, "confidence", None),
            "total_labor_hours_expected": getattr(
                labor, "total_labor_hours_expected", None
            ),
            "risk_factors": risk_factors,
            "warnings": list(getattr(labor, "warnings", []) or []),
        }

    def _revision_summary(self, review: BidPackageReview) -> dict[str, Any]:
        revision = getattr(review, "revision_comparison", None)
        if revision is None:
            return {
                "available": False,
                "confidence": None,
                "change_count": 0,
                "high_or_critical_changes": 0,
                "summary": "No revision comparison provided for this brief.",
            }

        high_or_critical = sum(
            1
            for change in getattr(revision, "changes", [])
            if self._value(getattr(change, "severity", None)) in {"high", "critical"}
        )
        return {
            "available": True,
            "confidence": getattr(revision, "confidence", None),
            "change_count": len(getattr(revision, "changes", []) or []),
            "high_or_critical_changes": high_or_critical,
            "summary": (
                f"Revision comparison contains {len(getattr(revision, 'changes', []) or [])} "
                f"changes with {high_or_critical} high/critical impacts."
            ),
        }

    def _assumption_summary(self, review: BidPackageReview) -> dict[str, Any]:
        assumptions = list(getattr(review, "engineering_assumptions", []) or [])
        risk_count = sum(
            1
            for assumption in assumptions
            if self._value(getattr(assumption, "severity", None)) == "risk"
        )
        return {
            "total_count": len(assumptions),
            "risk_count": risk_count,
            "review_count": sum(
                1
                for assumption in assumptions
                if self._value(getattr(assumption, "severity", None)) == "review"
            ),
            "informational_count": sum(
                1
                for assumption in assumptions
                if self._value(getattr(assumption, "severity", None)) == "informational"
            ),
        }

    def _missing_scope_summary(self, review: BidPackageReview) -> dict[str, Any]:
        readiness = getattr(review, "readiness", None)
        diagnostics = list(getattr(readiness, "missing_scope_diagnostics", []) or [])
        return {
            "diagnostic_count": len(diagnostics),
            "diagnostics": diagnostics[:10],
        }

    def _prioritized_reviewer_actions(
        self,
        review: BidPackageReview,
    ) -> list[EstimatorReviewerAction]:
        readiness = getattr(review, "readiness", None)
        actions: list[EstimatorReviewerAction] = []

        for blocker in list(getattr(readiness, "blocking_issues", []) or []):
            actions.append(
                self._build_action(
                    priority="critical",
                    title="Resolve readiness blocker",
                    description=blocker,
                    reason="Blocking issue prevents bid-ready status.",
                    related_risks=["readiness_blocker"],
                    source_refs=self._readiness_evidence_refs(review),
                    suggested_owner_role="estimator",
                )
            )

        for warning in list(getattr(readiness, "warnings", []) or [])[:3]:
            actions.append(
                self._build_action(
                    priority="high",
                    title="Address readiness warning",
                    description=warning,
                    reason="Warning indicates unresolved estimating risk.",
                    related_risks=["readiness_warning"],
                    source_refs=self._readiness_evidence_refs(review),
                    suggested_owner_role="discipline_lead",
                )
            )

        for candidate in self._key_rfi_candidates(review)[:3]:
            severity = str(candidate.get("severity") or "low")
            actions.append(
                self._build_action(
                    priority=("critical" if severity == "critical" else "high"),
                    title="Review high-impact RFI candidate",
                    description=str(candidate.get("title") or "RFI candidate issue"),
                    reason="RFI candidate ambiguity affects bid inclusions.",
                    related_risks=[
                        str(candidate.get("detected_condition") or "rfi_candidate_risk")
                    ],
                    source_refs=[
                        EstimatorBriefEvidenceRef(
                            source_type="rfi_candidate",
                            source_id=str(candidate.get("candidate_id") or "unknown"),
                            field="detected_condition",
                            excerpt=str(candidate.get("detected_condition") or ""),
                        )
                    ],
                    suggested_owner_role="systems_engineer",
                )
            )

        labor = getattr(review, "labor_estimate", None)
        if labor is not None and float(getattr(labor, "confidence", 0.0) or 0.0) < 0.7:
            actions.append(
                self._build_action(
                    priority="high",
                    title="Recalibrate labor confidence",
                    description=(
                        "Labor estimate confidence is below preferred threshold for bid carry."
                    ),
                    reason="Low labor confidence increases estimate volatility.",
                    related_risks=["labor_confidence_low"],
                    source_refs=[
                        EstimatorBriefEvidenceRef(
                            source_type="labor_estimate",
                            source_id=str(review.review_id),
                            field="confidence",
                            excerpt=f"confidence={getattr(labor, 'confidence', None)}",
                        )
                    ],
                    suggested_owner_role="estimator",
                )
            )

        revision = getattr(review, "revision_comparison", None)
        if revision is not None:
            high_or_critical = [
                change
                for change in getattr(revision, "changes", [])
                if self._value(getattr(change, "severity", None))
                in {"high", "critical"}
            ]
            if high_or_critical:
                actions.append(
                    self._build_action(
                        priority="high",
                        title="Review high-impact revision deltas",
                        description=(
                            f"{len(high_or_critical)} high/critical revision changes need estimator alignment."
                        ),
                        reason="Revision deltas can shift scope and labor assumptions.",
                        related_risks=["revision_instability"],
                        source_refs=[
                            EstimatorBriefEvidenceRef(
                                source_type="revision_comparison",
                                source_id=str(
                                    getattr(
                                        revision,
                                        "comparison_revision_id",
                                        review.review_id,
                                    )
                                ),
                                field="changes",
                                excerpt=f"high_or_critical={len(high_or_critical)}",
                            )
                        ],
                        suggested_owner_role="project_manager",
                    )
                )

        unique_actions: dict[str, EstimatorReviewerAction] = {}
        for action in actions:
            dedupe_key = f"{action.priority}|{action.title}|{action.description}"
            unique_actions[dedupe_key] = action

        ranked = sorted(
            unique_actions.values(),
            key=lambda action: (
                -self._PRIORITY_RANK.get(action.priority, 0),
                action.title,
                action.action_id,
            ),
        )
        return ranked

    def _collect_evidence_refs(
        self,
        review: BidPackageReview,
        actions: list[EstimatorReviewerAction],
        key_rfi_candidates: list[dict[str, Any]],
        missing_scope_summary: dict[str, Any],
    ) -> list[EstimatorBriefEvidenceRef]:
        refs: dict[tuple[str, str, str], EstimatorBriefEvidenceRef] = {}

        refs[("review", review.review_id, "review")] = EstimatorBriefEvidenceRef(
            source_type="review",
            source_id=review.review_id,
            excerpt=review.name,
        )

        readiness = getattr(review, "readiness", None)
        for evidence_ref in getattr(readiness, "evidence_refs", []) or []:
            source_type = str(getattr(evidence_ref, "source_type", "readiness"))
            source_id = str(getattr(evidence_ref, "source_id", "unknown"))
            field = str(getattr(evidence_ref, "field", "") or "")
            refs[(source_type, source_id, field)] = EstimatorBriefEvidenceRef(
                source_type=source_type,
                source_id=source_id,
                field=field or None,
                excerpt=getattr(evidence_ref, "excerpt", None),
            )

        for action in actions:
            for source_ref in action.source_refs:
                field = source_ref.field or ""
                refs[(source_ref.source_type, source_ref.source_id, field)] = source_ref

        for candidate in key_rfi_candidates:
            candidate_id = str(candidate.get("candidate_id") or "unknown")
            refs[("rfi_candidate", candidate_id, "detected_condition")] = (
                EstimatorBriefEvidenceRef(
                    source_type="rfi_candidate",
                    source_id=candidate_id,
                    field="detected_condition",
                    excerpt=str(candidate.get("detected_condition") or ""),
                )
            )

        if missing_scope_summary.get("diagnostic_count", 0) > 0:
            refs[("missing_scope", review.review_id, "diagnostics")] = (
                EstimatorBriefEvidenceRef(
                    source_type="missing_scope",
                    source_id=review.review_id,
                    field="diagnostics",
                    excerpt=str(missing_scope_summary.get("diagnostic_count")),
                )
            )

        return sorted(refs.values(), key=lambda ref: (ref.source_type, ref.source_id))

    def _readiness_evidence_refs(
        self,
        review: BidPackageReview,
    ) -> list[EstimatorBriefEvidenceRef]:
        readiness = getattr(review, "readiness", None)
        refs: list[EstimatorBriefEvidenceRef] = []
        for evidence_ref in list(getattr(readiness, "evidence_refs", []) or [])[:3]:
            refs.append(
                EstimatorBriefEvidenceRef(
                    source_type=str(getattr(evidence_ref, "source_type", "readiness")),
                    source_id=str(getattr(evidence_ref, "source_id", "unknown")),
                    field=getattr(evidence_ref, "field", None),
                    excerpt=getattr(evidence_ref, "excerpt", None),
                )
            )

        if not refs:
            refs.append(
                EstimatorBriefEvidenceRef(
                    source_type="readiness",
                    source_id=review.review_id,
                    field="status",
                    excerpt=str(self._readiness_status(review) or "unknown"),
                )
            )

        return refs

    def _build_action(
        self,
        priority: str,
        title: str,
        description: str,
        reason: str,
        related_risks: list[str],
        source_refs: list[EstimatorBriefEvidenceRef],
        suggested_owner_role: str,
    ) -> EstimatorReviewerAction:
        action_key = "|".join([priority, title, description, suggested_owner_role])
        action_id = f"act-{hashlib.sha1(action_key.encode('utf-8')).hexdigest()[:10]}"
        return EstimatorReviewerAction(
            action_id=action_id,
            priority=priority,
            title=title,
            description=description,
            reason=reason,
            related_risks=sorted(set(related_risks)),
            source_refs=source_refs,
            suggested_owner_role=suggested_owner_role,
        )

    def _executive_summary(
        self,
        review: BidPackageReview,
        readiness_summary: dict[str, Any],
        top_blockers: list[str],
        top_warnings: list[str],
        actions: list[EstimatorReviewerAction],
    ) -> str:
        readiness_level = str(readiness_summary.get("readiness_level") or "unknown")
        readiness_score = readiness_summary.get("readiness_score")
        return (
            f"{review.name}: readiness level {readiness_level}"
            f" (score={readiness_score}), with {len(top_blockers)} blockers,"
            f" {len(top_warnings)} warnings, and {len(actions)} prioritized"
            " reviewer actions."
        )

    @classmethod
    def _bid_completeness_score(cls, review: BidPackageReview) -> float | None:
        bid_completeness = getattr(review, "bid_completeness", None)
        if bid_completeness is None:
            return None

        return float(bid_completeness.score)

    @classmethod
    def _bid_completeness_status(cls, review: BidPackageReview) -> str | None:
        bid_completeness = getattr(review, "bid_completeness", None)
        if bid_completeness is None:
            return None

        return str(getattr(bid_completeness.status, "value", bid_completeness.status))

    @classmethod
    def _readiness_status(cls, review: BidPackageReview) -> str | None:
        readiness = getattr(review, "readiness", None)
        if readiness is None:
            return None

        return str(getattr(readiness.status, "value", readiness.status))

    @classmethod
    def _readiness_message(cls, review: BidPackageReview) -> str | None:
        readiness = getattr(review, "readiness", None)
        if readiness is None:
            return None

        return str(readiness.message)

    @classmethod
    def _placeholder_count(cls, review: BidPackageReview) -> int:
        return sum(
            1
            for equipment in review.equipment
            if cls._value(getattr(equipment, "status", None)) == "placeholder"
        )

    @classmethod
    def _review_required_count(cls, review: BidPackageReview) -> int:
        equipment_count = sum(
            1
            for equipment in review.equipment
            if getattr(equipment, "review_required", False) is True
        )
        return equipment_count + len(review.review_report)

    @staticmethod
    def _value(value: Any) -> Any:
        return getattr(value, "value", value)

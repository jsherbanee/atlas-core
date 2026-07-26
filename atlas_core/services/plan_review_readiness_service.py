"""Plan review readiness assessment for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from atlas_core.domain.bid_package_review import BidPackageReview


class ReadinessStatus(str, Enum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    NOT_READY = "not_ready"


class ReadinessLevel(str, Enum):
    NOT_READY = "not_ready"
    NEEDS_REVIEW = "needs_review"
    BID_READY_WITH_ASSUMPTIONS = "bid_ready_with_assumptions"
    BID_READY = "bid_ready"


@dataclass
class ReadinessEvidenceRef:
    source_type: str
    source_id: str
    field: str | None = None
    excerpt: str | None = None

    def __post_init__(self) -> None:
        self.source_type = self._normalize_required_text(
            "source_type", self.source_type
        )
        self.source_id = self._normalize_required_text("source_id", self.source_id)
        self.field = self._normalize_optional_text(self.field)
        self.excerpt = self._normalize_optional_text(self.excerpt)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "field": self.field,
            "excerpt": self.excerpt,
        }

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


@dataclass
class PlanReviewReadiness:
    status: ReadinessStatus
    message: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    project_id: str = ""
    readiness_score: float = 0.0
    readiness_level: ReadinessLevel = ReadinessLevel.NOT_READY
    section_scores: dict[str, float] = field(default_factory=dict)
    blocking_issues: list[str] = field(default_factory=list)
    missing_scope_diagnostics: list[str] = field(default_factory=list)
    evidence_refs: list[ReadinessEvidenceRef] = field(default_factory=list)
    recommendation_summary: str = "No readiness recommendations."
    recommended_reviewer_actions: list[str] = field(default_factory=list)
    confidence: float = 0.75
    created_by_engine_version: str = "plan-review-readiness-service/2.0.0"

    def __post_init__(self) -> None:
        if not isinstance(self.status, ReadinessStatus):
            self.status = ReadinessStatus(str(self.status).strip().lower())

        if not isinstance(self.readiness_level, ReadinessLevel):
            self.readiness_level = ReadinessLevel(
                str(self.readiness_level).strip().lower()
            )

        if self.blockers and not self.blocking_issues:
            self.blocking_issues = list(self.blockers)

        self.project_id = self._normalize_optional_text(self.project_id) or ""
        self.readiness_score = self._validate_score(
            "readiness_score", self.readiness_score
        )
        self.confidence = self._validate_score("confidence", self.confidence)
        self.created_by_engine_version = self._normalize_required_text(
            "created_by_engine_version", self.created_by_engine_version
        )

        self.message = self._normalize_required_text("message", self.message)
        self.blockers = [
            self._normalize_required_text("blocker", blocker)
            for blocker in self.blockers
        ]
        self.blocking_issues = [
            self._normalize_required_text("blocking_issue", blocker)
            for blocker in self.blocking_issues
        ]
        self.warnings = [
            self._normalize_required_text("warning", warning)
            for warning in self.warnings
        ]
        self.missing_scope_diagnostics = [
            self._normalize_required_text("missing_scope_diagnostic", diagnostic)
            for diagnostic in self.missing_scope_diagnostics
        ]
        self.recommendation_summary = (
            self._normalize_optional_text(self.recommendation_summary)
            or "No readiness recommendations."
        )
        self.recommended_reviewer_actions = [
            self._normalize_required_text("recommended_reviewer_action", action)
            for action in self.recommended_reviewer_actions
        ]
        self.section_scores = {
            self._normalize_required_text(
                "section_name", section_name
            ): self._validate_score(
                f"section_scores[{section_name}]",
                score,
            )
            for section_name, score in self.section_scores.items()
        }
        self.evidence_refs = [
            (
                evidence_ref
                if isinstance(evidence_ref, ReadinessEvidenceRef)
                else ReadinessEvidenceRef(**evidence_ref)
            )
            for evidence_ref in self.evidence_refs
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "project_id": self.project_id,
            "readiness_score": self.readiness_score,
            "readiness_level": self.readiness_level.value,
            "section_scores": dict(self.section_scores),
            "blocking_issues": list(self.blocking_issues),
            "missing_scope_diagnostics": list(self.missing_scope_diagnostics),
            "evidence_refs": [
                evidence_ref.to_dict() for evidence_ref in self.evidence_refs
            ],
            "recommendation_summary": self.recommendation_summary,
            "recommended_reviewer_actions": list(self.recommended_reviewer_actions),
            "confidence": self.confidence,
            "created_by_engine_version": self.created_by_engine_version,
        }

    @staticmethod
    def _validate_score(field_name: str, value: float) -> float:
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"{field_name} must be between 0 and 1")

        return round(float(value), 2)

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_required_text(field_name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be blank")

        return value.strip()


class PlanReviewReadinessService:
    ENGINE_VERSION = "plan-review-readiness-service/2.0.0"

    READY_MESSAGE = "Plan review is ready for pricing."
    NEEDS_REVIEW_MESSAGE = "Plan review needs estimator review before pricing."
    NOT_READY_MESSAGE = "Plan review is not ready for pricing."

    _RESPONSIBILITY_TOKENS = {
        "ofe",
        "ofci",
        "cfci",
        "nic",
        "by others",
        "owner provided",
        "contractor provided",
    }

    _RFI_SEVERITY_PENALTY = {
        "critical": 0.2,
        "high": 0.1,
        "medium": 0.05,
        "low": 0.02,
    }

    _SECTION_WEIGHTS = {
        "equipment_completeness": 0.15,
        "quantity_confidence": 0.14,
        "scope_responsibility_clarity": 0.14,
        "drawing_spec_alignment": 0.14,
        "assumptions_quality": 0.12,
        "rfi_candidate_risk": 0.12,
        "labor_estimate_confidence": 0.12,
        "revision_stability": 0.07,
    }

    def assess(self, readiness_review: BidPackageReview) -> PlanReviewReadiness:
        diagnostics, evidence_refs = self._missing_scope_diagnostics(readiness_review)
        section_scores = self._section_scores(
            review=readiness_review,
            diagnostics=diagnostics,
            evidence_refs=evidence_refs,
        )
        blockers = self._blocking_issues(readiness_review, section_scores, diagnostics)
        warnings = self._warnings(readiness_review, section_scores, diagnostics)

        readiness_score = round(
            sum(
                section_scores[section_name] * self._SECTION_WEIGHTS[section_name]
                for section_name in self._SECTION_WEIGHTS
            ),
            2,
        )
        readiness_level = self._readiness_level(
            score=readiness_score,
            blockers=blockers,
            warnings=warnings,
        )
        status = self._status_from_level(readiness_level)
        message = self._message_for_level(readiness_level)
        actions = self._recommended_actions(
            section_scores=section_scores,
            blockers=blockers,
            warnings=warnings,
            diagnostics=diagnostics,
        )

        recommendation_summary = (
            f"{len(blockers)} blockers, {len(warnings)} warnings, and "
            f"{len(actions)} recommended actions based on deterministic scoring."
        )

        confidence = round(
            max(
                0.05,
                min(
                    0.99,
                    (float(getattr(readiness_review, "confidence", 0.75) or 0.75) * 0.7)
                    + (readiness_score * 0.3),
                ),
            ),
            2,
        )

        return PlanReviewReadiness(
            status=status,
            message=message,
            blockers=blockers,
            warnings=warnings,
            project_id=readiness_review.project_id,
            readiness_score=readiness_score,
            readiness_level=readiness_level,
            section_scores=section_scores,
            blocking_issues=blockers,
            missing_scope_diagnostics=diagnostics,
            evidence_refs=evidence_refs,
            recommendation_summary=recommendation_summary,
            recommended_reviewer_actions=actions,
            confidence=confidence,
            created_by_engine_version=self.ENGINE_VERSION,
        )

    def _blocking_issues(
        self,
        review: BidPackageReview,
        section_scores: dict[str, float],
        diagnostics: list[str],
    ) -> list[str]:
        blockers: list[str] = []

        if not review.drawing_sheets:
            blockers.append("No drawing sheets are available.")

        if not review.specification_sections:
            blockers.append("No specification sections are available.")

        if not review.systems:
            blockers.append("No systems were detected.")

        if not review.equipment:
            blockers.append("No equipment was detected.")

        if any(
            self._value(getattr(candidate, "severity", None)) == "critical"
            for candidate in review.rfi_candidates
        ):
            blockers.append("Critical RFI candidate risk requires clarification.")

        if section_scores["quantity_confidence"] < 0.45:
            blockers.append(
                "Quantity confidence is below acceptable pricing threshold."
            )

        if section_scores["drawing_spec_alignment"] < 0.45:
            blockers.append(
                "Major drawing/specification alignment gaps remain unresolved."
            )

        if section_scores["scope_responsibility_clarity"] < 0.45:
            blockers.append(
                "Scope responsibility is unresolved across key bid package items."
            )

        if any("Missing quantity" in diagnostic for diagnostic in diagnostics):
            blockers.append(
                "One or more equipment items have missing quantity evidence."
            )

        bid_completeness = getattr(review, "bid_completeness", None)
        status = self._value(getattr(bid_completeness, "status", None))
        if status == "incomplete":
            blockers.extend(list(getattr(bid_completeness, "missing_items", [])))

        return sorted(set(blockers))

    def _warnings(
        self,
        review: BidPackageReview,
        section_scores: dict[str, float],
        diagnostics: list[str],
    ) -> list[str]:
        warnings: list[str] = []

        bid_completeness = getattr(review, "bid_completeness", None)
        status = self._value(getattr(bid_completeness, "status", None))
        if status == "partial":
            warnings.extend(list(getattr(bid_completeness, "missing_items", [])))

        if review.scope_gaps:
            warnings.append("Scope gaps require estimator review.")

        if any(
            self._value(risk.risk_level) == "high" for risk in review.estimator_risks
        ):
            warnings.append("High estimator risks require estimator review.")

        if any(
            self._value(recommendation.priority) == "high"
            for recommendation in review.recommendations
        ):
            warnings.append("High-priority recommendations require estimator review.")

        if section_scores["rfi_candidate_risk"] < 0.7:
            warnings.append("RFI candidate risk profile reduces bid readiness.")

        if section_scores["labor_estimate_confidence"] < 0.65:
            warnings.append("Labor estimate confidence is below preferred threshold.")

        if section_scores["revision_stability"] < 0.7:
            warnings.append(
                "Revision instability suggests additional estimator review."
            )

        if diagnostics:
            warnings.append("Missing or ambiguous scope evidence was detected.")

        if review.confidence < 0.75:
            warnings.append("Review confidence is below 0.75.")

        return sorted(set(warnings))

    def _section_scores(
        self,
        review: BidPackageReview,
        diagnostics: list[str],
        evidence_refs: list[ReadinessEvidenceRef],
    ) -> dict[str, float]:
        equipment_items = list(review.equipment)
        equipment_count = len(equipment_items)

        missing_model_count = 0
        missing_manufacturer_count = 0
        missing_quantity_count = 0
        responsibility_token_count = 0

        for equipment in equipment_items:
            if not self._text(getattr(equipment, "model", None)):
                missing_model_count += 1
                evidence_refs.append(
                    ReadinessEvidenceRef(
                        source_type="equipment",
                        source_id=self._text(getattr(equipment, "equipment_id", None))
                        or "unknown",
                        field="model",
                        excerpt="model is missing",
                    )
                )

            if not self._text(getattr(equipment, "manufacturer", None)):
                missing_manufacturer_count += 1
                evidence_refs.append(
                    ReadinessEvidenceRef(
                        source_type="equipment",
                        source_id=self._text(getattr(equipment, "equipment_id", None))
                        or "unknown",
                        field="manufacturer",
                        excerpt="manufacturer is missing",
                    )
                )

            quantity = getattr(equipment, "quantity", None)
            if not isinstance(quantity, (int, float)) or quantity <= 0:
                missing_quantity_count += 1
                evidence_refs.append(
                    ReadinessEvidenceRef(
                        source_type="equipment",
                        source_id=self._text(getattr(equipment, "equipment_id", None))
                        or "unknown",
                        field="quantity",
                        excerpt="quantity is missing or invalid",
                    )
                )

            token_count = len(self._responsibility_tokens_for_equipment(equipment))
            responsibility_token_count += token_count

        base_equipment_score = 0.0 if equipment_count == 0 else 1.0
        if equipment_count > 0:
            base_equipment_score -= (missing_model_count / equipment_count) * 0.4
            base_equipment_score -= (missing_manufacturer_count / equipment_count) * 0.2
            base_equipment_score -= (missing_quantity_count / equipment_count) * 0.4

        quantity_confidence = 0.0 if equipment_count == 0 else 1.0
        quantity_conflicts = sum(
            1
            for candidate in review.rfi_candidates
            if self._text(getattr(candidate, "detected_condition", None))
            == "quantity_conflict"
        )
        if equipment_count > 0:
            quantity_confidence -= min(0.7, quantity_conflicts * 0.2)
            quantity_confidence -= (missing_quantity_count / equipment_count) * 0.3

        scope_clarity = 1.0
        if responsibility_token_count > 0:
            scope_clarity -= min(0.4, responsibility_token_count * 0.05)
        scope_ambiguity_candidates = sum(
            1
            for candidate in review.rfi_candidates
            if self._text(getattr(candidate, "detected_condition", None))
            == "scope_responsibility_ambiguity"
        )
        scope_clarity -= min(0.55, scope_ambiguity_candidates * 0.2)

        drawing_spec_alignment = 0.0
        if equipment_count > 0:
            drawing_spec_gap_groups = sum(
                1
                for candidate in review.rfi_candidates
                if self._text(getattr(candidate, "detected_condition", None))
                == "drawing_spec_cross_reference_gap"
            )
            drawing_spec_support = sum(
                1
                for reference in review.cross_references
                if self._value(getattr(reference, "reference_type", None))
                in {
                    "equipment_to_drawing",
                    "equipment_to_spec",
                    "drawing_to_spec",
                    "system_to_spec",
                }
            )
            drawing_spec_alignment = 0.68
            drawing_spec_alignment += min(
                0.18,
                (drawing_spec_support / equipment_count) * 0.18,
            )
            drawing_spec_alignment -= min(0.28, drawing_spec_gap_groups * 0.04)

        assumptions = list(review.engineering_assumptions)
        assumptions_quality = 0.85 if not assumptions else 1.0
        risk_assumptions = sum(
            1
            for assumption in assumptions
            if self._value(getattr(assumption, "severity", None)) == "risk"
        )
        assumptions_quality -= min(0.5, risk_assumptions * 0.12)

        rfi_risk_score = 1.0
        for candidate in review.rfi_candidates:
            severity = self._value(getattr(candidate, "severity", None))
            confidence = float(getattr(candidate, "confidence", 0.75) or 0.75)
            rfi_risk_score -= (
                self._RFI_SEVERITY_PENALTY.get(str(severity), 0.03) * confidence
            )

        labor_confidence = 0.45
        if review.labor_estimate is not None:
            labor_confidence = float(
                getattr(review.labor_estimate, "confidence", 0.45) or 0.45
            )

        revision_stability = 1.0
        revision_comparison = getattr(review, "revision_comparison", None)
        if revision_comparison is not None:
            revision_confidence = float(
                getattr(revision_comparison, "confidence", 0.8) or 0.8
            )
            critical_or_high = sum(
                1
                for change in getattr(revision_comparison, "changes", [])
                if self._value(getattr(change, "severity", None))
                in {"high", "critical"}
            )
            revision_stability = max(
                0.2, revision_confidence - min(0.6, critical_or_high * 0.08)
            )

        section_scores = {
            "equipment_completeness": self._score(base_equipment_score),
            "quantity_confidence": self._score(quantity_confidence),
            "scope_responsibility_clarity": self._score(scope_clarity),
            "drawing_spec_alignment": self._score(drawing_spec_alignment),
            "assumptions_quality": self._score(assumptions_quality),
            "rfi_candidate_risk": self._score(rfi_risk_score),
            "labor_estimate_confidence": self._score(labor_confidence),
            "revision_stability": self._score(revision_stability),
        }

        return section_scores

    def _missing_scope_diagnostics(
        self,
        review: BidPackageReview,
    ) -> tuple[list[str], list[ReadinessEvidenceRef]]:
        diagnostics: list[str] = []
        evidence_refs: list[ReadinessEvidenceRef] = []

        for equipment in review.equipment:
            equipment_id = (
                self._text(getattr(equipment, "equipment_id", None)) or "unknown"
            )
            if not self._text(getattr(equipment, "model", None)):
                diagnostics.append(f"Missing model for equipment {equipment_id}.")
            if not self._text(getattr(equipment, "manufacturer", None)):
                diagnostics.append(
                    f"Missing manufacturer for equipment {equipment_id}."
                )
            quantity = getattr(equipment, "quantity", None)
            if not isinstance(quantity, (int, float)) or quantity <= 0:
                diagnostics.append(f"Missing quantity for equipment {equipment_id}.")
            if not self._text(getattr(equipment, "drawing_reference", None)):
                diagnostics.append(
                    f"Missing drawing reference for equipment {equipment_id}."
                )
            if not self._text(getattr(equipment, "specification_reference", None)):
                diagnostics.append(
                    f"Missing specification reference for equipment {equipment_id}."
                )

        for candidate in review.rfi_candidates:
            condition = self._text(getattr(candidate, "detected_condition", None))
            if condition in {
                "scope_responsibility_ambiguity",
                "quantity_conflict",
                "drawing_spec_cross_reference_gap",
            }:
                diagnostics.append(
                    "RFI candidate indicates unresolved "
                    f"{condition.replace('_', ' ')}."
                )
                evidence_refs.append(
                    ReadinessEvidenceRef(
                        source_type="rfi_candidate",
                        source_id=self._text(getattr(candidate, "candidate_id", None))
                        or "unknown-rfi",
                        field="detected_condition",
                        excerpt=condition,
                    )
                )

        return sorted(set(diagnostics)), evidence_refs

    def _readiness_level(
        self,
        score: float,
        blockers: list[str],
        warnings: list[str],
    ) -> ReadinessLevel:
        if blockers:
            return ReadinessLevel.NOT_READY
        if score < 0.7:
            return ReadinessLevel.NEEDS_REVIEW
        if score >= 0.85 and not warnings:
            return ReadinessLevel.BID_READY

        return ReadinessLevel.BID_READY_WITH_ASSUMPTIONS

    @staticmethod
    def _status_from_level(level: ReadinessLevel) -> ReadinessStatus:
        if level is ReadinessLevel.NOT_READY:
            return ReadinessStatus.NOT_READY
        if level is ReadinessLevel.NEEDS_REVIEW:
            return ReadinessStatus.NEEDS_REVIEW
        return ReadinessStatus.READY

    def _message_for_level(self, level: ReadinessLevel) -> str:
        if level is ReadinessLevel.NOT_READY:
            return self.NOT_READY_MESSAGE
        if level is ReadinessLevel.NEEDS_REVIEW:
            return self.NEEDS_REVIEW_MESSAGE
        if level is ReadinessLevel.BID_READY_WITH_ASSUMPTIONS:
            return "Plan review is bid-ready with explicit assumptions."

        return self.READY_MESSAGE

    def _recommended_actions(
        self,
        section_scores: dict[str, float],
        blockers: list[str],
        warnings: list[str],
        diagnostics: list[str],
    ) -> list[str]:
        actions: list[str] = []
        if blockers:
            actions.append("Resolve all blocking issues before final pricing release.")
        if section_scores["quantity_confidence"] < 0.75:
            actions.append(
                "Reconcile all quantity conflicts across schedule and equipment matrix."
            )
        if section_scores["scope_responsibility_clarity"] < 0.75:
            actions.append(
                "Issue scope responsibility clarification notes for ambiguous items."
            )
        if section_scores["drawing_spec_alignment"] < 0.75:
            actions.append(
                "Validate drawing-to-spec references for affected equipment."
            )
        if section_scores["labor_estimate_confidence"] < 0.7:
            actions.append("Re-run labor assumptions with estimator calibration notes.")
        if section_scores["revision_stability"] < 0.75:
            actions.append(
                "Review latest addenda/revision deltas before bid submission."
            )
        if diagnostics:
            actions.append(
                "Close missing scope diagnostics or document estimator assumptions."
            )
        if warnings and not blockers:
            actions.append(
                "Document reviewer sign-off for warnings prior to submission."
            )

        return sorted(set(actions))

    def _responsibility_tokens_for_equipment(self, equipment: Any) -> set[str]:
        text = " ".join(
            [
                self._text(getattr(equipment, "description", None)),
                " ".join(
                    self._text(value)
                    for value in getattr(equipment, "assumptions", []) or []
                ),
            ]
        ).casefold()
        return {token for token in self._RESPONSIBILITY_TOKENS if token in text}

    @staticmethod
    def _score(value: float) -> float:
        return round(max(0.0, min(1.0, value)), 2)

    @staticmethod
    def _value(value: Any) -> Any:
        return getattr(value, "value", value)

    @staticmethod
    def _text(value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        return value.strip()

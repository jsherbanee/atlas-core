"""Deterministic coordination intelligence models for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from statistics import fmean
from typing import Any


class CoordinationCategory(str, Enum):
    DRAWING_SPECIFICATION_ALIGNMENT = "drawing_specification_alignment"
    EQUIPMENT_SPECIFICATION_ALIGNMENT = "equipment_specification_alignment"
    SYSTEM_COORDINATION = "system_coordination"
    REQUIREMENT_CANDIDATE_COVERAGE = "requirement_candidate_coverage"
    RFI_CANDIDATE_SIGNAL = "rfi_candidate_signal"
    ASSUMPTION_TRACEABILITY = "assumption_traceability"
    EVIDENCE_TRACEABILITY = "evidence_traceability"


class CoordinationSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CoordinationConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class CoordinationEvidence:
    source_ref: str
    object_id: str
    confidence: float = 0.75
    excerpt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref,
            "object_id": self.object_id,
            "confidence": self.confidence,
            "excerpt": self.excerpt,
        }


@dataclass(frozen=True)
class CoordinationFinding:
    finding_id: str
    category: CoordinationCategory
    severity: CoordinationSeverity
    confidence: CoordinationConfidence
    title: str
    description: str
    recommended_action: str
    related_objects: list[str] = field(default_factory=list)
    evidence: list[CoordinationEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "confidence": self.confidence.value,
            "title": self.title,
            "description": self.description,
            "recommended_action": self.recommended_action,
            "related_objects": list(self.related_objects),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class CoordinationIssue:
    issue_id: str
    category: CoordinationCategory
    severity: CoordinationSeverity
    finding_ids: list[str] = field(default_factory=list)
    related_objects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "finding_ids": list(self.finding_ids),
            "related_objects": list(self.related_objects),
        }


@dataclass(frozen=True)
class CoordinationSummary:
    total_findings: int
    conflict_count: int
    gap_count: int
    agreement_count: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    by_confidence: dict[str, int]
    top_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_findings": self.total_findings,
            "conflict_count": self.conflict_count,
            "gap_count": self.gap_count,
            "agreement_count": self.agreement_count,
            "by_category": dict(self.by_category),
            "by_severity": dict(self.by_severity),
            "by_confidence": dict(self.by_confidence),
            "top_actions": list(self.top_actions),
        }


@dataclass(frozen=True)
class CoordinationIntelligenceResult:
    findings: list[CoordinationFinding]
    issues: list[CoordinationIssue]
    summary: CoordinationSummary
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [item.to_dict() for item in self.findings],
            "issues": [item.to_dict() for item in self.issues],
            "summary": self.summary.to_dict(),
            "confidence": self.confidence,
        }


def aggregate_confidence(values: list[float], default: float = 0.75) -> float:
    usable = [value for value in values if isinstance(value, (int, float))]
    if not usable:
        return default
    return max(0.0, min(1.0, float(fmean(usable))))

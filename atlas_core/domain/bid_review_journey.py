"""Bid-review journey contract for Atlas Core.

This module keeps bid-review reporting, estimate state, sales-order conversion,
and tenant policy separate from the commercial document lifecycle state machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


def _required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    return normalized or None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _decimal(value: Any, *, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid decimal value") from exc


def _decimal_between_zero_and_one(value: Any, *, field_name: str) -> Decimal:
    parsed = _decimal(value, field_name=field_name)
    if parsed < Decimal("0") or parsed > Decimal("1"):
        raise ValueError(f"{field_name} must be between 0 and 1")
    return parsed


def _int_non_negative(value: Any, *, field_name: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return parsed


def _normalize_sequence(
    values: Sequence[Any] | Iterable[Any] | None,
) -> tuple[str, ...]:
    if values is None:
        return ()
    normalized: list[str] = []
    for value in values:
        text = _optional_text(value)
        if text:
            normalized.append(text)
    return tuple(normalized)


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def _freeze_mapping(
    value: Mapping[str, Any] | dict[str, Any] | None,
) -> Mapping[str, Any]:
    payload = dict(value or {})
    return MappingProxyType(
        {str(key): _freeze_value(item) for key, item in payload.items()}
    )


class BidReviewJourneyError(ValueError):
    """Domain validation error for the bid-review journey contract."""


class BidReviewReportStatus(str, Enum):
    PRELIMINARY = "preliminary"
    REVISED = "revised"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class EstimateJourneyState(str, Enum):
    DRAFT = "draft"
    REJECTED = "rejected"
    APPROVED_INTERNAL = "approved_internal"
    SUBMITTED = "submitted"
    CUSTOMER_ACCEPTED = "customer_accepted"
    CUSTOMER_DECLINED = "customer_declined"
    EXPIRED = "expired"
    REVISED = "revised"
    SUPERSEDED = "superseded"


class RejectedDraftRetention(str, Enum):
    ARCHIVE = "archive"
    DELETE_AFTER_AUDIT = "delete_after_audit"
    RETAIN = "retain"


class SalesOrderConversionGate(str, Enum):
    INTERNAL_APPROVAL = "internal_approval"
    CUSTOMER_ACCEPTANCE = "customer_acceptance"


_REPORT_TRANSITIONS: dict[BidReviewReportStatus, set[BidReviewReportStatus]] = {
    BidReviewReportStatus.PRELIMINARY: {
        BidReviewReportStatus.REVISED,
        BidReviewReportStatus.ARCHIVED,
    },
    BidReviewReportStatus.REVISED: {
        BidReviewReportStatus.SUPERSEDED,
        BidReviewReportStatus.ARCHIVED,
    },
    BidReviewReportStatus.SUPERSEDED: set(),
    BidReviewReportStatus.ARCHIVED: set(),
}


_ESTIMATE_TRANSITIONS: dict[EstimateJourneyState, set[EstimateJourneyState]] = {
    EstimateJourneyState.DRAFT: {
        EstimateJourneyState.REJECTED,
        EstimateJourneyState.APPROVED_INTERNAL,
    },
    EstimateJourneyState.REJECTED: set(),
    EstimateJourneyState.APPROVED_INTERNAL: {
        EstimateJourneyState.SUBMITTED,
        EstimateJourneyState.REVISED,
    },
    EstimateJourneyState.SUBMITTED: {
        EstimateJourneyState.CUSTOMER_ACCEPTED,
        EstimateJourneyState.CUSTOMER_DECLINED,
        EstimateJourneyState.EXPIRED,
        EstimateJourneyState.REVISED,
    },
    EstimateJourneyState.CUSTOMER_ACCEPTED: {
        EstimateJourneyState.REVISED,
    },
    EstimateJourneyState.CUSTOMER_DECLINED: set(),
    EstimateJourneyState.EXPIRED: set(),
    EstimateJourneyState.REVISED: {
        EstimateJourneyState.SUPERSEDED,
    },
    EstimateJourneyState.SUPERSEDED: set(),
}


@dataclass(frozen=True, slots=True)
class BidReviewTenantPolicy:
    rejected_draft_retention: RejectedDraftRetention = RejectedDraftRetention.ARCHIVE
    sales_order_conversion_gate: SalesOrderConversionGate = (
        SalesOrderConversionGate.CUSTOMER_ACCEPTANCE
    )
    allow_draft_below_readiness_threshold: bool = True
    minimum_recommended_readiness: Decimal = Decimal("0.70")
    require_pending_rfi_acknowledgement: bool = False
    accepted_estimate_revision_required: bool = True
    allowance_policy_id: str | None = None
    lot_policy_id: str | None = None
    contingency_policy_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.rejected_draft_retention, RejectedDraftRetention):
            object.__setattr__(
                self,
                "rejected_draft_retention",
                RejectedDraftRetention(self.rejected_draft_retention),
            )
        if not isinstance(self.sales_order_conversion_gate, SalesOrderConversionGate):
            object.__setattr__(
                self,
                "sales_order_conversion_gate",
                SalesOrderConversionGate(self.sales_order_conversion_gate),
            )
        object.__setattr__(
            self,
            "allow_draft_below_readiness_threshold",
            bool(self.allow_draft_below_readiness_threshold),
        )
        object.__setattr__(
            self,
            "minimum_recommended_readiness",
            _decimal_between_zero_and_one(
                self.minimum_recommended_readiness,
                field_name="minimum_recommended_readiness",
            ),
        )
        object.__setattr__(
            self,
            "require_pending_rfi_acknowledgement",
            bool(self.require_pending_rfi_acknowledgement),
        )
        object.__setattr__(
            self,
            "accepted_estimate_revision_required",
            bool(self.accepted_estimate_revision_required),
        )
        object.__setattr__(
            self, "allowance_policy_id", _optional_text(self.allowance_policy_id)
        )
        object.__setattr__(self, "lot_policy_id", _optional_text(self.lot_policy_id))
        object.__setattr__(
            self,
            "contingency_policy_id",
            _optional_text(self.contingency_policy_id),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rejected_draft_retention": self.rejected_draft_retention.value,
            "sales_order_conversion_gate": self.sales_order_conversion_gate.value,
            "allow_draft_below_readiness_threshold": self.allow_draft_below_readiness_threshold,
            "minimum_recommended_readiness": str(self.minimum_recommended_readiness),
            "require_pending_rfi_acknowledgement": self.require_pending_rfi_acknowledgement,
            "accepted_estimate_revision_required": self.accepted_estimate_revision_required,
            "allowance_policy_id": self.allowance_policy_id,
            "lot_policy_id": self.lot_policy_id,
            "contingency_policy_id": self.contingency_policy_id,
        }


@dataclass(frozen=True, slots=True)
class BidReviewReportVersion:
    project_id: str
    version: int
    source_document_set_id: str
    parent_version: int | None
    status: BidReviewReportStatus
    readiness_score: Decimal
    unresolved_item_count: int
    pending_rfi_count: int
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    guidance_inputs: tuple[str, ...] = field(default_factory=tuple)
    tenant_rules_snapshot: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )
    generated_at: str = field(default_factory=_utc_now)
    generated_by: str = "system"
    change_summary: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "project_id", _required_text("project_id", self.project_id)
        )
        object.__setattr__(self, "version", int(self.version))
        if self.version <= 0:
            raise ValueError("version must be greater than 0")
        object.__setattr__(
            self,
            "source_document_set_id",
            _required_text("source_document_set_id", self.source_document_set_id),
        )
        if self.parent_version is not None:
            object.__setattr__(self, "parent_version", int(self.parent_version))
            if self.parent_version <= 0:
                raise ValueError("parent_version must be greater than 0")
            if self.parent_version >= self.version:
                raise ValueError("parent_version must be lower than version")
        if not isinstance(self.status, BidReviewReportStatus):
            object.__setattr__(self, "status", BidReviewReportStatus(self.status))
        object.__setattr__(
            self,
            "readiness_score",
            _decimal_between_zero_and_one(
                self.readiness_score, field_name="readiness_score"
            ),
        )
        object.__setattr__(
            self,
            "unresolved_item_count",
            _int_non_negative(
                self.unresolved_item_count, field_name="unresolved_item_count"
            ),
        )
        object.__setattr__(
            self,
            "pending_rfi_count",
            _int_non_negative(self.pending_rfi_count, field_name="pending_rfi_count"),
        )
        object.__setattr__(self, "assumptions", _normalize_sequence(self.assumptions))
        object.__setattr__(
            self, "guidance_inputs", _normalize_sequence(self.guidance_inputs)
        )
        object.__setattr__(
            self,
            "tenant_rules_snapshot",
            _freeze_mapping(self.tenant_rules_snapshot),
        )
        object.__setattr__(
            self, "generated_at", _required_text("generated_at", self.generated_at)
        )
        object.__setattr__(
            self, "generated_by", _required_text("generated_by", self.generated_by)
        )
        object.__setattr__(
            self, "change_summary", _normalize_sequence(self.change_summary)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "version": self.version,
            "source_document_set_id": self.source_document_set_id,
            "parent_version": self.parent_version,
            "status": self.status.value,
            "readiness_score": str(self.readiness_score),
            "unresolved_item_count": self.unresolved_item_count,
            "pending_rfi_count": self.pending_rfi_count,
            "assumptions": list(self.assumptions),
            "guidance_inputs": list(self.guidance_inputs),
            "tenant_rules_snapshot": dict(self.tenant_rules_snapshot),
            "generated_at": self.generated_at,
            "generated_by": self.generated_by,
            "change_summary": list(self.change_summary),
        }


@dataclass(frozen=True, slots=True)
class BidReviewEstimateVersion:
    project_id: str
    estimate_id: str
    version: int
    state: EstimateJourneyState
    source_report_version: int
    source_document_set_id: str
    readiness_score: Decimal
    unresolved_item_count: int
    pending_rfi_count: int
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    guidance_inputs: tuple[str, ...] = field(default_factory=tuple)
    tenant_rules_snapshot: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )
    generated_at: str = field(default_factory=_utc_now)
    generated_by: str = "system"
    change_summary: tuple[str, ...] = field(default_factory=tuple)
    parent_version: int | None = None
    advisories: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "project_id", _required_text("project_id", self.project_id)
        )
        object.__setattr__(
            self, "estimate_id", _required_text("estimate_id", self.estimate_id)
        )
        object.__setattr__(self, "version", int(self.version))
        if self.version <= 0:
            raise ValueError("version must be greater than 0")
        if not isinstance(self.state, EstimateJourneyState):
            object.__setattr__(self, "state", EstimateJourneyState(self.state))
        object.__setattr__(
            self,
            "source_report_version",
            int(self.source_report_version),
        )
        if self.source_report_version <= 0:
            raise ValueError("source_report_version must be greater than 0")
        object.__setattr__(
            self,
            "source_document_set_id",
            _required_text("source_document_set_id", self.source_document_set_id),
        )
        object.__setattr__(
            self,
            "readiness_score",
            _decimal_between_zero_and_one(
                self.readiness_score, field_name="readiness_score"
            ),
        )
        object.__setattr__(
            self,
            "unresolved_item_count",
            _int_non_negative(
                self.unresolved_item_count, field_name="unresolved_item_count"
            ),
        )
        object.__setattr__(
            self,
            "pending_rfi_count",
            _int_non_negative(self.pending_rfi_count, field_name="pending_rfi_count"),
        )
        object.__setattr__(self, "assumptions", _normalize_sequence(self.assumptions))
        object.__setattr__(
            self, "guidance_inputs", _normalize_sequence(self.guidance_inputs)
        )
        object.__setattr__(
            self,
            "tenant_rules_snapshot",
            _freeze_mapping(self.tenant_rules_snapshot),
        )
        object.__setattr__(
            self, "generated_at", _required_text("generated_at", self.generated_at)
        )
        object.__setattr__(
            self, "generated_by", _required_text("generated_by", self.generated_by)
        )
        object.__setattr__(
            self, "change_summary", _normalize_sequence(self.change_summary)
        )
        if self.parent_version is not None:
            object.__setattr__(self, "parent_version", int(self.parent_version))
            if self.parent_version <= 0:
                raise ValueError("parent_version must be greater than 0")
            if self.parent_version >= self.version:
                raise ValueError("parent_version must be lower than version")
        object.__setattr__(self, "advisories", _normalize_sequence(self.advisories))

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "estimate_id": self.estimate_id,
            "version": self.version,
            "state": self.state.value,
            "source_report_version": self.source_report_version,
            "source_document_set_id": self.source_document_set_id,
            "readiness_score": str(self.readiness_score),
            "unresolved_item_count": self.unresolved_item_count,
            "pending_rfi_count": self.pending_rfi_count,
            "assumptions": list(self.assumptions),
            "guidance_inputs": list(self.guidance_inputs),
            "tenant_rules_snapshot": dict(self.tenant_rules_snapshot),
            "generated_at": self.generated_at,
            "generated_by": self.generated_by,
            "change_summary": list(self.change_summary),
            "parent_version": self.parent_version,
            "advisories": list(self.advisories),
        }


@dataclass(frozen=True, slots=True)
class BidReviewAuditRecord:
    actor: str
    timestamp: str
    prior_state: str
    new_state: str
    reason: str
    tenant_policy_snapshot: Mapping[str, Any]
    project_guidance_snapshot: Mapping[str, Any]
    project_id: str
    entity_type: str
    entity_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor", _required_text("actor", self.actor))
        object.__setattr__(
            self, "timestamp", _required_text("timestamp", self.timestamp)
        )
        object.__setattr__(
            self, "prior_state", _required_text("prior_state", self.prior_state)
        )
        object.__setattr__(
            self, "new_state", _required_text("new_state", self.new_state)
        )
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        object.__setattr__(
            self, "tenant_policy_snapshot", _freeze_mapping(self.tenant_policy_snapshot)
        )
        object.__setattr__(
            self,
            "project_guidance_snapshot",
            _freeze_mapping(self.project_guidance_snapshot),
        )
        object.__setattr__(
            self, "project_id", _required_text("project_id", self.project_id)
        )
        object.__setattr__(
            self, "entity_type", _required_text("entity_type", self.entity_type)
        )
        object.__setattr__(
            self, "entity_id", _required_text("entity_id", self.entity_id)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor": self.actor,
            "timestamp": self.timestamp,
            "prior_state": self.prior_state,
            "new_state": self.new_state,
            "reason": self.reason,
            "tenant_policy_snapshot": dict(self.tenant_policy_snapshot),
            "project_guidance_snapshot": dict(self.project_guidance_snapshot),
            "project_id": self.project_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
        }


@dataclass(frozen=True, slots=True)
class ConversionEligibilityResult:
    eligible: bool
    estimate_id: str
    estimate_version: int
    report_version: int
    project_id: str
    blocking_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    pending_rfis: tuple[str, ...]
    unresolved_assumptions: tuple[str, ...]
    policy_gate_used: SalesOrderConversionGate
    source_document_set_id: str
    estimate_state: EstimateJourneyState

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "estimate_id", _required_text("estimate_id", self.estimate_id)
        )
        object.__setattr__(self, "estimate_version", int(self.estimate_version))
        if self.estimate_version <= 0:
            raise ValueError("estimate_version must be greater than 0")
        object.__setattr__(self, "report_version", int(self.report_version))
        if self.report_version <= 0:
            raise ValueError("report_version must be greater than 0")
        object.__setattr__(
            self, "project_id", _required_text("project_id", self.project_id)
        )
        object.__setattr__(
            self,
            "blocking_reasons",
            _normalize_sequence(self.blocking_reasons),
        )
        object.__setattr__(self, "warnings", _normalize_sequence(self.warnings))
        object.__setattr__(self, "pending_rfis", _normalize_sequence(self.pending_rfis))
        object.__setattr__(
            self,
            "unresolved_assumptions",
            _normalize_sequence(self.unresolved_assumptions),
        )
        if not isinstance(self.policy_gate_used, SalesOrderConversionGate):
            object.__setattr__(
                self,
                "policy_gate_used",
                SalesOrderConversionGate(self.policy_gate_used),
            )
        object.__setattr__(
            self,
            "source_document_set_id",
            _required_text("source_document_set_id", self.source_document_set_id),
        )
        if not isinstance(self.estimate_state, EstimateJourneyState):
            object.__setattr__(
                self, "estimate_state", EstimateJourneyState(self.estimate_state)
            )
        object.__setattr__(self, "eligible", bool(self.eligible))

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "estimate_id": self.estimate_id,
            "estimate_version": self.estimate_version,
            "report_version": self.report_version,
            "project_id": self.project_id,
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
            "pending_rfis": list(self.pending_rfis),
            "unresolved_assumptions": list(self.unresolved_assumptions),
            "policy_gate_used": self.policy_gate_used.value,
            "source_document_set_id": self.source_document_set_id,
            "estimate_state": self.estimate_state.value,
        }


def validate_report_transition(
    current_status: BidReviewReportStatus | str,
    next_status: BidReviewReportStatus | str,
) -> BidReviewReportStatus:
    current = (
        current_status
        if isinstance(current_status, BidReviewReportStatus)
        else BidReviewReportStatus(current_status)
    )
    target = (
        next_status
        if isinstance(next_status, BidReviewReportStatus)
        else BidReviewReportStatus(next_status)
    )
    allowed = _REPORT_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise BidReviewJourneyError(
            f"invalid report transition {current.value} -> {target.value}"
        )
    return target


def validate_estimate_transition(
    current_state: EstimateJourneyState | str,
    next_state: EstimateJourneyState | str,
) -> EstimateJourneyState:
    current = (
        current_state
        if isinstance(current_state, EstimateJourneyState)
        else EstimateJourneyState(current_state)
    )
    target = (
        next_state
        if isinstance(next_state, EstimateJourneyState)
        else EstimateJourneyState(next_state)
    )
    allowed = _ESTIMATE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise BidReviewJourneyError(
            f"invalid estimate transition {current.value} -> {target.value}"
        )
    return target


def create_draft_estimate_version(
    *,
    estimate_id: str,
    version: int,
    report_version: BidReviewReportVersion,
    tenant_policy: BidReviewTenantPolicy,
    generated_by: str,
    generated_at: str | None = None,
    parent_version: int | None = None,
    guidance_inputs: Sequence[Any] | Iterable[Any] | None = None,
    change_summary: Sequence[Any] | Iterable[Any] | None = None,
    assumptions: Sequence[Any] | Iterable[Any] | None = None,
    pending_rfi_count: int | None = None,
    unresolved_item_count: int | None = None,
) -> BidReviewEstimateVersion:
    advisories: list[str] = []
    readiness = report_version.readiness_score
    if readiness < tenant_policy.minimum_recommended_readiness:
        advisories.append(
            "readiness below recommended threshold; draft generation remains advisory only"
        )
    if not tenant_policy.allow_draft_below_readiness_threshold:
        advisories.append(
            "tenant policy does not allow low-readiness drafts, but draft generation is not blocked"
        )
    return BidReviewEstimateVersion(
        project_id=report_version.project_id,
        estimate_id=estimate_id,
        version=version,
        state=EstimateJourneyState.DRAFT,
        source_report_version=report_version.version,
        source_document_set_id=report_version.source_document_set_id,
        readiness_score=readiness,
        unresolved_item_count=(
            report_version.unresolved_item_count
            if unresolved_item_count is None
            else unresolved_item_count
        ),
        pending_rfi_count=(
            report_version.pending_rfi_count
            if pending_rfi_count is None
            else pending_rfi_count
        ),
        assumptions=(
            _normalize_sequence(assumptions)
            if assumptions is not None
            else report_version.assumptions
        ),
        guidance_inputs=(
            _normalize_sequence(guidance_inputs)
            if guidance_inputs is not None
            else report_version.guidance_inputs
        ),
        tenant_rules_snapshot=report_version.tenant_rules_snapshot,
        generated_at=generated_at or report_version.generated_at,
        generated_by=generated_by,
        change_summary=(
            _normalize_sequence(change_summary)
            if change_summary is not None
            else report_version.change_summary
        ),
        parent_version=parent_version,
        advisories=tuple(advisories),
    )


def create_estimate_revision(
    current_version: BidReviewEstimateVersion,
    *,
    generated_by: str,
    change_summary: Sequence[Any] | Iterable[Any] | None = None,
    generated_at: str | None = None,
) -> BidReviewEstimateVersion:
    validate_estimate_transition(current_version.state, EstimateJourneyState.REVISED)
    return replace(
        current_version,
        version=current_version.version + 1,
        state=EstimateJourneyState.REVISED,
        parent_version=current_version.version,
        generated_at=generated_at or _utc_now(),
        generated_by=generated_by,
        change_summary=(
            _normalize_sequence(change_summary)
            if change_summary is not None
            else current_version.change_summary
        ),
        advisories=current_version.advisories,
    )


def evaluate_sales_order_conversion(
    *,
    estimate_version: BidReviewEstimateVersion,
    report_version: BidReviewReportVersion,
    tenant_policy: BidReviewTenantPolicy,
    pending_rfis: Sequence[Any] | Iterable[Any] | None = None,
    unresolved_assumptions: Sequence[Any] | Iterable[Any] | None = None,
) -> ConversionEligibilityResult:
    blocking_reasons: list[str] = []
    warnings: list[str] = []

    if estimate_version.project_id != report_version.project_id:
        blocking_reasons.append("cross-project conversion is not allowed")
    if estimate_version.source_report_version != report_version.version:
        blocking_reasons.append(
            "estimate does not reference the provided report version"
        )
    if estimate_version.source_document_set_id != report_version.source_document_set_id:
        blocking_reasons.append(
            "estimate and report document-set traceability mismatch"
        )

    if report_version.status in {
        BidReviewReportStatus.SUPERSEDED,
        BidReviewReportStatus.ARCHIVED,
    }:
        warnings.append(
            f"report version {report_version.version} is {report_version.status.value}"
        )

    if estimate_version.state == EstimateJourneyState.REJECTED:
        blocking_reasons.append("rejected estimates cannot convert to sales orders")
    elif estimate_version.state == EstimateJourneyState.DRAFT:
        blocking_reasons.append("draft estimates cannot convert to sales orders")
    elif estimate_version.state in {
        EstimateJourneyState.REVISED,
        EstimateJourneyState.SUPERSEDED,
        EstimateJourneyState.CUSTOMER_DECLINED,
        EstimateJourneyState.EXPIRED,
    }:
        blocking_reasons.append(
            f"estimate state {estimate_version.state.value} is not eligible for conversion"
        )

    gate = tenant_policy.sales_order_conversion_gate
    if gate == SalesOrderConversionGate.CUSTOMER_ACCEPTANCE:
        if estimate_version.state != EstimateJourneyState.CUSTOMER_ACCEPTED:
            blocking_reasons.append(
                "customer acceptance is required before sales-order conversion"
            )
    elif estimate_version.state not in {
        EstimateJourneyState.APPROVED_INTERNAL,
        EstimateJourneyState.SUBMITTED,
        EstimateJourneyState.CUSTOMER_ACCEPTED,
    }:
        blocking_reasons.append(
            "internal approval is required before sales-order conversion"
        )

    pending_rfi_values = _normalize_sequence(pending_rfis)
    if not pending_rfi_values and estimate_version.pending_rfi_count > 0:
        pending_rfi_values = tuple(
            f"pending-rfi-{index + 1}"
            for index in range(estimate_version.pending_rfi_count)
        )
    if pending_rfi_values:
        if tenant_policy.require_pending_rfi_acknowledgement:
            blocking_reasons.append("pending RFI acknowledgement is required")
        else:
            warnings.append("pending RFIs remain open")

    unresolved_values = _normalize_sequence(unresolved_assumptions)
    if not unresolved_values:
        unresolved_values = estimate_version.assumptions
    if unresolved_values:
        warnings.append("unresolved assumptions remain on the estimate")

    if estimate_version.readiness_score < tenant_policy.minimum_recommended_readiness:
        warning = (
            f"readiness {estimate_version.readiness_score} is below recommended "
            f"threshold {tenant_policy.minimum_recommended_readiness}"
        )
        if tenant_policy.allow_draft_below_readiness_threshold:
            warnings.append(warning)
        else:
            blocking_reasons.append(warning)

    eligible = not blocking_reasons
    return ConversionEligibilityResult(
        eligible=eligible,
        estimate_id=estimate_version.estimate_id,
        estimate_version=estimate_version.version,
        report_version=report_version.version,
        project_id=estimate_version.project_id,
        blocking_reasons=tuple(blocking_reasons),
        warnings=tuple(warnings),
        pending_rfis=pending_rfi_values,
        unresolved_assumptions=unresolved_values,
        policy_gate_used=gate,
        source_document_set_id=estimate_version.source_document_set_id,
        estimate_state=estimate_version.state,
    )

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from atlas_core.domain.bid_review_journey import (
    BidReviewAuditRecord,
    BidReviewEstimateVersion,
    BidReviewJourneyError,
    BidReviewReportStatus,
    BidReviewReportVersion,
    BidReviewTenantPolicy,
    EstimateJourneyState,
    RejectedDraftRetention,
    SalesOrderConversionGate,
    create_draft_estimate_version,
    create_estimate_revision,
    evaluate_sales_order_conversion,
    validate_estimate_transition,
    validate_report_transition,
)


def _policy(
    *,
    gate: SalesOrderConversionGate = SalesOrderConversionGate.CUSTOMER_ACCEPTANCE,
    allow_draft_below_readiness_threshold: bool = True,
    require_pending_rfi_acknowledgement: bool = False,
) -> BidReviewTenantPolicy:
    return BidReviewTenantPolicy(
        rejected_draft_retention=RejectedDraftRetention.ARCHIVE,
        sales_order_conversion_gate=gate,
        allow_draft_below_readiness_threshold=allow_draft_below_readiness_threshold,
        minimum_recommended_readiness=Decimal("0.70"),
        require_pending_rfi_acknowledgement=require_pending_rfi_acknowledgement,
        accepted_estimate_revision_required=True,
        allowance_policy_id="allowance-policy-1",
        lot_policy_id="lot-policy-1",
        contingency_policy_id="contingency-policy-1",
    )


def _report_version(
    *,
    project_id: str = "project-1",
    version: int = 1,
    status: BidReviewReportStatus = BidReviewReportStatus.PRELIMINARY,
    readiness_score: Decimal = Decimal("0.55"),
    parent_version: int | None = None,
) -> BidReviewReportVersion:
    policy = _policy()
    return BidReviewReportVersion(
        project_id=project_id,
        version=version,
        source_document_set_id="docs-set-1",
        parent_version=parent_version,
        status=status,
        readiness_score=readiness_score,
        unresolved_item_count=12,
        pending_rfi_count=3,
        assumptions=("assume owner-provided network drops",),
        guidance_inputs=("original review notes",),
        tenant_rules_snapshot=policy.to_dict(),
        generated_at="2026-07-26T12:00:00+00:00",
        generated_by="qa",
        change_summary=("initial report",),
    )


def _estimate_version(
    *,
    project_id: str = "project-1",
    version: int = 1,
    state: EstimateJourneyState = EstimateJourneyState.CUSTOMER_ACCEPTED,
    source_report_version: int = 1,
    readiness_score: Decimal = Decimal("0.82"),
    pending_rfi_count: int = 0,
    assumptions: tuple[str, ...] = (),
    source_document_set_id: str = "docs-set-1",
) -> BidReviewEstimateVersion:
    policy = _policy()
    return BidReviewEstimateVersion(
        project_id=project_id,
        estimate_id="estimate-1",
        version=version,
        state=state,
        source_report_version=source_report_version,
        source_document_set_id=source_document_set_id,
        readiness_score=readiness_score,
        unresolved_item_count=2,
        pending_rfi_count=pending_rfi_count,
        assumptions=assumptions,
        guidance_inputs=("review guidance",),
        tenant_rules_snapshot=policy.to_dict(),
        generated_at="2026-07-26T12:05:00+00:00",
        generated_by="qa",
        change_summary=("initial estimate",),
    )


def test_report_versions_are_immutable_and_versioned() -> None:
    report_v1 = _report_version(version=1, status=BidReviewReportStatus.PRELIMINARY)
    report_v2 = _report_version(
        version=2,
        status=validate_report_transition(
            report_v1.status, BidReviewReportStatus.REVISED
        ),
        parent_version=1,
    )

    assert report_v1.version == 1
    assert report_v1.status == BidReviewReportStatus.PRELIMINARY
    assert report_v2.version == 2
    assert report_v2.parent_version == 1
    with pytest.raises(FrozenInstanceError):
        report_v1.status = BidReviewReportStatus.ARCHIVED  # type: ignore[misc]


def test_draft_generation_does_not_block_low_readiness_reports() -> None:
    report = _report_version(readiness_score=Decimal("0.12"))
    draft = create_draft_estimate_version(
        estimate_id="estimate-1",
        version=1,
        report_version=report,
        tenant_policy=_policy(allow_draft_below_readiness_threshold=False),
        generated_by="qa",
    )

    assert draft.state == EstimateJourneyState.DRAFT
    assert draft.source_report_version == report.version
    assert draft.source_document_set_id == report.source_document_set_id
    assert draft.readiness_score == report.readiness_score
    assert draft.advisories


def test_rejected_draft_cannot_become_sales_order() -> None:
    draft = _estimate_version(state=EstimateJourneyState.DRAFT)
    rejected_state = validate_estimate_transition(
        draft.state, EstimateJourneyState.REJECTED
    )
    rejected = BidReviewEstimateVersion(
        **{
            **draft.to_dict(),
            "state": rejected_state,
        }
    )

    result = evaluate_sales_order_conversion(
        estimate_version=rejected,
        report_version=_report_version(),
        tenant_policy=_policy(),
    )

    assert not result.eligible
    assert any("rejected estimates" in reason for reason in result.blocking_reasons)


def test_internal_approval_and_customer_acceptance_remain_distinct() -> None:
    approved = validate_estimate_transition(
        EstimateJourneyState.DRAFT,
        EstimateJourneyState.APPROVED_INTERNAL,
    )
    submitted = validate_estimate_transition(approved, EstimateJourneyState.SUBMITTED)
    accepted = validate_estimate_transition(
        submitted, EstimateJourneyState.CUSTOMER_ACCEPTED
    )

    assert approved == EstimateJourneyState.APPROVED_INTERNAL
    assert submitted == EstimateJourneyState.SUBMITTED
    assert accepted == EstimateJourneyState.CUSTOMER_ACCEPTED

    with pytest.raises(BidReviewJourneyError):
        validate_estimate_transition(
            EstimateJourneyState.APPROVED_INTERNAL,
            EstimateJourneyState.CUSTOMER_ACCEPTED,
        )


def test_customer_acceptance_permits_conversion_under_default_policy() -> None:
    estimate = _estimate_version(state=EstimateJourneyState.CUSTOMER_ACCEPTED)
    result = evaluate_sales_order_conversion(
        estimate_version=estimate,
        report_version=_report_version(),
        tenant_policy=_policy(),
    )

    assert result.eligible is True
    assert result.policy_gate_used == SalesOrderConversionGate.CUSTOMER_ACCEPTANCE
    assert result.source_document_set_id == estimate.source_document_set_id


def test_internal_approval_permits_conversion_only_when_policy_allows() -> None:
    estimate = _estimate_version(state=EstimateJourneyState.APPROVED_INTERNAL)

    default_policy_result = evaluate_sales_order_conversion(
        estimate_version=estimate,
        report_version=_report_version(),
        tenant_policy=_policy(),
    )
    internal_gate_result = evaluate_sales_order_conversion(
        estimate_version=estimate,
        report_version=_report_version(),
        tenant_policy=_policy(gate=SalesOrderConversionGate.INTERNAL_APPROVAL),
    )

    assert default_policy_result.eligible is False
    assert internal_gate_result.eligible is True
    assert (
        internal_gate_result.policy_gate_used
        == SalesOrderConversionGate.INTERNAL_APPROVAL
    )


def test_accepted_estimate_changes_create_revisions() -> None:
    accepted = _estimate_version(
        version=3,
        state=EstimateJourneyState.CUSTOMER_ACCEPTED,
        source_report_version=2,
    )
    revised = create_estimate_revision(
        accepted,
        generated_by="qa",
        change_summary=("client scope update",),
    )

    assert revised.version == 4
    assert revised.parent_version == 3
    assert revised.state == EstimateJourneyState.REVISED
    assert revised.source_report_version == accepted.source_report_version
    assert revised.source_document_set_id == accepted.source_document_set_id


def test_sales_order_references_exact_estimate_and_report_versions() -> None:
    report = _report_version(version=4, status=BidReviewReportStatus.REVISED)
    estimate = _estimate_version(
        version=7,
        state=EstimateJourneyState.CUSTOMER_ACCEPTED,
        source_report_version=4,
    )

    result = evaluate_sales_order_conversion(
        estimate_version=estimate,
        report_version=report,
        tenant_policy=_policy(),
    )

    assert result.eligible is True
    assert result.estimate_id == estimate.estimate_id
    assert result.estimate_version == 7
    assert result.report_version == 4
    assert result.project_id == estimate.project_id


def test_pending_rfis_create_warnings_or_blockers_by_policy() -> None:
    estimate = _estimate_version(
        state=EstimateJourneyState.CUSTOMER_ACCEPTED,
        pending_rfi_count=2,
    )
    report = _report_version()

    warning_result = evaluate_sales_order_conversion(
        estimate_version=estimate,
        report_version=report,
        tenant_policy=_policy(require_pending_rfi_acknowledgement=False),
        pending_rfis=("RFI-11", "RFI-12"),
    )
    blocker_result = evaluate_sales_order_conversion(
        estimate_version=estimate,
        report_version=report,
        tenant_policy=_policy(require_pending_rfi_acknowledgement=True),
        pending_rfis=("RFI-11", "RFI-12"),
    )

    assert warning_result.eligible is True
    assert warning_result.warnings
    assert blocker_result.eligible is False
    assert any(
        "pending RFI acknowledgement" in reason
        for reason in blocker_result.blocking_reasons
    )


def test_invalid_transitions_fail_deterministically() -> None:
    with pytest.raises(BidReviewJourneyError, match="invalid report transition"):
        validate_report_transition(
            BidReviewReportStatus.PRELIMINARY,
            BidReviewReportStatus.SUPERSEDED,
        )

    with pytest.raises(BidReviewJourneyError, match="invalid estimate transition"):
        validate_estimate_transition(
            EstimateJourneyState.DRAFT,
            EstimateJourneyState.CUSTOMER_ACCEPTED,
        )


def test_no_cross_project_conversion() -> None:
    estimate = _estimate_version(project_id="project-a")
    report = _report_version(project_id="project-b")

    result = evaluate_sales_order_conversion(
        estimate_version=estimate,
        report_version=report,
        tenant_policy=_policy(),
    )

    assert result.eligible is False
    assert any(
        "cross-project conversion" in reason for reason in result.blocking_reasons
    )


def test_audit_records_preserve_transition_context() -> None:
    policy = _policy()
    audit = BidReviewAuditRecord(
        actor="qa",
        timestamp="2026-07-26T12:15:00+00:00",
        prior_state=EstimateJourneyState.APPROVED_INTERNAL.value,
        new_state=EstimateJourneyState.SUBMITTED.value,
        reason="customer copy sent",
        tenant_policy_snapshot=policy.to_dict(),
        project_guidance_snapshot={"guidance": "confirm alternates"},
        project_id="project-1",
        entity_type="estimate",
        entity_id="estimate-99",
    )

    payload = audit.to_dict()
    assert payload["actor"] == "qa"
    assert payload["prior_state"] == EstimateJourneyState.APPROVED_INTERNAL.value
    assert payload["new_state"] == EstimateJourneyState.SUBMITTED.value
    assert payload["tenant_policy_snapshot"]["sales_order_conversion_gate"] == (
        SalesOrderConversionGate.CUSTOMER_ACCEPTANCE.value
    )
    assert payload["project_guidance_snapshot"]["guidance"] == "confirm alternates"

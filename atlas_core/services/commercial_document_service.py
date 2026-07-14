"""Commercial document orchestration services for Atlas Core."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha1
from typing import Any
from uuid import NAMESPACE_DNS, uuid5

from atlas_core.domain.commercial_document import (
    ApprovalState,
    CommercialDocument,
    CommercialDocumentDiagnostic,
    CommercialDocumentLifecycleState,
    CommercialDocumentLineItem,
    CommercialDocumentRelationship,
    CommercialDocumentRevision,
    CommercialDocumentSyncMetadata,
    CommercialDocumentTotals,
    CommercialDocumentType,
    CommercialNumberingPolicy,
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _stable_hash(*parts: str) -> str:
    canonical = "|".join(part.strip() for part in parts)
    return sha1(canonical.encode("utf-8")).hexdigest()


@dataclass
class NumberPreview:
    tenant_id: str
    organization_id: str
    document_type: CommercialDocumentType
    preview_number: str


class CommercialNumberingService:
    """Organization-scoped tenant-safe numbering service with no number reuse."""

    def __init__(self, serialized_policies: list[dict[str, Any]] | None = None) -> None:
        self._policies: dict[
            tuple[str, str, CommercialDocumentType], CommercialNumberingPolicy
        ] = {}
        for payload in list(serialized_policies or []):
            if not isinstance(payload, dict):
                continue
            policy = CommercialNumberingPolicy(**payload)
            self.set_policy(policy)

    def set_policy(self, policy: CommercialNumberingPolicy) -> None:
        key = (policy.tenant_id, policy.organization_id, policy.document_type)
        self._policies[key] = policy

    def _policy(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
    ) -> CommercialNumberingPolicy:
        key = (tenant_id, organization_id, document_type)
        policy = self._policies.get(key)
        if policy is None:
            prefix = f"{organization_id}-{document_type.value}".upper().replace(
                "_", "-"
            )
            policy = CommercialNumberingPolicy(
                tenant_id=tenant_id,
                organization_id=organization_id,
                document_type=document_type,
                prefix=prefix,
            )
            self._policies[key] = policy
        return policy

    def preview_next_number(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
        context: dict[str, Any] | None = None,
    ) -> NumberPreview:
        policy = self._policy(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=document_type,
        )
        return NumberPreview(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=document_type,
            preview_number=policy.preview(context=context),
        )

    def allocate_number(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
        context: dict[str, Any] | None = None,
    ) -> str:
        policy = self._policy(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=document_type,
        )
        return policy.allocate(context=context)

    def to_payload(self) -> list[dict[str, Any]]:
        return [
            policy.to_dict()
            for policy in sorted(
                self._policies.values(),
                key=lambda item: (
                    item.tenant_id,
                    item.organization_id,
                    item.document_type.value,
                ),
            )
        ]

    def policy_snapshot(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
    ) -> dict[str, Any]:
        return self._policy(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=document_type,
        ).to_dict()


class CommercialDocumentService:
    """Reusable service for commercial document lifecycle and revision behavior."""

    def __init__(
        self, numbering_service: CommercialNumberingService | None = None
    ) -> None:
        self.numbering_service = numbering_service or CommercialNumberingService()
        self._line_counters: dict[str, int] = defaultdict(int)

    def create_document(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
        project_id: str | None = None,
        project_code: str | None = None,
        customer_id: str | None = None,
        vendor_id: str | None = None,
        document_id: str | None = None,
    ) -> CommercialDocument:
        doc_id = document_id or self.generate_document_id(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=document_type,
            project_id=project_id,
            project_code=project_code,
        )
        now = _utc_now()
        first_revision = CommercialDocumentRevision(
            revision_id=f"{doc_id}-r1",
            revision_number=1,
            lifecycle_state=CommercialDocumentLifecycleState.DRAFT,
            approval_state=ApprovalState.NOT_REQUESTED,
            revision_label="R1",
            revision_reason="Initial draft",
            revision_date=now,
            parent_revision_id=None,
            is_current=True,
            immutable=False,
            notes="Initial draft",
            lines=[],
            totals=CommercialDocumentTotals(),
            created_at=now,
            created_by="system",
        )
        return CommercialDocument(
            document_id=doc_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=document_type,
            project_id=project_id,
            project_code=project_code,
            customer_id=customer_id,
            vendor_id=vendor_id,
            lines=[],
            relationships=[],
            diagnostics=[],
            sync_metadata=CommercialDocumentSyncMetadata(),
            totals=CommercialDocumentTotals(),
            revisions=[first_revision],
            created_at=now,
            updated_at=now,
        )

    def generate_document_id(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
        project_id: str | None,
        project_code: str | None,
    ) -> str:
        timestamp = _utc_now()
        material = _stable_hash(
            tenant_id,
            organization_id,
            document_type.value,
            project_id or "",
            project_code or "",
            timestamp,
        )
        return f"doc-{material[:20]}"

    def generate_line_id(self, document: CommercialDocument) -> str:
        counter = self._line_counters[document.document_id] + 1
        self._line_counters[document.document_id] = counter
        value = uuid5(NAMESPACE_DNS, f"{document.document_id}:{counter}")
        return f"line-{value.hex[:16]}"

    def add_line(
        self,
        document: CommercialDocument,
        *,
        description: str,
        quantity: Decimal,
        unit_price: Decimal,
        sequence: int | None = None,
        unit_of_measure: str | None = None,
        discount: Decimal = Decimal("0"),
        tax_rate: Decimal = Decimal("0"),
        unit_cost: Decimal = Decimal("0"),
        project_code: str | None = None,
        product_or_service_reference: str | None = None,
        source_document_id: str | None = None,
        source_line_id: str | None = None,
        related_document_id: str | None = None,
        related_line_id: str | None = None,
    ) -> CommercialDocumentLineItem:
        self._assert_mutable(document)
        line = CommercialDocumentLineItem(
            line_id=self.generate_line_id(document),
            sequence=sequence or len(document.lines) + 1,
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            unit_cost=unit_cost,
            unit_of_measure=unit_of_measure,
            discount=discount,
            tax_rate=tax_rate,
            project_code=project_code,
            product_or_service_reference=product_or_service_reference,
            source_document_id=source_document_id,
            source_line_id=source_line_id,
            related_document_id=related_document_id,
            related_line_id=related_line_id,
        )
        document.lines.append(line)
        self.recompute_totals(document)
        self._sync_current_revision_snapshot(document)
        document.updated_at = _utc_now()
        return line

    def add_relationship(
        self,
        document: CommercialDocument,
        *,
        relationship_type: str,
        related_document_id: str,
        related_line_id: str | None = None,
        source_line_id: str | None = None,
    ) -> CommercialDocumentRelationship:
        relationship = CommercialDocumentRelationship(
            relationship_id=f"{document.document_id}:{relationship_type}:{len(document.relationships)+1}",
            relationship_type=relationship_type,
            related_document_id=related_document_id,
            related_line_id=related_line_id,
            source_line_id=source_line_id,
        )
        document.relationships.append(relationship)
        document.updated_at = _utc_now()
        self._sync_current_revision_snapshot(document)
        return relationship

    def set_approval_state(
        self,
        document: CommercialDocument,
        state: ApprovalState,
    ) -> None:
        if not isinstance(state, ApprovalState):
            state = ApprovalState(state)
        document.approval_state = state
        document.updated_at = _utc_now()

    def recompute_totals(
        self, document: CommercialDocument
    ) -> CommercialDocumentTotals:
        document.totals = CommercialDocumentTotals.from_lines(document.lines)
        self._sync_current_revision_snapshot(document)
        return document.totals

    def preview_number(self, document: CommercialDocument) -> NumberPreview:
        return self.numbering_service.preview_next_number(
            tenant_id=document.tenant_id,
            organization_id=document.organization_id,
            document_type=document.document_type,
            context={
                "project_code": document.project_code,
                "as_of": _utc_now(),
            },
        )

    def allocate_number(self, document: CommercialDocument) -> str:
        if document.document_number:
            return document.document_number
        number = self.numbering_service.allocate_number(
            tenant_id=document.tenant_id,
            organization_id=document.organization_id,
            document_type=document.document_type,
            context={
                "project_code": document.project_code,
                "as_of": _utc_now(),
            },
        )
        document.document_number = number
        document.numbering_policy_snapshot = self.numbering_service.policy_snapshot(
            tenant_id=document.tenant_id,
            organization_id=document.organization_id,
            document_type=document.document_type,
        )
        self._sync_current_revision_snapshot(document)
        document.updated_at = _utc_now()
        return number

    def transition_lifecycle(
        self,
        document: CommercialDocument,
        target_state: CommercialDocumentLifecycleState,
        *,
        reason: str,
    ) -> None:
        if not isinstance(target_state, CommercialDocumentLifecycleState):
            target_state = CommercialDocumentLifecycleState(target_state)
        if not document.can_transition_to(target_state):
            raise ValueError(
                f"invalid lifecycle transition: {document.lifecycle_state.value} -> {target_state.value}"
            )

        previous_state = document.lifecycle_state
        document.lifecycle_state = target_state
        document.updated_at = _utc_now()

        if target_state == CommercialDocumentLifecycleState.ISSUED:
            if document.approval_state != ApprovalState.APPROVED:
                raise ValueError("document must be approved before issuing")
            self.allocate_number(document)
            self._freeze_current_revision(document, reason=reason)
        elif (
            previous_state == CommercialDocumentLifecycleState.ISSUED
            and target_state == CommercialDocumentLifecycleState.IN_REVIEW
        ):
            self.start_new_revision(document, reason=reason)

    def start_new_revision(
        self,
        document: CommercialDocument,
        *,
        reason: str,
        actor: str = "system",
        revision_label: str | None = None,
    ) -> int:
        if document.lifecycle_state not in {
            CommercialDocumentLifecycleState.DRAFT,
            CommercialDocumentLifecycleState.IN_REVIEW,
            CommercialDocumentLifecycleState.APPROVED,
        }:
            raise ValueError("new revision can only start in editable lifecycle states")

        now = _utc_now()
        previous_revision = self._current_revision(document)

        document.revision_number += 1
        revision_id = f"{document.document_id}-r{document.revision_number}"
        if previous_revision is not None:
            previous_revision.is_current = False
            previous_revision.superseded_by_revision_id = revision_id
            previous_revision.superseded_at = now

        document.approval_state = ApprovalState.NOT_REQUESTED
        revision = CommercialDocumentRevision(
            revision_id=revision_id,
            revision_number=document.revision_number,
            lifecycle_state=document.lifecycle_state,
            approval_state=document.approval_state,
            revision_label=revision_label or f"R{document.revision_number}",
            revision_reason=reason,
            revision_date=now,
            parent_revision_id=(
                previous_revision.revision_id if previous_revision is not None else None
            ),
            is_current=True,
            immutable=False,
            notes=reason,
            lines=deepcopy(document.lines),
            totals=deepcopy(document.totals),
            created_at=now,
            created_by=actor,
        )
        document.revisions.append(revision)
        document.diagnostics.append(
            CommercialDocumentDiagnostic(
                code="revision_started",
                message=f"Revision {document.revision_number} started",
                details={"reason": reason},
            )
        )
        document.updated_at = now
        return document.revision_number

    def _freeze_current_revision(
        self, document: CommercialDocument, *, reason: str
    ) -> None:
        now = _utc_now()
        current_revision = self._current_revision(document)
        if current_revision is None:
            current_revision = CommercialDocumentRevision(
                revision_id=f"{document.document_id}-r{document.revision_number}",
                revision_number=document.revision_number,
                lifecycle_state=document.lifecycle_state,
                approval_state=document.approval_state,
                revision_label=f"R{document.revision_number}",
                revision_reason=reason,
                revision_date=now,
                is_current=True,
                immutable=True,
                issued_at=now,
                notes=reason,
                lines=deepcopy(document.lines),
                totals=deepcopy(document.totals),
                created_at=now,
                created_by="system",
            )
            document.revisions.append(current_revision)
            return

        current_revision.lifecycle_state = document.lifecycle_state
        current_revision.approval_state = document.approval_state
        current_revision.issued_at = now
        current_revision.immutable = True
        current_revision.revision_reason = reason
        current_revision.notes = reason
        current_revision.lines = deepcopy(document.lines)
        current_revision.totals = deepcopy(document.totals)
        current_revision.revision_date = now

    def add_diagnostic(
        self,
        document: CommercialDocument,
        diagnostic: CommercialDocumentDiagnostic,
    ) -> None:
        document.diagnostics.append(diagnostic)
        document.updated_at = _utc_now()

    def assign_terms_and_conditions(
        self,
        document: CommercialDocument,
        *,
        reference: dict[str, Any],
        snapshot: dict[str, Any],
        force: bool = False,
    ) -> None:
        if not force:
            self._assert_mutable(document)
        document.terms_and_conditions_reference = dict(reference)
        document.terms_and_conditions_snapshot = dict(snapshot)
        self._sync_current_revision_snapshot(document)
        document.updated_at = _utc_now()

    @staticmethod
    def assert_same_tenant(*documents: CommercialDocument) -> None:
        tenant_ids = {document.tenant_id for document in documents}
        if len(tenant_ids) > 1:
            raise ValueError("cross-tenant operations are not allowed")

    @staticmethod
    def snapshot(document: CommercialDocument) -> dict[str, Any]:
        return document.to_dict()

    @staticmethod
    def restore(payload: dict[str, Any]) -> CommercialDocument:
        return CommercialDocument.from_dict(payload)

    @staticmethod
    def _assert_mutable(document: CommercialDocument) -> None:
        if not document.is_mutable:
            raise ValueError(
                "document revision is immutable in current lifecycle state"
            )

    @staticmethod
    def _current_revision(
        document: CommercialDocument,
    ) -> CommercialDocumentRevision | None:
        for revision in list(document.revisions or []):
            if (
                revision.revision_number == document.revision_number
                and revision.is_current
            ):
                return revision
        for revision in list(document.revisions or []):
            if revision.revision_number == document.revision_number:
                return revision
        return None

    def _sync_current_revision_snapshot(self, document: CommercialDocument) -> None:
        current_revision = self._current_revision(document)
        if current_revision is None or current_revision.immutable:
            return
        current_revision.lifecycle_state = document.lifecycle_state
        current_revision.approval_state = document.approval_state
        current_revision.lines = deepcopy(document.lines)
        current_revision.totals = deepcopy(document.totals)

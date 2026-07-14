"""Transactions workspace orchestration built on commercial document foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_core.domain.commercial_document import (
    ApprovalState,
    CommercialDocument,
    CommercialDocumentLifecycleState,
    CommercialDocumentType,
    SyncStatus,
)
from atlas_core.services.commercial_document_service import (
    CommercialDocumentService,
    CommercialNumberingService,
)


@dataclass(frozen=True)
class TransactionsOverviewMetrics:
    draft_documents: int
    pending_approval: int
    issued_documents: int
    open_purchase_orders: int
    partially_received_purchase_orders: int
    vendor_bills_pending_sync: int
    customer_invoices_pending_sync: int
    sync_failures: int


class TransactionsWorkspaceService:
    """Reusable transactions workspace behavior across all document families."""

    def __init__(
        self,
        *,
        serialized_documents: list[dict[str, Any]] | None = None,
        serialized_numbering_policies: list[dict[str, Any]] | None = None,
        commercial_service: CommercialDocumentService | None = None,
    ) -> None:
        self._commercial_service = commercial_service or CommercialDocumentService(
            numbering_service=CommercialNumberingService(
                serialized_policies=serialized_numbering_policies
            )
        )
        self._documents: list[CommercialDocument] = [
            CommercialDocument.from_dict(item)
            for item in list(serialized_documents or [])
            if isinstance(item, dict)
        ]

    def list_documents(
        self,
        *,
        query: str = "",
        document_type: CommercialDocumentType | None = None,
        include_archived: bool = False,
        lifecycle_state: CommercialDocumentLifecycleState | None = None,
    ) -> list[CommercialDocument]:
        normalized_query = query.strip().lower()
        rows: list[CommercialDocument] = []
        for document in self._documents:
            if not include_archived and (
                document.lifecycle_state == CommercialDocumentLifecycleState.ARCHIVED
            ):
                continue
            if document_type is not None and document.document_type != document_type:
                continue
            if (
                lifecycle_state is not None
                and document.lifecycle_state != lifecycle_state
            ):
                continue
            if normalized_query:
                corpus = " ".join(
                    [
                        document.document_id,
                        document.document_number or "",
                        document.document_type.value,
                        document.project_id or "",
                        document.project_code or "",
                        document.customer_id or "",
                        document.vendor_id or "",
                    ]
                ).lower()
                if normalized_query not in corpus:
                    continue
            rows.append(document)
        rows.sort(key=lambda item: item.updated_at, reverse=True)
        return rows

    def create_draft(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        document_type: CommercialDocumentType,
        project_id: str | None = None,
        project_code: str | None = None,
        customer_id: str | None = None,
        vendor_id: str | None = None,
    ) -> CommercialDocument:
        if (
            document_type == CommercialDocumentType.ESTIMATE
            and not (project_id or "").strip()
            and not (customer_id or "").strip()
        ):
            raise ValueError("standalone estimates require customer_id")
        document = self._commercial_service.create_document(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=document_type,
            project_id=project_id,
            project_code=project_code,
            customer_id=customer_id,
            vendor_id=vendor_id,
        )
        self._documents.append(document)
        return document

    def preview_number(self, document_id: str) -> str:
        document = self._required_document(document_id)
        return self._commercial_service.preview_number(document).preview_number

    def issue_document(self, *, document_id: str, reason: str) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.lifecycle_state == CommercialDocumentLifecycleState.DRAFT:
            self._commercial_service.transition_lifecycle(
                document,
                CommercialDocumentLifecycleState.IN_REVIEW,
                reason=reason,
            )
        if document.lifecycle_state == CommercialDocumentLifecycleState.IN_REVIEW:
            self._commercial_service.transition_lifecycle(
                document,
                CommercialDocumentLifecycleState.APPROVED,
                reason=reason,
            )
        self._commercial_service.transition_lifecycle(
            document,
            CommercialDocumentLifecycleState.ISSUED,
            reason=reason,
        )
        return document

    def create_draft_revision(
        self,
        *,
        document_id: str,
        reason: str,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.lifecycle_state == CommercialDocumentLifecycleState.ISSUED:
            document.lifecycle_state = CommercialDocumentLifecycleState.DRAFT
            document.approval_state = ApprovalState.NOT_REQUESTED
            self._commercial_service.start_new_revision(document, reason=reason)
            return document
        self._commercial_service.start_new_revision(document, reason=reason)
        return document

    def get_document(self, document_id: str) -> CommercialDocument | None:
        normalized_id = document_id.strip()
        for document in self._documents:
            if document.document_id == normalized_id:
                return document
        return None

    def update_draft_metadata(
        self,
        *,
        document_id: str,
        project_id: str | None,
        project_code: str | None,
        customer_id: str | None,
        vendor_id: str | None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if not document.is_mutable:
            raise ValueError("only mutable drafts/review documents can be edited")
        normalized_project_id = project_id.strip() or None if project_id else None
        normalized_customer_id = customer_id.strip() or None if customer_id else None
        if (
            document.document_type == CommercialDocumentType.ESTIMATE
            and not normalized_project_id
            and not normalized_customer_id
        ):
            raise ValueError("standalone estimates require customer_id")
        document.project_id = normalized_project_id
        document.project_code = project_code.strip() or None if project_code else None
        document.customer_id = normalized_customer_id
        document.vendor_id = vendor_id.strip() or None if vendor_id else None
        return document

    def set_approval_state(
        self,
        *,
        document_id: str,
        approval_state: ApprovalState,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        self._commercial_service.set_approval_state(document, approval_state)
        return document

    def set_sync_status(
        self,
        *,
        document_id: str,
        sync_status: SyncStatus,
        failure_code: str | None = None,
        failure_message: str | None = None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if not isinstance(sync_status, SyncStatus):
            sync_status = SyncStatus(sync_status)
        document.sync_metadata.status = sync_status
        document.sync_metadata.failure_code = failure_code
        document.sync_metadata.failure_message = failure_message
        return document

    def archive_document(self, document_id: str) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.lifecycle_state != CommercialDocumentLifecycleState.ARCHIVED:
            document.lifecycle_state = CommercialDocumentLifecycleState.ARCHIVED
        return document

    def restore_document(self, document_id: str) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.lifecycle_state == CommercialDocumentLifecycleState.ARCHIVED:
            document.lifecycle_state = CommercialDocumentLifecycleState.DRAFT
            document.approval_state = ApprovalState.NOT_REQUESTED
        return document

    def overview_metrics(self) -> TransactionsOverviewMetrics:
        draft_documents = sum(
            1
            for document in self._documents
            if document.lifecycle_state == CommercialDocumentLifecycleState.DRAFT
        )
        pending_approval = sum(
            1
            for document in self._documents
            if document.approval_state
            in {
                ApprovalState.PENDING,
                ApprovalState.REJECTED,
            }
        )
        issued_documents = sum(
            1
            for document in self._documents
            if document.lifecycle_state == CommercialDocumentLifecycleState.ISSUED
        )
        open_purchase_orders = sum(
            1
            for document in self._documents
            if document.document_type == CommercialDocumentType.PURCHASE_ORDER
            and document.lifecycle_state
            not in {
                CommercialDocumentLifecycleState.CLOSED,
                CommercialDocumentLifecycleState.FULFILLED,
                CommercialDocumentLifecycleState.ARCHIVED,
            }
        )
        partially_received_purchase_orders = sum(
            1
            for document in self._documents
            if document.document_type == CommercialDocumentType.PURCHASE_ORDER
            and document.lifecycle_state
            == CommercialDocumentLifecycleState.PARTIALLY_FULFILLED
        )
        vendor_bills_pending_sync = sum(
            1
            for document in self._documents
            if document.document_type == CommercialDocumentType.VENDOR_BILL
            and document.sync_metadata.status == SyncStatus.READY
        )
        customer_invoices_pending_sync = sum(
            1
            for document in self._documents
            if document.document_type == CommercialDocumentType.CUSTOMER_INVOICE
            and document.sync_metadata.status == SyncStatus.READY
        )
        sync_failures = sum(
            1
            for document in self._documents
            if document.sync_metadata.status == SyncStatus.FAILED
        )

        return TransactionsOverviewMetrics(
            draft_documents=draft_documents,
            pending_approval=pending_approval,
            issued_documents=issued_documents,
            open_purchase_orders=open_purchase_orders,
            partially_received_purchase_orders=partially_received_purchase_orders,
            vendor_bills_pending_sync=vendor_bills_pending_sync,
            customer_invoices_pending_sync=customer_invoices_pending_sync,
            sync_failures=sync_failures,
        )

    def to_payload(self) -> list[dict[str, Any]]:
        return [document.to_dict() for document in self._documents]

    def numbering_policy_payload(self) -> list[dict[str, Any]]:
        return self._commercial_service.numbering_service.to_payload()

    def _required_document(self, document_id: str) -> CommercialDocument:
        document = self.get_document(document_id)
        if document is None:
            raise ValueError("document was not found")
        return document

"""Transactions workspace orchestration built on commercial document foundation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from atlas_core.domain.commercial_document import (
    ApprovalState,
    CommercialDocument,
    CommercialDocumentDiagnostic,
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
        serialized_terms_blocks: list[dict[str, Any]] | None = None,
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
        self._terms_blocks: list[dict[str, Any]] = [
            dict(item)
            for item in list(serialized_terms_blocks or [])
            if isinstance(item, dict)
        ]

    def _document_family(self, document_type: CommercialDocumentType) -> str:
        return document_type.value

    def _active_terms_blocks_for_family(
        self,
        *,
        document_family: str,
        customer_id: str | None,
        project_id: str | None,
        transaction_id: str | None,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for item in list(self._terms_blocks or []):
            family = str(item.get("document_family") or "").strip().lower()
            if family != document_family:
                continue
            if bool(item.get("archived", False)):
                continue
            if str(item.get("status") or "").strip().lower() != "active":
                continue
            scope_transaction_id = str(item.get("transaction_id") or "").strip() or None
            scope_project_id = str(item.get("project_id") or "").strip() or None
            scope_customer_id = str(item.get("customer_id") or "").strip() or None
            if scope_transaction_id and scope_transaction_id != (transaction_id or ""):
                continue
            if scope_project_id and scope_project_id != (project_id or ""):
                continue
            if scope_customer_id and scope_customer_id != (customer_id or ""):
                continue
            candidates.append(dict(item))
        return candidates

    def _resolve_terms_block(
        self,
        *,
        document_type: CommercialDocumentType,
        customer_id: str | None,
        project_id: str | None,
        transaction_id: str | None,
        explicit_block_id: str | None = None,
    ) -> dict[str, Any] | None:
        family = self._document_family(document_type)
        candidates = self._active_terms_blocks_for_family(
            document_family=family,
            customer_id=customer_id,
            project_id=project_id,
            transaction_id=transaction_id,
        )
        if explicit_block_id:
            normalized_id = explicit_block_id.strip()
            for item in candidates:
                if str(item.get("block_id") or "").strip() == normalized_id:
                    return item
            return None
        if not candidates:
            return None

        def _scope_rank(item: dict[str, Any]) -> int:
            if str(item.get("transaction_id") or "").strip():
                return 4
            if str(item.get("project_id") or "").strip():
                return 3
            if str(item.get("customer_id") or "").strip():
                return 2
            return 1

        candidates.sort(
            key=lambda item: (
                _scope_rank(item),
                int(item.get("version") or 0),
                str(item.get("updated_at") or ""),
            ),
            reverse=True,
        )
        return candidates[0]

    def _default_terms_block_id(self, *, document_family: str) -> str | None:
        defaults = [
            item
            for item in self._terms_blocks
            if str(item.get("document_family") or "").strip().lower() == document_family
            and bool(item.get("is_default", False))
            and not bool(item.get("archived", False))
            and str(item.get("status") or "").strip().lower() == "active"
            and not str(item.get("customer_id") or "").strip()
            and not str(item.get("project_id") or "").strip()
            and not str(item.get("transaction_id") or "").strip()
        ]
        if not defaults:
            return None
        defaults.sort(
            key=lambda item: (
                int(item.get("version") or 0),
                str(item.get("updated_at") or ""),
            ),
            reverse=True,
        )
        return str(defaults[0].get("block_id") or "").strip() or None

    def _terms_reference_and_snapshot(
        self,
        *,
        document_type: CommercialDocumentType,
        customer_id: str | None,
        project_id: str | None,
        transaction_id: str | None,
        explicit_block_id: str | None = None,
        source: str = "resolved",
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        block = self._resolve_terms_block(
            document_type=document_type,
            customer_id=customer_id,
            project_id=project_id,
            transaction_id=transaction_id,
            explicit_block_id=explicit_block_id,
        )
        if block is None:
            return None
        family = self._document_family(document_type)
        reference = {
            "block_id": str(block.get("block_id") or ""),
            "document_family": family,
            "version": int(block.get("version") or 1),
            "source": source,
            "is_default": bool(block.get("is_default", False)),
            "customer_id": str(block.get("customer_id") or "").strip() or None,
            "project_id": str(block.get("project_id") or "").strip() or None,
            "transaction_id": str(block.get("transaction_id") or "").strip() or None,
            "resolved_default_block_id": self._default_terms_block_id(
                document_family=family
            ),
        }
        snapshot = {
            "block_id": str(block.get("block_id") or ""),
            "title": str(block.get("title") or ""),
            "document_family": family,
            "version": int(block.get("version") or 1),
            "content": str(block.get("content") or ""),
            "effective_date": str(block.get("effective_date") or "").strip() or None,
            "expiration_date": str(block.get("expiration_date") or "").strip() or None,
        }
        return reference, snapshot

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
        if document.document_type in {
            CommercialDocumentType.ESTIMATE,
            CommercialDocumentType.SALES_ORDER,
        }:
            terms_payload = self._terms_reference_and_snapshot(
                document_type=document.document_type,
                customer_id=document.customer_id,
                project_id=document.project_id,
                transaction_id=document.document_id,
            )
            if terms_payload is not None:
                reference, snapshot = terms_payload
                self._commercial_service.assign_terms_and_conditions(
                    document,
                    reference=reference,
                    snapshot=snapshot,
                )
        self._documents.append(document)
        return document

    def refresh_draft_terms(
        self,
        *,
        document_id: str,
        explicit_block_id: str | None = None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if not document.is_mutable:
            raise ValueError(
                "terms can only be refreshed on mutable drafts/review documents"
            )
        payload = self._terms_reference_and_snapshot(
            document_type=document.document_type,
            customer_id=document.customer_id,
            project_id=document.project_id,
            transaction_id=document.document_id,
            explicit_block_id=explicit_block_id,
            source="explicit_refresh",
        )
        if payload is None:
            raise ValueError("no active terms and conditions block is available")
        reference, snapshot = payload
        self._commercial_service.assign_terms_and_conditions(
            document,
            reference=reference,
            snapshot=snapshot,
        )
        return document

    def create_sales_order_from_estimate(
        self,
        *,
        estimate_document_id: str,
        inherit_terms_from_estimate: bool = True,
    ) -> CommercialDocument:
        estimate = self._required_document(estimate_document_id)
        if estimate.document_type != CommercialDocumentType.ESTIMATE:
            raise ValueError("source document must be an estimate")
        is_estimate_approved = (
            estimate.lifecycle_state
            in {
                CommercialDocumentLifecycleState.APPROVED,
                CommercialDocumentLifecycleState.ISSUED,
            }
            or estimate.approval_state == ApprovalState.APPROVED
        )
        if not is_estimate_approved:
            raise ValueError("sales order source estimate must be approved or issued")

        sales_order = self.create_draft(
            tenant_id=estimate.tenant_id,
            organization_id=estimate.organization_id,
            document_type=CommercialDocumentType.SALES_ORDER,
            project_id=estimate.project_id,
            project_code=estimate.project_code,
            customer_id=estimate.customer_id,
            vendor_id=estimate.vendor_id,
        )

        for line in list(estimate.lines or []):
            self._commercial_service.add_line(
                sales_order,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                sequence=line.sequence,
                unit_of_measure=line.unit_of_measure,
                discount=line.discount,
                tax_rate=line.tax_rate,
                unit_cost=line.unit_cost,
                project_code=line.project_code,
                product_or_service_reference=line.product_or_service_reference,
                source_document_id=estimate.document_id,
                source_line_id=line.line_id,
                related_document_id=estimate.document_id,
                related_line_id=line.line_id,
            )

        self._commercial_service.add_relationship(
            sales_order,
            relationship_type="derived_from_estimate",
            related_document_id=estimate.document_id,
        )
        self._commercial_service.add_diagnostic(
            sales_order,
            CommercialDocumentDiagnostic(
                code="estimate_source_revision",
                message="Sales order created from estimate source revision",
                details={
                    "source_estimate_id": estimate.document_id,
                    "source_estimate_revision_number": estimate.revision_number,
                    "source_estimate_document_number": estimate.document_number,
                },
            ),
        )

        if inherit_terms_from_estimate and estimate.terms_and_conditions_snapshot:
            inherited_reference = dict(estimate.terms_and_conditions_reference or {})
            inherited_reference["source"] = "inherited_from_estimate"
            inherited_reference["inherited_from_document_id"] = estimate.document_id
            self._commercial_service.assign_terms_and_conditions(
                sales_order,
                reference=inherited_reference,
                snapshot=deepcopy(dict(estimate.terms_and_conditions_snapshot)),
            )
        else:
            payload = self._terms_reference_and_snapshot(
                document_type=CommercialDocumentType.SALES_ORDER,
                customer_id=sales_order.customer_id,
                project_id=sales_order.project_id,
                transaction_id=sales_order.document_id,
            )
            if payload is not None:
                reference, snapshot = payload
                self._commercial_service.assign_terms_and_conditions(
                    sales_order,
                    reference=reference,
                    snapshot=snapshot,
                )
        return sales_order

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

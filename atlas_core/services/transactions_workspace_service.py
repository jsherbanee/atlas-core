"""Transactions workspace orchestration built on commercial document foundation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha1
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
from atlas_core.services.commercial_document_pdf_export_service import (
    CommercialDocumentPdfExportService,
    PdfSectionConfig,
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


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
        self._pdf_export_service = CommercialDocumentPdfExportService()

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

    def create_return_order(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        customer_id: str | None,
        project_id: str | None = None,
        project_code: str | None = None,
        source_sales_order_id: str | None = None,
        source_invoice_id: str | None = None,
        return_reason: str = "other",
        return_type: str = "product",
        requested_date: str | None = None,
        notes: str | None = None,
    ) -> CommercialDocument:
        source_sales_order = (
            self._required_document(source_sales_order_id)
            if source_sales_order_id
            else None
        )
        source_invoice = (
            self._required_document(source_invoice_id) if source_invoice_id else None
        )
        derived_customer_id = (
            customer_id
            or (source_sales_order.customer_id if source_sales_order else None)
            or (source_invoice.customer_id if source_invoice else None)
        )
        if not (derived_customer_id or "").strip():
            raise ValueError(
                "return orders require customer_id or linked source document"
            )

        document = self.create_draft(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=CommercialDocumentType.RETURN_ORDER,
            project_id=project_id
            or (source_sales_order.project_id if source_sales_order else None)
            or (source_invoice.project_id if source_invoice else None),
            project_code=project_code
            or (source_sales_order.project_code if source_sales_order else None)
            or (source_invoice.project_code if source_invoice else None),
            customer_id=derived_customer_id,
        )
        document.source_sales_order_id = (
            source_sales_order.document_id if source_sales_order else None
        )
        document.source_invoice_id = (
            source_invoice.document_id if source_invoice else None
        )
        self._commercial_service.set_document_metadata(
            document,
            metadata={
                "return_reason": return_reason.strip().lower(),
                "return_type": return_type.strip().lower(),
                "requested_date": requested_date,
                "received_date": None,
                "approved_credit_amount": "0",
                "restocking_fee": "0",
                "tax_adjustment": "0",
                "notes": notes,
                "generated_credit_memo_id": None,
            },
        )
        if source_sales_order is not None:
            self._commercial_service.add_relationship(
                document,
                relationship_type="source_sales_order",
                related_document_id=source_sales_order.document_id,
            )
        if source_invoice is not None:
            self._commercial_service.add_relationship(
                document,
                relationship_type="source_invoice",
                related_document_id=source_invoice.document_id,
            )
        return document

    def add_return_order_line(
        self,
        *,
        return_order_document_id: str,
        description: str,
        quantity: Decimal,
        original_unit_price: Decimal,
        line_type: str,
        approved_return_quantity: Decimal | None = None,
        restocking_fee: Decimal = Decimal("0"),
        tax_adjustment: Decimal = Decimal("0"),
        product_or_service_reference: str | None = None,
        source_document_id: str | None = None,
        source_line_id: str | None = None,
        related_document_id: str | None = None,
        related_line_id: str | None = None,
        inventory_disposition_hook: str | None = None,
    ) -> CommercialDocument:
        document = self._required_document(return_order_document_id)
        if document.document_type != CommercialDocumentType.RETURN_ORDER:
            raise ValueError("document must be a return order")
        approved_quantity = approved_return_quantity or quantity
        approved_credit_amount = approved_quantity * original_unit_price
        self._commercial_service.add_line(
            document,
            description=description,
            quantity=quantity,
            unit_price=original_unit_price,
            unit_cost=Decimal("0"),
            product_or_service_reference=product_or_service_reference,
            source_document_id=source_document_id,
            source_line_id=source_line_id,
            related_document_id=related_document_id,
            related_line_id=related_line_id,
            line_metadata={
                "line_type": line_type.strip().lower(),
                "requested_return_quantity": str(quantity),
                "approved_return_quantity": str(approved_quantity),
                "original_unit_price": str(original_unit_price),
                "approved_credit_amount": str(approved_credit_amount),
                "restocking_fee": str(restocking_fee),
                "tax_adjustment": str(tax_adjustment),
                "inspection_status": None,
                "inventory_disposition_hook": inventory_disposition_hook,
            },
        )
        self._recalculate_return_order_financials(document)
        return document

    def request_return_order(
        self, *, document_id: str, reason: str
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.document_type != CommercialDocumentType.RETURN_ORDER:
            raise ValueError("document must be a return order")
        self._commercial_service.transition_lifecycle(
            document,
            CommercialDocumentLifecycleState.REQUESTED,
            reason=reason,
        )
        return document

    def approve_return_order(
        self, *, document_id: str, reason: str
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.document_type != CommercialDocumentType.RETURN_ORDER:
            raise ValueError("document must be a return order")
        if document.lifecycle_state == CommercialDocumentLifecycleState.DRAFT:
            self.request_return_order(document_id=document_id, reason=reason)
        self._commercial_service.set_approval_state(document, ApprovalState.APPROVED)
        self._commercial_service.transition_lifecycle(
            document,
            CommercialDocumentLifecycleState.APPROVED,
            reason=reason,
        )
        return document

    def receive_return_order(
        self,
        *,
        document_id: str,
        partial: bool,
        received_date: str | None,
        inventory_disposition: str | None = None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.document_type != CommercialDocumentType.RETURN_ORDER:
            raise ValueError("document must be a return order")
        if document.lifecycle_state == CommercialDocumentLifecycleState.APPROVED:
            self._commercial_service.transition_lifecycle(
                document,
                CommercialDocumentLifecycleState.AWAITING_RETURN,
                reason="Awaiting customer return",
            )
        target_state = (
            CommercialDocumentLifecycleState.PARTIALLY_RECEIVED
            if partial
            else CommercialDocumentLifecycleState.RECEIVED
        )
        self._commercial_service.transition_lifecycle(
            document,
            target_state,
            reason="Return received",
        )
        metadata = dict(document.document_metadata or {})
        metadata["received_date"] = received_date
        if inventory_disposition:
            metadata["inventory_disposition"] = inventory_disposition
        self._commercial_service.set_document_metadata(
            document,
            metadata=metadata,
            force=True,
        )
        return document

    def inspect_return_order(
        self,
        *,
        document_id: str,
        inspection_status: str,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.document_type != CommercialDocumentType.RETURN_ORDER:
            raise ValueError("document must be a return order")
        if document.lifecycle_state in {
            CommercialDocumentLifecycleState.APPROVED,
            CommercialDocumentLifecycleState.AWAITING_RETURN,
        }:
            if document.lifecycle_state == CommercialDocumentLifecycleState.APPROVED:
                self._commercial_service.transition_lifecycle(
                    document,
                    CommercialDocumentLifecycleState.AWAITING_RETURN,
                    reason="Inspection initiated",
                )
            self._commercial_service.transition_lifecycle(
                document,
                CommercialDocumentLifecycleState.RECEIVED,
                reason="Inspection initiated",
            )
        self._commercial_service.transition_lifecycle(
            document,
            CommercialDocumentLifecycleState.INSPECTED,
            reason="Return inspected",
        )
        for line in document.lines:
            metadata = dict(line.line_metadata or {})
            metadata["inspection_status"] = inspection_status
            line.line_metadata = metadata
        self._commercial_service.set_document_metadata(
            document,
            metadata={"inspection_status": inspection_status},
            force=True,
        )
        return document

    def process_return_order(
        self,
        *,
        document_id: str,
        actor: str,
        reason: str = "Return order processed",
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.document_type != CommercialDocumentType.RETURN_ORDER:
            raise ValueError("document must be a return order")
        existing_credit_memo_id = _safe_text(
            (document.document_metadata or {}).get("generated_credit_memo_id"), ""
        )
        if existing_credit_memo_id:
            raise ValueError("credit memo already generated for return order")
        self._validate_return_order(document)
        self._recalculate_return_order_financials(document, force=True)

        credit_memo = self._generate_credit_memo_for_return_order(
            return_order=document,
            actor=actor,
        )
        self._commercial_service.set_document_metadata(
            document,
            metadata={
                "generated_credit_memo_id": credit_memo.document_id,
                "processed_at": _utc_now(),
                "processed_by": actor,
            },
            force=True,
        )
        self._commercial_service.add_relationship(
            document,
            relationship_type="generated_credit_memo",
            related_document_id=credit_memo.document_id,
        )
        self._commercial_service.transition_lifecycle(
            document,
            CommercialDocumentLifecycleState.PROCESSED,
            reason=reason,
        )
        self._commercial_service.add_diagnostic(
            document,
            CommercialDocumentDiagnostic(
                code="return_order_processed",
                message="Return order processed into credit memo",
                details={
                    "credit_memo_id": credit_memo.document_id,
                    "credit_memo_number": credit_memo.document_number,
                },
            ),
        )
        return credit_memo

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
        actor: str = "atlas-ui",
        revision_label: str | None = None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.lifecycle_state == CommercialDocumentLifecycleState.ISSUED:
            document.lifecycle_state = CommercialDocumentLifecycleState.DRAFT
            document.approval_state = ApprovalState.NOT_REQUESTED
            self._commercial_service.start_new_revision(
                document,
                reason=reason,
                actor=actor,
                revision_label=revision_label,
            )
            return document
        self._commercial_service.start_new_revision(
            document,
            reason=reason,
            actor=actor,
            revision_label=revision_label,
        )
        return document

    def duplicate_document(
        self,
        *,
        document_id: str,
        actor: str,
    ) -> CommercialDocument:
        source = self._required_document(document_id)
        if source.document_type not in {
            CommercialDocumentType.ESTIMATE,
            CommercialDocumentType.SALES_ORDER,
        }:
            raise ValueError("only estimates and sales orders are supported")

        duplicate = self.create_draft(
            tenant_id=source.tenant_id,
            organization_id=source.organization_id,
            document_type=source.document_type,
            project_id=source.project_id,
            project_code=source.project_code,
            customer_id=source.customer_id,
            vendor_id=source.vendor_id,
        )

        for line in list(source.lines or []):
            self._commercial_service.add_line(
                duplicate,
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
            )

        if source.terms_and_conditions_snapshot:
            reference = dict(source.terms_and_conditions_reference or {})
            reference["source"] = "duplicated_snapshot"
            reference["duplicated_from_document_id"] = source.document_id
            self._commercial_service.assign_terms_and_conditions(
                duplicate,
                reference=reference,
                snapshot=deepcopy(dict(source.terms_and_conditions_snapshot)),
            )

        duplicate.source_document_id = source.document_id
        duplicate.source_relationship_type = "duplicate_of"
        duplicate.duplicated_from_document_id = source.document_id
        duplicate.duplicated_by = actor
        duplicate.duplicated_at = _utc_now()
        duplicate.numbering_policy_snapshot = deepcopy(source.numbering_policy_snapshot)

        self._commercial_service.add_relationship(
            duplicate,
            relationship_type="duplicate_of",
            related_document_id=source.document_id,
        )
        self._commercial_service.add_diagnostic(
            duplicate,
            CommercialDocumentDiagnostic(
                code="document_duplicated",
                message="Draft duplicated from source document",
                details={
                    "source_document_id": source.document_id,
                    "source_document_number": source.document_number,
                    "duplicated_by": actor,
                    "duplicated_at": duplicate.duplicated_at,
                },
            ),
        )
        self._commercial_service.allocate_number(duplicate)
        return duplicate

    def revision_history(self, *, document_id: str) -> list[dict[str, Any]]:
        document = self._required_document(document_id)
        rows = [
            {
                "revision_id": revision.revision_id,
                "revision_number": revision.revision_number,
                "revision_label": revision.revision_label,
                "revision_reason": revision.revision_reason,
                "revision_date": revision.revision_date,
                "parent_revision_id": revision.parent_revision_id,
                "superseded_by_revision_id": revision.superseded_by_revision_id,
                "superseded_at": revision.superseded_at,
                "is_current": revision.is_current,
                "is_archived": revision.is_archived,
                "archived_at": revision.archived_at,
                "immutable": revision.immutable,
                "lifecycle_state": revision.lifecycle_state.value,
                "approval_state": revision.approval_state.value,
            }
            for revision in list(document.revisions or [])
        ]
        rows.sort(key=lambda item: int(item.get("revision_number") or 0))
        return rows

    def export_document_pdf(
        self,
        *,
        document_id: str,
        presentation: str,
        actor: str,
        revision_number: int | None = None,
        section_config: PdfSectionConfig | None = None,
        branding: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        document = self._required_document(document_id)
        normalized_presentation = presentation.strip().lower()
        if normalized_presentation not in {
            "internal_estimate",
            "customer_estimate",
            "sales_order",
            "return_order",
            "credit_memo",
        }:
            raise ValueError("unsupported presentation")

        target_revision_number = revision_number or document.revision_number
        revision = next(
            (
                item
                for item in list(document.revisions or [])
                if item.revision_number == target_revision_number
            ),
            None,
        )
        if revision is None:
            raise ValueError("revision was not found")

        config = section_config or PdfSectionConfig()
        payload = self._pdf_export_service.build_pdf_bytes(
            document=document,
            revision=revision,
            presentation=normalized_presentation,
            section_config=config,
            branding=branding,
        )
        file_name = self._pdf_export_service.suggested_filename(
            document=document,
            presentation=normalized_presentation,
            revision_number=revision.revision_number,
        )
        content_hash = sha1(payload).hexdigest()
        export_event = {
            "event": "pdf_exported",
            "actor": actor,
            "timestamp": _utc_now(),
            "presentation": normalized_presentation,
            "revision_number": revision.revision_number,
            "revision_id": revision.revision_id,
            "file_name": file_name,
            "content_hash": content_hash,
            "status": document.lifecycle_state.value,
            "is_archived_revision": revision.is_archived,
        }
        document.export_activity.append(export_event)
        return {
            "file_name": file_name,
            "mime_type": "application/pdf",
            "payload": payload,
            "revision_number": revision.revision_number,
            "content_hash": content_hash,
        }

    def enqueue_future_email_delivery(
        self,
        *,
        document_id: str,
        provider: str,
        recipient: str,
        subject: str,
        actor: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        message_template: str | None = None,
        attached_revision_number: int | None = None,
    ) -> dict[str, Any]:
        document = self._required_document(document_id)
        normalized_provider = provider.strip().lower()
        if normalized_provider not in {
            "microsoft_365",
            "google_workspace",
            "smtp",
            "approved_other",
        }:
            raise ValueError("unsupported email provider")
        entry = {
            "provider": normalized_provider,
            "recipient": recipient.strip(),
            "cc": list(cc or []),
            "bcc": list(bcc or []),
            "subject": subject.strip(),
            "message_template": (message_template or "").strip() or None,
            "attached_revision_number": attached_revision_number
            or document.revision_number,
            "sent_timestamp": None,
            "delivery_status": "queued_for_future",
            "provider_message_id": None,
            "created_at": _utc_now(),
            "created_by": actor,
        }
        document.future_email_metadata.append(entry)
        return dict(entry)

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

    def detail_credit_memo(self, *, document_id: str) -> dict[str, Any]:
        document = self._required_document(document_id)
        if document.document_type != CommercialDocumentType.CREDIT_MEMO:
            raise ValueError("document must be a credit memo")
        return {
            "document_id": document.document_id,
            "document_number": document.document_number,
            "customer_id": document.customer_id,
            "project_id": document.project_id,
            "project_code": document.project_code,
            "source_return_order_id": document.source_document_id,
            "source_sales_order_id": document.source_sales_order_id,
            "source_invoice_id": document.source_invoice_id,
            "lifecycle_state": document.lifecycle_state.value,
            "sync_status": document.sync_metadata.status.value,
            "approved_credit_amount": (document.document_metadata or {}).get(
                "approved_credit_amount"
            ),
            "restocking_fee": (document.document_metadata or {}).get("restocking_fee"),
            "tax_adjustment": (document.document_metadata or {}).get("tax_adjustment"),
        }

    def archive_document(self, document_id: str) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.lifecycle_state != CommercialDocumentLifecycleState.ARCHIVED:
            document.lifecycle_state = CommercialDocumentLifecycleState.ARCHIVED
        active_revision = next(
            (
                revision
                for revision in list(document.revisions or [])
                if revision.revision_number == document.revision_number
            ),
            None,
        )
        if active_revision is not None:
            active_revision.is_archived = True
            active_revision.archived_at = _utc_now()
        return document

    def restore_document(self, document_id: str) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.lifecycle_state == CommercialDocumentLifecycleState.ARCHIVED:
            document.lifecycle_state = CommercialDocumentLifecycleState.DRAFT
            document.approval_state = ApprovalState.NOT_REQUESTED
        active_revision = next(
            (
                revision
                for revision in list(document.revisions or [])
                if revision.revision_number == document.revision_number
            ),
            None,
        )
        if active_revision is not None:
            active_revision.is_archived = False
            active_revision.archived_at = None
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

    def _recalculate_return_order_financials(
        self,
        document: CommercialDocument,
        force: bool = False,
    ) -> CommercialDocument:
        subtotal = Decimal("0")
        restocking_total = Decimal("0")
        tax_total = Decimal("0")
        for line in list(document.lines or []):
            metadata = dict(line.line_metadata or {})
            approved_quantity = Decimal(
                str(metadata.get("approved_return_quantity") or line.quantity)
            )
            original_unit_price = Decimal(
                str(metadata.get("original_unit_price") or line.unit_price)
            )
            approved_credit_amount = approved_quantity * original_unit_price
            metadata["approved_credit_amount"] = str(approved_credit_amount)
            line.line_metadata = metadata
            subtotal += approved_credit_amount
            restocking_total += Decimal(str(metadata.get("restocking_fee") or "0"))
            tax_total += Decimal(str(metadata.get("tax_adjustment") or "0"))

        metadata = dict(document.document_metadata or {})
        restocking_total += Decimal(str(metadata.get("restocking_fee") or "0"))
        tax_total += Decimal(str(metadata.get("tax_adjustment") or "0"))
        approved_credit_amount = subtotal - restocking_total + tax_total
        self._commercial_service.set_totals(
            document,
            subtotal=subtotal,
            discount_total=restocking_total,
            tax_total=tax_total,
            grand_total=approved_credit_amount,
            force=force,
        )
        self._commercial_service.set_document_metadata(
            document,
            metadata={
                "approved_credit_amount": str(approved_credit_amount),
                "restocking_fee": str(restocking_total),
                "tax_adjustment": str(tax_total),
            },
            force=force,
        )
        return document

    def _validate_return_order(self, document: CommercialDocument) -> None:
        if not (document.customer_id or "").strip():
            raise ValueError("return order requires customer_id")
        if not document.lines:
            raise ValueError("return order requires at least one line")
        approved_credit_total = Decimal("0")
        for line in list(document.lines or []):
            metadata = dict(line.line_metadata or {})
            line_type = _safe_text(metadata.get("line_type"), "")
            if line_type not in {"product", "service"}:
                raise ValueError("return order lines must declare product or service")
            requested_quantity = Decimal(
                str(metadata.get("requested_return_quantity") or line.quantity)
            )
            approved_quantity = Decimal(
                str(metadata.get("approved_return_quantity") or line.quantity)
            )
            if approved_quantity < Decimal("0"):
                raise ValueError("approved return quantity cannot be negative")
            if approved_quantity > requested_quantity:
                raise ValueError(
                    "approved return quantity cannot exceed requested quantity"
                )
            approved_credit_total += Decimal(
                str(metadata.get("approved_credit_amount") or "0")
            )
        if approved_credit_total <= Decimal("0"):
            raise ValueError("return order must produce a positive approved credit")

    def _generate_credit_memo_for_return_order(
        self,
        *,
        return_order: CommercialDocument,
        actor: str,
    ) -> CommercialDocument:
        credit_memo = self.create_draft(
            tenant_id=return_order.tenant_id,
            organization_id=return_order.organization_id,
            document_type=CommercialDocumentType.CREDIT_MEMO,
            project_id=return_order.project_id,
            project_code=return_order.project_code,
            customer_id=return_order.customer_id,
        )
        credit_memo.source_document_id = return_order.document_id
        credit_memo.source_relationship_type = "generated_from_return_order"
        credit_memo.source_sales_order_id = return_order.source_sales_order_id
        credit_memo.source_invoice_id = return_order.source_invoice_id
        for line in list(return_order.lines or []):
            metadata = dict(line.line_metadata or {})
            approved_quantity = Decimal(
                str(metadata.get("approved_return_quantity") or line.quantity)
            )
            self._commercial_service.add_line(
                credit_memo,
                description=line.description,
                quantity=approved_quantity,
                unit_price=Decimal(
                    str(metadata.get("original_unit_price") or line.unit_price)
                ),
                sequence=line.sequence,
                unit_of_measure=line.unit_of_measure,
                discount=Decimal(str(metadata.get("restocking_fee") or "0")),
                tax_rate=Decimal("0"),
                product_or_service_reference=line.product_or_service_reference,
                source_document_id=return_order.document_id,
                source_line_id=line.line_id,
                related_document_id=line.related_document_id
                or return_order.document_id,
                related_line_id=line.related_line_id or line.line_id,
                line_metadata={
                    **metadata,
                    "original_return_order_id": return_order.document_id,
                    "original_source_document_id": line.source_document_id,
                    "original_source_line_id": line.source_line_id,
                },
            )
        self._recalculate_return_order_financials(credit_memo)
        self._commercial_service.set_document_metadata(
            credit_memo,
            metadata={
                "approved_credit_amount": (return_order.document_metadata or {}).get(
                    "approved_credit_amount", "0"
                ),
                "restocking_fee": (return_order.document_metadata or {}).get(
                    "restocking_fee", "0"
                ),
                "tax_adjustment": (return_order.document_metadata or {}).get(
                    "tax_adjustment", "0"
                ),
                "created_from_return_order_id": return_order.document_id,
            },
        )
        self._commercial_service.add_relationship(
            credit_memo,
            relationship_type="source_return_order",
            related_document_id=return_order.document_id,
        )
        if return_order.source_sales_order_id:
            self._commercial_service.add_relationship(
                credit_memo,
                relationship_type="source_sales_order",
                related_document_id=return_order.source_sales_order_id,
            )
        if return_order.source_invoice_id:
            self._commercial_service.add_relationship(
                credit_memo,
                relationship_type="source_invoice",
                related_document_id=return_order.source_invoice_id,
            )
        self._commercial_service.allocate_number(credit_memo)
        self._commercial_service.set_approval_state(
            credit_memo,
            ApprovalState.APPROVED,
        )
        self.issue_document(
            document_id=credit_memo.document_id,
            reason="Credit memo generated from return order",
        )
        self._commercial_service.add_diagnostic(
            credit_memo,
            CommercialDocumentDiagnostic(
                code="credit_memo_generated",
                message="Credit memo generated from processed return order",
                details={
                    "return_order_id": return_order.document_id,
                    "generated_by": actor,
                },
            ),
        )
        return credit_memo


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    return normalized or default

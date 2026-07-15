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
from atlas_core.contracts.document_generation_contracts import (
    OutputFormat,
    RenderRequest,
)
from atlas_core.services.commercial_document_service import (
    CommercialDocumentService,
    CommercialNumberingService,
)
from atlas_core.services.commercial_document_pdf_export_service import (
    CommercialDocumentPdfExportService,
    PdfSectionConfig,
)
from atlas_core.services.document_generation_service import DocumentGenerationService


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

    _PRESENTATION_DOCUMENT_TYPES = {
        CommercialDocumentType.ESTIMATE,
        CommercialDocumentType.SALES_ORDER,
        CommercialDocumentType.RETURN_ORDER,
        CommercialDocumentType.CREDIT_MEMO,
        CommercialDocumentType.CUSTOMER_INVOICE,
    }
    _CUSTOMER_INVOICE_SOURCE_TYPES = {
        "standalone",
        "sales_order",
        "project",
        "project_milestone",
        "change_order",
    }
    _CUSTOMER_INVOICE_BILLING_STRATEGIES = {
        "full",
        "partial",
        "milestone",
        "progress",
        "line",
        "final",
    }
    _DEFAULT_VISIBLE_COLUMNS = [
        "description",
        "quantity",
        "unit_price",
        "extended_price",
    ]
    _SORTABLE_COLUMNS = {
        "sku_or_part_number",
        "manufacturer",
        "description",
        "item_type",
        "quantity",
        "unit_price",
        "extended_price",
    }

    def __init__(
        self,
        *,
        serialized_documents: list[dict[str, Any]] | None = None,
        serialized_numbering_policies: list[dict[str, Any]] | None = None,
        serialized_terms_blocks: list[dict[str, Any]] | None = None,
        serialized_document_templates: list[dict[str, Any]] | None = None,
        serialized_project_commercial_state: dict[str, Any] | None = None,
        active_tenant_id: str | None = None,
        active_organization_id: str | None = None,
        enforce_active_scope: bool = True,
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
        self._document_generation_service = DocumentGenerationService(
            serialized_templates=serialized_document_templates
        )
        self._project_commercial_state: dict[str, dict[str, Any]] = {
            str(project_id): dict(payload)
            for project_id, payload in dict(
                serialized_project_commercial_state or {}
            ).items()
            if str(project_id).strip() and isinstance(payload, dict)
        }
        self._enforce_active_scope = bool(enforce_active_scope)
        self._active_tenant_id = _safe_text(active_tenant_id, "") or None
        self._active_organization_id = _safe_text(active_organization_id, "") or None
        if self._enforce_active_scope and (
            not self._active_tenant_id or not self._active_organization_id
        ):
            raise ValueError(
                "active_tenant_id and active_organization_id are required when scope enforcement is enabled"
            )

    def _is_in_active_scope(self, document: CommercialDocument) -> bool:
        if self._active_tenant_id and document.tenant_id != self._active_tenant_id:
            return False
        if (
            self._active_organization_id
            and document.organization_id != self._active_organization_id
        ):
            return False
        return True

    def _assert_scope_allowed(self, *, tenant_id: str, organization_id: str) -> None:
        if self._enforce_active_scope and (
            not self._active_tenant_id or not self._active_organization_id
        ):
            raise ValueError("transactions workspace scope is not configured")
        if self._active_tenant_id and tenant_id != self._active_tenant_id:
            raise ValueError("tenant scope mismatch for transactions workspace")
        if (
            self._active_organization_id
            and organization_id != self._active_organization_id
        ):
            raise ValueError("organization scope mismatch for transactions workspace")

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
        tenant_id: str | None = None,
        organization_id: str | None = None,
    ) -> list[CommercialDocument]:
        normalized_query = query.strip().lower()
        rows: list[CommercialDocument] = []
        scoped_tenant_id = _safe_text(tenant_id, "") or None
        scoped_organization_id = _safe_text(organization_id, "") or None
        for document in self._documents:
            if not self._is_in_active_scope(document):
                continue
            if scoped_tenant_id and document.tenant_id != scoped_tenant_id:
                continue
            if (
                scoped_organization_id
                and document.organization_id != scoped_organization_id
            ):
                continue
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
                        _safe_text(
                            (document.document_metadata or {}).get(
                                "change_order_number"
                            ),
                            "",
                        ),
                        _safe_text(
                            (document.document_metadata or {}).get("change_reason"),
                            "",
                        ),
                        _safe_text(
                            (document.document_metadata or {}).get(
                                "base_bid_reference"
                            ),
                            "",
                        ),
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
        self._assert_scope_allowed(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
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
            CommercialDocumentType.CUSTOMER_INVOICE,
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
            if source_sales_order.tenant_id != tenant_id:
                raise ValueError("cross-tenant source sales order is not allowed")
            if source_sales_order.organization_id != organization_id:
                raise ValueError("cross-organization source sales order is not allowed")
            self._commercial_service.add_relationship(
                document,
                relationship_type="source_sales_order",
                related_document_id=source_sales_order.document_id,
            )
        if source_invoice is not None:
            if source_invoice.tenant_id != tenant_id:
                raise ValueError("cross-tenant source invoice is not allowed")
            if source_invoice.organization_id != organization_id:
                raise ValueError("cross-organization source invoice is not allowed")
            self._commercial_service.add_relationship(
                document,
                relationship_type="source_invoice",
                related_document_id=source_invoice.document_id,
            )
        return document

    def preview_next_change_order_number(
        self,
        *,
        tenant_id: str,
        project_id: str,
    ) -> dict[str, Any]:
        normalized_project_id = _safe_text(project_id, "")
        if not normalized_project_id:
            raise ValueError("project_id is required for change-order preview")
        next_sequence = self._next_change_order_sequence(
            tenant_id=tenant_id,
            project_id=normalized_project_id,
        )
        return {
            "project_id": normalized_project_id,
            "change_order_sequence": next_sequence,
            "change_order_number": self._format_change_order_number(next_sequence),
        }

    def configure_change_order_tracking(
        self,
        *,
        document_id: str,
        is_change_order: bool,
        base_bid_reference: str | None = None,
        change_reason: str | None = None,
        requested_by: str | None = None,
        approved_by: str | None = None,
        approval_date: str | None = None,
        effective_date: str | None = None,
        source_document: str | None = None,
        related_documents: list[str] | None = None,
        change_order_sequence: int | None = None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.document_type not in {
            CommercialDocumentType.SALES_ORDER,
            CommercialDocumentType.RETURN_ORDER,
        }:
            raise ValueError(
                "change-order tracking is only supported on sales and return orders"
            )
        if not document.is_mutable:
            raise ValueError("only mutable drafts/review documents can be edited")

        if not is_change_order:
            self._commercial_service.set_document_metadata(
                document,
                metadata={
                    "is_change_order": False,
                    "change_order_number": None,
                    "change_order_sequence": None,
                    "change_order_direction": None,
                    "base_bid_reference": None,
                    "change_reason": None,
                    "requested_by": None,
                    "approved_by": None,
                    "approval_date": None,
                    "effective_date": None,
                    "source_document": None,
                    "related_documents": [],
                },
            )
            return document

        normalized_project_id = _safe_text(document.project_id, "")
        if not normalized_project_id:
            raise ValueError("project_id is required when marking a change order")
        direction = self._change_order_direction(document.document_type)

        if change_order_sequence is None:
            existing_sequence = (document.document_metadata or {}).get(
                "change_order_sequence"
            )
            if existing_sequence is not None:
                sequence = int(existing_sequence)
            else:
                sequence = self._next_change_order_sequence(
                    tenant_id=document.tenant_id,
                    project_id=normalized_project_id,
                )
        else:
            sequence = int(change_order_sequence)
            if sequence <= 0:
                raise ValueError("change_order_sequence must be greater than zero")

        self._assert_change_order_sequence_available(
            tenant_id=document.tenant_id,
            project_id=normalized_project_id,
            sequence=sequence,
            excluding_document_id=document.document_id,
        )
        number = self._format_change_order_number(sequence)
        related = [_safe_text(item, "") for item in list(related_documents or [])]
        related = [item for item in related if item]

        self._commercial_service.set_document_metadata(
            document,
            metadata={
                "is_change_order": True,
                "change_order_number": number,
                "change_order_sequence": sequence,
                "change_order_direction": direction,
                "base_bid_reference": _safe_text(base_bid_reference, "") or None,
                "project_id": normalized_project_id,
                "project_code": _safe_text(document.project_code, "") or None,
                "change_reason": _safe_text(change_reason, "") or None,
                "requested_by": _safe_text(requested_by, "") or None,
                "approved_by": _safe_text(approved_by, "") or None,
                "approval_date": _safe_text(approval_date, "") or None,
                "effective_date": _safe_text(effective_date, "") or None,
                "source_document": _safe_text(source_document, "")
                or _safe_text(document.source_document_id, "")
                or None,
                "related_documents": related,
            },
        )
        source_document_id = _safe_text(source_document, "")
        if source_document_id:
            self._commercial_service.add_relationship(
                document,
                relationship_type="change_order_source_document",
                related_document_id=source_document_id,
            )
        for related_document_id in related:
            self._commercial_service.add_relationship(
                document,
                relationship_type="change_order_related_document",
                related_document_id=related_document_id,
            )
        self._commercial_service.add_diagnostic(
            document,
            CommercialDocumentDiagnostic(
                code="change_order_configured",
                message="Document configured for project-scoped change-order tracking",
                details={
                    "change_order_number": number,
                    "change_order_sequence": sequence,
                    "change_order_direction": direction,
                    "project_id": normalized_project_id,
                },
            ),
        )
        return document

    def set_project_base_bid(
        self,
        *,
        tenant_id: str,
        project_id: str,
        project_code: str | None,
        reference_type: str,
        reference_document_id: str | None = None,
        imported_contract_amount: Decimal | None = None,
        actor: str,
    ) -> dict[str, Any]:
        normalized_project_id = _safe_text(project_id, "")
        normalized_reference_type = _safe_text(reference_type, "").lower()
        if not normalized_project_id:
            raise ValueError("project_id is required")
        if self._active_tenant_id and tenant_id != self._active_tenant_id:
            raise ValueError("tenant scope mismatch for transactions workspace")
        if normalized_reference_type not in {
            "accepted_estimate",
            "originating_sales_order",
            "imported_contract_amount",
        }:
            raise ValueError("unsupported base bid reference_type")

        base_bid_value = Decimal("0")
        if normalized_reference_type in {
            "accepted_estimate",
            "originating_sales_order",
        }:
            source_id = _safe_text(reference_document_id, "")
            if not source_id:
                raise ValueError(
                    "reference_document_id is required for document-linked base bid"
                )
            source_document = self._required_document(source_id)
            if source_document.tenant_id != tenant_id:
                raise ValueError("cross-tenant base bid assignment is not allowed")
            if self._active_organization_id:
                if source_document.organization_id != self._active_organization_id:
                    raise ValueError(
                        "cross-organization base bid assignment is not allowed"
                    )
            expected_type = (
                CommercialDocumentType.ESTIMATE
                if normalized_reference_type == "accepted_estimate"
                else CommercialDocumentType.SALES_ORDER
            )
            if source_document.document_type != expected_type:
                raise ValueError(
                    "base bid source document type does not match reference_type"
                )
            if (
                source_document.document_type == CommercialDocumentType.ESTIMATE
                and source_document.approval_state != ApprovalState.APPROVED
                and source_document.lifecycle_state
                not in {
                    CommercialDocumentLifecycleState.APPROVED,
                    CommercialDocumentLifecycleState.ISSUED,
                }
            ):
                raise ValueError(
                    "accepted estimate base bid requires approved/issued estimate"
                )
            base_bid_value = source_document.totals.grand_total
        else:
            if imported_contract_amount is None:
                raise ValueError(
                    "imported_contract_amount is required for imported base bid"
                )
            base_bid_value = Decimal(str(imported_contract_amount))
            if base_bid_value < Decimal("0"):
                raise ValueError("imported_contract_amount cannot be negative")

        self._project_commercial_state[normalized_project_id] = {
            "tenant_id": _safe_text(tenant_id, ""),
            "project_id": normalized_project_id,
            "project_code": _safe_text(project_code, "") or None,
            "reference_type": normalized_reference_type,
            "reference_document_id": _safe_text(reference_document_id, "") or None,
            "base_bid_value": str(base_bid_value),
            "assigned_by": _safe_text(actor, "") or "atlas-ui",
            "assigned_at": _utc_now(),
        }
        return dict(self._project_commercial_state[normalized_project_id])

    def project_commercial_summary(
        self,
        *,
        tenant_id: str,
        project_id: str,
    ) -> dict[str, Any]:
        normalized_project_id = _safe_text(project_id, "")
        if not normalized_project_id:
            raise ValueError("project_id is required")
        project_documents = [
            document
            for document in self._documents
            if document.tenant_id == tenant_id
            and _safe_text(document.project_id, "") == normalized_project_id
            and document.document_type
            in {
                CommercialDocumentType.SALES_ORDER,
                CommercialDocumentType.RETURN_ORDER,
            }
        ]
        change_orders = [
            document
            for document in project_documents
            if bool((document.document_metadata or {}).get("is_change_order", False))
        ]
        change_orders.sort(
            key=lambda document: (
                int(
                    (document.document_metadata or {}).get("change_order_sequence") or 0
                ),
                document.updated_at,
            )
        )

        additive_total = Decimal("0")
        deductive_total = Decimal("0")
        ordered_change_list: list[dict[str, Any]] = []
        for document in change_orders:
            metadata = dict(document.document_metadata or {})
            direction = _safe_text(metadata.get("change_order_direction"), "")
            amount = Decimal(str(document.totals.grand_total or Decimal("0")))
            if direction == "additive":
                additive_total += amount
            elif direction == "deductive":
                deductive_total += amount
            ordered_change_list.append(
                {
                    "document_id": document.document_id,
                    "document_type": document.document_type.value,
                    "change_order_number": _safe_text(
                        metadata.get("change_order_number"), ""
                    ),
                    "change_order_sequence": int(
                        metadata.get("change_order_sequence") or 0
                    ),
                    "change_order_direction": direction,
                    "amount": str(amount),
                    "approval_state": document.approval_state.value,
                    "lifecycle_state": document.lifecycle_state.value,
                    "related_sales_order_or_return_order": document.document_number
                    or document.document_id,
                    "invoice_status": _safe_text(
                        metadata.get("quickbooks_payment_status")
                        or metadata.get("payment_status"),
                        "",
                    ),
                }
            )

        base_bid_payload = dict(
            self._project_commercial_state.get(normalized_project_id) or {}
        )
        if (
            base_bid_payload
            and _safe_text(base_bid_payload.get("tenant_id"), "") != tenant_id
        ):
            base_bid_payload = {}
        base_bid_value = Decimal(str(base_bid_payload.get("base_bid_value") or "0"))
        net_change_total = additive_total - deductive_total
        revised_contract_value = base_bid_value + net_change_total

        status = "none"
        if ordered_change_list:
            if any(
                item["approval_state"] == ApprovalState.PENDING.value
                for item in ordered_change_list
            ):
                status = "pending_approval"
            elif all(
                item["approval_state"] == ApprovalState.APPROVED.value
                for item in ordered_change_list
            ):
                status = "approved"
            else:
                status = "mixed"

        return {
            "project_id": normalized_project_id,
            "project_code": _safe_text(
                base_bid_payload.get("project_code"),
                _safe_text(
                    next(
                        (
                            document.project_code
                            for document in project_documents
                            if _safe_text(document.project_code, "")
                        ),
                        "",
                    ),
                    "",
                ),
            )
            or None,
            "base_bid_reference": base_bid_payload,
            "base_bid_value": str(base_bid_value),
            "additive_change_total": str(additive_total),
            "deductive_change_total": str(deductive_total),
            "net_change_total": str(net_change_total),
            "revised_contract_value": str(revised_contract_value),
            "ordered_change_list": ordered_change_list,
            "change_order_status": status,
        }

    def project_commercial_state_payload(self) -> dict[str, dict[str, Any]]:
        return {
            project_id: dict(payload)
            for project_id, payload in self._project_commercial_state.items()
        }

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
                line_metadata=deepcopy(line.line_metadata),
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
        if document.document_type == CommercialDocumentType.CUSTOMER_INVOICE:
            document.sync_metadata.status = SyncStatus.READY
            document.sync_metadata.external_object_type = "invoice"
            self._commercial_service.set_document_metadata(
                document,
                metadata={
                    "payment_status": _safe_text(
                        (document.document_metadata or {}).get("payment_status"),
                        "unpaid",
                    ),
                    "payment_status_updated_at": _utc_now(),
                    "issued_at": _utc_now(),
                },
                force=True,
            )
        return document

    def create_customer_invoice_draft(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        customer_id: str | None,
        project_id: str | None = None,
        project_code: str | None = None,
        source_type: str = "standalone",
        source_document_id: str | None = None,
        source_reference: str | None = None,
        billing_strategy: str = "full",
        requested_amount: Decimal | None = None,
        available_to_bill: Decimal | None = None,
        allow_overbilling: bool = False,
        override_reason: str | None = None,
        override_actor: str | None = None,
        billing_context: dict[str, Any] | None = None,
    ) -> CommercialDocument:
        normalized_source_type = _safe_text(source_type, "standalone").lower()
        if normalized_source_type not in self._CUSTOMER_INVOICE_SOURCE_TYPES:
            raise ValueError("unsupported customer invoice source_type")

        normalized_billing_strategy = _safe_text(billing_strategy, "full").lower()
        if normalized_billing_strategy not in self._CUSTOMER_INVOICE_BILLING_STRATEGIES:
            raise ValueError("unsupported customer invoice billing_strategy")

        source_document: CommercialDocument | None = None
        if normalized_source_type in {"sales_order", "change_order"}:
            if not _safe_text(source_document_id, ""):
                raise ValueError(
                    "source_document_id is required for source-linked invoices"
                )
            source_document = self._required_document(
                _safe_text(source_document_id, "")
            )
            expected_type = (
                CommercialDocumentType.SALES_ORDER
                if normalized_source_type == "sales_order"
                else CommercialDocumentType.CHANGE_ORDER
            )
            if source_document.document_type != expected_type:
                raise ValueError("source document type does not match source_type")

        derived_customer_id = (
            _safe_text(
                customer_id,
                _safe_text(source_document.customer_id, "") if source_document else "",
            )
            or None
        )
        derived_project_id = (
            _safe_text(
                project_id,
                _safe_text(source_document.project_id, "") if source_document else "",
            )
            or None
        )
        derived_project_code = (
            _safe_text(
                project_code,
                _safe_text(source_document.project_code, "") if source_document else "",
            )
            or None
        )

        if not derived_customer_id:
            raise ValueError("customer invoices require customer_id")

        invoice = self.create_draft(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=CommercialDocumentType.CUSTOMER_INVOICE,
            project_id=derived_project_id,
            project_code=derived_project_code,
            customer_id=derived_customer_id,
        )

        if source_document is not None:
            invoice.source_document_id = source_document.document_id
            invoice.source_relationship_type = "derived_from_source"
            self._commercial_service.add_relationship(
                invoice,
                relationship_type=f"source_{normalized_source_type}",
                related_document_id=source_document.document_id,
            )

        self._commercial_service.set_document_metadata(
            invoice,
            metadata={
                "source_type": normalized_source_type,
                "source_document_id": _safe_text(source_document_id, "") or None,
                "source_reference": _safe_text(source_reference, "") or None,
                "billing_strategy": normalized_billing_strategy,
                "billing_context": dict(billing_context or {}),
                "payment_status": "unpaid",
                "payment_status_updated_at": _utc_now(),
            },
        )

        if requested_amount is not None and available_to_bill is not None:
            self.set_customer_invoice_billing(
                document_id=invoice.document_id,
                billing_strategy=normalized_billing_strategy,
                requested_amount=requested_amount,
                available_to_bill=available_to_bill,
                allow_overbilling=allow_overbilling,
                override_reason=override_reason,
                override_actor=override_actor,
                billing_context=billing_context,
            )
        return invoice

    def set_customer_invoice_billing(
        self,
        *,
        document_id: str,
        billing_strategy: str,
        requested_amount: Decimal,
        available_to_bill: Decimal,
        allow_overbilling: bool = False,
        override_reason: str | None = None,
        override_actor: str | None = None,
        billing_context: dict[str, Any] | None = None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.document_type != CommercialDocumentType.CUSTOMER_INVOICE:
            raise ValueError("document must be a customer invoice")
        if not document.is_mutable:
            raise ValueError("only mutable drafts/review documents can be edited")

        normalized_strategy = _safe_text(billing_strategy, "").lower()
        if normalized_strategy not in self._CUSTOMER_INVOICE_BILLING_STRATEGIES:
            raise ValueError("unsupported customer invoice billing_strategy")

        requested = Decimal(str(requested_amount))
        available = Decimal(str(available_to_bill))
        if requested <= Decimal("0"):
            raise ValueError("requested_amount must be greater than zero")
        if available <= Decimal("0"):
            raise ValueError("available_to_bill must be greater than zero")

        override_applied = False
        if requested > available:
            if not allow_overbilling:
                raise ValueError("requested_amount exceeds available_to_bill")
            if not _safe_text(override_reason, "") or not _safe_text(
                override_actor, ""
            ):
                raise ValueError(
                    "override_reason and override_actor are required when overbilling"
                )
            override_applied = True
            self._commercial_service.add_diagnostic(
                document,
                CommercialDocumentDiagnostic(
                    code="customer_invoice_overbilling_override",
                    message="Requested amount exceeds available-to-bill via explicit override",
                    details={
                        "requested_amount": str(requested),
                        "available_to_bill": str(available),
                        "override_reason": _safe_text(override_reason, ""),
                        "override_actor": _safe_text(override_actor, ""),
                    },
                ),
            )

        self._commercial_service.set_totals(
            document,
            subtotal=requested,
            discount_total=Decimal("0"),
            tax_total=document.totals.tax_total,
            grand_total=requested + document.totals.tax_total,
        )
        self._commercial_service.set_document_metadata(
            document,
            metadata={
                "billing_strategy": normalized_strategy,
                "billable_available": str(available),
                "requested_amount": str(requested),
                "approved_amount": str(requested),
                "allow_overbilling": bool(allow_overbilling),
                "overbilling_override_applied": override_applied,
                "overbilling_override_reason": _safe_text(override_reason, "") or None,
                "overbilling_override_actor": _safe_text(override_actor, "") or None,
                "billing_context": dict(billing_context or {}),
            },
        )
        return document

    def set_customer_invoice_payment_state(
        self,
        *,
        document_id: str,
        payment_state: str,
        reason: str,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.document_type != CommercialDocumentType.CUSTOMER_INVOICE:
            raise ValueError("document must be a customer invoice")
        target_by_payment_state = {
            "partially_paid": CommercialDocumentLifecycleState.PARTIALLY_PAID,
            "paid": CommercialDocumentLifecycleState.PAID,
            "overdue": CommercialDocumentLifecycleState.OVERDUE,
            "voided": CommercialDocumentLifecycleState.VOIDED,
            "closed": CommercialDocumentLifecycleState.CLOSED,
        }
        normalized_payment_state = _safe_text(payment_state, "").lower()
        target_state = target_by_payment_state.get(normalized_payment_state)
        if target_state is None:
            raise ValueError("unsupported customer invoice payment_state")
        self._commercial_service.transition_lifecycle(
            document,
            target_state,
            reason=reason,
        )
        self._commercial_service.set_document_metadata(
            document,
            metadata={
                "payment_status": normalized_payment_state,
                "payment_status_updated_at": _utc_now(),
            },
            force=True,
        )
        return document

    def record_customer_invoice_sync_event(
        self,
        *,
        document_id: str,
        sync_status: SyncStatus,
        external_id: str | None = None,
        external_revision: str | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
        reconciliation_state: str | None = None,
        payment_status: str | None = None,
        payment_status_timestamp: str | None = None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        if document.document_type != CommercialDocumentType.CUSTOMER_INVOICE:
            raise ValueError("document must be a customer invoice")
        if not isinstance(sync_status, SyncStatus):
            sync_status = SyncStatus(sync_status)

        metadata = document.sync_metadata
        metadata.external_object_type = "invoice"
        metadata.status = sync_status
        metadata.external_id = _safe_text(external_id, "") or metadata.external_id
        metadata.external_revision = (
            _safe_text(external_revision, "") or metadata.external_revision
        )
        metadata.last_attempt_at = _utc_now()
        metadata.failure_code = _safe_text(failure_code, "") or None
        metadata.failure_message = _safe_text(failure_message, "") or None
        metadata.reconciliation_state = (
            _safe_text(reconciliation_state, "") or metadata.reconciliation_state
        )
        if sync_status == SyncStatus.SYNCED:
            metadata.last_success_at = _utc_now()
            metadata.failure_code = None
            metadata.failure_message = None
        if sync_status == SyncStatus.FAILED:
            metadata.retry_count = int(metadata.retry_count or 0) + 1

        if _safe_text(payment_status, ""):
            self._commercial_service.set_document_metadata(
                document,
                metadata={
                    "quickbooks_payment_status": _safe_text(payment_status, ""),
                    "quickbooks_payment_status_timestamp": _safe_text(
                        payment_status_timestamp,
                        _utc_now(),
                    ),
                },
                force=True,
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
            CommercialDocumentType.RETURN_ORDER,
            CommercialDocumentType.CREDIT_MEMO,
            CommercialDocumentType.CUSTOMER_INVOICE,
        }:
            raise ValueError(
                "only estimates, sales orders, return orders, credit memos, and customer invoices are supported"
            )

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
                source_document_id=line.source_document_id,
                source_line_id=line.source_line_id,
                related_document_id=line.related_document_id,
                related_line_id=line.related_line_id,
                line_metadata=deepcopy(line.line_metadata),
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
        duplicate.attachments = deepcopy(list(source.attachments or []))
        duplicate.document_metadata = deepcopy(dict(source.document_metadata or {}))
        if bool((duplicate.document_metadata or {}).get("is_change_order", False)):
            duplicate.document_metadata.update(
                {
                    "is_change_order": False,
                    "change_order_number": None,
                    "change_order_sequence": None,
                }
            )
        duplicate.source_sales_order_id = source.source_sales_order_id
        duplicate.source_invoice_id = source.source_invoice_id

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

    def line_presentation_snapshot(self, *, document_id: str) -> dict[str, Any]:
        document = self._required_document(document_id)
        self._assert_presentation_supported(document)
        groups = self._presentation_groups(document)
        subtotals = self._group_subtotals(document)
        return {
            "groups": groups,
            "rows": [
                self._line_presentation_row(line, groups, subtotals)
                for line in self._ordered_lines(document)
            ],
            "visible_columns": self._visible_columns(document),
            "active_sort": self._active_sort(document),
        }

    def create_named_group(
        self,
        *,
        document_id: str,
        name: str,
        show_subtotal: bool = True,
    ) -> dict[str, Any]:
        document = self._required_document(document_id)
        self._assert_presentation_supported(document)
        self._commercial_service._assert_mutable(document)
        groups = self._presentation_groups(document)
        group_id = f"group-{len(groups) + 1}"
        next_sequence = len(document.lines) + 1
        header = self._commercial_service.add_line(
            document,
            description=name,
            quantity=Decimal("0"),
            unit_price=Decimal("0"),
            sequence=next_sequence,
            line_metadata={
                "presentation": {
                    "line_type": "group_header",
                    "group_id": group_id,
                    "display_sequence": next_sequence,
                    "manual_display_sequence": next_sequence,
                }
            },
        )
        subtotal = self._commercial_service.add_line(
            document,
            description=f"{name} subtotal",
            quantity=Decimal("0"),
            unit_price=Decimal("0"),
            sequence=next_sequence + 1,
            line_metadata={
                "presentation": {
                    "line_type": "subtotal",
                    "group_id": group_id,
                    "display_sequence": next_sequence + 1,
                    "manual_display_sequence": next_sequence + 1,
                }
            },
        )
        groups.append(
            {
                "group_id": group_id,
                "name": name.strip(),
                "collapsed": False,
                "show_subtotal": bool(show_subtotal),
                "header_line_id": header.line_id,
                "subtotal_line_id": subtotal.line_id,
            }
        )
        self._save_presentation_groups(document, groups)
        self._capture_manual_order(document)
        return dict(groups[-1])

    def add_presentation_line(
        self,
        *,
        document_id: str,
        line_type: str,
        text: str = "",
        group_id: str | None = None,
        parent_line_id: str | None = None,
        comment_reference_line_id: str | None = None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        self._assert_presentation_supported(document)
        self._commercial_service._assert_mutable(document)
        normalized_line_type = line_type.strip().lower()
        if normalized_line_type not in {"comment", "blank_spacer"}:
            raise ValueError("unsupported presentation line type")
        next_sequence = len(document.lines) + 1
        description = text if normalized_line_type != "blank_spacer" else "Spacer"
        self._commercial_service.add_line(
            document,
            description=description or normalized_line_type,
            quantity=Decimal("0"),
            unit_price=Decimal("0"),
            sequence=next_sequence,
            line_metadata={
                "presentation": {
                    "line_type": normalized_line_type,
                    "group_id": group_id,
                    "parent_line_id": parent_line_id,
                    "comment_reference_line_id": comment_reference_line_id,
                    "display_sequence": next_sequence,
                    "manual_display_sequence": next_sequence,
                }
            },
        )
        self._capture_manual_order(document)
        return document

    def assign_line_to_group(
        self,
        *,
        document_id: str,
        line_id: str,
        group_id: str | None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        self._assert_presentation_supported(document)
        self._commercial_service._assert_mutable(document)
        line = self._required_line(document, line_id)
        presentation = dict(line.presentation_metadata)
        presentation["group_id"] = group_id
        self._commercial_service.set_line_metadata(
            document,
            line_id=line_id,
            metadata={"presentation": presentation},
        )
        self._capture_manual_order(document)
        return document

    def reorder_lines(
        self,
        *,
        document_id: str,
        ordered_line_ids: list[str],
        capture_manual_order: bool = True,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        self._assert_presentation_supported(document)
        self._commercial_service._assert_mutable(document)
        normalized_ids = [
            line_id.strip() for line_id in ordered_line_ids if line_id.strip()
        ]
        expected_ids = {line.line_id for line in document.lines}
        if set(normalized_ids) != expected_ids:
            raise ValueError("ordered_line_ids must include every document line")
        for index, line_id in enumerate(normalized_ids, start=1):
            line = self._required_line(document, line_id)
            presentation = dict(line.presentation_metadata)
            presentation["display_sequence"] = index
            presentation["manual_display_sequence"] = index
            self._commercial_service.set_line_metadata(
                document,
                line_id=line_id,
                metadata={"presentation": presentation},
            )
        if capture_manual_order:
            self._capture_manual_order(document)
        self._save_active_sort(document, None)
        return document

    def sort_lines(
        self,
        *,
        document_id: str,
        column: str,
        direction: str,
        apply: bool = False,
    ) -> list[dict[str, Any]]:
        document = self._required_document(document_id)
        self._assert_presentation_supported(document)
        normalized_column = column.strip().lower()
        normalized_direction = direction.strip().lower()
        if normalized_column not in self._SORTABLE_COLUMNS:
            raise ValueError("unsupported sort column")
        if normalized_direction not in {"asc", "desc"}:
            raise ValueError("unsupported sort direction")
        sorted_lines = self._sorted_presentation_lines(
            document,
            column=normalized_column,
            direction=normalized_direction,
        )
        if apply:
            if not self._manual_order(document):
                self._capture_manual_order(document)
            self.reorder_lines(
                document_id=document_id,
                ordered_line_ids=[line.line_id for line in sorted_lines],
                capture_manual_order=False,
            )
            self._save_active_sort(
                document,
                {"column": normalized_column, "direction": normalized_direction},
            )
        groups = self._presentation_groups(document)
        subtotals = self._group_subtotals(document)
        return [
            self._line_presentation_row(line, groups, subtotals)
            for line in sorted_lines
        ]

    def restore_manual_line_order(self, *, document_id: str) -> CommercialDocument:
        document = self._required_document(document_id)
        self._assert_presentation_supported(document)
        manual_order = self._manual_order(document)
        if not manual_order:
            manual_order = [line.line_id for line in self._ordered_lines(document)]
        self.reorder_lines(document_id=document_id, ordered_line_ids=manual_order)
        self._save_active_sort(document, None)
        return document

    def set_group_options(
        self,
        *,
        document_id: str,
        group_id: str,
        show_subtotal: bool | None = None,
        collapsed: bool | None = None,
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        self._assert_presentation_supported(document)
        self._commercial_service._assert_mutable(document)
        groups = self._presentation_groups(document)
        found = False
        for group in groups:
            if _safe_text(group.get("group_id"), "") != group_id:
                continue
            if show_subtotal is not None:
                group["show_subtotal"] = bool(show_subtotal)
            if collapsed is not None:
                group["collapsed"] = bool(collapsed)
            found = True
        if not found:
            raise ValueError("group was not found")
        self._save_presentation_groups(document, groups)
        return document

    def set_visible_columns(
        self,
        *,
        document_id: str,
        visible_columns: list[str],
    ) -> CommercialDocument:
        document = self._required_document(document_id)
        self._assert_presentation_supported(document)
        metadata, presentation = self._presentation_document_metadata(document)
        presentation["visible_columns"] = [
            _safe_text(item, "") for item in visible_columns if _safe_text(item, "")
        ] or list(self._DEFAULT_VISIBLE_COLUMNS)
        metadata["presentation"] = presentation
        self._commercial_service.set_document_metadata(document, metadata=metadata)
        return document

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
        if section_config is not None:
            return self._export_document_pdf_legacy(
                document_id=document_id,
                presentation=presentation,
                actor=actor,
                revision_number=revision_number,
                section_config=section_config,
                branding=branding,
            )

        generated = self.generate_document_artifact(
            document_id=document_id,
            presentation=presentation,
            actor=actor,
            revision_number=revision_number,
            output_format="pdf",
            branding=branding,
        )
        return {
            "file_name": generated["file_name"],
            "mime_type": generated["mime_type"],
            "payload": generated["payload"],
            "revision_number": generated["revision_number"],
            "content_hash": generated["content_hash"],
        }

    def generate_document_artifact(
        self,
        *,
        document_id: str,
        presentation: str,
        actor: str,
        revision_number: int | None = None,
        output_format: str = "pdf",
        explicit_template_id: str | None = None,
        branding: dict[str, Any] | None = None,
        permission_allowed: bool = True,
    ) -> dict[str, Any]:
        if not permission_allowed:
            raise ValueError("document generation permission was denied")

        document = self._required_document(document_id)
        normalized_presentation = presentation.strip().lower()
        if normalized_presentation not in {
            "internal_estimate",
            "customer_estimate",
            "sales_order",
            "customer_invoice",
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

        format_value = output_format.strip().lower()
        if format_value not in {"pdf", "html"}:
            raise ValueError("unsupported output_format")

        result = self._document_generation_service.render_document(
            request=RenderRequest(
                tenant_id=document.tenant_id,
                organization_id=document.organization_id,
                actor_id=actor,
                document_id=document.document_id,
                revision_number=revision.revision_number,
                document_family=document.document_type.value,
                output_format=OutputFormat(format_value),
                presentation=normalized_presentation,
                explicit_template_id=explicit_template_id,
            ),
            document=document,
            revision=revision,
            branding=branding,
        )

        if document.is_mutable and not revision.immutable:
            self._commercial_service.assign_template_version(
                document,
                assignment=result.assignment.to_dict(),
                snapshot=result.template_version_snapshot,
            )

        export_event = {
            "event": "document_generated",
            "actor": actor,
            "timestamp": _utc_now(),
            "presentation": normalized_presentation,
            "output_format": result.artifact.output_format.value,
            "revision_number": revision.revision_number,
            "revision_id": revision.revision_id,
            "file_name": result.artifact.file_name,
            "content_hash": result.artifact.content_hash,
            "status": document.lifecycle_state.value,
            "is_archived_revision": revision.is_archived,
            "template_assignment": result.assignment.to_dict(),
            "template_version_snapshot": deepcopy(result.template_version_snapshot),
        }
        document.export_activity.append(export_event)
        document.attachments.append(
            {
                "attachment_id": result.artifact.artifact_id,
                "file_name": result.artifact.file_name,
                "mime_type": result.artifact.mime_type,
                "content_hash": result.artifact.content_hash,
                "revision_number": revision.revision_number,
                "presentation": normalized_presentation,
                "output_format": result.artifact.output_format.value,
                "generated_at": export_event["timestamp"],
                "generated_by": actor,
                "template_assignment": result.assignment.to_dict(),
            }
        )
        return {
            "file_name": result.artifact.file_name,
            "mime_type": result.artifact.mime_type,
            "payload": result.artifact.payload,
            "revision_number": revision.revision_number,
            "content_hash": result.artifact.content_hash,
            "assignment": result.assignment.to_dict(),
            "template_version_snapshot": deepcopy(result.template_version_snapshot),
        }

    def _export_document_pdf_legacy(
        self,
        *,
        document_id: str,
        presentation: str,
        actor: str,
        revision_number: int | None = None,
        section_config: PdfSectionConfig,
        branding: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        document = self._required_document(document_id)
        normalized_presentation = presentation.strip().lower()
        if normalized_presentation not in {
            "internal_estimate",
            "customer_estimate",
            "sales_order",
            "customer_invoice",
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

    def get_document(
        self,
        document_id: str,
        *,
        tenant_id: str | None = None,
        organization_id: str | None = None,
    ) -> CommercialDocument | None:
        normalized_id = document_id.strip()
        scoped_tenant_id = _safe_text(tenant_id, "") or None
        scoped_organization_id = _safe_text(organization_id, "") or None
        for document in self._documents:
            if not self._is_in_active_scope(document):
                continue
            if document.document_id == normalized_id:
                if scoped_tenant_id and document.tenant_id != scoped_tenant_id:
                    continue
                if (
                    scoped_organization_id
                    and document.organization_id != scoped_organization_id
                ):
                    continue
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

    def _change_order_direction(self, document_type: CommercialDocumentType) -> str:
        if document_type == CommercialDocumentType.SALES_ORDER:
            return "additive"
        if document_type == CommercialDocumentType.RETURN_ORDER:
            return "deductive"
        raise ValueError("unsupported document_type for change-order direction")

    def _format_change_order_number(self, sequence: int) -> str:
        return f"CO #{sequence}"

    def _next_change_order_sequence(
        self,
        *,
        tenant_id: str,
        project_id: str,
    ) -> int:
        highest_sequence = 0
        for document in self._documents:
            if document.tenant_id != tenant_id:
                continue
            if _safe_text(document.project_id, "") != project_id:
                continue
            metadata = dict(document.document_metadata or {})
            if not bool(metadata.get("is_change_order", False)):
                continue
            sequence = int(metadata.get("change_order_sequence") or 0)
            if sequence > highest_sequence:
                highest_sequence = sequence
        return highest_sequence + 1

    def _assert_change_order_sequence_available(
        self,
        *,
        tenant_id: str,
        project_id: str,
        sequence: int,
        excluding_document_id: str,
    ) -> None:
        for document in self._documents:
            if document.document_id == excluding_document_id:
                continue
            if document.tenant_id != tenant_id:
                continue
            if _safe_text(document.project_id, "") != project_id:
                continue
            metadata = dict(document.document_metadata or {})
            if not bool(metadata.get("is_change_order", False)):
                continue
            existing_sequence = int(metadata.get("change_order_sequence") or 0)
            if existing_sequence == sequence:
                raise ValueError(
                    "change-order sequence is already allocated for this project"
                )

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
            if line.presentation_line_type not in {"item", "service"}:
                continue
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
            if line.presentation_line_type not in {"item", "service"}:
                continue
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

    def _required_line(self, document: CommercialDocument, line_id: str) -> Any:
        line = next((item for item in document.lines if item.line_id == line_id), None)
        if line is None:
            raise ValueError("line was not found")
        return line

    def _assert_presentation_supported(self, document: CommercialDocument) -> None:
        if document.document_type not in self._PRESENTATION_DOCUMENT_TYPES:
            raise ValueError("document type does not support line presentation")

    def _presentation_document_metadata(
        self,
        document: CommercialDocument,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        metadata = dict(document.document_metadata or {})
        presentation = dict(metadata.get("presentation") or {})
        metadata["presentation"] = presentation
        return metadata, presentation

    def _presentation_groups(
        self, document: CommercialDocument
    ) -> list[dict[str, Any]]:
        _, presentation = self._presentation_document_metadata(document)
        return [
            dict(item)
            for item in list(presentation.get("groups") or [])
            if isinstance(item, dict)
        ]

    def _save_presentation_groups(
        self,
        document: CommercialDocument,
        groups: list[dict[str, Any]],
    ) -> None:
        metadata, presentation = self._presentation_document_metadata(document)
        presentation["groups"] = [dict(item) for item in groups]
        metadata["presentation"] = presentation
        self._commercial_service.set_document_metadata(document, metadata=metadata)

    def _visible_columns(self, document: CommercialDocument) -> list[str]:
        _, presentation = self._presentation_document_metadata(document)
        values = [
            _safe_text(item, "")
            for item in list(
                presentation.get("visible_columns") or self._DEFAULT_VISIBLE_COLUMNS
            )
            if _safe_text(item, "")
        ]
        return values or list(self._DEFAULT_VISIBLE_COLUMNS)

    def _manual_order(self, document: CommercialDocument) -> list[str]:
        _, presentation = self._presentation_document_metadata(document)
        return [
            _safe_text(item, "")
            for item in list(presentation.get("manual_order") or [])
            if _safe_text(item, "")
        ]

    def _capture_manual_order(self, document: CommercialDocument) -> None:
        metadata, presentation = self._presentation_document_metadata(document)
        presentation["manual_order"] = [
            line.line_id for line in self._ordered_lines(document)
        ]
        metadata["presentation"] = presentation
        self._commercial_service.set_document_metadata(document, metadata=metadata)

    def _active_sort(self, document: CommercialDocument) -> dict[str, Any] | None:
        _, presentation = self._presentation_document_metadata(document)
        value = presentation.get("active_sort")
        return dict(value) if isinstance(value, dict) else None

    def _save_active_sort(
        self,
        document: CommercialDocument,
        active_sort: dict[str, Any] | None,
    ) -> None:
        metadata, presentation = self._presentation_document_metadata(document)
        presentation["active_sort"] = dict(active_sort) if active_sort else None
        metadata["presentation"] = presentation
        self._commercial_service.set_document_metadata(document, metadata=metadata)

    def _ordered_lines(self, document: CommercialDocument) -> list[Any]:
        return sorted(
            list(document.lines or []),
            key=lambda line: (line.display_sequence, line.sequence, line.line_id),
        )

    def _group_subtotals(self, document: CommercialDocument) -> dict[str, Decimal]:
        subtotals: dict[str, Decimal] = {}
        for line in list(document.lines or []):
            group_id = _safe_text(line.presentation_metadata.get("group_id"), "")
            if not group_id or not line.contributes_to_totals:
                continue
            subtotals[group_id] = (
                subtotals.get(group_id, Decimal("0")) + line.extended_amount
            )
        return subtotals

    def _line_presentation_row(
        self,
        line: Any,
        groups: list[dict[str, Any]],
        subtotals: dict[str, Decimal],
    ) -> dict[str, Any]:
        group_id = _safe_text(line.presentation_metadata.get("group_id"), "") or None
        group = next(
            (
                item
                for item in groups
                if _safe_text(item.get("group_id"), "") == (group_id or "")
            ),
            None,
        )
        return {
            "line_id": line.line_id,
            "line_type": line.presentation_line_type,
            "description": line.description,
            "display_sequence": line.display_sequence,
            "group_id": group_id,
            "group_name": _safe_text((group or {}).get("name"), ""),
            "show_subtotal": (group or {}).get("show_subtotal"),
            "parent_line_id": line.presentation_metadata.get("parent_line_id"),
            "comment_reference_line_id": line.presentation_metadata.get(
                "comment_reference_line_id"
            ),
            "quantity": str(line.quantity),
            "unit_price": str(line.unit_price),
            "extended_price": str(line.extended_amount),
            "group_subtotal": str(subtotals.get(group_id or "", Decimal("0"))),
        }

    def _sort_value(self, line: Any, column: str) -> Any:
        metadata = dict(line.line_metadata or {})
        if column == "sku_or_part_number":
            return _safe_text(line.product_or_service_reference, "")
        if column == "manufacturer":
            return _safe_text(metadata.get("manufacturer"), "")
        if column == "description":
            return _safe_text(line.description, "")
        if column == "item_type":
            return line.presentation_line_type
        if column == "quantity":
            return line.quantity
        if column == "unit_price":
            return line.unit_price
        if column == "extended_price":
            return line.extended_amount
        return _safe_text(line.description, "")

    def _sorted_presentation_lines(
        self,
        document: CommercialDocument,
        *,
        column: str,
        direction: str,
    ) -> list[Any]:
        ordered = self._ordered_lines(document)
        reverse = direction == "desc"

        def sort_segment(lines: list[Any]) -> list[Any]:
            anchored_children: dict[str, list[Any]] = {}
            anchors: list[Any] = []
            unattached: list[Any] = []
            for line in lines:
                if line.presentation_line_type in {"item", "service"}:
                    anchors.append(line)
                    continue
                parent_id = _safe_text(
                    line.presentation_metadata.get("parent_line_id")
                    or line.presentation_metadata.get("comment_reference_line_id"),
                    "",
                )
                if parent_id:
                    anchored_children.setdefault(parent_id, []).append(line)
                else:
                    unattached.append(line)
            sorted_anchors = sorted(
                anchors,
                key=lambda line: (
                    self._sort_value(line, column),
                    line.display_sequence,
                ),
                reverse=reverse,
            )
            output: list[Any] = []
            for anchor in sorted_anchors:
                output.append(anchor)
                output.extend(
                    sorted(
                        anchored_children.get(anchor.line_id, []),
                        key=lambda item: item.display_sequence,
                    )
                )
            output.extend(sorted(unattached, key=lambda item: item.display_sequence))
            return output

        result: list[Any] = []
        groups = self._presentation_groups(document)
        grouped_ids = [
            _safe_text(group.get("group_id"), "")
            for group in groups
            if _safe_text(group.get("group_id"), "")
        ]
        top_level = [
            line
            for line in ordered
            if not _safe_text(line.presentation_metadata.get("group_id"), "")
        ]
        result.extend(sort_segment(top_level))
        for group_id in grouped_ids:
            group_lines = [
                line
                for line in ordered
                if _safe_text(line.presentation_metadata.get("group_id"), "")
                == group_id
            ]
            headers = [
                line
                for line in group_lines
                if line.presentation_line_type == "group_header"
            ]
            subtotals = [
                line
                for line in group_lines
                if line.presentation_line_type == "subtotal"
            ]
            members = [
                line
                for line in group_lines
                if line.presentation_line_type not in {"group_header", "subtotal"}
            ]
            result.extend(sorted(headers, key=lambda line: line.display_sequence))
            result.extend(sort_segment(members))
            result.extend(sorted(subtotals, key=lambda line: line.display_sequence))
        return result


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    return normalized or default

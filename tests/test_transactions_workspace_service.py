from decimal import Decimal

import pytest

from atlas_core.domain.commercial_document import (
    ApprovalState,
    CommercialDocumentLifecycleState,
    CommercialDocumentType,
    SyncStatus,
)
from atlas_core.services.transactions_workspace_service import (
    TransactionsWorkspaceService,
)


def _service() -> TransactionsWorkspaceService:
    return TransactionsWorkspaceService()


def _terms_blocks(default_content: str, *, version: int = 1) -> list[dict[str, object]]:
    return [
        {
            "block_id": f"terms-estimate-v{version}",
            "title": "Estimate Terms",
            "document_family": "estimate",
            "status": "active",
            "content": default_content,
            "version": version,
            "effective_date": None,
            "expiration_date": None,
            "is_default": True,
            "customer_id": None,
            "project_id": None,
            "transaction_id": None,
            "archived": False,
            "created_at": "2026-07-13T00:00:00+00:00",
            "created_by": "tester",
            "updated_at": "2026-07-13T00:00:00+00:00",
            "updated_by": "tester",
            "previous_block_id": None,
        },
        {
            "block_id": f"terms-sales-order-v{version}",
            "title": "Sales Order Terms",
            "document_family": "sales_order",
            "status": "active",
            "content": f"SO {default_content}",
            "version": version,
            "effective_date": None,
            "expiration_date": None,
            "is_default": True,
            "customer_id": None,
            "project_id": None,
            "transaction_id": None,
            "archived": False,
            "created_at": "2026-07-13T00:00:00+00:00",
            "created_by": "tester",
            "updated_at": "2026-07-13T00:00:00+00:00",
            "updated_by": "tester",
            "previous_block_id": None,
        },
    ]


def test_create_and_filter_documents() -> None:
    service = _service()

    estimate = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        project_code="P-A",
        customer_id="customer-a",
    )
    sales_order = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-b",
        project_code="P-B",
        customer_id="customer-b",
    )

    assert estimate.document_type == CommercialDocumentType.ESTIMATE
    assert sales_order.document_type == CommercialDocumentType.SALES_ORDER

    filtered = service.list_documents(document_type=CommercialDocumentType.ESTIMATE)
    assert len(filtered) == 1
    assert filtered[0].document_id == estimate.document_id

    searched = service.list_documents(query="project-b")
    assert len(searched) == 1
    assert searched[0].document_id == sales_order.document_id


def test_edit_archive_restore() -> None:
    service = _service()
    created = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.RFQ,
        project_id="old-project",
        project_code="OLD",
        vendor_id="vendor-1",
    )

    updated = service.update_draft_metadata(
        document_id=created.document_id,
        project_id="new-project",
        project_code="NEW",
        customer_id="customer-7",
        vendor_id="vendor-2",
    )
    assert updated.project_id == "new-project"
    assert updated.project_code == "NEW"
    assert updated.customer_id == "customer-7"
    assert updated.vendor_id == "vendor-2"

    archived = service.archive_document(created.document_id)
    assert archived.lifecycle_state == CommercialDocumentLifecycleState.ARCHIVED
    assert service.list_documents(query=created.document_id) == []
    assert (
        len(service.list_documents(query=created.document_id, include_archived=True))
        == 1
    )

    restored = service.restore_document(created.document_id)
    assert restored.lifecycle_state == CommercialDocumentLifecycleState.DRAFT
    assert restored.approval_state == ApprovalState.NOT_REQUESTED


def test_overview_metrics_and_sync_status() -> None:
    service = _service()

    po = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.PURCHASE_ORDER,
        vendor_id="vendor-a",
    )
    vendor_bill = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.VENDOR_BILL,
        vendor_id="vendor-a",
    )
    customer_invoice = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.CUSTOMER_INVOICE,
        customer_id="customer-a",
    )

    po.lifecycle_state = CommercialDocumentLifecycleState.PARTIALLY_FULFILLED
    service.set_approval_state(
        document_id=po.document_id,
        approval_state=ApprovalState.PENDING,
    )
    vendor_bill.lifecycle_state = CommercialDocumentLifecycleState.ISSUED
    service.set_sync_status(
        document_id=vendor_bill.document_id,
        sync_status=SyncStatus.READY,
    )
    service.set_sync_status(
        document_id=customer_invoice.document_id,
        sync_status=SyncStatus.FAILED,
        failure_code="sync_failure",
        failure_message="temporary outage",
    )

    metrics = service.overview_metrics()
    assert metrics.draft_documents == 1
    assert metrics.pending_approval == 1
    assert metrics.issued_documents == 1
    assert metrics.open_purchase_orders == 1
    assert metrics.partially_received_purchase_orders == 1
    assert metrics.vendor_bills_pending_sync == 1
    assert metrics.customer_invoices_pending_sync == 0
    assert metrics.sync_failures == 1


def test_estimate_standalone_requires_customer() -> None:
    service = _service()

    with pytest.raises(ValueError, match="standalone estimates require customer_id"):
        service.create_draft(
            tenant_id="tenant-1",
            organization_id="org-1",
            document_type=CommercialDocumentType.ESTIMATE,
        )


def test_issue_document_allocates_number() -> None:
    service = _service()
    estimate = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        customer_id="customer-a",
    )
    service.set_approval_state(
        document_id=estimate.document_id,
        approval_state=ApprovalState.APPROVED,
    )

    preview = service.preview_number(estimate.document_id)
    issued = service.issue_document(
        document_id=estimate.document_id,
        reason="Issue estimate for review",
    )

    assert issued.lifecycle_state == CommercialDocumentLifecycleState.ISSUED
    assert issued.document_number == preview


def test_create_draft_revision_from_issued_estimate_returns_to_review() -> None:
    service = _service()
    estimate = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        customer_id="customer-a",
    )
    service.set_approval_state(
        document_id=estimate.document_id,
        approval_state=ApprovalState.APPROVED,
    )
    issued = service.issue_document(
        document_id=estimate.document_id,
        reason="Issue estimate for review",
    )
    issued_revision = issued.revision_number

    revised = service.create_draft_revision(
        document_id=estimate.document_id,
        reason="Post-issue change",
    )

    assert revised.lifecycle_state == CommercialDocumentLifecycleState.DRAFT
    assert revised.revision_number == issued_revision + 1
    assert revised.approval_state == ApprovalState.NOT_REQUESTED


def test_explicit_draft_terms_refresh_and_issued_snapshot_immutability() -> None:
    service = TransactionsWorkspaceService(serialized_terms_blocks=_terms_blocks("v1"))
    estimate = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        customer_id="customer-a",
    )
    assert (estimate.terms_and_conditions_snapshot or {}).get("content") == "v1"

    service_v2 = TransactionsWorkspaceService(
        serialized_documents=service.to_payload(),
        serialized_terms_blocks=_terms_blocks("v2", version=2),
    )
    refreshed = service_v2.refresh_draft_terms(document_id=estimate.document_id)
    assert (refreshed.terms_and_conditions_snapshot or {}).get("content") == "v2"

    service_v2.set_approval_state(
        document_id=estimate.document_id,
        approval_state=ApprovalState.APPROVED,
    )
    issued = service_v2.issue_document(
        document_id=estimate.document_id,
        reason="issue",
    )
    assert issued.lifecycle_state == CommercialDocumentLifecycleState.ISSUED
    with pytest.raises(ValueError, match="terms can only be refreshed"):
        service_v2.refresh_draft_terms(document_id=estimate.document_id)

    service_v3 = TransactionsWorkspaceService(
        serialized_documents=service_v2.to_payload(),
        serialized_terms_blocks=_terms_blocks("v3", version=3),
    )
    preserved = service_v3.get_document(estimate.document_id)
    assert preserved is not None
    assert (preserved.terms_and_conditions_snapshot or {}).get("content") == "v2"


def test_create_sales_order_from_estimate_preserves_traceability_and_terms() -> None:
    service = TransactionsWorkspaceService(serialized_terms_blocks=_terms_blocks("v1"))
    estimate = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        project_code="P-A",
        customer_id="customer-a",
    )
    service._commercial_service.add_line(
        estimate,
        description="Line 1",
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        unit_cost=Decimal("55"),
    )
    service.set_approval_state(
        document_id=estimate.document_id,
        approval_state=ApprovalState.APPROVED,
    )

    sales_order = service.create_sales_order_from_estimate(
        estimate_document_id=estimate.document_id,
        inherit_terms_from_estimate=True,
    )

    assert sales_order.document_type == CommercialDocumentType.SALES_ORDER
    assert sales_order.project_id == estimate.project_id
    assert sales_order.customer_id == estimate.customer_id
    assert len(sales_order.lines) == len(estimate.lines)
    assert sales_order.lines[0].source_document_id == estimate.document_id
    assert sales_order.lines[0].source_line_id == estimate.lines[0].line_id
    assert (sales_order.terms_and_conditions_reference or {}).get("source") in {
        "inherited_from_estimate",
        "resolved",
    }
    assert (sales_order.terms_and_conditions_snapshot or {}).get("content")


def test_duplicate_document_assigns_new_identity_number_and_traceability() -> None:
    service = TransactionsWorkspaceService(serialized_terms_blocks=_terms_blocks("v1"))
    estimate = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        project_code="P-A",
        customer_id="customer-a",
    )
    service._commercial_service.add_line(
        estimate,
        description="Line A",
        quantity=Decimal("2"),
        unit_price=Decimal("125"),
    )
    service.set_approval_state(
        document_id=estimate.document_id,
        approval_state=ApprovalState.APPROVED,
    )
    service.issue_document(document_id=estimate.document_id, reason="issue source")

    duplicate = service.duplicate_document(document_id=estimate.document_id, actor="qa")

    assert duplicate.document_id != estimate.document_id
    assert duplicate.document_number
    assert duplicate.document_number != estimate.document_number
    assert duplicate.lifecycle_state == CommercialDocumentLifecycleState.DRAFT
    assert duplicate.source_document_id == estimate.document_id
    assert duplicate.duplicated_from_document_id == estimate.document_id
    assert duplicate.duplicated_by == "qa"
    assert len(duplicate.lines) == len(estimate.lines)
    assert (duplicate.terms_and_conditions_snapshot or {}).get("content") == (
        estimate.terms_and_conditions_snapshot or {}
    ).get("content")


def test_revision_history_tracks_parent_and_superseded_revisions() -> None:
    service = _service()
    sales_order = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        customer_id="customer-a",
    )

    service.create_draft_revision(
        document_id=sales_order.document_id,
        reason="Scope change",
        actor="qa",
        revision_label="R2-SCOPE",
    )
    service.create_draft_revision(
        document_id=sales_order.document_id,
        reason="Pricing adjustment",
        actor="qa",
        revision_label="R3-PRICE",
    )

    history = service.revision_history(document_id=sales_order.document_id)
    assert len(history) == 3
    assert history[0]["revision_number"] == 1
    assert history[0]["superseded_by_revision_id"]
    assert history[1]["parent_revision_id"] == history[0]["revision_id"]
    assert history[2]["parent_revision_id"] == history[1]["revision_id"]
    assert history[2]["is_current"] is True


def test_issued_revision_is_immutable_and_requires_explicit_new_revision() -> None:
    service = _service()
    estimate = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        customer_id="customer-a",
    )
    service.set_approval_state(
        document_id=estimate.document_id,
        approval_state=ApprovalState.APPROVED,
    )
    issued = service.issue_document(document_id=estimate.document_id, reason="issue")
    assert issued.lifecycle_state == CommercialDocumentLifecycleState.ISSUED

    with pytest.raises(ValueError, match="only mutable drafts/review documents"):
        service.update_draft_metadata(
            document_id=estimate.document_id,
            project_id="project-b",
            project_code="P-B",
            customer_id="customer-b",
            vendor_id=None,
        )

    revised = service.create_draft_revision(
        document_id=estimate.document_id,
        reason="Customer requested change",
        actor="qa",
        revision_label="R2-CHANGE",
    )
    assert revised.lifecycle_state == CommercialDocumentLifecycleState.DRAFT
    assert revised.revision_number == 2

    history = service.revision_history(document_id=estimate.document_id)
    latest = history[-1]
    assert latest["revision_reason"] == "Customer requested change"
    assert latest["revision_label"] == "R2-CHANGE"


def test_pdf_export_is_deterministic_records_activity_and_supports_archived() -> None:
    service = _service()
    sales_order = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        project_code="P-A",
        customer_id="customer-a",
    )
    service._commercial_service.add_line(
        sales_order,
        description="Hardware",
        quantity=Decimal("1"),
        unit_price=Decimal("99.99"),
    )

    export_1 = service.export_document_pdf(
        document_id=sales_order.document_id,
        presentation="sales_order",
        actor="qa",
    )
    export_2 = service.export_document_pdf(
        document_id=sales_order.document_id,
        presentation="sales_order",
        actor="qa",
    )

    assert export_1["file_name"].endswith(".pdf")
    assert export_1["payload"] == export_2["payload"]
    assert export_1["content_hash"] == export_2["content_hash"]

    archived = service.archive_document(sales_order.document_id)
    assert archived.lifecycle_state == CommercialDocumentLifecycleState.ARCHIVED
    archived_export = service.export_document_pdf(
        document_id=sales_order.document_id,
        presentation="sales_order",
        actor="qa",
    )
    assert archived_export["payload"]
    assert len(archived.export_activity) >= 3


def test_future_email_metadata_serialization_round_trip() -> None:
    service = _service()
    estimate = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        customer_id="customer-a",
    )

    queued = service.enqueue_future_email_delivery(
        document_id=estimate.document_id,
        provider="microsoft_365",
        recipient="customer@example.com",
        cc=["ops@example.com"],
        bcc=["audit@example.com"],
        subject="Estimate revision",
        message_template="template-a",
        actor="qa",
        attached_revision_number=estimate.revision_number,
    )
    assert queued["delivery_status"] == "queued_for_future"
    assert queued["provider_message_id"] is None

    restored = TransactionsWorkspaceService(serialized_documents=service.to_payload())
    restored_doc = restored.get_document(estimate.document_id)
    assert restored_doc is not None
    assert len(restored_doc.future_email_metadata) == 1
    assert restored_doc.future_email_metadata[0]["recipient"] == "customer@example.com"


def test_duplicate_and_export_preserve_tenant_isolation() -> None:
    service = _service()
    estimate_tenant_a = service.create_draft(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        customer_id="customer-a",
    )
    estimate_tenant_b = service.create_draft(
        tenant_id="tenant-b",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-b",
        customer_id="customer-b",
    )

    duplicate = service.duplicate_document(
        document_id=estimate_tenant_a.document_id,
        actor="qa",
    )
    assert duplicate.tenant_id == "tenant-a"

    service.export_document_pdf(
        document_id=duplicate.document_id,
        presentation="internal_estimate",
        actor="qa",
    )
    service.enqueue_future_email_delivery(
        document_id=duplicate.document_id,
        provider="smtp",
        recipient="a@example.com",
        subject="tenant-a",
        actor="qa",
    )

    untouched = service.get_document(estimate_tenant_b.document_id)
    assert untouched is not None
    assert untouched.tenant_id == "tenant-b"
    assert untouched.export_activity == []
    assert untouched.future_email_metadata == []

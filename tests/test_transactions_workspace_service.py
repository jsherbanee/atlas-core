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
    return TransactionsWorkspaceService(
        active_tenant_id="tenant-1",
        active_organization_id="org-1",
    )


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


def test_transactions_workspace_requires_active_scope_by_default() -> None:
    with pytest.raises(ValueError, match="active_tenant_id"):
        TransactionsWorkspaceService()


def test_transactions_workspace_blocks_cross_tenant_create_when_scope_enforced() -> (
    None
):
    service = TransactionsWorkspaceService(
        active_tenant_id="tenant-a",
        active_organization_id="org-1",
    )

    with pytest.raises(ValueError, match="tenant scope mismatch"):
        service.create_draft(
            tenant_id="tenant-b",
            organization_id="org-1",
            document_type=CommercialDocumentType.ESTIMATE,
            project_id="project-b",
            customer_id="customer-b",
        )


def test_active_scope_filters_cross_tenant_documents() -> None:
    service = TransactionsWorkspaceService(
        active_tenant_id="tenant-a",
        active_organization_id="org-1",
    )
    tenant_a = service.create_draft(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        customer_id="customer-a",
    )
    service_unscoped = TransactionsWorkspaceService(
        serialized_documents=service.to_payload(),
        enforce_active_scope=False,
    )
    tenant_b = service_unscoped.create_draft(
        tenant_id="tenant-b",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-b",
        customer_id="customer-b",
    )

    scoped = TransactionsWorkspaceService(
        serialized_documents=service_unscoped.to_payload(),
        active_tenant_id="tenant-a",
        active_organization_id="org-1",
    )
    visible = scoped.list_documents(include_archived=True)

    assert [item.document_id for item in visible] == [tenant_a.document_id]
    assert scoped.get_document(tenant_b.document_id) is None


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


def test_create_customer_invoice_from_sales_order_with_billing() -> None:
    service = _service()
    sales_order = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        project_code="P-A",
        customer_id="customer-a",
    )

    invoice = service.create_customer_invoice_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id=None,
        source_type="sales_order",
        source_document_id=sales_order.document_id,
        billing_strategy="milestone",
        requested_amount=Decimal("450.00"),
        available_to_bill=Decimal("1000.00"),
        billing_context={"milestone": "rough_in_complete"},
    )

    assert invoice.document_type == CommercialDocumentType.CUSTOMER_INVOICE
    assert invoice.customer_id == "customer-a"
    assert invoice.project_id == "project-a"
    assert invoice.source_document_id == sales_order.document_id
    assert (invoice.document_metadata or {}).get("source_type") == "sales_order"
    assert (invoice.document_metadata or {}).get("billing_strategy") == "milestone"
    assert (invoice.document_metadata or {}).get("requested_amount") == "450.00"
    assert invoice.totals.subtotal == Decimal("450.00")


def test_customer_invoice_overbilling_requires_override() -> None:
    service = _service()
    invoice = service.create_customer_invoice_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-a",
        source_type="standalone",
        billing_strategy="partial",
    )

    with pytest.raises(ValueError, match="requested_amount exceeds available_to_bill"):
        service.set_customer_invoice_billing(
            document_id=invoice.document_id,
            billing_strategy="partial",
            requested_amount=Decimal("1200.00"),
            available_to_bill=Decimal("800.00"),
        )

    updated = service.set_customer_invoice_billing(
        document_id=invoice.document_id,
        billing_strategy="partial",
        requested_amount=Decimal("1200.00"),
        available_to_bill=Decimal("800.00"),
        allow_overbilling=True,
        override_reason="Final reconciliation",
        override_actor="qa",
    )
    assert (updated.document_metadata or {}).get("overbilling_override_applied") is True
    assert any(
        diagnostic.code == "customer_invoice_overbilling_override"
        for diagnostic in updated.diagnostics
    )


def test_customer_invoice_issue_payment_and_sync_metadata() -> None:
    service = _service()
    invoice = service.create_customer_invoice_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-a",
        source_type="project",
        project_id="project-a",
        project_code="P-A",
        billing_strategy="progress",
        requested_amount=Decimal("500.00"),
        available_to_bill=Decimal("1000.00"),
    )
    service.set_approval_state(
        document_id=invoice.document_id,
        approval_state=ApprovalState.APPROVED,
    )

    issued = service.issue_document(document_id=invoice.document_id, reason="issue")
    assert issued.lifecycle_state == CommercialDocumentLifecycleState.ISSUED
    assert issued.sync_metadata.status == SyncStatus.READY
    assert (issued.document_metadata or {}).get("payment_status") == "unpaid"

    partially_paid = service.set_customer_invoice_payment_state(
        document_id=invoice.document_id,
        payment_state="partially_paid",
        reason="Partial payment posted",
    )
    assert (
        partially_paid.lifecycle_state
        == CommercialDocumentLifecycleState.PARTIALLY_PAID
    )

    paid = service.set_customer_invoice_payment_state(
        document_id=invoice.document_id,
        payment_state="paid",
        reason="Final payment posted",
    )
    assert paid.lifecycle_state == CommercialDocumentLifecycleState.PAID

    synced = service.record_customer_invoice_sync_event(
        document_id=invoice.document_id,
        sync_status=SyncStatus.SYNCED,
        external_id="qb-inv-123",
        external_revision="v7",
        reconciliation_state="reconciled",
        payment_status="paid",
    )
    assert synced.sync_metadata.external_object_type == "invoice"
    assert synced.sync_metadata.external_id == "qb-inv-123"
    assert synced.sync_metadata.status == SyncStatus.SYNCED
    assert (synced.document_metadata or {}).get("quickbooks_payment_status") == "paid"


def test_customer_invoice_pdf_and_duplication_supported() -> None:
    service = _service()
    invoice = service.create_customer_invoice_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-a",
        source_type="standalone",
        billing_strategy="full",
        requested_amount=Decimal("200.00"),
        available_to_bill=Decimal("200.00"),
    )
    service.set_approval_state(
        document_id=invoice.document_id,
        approval_state=ApprovalState.APPROVED,
    )
    service.issue_document(document_id=invoice.document_id, reason="issue")

    export_1 = service.export_document_pdf(
        document_id=invoice.document_id,
        presentation="customer_invoice",
        actor="qa",
    )
    export_2 = service.export_document_pdf(
        document_id=invoice.document_id,
        presentation="customer_invoice",
        actor="qa",
    )
    assert export_1["payload"] == export_2["payload"]
    assert export_1["content_hash"] == export_2["content_hash"]

    duplicate = service.duplicate_document(document_id=invoice.document_id, actor="qa")
    assert duplicate.document_type == CommercialDocumentType.CUSTOMER_INVOICE
    assert duplicate.source_document_id == invoice.document_id


def test_additive_change_order_from_sales_order_tracks_metadata() -> None:
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
        description="Add equipment",
        quantity=Decimal("1"),
        unit_price=Decimal("500.00"),
    )

    configured = service.configure_change_order_tracking(
        document_id=sales_order.document_id,
        is_change_order=True,
        base_bid_reference="accepted_estimate:est-1",
        change_reason="Client requested expansion",
        requested_by="pm",
        approved_by="director",
        approval_date="2026-07-14",
        effective_date="2026-07-20",
        source_document="est-1",
        related_documents=["est-1"],
    )

    metadata = configured.document_metadata or {}
    assert metadata.get("is_change_order") is True
    assert metadata.get("change_order_direction") == "additive"
    assert metadata.get("change_order_number") == "CO #1"
    assert metadata.get("change_order_sequence") == 1


def test_deductive_change_order_from_return_order_tracks_metadata() -> None:
    service = _service()
    return_order = service.create_return_order(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-a",
        project_id="project-a",
        project_code="P-A",
        return_reason="scope reduction",
        return_type="service",
    )

    configured = service.configure_change_order_tracking(
        document_id=return_order.document_id,
        is_change_order=True,
        change_reason="Scope reduction",
        requested_by="pm",
    )

    metadata = configured.document_metadata or {}
    assert metadata.get("is_change_order") is True
    assert metadata.get("change_order_direction") == "deductive"
    assert metadata.get("change_order_number") == "CO #1"
    assert metadata.get("change_order_sequence") == 1


def test_change_order_preview_non_consuming_and_duplicate_rejection() -> None:
    service = _service()
    first = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        customer_id="customer-a",
    )
    second = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        customer_id="customer-a",
    )

    preview_1 = service.preview_next_change_order_number(
        tenant_id="tenant-1",
        project_id="project-a",
    )
    preview_2 = service.preview_next_change_order_number(
        tenant_id="tenant-1",
        project_id="project-a",
    )
    assert preview_1["change_order_sequence"] == 1
    assert preview_2["change_order_sequence"] == 1

    service.configure_change_order_tracking(
        document_id=first.document_id,
        is_change_order=True,
        change_order_sequence=1,
    )

    with pytest.raises(
        ValueError,
        match="change-order sequence is already allocated for this project",
    ):
        service.configure_change_order_tracking(
            document_id=second.document_id,
            is_change_order=True,
            change_order_sequence=1,
        )


def test_change_order_sequence_is_project_scoped_and_not_reused_after_archive() -> None:
    service = _service()
    first_project_a = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        customer_id="customer-a",
    )
    first_project_b = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-b",
        customer_id="customer-a",
    )
    service.configure_change_order_tracking(
        document_id=first_project_a.document_id,
        is_change_order=True,
    )
    service.configure_change_order_tracking(
        document_id=first_project_b.document_id,
        is_change_order=True,
    )

    service.archive_document(first_project_a.document_id)
    second_project_a = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        customer_id="customer-a",
    )
    configured = service.configure_change_order_tracking(
        document_id=second_project_a.document_id,
        is_change_order=True,
    )
    assert (configured.document_metadata or {}).get("change_order_sequence") == 2


def test_project_base_bid_and_net_contract_value_summary() -> None:
    service = _service()
    estimate = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-a",
        customer_id="customer-a",
    )
    service._commercial_service.add_line(
        estimate,
        description="Base scope",
        quantity=Decimal("1"),
        unit_price=Decimal("1000.00"),
    )
    service.set_approval_state(
        document_id=estimate.document_id,
        approval_state=ApprovalState.APPROVED,
    )
    service.set_project_base_bid(
        tenant_id="tenant-1",
        project_id="project-a",
        project_code="P-A",
        reference_type="accepted_estimate",
        reference_document_id=estimate.document_id,
        actor="qa",
    )

    additive = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        customer_id="customer-a",
    )
    service._commercial_service.add_line(
        additive,
        description="Add scope",
        quantity=Decimal("1"),
        unit_price=Decimal("250.00"),
    )
    service.configure_change_order_tracking(
        document_id=additive.document_id,
        is_change_order=True,
    )

    deductive = service.create_return_order(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-a",
        project_id="project-a",
        project_code="P-A",
    )
    service.add_return_order_line(
        return_order_document_id=deductive.document_id,
        description="Deduct scope",
        quantity=Decimal("1"),
        original_unit_price=Decimal("50.00"),
        line_type="service",
    )
    service.configure_change_order_tracking(
        document_id=deductive.document_id,
        is_change_order=True,
    )

    summary = service.project_commercial_summary(
        tenant_id="tenant-1",
        project_id="project-a",
    )
    assert summary["base_bid_value"] == "1000.00"
    assert summary["additive_change_total"] == "250.00"
    assert summary["deductive_change_total"] == "50.00"
    assert summary["net_change_total"] == "200.00"
    assert summary["revised_contract_value"] == "1200.00"
    assert len(summary["ordered_change_list"]) == 2


def test_change_order_revision_behavior_and_audit_diagnostics() -> None:
    service = _service()
    sales_order = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        customer_id="customer-a",
    )
    service.configure_change_order_tracking(
        document_id=sales_order.document_id,
        is_change_order=True,
        change_reason="Adjustment",
    )
    assert any(
        diagnostic.code == "change_order_configured"
        for diagnostic in sales_order.diagnostics
    )

    service.set_approval_state(
        document_id=sales_order.document_id,
        approval_state=ApprovalState.APPROVED,
    )
    service.issue_document(document_id=sales_order.document_id, reason="issue")
    revised = service.create_draft_revision(
        document_id=sales_order.document_id,
        reason="post-issue revision",
    )
    assert revised.lifecycle_state == CommercialDocumentLifecycleState.DRAFT
    assert (revised.document_metadata or {}).get("is_change_order") is True
    assert (revised.document_metadata or {}).get("change_order_number") == "CO #1"


def test_change_order_tenant_isolation_numbering() -> None:
    service = TransactionsWorkspaceService(enforce_active_scope=False)
    tenant_a = service.create_draft(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        customer_id="customer-a",
    )
    tenant_b = service.create_draft(
        tenant_id="tenant-b",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        customer_id="customer-a",
    )
    service.configure_change_order_tracking(
        document_id=tenant_a.document_id,
        is_change_order=True,
    )
    service.configure_change_order_tracking(
        document_id=tenant_b.document_id,
        is_change_order=True,
    )
    assert (tenant_a.document_metadata or {}).get("change_order_sequence") == 1
    assert (tenant_b.document_metadata or {}).get("change_order_sequence") == 1


def test_change_order_pdf_export_and_search_metadata() -> None:
    service = _service()
    sales_order = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        customer_id="customer-a",
    )
    service._commercial_service.add_line(
        sales_order,
        description="CO line",
        quantity=Decimal("1"),
        unit_price=Decimal("100.00"),
    )
    service.configure_change_order_tracking(
        document_id=sales_order.document_id,
        is_change_order=True,
    )
    service.set_approval_state(
        document_id=sales_order.document_id,
        approval_state=ApprovalState.APPROVED,
    )
    service.issue_document(document_id=sales_order.document_id, reason="issue")

    export_payload = service.export_document_pdf(
        document_id=sales_order.document_id,
        presentation="sales_order",
        actor="qa",
    )
    assert export_payload["payload"]
    search_rows = service.list_documents(query="CO #1")
    assert any(row.document_id == sales_order.document_id for row in search_rows)


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
    service = TransactionsWorkspaceService(
        serialized_terms_blocks=_terms_blocks("v1"),
        active_tenant_id="tenant-1",
        active_organization_id="org-1",
    )
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
        active_tenant_id="tenant-1",
        active_organization_id="org-1",
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
        active_tenant_id="tenant-1",
        active_organization_id="org-1",
    )
    preserved = service_v3.get_document(estimate.document_id)
    assert preserved is not None
    assert (preserved.terms_and_conditions_snapshot or {}).get("content") == "v2"


def test_create_sales_order_from_estimate_preserves_traceability_and_terms() -> None:
    service = TransactionsWorkspaceService(
        serialized_terms_blocks=_terms_blocks("v1"),
        active_tenant_id="tenant-1",
        active_organization_id="org-1",
    )
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
    service = TransactionsWorkspaceService(
        serialized_terms_blocks=_terms_blocks("v1"),
        active_tenant_id="tenant-1",
        active_organization_id="org-1",
    )
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

    restored = TransactionsWorkspaceService(
        serialized_documents=service.to_payload(),
        active_tenant_id="tenant-1",
        active_organization_id="org-1",
    )
    restored_doc = restored.get_document(estimate.document_id)
    assert restored_doc is not None
    assert len(restored_doc.future_email_metadata) == 1
    assert restored_doc.future_email_metadata[0]["recipient"] == "customer@example.com"


def test_duplicate_and_export_preserve_tenant_isolation() -> None:
    service = TransactionsWorkspaceService(enforce_active_scope=False)
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


def test_create_standalone_and_linked_return_orders() -> None:
    service = _service()
    standalone = service.create_return_order(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-a",
        project_id=None,
        project_code=None,
        return_reason="damaged",
        return_type="product",
        requested_date="2026-07-13",
    )
    assert standalone.document_type == CommercialDocumentType.RETURN_ORDER
    assert standalone.customer_id == "customer-a"

    sales_order = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        project_code="P-A",
        customer_id="customer-a",
    )
    linked = service.create_return_order(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id=None,
        source_sales_order_id=sales_order.document_id,
        return_reason="incorrect item",
        return_type="service",
    )
    assert linked.source_sales_order_id == sales_order.document_id
    assert linked.customer_id == sales_order.customer_id


def test_process_product_and_service_return_orders_generates_credit_memo() -> None:
    service = _service()
    return_order = service.create_return_order(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-a",
        project_id="project-a",
        project_code="P-A",
        return_reason="service adjustment",
        return_type="mixed",
    )
    service.add_return_order_line(
        return_order_document_id=return_order.document_id,
        description="Returned amplifier",
        quantity=Decimal("2"),
        original_unit_price=Decimal("100.00"),
        approved_return_quantity=Decimal("1"),
        line_type="product",
        restocking_fee=Decimal("10.00"),
        tax_adjustment=Decimal("5.00"),
        product_or_service_reference="amp-1",
        source_document_id="so-1",
        source_line_id="so-line-1",
        inventory_disposition_hook="restock",
    )
    service.add_return_order_line(
        return_order_document_id=return_order.document_id,
        description="Cancelled programming",
        quantity=Decimal("3"),
        original_unit_price=Decimal("50.00"),
        approved_return_quantity=Decimal("2"),
        line_type="service",
        restocking_fee=Decimal("0"),
        tax_adjustment=Decimal("2.50"),
        product_or_service_reference="svc-1",
        source_document_id="inv-1",
        source_line_id="inv-line-2",
    )

    service.request_return_order(
        document_id=return_order.document_id, reason="Requested"
    )
    service.approve_return_order(
        document_id=return_order.document_id, reason="Approved"
    )
    service.receive_return_order(
        document_id=return_order.document_id,
        partial=False,
        received_date="2026-07-14",
        inventory_disposition="restock",
    )
    service.inspect_return_order(
        document_id=return_order.document_id,
        inspection_status="accepted",
    )

    credit_memo = service.process_return_order(
        document_id=return_order.document_id,
        actor="qa",
    )

    assert credit_memo.document_type == CommercialDocumentType.CREDIT_MEMO
    assert credit_memo.lifecycle_state == CommercialDocumentLifecycleState.ISSUED
    assert credit_memo.document_number is not None
    assert credit_memo.source_document_id == return_order.document_id
    assert len(credit_memo.lines) == 2
    assert credit_memo.lines[0].source_document_id == return_order.document_id
    assert credit_memo.lines[0].line_metadata is not None
    assert credit_memo.lines[0].line_metadata["original_source_document_id"] == "so-1"
    assert return_order.lifecycle_state == CommercialDocumentLifecycleState.PROCESSED
    assert return_order.revisions[-1].immutable is True


def test_partial_returns_restocking_fees_and_tax_adjustments_are_deterministic() -> (
    None
):
    service = _service()
    return_order = service.create_return_order(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-a",
        return_reason="over-shipment",
        return_type="product",
    )
    service.add_return_order_line(
        return_order_document_id=return_order.document_id,
        description="Returned fixture",
        quantity=Decimal("4"),
        original_unit_price=Decimal("25.00"),
        approved_return_quantity=Decimal("3"),
        line_type="product",
        restocking_fee=Decimal("7.50"),
        tax_adjustment=Decimal("3.25"),
    )

    metadata = return_order.document_metadata or {}
    assert metadata["approved_credit_amount"] == "70.75"
    assert metadata["restocking_fee"] == "7.50"
    assert metadata["tax_adjustment"] == "3.25"
    assert return_order.totals.grand_total == Decimal("70.75")


def test_return_order_duplicate_credit_memo_generation_is_prevented() -> None:
    service = _service()
    return_order = service.create_return_order(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-a",
        return_reason="defective",
        return_type="product",
    )
    service.add_return_order_line(
        return_order_document_id=return_order.document_id,
        description="Defective device",
        quantity=Decimal("1"),
        original_unit_price=Decimal("120.00"),
        line_type="product",
    )
    service.request_return_order(
        document_id=return_order.document_id, reason="Requested"
    )
    service.approve_return_order(
        document_id=return_order.document_id, reason="Approved"
    )
    service.inspect_return_order(
        document_id=return_order.document_id,
        inspection_status="accepted",
    )
    service.process_return_order(document_id=return_order.document_id, actor="qa")

    with pytest.raises(ValueError, match="credit memo already generated"):
        service.process_return_order(document_id=return_order.document_id, actor="qa")


def test_credit_memo_pdf_export_and_quickbooks_sync_metadata() -> None:
    service = _service()
    return_order = service.create_return_order(
        tenant_id="tenant-1",
        organization_id="org-1",
        customer_id="customer-a",
        return_reason="goodwill",
        return_type="service",
    )
    service.add_return_order_line(
        return_order_document_id=return_order.document_id,
        description="Service credit",
        quantity=Decimal("1"),
        original_unit_price=Decimal("80.00"),
        line_type="service",
    )
    service.request_return_order(
        document_id=return_order.document_id, reason="Requested"
    )
    service.approve_return_order(
        document_id=return_order.document_id, reason="Approved"
    )
    credit_memo = service.process_return_order(
        document_id=return_order.document_id, actor="qa"
    )

    export_result = service.export_document_pdf(
        document_id=credit_memo.document_id,
        presentation="credit_memo",
        actor="qa",
    )
    assert export_result["file_name"].endswith(".pdf")
    assert export_result["payload"].startswith(b"%PDF-1.4")
    assert credit_memo.sync_metadata.integration == "quickbooks"
    assert credit_memo.sync_metadata.status == SyncStatus.NOT_READY


def test_return_order_tenant_isolation_preserved_through_credit_generation() -> None:
    service = TransactionsWorkspaceService(enforce_active_scope=False)
    tenant_a = service.create_return_order(
        tenant_id="tenant-a",
        organization_id="org-1",
        customer_id="customer-a",
        return_reason="warranty",
        return_type="product",
    )
    service.add_return_order_line(
        return_order_document_id=tenant_a.document_id,
        description="Returned unit",
        quantity=Decimal("1"),
        original_unit_price=Decimal("40.00"),
        line_type="product",
    )
    tenant_b = service.create_return_order(
        tenant_id="tenant-b",
        organization_id="org-1",
        customer_id="customer-b",
        return_reason="other",
        return_type="service",
    )
    service.add_return_order_line(
        return_order_document_id=tenant_b.document_id,
        description="Service reversal",
        quantity=Decimal("1"),
        original_unit_price=Decimal("15.00"),
        line_type="service",
    )
    service.request_return_order(document_id=tenant_a.document_id, reason="Requested")
    service.approve_return_order(document_id=tenant_a.document_id, reason="Approved")
    credit_memo = service.process_return_order(
        document_id=tenant_a.document_id, actor="qa"
    )

    assert credit_memo.tenant_id == "tenant-a"
    untouched = service.get_document(tenant_b.document_id)
    assert untouched is not None
    assert untouched.document_metadata is not None
    assert untouched.document_metadata.get("generated_credit_memo_id") is None

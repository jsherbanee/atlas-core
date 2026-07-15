from __future__ import annotations

from decimal import Decimal

from atlas_core.domain.commercial_document import ApprovalState, CommercialDocumentType
from atlas_core.services.transactions_workspace_service import (
    TransactionsWorkspaceService,
)


def _service() -> TransactionsWorkspaceService:
    return TransactionsWorkspaceService(
        active_tenant_id="tenant-1",
        active_organization_id="org-1",
    )


def _sales_order_with_lines() -> tuple[TransactionsWorkspaceService, str]:
    service = _service()
    document = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        project_code="P-A",
        customer_id="customer-a",
    )
    service._commercial_service.add_line(
        document,
        description="Camera",
        quantity=Decimal("2"),
        unit_price=Decimal("100.00"),
        unit_cost=Decimal("10.00"),
        discount=Decimal("0"),
        tax_rate=Decimal("0"),
        product_or_service_reference="CAM-1",
        line_metadata={"manufacturer": "Acme"},
    )
    service._commercial_service.add_line(
        document,
        description="Programming",
        quantity=Decimal("3"),
        unit_price=Decimal("50.00"),
        unit_cost=Decimal("20.00"),
        discount=Decimal("2.00"),
        tax_rate=Decimal("10.00"),
        product_or_service_reference="SVC-1",
        line_metadata={"line_type": "service", "manufacturer": "Atlas Services"},
    )
    return service, document.document_id


def test_reorder_persists_display_sequence_without_changing_totals() -> None:
    service, document_id = _sales_order_with_lines()
    document = service.get_document(document_id)
    assert document is not None
    baseline_total = document.totals.grand_total
    baseline_ids = [line.line_id for line in document.lines]

    service.reorder_lines(
        document_id=document_id, ordered_line_ids=list(reversed(baseline_ids))
    )

    snapshot = service.line_presentation_snapshot(document_id=document_id)
    assert [row["line_id"] for row in snapshot["rows"][:2]] == list(
        reversed(baseline_ids)
    )
    assert document.totals.grand_total == baseline_total


def test_grouping_comment_lines_blank_lines_and_subtotals_are_preserved() -> None:
    service, document_id = _sales_order_with_lines()
    document = service.get_document(document_id)
    assert document is not None
    first_line_id = document.lines[0].line_id

    group = service.create_named_group(
        document_id=document_id, name="Video", show_subtotal=True
    )
    service.assign_line_to_group(
        document_id=document_id, line_id=first_line_id, group_id=group["group_id"]
    )
    service.add_presentation_line(
        document_id=document_id,
        line_type="comment",
        text="Installed near lobby",
        group_id=group["group_id"],
        parent_line_id=first_line_id,
        comment_reference_line_id=first_line_id,
    )
    service.add_presentation_line(
        document_id=document_id,
        line_type="blank_spacer",
        group_id=group["group_id"],
        parent_line_id=first_line_id,
    )

    snapshot = service.line_presentation_snapshot(document_id=document_id)
    line_types = [row["line_type"] for row in snapshot["rows"]]
    assert "group_header" in line_types
    assert "subtotal" in line_types
    assert "comment" in line_types
    assert "blank_spacer" in line_types
    comment_row = next(row for row in snapshot["rows"] if row["line_type"] == "comment")
    assert comment_row["comment_reference_line_id"] == first_line_id
    subtotal_row = next(
        row for row in snapshot["rows"] if row["line_type"] == "subtotal"
    )
    assert subtotal_row["group_subtotal"] == "200.00"


def test_sort_preview_apply_and_restore_manual_order() -> None:
    service, document_id = _sales_order_with_lines()
    document = service.get_document(document_id)
    assert document is not None
    original_order = [line.line_id for line in document.lines]

    preview = service.sort_lines(
        document_id=document_id,
        column="description",
        direction="desc",
        apply=False,
    )
    assert preview[0]["description"] == "Programming"
    snapshot = service.line_presentation_snapshot(document_id=document_id)
    assert [row["line_id"] for row in snapshot["rows"][:2]] == original_order

    service.sort_lines(
        document_id=document_id,
        column="description",
        direction="desc",
        apply=True,
    )
    applied = service.line_presentation_snapshot(document_id=document_id)
    assert applied["rows"][0]["description"] == "Programming"

    service.restore_manual_line_order(document_id=document_id)
    restored = service.line_presentation_snapshot(document_id=document_id)
    assert [row["line_id"] for row in restored["rows"][:2]] == original_order


def test_sort_preview_supports_extended_numeric_columns() -> None:
    service, document_id = _sales_order_with_lines()

    unit_cost_preview = service.sort_lines(
        document_id=document_id,
        column="unit_cost",
        direction="desc",
        apply=False,
    )
    discount_preview = service.sort_lines(
        document_id=document_id,
        column="discount",
        direction="desc",
        apply=False,
    )
    tax_rate_preview = service.sort_lines(
        document_id=document_id,
        column="tax_rate",
        direction="desc",
        apply=False,
    )

    assert unit_cost_preview[0]["description"] == "Programming"
    assert discount_preview[0]["description"] == "Programming"
    assert tax_rate_preview[0]["description"] == "Programming"


def test_duplicate_and_revision_preserve_presentation_metadata() -> None:
    service, document_id = _sales_order_with_lines()
    document = service.get_document(document_id)
    assert document is not None
    group = service.create_named_group(document_id=document_id, name="Systems")
    service.assign_line_to_group(
        document_id=document_id,
        line_id=document.lines[0].line_id,
        group_id=group["group_id"],
    )
    service.set_visible_columns(
        document_id=document_id,
        visible_columns=["description", "quantity", "extended_price"],
    )
    service.add_presentation_line(
        document_id=document_id,
        line_type="comment",
        text="Presentation note",
        parent_line_id=document.lines[0].line_id,
        comment_reference_line_id=document.lines[0].line_id,
    )

    duplicated = service.duplicate_document(document_id=document_id, actor="qa")
    assert duplicated.document_metadata is not None
    assert (duplicated.document_metadata.get("presentation") or {}).get(
        "visible_columns"
    ) == [
        "description",
        "quantity",
        "extended_price",
    ]
    assert any(
        (line.presentation_metadata.get("group_id") or "") == group["group_id"]
        for line in duplicated.lines
    )

    service.set_approval_state(
        document_id=document_id, approval_state=ApprovalState.APPROVED
    )
    service.issue_document(document_id=document_id, reason="issue")
    revised = service.create_draft_revision(
        document_id=document_id, reason="presentation keep", actor="qa"
    )
    assert revised.revisions[-1].parent_revision_id is not None


def test_pdf_export_respects_presentation_order_and_visible_columns() -> None:
    service, document_id = _sales_order_with_lines()
    document = service.get_document(document_id)
    assert document is not None
    service.create_named_group(document_id=document_id, name="Audio")
    service.reorder_lines(
        document_id=document_id,
        ordered_line_ids=[line.line_id for line in reversed(document.lines)],
    )
    service.set_visible_columns(
        document_id=document_id,
        visible_columns=["description", "extended_price"],
    )

    export = service.export_document_pdf(
        document_id=document_id,
        presentation="sales_order",
        actor="qa",
    )
    payload = export["payload"]
    assert payload.startswith(b"%PDF-1.4")
    assert payload.find(b"Programming") < payload.find(b"Camera")
    assert b"Qty" not in payload


def test_tenant_isolation_for_presentation_metadata() -> None:
    service = TransactionsWorkspaceService(enforce_active_scope=False)
    primary = service.create_draft(
        tenant_id="tenant-1",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-a",
        project_code="P-A",
        customer_id="customer-a",
    )
    service._commercial_service.add_line(
        primary,
        description="Camera",
        quantity=Decimal("2"),
        unit_price=Decimal("100.00"),
    )
    document_id = primary.document_id
    other = service.create_draft(
        tenant_id="tenant-2",
        organization_id="org-1",
        document_type=CommercialDocumentType.CREDIT_MEMO,
        customer_id="customer-b",
    )
    service.create_named_group(document_id=document_id, name="Primary")

    original_snapshot = service.line_presentation_snapshot(document_id=document_id)
    assert original_snapshot["groups"]
    assert (
        service.line_presentation_snapshot(document_id=other.document_id)["groups"]
        == []
    )

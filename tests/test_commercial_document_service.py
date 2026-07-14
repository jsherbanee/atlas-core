from __future__ import annotations

from decimal import Decimal

from atlas_core.domain.commercial_document import (
    ApprovalState,
    CommercialDocument,
    CommercialDocumentLifecycleState,
    CommercialDocumentType,
)
from atlas_core.services.commercial_document_service import CommercialDocumentService
import pytest


def test_create_document_supports_optional_project_and_project_code() -> None:
    service = CommercialDocumentService()

    document = service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id=None,
        project_code="PC-001",
        customer_id="customer-1",
    )

    assert document.project_id is None
    assert document.project_code == "PC-001"
    assert document.customer_id == "customer-1"
    assert document.vendor_id is None


def test_add_line_uses_stable_document_scoped_line_ids() -> None:
    service = CommercialDocumentService()
    document = service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
    )

    line_1 = service.add_line(
        document,
        description="Labor",
        quantity=Decimal("2"),
        unit_price=Decimal("10.00"),
    )
    line_2 = service.add_line(
        document,
        description="Materials",
        quantity=Decimal("1"),
        unit_price=Decimal("5.00"),
    )

    assert line_1.line_id.startswith("line-")
    assert line_2.line_id.startswith("line-")
    assert line_1.line_id != line_2.line_id
    assert line_1.sequence == 1
    assert line_2.sequence == 2


def test_totals_are_decimal_safe() -> None:
    service = CommercialDocumentService()
    document = service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
    )

    service.add_line(
        document,
        description="Line A",
        quantity=Decimal("3"),
        unit_price=Decimal("0.10"),
        tax_rate=Decimal("0.05"),
    )
    service.add_line(
        document,
        description="Line B",
        quantity=Decimal("2"),
        unit_price=Decimal("0.20"),
        discount=Decimal("0.05"),
    )

    assert document.totals.subtotal == Decimal("0.70")
    assert document.totals.discount_total == Decimal("0.05")
    assert document.totals.tax_total == Decimal("0.015")
    assert document.totals.grand_total == Decimal("0.665")


def test_number_preview_and_allocation_do_not_reuse_numbers() -> None:
    service = CommercialDocumentService()
    document = service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.PURCHASE_ORDER,
    )

    preview_1 = service.preview_number(document)
    preview_2 = service.preview_number(document)

    assert preview_1.preview_number == preview_2.preview_number

    allocated = service.allocate_number(document)
    assert allocated == preview_1.preview_number

    next_preview = service.preview_number(document)
    assert next_preview.preview_number != allocated


def test_issued_revision_is_immutable_for_line_mutations() -> None:
    service = CommercialDocumentService()
    document = service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.CUSTOMER_INVOICE,
    )

    service.add_line(
        document,
        description="Billable",
        quantity=Decimal("1"),
        unit_price=Decimal("100.00"),
    )
    service.set_approval_state(document, ApprovalState.APPROVED)
    service.transition_lifecycle(
        document,
        CommercialDocumentLifecycleState.IN_REVIEW,
        reason="review",
    )
    service.transition_lifecycle(
        document,
        CommercialDocumentLifecycleState.APPROVED,
        reason="approved",
    )
    service.transition_lifecycle(
        document,
        CommercialDocumentLifecycleState.ISSUED,
        reason="issued",
    )

    assert document.revisions
    assert document.revisions[0].immutable is True

    with pytest.raises(ValueError):
        service.add_line(
            document,
            description="Late mutation",
            quantity=Decimal("1"),
            unit_price=Decimal("1"),
        )


def test_transition_rejects_invalid_state_jump() -> None:
    service = CommercialDocumentService()
    document = service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.VENDOR_BILL,
    )

    with pytest.raises(ValueError):
        service.transition_lifecycle(
            document,
            CommercialDocumentLifecycleState.ISSUED,
            reason="invalid",
        )


def test_terms_snapshot_assignment_is_immutable_after_issue() -> None:
    service = CommercialDocumentService()
    document = service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
    )
    service.assign_terms_and_conditions(
        document,
        reference={"block_id": "terms-estimate-v1", "version": 1},
        snapshot={"title": "Estimate Terms", "content": "v1", "version": 1},
    )
    service.set_approval_state(document, ApprovalState.APPROVED)
    service.transition_lifecycle(
        document,
        CommercialDocumentLifecycleState.IN_REVIEW,
        reason="review",
    )
    service.transition_lifecycle(
        document,
        CommercialDocumentLifecycleState.APPROVED,
        reason="approved",
    )
    service.transition_lifecycle(
        document,
        CommercialDocumentLifecycleState.ISSUED,
        reason="issued",
    )

    with pytest.raises(ValueError):
        service.assign_terms_and_conditions(
            document,
            reference={"block_id": "terms-estimate-v2", "version": 2},
            snapshot={"title": "Estimate Terms", "content": "v2", "version": 2},
        )


def test_relationship_and_line_traceability_fields_are_preserved() -> None:
    service = CommercialDocumentService()
    document = service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.CHANGE_ORDER,
        project_id="project-1",
    )

    line = service.add_line(
        document,
        description="Change item",
        quantity=Decimal("1"),
        unit_price=Decimal("50"),
        source_document_id="doc-source",
        source_line_id="line-source",
        related_document_id="doc-related",
        related_line_id="line-related",
    )
    relationship = service.add_relationship(
        document,
        relationship_type="derived_from",
        related_document_id="doc-source",
        related_line_id="line-source",
        source_line_id=line.line_id,
    )

    assert line.source_document_id == "doc-source"
    assert line.source_line_id == "line-source"
    assert line.related_document_id == "doc-related"
    assert line.related_line_id == "line-related"
    assert relationship.related_document_id == "doc-source"
    assert relationship.source_line_id == line.line_id


def test_tenant_isolation_is_enforced() -> None:
    service = CommercialDocumentService()
    doc_a = service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.RFQ,
    )
    doc_b = service.create_document(
        tenant_id="tenant-b",
        organization_id="org-1",
        document_type=CommercialDocumentType.VENDOR_QUOTE,
    )

    with pytest.raises(ValueError):
        service.assert_same_tenant(doc_a, doc_b)


def test_backward_compatible_serialization_supports_status_field() -> None:
    document = CommercialDocument.from_dict(
        {
            "document_id": "doc-1",
            "tenant_id": "tenant-a",
            "organization_id": "org-1",
            "document_type": "estimate",
            "status": "draft",
            "approval_state": "not_requested",
            "document_number": None,
            "project_id": None,
            "project_code": None,
            "customer_id": None,
            "vendor_id": None,
            "lines": [],
            "relationships": [],
            "diagnostics": [],
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    )

    assert document.lifecycle_state == CommercialDocumentLifecycleState.DRAFT
    payload = document.to_dict()
    assert payload["lifecycle_state"] == "draft"

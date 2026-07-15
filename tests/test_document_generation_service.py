from __future__ import annotations

from decimal import Decimal

from atlas_core.contracts.document_generation_contracts import (
    OutputFormat,
    RenderRequest,
)
from atlas_core.domain.commercial_document import (
    ApprovalState,
    CommercialDocument,
    CommercialDocumentLifecycleState,
    CommercialDocumentType,
)
from atlas_core.services.commercial_document_service import CommercialDocumentService
from atlas_core.services.document_generation_service import DocumentGenerationService
from atlas_core.services.transactions_workspace_service import (
    TransactionsWorkspaceService,
)


def _template_payload(
    *,
    template_id: str,
    version_number: int,
    content: str,
    tenant_id: str = "tenant-a",
    organization_id: str = "org-a",
    document_family: str = "estimate",
    is_default: bool = False,
    customer_id: str | None = None,
    project_id: str | None = None,
    transaction_id: str | None = None,
) -> dict[str, object]:
    return {
        "template_id": template_id,
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "title": f"{template_id}-title",
        "document_family": document_family,
        "status": "active",
        "is_default": is_default,
        "customer_id": customer_id,
        "project_id": project_id,
        "transaction_id": transaction_id,
        "archived": False,
        "versions": [
            {
                "template_version_id": f"{template_id}-v{version_number}",
                "version_number": version_number,
                "content": content,
                "content_hash": f"hash-{template_id}-v{version_number}",
                "section_config": {},
                "created_at": "2026-07-15T00:00:00+00:00",
                "created_by": "tester",
            }
        ],
        "created_at": "2026-07-15T00:00:00+00:00",
        "created_by": "tester",
        "updated_at": "2026-07-15T00:00:00+00:00",
        "updated_by": "tester",
    }


def _build_document() -> tuple[CommercialDocumentService, CommercialDocument]:
    service = CommercialDocumentService()
    document = service.create_document(
        tenant_id="tenant-a",
        organization_id="org-a",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-1",
        project_code="P-1",
        customer_id="customer-1",
    )
    service.add_line(
        document,
        description="Line A",
        quantity=Decimal("2"),
        unit_price=Decimal("125.00"),
    )
    service.assign_terms_and_conditions(
        document,
        reference={"block_id": "terms-1", "version": 1, "source": "resolved"},
        snapshot={"block_id": "terms-1", "version": 1, "content": "Net 30"},
    )
    return service, document


def test_template_precedence_prefers_transaction_over_other_scopes() -> None:
    generation = DocumentGenerationService(
        serialized_templates=[
            _template_payload(
                template_id="default-template",
                version_number=1,
                content="default",
                is_default=True,
            ),
            _template_payload(
                template_id="customer-template",
                version_number=1,
                content="customer",
                customer_id="customer-1",
            ),
            _template_payload(
                template_id="project-template",
                version_number=1,
                content="project",
                project_id="project-1",
            ),
            _template_payload(
                template_id="transaction-template",
                version_number=1,
                content="transaction",
                transaction_id="doc-abc",
            ),
        ]
    )

    resolved = generation.resolve_template(
        tenant_id="tenant-a",
        organization_id="org-a",
        document_family="estimate",
        customer_id="customer-1",
        project_id="project-1",
        transaction_id="doc-abc",
    )

    assert resolved.template.template_id == "transaction-template"
    assert resolved.source.value == "transaction"


def test_render_uses_revision_template_snapshot_after_issue_even_when_new_template_versions_exist() -> (
    None
):
    commercial_service, document = _build_document()
    generation = DocumentGenerationService(
        serialized_templates=[
            _template_payload(
                template_id="default-template",
                version_number=1,
                content="<html><body>v1 {{document_number}}</body></html>",
                is_default=True,
            )
        ]
    )
    revision = document.revisions[0]

    first = generation.render_document(
        request=RenderRequest(
            tenant_id=document.tenant_id,
            organization_id=document.organization_id,
            actor_id="tester",
            document_id=document.document_id,
            revision_number=revision.revision_number,
            document_family=document.document_type.value,
            output_format=OutputFormat.HTML,
            presentation="internal_estimate",
        ),
        document=document,
        revision=revision,
    )
    commercial_service.assign_template_version(
        document,
        assignment=first.assignment.to_dict(),
        snapshot=first.template_version_snapshot,
    )
    commercial_service.transition_lifecycle(
        document,
        target_state=CommercialDocumentLifecycleState.IN_REVIEW,
        reason="review",
    )
    commercial_service.set_approval_state(document, ApprovalState.APPROVED)
    commercial_service.transition_lifecycle(
        document,
        target_state=CommercialDocumentLifecycleState.APPROVED,
        reason="approved",
    )
    commercial_service.transition_lifecycle(
        document,
        target_state=CommercialDocumentLifecycleState.ISSUED,
        reason="issue",
    )
    issued_revision = next(
        item
        for item in document.revisions
        if item.revision_number == document.revision_number
    )
    issued_before_template_change = generation.render_document(
        request=RenderRequest(
            tenant_id=document.tenant_id,
            organization_id=document.organization_id,
            actor_id="tester",
            document_id=document.document_id,
            revision_number=issued_revision.revision_number,
            document_family=document.document_type.value,
            output_format=OutputFormat.HTML,
            presentation="internal_estimate",
        ),
        document=document,
        revision=issued_revision,
    )

    generation.create_template_version(
        template_id="default-template",
        actor_id="tester",
        content="<html><body>v2 {{document_number}}</body></html>",
    )
    second = generation.render_document(
        request=RenderRequest(
            tenant_id=document.tenant_id,
            organization_id=document.organization_id,
            actor_id="tester",
            document_id=document.document_id,
            revision_number=issued_revision.revision_number,
            document_family=document.document_type.value,
            output_format=OutputFormat.HTML,
            presentation="internal_estimate",
        ),
        document=document,
        revision=issued_revision,
    )

    assert second.assignment.source.value == "revision_snapshot"
    assert (
        second.artifact.content_hash
        == issued_before_template_change.artifact.content_hash
    )


def test_transactions_export_records_generated_artifact_template_and_deterministic_hash() -> (
    None
):
    templates = [
        _template_payload(
            template_id="default-template",
            version_number=1,
            content="<html><body>{{document_number}}</body></html>",
            is_default=True,
            document_family="sales_order",
        )
    ]
    service = TransactionsWorkspaceService(serialized_document_templates=templates)
    document = service.create_draft(
        tenant_id="tenant-a",
        organization_id="org-a",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-1",
        customer_id="customer-1",
    )
    service._commercial_service.add_line(
        document,
        description="Hardware",
        quantity=Decimal("1"),
        unit_price=Decimal("99.00"),
    )

    first = service.export_document_pdf(
        document_id=document.document_id,
        presentation="sales_order",
        actor="tester",
    )
    second = service.export_document_pdf(
        document_id=document.document_id,
        presentation="sales_order",
        actor="tester",
    )

    assert first["content_hash"] == second["content_hash"]
    assert document.attachments
    latest_attachment = document.attachments[-1]
    assert latest_attachment["output_format"] == "pdf"
    assert "template_assignment" in latest_attachment
    assert document.export_activity[-1]["event"] == "document_generated"

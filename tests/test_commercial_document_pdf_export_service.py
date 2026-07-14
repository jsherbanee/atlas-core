from __future__ import annotations

from decimal import Decimal

from atlas_core.domain.commercial_document import CommercialDocumentType
from atlas_core.services.commercial_document_pdf_export_service import (
    CommercialDocumentPdfExportService,
    PdfSectionConfig,
)
from atlas_core.services.commercial_document_service import CommercialDocumentService


def test_pdf_export_is_deterministic_for_same_revision() -> None:
    document_service = CommercialDocumentService()
    pdf_service = CommercialDocumentPdfExportService()
    document = document_service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        project_id="project-1",
        project_code="P-1",
        customer_id="customer-1",
    )
    document_service.add_line(
        document,
        description="Speaker",
        quantity=Decimal("2"),
        unit_price=Decimal("150.00"),
    )
    document_service.allocate_number(document)
    document_service.assign_terms_and_conditions(
        document,
        reference={"block_id": "terms-estimate-v1", "version": 1, "source": "default"},
        snapshot={
            "block_id": "terms-estimate-v1",
            "version": 1,
            "content": "Net 30",
            "effective_date": "2026-01-01",
        },
    )

    revision = document.revisions[0]
    payload_1 = pdf_service.build_pdf_bytes(
        document=document,
        revision=revision,
        presentation="internal_estimate",
        section_config=PdfSectionConfig(),
        branding={"organization_name": "Atlas", "logo_reference": "atlas-logo"},
    )
    payload_2 = pdf_service.build_pdf_bytes(
        document=document,
        revision=revision,
        presentation="internal_estimate",
        section_config=PdfSectionConfig(),
        branding={"organization_name": "Atlas", "logo_reference": "atlas-logo"},
    )

    assert payload_1 == payload_2
    assert payload_1.startswith(b"%PDF-1.4")


def test_pdf_filename_includes_document_number_and_revision() -> None:
    document_service = CommercialDocumentService()
    pdf_service = CommercialDocumentPdfExportService()
    document = document_service.create_document(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        project_id="project-1",
        customer_id="customer-1",
    )
    document_service.allocate_number(document)

    file_name = pdf_service.suggested_filename(
        document=document,
        presentation="sales_order",
        revision_number=document.revision_number,
    )

    assert document.document_number is not None
    assert document.document_number in file_name
    assert f"-r{document.revision_number}-" in file_name
    assert file_name.endswith(".pdf")

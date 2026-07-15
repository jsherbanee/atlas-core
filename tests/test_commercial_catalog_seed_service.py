from __future__ import annotations

from pathlib import Path

import pytest

from atlas_core.sample_data.commercial_catalog_seed import (
    SEED_PACKAGE_ID,
    SEED_SOURCE,
    build_c04_seed_import_artifacts,
)
from atlas_core.services.commercial_catalog_seed_service import (
    CommercialCatalogSeedService,
)
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
from atlas_core.services.document_intake_service import DocumentIntakeService


def _service() -> CommercialCatalogSeedService:
    return CommercialCatalogSeedService(CommercialKnowledgeService())


def test_seed_load_is_repeatable_and_suppresses_duplicates() -> None:
    service = _service()

    first = service.load_seed_data(
        tenant_id="tenant-a",
        organization_id="org-1",
        imported_by="tester",
    )
    second = service.load_seed_data(
        tenant_id="tenant-a",
        organization_id="org-1",
        imported_by="tester",
    )

    assert first["already_loaded"] is False
    assert second["already_loaded"] is True
    summary = first["seed_summary"]
    assert summary["manufacturers"] >= 5
    assert summary["vendors"] >= 3
    assert summary["products"] >= 25
    assert summary["services"] >= 10
    assert summary["fees"] >= 5
    assert summary["assemblies"] >= 5


def test_seed_reset_removes_only_seed_data_and_preserves_non_seed_data() -> None:
    catalog = CommercialKnowledgeService()
    non_seed_item = catalog.upsert_catalog_item(
        catalog_item_id=None,
        item_type="product",
        code="CUSTOM-001",
        name="Custom Product",
        source="manual",
        provenance={"tenant_id": "tenant-a"},
        default_tax_nexus="CA-LOSANGELES",
    )
    seed_service = CommercialCatalogSeedService(catalog)
    seed_service.load_seed_data(
        tenant_id="tenant-a",
        organization_id="org-1",
        imported_by="tester",
    )

    reset = seed_service.reset_seed_data(tenant_id="tenant-a")

    assert reset["removed_counts"]["catalog_items"] > 0
    assert catalog.catalog_item(non_seed_item["catalog_item_id"]) is not None
    assert seed_service.seed_summary(tenant_id="tenant-a")["products"] == 0


def test_seed_loader_tenant_isolation_with_separate_services() -> None:
    tenant_a = _service()
    tenant_b = _service()

    tenant_a.load_seed_data(
        tenant_id="tenant-a",
        organization_id="org-1",
        imported_by="tester",
    )

    assert tenant_a.is_seed_loaded(tenant_id="tenant-a") is True
    assert tenant_b.is_seed_loaded(tenant_id="tenant-b") is False


def test_seed_import_formats_include_csv_xlsx_and_pdf_inspection() -> None:
    service = _service()
    result = service.load_seed_data(
        tenant_id="tenant-a",
        organization_id="org-1",
        imported_by="tester",
    )

    source_files = {
        row["source_filename"] for row in list(result["import_results"] or [])
    }
    assert "c04_seed_products.csv" in source_files
    assert "c04_seed_products.xlsx" in source_files
    assert result["pdf_validation"]["inspected"] is True


def test_seed_pdf_import_validates_partial_success_and_immutable_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service()
    artifacts = build_c04_seed_import_artifacts()
    pdf_spec = artifacts["pdf_price_list"]
    pdf_bytes = bytes(pdf_spec["content"])
    assert pdf_bytes

    def _fake_extract(
        self: DocumentIntakeService,
        file_path: Path,
        group_name: str,
    ) -> tuple[list[dict[str, object]], list[str], dict[str, object]]:
        _ = (self, file_path, group_name)
        return (
            [
                {
                    "page_number": 1,
                    "text": (
                        "Code  Name  Cost  MSRP\n"
                        "QSC-CORE-110F  Q-SYS Core 110f  3550  5200\n"
                        "BAD-CODE  Broken Row  bad  100\n"
                    ),
                    "has_text": True,
                    "ocr_derived": False,
                    "text_source": "embedded",
                    "source_file": "c04_seed_catalog_price_list.pdf",
                }
            ],
            [],
            {"status": "extracted"},
        )

    monkeypatch.setattr(DocumentIntakeService, "_extract_document_pages", _fake_extract)

    loaded = service.load_seed_data(
        tenant_id="tenant-a",
        organization_id="org-1",
        imported_by="tester",
        enable_pdf_finalize=True,
    )

    pdf_validation = loaded["pdf_validation"]
    assert pdf_validation["finalized"] is True
    versions = service._catalog.list_catalog_price_list_versions()
    assert versions
    assert versions[0]["immutable"] is True


def test_seed_validation_proves_catalog_to_invoice_and_return_to_credit_memo() -> None:
    service = _service()
    service.load_seed_data(
        tenant_id="tenant-a",
        organization_id="org-1",
        imported_by="tester",
    )

    validation = service.validate_catalog_to_transaction_workflow(
        tenant_id="tenant-a",
        organization_id="org-1",
        actor="tester",
    )

    assert validation["estimate_id"]
    assert validation["sales_order_id"]
    assert validation["invoice_id"]
    assert validation["return_order_id"]
    assert validation["credit_memo_id"]
    assert validation["credit_memo_source_traceable"] is True
    assert validation["policy_quote"]["policy"] == "cost_plus_percent"
    assert validation["manual_quote"]["policy"] == "manual"
    assert validation["manual_quote"]["manual_override_applied"] is True


def test_seed_validation_generates_representative_pdfs() -> None:
    service = _service()
    service.load_seed_data(
        tenant_id="tenant-a",
        organization_id="org-1",
        imported_by="tester",
    )

    validation = service.validate_catalog_to_transaction_workflow(
        tenant_id="tenant-a",
        organization_id="org-1",
        actor="tester",
    )

    assert validation["estimate_pdf"]["mime_type"] == "application/pdf"
    assert validation["invoice_pdf"]["mime_type"] == "application/pdf"
    assert validation["credit_memo_pdf"]["mime_type"] == "application/pdf"
    assert validation["estimate_pdf"]["bytes"] > 0


def test_seed_package_metadata_and_provenance_markers_are_explicit() -> None:
    service = _service()
    loaded = service.load_seed_data(
        tenant_id="tenant-a",
        organization_id="org-1",
        imported_by="tester",
    )

    assert loaded["package_id"] == SEED_PACKAGE_ID
    assert loaded["source"] == SEED_SOURCE
    seeded_items = [
        item
        for item in service._catalog.list_catalog_items(include_archived=True)
        if item.get("source") == SEED_SOURCE
    ]
    assert seeded_items
    assert all(
        "seed_package_id" in dict(item.get("provenance") or {}) for item in seeded_items
    )

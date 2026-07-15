from __future__ import annotations

import csv
import io
from decimal import Decimal
from pathlib import Path
import zipfile
import hashlib

import pytest

from atlas_core.domain.commercial_document import CommercialDocumentType
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
from atlas_core.services.document_intake_service import DocumentIntakeService
from atlas_core.services.settings_service import SettingsService
from atlas_core.services.transactions_workspace_service import (
    TransactionsWorkspaceService,
)


def _xlsx_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    values = [*headers]
    for row in rows:
        values.extend(row)
    unique_values: list[str] = []
    for value in values:
        if value not in unique_values:
            unique_values.append(value)
    shared_index = {value: index for index, value in enumerate(unique_values)}

    def _cell(value: str) -> str:
        return f'<c t="s"><v>{shared_index[value]}</v></c>'

    row_xml = []
    row_xml.append("<row>" + "".join(_cell(value) for value in headers) + "</row>")
    for row in rows:
        row_xml.append("<row>" + "".join(_cell(value) for value in row) + "</row>")

    shared_strings_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + "".join(f"<si><t>{value}</t></si>" for value in unique_values)
        + "</sst>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + "".join(row_xml) + "</sheetData>"
        "</worksheet>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        archive.writestr("xl/sharedStrings.xml", shared_strings_xml)
    return buffer.getvalue()


def test_catalog_item_crud_and_archive_restore() -> None:
    service = CommercialKnowledgeService()

    product = service.upsert_catalog_item(
        catalog_item_id=None,
        item_type="product",
        code="QSC-110F",
        name="Q-SYS Core 110f",
        manufacturer="QSC",
        vendor="AV Partner",
        cost=1200.0,
        msrp=2000.0,
        taxable=True,
        default_tax_nexus="CA-LOSANGELES",
    )
    service.upsert_catalog_item(
        catalog_item_id=None,
        item_type="service",
        code="INSTALL-STD",
        name="Standard Installation",
        taxable=False,
        manual_unit_price=250.0,
    )

    assert len(service.list_catalog_items()) == 2
    assert len(service.list_catalog_items(item_type="service")) == 1

    archived = service.archive_catalog_item(product["catalog_item_id"])
    assert archived["archived"] is True
    assert len(service.list_catalog_items()) == 1

    restored = service.restore_catalog_item(product["catalog_item_id"])
    assert restored["archived"] is False
    assert len(service.list_catalog_items()) == 2


def test_pricing_policy_and_manual_override_semantics() -> None:
    service = CommercialKnowledgeService()
    service.set_pricing_defaults(
        default_policy="cost_plus_percent",
        default_markup_percent=20.0,
        default_margin_percent=0.0,
        default_multiplier=1.0,
        rounding_policy="currency_2dp",
    )
    item = service.upsert_catalog_item(
        catalog_item_id=None,
        item_type="product",
        code="DSP-1",
        name="DSP",
        cost=100.0,
        msrp=180.0,
        map_price=150.0,
        taxable=True,
    )

    auto_quote = service.quote_catalog_item(
        catalog_item_id=item["catalog_item_id"],
        quantity=2,
    )
    override_quote = service.quote_catalog_item(
        catalog_item_id=item["catalog_item_id"],
        quantity=2,
        policy="msrp",
        manual_unit_price=160.0,
    )

    assert auto_quote["policy"] == "cost_plus_percent"
    assert auto_quote["unit_price"] == 120.0
    assert override_quote["policy"] == "manual"
    assert override_quote["manual_override_applied"] is True
    assert override_quote["unit_price"] == 160.0


def test_tax_nexus_rules_priority_compound_effective_and_exemption_flags() -> None:
    service = CommercialKnowledgeService()
    service.create_or_update_tax_nexus_rule(
        tax_rule_id=None,
        nexus="CA-LOSANGELES",
        title="State Tax",
        rate=7.5,
        priority=10,
        compound=False,
        taxable_item_types=["product", "service"],
        exemption_flags=[],
    )
    service.create_or_update_tax_nexus_rule(
        tax_rule_id=None,
        nexus="CA-LOSANGELES",
        title="City Tax",
        rate=2.5,
        priority=20,
        compound=True,
        taxable_item_types=["product"],
        exemption_flags=["resale"],
    )

    standard = service.tax_quote_for_line(
        nexus="CA-LOSANGELES",
        item_type="product",
        taxable_amount=100.0,
        exemption_flags=[],
    )
    exempt = service.tax_quote_for_line(
        nexus="CA-LOSANGELES",
        item_type="product",
        taxable_amount=100.0,
        exemption_flags=["resale"],
    )

    assert round(standard["tax_amount"], 2) == 10.19
    assert len(standard["applied_rules"]) == 2
    assert exempt["tax_amount"] == 7.5
    assert len(exempt["applied_rules"]) == 1


def test_catalog_import_supports_csv_and_xlsx_for_products() -> None:
    service = CommercialKnowledgeService()

    csv_buffer = io.StringIO()
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=["code", "name", "manufacturer", "vendor", "cost", "msrp"],
    )
    writer.writeheader()
    writer.writerow(
        {
            "code": "AMP-100",
            "name": "Amplifier 100",
            "manufacturer": "QSC",
            "vendor": "AV Partner",
            "cost": "500",
            "msrp": "900",
        }
    )
    csv_summary = service.import_catalog_entities(
        source_filename="products.csv",
        file_bytes=csv_buffer.getvalue().encode("utf-8"),
        entity_type="products",
        imported_by="tester",
    )

    xlsx_bytes = _xlsx_bytes(
        headers=["code", "name", "manufacturer", "vendor", "cost", "msrp"],
        rows=[["AMP-200", "Amplifier 200", "QSC", "AV Partner", "700", "1200"]],
    )
    xlsx_summary = service.import_catalog_entities(
        source_filename="products.xlsx",
        file_bytes=xlsx_bytes,
        entity_type="products",
        imported_by="tester",
    )

    codes = {item["code"] for item in service.list_catalog_items(item_type="product")}
    assert csv_summary["inserted"] == 1
    assert xlsx_summary["inserted"] == 1
    assert "AMP-100" in codes
    assert "AMP-200" in codes


def test_import_supports_manufacturers_and_vendors() -> None:
    service = CommercialKnowledgeService()

    summary_mfr = service.import_catalog_entities_from_rows(
        entity_type="manufacturers",
        rows=[{"manufacturer_code": "QSC", "manufacturer_name": "QSC Audio"}],
        imported_by="tester",
        source_filename="manufacturers.csv",
    )
    summary_vendor = service.import_catalog_entities_from_rows(
        entity_type="vendors",
        rows=[
            {
                "vendor_code": "AVP",
                "vendor_name": "AV Partner",
                "vendor_type": "distributor",
            }
        ],
        imported_by="tester",
        source_filename="vendors.csv",
    )

    assert summary_mfr["inserted"] == 1
    assert summary_vendor["inserted"] == 1
    assert service.to_dict()["manufacturers"]["QSC"]["manufacturer_name"] == "QSC Audio"
    assert service.to_dict()["vendors"]["AVP"]["vendor_name"] == "AV Partner"


def test_settings_commercial_defaults_are_tenant_scoped() -> None:
    service = SettingsService()
    updated = service.update_organization_commercial_defaults(
        tenant_id="tenant-a",
        organization_id="org-1",
        actor="tester",
        updates={
            "default_pricing_policy": "margin_percent",
            "default_margin_percent": "35",
            "default_tax_nexus": "CA-LOSANGELES",
            "currency": "USD",
            "rounding_policy": "currency_2dp",
        },
    )

    other = service.organization_commercial_defaults(
        tenant_id="tenant-b",
        organization_id="org-1",
    )

    assert updated.default_pricing_policy == "margin_percent"
    assert updated.default_tax_nexus == "CA-LOSANGELES"
    assert other.default_pricing_policy == "manual"


def test_transactions_add_catalog_line_preserves_manual_lines() -> None:
    catalog = CommercialKnowledgeService()
    catalog_item = catalog.upsert_catalog_item(
        catalog_item_id=None,
        item_type="service",
        code="LABOR-STD",
        name="Labor",
        manual_unit_price=150.0,
        taxable=False,
    )

    workspace = TransactionsWorkspaceService(
        enforce_active_scope=False,
        commercial_catalog_service=catalog,
    )
    document = workspace.create_draft(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.SALES_ORDER,
        customer_id="customer-1",
    )

    workspace._commercial_service.add_line(
        document,
        description="Manual line",
        quantity=Decimal("1"),
        unit_price=Decimal("50"),
    )
    workspace.add_catalog_line(
        document_id=document.document_id,
        catalog_item_id=catalog_item["catalog_item_id"],
        quantity=Decimal("2"),
    )

    assert len(document.lines) == 2
    assert document.lines[0].description == "Manual line"
    assert document.lines[1].line_metadata is not None
    assert (
        document.lines[1].line_metadata["catalog"]["catalog_item_id"]
        == catalog_item["catalog_item_id"]
    )
    assert document.lines[1].line_metadata["catalog"]["pricing_policy"] == "manual"


def test_transactions_return_order_catalog_line_contains_return_metadata() -> None:
    catalog = CommercialKnowledgeService()
    item = catalog.upsert_catalog_item(
        catalog_item_id=None,
        item_type="product",
        code="RET-100",
        name="Returnable Product",
        cost=60.0,
        manual_unit_price=100.0,
    )

    workspace = TransactionsWorkspaceService(
        enforce_active_scope=False,
        commercial_catalog_service=catalog,
    )
    document = workspace.create_return_order(
        tenant_id="tenant-a",
        organization_id="org-1",
        customer_id="customer-1",
    )

    workspace.add_catalog_line(
        document_id=document.document_id,
        catalog_item_id=item["catalog_item_id"],
        quantity=Decimal("1"),
    )

    metadata = document.lines[0].line_metadata
    assert metadata is not None
    assert metadata["line_type"] == "product"
    assert metadata["requested_return_quantity"] == "1"
    assert metadata["approved_return_quantity"] == "1"
    assert document.document_metadata is not None
    assert Decimal(document.document_metadata["approved_credit_amount"]) > Decimal("0")


def test_assembly_versioning_rollups_and_expansion_with_nested_components() -> None:
    service = CommercialKnowledgeService()
    amp = service.upsert_catalog_item(
        catalog_item_id=None,
        item_type="product",
        code="AMP-A",
        name="Amplifier",
        cost=500.0,
        default_sales_price=800.0,
    )
    labor = service.upsert_catalog_item(
        catalog_item_id=None,
        item_type="service",
        code="LAB-A",
        name="Labor",
        cost=100.0,
        default_sales_price=200.0,
    )
    sub_assembly = service.upsert_catalog_item(
        catalog_item_id=None,
        item_type="assembly",
        code="SUB-1",
        name="Sub Assembly",
    )
    main_assembly = service.upsert_catalog_item(
        catalog_item_id=None,
        item_type="assembly",
        code="MAIN-1",
        name="Main Assembly",
    )

    service.create_or_update_assembly_version(
        assembly_item_id=sub_assembly["catalog_item_id"],
        components=[
            {
                "component_item_id": amp["catalog_item_id"],
                "quantity": 1,
                "required": True,
                "sequence": 1,
            }
        ],
    )
    version = service.create_or_update_assembly_version(
        assembly_item_id=main_assembly["catalog_item_id"],
        components=[
            {
                "component_item_id": sub_assembly["catalog_item_id"],
                "quantity": 2,
                "required": True,
                "sequence": 1,
            },
            {
                "component_item_id": labor["catalog_item_id"],
                "quantity": 1,
                "required": True,
                "sequence": 2,
            },
        ],
    )

    expanded = service.expand_assembly(
        assembly_item_id=main_assembly["catalog_item_id"],
        quantity=1,
    )

    assert version["version_number"] == 1
    assert round(version["total_cost"], 2) == 1100.0
    assert round(version["total_sales_price"], 2) == 1800.0
    assert len(expanded["components"]) == 2
    assert round(expanded["total_cost"], 2) == 1100.0
    assert round(expanded["total_sales_price"], 2) == 1800.0


def test_assembly_cycle_prevention_rejects_circular_references() -> None:
    service = CommercialKnowledgeService()
    a = service.upsert_catalog_item(
        catalog_item_id=None,
        item_type="assembly",
        code="ASM-A",
        name="Assembly A",
    )
    b = service.upsert_catalog_item(
        catalog_item_id=None,
        item_type="assembly",
        code="ASM-B",
        name="Assembly B",
    )

    service.create_or_update_assembly_version(
        assembly_item_id=b["catalog_item_id"],
        components=[
            {
                "component_item_id": a["catalog_item_id"],
                "quantity": 1,
                "required": True,
                "sequence": 1,
            }
        ],
    )
    with pytest.raises(ValueError, match="circular"):
        service.create_or_update_assembly_version(
            assembly_item_id=a["catalog_item_id"],
            components=[
                {
                    "component_item_id": b["catalog_item_id"],
                    "quantity": 1,
                    "required": True,
                    "sequence": 1,
                }
            ],
        )


def test_import_supports_assemblies_and_components_rows() -> None:
    service = CommercialKnowledgeService()
    service.import_catalog_entities_from_rows(
        entity_type="products",
        rows=[{"code": "SPK-1", "name": "Speaker", "cost": "100"}],
        imported_by="tester",
        source_filename="products.csv",
    )
    service.import_catalog_entities_from_rows(
        entity_type="assemblies",
        rows=[{"code": "KIT-1", "name": "Kit 1"}],
        imported_by="tester",
        source_filename="assemblies.csv",
    )
    component_summary = service.import_catalog_entities_from_rows(
        entity_type="assembly_components",
        rows=[
            {
                "assembly_code": "KIT-1",
                "component_code": "SPK-1",
                "quantity": 2,
                "required": "true",
                "sequence": 1,
            }
        ],
        imported_by="tester",
        source_filename="assembly_components.csv",
    )

    assembly_id = service._catalog_item_id("assembly", "KIT-1")
    latest = service.latest_assembly_version(assembly_id)
    assert component_summary["inserted"] == 1
    assert latest is not None
    assert latest["component_count"] == 1


def test_pdf_price_list_preview_and_finalize_partial_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CommercialKnowledgeService()
    fixture_path = Path(__file__).parent / "fixtures" / "simple.pdf"
    pdf_bytes = fixture_path.read_bytes()

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
                        "AMP-100  Amplifier  500  900\n"
                        "BAD-1  Broken  bad-value  100\n"
                    ),
                    "has_text": True,
                    "ocr_derived": False,
                    "text_source": "embedded",
                    "source_file": "simple.pdf",
                }
            ],
            [],
            {"status": "extracted"},
        )

    monkeypatch.setattr(DocumentIntakeService, "_extract_document_pages", _fake_extract)
    inspected = service.inspect_catalog_pdf_price_list(
        source_filename="simple.pdf",
        file_bytes=pdf_bytes,
    )
    candidate = list(inspected.get("table_candidates") or [])[0]

    preview = service.preview_catalog_pdf_price_list_import(
        source_filename="simple.pdf",
        file_bytes=pdf_bytes,
        selected_pages=[1],
        table_candidate_id=str(candidate.get("candidate_id")),
        header_row_index=0,
        column_mapping={
            "code": "Code",
            "name": "Name",
            "cost": "Cost",
            "msrp": "MSRP",
        },
        imported_by="tester",
    )
    finalized = service.finalize_catalog_pdf_price_list_import(
        preview_id=preview["preview_id"],
        imported_by="tester",
    )

    assert len(preview["accepted_rows"]) == 1
    assert len(preview["rejected_rows"]) == 1
    assert finalized["partial_success"] is True
    assert finalized["inserted"] == 1
    assert "row_number" in finalized["rejected_rows_csv"]
    versions = service.list_catalog_price_list_versions()
    assert versions
    assert versions[0]["source_hash"] == hashlib.sha1(pdf_bytes).hexdigest()


def test_transactions_add_assembly_lines_grouped_and_credit_memo_support() -> None:
    catalog = CommercialKnowledgeService()
    component = catalog.upsert_catalog_item(
        catalog_item_id=None,
        item_type="product",
        code="CMP-1",
        name="Component",
        cost=10.0,
        default_sales_price=20.0,
    )
    assembly = catalog.upsert_catalog_item(
        catalog_item_id=None,
        item_type="assembly",
        code="ASM-1",
        name="Assembly",
        default_sales_price=100.0,
    )
    catalog.create_or_update_assembly_version(
        assembly_item_id=assembly["catalog_item_id"],
        components=[
            {
                "component_item_id": component["catalog_item_id"],
                "quantity": 2,
                "required": True,
                "sequence": 1,
            }
        ],
    )

    workspace = TransactionsWorkspaceService(
        enforce_active_scope=False,
        commercial_catalog_service=catalog,
    )
    estimate = workspace.create_draft(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.ESTIMATE,
        customer_id="customer-1",
    )
    workspace.add_catalog_line(
        document_id=estimate.document_id,
        catalog_item_id=assembly["catalog_item_id"],
        quantity=Decimal("1"),
        assembly_mode="grouped",
    )
    assert len(estimate.lines) == 2
    assert estimate.lines[0].line_metadata is not None
    assert estimate.lines[0].line_metadata["line_type"] == "assembly"
    assert estimate.lines[1].line_metadata is not None
    assert estimate.lines[1].line_metadata["assembly_component"] is True

    credit_memo = workspace.create_draft(
        tenant_id="tenant-a",
        organization_id="org-1",
        document_type=CommercialDocumentType.CREDIT_MEMO,
        customer_id="customer-1",
    )
    workspace.add_catalog_line(
        document_id=credit_memo.document_id,
        catalog_item_id=component["catalog_item_id"],
        quantity=Decimal("1"),
    )
    assert len(credit_memo.lines) == 1

from __future__ import annotations

import csv
import io
from decimal import Decimal
import zipfile

from atlas_core.domain.commercial_document import CommercialDocumentType
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
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

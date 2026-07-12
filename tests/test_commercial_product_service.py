import io
import zipfile

import pytest

from atlas_core.domain.commercial_product import ProductLifecycleStatus
from atlas_core.services.master_library import CommercialProductService


def _simple_xlsx_bytes() -> bytes:
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
    package_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
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
        "</Types>"
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        '<row r="1">'
        '<c r="A1" t="inlineStr"><is><t>Manufacturer Part Number</t></is></c>'
        '<c r="B1" t="inlineStr"><is><t>Vendor SKU</t></is></c>'
        '<c r="C1" t="inlineStr"><is><t>Description</t></is></c>'
        '<c r="D1" t="inlineStr"><is><t>Unit Cost</t></is></c>'
        '<c r="E1" t="inlineStr"><is><t>List Price</t></is></c>'
        "</row>"
        '<row r="2">'
        '<c r="A2" t="inlineStr"><is><t>CORE-110F</t></is></c>'
        '<c r="B2" t="inlineStr"><is><t>AVP-CORE110F</t></is></c>'
        '<c r="C2" t="inlineStr"><is><t>Network DSP core</t></is></c>'
        '<c r="D2"><v>1200</v></c>'
        '<c r="E2"><v>2999</v></c>'
        "</row>"
        "</sheetData>"
        "</worksheet>"
    )

    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", package_rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return output.getvalue()


def _rows(cost_a: float = 1200.0, cost_b: float = 800.0) -> list[dict[str, object]]:
    return [
        {
            "vendor": "AV Partner",
            "manufacturer": "QSC",
            "manufacturer_sku": "Core 110f",
            "canonical_sku": "CORE-110F",
            "alternate_skus": ["CORE110F", "QSC-110F"],
            "description": "Network DSP core",
            "product_family": "Q-SYS Core",
            "category": "dsp",
            "discipline": "audio",
            "lifecycle_status": ProductLifecycleStatus.ACTIVE.value,
            "preferred_cost": cost_a,
            "msrp": 2999.0,
            "map": 2799.0,
            "preferred_vendor": "AV Partner",
            "vendor_sku": "AVP-CORE110F",
            "vendor_type": "distributor",
            "availability_status": "in_stock",
            "lead_time": "2 weeks",
            "effective_date": "2026-01-01",
            "date_verified": "2026-01-05",
        },
        {
            "vendor": "Integrator Supply",
            "manufacturer": "Shure",
            "manufacturer_sku": "ULX-D4Q",
            "canonical_sku": "ULXD4Q",
            "alternate_skus": ["ULX D4Q"],
            "description": "Wireless receiver",
            "product_family": "ULX-D",
            "category": "microphone",
            "discipline": "audio",
            "lifecycle_status": ProductLifecycleStatus.NEW.value,
            "preferred_cost": cost_b,
            "msrp": 1899.0,
            "preferred_vendor": "Integrator Supply",
            "vendor_sku": "INT-ULXD4Q",
            "vendor_type": "distributor",
            "availability_status": "limited",
            "lead_time": "6 weeks",
            "effective_date": "2026-01-01",
            "date_verified": "2026-01-07",
        },
    ]


def test_import_price_list_versions_create_immutable_records_and_price_history() -> (
    None
):
    service = CommercialProductService()

    first = service.import_price_list_version(
        manufacturer="QSC",
        vendor="AV Partner",
        source_file="qsc_v1.csv",
        file_bytes=b"v1",
        import_user="tester",
        rows=[_rows()[0]],
        effective_date="2026-01-01",
    )
    second = service.import_price_list_version(
        manufacturer="QSC",
        vendor="AV Partner",
        source_file="qsc_v2.csv",
        file_bytes=b"v2",
        import_user="tester",
        rows=[_rows(cost_a=1350.0)[0]],
        effective_date="2026-02-01",
    )

    assert first["version"]["version_id"] != second["version"]["version_id"]
    state = service.to_dict()
    assert len(state["price_list_versions"]) == 2

    product_rows = service.product_rows()
    assert len(product_rows) == 1
    row = product_rows[0]
    assert len(row["price_history"]) == 2
    assert row["price_history"][1]["dollar_difference"] == 150.0


def test_dashboard_summary_reports_required_product_health_metrics() -> None:
    service = CommercialProductService()
    service.import_price_list_version(
        manufacturer="Mixed",
        vendor="Atlas Vendor",
        source_file="mixed.csv",
        file_bytes=b"mixed",
        import_user="tester",
        rows=_rows(),
        effective_date="2026-01-01",
    )

    dashboard = service.dashboard_summary()
    assert dashboard["active_products"] >= 1
    assert "missing_pricing" in dashboard
    assert "stale_pricing" in dashboard
    assert "missing_preferred_vendor" in dashboard
    assert "recent_price_changes" in dashboard
    assert "average_confidence" in dashboard


def test_project_only_product_can_be_added_and_promoted() -> None:
    service = CommercialProductService()
    added = service.add_project_only_product(
        project_id="proj-123",
        manufacturer="Sony",
        model="BRC-X1000",
        description="Project-only camera",
        vendor="Field Source",
        vendor_type="local",
        cost=2200.0,
        source="manual_add",
    )

    assert added["project_only"] is True
    promotion = service.promote_project_only_product(
        project_id="proj-123",
        atlas_product_uuid=added["atlas_product_uuid"],
        vendor="Field Source",
        vendor_type="local",
        import_user="tester",
    )

    assert promotion["promoted_product_uuid"] == added["atlas_product_uuid"]
    assert promotion["import_result"]["version"]["products_added"] >= 1


def _foundation_service() -> CommercialProductService:
    service = CommercialProductService()
    service.create_manufacturer(
        manufacturer_id="mfr-qsc",
        canonical_name="QSC",
        display_name="QSC",
        manufacturer_code="QSC",
    )
    service.create_manufacturer(
        manufacturer_id="mfr-shure",
        canonical_name="Shure",
        display_name="Shure",
        manufacturer_code="SHURE",
    )
    service.create_vendor(
        vendor_id="vendor-avp",
        canonical_name="AV Partner",
        display_name="AV Partner",
        vendor_code="AVP",
    )
    service.create_vendor(
        vendor_id="vendor-int",
        canonical_name="Integrator Supply",
        display_name="Integrator Supply",
        vendor_code="INT",
    )
    return service


def test_manufacturer_and_vendor_duplicate_detection_is_conservative() -> None:
    service = CommercialProductService()
    service.create_manufacturer(manufacturer_id="mfr-1", canonical_name="QSC")
    with pytest.raises(ValueError, match="Duplicate manufacturer"):
        service.create_manufacturer(manufacturer_id="mfr-2", canonical_name="qsc")

    service.create_vendor(vendor_id="vendor-1", canonical_name="AV Partner")
    with pytest.raises(ValueError, match="Duplicate vendor"):
        service.create_vendor(vendor_id="vendor-2", canonical_name="AV PARTNER")


def test_product_uniqueness_is_by_manufacturer_and_normalized_part_number() -> None:
    service = _foundation_service()
    product = service.create_product(
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        manufacturer_part_number="Core-110F",
        product_name="Core 110f",
        product_description="DSP",
        category="dsp",
    )
    assert product["normalized_manufacturer_part_number"] == "CORE-110F"

    with pytest.raises(ValueError, match="Duplicate product identity"):
        service.create_product(
            manufacturer_id="mfr-qsc",
            manufacturer="QSC",
            manufacturer_part_number="core-110f",
            product_name="Core 110f Duplicate",
            product_description="DSP",
            category="dsp",
        )


def test_replacement_cycle_is_rejected() -> None:
    service = _foundation_service()
    p1 = service.create_product(
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        manufacturer_part_number="QSC-1",
        product_name="P1",
        product_description="P1",
        category="dsp",
    )
    p2 = service.create_product(
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        manufacturer_part_number="QSC-2",
        product_name="P2",
        product_description="P2",
        category="dsp",
    )
    p3 = service.create_product(
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        manufacturer_part_number="QSC-3",
        product_name="P3",
        product_description="P3",
        category="dsp",
    )

    service.assign_replacement_product(
        atlas_product_uuid=p1["atlas_product_uuid"],
        replacement_product_uuid=p2["atlas_product_uuid"],
    )
    service.assign_replacement_product(
        atlas_product_uuid=p2["atlas_product_uuid"],
        replacement_product_uuid=p3["atlas_product_uuid"],
    )
    with pytest.raises(ValueError, match="cycle"):
        service.assign_replacement_product(
            atlas_product_uuid=p3["atlas_product_uuid"],
            replacement_product_uuid=p1["atlas_product_uuid"],
        )


def test_vendor_offerings_support_multi_vendor_and_channel_validation() -> None:
    service = _foundation_service()
    product = service.create_product(
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        manufacturer_part_number="QSC-CORE-X",
        product_name="Core X",
        product_description="DSP",
        category="dsp",
    )

    first = service.create_vendor_offering(
        vendor_id="vendor-avp",
        vendor="AV Partner",
        atlas_product_uuid=product["atlas_product_uuid"],
        vendor_sku="AVP-COREX",
        purchasing_channel="distributor",
        direct_from_manufacturer=False,
        authorization_status="unknown",
        minimum_order_quantity=1,
        order_multiple=1,
        unit_of_measure="ea",
        pack_quantity=1,
        lead_time_notes="stocked",
    )
    second = service.create_vendor_offering(
        vendor_id="vendor-int",
        vendor="Integrator Supply",
        atlas_product_uuid=product["atlas_product_uuid"],
        vendor_sku="INT-COREX",
        purchasing_channel="dealer_reseller",
        direct_from_manufacturer=False,
        authorization_status="unknown",
        minimum_order_quantity=1,
        order_multiple=1,
        unit_of_measure="ea",
        pack_quantity=1,
        lead_time_notes="order",
    )
    assert first["vendor_offering_id"] != second["vendor_offering_id"]

    with pytest.raises(ValueError, match="Invalid purchasing channel"):
        service.create_vendor_offering(
            vendor_id="vendor-avp",
            vendor="AV Partner",
            atlas_product_uuid=product["atlas_product_uuid"],
            vendor_sku="AVP-BAD",
            purchasing_channel="invalid-channel",
            direct_from_manufacturer=False,
            authorization_status="unknown",
            minimum_order_quantity=1,
            order_multiple=1,
            unit_of_measure="ea",
            pack_quantity=1,
            lead_time_notes="",
        )


def test_price_sheet_version_and_record_immutability() -> None:
    service = _foundation_service()
    sheet = service.create_price_sheet(
        name="QSC Distributor List",
        vendor_id="vendor-avp",
        vendor="AV Partner",
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        purchasing_channel="distributor",
        currency="USD",
    )
    version = service.create_price_sheet_version(
        price_sheet_id=sheet["price_sheet_id"],
        version_label="v1",
        effective_date="2026-01-01",
        expiration_date="2026-12-31",
        source_filename="qsc_v1.csv",
        source_metadata="manual",
        source_hash="abc",
        import_status="finalized",
        record_count=1,
        imported_by="tester",
    )
    with pytest.raises(ValueError, match="immutable"):
        service.update_price_sheet_version(
            version["version_id"],
            updates={"version_label": "v1a"},
        )

    record = service.create_price_record(
        price_sheet_version_id=version["version_id"],
        vendor_offering_id="",
        atlas_product_uuid="",
        manufacturer_part_number_imported="CORE-110F",
        vendor_sku_imported="AVP-CORE110F",
        description_imported="Core",
        unit_cost=1200.0,
        list_price=2000.0,
        currency="USD",
        unit_of_measure="ea",
        pack_quantity=1,
        minimum_order_quantity=1,
        effective_date_override="2026-01-01",
        resolution_status="unresolved",
        source_row_reference="1",
        finalized=True,
    )
    with pytest.raises(ValueError, match="immutable"):
        service.update_price_record(
            record["price_record_id"],
            updates={"description_imported": "Updated"},
        )


def test_manual_single_sku_workflow_without_price_sheet_import() -> None:
    service = _foundation_service()
    product = service.create_product(
        manufacturer_id="mfr-shure",
        manufacturer="Shure",
        manufacturer_part_number="ULXD4Q",
        product_name="ULX-D4Q",
        product_description="Wireless receiver",
        category="microphone",
    )
    offering = service.create_vendor_offering(
        vendor_id="vendor-int",
        vendor="Integrator Supply",
        atlas_product_uuid=product["atlas_product_uuid"],
        vendor_sku="INT-ULXD4Q",
        purchasing_channel="dealer_reseller",
        direct_from_manufacturer=False,
        authorization_status="unknown",
        minimum_order_quantity=1,
        order_multiple=1,
        unit_of_measure="ea",
        pack_quantity=1,
        lead_time_notes="manual",
    )

    assert product["manufacturer_part_number"] == "ULXD4Q"
    assert offering["pricing_available"] is False
    assert service.list_price_sheets() == []


def test_c02_import_draft_lifecycle_requires_warning_ack_before_finalize() -> None:
    service = _foundation_service()
    sheet = service.create_price_sheet(
        name="QSC AVP List",
        vendor_id="vendor-avp",
        vendor="AV Partner",
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        purchasing_channel="distributor",
        currency="USD",
    )

    csv_bytes = (
        "Manufacturer Part Number,Vendor SKU,Description,Unit Cost,List Price\n"
        "CORE-110F,AVP-CORE110F,Network DSP core,1200,2999\n"
    ).encode("utf-8")
    parsed = service.parse_import_source(
        source_filename="qsc_v1.csv",
        file_bytes=csv_bytes,
    )
    mapping = service.suggest_column_mapping(list(parsed.get("headers") or []))
    draft = service.create_import_draft(
        price_sheet_id=sheet["price_sheet_id"],
        source_filename="qsc_v1.csv",
        file_bytes=csv_bytes,
        version_label="v1",
        effective_date="2026-01-01",
        expiration_date="",
        currency="USD",
        worksheet=None,
        header_row_index=0,
        column_mapping=mapping,
        imported_by="tester",
    )

    assert draft["status"] == "validated"
    assert draft["unresolved_count"] == 1
    with pytest.raises(ValueError, match="acknowledge warnings"):
        service.validate_price_sheet_draft(
            draft["draft_id"], acknowledge_warnings=False
        )

    validated = service.validate_price_sheet_draft(
        draft["draft_id"], acknowledge_warnings=True
    )
    finalized = service.finalize_price_sheet_draft(
        validated["draft_id"],
        imported_by="tester",
    )
    assert finalized["version"]["import_status"] == "finalized"
    assert len(finalized["records"]) == 1

    with pytest.raises(ValueError, match="immutable"):
        service.add_manual_price_record_to_draft(
            validated["draft_id"],
            manufacturer_part_number_imported="X",
            vendor_sku_imported="Y",
            description_imported="Late edit",
            unit_cost=10.0,
            list_price=20.0,
        )


def test_c02_finalize_can_block_duplicate_source_hash() -> None:
    service = _foundation_service()
    sheet = service.create_price_sheet(
        name="QSC AVP List",
        vendor_id="vendor-avp",
        vendor="AV Partner",
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        purchasing_channel="distributor",
        currency="USD",
    )
    csv_bytes = (
        "Manufacturer Part Number,Vendor SKU,Description,Unit Cost,List Price\n"
        "CORE-110F,AVP-CORE110F,Network DSP core,1200,2999\n"
    ).encode("utf-8")
    mapping = {
        "manufacturer_part_number": "Manufacturer Part Number",
        "vendor_sku": "Vendor SKU",
        "description": "Description",
        "unit_cost": "Unit Cost",
        "list_price": "List Price",
    }

    first = service.create_import_draft(
        price_sheet_id=sheet["price_sheet_id"],
        source_filename="qsc_v1.csv",
        file_bytes=csv_bytes,
        version_label="v1",
        effective_date="2026-01-01",
        expiration_date="",
        currency="USD",
        worksheet=None,
        header_row_index=0,
        column_mapping=mapping,
        imported_by="tester",
    )
    service.validate_price_sheet_draft(first["draft_id"], acknowledge_warnings=True)
    service.finalize_price_sheet_draft(first["draft_id"], imported_by="tester")

    second = service.create_import_draft(
        price_sheet_id=sheet["price_sheet_id"],
        source_filename="qsc_v1.csv",
        file_bytes=csv_bytes,
        version_label="v2",
        effective_date="2026-02-01",
        expiration_date="",
        currency="USD",
        worksheet=None,
        header_row_index=0,
        column_mapping=mapping,
        imported_by="tester",
    )
    service.validate_price_sheet_draft(second["draft_id"], acknowledge_warnings=True)
    with pytest.raises(ValueError, match="Duplicate source hash"):
        service.finalize_price_sheet_draft(
            second["draft_id"],
            imported_by="tester",
            block_duplicate_hash=True,
        )


def test_c02_completeness_summary_counts_pending_drafts() -> None:
    service = _foundation_service()
    sheet = service.create_price_sheet(
        name="Shure INT List",
        vendor_id="vendor-int",
        vendor="Integrator Supply",
        manufacturer_id="mfr-shure",
        manufacturer="Shure",
        purchasing_channel="dealer_reseller",
        currency="USD",
    )
    service.create_manual_draft_version(
        price_sheet_id=sheet["price_sheet_id"],
        version_label="manual-v1",
        effective_date="2026-01-01",
        currency="USD",
        imported_by="tester",
    )

    summary = service.commercial_completeness_summary()
    assert summary["price_sheets_total"] >= 1
    assert summary["price_sheets_with_pending_drafts"] >= 1


def test_c02_create_import_draft_accepts_valid_xlsx_source() -> None:
    service = _foundation_service()
    sheet = service.create_price_sheet(
        name="QSC AVP XLSX",
        vendor_id="vendor-avp",
        vendor="AV Partner",
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        purchasing_channel="distributor",
        currency="USD",
    )
    xlsx_bytes = _simple_xlsx_bytes()

    parsed = service.parse_import_source(
        source_filename="qsc_v1.xlsx",
        file_bytes=xlsx_bytes,
        worksheet="Sheet1",
        header_row_index=0,
    )
    mapping = service.suggest_column_mapping(list(parsed.get("headers") or []))

    draft = service.create_import_draft(
        price_sheet_id=sheet["price_sheet_id"],
        source_filename="qsc_v1.xlsx",
        file_bytes=xlsx_bytes,
        version_label="xlsx-v1",
        effective_date="2026-01-01",
        expiration_date="",
        currency="USD",
        worksheet="Sheet1",
        header_row_index=0,
        column_mapping=mapping,
        imported_by="tester",
    )

    assert draft["source_filename"] == "qsc_v1.xlsx"
    assert draft["record_count"] == 1
    assert draft["status"] == "validated"


def test_c02_unresolved_record_filters_are_applied() -> None:
    service = _foundation_service()
    sheet = service.create_price_sheet(
        name="QSC AVP List",
        vendor_id="vendor-avp",
        vendor="AV Partner",
        manufacturer_id="mfr-qsc",
        manufacturer="QSC",
        purchasing_channel="distributor",
        currency="USD",
    )
    csv_bytes = (
        "Manufacturer Part Number,Vendor SKU,Description,Unit Cost,List Price\n"
        "CORE-110F,AVP-CORE110F,Network DSP core,1200,2999\n"
    ).encode("utf-8")
    mapping = {
        "manufacturer_part_number": "Manufacturer Part Number",
        "vendor_sku": "Vendor SKU",
        "description": "Description",
        "unit_cost": "Unit Cost",
        "list_price": "List Price",
    }

    draft = service.create_import_draft(
        price_sheet_id=sheet["price_sheet_id"],
        source_filename="qsc_v1.csv",
        file_bytes=csv_bytes,
        version_label="v1",
        effective_date="2026-01-01",
        expiration_date="",
        currency="USD",
        worksheet=None,
        header_row_index=0,
        column_mapping=mapping,
        imported_by="tester",
    )
    service.validate_price_sheet_draft(draft["draft_id"], acknowledge_warnings=True)
    finalized = service.finalize_price_sheet_draft(
        draft["draft_id"], imported_by="tester"
    )
    version_id = str(dict(finalized.get("version") or {}).get("version_id") or "")

    all_unresolved = service.unresolved_price_records()
    filtered = service.unresolved_price_records(
        version_id=version_id,
        missing_product=True,
        missing_vendor_offering=True,
    )

    assert all_unresolved
    assert filtered
    assert all(row.get("price_sheet_version_id") == version_id for row in filtered)
    assert all(not row.get("atlas_product_uuid") for row in filtered)
    assert all(not row.get("vendor_offering_id") for row in filtered)

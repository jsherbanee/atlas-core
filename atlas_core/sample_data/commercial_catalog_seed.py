"""C-04 commercial catalog seed package builders.

This module provides deterministic non-production sample data for tenant-scoped
catalog seeding and import validation.
"""

from __future__ import annotations

import csv
import io
from typing import Any
import zipfile

from pypdf import PdfWriter

SEED_PACKAGE_ID = "atlas-c04-alpha-seed-v1"
SEED_SOURCE = "seed_c04_alpha"
SEED_SOURCE_PREFIX = "c04_seed"


def build_c04_seed_payload() -> dict[str, Any]:
    manufacturers = [
        {
            "manufacturer_code": "QSC",
            "manufacturer_name": "QSC Systems Demo",
            "website": "https://example.invalid/qsc",
            "status": "active",
            "source": SEED_SOURCE,
        },
        {
            "manufacturer_code": "SHURE",
            "manufacturer_name": "Shure Sample Labs",
            "website": "https://example.invalid/shure",
            "status": "active",
            "source": SEED_SOURCE,
        },
        {
            "manufacturer_code": "SONY",
            "manufacturer_name": "Sony AV Demo",
            "website": "https://example.invalid/sony",
            "status": "active",
            "source": SEED_SOURCE,
        },
        {
            "manufacturer_code": "EPSON",
            "manufacturer_name": "Epson Projection Sample",
            "website": "https://example.invalid/epson",
            "status": "active",
            "source": SEED_SOURCE,
        },
        {
            "manufacturer_code": "CHIEF",
            "manufacturer_name": "Chief Mounting Demo",
            "website": "https://example.invalid/chief",
            "status": "active",
            "source": SEED_SOURCE,
        },
    ]

    vendors = [
        {
            "vendor_code": "MIDWICH",
            "vendor_name": "Midwich Demo Distribution",
            "vendor_type": "distributor",
            "status": "active",
            "source": SEED_SOURCE,
        },
        {
            "vendor_code": "ALMO",
            "vendor_name": "Exertis Almo Demo",
            "vendor_type": "distributor",
            "status": "active",
            "source": SEED_SOURCE,
        },
        {
            "vendor_code": "DIRECT",
            "vendor_name": "Manufacturer Direct Demo",
            "vendor_type": "manufacturer_direct",
            "status": "active",
            "source": SEED_SOURCE,
        },
    ]

    products = [
        _product(
            "QSC-CORE-110F", "Q-SYS Core 110f", "QSC", "MIDWICH", 3550, 5200, 4999
        ),
        _product("QSC-NC-12X80", "Q-SYS NC-12x80", "QSC", "MIDWICH", 1190, 1899, 1799),
        _product("QSC-PTZ-20X60", "Q-SYS PTZ 20x60", "QSC", "ALMO", 1425, 2199, 1999),
        _product(
            "QSC-TSC-101", "Q-SYS Touch Screen 10", "QSC", "ALMO", 780, 1299, 1199
        ),
        _product("QSC-NV-32H", "Q-SYS NV-32-H", "QSC", "MIDWICH", 930, 1499, 1399),
        _product(
            "SHURE-MXA920-W", "Shure MXA920 White", "SHURE", "DIRECT", 2820, 4299, 3999
        ),
        _product(
            "SHURE-ULXD4Q", "Shure ULXD4Q Receiver", "SHURE", "DIRECT", 2380, 3799, 3499
        ),
        _product("SHURE-ULXD2-B58", "Shure ULXD2/B58", "SHURE", "ALMO", 490, 799, 749),
        _product(
            "SHURE-ANIUSB", "Shure ANIUSB-MATRIX", "SHURE", "MIDWICH", 525, 899, 849
        ),
        _product(
            "SHURE-P300", "Shure IntelliMix P300", "SHURE", "MIDWICH", 760, 1299, 1199
        ),
        _product(
            "SONY-FW-75BZ40L", "Sony 75in Pro Display", "SONY", "ALMO", 1910, 3199, 2999
        ),
        _product(
            "SONY-FW-65BZ40L", "Sony 65in Pro Display", "SONY", "ALMO", 1420, 2499, 2299
        ),
        _product(
            "SONY-SRG-A40", "Sony SRG-A40 Camera", "SONY", "MIDWICH", 2140, 3299, 3099
        ),
        _product(
            "SONY-BRC-X1000", "Sony BRC-X1000", "SONY", "DIRECT", 4890, 7399, 6999
        ),
        _product("SONY-RM-IP500", "Sony RM-IP500", "SONY", "DIRECT", 1190, 1899, 1799),
        _product("EPSON-L735U", "Epson Pro L735U", "EPSON", "ALMO", 4180, 6299, 5999),
        _product("EPSON-L630SU", "Epson Pro L630SU", "EPSON", "ALMO", 4020, 5999, 5799),
        _product(
            "EPSON-ELPMB68", "Epson Ceiling Mount", "EPSON", "MIDWICH", 225, 349, 329
        ),
        _product(
            "EPSON-ELPLP99", "Epson Replacement Lamp", "EPSON", "MIDWICH", 160, 259, 239
        ),
        _product(
            "EPSON-ELPSC35", "Epson Screen Controller", "EPSON", "DIRECT", 290, 459, 429
        ),
        _product("CHIEF-RPAU", "Chief RPAU Mount", "CHIEF", "MIDWICH", 135, 239, 219),
        _product("CHIEF-CMA-440", "Chief CMS Adapter", "CHIEF", "MIDWICH", 45, 89, 79),
        _product(
            "CHIEF-LTA1U", "Chief Fusion Wall Mount", "CHIEF", "ALMO", 210, 349, 319
        ),
        _product("CHIEF-CPA-100", "Chief Pipe Accessory", "CHIEF", "ALMO", 40, 79, 69),
        _product(
            "CHIEF-PAC525", "Chief In-Wall Box", "CHIEF", "MIDWICH", 155, 259, 239
        ),
    ]

    products[3]["status"] = "discontinued"
    products[14]["status"] = "discontinued"
    products[21]["archived"] = "true"

    products[18]["taxable"] = "false"
    products[8]["taxable"] = "false"

    services = [
        _service("SVC-ENG-DESIGN", "Engineering Design", 145),
        _service("SVC-PROG-QSYS", "Q-SYS Programming", 165),
        _service("SVC-INSTALL-STD", "Standard Installation", 125),
        _service("SVC-COMMISSION", "Commissioning", 135),
        _service("SVC-TRAINING", "Client Training", 110),
        _service("SVC-PM", "Project Management", 150),
        _service("SVC-CABLE-TERM", "Cable Termination", 95),
        _service("SVC-RACK-BUILD", "Rack Build", 115),
        _service("SVC-TEST-VERIFY", "Test and Verify", 130),
        _service("SVC-WARRANTY", "Warranty Labor", 0, taxable=False),
    ]
    services[9]["status"] = "discontinued"

    fees = [
        _fee("FEE-SHIPPING", "Freight and Shipping", 225),
        _fee("FEE-PERMIT", "Permit Processing", 175),
        _fee("FEE-DISPOSAL", "Equipment Disposal", 95),
        _fee("FEE-RESTOCK", "Restocking Fee", 125),
        _fee("FEE-TRAVEL", "Travel Surcharge", 140),
    ]
    fees[2]["taxable"] = "false"
    fees[4]["archived"] = "true"

    assemblies = [
        _assembly("ASM-CONF-SM", "Conference Room Small Kit"),
        _assembly("ASM-CONF-MD", "Conference Room Medium Kit"),
        _assembly("ASM-CONF-LG", "Conference Room Large Kit"),
        _assembly("ASM-HUDDLE", "Huddle Space Kit"),
        _assembly("ASM-RACK-STD", "Standard Rack Package"),
    ]

    assembly_components = [
        _assembly_component("ASM-CONF-SM", "QSC-CORE-110F", 1, 1),
        _assembly_component("ASM-CONF-SM", "SHURE-MXA920-W", 1, 2),
        _assembly_component("ASM-CONF-SM", "SONY-FW-75BZ40L", 1, 3),
        _assembly_component("ASM-CONF-SM", "SVC-INSTALL-STD", 12, 4),
        _assembly_component("ASM-CONF-SM", "FEE-SHIPPING", 1, 5, required=False),
        _assembly_component("ASM-CONF-MD", "ASM-CONF-SM", 1, 1),
        _assembly_component("ASM-CONF-MD", "QSC-NV-32H", 2, 2),
        _assembly_component("ASM-CONF-MD", "SVC-PROG-QSYS", 8, 3),
        _assembly_component("ASM-CONF-LG", "ASM-CONF-MD", 1, 1),
        _assembly_component("ASM-CONF-LG", "SONY-SRG-A40", 2, 2),
        _assembly_component("ASM-CONF-LG", "SVC-COMMISSION", 10, 3),
        _assembly_component("ASM-HUDDLE", "QSC-NC-12X80", 1, 1),
        _assembly_component("ASM-HUDDLE", "SONY-FW-65BZ40L", 1, 2),
        _assembly_component("ASM-HUDDLE", "SVC-TRAINING", 2, 3),
        _assembly_component("ASM-RACK-STD", "CHIEF-CMA-440", 2, 1),
        _assembly_component("ASM-RACK-STD", "SVC-RACK-BUILD", 6, 2),
    ]

    tax_rules = [
        _tax_rule("CA-LOSANGELES", "CA State Base", 7.25, 10, False, "2025-01-01"),
        _tax_rule("CA-LOSANGELES", "Los Angeles City", 2.50, 20, False, "2025-01-01"),
        _tax_rule("CA-SANFRANCISCO", "CA State Base", 7.25, 10, False, "2025-01-01"),
        _tax_rule(
            "CA-SANFRANCISCO", "San Francisco City", 1.50, 20, False, "2025-01-01"
        ),
        _tax_rule("CA-SANJOSE", "CA State Base", 7.25, 10, False, "2025-01-01"),
        _tax_rule("CA-SANJOSE", "San Jose City", 1.00, 20, False, "2025-01-01"),
    ]

    price_lists = [
        {
            "vendor": "Midwich Demo Distribution",
            "manufacturer": "QSC Systems Demo",
            "sheet_name": "C04 Midwich QSC",
            "description": "Seed price list for QSC sample products",
            "source_filename": "c04_seed_midwich_qsc.csv",
            "rows": [
                _price_row("QSC-CORE-110F", "MID-QSC-110F", 3480, 5200),
                _price_row("QSC-NC-12X80", "MID-QSC-NC12", 1150, 1899),
                _price_row("QSC-NV-32H", "MID-QSC-NV32", 910, 1499),
                _price_row("QSC-PTZ-20X60", "MID-QSC-PTZ", 1390, 2199),
            ],
        },
        {
            "vendor": "Exertis Almo Demo",
            "manufacturer": "Sony AV Demo",
            "sheet_name": "C04 Almo Sony",
            "description": "Seed price list for Sony sample products",
            "source_filename": "c04_seed_almo_sony.csv",
            "rows": [
                _price_row("SONY-FW-75BZ40L", "ALM-SNY-75BZ", 1860, 3199),
                _price_row("SONY-FW-65BZ40L", "ALM-SNY-65BZ", 1390, 2499),
                _price_row("SONY-SRG-A40", "ALM-SNY-SRGA40", 2110, 3299),
                _price_row("SONY-RM-IP500", "ALM-SNY-RM500", 1160, 1899),
            ],
        },
        {
            "vendor": "Manufacturer Direct Demo",
            "manufacturer": "Shure Sample Labs",
            "sheet_name": "C04 Direct Shure",
            "description": "Seed direct price list for Shure sample products",
            "source_filename": "c04_seed_direct_shure.csv",
            "rows": [
                _price_row("SHURE-MXA920-W", "DIR-SHU-MXA920", 2790, 4299),
                _price_row("SHURE-ULXD4Q", "DIR-SHU-ULXD4Q", 2350, 3799),
                _price_row("SHURE-ULXD2-B58", "DIR-SHU-ULXD2", 470, 799),
                _price_row("SHURE-ANIUSB", "DIR-SHU-ANIUSB", 505, 899),
            ],
        },
    ]

    return {
        "package_id": SEED_PACKAGE_ID,
        "source": SEED_SOURCE,
        "manufacturers": manufacturers,
        "vendors": vendors,
        "products": products,
        "services": services,
        "fees": fees,
        "assemblies": assemblies,
        "assembly_components": assembly_components,
        "tax_rules": tax_rules,
        "price_lists": price_lists,
    }


def build_c04_seed_import_artifacts() -> dict[str, Any]:
    payload = build_c04_seed_payload()
    manufacturers_csv = _to_csv_bytes(payload["manufacturers"])
    vendors_csv = _to_csv_bytes(payload["vendors"])
    products_csv = _to_csv_bytes(payload["products"][:20])
    products_xlsx = _to_xlsx_bytes(payload["products"][20:])
    services_csv = _to_csv_bytes(payload["services"])
    fees_csv = _to_csv_bytes(payload["fees"])
    assemblies_csv = _to_csv_bytes(payload["assemblies"])
    components_csv = _to_csv_bytes(payload["assembly_components"])

    return {
        "manufacturers_csv": {
            "filename": f"{SEED_SOURCE_PREFIX}_manufacturers.csv",
            "entity_type": "manufacturers",
            "content": manufacturers_csv,
        },
        "vendors_csv": {
            "filename": f"{SEED_SOURCE_PREFIX}_vendors.csv",
            "entity_type": "vendors",
            "content": vendors_csv,
        },
        "products_csv": {
            "filename": f"{SEED_SOURCE_PREFIX}_products.csv",
            "entity_type": "products",
            "content": products_csv,
        },
        "products_xlsx": {
            "filename": f"{SEED_SOURCE_PREFIX}_products.xlsx",
            "entity_type": "products",
            "content": products_xlsx,
        },
        "services_csv": {
            "filename": f"{SEED_SOURCE_PREFIX}_services.csv",
            "entity_type": "services",
            "content": services_csv,
        },
        "fees_csv": {
            "filename": f"{SEED_SOURCE_PREFIX}_fees.csv",
            "entity_type": "fees",
            "content": fees_csv,
        },
        "assemblies_csv": {
            "filename": f"{SEED_SOURCE_PREFIX}_assemblies.csv",
            "entity_type": "assemblies",
            "content": assemblies_csv,
        },
        "assembly_components_csv": {
            "filename": f"{SEED_SOURCE_PREFIX}_assembly_components.csv",
            "entity_type": "assembly_components",
            "content": components_csv,
        },
        "pdf_price_list": {
            "filename": f"{SEED_SOURCE_PREFIX}_catalog_price_list.pdf",
            "content": _build_seed_pdf_bytes(),
        },
    }


def _to_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fieldnames = sorted({key for row in rows for key in row.keys()})
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in fieldnames})
    return buffer.getvalue().encode("utf-8")


def _to_xlsx_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    headers = sorted({key for row in rows for key in row.keys()})
    values = [*headers]
    matrix = [[str(row.get(column, "")) for column in headers] for row in rows]
    for row in matrix:
        values.extend(row)
    unique_values: list[str] = []
    for value in values:
        if value not in unique_values:
            unique_values.append(value)
    shared_index = {value: index for index, value in enumerate(unique_values)}

    def _cell(value: str) -> str:
        return f'<c t="s"><v>{shared_index[value]}</v></c>'

    row_xml = ["<row>" + "".join(_cell(value) for value in headers) + "</row>"]
    for row in matrix:
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


def _build_seed_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    payload = io.BytesIO()
    writer.write(payload)
    return payload.getvalue()


def _product(
    code: str,
    name: str,
    manufacturer: str,
    vendor: str,
    cost: float,
    msrp: float,
    map_price: float,
) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "description": f"{name} sample catalog entry",
        "long_description": f"Non-production sample for {name} in Atlas C-04 seed package.",
        "manufacturer": manufacturer,
        "vendor": vendor,
        "uom": "ea",
        "category": "equipment",
        "family": "commercial_av",
        "status": "active",
        "tax_category": "hardware",
        "cost": f"{cost:.2f}",
        "msrp": f"{msrp:.2f}",
        "map_price": f"{map_price:.2f}",
        "default_sales_price": f"{map_price:.2f}",
        "taxable": "true",
        "default_tax_nexus": "CA-LOSANGELES",
        "notes": "Seeded for C-04 alpha validation",
        "tags": "seed|c04|hardware",
        "source": SEED_SOURCE,
        "archived": "false",
    }


def _service(
    code: str, name: str, default_sales_price: float, taxable: bool = False
) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "description": f"{name} sample service",
        "manufacturer": "",
        "vendor": "",
        "uom": "hr",
        "category": "service",
        "family": "operations",
        "status": "active",
        "tax_category": "labor",
        "cost": "0.00",
        "default_sales_price": f"{default_sales_price:.2f}",
        "manual_unit_price": f"{default_sales_price:.2f}",
        "taxable": "true" if taxable else "false",
        "default_tax_nexus": "CA-LOSANGELES",
        "notes": "Seeded for C-04 alpha validation",
        "tags": "seed|c04|service",
        "source": SEED_SOURCE,
        "archived": "false",
    }


def _fee(code: str, name: str, default_sales_price: float) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "description": f"{name} sample fee",
        "manufacturer": "",
        "vendor": "",
        "uom": "ea",
        "category": "fee",
        "family": "commercial",
        "status": "active",
        "tax_category": "fee",
        "cost": "0.00",
        "default_sales_price": f"{default_sales_price:.2f}",
        "manual_unit_price": f"{default_sales_price:.2f}",
        "taxable": "true",
        "default_tax_nexus": "CA-LOSANGELES",
        "notes": "Seeded for C-04 alpha validation",
        "tags": "seed|c04|fee",
        "source": SEED_SOURCE,
        "archived": "false",
    }


def _assembly(code: str, name: str) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "description": f"{name} assembly sample",
        "uom": "ea",
        "category": "assembly",
        "family": "kits",
        "status": "active",
        "tax_category": "hardware",
        "cost": "0.00",
        "default_sales_price": "0.00",
        "taxable": "true",
        "default_tax_nexus": "CA-LOSANGELES",
        "notes": "Seeded for C-04 alpha validation",
        "tags": "seed|c04|assembly",
        "source": SEED_SOURCE,
        "archived": "false",
    }


def _assembly_component(
    assembly_code: str,
    component_code: str,
    quantity: float,
    sequence: int,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "assembly_code": assembly_code,
        "component_code": component_code,
        "quantity": str(quantity),
        "sequence": str(sequence),
        "required": "true" if required else "false",
        "notes": "Seeded for C-04 alpha validation",
        "source": SEED_SOURCE,
    }


def _tax_rule(
    nexus: str,
    title: str,
    rate: float,
    priority: int,
    compound: bool,
    effective_date: str,
) -> dict[str, Any]:
    return {
        "nexus": nexus,
        "title": title,
        "rate": rate,
        "priority": priority,
        "compound": compound,
        "taxable_item_types": ["product", "fee", "assembly"],
        "effective_date": effective_date,
        "expiration_date": "",
        "exemption_flags": [],
    }


def _price_row(
    code: str, vendor_sku: str, unit_cost: float, list_price: float
) -> dict[str, Any]:
    manufacturer_code = code.split("-", 1)[0]
    return {
        "model": code,
        "product": f"{manufacturer_code}::{code}",
        "vendor_sku": vendor_sku,
        "description": f"Sample price row for {code}",
        "unit_cost": unit_cost,
        "list_price": list_price,
        "currency": "USD",
        "availability": "in_stock",
        "lead_time": "5-10 days",
        "effective_date": "2026-01-01",
        "expiration_date": "",
        "notes": f"{SEED_SOURCE} price list row",
    }

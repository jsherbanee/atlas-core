"""Manufacturer/vendor price list ingestion and deterministic BOM enrichment."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
import io
import re
from typing import Any
from xml.etree import ElementTree as ET
import zipfile


def _today() -> date:
    return date.today()


@dataclass
class ManufacturerProduct:
    manufacturer: str
    model: str
    description: str
    category: str
    status: str
    aliases: list[str]
    list_price: float | None
    effective_date: str
    discontinued_date: str
    replacement_model: str
    source_file: str
    source_row: int
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VendorProductOffer:
    vendor: str
    manufacturer: str
    model: str
    vendor_sku: str
    description: str
    unit_cost: float | None
    discount: float | None
    effective_date: str
    expiration_date: str
    availability_status: str
    source_file: str
    source_row: int
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PriceListImportSummary:
    source_file: str
    manufacturer: str
    vendor: str
    effective_date: str
    product_count: int
    unmatched_rows: int
    duplicate_rows: int
    expired_pricing: int
    import_warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PricingService:
    SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".pdf", ".docx"}

    def ingest_price_lists(
        self,
        uploaded_files: list[tuple[str, bytes]],
    ) -> dict[str, Any]:
        manufacturer_products: list[ManufacturerProduct] = []
        vendor_offers: list[VendorProductOffer] = []
        uploaded_summaries: list[PriceListImportSummary] = []
        global_warnings: list[str] = []

        for filename, payload in uploaded_files:
            parsed_rows, warnings = self._parse_uploaded_rows(filename, payload)
            normalized_rows = [self._normalize_row_keys(row) for row in parsed_rows]
            file_products: list[ManufacturerProduct] = []
            file_offers: list[VendorProductOffer] = []
            unmatched_rows = 0

            for row_index, row in enumerate(normalized_rows, start=1):
                manufacturer_product = self._to_manufacturer_product(
                    row,
                    source_file=filename,
                    source_row=row_index,
                )
                vendor_offer = self._to_vendor_offer(
                    row,
                    source_file=filename,
                    source_row=row_index,
                )

                if manufacturer_product is None and vendor_offer is None:
                    unmatched_rows += 1
                    continue

                if manufacturer_product is not None:
                    file_products.append(manufacturer_product)
                if vendor_offer is not None:
                    file_offers.append(vendor_offer)

            duplicate_rows = self._duplicate_count(file_products, file_offers)
            expired_count = self._expired_count(file_products, file_offers)
            effective_date = self._summary_effective_date(file_products, file_offers)

            manufacturer_products.extend(file_products)
            vendor_offers.extend(file_offers)

            uploaded_summaries.append(
                PriceListImportSummary(
                    source_file=filename,
                    manufacturer=self._summary_manufacturer(file_products),
                    vendor=self._summary_vendor(file_offers),
                    effective_date=effective_date,
                    product_count=len(file_products) + len(file_offers),
                    unmatched_rows=unmatched_rows,
                    duplicate_rows=duplicate_rows,
                    expired_pricing=expired_count,
                    import_warnings=warnings,
                )
            )
            global_warnings.extend(
                [f"{filename}: {item}" for item in warnings if item.strip()]
            )

        return {
            "uploaded_price_lists": [item.to_dict() for item in uploaded_summaries],
            "manufacturer_products": [item.to_dict() for item in manufacturer_products],
            "vendor_offers": [item.to_dict() for item in vendor_offers],
            "import_warnings": global_warnings,
        }

    def enrich_bom_rows(
        self,
        bom_rows: list[dict[str, Any]],
        manufacturer_products: list[dict[str, Any]],
        vendor_offers: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        product_index = self._build_product_index(manufacturer_products)
        vendor_index = self._build_vendor_index(vendor_offers)
        enriched: list[dict[str, Any]] = []

        for row in bom_rows:
            item = dict(row)
            manufacturer = self._canonical_manufacturer(
                self._text(item.get("manufacturer"), "")
            )
            model_raw = self._text(item.get("model"), "")
            model_normalized = self._normalized_model(model_raw)

            exact_product_matches = self._product_matches(
                product_index,
                manufacturer,
                model_raw,
                exact=True,
            )
            normalized_product_matches = self._product_matches(
                product_index,
                manufacturer,
                model_normalized,
                exact=False,
            )
            product_matches = (
                exact_product_matches
                if exact_product_matches
                else normalized_product_matches
            )

            exact_vendor_matches = self._vendor_matches(
                vendor_index,
                manufacturer,
                model_raw,
                exact=True,
            )
            normalized_vendor_matches = self._vendor_matches(
                vendor_index,
                manufacturer,
                model_normalized,
                exact=False,
            )
            vendor_matches = (
                exact_vendor_matches
                if exact_vendor_matches
                else normalized_vendor_matches
            )

            match_confidence = 0.0
            warning = ""
            matched_product = None
            matched_offer = None

            if len(product_matches) == 1:
                matched_product = product_matches[0]
                match_confidence = 1.0 if exact_product_matches else 0.86
            elif len(product_matches) > 1:
                warning = "Ambiguous manufacturer product match; review required."

            if len(vendor_matches) == 1:
                matched_offer = vendor_matches[0]
                match_confidence = max(
                    match_confidence,
                    1.0 if exact_vendor_matches else 0.86,
                )
            elif len(vendor_matches) > 1:
                warning = (
                    warning
                    + (" " if warning else "")
                    + "Ambiguous vendor offer match; review required."
                )

            if matched_offer is not None and self._is_offer_expired(matched_offer):
                warning = (
                    warning + (" " if warning else "") + "Vendor pricing is expired."
                )

            pricing_source = ""
            pricing_effective_date = ""
            if matched_offer is not None:
                pricing_source = self._text(matched_offer.get("source_file"), "")
                pricing_effective_date = self._text(
                    matched_offer.get("effective_date"), ""
                )
            elif matched_product is not None:
                pricing_source = self._text(matched_product.get("source_file"), "")
                pricing_effective_date = self._text(
                    matched_product.get("effective_date"), ""
                )

            item["matched_manufacturer_product"] = (
                ""
                if matched_product is None
                else f"{self._text(matched_product.get('manufacturer'), '')} {self._text(matched_product.get('model'), '')}".strip()
            )
            item["matched_vendor_offer"] = (
                ""
                if matched_offer is None
                else self._text(
                    matched_offer.get("vendor_sku") or matched_offer.get("vendor"),
                    "",
                )
            )
            item["list_price"] = (
                matched_product.get("list_price")
                if matched_product is not None
                else None
            )
            item["known_cost"] = (
                matched_offer.get("unit_cost") if matched_offer is not None else None
            )
            item["pricing_source"] = pricing_source
            item["pricing_effective_date"] = pricing_effective_date
            item["match_confidence"] = round(match_confidence, 2)
            item["pricing_warning"] = warning

            enriched.append(item)

        return enriched

    def _parse_uploaded_rows(
        self,
        filename: str,
        payload: bytes,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        suffix = self._file_suffix(filename)
        if suffix not in self.SUPPORTED_EXTENSIONS:
            return [], [f"Unsupported file type: {suffix}"]
        if suffix == ".csv":
            return self._parse_csv(payload), []
        if suffix == ".xlsx":
            return self._parse_xlsx(payload)
        if suffix == ".xls":
            return self._parse_xls(payload)
        if suffix == ".pdf":
            return self._parse_pdf(payload), []
        if suffix == ".docx":
            return self._parse_docx(payload), []
        return [], ["No parser available for uploaded file."]

    def _parse_csv(self, payload: bytes) -> list[dict[str, Any]]:
        text = self._decode_bytes(payload)
        stream = io.StringIO(text)
        reader = csv.DictReader(stream)
        rows = [dict(row or {}) for row in reader]
        return rows

    def _parse_xlsx(self, payload: bytes) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        rows: list[dict[str, Any]] = []
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                shared = self._xlsx_shared_strings(archive)
                sheet_names = [
                    name
                    for name in archive.namelist()
                    if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
                ]
                if not sheet_names:
                    return [], ["XLSX file contains no worksheets."]
                root = ET.fromstring(archive.read(sorted(sheet_names)[0]))
                ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                data_rows: list[list[str]] = []
                for row in root.findall(".//s:sheetData/s:row", ns):
                    values: list[str] = []
                    for cell in row.findall("s:c", ns):
                        cell_type = cell.attrib.get("t", "")
                        value_node = cell.find("s:v", ns)
                        if value_node is None:
                            values.append("")
                            continue
                        raw_value = value_node.text or ""
                        if cell_type == "s":
                            values.append(
                                shared[int(raw_value)] if raw_value.isdigit() else ""
                            )
                        else:
                            values.append(raw_value)
                    data_rows.append(values)
                if not data_rows:
                    return [], ["XLSX worksheet contains no rows."]
                headers = [self._text(item, "") for item in data_rows[0]]
                for values in data_rows[1:]:
                    rows.append(
                        {
                            headers[index]: values[index] if index < len(values) else ""
                            for index in range(len(headers))
                            if headers[index]
                        }
                    )
        except Exception:
            warnings.append("Unable to parse XLSX contents.")

        return rows, warnings

    def _parse_xls(self, payload: bytes) -> tuple[list[dict[str, Any]], list[str]]:
        try:
            import xlrd  # type: ignore[import-not-found]
        except Exception:
            return [], ["XLS parser unavailable; install xlrd to ingest .xls files."]

        rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        try:
            book = xlrd.open_workbook(file_contents=payload)
            if book.nsheets <= 0:
                return [], ["XLS file contains no sheets."]
            sheet = book.sheet_by_index(0)
            headers = [
                self._text(sheet.cell_value(0, index), "")
                for index in range(sheet.ncols)
            ]
            for row_index in range(1, sheet.nrows):
                rows.append(
                    {
                        headers[col]: self._text(sheet.cell_value(row_index, col), "")
                        for col in range(sheet.ncols)
                        if col < len(headers) and headers[col]
                    }
                )
        except Exception:
            warnings.append("Unable to parse XLS contents.")

        return rows, warnings

    def _parse_pdf(self, payload: bytes) -> list[dict[str, Any]]:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(payload))
            lines: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                lines.extend(
                    [line.strip() for line in text.splitlines() if line.strip()]
                )
            return self._rows_from_delimited_lines(lines)
        except Exception:
            return []

    def _parse_docx(self, payload: bytes) -> list[dict[str, Any]]:
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                xml_text = archive.read("word/document.xml").decode(
                    "utf-8", errors="ignore"
                )
            lines = [
                line.strip() for line in re.split(r"<[^>]+>", xml_text) if line.strip()
            ]
            return self._rows_from_delimited_lines(lines)
        except Exception:
            return []

    def _rows_from_delimited_lines(self, lines: list[str]) -> list[dict[str, Any]]:
        candidates = [
            line for line in lines if any(sep in line for sep in [",", "\t", "|"])
        ]
        if len(candidates) < 2:
            return []
        separator = ","
        if candidates[0].count("\t") >= candidates[0].count(","):
            separator = "\t"
        if candidates[0].count("|") >= candidates[0].count(separator):
            separator = "|"

        headers = [part.strip() for part in candidates[0].split(separator)]
        if not headers:
            return []

        rows: list[dict[str, Any]] = []
        for line in candidates[1:]:
            values = [part.strip() for part in line.split(separator)]
            row = {
                headers[index]: values[index] if index < len(values) else ""
                for index in range(len(headers))
                if headers[index]
            }
            rows.append(row)
        return rows

    def _to_manufacturer_product(
        self,
        row: dict[str, Any],
        source_file: str,
        source_row: int,
    ) -> ManufacturerProduct | None:
        manufacturer = self._text(
            self._row_value(row, ["manufacturer", "mfr", "brand"]),
            "",
        )
        model = self._text(
            self._row_value(row, ["model", "part_number", "mpn", "sku"]),
            "",
        )

        if not manufacturer or not model:
            return None

        aliases = self._split_aliases(
            self._row_value(row, ["aliases", "model_aliases", "alt_model", "alias"])
        )

        return ManufacturerProduct(
            manufacturer=manufacturer,
            model=model,
            description=self._text(
                self._row_value(row, ["description", "product_description"]), ""
            ),
            category=self._text(
                self._row_value(row, ["category", "product_category"]), ""
            ),
            status=self._text(
                self._row_value(row, ["status", "product_status"]), "active"
            ),
            aliases=aliases,
            list_price=self._to_float(
                self._row_value(row, ["list_price", "msrp", "price"])
            ),
            effective_date=self._normalize_date(
                self._row_value(row, ["effective_date", "effective", "start_date"])
            ),
            discontinued_date=self._normalize_date(
                self._row_value(
                    row, ["discontinued_date", "end_of_life", "obsolete_date"]
                )
            ),
            replacement_model=self._text(
                self._row_value(row, ["replacement_model", "replacement", "successor"]),
                "",
            ),
            source_file=source_file,
            source_row=source_row,
            confidence=0.9,
        )

    def _to_vendor_offer(
        self,
        row: dict[str, Any],
        source_file: str,
        source_row: int,
    ) -> VendorProductOffer | None:
        vendor = self._text(
            self._row_value(row, ["vendor", "reseller", "supplier"]), ""
        )
        manufacturer = self._text(
            self._row_value(row, ["manufacturer", "mfr", "brand"]),
            "",
        )
        model = self._text(
            self._row_value(row, ["model", "part_number", "mpn", "sku"]),
            "",
        )
        unit_cost = self._to_float(
            self._row_value(row, ["unit_cost", "cost", "net_cost"])
        )

        if not vendor or not model or unit_cost is None:
            return None

        return VendorProductOffer(
            vendor=vendor,
            manufacturer=manufacturer,
            model=model,
            vendor_sku=self._text(
                self._row_value(row, ["vendor_sku", "sku", "vendor_part"]), ""
            ),
            description=self._text(
                self._row_value(row, ["description", "product_description"]), ""
            ),
            unit_cost=unit_cost,
            discount=self._to_float(self._row_value(row, ["discount", "discount_pct"])),
            effective_date=self._normalize_date(
                self._row_value(row, ["effective_date", "effective", "start_date"])
            ),
            expiration_date=self._normalize_date(
                self._row_value(row, ["expiration_date", "expires", "end_date"])
            ),
            availability_status=self._text(
                self._row_value(
                    row, ["availability_status", "availability", "stock_status"]
                ),
                "unknown",
            ),
            source_file=source_file,
            source_row=source_row,
            confidence=0.9,
        )

    def _build_product_index(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        index: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            manufacturer = self._canonical_manufacturer(
                self._text(row.get("manufacturer"), "")
            )
            model_raw = self._text(row.get("model"), "")
            model_norm = self._normalized_model(model_raw)
            aliases = self._split_aliases(row.get("aliases"))

            keys = [
                f"exact::{manufacturer}::{model_raw.upper()}",
                f"norm::{manufacturer}::{model_norm}",
            ]
            for alias in aliases:
                keys.append(f"norm::{manufacturer}::{self._normalized_model(alias)}")

            for key in keys:
                index.setdefault(key, []).append(row)
        return index

    def _build_vendor_index(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        index: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            manufacturer = self._canonical_manufacturer(
                self._text(row.get("manufacturer"), "")
            )
            model_raw = self._text(row.get("model"), "")
            model_norm = self._normalized_model(model_raw)
            keys = [
                f"exact::{manufacturer}::{model_raw.upper()}",
                f"norm::{manufacturer}::{model_norm}",
            ]
            for key in keys:
                index.setdefault(key, []).append(row)
        return index

    def _product_matches(
        self,
        index: dict[str, list[dict[str, Any]]],
        manufacturer: str,
        model_value: str,
        exact: bool,
    ) -> list[dict[str, Any]]:
        if not manufacturer or not model_value:
            return []
        key = (
            f"exact::{manufacturer}::{model_value.upper()}"
            if exact
            else f"norm::{manufacturer}::{model_value}"
        )
        return sorted(index.get(key, []), key=lambda row: str(row))

    def _vendor_matches(
        self,
        index: dict[str, list[dict[str, Any]]],
        manufacturer: str,
        model_value: str,
        exact: bool,
    ) -> list[dict[str, Any]]:
        if not manufacturer or not model_value:
            return []
        key = (
            f"exact::{manufacturer}::{model_value.upper()}"
            if exact
            else f"norm::{manufacturer}::{model_value}"
        )
        return sorted(index.get(key, []), key=lambda row: str(row))

    def _is_offer_expired(self, row: dict[str, Any]) -> bool:
        expiry = self._parse_date(self._text(row.get("expiration_date"), ""))
        return expiry is not None and expiry < _today()

    def _summary_manufacturer(self, rows: list[ManufacturerProduct]) -> str:
        names = sorted(
            {self._text(item.manufacturer, "") for item in rows if item.manufacturer}
        )
        if not names:
            return ""
        return names[0] if len(names) == 1 else "Multiple"

    def _summary_vendor(self, rows: list[VendorProductOffer]) -> str:
        names = sorted({self._text(item.vendor, "") for item in rows if item.vendor})
        if not names:
            return ""
        return names[0] if len(names) == 1 else "Multiple"

    def _summary_effective_date(
        self,
        products: list[ManufacturerProduct],
        offers: list[VendorProductOffer],
    ) -> str:
        dates = [
            item.effective_date
            for item in products
            if self._text(item.effective_date, "")
        ]
        dates.extend(
            [
                item.effective_date
                for item in offers
                if self._text(item.effective_date, "")
            ]
        )
        if not dates:
            return ""
        return sorted(dates)[0]

    def _duplicate_count(
        self,
        products: list[ManufacturerProduct],
        offers: list[VendorProductOffer],
    ) -> int:
        seen: set[str] = set()
        duplicates = 0
        for item in products:
            key = f"m::{self._canonical_manufacturer(item.manufacturer)}::{self._normalized_model(item.model)}"
            if key in seen:
                duplicates += 1
            seen.add(key)
        for offer in offers:
            key = f"v::{self._text(offer.vendor, '').lower()}::{self._canonical_manufacturer(offer.manufacturer)}::{self._normalized_model(offer.model)}"
            if key in seen:
                duplicates += 1
            seen.add(key)
        return duplicates

    def _expired_count(
        self,
        products: list[ManufacturerProduct],
        offers: list[VendorProductOffer],
    ) -> int:
        count = 0
        for item in products:
            discontinued = self._parse_date(item.discontinued_date)
            if discontinued is not None and discontinued <= _today():
                count += 1
        for offer in offers:
            expiry = self._parse_date(offer.expiration_date)
            if expiry is not None and expiry < _today():
                count += 1
        return count

    def _xlsx_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        shared_path = "xl/sharedStrings.xml"
        if shared_path not in archive.namelist():
            return []
        root = ET.fromstring(archive.read(shared_path))
        ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        values: list[str] = []
        for si in root.findall("s:si", ns):
            text_parts = [node.text or "" for node in si.findall(".//s:t", ns)]
            values.append("".join(text_parts))
        return values

    def _row_value(self, row: dict[str, Any], candidates: list[str]) -> Any:
        for candidate in candidates:
            if candidate in row and self._text(row.get(candidate), ""):
                return row.get(candidate)
        return ""

    def _normalize_row_keys(self, row: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in row.items():
            key_text = self._normalized_key(key)
            if key_text:
                normalized[key_text] = value
        return normalized

    def _normalized_key(self, value: Any) -> str:
        text = self._text(value, "").lower()
        text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
        return text

    def _canonical_manufacturer(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "", value.lower())
        return normalized

    def _normalized_model(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "", value.lower())
        return normalized

    def _split_aliases(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return sorted(
                {self._text(item, "") for item in value if self._text(item, "")}
            )
        text = self._text(value, "")
        if not text:
            return []
        parts = re.split(r"[|,;]", text)
        return sorted({part.strip() for part in parts if part.strip()})

    def _normalize_date(self, value: Any) -> str:
        parsed = self._parse_date(self._text(value, ""))
        return "" if parsed is None else parsed.isoformat()

    def _parse_date(self, value: str) -> date | None:
        if not value:
            return None
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"]:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        text = self._text(value, "")
        if not text:
            return None
        cleaned = text.replace("$", "").replace(",", "").replace("%", "")
        try:
            return round(float(cleaned), 4)
        except ValueError:
            return None

    def _decode_bytes(self, payload: bytes) -> str:
        for encoding in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                return payload.decode(encoding)
            except UnicodeDecodeError:
                continue
        return payload.decode("utf-8", errors="ignore")

    def _file_suffix(self, filename: str) -> str:
        dot = filename.rfind(".")
        if dot < 0:
            return ""
        return filename[dot:].lower()

    def _text(self, value: Any, default: str) -> str:
        if value is None:
            return default
        normalized = str(value).strip()
        return normalized if normalized else default

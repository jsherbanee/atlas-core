"""Commercial knowledge service with immutable price sheet versioning."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
import hashlib
import io
import json
from pathlib import Path
import tempfile
from typing import Any
import zipfile
import xml.etree.ElementTree as ET
from pypdf import PdfReader

from atlas_core.domain.commercial_knowledge import (
    AssemblyComponent,
    AssemblyVersion,
    CatalogItem,
    CatalogItemType,
    CommercialProductLifecycleStatus,
    KnowledgeFreshnessStatus,
    PricingPolicyType,
    PriceRecord,
    PriceSheet,
    PriceSheetVersion,
    TaxNexusRule,
    VendorOffering,
)
from atlas_core.services.document_intake_service import DocumentIntakeService


class CommercialKnowledgeService:
    def __init__(
        self,
        state: dict[str, Any] | None = None,
        *,
        as_of: date | None = None,
    ) -> None:
        self._as_of = as_of or datetime.now(UTC).date()
        if state is None:
            self.state = self.empty_state()
        else:
            self.state = self._normalized_state(state)

    @staticmethod
    def empty_state() -> dict[str, Any]:
        return {
            "price_sheets": {},
            "price_sheet_versions": {},
            "price_records": {},
            "vendor_offerings": {},
            "product_history": {},
            "product_lifecycle": {},
            "import_history": [],
            "change_reports": [],
            "catalog_items": {},
            "manufacturers": {},
            "vendors": {},
            "tax_nexus_rules": {},
            "pricing_defaults": {
                "default_policy": PricingPolicyType.MANUAL.value,
                "default_markup_percent": 0.0,
                "default_margin_percent": 0.0,
                "default_multiplier": 1.0,
                "rounding_policy": "currency_2dp",
                "default_tax_nexus": "",
                "currency": "USD",
            },
            "catalog_import_history": [],
            "assembly_versions": {},
            "assembly_version_lineage": {},
            "price_list_import_previews": {},
            "catalog_price_list_versions": {},
        }

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.state, sort_keys=True))

    def import_price_sheet(
        self,
        *,
        vendor: str,
        manufacturer: str,
        sheet_name: str,
        description: str,
        source_filename: str,
        file_bytes: bytes,
        imported_by: str,
        rows: list[dict[str, Any]],
        effective_date: str = "",
        expiration_date: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        vendor_text = self._safe(vendor, "Unknown Vendor")
        manufacturer_text = self._safe(manufacturer, "Unknown Manufacturer")
        sheet_name_text = self._safe(sheet_name, source_filename)

        sheet_id = self._sheet_id(vendor_text, manufacturer_text, sheet_name_text)
        sheet = self.state["price_sheets"].get(sheet_id)
        if sheet is None:
            sheet = PriceSheet(
                price_sheet_id=sheet_id,
                vendor=vendor_text,
                manufacturer=manufacturer_text,
                sheet_name=sheet_name_text,
                description=description,
                status="active",
                notes=notes,
            ).to_dict()

        previous_version_id = self._safe(sheet.get("active_version"), "")
        previous_records = self._records_for_version(previous_version_id)
        previous_by_product = {
            self._safe(item.get("product"), ""): item for item in previous_records
        }

        import_date = self._now_iso()
        version_index = 1 + len(
            [
                item
                for item in self.state["price_sheet_versions"].values()
                if self._safe(item.get("price_sheet_id"), "") == sheet_id
            ]
        )
        version_id = self._version_id(sheet_id, version_index)

        file_hash = hashlib.sha1(file_bytes).hexdigest()
        normalized_rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        for row_index, row in enumerate(list(rows or []), start=1):
            normalized = self._normalized_row(
                row,
                vendor=vendor_text,
                manufacturer=manufacturer_text,
                source_row=row_index,
            )
            if not normalized.get("product"):
                warnings.append(f"row {row_index}: missing product/model")
                continue
            normalized_rows.append(normalized)

        current_by_product = {
            self._safe(item.get("product"), ""): item for item in normalized_rows
        }
        comparison = self._compare_versions(previous_by_product, current_by_product)

        records: list[dict[str, Any]] = []
        for row in normalized_rows:
            record_id = self._price_record_id(
                version_id=version_id,
                product=self._safe(row.get("product"), ""),
                vendor_sku=self._safe(row.get("vendor_sku"), ""),
                source_row=int(row.get("source_row", 0) or 0),
            )
            record = PriceRecord(
                price_record_id=record_id,
                version_id=version_id,
                vendor=vendor_text,
                vendor_type=self._safe(row.get("vendor_type"), "other"),
                product=self._safe(row.get("product"), ""),
                vendor_sku=self._safe(row.get("vendor_sku"), "UNKNOWN-SKU"),
                cost=self._float_or_none(row.get("cost")),
                list_price=self._float_or_none(row.get("list_price")),
                currency=self._safe(row.get("currency"), "USD"),
                lead_time=self._safe(row.get("lead_time"), "unknown"),
                availability=self._safe(row.get("availability"), "unknown"),
                effective_date=self._safe(row.get("effective_date"), effective_date),
                expiration_date=self._safe(
                    row.get("expiration_date"),
                    expiration_date,
                ),
                confidence=self._bounded_confidence(row.get("confidence", 0.9)),
                source_row=int(row.get("source_row", 0) or 0),
                unit_of_measure=self._safe(row.get("unit_of_measure"), "ea"),
                pack_quantity=self._int_or_none(row.get("pack_quantity")),
                minimum_order_quantity=self._int_or_none(
                    row.get("minimum_order_quantity")
                ),
                purchase_multiple=self._int_or_none(row.get("purchase_multiple")),
                active=bool(row.get("active", True)),
                notes=self._safe(row.get("notes"), ""),
            ).to_dict()
            self.state["price_records"][record_id] = record
            records.append(record)

            offering_id = self._vendor_offering_id(
                vendor=vendor_text,
                product=self._safe(record.get("product"), ""),
                vendor_sku=self._safe(record.get("vendor_sku"), "UNKNOWN-SKU"),
            )
            offering = self.state["vendor_offerings"].get(offering_id)
            if offering is None:
                offering = VendorOffering(
                    vendor_offering_id=offering_id,
                    vendor=vendor_text,
                    vendor_type=self._safe(record.get("vendor_type"), "other"),
                    product=self._safe(record.get("product"), ""),
                    manufacturer=manufacturer_text,
                    vendor_sku=self._safe(record.get("vendor_sku"), "UNKNOWN-SKU"),
                    latest_version=version_id,
                    historical_versions=[version_id],
                ).to_dict()
            else:
                history = [
                    self._safe(item, "")
                    for item in list(offering.get("historical_versions") or [])
                ]
                if version_id not in history:
                    history.append(version_id)
                offering["historical_versions"] = history
                offering["latest_version"] = version_id
                offering["vendor_type"] = self._safe(
                    record.get("vendor_type"),
                    self._safe(offering.get("vendor_type"), "other"),
                )
            self.state["vendor_offerings"][offering_id] = offering

            self._update_product_history(
                product=self._safe(record.get("product"), ""),
                vendor=vendor_text,
                manufacturer=manufacturer_text,
                version_id=version_id,
                record=record,
                import_date=import_date,
            )

        version = PriceSheetVersion(
            version_id=version_id,
            price_sheet_id=sheet_id,
            version_name=f"v{version_index}",
            import_date=import_date,
            effective_date=self._safe(effective_date, import_date[:10]),
            expiration_date=self._safe(expiration_date, ""),
            source_filename=self._safe(source_filename, "upload"),
            file_hash=file_hash,
            imported_by=self._safe(imported_by, "atlas"),
            row_count=len(records),
            added_products=len(comparison["products_added"]),
            removed_products=len(comparison["products_removed"]),
            updated_products=len(comparison["products_updated"]),
            unchanged_products=len(comparison["products_unchanged"]),
            warnings=sorted(set(warnings + list(comparison["warnings"]))),
        ).to_dict()

        sheet["active_version"] = version_id
        sheet["last_import_date"] = import_date
        sheet["status"] = "active"

        self.state["price_sheets"][sheet_id] = sheet
        self.state["price_sheet_versions"][version_id] = {
            **version,
            "comparison_summary": comparison,
        }

        lifecycle_updates = self._apply_product_lifecycle(current_by_product)
        freshness_rows = self._freshness_rows()
        change_report = self._build_change_report(
            version=version,
            comparison=comparison,
            freshness_rows=freshness_rows,
            lifecycle_updates=lifecycle_updates,
        )
        self.state["change_reports"].append(change_report)

        import_history_row = {
            "import_date": import_date,
            "vendor": vendor_text,
            "manufacturer": manufacturer_text,
            "version": version["version_name"],
            "version_id": version_id,
            "price_sheet_id": sheet_id,
            "rows_imported": len(records),
            "products_added": len(comparison["products_added"]),
            "products_removed": len(comparison["products_removed"]),
            "products_changed": len(comparison["products_updated"]),
            "warnings": list(version["warnings"]),
            "comparison_summary": comparison,
            "source_filename": source_filename,
        }
        self.state["import_history"].append(import_history_row)

        return {
            "price_sheet": dict(sheet),
            "version": dict(self.state["price_sheet_versions"][version_id]),
            "change_report": dict(change_report),
            "import_history": dict(import_history_row),
        }

    def import_history_rows(self) -> list[dict[str, Any]]:
        rows = list(self.state.get("import_history") or [])
        rows.sort(
            key=lambda item: self._safe(item.get("import_date"), ""), reverse=True
        )
        return rows

    def dashboard_summary(self) -> dict[str, Any]:
        sheets = list(self.state["price_sheets"].values())
        versions = list(self.state["price_sheet_versions"].values())
        records = list(self.state["price_records"].values())
        offerings = list(self.state["vendor_offerings"].values())
        product_history = dict(self.state["product_history"])
        freshness_rows = self._freshness_rows()

        unique_mfr = sorted(
            {
                self._safe(item.get("manufacturer"), "")
                for item in sheets
                if self._safe(item.get("manufacturer"), "")
            }
        )
        unique_vendors = sorted(
            {
                self._safe(item.get("vendor"), "")
                for item in sheets
                if self._safe(item.get("vendor"), "")
            }
        )

        latest_imports = sorted(
            versions,
            key=lambda item: self._safe(item.get("import_date"), ""),
            reverse=True,
        )[:5]
        missing_pricing = sum(
            1
            for item in freshness_rows
            if self._safe(item.get("current_status"), "")
            == KnowledgeFreshnessStatus.MISSING.value
        )
        stale_pricing = sum(
            1
            for item in freshness_rows
            if self._safe(item.get("current_status"), "")
            == KnowledgeFreshnessStatus.STALE.value
        )
        recently_updated = sum(
            1
            for item in freshness_rows
            if int(item.get("days_since_import", 9999)) <= 30
        )
        missing_from_latest = sum(
            1
            for value in self.state["product_lifecycle"].values()
            if self._safe(value.get("lifecycle_status"), "")
            == CommercialProductLifecycleStatus.MISSING_FROM_LATEST_PRICE_SHEET.value
        )

        coverage_pct = 0.0
        if product_history:
            covered = sum(
                1
                for item in product_history.values()
                if list(item.get("historical_prices") or [])
            )
            coverage_pct = round((covered / len(product_history)) * 100, 2)

        freshness_map = {
            KnowledgeFreshnessStatus.FRESH.value: 0,
            KnowledgeFreshnessStatus.REVIEW_RECOMMENDED.value: 0,
            KnowledgeFreshnessStatus.STALE.value: 0,
            KnowledgeFreshnessStatus.MISSING.value: 0,
        }
        for item in freshness_rows:
            status = self._safe(
                item.get("current_status"), KnowledgeFreshnessStatus.MISSING.value
            )
            freshness_map.setdefault(status, 0)
            freshness_map[status] += 1

        confidence_values = [
            float(item.get("confidence", 0.0) or 0.0)
            for item in records
            if isinstance(item.get("confidence", 0.0), (int, float))
        ]
        confidence = (
            round(sum(confidence_values) / len(confidence_values), 4)
            if confidence_values
            else 0.0
        )

        return {
            "manufacturers": len(unique_mfr),
            "vendors": len(unique_vendors),
            "products": len(product_history),
            "vendor_offerings": len(offerings),
            "active_price_sheets": len(sheets),
            "latest_imports": [
                {
                    "version": self._safe(item.get("version_name"), ""),
                    "import_date": self._safe(item.get("import_date"), ""),
                    "vendor": self._safe(
                        self.state["price_sheets"]
                        .get(self._safe(item.get("price_sheet_id"), ""), {})
                        .get("vendor"),
                        "",
                    ),
                    "manufacturer": self._safe(
                        self.state["price_sheets"]
                        .get(self._safe(item.get("price_sheet_id"), ""), {})
                        .get("manufacturer"),
                        "",
                    ),
                }
                for item in latest_imports
            ],
            "products_missing_pricing": missing_pricing,
            "pricing_stale": stale_pricing,
            "recently_updated": recently_updated,
            "products_missing_from_latest_version": missing_from_latest,
            "coverage_percentage": coverage_pct,
            "knowledge_freshness": freshness_map,
            "commercial_confidence": confidence,
        }

    def freshness_rows(self) -> list[dict[str, Any]]:
        rows = self._freshness_rows()
        rows.sort(key=lambda item: self._safe(item.get("product"), ""))
        return rows

    def price_history_for_product(self, product: str) -> dict[str, Any]:
        key = self._safe(product, "")
        history = dict(self.state["product_history"].get(key) or {})
        return {
            "product": key,
            "known_vendors": sorted(set(history.get("known_vendors") or [])),
            "historical_prices": list(history.get("historical_prices") or []),
            "historical_vendor_offerings": list(
                history.get("historical_vendor_offerings") or []
            ),
            "price_trend": self._price_trend(
                list(history.get("historical_prices") or [])
            ),
            "last_updated": self._safe(history.get("last_updated"), ""),
            "latest_version": self._safe(history.get("latest_version"), ""),
            "historical_versions": list(history.get("historical_versions") or []),
            "engineering_usage": list(history.get("engineering_usage") or []),
            "referenced_projects": list(history.get("referenced_projects") or []),
        }

    def list_catalog_items(
        self,
        *,
        item_type: CatalogItemType | str | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        normalized_item_type = self._safe(item_type, "").lower() or None
        rows: list[dict[str, Any]] = []
        for payload in self.state["catalog_items"].values():
            if not isinstance(payload, dict):
                continue
            if (
                normalized_item_type
                and self._safe(payload.get("item_type"), "") != normalized_item_type
            ):
                continue
            if not include_archived and bool(payload.get("archived", False)):
                continue
            rows.append(dict(payload))
        rows.sort(
            key=lambda item: (
                self._safe(item.get("item_type"), ""),
                self._safe(item.get("code"), ""),
                self._safe(item.get("name"), ""),
            )
        )
        return rows

    def catalog_item(self, catalog_item_id: str) -> dict[str, Any] | None:
        key = self._safe(catalog_item_id, "")
        if not key:
            return None
        payload = self.state["catalog_items"].get(key)
        if not isinstance(payload, dict):
            return None
        return dict(payload)

    def upsert_catalog_item(
        self,
        *,
        catalog_item_id: str | None,
        item_type: CatalogItemType | str,
        code: str,
        name: str,
        description: str = "",
        long_description: str = "",
        manufacturer: str | None = None,
        vendor: str | None = None,
        uom: str = "ea",
        category: str = "",
        family: str = "",
        status: str = "active",
        tax_category: str = "standard",
        cost_references: list[dict[str, Any]] | None = None,
        cost: float | None = None,
        msrp: float | None = None,
        map_price: float | None = None,
        default_sales_price: float | None = None,
        manual_unit_price: float | None = None,
        taxable: bool = True,
        default_tax_nexus: str | None = None,
        notes: str = "",
        tags: list[str] | None = None,
        source: str = "manual",
        provenance: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        archived: bool = False,
    ) -> dict[str, Any]:
        item_type_value = CatalogItemType(self._safe(item_type, "")).value
        now = self._now_iso()
        item_id = self._safe(catalog_item_id, "")
        if not item_id:
            item_id = self._catalog_item_id(item_type_value, code)
        existing = dict(self.state["catalog_items"].get(item_id) or {})
        created_at = self._safe(existing.get("created_at"), now)
        item = CatalogItem(
            catalog_item_id=item_id,
            item_type=CatalogItemType(item_type_value),
            code=code,
            name=name,
            description=description,
            long_description=long_description,
            manufacturer=manufacturer,
            vendor=vendor,
            uom=uom,
            category=category,
            family=family,
            status=status,
            tax_category=tax_category,
            cost_references=list(cost_references or []),
            cost=cost,
            msrp=msrp,
            map_price=map_price,
            default_sales_price=default_sales_price,
            manual_unit_price=manual_unit_price,
            taxable=taxable,
            default_tax_nexus=default_tax_nexus,
            notes=notes,
            tags=list(tags or []),
            source=source,
            provenance=dict(provenance or {}),
            metadata=dict(metadata or {}),
            archived=archived,
            created_at=created_at,
            updated_at=now,
        ).to_dict()
        self.state["catalog_items"][item_id] = item
        return dict(item)

    def archive_catalog_item(self, catalog_item_id: str) -> dict[str, Any]:
        item = self.catalog_item(catalog_item_id)
        if item is None:
            raise ValueError("catalog item was not found")
        item["archived"] = True
        item["updated_at"] = self._now_iso()
        self.state["catalog_items"][item["catalog_item_id"]] = item
        return dict(item)

    def restore_catalog_item(self, catalog_item_id: str) -> dict[str, Any]:
        item = self.catalog_item(catalog_item_id)
        if item is None:
            raise ValueError("catalog item was not found")
        item["archived"] = False
        item["updated_at"] = self._now_iso()
        self.state["catalog_items"][item["catalog_item_id"]] = item
        return dict(item)

    def set_pricing_defaults(
        self,
        *,
        default_policy: PricingPolicyType | str,
        default_markup_percent: float,
        default_margin_percent: float,
        default_multiplier: float,
        rounding_policy: str,
        default_tax_nexus: str = "",
        currency: str = "USD",
    ) -> dict[str, Any]:
        policy = PricingPolicyType(self._safe(default_policy, "")).value
        defaults = {
            "default_policy": policy,
            "default_markup_percent": max(0.0, round(float(default_markup_percent), 4)),
            "default_margin_percent": max(0.0, round(float(default_margin_percent), 4)),
            "default_multiplier": max(0.0, round(float(default_multiplier), 6)),
            "rounding_policy": self._safe(rounding_policy, "currency_2dp"),
            "default_tax_nexus": self._safe(default_tax_nexus, ""),
            "currency": self._safe(currency, "USD").upper() or "USD",
        }
        self.state["pricing_defaults"] = defaults
        return dict(defaults)

    def pricing_defaults(self) -> dict[str, Any]:
        return dict(self.state.get("pricing_defaults") or {})

    def create_or_update_tax_nexus_rule(
        self,
        *,
        tax_rule_id: str | None,
        nexus: str,
        title: str,
        rate: float,
        priority: int = 100,
        compound: bool = False,
        taxable_item_types: list[CatalogItemType | str] | None = None,
        exemption_flags: list[str] | None = None,
        effective_date: str | None = None,
        expiration_date: str | None = None,
        archived: bool = False,
    ) -> dict[str, Any]:
        key = self._safe(tax_rule_id, "")
        if not key:
            key = self._tax_rule_id(nexus=nexus, title=title, priority=priority)
        row = TaxNexusRule(
            tax_rule_id=key,
            nexus=nexus,
            title=title,
            rate=rate,
            priority=priority,
            compound=compound,
            taxable_item_types=list(taxable_item_types or []),
            exemption_flags=list(exemption_flags or []),
            effective_date=effective_date,
            expiration_date=expiration_date,
            archived=archived,
        ).to_dict()
        self.state["tax_nexus_rules"][key] = row
        return dict(row)

    def list_tax_nexus_rules(
        self,
        *,
        nexus: str | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        normalized_nexus = self._safe(nexus, "").lower() or None
        rows: list[dict[str, Any]] = []
        for payload in self.state["tax_nexus_rules"].values():
            if not isinstance(payload, dict):
                continue
            if (
                normalized_nexus
                and self._safe(payload.get("nexus"), "").lower() != normalized_nexus
            ):
                continue
            if not include_archived and bool(payload.get("archived", False)):
                continue
            rows.append(dict(payload))
        rows.sort(
            key=lambda item: (
                int(item.get("priority", 100) or 100),
                self._safe(item.get("tax_rule_id"), ""),
            )
        )
        return rows

    def tax_quote_for_line(
        self,
        *,
        nexus: str,
        item_type: CatalogItemType | str,
        taxable_amount: float,
        exemption_flags: list[str] | None = None,
        as_of: str | None = None,
    ) -> dict[str, Any]:
        normalized_nexus = self._safe(nexus, "")
        if not normalized_nexus:
            return {
                "nexus": "",
                "taxable_amount": round(float(taxable_amount), 4),
                "effective_tax_rate": 0.0,
                "tax_amount": 0.0,
                "applied_rules": [],
            }
        normalized_type = CatalogItemType(self._safe(item_type, "")).value
        amount = max(0.0, round(float(taxable_amount), 6))
        as_of_date = self._date_from_iso(self._safe(as_of, "")) or self._as_of
        flags = {
            self._safe(item, "").lower()
            for item in list(exemption_flags or [])
            if self._safe(item, "")
        }
        applicable_rules: list[dict[str, Any]] = []
        for rule in self.list_tax_nexus_rules(
            nexus=normalized_nexus,
            include_archived=False,
        ):
            types = {
                self._safe(item, "")
                for item in list(rule.get("taxable_item_types") or [])
                if self._safe(item, "")
            }
            if normalized_type not in types:
                continue
            if flags.intersection(
                {
                    self._safe(item, "").lower()
                    for item in list(rule.get("exemption_flags") or [])
                }
            ):
                continue
            if not self._is_rule_effective(rule=rule, as_of=as_of_date):
                continue
            applicable_rules.append(rule)

        total_tax = 0.0
        applied: list[dict[str, Any]] = []
        for rule in applicable_rules:
            rate = max(0.0, float(rule.get("rate", 0.0) or 0.0))
            basis = amount + total_tax if bool(rule.get("compound", False)) else amount
            rule_tax = round(basis * (rate / 100.0), 6)
            total_tax = round(total_tax + rule_tax, 6)
            applied.append(
                {
                    "tax_rule_id": self._safe(rule.get("tax_rule_id"), ""),
                    "title": self._safe(rule.get("title"), ""),
                    "rate": rate,
                    "compound": bool(rule.get("compound", False)),
                    "tax_amount": round(rule_tax, 4),
                }
            )

        effective_rate = 0.0
        if amount > 0:
            effective_rate = round(total_tax / amount, 6)
        return {
            "nexus": normalized_nexus,
            "taxable_amount": round(amount, 4),
            "effective_tax_rate": effective_rate,
            "tax_amount": round(total_tax, 4),
            "applied_rules": applied,
        }

    def quote_catalog_item(
        self,
        *,
        catalog_item_id: str,
        quantity: float,
        policy: PricingPolicyType | str | None = None,
        markup_percent: float | None = None,
        margin_percent: float | None = None,
        multiplier: float | None = None,
        manual_unit_price: float | None = None,
        tax_nexus: str | None = None,
        exemption_flags: list[str] | None = None,
        as_of: str | None = None,
    ) -> dict[str, Any]:
        item = self.catalog_item(catalog_item_id)
        if item is None or bool(item.get("archived", False)):
            raise ValueError("catalog item was not found")
        qty = max(0.0, round(float(quantity), 6))
        defaults = self.pricing_defaults()
        selected_policy = PricingPolicyType(
            self._safe(
                policy,
                self._safe(
                    defaults.get("default_policy"), PricingPolicyType.MANUAL.value
                ),
            )
        ).value

        base_cost = self._float_or_none(item.get("cost"))
        msrp = self._float_or_none(item.get("msrp"))
        map_price = self._float_or_none(item.get("map_price"))
        default_sales_price = self._float_or_none(item.get("default_sales_price"))
        manual_default = self._float_or_none(item.get("manual_unit_price"))

        resolved_markup = (
            float(markup_percent)
            if markup_percent is not None
            else float(defaults.get("default_markup_percent", 0.0) or 0.0)
        )
        resolved_margin = (
            float(margin_percent)
            if margin_percent is not None
            else float(defaults.get("default_margin_percent", 0.0) or 0.0)
        )
        resolved_multiplier = (
            float(multiplier)
            if multiplier is not None
            else float(defaults.get("default_multiplier", 1.0) or 1.0)
        )

        resolved_manual_price = self._float_or_none(manual_unit_price)
        manual_override_applied = resolved_manual_price is not None
        if manual_override_applied:
            unit_price = resolved_manual_price
            selected_policy = PricingPolicyType.MANUAL.value
        elif selected_policy == PricingPolicyType.MSRP.value:
            unit_price = msrp if msrp is not None else base_cost or 0.0
        elif selected_policy == PricingPolicyType.MAP.value:
            unit_price = map_price if map_price is not None else base_cost or 0.0
        elif selected_policy == PricingPolicyType.COST_PLUS_PERCENT.value:
            unit_price = (base_cost or 0.0) * (1.0 + max(0.0, resolved_markup) / 100.0)
        elif selected_policy == PricingPolicyType.MARGIN_PERCENT.value:
            margin_ratio = max(0.0, min(99.99, resolved_margin)) / 100.0
            denominator = max(0.0001, 1.0 - margin_ratio)
            unit_price = (base_cost or 0.0) / denominator
        elif selected_policy == PricingPolicyType.MULTIPLIER.value:
            unit_price = (base_cost or 0.0) * max(0.0, resolved_multiplier)
        else:
            unit_price = manual_default
            if unit_price is None:
                unit_price = (
                    default_sales_price
                    if default_sales_price is not None
                    else (msrp if msrp is not None else base_cost or 0.0)
                )

        if unit_price is None:
            unit_price = 0.0
        unit_price = round(max(0.0, float(unit_price)), 4)
        line_subtotal = round(qty * unit_price, 4)
        resolved_nexus = self._safe(
            tax_nexus,
            self._safe(
                item.get("default_tax_nexus"),
                self._safe(defaults.get("default_tax_nexus"), ""),
            ),
        )
        tax_quote = self.tax_quote_for_line(
            nexus=resolved_nexus,
            item_type=self._safe(item.get("item_type"), CatalogItemType.PRODUCT.value),
            taxable_amount=(line_subtotal if bool(item.get("taxable", True)) else 0.0),
            exemption_flags=exemption_flags,
            as_of=as_of,
        )
        line_total = round(line_subtotal + float(tax_quote.get("tax_amount", 0.0)), 4)

        return {
            "catalog_item_id": self._safe(item.get("catalog_item_id"), ""),
            "code": self._safe(item.get("code"), ""),
            "item_type": self._safe(item.get("item_type"), ""),
            "quantity": qty,
            "unit_price": unit_price,
            "policy": selected_policy,
            "manual_override_applied": manual_override_applied,
            "line_subtotal": line_subtotal,
            "tax": tax_quote,
            "line_total": line_total,
            "uom": self._safe(item.get("uom"), "ea"),
            "manufacturer": self._safe(item.get("manufacturer"), "") or None,
            "vendor": self._safe(item.get("vendor"), "") or None,
        }

    def create_or_update_assembly_version(
        self,
        *,
        assembly_item_id: str,
        components: list[dict[str, Any]],
        expanded_description: str = "",
        status: str = "active",
        clone_from_version_id: str | None = None,
    ) -> dict[str, Any]:
        assembly = self.catalog_item(assembly_item_id)
        if assembly is None:
            raise ValueError("assembly catalog item was not found")
        if self._safe(assembly.get("item_type"), "") != CatalogItemType.ASSEMBLY.value:
            raise ValueError("catalog item is not an assembly")

        normalized_components: list[dict[str, Any]] = []
        if clone_from_version_id:
            previous = self.assembly_version(clone_from_version_id)
            if previous is None:
                raise ValueError("clone source assembly version was not found")
            normalized_components.extend(
                [dict(item) for item in list(previous.get("components") or [])]
            )
        for row in list(components or []):
            component_item_id = self._safe(row.get("component_item_id"), "")
            if not component_item_id:
                raise ValueError("assembly components require component_item_id")
            component_item = self.catalog_item(component_item_id)
            if component_item is None:
                raise ValueError(
                    f"assembly component catalog item was not found: {component_item_id}"
                )
            component = AssemblyComponent(
                component_id=self._safe(row.get("component_id"), "")
                or self._assembly_component_id(
                    assembly_item_id=assembly_item_id,
                    component_item_id=component_item_id,
                    sequence=int(
                        row.get("sequence", len(normalized_components) + 1) or 1
                    ),
                ),
                component_item_id=component_item_id,
                quantity=float(row.get("quantity", 0.0) or 0.0),
                required=bool(row.get("required", True)),
                sequence=int(row.get("sequence", len(normalized_components) + 1) or 1),
                notes=self._safe(row.get("notes"), ""),
            ).to_dict()
            normalized_components.append(component)

        normalized_components.sort(
            key=lambda item: (
                int(item.get("sequence", 1) or 1),
                self._safe(item.get("component_id"), ""),
            )
        )
        self._assert_no_assembly_cycle(
            root_assembly_item_id=assembly_item_id,
            components=normalized_components,
        )

        version_number = self._next_assembly_version_number(assembly_item_id)
        version_id = self._assembly_version_id(assembly_item_id, version_number)
        rollup = self._assembly_rollup(
            assembly_item_id=assembly_item_id,
            components=normalized_components,
        )
        payload = AssemblyVersion(
            assembly_version_id=version_id,
            assembly_item_id=assembly_item_id,
            version_number=version_number,
            status=self._safe(status, "active"),
            expanded_description=self._safe(expanded_description),
            component_count=len(normalized_components),
            total_cost=rollup["total_cost"],
            total_sales_price=rollup["total_sales_price"],
            components=normalized_components,
            created_at=self._now_iso(),
            updated_at=self._now_iso(),
            archived=False,
        ).to_dict()
        self.state.setdefault("assembly_versions", {})[version_id] = payload
        lineage = self.state.setdefault("assembly_version_lineage", {})
        lineage.setdefault(assembly_item_id, [])
        lineage[assembly_item_id].append(version_id)
        return dict(payload)

    def assembly_version(self, assembly_version_id: str) -> dict[str, Any] | None:
        key = self._safe(assembly_version_id, "")
        if not key:
            return None
        row = self.state.get("assembly_versions", {}).get(key)
        if not isinstance(row, dict):
            return None
        return dict(row)

    def list_assembly_versions(
        self,
        *,
        assembly_item_id: str,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        key = self._safe(assembly_item_id, "")
        version_ids = list(
            self.state.get("assembly_version_lineage", {}).get(key) or []
        )
        rows: list[dict[str, Any]] = []
        for version_id in version_ids:
            payload = self.assembly_version(version_id)
            if payload is None:
                continue
            if not include_archived and bool(payload.get("archived", False)):
                continue
            rows.append(payload)
        rows.sort(
            key=lambda item: int(item.get("version_number", 0) or 0), reverse=True
        )
        return rows

    def latest_assembly_version(self, assembly_item_id: str) -> dict[str, Any] | None:
        rows = self.list_assembly_versions(assembly_item_id=assembly_item_id)
        return dict(rows[0]) if rows else None

    def expand_assembly(
        self,
        *,
        assembly_item_id: str,
        quantity: float,
        assembly_version_id: str | None = None,
        include_optional: bool = True,
    ) -> dict[str, Any]:
        qty = max(0.0, round(float(quantity), 6))
        assembly_item = self.catalog_item(assembly_item_id)
        if assembly_item is None:
            raise ValueError("assembly catalog item was not found")
        if (
            self._safe(assembly_item.get("item_type"), "")
            != CatalogItemType.ASSEMBLY.value
        ):
            raise ValueError("catalog item is not an assembly")

        version = (
            self.assembly_version(self._safe(assembly_version_id, ""))
            if self._safe(assembly_version_id, "")
            else self.latest_assembly_version(assembly_item_id)
        )
        if version is None:
            raise ValueError("assembly has no active version")

        exploded: list[dict[str, Any]] = []
        self._expand_assembly_recursive(
            assembly_item_id=assembly_item_id,
            assembly_version=version,
            root_multiplier=qty,
            include_optional=include_optional,
            exploded=exploded,
            traversal_stack=[assembly_item_id],
            parent_path=self._safe(assembly_item.get("code"), assembly_item_id),
        )
        total_cost = round(
            sum(float(item.get("extended_cost", 0.0) or 0.0) for item in exploded), 4
        )
        total_sales_price = round(
            sum(
                float(item.get("extended_sales_price", 0.0) or 0.0) for item in exploded
            ),
            4,
        )
        return {
            "assembly_item_id": assembly_item_id,
            "assembly_code": self._safe(assembly_item.get("code"), ""),
            "assembly_name": self._safe(assembly_item.get("name"), ""),
            "assembly_version_id": self._safe(version.get("assembly_version_id"), ""),
            "quantity": qty,
            "components": exploded,
            "total_cost": total_cost,
            "total_sales_price": total_sales_price,
            "snapshot": {
                "expanded_at": self._now_iso(),
                "assembly_version_id": self._safe(
                    version.get("assembly_version_id"), ""
                ),
                "component_count": len(exploded),
            },
        }

    def inspect_catalog_pdf_price_list(
        self,
        *,
        source_filename: str,
        file_bytes: bytes,
    ) -> dict[str, Any]:
        if Path(self._safe(source_filename, "")).suffix.lower() != ".pdf":
            raise ValueError("PDF inspection requires a .pdf source file")
        file_hash = hashlib.sha1(file_bytes).hexdigest()
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
        except Exception:
            return {
                "source_filename": self._safe(source_filename),
                "source_hash": file_hash,
                "valid_pdf": False,
                "page_count": 0,
                "table_candidates": [],
                "diagnostics": [
                    {
                        "severity": "error",
                        "code": "malformed_pdf",
                        "message": "Malformed PDF could not be parsed.",
                        "row_number": None,
                    }
                ],
            }
        if getattr(reader, "is_encrypted", False):
            return {
                "source_filename": self._safe(source_filename),
                "source_hash": file_hash,
                "valid_pdf": True,
                "page_count": 0,
                "table_candidates": [],
                "diagnostics": [
                    {
                        "severity": "error",
                        "code": "encrypted_pdf",
                        "message": "Encrypted PDF is unsupported for import.",
                        "row_number": None,
                    }
                ],
            }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)
        try:
            intake = DocumentIntakeService(enable_local_ocr=True)
            pages, intake_warnings, _status = intake._extract_document_pages(
                tmp_path,
                "schedules",
            )
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

        diagnostics: list[dict[str, Any]] = []
        for warning in intake_warnings:
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "extraction_warning",
                    "message": self._safe(warning),
                    "row_number": None,
                }
            )

        table_candidates = self._pdf_table_candidates(pages)
        if not table_candidates:
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "no_table_candidate_found",
                    "message": "No table candidate found in selected PDF.",
                    "row_number": None,
                }
            )
        if len(table_candidates) > 1:
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "multiple_table_candidates_found",
                    "message": "Multiple table candidates detected; selection required.",
                    "row_number": None,
                }
            )
        return {
            "source_filename": self._safe(source_filename),
            "source_hash": file_hash,
            "valid_pdf": True,
            "page_count": len(reader.pages),
            "table_candidates": table_candidates,
            "diagnostics": diagnostics,
        }

    def preview_catalog_pdf_price_list_import(
        self,
        *,
        source_filename: str,
        file_bytes: bytes,
        selected_pages: list[int],
        table_candidate_id: str,
        header_row_index: int,
        column_mapping: dict[str, str],
        imported_by: str,
    ) -> dict[str, Any]:
        inspected = self.inspect_catalog_pdf_price_list(
            source_filename=source_filename,
            file_bytes=file_bytes,
        )
        candidates = list(inspected.get("table_candidates") or [])
        candidate = next(
            (
                item
                for item in candidates
                if self._safe(item.get("candidate_id"), "")
                == self._safe(table_candidate_id, "")
            ),
            None,
        )
        if candidate is None:
            raise ValueError("selected table candidate was not found")
        page_set = {
            int(value) for value in list(selected_pages or []) if int(value) > 0
        }
        if not page_set:
            raise ValueError("at least one selected page is required")
        rows = [
            dict(item)
            for item in list(candidate.get("rows") or [])
            if int(item.get("page_number", 0) or 0) in page_set
        ]
        if not rows:
            raise ValueError("no rows found for selected pages and candidate")

        header_index = max(0, min(int(header_row_index), len(rows) - 1))
        header_cells = [
            self._safe(cell) for cell in list(rows[header_index].get("cells") or [])
        ]
        mapping = {
            self._safe(target): self._safe(source)
            for target, source in dict(column_mapping or {}).items()
            if self._safe(target) and self._safe(source)
        }
        required_fields = {"code", "name"}
        diagnostics = list(inspected.get("diagnostics") or [])
        missing_required = [
            field for field in sorted(required_fields) if field not in mapping
        ]
        if missing_required:
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "missing_required_mapping",
                    "message": f"Missing required mapping fields: {', '.join(missing_required)}",
                    "row_number": None,
                }
            )

        preview_rows: list[dict[str, Any]] = []
        rejected_rows: list[dict[str, Any]] = []
        for idx, row in enumerate(rows):
            if idx == header_index:
                continue
            cells = [self._safe(cell) for cell in list(row.get("cells") or [])]
            cell_map = {
                header_cells[col_idx]: (cells[col_idx] if col_idx < len(cells) else "")
                for col_idx in range(len(header_cells))
                if header_cells[col_idx]
            }
            normalized: dict[str, Any] = {
                target: self._safe(cell_map.get(source), "")
                for target, source in mapping.items()
            }
            normalized["source_page_number"] = int(row.get("page_number", 0) or 0)
            normalized["source_row_reference"] = self._safe(
                row.get("row_reference"), ""
            )
            row_errors: list[str] = []
            if not self._safe(normalized.get("code"), ""):
                row_errors.append("missing code")
            if not self._safe(normalized.get("name"), ""):
                row_errors.append("missing name")
            if (
                self._safe(normalized.get("cost"), "")
                and self._float_or_none(normalized.get("cost")) is None
            ):
                row_errors.append("invalid cost")
            if (
                self._safe(normalized.get("msrp"), "")
                and self._float_or_none(normalized.get("msrp")) is None
            ):
                row_errors.append("invalid msrp")

            if row_errors:
                rejected_rows.append(
                    {
                        "row_number": int(
                            row.get("sequence_number", idx + 1) or idx + 1
                        ),
                        "source_page_number": normalized["source_page_number"],
                        "errors": row_errors,
                        "raw_values": dict(cell_map),
                    }
                )
                diagnostics.append(
                    {
                        "severity": "warning",
                        "code": "row_rejected",
                        "message": f"Row rejected: {', '.join(row_errors)}",
                        "row_number": int(
                            row.get("sequence_number", idx + 1) or idx + 1
                        ),
                    }
                )
            else:
                preview_rows.append(normalized)

        preview_id = self._catalog_price_list_preview_id(
            source_filename=self._safe(source_filename),
            source_hash=self._safe(inspected.get("source_hash"), ""),
            imported_by=self._safe(imported_by, "atlas"),
        )
        duplicate_versions = self.catalog_price_list_versions_by_hash(
            self._safe(inspected.get("source_hash"), "")
        )
        if duplicate_versions:
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "duplicate_source_hash",
                    "message": "Source file hash already exists in catalog import versions.",
                    "row_number": None,
                }
            )
        rejected_csv = self._rows_to_csv(
            [
                {
                    "row_number": row["row_number"],
                    "source_page_number": row["source_page_number"],
                    "errors": "; ".join(list(row.get("errors") or [])),
                }
                for row in rejected_rows
            ]
        )
        preview = {
            "preview_id": preview_id,
            "source_filename": self._safe(source_filename),
            "source_hash": self._safe(inspected.get("source_hash"), ""),
            "imported_by": self._safe(imported_by, "atlas"),
            "selected_pages": sorted(page_set),
            "table_candidate_id": self._safe(table_candidate_id),
            "header_row_index": header_index,
            "column_mapping": dict(mapping),
            "accepted_rows": preview_rows,
            "rejected_rows": rejected_rows,
            "rejected_rows_csv": rejected_csv,
            "diagnostics": diagnostics,
            "created_at": self._now_iso(),
            "status": "preview",
        }
        self.state.setdefault("price_list_import_previews", {})[preview_id] = preview
        return dict(preview)

    def finalize_catalog_pdf_price_list_import(
        self,
        *,
        preview_id: str,
        imported_by: str,
    ) -> dict[str, Any]:
        preview = dict(
            self.state.setdefault("price_list_import_previews", {}).get(
                self._safe(preview_id), {}
            )
        )
        if not preview:
            raise ValueError("price list preview was not found")
        if self._safe(preview.get("status"), "") == "finalized":
            raise ValueError("price list preview already finalized")

        inserted = 0
        updated = 0
        rejected = len(list(preview.get("rejected_rows") or []))
        for row in list(preview.get("accepted_rows") or []):
            upserted = self._upsert_catalog_item_from_row(
                item_type=CatalogItemType.PRODUCT.value,
                row={
                    **dict(row),
                    "source": "pdf_price_list_import",
                },
            )
            inserted += 1 if upserted["is_insert"] else 0
            updated += 0 if upserted["is_insert"] else 1

        version = {
            "catalog_price_list_version_id": self._catalog_price_list_version_id(
                source_hash=self._safe(preview.get("source_hash"), ""),
                created_at=self._now_iso(),
            ),
            "source_filename": self._safe(preview.get("source_filename"), ""),
            "source_hash": self._safe(preview.get("source_hash"), ""),
            "imported_by": self._safe(imported_by, "atlas"),
            "created_at": self._now_iso(),
            "inserted": inserted,
            "updated": updated,
            "rejected": rejected,
            "accepted_row_count": len(list(preview.get("accepted_rows") or [])),
            "rejected_row_count": rejected,
            "preview_id": self._safe(preview_id),
            "immutable": True,
            "snapshot": {
                "selected_pages": list(preview.get("selected_pages") or []),
                "table_candidate_id": self._safe(preview.get("table_candidate_id"), ""),
                "column_mapping": dict(preview.get("column_mapping") or {}),
                "accepted_rows": [
                    dict(item) for item in list(preview.get("accepted_rows") or [])
                ],
            },
        }
        self.state.setdefault("catalog_price_list_versions", {})[
            version["catalog_price_list_version_id"]
        ] = version
        preview["status"] = "finalized"
        preview["finalized_at"] = self._now_iso()
        self.state["price_list_import_previews"][self._safe(preview_id)] = preview

        return {
            "version": dict(version),
            "inserted": inserted,
            "updated": updated,
            "rejected": rejected,
            "partial_success": rejected > 0,
            "rejected_rows_csv": self._safe(preview.get("rejected_rows_csv"), ""),
            "diagnostics": list(preview.get("diagnostics") or []),
        }

    def list_catalog_price_list_versions(self) -> list[dict[str, Any]]:
        rows = [
            dict(item)
            for item in self.state.setdefault(
                "catalog_price_list_versions", {}
            ).values()
            if isinstance(item, dict)
        ]
        rows.sort(key=lambda item: self._safe(item.get("created_at"), ""), reverse=True)
        return rows

    def catalog_price_list_versions_by_hash(
        self, source_hash: str
    ) -> list[dict[str, Any]]:
        digest = self._safe(source_hash, "")
        return [
            dict(item)
            for item in self.list_catalog_price_list_versions()
            if self._safe(item.get("source_hash"), "") == digest
        ]

    def import_catalog_entities(
        self,
        *,
        source_filename: str,
        file_bytes: bytes,
        entity_type: str,
        imported_by: str,
    ) -> dict[str, Any]:
        rows = self._parse_tabular_rows(
            source_filename=source_filename,
            file_bytes=file_bytes,
        )
        return self.import_catalog_entities_from_rows(
            entity_type=entity_type,
            rows=rows,
            imported_by=imported_by,
            source_filename=source_filename,
        )

    def import_catalog_entities_from_rows(
        self,
        *,
        entity_type: str,
        rows: list[dict[str, Any]],
        imported_by: str,
        source_filename: str,
    ) -> dict[str, Any]:
        normalized_type = self._safe(entity_type, "").lower()
        if normalized_type not in {
            "manufacturers",
            "vendors",
            "products",
            "services",
            "fees",
            "assemblies",
            "assembly_components",
        }:
            raise ValueError("unsupported entity_type")

        inserted = 0
        updated = 0
        rejected = 0
        warnings: list[str] = []
        for index, row in enumerate(list(rows or []), start=1):
            normalized_row = {
                self._safe(key, "").lower(): value
                for key, value in dict(row or {}).items()
            }
            try:
                if normalized_type == "manufacturers":
                    is_insert = self._upsert_manufacturer(normalized_row)
                    inserted += 1 if is_insert else 0
                    updated += 0 if is_insert else 1
                elif normalized_type == "vendors":
                    is_insert = self._upsert_vendor(normalized_row)
                    inserted += 1 if is_insert else 0
                    updated += 0 if is_insert else 1
                elif normalized_type == "assembly_components":
                    is_insert = self._upsert_assembly_component_from_row(normalized_row)
                    inserted += 1 if is_insert else 0
                    updated += 0 if is_insert else 1
                else:
                    item_type = {
                        "products": CatalogItemType.PRODUCT.value,
                        "services": CatalogItemType.SERVICE.value,
                        "fees": CatalogItemType.FEE.value,
                        "assemblies": CatalogItemType.ASSEMBLY.value,
                    }[normalized_type]
                    upserted = self._upsert_catalog_item_from_row(
                        item_type=item_type,
                        row=normalized_row,
                    )
                    inserted += 1 if upserted["is_insert"] else 0
                    updated += 0 if upserted["is_insert"] else 1
            except ValueError as exc:
                rejected += 1
                warnings.append(f"row {index}: {exc}")

        summary = {
            "entity_type": normalized_type,
            "source_filename": self._safe(source_filename, "upload"),
            "imported_by": self._safe(imported_by, "atlas"),
            "imported_at": self._now_iso(),
            "rows_received": len(list(rows or [])),
            "inserted": inserted,
            "updated": updated,
            "rejected": rejected,
            "warnings": warnings,
        }
        self.state["catalog_import_history"].append(summary)
        return dict(summary)

    def _normalized_state(self, state: dict[str, Any]) -> dict[str, Any]:
        normalized = self.empty_state()
        for key in normalized:
            candidate = state.get(key)
            if isinstance(candidate, dict):
                normalized[key] = dict(candidate)
            elif isinstance(candidate, list):
                normalized[key] = list(candidate)
        return normalized

    def _records_for_version(self, version_id: str) -> list[dict[str, Any]]:
        if not version_id:
            return []
        return [
            dict(item)
            for item in self.state["price_records"].values()
            if self._safe(item.get("version_id"), "") == version_id
        ]

    def _compare_versions(
        self,
        previous: dict[str, dict[str, Any]],
        current: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        prev_keys = set(previous.keys())
        curr_keys = set(current.keys())

        added = sorted(curr_keys - prev_keys)
        removed = sorted(prev_keys - curr_keys)

        updated: list[dict[str, Any]] = []
        unchanged: list[str] = []
        price_increased: list[dict[str, Any]] = []
        price_decreased: list[dict[str, Any]] = []
        description_changed: list[str] = []
        lead_time_changed: list[str] = []
        availability_changed: list[str] = []
        vendor_sku_changed: list[str] = []
        warnings: list[str] = []

        for key in sorted(curr_keys & prev_keys):
            old = previous[key]
            new = current[key]
            changes: list[str] = []

            old_cost = self._float_or_none(old.get("cost"))
            new_cost = self._float_or_none(new.get("cost"))
            if old_cost is not None and new_cost is not None and old_cost != new_cost:
                if new_cost > old_cost:
                    price_increased.append(
                        {
                            "product": key,
                            "old_cost": old_cost,
                            "new_cost": new_cost,
                            "delta": round(new_cost - old_cost, 4),
                        }
                    )
                    changes.append("price_increased")
                elif new_cost < old_cost:
                    price_decreased.append(
                        {
                            "product": key,
                            "old_cost": old_cost,
                            "new_cost": new_cost,
                            "delta": round(new_cost - old_cost, 4),
                        }
                    )
                    changes.append("price_decreased")

            if self._safe(old.get("description"), "") != self._safe(
                new.get("description"), ""
            ):
                description_changed.append(key)
                changes.append("description_changed")
            if self._safe(old.get("lead_time"), "") != self._safe(
                new.get("lead_time"), ""
            ):
                lead_time_changed.append(key)
                changes.append("lead_time_changed")
            if self._safe(old.get("availability"), "") != self._safe(
                new.get("availability"), ""
            ):
                availability_changed.append(key)
                changes.append("availability_changed")
            if self._safe(old.get("vendor_sku"), "") != self._safe(
                new.get("vendor_sku"), ""
            ):
                vendor_sku_changed.append(key)
                changes.append("vendor_sku_changed")

            if changes:
                updated.append({"product": key, "changes": changes})
            else:
                unchanged.append(key)

        if removed:
            warnings.append(
                f"{len(removed)} products missing from latest version; lifecycle set to missing_from_latest_price_sheet."
            )

        return {
            "products_added": added,
            "products_removed": removed,
            "products_updated": updated,
            "products_unchanged": unchanged,
            "price_increased": price_increased,
            "price_decreased": price_decreased,
            "description_changed": description_changed,
            "lead_time_changed": lead_time_changed,
            "availability_changed": availability_changed,
            "vendor_sku_changed": vendor_sku_changed,
            "warnings": warnings,
        }

    def _apply_product_lifecycle(
        self,
        current_products: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        updates: list[dict[str, Any]] = []
        current_keys = set(current_products.keys())
        known_products = set(self.state["product_history"].keys())

        for product in sorted(known_products):
            prior = dict(self.state["product_lifecycle"].get(product) or {})
            old_status = self._safe(
                prior.get("lifecycle_status"),
                CommercialProductLifecycleStatus.UNKNOWN.value,
            )
            if product in current_keys:
                if old_status in {
                    CommercialProductLifecycleStatus.CONFIRMED_DISCONTINUED.value,
                    CommercialProductLifecycleStatus.OBSOLETE.value,
                }:
                    new_status = old_status
                else:
                    new_status = CommercialProductLifecycleStatus.ACTIVE.value
            else:
                new_status = (
                    CommercialProductLifecycleStatus.MISSING_FROM_LATEST_PRICE_SHEET.value
                )
            self.state["product_lifecycle"][product] = {
                "product": product,
                "lifecycle_status": new_status,
                "last_updated": self._now_iso(),
            }
            if new_status != old_status:
                updates.append(
                    {
                        "product": product,
                        "from": old_status,
                        "to": new_status,
                    }
                )
        return updates

    def _freshness_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for product, entry in self.state["product_history"].items():
            last_updated = self._safe(entry.get("last_updated"), "")
            last_date = self._date_from_iso(last_updated)
            days_since = (
                9999 if last_date is None else max((self._as_of - last_date).days, 0)
            )

            latest_version = self._safe(entry.get("latest_version"), "")
            lifecycle = self._safe(
                (self.state["product_lifecycle"].get(product) or {}).get(
                    "lifecycle_status"
                ),
                CommercialProductLifecycleStatus.UNKNOWN.value,
            )

            if not latest_version:
                status = KnowledgeFreshnessStatus.MISSING.value
            elif days_since > 365:
                status = KnowledgeFreshnessStatus.STALE.value
            elif days_since > 180:
                status = KnowledgeFreshnessStatus.REVIEW_RECOMMENDED.value
            else:
                status = KnowledgeFreshnessStatus.FRESH.value

            rows.append(
                {
                    "product": product,
                    "last_updated": last_updated,
                    "days_since_import": days_since,
                    "latest_version": latest_version,
                    "current_version": latest_version,
                    "current_status": status,
                    "lifecycle_status": lifecycle,
                }
            )
        return rows

    def _build_change_report(
        self,
        *,
        version: dict[str, Any],
        comparison: dict[str, Any],
        freshness_rows: list[dict[str, Any]],
        lifecycle_updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        increases = list(comparison.get("price_increased") or [])
        decreases = list(comparison.get("price_decreased") or [])
        stale_products = [
            item["product"]
            for item in freshness_rows
            if self._safe(item.get("current_status"), "")
            == KnowledgeFreshnessStatus.STALE.value
        ]
        products_missing_now = [
            item["product"]
            for item in lifecycle_updates
            if self._safe(item.get("to"), "")
            == CommercialProductLifecycleStatus.MISSING_FROM_LATEST_PRICE_SHEET.value
        ]

        largest_increase = (
            max(increases, key=lambda item: float(item["delta"])) if increases else None
        )
        largest_decrease = (
            min(decreases, key=lambda item: float(item["delta"])) if decreases else None
        )

        products_requiring_review = sorted(
            set(products_missing_now)
            | set(stale_products)
            | {
                item["product"]
                for item in list(comparison.get("products_updated") or [])
                if item.get("changes")
            }
        )

        return {
            "generated_at": self._now_iso(),
            "version_id": self._safe(version.get("version_id"), ""),
            "version_name": self._safe(version.get("version_name"), ""),
            "products_added": list(comparison.get("products_added") or []),
            "products_removed": list(comparison.get("products_removed") or []),
            "price_increases": increases,
            "price_decreases": decreases,
            "largest_increase": largest_increase,
            "largest_decrease": largest_decrease,
            "products_now_missing": products_missing_now,
            "products_becoming_stale": stale_products,
            "products_requiring_review": products_requiring_review,
        }

    def _update_product_history(
        self,
        *,
        product: str,
        vendor: str,
        manufacturer: str,
        version_id: str,
        record: dict[str, Any],
        import_date: str,
    ) -> None:
        history = dict(self.state["product_history"].get(product) or {})
        known_vendors = set(history.get("known_vendors") or [])
        known_vendors.add(vendor)

        historical_prices = list(history.get("historical_prices") or [])
        historical_prices.append(
            {
                "version_id": version_id,
                "vendor": vendor,
                "cost": self._float_or_none(record.get("cost")),
                "list_price": self._float_or_none(record.get("list_price")),
                "currency": self._safe(record.get("currency"), "USD"),
                "effective_date": self._safe(record.get("effective_date"), ""),
                "expiration_date": self._safe(record.get("expiration_date"), ""),
                "import_date": import_date,
            }
        )

        offering_id = self._vendor_offering_id(
            vendor=vendor,
            product=product,
            vendor_sku=self._safe(record.get("vendor_sku"), "UNKNOWN-SKU"),
        )
        historical_offerings = list(history.get("historical_vendor_offerings") or [])
        if offering_id not in historical_offerings:
            historical_offerings.append(offering_id)

        versions = list(history.get("historical_versions") or [])
        if version_id not in versions:
            versions.append(version_id)

        history.update(
            {
                "product": product,
                "manufacturer": manufacturer,
                "known_vendors": sorted(known_vendors),
                "historical_prices": historical_prices,
                "historical_vendor_offerings": historical_offerings,
                "last_updated": import_date,
                "latest_version": version_id,
                "historical_versions": versions,
                "engineering_usage": list(history.get("engineering_usage") or []),
                "referenced_projects": list(history.get("referenced_projects") or []),
            }
        )
        self.state["product_history"][product] = history

    def _is_rule_effective(self, *, rule: dict[str, Any], as_of: date) -> bool:
        effective = self._date_from_iso(self._safe(rule.get("effective_date"), ""))
        expiration = self._date_from_iso(self._safe(rule.get("expiration_date"), ""))
        if effective is not None and as_of < effective:
            return False
        if expiration is not None and as_of > expiration:
            return False
        return True

    @staticmethod
    def _catalog_item_id(item_type: str, code: str) -> str:
        digest = hashlib.sha1(
            f"{item_type}|{code.strip().upper()}".encode("utf-8")
        ).hexdigest()[:16]
        return f"catalog-item:{digest}"

    @staticmethod
    def _assembly_version_id(assembly_item_id: str, version_number: int) -> str:
        return f"{assembly_item_id}:assembly-v{version_number}"

    @staticmethod
    def _assembly_component_id(
        *,
        assembly_item_id: str,
        component_item_id: str,
        sequence: int,
    ) -> str:
        digest = hashlib.sha1(
            f"{assembly_item_id}|{component_item_id}|{sequence}".encode("utf-8")
        ).hexdigest()[:12]
        return f"assembly-component:{digest}"

    def _next_assembly_version_number(self, assembly_item_id: str) -> int:
        lineage = list(
            self.state.setdefault("assembly_version_lineage", {}).get(assembly_item_id)
            or []
        )
        return len(lineage) + 1

    def _assert_no_assembly_cycle(
        self,
        *,
        root_assembly_item_id: str,
        components: list[dict[str, Any]],
    ) -> None:
        for component in components:
            component_item_id = self._safe(component.get("component_item_id"), "")
            if component_item_id == root_assembly_item_id:
                raise ValueError("assembly circular reference detected")
            component_item = self.catalog_item(component_item_id)
            if component_item is None:
                continue
            if (
                self._safe(component_item.get("item_type"), "")
                != CatalogItemType.ASSEMBLY.value
            ):
                continue
            nested = self.latest_assembly_version(component_item_id)
            if nested is None:
                continue
            for nested_component in list(nested.get("components") or []):
                nested_item_id = self._safe(
                    nested_component.get("component_item_id"), ""
                )
                if nested_item_id == root_assembly_item_id:
                    raise ValueError("assembly circular reference detected")

    def _assembly_rollup(
        self,
        *,
        assembly_item_id: str,
        components: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total_cost = 0.0
        total_sales_price = 0.0
        for row in components:
            component_item_id = self._safe(row.get("component_item_id"), "")
            component_item = self.catalog_item(component_item_id)
            if component_item is None:
                continue
            quantity = max(0.0, float(row.get("quantity", 0.0) or 0.0))
            if (
                self._safe(component_item.get("item_type"), "")
                == CatalogItemType.ASSEMBLY.value
            ):
                nested_version = self.latest_assembly_version(component_item_id)
                if nested_version is None:
                    continue
                nested_expansion = self.expand_assembly(
                    assembly_item_id=component_item_id,
                    quantity=quantity,
                    assembly_version_id=self._safe(
                        nested_version.get("assembly_version_id"), ""
                    )
                    or None,
                )
                total_cost += float(nested_expansion.get("total_cost", 0.0) or 0.0)
                total_sales_price += float(
                    nested_expansion.get("total_sales_price", 0.0) or 0.0
                )
                continue
            item_cost = self._float_or_none(component_item.get("cost")) or 0.0
            item_sales = (
                self._float_or_none(component_item.get("default_sales_price"))
                or self._float_or_none(component_item.get("manual_unit_price"))
                or self._float_or_none(component_item.get("msrp"))
                or item_cost
            )
            total_cost += quantity * item_cost
            total_sales_price += quantity * item_sales
        return {
            "assembly_item_id": assembly_item_id,
            "total_cost": round(max(0.0, total_cost), 4),
            "total_sales_price": round(max(0.0, total_sales_price), 4),
        }

    def _expand_assembly_recursive(
        self,
        *,
        assembly_item_id: str,
        assembly_version: dict[str, Any],
        root_multiplier: float,
        include_optional: bool,
        exploded: list[dict[str, Any]],
        traversal_stack: list[str],
        parent_path: str,
    ) -> None:
        components = [
            dict(item) for item in list(assembly_version.get("components") or [])
        ]
        components.sort(
            key=lambda item: (
                int(item.get("sequence", 1) or 1),
                self._safe(item.get("component_id"), ""),
            )
        )
        for component in components:
            if not include_optional and not bool(component.get("required", True)):
                continue
            component_item_id = self._safe(component.get("component_item_id"), "")
            component_item = self.catalog_item(component_item_id)
            if component_item is None:
                continue
            quantity = round(
                float(component.get("quantity", 0.0) or 0.0) * root_multiplier,
                6,
            )
            if (
                self._safe(component_item.get("item_type"), "")
                == CatalogItemType.ASSEMBLY.value
            ):
                if component_item_id in traversal_stack:
                    raise ValueError("assembly circular reference detected")
                nested_version = self.latest_assembly_version(component_item_id)
                if nested_version is None:
                    continue
                self._expand_assembly_recursive(
                    assembly_item_id=component_item_id,
                    assembly_version=nested_version,
                    root_multiplier=quantity,
                    include_optional=include_optional,
                    exploded=exploded,
                    traversal_stack=[*traversal_stack, component_item_id],
                    parent_path=f"{parent_path}>{self._safe(component_item.get('code'), component_item_id)}",
                )
                continue

            item_cost = self._float_or_none(component_item.get("cost")) or 0.0
            unit_price = (
                self._float_or_none(component_item.get("default_sales_price"))
                or self._float_or_none(component_item.get("manual_unit_price"))
                or self._float_or_none(component_item.get("msrp"))
                or item_cost
            )
            exploded.append(
                {
                    "assembly_item_id": assembly_item_id,
                    "component_item_id": component_item_id,
                    "component_code": self._safe(component_item.get("code"), ""),
                    "component_name": self._safe(component_item.get("name"), ""),
                    "component_item_type": self._safe(
                        component_item.get("item_type"), ""
                    ),
                    "quantity": quantity,
                    "required": bool(component.get("required", True)),
                    "sequence": int(component.get("sequence", 1) or 1),
                    "path": f"{parent_path}>{self._safe(component_item.get('code'), component_item_id)}",
                    "unit_cost": round(item_cost, 4),
                    "unit_sales_price": round(unit_price, 4),
                    "extended_cost": round(quantity * item_cost, 4),
                    "extended_sales_price": round(quantity * unit_price, 4),
                }
            )

    def _pdf_table_candidates(
        self, pages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for page in list(pages or []):
            page_number = int(page.get("page_number", 0) or 0)
            text = self._safe(page.get("text"), "")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            rows: list[dict[str, Any]] = []
            for idx, line in enumerate(lines, start=1):
                cells = self._split_pdf_line_cells(line)
                if len(cells) < 3:
                    continue
                rows.append(
                    {
                        "sequence_number": idx,
                        "page_number": page_number,
                        "row_reference": f"p{page_number}:row{idx}",
                        "cells": cells,
                    }
                )
            if len(rows) < 2:
                continue
            signature = "|".join(rows[0]["cells"])[:240]
            candidate_id = f"pdf-candidate:{hashlib.sha1(signature.encode('utf-8')).hexdigest()[:12]}"
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "page_numbers": [page_number],
                    "header_preview": rows[0]["cells"],
                    "row_count": len(rows),
                    "rows": rows,
                }
            )
        return candidates

    @staticmethod
    def _split_pdf_line_cells(line: str) -> list[str]:
        parts = [segment.strip() for segment in line.replace("\t", "  ").split("  ")]
        return [segment for segment in parts if segment]

    @staticmethod
    def _catalog_price_list_preview_id(
        *,
        source_filename: str,
        source_hash: str,
        imported_by: str,
    ) -> str:
        digest = hashlib.sha1(
            f"{source_filename}|{source_hash}|{imported_by}".encode("utf-8")
        ).hexdigest()[:16]
        return f"catalog-price-preview:{digest}"

    @staticmethod
    def _catalog_price_list_version_id(*, source_hash: str, created_at: str) -> str:
        digest = hashlib.sha1(
            f"{source_hash}|{created_at}".encode("utf-8")
        ).hexdigest()[:16]
        return f"catalog-price-version:{digest}"

    @staticmethod
    def _rows_to_csv(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return ""
        headers = sorted({key for row in rows for key in row.keys()})
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in headers})
        return buffer.getvalue()

    @staticmethod
    def _tax_rule_id(*, nexus: str, title: str, priority: int) -> str:
        digest = hashlib.sha1(
            f"{nexus.strip().lower()}|{title.strip().lower()}|{priority}".encode(
                "utf-8"
            )
        ).hexdigest()[:16]
        return f"tax-nexus-rule:{digest}"

    def _upsert_manufacturer(self, row: dict[str, Any]) -> bool:
        code = self._safe(row.get("manufacturer_code"), "") or self._safe(
            row.get("code"), ""
        )
        name = self._safe(row.get("manufacturer_name"), "") or self._safe(
            row.get("name"), ""
        )
        if not code or not name:
            raise ValueError("manufacturer imports require code and name")
        key = code.upper()
        is_insert = key not in self.state["manufacturers"]
        provenance_payload = row.get("provenance")
        self.state["manufacturers"][key] = {
            "manufacturer_code": key,
            "manufacturer_name": name,
            "website": self._safe(row.get("website"), "") or None,
            "status": self._safe(row.get("status"), "active") or "active",
            "source": self._safe(row.get("source"), "catalog_import")
            or "catalog_import",
            "provenance": (
                dict(provenance_payload) if isinstance(provenance_payload, dict) else {}
            ),
            "updated_at": self._now_iso(),
        }
        return is_insert

    def _upsert_vendor(self, row: dict[str, Any]) -> bool:
        code = self._safe(row.get("vendor_code"), "") or self._safe(row.get("code"), "")
        name = self._safe(row.get("vendor_name"), "") or self._safe(row.get("name"), "")
        if not code or not name:
            raise ValueError("vendor imports require code and name")
        key = code.upper()
        is_insert = key not in self.state["vendors"]
        provenance_payload = row.get("provenance")
        self.state["vendors"][key] = {
            "vendor_code": key,
            "vendor_name": name,
            "vendor_type": self._safe(row.get("vendor_type"), "other") or "other",
            "status": self._safe(row.get("status"), "active") or "active",
            "source": self._safe(row.get("source"), "catalog_import")
            or "catalog_import",
            "provenance": (
                dict(provenance_payload) if isinstance(provenance_payload, dict) else {}
            ),
            "updated_at": self._now_iso(),
        }
        return is_insert

    def _upsert_catalog_item_from_row(
        self,
        *,
        item_type: str,
        row: dict[str, Any],
    ) -> dict[str, Any]:
        code = self._safe(row.get("code"), "") or self._safe(row.get("sku"), "")
        name = self._safe(row.get("name"), "") or self._safe(row.get("description"), "")
        if not code or not name:
            raise ValueError("catalog imports require code and name")
        item_id = self._catalog_item_id(item_type, code)
        is_insert = item_id not in self.state["catalog_items"]
        self.upsert_catalog_item(
            catalog_item_id=item_id,
            item_type=item_type,
            code=code,
            name=name,
            description=self._safe(row.get("description"), ""),
            long_description=self._safe(row.get("long_description"), ""),
            manufacturer=self._safe(row.get("manufacturer"), "") or None,
            vendor=self._safe(row.get("vendor"), "") or None,
            uom=self._safe(row.get("uom"), "ea"),
            category=self._safe(row.get("category"), ""),
            family=self._safe(row.get("family"), ""),
            status=self._safe(row.get("status"), "active"),
            tax_category=self._safe(row.get("tax_category"), "standard"),
            cost=self._float_or_none(row.get("cost") or row.get("unit_cost")),
            msrp=self._float_or_none(row.get("msrp") or row.get("list_price")),
            map_price=self._float_or_none(row.get("map") or row.get("map_price")),
            default_sales_price=self._float_or_none(
                row.get("default_sales_price") or row.get("unit_price")
            ),
            manual_unit_price=self._float_or_none(row.get("manual_unit_price")),
            taxable=self._safe(row.get("taxable"), "true").lower()
            not in {"0", "false", "no"},
            default_tax_nexus=self._safe(row.get("default_tax_nexus"), "") or None,
            notes=self._safe(row.get("notes"), ""),
            tags=[
                self._safe(item)
                for item in self._safe(row.get("tags"), "").split("|")
                if self._safe(item)
            ],
            source=self._safe(row.get("source"), "catalog_import"),
            provenance={
                "import_type": "catalog_rows",
                "source_row_reference": self._safe(row.get("source_row_reference"), ""),
                "source_page_number": self._safe(row.get("source_page_number"), ""),
            },
            metadata={
                "source": self._safe(row.get("source"), "catalog_import"),
                "raw_row": dict(row),
            },
            archived=self._safe(row.get("archived"), "false").lower()
            in {"1", "true", "yes"},
        )
        return {"catalog_item_id": item_id, "is_insert": is_insert}

    def _upsert_assembly_component_from_row(self, row: dict[str, Any]) -> bool:
        assembly_code = self._safe(row.get("assembly_code"), "")
        component_code = self._safe(row.get("component_code"), "")
        if not assembly_code or not component_code:
            raise ValueError(
                "assembly component imports require assembly_code and component_code"
            )
        assembly_id = self._catalog_item_id(
            CatalogItemType.ASSEMBLY.value, assembly_code
        )
        component_item_id = (
            self._catalog_item_id(CatalogItemType.PRODUCT.value, component_code)
            if self.catalog_item(
                self._catalog_item_id(CatalogItemType.PRODUCT.value, component_code)
            )
            else (
                self._catalog_item_id(CatalogItemType.SERVICE.value, component_code)
                if self.catalog_item(
                    self._catalog_item_id(CatalogItemType.SERVICE.value, component_code)
                )
                else (
                    self._catalog_item_id(CatalogItemType.FEE.value, component_code)
                    if self.catalog_item(
                        self._catalog_item_id(CatalogItemType.FEE.value, component_code)
                    )
                    else self._catalog_item_id(
                        CatalogItemType.ASSEMBLY.value, component_code
                    )
                )
            )
        )
        if self.catalog_item(assembly_id) is None:
            raise ValueError("assembly component import assembly was not found")
        if self.catalog_item(component_item_id) is None:
            raise ValueError("assembly component import component was not found")

        latest = self.latest_assembly_version(assembly_id)
        existing_components = (
            [dict(item) for item in list(latest.get("components") or [])]
            if latest
            else []
        )
        sequence = int(
            row.get("sequence", len(existing_components) + 1)
            or len(existing_components) + 1
        )
        required = self._safe(row.get("required"), "true").lower() not in {
            "0",
            "false",
            "no",
        }
        component_payload = {
            "component_item_id": component_item_id,
            "quantity": float(row.get("quantity", 1.0) or 1.0),
            "required": required,
            "sequence": sequence,
            "notes": self._safe(row.get("notes"), ""),
        }
        is_insert = True
        for existing in existing_components:
            if (
                self._safe(existing.get("component_item_id"), "") == component_item_id
                and int(existing.get("sequence", 0) or 0) == sequence
            ):
                is_insert = False
                existing.update(component_payload)
                break
        if is_insert:
            existing_components.append(component_payload)
        self.create_or_update_assembly_version(
            assembly_item_id=assembly_id,
            components=existing_components,
            expanded_description=self._safe(row.get("expanded_description"), ""),
        )
        return is_insert

    def _parse_tabular_rows(
        self,
        *,
        source_filename: str,
        file_bytes: bytes,
    ) -> list[dict[str, Any]]:
        lower_name = self._safe(source_filename, "").lower()
        if lower_name.endswith(".csv"):
            text = file_bytes.decode("utf-8-sig", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            return [dict(row) for row in reader]
        if lower_name.endswith(".xlsx"):
            return self._parse_xlsx_rows(file_bytes)
        raise ValueError("unsupported file format; expected .csv or .xlsx")

    def _parse_xlsx_rows(self, file_bytes: bytes) -> list[dict[str, Any]]:
        try:
            archive = zipfile.ZipFile(io.BytesIO(file_bytes))
        except zipfile.BadZipFile as exc:
            raise ValueError("invalid xlsx payload") from exc

        with archive:
            workbook_xml = archive.read("xl/workbook.xml")
            workbook = ET.fromstring(workbook_xml)
            workbook_ns = {
                "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            }
            rel_ns = {
                "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
            }
            relationship_xml = archive.read("xl/_rels/workbook.xml.rels")
            relationship_tree = ET.fromstring(relationship_xml)
            rels = {
                rel.attrib.get("Id"): rel.attrib.get("Target")
                for rel in relationship_tree
                if rel.attrib.get("Id") and rel.attrib.get("Target")
            }

            shared_strings = self._xlsx_shared_strings(archive)
            sheets = workbook.findall("x:sheets/x:sheet", workbook_ns)
            if not sheets:
                return []
            first_sheet = sheets[0]
            rel_id = first_sheet.attrib.get(f"{{{rel_ns['r']}}}id")
            target = rels.get(rel_id)
            if not target:
                return []
            normalized_target = target.lstrip("/")
            if not normalized_target.startswith("xl/"):
                normalized_target = f"xl/{normalized_target}"
            if normalized_target not in archive.namelist():
                return []
            worksheet = ET.fromstring(archive.read(normalized_target))
            sheet_data = worksheet.find("x:sheetData", workbook_ns)
            if sheet_data is None:
                return []

            matrix: list[list[str]] = []
            for row in sheet_data.findall("x:row", workbook_ns):
                values: list[str] = []
                for cell in row.findall("x:c", workbook_ns):
                    values.append(
                        self._xlsx_cell_text(cell, workbook_ns, shared_strings)
                    )
                matrix.append(values)
            if not matrix:
                return []
            header = [self._safe(item, "") for item in matrix[0]]
            data_rows: list[dict[str, Any]] = []
            for value_row in matrix[1:]:
                if not any(self._safe(value, "") for value in value_row):
                    continue
                payload: dict[str, Any] = {}
                for index, column in enumerate(header):
                    if not column:
                        continue
                    payload[column] = value_row[index] if index < len(value_row) else ""
                data_rows.append(payload)
            return data_rows

    @staticmethod
    def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
        shared_path = "xl/sharedStrings.xml"
        if shared_path not in archive.namelist():
            return []
        tree = ET.fromstring(archive.read(shared_path))
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        values: list[str] = []
        for item in tree.findall("x:si", namespace):
            parts = [node.text or "" for node in item.findall(".//x:t", namespace)]
            values.append("".join(parts))
        return values

    @staticmethod
    def _xlsx_cell_text(
        cell: ET.Element,
        namespace: dict[str, str],
        shared_strings: list[str],
    ) -> str:
        raw_value = cell.find("x:v", namespace)
        if raw_value is None or raw_value.text is None:
            return ""
        value = raw_value.text
        if cell.attrib.get("t") == "s":
            try:
                index = int(value)
            except ValueError:
                return ""
            if 0 <= index < len(shared_strings):
                return shared_strings[index]
            return ""
        return value

    @staticmethod
    def _price_trend(history: list[dict[str, Any]]) -> str:
        costs = [
            float(item["cost"])
            for item in history
            if isinstance(item.get("cost"), (int, float))
        ]
        if len(costs) < 2:
            return "stable"
        if costs[-1] > costs[0]:
            return "up"
        if costs[-1] < costs[0]:
            return "down"
        return "stable"

    @staticmethod
    def _sheet_id(vendor: str, manufacturer: str, sheet_name: str) -> str:
        digest = hashlib.sha1(
            f"{vendor}|{manufacturer}|{sheet_name}".encode("utf-8")
        ).hexdigest()[:16]
        return f"price-sheet:{digest}"

    @staticmethod
    def _version_id(sheet_id: str, index: int) -> str:
        return f"{sheet_id}:v{index}"

    @staticmethod
    def _price_record_id(
        *, version_id: str, product: str, vendor_sku: str, source_row: int
    ) -> str:
        digest = hashlib.sha1(
            f"{version_id}|{product}|{vendor_sku}|{source_row}".encode("utf-8")
        ).hexdigest()[:16]
        return f"price-record:{digest}"

    @staticmethod
    def _vendor_offering_id(*, vendor: str, product: str, vendor_sku: str) -> str:
        digest = hashlib.sha1(
            f"{vendor}|{product}|{vendor_sku}".encode("utf-8")
        ).hexdigest()[:16]
        return f"vendor-offering:{digest}"

    def _normalized_row(
        self,
        row: dict[str, Any],
        *,
        vendor: str,
        manufacturer: str,
        source_row: int,
    ) -> dict[str, Any]:
        model = self._safe(row.get("model"), "")
        product = self._safe(row.get("product"), model)
        if product and "::" not in product:
            product = f"{manufacturer}::{product}"

        return {
            "vendor": self._safe(row.get("vendor"), vendor),
            "vendor_type": self._safe(row.get("vendor_type"), "other"),
            "manufacturer": self._safe(row.get("manufacturer"), manufacturer),
            "product": product,
            "vendor_sku": self._safe(
                row.get("vendor_sku"), self._safe(row.get("sku"), "UNKNOWN-SKU")
            ),
            "description": self._safe(row.get("description"), ""),
            "cost": self._float_or_none(row.get("unit_cost", row.get("cost"))),
            "list_price": self._float_or_none(row.get("list_price")),
            "currency": self._safe(row.get("currency"), "USD"),
            "lead_time": self._safe(row.get("lead_time"), "unknown"),
            "availability": self._safe(
                row.get("availability_status", row.get("availability")), "unknown"
            ),
            "effective_date": self._safe(row.get("effective_date"), ""),
            "expiration_date": self._safe(row.get("expiration_date"), ""),
            "confidence": self._bounded_confidence(row.get("confidence", 0.9)),
            "source_row": source_row,
            "unit_of_measure": self._safe(row.get("unit_of_measure"), "ea"),
            "pack_quantity": self._int_or_none(row.get("pack_quantity")),
            "minimum_order_quantity": self._int_or_none(
                row.get("minimum_order_quantity")
            ),
            "purchase_multiple": self._int_or_none(row.get("purchase_multiple")),
            "active": bool(row.get("active", True)),
            "notes": self._safe(row.get("notes"), ""),
        }

    @staticmethod
    def _bounded_confidence(value: Any) -> float:
        try:
            numeric = float(value)
        except Exception:
            return 0.9
        return round(max(0.0, min(1.0, numeric)), 4)

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return round(float(value), 4)
        text = str(value).strip().replace("$", "").replace(",", "")
        if not text:
            return None
        try:
            return round(float(text), 4)
        except ValueError:
            return None

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value.is_integer():
                return int(value)
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    @staticmethod
    def _safe(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _date_from_iso(value: str) -> date | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()

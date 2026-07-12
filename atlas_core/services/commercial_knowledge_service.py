"""Commercial knowledge service with immutable price sheet versioning."""

from __future__ import annotations

from datetime import UTC, date, datetime
import hashlib
import json
from typing import Any

from atlas_core.domain.commercial_knowledge import (
    CommercialProductLifecycleStatus,
    KnowledgeFreshnessStatus,
    PriceRecord,
    PriceSheet,
    PriceSheetVersion,
    VendorOffering,
)


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

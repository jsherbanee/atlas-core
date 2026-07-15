"""C-04 deterministic commercial catalog seed loader and reset utility."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from atlas_core.domain.commercial_document import ApprovalState, CommercialDocumentType
from atlas_core.sample_data.commercial_catalog_seed import (
    SEED_PACKAGE_ID,
    SEED_SOURCE,
    SEED_SOURCE_PREFIX,
    build_c04_seed_import_artifacts,
    build_c04_seed_payload,
)
from atlas_core.services.commercial_knowledge_service import CommercialKnowledgeService
from atlas_core.services.transactions_workspace_service import (
    TransactionsWorkspaceService,
)


class CommercialCatalogSeedService:
    """Loads and resets deterministic C-04 sample catalog data."""

    def __init__(self, catalog_service: CommercialKnowledgeService) -> None:
        self._catalog = catalog_service

    def is_seed_loaded(self, *, tenant_id: str) -> bool:
        target_tenant = self._safe(tenant_id)
        for item in self._catalog.list_catalog_items(include_archived=True):
            if self._safe(item.get("source")) != SEED_SOURCE:
                continue
            provenance = self._provenance(item)
            if self._safe(provenance.get("tenant_id")) == target_tenant:
                return True
        return False

    def load_seed_data(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        imported_by: str,
        force_reload: bool = False,
        enable_pdf_finalize: bool = False,
    ) -> dict[str, Any]:
        target_tenant = self._safe(tenant_id)
        target_org = self._safe(organization_id)
        actor = self._safe(imported_by, "atlas-seed")

        if force_reload:
            self.reset_seed_data(tenant_id=target_tenant)
        elif self.is_seed_loaded(tenant_id=target_tenant):
            return {
                "package_id": SEED_PACKAGE_ID,
                "tenant_id": target_tenant,
                "organization_id": target_org,
                "already_loaded": True,
                "seed_summary": self.seed_summary(tenant_id=target_tenant),
            }

        payload = build_c04_seed_payload()
        import_artifacts = build_c04_seed_import_artifacts()

        self._catalog.set_pricing_defaults(
            default_policy="cost_plus_percent",
            default_markup_percent=18.0,
            default_margin_percent=0.0,
            default_multiplier=1.0,
            default_tax_nexus="CA-LOSANGELES",
            currency="USD",
            rounding_policy="currency_2dp",
        )

        import_results: list[dict[str, Any]] = []
        for key in (
            "manufacturers_csv",
            "vendors_csv",
            "products_csv",
            "products_xlsx",
            "services_csv",
            "fees_csv",
            "assemblies_csv",
            "assembly_components_csv",
        ):
            spec = import_artifacts[key]
            if self._safe(spec.get("entity_type")) == "assembly_components":
                component_rows = payload["assembly_components"]
                import_results.append(
                    self._catalog.import_catalog_entities_from_rows(
                        entity_type="assembly_components",
                        rows=component_rows,
                        imported_by=actor,
                        source_filename=self._safe(
                            spec.get("filename"), "seed_components.csv"
                        ),
                    )
                )
                continue
            import_results.append(
                self._catalog.import_catalog_entities(
                    source_filename=self._safe(spec.get("filename"), "seed.csv"),
                    file_bytes=bytes(spec.get("content") or b""),
                    entity_type=self._safe(spec.get("entity_type"), ""),
                    imported_by=actor,
                )
            )

        seeded_catalog_ids = self._mark_seeded_catalog_items(
            tenant_id=target_tenant,
            organization_id=target_org,
            actor=actor,
        )
        self._mark_seeded_manufacturers_and_vendors(
            tenant_id=target_tenant,
            organization_id=target_org,
            actor=actor,
        )

        tax_results = self._load_tax_rules(
            tenant_id=target_tenant,
            organization_id=target_org,
            actor=actor,
            tax_rules=list(payload["tax_rules"]),
        )
        price_list_results = self._load_price_lists(
            actor=actor,
            tenant_id=target_tenant,
            organization_id=target_org,
            price_lists=list(payload["price_lists"]),
        )
        pdf_validation = self._validate_pdf_import(
            import_artifacts=import_artifacts,
            actor=actor,
            enable_pdf_finalize=enable_pdf_finalize,
        )

        return {
            "package_id": SEED_PACKAGE_ID,
            "source": SEED_SOURCE,
            "tenant_id": target_tenant,
            "organization_id": target_org,
            "already_loaded": False,
            "catalog_item_ids": seeded_catalog_ids,
            "import_results": import_results,
            "tax_results": tax_results,
            "price_list_results": price_list_results,
            "pdf_validation": pdf_validation,
            "seed_summary": self.seed_summary(tenant_id=target_tenant),
        }

    def seed_summary(self, *, tenant_id: str) -> dict[str, Any]:
        target_tenant = self._safe(tenant_id)
        items = [
            item
            for item in self._catalog.list_catalog_items(include_archived=True)
            if self._safe(item.get("source")) == SEED_SOURCE
            and self._safe(self._provenance(item).get("tenant_id")) == target_tenant
        ]
        products = [
            item for item in items if self._safe(item.get("item_type")) == "product"
        ]
        services = [
            item for item in items if self._safe(item.get("item_type")) == "service"
        ]
        fees = [item for item in items if self._safe(item.get("item_type")) == "fee"]
        assemblies = [
            item for item in items if self._safe(item.get("item_type")) == "assembly"
        ]

        manufacturers = [
            payload
            for payload in self._catalog.state.get("manufacturers", {}).values()
            if self._safe(self._provenance(payload).get("tenant_id")) == target_tenant
            and self._safe(payload.get("source")) == SEED_SOURCE
        ]
        vendors = [
            payload
            for payload in self._catalog.state.get("vendors", {}).values()
            if self._safe(self._provenance(payload).get("tenant_id")) == target_tenant
            and self._safe(payload.get("source")) == SEED_SOURCE
        ]
        tax_rules = [
            payload
            for payload in self._catalog.state.get("tax_nexus_rules", {}).values()
            if self._safe(self._provenance(payload).get("tenant_id")) == target_tenant
            and self._safe(payload.get("source")) == SEED_SOURCE
        ]

        seeded_sheet_ids = {
            self._safe(sheet.get("price_sheet_id"))
            for sheet in self._catalog.state.get("price_sheets", {}).values()
            if self._is_seeded_sheet(sheet, target_tenant)
        }
        seeded_version_ids = {
            self._safe(version.get("version_id"))
            for version in self._catalog.state.get("price_sheet_versions", {}).values()
            if self._safe(version.get("price_sheet_id")) in seeded_sheet_ids
        }
        seeded_offerings = [
            payload
            for payload in self._catalog.state.get("vendor_offerings", {}).values()
            if all(
                self._safe(version_id) in seeded_version_ids
                for version_id in list(payload.get("historical_versions") or [])
            )
            and list(payload.get("historical_versions") or [])
        ]
        return {
            "manufacturers": len(manufacturers),
            "vendors": len(vendors),
            "products": len(products),
            "services": len(services),
            "fees": len(fees),
            "assemblies": len(assemblies),
            "vendor_offerings": len(seeded_offerings),
            "price_sheets": len(seeded_sheet_ids),
            "price_sheet_versions": len(seeded_version_ids),
            "tax_rules": len(tax_rules),
            "archived_items": len(
                [item for item in items if bool(item.get("archived"))]
            ),
            "discontinued_items": len(
                [
                    item
                    for item in items
                    if self._safe(item.get("status")) == "discontinued"
                ]
            ),
        }

    def reset_seed_data(self, *, tenant_id: str) -> dict[str, Any]:
        target_tenant = self._safe(tenant_id)
        removed_counts = {
            "catalog_items": 0,
            "assembly_versions": 0,
            "manufacturers": 0,
            "vendors": 0,
            "tax_rules": 0,
            "price_records": 0,
            "price_sheet_versions": 0,
            "price_sheets": 0,
            "vendor_offerings": 0,
            "catalog_import_history": 0,
            "pdf_versions": 0,
            "pdf_previews": 0,
        }

        seeded_catalog_item_ids = {
            self._safe(item.get("catalog_item_id"))
            for item in self._catalog.list_catalog_items(include_archived=True)
            if self._safe(item.get("source")) == SEED_SOURCE
            and self._safe(self._provenance(item).get("tenant_id")) == target_tenant
        }
        for item_id in seeded_catalog_item_ids:
            if item_id in self._catalog.state.get("catalog_items", {}):
                del self._catalog.state["catalog_items"][item_id]
                removed_counts["catalog_items"] += 1

        assembly_versions = self._catalog.state.get("assembly_versions", {})
        assembly_lineage = self._catalog.state.get("assembly_version_lineage", {})
        for version_id, version in list(assembly_versions.items()):
            assembly_item_id = self._safe(version.get("assembly_item_id"))
            if assembly_item_id not in seeded_catalog_item_ids:
                continue
            del assembly_versions[version_id]
            removed_counts["assembly_versions"] += 1
        for assembly_item_id in list(assembly_lineage.keys()):
            if assembly_item_id in seeded_catalog_item_ids:
                del assembly_lineage[assembly_item_id]

        for key in list(self._catalog.state.get("manufacturers", {}).keys()):
            payload = self._catalog.state["manufacturers"][key]
            if self._safe(payload.get("source")) != SEED_SOURCE:
                continue
            if self._safe(self._provenance(payload).get("tenant_id")) != target_tenant:
                continue
            del self._catalog.state["manufacturers"][key]
            removed_counts["manufacturers"] += 1

        for key in list(self._catalog.state.get("vendors", {}).keys()):
            payload = self._catalog.state["vendors"][key]
            if self._safe(payload.get("source")) != SEED_SOURCE:
                continue
            if self._safe(self._provenance(payload).get("tenant_id")) != target_tenant:
                continue
            del self._catalog.state["vendors"][key]
            removed_counts["vendors"] += 1

        for key in list(self._catalog.state.get("tax_nexus_rules", {}).keys()):
            payload = self._catalog.state["tax_nexus_rules"][key]
            if self._safe(payload.get("source")) != SEED_SOURCE:
                continue
            if self._safe(self._provenance(payload).get("tenant_id")) != target_tenant:
                continue
            del self._catalog.state["tax_nexus_rules"][key]
            removed_counts["tax_rules"] += 1

        seeded_sheet_ids = {
            self._safe(sheet.get("price_sheet_id"))
            for sheet in self._catalog.state.get("price_sheets", {}).values()
            if self._is_seeded_sheet(sheet, target_tenant)
        }
        seeded_version_ids = {
            self._safe(version.get("version_id"))
            for version in self._catalog.state.get("price_sheet_versions", {}).values()
            if self._safe(version.get("price_sheet_id")) in seeded_sheet_ids
        }
        for key, record in list(self._catalog.state.get("price_records", {}).items()):
            if self._safe(record.get("version_id")) in seeded_version_ids:
                del self._catalog.state["price_records"][key]
                removed_counts["price_records"] += 1
        for key in list(self._catalog.state.get("price_sheet_versions", {}).keys()):
            if key in seeded_version_ids:
                del self._catalog.state["price_sheet_versions"][key]
                removed_counts["price_sheet_versions"] += 1
        for key in list(self._catalog.state.get("price_sheets", {}).keys()):
            if key in seeded_sheet_ids:
                del self._catalog.state["price_sheets"][key]
                removed_counts["price_sheets"] += 1

        for key, payload in list(
            self._catalog.state.get("vendor_offerings", {}).items()
        ):
            historical_versions = [
                self._safe(item)
                for item in list(payload.get("historical_versions") or [])
                if self._safe(item)
            ]
            if historical_versions and all(
                version_id in seeded_version_ids for version_id in historical_versions
            ):
                del self._catalog.state["vendor_offerings"][key]
                removed_counts["vendor_offerings"] += 1

        for key in list(
            self._catalog.state.get("price_list_import_previews", {}).keys()
        ):
            preview = self._catalog.state["price_list_import_previews"][key]
            if self._safe(preview.get("source_filename")).startswith(
                SEED_SOURCE_PREFIX
            ):
                del self._catalog.state["price_list_import_previews"][key]
                removed_counts["pdf_previews"] += 1
        for key in list(
            self._catalog.state.get("catalog_price_list_versions", {}).keys()
        ):
            version = self._catalog.state["catalog_price_list_versions"][key]
            if self._safe(version.get("source_filename")).startswith(
                SEED_SOURCE_PREFIX
            ):
                del self._catalog.state["catalog_price_list_versions"][key]
                removed_counts["pdf_versions"] += 1

        retained_import_history = []
        for row in list(self._catalog.state.get("catalog_import_history", [])):
            source_filename = self._safe(row.get("source_filename"))
            if source_filename.startswith(SEED_SOURCE_PREFIX):
                removed_counts["catalog_import_history"] += 1
                continue
            retained_import_history.append(row)
        self._catalog.state["catalog_import_history"] = retained_import_history

        return {
            "package_id": SEED_PACKAGE_ID,
            "tenant_id": target_tenant,
            "removed_counts": removed_counts,
            "seed_summary": self.seed_summary(tenant_id=target_tenant),
        }

    def validate_catalog_to_transaction_workflow(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
    ) -> dict[str, Any]:
        products = self._catalog.list_catalog_items(item_type="product")
        services = self._catalog.list_catalog_items(item_type="service")
        fees = self._catalog.list_catalog_items(item_type="fee")
        assemblies = self._catalog.list_catalog_items(item_type="assembly")
        if not products or not services or not fees or not assemblies:
            raise ValueError("seed catalog is incomplete for workflow validation")

        workspace = TransactionsWorkspaceService(
            enforce_active_scope=False,
            commercial_catalog_service=self._catalog,
        )
        estimate = workspace.create_draft(
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_type=CommercialDocumentType.ESTIMATE,
            customer_id="seed-customer-alpha",
            project_id="seed-project-alpha",
            project_code="SEED-ALPHA",
        )

        product = products[0]
        service = services[0]
        fee = fees[0]
        assembly = assemblies[0]

        workspace.add_catalog_line(
            document_id=estimate.document_id,
            catalog_item_id=self._safe(product.get("catalog_item_id")),
            quantity=Decimal("2"),
        )
        workspace.add_catalog_line(
            document_id=estimate.document_id,
            catalog_item_id=self._safe(service.get("catalog_item_id")),
            quantity=Decimal("3"),
        )
        workspace.add_catalog_line(
            document_id=estimate.document_id,
            catalog_item_id=self._safe(fee.get("catalog_item_id")),
            quantity=Decimal("1"),
        )
        workspace.add_catalog_line(
            document_id=estimate.document_id,
            catalog_item_id=self._safe(assembly.get("catalog_item_id")),
            quantity=Decimal("1"),
            assembly_mode="grouped",
        )
        workspace.add_catalog_line(
            document_id=estimate.document_id,
            catalog_item_id=self._safe(product.get("catalog_item_id")),
            quantity=Decimal("1"),
            manual_unit_price=Decimal("1999.99"),
        )

        policy_quote = self._catalog.quote_catalog_item(
            catalog_item_id=self._safe(product.get("catalog_item_id")),
            quantity=1,
        )
        manual_quote = self._catalog.quote_catalog_item(
            catalog_item_id=self._safe(product.get("catalog_item_id")),
            quantity=1,
            manual_unit_price=1999.99,
        )

        workspace._commercial_service.set_approval_state(
            estimate,
            ApprovalState.APPROVED,
        )
        workspace.issue_document(
            document_id=estimate.document_id,
            reason="seed workflow estimate issue",
        )
        sales_order = workspace.create_sales_order_from_estimate(
            estimate_document_id=estimate.document_id,
            inherit_terms_from_estimate=True,
        )
        invoice = workspace.create_customer_invoice_draft(
            tenant_id=tenant_id,
            organization_id=organization_id,
            customer_id=estimate.customer_id,
            project_id=estimate.project_id,
            project_code=estimate.project_code,
            source_type="sales_order",
            source_document_id=sales_order.document_id,
            billing_strategy="full",
        )
        workspace.add_catalog_line(
            document_id=invoice.document_id,
            catalog_item_id=self._safe(product.get("catalog_item_id")),
            quantity=Decimal("1"),
        )
        workspace._commercial_service.set_approval_state(
            invoice,
            ApprovalState.APPROVED,
        )
        workspace.issue_document(
            document_id=invoice.document_id,
            reason="seed workflow invoice issue",
        )

        return_order = workspace.create_return_order(
            tenant_id=tenant_id,
            organization_id=organization_id,
            customer_id=estimate.customer_id,
            project_id=estimate.project_id,
            project_code=estimate.project_code,
            source_sales_order_id=sales_order.document_id,
            source_invoice_id=invoice.document_id,
            return_reason="defective",
            return_type="product",
        )
        workspace.add_catalog_line(
            document_id=return_order.document_id,
            catalog_item_id=self._safe(product.get("catalog_item_id")),
            quantity=Decimal("1"),
        )
        workspace.approve_return_order(
            document_id=return_order.document_id,
            reason="seed workflow return approval",
        )
        workspace.receive_return_order(
            document_id=return_order.document_id,
            partial=False,
            received_date="2026-06-15",
            inventory_disposition="no_inventory",
        )
        credit_memo = workspace.process_return_order(
            document_id=return_order.document_id,
            actor=actor,
            reason="seed workflow return processing",
        )
        traceable_credit_lines = [
            line
            for line in list(credit_memo.lines or [])
            if self._safe(line.source_document_id) == return_order.document_id
            and self._safe(line.source_line_id)
        ]

        estimate_pdf = workspace.export_document_pdf(
            document_id=estimate.document_id,
            presentation="customer_estimate",
            actor=actor,
        )
        invoice_pdf = workspace.export_document_pdf(
            document_id=invoice.document_id,
            presentation="customer_invoice",
            actor=actor,
        )
        credit_memo_pdf = workspace.export_document_pdf(
            document_id=credit_memo.document_id,
            presentation="credit_memo",
            actor=actor,
        )

        return {
            "estimate_id": estimate.document_id,
            "sales_order_id": sales_order.document_id,
            "invoice_id": invoice.document_id,
            "return_order_id": return_order.document_id,
            "credit_memo_id": credit_memo.document_id,
            "estimate_pdf": {
                "file_name": self._safe(estimate_pdf.get("file_name")),
                "mime_type": self._safe(estimate_pdf.get("mime_type")),
                "bytes": len(bytes(estimate_pdf.get("payload") or b"")),
            },
            "invoice_pdf": {
                "file_name": self._safe(invoice_pdf.get("file_name")),
                "mime_type": self._safe(invoice_pdf.get("mime_type")),
                "bytes": len(bytes(invoice_pdf.get("payload") or b"")),
            },
            "credit_memo_pdf": {
                "file_name": self._safe(credit_memo_pdf.get("file_name")),
                "mime_type": self._safe(credit_memo_pdf.get("mime_type")),
                "bytes": len(bytes(credit_memo_pdf.get("payload") or b"")),
            },
            "tax_applied": self._catalog.tax_quote_for_line(
                nexus="CA-LOSANGELES",
                item_type="product",
                taxable_amount=100.0,
                as_of="2026-03-01",
            ),
            "policy_quote": policy_quote,
            "manual_quote": manual_quote,
            "credit_memo_source_traceable": bool(traceable_credit_lines),
        }

    def _mark_seeded_catalog_items(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
    ) -> list[str]:
        seeded_ids: list[str] = []
        for item in self._catalog.list_catalog_items(include_archived=True):
            if self._safe(item.get("source")) != SEED_SOURCE:
                continue
            item_id = self._safe(item.get("catalog_item_id"))
            if not item_id:
                continue
            payload = dict(item)
            payload["provenance"] = {
                "seed_package_id": SEED_PACKAGE_ID,
                "seed_source": SEED_SOURCE,
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "seeded_by": actor,
            }
            self._catalog.state.setdefault("catalog_items", {})[item_id] = payload
            seeded_ids.append(item_id)
        return seeded_ids

    def _mark_seeded_manufacturers_and_vendors(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
    ) -> None:
        for collection_name in ("manufacturers", "vendors"):
            collection = self._catalog.state.get(collection_name, {})
            for key, payload in list(collection.items()):
                if self._safe(payload.get("source")) != SEED_SOURCE:
                    continue
                updated = dict(payload)
                updated["provenance"] = {
                    "seed_package_id": SEED_PACKAGE_ID,
                    "seed_source": SEED_SOURCE,
                    "tenant_id": tenant_id,
                    "organization_id": organization_id,
                    "seeded_by": actor,
                }
                collection[key] = updated

    def _load_tax_rules(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        actor: str,
        tax_rules: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in tax_rules:
            rule_id = f"seed-tax:{self._safe(row.get('nexus')).lower()}:{self._safe(row.get('title')).lower()}".replace(
                " ", "-"
            ).replace(
                "/", "-"
            )
            created = self._catalog.create_or_update_tax_nexus_rule(
                tax_rule_id=rule_id,
                nexus=self._safe(row.get("nexus")),
                title=self._safe(row.get("title")),
                rate=float(row.get("rate") or 0.0),
                priority=int(row.get("priority") or 100),
                compound=bool(row.get("compound", False)),
                taxable_item_types=list(row.get("taxable_item_types") or []),
                exemption_flags=list(row.get("exemption_flags") or []),
                effective_date=self._safe(row.get("effective_date")) or None,
                expiration_date=self._safe(row.get("expiration_date")) or None,
                archived=False,
            )
            created["source"] = SEED_SOURCE
            created["provenance"] = {
                "seed_package_id": SEED_PACKAGE_ID,
                "seed_source": SEED_SOURCE,
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "seeded_by": actor,
            }
            self._catalog.state["tax_nexus_rules"][rule_id] = created
            rows.append(created)
        return rows

    def _load_price_lists(
        self,
        *,
        actor: str,
        tenant_id: str,
        organization_id: str,
        price_lists: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for row in price_lists:
            source_filename = self._safe(row.get("source_filename"), "")
            if self._seed_sheet_exists(
                source_filename=source_filename,
                tenant_id=tenant_id,
            ):
                results.append(
                    {
                        "source_filename": source_filename,
                        "skipped": True,
                        "reason": "existing_seed_price_sheet",
                    }
                )
                continue
            imported = self._catalog.import_price_sheet(
                vendor=self._safe(row.get("vendor")),
                manufacturer=self._safe(row.get("manufacturer")),
                sheet_name=self._safe(row.get("sheet_name")),
                description=self._safe(row.get("description")),
                source_filename=source_filename,
                file_bytes=source_filename.encode("utf-8"),
                imported_by=actor,
                rows=list(row.get("rows") or []),
                effective_date="2026-01-01",
                expiration_date="",
                notes=(
                    f"{SEED_SOURCE};seed_package_id={SEED_PACKAGE_ID};"
                    f"tenant_id={tenant_id};organization_id={organization_id}"
                ),
            )
            results.append(imported)
        return results

    def _validate_pdf_import(
        self,
        *,
        import_artifacts: dict[str, Any],
        actor: str,
        enable_pdf_finalize: bool,
    ) -> dict[str, Any]:
        pdf_spec = dict(import_artifacts.get("pdf_price_list") or {})
        source_filename = self._safe(pdf_spec.get("filename"), "c04_seed_catalog.pdf")
        content = bytes(pdf_spec.get("content") or b"")
        inspected = self._catalog.inspect_catalog_pdf_price_list(
            source_filename=source_filename,
            file_bytes=content,
        )
        result: dict[str, Any] = {
            "source_filename": source_filename,
            "inspected": True,
            "valid_pdf": bool(inspected.get("valid_pdf", False)),
            "candidate_count": len(list(inspected.get("table_candidates") or [])),
            "diagnostic_count": len(list(inspected.get("diagnostics") or [])),
            "preview_id": None,
            "version_id": None,
            "finalized": False,
        }
        if not enable_pdf_finalize:
            return result
        candidates = list(inspected.get("table_candidates") or [])
        if not candidates:
            result["finalized"] = False
            result["skipped_reason"] = "no_table_candidates"
            return result
        preview = self._catalog.preview_catalog_pdf_price_list_import(
            source_filename=source_filename,
            file_bytes=content,
            selected_pages=list(candidates[0].get("page_numbers") or [1]),
            table_candidate_id=self._safe(candidates[0].get("candidate_id")),
            header_row_index=0,
            column_mapping={
                "code": "Code",
                "name": "Name",
                "cost": "Cost",
                "msrp": "MSRP",
            },
            imported_by=actor,
        )
        finalized = self._catalog.finalize_catalog_pdf_price_list_import(
            preview_id=self._safe(preview.get("preview_id")),
            imported_by=actor,
        )
        version = dict(finalized.get("version") or {})
        result.update(
            {
                "preview_id": self._safe(preview.get("preview_id")),
                "version_id": self._safe(version.get("catalog_price_list_version_id")),
                "finalized": True,
                "partial_success": bool(finalized.get("partial_success", False)),
            }
        )
        return result

    def _seed_sheet_exists(self, *, source_filename: str, tenant_id: str) -> bool:
        for sheet in self._catalog.state.get("price_sheets", {}).values():
            notes = self._safe(sheet.get("notes"))
            if self._safe(source_filename) not in notes and self._safe(
                sheet.get("sheet_name")
            ) not in self._safe(source_filename):
                continue
            if f"tenant_id={tenant_id}" not in notes:
                continue
            if SEED_SOURCE not in notes:
                continue
            return True
        return False

    def _is_seeded_sheet(self, sheet: dict[str, Any], tenant_id: str) -> bool:
        notes = self._safe(sheet.get("notes"))
        return SEED_SOURCE in notes and f"tenant_id={tenant_id}" in notes

    @staticmethod
    def _safe(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    def _provenance(self, payload: dict[str, Any]) -> dict[str, Any]:
        value = payload.get("provenance")
        if isinstance(value, dict):
            return dict(value)
        return {}

"""Deterministic product resolution engine for Atlas Core."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import re
from typing import Any

from atlas_core.domain.master_library import MasterProduct
from atlas_core.domain.product_resolution import (
    ProductResolution,
    ProductResolutionCandidate,
    ProductResolutionManualOverride,
)
from atlas_core.domain.deterministic_estimate import ProductResolutionStatus
from atlas_core.registry import ManufacturerRegistry
from atlas_core.services.master_library import MasterLibraryService


class ProductResolutionService:
    """Resolve equipment rows to canonical master-library products deterministically."""

    _normalize_pattern = re.compile(r"[^A-Z0-9]+")

    def __init__(
        self,
        master_library_service: MasterLibraryService | None = None,
        manufacturer_registry: ManufacturerRegistry | None = None,
    ) -> None:
        self.master_library_service = master_library_service or MasterLibraryService()
        self.manufacturer_registry = manufacturer_registry or ManufacturerRegistry()

    def resolve_equipment_rows(
        self,
        equipment_rows: list[dict[str, Any]],
        *,
        manual_overrides: dict[str, dict[str, Any]] | None = None,
    ) -> list[ProductResolution]:
        rows = list(equipment_rows or [])
        products = self.master_library_service.repository.list_products()
        if not products:
            seed_rows = [row for row in rows if self._is_seedable_row(row)]
            if seed_rows:
                self.master_library_service.import_workspace_equipment(seed_rows)
                products = self.master_library_service.repository.list_products()
        by_id = {product.product_id: product for product in products}

        resolutions: list[ProductResolution] = []
        overrides = dict(manual_overrides or {})
        for row in rows:
            resolutions.append(
                self._resolve_single_row(
                    row,
                    products=products,
                    product_by_id=by_id,
                    manual_override=overrides.get(
                        _safe_text(
                            row.get("equipment_id"),
                            _safe_text(row.get("bom_item_id"), ""),
                        )
                    ),
                )
            )
        return resolutions

    def _resolve_single_row(
        self,
        row: dict[str, Any],
        *,
        products: list[MasterProduct],
        product_by_id: dict[str, MasterProduct],
        manual_override: dict[str, Any] | None,
    ) -> ProductResolution:
        source_object_id = _safe_text(
            row.get("equipment_id"),
            _safe_text(row.get("bom_item_id"), "unknown_equipment"),
        )
        manufacturer = _safe_text(row.get("manufacturer"), "Unknown")
        model = _safe_text(row.get("model"), "Unknown")
        description = _safe_text(row.get("description"), "")
        completeness = _safe_text(row.get("completeness_status"), "")

        raw_candidates = self._rank_candidates(
            manufacturer=manufacturer,
            model=model,
            description=description,
            products=products,
        )
        candidate_matches = [
            ProductResolutionCandidate(**candidate)
            for candidate in raw_candidates[:8]
            if candidate.get("product_id")
        ]

        auto_resolution = self._auto_resolution(
            source_object_id=source_object_id,
            manufacturer=manufacturer,
            model=model,
            description=description,
            completeness_status=completeness,
            candidate_matches=candidate_matches,
            product_by_id=product_by_id,
            row=row,
        )

        if manual_override:
            return self._apply_manual_override(
                auto_resolution=auto_resolution,
                manual_override=manual_override,
                product_by_id=product_by_id,
            )
        return auto_resolution

    def _auto_resolution(
        self,
        *,
        source_object_id: str,
        manufacturer: str,
        model: str,
        description: str,
        completeness_status: str,
        candidate_matches: list[ProductResolutionCandidate],
        product_by_id: dict[str, MasterProduct],
        row: dict[str, Any],
    ) -> ProductResolution:
        normalized_manufacturer = self._normalize(manufacturer)
        normalized_model = self._normalize(model)

        selected_status = ProductResolutionStatus.UNKNOWN_PRODUCT
        selected_reason = "Unknown product: no deterministic manufacturer/model match."
        selected_product: dict[str, Any] | None = None
        selected_product_id: str | None = None

        top = candidate_matches[0] if candidate_matches else None
        if top is not None:
            selected_product_id = top.product_id
            product = product_by_id.get(top.product_id)
            if product is not None:
                selected_product = product.to_dict()
                if top.match_type == "exact_manufacturer_model":
                    selected_status = ProductResolutionStatus.EXACT_PRODUCT
                    selected_reason = "Exact manufacturer/model match."
                elif top.match_type == "normalized_manufacturer_model":
                    selected_status = ProductResolutionStatus.EXACT_PRODUCT
                    selected_reason = "Exact normalized manufacturer/model match."
                elif top.match_type == "alias_match":
                    selected_status = ProductResolutionStatus.EXACT_PRODUCT
                    selected_reason = "Alias mapping resolved to canonical product."
                elif top.match_type == "approved_substitute":
                    selected_status = ProductResolutionStatus.APPROVED_SUBSTITUTE
                    selected_reason = (
                        "Approved substitute selected by deterministic rules."
                    )
                elif top.match_type == "preferred_alternate":
                    selected_status = ProductResolutionStatus.PREFERRED_ALTERNATE
                    selected_reason = (
                        "Preferred alternate selected by deterministic rules."
                    )

        if selected_status is ProductResolutionStatus.UNKNOWN_PRODUCT:
            if completeness_status in {"drawing_only", "specification_only"}:
                selected_status = ProductResolutionStatus.GENERIC_ALLOWANCE
                selected_reason = "Generic allowance: source coverage incomplete for deterministic product selection."
            elif (
                not normalized_manufacturer
                or normalized_manufacturer == "UNKNOWN"
                or not normalized_model
                or normalized_model == "UNKNOWN"
            ):
                selected_reason = (
                    "Unknown product: manufacturer/model missing or unresolved."
                )

        confidence = self._resolution_confidence(
            status=selected_status,
            candidate_matches=candidate_matches,
            manufacturer=manufacturer,
            model=model,
        )

        canonical_product = None
        manufacturer_id = None
        if selected_product_id and selected_product:
            canonical_product = selected_product
            manufacturer_id = _safe_text(canonical_product.get("manufacturer"), "")

        return ProductResolution(
            resolution_id=self._resolution_id(source_object_id),
            source_object_id=source_object_id,
            resolution_status=selected_status,
            canonical_product=canonical_product,
            manufacturer=manufacturer,
            model=model,
            resolution_confidence=confidence,
            resolution_reason=selected_reason,
            candidate_matches=candidate_matches,
            source_evidence=self._source_evidence(row),
            canonical_product_id=selected_product_id,
            manufacturer_id=manufacturer_id,
            future_price_records=[],
            future_vendor_records=[],
            future_labor_templates=[],
        )

    def _apply_manual_override(
        self,
        *,
        auto_resolution: ProductResolution,
        manual_override: dict[str, Any],
        product_by_id: dict[str, MasterProduct],
    ) -> ProductResolution:
        selected_product_id = _safe_text(manual_override.get("selected_product_id"), "")
        selected_status_text = _safe_text(manual_override.get("resolution_status"), "")
        reviewer = _safe_text(manual_override.get("reviewer"), "Manual Reviewer")
        reason = _safe_text(manual_override.get("reason"), "Manual selection")
        timestamp = _safe_text(manual_override.get("timestamp"), self._now_iso())

        selected_product = product_by_id.get(selected_product_id)
        if selected_product is None:
            return auto_resolution

        override_status = (
            ProductResolutionStatus(selected_status_text)
            if selected_status_text
            else ProductResolutionStatus.EXACT_PRODUCT
        )
        manual = ProductResolutionManualOverride(
            original_match=(
                {
                    "canonical_product_id": auto_resolution.canonical_product_id,
                    "resolution_status": auto_resolution.resolution_status.value,
                    "resolution_reason": auto_resolution.resolution_reason,
                }
                if auto_resolution.canonical_product_id
                else None
            ),
            manual_selection={
                "selected_product_id": selected_product.product_id,
                "selected_manufacturer": selected_product.manufacturer,
                "selected_model": selected_product.model,
                "selected_status": override_status.value,
            },
            reviewer=reviewer,
            timestamp=timestamp,
            reason=reason,
        )

        return ProductResolution(
            resolution_id=auto_resolution.resolution_id,
            source_object_id=auto_resolution.source_object_id,
            resolution_status=override_status,
            canonical_product=selected_product.to_dict(),
            manufacturer=auto_resolution.manufacturer,
            model=auto_resolution.model,
            resolution_confidence=min(
                1.0, auto_resolution.resolution_confidence + 0.05
            ),
            resolution_reason="Manual selection applied.",
            candidate_matches=list(auto_resolution.candidate_matches),
            manual_override=manual,
            source_evidence=list(auto_resolution.source_evidence),
            canonical_product_id=selected_product.product_id,
            manufacturer_id=selected_product.manufacturer,
            future_price_records=[],
            future_vendor_records=[],
            future_labor_templates=[],
        )

    def _rank_candidates(
        self,
        *,
        manufacturer: str,
        model: str,
        description: str,
        products: list[MasterProduct],
    ) -> list[dict[str, Any]]:
        normalized_manufacturer = self._normalize(manufacturer)
        normalized_model = self._normalize(model)
        normalized_description = description.strip().lower()

        ranked: list[dict[str, Any]] = []
        for product in products:
            product_manufacturer = self._normalize(product.manufacturer)
            product_model = self._normalize(product.model)
            product_aliases = {
                self._normalize(alias.alias) for alias in product.aliases
            }
            product_aliases.add(self._normalize(product.normalized_model))

            match_type = None
            confidence = 0.0
            reason = ""

            if (
                product.manufacturer.upper() == manufacturer.upper()
                and product.model.upper() == model.upper()
            ):
                match_type = "exact_manufacturer_model"
                confidence = 0.98
                reason = "Exact manufacturer/model match"
            elif (
                product_manufacturer == normalized_manufacturer
                and product_model == normalized_model
            ):
                match_type = "normalized_manufacturer_model"
                confidence = 0.95
                reason = "Exact normalized manufacturer/model match"
            elif normalized_model and normalized_model in product_aliases:
                match_type = "alias_match"
                confidence = 0.9
                reason = "Alias mapping matched canonical product"
            elif self._is_approved_substitute(product, manufacturer):
                match_type = "approved_substitute"
                confidence = 0.74
                reason = "Approved substitute by manufacturer discipline/tier"
            elif self._is_preferred_alternate(product, manufacturer):
                match_type = "preferred_alternate"
                confidence = 0.68
                reason = "Preferred alternate by manufacturer discipline/tier"

            if match_type is None:
                continue

            if (
                normalized_description
                and normalized_description in product.description.lower()
            ):
                confidence = min(1.0, confidence + 0.02)
            ranked.append(
                {
                    "product_id": product.product_id,
                    "manufacturer": product.manufacturer,
                    "model": product.model,
                    "match_type": match_type,
                    "confidence": round(confidence, 4),
                    "reason": reason,
                }
            )

        priority = {
            "exact_manufacturer_model": 0,
            "normalized_manufacturer_model": 1,
            "alias_match": 2,
            "approved_substitute": 3,
            "preferred_alternate": 4,
        }
        ranked.sort(
            key=lambda item: (
                priority.get(_safe_text(item.get("match_type"), ""), 9),
                -float(item.get("confidence", 0.0) or 0.0),
                _safe_text(item.get("manufacturer"), "").lower(),
                _safe_text(item.get("model"), "").lower(),
            )
        )
        return ranked

    def _is_approved_substitute(
        self, product: MasterProduct, manufacturer: str
    ) -> bool:
        requested = self.manufacturer_registry.get_by_name(manufacturer)
        if requested is None:
            return False
        substitutes = self.manufacturer_registry.approved_by_discipline(
            requested.discipline
        )
        substitute_names = {
            item.name.upper()
            for item in substitutes
            if item.name.upper() != requested.name.upper()
        }
        if product.manufacturer.upper() in substitute_names:
            return True
        return any(
            rel.relationship_type == "approved_substitute"
            for rel in list(product.related_products or [])
        )

    def _is_preferred_alternate(
        self, product: MasterProduct, manufacturer: str
    ) -> bool:
        requested = self.manufacturer_registry.get_by_name(manufacturer)
        if requested is None:
            return False
        preferred = self.manufacturer_registry.preferred_by_discipline(
            requested.discipline
        )
        preferred_names = {
            item.name.upper()
            for item in preferred
            if item.name.upper() != requested.name.upper()
        }
        if product.manufacturer.upper() in preferred_names:
            return True
        return any(
            rel.relationship_type == "preferred_alternate"
            for rel in list(product.related_products or [])
        )

    def _resolution_confidence(
        self,
        *,
        status: ProductResolutionStatus,
        candidate_matches: list[ProductResolutionCandidate],
        manufacturer: str,
        model: str,
    ) -> float:
        base = {
            ProductResolutionStatus.EXACT_PRODUCT: 0.95,
            ProductResolutionStatus.APPROVED_SUBSTITUTE: 0.74,
            ProductResolutionStatus.PREFERRED_ALTERNATE: 0.66,
            ProductResolutionStatus.GENERIC_ALLOWANCE: 0.45,
            ProductResolutionStatus.UNKNOWN_PRODUCT: 0.2,
        }[status]
        if candidate_matches:
            base = max(base, candidate_matches[0].confidence)
        if _safe_text(manufacturer, "Unknown").lower() == "unknown":
            base -= 0.12
        if _safe_text(model, "Unknown").lower() == "unknown":
            base -= 0.12
        return round(max(0.0, min(base, 1.0)), 4)

    def _source_evidence(self, row: dict[str, Any]) -> list[str]:
        evidence: list[str] = []
        for key in [
            "source_documents",
            "drawing_references",
            "specification_references",
        ]:
            for item in list(row.get(key) or []):
                text = _safe_text(item, "")
                if text:
                    evidence.append(text)
        return sorted(set(evidence))

    def _is_seedable_row(self, row: dict[str, Any]) -> bool:
        manufacturer = _safe_text(row.get("manufacturer"), "").lower()
        model = _safe_text(row.get("model"), "").lower()
        if not manufacturer or manufacturer == "unknown":
            return False
        if not model or model == "unknown":
            return False
        return True

    @classmethod
    def _normalize(cls, value: str | None) -> str:
        text = _safe_text(value, "")
        if not text:
            return ""
        return cls._normalize_pattern.sub("", text.upper())

    @staticmethod
    def _resolution_id(source_object_id: str) -> str:
        digest = hashlib.sha1(source_object_id.encode("utf-8")).hexdigest()[:12]
        return f"resolution:{digest}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or default
    return str(value)

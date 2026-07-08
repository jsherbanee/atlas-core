"""Master Library service orchestration for Atlas engineering product understanding."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any

from atlas_core.domain.master_library import (
    EngineeringAttributes,
    MasterProduct,
    ProductAlias,
    ProductCategory,
    ProductFamily,
    ProductRelationship,
    ProductStatus,
)
from atlas_core.services.master_library.repository import MasterLibraryRepository
from atlas_core.services.master_library.resolver import AliasResolver, LibraryResolver

CATEGORY_KEYWORDS: list[tuple[ProductCategory, tuple[str, ...]]] = [
    (ProductCategory.LOUDSPEAKER, ("speaker", "loudspeaker")),
    (ProductCategory.AMPLIFIER, ("amp", "amplifier")),
    (ProductCategory.DSP, ("dsp", "signal processor", "qsys core")),
    (ProductCategory.MICROPHONE, ("microphone", "mic", "ulxd")),
    (ProductCategory.CAMERA, ("camera", "ptz")),
    (ProductCategory.PROJECTOR, ("projector",)),
    (ProductCategory.DISPLAY, ("display", "monitor")),
    (ProductCategory.LED, ("led", "videowall")),
    (ProductCategory.RACK, ("rack", "cabinet")),
    (ProductCategory.CONTROL_PROCESSOR, ("control processor", "controller")),
    (ProductCategory.TOUCH_PANEL, ("touch panel", "touchscreen")),
    (ProductCategory.NETWORK_SWITCH, ("switch", "network switch")),
    (ProductCategory.AV_OVER_IP, ("av over ip", "nvx", "aVoIP")),
    (ProductCategory.CABLE, ("cable", "wire")),
    (ProductCategory.CONNECTOR, ("connector", "adapter", "termination")),
    (ProductCategory.ACCESSORY, ("accessory", "kit")),
    (ProductCategory.MOUNT, ("mount", "bracket", "hanger")),
    (ProductCategory.FURNITURE, ("furniture", "lectern", "console")),
]


class MasterLibraryService:
    """Builds and resolves canonical products for the Atlas master library."""

    def __init__(
        self,
        repository: MasterLibraryRepository | None = None,
        alias_resolver: AliasResolver | None = None,
    ) -> None:
        self._repository = repository or MasterLibraryRepository()
        self._alias_resolver = alias_resolver or AliasResolver()
        self._resolver = LibraryResolver(
            repository=self._repository,
            alias_resolver=self._alias_resolver,
        )

    @property
    def repository(self) -> MasterLibraryRepository:
        return self._repository

    def upsert_product(self, product: MasterProduct) -> MasterProduct:
        return self._repository.upsert_product(product)

    def import_workspace_equipment(
        self,
        equipment_rows: list[dict[str, Any]],
    ) -> list[MasterProduct]:
        upserted: list[MasterProduct] = []
        for row in list(equipment_rows or []):
            manufacturer = (
                str(row.get("manufacturer") or "Unknown").strip() or "Unknown"
            )
            model = str(row.get("model") or "Unknown").strip() or "Unknown"
            description = str(row.get("description") or "Unspecified product").strip()

            normalized_model = self._alias_resolver.normalize(model) or "UNKNOWN"
            product_id = self._product_id(manufacturer=manufacturer, model=model)
            category = self._infer_category(description=description, model=model)
            family = ProductFamily(
                family_id=self._family_id(manufacturer=manufacturer, category=category),
                name=f"{manufacturer} {category.value.replace('_', ' ').title()}",
                category=category,
            )

            aliases = self._aliases_from_row(
                manufacturer=manufacturer, model=model, row=row
            )
            relationships = self._relationships_from_row(row)
            attributes = EngineeringAttributes(
                attributes={
                    "system": str(row.get("system") or "Unknown"),
                    "room": str(row.get("room") or "Unknown"),
                },
                tags=[
                    str(category.value),
                    "workspace_import",
                ],
            )

            existing = self._repository.get_product(product_id)
            confidence = float(row.get("confidence", 0.75) or 0.75)
            try:
                confidence = max(0.0, min(1.0, confidence))
            except Exception:
                confidence = 0.75

            if existing is None:
                product = MasterProduct(
                    product_id=product_id,
                    manufacturer=manufacturer,
                    model=model,
                    normalized_model=normalized_model,
                    description=description,
                    category=category,
                    family=family.name,
                    status=ProductStatus.ACTIVE,
                    aliases=aliases,
                    engineering_attributes=attributes,
                    related_products=relationships,
                    confidence=confidence,
                    created_at=_now_iso(),
                    updated_at=_now_iso(),
                )
            else:
                product = MasterProduct(
                    product_id=existing.product_id,
                    manufacturer=existing.manufacturer,
                    model=existing.model,
                    normalized_model=existing.normalized_model,
                    description=existing.description,
                    category=existing.category,
                    family=existing.family,
                    status=existing.status,
                    aliases=list(existing.aliases),
                    engineering_attributes=existing.engineering_attributes,
                    related_products=list(existing.related_products),
                    confidence=max(existing.confidence, confidence),
                    created_at=existing.created_at,
                    updated_at=_now_iso(),
                )
                product.add_alias(
                    ProductAlias(
                        alias=model,
                        normalized_alias=normalized_model,
                        source="workspace",
                    )
                )
                for alias in aliases:
                    product.add_alias(alias)

            self._repository.upsert_product(product)
            upserted.append(product)

        return upserted

    def resolve_product(
        self,
        manufacturer: str,
        model: str,
        description: str = "",
    ) -> dict[str, Any]:
        resolution = self._resolver.resolve(
            manufacturer=manufacturer,
            model=model,
            description=description,
        )
        matched = resolution.matched_product
        return {
            "matched": matched.to_dict() if matched is not None else None,
            "confidence": resolution.confidence,
            "trace": list(resolution.trace),
        }

    def explorer_rows(
        self,
        query: str = "",
        category: str | None = None,
        manufacturer: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        q = query.strip().lower()
        rows: list[dict[str, Any]] = []
        for product in self._repository.list_products():
            if category and product.category.value != category:
                continue
            if manufacturer and product.manufacturer != manufacturer:
                continue
            if status and product.status.value != status:
                continue

            aliases = [item.alias for item in list(product.aliases)]
            searchable = " ".join(
                [
                    product.product_id,
                    product.manufacturer,
                    product.model,
                    product.description,
                    product.family,
                    " ".join(aliases),
                ]
            ).lower()
            if q and q not in searchable:
                continue

            rows.append(
                {
                    "product_id": product.product_id,
                    "manufacturer": product.manufacturer,
                    "model": product.model,
                    "normalized_model": product.normalized_model,
                    "description": product.description,
                    "category": product.category.value,
                    "family": product.family,
                    "status": product.status.value,
                    "aliases": aliases,
                    "engineering_attributes": product.engineering_attributes.to_dict(),
                    "related_products": [
                        item.to_dict() for item in product.related_products
                    ],
                    "confidence": product.confidence,
                    "created_at": product.created_at,
                    "updated_at": product.updated_at,
                }
            )

        rows.sort(
            key=lambda item: (
                str(item.get("manufacturer", "")).lower(),
                str(item.get("model", "")).lower(),
            )
        )
        return rows

    @staticmethod
    def _family_id(manufacturer: str, category: ProductCategory) -> str:
        digest = hashlib.sha1(
            f"{manufacturer.upper()}::{category.value}".encode("utf-8")
        ).hexdigest()
        return f"fam:{digest[:10]}"

    def _product_id(self, manufacturer: str, model: str) -> str:
        digest = hashlib.sha1(
            f"{manufacturer.upper()}::{self._alias_resolver.normalize(model)}".encode(
                "utf-8"
            )
        ).hexdigest()
        return f"prd:{digest[:12]}"

    def _infer_category(self, description: str, model: str) -> ProductCategory:
        text = f"{description} {model}".lower()
        for category, keywords in CATEGORY_KEYWORDS:
            if any(keyword.lower() in text for keyword in keywords):
                return category
        return ProductCategory.OTHER

    def _aliases_from_row(
        self,
        manufacturer: str,
        model: str,
        row: dict[str, Any],
    ) -> list[ProductAlias]:
        alias_values = {
            model,
            self._alias_resolver.normalize(model),
            manufacturer,
            self._alias_resolver.normalize(manufacturer),
        }

        description = str(row.get("description") or "").strip()
        if description and len(description.split()) <= 5:
            alias_values.add(description)

        aliases: list[ProductAlias] = []
        seen: set[str] = set()
        for raw in sorted(
            {str(item).strip() for item in alias_values if str(item).strip()}
        ):
            normalized = self._alias_resolver.normalize(raw)
            if not normalized or normalized in seen:
                continue
            aliases.append(
                ProductAlias(alias=raw, normalized_alias=normalized, source="workspace")
            )
            seen.add(normalized)
        return aliases

    @staticmethod
    def _relationships_from_row(row: dict[str, Any]) -> list[ProductRelationship]:
        related: list[ProductRelationship] = []
        for reference in list(row.get("drawing_references") or [])[:2]:
            reference_text = str(reference).strip()
            if not reference_text:
                continue
            related.append(
                ProductRelationship(
                    relationship_type="referenced_by_drawing",
                    target_product_id=f"drawing:{reference_text}",
                    confidence=0.8,
                    evidence_refs=[f"drawing:{reference_text}"],
                )
            )
        for reference in list(row.get("specification_references") or [])[:2]:
            reference_text = str(reference).strip()
            if not reference_text:
                continue
            related.append(
                ProductRelationship(
                    relationship_type="referenced_by_specification",
                    target_product_id=f"spec:{reference_text}",
                    confidence=0.8,
                    evidence_refs=[f"spec:{reference_text}"],
                )
            )
        return related


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

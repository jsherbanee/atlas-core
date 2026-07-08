"""Deterministic in-memory repository for Master Library products."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from atlas_core.domain.master_library import MasterProduct


class MasterLibraryRepository:
    """Stores canonical products and alias indexes for deterministic lookup."""

    def __init__(self, products: Iterable[MasterProduct] | None = None) -> None:
        self._products_by_id: dict[str, MasterProduct] = {}
        self._products_by_model_key: dict[str, set[str]] = defaultdict(set)
        self._products_by_manufacturer_key: dict[str, set[str]] = defaultdict(set)
        self._products_by_alias_key: dict[str, set[str]] = defaultdict(set)

        for product in list(products or []):
            self.upsert_product(product)

    def upsert_product(self, product: MasterProduct) -> MasterProduct:
        self._products_by_id[product.product_id] = product

        model_key = (
            f"{product.manufacturer.upper()}::{product.normalized_model.upper()}"
        )
        self._products_by_model_key[model_key].add(product.product_id)
        self._products_by_manufacturer_key[product.manufacturer.upper()].add(
            product.product_id
        )

        self._products_by_alias_key[product.model.upper()].add(product.product_id)
        for alias in list(product.aliases):
            self._products_by_alias_key[alias.normalized_alias.upper()].add(
                product.product_id
            )

        return product

    def list_products(self) -> list[MasterProduct]:
        return sorted(
            self._products_by_id.values(),
            key=lambda item: (item.manufacturer.lower(), item.normalized_model.lower()),
        )

    def get_product(self, product_id: str) -> MasterProduct | None:
        return self._products_by_id.get(product_id)

    def find_by_alias(self, alias_key: str) -> list[MasterProduct]:
        ids = self._products_by_alias_key.get(alias_key.upper(), set())
        return [self._products_by_id[item] for item in sorted(ids)]

    def find_by_model(
        self, manufacturer: str, normalized_model: str
    ) -> list[MasterProduct]:
        key = f"{manufacturer.upper()}::{normalized_model.upper()}"
        ids = self._products_by_model_key.get(key, set())
        return [self._products_by_id[item] for item in sorted(ids)]

    def find_by_manufacturer(self, manufacturer: str) -> list[MasterProduct]:
        ids = self._products_by_manufacturer_key.get(manufacturer.upper(), set())
        return [self._products_by_id[item] for item in sorted(ids)]

"""Deterministic matching utilities for Master Library resolution."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_core.domain.master_library import MasterProduct


@dataclass
class ProductMatch:
    product: MasterProduct
    score: float
    rationale: str


class ProductMatcher:
    """Simple deterministic scoring for canonical product matching."""

    def score(
        self,
        product: MasterProduct,
        manufacturer: str,
        normalized_model: str,
        description: str,
    ) -> ProductMatch:
        score = 0.0
        reasons: list[str] = []

        if product.manufacturer.upper() == manufacturer.upper():
            score += 0.45
            reasons.append("manufacturer_match")

        if product.normalized_model.upper() == normalized_model.upper():
            score += 0.45
            reasons.append("model_match")

        normalized_description = description.strip().lower()
        if (
            normalized_description
            and normalized_description in product.description.lower()
        ):
            score += 0.1
            reasons.append("description_overlap")

        if score <= 0.0:
            reasons.append("no_direct_match")

        return ProductMatch(
            product=product,
            score=round(min(score, 1.0), 3),
            rationale=",".join(reasons),
        )

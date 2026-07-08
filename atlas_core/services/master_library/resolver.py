"""Alias and library resolvers for deterministic product identity matching."""

from __future__ import annotations

import re
from dataclasses import dataclass

from atlas_core.domain.master_library import MasterProduct
from atlas_core.services.master_library.matcher import ProductMatch, ProductMatcher
from atlas_core.services.master_library.repository import MasterLibraryRepository


@dataclass
class LibraryResolution:
    matched_product: MasterProduct | None
    confidence: float
    trace: list[str]


class AliasResolver:
    """Normalizes manufacturer/model aliases while preserving traceability."""

    _alias_pattern = re.compile(r"[^A-Z0-9]+")

    def normalize(self, value: str | None) -> str:
        if not value:
            return ""
        return self._alias_pattern.sub("", value.upper())


class LibraryResolver:
    """Resolves extracted objects to canonical master-library products."""

    def __init__(
        self,
        repository: MasterLibraryRepository,
        alias_resolver: AliasResolver | None = None,
        matcher: ProductMatcher | None = None,
    ) -> None:
        self._repository = repository
        self._alias_resolver = alias_resolver or AliasResolver()
        self._matcher = matcher or ProductMatcher()

    def resolve(
        self,
        manufacturer: str,
        model: str,
        description: str = "",
    ) -> LibraryResolution:
        normalized_manufacturer = self._alias_resolver.normalize(manufacturer)
        normalized_model = self._alias_resolver.normalize(model)

        trace = [
            f"manufacturer={normalized_manufacturer or 'unknown'}",
            f"model={normalized_model or 'unknown'}",
        ]

        direct = self._repository.find_by_model(
            manufacturer=manufacturer,
            normalized_model=normalized_model,
        )
        if direct:
            match = self._matcher.score(
                product=direct[0],
                manufacturer=manufacturer,
                normalized_model=normalized_model,
                description=description,
            )
            trace.append("match_path=direct_model")
            trace.append(f"rationale={match.rationale}")
            return LibraryResolution(
                matched_product=match.product,
                confidence=match.score,
                trace=trace,
            )

        candidates = self._repository.find_by_alias(normalized_model)
        if not candidates:
            candidates = self._repository.find_by_alias(model)
        if candidates:
            ranked: list[ProductMatch] = [
                self._matcher.score(
                    product=item,
                    manufacturer=manufacturer,
                    normalized_model=normalized_model,
                    description=description,
                )
                for item in candidates
            ]
            ranked.sort(key=lambda item: item.score, reverse=True)
            top = ranked[0]
            trace.append("match_path=alias")
            trace.append(f"rationale={top.rationale}")
            return LibraryResolution(
                matched_product=top.product,
                confidence=top.score,
                trace=trace,
            )

        manufacturer_candidates = self._repository.find_by_manufacturer(manufacturer)
        if manufacturer_candidates and description.strip():
            ranked = [
                self._matcher.score(
                    product=item,
                    manufacturer=manufacturer,
                    normalized_model=normalized_model,
                    description=description,
                )
                for item in manufacturer_candidates
            ]
            ranked.sort(key=lambda item: item.score, reverse=True)
            top = ranked[0]
            if top.score >= 0.35:
                trace.append("match_path=manufacturer_fallback")
                trace.append(f"rationale={top.rationale}")
                return LibraryResolution(
                    matched_product=top.product,
                    confidence=top.score,
                    trace=trace,
                )

        trace.append("match_path=none")
        return LibraryResolution(matched_product=None, confidence=0.0, trace=trace)

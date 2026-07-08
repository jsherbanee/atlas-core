"""Deterministic Atlas specification intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_core.domain.bid_package_review import BidPackageReview

from atlas_core.services.specification_intelligence.analyzer import (
    SpecificationAnalyzer,
)
from atlas_core.services.specification_intelligence.models import (
    SpecificationIndex,
    SpecificationIntelligenceResult,
    SpecificationReferenceType,
    SpecificationRelationship,
    SpecificationSection,
    aggregate_confidence,
)


@dataclass
class SpecificationIntelligenceEngine:
    """Build deterministic section intelligence, index and relationships."""

    analyzer: SpecificationAnalyzer | None = None

    def __post_init__(self) -> None:
        if self.analyzer is None:
            self.analyzer = SpecificationAnalyzer()

    def build(
        self,
        review: BidPackageReview,
        context: dict[str, Any] | None = None,
    ) -> SpecificationIntelligenceResult:
        del context

        known_sections = {
            section.section_number.strip()
            for section in review.specification_sections
            if section.section_number
        }

        sections = [
            self.analyzer.analyze_section(section, known_sections)  # type: ignore[union-attr]
            for section in review.specification_sections
        ]
        metadata = [item.metadata for item in sections]
        index = self._build_index(sections)
        relationships = self._build_relationships(sections)

        confidence = aggregate_confidence(
            [
                review.confidence,
                aggregate_confidence([item.confidence for item in sections]),
                aggregate_confidence([item.confidence for item in relationships]),
            ],
            default=review.confidence,
        )

        return SpecificationIntelligenceResult(
            metadata=metadata,
            sections=sections,
            specification_index=index,
            relationships=relationships,
            confidence=confidence,
        )

    def _build_index(self, sections: list[SpecificationSection]) -> SpecificationIndex:
        by_section = {item.section_number: item for item in sections}
        by_division: dict[str, list[str]] = {}
        by_discipline: dict[str, list[str]] = {}
        by_status: dict[str, list[str]] = {}
        by_revision: dict[str, list[str]] = {}

        for item in sections:
            section_number = item.section_number
            by_division.setdefault(item.division, []).append(section_number)
            by_discipline.setdefault(item.discipline.value, []).append(section_number)
            by_status.setdefault(item.status, []).append(section_number)
            by_revision.setdefault(item.revision or "n/a", []).append(section_number)

        for mapping in (by_division, by_discipline, by_status, by_revision):
            for values in mapping.values():
                values.sort()

        return SpecificationIndex(
            by_section=by_section,
            by_division=by_division,
            by_discipline=by_discipline,
            by_status=by_status,
            by_revision=by_revision,
        )

    def _build_relationships(
        self,
        sections: list[SpecificationSection],
    ) -> list[SpecificationRelationship]:
        relationships: list[SpecificationRelationship] = []
        seen: set[tuple[str, str, str]] = set()
        known_sections = {item.section_number for item in sections}

        for section in sections:
            source = section.section_number

            for part in section.parts:
                target_id = f"{source}:{part.part_number}"
                self._append_relationship(
                    relationships,
                    seen,
                    SpecificationRelationship(
                        source_id=source,
                        target_id=target_id,
                        relationship_type="has_part",
                        confidence=section.confidence,
                        evidence=part.title,
                    ),
                )

            for article in section.articles:
                target_id = f"{source}:article:{article.identifier}"
                self._append_relationship(
                    relationships,
                    seen,
                    SpecificationRelationship(
                        source_id=source,
                        target_id=target_id,
                        relationship_type="has_article",
                        confidence=section.confidence,
                        evidence=article.heading,
                    ),
                )

            for requirement in section.requirement_candidates:
                req_type = str(requirement.get("requirement_type") or "requirement")
                target_id = f"{source}:requirement:{req_type}"
                self._append_relationship(
                    relationships,
                    seen,
                    SpecificationRelationship(
                        source_id=source,
                        target_id=target_id,
                        relationship_type="has_requirement_candidate",
                        confidence=float(requirement.get("confidence", 0.75)),
                        evidence=str(requirement.get("text") or ""),
                    ),
                )

            for reference in section.references:
                rel_type = self._relationship_type_from_reference(
                    reference.reference_type.value
                )
                if (
                    reference.reference_type == SpecificationReferenceType.SECTION
                    and reference.target_id in known_sections
                ):
                    target_id = reference.target_id
                elif reference.reference_type == SpecificationReferenceType.SECTION:
                    continue
                else:
                    target_id = (
                        f"{reference.reference_type.value}:{reference.target_id}"
                    )

                self._append_relationship(
                    relationships,
                    seen,
                    SpecificationRelationship(
                        source_id=source,
                        target_id=target_id,
                        relationship_type=rel_type,
                        confidence=reference.confidence,
                        evidence=reference.source_text,
                    ),
                )

        return relationships

    @staticmethod
    def _append_relationship(
        relationships: list[SpecificationRelationship],
        seen: set[tuple[str, str, str]],
        relationship: SpecificationRelationship,
    ) -> None:
        key = (
            relationship.source_id,
            relationship.target_id,
            relationship.relationship_type,
        )
        if key in seen:
            return
        seen.add(key)
        relationships.append(relationship)

    @staticmethod
    def _relationship_type_from_reference(reference_type: str) -> str:
        mapping = {
            SpecificationReferenceType.SECTION.value: "references_specification",
            SpecificationReferenceType.DRAWING.value: "references_drawing",
            SpecificationReferenceType.EQUIPMENT.value: "references_equipment",
            SpecificationReferenceType.MANUFACTURER.value: "references_manufacturer",
            SpecificationReferenceType.PRODUCT.value: "references_product",
            SpecificationReferenceType.SYSTEM.value: "references_system",
            SpecificationReferenceType.STANDARD.value: "references_standard",
            SpecificationReferenceType.SCHEDULE.value: "references_schedule",
            SpecificationReferenceType.ADDENDUM.value: "references_addendum",
        }
        return mapping.get(reference_type, "references")

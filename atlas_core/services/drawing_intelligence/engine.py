"""Deterministic Atlas Drawing Intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_core.domain.bid_package_review import BidPackageReview

from atlas_core.services.drawing_intelligence.analyzer import DrawingAnalyzer
from atlas_core.services.drawing_intelligence.models import (
    DrawingHierarchy,
    DrawingIndex,
    DrawingIntelligenceResult,
    DrawingMetadata,
    DrawingReferenceType,
    DrawingRelationship,
    aggregate_confidence,
)


@dataclass
class DrawingIntelligenceEngine:
    """Build deterministic sheet metadata, hierarchy, and graph relationships."""

    analyzer: DrawingAnalyzer | None = None

    def __post_init__(self) -> None:
        if self.analyzer is None:
            self.analyzer = DrawingAnalyzer()

    def build(
        self,
        review: BidPackageReview,
        context: dict[str, Any] | None = None,
    ) -> DrawingIntelligenceResult:
        del context

        known_sheet_numbers = {
            sheet.sheet_number.strip().upper()
            for sheet in review.drawing_sheets
            if sheet.sheet_number
        }

        metadata = [
            self.analyzer.analyze_sheet(sheet, known_sheet_numbers)  # type: ignore[union-attr]
            for sheet in review.drawing_sheets
        ]

        drawing_index = self._build_index(metadata)
        hierarchy = self._build_hierarchy(review.project_id, metadata)
        relationships = self._build_relationships(metadata)

        confidence = aggregate_confidence(
            [
                review.confidence,
                aggregate_confidence([item.confidence for item in metadata]),
                aggregate_confidence([item.confidence for item in relationships]),
            ],
            default=review.confidence,
        )

        return DrawingIntelligenceResult(
            metadata=metadata,
            drawing_index=drawing_index,
            relationships=relationships,
            hierarchy=hierarchy,
            confidence=confidence,
        )

    def _build_index(self, metadata: list[DrawingMetadata]) -> DrawingIndex:
        by_sheet_number = {item.sheet_number.upper(): item for item in metadata}

        by_discipline: dict[str, list[str]] = {}
        by_category: dict[str, list[str]] = {}

        for item in metadata:
            discipline_key = item.discipline.value
            category_key = item.sheet_category.value
            sheet_key = item.sheet_number.upper()

            by_discipline.setdefault(discipline_key, []).append(sheet_key)
            by_category.setdefault(category_key, []).append(sheet_key)

        for value in by_discipline.values():
            value.sort()
        for value in by_category.values():
            value.sort()

        return DrawingIndex(
            by_sheet_number=by_sheet_number,
            by_discipline=by_discipline,
            by_sheet_category=by_category,
        )

    def _build_hierarchy(
        self,
        project_id: str,
        metadata: list[DrawingMetadata],
    ) -> DrawingHierarchy:
        disciplines: dict[str, dict[str, list[str]]] = {}

        for item in metadata:
            discipline_key = item.discipline.value
            set_key = item.sheet_category.value
            sheet_key = item.sheet_number.upper()
            discipline_sets = disciplines.setdefault(discipline_key, {})
            discipline_sets.setdefault(set_key, []).append(sheet_key)

        for drawing_sets in disciplines.values():
            for sheets in drawing_sets.values():
                sheets.sort()

        return DrawingHierarchy(
            project_id=project_id,
            disciplines=disciplines,
        )

    def _build_relationships(
        self,
        metadata: list[DrawingMetadata],
    ) -> list[DrawingRelationship]:
        sheet_numbers = {item.sheet_number.upper() for item in metadata}

        relationships: list[DrawingRelationship] = []
        seen: set[tuple[str, str, str]] = set()

        for item in metadata:
            source = item.sheet_number.upper()
            for ref in item.references:
                target = ref.target_id.upper()
                rel_type = self._relationship_type_from_reference(
                    ref.reference_type.value
                )

                if (
                    ref.reference_type == DrawingReferenceType.SHEET
                    and target in sheet_numbers
                ):
                    normalized_target = target
                elif ref.reference_type == DrawingReferenceType.SHEET:
                    continue
                else:
                    normalized_target = f"{source}:{ref.reference_type.value}:{target}"

                key = (source, normalized_target, rel_type)
                if key in seen:
                    continue
                seen.add(key)

                relationships.append(
                    DrawingRelationship(
                        source_id=source,
                        target_id=normalized_target,
                        relationship_type=rel_type,
                        confidence=ref.confidence,
                        evidence=ref.source_text,
                    )
                )

        return relationships

    @staticmethod
    def _relationship_type_from_reference(reference_type: str) -> str:
        mapping = {
            DrawingReferenceType.SHEET.value: "references_sheet",
            DrawingReferenceType.DETAIL.value: "references_detail",
            DrawingReferenceType.SECTION.value: "references_section",
            DrawingReferenceType.CALLOUT.value: "references_callout",
            DrawingReferenceType.VIEW.value: "references_view",
            DrawingReferenceType.SCHEDULE.value: "references_schedule",
            DrawingReferenceType.INDEX.value: "references_index",
        }
        return mapping.get(reference_type, "references")

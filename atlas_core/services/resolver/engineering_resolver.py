"""Deterministic engineering resolution for Atlas Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import fmean
from typing import Any

from atlas_core.domain.bid_package_review import BidPackageReview
from atlas_core.domain.drawing import DrawingSheet
from atlas_core.domain.equipment import Equipment
from atlas_core.domain.integrated_system import IntegratedSystem
from atlas_core.domain.room import Room
from atlas_core.domain.specification import SpecificationSection


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _split_references(value: Any) -> list[str]:
    text = _normalize_text(value)
    if not text:
        return []

    separators = ["\n", ";", ",", "|"]
    pieces = [text]
    for separator in separators:
        next_pieces: list[str] = []
        for piece in pieces:
            next_pieces.extend(piece.split(separator))
        pieces = next_pieces

    normalized = []
    for piece in pieces:
        item = piece.strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def _enum_text(value: Any) -> str:
    candidate = getattr(value, "value", value)
    return _normalize_text(candidate)


def _confidence_from(values: list[float], default: float = 0.75) -> float:
    if not values:
        return default
    return max(0.0, min(1.0, fmean(values)))


@dataclass(frozen=True)
class ResolutionEvidence:
    evidence_id: str
    evidence_type: str
    source_id: str
    summary: str
    confidence: float = 0.75
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source_id": self.source_id,
            "summary": self.summary,
            "confidence": self.confidence,
            "references": list(self.references),
        }


@dataclass(frozen=True)
class ResolutionConflict:
    conflict_id: str
    target_id: str
    field_name: str
    observed_values: list[str]
    message: str
    severity: str = "medium"
    evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "target_id": self.target_id,
            "field_name": self.field_name,
            "observed_values": list(self.observed_values),
            "message": self.message,
            "severity": self.severity,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class ResolutionRule:
    rule_id: str
    name: str
    target_type: str
    field_name: str
    description: str
    confidence_weight: float = 0.75
    requires_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "target_type": self.target_type,
            "field_name": self.field_name,
            "description": self.description,
            "confidence_weight": self.confidence_weight,
            "requires_review": self.requires_review,
        }


@dataclass(frozen=True)
class ResolvedObject:
    object_type: str
    object_id: str
    canonical_values: dict[str, Any]
    evidence_ids: list[str]
    rules_applied: list[str]
    confidence: float
    manual_review_required: bool = False
    conflict_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "object_id": self.object_id,
            "canonical_values": dict(self.canonical_values),
            "evidence_ids": list(self.evidence_ids),
            "rules_applied": list(self.rules_applied),
            "confidence": self.confidence,
            "manual_review_required": self.manual_review_required,
            "conflict_ids": list(self.conflict_ids),
        }


@dataclass(frozen=True)
class ResolverContext:
    review: BidPackageReview
    knowledge_graph: dict[str, Any] | None = None


@dataclass(frozen=True)
class ResolverResult:
    resolved_objects: list[ResolvedObject]
    conflicts: list[ResolutionConflict]
    rules_applied: list[ResolutionRule]
    confidence: float
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolved_objects": [item.to_dict() for item in self.resolved_objects],
            "conflicts": [item.to_dict() for item in self.conflicts],
            "rules_applied": [item.to_dict() for item in self.rules_applied],
            "confidence": self.confidence,
            "summary": dict(self.summary),
        }


class EngineeringResolver:
    """Deterministic resolver for extracted engineering objects."""

    def __init__(self) -> None:
        self._rules = [
            ResolutionRule(
                rule_id="resolver-equipment-manufacturer",
                name="Normalize equipment manufacturer",
                target_type="equipment",
                field_name="manufacturer",
                description="Resolve the equipment manufacturer to a canonical text value.",
                confidence_weight=0.9,
                requires_review=True,
            ),
            ResolutionRule(
                rule_id="resolver-equipment-system",
                name="Normalize equipment system",
                target_type="equipment",
                field_name="system_id",
                description="Resolve equipment system references against the extracted system list.",
                confidence_weight=0.86,
                requires_review=True,
            ),
            ResolutionRule(
                rule_id="resolver-equipment-room",
                name="Normalize equipment room",
                target_type="equipment",
                field_name="room_id",
                description="Resolve equipment room references against the extracted room list.",
                confidence_weight=0.84,
                requires_review=True,
            ),
            ResolutionRule(
                rule_id="resolver-equipment-drawing",
                name="Normalize equipment drawing references",
                target_type="equipment",
                field_name="drawing_reference",
                description="Split and normalize drawing references for equipment.",
                confidence_weight=0.8,
            ),
            ResolutionRule(
                rule_id="resolver-equipment-specification",
                name="Normalize equipment specification references",
                target_type="equipment",
                field_name="specification_reference",
                description="Split and normalize specification references for equipment.",
                confidence_weight=0.8,
            ),
            ResolutionRule(
                rule_id="resolver-system-equipment",
                name="Resolve system membership",
                target_type="system",
                field_name="equipment_ids",
                description="Resolve system members from equipment assignments.",
                confidence_weight=0.88,
            ),
            ResolutionRule(
                rule_id="resolver-room-equipment",
                name="Resolve room membership",
                target_type="room",
                field_name="equipment_ids",
                description="Resolve room members from equipment assignments.",
                confidence_weight=0.84,
            ),
            ResolutionRule(
                rule_id="resolver-manufacturer-equipment",
                name="Resolve manufacturer usage",
                target_type="manufacturer",
                field_name="equipment_ids",
                description="Resolve manufacturer usage from referenced equipment.",
                confidence_weight=0.82,
            ),
        ]

    @property
    def rules(self) -> list[ResolutionRule]:
        return list(self._rules)

    def resolve(self, context: ResolverContext) -> ResolverResult:
        review = context.review
        resolved_objects: list[ResolvedObject] = []
        conflicts: list[ResolutionConflict] = []

        rules_by_id = {rule.rule_id: rule for rule in self._rules}

        equipment_by_id = {item.equipment_id: item for item in review.equipment}
        systems_by_id = {item.system_id: item for item in review.systems}
        rooms_by_id = {item.room_id: item for item in review.rooms}
        drawings_by_id = {item.sheet_number: item for item in review.drawing_sheets}
        specifications_by_id = {
            item.section_number: item for item in review.specification_sections
        }

        manufacturer_names = sorted(
            {
                _normalize_text(item.manufacturer)
                for item in review.equipment
                if _normalize_text(item.manufacturer)
            }
        )

        for equipment in review.equipment:
            resolved_objects.extend(
                self._resolve_equipment(
                    equipment=equipment,
                    equipment_by_id=equipment_by_id,
                    systems_by_id=systems_by_id,
                    rooms_by_id=rooms_by_id,
                    drawings_by_id=drawings_by_id,
                    specifications_by_id=specifications_by_id,
                    rules_by_id=rules_by_id,
                    conflicts=conflicts,
                )
            )

        for system in review.systems:
            resolved_objects.append(
                self._resolve_system(system, review.equipment, rules_by_id, conflicts)
            )

        for room in review.rooms:
            resolved_objects.append(
                self._resolve_room(room, review.equipment, rules_by_id)
            )

        for drawing in review.drawing_sheets:
            resolved_objects.append(
                self._resolve_drawing(drawing, review.equipment, rules_by_id)
            )

        for specification in review.specification_sections:
            resolved_objects.append(
                self._resolve_specification(specification, review.equipment, rules_by_id)
            )

        for manufacturer_name in manufacturer_names:
            resolved_objects.append(
                self._resolve_manufacturer(
                    manufacturer_name, review.equipment, rules_by_id
                )
            )

        confidence = self._resolve_confidence(resolved_objects, conflicts)
        summary = {
            "resolved_count": len(resolved_objects),
            "conflict_count": len(conflicts),
            "manual_review_count": sum(
                1 for item in resolved_objects if item.manual_review_required
            ),
            "object_type_counts": self._count_object_types(resolved_objects),
            "confidence": confidence,
        }

        return ResolverResult(
            resolved_objects=resolved_objects,
            conflicts=conflicts,
            rules_applied=list(rules_by_id.values()),
            confidence=confidence,
            summary=summary,
        )

    def _resolve_equipment(
        self,
        *,
        equipment: Equipment,
        equipment_by_id: dict[str, Equipment],
        systems_by_id: dict[str, IntegratedSystem],
        rooms_by_id: dict[str, Room],
        drawings_by_id: dict[str, DrawingSheet],
        specifications_by_id: dict[str, SpecificationSection],
        rules_by_id: dict[str, ResolutionRule],
        conflicts: list[ResolutionConflict],
    ) -> list[ResolvedObject]:
        evidence_ids = [f"equipment:{equipment.equipment_id}"]
        canonical_values: dict[str, Any] = {
            "manufacturer": _normalize_text(equipment.manufacturer),
            "model": _normalize_text(equipment.model),
            "system_id": _normalize_text(equipment.system_id),
            "room_id": _normalize_text(equipment.room_id),
            "building_id": _normalize_text(equipment.building_id),
            "drawing_references": _split_references(equipment.drawing_reference),
            "specification_references": _split_references(
                equipment.specification_reference
            ),
            "confidence": equipment.confidence,
        }

        rules_applied = [
            rules_by_id["resolver-equipment-manufacturer"].rule_id,
            rules_by_id["resolver-equipment-system"].rule_id,
            rules_by_id["resolver-equipment-room"].rule_id,
            rules_by_id["resolver-equipment-drawing"].rule_id,
            rules_by_id["resolver-equipment-specification"].rule_id,
        ]
        manual_review_required = False

        system_id = canonical_values["system_id"]
        if system_id and system_id not in systems_by_id:
            conflict_id = f"conflict:equipment:{equipment.equipment_id}:system"
            conflicts.append(
                ResolutionConflict(
                    conflict_id=conflict_id,
                    target_id=f"equipment:{equipment.equipment_id}",
                    field_name="system_id",
                    observed_values=[system_id],
                    message="Equipment references a system that is not present in the review.",
                    severity="high",
                    evidence_ids=evidence_ids,
                )
            )
            manual_review_required = True

        room_id = canonical_values["room_id"]
        if room_id and room_id not in rooms_by_id:
            conflict_id = f"conflict:equipment:{equipment.equipment_id}:room"
            conflicts.append(
                ResolutionConflict(
                    conflict_id=conflict_id,
                    target_id=f"equipment:{equipment.equipment_id}",
                    field_name="room_id",
                    observed_values=[room_id],
                    message="Equipment references a room that is not present in the review.",
                    severity="medium",
                    evidence_ids=evidence_ids,
                )
            )
            manual_review_required = True

        drawing_references = canonical_values["drawing_references"]
        for drawing_reference in drawing_references:
            if drawing_reference not in drawings_by_id:
                conflict_id = (
                    f"conflict:equipment:{equipment.equipment_id}:drawing:{drawing_reference}"
                )
                conflicts.append(
                    ResolutionConflict(
                        conflict_id=conflict_id,
                        target_id=f"equipment:{equipment.equipment_id}",
                        field_name="drawing_reference",
                        observed_values=[drawing_reference],
                        message="Equipment references a drawing that is not present in the review.",
                        severity="low",
                        evidence_ids=evidence_ids,
                    )
                )
                manual_review_required = True

        specification_references = canonical_values["specification_references"]
        for specification_reference in specification_references:
            if specification_reference not in specifications_by_id:
                conflict_id = (
                    f"conflict:equipment:{equipment.equipment_id}:spec:{specification_reference}"
                )
                conflicts.append(
                    ResolutionConflict(
                        conflict_id=conflict_id,
                        target_id=f"equipment:{equipment.equipment_id}",
                        field_name="specification_reference",
                        observed_values=[specification_reference],
                        message="Equipment references a specification that is not present in the review.",
                        severity="low",
                        evidence_ids=evidence_ids,
                    )
                )
                manual_review_required = True

        if not canonical_values["manufacturer"]:
            manual_review_required = True
        if not canonical_values["model"]:
            manual_review_required = True

        confidence = self._resolve_confidence_value(
            equipment.confidence,
            0.9 if canonical_values["manufacturer"] else 0.55,
            0.9 if canonical_values["model"] else 0.55,
            0.9 if not conflicts else 0.65,
        )

        return [
            ResolvedObject(
                object_type="equipment",
                object_id=equipment.equipment_id,
                canonical_values=canonical_values,
                evidence_ids=evidence_ids,
                rules_applied=rules_applied,
                confidence=confidence,
                manual_review_required=manual_review_required,
                conflict_ids=[
                    item.conflict_id
                    for item in conflicts
                    if item.target_id == f"equipment:{equipment.equipment_id}"
                ],
            )
        ]

    def _resolve_system(
        self,
        system: IntegratedSystem,
        equipment: list[Equipment],
        rules_by_id: dict[str, ResolutionRule],
        conflicts: list[ResolutionConflict],
    ) -> ResolvedObject:
        system_equipment = [
            item for item in equipment if _normalize_text(item.system_id) == system.system_id
        ]
        evidence_ids = [f"system:{system.system_id}"] + [
            f"equipment:{item.equipment_id}" for item in system_equipment
        ]
        manual_review_required = not bool(system_equipment)
        confidence = self._resolve_confidence_value(
            system.confidence,
            0.9 if system_equipment else 0.6,
        )
        return ResolvedObject(
            object_type="system",
            object_id=system.system_id,
            canonical_values={
                "name": system.name,
                "category": system.category.value,
                "room_id": _normalize_text(system.room_id),
                "building_id": _normalize_text(system.building_id),
                "equipment_ids": [item.equipment_id for item in system_equipment],
                "confidence": system.confidence,
            },
            evidence_ids=evidence_ids,
            rules_applied=[rules_by_id["resolver-system-equipment"].rule_id],
            confidence=confidence,
            manual_review_required=manual_review_required,
            conflict_ids=[
                item.conflict_id
                for item in conflicts
                if item.target_id == f"system:{system.system_id}"
            ],
        )

    def _resolve_room(
        self,
        room: Room,
        equipment: list[Equipment],
        rules_by_id: dict[str, ResolutionRule],
    ) -> ResolvedObject:
        room_equipment = [
            item for item in equipment if _normalize_text(item.room_id) == room.room_id
        ]
        room_system_ids = sorted(
            {
                _normalize_text(item.system_id)
                for item in room_equipment
                if _normalize_text(item.system_id)
            }
        )
        evidence_ids = [f"room:{room.room_id}"] + [
            f"equipment:{item.equipment_id}" for item in room_equipment
        ]
        confidence = self._resolve_confidence_value(
            room.confidence,
            0.9 if room_equipment else 0.6,
        )
        return ResolvedObject(
            object_type="room",
            object_id=room.room_id,
            canonical_values={
                "name": room.name,
                "building_id": room.building_id,
                "room_type": room.room_type.value,
                "space_ids": list(room.space_ids),
                "system_ids": room_system_ids,
                "equipment_ids": [item.equipment_id for item in room_equipment],
                "confidence": room.confidence,
            },
            evidence_ids=evidence_ids,
            rules_applied=[rules_by_id["resolver-room-equipment"].rule_id],
            confidence=confidence,
            manual_review_required=not bool(room_equipment),
        )

    def _resolve_drawing(
        self,
        drawing: DrawingSheet,
        equipment: list[Equipment],
        rules_by_id: dict[str, ResolutionRule],
    ) -> ResolvedObject:
        linked_equipment = [
            item
            for item in equipment
            if drawing.sheet_number in _split_references(item.drawing_reference)
        ]
        evidence_ids = [f"drawing:{drawing.sheet_number}"] + [
            f"equipment:{item.equipment_id}" for item in linked_equipment
        ]
        confidence = self._resolve_confidence_value(
            drawing.confidence,
            0.9 if linked_equipment else 0.6,
        )
        return ResolvedObject(
            object_type="drawing",
            object_id=drawing.sheet_number,
            canonical_values={
                "sheet_id": drawing.sheet_id,
                "sheet_number": drawing.sheet_number,
                "title": drawing.title,
                "discipline": drawing.discipline.value,
                "page_number": drawing.page_number,
                "equipment_ids": [item.equipment_id for item in linked_equipment],
                "confidence": drawing.confidence,
            },
            evidence_ids=evidence_ids,
            rules_applied=[rules_by_id["resolver-equipment-drawing"].rule_id],
            confidence=confidence,
            manual_review_required=not bool(linked_equipment),
        )

    def _resolve_specification(
        self,
        specification: SpecificationSection,
        equipment: list[Equipment],
        rules_by_id: dict[str, ResolutionRule],
    ) -> ResolvedObject:
        linked_equipment = [
            item
            for item in equipment
            if specification.section_number
            in _split_references(item.specification_reference)
        ]
        evidence_ids = [f"specification:{specification.section_number}"] + [
            f"equipment:{item.equipment_id}" for item in linked_equipment
        ]
        confidence = self._resolve_confidence_value(
            specification.confidence,
            0.9 if linked_equipment else 0.6,
        )
        return ResolvedObject(
            object_type="specification",
            object_id=specification.section_number,
            canonical_values={
                "section_id": specification.section_id,
                "section_number": specification.section_number,
                "title": specification.title,
                "discipline": _enum_text(specification.discipline),
                "manufacturers": list(specification.manufacturers),
                "equipment_ids": [item.equipment_id for item in linked_equipment],
                "confidence": specification.confidence,
            },
            evidence_ids=evidence_ids,
            rules_applied=[rules_by_id["resolver-equipment-specification"].rule_id],
            confidence=confidence,
            manual_review_required=not bool(linked_equipment),
        )

    def _resolve_manufacturer(
        self,
        manufacturer_name: str,
        equipment: list[Equipment],
        rules_by_id: dict[str, ResolutionRule],
    ) -> ResolvedObject:
        linked_equipment = [
            item
            for item in equipment
            if _normalize_text(item.manufacturer).lower() == manufacturer_name.lower()
        ]
        evidence_ids = [f"manufacturer:{manufacturer_name}"] + [
            f"equipment:{item.equipment_id}" for item in linked_equipment
        ]
        categories = sorted(
            {
                _enum_text(item.category)
                for item in linked_equipment
                if _enum_text(item.category)
            }
        )
        confidence = self._resolve_confidence_value(
            _confidence_from([item.confidence for item in linked_equipment]),
            0.9 if linked_equipment else 0.6,
        )
        return ResolvedObject(
            object_type="manufacturer",
            object_id=manufacturer_name,
            canonical_values={
                "name": manufacturer_name,
                "product_families": categories,
                "equipment_ids": [item.equipment_id for item in linked_equipment],
                "confidence": confidence,
            },
            evidence_ids=evidence_ids,
            rules_applied=[rules_by_id["resolver-manufacturer-equipment"].rule_id],
            confidence=confidence,
            manual_review_required=not bool(linked_equipment),
        )

    @staticmethod
    def _resolve_confidence_value(*values: float) -> float:
        return max(0.0, min(1.0, fmean(values)))

    @staticmethod
    def _resolve_confidence(
        resolved_objects: list[ResolvedObject],
        conflicts: list[ResolutionConflict],
    ) -> float:
        if not resolved_objects:
            return 0.0

        base = fmean(item.confidence for item in resolved_objects)
        penalty = min(0.3, len(conflicts) * 0.03)
        review_penalty = min(
            0.2,
            sum(1 for item in resolved_objects if item.manual_review_required) * 0.02,
        )
        return max(0.0, min(1.0, base - penalty - review_penalty))

    @staticmethod
    def _count_object_types(resolved_objects: list[ResolvedObject]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in resolved_objects:
            counts[item.object_type] = counts.get(item.object_type, 0) + 1
        return counts
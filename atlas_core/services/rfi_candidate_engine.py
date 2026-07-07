"""Deterministic RFI candidate detection engine for Atlas Core."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import re
from typing import Any

from atlas_core.domain import (
    BidPackageReview,
    RFICandidate,
    RFICandidateCategory,
    RFICandidateSeverity,
    RFICandidateSourceRef,
)


@dataclass(frozen=True)
class _CandidateDraft:
    title: str
    description: str
    category: RFICandidateCategory
    severity: RFICandidateSeverity
    confidence: float
    detected_condition: str
    recommended_action: str
    source_refs: tuple[RFICandidateSourceRef, ...]
    related_items: tuple[str, ...]


class RFICandidateEngine:
    ENGINE_VERSION = "rfi-candidate-engine/1.0.0"

    _MISSING_MODEL_TOKENS = {"tbd", "n/a", "na", "unknown", "to be determined"}
    _RESPONSIBILITY_TOKENS = {
        "ofe",
        "ofci",
        "cfci",
        "nic",
        "by others",
        "owner provided",
        "contractor provided",
    }
    _PLACEHOLDER_TOKENS = {
        "tbd",
        "to be determined",
        "as selected",
        "by others",
        "allowance",
        "future",
        "generic",
    }
    _ADD_ALTERNATE_TOKENS = {"add alternate", "alternate", "allowance"}
    _UNAVAILABLE_PRODUCT_TOKENS = {
        "discontinued",
        "obsolete",
        "no longer available",
        "unavailable",
    }
    _INSTALLATION_RESPONSIBILITY_TOKENS = {
        "mount",
        "mounting",
        "power",
        "network",
        "conduit",
        "backing",
        "rigging",
        "structural",
    }

    def build(self, review: BidPackageReview) -> list[RFICandidate]:
        drafts: list[_CandidateDraft] = []
        drafts.extend(self._detect_missing_model(review))
        drafts.extend(self._detect_missing_manufacturer(review))
        drafts.extend(self._detect_quantity_conflicts(review))
        drafts.extend(self._detect_scope_responsibility_ambiguity(review))
        drafts.extend(self._detect_placeholder_descriptions(review))
        drafts.extend(self._detect_responsibility_gaps(review))
        drafts.extend(self._detect_add_alternate_ambiguity(review))
        drafts.extend(self._detect_unavailable_product_references(review))
        drafts.extend(self._detect_drawing_spec_gaps(review))
        deduped = self._suppress_duplicates(drafts)

        candidates: list[RFICandidate] = []
        for draft in deduped:
            candidate_key = self._candidate_key(draft)
            candidate_id = self._candidate_id(review.project_id, candidate_key)
            candidates.append(
                RFICandidate(
                    candidate_id=candidate_id,
                    project_id=review.project_id,
                    title=draft.title,
                    description=draft.description,
                    category=draft.category,
                    severity=draft.severity,
                    confidence=draft.confidence,
                    source_refs=list(draft.source_refs),
                    related_items=list(draft.related_items),
                    detected_condition=draft.detected_condition,
                    recommended_action=draft.recommended_action,
                    created_by_engine_version=self.ENGINE_VERSION,
                )
            )

        return sorted(candidates, key=lambda candidate: candidate.candidate_id)

    def _detect_missing_model(self, review: BidPackageReview) -> list[_CandidateDraft]:
        grouped_items: dict[
            tuple[str, str, str],
            list[tuple[str, str]],
        ] = defaultdict(list)
        for item in review.equipment:
            manufacturer = self._text(getattr(item, "manufacturer", None))
            model = self._text(getattr(item, "model", None))
            if not manufacturer or self._has_meaningful_value(model):
                continue

            equipment_id = self._text(getattr(item, "equipment_id", None))
            if not equipment_id:
                continue

            description = self._text(getattr(item, "description", None))
            category = self._enum_value(getattr(item, "category", None))
            group_key = (manufacturer.casefold(), description.casefold(), category)
            grouped_items[group_key].append((equipment_id, description))

        drafts: list[_CandidateDraft] = []
        for (manufacturer_key, description_key, _), grouped in grouped_items.items():
            equipment_ids = tuple(sorted(item_id for item_id, _ in grouped))
            sample_id = equipment_ids[0]
            sample_description = next(
                (
                    description
                    for item_id, description in grouped
                    if item_id == sample_id and description
                ),
                description_key,
            )
            scope_text = (
                f" across {len(equipment_ids)} related items"
                if len(equipment_ids) > 1
                else ""
            )

            drafts.append(
                _CandidateDraft(
                    title=f"Missing model number for {sample_id}",
                    description=(
                        f"Equipment {sample_id} has manufacturer '{manufacturer_key}' "
                        f"but no usable model number was detected{scope_text}."
                    ),
                    category=RFICandidateCategory.MISSING_INFORMATION,
                    severity=RFICandidateSeverity.HIGH,
                    confidence=self._confidence(0.9, source_count=len(equipment_ids)),
                    detected_condition="missing_model_number",
                    recommended_action=(
                        "Confirm basis-of-design model number or accepted equal before "
                        "pricing."
                    ),
                    source_refs=tuple(
                        RFICandidateSourceRef(
                            source_type="equipment",
                            source_id=equipment_id,
                            field="model",
                            source_label=description or sample_description,
                            excerpt=f"manufacturer={manufacturer_key}",
                        )
                        for equipment_id, description in grouped
                    ),
                    related_items=equipment_ids,
                )
            )

        return drafts

    def _detect_missing_manufacturer(
        self,
        review: BidPackageReview,
    ) -> list[_CandidateDraft]:
        drafts: list[_CandidateDraft] = []
        for item in review.equipment:
            manufacturer = self._text(getattr(item, "manufacturer", None))
            category_value = self._enum_value(getattr(item, "category", None))
            specification_reference = self._text(
                getattr(item, "specification_reference", None)
            )
            if manufacturer:
                continue
            if not category_value and not specification_reference:
                continue

            equipment_id = self._text(getattr(item, "equipment_id", None))
            if not equipment_id:
                continue

            source_refs = [
                RFICandidateSourceRef(
                    source_type="equipment",
                    source_id=equipment_id,
                    field="manufacturer",
                    source_label=getattr(item, "description", None),
                    excerpt=(
                        f"category={category_value or 'unknown'}"
                        f" spec={specification_reference or 'none'}"
                    ),
                )
            ]
            if specification_reference:
                source_refs.append(
                    RFICandidateSourceRef(
                        source_type="specification",
                        source_id=specification_reference,
                        source_label=specification_reference,
                    )
                )

            drafts.append(
                _CandidateDraft(
                    title=f"Missing manufacturer for {equipment_id}",
                    description=(
                        f"Equipment {equipment_id} has known device context but no "
                        "manufacturer assignment."
                    ),
                    category=RFICandidateCategory.MISSING_INFORMATION,
                    severity=RFICandidateSeverity.MEDIUM,
                    confidence=self._confidence(0.82, source_count=len(source_refs)),
                    detected_condition="missing_manufacturer",
                    recommended_action=(
                        "Confirm named manufacturer or approved manufacturers list for "
                        "this item."
                    ),
                    source_refs=tuple(source_refs),
                    related_items=(equipment_id,),
                )
            )

        return drafts

    def _detect_quantity_conflicts(
        self,
        review: BidPackageReview,
    ) -> list[_CandidateDraft]:
        drafts: list[_CandidateDraft] = []

        for issue in review.reconciliation_issues:
            message = self._text(getattr(issue, "message", None)).casefold()
            if "quantity" not in message and "count" not in message:
                continue

            issue_id = self._text(getattr(issue, "issue_id", None)) or "unknown"
            target_id = self._text(getattr(issue, "target_id", None)) or "unknown"
            drafts.append(
                _CandidateDraft(
                    title="Quantity conflict identified across project sources",
                    description=getattr(
                        issue, "message", "Quantity conflict detected."
                    ),
                    category=RFICandidateCategory.QUANTITY_CONFLICT,
                    severity=RFICandidateSeverity.HIGH,
                    confidence=self._confidence(0.88, source_count=1),
                    detected_condition="quantity_conflict",
                    recommended_action=(
                        "Resolve quantity discrepancy between schedule, drawings, and "
                        "narrative notes before pricing."
                    ),
                    source_refs=(
                        RFICandidateSourceRef(
                            source_type="reconciliation_issue",
                            source_id=issue_id,
                            source_label=target_id,
                            excerpt=getattr(issue, "message", None),
                        ),
                    ),
                    related_items=(target_id,),
                )
            )

        equipment_by_fingerprint: dict[str, tuple[str, float]] = {}
        for item in review.equipment:
            equipment_id = self._text(getattr(item, "equipment_id", None))
            if not equipment_id:
                continue
            fingerprint = self._item_fingerprint(
                manufacturer=getattr(item, "manufacturer", None),
                model=getattr(item, "model", None),
                description=getattr(item, "description", None),
            )
            equipment_by_fingerprint[fingerprint] = (
                equipment_id,
                float(getattr(item, "quantity", 0) or 0),
            )

        for schedule in review.device_schedules:
            schedule_id = self._text(getattr(schedule, "schedule_id", None))
            for schedule_item in getattr(schedule, "items", []):
                fingerprint = self._item_fingerprint(
                    manufacturer=getattr(schedule_item, "manufacturer", None),
                    model=getattr(schedule_item, "model", None),
                    description=getattr(schedule_item, "description", None),
                )
                if fingerprint not in equipment_by_fingerprint:
                    continue
                equipment_id, equipment_quantity = equipment_by_fingerprint[fingerprint]
                schedule_quantity = float(getattr(schedule_item, "quantity", 0) or 0)
                if abs(equipment_quantity - schedule_quantity) < 1e-6:
                    continue

                schedule_item_id = self._text(getattr(schedule_item, "item_id", None))
                drafts.append(
                    _CandidateDraft(
                        title=f"Quantity mismatch for {equipment_id}",
                        description=(
                            f"Equipment quantity is {equipment_quantity:g} while device "
                            f"schedule quantity is {schedule_quantity:g}."
                        ),
                        category=RFICandidateCategory.QUANTITY_CONFLICT,
                        severity=RFICandidateSeverity.HIGH,
                        confidence=self._confidence(0.93, source_count=2),
                        detected_condition="quantity_conflict",
                        recommended_action=(
                            "Confirm final quantity and update all source documents to "
                            "a single coordinated value."
                        ),
                        source_refs=(
                            RFICandidateSourceRef(
                                source_type="equipment",
                                source_id=equipment_id,
                                field="quantity",
                                excerpt=f"quantity={equipment_quantity:g}",
                            ),
                            RFICandidateSourceRef(
                                source_type="device_schedule",
                                source_id=schedule_item_id or "unknown-schedule-item",
                                field="quantity",
                                source_label=schedule_id,
                                excerpt=f"quantity={schedule_quantity:g}",
                            ),
                        ),
                        related_items=(equipment_id, schedule_item_id or "unknown"),
                    )
                )

        return drafts

    def _detect_scope_responsibility_ambiguity(
        self,
        review: BidPackageReview,
    ) -> list[_CandidateDraft]:
        drafts: list[_CandidateDraft] = []
        token_hits: dict[str, list[RFICandidateSourceRef]] = defaultdict(list)

        for source_ref, text in self._iter_review_text(review):
            normalized = text.casefold()
            for token in self._RESPONSIBILITY_TOKENS:
                if token in normalized:
                    token_hits[token].append(source_ref)

        if not token_hits:
            return drafts

        tokens = sorted(token_hits)
        source_refs = tuple(ref for refs in token_hits.values() for ref in refs[:2])
        severity = (
            RFICandidateSeverity.HIGH
            if len(tokens) > 1
            else RFICandidateSeverity.MEDIUM
        )

        drafts.append(
            _CandidateDraft(
                title="Scope responsibility language is ambiguous",
                description=(
                    "Detected responsibility qualifiers that may shift scope without a "
                    f"clear matrix: {', '.join(tokens)}."
                ),
                category=RFICandidateCategory.RESPONSIBILITY_GAP,
                severity=severity,
                confidence=self._confidence(0.84, source_count=len(source_refs)),
                detected_condition="scope_responsibility_ambiguity",
                recommended_action=(
                    "Issue a responsibility matrix request clarifying installer, "
                    "provider, and cost owner for each affected item."
                ),
                source_refs=source_refs,
                related_items=tuple(sorted({ref.source_id for ref in source_refs})),
            )
        )

        return drafts

    def _detect_placeholder_descriptions(
        self,
        review: BidPackageReview,
    ) -> list[_CandidateDraft]:
        drafts: list[_CandidateDraft] = []
        for item in review.equipment:
            description = self._text(getattr(item, "description", None))
            normalized = description.casefold()
            if not any(token in normalized for token in self._PLACEHOLDER_TOKENS):
                continue
            equipment_id = self._text(getattr(item, "equipment_id", None))
            if not equipment_id:
                continue

            drafts.append(
                _CandidateDraft(
                    title=f"Placeholder device description for {equipment_id}",
                    description=(
                        f"Equipment description '{description}' appears generic and may "
                        "not be priceable without clarification."
                    ),
                    category=RFICandidateCategory.MISSING_INFORMATION,
                    severity=RFICandidateSeverity.MEDIUM,
                    confidence=self._confidence(0.8, source_count=1),
                    detected_condition="placeholder_device_description",
                    recommended_action=(
                        "Request a specific performance requirement or basis-of-design "
                        "selection for this item."
                    ),
                    source_refs=(
                        RFICandidateSourceRef(
                            source_type="equipment",
                            source_id=equipment_id,
                            field="description",
                            excerpt=description,
                        ),
                    ),
                    related_items=(equipment_id,),
                )
            )

        return drafts

    def _detect_responsibility_gaps(
        self,
        review: BidPackageReview,
    ) -> list[_CandidateDraft]:
        drafts: list[_CandidateDraft] = []
        responsibility_text = self._review_installation_text(review)
        for item in review.equipment:
            category = self._enum_value(getattr(item, "category", None))
            if category not in {"projector", "display", "camera", "speaker", "drapery"}:
                continue
            equipment_id = self._text(getattr(item, "equipment_id", None))
            if not equipment_id:
                continue

            if any(
                token in responsibility_text
                for token in self._INSTALLATION_RESPONSIBILITY_TOKENS
            ):
                continue

            drafts.append(
                _CandidateDraft(
                    title=f"Installation responsibility gap for {equipment_id}",
                    description=(
                        "No mounting/power/network/conduit/backing/rigging/structural "
                        "responsibility language was detected for this installation item."
                    ),
                    category=RFICandidateCategory.RESPONSIBILITY_GAP,
                    severity=RFICandidateSeverity.HIGH,
                    confidence=self._confidence(0.79, source_count=1),
                    detected_condition="installation_responsibility_gap",
                    recommended_action=(
                        "Request explicit trade responsibility for mounting, pathway, "
                        "power, data, and structural support."
                    ),
                    source_refs=(
                        RFICandidateSourceRef(
                            source_type="equipment",
                            source_id=equipment_id,
                            source_label=getattr(item, "description", None),
                        ),
                    ),
                    related_items=(equipment_id,),
                )
            )

        return drafts

    def _detect_add_alternate_ambiguity(
        self,
        review: BidPackageReview,
    ) -> list[_CandidateDraft]:
        drafts: list[_CandidateDraft] = []
        for source_ref, text in self._iter_review_text(review):
            normalized = text.casefold()
            if not any(token in normalized for token in self._ADD_ALTERNATE_TOKENS):
                continue
            if self._contains_pricing_detail(normalized):
                continue

            drafts.append(
                _CandidateDraft(
                    title="Add alternate or allowance language needs clarification",
                    description=(
                        "Detected add alternate/allowance language without enough "
                        "pricing definition (scope, quantity, or basis of design)."
                    ),
                    category=RFICandidateCategory.ADD_ALTERNATE_CLARIFICATION,
                    severity=RFICandidateSeverity.HIGH,
                    confidence=self._confidence(0.86, source_count=1),
                    detected_condition="add_alternate_ambiguity",
                    recommended_action=(
                        "Request add alternate definition including scope limits, "
                        "quantity basis, and acceptable products."
                    ),
                    source_refs=(source_ref,),
                    related_items=(source_ref.source_id,),
                )
            )

        return drafts

    def _detect_unavailable_product_references(
        self,
        review: BidPackageReview,
    ) -> list[_CandidateDraft]:
        drafts: list[_CandidateDraft] = []

        for source_ref, text in self._iter_review_text(review):
            normalized = text.casefold()
            if not any(
                token in normalized for token in self._UNAVAILABLE_PRODUCT_TOKENS
            ):
                continue

            drafts.append(
                _CandidateDraft(
                    title="Potential discontinued or unavailable product detected",
                    description=(
                        "Project data references an unavailable/discontinued product that "
                        "requires substitution guidance."
                    ),
                    category=RFICandidateCategory.PRODUCT_CONFLICT,
                    severity=RFICandidateSeverity.CRITICAL,
                    confidence=self._confidence(0.91, source_count=1),
                    detected_condition="product_unavailable_reference",
                    recommended_action=(
                        "Request approved substitution path and any performance "
                        "equivalency requirements."
                    ),
                    source_refs=(source_ref,),
                    related_items=(source_ref.source_id,),
                )
            )

        return drafts

    def _detect_drawing_spec_gaps(
        self,
        review: BidPackageReview,
    ) -> list[_CandidateDraft]:
        drafts: list[_CandidateDraft] = []
        for item in review.equipment:
            equipment_id = self._text(getattr(item, "equipment_id", None))
            if not equipment_id:
                continue

            drawing_reference = self._text(getattr(item, "drawing_reference", None))
            specification_reference = self._text(
                getattr(item, "specification_reference", None)
            )
            if bool(drawing_reference) == bool(specification_reference):
                continue

            missing_reference = (
                "specification"
                if drawing_reference and not specification_reference
                else "drawing"
            )
            source_refs = [
                RFICandidateSourceRef(
                    source_type="equipment",
                    source_id=equipment_id,
                    source_label=getattr(item, "description", None),
                    excerpt=(
                        f"drawing={drawing_reference or 'none'} "
                        f"spec={specification_reference or 'none'}"
                    ),
                )
            ]
            if drawing_reference:
                source_refs.append(
                    RFICandidateSourceRef(
                        source_type="drawing",
                        source_id=drawing_reference,
                        source_label=drawing_reference,
                    )
                )
            if specification_reference:
                source_refs.append(
                    RFICandidateSourceRef(
                        source_type="specification",
                        source_id=specification_reference,
                        source_label=specification_reference,
                    )
                )

            drafts.append(
                _CandidateDraft(
                    title=f"Drawing/spec mismatch for {equipment_id}",
                    description=(
                        f"Equipment {equipment_id} is missing a linked {missing_reference} "
                        "reference, creating a cross-reference gap."
                    ),
                    category=RFICandidateCategory.DRAWING_SPEC_MISMATCH,
                    severity=RFICandidateSeverity.MEDIUM,
                    confidence=self._confidence(0.87, source_count=len(source_refs)),
                    detected_condition="drawing_spec_cross_reference_gap",
                    recommended_action=(
                        "Confirm both drawing and specification references for this item "
                        "to align scope and pricing basis."
                    ),
                    source_refs=tuple(source_refs),
                    related_items=(equipment_id,),
                )
            )

        return drafts

    @classmethod
    def _iter_review_text(
        cls,
        review: BidPackageReview,
    ) -> list[tuple[RFICandidateSourceRef, str]]:
        rows: list[tuple[RFICandidateSourceRef, str]] = []

        for sheet in review.drawing_sheets:
            sheet_id = cls._text(getattr(sheet, "sheet_id", None))
            title = cls._text(getattr(sheet, "title", None))
            if sheet_id and title:
                rows.append(
                    (
                        RFICandidateSourceRef(
                            source_type="drawing",
                            source_id=sheet_id,
                            field="title",
                            source_label=getattr(sheet, "sheet_number", None),
                            excerpt=title,
                        ),
                        title,
                    )
                )
            for note in getattr(sheet, "notes", []):
                text_note = cls._text(note)
                if not text_note or not sheet_id:
                    continue
                rows.append(
                    (
                        RFICandidateSourceRef(
                            source_type="drawing",
                            source_id=sheet_id,
                            field="notes",
                            source_label=getattr(sheet, "sheet_number", None),
                            excerpt=text_note,
                        ),
                        text_note,
                    )
                )

        for section in review.specification_sections:
            section_id = cls._text(getattr(section, "section_id", None))
            title = cls._text(getattr(section, "title", None))
            if section_id and title:
                rows.append(
                    (
                        RFICandidateSourceRef(
                            source_type="specification",
                            source_id=section_id,
                            field="title",
                            source_label=getattr(section, "section_number", None),
                            excerpt=title,
                        ),
                        title,
                    )
                )
            for note in getattr(section, "notes", []):
                text_note = cls._text(note)
                if not text_note or not section_id:
                    continue
                rows.append(
                    (
                        RFICandidateSourceRef(
                            source_type="specification",
                            source_id=section_id,
                            field="notes",
                            source_label=getattr(section, "section_number", None),
                            excerpt=text_note,
                        ),
                        text_note,
                    )
                )

        for schedule in review.device_schedules:
            schedule_id = cls._text(getattr(schedule, "schedule_id", None))
            for item in getattr(schedule, "items", []):
                item_id = cls._text(getattr(item, "item_id", None))
                description = cls._text(getattr(item, "description", None))
                if schedule_id and item_id and description:
                    rows.append(
                        (
                            RFICandidateSourceRef(
                                source_type="device_schedule",
                                source_id=item_id,
                                field="description",
                                source_label=schedule_id,
                                excerpt=description,
                            ),
                            description,
                        )
                    )
                for note in getattr(item, "notes", []):
                    text_note = cls._text(note)
                    if not text_note or not item_id:
                        continue
                    rows.append(
                        (
                            RFICandidateSourceRef(
                                source_type="device_schedule",
                                source_id=item_id,
                                field="notes",
                                source_label=schedule_id,
                                excerpt=text_note,
                            ),
                            text_note,
                        )
                    )

        for equipment_item in review.equipment:
            equipment_id = cls._text(getattr(equipment_item, "equipment_id", None))
            description = cls._text(getattr(equipment_item, "description", None))
            if equipment_id and description:
                rows.append(
                    (
                        RFICandidateSourceRef(
                            source_type="equipment",
                            source_id=equipment_id,
                            field="description",
                            excerpt=description,
                        ),
                        description,
                    )
                )
            for assumption in getattr(equipment_item, "assumptions", []):
                text_assumption = cls._text(assumption)
                if not text_assumption or not equipment_id:
                    continue
                rows.append(
                    (
                        RFICandidateSourceRef(
                            source_type="equipment",
                            source_id=equipment_id,
                            field="assumptions",
                            excerpt=text_assumption,
                        ),
                        text_assumption,
                    )
                )

        for issue in review.reconciliation_issues:
            issue_id = cls._text(getattr(issue, "issue_id", None))
            message = cls._text(getattr(issue, "message", None))
            if issue_id and message:
                rows.append(
                    (
                        RFICandidateSourceRef(
                            source_type="reconciliation_issue",
                            source_id=issue_id,
                            field="message",
                            source_label=cls._text(getattr(issue, "target_id", None)),
                            excerpt=message,
                        ),
                        message,
                    )
                )

        for scope_gap in review.scope_gaps:
            gap_id = cls._text(getattr(scope_gap, "gap_id", None))
            message = cls._text(getattr(scope_gap, "message", None))
            if gap_id and message:
                rows.append(
                    (
                        RFICandidateSourceRef(
                            source_type="scope_gap",
                            source_id=gap_id,
                            field="message",
                            source_label=cls._text(
                                getattr(scope_gap, "target_id", None)
                            ),
                            excerpt=message,
                        ),
                        message,
                    )
                )

        for assumption in review.engineering_assumptions:
            assumption_id = cls._text(getattr(assumption, "assumption_id", None))
            description = cls._text(getattr(assumption, "description", None))
            if assumption_id and description:
                rows.append(
                    (
                        RFICandidateSourceRef(
                            source_type="engineering_assumption",
                            source_id=assumption_id,
                            field="description",
                            source_label=cls._text(
                                getattr(assumption, "related_equipment", None)
                            ),
                            excerpt=description,
                        ),
                        description,
                    )
                )

        return rows

    @classmethod
    def _review_installation_text(cls, review: BidPackageReview) -> str:
        return " ".join(text.casefold() for _, text in cls._iter_review_text(review))

    @classmethod
    def _contains_pricing_detail(cls, normalized_text: str) -> bool:
        return bool(
            re.search(
                r"\b(qty|quantity|model|manufacturer|basis of design)\b",
                normalized_text,
            )
            or "$" in normalized_text
            or bool(re.search(r"\b\d+\b", normalized_text))
        )

    @classmethod
    def _suppress_duplicates(
        cls, drafts: list[_CandidateDraft]
    ) -> list[_CandidateDraft]:
        deduped: dict[str, _CandidateDraft] = {}
        for draft in drafts:
            key = cls._candidate_key(draft)
            existing = deduped.get(key)
            if existing is None or draft.confidence > existing.confidence:
                deduped[key] = draft

        return list(deduped.values())

    @classmethod
    def _candidate_key(cls, draft: _CandidateDraft) -> str:
        normalized_items = ",".join(
            sorted(item.casefold() for item in draft.related_items)
        )
        normalized_title = " ".join(draft.title.casefold().split())
        return (
            f"{draft.category.value}|{draft.detected_condition}|"
            f"{normalized_items}|{normalized_title}"
        )

    @classmethod
    def _candidate_id(cls, project_id: str, key: str) -> str:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        project_key = re.sub(r"[^a-z0-9]+", "-", project_id.casefold()).strip("-")
        return f"rfi-{project_key}-{digest}"

    @classmethod
    def _item_fingerprint(
        cls,
        manufacturer: str | None,
        model: str | None,
        description: str | None,
    ) -> str:
        manuf = cls._text(manufacturer).casefold()
        model_value = cls._text(model).casefold()
        desc = cls._text(description).casefold()
        return f"{manuf}|{model_value}|{desc}"

    @staticmethod
    def _enum_value(value: Any) -> str:
        return str(getattr(value, "value", value) or "")

    @staticmethod
    def _text(value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        return value.strip()

    @classmethod
    def _has_meaningful_value(cls, value: str) -> bool:
        normalized = value.casefold().strip()
        return bool(normalized and normalized not in cls._MISSING_MODEL_TOKENS)

    @staticmethod
    def _confidence(base: float, source_count: int) -> float:
        adjusted = min(0.99, base + (min(source_count, 4) * 0.02))
        return round(max(0.01, adjusted), 2)

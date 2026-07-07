"""Deterministic revision comparison engine for Atlas Core bid intelligence."""

from __future__ import annotations

import hashlib
from typing import Any

from atlas_core.domain.bid_package_review import BidPackageReview
from atlas_core.domain.revision_comparison import (
    RevisionChangeRecord,
    RevisionChangeSeverity,
    RevisionChangeType,
    RevisionComparison,
    RevisionComparisonSourceRef,
)


class RevisionComparisonEngine:
    ENGINE_VERSION = "revision-comparison-engine/1.0.0"

    _RESPONSIBILITY_TOKENS = {
        "ofe",
        "ofci",
        "cfci",
        "nic",
        "by others",
        "owner provided",
        "contractor provided",
    }
    _ADD_ALTERNATE_TOKENS = {
        "add alternate",
        "alternate",
        "allowance",
    }

    _SEVERITY_RANK = {
        RevisionChangeSeverity.LOW: 1,
        RevisionChangeSeverity.MEDIUM: 2,
        RevisionChangeSeverity.HIGH: 3,
        RevisionChangeSeverity.CRITICAL: 4,
    }

    def build(
        self,
        baseline_review: BidPackageReview,
        comparison_review: BidPackageReview,
        baseline_revision_id: str | None = None,
        comparison_revision_id: str | None = None,
    ) -> RevisionComparison:
        baseline_id = baseline_revision_id or baseline_review.review_id
        comparison_id = comparison_revision_id or comparison_review.review_id

        changes: list[RevisionChangeRecord] = []
        changes.extend(self._compare_equipment(baseline_review, comparison_review))
        changes.extend(self._compare_assumptions(baseline_review, comparison_review))
        changes.extend(self._compare_rfi_candidates(baseline_review, comparison_review))
        labor_change = self._compare_labor_estimate(baseline_review, comparison_review)
        if labor_change is not None:
            changes.append(labor_change)

        deduped_changes = self._suppress_duplicates(changes)
        deduped_changes.sort(
            key=lambda change: (change.change_type.value, change.change_id)
        )

        added_items = sorted(
            {
                item
                for change in deduped_changes
                if change.change_type is RevisionChangeType.ITEM_ADDED
                for item in change.affected_items
            }
        )
        removed_items = sorted(
            {
                item
                for change in deduped_changes
                if change.change_type is RevisionChangeType.ITEM_REMOVED
                for item in change.affected_items
            }
        )
        modified_items = sorted(
            {
                item
                for change in deduped_changes
                if change.change_type
                in {
                    RevisionChangeType.ITEM_MODIFIED,
                    RevisionChangeType.SPECIFICATION_CHANGED,
                    RevisionChangeType.DRAWING_REFERENCE_CHANGED,
                    RevisionChangeType.SCOPE_RESPONSIBILITY_CHANGED,
                    RevisionChangeType.ADD_ALTERNATE_CHANGED,
                }
                for item in change.affected_items
            }
        )
        quantity_changes = [
            change.change_id
            for change in deduped_changes
            if change.change_type is RevisionChangeType.QUANTITY_CHANGED
        ]
        scope_changes = [
            change.change_id
            for change in deduped_changes
            if change.change_type
            in {
                RevisionChangeType.SCOPE_RESPONSIBILITY_CHANGED,
                RevisionChangeType.ADD_ALTERNATE_CHANGED,
            }
        ]
        labor_impact_flags = [
            change.change_id for change in deduped_changes if change.labor_impact
        ]
        assumption_impacts = [
            change.change_id
            for change in deduped_changes
            if change.change_type is RevisionChangeType.ASSUMPTION_CHANGED
        ]
        rfi_impacts = [
            change.change_id
            for change in deduped_changes
            if self._is_rfi_impacting_change(change)
        ]

        warnings: list[str] = []
        if not deduped_changes:
            warnings.append("No meaningful revision deltas were detected.")

        confidence = self._overall_confidence(deduped_changes, warnings)
        summary = self._build_summary(
            deduped_changes,
            added_count=len(added_items),
            removed_count=len(removed_items),
            modified_count=len(modified_items),
        )
        source_refs = self._collect_source_refs(
            baseline_review,
            comparison_review,
            deduped_changes,
        )

        return RevisionComparison(
            project_id=comparison_review.project_id,
            baseline_revision_id=baseline_id,
            comparison_revision_id=comparison_id,
            summary=summary,
            changes=deduped_changes,
            added_items=added_items,
            removed_items=removed_items,
            modified_items=modified_items,
            quantity_changes=quantity_changes,
            scope_changes=scope_changes,
            labor_impact_flags=labor_impact_flags,
            assumption_impacts=assumption_impacts,
            rfi_impacts=rfi_impacts,
            confidence=confidence,
            source_refs=source_refs,
            warnings=warnings,
            created_by_engine_version=self.ENGINE_VERSION,
        )

    def _compare_equipment(
        self,
        baseline_review: BidPackageReview,
        comparison_review: BidPackageReview,
    ) -> list[RevisionChangeRecord]:
        changes: list[RevisionChangeRecord] = []
        baseline_system_names = self._system_name_by_id(baseline_review)
        comparison_system_names = self._system_name_by_id(comparison_review)

        baseline_by_id = {
            equipment.equipment_id: equipment for equipment in baseline_review.equipment
        }
        comparison_by_id = {
            equipment.equipment_id: equipment
            for equipment in comparison_review.equipment
        }

        for equipment_id in sorted(set(comparison_by_id) - set(baseline_by_id)):
            equipment = comparison_by_id[equipment_id]
            changes.append(
                self._change_record(
                    change_type=RevisionChangeType.ITEM_ADDED,
                    title=f"Equipment item added: {equipment_id}",
                    description=(
                        f"Equipment {equipment_id} was added in the comparison revision."
                    ),
                    severity=(
                        RevisionChangeSeverity.HIGH
                        if float(getattr(equipment, "quantity", 1) or 1) > 1
                        else RevisionChangeSeverity.MEDIUM
                    ),
                    confidence=0.95,
                    source_refs=[
                        self._equipment_source_ref(
                            "comparison_equipment",
                            equipment,
                            comparison_system_names,
                        )
                    ],
                    affected_items=[equipment_id],
                    previous_value=None,
                    current_value=self._equipment_compact_value(
                        equipment,
                        comparison_system_names,
                    ),
                    detected_condition="equipment_added",
                    estimating_impact=(
                        "Added scope likely increases pricing and installation effort."
                    ),
                    labor_impact=True,
                    recommended_action=(
                        "Confirm quantity, basis-of-design, and included labor assumptions."
                    ),
                )
            )

        for equipment_id in sorted(set(baseline_by_id) - set(comparison_by_id)):
            equipment = baseline_by_id[equipment_id]
            changes.append(
                self._change_record(
                    change_type=RevisionChangeType.ITEM_REMOVED,
                    title=f"Equipment item removed: {equipment_id}",
                    description=(
                        f"Equipment {equipment_id} was removed in the comparison revision."
                    ),
                    severity=RevisionChangeSeverity.HIGH,
                    confidence=0.95,
                    source_refs=[
                        self._equipment_source_ref(
                            "baseline_equipment",
                            equipment,
                            baseline_system_names,
                        )
                    ],
                    affected_items=[equipment_id],
                    previous_value=self._equipment_compact_value(
                        equipment,
                        baseline_system_names,
                    ),
                    current_value=None,
                    detected_condition="equipment_removed",
                    estimating_impact="Removed scope likely reduces pricing and labor carry.",
                    labor_impact=True,
                    recommended_action=(
                        "Confirm this removal is not a document coordination omission."
                    ),
                )
            )

        for equipment_id in sorted(set(baseline_by_id) & set(comparison_by_id)):
            baseline_equipment = baseline_by_id[equipment_id]
            comparison_equipment = comparison_by_id[equipment_id]

            baseline_quantity = float(getattr(baseline_equipment, "quantity", 1) or 1)
            comparison_quantity = float(
                getattr(comparison_equipment, "quantity", 1) or 1
            )
            if abs(baseline_quantity - comparison_quantity) >= 1e-6:
                changes.append(
                    self._change_record(
                        change_type=RevisionChangeType.QUANTITY_CHANGED,
                        title=f"Equipment quantity changed: {equipment_id}",
                        description=(
                            f"Quantity changed from {baseline_quantity:g} to "
                            f"{comparison_quantity:g}."
                        ),
                        severity=(
                            RevisionChangeSeverity.HIGH
                            if abs(baseline_quantity - comparison_quantity) >= 2
                            else RevisionChangeSeverity.MEDIUM
                        ),
                        confidence=0.97,
                        source_refs=[
                            self._equipment_source_ref(
                                "baseline_equipment",
                                baseline_equipment,
                                baseline_system_names,
                                field="quantity",
                            ),
                            self._equipment_source_ref(
                                "comparison_equipment",
                                comparison_equipment,
                                comparison_system_names,
                                field="quantity",
                            ),
                        ],
                        affected_items=[equipment_id],
                        previous_value=baseline_quantity,
                        current_value=comparison_quantity,
                        detected_condition="equipment_quantity_changed",
                        estimating_impact=(
                            "Quantity delta affects material takeoff and labor hours."
                        ),
                        labor_impact=True,
                        recommended_action=(
                            "Update estimate quantities and re-check labor-hour ranges."
                        ),
                    )
                )

            baseline_fingerprint = self._equipment_fingerprint(
                baseline_equipment,
                baseline_system_names,
            )
            comparison_fingerprint = self._equipment_fingerprint(
                comparison_equipment,
                comparison_system_names,
            )
            if baseline_fingerprint != comparison_fingerprint:
                changes.append(
                    self._change_record(
                        change_type=RevisionChangeType.ITEM_MODIFIED,
                        title=f"Equipment attributes modified: {equipment_id}",
                        description=(
                            "Manufacturer/model/description/system or references changed "
                            "between revisions."
                        ),
                        severity=RevisionChangeSeverity.HIGH,
                        confidence=0.93,
                        source_refs=[
                            self._equipment_source_ref(
                                "baseline_equipment",
                                baseline_equipment,
                                baseline_system_names,
                            ),
                            self._equipment_source_ref(
                                "comparison_equipment",
                                comparison_equipment,
                                comparison_system_names,
                            ),
                        ],
                        affected_items=[equipment_id],
                        previous_value=self._equipment_compact_value(
                            baseline_equipment,
                            baseline_system_names,
                        ),
                        current_value=self._equipment_compact_value(
                            comparison_equipment,
                            comparison_system_names,
                        ),
                        detected_condition="equipment_attributes_modified",
                        estimating_impact=(
                            "Device attribute changes may alter basis-of-design pricing "
                            "and substitutions."
                        ),
                        labor_impact=True,
                        recommended_action=(
                            "Validate revised basis-of-design and adjust estimate line item."
                        ),
                    )
                )

            baseline_spec = self._text(
                getattr(baseline_equipment, "specification_reference", None)
            )
            comparison_spec = self._text(
                getattr(comparison_equipment, "specification_reference", None)
            )
            if baseline_spec != comparison_spec:
                changes.append(
                    self._change_record(
                        change_type=RevisionChangeType.SPECIFICATION_CHANGED,
                        title=f"Specification reference changed: {equipment_id}",
                        description=(
                            f"Specification changed from '{baseline_spec or 'none'}' to "
                            f"'{comparison_spec or 'none'}'."
                        ),
                        severity=RevisionChangeSeverity.HIGH,
                        confidence=0.95,
                        source_refs=[
                            self._equipment_source_ref(
                                "baseline_equipment",
                                baseline_equipment,
                                baseline_system_names,
                                field="specification_reference",
                            ),
                            self._equipment_source_ref(
                                "comparison_equipment",
                                comparison_equipment,
                                comparison_system_names,
                                field="specification_reference",
                            ),
                        ],
                        affected_items=[equipment_id],
                        previous_value=baseline_spec or None,
                        current_value=comparison_spec or None,
                        detected_condition="specification_reference_changed",
                        estimating_impact=(
                            "Spec section delta may shift compliance scope and product basis."
                        ),
                        labor_impact=True,
                        recommended_action=(
                            "Review new spec section requirements and update estimate assumptions."
                        ),
                    )
                )

            baseline_drawing = self._text(
                getattr(baseline_equipment, "drawing_reference", None)
            )
            comparison_drawing = self._text(
                getattr(comparison_equipment, "drawing_reference", None)
            )
            if baseline_drawing != comparison_drawing:
                changes.append(
                    self._change_record(
                        change_type=RevisionChangeType.DRAWING_REFERENCE_CHANGED,
                        title=f"Drawing reference changed: {equipment_id}",
                        description=(
                            f"Drawing changed from '{baseline_drawing or 'none'}' to "
                            f"'{comparison_drawing or 'none'}'."
                        ),
                        severity=RevisionChangeSeverity.MEDIUM,
                        confidence=0.95,
                        source_refs=[
                            self._equipment_source_ref(
                                "baseline_equipment",
                                baseline_equipment,
                                baseline_system_names,
                                field="drawing_reference",
                            ),
                            self._equipment_source_ref(
                                "comparison_equipment",
                                comparison_equipment,
                                comparison_system_names,
                                field="drawing_reference",
                            ),
                        ],
                        affected_items=[equipment_id],
                        previous_value=baseline_drawing or None,
                        current_value=comparison_drawing or None,
                        detected_condition="drawing_reference_changed",
                        estimating_impact=(
                            "Drawing reference delta may indicate revised installation context."
                        ),
                        labor_impact=True,
                        recommended_action=(
                            "Verify revised drawing context and re-check installation assumptions."
                        ),
                    )
                )

            baseline_scope_tokens = self._responsibility_tokens_for_equipment(
                baseline_equipment
            )
            comparison_scope_tokens = self._responsibility_tokens_for_equipment(
                comparison_equipment
            )
            if baseline_scope_tokens != comparison_scope_tokens:
                changes.append(
                    self._change_record(
                        change_type=RevisionChangeType.SCOPE_RESPONSIBILITY_CHANGED,
                        title=f"Scope responsibility language changed: {equipment_id}",
                        description=(
                            "Responsibility markers changed from "
                            f"{sorted(baseline_scope_tokens)} to "
                            f"{sorted(comparison_scope_tokens)}."
                        ),
                        severity=RevisionChangeSeverity.HIGH,
                        confidence=0.9,
                        source_refs=[
                            self._equipment_source_ref(
                                "baseline_equipment",
                                baseline_equipment,
                                baseline_system_names,
                                field="assumptions",
                            ),
                            self._equipment_source_ref(
                                "comparison_equipment",
                                comparison_equipment,
                                comparison_system_names,
                                field="assumptions",
                            ),
                        ],
                        affected_items=[equipment_id],
                        previous_value=sorted(baseline_scope_tokens),
                        current_value=sorted(comparison_scope_tokens),
                        detected_condition="scope_responsibility_changed",
                        estimating_impact=(
                            "Scope ownership ambiguity can shift inclusions and bid risk."
                        ),
                        labor_impact=True,
                        recommended_action=(
                            "Clarify ownership matrix for labor, materials, and coordination."
                        ),
                    )
                )

            baseline_add_alternate = self._contains_add_alternate_text(
                baseline_equipment
            )
            comparison_add_alternate = self._contains_add_alternate_text(
                comparison_equipment
            )
            if baseline_add_alternate != comparison_add_alternate:
                changes.append(
                    self._change_record(
                        change_type=RevisionChangeType.ADD_ALTERNATE_CHANGED,
                        title=f"Add alternate language changed: {equipment_id}",
                        description=(
                            "Add alternate/allowance markers changed across revisions."
                        ),
                        severity=RevisionChangeSeverity.MEDIUM,
                        confidence=0.86,
                        source_refs=[
                            self._equipment_source_ref(
                                "baseline_equipment",
                                baseline_equipment,
                                baseline_system_names,
                                field="description",
                            ),
                            self._equipment_source_ref(
                                "comparison_equipment",
                                comparison_equipment,
                                comparison_system_names,
                                field="description",
                            ),
                        ],
                        affected_items=[equipment_id],
                        previous_value=baseline_add_alternate,
                        current_value=comparison_add_alternate,
                        detected_condition="add_alternate_language_changed",
                        estimating_impact=(
                            "Alternate language changes can alter bid inclusions and labor carry."
                        ),
                        labor_impact=True,
                        recommended_action=(
                            "Confirm alternate pricing boundaries and update estimate options."
                        ),
                    )
                )

        return changes

    def _compare_assumptions(
        self,
        baseline_review: BidPackageReview,
        comparison_review: BidPackageReview,
    ) -> list[RevisionChangeRecord]:
        changes: list[RevisionChangeRecord] = []
        baseline_by_id = {
            assumption.assumption_id: assumption
            for assumption in baseline_review.engineering_assumptions
        }
        comparison_by_id = {
            assumption.assumption_id: assumption
            for assumption in comparison_review.engineering_assumptions
        }

        for assumption_id in sorted(set(comparison_by_id) - set(baseline_by_id)):
            assumption = comparison_by_id[assumption_id]
            changes.append(
                self._change_record(
                    change_type=RevisionChangeType.ASSUMPTION_CHANGED,
                    title=f"Engineering assumption added: {assumption_id}",
                    description="A new engineering assumption was introduced.",
                    severity=RevisionChangeSeverity.MEDIUM,
                    confidence=0.9,
                    source_refs=[
                        RevisionComparisonSourceRef(
                            source_type="comparison_assumption",
                            source_id=assumption_id,
                            field="description",
                            excerpt=getattr(assumption, "description", None),
                        )
                    ],
                    affected_items=[
                        self._text(getattr(assumption, "related_equipment", None))
                        or assumption_id
                    ],
                    previous_value=None,
                    current_value=getattr(assumption, "description", None),
                    detected_condition="assumption_added",
                    estimating_impact=(
                        "New assumption may affect inclusions, contingencies, and estimate narrative."
                    ),
                    labor_impact=(
                        self._text(
                            getattr(getattr(assumption, "severity", None), "value", "")
                        )
                        == "risk"
                    ),
                    recommended_action=(
                        "Review assumption validity and align estimate clarifications."
                    ),
                )
            )

        for assumption_id in sorted(set(baseline_by_id) - set(comparison_by_id)):
            assumption = baseline_by_id[assumption_id]
            changes.append(
                self._change_record(
                    change_type=RevisionChangeType.ASSUMPTION_CHANGED,
                    title=f"Engineering assumption removed: {assumption_id}",
                    description="An engineering assumption was removed.",
                    severity=RevisionChangeSeverity.MEDIUM,
                    confidence=0.9,
                    source_refs=[
                        RevisionComparisonSourceRef(
                            source_type="baseline_assumption",
                            source_id=assumption_id,
                            field="description",
                            excerpt=getattr(assumption, "description", None),
                        )
                    ],
                    affected_items=[
                        self._text(getattr(assumption, "related_equipment", None))
                        or assumption_id
                    ],
                    previous_value=getattr(assumption, "description", None),
                    current_value=None,
                    detected_condition="assumption_removed",
                    estimating_impact=(
                        "Removed assumption can reduce carried risk or conceal unresolved scope."
                    ),
                    labor_impact=(
                        self._text(
                            getattr(getattr(assumption, "severity", None), "value", "")
                        )
                        == "risk"
                    ),
                    recommended_action=(
                        "Confirm removal reflects resolved design intent, not missing documentation."
                    ),
                )
            )

        for assumption_id in sorted(set(baseline_by_id) & set(comparison_by_id)):
            baseline_assumption = baseline_by_id[assumption_id]
            comparison_assumption = comparison_by_id[assumption_id]
            baseline_value = {
                "description": self._text(
                    getattr(baseline_assumption, "description", None)
                ),
                "severity": self._text(
                    getattr(
                        getattr(baseline_assumption, "severity", None), "value", None
                    )
                ),
                "related_equipment": self._text(
                    getattr(baseline_assumption, "related_equipment", None)
                ),
            }
            comparison_value = {
                "description": self._text(
                    getattr(comparison_assumption, "description", None)
                ),
                "severity": self._text(
                    getattr(
                        getattr(comparison_assumption, "severity", None), "value", None
                    )
                ),
                "related_equipment": self._text(
                    getattr(comparison_assumption, "related_equipment", None)
                ),
            }
            if baseline_value == comparison_value:
                continue

            changes.append(
                self._change_record(
                    change_type=RevisionChangeType.ASSUMPTION_CHANGED,
                    title=f"Engineering assumption modified: {assumption_id}",
                    description="Assumption description, severity, or related scope changed.",
                    severity=(
                        RevisionChangeSeverity.HIGH
                        if "risk"
                        in {baseline_value["severity"], comparison_value["severity"]}
                        else RevisionChangeSeverity.MEDIUM
                    ),
                    confidence=0.92,
                    source_refs=[
                        RevisionComparisonSourceRef(
                            source_type="baseline_assumption",
                            source_id=assumption_id,
                            field="description",
                            excerpt=baseline_value["description"],
                        ),
                        RevisionComparisonSourceRef(
                            source_type="comparison_assumption",
                            source_id=assumption_id,
                            field="description",
                            excerpt=comparison_value["description"],
                        ),
                    ],
                    affected_items=[
                        comparison_value["related_equipment"]
                        or baseline_value["related_equipment"]
                        or assumption_id
                    ],
                    previous_value=baseline_value,
                    current_value=comparison_value,
                    detected_condition="assumption_modified",
                    estimating_impact=(
                        "Assumption changes can alter contingency and scope interpretation."
                    ),
                    labor_impact=(
                        "risk"
                        in {baseline_value["severity"], comparison_value["severity"]}
                    ),
                    recommended_action=(
                        "Reconcile assumption delta with estimator risk and labor rationale."
                    ),
                )
            )

        return changes

    def _compare_rfi_candidates(
        self,
        baseline_review: BidPackageReview,
        comparison_review: BidPackageReview,
    ) -> list[RevisionChangeRecord]:
        changes: list[RevisionChangeRecord] = []
        baseline_by_id = {
            candidate.candidate_id: candidate
            for candidate in baseline_review.rfi_candidates
        }
        comparison_by_id = {
            candidate.candidate_id: candidate
            for candidate in comparison_review.rfi_candidates
        }

        for candidate_id in sorted(set(comparison_by_id) - set(baseline_by_id)):
            candidate = comparison_by_id[candidate_id]
            changes.append(
                self._change_record(
                    change_type=RevisionChangeType.RFI_CANDIDATE_CHANGED,
                    title=f"RFI candidate added: {candidate_id}",
                    description="A new RFI candidate condition was detected.",
                    severity=RevisionChangeSeverity.HIGH,
                    confidence=0.9,
                    source_refs=[
                        RevisionComparisonSourceRef(
                            source_type="comparison_rfi_candidate",
                            source_id=candidate_id,
                            field="detected_condition",
                            excerpt=getattr(candidate, "detected_condition", None),
                        )
                    ],
                    affected_items=list(
                        getattr(candidate, "related_items", []) or [candidate_id]
                    ),
                    previous_value=None,
                    current_value={
                        "detected_condition": getattr(
                            candidate, "detected_condition", None
                        ),
                        "severity": self._text(
                            getattr(getattr(candidate, "severity", None), "value", None)
                        ),
                    },
                    detected_condition="rfi_candidate_added",
                    estimating_impact=(
                        "New ambiguity or conflict condition may change estimator clarifications."
                    ),
                    labor_impact=True,
                    recommended_action=(
                        "Validate if this candidate requires updated assumptions or labor contingency."
                    ),
                )
            )

        for candidate_id in sorted(set(baseline_by_id) - set(comparison_by_id)):
            candidate = baseline_by_id[candidate_id]
            changes.append(
                self._change_record(
                    change_type=RevisionChangeType.RFI_CANDIDATE_CHANGED,
                    title=f"RFI candidate removed: {candidate_id}",
                    description="An earlier RFI candidate condition is no longer detected.",
                    severity=RevisionChangeSeverity.MEDIUM,
                    confidence=0.88,
                    source_refs=[
                        RevisionComparisonSourceRef(
                            source_type="baseline_rfi_candidate",
                            source_id=candidate_id,
                            field="detected_condition",
                            excerpt=getattr(candidate, "detected_condition", None),
                        )
                    ],
                    affected_items=list(
                        getattr(candidate, "related_items", []) or [candidate_id]
                    ),
                    previous_value={
                        "detected_condition": getattr(
                            candidate, "detected_condition", None
                        ),
                        "severity": self._text(
                            getattr(getattr(candidate, "severity", None), "value", None)
                        ),
                    },
                    current_value=None,
                    detected_condition="rfi_candidate_removed",
                    estimating_impact=(
                        "Resolved ambiguity may reduce bid clarifications and risk carry."
                    ),
                    labor_impact=False,
                    recommended_action=(
                        "Confirm condition is resolved in documents rather than missed in parsing."
                    ),
                )
            )

        return changes

    def _compare_labor_estimate(
        self,
        baseline_review: BidPackageReview,
        comparison_review: BidPackageReview,
    ) -> RevisionChangeRecord | None:
        baseline_labor = baseline_review.labor_estimate
        comparison_labor = comparison_review.labor_estimate
        if baseline_labor is None and comparison_labor is None:
            return None

        baseline_expected = (
            float(getattr(baseline_labor, "total_labor_hours_expected", 0) or 0)
            if baseline_labor is not None
            else 0.0
        )
        comparison_expected = (
            float(getattr(comparison_labor, "total_labor_hours_expected", 0) or 0)
            if comparison_labor is not None
            else 0.0
        )

        if abs(baseline_expected - comparison_expected) < 1e-6 and (
            baseline_labor is not None and comparison_labor is not None
        ):
            return None

        percent_delta = (
            abs(comparison_expected - baseline_expected) / baseline_expected
            if baseline_expected > 0
            else 1.0
        )

        return self._change_record(
            change_type=RevisionChangeType.LABOR_ESTIMATE_CHANGED,
            title="Labor estimate changed between revisions",
            description=(
                "Total expected labor hours changed from "
                f"{baseline_expected:g} to {comparison_expected:g}."
            ),
            severity=(
                RevisionChangeSeverity.HIGH
                if percent_delta >= 0.2
                else RevisionChangeSeverity.MEDIUM
            ),
            confidence=0.9,
            source_refs=[
                RevisionComparisonSourceRef(
                    source_type="baseline_review",
                    source_id=baseline_review.review_id,
                    field="labor_estimate.total_labor_hours_expected",
                    excerpt=f"expected={baseline_expected:g}",
                ),
                RevisionComparisonSourceRef(
                    source_type="comparison_review",
                    source_id=comparison_review.review_id,
                    field="labor_estimate.total_labor_hours_expected",
                    excerpt=f"expected={comparison_expected:g}",
                ),
            ],
            affected_items=["labor_estimate"],
            previous_value={
                "total_labor_hours_expected": baseline_expected,
                "confidence": (
                    getattr(baseline_labor, "confidence", None)
                    if baseline_labor is not None
                    else None
                ),
            },
            current_value={
                "total_labor_hours_expected": comparison_expected,
                "confidence": (
                    getattr(comparison_labor, "confidence", None)
                    if comparison_labor is not None
                    else None
                ),
            },
            detected_condition="labor_estimate_changed",
            estimating_impact=(
                "Labor-hour delta affects estimate carry and discipline loading."
            ),
            labor_impact=True,
            recommended_action=(
                "Reconcile labor deltas against quantity, scope, and assumption changes."
            ),
        )

    def _build_summary(
        self,
        changes: list[RevisionChangeRecord],
        added_count: int,
        removed_count: int,
        modified_count: int,
    ) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for change in changes:
            by_type[change.change_type.value] = (
                by_type.get(change.change_type.value, 0) + 1
            )
            by_severity[change.severity.value] = (
                by_severity.get(change.severity.value, 0) + 1
            )

        return {
            "change_count": len(changes),
            "added_count": added_count,
            "removed_count": removed_count,
            "modified_count": modified_count,
            "labor_impact_count": sum(1 for change in changes if change.labor_impact),
            "rfi_impact_count": sum(
                1 for change in changes if self._is_rfi_impacting_change(change)
            ),
            "changes_by_type": by_type,
            "changes_by_severity": by_severity,
        }

    def _collect_source_refs(
        self,
        baseline_review: BidPackageReview,
        comparison_review: BidPackageReview,
        changes: list[RevisionChangeRecord],
    ) -> list[RevisionComparisonSourceRef]:
        refs: dict[tuple[str, str, str], RevisionComparisonSourceRef] = {}

        refs[("baseline_review", baseline_review.review_id, "review")] = (
            RevisionComparisonSourceRef(
                source_type="baseline_review",
                source_id=baseline_review.review_id,
                source_label=baseline_review.name,
            )
        )
        refs[("comparison_review", comparison_review.review_id, "review")] = (
            RevisionComparisonSourceRef(
                source_type="comparison_review",
                source_id=comparison_review.review_id,
                source_label=comparison_review.name,
            )
        )

        for change in changes:
            for source_ref in change.source_refs:
                key = (
                    source_ref.source_type,
                    source_ref.source_id,
                    source_ref.field or "",
                )
                refs[key] = source_ref

        return sorted(refs.values(), key=lambda ref: (ref.source_type, ref.source_id))

    def _overall_confidence(
        self,
        changes: list[RevisionChangeRecord],
        warnings: list[str],
    ) -> float:
        if not changes:
            return 0.9

        confidence = sum(change.confidence for change in changes) / len(changes)
        high_or_critical = sum(
            1
            for change in changes
            if change.severity
            in {RevisionChangeSeverity.HIGH, RevisionChangeSeverity.CRITICAL}
        )
        confidence -= min(0.15, high_or_critical * 0.01)
        confidence -= min(0.05, len(warnings) * 0.01)
        return round(max(0.05, min(0.99, confidence)), 2)

    def _suppress_duplicates(
        self,
        changes: list[RevisionChangeRecord],
    ) -> list[RevisionChangeRecord]:
        deduped: dict[str, RevisionChangeRecord] = {}
        for change in changes:
            key = self._duplicate_key(change)
            existing = deduped.get(key)
            if existing is None:
                deduped[key] = change
                continue

            existing_rank = self._SEVERITY_RANK[existing.severity]
            candidate_rank = self._SEVERITY_RANK[change.severity]
            if (candidate_rank, change.confidence) > (
                existing_rank,
                existing.confidence,
            ):
                deduped[key] = change

        return list(deduped.values())

    def _duplicate_key(self, change: RevisionChangeRecord) -> str:
        affected = ",".join(sorted(item.casefold() for item in change.affected_items))
        title = self._normalize_text(change.title)
        return (
            f"{change.change_type.value}|{change.detected_condition}|{affected}|{title}"
        )

    def _change_record(
        self,
        change_type: RevisionChangeType,
        title: str,
        description: str,
        severity: RevisionChangeSeverity,
        confidence: float,
        source_refs: list[RevisionComparisonSourceRef],
        affected_items: list[str],
        previous_value: Any,
        current_value: Any,
        detected_condition: str,
        estimating_impact: str,
        labor_impact: bool,
        recommended_action: str,
    ) -> RevisionChangeRecord:
        change_id = self._change_id(
            change_type=change_type,
            detected_condition=detected_condition,
            affected_items=affected_items,
            previous_value=previous_value,
            current_value=current_value,
        )
        return RevisionChangeRecord(
            change_id=change_id,
            change_type=change_type,
            title=title,
            description=description,
            severity=severity,
            confidence=confidence,
            source_refs=source_refs,
            affected_items=affected_items,
            previous_value=previous_value,
            current_value=current_value,
            detected_condition=detected_condition,
            estimating_impact=estimating_impact,
            labor_impact=labor_impact,
            recommended_action=recommended_action,
        )

    def _change_id(
        self,
        change_type: RevisionChangeType,
        detected_condition: str,
        affected_items: list[str],
        previous_value: Any,
        current_value: Any,
    ) -> str:
        key = "|".join(
            [
                change_type.value,
                detected_condition,
                ",".join(sorted(item.casefold() for item in affected_items)),
                self._normalize_text(repr(previous_value)),
                self._normalize_text(repr(current_value)),
            ]
        )
        return f"chg-{hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]}"

    def _equipment_source_ref(
        self,
        source_type: str,
        equipment: Any,
        system_names: dict[str, str],
        field: str | None = None,
    ) -> RevisionComparisonSourceRef:
        equipment_id = self._text(getattr(equipment, "equipment_id", None)) or "unknown"
        return RevisionComparisonSourceRef(
            source_type=source_type,
            source_id=equipment_id,
            field=field,
            source_label=self._text(getattr(equipment, "description", None)) or None,
            excerpt=(
                f"manufacturer={self._text(getattr(equipment, 'manufacturer', None)) or 'none'} "
                f"model={self._text(getattr(equipment, 'model', None)) or 'none'} "
                f"system={self._equipment_system_area(equipment, system_names)}"
            ),
        )

    def _equipment_compact_value(
        self,
        equipment: Any,
        system_names: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "manufacturer": self._text(getattr(equipment, "manufacturer", None))
            or None,
            "model": self._text(getattr(equipment, "model", None)) or None,
            "description": self._text(getattr(equipment, "description", None)),
            "quantity": float(getattr(equipment, "quantity", 1) or 1),
            "system_area": self._equipment_system_area(equipment, system_names),
            "drawing_reference": self._text(
                getattr(equipment, "drawing_reference", None)
            )
            or None,
            "specification_reference": self._text(
                getattr(equipment, "specification_reference", None)
            )
            or None,
        }

    def _equipment_fingerprint(
        self, equipment: Any, system_names: dict[str, str]
    ) -> str:
        values = [
            self._text(getattr(equipment, "manufacturer", None)).casefold(),
            self._text(getattr(equipment, "model", None)).casefold(),
            self._text(getattr(equipment, "description", None)).casefold(),
            self._equipment_system_area(equipment, system_names).casefold(),
            self._text(getattr(equipment, "drawing_reference", None)).casefold(),
            self._text(getattr(equipment, "specification_reference", None)).casefold(),
            self._normalize_text(
                " ".join(getattr(equipment, "assumptions", []) or [])
            ).casefold(),
        ]
        return "|".join(values)

    def _equipment_system_area(
        self, equipment: Any, system_names: dict[str, str]
    ) -> str:
        system_id = self._text(getattr(equipment, "system_id", None))
        if not system_id:
            return "general"

        return system_names.get(system_id, system_id)

    def _responsibility_tokens_for_equipment(self, equipment: Any) -> set[str]:
        text = " ".join(
            [
                self._text(getattr(equipment, "description", None)),
                " ".join(
                    self._text(value)
                    for value in getattr(equipment, "assumptions", []) or []
                ),
            ]
        ).casefold()
        return {token for token in self._RESPONSIBILITY_TOKENS if token in text}

    def _contains_add_alternate_text(self, equipment: Any) -> bool:
        text = " ".join(
            [
                self._text(getattr(equipment, "description", None)),
                " ".join(
                    self._text(value)
                    for value in getattr(equipment, "assumptions", []) or []
                ),
            ]
        ).casefold()
        return any(token in text for token in self._ADD_ALTERNATE_TOKENS)

    def _system_name_by_id(self, review: BidPackageReview) -> dict[str, str]:
        result: dict[str, str] = {}
        for system in review.systems:
            system_id = self._text(getattr(system, "system_id", None))
            if not system_id:
                continue
            result[system_id] = self._text(getattr(system, "name", None)) or system_id

        return result

    def _is_rfi_impacting_change(self, change: RevisionChangeRecord) -> bool:
        return (
            change.change_type
            in {
                RevisionChangeType.SCOPE_RESPONSIBILITY_CHANGED,
                RevisionChangeType.SPECIFICATION_CHANGED,
                RevisionChangeType.DRAWING_REFERENCE_CHANGED,
                RevisionChangeType.ADD_ALTERNATE_CHANGED,
                RevisionChangeType.RFI_CANDIDATE_CHANGED,
                RevisionChangeType.QUANTITY_CHANGED,
            }
            or "ambigu" in change.detected_condition
            or "rfi" in change.detected_condition
        )

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _text(value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        return value.strip()
